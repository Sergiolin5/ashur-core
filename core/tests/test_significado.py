import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ashur_core import memoria, nodos, significado
from ashur_core.app import app

EJEMPLO = Path(__file__).resolve().parents[2] / "contracts" / "recuerdo.ejemplo.json"
ADMIN = {"X-Ashur-Clave-Admin": "a"}
GB = 1_000_000_000
QWEN7 = {"nombre": "qwen2.5:7b", "tamano": int(4.7 * GB), "capacidades": ["completion", "tools"]}
BGE = {"nombre": "bge-m3:latest", "tamano": int(1.2 * GB), "capacidades": ["embedding"]}
NOMIC = {"nombre": "nomic-embed-text", "tamano": int(0.3 * GB), "capacidades": ["embedding"]}
# Un "modelo" de juguete: cada dimensión es una raíz. Entiende que «llavecitas» y «llaves» son lo mismo, cosa que la
# búsqueda por palabras no puede.
RAICES = ("llav", "bici", "perr", "comid")


def vector(texto: str) -> list[float]:
    texto = texto.lower()
    return [1.0 if r in texto else 0.0 for r in RAICES] + [0.1]


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("ASHUR_DB", str(tmp_path / "ashur.db"))
    monkeypatch.setenv("ASHUR_CLAVE", "c")
    monkeypatch.setenv("ASHUR_CLAVE_ADMIN", "a")
    return TestClient(app, headers={"X-Ashur-Clave": "c"})


def nuevo_nodo(cliente, modelos=(QWEN7, BGE)):
    creado = cliente.post("/nodos", json={"nombre": "windows"}, headers=ADMIN).json()
    encabezado = {"X-Ashur-Clave-Nodo": creado["clave"]}
    latir(cliente, encabezado, modelos)
    return encabezado


def latir(cliente, encabezado, modelos=(QWEN7, BGE)):
    assert cliente.post("/nodo/latido", json={"modo": "full", "modelos": list(modelos)}, headers=encabezado).status_code == 200


def recordar(cliente, texto):
    datos = json.loads(EJEMPLO.read_text(encoding="utf-8"))
    del datos["id"]
    datos.update(texto=texto, identidades=[], objetos=[], opinion=None)
    return cliente.post("/recuerdos", json=datos).json()["id"]


def atender(cliente, nodo, respuesta="Listo."):
    """El nodo falso: toma un trabajo y lo devuelve. Devuelve el trabajo, o None si no había."""
    tomado = cliente.post("/nodo/trabajos/tomar", headers=nodo)
    if tomado.status_code == 204:
        return None
    trabajo = tomado.json()
    if trabajo["necesidad"] == "embedding":
        salida = {"vectores": [vector(t) for t in trabajo["entrada"]["input"]]}
    else:
        salida = {"mensaje": {"role": "assistant", "content": respuesta}}
    assert cliente.post(f"/nodo/trabajos/{trabajo['id']}", json={"salida": salida}, headers=nodo).status_code == 204
    return trabajo


def atender_todo(cliente, nodo):
    trabajos = []
    while (t := atender(cliente, nodo)) is not None:
        trabajos.append(t)
    return trabajos


# ── Funciones puras ──


def test_la_combinacion_premia_lo_que_aparece_en_las_dos_listas():
    assert significado.combinar([1, 2, 3], [3, 4], cuantos=2) == [3, 1]
    assert significado.combinar([5], cuantos=5) == [5]
    assert significado.combinar(cuantos=5) == []


def test_solo_bge_m3_calcula_embeddings():
    assert significado.es_el_modelo("bge-m3:latest") and significado.es_el_modelo("bge-m3")
    modelos = [nodos.Modelo(**NOMIC), nodos.Modelo(**BGE)]
    assert nodos.mejor_modelo("embedding", "full", modelos).nombre == "bge-m3:latest"
    assert nodos.mejor_modelo("embedding", "full", [nodos.Modelo(**NOMIC)]) is None  # nunca se mezclan modelos


