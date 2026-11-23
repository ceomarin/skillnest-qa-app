"""Dataset de tuning (B29): clasificar un criterio de aceptación con formato JSON fijo.

Tarea de comportamiento consistente, no de conocimiento: el modelo ya sabe qué es un
criterio ambiguo; lo que se busca es que responda siempre con las mismas claves y
categorías. Todos los ejemplos son sintéticos (sistema de reservas de salas).

No llama a la API: solo construye y valida los ejemplos.
"""

import json
from collections import Counter

from google.genai import types

CLAVES_ESPERADAS = ["categoria", "accion_sugerida"]

# (criterio de aceptación, salida esperada)
EJEMPLOS_RAW = [
    # ambiguo: admite más de una interpretación
    (
        "La reserva debe confirmarse rápido.",
        {"categoria": "ambiguo", "accion_sugerida": "Definir qué significa «rápido» con un tiempo máximo."},
    ),
    (
        "El sistema permite reservar salas grandes.",
        {"categoria": "ambiguo", "accion_sugerida": "Definir la capacidad mínima que se considera «grande»."},
    ),
    (
        "Los usuarios frecuentes tienen ventajas al reservar.",
        {"categoria": "ambiguo", "accion_sugerida": "Indicar cuántas reservas son «frecuente» y cuál es la ventaja."},
    ),
    # no_medible: describe una cualidad que no se puede comprobar con un dato
    (
        "La pantalla de reserva debe ser intuitiva.",
        {"categoria": "no_medible", "accion_sugerida": "Convertirlo en un criterio comprobable, por ejemplo pasos para reservar."},
    ),
    (
        "El mensaje de error debe ser amigable.",
        {"categoria": "no_medible", "accion_sugerida": "Fijar el texto del mensaje o los elementos que debe incluir."},
    ),
    (
        "La búsqueda de salas debe sentirse fluida.",
        {"categoria": "no_medible", "accion_sugerida": "Definir un tiempo de respuesta máximo medible."},
    ),
    # sin_resultado_verificable: dice qué se hace, pero no qué debe observarse
    (
        "El usuario puede cancelar una reserva.",
        {"categoria": "sin_resultado_verificable", "accion_sugerida": "Indicar el estado final de la reserva y si se notifica al usuario."},
    ),
    (
        "El administrador puede cambiar el rol de un usuario.",
        {"categoria": "sin_resultado_verificable", "accion_sugerida": "Indicar qué permisos cambian y cómo se comprueba."},
    ),
    (
        "Al registrarse, el sistema valida el correo.",
        {"categoria": "sin_resultado_verificable", "accion_sugerida": "Indicar qué ocurre con un correo válido y con uno inválido."},
    ),
    # correcto: específico, medible y con un resultado observable
    (
        "Si la sala ya está reservada en ese horario, se muestra el mensaje «Sala no disponible» y no se crea la reserva.",
        {"categoria": "correcto", "accion_sugerida": "Sin cambios: derivar un caso válido, uno inválido y uno de borde."},
    ),
    (
        "Una reserva no puede durar más de 4 horas; con 4 horas se acepta y con 4 horas y 1 minuto se rechaza.",
        {"categoria": "correcto", "accion_sugerida": "Sin cambios: probar los valores frontera indicados."},
    ),
    (
        "Al cancelar una reserva con más de 24 horas de anticipación, el estado cambia a «cancelada» y no se aplica penalización.",
        {"categoria": "correcto", "accion_sugerida": "Sin cambios: cubrir también el caso con menos de 24 horas."},
    ),
]


def construir_ejemplos(ejemplos_raw):
    """Convierte los pares (texto, salida) en TuningExample del SDK."""
    return [
        types.TuningExample(text_input=texto, output=json.dumps(salida, ensure_ascii=False))
        for texto, salida in ejemplos_raw
    ]


def chequear_balance(ejemplos_raw, clave):
    """Cuenta los ejemplos por categoría y devuelve (conteo, razón max/min)."""
    conteo = Counter(salida[clave] for _, salida in ejemplos_raw)
    razon = max(conteo.values()) / min(conteo.values())
    return conteo, razon


def validar_dataset(examples, claves_esperadas):
    """Devuelve la lista de problemas encontrados; vacía si el dataset está bien."""
    problemas = []
    vistos = set()
    for i, ejemplo in enumerate(examples):
        entrada = (ejemplo.text_input or "").strip()
        salida = (ejemplo.output or "").strip()
        if not entrada:
            problemas.append(f"Ejemplo {i}: text_input vacío")
        if not salida:
            problemas.append(f"Ejemplo {i}: output vacío")
        if entrada in vistos:
            problemas.append(f"Ejemplo {i}: text_input duplicado")
        vistos.add(entrada)
        if not salida:
            continue
        try:
            datos = json.loads(salida)
        except json.JSONDecodeError:
            problemas.append(f"Ejemplo {i}: output no es JSON válido")
            continue
        if not isinstance(datos, dict):
            problemas.append(f"Ejemplo {i}: output no es un objeto JSON")
            continue
        faltantes = [c for c in claves_esperadas if c not in datos]
        if faltantes:
            problemas.append(f"Ejemplo {i}: faltan las claves {faltantes}")
    return problemas


if __name__ == "__main__":
    examples = construir_ejemplos(EJEMPLOS_RAW)
    conteo, razon = chequear_balance(EJEMPLOS_RAW, "categoria")
    print("Balance por categoría:", dict(conteo), f"(razón max/min: {razon:.1f}x)")
    problemas = validar_dataset(examples, CLAVES_ESPERADAS)
    for problema in problemas:
        print(" -", problema)
    print(f"{len(examples)} ejemplos, {len(problemas)} problemas")
