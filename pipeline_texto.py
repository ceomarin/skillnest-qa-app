import re
from cliente import consultar_modelo

CASOS = [
    {
        "consulta": "¿Qué es una prueba de regresión?",
        "referencia": (
            "Una prueba de regresión verifica que los cambios nuevos "
            "no rompan lo que ya funcionaba."
        ),
    },
    {
        "consulta": "¿Qué es una prueba de valor límite?",
        "referencia": (
            "La prueba de valor límite verifica el comportamiento del sistema "
            "en los extremos de un rango de valores válidos."
        ),
    },
    {
        "consulta": "¿Qué es un criterio de aceptación?",
        "referencia": (
            "Un criterio de aceptación es una condición verificable que una "
            "historia de usuario debe cumplir para considerarse terminada."
        ),
    },
]


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

def proporcion_coincidencia(tokens_referencia: list[str], tokens_respuesta: list[str]) -> float:
    unicos_referencia = set(tokens_referencia)
    if not unicos_referencia:
        return 0.0
    unicos_respuesta = set(tokens_respuesta)
    comunes = unicos_referencia & unicos_respuesta
    return len(comunes)/len(unicos_referencia)


def main():
    for numero,caso in enumerate(CASOS, start=1):
        try:
            respuesta = consultar_modelo(caso["consulta"])
        except(ValueError, RuntimeError, TimeoutError) as error:
            print("No se pudo completar la operacion:", error)
            continue     

        pct_crudo = proporcion_coincidencia(caso["referencia"].split(),respuesta.split())
        pct_proc = proporcion_coincidencia(procesar_texto(caso["referencia"]),procesar_texto(respuesta))

        
        print(f"[Caso {numero}] Coincidencia texto crudo: {pct_crudo:.1%}")
        print(f"[Caso {numero}] Coincidencia texto procesado: {pct_proc:.1%}")

if __name__== "__main__":
    main()
