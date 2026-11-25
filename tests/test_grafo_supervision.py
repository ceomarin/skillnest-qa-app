import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "src"))

from langgraph.types import Command

from grafo_supervision import crear_app

ENTRADA = {
    "casos": [
        {"id": "TC-01", "titulo": "Crear una reserva dentro del horario permitido"}
    ],
    "fuentes": ["crear-reserva.md#0"],
    "version_prompt": None,
    "estado": "borrador",
}


def _pausar(thread_id):
    app = crear_app()
    config = {"configurable": {"thread_id": thread_id}}
    resultado = app.invoke(ENTRADA, config=config)
    assert "__interrupt__" in resultado
    assert app.get_state(config).values["estado"] == "borrador"
    return app, config


def test_pausa_y_reanuda_con_aprobacion():
    app, config = _pausar("aprobar-1")

    final = app.invoke(Command(resume={"aprobado": True}), config=config)

    assert final["estado"] == "aprobado"
    assert not app.get_state(config).next


def test_pausa_y_reanuda_con_rechazo_que_queda_guardado_con_su_motivo():
    app, config = _pausar("rechazar-1")

    app.invoke(
        Command(resume={"aprobado": False, "motivo": "dato_inventado"}), config=config
    )

    guardado = app.get_state(config).values
    assert guardado["estado"] == "rechazado"
    assert guardado["motivo"] == "dato_inventado"
    assert guardado["casos"] == ENTRADA["casos"]


def test_rechazo_con_false_se_guarda_como_otro_con_comentario():
    app, config = _pausar("rechazar-false-1")

    final = app.invoke(Command(resume=False), config=config)

    assert "__interrupt__" not in final
    guardado = app.get_state(config).values
    assert guardado["estado"] == "rechazado"
    assert guardado["motivo"] == "otro"
    assert guardado["comentario"]


def test_otro_sin_comentario_se_rechaza():
    app, config = _pausar("otro-1")

    resultado = app.invoke(
        Command(resume={"aprobado": False, "motivo": "otro"}), config=config
    )

    assert "__interrupt__" in resultado
    assert "comentario" in resultado["__interrupt__"][0].value["error"]
    assert app.get_state(config).values["estado"] == "borrador"
