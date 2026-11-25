"""Matriz de riesgos del copiloto de QA: probabilidad × impacto, mitigación y supervisión.

Probabilidad e impacto van de 1 a 5 y se puntúan con la información de hoy. Los
cortes de categoría (15, 9 y 4) se fijan de antemano. Todo riesgo ALTO o CRÍTICO
nombra su punto de supervisión humana. No consume API.
"""

SUPERVISION_CASOS = (
    "aprobación humana de los casos generados (src/grafo_supervision.py): "
    "nada se da por bueno sin aprobación y el rechazo se conserva con su motivo"
)

mis_riesgos = [
    {
        "riesgo": "Un caso de prueba con un resultado esperado inventado se aprueba "
        "y produce una prueba que pasa sin probar nada",
        "probabilidad": 3,
        "impacto": 5,
        "mitigacion": "El prompt exige responder solo con el contexto recuperado y "
        "admitir cuando no alcanza (src/recuperar_corpus.py, Bloque 26)",
        "supervision": SUPERVISION_CASOS + " (motivo dato_inventado)",
    },
    {
        "riesgo": "La respuesta cita un fragmento que no respalda la afirmación; "
        "ya ocurrió: sin respuesta, el modelo citaba todos los fragmentos recuperados",
        "probabilidad": 4,
        "impacto": 4,
        "mitigacion": "resolver_citas marca las citas que no corresponden a un "
        "fragmento recuperado (src/recuperar_corpus.py, Bloque 26)",
        "supervision": SUPERVISION_CASOS + " (motivo cita_incorrecta)",
    },
    {
        "riesgo": "Un fragmento del corpus con instrucciones ocultas cambia el "
        "comportamiento del modelo (inyección de prompt indirecta)",
        "probabilidad": 2,
        "impacto": 4,
        "mitigacion": "filtrar_documentos_sospechosos descarta el fragmento antes "
        "del prompt y el contexto va delimitado como datos (src/logging_rag.py, "
        "Bloque 31)",
        "supervision": None,
    },
    {
        "riesgo": "Una pregunta que el corpus sí cubre se responde como sin "
        "información porque el fragmento correcto no se recupera (caso de pagos)",
        "probabilidad": 3,
        "impacto": 2,
        "mitigacion": "Precisión y recall medidos con 15 preguntas etiquetadas "
        "(src/evaluacion_recuperacion.py, Bloque 27)",
        "supervision": None,
    },
    {
        "riesgo": "Un cambio del prompt degrada las respuestas sin que nadie lo note",
        "probabilidad": 3,
        "impacto": 3,
        "mitigacion": "Registro de versiones con huella y diff, y la huella del "
        "prompt se muestra al aprobar los casos (src/registro_prompts.py, Bloque 32)",
        "supervision": SUPERVISION_CASOS + " (el aprobador ve la huella del prompt)",
    },
    {
        "riesgo": "El límite de peticiones del nivel gratuito corta una consulta "
        "(429 observado en el ensayo de rate limit)",
        "probabilidad": 3,
        "impacto": 2,
        "mitigacion": "Reintentos con backoff y jitter (cliente.py, Bloque 13) y "
        "mensaje legible sin tumbar la ejecución (src/recuperar_corpus.py)",
        "supervision": None,
    },
]


def puntaje_riesgo(probabilidad, impacto):
    return probabilidad * impacto


def categoria_riesgo(puntaje):
    if puntaje >= 15:
        return "CRITICO"
    if puntaje >= 9:
        return "ALTO"
    if puntaje >= 4:
        return "MEDIO"
    return "BAJO"


def esta_en_el_limite(probabilidad, impacto):
    """True si cambiar en 1 la probabilidad o el impacto cambia la categoría."""
    actual = categoria_riesgo(puntaje_riesgo(probabilidad, impacto))
    vecinos = [
        (probabilidad - 1, impacto),
        (probabilidad + 1, impacto),
        (probabilidad, impacto - 1),
        (probabilidad, impacto + 1),
    ]
    return any(
        categoria_riesgo(puntaje_riesgo(p, i)) != actual
        for p, i in vecinos
        if 1 <= p <= 5 and 1 <= i <= 5
    )


def evaluar(riesgos):
    """Agrega puntaje, categoría y si está al límite; ordena de mayor a menor."""
    evaluados = []
    for r in riesgos:
        puntaje = puntaje_riesgo(r["probabilidad"], r["impacto"])
        evaluados.append(
            {
                **r,
                "puntaje": puntaje,
                "categoria": categoria_riesgo(puntaje),
                "al_limite": esta_en_el_limite(r["probabilidad"], r["impacto"]),
            }
        )
    return sorted(evaluados, key=lambda r: r["puntaje"], reverse=True)


def main():
    evaluados = evaluar(mis_riesgos)
    for r in evaluados:
        marca = " [AL LIMITE]" if r["al_limite"] else ""
        print(f"{r['categoria']} ({r['puntaje']}) - {r['riesgo']}{marca}")
        print(f"    mitigación: {r['mitigacion']}")
        if r["supervision"]:
            print(f"    supervisión: {r['supervision']}")

    print()
    for r in evaluados:
        if r["al_limite"]:
            print(f"revisar con otra persona: {r['riesgo']}")

    graves = [r for r in evaluados if r["categoria"] in ("ALTO", "CRITICO")]
    assert len(evaluados) >= 5, "la matriz necesita al menos 5 riesgos"
    assert graves, "sin ALTO ni CRÍTICO, probablemente se subestima algún riesgo"
    assert all(r["supervision"] for r in graves), (
        "todo riesgo ALTO o CRÍTICO necesita un punto de supervisión"
    )
    assert sum("Bloque" in r["mitigacion"] for r in evaluados) >= 2
    assert esta_en_el_limite(1, 1) is False, "el riesgo 1×1 no está al límite"
    print("\nverificaciones superadas")


if __name__ == "__main__":
    main()
