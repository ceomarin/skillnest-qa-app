import json
import os
import re
import time

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


def armar_peticion(
    pregunta, system_instruction, response_schema=None, modelo=MODELO_POR_DEFECTO
):
    validar_pregunta(pregunta)
    api_key = leer_api_key()
    url = f"{URL_BASE}/{modelo}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    body = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"parts": [{"text": pregunta.strip()}]}],
    }

    if response_schema is not None:
        body["generationConfig"] = {
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        }
    return url, headers, body


def enviar_peticion(url, headers, body):
    try:
        respuesta = requests.post(
            url, headers=headers, json=body, timeout=TIMEOUT_SEGUNDOS
        )
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as error:
        raise TimeoutError(
            "No se pudo contactar al proveedor. Puede ser momentaneo."
        ) from error
    except requests.exceptions.RequestException as error:
        raise RuntimeError(
            "La peticion al servicio fallo antes de recibir respuesta."
        ) from error

    codigo = respuesta.status_code
    if codigo in (401, 403):
        raise ValueError(
            f"El servicio rechazo la credencial (HTTP {codigo}). Revisa GEMINI_API_KEY."
        )
    if codigo == 429 or codigo >= 500:
        segundos = respuesta.headers.get("Retry-After")
        sufijo = f" Reintentar en {segundos}s." if segundos else ""
        raise TimeoutError(
            f"El proveedor no pudo procesar la peticion (HTTP {codigo}).{sufijo}"
        )
    if codigo >= 400:
        raise RuntimeError(f"El servicio devolvio un error HTTP {codigo}.")

    try:
        return respuesta.json()
    except requests.exceptions.JSONDecodeError as error:
        raise RuntimeError(
            "La respuesta del servicio no llego en formato JSON valido."
        ) from error


def extraer_texto(datos):
    try:
        return datos["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(
            f"La respuesta no trae el campo esperado ({type(error).__name__}: {error})."
        ) from error


# funcion para calcular los costos de la peticion, en base a la cantidad de tokens usados
def calcular_costos(datos, precio_entrada, precio_salida):
    """Calcula el costo en USD a partir de los tokens de usageMetadata.

    Usa promptTokenCount y candidatesTokenCount, por ejemplo:
    {"promptTokenCount": 14, "candidatesTokenCount": 1, "totalTokenCount": 15}
    """
    try:
        uso = datos["usageMetadata"]
        tokens_entrada = uso["promptTokenCount"]
        tokens_salida = uso["candidatesTokenCount"]
    except (KeyError, TypeError) as error:
        raise RuntimeError(
            "La respuesta no trae el consumo de tokens (usageMetadata)."
        ) from error
    coste_entrada = tokens_entrada * precio_entrada
    coste_salida = tokens_salida * precio_salida
    return coste_entrada + coste_salida


def parsear_respuesta_json(texto, claves_rqueridas=None):
    texto_limpio = texto.strip()
    texto_limpio = re.sub(r"^```(?:json)?\s*", "", texto_limpio)
    texto_limpio = re.sub(r"\s*```$", "", texto_limpio)
    try:
        datos = json.loads(texto_limpio)
    except json.JSONDecodeError:
        raise ValueError("La repuesta del modelo no es JSON válido")

    if not isinstance(datos, dict):
        raise ValueError("La respuesta del modelo no es un objeto JSON.")

    if claves_rqueridas:
        faltantes = [clave for clave in claves_rqueridas if clave not in datos]
        if faltantes:
            raise ValueError("La respuesta no tiene la estructura esperado")
    return datos


def consultar_modelo(pregunta):

    response_schema = {
        "type": "OBJECT",
        "properties": {
            "categoria": {"type": "STRING"},
            "nivel": {"type": "NUMBER"},
        },
        "required": ["categoria", "nivel"],
    }

    system_instruction = "Eres un asistente amigable y respondes en máximo 10 palabras. Responde en un objeto json con clave 'categoria' y 'nivel' "
    url, headers, body = armar_peticion(
        pregunta, system_instruction, response_schema=response_schema
    )
    inicio = time.perf_counter()
    datos = enviar_peticion(url, headers, body)
    fin = time.perf_counter()
    latencia = fin - inicio
    print(f"Latencia: {latencia:2f} segundos")
    coste = calcular_costos(datos, 0.0000003, 0.0000025)  # ejemplo de precios por token
    print(f"Coste de la peticion: ${coste:.6f} USD")
    texto = extraer_texto(datos)
    return parsear_respuesta_json(texto, ["categoria", "nivel"])


def main():
    pregunta = "Cual es la Capital de Francia?"
    try:
        print(consultar_modelo(pregunta))
    except (ValueError, RuntimeError, TimeoutError) as error:
        print("No se pudo completar la operacion:", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
