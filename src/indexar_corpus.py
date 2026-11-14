import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_CORPUS = RAIZ / "corpus" / "reservas"
PERSIST_DIR = RAIZ / "vectorstore"
COLLECTION_NAME = "reservas"
MODELO_EMBEDDINGS = "models/gemini-embedding-001"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TAMANO_LOTE = 50
EXTENSIONES = (".md", ".txt")


def crear_embeddings():
    """Valida la clave y devuelve el modelo de embeddings"""
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit(
            "Falta GEMINI_API_KEY. Definela en tu archivo '.env' y vuelve a ejecutar."
        )
    return GoogleGenerativeAIEmbeddings(model=MODELO_EMBEDDINGS)


def cargar_documentos(carpeta=CARPETA_CORPUS):
    """Lee los archivos del corpus y devuelve un Document por archivo."""
    documentos = []
    for ruta in sorted(carpeta.rglob("*")):
        if ruta.suffix.lower() not in EXTENSIONES:
            continue
        texto = ruta.read_text(encoding="utf-8")
        origen = ruta.relative_to(carpeta).as_posix()
        documentos.append(Document(page_content=texto, metadata={"fuente": origen}))
    return documentos

def dividir_documentos(documentos, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    """Divide los documentos en chunks conservando su metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_documents(documentos)


def generar_ids(chunks):
    """Genera ids estables con el formato '<origen>#<n>', contando por archivo."""
    contadores = {}
    ids = []
    for chunk in chunks:
        origen = chunk.metadata["fuente"]
        n = contadores.get(origen, 0)
        ids.append(f"{origen}#{n}")
        contadores[origen] = n + 1
    return ids

def abrir_vectorstore(embeddings, persist_directory=PERSIST_DIR):
    """Abre (o crea si no existe) la colección en disco. No gasta tokens."""
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(persist_directory),
    )


def indexar(vectorstore, chunks, ids, tamano_lote=TAMANO_LOTE):
    """Indexa los chunks por lotes con upsert. Devuelve cuántos se indexaron."""
    indexados = 0
    for inicio in range(0, len(chunks), tamano_lote):
        lote = chunks[inicio:inicio + tamano_lote]
        ids_lote = ids[inicio:inicio + tamano_lote]
        try:
            vectorstore.add_documents(documents=lote, ids=ids_lote)
        except Exception as error:
            mensaje = str(error)
            if "429" in mensaje or "RESOURCE_EXHAUSTED" in mensaje:
                print("Límite de peticiones alcanzado. Espera un minuto y vuelve a ejecutar.")
            else:
                print(f"Falló el lote que empieza en {inicio}: {type(error).__name__}")
            break
        indexados += len(lote)
    return indexados


def consultar(vectorstore, pregunta, k=3):
    """Busca los k chunks más parecidos a la pregunta. Gasta un embedding."""
    return vectorstore.similarity_search_with_score(pregunta, k=k)


def eliminar_por_origen(vectorstore, origen):
    """Borra todos los chunks de un archivo. Devuelve cuántos borró."""
    ids = vectorstore.get(where={"fuente": origen})["ids"]
    if ids:
        vectorstore.delete(ids=ids)
    return len(ids)


def main():
    documentos = cargar_documentos()
    if not documentos:
        raise SystemExit(f"No se encontraron documentos en {CARPETA_CORPUS}.")

    chunks = dividir_documentos(documentos)
    ids = generar_ids(chunks)
    print(f"{len(documentos)} documentos -> {len(chunks)} chunks")

    embeddings = crear_embeddings()
    vectorstore = abrir_vectorstore(embeddings)
    indexados = indexar(vectorstore, chunks, ids)

    print(f"Indexados {indexados} de {len(chunks)} chunks")
    print(f"Total en la colección: {len(vectorstore.get()['ids'])}")
    if indexados < len(chunks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()