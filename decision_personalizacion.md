# Decisión de personalización

Fecha: 2026-11-23. Todos los datos citados están en este repositorio y son sintéticos.

## 1. El problema

El copiloto de QA recibe una historia de usuario y devuelve su estructura, un diagnóstico de sus criterios de aceptación y casos de prueba. Cada caso debe apoyarse en una regla del sistema bajo prueba y citar de dónde sale: un resultado esperado inventado es justo el defecto que el copiloto debe evitar. Esas reglas viven en la documentación de ese sistema, que cambia con cada sprint y es distinta para cada producto: en esta versión, un servicio de reservas de salas descrito en 9 documentos (`corpus/reservas/`). Además, cada salida debe respetar siempre un formato JSON fijo, para que pueda validarse por código.

## 2. Resultado del método

Para decidir cómo adaptar el modelo al copiloto se compararon tres técnicas (RAG, PEFT y fine-tuning completo) con un método de puntaje de cinco preguntas. Cada respuesta afirmativa suma puntos a una o más técnicas:

| Pregunta | Si la respuesta es Sí |
|---|---|
| ¿La información cambia seguido? | RAG +3 |
| ¿Hay un problema de formato o tono? | PEFT +2, fine-tuning completo +1 |
| ¿Hay un dataset grande y de calidad? | Fine-tuning completo +2, PEFT +1 |
| ¿El presupuesto es limitado o hay que iterar rápido? | RAG +2, PEFT +1 |
| ¿Se necesitan varias variantes del modelo? | PEFT +2 |

Respuestas para el copiloto, cada una con el hecho que la sustenta:

| Pregunta | Respuesta | Hecho que la sustenta |
|---|---|---|
| ¿La información cambia seguido? (Sí si cambia al menos una vez al mes) | Sí | Es una premisa del producto, no una medición: el copiloto trabaja sobre la documentación del sistema bajo prueba, que cambia con cada sprint, y cada producto nuevo trae la suya. Si la respuesta fuera No, RAG seguiría ganando (ver la sensibilidad). |
| ¿Hay un problema de formato o tono? (Sí si falla al menos el 15 % de las respuestas, por ejemplo 3 de 20) | No | `prompts/registro_resultados.json`: los 3 pasos del copiloto (estructurar la HU, diagnosticarla y generar casos), con 3 corridas cada uno. 9 de 9 respuestas con las claves JSON esperadas y 0 fallos de formato. La muestra es de 9 respuestas, no de 20: con 9, el 15 % equivale a 2 fallos, y hubo 0. Mide el formato, no la calidad del contenido. |
| ¿Hay un dataset grande y de calidad? (Sí con 200 ejemplos o más, sin contradicciones en una muestra de 20) | No | `dataset_tuning.py` tiene 12 ejemplos etiquetados para clasificar criterios de aceptación, 3 por cada una de 4 categorías, con 0 problemas de validación. 12 < 200. |
| ¿El presupuesto es limitado o hay que iterar rápido? (Sí si no se pueden pagar más de 2 entrenamientos) | Sí | No hay presupuesto para entrenar: el proyecto no ha ejecutado ningún entrenamiento y opera en el nivel gratuito de Gemini, sin un plan de pago. Ese nivel limita incluso la inferencia: 15 peticiones por minuto, con el primer 429 en la petición 16 (ensayo de rate limit del README). |
| ¿Se necesitan varias variantes del modelo? (Sí con 2 o más) | No | Un idioma y un formato de caso. Cada producto aporta su propia documentación, pero eso cambia los datos que se consultan, no el comportamiento del modelo. |

Puntaje:

| Técnica | Puntos | Origen |
|---|---|---|
| RAG | **5** | Información que cambia seguido (+3) y presupuesto limitado (+2) |
| PEFT | 1 | Presupuesto limitado (+1) |
| Fine-tuning completo | 0 | — |

**No hubo empate:** RAG gana con 5 puntos contra 1 de PEFT.

Sensibilidad, cambiando una sola respuesta:

| Si cambia… | Puntaje resultante | Ganadora |
|---|---|---|
| Información cambia seguido: No | RAG 2, PEFT 1, fine-tuning 0 | RAG |
| Formato o tono: Sí | RAG 5, PEFT 3, fine-tuning 1 | RAG |
| Dataset grande: Sí | RAG 5, PEFT 2, fine-tuning 2 | RAG |
| Presupuesto limitado: No | RAG 3, PEFT 0, fine-tuning 0 | RAG |
| Varias variantes: Sí | RAG 5, PEFT 3, fine-tuning 0 | RAG |

Ningún cambio de una sola respuesta altera la ganadora: la decisión es estable. La respuesta menos firme es la primera, porque es una premisa del producto; aun si fuera No, RAG gana 2 a 1.

