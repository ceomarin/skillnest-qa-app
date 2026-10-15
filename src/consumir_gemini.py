import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Constantes
URL_BASE = os.getenv("GEMINI_URL")
API_KEY = os.getenv("GEMINI_API_KEY")
MODELO = "gemini-3.5-flash-lite"
PREGUNTA = "Explain how AI works in a few words"

# funcion para crear headers y body de la peticion a la api de gemini
def crear_headers_body(modelo, api_key, pregunta = "Explain how AI works in a few words"):
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    body = {
        "model": modelo,
        "input": pregunta
    }
    return headers, body

# funcion que hace o envia la peticion a la api de gemini y devuelve la respuesta
def obtener_respuesta(url,headers,body):
    try:
        response = requests.post(url=url, headers=headers, json=body, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        raise RuntimeError("Error timed out")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Gemini devolvió error HTTP {e.response.status_code}")
    except requests.exceptions.RequestException:
        raise RuntimeError("Error de red al llamar a Gemini")
    except ValueError: # JSON inválido
        raise RuntimeError("Resspuesta de Gemini no es un JSON válido")

def procesar_respuesta(respuesta):
    token = respuesta["usage"]["total_tokens"]
    modelo = respuesta["model"]
    texto = respuesta["steps"][1]["content"][0]["text"]
    print(f"Total tokens used: {token}")
    print(f"Model: {modelo}")
    print(f"Text: {texto}")

def main():
    modelo = MODELO
    pregunta = PREGUNTA
    headers, body = crear_headers_body(modelo, API_KEY, pregunta)
    respuesta = obtener_respuesta(URL_BASE, headers, body)
    print(respuesta)

if __name__ == "__main__":
    main()