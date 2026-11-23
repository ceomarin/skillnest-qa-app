from datetime import date

from indexar_corpus import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    RAIZ,
    abrir_vectorstore,
    crear_embeddings,
)
from recuperar_corpus import ERRORES_PROVEEDOR, describir_error

K = 3  # cuántos chunks recupera el retriever y cuántos evalúan las métricas
ARCHIVO_RESULTADOS = RAIZ / "resultados_evaluacion.txt"

# Etiquetado a mano leyendo corpus/reservas/, antes de ejecutar el retriever.
# Criterio: un chunk es relevante si por sí solo alcanza para responder.
# Un set vacío indica una pregunta sin respuesta en el corpus.
CASOS_EVALUACION = [
    {
        "pregunta": "¿Cuántos puntos de penalización suma cancelar una reserva "
        "3 horas antes de que empiece?",
        "ids_relevantes": {"cancelacion-penalizaciones.md#0"},
    },
    {
        "pregunta": "Si suspenden a un usuario, ¿qué pasa con las reservas que ya tenía?",
        "ids_relevantes": {"cancelacion-penalizaciones.md#1"},
    },
    {
        "pregunta": "¿Qué se considera una reserva activa?",
        "ids_relevantes": {"glosario.md#1", "limites-cuotas.md#0"},
    },
    {
        "pregunta": "¿Un estudiante puede reservar el Auditorio?",
        "ids_relevantes": {"roles-permisos.md#1"},
    },
    {
        "pregunta": "¿Con cuántos días de anticipación puede reservar un docente?",
        "ids_relevantes": {"roles-permisos.md#2"},
    },
    {
        "pregunta": "¿Puedo reservar una sala justo a la hora en que termina "
        "la reserva de otra persona?",
        "ids_relevantes": {"crear-reserva.md#1"},
    },
    {
        "pregunta": "¿Cuántas horas a la semana puede reservar un estudiante?",
        "ids_relevantes": {"limites-cuotas.md#1"},
    },
    {
        "pregunta": "¿Hasta cuántos minutos después del inicio puedo hacer check-in?",
        "ids_relevantes": {"ciclo-vida-reserva.md#2", "glosario.md#1"},
    },
    {
        "pregunta": "¿Puedo cambiar el horario de una reserva que empieza dentro de 10 horas?",
        "ids_relevantes": {"ciclo-vida-reserva.md#3", "errores-mensajes.md#4"},
    },
    {
        "pregunta": "¿Cuántos intentos fallidos de inicio de sesión bloquean la cuenta?",
        "ids_relevantes": {"registro-cuenta.md#1"},
    },
    {
        "pregunta": "¿Qué mensaje aparece si la sala ya está ocupada en ese horario?",
        "ids_relevantes": {"errores-mensajes.md#2"},
    },
    {
        "pregunta": "¿Cuántas personas caben en la Sala Mediana?",
        "ids_relevantes": {"producto.md#0"},
    },
    {
        "pregunta": "¿Se puede pagar una reserva con tarjeta de crédito?",
        "ids_relevantes": {"producto.md#1"},
    },
    {
        "pregunta": "¿El sistema envía un recordatorio por correo antes de la reserva?",
        "ids_relevantes": set(),
    },
    {
        "pregunta": "¿Se pueden hacer reservas los días festivos?",
        "ids_relevantes": set(),
    },
]


def precision_at_k(ids_recuperados, ids_relevantes):
    """Fracción de los ids recuperados que son relevantes (0.0 si no hay ninguno)."""
    if not ids_recuperados:
        return 0.0
    acertados = [i for i in ids_recuperados if i in ids_relevantes]
    return len(acertados) / len(ids_recuperados)


def recall_at_k(ids_recuperados, ids_relevantes):
    """Fracción de los ids relevantes que se recuperaron (None si el caso no tiene ninguno)."""
    if not ids_relevantes:
        return None
    acertados = [i for i in ids_recuperados if i in ids_relevantes]
    return len(acertados) / len(ids_relevantes)


def promediar(valores):
    """Promedio que ignora los None y evita dividir por cero."""
    validos = [v for v in valores if v is not None]
    return sum(validos) / len(validos) if validos else 0.0


def evaluar_recuperacion(retriever, casos, k=K):
    """Corre cada caso contra el retriever real y promedia precision y recall."""
    resultados = []
    for caso in casos:
        chunks = retriever.invoke(caso["pregunta"])
        ids_recuperados = [c.id for c in chunks][:k]
        p = precision_at_k(ids_recuperados, caso["ids_relevantes"])
        r = recall_at_k(ids_recuperados, caso["ids_relevantes"])
        resultados.append({"pregunta": caso["pregunta"], "precision": p, "recall": r})

    precision_promedio = promediar(x["precision"] for x in resultados)
    recall_promedio = promediar(x["recall"] for x in resultados)
    return resultados, precision_promedio, recall_promedio


def formatear_reporte(resultados, precision_promedio, recall_promedio):
    """Una línea por pregunta (precision, recall, pregunta) y la línea de promedios."""
    lineas = []
    for r in resultados:
        recall_txt = "n/a" if r["recall"] is None else f"{r['recall']:.2f}"
        lineas.append(f"{r['precision']:.2f}  {recall_txt}  {r['pregunta']}")
    lineas.append("")
    lineas.append(
        f"promedio -> precision: {precision_promedio:.3f}  recall: {recall_promedio:.3f}"
    )
    return "\n".join(lineas)


def guardar_resultados(reporte, archivo=ARCHIVO_RESULTADOS):
    """Agrega la corrida al final del registro, sin borrar las anteriores."""
    with open(archivo, "a", encoding="utf-8") as salida:
        salida.write(f"Fecha: {date.today()}\n")
        salida.write(
            f"Configuracion: k={K}, chunk_size={CHUNK_SIZE}, chunk_overlap={CHUNK_OVERLAP}\n\n"
        )
        salida.write(f"{reporte}\n\n")


def main():
    vectorstore = abrir_vectorstore(crear_embeddings())
    total = vectorstore._collection.count()
    if total == 0:
        raise SystemExit(
            "El índice está vacío. Ejecuta antes: python src/indexar_corpus.py"
        )
    print(f"Chunks en el índice: {total}")

    retriever = vectorstore.as_retriever(search_kwargs={"k": K})
    try:
        resultados, precision_promedio, recall_promedio = evaluar_recuperacion(
            retriever, CASOS_EVALUACION, k=K
        )
    except ERRORES_PROVEEDOR as error:
        # Una corrida incompleta daría promedios engañosos: no se guarda nada.
        raise SystemExit(describir_error(error)) from error

    reporte = formatear_reporte(resultados, precision_promedio, recall_promedio)
    print(reporte)
    guardar_resultados(reporte)
    print(f"Resultados guardados en {ARCHIVO_RESULTADOS.name}")


if __name__ == "__main__":
    main()
