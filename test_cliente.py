from unittest.mock import patch, Mock

import pytest
import requests

import cliente
from cliente import enviar_peticion, con_reintento, consultar_modelo, registrar_costo

PETICION_FALSA = ("http://fake", {}, {"pregunta": "test"})


@pytest.fixture(autouse=True)
def reiniciar_costo_total():
    with patch("cliente.costo_total_sesion", 0.0):
        yield


# --- enviar_peticion ---

def test_enviar_peticion_credencial_invalida():
    respuesta_falsa = Mock(status_code=401)

    with patch("cliente.requests.post",return_value=respuesta_falsa):
        with pytest.raises(ValueError):
            enviar_peticion("http://fake",{},{"pregunta":"test"})

def test_enviar_peticion_credencial_prohibida():
    respuesta_falsa = Mock(status_code=403)

    with patch("cliente.requests.post", return_value=respuesta_falsa):
        with pytest.raises(ValueError):
            enviar_peticion("http://fake", {}, {"pregunta": "test"})

def test_enviar_peticion_limite_de_uso():
    respuesta_falsa = Mock(status_code=429,headers={})

    with patch("cliente.requests.post", return_value=respuesta_falsa):
        with pytest.raises(TimeoutError):
            enviar_peticion("http://fake",{},{"pregunta":"test"})


def test_enviar_peticion_limite_de_uso_con_retry_after():
    respuesta_falsa = Mock(status_code=429, headers={"Retry-After": "5"})

    with patch("cliente.requests.post", return_value=respuesta_falsa):
        with pytest.raises(TimeoutError) as info:
            enviar_peticion("http://fake", {}, {"pregunta": "test"})

    assert "Reintentar en 5" in str(info.value)


def test_enviar_peticion_exito():
    respuesta_falsa = Mock(status_code =200)
    respuesta_falsa.json.return_value = {"texto": "respuesta simulada"}
    with patch("cliente.requests.post",return_value = respuesta_falsa):
        resultado = enviar_peticion("http://fake",{},{"pregunta":"test"})
    assert resultado == {"texto": "respuesta simulada"}

def test_enviar_peticion_error_servidor():
    respuesta_falsa = Mock(status_code = 503, headers={})

    with patch("cliente.requests.post",return_value = respuesta_falsa):
        with pytest.raises(TimeoutError):
            enviar_peticion("http://fake",{},{"pregunta":"test"})

def test_enviar_peticion_error_cliente():
    respuesta_falsa = Mock(status_code = 404)

    with patch("cliente.requests.post",return_value = respuesta_falsa):
        with pytest.raises(RuntimeError):
            enviar_peticion("http://fake",{},{"pregunta":"test"})

def test_enviar_peticion_error_de_conexion():
    # Timeout y ConnectionError comparten rama en cliente.py
    error_simulado = requests.exceptions.ConnectionError("simulado")

    with patch("cliente.requests.post", side_effect=error_simulado):
        with pytest.raises(TimeoutError):
            enviar_peticion("http://fake", {}, {"pregunta": "test"})

def test_enviar_peticion_error_de_requests():
    error_simulado = requests.exceptions.RequestException("simulado")

    with patch("cliente.requests.post", side_effect=error_simulado):
        with pytest.raises(RuntimeError):
            enviar_peticion("http://fake", {}, {"pregunta": "test"})

def test_enviar_peticion_json_invalido():
    respuesta_falsa = Mock(status_code=200)
    respuesta_falsa.json.side_effect = requests.exceptions.JSONDecodeError(
        "simulado", "", 0
    )

    with patch("cliente.requests.post", return_value=respuesta_falsa):
        with pytest.raises(RuntimeError):
            enviar_peticion("http://fake", {}, {"pregunta": "test"})


# --- consultar_modelo ---

def test_consultar_modelo_exito():
    respuesta_falsa = {"candidates": []}

    with (
        patch("cliente.armar_peticion", return_value=PETICION_FALSA),
        patch("cliente.enviar_peticion", return_value=respuesta_falsa),
        patch("cliente.registrar_costo") as mock_costo,
        patch("cliente.extraer_texto", return_value="respuesta simulada"),
    ):
        resultado = consultar_modelo(pregunta="pregunta de prueba")

    assert resultado == "respuesta simulada"
    mock_costo.assert_called_once_with(respuesta_falsa)

def test_consultar_modelo_convierte_error():
    with (
        patch("cliente.armar_peticion", return_value=PETICION_FALSA),
        patch("cliente.con_reintento", side_effect=TimeoutError("simulado")),
    ):
        with pytest.raises(RuntimeError):
            consultar_modelo(pregunta="pregunta de prueba")

def test_consultar_modelo_propaga_value_error():
    with (
        patch("cliente.armar_peticion", return_value=PETICION_FALSA),
        patch("cliente.enviar_peticion", side_effect=ValueError("credencial")),
        patch("cliente.time.sleep") as mock_sleep,
    ):
        with pytest.raises(ValueError):
            consultar_modelo(pregunta="pregunta de prueba")

    mock_sleep.assert_not_called()


# --- con_reintento ---

def test_con_reintento_espera_entre_intentos():
    intentos = {"n":0}
    def funcion_que_falla_una_vez():
        intentos["n"] += 1
        if intentos["n"] == 1:
            raise TimeoutError("simulado")
        return "ok"
    with patch("cliente.time.sleep") as mock_sleep:
        resultado = con_reintento(funcion_que_falla_una_vez)
    assert resultado == "ok"
    mock_sleep.assert_called_once()

def test_con_reintento_agota_intentos():
    def siempre_falla():
        raise TimeoutError("simulado")

    with patch("cliente.time.sleep"):
        with pytest.raises(TimeoutError):
            con_reintento(siempre_falla,intentos=3)


def test_con_reintento_no_reintenta_value_error():
    llamadas = {"n": 0}

    def funcion_con_credencial_invalida():
        llamadas["n"] += 1
        raise ValueError("simulado")

    with patch("cliente.time.sleep") as mock_sleep:
        with pytest.raises(ValueError):
            con_reintento(funcion_con_credencial_invalida)

    assert llamadas["n"] == 1
    mock_sleep.assert_not_called()


# --- registrar_costo ---

def test_registrar_costo_calcula():
    respuesta_falsa = {
        "usageMetadata": {
            "promptTokenCount": 2000,
            "candidatesTokenCount": 300,
            "thoughtsTokenCount": 200,
        }
    }

    costo = registrar_costo(respuesta_falsa)

    # entrada: 2000/1000*0.0003 = 0.0006; salida: (300+200)/1000*0.0025 = 0.00125
    assert costo == pytest.approx(0.00185)


def test_registrar_costo_acumula():
    respuesta_falsa = {
        "usageMetadata": {
            "promptTokenCount": 1000,
            "candidatesTokenCount": 0,
            "thoughtsTokenCount": 0,
        }
    }

    registrar_costo(respuesta_falsa)
    registrar_costo(respuesta_falsa)

    assert cliente.costo_total_sesion == pytest.approx(0.0006)
