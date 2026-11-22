import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # el nodo no es un paquete instalado

import pytest  # noqa: E402

from ashur_nodo import __main__ as nodo_main, ollama, senales  # noqa: E402
from ashur_nodo.politica import Senales, modo  # noqa: E402


class CoreFalso:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = []

    def pedir(self, ruta, cuerpo):
        self.llamadas.append((ruta, cuerpo))
        return self.respuestas.pop(0)


TRABAJO = (200, {"id": 7, "necesidad": "conversar", "modelo": "qwen2.5:7b", "entrada": {"messages": []}})


@pytest.mark.parametrize("respuesta", [{"message": "texto"}, {"message": {"content": ["a"]}}, ["lista"]])
def test_un_ollama_raro_vuelve_como_error_y_no_tumba_al_nodo(monkeypatch, respuesta):
    monkeypatch.setattr(ollama, "_pedir", lambda *a: respuesta)
    core = CoreFalso([TRABAJO, (204, None)])
    assert nodo_main.Nodo(core, "http://x", None, 8192, 280).atender_uno()
    ruta, cuerpo = core.llamadas[1]
    assert ruta == "/nodo/trabajos/7" and "error" in cuerpo


def test_familias_null_no_matan_el_latido(monkeypatch):
    raro = {"models": [{"name": "x", "size": 1, "details": {"families": None}}, "no-es-un-modelo"]}
    assert ollama.modelos_de(raro, None) == [{"nombre": "x", "tamano": 1, "capacidades": ["completion"]}]
    monkeypatch.setattr(ollama, "_pedir", lambda *a: {"models": None})
    monkeypatch.setattr(nodo_main.senales, "carga", lambda: 0.0)

    class Alto(BaseException):
        """Corta el bucle de la prueba; el nodo nunca atrapa un BaseException."""

    vueltas = []

    def dormir(_):
        vueltas.append(1)
        if len(vueltas) >= 2:
            raise Alto

    def core_raro(ruta, cuerpo):
        raise ValueError("el core respondió HTML")

    monkeypatch.setattr(nodo_main.time, "sleep", dormir)
    nodo = nodo_main.Nodo(CoreFalso([]), "http://x", None, 8192, 280)
    nodo.core.pedir = core_raro
    with pytest.raises(Alto):
        nodo.latir_siempre()
    assert len(vueltas) == 2  # el primer latido falló y el bucle siguió latiendo


def S(inactivo_s=1000.0, carga_ajena=0.1, enchufado=True, bateria=100):
    return Senales(inactivo_s=inactivo_s, carga_ajena=carga_ajena, enchufado=enchufado, bateria=bateria)


def test_sergio_siempre_gana_en_sus_maquinas():
    assert modo(S()) == "full"  # libre y enchufado
    assert modo(S(inactivo_s=20)) == "light"  # Sergio lo está usando
    assert modo(S(carga_ajena=0.9)) == "busy"  # otros programas lo cargan
    assert modo(S(enchufado=False, bateria=80)) == "light"  # con batería, solo lo liviano
    assert modo(S(enchufado=False, bateria=10)) == "off"  # batería baja: nada
    assert modo(S(enchufado=False, bateria=10, carga_ajena=0.9)) == "off"


def test_el_horario_que_sergio_le_pone_al_nodo():
    from ashur_nodo.politica import en_horario

    assert en_horario(None, "03:00")
    de_dia = {"desde": "08:00", "hasta": "18:00"}
    assert en_horario(de_dia, "08:00") and en_horario(de_dia, "17:59") and not en_horario(de_dia, "18:00")
    de_noche = {"desde": "22:00", "hasta": "07:00"}  # cruza la medianoche
    assert en_horario(de_noche, "23:30") and en_horario(de_noche, "06:59") and not en_horario(de_noche, "12:00")


def test_sin_senales_el_equipo_se_ofrece_entero():
    assert modo(Senales(None, None, None, None)) == "full"  # un equipo sin batería ni lector, siempre encendido