## 3. Técnica elegida y por qué

**RAG.** El puntaje lo respalda con claridad, y el tipo de problema apunta en la misma dirección:

- **Lo que falta es información con fuente, no comportamiento.** El copiloto debe conocer reglas concretas del sistema bajo prueba (por ejemplo, el límite de horas por reserva) y citar de dónde salen. Un modelo ajustado con tuning memoriza los hechos de forma imprecisa y no puede citarlos. RAG los recupera en cada consulta y devuelve el identificador del fragmento que los respalda.
- **La documentación cambia y depende del producto.** Con RAG, un cambio en la documentación o un producto nuevo se resuelve reindexando. Con tuning habría que reentrenar cada vez.
- **El formato ya se cumple sin tuning.** 9 de 9 respuestas salieron con las claves esperadas gracias al prompt de sistema, el esquema JSON y la validación por código. La tarea candidata a PEFT, clasificar criterios de aceptación, corresponde al paso de diagnóstico, que ya salió 3 de 3 en formato.
- **Faltan datos para entrenar.** Hay 12 ejemplos etiquetados contra 200 necesarios, y etiquetarlos es trabajo manual de QA.

Costos comparados:

| Costo | RAG (medido en este proyecto) | PEFT o fine-tuning |
|---|---|---|
| Datos | No hay que etiquetar: se indexan los 9 documentos existentes. | 188 ejemplos más, etiquetados a mano: ≈ 15,7 h a 5 minutos cada uno (el tiempo por ejemplo es un supuesto). |
| Infraestructura | Un índice Chroma persistente que hay que mantener al día con la documentación y respaldar. Se reconstruye con `src/indexar_corpus.py`. | No necesita una base adicional: el modelo ajustado se llama como cualquier otro. Entrenarlo exige un plan de pago. |
| Cómputo | Por consulta: 400 a 423 tokens de entrada con k=3 y 629 a 705 con k=6, más 16 a 65 de salida (`registros_latencia_costo.jsonl`, 3 preguntas). | Los tokens de cada intento de entrenamiento, más el costo por consulta del modelo ajustado. No se midió porque no hubo entrenamiento. |
| Tiempo | De 1,7 a 5,6 s por consulta. Reindexar tras un cambio cuesta un embedding por fragmento (tiempo no medido). | De minutos a horas por intento de entrenamiento (estimación general, no medida aquí). |

Se descartan:
- **Fine-tuning completo:** 0 puntos y exige el dataset más grande.
- **PEFT:** hoy no resuelve ningún problema medido. Se reconsideraría solo si se cumplen las condiciones de la sección 4, y como complemento de RAG, no como reemplazo.

## 4. Qué haría falta para ejecutarla

**Para mantener RAG** (ya está en funcionamiento):

| Necesidad | Número |
|---|---|
| Documentación a mantener indexada | 9 documentos en `corpus/reservas/`. Cada producto nuevo agrega los suyos. |
| Mejorar la recuperación en dos casos débiles | Recall promedio de 0.885 con k=3 y con k=5 (`resultados_evaluacion.txt`). Pagos tiene recall 0 y modificar una reserva, 0.5. La meta es 1.0 en ambos sin bajar el resto. |
| Consumo por consulta a vigilar | De 400 a 423 tokens de entrada con k=3 y de 629 a 705 con k=6 (`registros_latencia_costo.jsonl`, 3 preguntas). La recuperación se evaluó con k=3 y k=5; el consumo, con k=3 y k=6. |

**Para sumar PEFT como complemento**, haría falta que se cumplan estas condiciones:

| Condición | Hoy | Falta |
|---|---|---|
| 200 ejemplos etiquetados, sin contradicciones en una muestra de 20 | 12 | 188 ejemplos, ≈ 15,7 h a 5 minutos cada uno (el tiempo por ejemplo es un supuesto, no una medición) |
| Al menos 15 % de fallos de formato en una muestra de 20 respuestas | 0 de 9 | Una muestra de 20 respuestas |
| Presupuesto para pagar los entrenamientos | Nivel gratuito, 0 entrenamientos | Un plan de pago |
| Un adapter acorde a la tarea | — | La tarea es estrecha (4 categorías y 2 claves). Se empezaría con un adapter pequeño, como `ADAPTER_SIZE_FOUR`, porque uno grande entrenado con 200 ejemplos tiende a memorizar en vez de generalizar. El tamaño es un supuesto que confirmaría el primer entrenamiento. |

Escenarios que activarían esa reconsideración:
- Si se pasa a un modelo más barato y empieza a fallar el formato.
- Si distintos equipos piden formatos distintos de caso.
- Si se acumulan casos aprobados por personas de QA que sirvan como material de entrenamiento
