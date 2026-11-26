import logging
import os
import re
import uuid

from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.types import Command

from grafo_supervision import crear_app
from indexar_corpus import (
    abrir_vectorstore,
    cargar_documentos,
    crear_embeddings,
    dividir_documentos,
    generar_ids,
    indexar,
)
from logging_rag import (
    filtrar_documentos_sospechosos,
    huella,
    logger,
    registrar_consumo,
    trace_id_var,
)
from recuperar_corpus import (
    ERRORES_PROVEEDOR,
    NOMBRE_MODELO,
    PROMPT_TEMPLATE,
    TIMEOUT_MODELO_SEGUNDOS,
    K,
    describir_error,
    formatear_contexto,
)
from registro_prompts import NOMBRE_PROMPT, crear_registro

RESPUESTA_SIN_CONTEXTO = (
    "No tengo información suficiente y verificada para responder esto."
)

# Códigos estables del resultado: el llamador (hoy la terminal, mañana la API)
# decide qué hacer con cada uno sin interpretar texto.
RESPONDIDA = "respondida"
SIN_CONTEXTO = "sin_contexto"
MODELO_NO_DISPONIBLE = "modelo_no_disponible"
ERROR_PROVEEDOR = "error_proveedor"
ERROR_INDICE = "error_indice"

CITA = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


def _evento(nombre, nivel=logging.INFO, **campos):
    """Loguea un evento con sus campos. Solo longitudes, conteos, ids y huellas."""
    logger.log(
        nivel,
        nombre.replace("_", " "),
        extra={"extra_data": {"evento": nombre, **campos}},
    )


def version_prompt():
    """Huella del prompt en uso; avisa si no es la última versión registrada."""
    en_uso = huella(PROMPT_TEMPLATE)
    if en_uso != crear_registro().ultima(NOMBRE_PROMPT)["huella"]:
        _evento("prompt_sin_registrar", logging.WARNING, huella=en_uso)
    return en_uso


def asegurar_indice(vectorstore):
    """Indexa los chunks del corpus que aún no están en el índice.

    Devuelve cuántos indexó. Con el índice completo no gasta embeddings. Si no logra
    indexar todos los faltantes (por ejemplo, un rate limit), lanza RuntimeError
    para que no se consulte un índice a medias.
    """
    chunks = dividir_documentos(cargar_documentos())
    ids = generar_ids(chunks)
    existentes = set(vectorstore.get()["ids"])
    faltantes = [(c, i) for c, i in zip(chunks, ids) if i not in existentes]
    if not faltantes:
        _evento("indice_reutilizado", n_chunks=len(existentes))
        return 0
    nuevos = indexar(vectorstore, [c for c, _ in faltantes], [i for _, i in faltantes])
    _evento("indice_creado", n_nuevos=nuevos, n_faltantes=len(faltantes))
    if nuevos < len(faltantes):
        raise RuntimeError("indexación incompleta")
    return nuevos


def validar_citas(respuesta, citas):
    """Valida por código las citas `[n]` que propuso el modelo.

    Cada `[n]` que existe en `citas` pasa a `[id del chunk]`; las que el modelo
    inventó se quitan del texto. Devuelve (texto, fuentes ordenadas y únicas,
    cantidad de citas inventadas).
    """
    fuentes = set()
    inventadas = 0

    def traducir(coincidencia):
        nonlocal inventadas
        partes = []
        for numero in (int(n) for n in re.findall(r"\d+", coincidencia.group(1))):
            if numero in citas:
                fuentes.add(citas[numero])
                partes.append(f"[{citas[numero]}]")
            else:
                inventadas += 1
        return "".join(partes)

    texto = CITA.sub(traducir, respuesta)
    if inventadas:
        texto = re.sub(r" +([.,;:])", r"\1", texto)
    return texto, sorted(fuentes), inventadas


def _resultado(estado, respuesta, fuentes=None, version=None):
    resultado = {
        "respuesta": respuesta,
        "fuentes": fuentes or [],
        "estado": estado,
        "trace_id": trace_id_var.get(),
        "version_prompt": version,
    }
    _evento(
        "respuesta_entregada",
        estado=estado,
        respuesta_len=len(respuesta),
        n_fuentes=len(resultado["fuentes"]),
        version_prompt=version,
    )
    return resultado


