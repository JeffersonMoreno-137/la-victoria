import json
import re
from typing import Dict, Any
from app.agent.state import BotState
from app.agent.prompts import LUNA_SYSTEM_PROMPT
from app.rag.retriever import search_faq
from app.core.config import get_settings

settings = get_settings()

def detect_language_and_intent(state: BotState) -> Dict[str, Any]:
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
        detected_lang = "es"

    lang = state.get("language") or detected_lang

    # Intención
    intent = "faq"
    if any(w in text for w in ["cita", "agendar", "appointment", "book", "schedule"]):
        intent = "booking"
    elif any(w in text for w in ["mis citas", "my appointments", "cancelar", "reagendar", "reschedule", "cancel"]):
        intent = "manage_appointments"
    elif any(w in text for w in ["hola", "buenos dias", "buenas", "hi", "hello", "start"]):
        intent = "greeting"

    # Guardrail UPL check preliminar por palabras clave críticas
    upl_violation = any(kw in text for kw in [
        "me van a deportar", "will i be deported", "puedo ganar mi caso", "can i win my case",
        "es legal si", "is it legal", "consejo legal", "legal advice", "me aprueban la green card"
    ])

    return {
        "language": lang,
        "intent": intent,
        "upl_violation": upl_violation
    }

def upl_guardrail_node(state: BotState) -> Dict[str, Any]:
    lang = state.get("language", "es")
    if lang == "en":
        msg = (
            "⚠️ **Legal Notice (UPL Guardrail):**\n"
            "As an AI assistant (Luna), I cannot provide legal opinions or individualized case assessments. "
            "Immigration laws are delicate and every personal history is unique.\n\n"
            "To review your specific case with full legal guarantee and confidentiality, we invite you to schedule a consultation with one of our licensed attorneys at our Queens, NY or Dallas, TX branches."
        )
    else:
        msg = (
            "⚠️ **Aviso Legal Importante:**\n"
            "Como asistente virtual (Luna), tengo prohibido emitir dictámenes, opiniones legales o evaluar la viabilidad individual de un caso (Guardrail UPL).\n\n"
            "Las leyes de inmigración son estrictas y cada situación es única. Para analizar tu caso con total garantía profesional y confidencialidad, te invitamos a agendar una consulta con uno de los abogados licenciados de La Victoria Foundation en Queens, NY o Dallas, TX."
        )

    return {
        "response_text": msg,
        "inline_keyboard_type": "branches",
        "inline_keyboard_options": [
            {"text": "📍 Sede Queens, NY", "callback_data": "branch_NY_QUEENS"},
            {"text": "📍 Sede Dallas, TX", "callback_data": "branch_TX_DALLAS"}
        ]
    }

def rag_faq_node(state: BotState) -> Dict[str, Any]:
    query = state.get("user_message", "")
    lang = state.get("language", "es")
    
    # Búsqueda semántica
    search_results = search_faq(query, limit=2)
    context_text = "\n\n".join([f"Fuente: {r['title']}\n{r['content']}" for r in search_results]) if search_results else ""

    # Si hay API Key de OpenAI, generamos respuesta con gpt-5.6-luna
    if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-proj-mock") and settings.OPENAI_API_KEY != "your-openai-api-key-here":
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        system_content = f"{LUNA_SYSTEM_PROMPT}\n\nINFORMACIÓN DE SOPORTE (RAG):\n{context_text}"
        completion = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": query}
            ],
            temperature=0.3
        )
        answer = completion.choices[0].message.content
    else:
        if lang == "en":
            answer = (
                f"Thank you for contacting La Victoria Foundation. Based on our information:\n\n"
                f"{context_text[:350] if context_text else 'We provide specialized assistance for ITIN numbers, immigration processes, and document notary services.'}\n\n"
                "Would you like to schedule an appointment with one of our legal advisors?"
            )
        else:
            answer = (
                f"Gracias por comunicarte con La Victoria Foundation. Según nuestra base de orientación:\n\n"
                f"{context_text[:350] if context_text else 'En La Victoria Foundation brindamos acompañamiento especializado en trámites de Número ITIN, procesos de inmigración y servicios notariales.'}\n\n"
                "¿Deseas agendar una cita presencial o virtual con nuestros asesores?"
            )

    return {
        "response_text": answer,
        "inline_keyboard_type": "services",
        "inline_keyboard_options": [
            {"text": "📅 Agendar Trámite ITIN", "callback_data": "service_ITIN"},
            {"text": "🏛️ Asesoría Inmigración", "callback_data": "service_IMMIGRATION"},
            {"text": "✍️ Notaría y Traducciones", "callback_data": "service_NOTARY"}
        ]
    }

def greeting_node(state: BotState) -> Dict[str, Any]:
    lang = state.get("language", "es")
    if lang == "en":
        msg = (
            "👋 Welcome to **La Victoria Foundation**!\n"
            "I am Luna, your bilingual virtual assistant.\n\n"
            "You can ask me any questions about ITIN Number requirements, immigration services, or schedule an appointment with our legal team."
        )
    else:
        msg = (
            "👋 ¡Bienvenido a **La Victoria Foundation**!\n"
            "Soy Luna, tu asistente virtual bilingüe.\n\n"
            "Puedes escribirme libremente tu consulta sobre trámites de Número ITIN, servicios de inmigración o agendar directamente una cita con nuestro equipo legal."
        )

    return {
        "response_text": msg,
        "inline_keyboard_type": "main_menu",
        "inline_keyboard_options": [
            {"text": "📅 Agendar Cita / Book Appointment", "callback_data": "start_booking"},
            {"text": "📄 Mis Citas / My Appointments", "callback_data": "my_appointments"},
            {"text": "🌐 Idioma / Language", "callback_data": "change_lang"}
        ]
    }
