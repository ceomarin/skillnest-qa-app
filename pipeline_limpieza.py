import re
from collections import Counter

def limpiar_texto(texto: str) -> str:
    """Normaliza el texto: minúsculas y sin puntuación."""
    if not isinstance(texto, str):
        tipo = type(texto).__name__
        raise TypeError(f"limpiar_texto espera str, no {tipo}")
    texto = texto.lower()
    texto = re.sub(r"[^\w\s]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto

def tokenizar(texto_limpio: str) -> list[str]:
    """Convierte texto limpio en una lista de tokens."""
    return texto_limpio.split()

def procesar_texto(texto: str) -> list[str]:
    """Limpia y tokeniza un texto."""
    texto_limpio = limpiar_texto(texto)
    return tokenizar(texto_limpio)

def vectorizar(tokens: list[str]) -> Counter:
    """Cuenta cuántas veces aparece cada token."""
    return Counter(tokens)

def procesar_texto(texto):
    texto_limpio = limpiar_texto(texto)
    return tokenizar(texto_limpio)

if __name__ == "__main__":
    texto = "El gato, el perro y el gato corren."  

    # texto_limpio = limpiar_texto(texto)
    # tokens = tokenizar(texto_limpio)
    # conteo = vectorizar(tokens)
    # print("texto :",texto)
    # print("Texto limpio:", texto_limpio)
    # print("Tokens:", tokens)
    # print("Conteo:", conteo)

    # referencia = "El cielo es azul."
    # respuesta = "el cielo es azul"
    # tokens_referencia = referencia.split()
    # tokens_respuesta = respuesta.split()
    # print(f"tokens_referencia: {tokens_referencia}")
    # print(f"tokens_respuesta: {tokens_respuesta}")

    # comunes = set(tokens_referencia) & set(tokens_respuesta)
    # print("set: tokens_referencia: ",set(tokens_referencia))
    # print("set: tokens_respuesta: ",set(tokens_respuesta))
    # print("comunes: ",comunes)
    # if tokens_referencia:
    #     proporcion = len(comunes) / len(set(tokens_referencia))
    #     print("proporcion: ",proporcion)
    #     print("len comunes: ",len(comunes))
    #     print("len set tokens_referencia: ",len(set(tokens_referencia)))
    # else:
    #     proporcion = 0.0
    # print(f"Coincidencia: {proporcion:.0%}")

    # comunes = set(procesar_texto(referencia)) & set(procesar_texto(respuesta))
    # print("set: tokens_referencia: ",set(procesar_texto(referencia)))
    # print("set: tokens_respuesta: ",set(procesar_texto(respuesta)))
    # print("comunes: ",comunes)
    # if tokens_referencia:
    #     proporcion = len(comunes) / len(set(procesar_texto(referencia)))
    #     print("proporcion: ",proporcion)
    #     print("len comunes: ",len(comunes))
    #     print("len set tokens_referencia: ",len(set(procesar_texto(referencia))))
    # else:
    #     proporcion = 0.0
    # print(f"Coincidencia: {proporcion:.0%}")

  