def test_los_modelos_de_ollama_en_el_formato_del_protocolo():
    etiquetas = {"models": [
        {"name": "qwen2.5:7b", "size": 4683087332, "capabilities": ["completion", "tools"], "details": {"families": ["qwen2"]}},
        {"name": "bge-m3:latest", "size": 1157672605, "details": {"families": ["bert"]}},  # Ollama viejo, sin capabilities
    ]}
    assert ollama.modelos_de(etiquetas, None) == [
        {"nombre": "qwen2.5:7b", "tamano": 4683087332, "capacidades": ["completion", "tools"]},
        {"nombre": "bge-m3:latest", "tamano": 1157672605, "capacidades": ["embedding"]},
    ]
    assert [m["nombre"] for m in ollama.modelos_de(etiquetas, ["qwen2.5:7b"])] == ["qwen2.5:7b"]


def test_una_respuesta_vacia_es_un_error_para_que_el_core_reintente(monkeypatch):
    import pytest

    monkeypatch.setattr(ollama, "_pedir", lambda *a: {"message": {"role": "assistant", "content": "  "}})
    with pytest.raises(ValueError):
        ollama.conversar("http://x", "qwen2.5:7b", {"messages": []}, 8192, 1)
    monkeypatch.setattr(ollama, "_pedir", lambda *a: {"message": {"role": "assistant", "content": "Hola."}})
    assert ollama.conversar("http://x", "qwen2.5:7b", {"messages": []}, 8192, 1) == {
        "mensaje": {"role": "assistant", "content": "Hola."}
    }


def test_las_herramientas_viajan_a_ollama_y_las_llamadas_vuelven_al_core(monkeypatch):
    pedidos = []
    llamada = {"function": {"name": "buscar_objetos", "arguments": {"texto": "bici"}}}

    def falso(base, ruta, cuerpo, espera):
        pedidos.append(cuerpo)
        return {"message": {"role": "assistant", "content": "", "tool_calls": [llamada]}}

    monkeypatch.setattr(ollama, "_pedir", falso)
    herramienta = {"type": "function", "function": {"name": "buscar_objetos", "parameters": {"type": "object"}}}
    salida = ollama.conversar("http://x", "qwen2.5:7b", {"messages": [], "tools": [herramienta], "rondas": 0}, 8192, 1)
    assert salida == {"mensaje": {"role": "assistant", "content": "", "tool_calls": [llamada]}}  # sin texto, vale
    assert pedidos[0]["tools"] == [herramienta] and "rondas" not in pedidos[0]
    ollama.conversar("http://x", "qwen2.5:7b", {"messages": []}, 8192, 1)
    assert "tools" not in pedidos[1]


def test_los_embeddings_vuelven_uno_por_texto(monkeypatch):
    import pytest

    pedidos = []

    def falso(base, ruta, cuerpo, espera):
        pedidos.append((ruta, cuerpo))
        return {"embeddings": [[0.1, 0.2] for _ in cuerpo["input"]]}

    monkeypatch.setattr(ollama, "_pedir", falso)
    assert ollama.vectores("http://x", "bge-m3:latest", {"input": ["a", "b"]}, 1) == {"vectores": [[0.1, 0.2], [0.1, 0.2]]}
    assert pedidos == [("/api/embed", {"model": "bge-m3:latest", "input": ["a", "b"]})]
    monkeypatch.setattr(ollama, "_pedir", lambda *a: {"embeddings": [[0.1]]})
    with pytest.raises(ValueError):  # uno de menos: error, para que el core reintente
        ollama.vectores("http://x", "bge-m3:latest", {"input": ["a", "b"]}, 1)


def test_las_senales_de_este_sistema_se_leen_sin_fallar():
    s = senales.leer(senales.carga(0.2))
    assert modo(s) in ("full", "light", "busy", "off")
    if sys.platform == "win32":
        assert s.inactivo_s is not None and s.inactivo_s >= 0
        assert s.carga_ajena is not None and 0 <= s.carga_ajena <= 1
