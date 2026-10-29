import pytest

from pipeline_texto import limpiar_texto, procesar_texto


# --- procesar_texto ---

def test_procesar_texto_normaliza_mayusculas_y_puntuacion():
    resultado = procesar_texto("El Cielo, es AZUL!")

    assert resultado == ["el", "cielo", "es", "azul"]


def test_procesar_texto_solo_puntuacion_devuelve_lista_vacia():
    resultado = procesar_texto("¡¡¡...!!!")

    assert resultado == []


def test_procesar_texto_conserva_acentos():
    resultado = procesar_texto("¿Qué es Python?")

    assert resultado == ["qué", "es", "python"]


# --- limpiar_texto ---

def test_limpiar_texto_rechaza_tipo_no_str():
    with pytest.raises(TypeError):
        limpiar_texto(123)
