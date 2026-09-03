from langgraph.graph import StateGraph, END
from app.agent.state import BotState
from app.agent.nodes import (
    detect_language_and_intent,
    upl_guardrail_node,
    rag_faq_node,
    greeting_node
)

def route_intent(state: BotState) -> str:
    if state.get("upl_violation"):
        return "upl_guardrail"
    intent = state.get("intent")
    if intent == "greeting":
        return "greeting"
    elif intent in ["booking", "faq"]:
        return "rag_faq"
    return "rag_faq"

def build_bot_graph():
    workflow = StateGraph(BotState)

    # Nodos
    workflow.add_node("detect_language_and_intent", detect_language_and_intent)
    workflow.add_node("upl_guardrail", upl_guardrail_node)
    workflow.add_node("rag_faq", rag_faq_node)
    workflow.add_node("greeting", greeting_node)

    # Punto de entrada
    workflow.set_entry_point("detect_language_and_intent")

    # Enrutamiento condicional
    workflow.add_conditional_edges(
        "detect_language_and_intent",
        route_intent,
        {
            "upl_guardrail": "upl_guardrail",
            "rag_faq": "rag_faq",
            "greeting": "greeting"
        }
    )

    workflow.add_edge("upl_guardrail", END)
    workflow.add_edge("rag_faq", END)
    workflow.add_edge("greeting", END)

    return workflow.compile()
