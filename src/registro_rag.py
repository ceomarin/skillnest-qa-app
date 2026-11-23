import json
import time
from contextlib import contextmanager
from datetime import UTC, datetime

from langchain_google_genai import ChatGoogleGenerativeAI

from evaluacion_recuperacion import CASOS_EVALUACION
from indexar_corpus import RAIZ, abrir_vectorstore, crear_embeddings
from recuperar_corpus import (
    ERRORES_PROVEEDOR,
    NOMBRE_MODELO,
    TIMEOUT_MODELO_SEGUNDOS,
    construir_prompt,
    describir_error,
)

ARCHIVO_REGISTROS = RAIZ / "registros_latencia_costo.jsonl"
# Índices en CASOS_EVALUACION (B27): una pregunta larga, una media y una corta.
INDICES_MUESTRA = (0, 6, 11)
VALORES_K = (3, 6)


@contextmanager
def medir(tiempos, etapa):
    """Guarda en `tiempos[etapa]` los segundos que tarda el bloque (perf_counter)."""
    inicio = time.perf_counter()
    yield
    tiempos[etapa] = time.perf_counter() - inicio


def registrar_consulta(vectorstore, llm, pregunta, k):
    """Corre una consulta RAG real y devuelve su registro: tiempo por etapa y tokens reales.

    `embed_y_busqueda` incluye armar el prompt, que es local y despreciable.
    `tokens` es None si el proveedor no devolvió `usage_metadata`.
    """
    tiempos = {}

    with medir(tiempos, "embed_y_busqueda"):
        prompt, _citas = construir_prompt(vectorstore, pregunta, k=k)

    with medir(tiempos, "generacion"):
        respuesta = llm.invoke(prompt)

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "pregunta": pregunta,
        "k": k,
        "tiempos_ms": {etapa: round(s * 1000, 2) for etapa, s in tiempos.items()},
        "tiempo_total_ms": round(sum(tiempos.values()) * 1000, 2),
        "tokens": dict(respuesta.usage_metadata) if respuesta.usage_metadata else None,
    }


def guardar_registro(registro, archivo=ARCHIVO_REGISTROS):
    """Agrega el registro como una línea JSON, sin borrar las anteriores."""
    with open(archivo, "a", encoding="utf-8") as salida:
        salida.write(json.dumps(registro, ensure_ascii=False) + "\n")


def resumir_registro(registro):
    """Una línea legible: k, tokens de entrada, tiempo total y el inicio de la pregunta."""
    tokens = registro["tokens"]
    tokens_entrada = tokens["input_tokens"] if tokens else None
    return (
        f"k={registro['k']}  input_tokens={tokens_entrada}  "
        f"total={registro['tiempo_total_ms']} ms  {registro['pregunta'][:35]}"
    )


def registrar_corrida(vectorstore, llm, indices, valores_k, archivo=ARCHIVO_REGISTROS):
    """Registra cada pregunta con cada k. Devuelve (registradas, fallidas).

    Un error del proveedor se informa y esa consulta no se guarda: cada línea es
    independiente, así que las demás siguen siendo válidas.
    """
    registradas = 0
    fallidas = 0
    for indice in indices:
        pregunta = CASOS_EVALUACION[indice]["pregunta"]
        for k in valores_k:
            try:
                registro = registrar_consulta(vectorstore, llm, pregunta, k)
            except ERRORES_PROVEEDOR as error:
                print(
                    f"Sin registrar (k={k}, {pregunta[:35]}): {describir_error(error)}"
                )
                fallidas += 1
                continue
            guardar_registro(registro, archivo)
            print(resumir_registro(registro))
            registradas += 1
    return registradas, fallidas


def main():
    vectorstore = abrir_vectorstore(crear_embeddings())
    total = vectorstore._collection.count()
    if total == 0:
        raise SystemExit(
            "El índice está vacío. Ejecuta antes: python src/indexar_corpus.py"
        )
    print(f"Chunks en el índice: {total}")

    llm = ChatGoogleGenerativeAI(model=NOMBRE_MODELO, timeout=TIMEOUT_MODELO_SEGUNDOS)
    registradas, fallidas = registrar_corrida(
        vectorstore, llm, INDICES_MUESTRA, VALORES_K
    )

    print(f"Registradas {registradas}, sin registrar {fallidas}")
    print(f"Registros en {ARCHIVO_REGISTROS.name}")
    if fallidas:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
