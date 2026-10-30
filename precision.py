import json
from collections import Counter
from cliente import consultar_modelo
from pipeline_texto import procesar_texto 


CASOS = [
    # 1-3: definiciones (ya existentes)
    (
        "¿Qué es una historia de usuario?",
        "Una historia de usuario describe una necesidad con un rol, "
        "un objetivo y un beneficio.",
    ),
    (
        "¿Qué código HTTP indica una credencial inválida?",
        "El código 401 indica que la credencial es inválida.",
    ),
    (
        "¿Qué es la partición de equivalencia?",
        "La partición de equivalencia agrupa valores que el sistema "
        "trata igual y prueba un valor de cada grupo.",
    ),
    # 4-8: definiciones
    (
        "¿Qué es la prueba de regresión?",
        "La prueba de regresión verifica que un cambio no haya roto "
        "el comportamiento que ya funcionaba.",
    ),
    (
        "¿Qué es la prueba de confirmación?",
        "La prueba de confirmación verifica que un defecto reportado "
        "ya fue corregido.",
    ),
    (
        "¿Qué es el análisis de valores límite?",
        "El análisis de valores límite prueba los bordes de cada partición, "
        "donde se concentran los errores por uno.",
    ),
    (
        "¿Qué es la trazabilidad en las pruebas?",
        "La trazabilidad vincula requisitos, casos de prueba, resultados y "
        "defectos para evaluar la cobertura y el impacto de los cambios.",
    ),
    (
        "¿Qué es un criterio de aceptación?",
        "Un criterio de aceptación define las condiciones que debe cumplir "
        "una historia de usuario para darse por terminada.",
    ),
    # 9-12: dato concreto
    (
        "¿Qué código HTTP indica que el cliente superó el límite de solicitudes?",
        "El código 429 indica que el cliente superó el límite de "
        "solicitudes permitidas.",
    ),
    (
        "¿Qué código HTTP devuelve FastAPI cuando la entrada no cumple el schema?",
        "El código 422 indica que la entrada no cumple el schema de validación.",
    ),
    (
        "¿Cuántos principios del testing define el ISTQB?",
        "El syllabus ISTQB CTFL define 7 principios del testing.",
    ),
    (
        "¿Cuántos valores se prueban por borde en el 3-value BVA?",
        "El 3-value BVA prueba el valor del borde y sus dos vecinos, "
        "es decir, 3 valores por borde.",
    ),
    # 13-15: negación
    (
        "¿El testing puede demostrar que un sistema no tiene defectos?",
        "No, el testing muestra la presencia de defectos, pero no puede "
        "demostrar su ausencia.",
    ),
    (
        "¿Se pueden probar todas las combinaciones de entrada de un sistema?",
        "No, el testing exhaustivo es imposible salvo en casos triviales; "
        "se usan técnicas y priorización por riesgo.",
    ),
    (
        "¿El 100 % de cobertura de sentencias implica 100 % de cobertura de ramas?",
        "No, el 100 % de cobertura de sentencias no implica 100 % de ramas, "
        "pero al revés sí.",
    ),
    # 16-18: sinónimos habituales
    (
        "¿Qué es la Definition of Done?",
        "La Definition of Done lista los criterios de salida que deben "
        "cumplirse para dar una actividad por terminada.",
    ),
    (
        "¿Qué es una prueba de caja blanca?",
        "La prueba de caja blanca deriva los casos de prueba de la "
        "estructura interna del código.",
    ),
    (
        "¿Qué es el error guessing?",
        "El error guessing anticipa posibles defectos a partir de la "
        "experiencia del tester y diseña una prueba para cada falla.",
    ),
    # 19-20: listas
    (
        "¿Cuáles son los niveles de prueba del ISTQB?",
        "Los niveles de prueba son componente, integración de componentes, "
        "sistema, integración de sistemas y aceptación.",
    ),
    (
        "¿Cuáles son los criterios de cobertura de la transición de estados?",
        "Los criterios son todos los estados, transiciones válidas y "
        "todas las transiciones.",
    ),
]


RUTA_RESULTADOS = "resultados_metricas.json"
RUTA_RESULTADOS_PARA_REVISAR = "resultados_para_revisar.txt"

SYSTEM_INSTRUCTION = (
    "Eres un asistente de QA de software. Responde en español, en una sola "
    "oración completa, directa y sin introducciones, listas ni formato. "
    "Si la pregunta pide un dato (un código, un número), inclúyelo en esa oración."
)


def contar_coincidencias(tokens_referencia: list[str],tokens_respuesta: list[str],) -> int:
    """Devuelve cuántos tokens comparten la referencia y la respuesta.
     
     Cada token cuenta tantas veces como aparezca en ambas listas (el mínimo
    de sus repeticiones). El orden no importa y la comparación distingue
    mayúsculas de minúsculas.
    """
    conteo_referencia = Counter(tokens_referencia)
    conteo_respuesta = Counter(tokens_respuesta)
    interseccion = conteo_referencia & conteo_respuesta
    return sum(interseccion.values())


