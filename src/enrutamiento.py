import logging

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    RunnableBranch,
    RunnableLambda,
    RunnablePassthrough,
)
from langchain_google_genai import ChatGoogleGenerativeAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NOMBRE_MODELO = "gemini-3.8-flash"
NOMBRE_MODELO_SECUNDARIO = "gemini-3.8-flash-lite"

MENSAJE_ERROR_FINAL = (
    "No pudimos procesar tu mensaje en este momento. "
    "Intenta de nuevo más tarde."
)

# ---------------------------------------------------------------------------
# Plantillas (no dependen del modelo, por eso viven a nivel de módulo)
# ---------------------------------------------------------------------------

plantilla_clasificacion = PromptTemplate.from_template(
    "Clasifica el siguiente mensaje de soporte en una sola "
    "palabra: pregunta, queja o sugerencia. Responde solo "
    "con esa palabra.\n\n{mensaje}"
)

plantilla_pregunta = PromptTemplate.from_template(
    "Responde esta pregunta técnica con precisión:\n\n{mensaje}"
)

plantilla_queja = PromptTemplate.from_template(
    "Responde a esta queja con empatía, reconociendo el "
    "problema antes de ofrecer una solución:\n\n{mensaje}"
)

plantilla_sugerencia = PromptTemplate.from_template(
    "Agradece esta sugerencia y explica cómo se evaluará "
    "dentro del producto:\n\n{mensaje}"
)

# Último recurso de la ruta de queja: un texto fijo que no depende de
# ningún modelo ni de la red.
respuesta_generica = RunnableLambda(
    lambda x: (
        "Gracias por tu mensaje. Un miembro de nuestro "
        "equipo te va a responder pronto."
    )
)


# ---------------------------------------------------------------------------
# Bloque 19: clasificación, rutas y bifurcación
# ---------------------------------------------------------------------------

def construir_paso_clasificacion(modelo):
    """Paso de clasificación: devuelve la categoría ya normalizada."""
    return (
        plantilla_clasificacion
        | modelo
        | StrOutputParser()
        | (lambda texto: texto.strip().lower())
    )


def construir_cadena_pregunta(modelo):
    return plantilla_pregunta | modelo | StrOutputParser()


def construir_cadena_queja(modelo):
    return plantilla_queja | modelo | StrOutputParser()


def construir_cadena_sugerencia(modelo):
    return plantilla_sugerencia | modelo | StrOutputParser()


def construir_cadena_con_enrutamiento(
    paso_clasificacion,
    cadena_queja=None,
    cadena_sugerencia=None,
    cadena_pregunta=None,
):
    """Clasifica el mensaje y lo envía a la ruta que corresponde.

    Cada ruta que no se pase queda como RunnablePassthrough: nunca se
    ejecuta si la bifurcación no la elige, así que en las pruebas basta
    con pasar la ruta que se quiere verificar.
    """
    cadena_queja = cadena_queja or RunnablePassthrough()
    cadena_sugerencia = cadena_sugerencia or RunnablePassthrough()
    cadena_pregunta = cadena_pregunta or RunnablePassthrough()

    bifurcacion = RunnableBranch(
        (lambda x: x["categoria"] == "queja", cadena_queja),
        (lambda x: x["categoria"] == "sugerencia", cadena_sugerencia),
        cadena_pregunta,  # ruta por defecto
    )
    return (
        RunnablePassthrough.assign(categoria=paso_clasificacion)
        | bifurcacion
    )


# ---------------------------------------------------------------------------
# Bloque 20: manejo de errores
# ---------------------------------------------------------------------------

def construir_cadena_queja_segura(cadena_queja, fallbacks_intermedios=None):
    """Protege la ruta de queja con with_fallbacks.

    Los fallbacks se prueban en orden: primero los intermedios (por
    ejemplo, la misma ruta con un modelo secundario) y al final la
    respuesta genérica, que no depende de ningún modelo.
    """
    alternativas = list(fallbacks_intermedios or []) + [respuesta_generica]
    return cadena_queja.with_fallbacks(alternativas)


def procesar_mensaje_seguro(cadena, mensaje):
    """Red de seguridad final: ningún fallo deja al usuario sin respuesta.

    Recibe la chain como parámetro (en vez de leerla del módulo) para
    poder inyectar una chain falsa en las pruebas.
    """
    try:
        return cadena.invoke({"mensaje": mensaje})
    except Exception:
        # logger.exception registra el mensaje y el traceback completo,
        # así el try/except genérico no oculta errores de programación.
        logger.exception("Error procesando mensaje")
        return MENSAJE_ERROR_FINAL


# ---------------------------------------------------------------------------
# Ensamblado para producción
# ---------------------------------------------------------------------------

def construir_flujo_completo(modelo, modelo_secundario):
    """Ensambla el flujo real: clasificación + rutas + fallbacks."""
    cadena_queja = construir_cadena_queja_segura(
        construir_cadena_queja(modelo),
        fallbacks_intermedios=[construir_cadena_queja(modelo_secundario)],
    )
    return construir_cadena_con_enrutamiento(
        paso_clasificacion=construir_paso_clasificacion(modelo),
        cadena_queja=cadena_queja,
        cadena_sugerencia=construir_cadena_sugerencia(modelo),
        cadena_pregunta=construir_cadena_pregunta(modelo),
    )


if __name__ == "__main__":
    load_dotenv()
    modelo = ChatGoogleGenerativeAI(model=NOMBRE_MODELO)
    modelo_secundario = ChatGoogleGenerativeAI(
        model=NOMBRE_MODELO_SECUNDARIO
    )
    cadena_con_enrutamiento = construir_flujo_completo(
        modelo, modelo_secundario
    )

    mensajes = [
        "¿Cómo cambio mi contraseña?",
        "La app se cierra cada vez que subo una foto.",
        "Estaría bueno que la app tuviera modo oscuro.",
    ]
    for mensaje in mensajes:
        print(procesar_mensaje_seguro(cadena_con_enrutamiento, mensaje))
        print()