# ── Búsqueda híbrida de punta a punta ──


def test_ashur_recuerda_por_significado_lo_que_las_palabras_no_encuentran(cliente, tmp_path):
    recordar(cliente, "Dejé las llaves en el cajón azul.")
    recordar(cliente, "La bicicleta está en el garaje.")
    nodo = nuevo_nodo(cliente)  # el latido reparte los recuerdos sin vector
    lote = atender(cliente, nodo)
    assert lote["necesidad"] == "embedding" and lote["modelo"] == "bge-m3:latest"
    assert lote["entrada"]["input"] == ["Dejé las llaves en el cajón azul.", "La bicicleta está en el garaje."]

    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "¿Dónde quedaron mis llavecitas?"})
    consulta = atender(cliente, nodo)
    assert consulta["necesidad"] == "embedding" and consulta["entrada"] == {"input": ["¿Dónde quedaron mis llavecitas?"]}
    respuesta = atender(cliente, nodo, "En el cajón azul.")
    sistema = respuesta["entrada"]["messages"][0]["content"]
    assert "cajón azul" in sistema  # lo trajo el significado: «llavecitas» no comparte palabra con «llaves»
    assert "garaje" not in sistema
    assert cliente.get("/conversaciones/con-1").json()["mensajes"][-1]["texto"] == "En el cajón azul."

    # Los mensajes del chat también reciben su vector en el próximo latido.
    latir(cliente, nodo)
    atender_todo(cliente, nodo)
    con = memoria.abrir(str(tmp_path / "ashur.db"))
    assert significado.faltantes(con) == []
    assert con.execute("SELECT COUNT(*) FROM embeddings WHERE vector IS NOT NULL").fetchone()[0] == 4
    con.close()


def test_las_palabras_vacias_no_traen_recuerdos(cliente, tmp_path):
    recordar(cliente, "El perro come croquetas a las siete de la mañana.")
    con = memoria.abrir(str(tmp_path / "ashur.db"))
    assert memoria.buscar_alguna(con, "¿Dónde puse las llavecitas?") == []  # «las» y «dónde» no cuentan
    assert memoria.buscar_alguna(con, "¿Qué come el perro?") == [1]
    con.close()


def test_sin_nodo_de_embeddings_ashur_responde_con_las_palabras(cliente):
    recordar(cliente, "La bicicleta está en el garaje.")
    recordar(cliente, "El perro come a las siete.")
    nodo = nuevo_nodo(cliente, modelos=(QWEN7,))
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "¿Y la bicicleta?"})
    trabajo = atender(cliente, nodo)
    assert trabajo["necesidad"] == "conversar"
    sistema = trabajo["entrada"]["messages"][0]["content"]
    assert "garaje" in sistema and "perro" not in sistema


def test_una_busqueda_que_nadie_toma_no_frena_la_respuesta(cliente, tmp_path):
    recordar(cliente, "La bicicleta está en el garaje.")
    nodo = nuevo_nodo(cliente)
    atender_todo(cliente, nodo)  # los vectores de los recuerdos
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "¿Y la bicicleta?"})
    # El nodo de embeddings se fue antes de tomar la búsqueda; queda otro que solo conversa.
    con = memoria.abrir(str(tmp_path / "ashur.db"))
    viejo = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    con.execute("UPDATE trabajos SET creado = ? WHERE necesidad = 'embedding' AND estado = 'pendiente'", (viejo,))
    con.execute("UPDATE nodos SET ultimo_latido = ?", (viejo,))
    con.commit()
    con.close()
    otro = nuevo_nodo(cliente, modelos=(QWEN7,))
    trabajo = atender(cliente, otro)
    assert trabajo["necesidad"] == "conversar" and "garaje" in trabajo["entrada"]["messages"][0]["content"]
    assert cliente.get("/conversaciones/con-1").json()["espera"] is None


