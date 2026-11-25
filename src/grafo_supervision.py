from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

MOTIVOS_RECHAZO = (
    "cita_incorrecta",
    "dato_inventado",
    "resultado_incorrecto",
    "fuera_de_criterio",
    "duplicado",
    "no_ejecutable",
    "otro",
)


class EstadoSupervision(TypedDict, total=False):
    casos: list[dict]
    fuentes: list[str]
    version_prompt: str | None
    estado: str  # borrador | aprobado | rechazado
    aprobado: bool
    motivo: str | None
    comentario: str | None


def validar_decision(decision) -> dict:
    """Devuelve la decisión normalizada; lanza TypeError o ValueError si no es válida.

    `True` aprueba. `False` rechaza con el motivo `otro` y un comentario automático,
    para que todo rechazo conserve un motivo de la lista cerrada.
    """
    if decision is True:
        decision = {"aprobado": True}
    if decision is False:
        return {
            "aprobado": False,
            "motivo": "otro",
            "comentario": "rechazo sin motivo indicado",
        }
    if not isinstance(decision, dict):
        raise TypeError("la decisión debe ser True o un dict con la clave 'aprobado'")
    aprobado = decision.get("aprobado")
    if not isinstance(aprobado, bool):
        raise TypeError("'aprobado' debe ser True o False")
    if aprobado:
        return {"aprobado": True, "motivo": None, "comentario": None}

    motivo = decision.get("motivo")
    if motivo not in MOTIVOS_RECHAZO:
        raise ValueError(f"motivo de rechazo inválido: {motivo!r}")
    comentario = (decision.get("comentario") or "").strip() or None
    if motivo == "otro" and comentario is None:
        raise ValueError("el motivo 'otro' exige comentario")
    return {"aprobado": False, "motivo": motivo, "comentario": comentario}


def supervisar(estado: EstadoSupervision) -> dict:
    solicitud = {
        "accion": "aprobar los casos de prueba generados",
        "casos": estado["casos"],
        "fuentes": estado.get("fuentes", []),
        "version_prompt": estado.get("version_prompt"),
        "motivos_rechazo": list(MOTIVOS_RECHAZO),
        "error": None,
    }
    while True:
        decision = interrupt(solicitud)
        try:
            return validar_decision(decision)
        except (TypeError, ValueError) as error:
            solicitud = {**solicitud, "error": str(error)}


def aplicar(estado: EstadoSupervision) -> dict:
    # Solo una aprobación explícita saca los casos del borrador.
    return {"estado": "aprobado" if estado.get("aprobado") is True else "rechazado"}


def crear_app():
    grafo = StateGraph(EstadoSupervision)
    grafo.add_node("supervisar", supervisar)
    grafo.add_node("aplicar", aplicar)
    grafo.add_edge(START, "supervisar")
    grafo.add_edge("supervisar", "aplicar")
    grafo.add_edge("aplicar", END)
    return grafo.compile(checkpointer=InMemorySaver())


def main() -> None:
    from registro_prompts import NOMBRE_PROMPT, crear_registro

    app = crear_app()
    entrada = {
        "casos": [
            {"id": "TC-01", "titulo": "Crear una reserva dentro del horario permitido"}
        ],
        "fuentes": ["crear-reserva.md#0"],
        "version_prompt": crear_registro().ultima(NOMBRE_PROMPT)["huella"],
        "estado": "borrador",
    }

    config1 = {"configurable": {"thread_id": "supervision-1"}}
    resultado = app.invoke(entrada, config=config1)
    print("pausado:", "__interrupt__" in resultado)
    pendiente = app.get_state(config1).interrupts[0].value
    print("pendiente:", pendiente["accion"], "· prompt:", pendiente["version_prompt"])
    final = app.invoke(Command(resume={"aprobado": True}), config=config1)
    print("camino de aprobación:", final["estado"])

    config2 = {"configurable": {"thread_id": "supervision-2"}}
    app.invoke(entrada, config=config2)
    final = app.invoke(
        Command(resume={"aprobado": False, "motivo": "cita_incorrecta"}), config=config2
    )
    print("camino de rechazo:", final["estado"], "-", final["motivo"])

    config3 = {"configurable": {"thread_id": "supervision-3"}}
    app.invoke(entrada, config=config3)
    final = app.invoke(Command(resume=False), config=config3)
    print("rechazo con False:", final["estado"], "-", final["motivo"])


if __name__ == "__main__":
    main()
