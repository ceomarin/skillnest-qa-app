# skillnest-qa-app

Miniaplicación en Python que consume la API de Gemini (`generateContent`) para estructurar y analizar historias de usuario con salida JSON validada. Es el proyecto del Módulo 1 de la *Especialización en Desarrollo con IA Generativa*.

## Qué hace

- Valida la entrada, arma la petición y la envía a Gemini por REST con `requests`.
- Maneja errores de red, timeouts y errores HTTP (401, 403, 429 y otros) con mensajes accionables, sin exponer la clave.
- Extrae el texto de la respuesta, lo parsea como JSON y valida las claves esperadas.
- Calcula la latencia y el costo de cada consulta a partir de `usageMetadata`.
- Incluye un banco de prompts (`estructurar_hu`, `diagnosticar_hu`, `generar_casos`) con su esquema de salida y una prueba de consistencia.

El modelo elegido es `gemini-3.5-flash-lite`. La comparación de candidatos y la justificación están en [docs/decision-arquitectura.md](docs/decision-arquitectura.md).

## Requisitos

- Python 3.13
- Una llave de API de Gemini

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (en Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
```

Para desarrollo (`ruff`, `mypy`, `pytest`): `pip install -r requirements-dev.txt`.

## Configuración

Copia `.env.example` a `.env` y reemplaza el valor ficticio por tu llave real:

```bash
copy .env.example .env            # Windows (en Linux/macOS: cp .env.example .env)
```

| Variable | Para qué sirve |
|---|---|
| `GEMINI_API_KEY` | Llave de API de Gemini. Se envía en el header `x-goog-api-key` |

El archivo `.env` está en `.gitignore` y nunca se sube al repositorio.

## Uso

```bash
python src/consumir_gemini.py
```

Hace **una llamada real** a la API. Si todo sale bien, imprime la latencia, el costo y el resultado:

```text
Latencia: 2.062698 segundos
Coste de la peticion: $0.000046 USD
{'categoria': 'tecnologia', 'nivel': 1}
```

Si algo falla (clave ausente o inválida, sin red, límite de peticiones), muestra un mensaje y termina con código 1.

### Banco de prompts

```bash
python prompts/test_consistencia.py
```

Ejecuta cada prompt del banco 3 veces contra la API real (9 llamadas, consumen cuota) y guarda el resultado en `prompts/registro_resultados.json`. Mide que la salida sea JSON con las claves esperadas; **no evalúa la calidad del contenido**.

## Estructura

| Ruta | Contenido |
|---|---|
| `src/consumir_gemini.py` | Cliente de la API y flujo principal |
| `prompts/banco.py` | Prompts, esquemas de salida y ejemplos sintéticos |
| `prompts/test_consistencia.py` | Prueba de consistencia contra la API real |
| `prompts/registro_resultados.json` | Último resultado de la prueba |
| `docs/` | Decisión de arquitectura, diagrama y evidencias |
| `tests/` | Reservado para pruebas automáticas |
| `requirements.txt` | Dependencias de ejecución, con versiones fijadas |
| `requirements-dev.txt` | Dependencias de desarrollo |

## Seguridad

- Ningún secreto va en el código ni en archivos versionados.
- Los ejemplos y datos de prueba son sintéticos: el repositorio es público.

## Convenciones

- Commits con [Conventional Commits](https://www.conventionalcommits.org/): `tipo(alcance): descripción`, por ejemplo `docs: add architecture diagram`.
- Un commit por cambio lógico.