def test_si_la_busqueda_falla_responde_igual(cliente):
    nodo = nuevo_nodo(cliente)
    cliente.post("/conversaciones")
    cliente.post("/conversaciones/con-1/mensajes", json={"texto": "Hola"})
    for _ in range(nodos.INTENTOS):
        t = cliente.post("/nodo/trabajos/tomar", headers=nodo).json()
        assert t["necesidad"] == "embedding"
        cliente.post(f"/nodo/trabajos/{t['id']}", json={"error": "sin memoria"}, headers=nodo)
    assert atender(cliente, nodo)["necesidad"] == "conversar"


def test_un_vector_mal_formado_se_rechaza(cliente):
    recordar(cliente, "Uno.")
    recordar(cliente, "Dos.")
    nodo = nuevo_nodo(cliente)
    t = cliente.post("/nodo/trabajos/tomar", headers=nodo).json()
    for salida in ({"vectores": [[1.0]]}, {"vectores": [[1.0], [1.0, 2.0]]}, {"vectores": [[1.0], ["x"]]}, {"mensaje": {}}):
        assert cliente.post(f"/nodo/trabajos/{t['id']}", json={"salida": salida}, headers=nodo).status_code == 422
    assert cliente.post(f"/nodo/trabajos/{t['id']}", json={"salida": {"vectores": [[1.0], [0.5]]}}, headers=nodo).status_code == 204


def test_cambiar_el_texto_de_un_recuerdo_recalcula_su_vector(cliente, tmp_path):
    id_ = recordar(cliente, "La bicicleta está en el garaje.")
    nodo = nuevo_nodo(cliente)
    atender_todo(cliente, nodo)
    con = memoria.abrir(str(tmp_path / "ashur.db"))
    assert significado.faltantes(con) == []
    cliente.patch(f"/recuerdos/{id_}", json={"texto": "La bicicleta está en la sala."}, headers=ADMIN)
    assert significado.faltantes(con) == [(id_, "La bicicleta está en la sala.")]
    cliente.patch(f"/recuerdos/{id_}", json={"opinion": "Da igual."}, headers=ADMIN)
    cliente.delete(f"/recuerdos/{id_}", headers=ADMIN)
    assert con.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0] == 0
    con.close()


def test_un_recuerdo_que_siempre_falla_no_deja_sin_vector_a_los_demas(cliente, tmp_path):
    recordar(cliente, "Uno.")
    recordar(cliente, "Veneno.")
    recordar(cliente, "Tres.")
    nodo = nuevo_nodo(cliente)

    def atender_fallando_veneno():
        tomado = cliente.post("/nodo/trabajos/tomar", headers=nodo)
        if tomado.status_code == 204:
            return False
        t = tomado.json()
        if "Veneno." in t["entrada"]["input"]:
            cliente.post(f"/nodo/trabajos/{t['id']}", json={"error": "no se pudo"}, headers=nodo)
        else:
            salida = {"vectores": [vector(x) for x in t["entrada"]["input"]]}
            cliente.post(f"/nodo/trabajos/{t['id']}", json={"salida": salida}, headers=nodo)
        return True

    while atender_fallando_veneno():
        pass
    latir(cliente, nodo)  # el lote fallido no se vuelve a repartir
    assert cliente.post("/nodo/trabajos/tomar", headers=nodo).status_code == 204
    con = memoria.abrir(str(tmp_path / "ashur.db"))
    con_vector = {r for (r,) in con.execute("SELECT recuerdo_id FROM embeddings WHERE vector IS NOT NULL")}
    assert con_vector == {1, 3} and significado.faltantes(con) == []
    con.close()


def test_una_base_de_la_version_9_recibe_los_embeddings(tmp_path):
    ruta = str(tmp_path / "ashur.db")
    con = memoria.abrir(ruta)
    con.execute("DROP TABLE embeddings")
    con.execute("PRAGMA user_version = 9")
    con.commit()
    con.close()
    con = memoria.abrir(ruta)
    assert con.execute("PRAGMA user_version").fetchone()[0] == memoria.VERSION_ESQUEMA == 10
    assert significado.faltantes(con) == []
    con.close()
