from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from src.cadena_tres_pasos import construir_cadena

ESTRUCTURA = '{"rol": "cliente", "objetivo": "aplicar cupón", "beneficio": null, "criterios": [{"id": "CA-1", "texto": "Un cupón válido reduce el total."}]}'
CASOS = '{"casos": [{"criterio_id": "CA-1", "tipo": "valido", "titulo": "Cupón válido", "resultado_esperado": "El total baja"}]}'
TABLA = "| Criterio | Tipo |\n|---|---|\n| CA-1 | valido |"


def _modelo_falso():
    modelo = MagicMock()
    modelo.side_effect = [
        AIMessage(content=ESTRUCTURA),
        AIMessage(content=CASOS),
        AIMessage(content=TABLA),
    ]
    return modelo


def test_cadena_conecta_los_tres_pasos():
    modelo = _modelo_falso()
    resultado = construir_cadena(modelo).invoke({"hu": "historia de prueba"})
    assert modelo.call_count == 3
    assert resultado == TABLA


def test_cada_paso_recibe_la_salida_del_anterior():
    modelo = _modelo_falso()
    construir_cadena(modelo).invoke({"hu": "historia de prueba"})
    prompts = [llamada.args[0].to_string() for llamada in modelo.call_args_list]
    assert "historia de prueba" in prompts[0]
    assert ESTRUCTURA in prompts[1]
    assert CASOS in prompts[2]


def test_ningun_paso_recibe_el_repr_del_mensaje():
    modelo = _modelo_falso()
    construir_cadena(modelo).invoke({"hu": "historia de prueba"})
    for llamada in modelo.call_args_list:
        assert "content=" not in llamada.args[0].to_string()
