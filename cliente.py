import time
import random
import requests
from typing import Callable, Any

from src.consumir_gemini import armar_peticion, extraer_texto

PRECIO_ENTRADA_POR_1000 = 0.0003  # USD, gemini-3.5-flash-lite
PRECIO_SALIDA_POR_1000 = 0.0025   # USD, incluye razonamiento
TIMEOUT_SEGUNDOS = 30
costo_total_sesion = 0.0


def enviar_peticion(url: str, headers: dict, body: dict) -> dict:
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

def con_reintento(funcion: Callable[[], Any],intentos: int = 3,espera_base: int = 2, espera_maxima: float = 30) -> Any:
    for intento in range(1, intentos + 1):
        try:
            return funcion()
        except TimeoutError:
            if intento == intentos:
                raise
            espera = min(espera_base * (2 ** (intento - 1)), espera_maxima)
            espera_con_jitter = espera - random.uniform(0, espera * 0.1)
            print(f"Intento {intento} de {intentos} falló. Reintentando en {espera_con_jitter:.1f}s...")
            time.sleep(espera_con_jitter)

def registrar_costo(respuesta: dict) -> float:
    global costo_total_sesion
    uso = respuesta.get("usageMetadata", {})
    entrada = uso.get("promptTokenCount", 0)
    salida = uso.get("candidatesTokenCount", 0) + uso.get("thoughtsTokenCount", 0)
    costo_estimado = (
        entrada / 1000 * PRECIO_ENTRADA_POR_1000
        + salida / 1000 * PRECIO_SALIDA_POR_1000
    )
    costo_total_sesion += costo_estimado
    print(
        f"Operación: {entrada} tokens de entrada, {salida} de salida, "
        f"costo estimado: ${costo_estimado:.6f} (acumulado: ${costo_total_sesion:.6f})"
    )
    return costo_estimado

def consultar_modelo(pregunta: str,system_instruction: str = "",) -> str:
    """Envia la pregunta a Gemini con reintentos y devuelve el texto de la respuesta."""
    url, headers, body = armar_peticion(pregunta, system_instruction)
    try:
        respuesta = con_reintento(lambda: enviar_peticion(url, headers, body))
    except TimeoutError as error:
        raise RuntimeError(
            "El servicio no respondió tras varios intentos. Intenta más tarde."
        ) from error
    registrar_costo(respuesta)
    return extraer_texto(respuesta)

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

    # for i in range(20):
    #     try:
    #         respuesta = consultar_modelo(f"Pregunta de prueba número {i}")
    #         print(f"Respuesta {i}: {respuesta[:40]}...")
    #     except RuntimeError as error:
    #         print(f"Respuesta {i} falló definitivamente: {error}")

    # print(f"Costo total del ensayo: ${costo_total_sesion:.6f}")