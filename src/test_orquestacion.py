from unittest.mock import MagicMock

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from enrutamiento import (
    MENSAJE_ERROR_FINAL,
    construir_cadena_con_enrutamiento,
    construir_cadena_queja_segura,
    construir_paso_clasificacion,
    procesar_mensaje_seguro,
)


def _fallar_a_proposito(x):
    raise ConnectionError("simulado")


# --- Fila "Clasificación" del checklist ------------------------------------

def test_clasificacion_normaliza_antes_de_comparar():
    modelo_falso = MagicMock()
    modelo_falso.return_value = AIMessage(content=" Queja \n")

    resultado = construir_paso_clasificacion(modelo_falso).invoke(
        {"mensaje": "algo salió mal"}
    )

    assert resultado == "queja"


def test_clasificacion_con_texto_vacio_no_rompe_el_paso():
    modelo_falso = MagicMock()
    modelo_falso.return_value = AIMessage(content="pregunta")

    resultado = construir_paso_clasificacion(modelo_falso).invoke(
        {"mensaje": ""}
    )

    assert resultado == "pregunta"


# --- Fila "Cada ruta de destino" del checklist ------------------------------

def test_cadena_queja_usa_fallback_ante_fallo_del_modelo():
    cadena_queja_falsa = RunnableLambda(_fallar_a_proposito)
    cadena_queja_segura = construir_cadena_queja_segura(cadena_queja_falsa)

    resultado = cadena_queja_segura.invoke({"mensaje": "esto no funciona"})

    assert "equipo" in resultado.lower()


def test_fallbacks_se_prueban_en_orden():
    cadena_queja_falsa = RunnableLambda(_fallar_a_proposito)
    modelo_secundario_ok = RunnableLambda(
        lambda x: "respuesta del modelo secundario"
    )
    cadena_queja_segura = construir_cadena_queja_segura(
        cadena_queja_falsa,
        fallbacks_intermedios=[modelo_secundario_ok],
    )

    resultado = cadena_queja_segura.invoke({"mensaje": "esto no funciona"})

    # El fallback intermedio funcionó, así que la respuesta genérica
    # no debió ejecutarse.
    assert resultado == "respuesta del modelo secundario"


# --- Fila "El flujo completo" del checklist ---------------------------------

def test_procesar_mensaje_seguro_devuelve_resultado_en_camino_exitoso():
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.return_value = "queja"
    cadena_queja_falsa = MagicMock()
    cadena_queja_falsa.return_value = "respuesta de queja"
    cadena = construir_cadena_con_enrutamiento(
        paso_clasificacion=clasificacion_falsa,
        cadena_queja=cadena_queja_falsa,
    )

    resultado = procesar_mensaje_seguro(cadena, "esto no funciona")

    assert resultado == "respuesta de queja"


def test_procesar_mensaje_seguro_no_propaga_excepciones():
    clasificacion_falsa = MagicMock()
    clasificacion_falsa.side_effect = ConnectionError("simulado")
    cadena_falsa = construir_cadena_con_enrutamiento(
        paso_clasificacion=clasificacion_falsa,
    )

    resultado = procesar_mensaje_seguro(cadena_falsa, "mensaje de prueba")

    assert "no pudimos procesar" in resultado.lower()
    assert resultado == MENSAJE_ERROR_FINAL
