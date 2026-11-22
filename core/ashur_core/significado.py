"""Búsqueda por significado: los embeddings de los recuerdos y la búsqueda híbrida (docs/adr/0018-busqueda-hibrida.md).

Los vectores los calculan los nodos con MODELO; el core solo los guarda y los compara. Cada vector guarda el modelo
que lo calculó, y nunca se comparan vectores de modelos distintos.
"""

import math
import sqlite3
from array import array

# El único modelo de embeddings: todos los vectores tienen que venir del mismo.
MODELO = "bge-m3"
# Cuántos recuerdos lleva un trabajo de embeddings.
LOTE = 32
# Combinación por rangos recíprocos (RRF): cada lista suma 1 / (K + rango).
K_RRF = 60
CANDIDATOS = 20
# Por debajo de este coseno, un recuerdo no se parece a la pregunta y no entra, aunque sea el más cercano.
# Provisional: falta medirlo con bge-m3 sobre recuerdos reales.
PARECIDO_MINIMO = 0.45


def es_el_modelo(nombre: str) -> bool:
    """Ollama nombra "bge-m3:latest" al mismo modelo que "bge-m3"."""
    return nombre == MODELO or nombre.split(":")[0] == MODELO


def crear_tabla(conexion: sqlite3.Connection) -> None:
    # vector NULL: el recuerdo ya está en un trabajo, esperando su vector.
    conexion.execute(
        """CREATE TABLE embeddings (
            recuerdo_id INTEGER PRIMARY KEY,
            modelo TEXT NOT NULL,
            vector BLOB,
            trabajo_id INTEGER
        )"""
    )


def faltantes(conexion: sqlite3.Connection, limite: int = LOTE) -> list[tuple[int, str]]:
    """Recuerdos sin vector y sin trabajo que lo esté calculando."""
    return conexion.execute(
        "SELECT r.id, r.texto FROM recuerdos r LEFT JOIN embeddings e ON e.recuerdo_id = r.id"
        " WHERE e.recuerdo_id IS NULL ORDER BY r.id LIMIT ?",
        (limite,),
    ).fetchall()


def apartar(conexion: sqlite3.Connection, ids: list[int], trabajo_id: int) -> None:
    conexion.executemany(
        "INSERT OR REPLACE INTO embeddings (recuerdo_id, modelo, vector, trabajo_id) VALUES (?, ?, NULL, ?)",
        [(i, MODELO, trabajo_id) for i in ids],
    )
    conexion.commit()


def abandonar(conexion: sqlite3.Connection, trabajo_id: int) -> None:
    """El recuerdo de un trabajo que falló solo queda sin vector y sin trabajo: no se vuelve a repartir."""
    conexion.execute("UPDATE embeddings SET trabajo_id = NULL WHERE trabajo_id = ? AND vector IS NULL", (trabajo_id,))
    conexion.commit()


def _normalizado(vector: list[float]) -> array:
    norma = math.sqrt(sum(x * x for x in vector)) or 1.0
    return array("f", (x / norma for x in vector))


def guardar(conexion: sqlite3.Connection, ids: list[int], vectores: list[list[float]], modelo: str) -> None:
    conexion.executemany(
        "UPDATE embeddings SET vector = ?, modelo = ?, trabajo_id = NULL WHERE recuerdo_id = ?",
        [(_normalizado(v).tobytes(), MODELO if es_el_modelo(modelo) else modelo, i) for i, v in zip(ids, vectores)],
    )
    conexion.commit()


def olvidar(conexion: sqlite3.Connection, recuerdo_id: int) -> None:
    """Al cambiar o borrar el texto de un recuerdo, su vector ya no sirve."""
    conexion.execute("DELETE FROM embeddings WHERE recuerdo_id = ?", (recuerdo_id,))


def cercanos(conexion: sqlite3.Connection, vector: list[float], permitidos: set[int] | None = None) -> list[int]:
    """Los recuerdos más parecidos al vector, por coseno, entre los que tienen un vector del mismo modelo."""
    consulta = _normalizado(vector)
    puntajes = []
    for recuerdo_id, blob in conexion.execute(
        "SELECT recuerdo_id, vector FROM embeddings WHERE vector IS NOT NULL AND modelo = ?", (MODELO,)
    ):
        if permitidos is not None and recuerdo_id not in permitidos:
            continue
        otro = array("f")
        otro.frombytes(blob)
        if len(otro) != len(consulta):
            continue
        parecido = sum(a * b for a, b in zip(consulta, otro))
        if parecido >= PARECIDO_MINIMO:
            puntajes.append((parecido, recuerdo_id))
    puntajes.sort(reverse=True)
    return [i for _, i in puntajes[:CANDIDATOS]]


def combinar(*listas: list[int], cuantos: int) -> list[int]:
    """Combinación por rangos recíprocos: lo que aparece alto en varias listas sube."""
    puntaje: dict[int, float] = {}
    for lista in listas:
        for rango, recuerdo_id in enumerate(lista):
            puntaje[recuerdo_id] = puntaje.get(recuerdo_id, 0.0) + 1 / (K_RRF + rango + 1)
    return sorted(puntaje, key=lambda i: (-puntaje[i], i))[:cuantos]

