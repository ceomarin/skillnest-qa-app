# Revisión manual de la métrica F1

Registro de cada ronda de revisión manual hecha con la [rúbrica](rubrica.md).
Las rondas nuevas se agregan arriba; las anteriores no se borran.

---

## Ronda 1 — 2026-10-30

- **Fuente:** `resultados_metricas.json` (20 respuestas de `gemini-3.5-flash-lite`).
- **Referencias:** lista `CASOS` en `precision.py`.
- **Muestra:** 10 casos, los 5 con menor F1 y los 5 con mayor F1 (`resultados_para_revisar.txt`).
- **Rúbrica:** las tres preguntas de [rubrica.md](rubrica.md), una por columna.

### Resultados por caso

| F1 | Consulta | Corrección factual | Completitud | Contradicción | Qué pasó |
|---|---|---|---|---|---|
| 0.20 | ¿Se pueden probar todas las combinaciones de entrada? | Sí | Parcial | No | Respuesta correcta pero mas palabras contra 17 de la referencia; omite "priorización por riesgo". El largo hunde la precisión (0.13). |
| 0.26 | ¿Qué es una historia de usuario? | Sí | Parcial | No | Dice "perspectiva del usuario" y "valor" en lugar de "rol" y "beneficio": sinónimos. No menciona el objetivo de forma explícita. |
| 0.29 | ¿Qué es la partición de equivalencia? | Sí | Parcial | No | "divide en clases" en lugar de "agrupa en grupos". Omite que se prueba un valor de cada grupo, pero F1 no distingue esa omisión de la paráfrasis. |
| 0.35 | ¿Qué es la prueba de regresión? | Sí | Sí | No | Paráfrasis pura: "afectado negativamente el funcionamiento existente" en lugar de "roto lo que ya funcionaba". |
| 0.37 | ¿Qué es la Definition of Done? | Sí | Sí | No | Usa la redacción de Scrum ("criterios de calidad", "incremento") en lugar de la de ISTQB ("criterios de salida", "actividad"). |
| 0.69 | ¿Cuáles son los niveles de prueba del ISTQB? | **No** | **Parcial** | **Sí** | Dice "cuatro" niveles; la referencia lista cinco. Omite "integración de sistemas". Es la única respuesta incorrecta de la muestra y quedó entre las 5 mejores. |
| 0.71 | ¿Cuántos principios del testing define el ISTQB? | Sí | Sí | No | Escribe "siete" y la referencia "7": el token del dato no coincide. Con "ocho" el F1 sería el mismo (0.71). |
| 0.75 | ¿Qué código HTTP indica que se superó el límite de solicitudes? | Sí | Sí | No | Correcta (429). Con un código falso (430) el F1 sería 0.69. |
| 0.76 | ¿Qué código HTTP indica una credencial inválida? | Sí | Sí | No | Correcta (401). Con un código falso (403) el F1 sería 0.67, más que cualquier definición correcta de la muestra. |
| 0.84 | ¿El testing puede demostrar que un sistema no tiene defectos? | Sí | Sí | No | Correcta. Si se quita el segundo "no" (la respuesta pasa a afirmar lo contrario), el F1 solo baja a 0.80. |

Los F1 hipotéticos (430, 403, "ocho", sin "no") se calcularon con `calcular_metricas` sobre la misma referencia, cambiando solo esa palabra.

### Hallazgos

1. **Los 5 casos con F1 más bajo son correctos.** Ninguno tiene errores factuales ni contradicciones. Su F1 bajo se explica por sinónimos, paráfrasis y respuestas más largas que la referencia.
2. **El único error real está en el grupo de F1 alto.** "Niveles de prueba" (0.69) tiene un dato equivocado, omite un elemento y contradice la referencia.
3. **Un número escrito en letras no coincide con el dígito.** "siete" frente a "7" no cuenta como coincidencia, así que la métrica no ve el dato que responde la pregunta.
4. **Cambiar el dato clave casi no mueve el puntaje.** En respuestas de una oración, un código HTTP falso baja el F1 menos de 0.10.
5. **Una negación eliminada casi no mueve el puntaje.** Bajó 0.04 en un caso donde invierte el sentido de la respuesta.
6. **Las listas incompletas puntúan alto.** Si la respuesta repite la mayoría de los elementos de la referencia, omitir uno o fusionar dos apenas baja la cobertura.

### Observación fuera de la muestra

Al leer el resto de las respuestas apareció un error que la muestra no incluía.

**Pregunta:** "¿Cuántos valores se prueban por borde en el 3-value BVA?" (F1 = 0.43)

- **Correcto:** en cada límite se prueban 3 valores: el límite y los dos valores pegados a él. En un rango de 1 a 100, para el límite 1 se prueban 0, 1 y 2.
- **Lo que respondió el modelo:** el mínimo, un valor del medio y el máximo del rango (por ejemplo, 1, 50 y 100). El número de valores (3) coincide, pero la técnica descrita es otra.

**Por qué importa:** la muestra solo tomó los 5 F1 más bajos y los 5 más altos. Esta respuesta tiene un F1 intermedio, así que quedó fuera aunque está mal. Las próximas revisiones deberían incluir también algunos casos del medio.
