"""Tests de registrar_traza. Sin red ni clave real."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "src"))

import pytest
from langchain_core.runnables import RunnableLambda

import agente_con_herramientas as agente


@pytest.fixture(autouse=True)
def historiales_limpios():
    agente.historiales.clear()
    yield
    agente.historiales.clear()


def _ejecutor_falso(salida=None):
    """Ejecutor sin modelo: responde cuántos mensajes de historial recibió."""

    def responder(entrada):
        vistos = len(entrada["chat_history"])
        return {
            "output": salida if salida is not None else f"vistos:{vistos}",
            "intermediate_steps": [],
        }

    return RunnableLambda(responder)


def _accion(herramienta, argumentos):
    return SimpleNamespace(tool=herramienta, tool_input=argumentos)


def _leer_lineas(ruta):
    return [
        json.loads(linea)
        for linea in ruta.read_text(encoding="utf-8").splitlines()
    ]


def test_escribe_una_linea_json_valida_con_los_campos_esperados(tmp_path):
    ruta = tmp_path / "trazas.jsonl"
    resultado = {
        "output": "Prueba 29.99, 30 y 30.01.",
        "intermediate_steps": [
            (
                _accion("calcular_valores_frontera", {"limite_superior": 30}),
                "Válidos: 29.99, 30. Inválidos: 30.01.",
            )
        ],
    }

    agente.registrar_traza("s1", "¿Qué valores pruebo?", resultado, ruta)

    (registro,) = _leer_lineas(ruta)
    assert registro["session_id"] == "s1"
    assert registro["entrada"] == "¿Qué valores pruebo?"
    assert registro["respuesta_final"] == "Prueba 29.99, 30 y 30.01."
    assert registro["acciones"] == [
        {
            "herramienta": "calcular_valores_frontera",
            "argumentos": {"limite_superior": 30},
            "observacion": "Válidos: 29.99, 30. Inválidos: 30.01.",
        }
    ]
    assert registro["timestamp"].endswith("+00:00")


def test_agrega_sin_sobrescribir(tmp_path):
    ruta = tmp_path / "trazas.jsonl"
    resultado = {"output": "ok", "intermediate_steps": []}

    agente.registrar_traza("s1", "primera", resultado, ruta)
    agente.registrar_traza("s1", "segunda", resultado, ruta)

    assert [r["entrada"] for r in _leer_lineas(ruta)] == ["primera", "segunda"]


def test_conserva_tildes_y_enie_sin_escapar(tmp_path):
    ruta = tmp_path / "trazas.jsonl"
    resultado = {"output": "Señal válida", "intermediate_steps": []}

    agente.registrar_traza("s1", "¿Está el año?", resultado, ruta)

    texto = ruta.read_text(encoding="utf-8")
    assert "Señal válida" in texto
    assert "¿Está el año?" in texto
    assert "\\u" not in texto


def test_sin_intermediate_steps_acciones_queda_vacia(tmp_path):
    ruta = tmp_path / "trazas.jsonl"

    agente.registrar_traza("s1", "hola", {"output": "respuesta"}, ruta)

    (registro,) = _leer_lineas(ruta)
    assert registro["acciones"] == []


def test_crea_la_carpeta_si_no_existe(tmp_path):
    ruta = tmp_path / "logs" / "anidada" / "trazas.jsonl"

    agente.registrar_traza("s1", "hola", {"output": "ok"}, ruta)

    assert ruta.exists()


def test_la_ruta_por_defecto_cae_en_logs_del_repositorio():
    assert agente.RUTA_TRAZAS == RAIZ / "logs" / "trazas_agente.jsonl"


# --- Herramienta con args_schema -------------------------------------------


def test_herramienta_frontera_valida_y_calcula_via_invoke():
    texto = agente.calcular_valores_frontera.invoke(
        {"limite_superior": 30, "paso": 0.01}
    )

    assert "29.99" in texto
    assert "30.01" in texto


def test_herramienta_frontera_expone_los_tres_campos_con_descripcion():
    campos = agente.ArgumentosValoresFrontera.model_fields

    assert set(campos) == {"limite_superior", "limite_inferior", "paso"}
    assert all(campo.description for campo in campos.values())
    assert agente.calcular_valores_frontera.name == "calcular_valores_frontera"


def test_herramienta_frontera_rechaza_tipos_invalidos():
    with pytest.raises(Exception, match="paso"):
        agente.calcular_valores_frontera.invoke({"paso": "tal vez"})


# --- Memoria por sesión ----------------------------------------------------


def test_dos_turnos_misma_sesion_el_segundo_ve_el_primero():
    ejecutor = agente.con_memoria(_ejecutor_falso())

    primero = agente.consultar_agente(ejecutor, "pregunta 1", "cliente_1")
    segundo = agente.consultar_agente(ejecutor, "pregunta 2", "cliente_1")

    assert primero["output"] == "vistos:0"
    assert segundo["output"] == "vistos:2"  # pregunta 1 y su respuesta


def test_sesiones_distintas_no_comparten_historial():
    ejecutor = agente.con_memoria(_ejecutor_falso())

    agente.consultar_agente(ejecutor, "menciona AR12345", "cliente_1")
    otra = agente.consultar_agente(ejecutor, "¿de qué te hablé?", "cliente_2")

    assert otra["output"] == "vistos:0"
    assert len(agente.historiales["cliente_1"].messages) == 2
    assert len(agente.historiales["cliente_2"].messages) == 2


def test_el_historial_crece_con_cada_turno():
    ejecutor = agente.con_memoria(_ejecutor_falso())

    for turno in (1, 2, 3):
        agente.consultar_agente(ejecutor, f"pregunta {turno}", "cliente_1")
        assert len(agente.historiales["cliente_1"].messages) == 2 * turno


def test_salida_en_bloques_de_gemini_se_guarda_como_texto():
    bloques = [{"type": "text", "text": "Hola", "extras": {"signature": "x"}}]
    ejecutor = agente.con_memoria(_ejecutor_falso(salida=bloques))

    resultado = agente.consultar_agente(ejecutor, "hola", "cliente_1")

    assert resultado["output"] == "Hola"
    assert agente.historiales["cliente_1"].messages[-1].content == "Hola"


def test_cerrar_sesion_libera_el_historial_y_es_segura_si_no_existe():
    ejecutor = agente.con_memoria(_ejecutor_falso())
    agente.consultar_agente(ejecutor, "hola", "cliente_1")

    agente.cerrar_sesion("cliente_1")
    agente.cerrar_sesion("nunca_existio")  # no debe lanzar

    assert "cliente_1" not in agente.historiales


def test_el_prompt_tiene_chat_history_antes_del_mensaje_humano():
    variables = [
        getattr(m, "variable_name", None) for m in agente.PROMPT_AGENTE.messages
    ]

    assert variables.index("chat_history") == 1  # tras el system, antes del human
    assert variables.index("chat_history") < variables.index("agent_scratchpad")
