# Límites de autonomía: copiloto de QA

Describe el agente tal como está implementado en
`src/agente_con_herramientas.py`, no un agente ideal. Último contraste
documento-código: 2026-11-09.

## Qué hace el agente y qué no

Ayuda a un analista a diseñar pruebas para **una** historia de usuario (HU).
Solo **sugiere**: devuelve texto. No escribe en ningún sistema, no envía nada
y no ejecuta pruebas. Quien decide qué hacer con la respuesta es el analista.

Topes de ejecución: 4 iteraciones (`MAX_ITERACIONES`), 60 segundos
(`MAX_SEGUNDOS`) por consulta y 20 segundos por llamada al modelo
(`TIMEOUT_MODELO_SEGUNDOS`, que convierte una llamada colgada en una
excepción). Si el proveedor falla, `consultar_agente` devuelve un mensaje de
error en lugar de tumbar el script.

**Memoria por sesión:** el agente recuerda los turnos anteriores de un mismo
`session_id` (`RunnableWithMessageHistory`), así que acepta seguimientos como
"¿y si el paso fuera 0.1?". Es la única información que persiste entre
consultas, y tiene tres límites:

- Vive en el proceso: se pierde al reiniciar.
- Crece con cada turno, y cada turno reenvía todo el historial al modelo
  (más tokens y más costo). `cerrar_sesion` libera una sesión.
- Cada sesión es independiente: dos `session_id` no comparten historial
  (cubierto por un test).

## Herramientas y nivel de riesgo

Escala: bajo (solo lectura o cálculo), medio (escritura reversible), alto
(escritura irreversible o con impacto económico).

- `calcular_valores_frontera`: **bajo**. Calcula con una función pura
  (`valores_frontera`); no lee ni escribe nada externo. Si falla, devuelve
  un texto de error. El peor caso es que el analista reciba valores de
  prueba mal elegidos, y lo ve antes de usarlos.
- `verificar_cita`: **bajo**. Compara un texto contra la HU, que queda fija
  en la herramienta; el modelo no puede cambiar contra qué se compara. El
  peor caso es un "sí/no" equivocado sobre lo que dice la HU.

No hay herramientas de riesgo medio ni alto.

## Herramientas que requieren aprobación humana

**Ninguna**, y es deliberado:

- Ninguna herramienta modifica nada ni tiene efectos fuera del proceso, así
  que no hay una acción irreversible que un humano deba confirmar antes.
- Pedir aprobación para acciones de riesgo bajo diluiría la atención de
  quien aprueba, que es justo lo que ese control debe evitar.

Verificación contra el código: `grep -n "esperar_aprobacion("
src/agente_con_herramientas.py` no devuelve coincidencias. El agente no tiene
ningún mecanismo de aprobación implementado.

**Condición para cambiar esto:** si se añade una herramienta que escriba
(por ejemplo, registrar un defecto en un gestor), se clasifica antes de
integrarla. Si es de riesgo alto, no se incorpora sin un paso de aprobación
con tiempo límite que, ante el timeout, resuelva en "no aprobado", y sin
registrar quién aprobó, qué argumentos y cuándo.

## Revisión de trazas

Cada interacción se guarda como una línea JSON en `logs/trazas_agente.jsonl`
con `registrar_traza`: entrada, herramientas usadas (argumentos y
observación) y respuesta final. Ese archivo se genera al ejecutar el agente
y no se versiona.

**Frecuencia:**

- Hoy, mientras el agente solo se ejecuta a mano: leer **todas** las trazas
  después de cada ejecución de prueba (son pocas).
- Cuando lo consuma un servicio, revisar cada semana una muestra pequeña, y
  siempre todas las trazas con error.

**Qué se busca**, según las reglas del prompt del sistema:

1. **La misma herramienta repetida** en una consulta: el agente no avanza o
   la observación es ambigua.
2. **Afirmaciones sobre la HU sin `verificar_cita`**: incumple la regla 2.
3. **Respuesta final que no coincide con la observación**: valores frontera
   distintos de los que devolvió `calcular_valores_frontera`, o una cita que
   la herramienta marcó con "No". Probablemente inventada.
4. **Herramientas usadas en una pregunta fuera de alcance**: incumple la
   regla 3.
5. **Respuestas con `No pude responder`**: fallos del proveedor. Un pico
   indica un problema de disponibilidad, no del agente.

Búsquedas rápidas (Git Bash):