def _responder(pregunta, vectorstore, llm, k):
    _evento("consulta_recibida", pregunta_len=len(pregunta))
    version = version_prompt()

    if (vectorstore is None or llm is None) and not os.environ.get("GEMINI_API_KEY"):
        _evento("modelo_no_disponible", logging.ERROR, motivo="falta_clave")
        return _resultado(
            MODELO_NO_DISPONIBLE,
            "El modelo no está disponible: falta configurar GEMINI_API_KEY.",
            version=version,
        )

    try:
        if vectorstore is None:
            vectorstore = abrir_vectorstore(crear_embeddings())
            asegurar_indice(vectorstore)
        if llm is None:
            llm = ChatGoogleGenerativeAI(
                model=NOMBRE_MODELO, timeout=TIMEOUT_MODELO_SEGUNDOS
            )
        documentos = vectorstore.as_retriever(search_kwargs={"k": k}).invoke(pregunta)
    except ERRORES_PROVEEDOR as error:
        _evento(
            "error_proveedor",
            logging.ERROR,
            etapa="recuperar",
            tipo=type(error).__name__,
        )
        return _resultado(ERROR_PROVEEDOR, describir_error(error), version=version)
    except Exception as error:  # noqa: BLE001 - índice ilegible: se informa, no se propaga
        _evento("error_indice", logging.ERROR, tipo=type(error).__name__)
        return _resultado(
            ERROR_INDICE,
            "No se pudo preparar el índice de documentos.",
            version=version,
        )
    _evento(
        "documentos_recuperados",
        n_recuperados=len(documentos),
        chunk_ids=[d.id for d in documentos],
    )

    limpios, descartados = filtrar_documentos_sospechosos(documentos)
    _evento("contexto_filtrado", n_limpios=len(limpios), n_descartados=len(descartados))
    if not limpios:
        _evento(
            "sin_contexto_confiable",
            logging.WARNING,
            n_recuperados=len(documentos),
            n_descartados=len(descartados),
        )
        return _resultado(SIN_CONTEXTO, RESPUESTA_SIN_CONTEXTO, version=version)

    contexto, citas = formatear_contexto(limpios)
    prompt = PROMPT_TEMPLATE.format(contexto=contexto, pregunta=pregunta)
    try:
        mensaje = llm.invoke(prompt)
    except ERRORES_PROVEEDOR as error:
        _evento(
            "error_proveedor", logging.ERROR, etapa="generar", tipo=type(error).__name__
        )
        return _resultado(ERROR_PROVEEDOR, describir_error(error), version=version)
    registrar_consumo(mensaje)

    texto, fuentes, inventadas = validar_citas(StrOutputParser().invoke(mensaje), citas)
    _evento("citas_validadas", n_validas=len(fuentes), n_inventadas=inventadas)
    if not fuentes:
        return _resultado(SIN_CONTEXTO, RESPUESTA_SIN_CONTEXTO, version=version)
    return _resultado(RESPONDIDA, texto, fuentes, version)


def responder(pregunta, vectorstore=None, llm=None, k=K):
    """Consulta el corpus y devuelve un dict con el resultado. No lanza errores del proveedor.

    Claves: `respuesta`, `fuentes`, `estado` (código estable), `trace_id` y
    `version_prompt` (huella del prompt usado). Sin `vectorstore` abre el índice
    persistido y lo completa si falta algo; sin `llm` crea el modelo real. Ambos
    se crean aquí dentro, nunca al importar el módulo.
    """
    token = trace_id_var.set("trace-" + uuid.uuid4().hex[:8])
    try:
        return _responder(pregunta, vectorstore, llm, k)
    finally:
        trace_id_var.reset(token)


def ejecutar_servicio(pregunta, vectorstore=None, llm=None):
    """Interfaz mínima del Gate: devuelve (respuesta, fuentes). `fuentes` vacía si no hay respaldo."""
    resultado = responder(pregunta, vectorstore=vectorstore, llm=llm)
    return resultado["respuesta"], resultado["fuentes"]


def crear_supervision(resultado=None):
    """Devuelve (app, entrada) para la aprobación humana de `grafo_supervision`.

    Con un `resultado` de `responder`, la entrada lleva sus fuentes y la huella de
    su prompt. Sin él, usa un caso de muestra con la huella del prompt en uso.
    """
    if resultado is None:
        entrada = {
            "casos": [
                {
                    "id": "TC-01",
                    "titulo": "Crear una reserva dentro del horario permitido",
                }
            ],
            "fuentes": ["crear-reserva.md#0"],
            "version_prompt": version_prompt(),
            "estado": "borrador",
        }
    else:
        entrada = {
            "casos": [{"id": resultado["trace_id"], "titulo": resultado["respuesta"]}],
            "fuentes": resultado["fuentes"],
            "version_prompt": resultado["version_prompt"],
            "estado": "borrador",
        }
    return crear_app(), entrada


def main():
    pregunta = "¿Qué pasa si cancelo una reserva dos horas antes de que empiece?"
    resultado = responder(pregunta)
    print(f"Estado: {resultado['estado']}")
    print(f"Respuesta: {resultado['respuesta']}")
    print(f"Fuentes: {resultado['fuentes']}")
    print(f"Prompt: {resultado['version_prompt']} · {resultado['trace_id']}")
    if resultado["estado"] != RESPONDIDA:
        raise SystemExit(1)

    app, entrada = crear_supervision(resultado)
    config = {"configurable": {"thread_id": resultado["trace_id"]}}
    pausa = app.invoke(entrada, config=config)
    print(f"Supervisión pausada: {'__interrupt__' in pausa}")
    final = app.invoke(Command(resume=True), config=config)
    print(f"Estado final: {final['estado']}")
    print("Proceso terminado sin errores.")


if __name__ == "__main__":
    main()
