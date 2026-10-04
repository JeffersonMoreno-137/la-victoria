import logging
from langgraph.graph import StateGraph, END
from app.agent.state import BotState
from app.agent.nodes import (
    detect_language_and_intent,
    upl_guardrail_node,
    document_advisory_node,
    booking_qualification_node,
    greeting_node,
    manage_appointments_node
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)

def route_intent(state: BotState) -> str:
    if state.get("upl_violation"):
        return "upl_guardrail"
    intent = state.get("intent")
    if intent == "greeting":
        return "greeting"
    elif intent == "booking_qualification":
        return "booking_qualification"
    elif intent == "manage_appointments":
        return "manage_appointments"
    elif intent == "advisory":
        return "document_advisory"
    return "document_advisory"

def build_bot_graph():
    workflow = StateGraph(BotState)

    # Nodos
    workflow.add_node("detect_language_and_intent", detect_language_and_intent)
    workflow.add_node("upl_guardrail", upl_guardrail_node)
    workflow.add_node("document_advisory", document_advisory_node)
    workflow.add_node("booking_qualification", booking_qualification_node)
    workflow.add_node("greeting", greeting_node)
    workflow.add_node("manage_appointments", manage_appointments_node)

    # Punto de entrada
    workflow.set_entry_point("detect_language_and_intent")

    # Enrutamiento condicional
    workflow.add_conditional_edges(
        "detect_language_and_intent",
        route_intent,
        {
            "upl_guardrail": "upl_guardrail",
            "document_advisory": "document_advisory",
            "booking_qualification": "booking_qualification",
            "greeting": "greeting",
            "manage_appointments": "manage_appointments"
        }
    )

    workflow.add_edge("upl_guardrail", END)
    workflow.add_edge("document_advisory", END)
    workflow.add_edge("booking_qualification", END)
    workflow.add_edge("greeting", END)
    workflow.add_edge("manage_appointments", END)

    # Configurar Checkpointer nativo de LangGraph (PostgreSQL en producción, MemorySaver en fallback)
    checkpointer = None
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        import psycopg
        settings = get_settings()
        conn = psycopg.connect(settings.DATABASE_URL_SYNC, autocommit=True, connect_timeout=3)
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS langgraph;")
        conn.execute("SET search_path TO langgraph, public;")
        checkpointer = PostgresSaver(conn)
        checkpointer.setup()
        logger.info("LangGraph PostgresSaver checkpointer activado en el esquema 'langgraph'.")
    except Exception as e:
        logger.warning(f"PostgresSaver no disponible ({e}), activando MemorySaver para LangGraph.")
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)


