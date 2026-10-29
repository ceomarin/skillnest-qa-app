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

## Registro del ensayo de instalación limpia
 
- Fecha: 2026-10-23
- Resultado tras la corrección: el proyecto corre sin intervención manual

## Registro del ensayo de rate limit
 
- Fecha: 2026-10-27
- Modelo: `gemini-3.5-flash-lite` (nivel gratuito; límite del proyecto en AI Studio: 15 peticiones por minuto)
- Peticiones enviadas: 20
- Petición donde apareció el primer 429: la número 16 (`Respuesta 15`)
- Errores del proveedor: 11 respuestas 429 y ninguna 503 (confirmado en el panel de uso de AI Studio)
- Esperas observadas: 1.9s, 2.0s, 4.0s, 2.0s, 3.9s, 1.8s, 3.7s, 1.9s (backoff exponencial con jitter, correcto)
- Costo total del ensayo: $0.001570
- Resultado: 17 peticiones terminaron con éxito (2 de ellas tras reintentar) y 3 fallaron definitivamente tras 3 intentos (respuestas 16, 17 y 18)

## Registro de Pipeline_texto aplicado a salidas reales
 
- Fecha: 2026-10-28

```bash
-- Primera Ronda de consultas 
Operación: 5 tokens de entrada, 550 de salida, costo estimado: $0.001377 (acumulado: $0.001377)
[Caso 1] Coincidencia texto crudo: 85.7%
[Caso 1] Coincidencia texto procesado: 100.0%
Operación: 9 tokens de entrada, 456 de salida, costo estimado: $0.001143 (acumulado: $0.002519)
[Caso 2] Coincidencia texto crudo: 78.6%
[Caso 2] Coincidencia texto procesado: 78.6%
Operación: 8 tokens de entrada, 9 de salida, costo estimado: $0.000025 (acumulado: $0.002544)
[Caso 3] Coincidencia texto crudo: 83.3%
[Caso 3] Coincidencia texto procesado: 100.0%
(.venv) 
-- Segunda Ronda de consultas 
Operación: 9 tokens de entrada, 355 de salida, costo estimado: $0.000890 (acumulado: $0.000890)
[Caso 1] Coincidencia texto crudo: 64.3%
[Caso 1] Coincidencia texto procesado: 78.6%
Operación: 9 tokens de entrada, 663 de salida, costo estimado: $0.001660 (acumulado: $0.002550)
[Caso 2] Coincidencia texto crudo: 76.5%
[Caso 2] Coincidencia texto procesado: 82.4%
Operación: 8 tokens de entrada, 586 de salida, costo estimado: $0.001467 (acumulado: $0.004018)
[Caso 3] Coincidencia texto crudo: 75.0%
[Caso 3] Coincidencia texto procesado: 87.5%
(.venv) 
```