def calcular_precision_cobertura_f1(tokens_referencia: list[str],tokens_respuesta: list[str],) -> dict[str, float]:
    """Calcula precisión, cobertura y F1 de dos listas de tokens."""
    coincidencias = contar_coincidencias(
        tokens_referencia, tokens_respuesta
    )

    if not tokens_respuesta or not tokens_referencia:
        return {"precision": 0.0, "cobertura": 0.0, "f1": 0.0}

    precision = coincidencias / len(tokens_respuesta)
    cobertura = coincidencias / len(tokens_referencia)

    if precision + cobertura == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * cobertura / (precision + cobertura)

    resultado = {
        "precision": precision,
        "cobertura": cobertura,
        "f1": f1,
    }

    return resultado

def calcular_metricas(texto_referencia, texto_respuesta):

    tokens_referencia = procesar_texto(texto_referencia)

    tokens_respuesta = procesar_texto(texto_respuesta)

    return calcular_precision_cobertura_f1(
        tokens_referencia, tokens_respuesta
    )

def guardar_resultados_precision_cobertura_f1(
    casos: list[tuple[str, str]], ruta: str = RUTA_RESULTADOS
) -> list[dict]:
    """Consulta el modelo por cada caso, calcula sus métricas y guarda el JSON.

    Guarda tras cada caso para no perder lo ya procesado si falla la red o la
    cuota. Un caso que falla se informa y se omite; los demás continúan.
    """
    resultados = []
    for consulta, referencia in casos:
        try:
            respuesta = consultar_modelo(consulta, SYSTEM_INSTRUCTION)
        except (ValueError, RuntimeError, TimeoutError) as error:
            print(f"No se pudo procesar '{consulta}': {error}")
            continue

        metricas = calcular_metricas(referencia, respuesta)
        resultados.append({"consulta": consulta, "respuesta": respuesta, **metricas})
        print(consulta, metricas)

        with open(ruta, "w", encoding="utf-8") as archivo:
            json.dump(resultados, archivo, indent=2, ensure_ascii=False)

    return resultados


def resumir_metricas(resultados):

    if not resultados:
        return {
            "precision_promedio": 0,
            "cobertura_promedio": 0,
            "f1_promedio": 0,
        }

    n = len(resultados)

    return {
        "precision_promedio": sum(
            r["precision"] for r in resultados
        ) / n,

        "cobertura_promedio": sum(
            r["cobertura"] for r in resultados
        ) / n,

        "f1_promedio": sum(r["f1"] for r in resultados) / n,
    }

def peores_resultados_precision_cobertura_f1(resultados, cantidad: int = 3):
    """Devuelve los resultados ordenados de menor a mayor F1, los peores primero."""
    return sorted(resultados, key=lambda r: r["f1"])[:cantidad]

def seleccionar_muestra(resultados: list[dict], cantidad: int = 5) -> list[dict]:
    """Devuelve los 'cantidad' peores y los 'cantidad' mejores por F1, sin repetir."""
    ordenados = sorted(resultados, key=lambda r: r["f1"])
    if len(ordenados) <= 2 * cantidad:
        return ordenados
    return ordenados[:cantidad] + ordenados[-cantidad:]

def guardar_muestra_para_revisar(
    ruta_resultados: str = RUTA_RESULTADOS,
    ruta: str = RUTA_RESULTADOS_PARA_REVISAR,
):
    with open(ruta_resultados, encoding="utf-8") as archivo:
        resultados = json.load(archivo)

    peores_casos = sorted(resultados, key=lambda r: r["f1"])
    muestra_para_revisar = peores_casos[:5] + peores_casos[-5:]

    with open(ruta, "w", encoding="utf-8") as archivo:
        for caso in muestra_para_revisar:
            archivo.write(f"{caso['consulta']} {caso['f1']:.2f}\n")



def main() -> int:
    # resultados = guardar_resultados_precision_cobertura_f1(CASOS)
    # if not resultados:
    #     print("No se obtuvo ningún resultado; no hay nada que resumir.")
    #     return 1
    #
    # print(f"\nResultados guardados en {RUTA_RESULTADOS}")
    # print("Resumen:", resumir_metricas(resultados))
    #
    # print("\nPeores casos por F1:")
    # for caso in peores_resultados_precision_cobertura_f1(resultados):
    #     print(caso["consulta"], round(caso["f1"], 2))

    guardar_muestra_para_revisar()
    print(f"Muestra guardada en {RUTA_RESULTADOS_PARA_REVISAR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())