# skillnest-qa-app

Miniaplicación en Python que consume la API de Gemini (`generateContent`) para estructurar y analizar historias de usuario con salida JSON validada. Es el proyecto del Módulo 1 de la *Especialización en Desarrollo con IA Generativa*. El Módulo 2 agrega un servicio RAG sobre un corpus sintético, con citas validadas por código, logs sin contenido sensible y supervisión humana (ver [Servicio RAG de punta a punta](#servicio-rag-de-punta-a-punta)).

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

## Servicio RAG de punta a punta

Responde preguntas sobre `corpus/reservas/`: 9 documentos sintéticos con las reglas de un sistema de reservas de salas. Cada respuesta cita los fragmentos que la respaldan. Si ninguna cita es válida, responde que no tiene información suficiente y no entrega fuentes.

Requiere la [instalación](#instalación) y la [configuración](#configuración) de arriba. Ejecuta todo desde la raíz del repositorio.

**1. Indexar el corpus** (consume 25 embeddings):

```bash
python src/indexar_corpus.py
```

```text
9 documentos -> 25 chunks
Indexados 25 de 25 chunks
Total en la colección: 25
```

El índice queda en `vectorstore/`, que no se versiona. Volver a ejecutarlo recalcula los 25 embeddings, pero no duplica chunks, porque cada uno tiene un id estable.

**2. Verificar el entorno** (no llama a la API):

```bash
python src/verificar_entorno.py
```

Revisa los paquetes, que `GEMINI_API_KEY` esté definida (sin imprimirla) y que exista el índice. Debe terminar con `Entorno listo para la corrida final`. Si falta algo, imprime `Pendiente: ...` y termina con código 1.

**3. Consultar** (1 embedding y 1 generación):

```bash
python src/servicio_rag.py
```

Hace una pregunta de ejemplo. Primero imprime los logs JSON, uno por etapa y todos con el mismo `trace_id`. Los logs solo llevan longitudes, ids, conteos y tokens; nunca la pregunta, los fragmentos ni la respuesta. Luego imprime el resultado y pasa la respuesta por la aprobación humana:

```text
Estado: respondida
Respuesta: ... [cancelacion-penalizaciones.md#0][glosario.md#2].
Fuentes: ['cancelacion-penalizaciones.md#0', 'glosario.md#2']
Prompt: <huella del prompt> · <trace_id>
Supervisión pausada: True
Estado final: aprobado
Proceso terminado sin errores.
```

Las fuentes pueden variar entre corridas. Si falta la clave, no hay red o el proveedor limita las peticiones, el servicio informa el estado y termina con código 1, sin un `Traceback`.

Para hacer otra pregunta, usa `ejecutar_servicio`, que devuelve `(respuesta, fuentes)`:

```bash
python -c "import sys; sys.path.insert(0, 'src'); from servicio_rag import ejecutar_servicio; print(ejecutar_servicio('Cuantas horas antes se puede cancelar sin penalizacion?'))"
```

## Pruebas

Necesitan las dependencias de desarrollo (`pip install -r requirements-dev.txt`).

```bash
pytest --ignore=test_gate2.py          # suite sin red: la API se sustituye por dobles
python -m pytest test_gate2.py -v      # 4 pruebas del Gate 2, contra la API real
```

`test_gate2.py` comprueba los cuatro criterios del Gate 2: el servicio responde sin excepciones, la respuesta cita su fuente, los logs no contienen la pregunta ni un correo de prueba, y la supervisión humana pausa y reanuda. Las tres primeras pruebas gastan 1 embedding y 1 generación cada una, y necesitan la clave y el índice. `pytest` sin argumentos también las ejecuta.

## Estructura

| Ruta | Contenido |
|---|---|
| `src/consumir_gemini.py` | Cliente de la API y flujo principal (Módulo 1) |
| `cliente.py` | Cliente con errores tipados, reintentos con backoff y costo acumulado |
| `prompts/banco.py` | Prompts, esquemas de salida y ejemplos sintéticos |
| `prompts/test_consistencia.py` | Prueba de consistencia contra la API real |
| `prompts/registro_resultados.json` | Último resultado de la prueba |
| `src/cadena_tres_pasos.py`, `src/enrutamiento.py`, `src/agente_con_herramientas.py` | Chain, enrutamiento y agente con LangChain |
| `corpus/reservas/` | Corpus sintético del servicio RAG |
| `src/indexar_corpus.py` | Chunking, embeddings e índice Chroma en `vectorstore/` |
| `src/recuperar_corpus.py` | Recuperación con contexto numerado y citas |
| `src/servicio_rag.py` | Servicio integrado: recupera, filtra la inyección, valida las citas y entrega la respuesta con sus fuentes |
| `src/logging_rag.py` | Logs JSON con `trace_id`, sin contenido sensible, y filtro de inyección |
| `src/registro_prompts.py` | Versiones del prompt con su huella |
| `src/grafo_supervision.py` | Aprobación humana con `interrupt()` y `Command` |
| `src/matriz_riesgos.py` | Matriz de riesgos del servicio |
| `src/verificar_entorno.py` | Revisión del entorno antes de la corrida |
| `test_gate2.py` | Pruebas del Gate 2, contra la API real |
| `test_*.py` (raíz), `src/test_*.py`, `tests/` | Pruebas automáticas sin red |
| `docs/` | Decisión de arquitectura, diagrama y evidencias |
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

## Registro del ensayo de instalación limpia del Gate 2

- Fecha: 2026-11-26
- Entorno: venv nuevo con Python 3.13.16, instalado solo con `pip install -r requirements-dev.txt` (que incluye `requirements.txt`)
- Resultado: la instalación terminó sin errores, `pytest --ignore=test_gate2.py` aprobó 62 pruebas, todos los módulos se importan y `python src/verificar_entorno.py` respondió `Entorno listo para la corrida final`
- Corrida real (entorno de desarrollo): `python src/servicio_rag.py` respondió con 2 fuentes citadas, y la supervisión pausó y aprobó; `python -m pytest test_gate2.py -v` aprobó las 4 pruebas

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


