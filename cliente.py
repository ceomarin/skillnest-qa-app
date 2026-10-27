import time
from typing import Callable, Any

from src.consumir_gemini import armar_peticion,enviar_peticion, extraer_texto


def con_reintento(funcion: Callable[[], Any],intentos: int = 3,espera_segundos: int = 2) -> Any:
    for intento in range(1, intentos + 1):
        try:
            return funcion()
        except TimeoutError:
            if intento == intentos:
                raise
            print(f"Intento {intento} de {intentos} falló por límite de uso/servidor. Reintentando...")
            time.sleep(espera_segundos)

def consultar_modelo(pregunta: str,system_instruction: str = "",) -> str:
    """Envia la pregunta a Gemini con reintentos y devuelve el texto de la respuesta."""
    url,headers, body = armar_peticion(pregunta, system_instruction)
    try:
        respuesta = con_reintento(lambda: enviar_peticion(url,headers, body))
    except TimeoutError as error:
        raise RuntimeError("El servicio no respondió tras varios intentos. Intenta más tarde.") from error
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

