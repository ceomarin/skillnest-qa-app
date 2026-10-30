"""Mide la consistencia de cada prompt del banco contra la API real.

Uso (desde la raíz del proyecto):
    .venv\\Scripts\\python prompts\\test_consistencia.py

Hace llamadas reales y consume cuota: no forma parte de la suite rápida.
"""

import json
import sys
import time
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
sys.path.insert(0, str(CARPETA))
sys.path.insert(0, str(CARPETA.parent))

from banco import BANCO_DE_PROMPTS
from cliente import consultar_modelo
from src.consumir_gemini import parsear_respuesta_json

INTENTOS = 3
PAUSA_SEGUNDOS = 2
ARCHIVO_REGISTRO = CARPETA / "registro_resultados.json"


def probar_prompt(prompt):
    """Ejecuta un prompt varias veces y cuenta los resultados."""
    resultado = {
        "exitos": 0,
        "intentos": INTENTOS,
        "fallos_formato": 0,
        "errores_proveedor": 0,
    }
    for intento in range(1, INTENTOS + 1):
        try:
            texto = consultar_modelo(
                prompt["ejemplo_usuario"],
                prompt["system_instruction"],
                prompt.get("response_schema"),
            )
            parsear_respuesta_json(texto, prompt["claves_esperadas"])
            resultado["exitos"] += 1
        except ValueError as error:
            resultado["fallos_formato"] += 1
            print(f"  intento {intento} falló (formato): {error}")
        except RuntimeError as error:
            resultado["errores_proveedor"] += 1
            print(f"  intento {intento} falló (proveedor): {error}")
        time.sleep(PAUSA_SEGUNDOS)
    return resultado


def main():
    registro = {}
    for prompt in BANCO_DE_PROMPTS:
        resultado = probar_prompt(prompt)
        print(
            f"{prompt['nombre']}: {resultado['exitos']}/{resultado['intentos']} respuestas válidas"
        )
        registro[prompt["nombre"]] = resultado

    ARCHIVO_REGISTRO.write_text(
        json.dumps(registro, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Registro guardado en {ARCHIVO_REGISTRO}")


if __name__ == "__main__":
    main()
