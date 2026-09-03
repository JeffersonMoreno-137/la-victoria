import unittest
import re
from typing import Dict, Any

# Simulador de lógica pura de nodos sin dependencias externas
def detect_language_and_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    text = state.get("user_message", "").lower()
    
    words = set(re.findall(r'\b[a-zA-Z]+\b', text))
    en_keywords = {"hello", "hi", "appointment", "appointments", "schedule", "requirements", "how", "what", "lawyer", "can", "please", "thanks"}
    es_keywords = {"hola", "buenos", "dias", "tardes", "necesito", "informacion", "tramite", "cita", "citas", "agendar", "abogado", "requisitos", "gracias"}

    en_score = len(words.intersection(en_keywords))
    es_score = len(words.intersection(es_keywords))

    if en_score > es_score:
        detected_lang = "en"
    elif es_score > en_score:
        detected_lang = "es"
    else:
        detected_lang = "es" # Default español institucional
    lang = state.get("language") or detected_lang

    intent = "faq"
    if any(w in text for w in ["cita", "agendar", "appointment", "book", "schedule"]):
        intent = "booking"
    elif any(w in text for w in ["mis citas", "my appointments", "cancelar", "reagendar", "reschedule", "cancel"]):
        intent = "manage_appointments"
    elif any(w in text for w in ["hola", "buenos dias", "buenas", "hi", "hello", "start"]):
        intent = "greeting"

    upl_violation = any(kw in text for kw in [
        "me van a deportar", "will i be deported", "puedo ganar mi caso", "can i win my case",
        "es legal si", "is it legal", "consejo legal", "legal advice", "me aprueban la green card"
    ])

    return {
        "language": lang,
        "intent": intent,
        "upl_violation": upl_violation
    }

def upl_guardrail_node(state: Dict[str, Any]) -> Dict[str, Any]:
    lang = state.get("language", "es")
    if lang == "en":
        msg = "⚠️ Legal Notice (UPL Guardrail): As an AI assistant, I cannot provide legal opinions."
    else:
        msg = "⚠️ Aviso Legal Importante: Como asistente virtual (Luna), tengo prohibido emitir dictámenes legales (UPL)."
    return {
        "response_text": msg,
        "inline_keyboard_type": "branches"
    }

class TestAgentGuardrails(unittest.TestCase):

    def test_language_detection_es(self):
        state = {
            "telegram_id": "123",
            "language": None,
            "user_message": "Hola, necesito información sobre el trámite del ITIN"
        }
        res = detect_language_and_intent(state)
        self.assertEqual(res["language"], "es")
        self.assertFalse(res["upl_violation"])

    def test_language_detection_en(self):
        state = {
            "telegram_id": "123",
            "language": None,
            "user_message": "Hi, I need an appointment for my ITIN number"
        }
        res = detect_language_and_intent(state)
        self.assertEqual(res["language"], "en")
        self.assertEqual(res["intent"], "booking")

    def test_upl_guardrail_trigger(self):
        state = {
            "telegram_id": "123",
            "language": "es",
            "user_message": "Dime la verdad, ¿me van a deportar si aplico a este asilo?"
        }
        detection = detect_language_and_intent(state)
        self.assertTrue(detection["upl_violation"])

        state["upl_violation"] = True
        response = upl_guardrail_node(state)
        self.assertIn("UPL", response["response_text"])
        self.assertEqual(response["inline_keyboard_type"], "branches")

if __name__ == "__main__":
    unittest.main()
