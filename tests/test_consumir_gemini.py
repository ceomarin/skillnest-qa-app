
import os

from pydantic import json

from consumir_gemini import procesar_respuesta

PATH_UTL = os.getenv("TEST_PATH_URL")

with open(PATH_UTL, "r", encoding="utf-8") as archivo:
    respuesta = json.load(archivo)
procesar_respuesta(respuesta)