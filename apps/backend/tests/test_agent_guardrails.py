import pytest
from app.agent.state import BotState
from app.agent.nodes import detect_language_and_intent, upl_guardrail_node

def test_language_detection_es():
    state: BotState = {
        "telegram_id": "123",
        "user_name": "Jefferson",
        "phone": None,
        "language": None,
        "user_message": "Hola, necesito información sobre el trámite del ITIN",
        "messages": [],
        "intent": None,
        "upl_violation": False,
        "selected_branch_code": None,
        "selected_service_type": None,
        "selected_date": None,
        "selected_slot": None,
        "response_text": "",
        "inline_keyboard_type": None,
        "inline_keyboard_options": None
    }
    result = detect_language_and_intent(state)
    assert result["language"] == "es"
    assert result["upl_violation"] is False

def test_language_detection_en():
    state: BotState = {
        "telegram_id": "123",
        "user_name": "John",
        "phone": None,
        "language": None,
        "user_message": "Hi, I need an appointment for my ITIN number and requirements",
        "messages": [],
        "intent": None,
        "upl_violation": False,
        "selected_branch_code": None,
        "selected_service_type": None,
        "selected_date": None,
        "selected_slot": None,
        "response_text": "",
        "inline_keyboard_type": None,
        "inline_keyboard_options": None
    }
    result = detect_language_and_intent(state)
    assert result["language"] == "en"
    assert result["intent"] == "booking"

def test_upl_guardrail_trigger():
    state: BotState = {
        "telegram_id": "123",
        "user_name": "Pedro",
        "phone": None,
        "language": "es",
        "user_message": "Dime la verdad, ¿me van a deportar si aplico a este asilo?",
        "messages": [],
        "intent": None,
        "upl_violation": False,
        "selected_branch_code": None,
        "selected_service_type": None,
        "selected_date": None,
        "selected_slot": None,
        "response_text": "",
        "inline_keyboard_type": None,
        "inline_keyboard_options": None
    }
    detection = detect_language_and_intent(state)
    assert detection["upl_violation"] is True

    # Ejecución del nodo de guardrail
    state["upl_violation"] = True
    response = upl_guardrail_node(state)
    assert "UPL" in response["response_text"] or "Aviso Legal" in response["response_text"]
    assert response["inline_keyboard_type"] == "branches"