```bash
wc -l logs/trazas_agente.jsonl
grep -c '"herramienta": "calcular_valores_frontera"' logs/trazas_agente.jsonl
grep -c '"herramienta": "verificar_cita"' logs/trazas_agente.jsonl
grep -c 'No pude responder' logs/trazas_agente.jsonl
```

En Windows CMD, `grep` no existe: usar `findstr /N /C:"texto" archivo`.

## Evidencia de una ejecución real (2026-11-09)

Dos ejecuciones del agente, con las 3 preguntas de `__main__`, dieron 6
trazas: 1 de `calcular_valores_frontera`, 2 de `verificar_cita`, 2 fuera de
alcance sin herramientas y 1 con error del proveedor.

- **Caso correcto:** la pregunta sobre el tope del 30 % con paso de 0.01
  llamó a `calcular_valores_frontera` con `limite_superior=30, paso=0.01` y
  la observación `Válidos: 29.99, 30.0. Inválidos: 30.01.` La respuesta final
  coincide con la observación.
- **Fuera de alcance:** "¿Qué es LangChain?" no usó herramientas y el agente
  respondió que está fuera de su alcance.
- **Error del proveedor:** en la primera ejecución Gemini respondió 503
  (alta demanda). El agente devolvió el mensaje de error y no se cayó.

Ejecución posterior, con memoria por sesión (4 preguntas en la sesión `demo`):

- **Seguimiento con memoria:** tras la pregunta del tope del 30 %, "¿Y si el
  paso fuera 0.1?" llamó a `calcular_valores_frontera` con
  `limite_superior=30, paso=0.1`. El `30` no estaba en la pregunta: lo tomó
  del turno anterior. Observación: `Válidos: 29.9, 30.0. Inválidos: 30.1.`

## Limitaciones conocidas

- **Una traza de error no dice qué herramienta se alcanzó a usar.** El 503
  ocurrió después de que el agente llamó a `calcular_valores_frontera`, pero
  la traza quedó con `acciones: []`, porque la excepción se pierde junto con
  los pasos intermedios. Se reconoce por el mensaje `No pude responder`, no
  por su contenido.
- **No hay detección automática de patrones.** La revisión es manual, con
  las búsquedas de arriba. No hay un script que marque repeticiones.
- **El historial no se persiste ni se recorta.** Si una conversación se
  alarga, el costo por turno sube sin límite. Además, un error de una
  respuesta anterior puede arrastrarse a las siguientes: por eso, al revisar
  una traza dudosa, se leen también los turnos previos de su `session_id`.
- **`__main__` usa un `session_id` fijo (`demo`)** para todas sus preguntas.
  Un servicio real tendría que generar un identificador por usuario.
- **`RunnableWithMessageHistory` está deprecado** en LangChain (sugiere la
  persistencia de LangGraph). Funciona y los tests lo cubren, pero muestra un
  aviso y habrá que migrarlo.
- **La traza no registra el contenido del modelo que no llegó a la
  respuesta.** Solo guarda herramientas, observaciones y respuesta final.

## Qué hacer ante un comportamiento inesperado

Aplica cuando una traza muestra alguno de los patrones de arriba, o cuando
el analista reporta una respuesta incorrecta.

1. **Contener:** si el problema viene de una herramienta, quitarla de la
   lista `herramientas` en `construir_agente`. Sin la herramienta, el agente
   deja de poder usarla; el resto sigue funcionando.
2. **Reproducir:** volver a ejecutar la `entrada` de la traza, con
   `verbose=True` para ver el razonamiento paso a paso. Si no es el primer
   turno de su sesión, reproducir también los turnos anteriores del mismo
   `session_id` en el mismo orden: sin ese contexto, el resultado puede ser
   distinto.
3. **Diagnosticar** en este orden, del cambio más barato al más caro:
   1. El docstring de la herramienta: es lo que el modelo lee para decidir
      cuándo usarla y con qué argumentos.
   2. `INSTRUCCIONES_SISTEMA`: la regla que se incumplió, ¿es ambigua?
   3. El código de la función pura (`valores_frontera`, `es_cita_literal`):
      si el error está en el cálculo, no se arregla con un prompt.
4. **Fijar el caso:** añadir un test que reproduzca la entrada (si el error
   está en una función pura) o una pregunta nueva en `__main__` (si es de
   comportamiento del modelo).
5. **Verificar:** volver a ejecutar el agente y comparar la traza nueva con
   la anterior. Si el patrón desapareció, volver a añadir la herramienta
   retirada.
