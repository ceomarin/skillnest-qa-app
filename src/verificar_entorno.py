import os
import sys
from importlib.metadata import PackageNotFoundError, version

PAQUETES = (
    "langchain-core",
    "langchain-chroma",
    "langchain-google-genai",
    "langgraph",
    "python-dotenv",
)


def main():
    pendientes = []
    for paquete in PAQUETES:
        try:
            print(f"{paquete}: {version(paquete)}")
        except PackageNotFoundError:
            print(f"{paquete}: no instalado")
            pendientes.append(paquete)
    if pendientes:
        # Sin los paquetes no se puede revisar lo demás.
        print("Pendiente: " + ", ".join(pendientes))
        sys.exit(1)

    from dotenv import load_dotenv

    from indexar_corpus import PERSIST_DIR

    load_dotenv()
    if os.environ.get("GEMINI_API_KEY"):
        print("GEMINI_API_KEY: definida")
    else:
        print("GEMINI_API_KEY: no definida")
        pendientes.append("GEMINI_API_KEY")

    if PERSIST_DIR.is_dir():
        print(f"Índice ({PERSIST_DIR.name}/): existe")
    else:
        print(f"Índice ({PERSIST_DIR.name}/): no existe")
        pendientes.append(f"carpeta del índice {PERSIST_DIR.name}/")

    if pendientes:
        print("Pendiente: " + ", ".join(pendientes))
        sys.exit(1)
    print("Entorno listo para la corrida final")


if __name__ == "__main__":
    main()
