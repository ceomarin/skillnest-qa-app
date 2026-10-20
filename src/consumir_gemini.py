import os

import requests
from dotenv import load_dotenv

load_dotenv()

URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MODELO_POR_DEFECTO = "gemini-3.5-flash-lite"
TIMEOUT_SEGUNDOS = 30


def validar_pregunta(pregunta):
    """Detiene el flujo si la pregunta no es texto o viene vacia."""
    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("La pregunta no puede estar vacia")


def leer_api_key():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Falta GEMINI_API_KEY. Revisa que .env este en la raiz del proyecto "
            "y que el nombre de la variable sea exacto."
        )
    return api_key


def armar_peticion(pregunta, modelo=MODELO_POR_DEFECTO):
    validar_pregunta(pregunta)
    api_key = leer_api_key()
    url = f"{URL_BASE}/{modelo}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    body = {"contents": [{"parts": [{"text": pregunta.strip()}]}]}
    return url, headers, body


def verificar_estado_http(codigo):
    """Traduce los codigos de error HTTP mas comunes a mensajes accionables."""
    if codigo in (401, 403):
        raise RuntimeError(f"El servicio rechazo la credencial (HTTP {codigo}). Revisa GEMINI_API_KEY.")
    if codigo == 429:
        raise RuntimeError("Se excedio el limite de peticiones (HTTP 429). Espera un momento y reintenta.")
    if codigo >= 400:
        raise RuntimeError(
            f"El servicio devolvio un error HTTP {codigo}. "
            "Si es 400, revisa tambien el valor de GEMINI_API_KEY."
        )


def enviar_peticion(url, headers, body):
    try:
        respuesta = requests.post(url, headers=headers, json=body, timeout=TIMEOUT_SEGUNDOS)
    except requests.exceptions.Timeout as error:
        raise RuntimeError(f"El servicio no respondio en {TIMEOUT_SEGUNDOS} segundos.") from error
    except requests.exceptions.ConnectionError as error:
        raise RuntimeError("No se pudo conectar con el servicio. Revisa tu conexion e intenta de nuevo.") from error
    except requests.exceptions.RequestException as error:
        raise RuntimeError("La peticion al servicio fallo antes de recibir respuesta.") from error

    verificar_estado_http(respuesta.status_code)

    try:
        return respuesta.json()
    except requests.exceptions.JSONDecodeError as error:
        raise RuntimeError("La respuesta del servicio no llego en formato JSON valido.") from error


def extraer_texto(datos):
    try:
        return datos["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(
            f"La respuesta no trae el campo esperado ({type(error).__name__}: {error})."
        ) from error

# funcion para calcular los costos de la peticion, en base a la cantidad de tokens usados
def calcular_costos(datos,precio_entrada,precio_salida):
    uso = datos["usageMetadata"] 
    """
     {
        "promptTokenCount": 14,
        "candidatesTokenCount": 1,
        "totalTokenCount": 15,
        "promptTokensDetails": [
            {
                "modality": "TEXT",
                "tokenCount": 14
            }
        ],
        "serviceTier": "standard"
    },
    """
    coste_entrada = uso["promptTokenCount"] * precio_entrada
    coste_salida = uso["candidatesTokenCount"] * precio_salida
    return coste_entrada + coste_salida 

def consultar_modelo(pregunta):
    url, headers, body = armar_peticion(pregunta)
    datos = enviar_peticion(url, headers, body)
    coste = calcular_costos(datos, 0.0000003, 0.0000025)  # ejemplo de precios por token
    print(f"Coste de la peticion: ${coste:.6f} USD")
    return extraer_texto(datos)


def main():
    pregunta = "Explain how AI works in a few words"
    try:
        print(consultar_modelo(pregunta))
    except (ValueError, RuntimeError) as error:
        print("No se pudo completar la operacion:", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
