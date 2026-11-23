"""Memoria de Ashur: modelos de contracts/recuerdo.schema.json y su tabla SQLite (docs/adr/0004-memoria.md)."""

import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from ashur_core import chat, identidades, inventario, modulos, nodos, personalidad, personas, significado
from ashur_core.galaxia import Aprendizaje  # lo que hace crecer el polvo, del contrato de la galaxia

VERSION_ESQUEMA = 15


class Identidad(BaseModel):
    """Una persona o una mascota que aparece en el recuerdo."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    identidad_id: str | None = Field(min_length=1)


class Objeto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    inventario_id: str | None = Field(min_length=1)


class RecuerdoNuevo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texto: str = Field(min_length=1)
    origen: str = Field(min_length=1)
    fecha: AwareDatetime
    sensibilidad: Literal["normal", "privado", "sensible"]
    identidades: list[Identidad]
    objetos: list[Objeto]
    opinion: str | None = Field(min_length=1)


class Recuerdo(RecuerdoNuevo):
    id: int = Field(ge=1)


class CambiosRecuerdo(BaseModel):
    """Lo que se cambia de un recuerdo. Solo se tocan los campos enviados."""

    model_config = ConfigDict(extra="forbid")

    texto: str | None = Field(default=None, min_length=1)
    origen: str | None = Field(default=None, min_length=1)
    fecha: AwareDatetime | None = None
    sensibilidad: Literal["normal", "privado", "sensible"] | None = None
    identidades: list[Identidad] | None = None
    objetos: list[Objeto] | None = None
    opinion: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def solo_opinion_puede_ser_null(self) -> "CambiosRecuerdo":
        nulos = [c for c in self.model_fields_set if c != "opinion" and getattr(self, c) is None]
        if nulos:
            raise ValueError(f"Estos campos no pueden ser null: {', '.join(sorted(nulos))}")
        return self


def abrir(ruta: str) -> sqlite3.Connection:
    """Abre la base y la deja en la versión de esquema que conoce este código."""
    # Una conexión por pedido; FastAPI la usa desde varios hilos.
    conexion = sqlite3.connect(ruta, check_same_thread=False, isolation_level=None)
    try:
        # WAL: mientras un pedido escribe, los demás siguen leyendo. Queda guardado en la base; fuera de una
        # transacción, porque dentro SQLite no lo cambia. El respaldo tiene que copiar también -wal y -shm.
        conexion.execute("PRAGMA journal_mode=WAL")
        conexion.execute("BEGIN IMMEDIATE")  # un solo pedido migra a la vez
        version = conexion.execute("PRAGMA user_version").fetchone()[0]
        if version > VERSION_ESQUEMA:
            raise RuntimeError(
                f"La base tiene el esquema {version} y este código solo conoce hasta el {VERSION_ESQUEMA}."
            )
        if version == 0:
            conexion.execute(
                """CREATE TABLE recuerdos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    texto TEXT NOT NULL,
                    origen TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    sensibilidad TEXT NOT NULL,
                    identidades TEXT NOT NULL,
                    objetos TEXT NOT NULL,
                    opinion TEXT
                )"""
            )
        if version == 1:
            _migrar_1_a_2(conexion)
        if version < 3:
            _migrar_2_a_3(conexion)
        if version < 4:
            _migrar_3_a_4(conexion)
        if version < 5:
            identidades.crear_tabla(conexion)  # versión 5: la lista de identidades
        if version < 6:
            modulos.crear_tabla_pedidos(conexion)  # versión 6: pedidos de acciones que escriben
        if version < 7:
            inventario.crear_tabla(conexion)  # versión 7: el inventario de objetos
        if version < 8:
            identidades.reservar_ids_enlazados(conexion)  # versión 8: enlaces viejos a identidades
        if version < 9:
            chat.crear_tablas(conexion)  # versión 9: el chat
            nodos.crear_tablas(conexion)  # y los nodos de casa con su cola de trabajos
        if version < 10:
            significado.crear_tabla(conexion)  # versión 10: embeddings para la búsqueda por significado
        if version < 11:
            modulos.crear_tabla_ajustes(conexion)  # versión 11: ajustes de los módulos
            nodos.agregar_ajustes(conexion)  # y de los nodos
        if version < 12:
            personas.migrar(conexion)  # versión 12: otras personas en el chat, con su clave y su rol
        if version < 13:
            personalidad.migrar(conexion)  # versión 13: correcciones al terminar cada conversación
        if version < 14:
            inventario.migrar_13_a_14(conexion)  # versión 14: jerarquía y datos ampliados de los objetos
        if version < 15:
            _migrar_14_a_15(conexion)  # versión 15: los mensajes del chat ya no son recuerdos
        conexion.execute(f"PRAGMA user_version = {VERSION_ESQUEMA}")
        conexion.execute("COMMIT")
    except BaseException:
        if conexion.in_transaction:
            conexion.execute("ROLLBACK")
        conexion.close()
        raise
    conexion.isolation_level = ""  # de aquí en adelante, transacciones normales con commit()
    return conexion


def _migrar_14_a_15(conexion: sqlite3.Connection) -> None:
    """Versión 15: cada recuerdo que sale del chat guarda de qué mensaje salió (docs/adr/0028-recuerdos-del-chat.md).
    Los de antes, cuando cada mensaje era un recuerdo, salieron de su propio mensaje."""
    conexion.execute("ALTER TABLE recuerdos ADD COLUMN mensaje_id INTEGER")
    conexion.execute(
        "UPDATE recuerdos SET mensaje_id = (SELECT m.id FROM mensajes m WHERE m.recuerdo_id = recuerdos.id)"
        " WHERE id IN (SELECT recuerdo_id FROM mensajes)"
    )
    chat.migrar_14_a_15(conexion)


def _migrar_3_a_4(conexion: sqlite3.Connection) -> None:
    """Versión 4: índice de búsqueda por palabras (FTS5) sobre el texto y la opinión, sin tildes."""
    conexion.execute(
        "CREATE VIRTUAL TABLE recuerdos_busqueda USING fts5(texto, opinion, content='recuerdos', content_rowid='id',"
        " tokenize='unicode61 remove_diacritics 2')"
    )
    conexion.execute(
        "CREATE TRIGGER recuerdos_ai AFTER INSERT ON recuerdos BEGIN"
        " INSERT INTO recuerdos_busqueda (rowid, texto, opinion) VALUES (new.id, new.texto, new.opinion); END"
    )
    conexion.execute(
        "CREATE TRIGGER recuerdos_ad AFTER DELETE ON recuerdos BEGIN"
        " INSERT INTO recuerdos_busqueda (recuerdos_busqueda, rowid, texto, opinion)"
        " VALUES ('delete', old.id, old.texto, old.opinion); END"
    )
    conexion.execute(
        "CREATE TRIGGER recuerdos_au AFTER UPDATE ON recuerdos BEGIN"
        " INSERT INTO recuerdos_busqueda (recuerdos_busqueda, rowid, texto, opinion)"
        " VALUES ('delete', old.id, old.texto, old.opinion);"
        " INSERT INTO recuerdos_busqueda (rowid, texto, opinion) VALUES (new.id, new.texto, new.opinion); END"
    )
    conexion.execute("INSERT INTO recuerdos_busqueda (recuerdos_busqueda) VALUES ('rebuild')")


def _migrar_2_a_3(conexion: sqlite3.Connection) -> None:
    """Versión 3: tabla meta con la fecha en que Ashur empezó a aprender. Una base nueva guarda ese momento; una base
    que ya existía guarda el momento en que se migra, porque no sabe cuándo se creó."""
    conexion.execute("CREATE TABLE meta (clave TEXT PRIMARY KEY, valor TEXT NOT NULL)")
    conexion.execute(
        "INSERT INTO meta (clave, valor) VALUES ('inicio_aprendizaje', ?)",
        (datetime.now(timezone.utc).isoformat(),),
    )


def _migrar_1_a_2(conexion: sqlite3.Connection) -> None:
    """Versión 1: personas con contacto_id. Versión 2: identidades con identidad_id."""
    conexion.execute("ALTER TABLE recuerdos RENAME COLUMN personas TO identidades")
    for id_, identidades in conexion.execute("SELECT id, identidades FROM recuerdos").fetchall():
        nuevas = [{"nombre": i["nombre"], "identidad_id": i["contacto_id"]} for i in json.loads(identidades)]
        conexion.execute(
            "UPDATE recuerdos SET identidades = ? WHERE id = ?", (json.dumps(nuevas, ensure_ascii=False), id_)
        )


def _desde_fila(fila: tuple) -> Recuerdo:
    id_, texto, origen, fecha, sensibilidad, identidades, objetos, opinion = fila
    return Recuerdo(
        id=id_,
        texto=texto,
        origen=origen,
        fecha=fecha,
        sensibilidad=sensibilidad,
        identidades=json.loads(identidades),
        objetos=json.loads(objetos),
        opinion=opinion,
    )


def crear(conexion: sqlite3.Connection, nuevo: RecuerdoNuevo, mensaje_id: int | None = None) -> Recuerdo:
    """[mensaje_id] es el mensaje del chat del que un nodo sacó este recuerdo. De ahí sale de qué conversación es, y
    con eso de quién (ashur_core/personas.py)."""
    cursor = conexion.execute(
        "INSERT INTO recuerdos (texto, origen, fecha, sensibilidad, identidades, objetos, opinion, mensaje_id)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            nuevo.texto,
            nuevo.origen,
            nuevo.fecha.isoformat(),
            nuevo.sensibilidad,
            json.dumps([i.model_dump() for i in nuevo.identidades], ensure_ascii=False),
            json.dumps([o.model_dump() for o in nuevo.objetos], ensure_ascii=False),
            nuevo.opinion,
            mensaje_id,
        ),
    )
    conexion.commit()
    return Recuerdo(id=cursor.lastrowid, **nuevo.model_dump())


def listar(conexion: sqlite3.Connection) -> list[Recuerdo]:
    filas = conexion.execute(
        "SELECT id, texto, origen, fecha, sensibilidad, identidades, objetos, opinion FROM recuerdos ORDER BY id"
    ).fetchall()
    return [_desde_fila(f) for f in filas]


def buscar(conexion: sqlite3.Connection, texto: str) -> list[Recuerdo]:
    """Recuerdos que tienen todas las palabras de [texto], o palabras que empiezan con ellas, sin importar tildes.
    Los más relevantes primero."""
    palabras = re.findall(r"\w+", texto)
    if not palabras:
        return []
    consulta = " ".join(f'"{p}"*' for p in palabras)
    filas = conexion.execute(
        "SELECT r.id, r.texto, r.origen, r.fecha, r.sensibilidad, r.identidades, r.objetos, r.opinion"
        " FROM recuerdos_busqueda JOIN recuerdos r ON r.id = recuerdos_busqueda.rowid"
        " WHERE recuerdos_busqueda MATCH ? ORDER BY rank",
        (consulta,),
    ).fetchall()
    return [_desde_fila(f) for f in filas]


# Palabras tan comunes que aparecen en casi cualquier recuerdo: no sirven para encontrar uno.
PALABRAS_VACIAS = frozenset(
    "las los del con por para que una uno unos unas como esta este esto estos estas eso esa ese pero sus mis tus "
    "donde dónde cuando cuándo porque qué cual cuál quien quién muy más mas también tiene tengo hay fue era son "
    "estoy está están ser sin sobre entre desde hasta todo toda todos todas nos les ella ello ellos ellas yo".split()
)


def consulta_de(texto: str) -> str | None:
    """La consulta de FTS5 con alguna de las palabras de [texto] que sirven para buscar, o None si no hay ninguna.
    También la usa la búsqueda en el historial del chat (chat.buscar)."""
    palabras = [p for p in re.findall(r"\w+", texto) if len(p) >= 3 and p.lower() not in PALABRAS_VACIAS]
    return " OR ".join(f'"{p}"*' for p in palabras) if palabras else None


def buscar_alguna(
    conexion: sqlite3.Connection, texto: str, limite: int = 20, permitidos: set[int] | None = None
) -> list[int]:
    """Para el chat: recuerdos con alguna de las palabras de [texto] (de tres letras o más y que no sean palabras
    vacías), los más relevantes primero. A diferencia de [buscar], no exige todas: una frase entera casi nunca aparece
    completa en un recuerdo."""
    consulta = consulta_de(texto)
    if consulta is None:
        return []
    limite_sql = "" if permitidos is not None else f" LIMIT {int(limite)}"
    filas = conexion.execute(
        f"SELECT rowid FROM recuerdos_busqueda WHERE recuerdos_busqueda MATCH ? ORDER BY rank{limite_sql}", (consulta,)
    ).fetchall()
    # Con [permitidos], solo esos: con otra persona, Ashur solo usa lo que salió de ella (docs/adr/0022).
    ids = [f[0] for f in filas if permitidos is None or f[0] in permitidos]
    return ids[:limite]


def salidos_de(conexion: sqlite3.Connection, mensajes: set[int]) -> set[int]:
    """Los recuerdos que salieron de esos mensajes del chat."""
    if not mensajes:
        return set()
    marcas = ",".join("?" * len(mensajes))
    filas = conexion.execute(f"SELECT id FROM recuerdos WHERE mensaje_id IN ({marcas})", list(mensajes)).fetchall()
    return {f[0] for f in filas}


def obtener(conexion: sqlite3.Connection, id_: int) -> Recuerdo | None:
    fila = conexion.execute(
        "SELECT id, texto, origen, fecha, sensibilidad, identidades, objetos, opinion FROM recuerdos WHERE id = ?", (id_,)
    ).fetchone()
    return _desde_fila(fila) if fila else None


def editar(conexion: sqlite3.Connection, id_: int, cambios: CambiosRecuerdo) -> Recuerdo | None:
    actual = obtener(conexion, id_)
    if actual is None:
        return None
    datos = actual.model_dump(exclude={"id"})
    datos.update({campo: getattr(cambios, campo) for campo in cambios.model_fields_set})
    nuevo = RecuerdoNuevo.model_validate(datos)
    conexion.execute(
        "UPDATE recuerdos SET texto = ?, origen = ?, fecha = ?, sensibilidad = ?, identidades = ?, objetos = ?,"
        " opinion = ? WHERE id = ?",
        (
            nuevo.texto,
            nuevo.origen,
            nuevo.fecha.isoformat(),
            nuevo.sensibilidad,
            json.dumps([i.model_dump() for i in nuevo.identidades], ensure_ascii=False),
            json.dumps([o.model_dump() for o in nuevo.objetos], ensure_ascii=False),
            nuevo.opinion,
            id_,
        ),
    )
    if nuevo.texto != actual.texto:
        significado.olvidar(conexion, id_)  # el vector viejo ya no corresponde; se vuelve a calcular
        chat.seguir_al_recuerdo(conexion, id_, nuevo.texto)
    conexion.commit()
    return Recuerdo(id=id_, **nuevo.model_dump())


def borrar(conexion: sqlite3.Connection, id_: int) -> bool:
    fila = conexion.execute("SELECT mensaje_id FROM recuerdos WHERE id = ?", (id_,)).fetchone()
    cursor = conexion.execute("DELETE FROM recuerdos WHERE id = ?", (id_,))
    significado.olvidar(conexion, id_)
    if cursor.rowcount > 0:
        chat.seguir_al_recuerdo(conexion, id_, chat.BORRADO)
        if fila[0] is not None:
            chat.borrar_intercambio(conexion, fila[0])
    conexion.commit()
    return cursor.rowcount > 0


class CambioInicio(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inicio: AwareDatetime


def aprendizaje(conexion: sqlite3.Connection) -> Aprendizaje:
    inicio = conexion.execute("SELECT valor FROM meta WHERE clave = 'inicio_aprendizaje'").fetchone()[0]
    recuerdos = conexion.execute("SELECT COUNT(*) FROM recuerdos").fetchone()[0]
    return Aprendizaje(inicio=inicio, recuerdos=recuerdos)


def cambiar_inicio(conexion: sqlite3.Connection, inicio: datetime) -> Aprendizaje:
    conexion.execute("UPDATE meta SET valor = ? WHERE clave = 'inicio_aprendizaje'", (inicio.isoformat(),))
    conexion.commit()
    return aprendizaje(conexion)


def contar_por_origen(conexion: sqlite3.Connection, origen: str) -> int:
    return conexion.execute("SELECT COUNT(*) FROM recuerdos WHERE origen = ?", (origen,)).fetchone()[0]


# ── Lo que un nodo decide recordar del chat (docs/adr/0028-recuerdos-del-chat.md) ──

ORIGEN_CHAT = "chat"
POR_INTERCAMBIO = 3
LARGO_RECUERDO = 300
# Cuántos mensajes anteriores ve el nodo para entender el intercambio («sí, ese» no dice nada solo).
CONTEXTO = 4

INSTRUCCIONES = (
    "Decides qué vale la pena guardar en la memoria de Ashur, un asistente personal, del último intercambio de una "
    "conversación con {nombre}. Guarda solo lo que {nombre} contó y que servirá más adelante: hechos de su vida, "
    "planes, gustos, decisiones, personas, lugares y dónde están sus cosas. No guardes saludos, preguntas, pedidos "
    "del momento ni lo que dijo Ashur: eso solo sirve para entender. Escribe como máximo {cuantas} líneas, cada una "
    "empezando con «- », en tercera persona, nombrando a {nombre}, y que se entiendan solas, sin la conversación. Si "
    "no hay nada que guardar, escribe solo NADA."
)


def pedido_de_recuerdos(mensajes: list, nombre: str, id_conversacion: str) -> dict:
    """El trabajo de fondo que sale tras cada respuesta de Ashur: [mensajes] termina en el mensaje de la persona y la
    respuesta. Nunca lleva herramientas."""
    def lineas(lista):
        return "\n".join(f"{'Ashur' if m.rol == 'assistant' else nombre}: {m.texto}" for m in lista)

    antes, intercambio = mensajes[:-2], mensajes[-2:]
    transcripcion = (f"Antes, solo para entender:\n{lineas(antes)}\n\n" if antes else "") + (
        f"Último intercambio:\n{lineas(intercambio)}"
    )
    return {
        "messages": [
            {"role": "system", "content": INSTRUCCIONES.format(nombre=nombre, cuantas=POR_INTERCAMBIO)},
            {"role": "user", "content": transcripcion},
        ],
        "proposito": "recuerdos",
        "conversacion": id_conversacion,
        "mensaje": intercambio[0].id,
        "vistos": [m.id for m in mensajes],
    }


def leer_recuerdos(texto: str) -> list[str]:
    """Las líneas «- …» de la respuesta del nodo, como máximo tres. NADA es ninguna."""
    return personalidad.vinetas(texto, POR_INTERCAMBIO, LARGO_RECUERDO)
