import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from langgraph.types import Command

# --- ADAPTA ESTA SECCION ---
from logging_rag import logger
from servicio_rag import crear_supervision, ejecutar_servicio

CORREO = "ana.perez@example.com"
PREGUNTA = (
    "¿Cancelar una reserva con menos de 24 horas suma puntos de penalización? "
    "Mi correo es " + CORREO
)
# --- FIN DE LA SECCION ---


def test_1_pipeline_sin_excepciones():
    respuesta, _ = ejecutar_servicio(PREGUNTA)

    assert respuesta, "la respuesta está vacía"


def test_2_respuesta_cita_fuente():
    respuesta, fuentes = ejecutar_servicio(PREGUNTA)

    assert fuentes, "la respuesta no trae fuentes"
    assert any(fuente in respuesta for fuente in fuentes), (
        "la respuesta no menciona su fuente"
    )


def test_3_logs_sin_contenido_crudo(caplog):
    # El logger del servicio no propaga al raíz: se le conecta el handler de caplog.
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.DEBUG, logger=logger.name):
            ejecutar_servicio(PREGUNTA)
    finally:
        logger.removeHandler(caplog.handler)

    # Se revisa el mensaje y también los campos de `extra`.
    registrado = caplog.text + "".join(str(vars(r)) for r in caplog.records)
    assert caplog.records, "no se capturó ningún log del servicio"
    assert CORREO not in registrado, "un dato sensible aparece en los logs"
    assert PREGUNTA not in registrado, "la pregunta completa aparece en los logs"


def test_4_supervision_pausa_y_reanuda():
    app, entrada = crear_supervision()
    config = {"configurable": {"thread_id": "gate2"}}

    primera = app.invoke(entrada, config=config)
    assert "__interrupt__" in primera

    final = app.invoke(Command(resume=True), config=config)
    assert "__interrupt__" not in final
    assert final["aprobado"] is True
