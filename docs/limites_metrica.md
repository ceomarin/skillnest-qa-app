# Límites de la métrica de evaluación

## Qué mide

Coincidencia de palabras entre una respuesta generada y una referencia,
después de pasar ambas a minúsculas y quitar la puntuación, contando
repeticiones (precisión, cobertura y F1 en `precision.py`).

## Modos de falla conocidos

Ejemplos reales y su detalle en [revision_manual.md](revision_manual.md).

- **Sinónimos y paráfrasis correctas puntúan bajo.** "Prueba de regresión":
  respuesta correcta y completa con F1 = 0.35.
- **Datos incorrectos puntúan alto.** "Niveles de prueba del ISTQB": dice
  "cuatro" en lugar de cinco y omite un nivel, con F1 = 0.69. Un código
  HTTP falso (403 en lugar de 401) sigue en 0.67.
- **Negaciones ausentes casi no bajan el puntaje.** Quitar el "no" de "no
  puede demostrar su ausencia" invierte el sentido y el F1 baja de 0.84 a 0.80.
- **Números en letras frente a dígitos.** "siete" no coincide con "7": con
  "siete" u "ocho" el F1 es el mismo (0.71).
- **Respuestas largas se penalizan aunque sean correctas.** "Combinaciones
  de entrada": 53 palabras correctas contra 17 de referencia, F1 = 0.20.
- **Listas incompletas puntúan alto.** Omitir o fusionar un elemento de una
  lista apenas baja la cobertura.

## Muestra revisada

- **2026-10-30:** 10 de 20 respuestas, los 5 con menor F1 y los 5 con mayor F1.
  Los 5 más bajos eran correctos y el único error estaba entre los 5 más altos.
  Fuera de la muestra se encontró otra respuesta incorrecta con F1 medio (0.43),
  así que revisar solo los F1 más bajos y más altos no basta.

## Recomendación de uso

Usar F1 solo para comparar tendencias en volumen entre versiones del cliente,
nunca para aprobar una respuesta individual. Revisar siempre a mano cualquier
respuesta con cifras, códigos, listas, negaciones o nombres propios.
