import json
import re
import logging
from typing import Dict, Any
from app.agent.state import BotState
from app.agent.prompts import VICTORIA_SYSTEM_PROMPT, CLASSIFIER_SYSTEM_PROMPT
from app.rag.retriever import search_faq
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

def detect_language_and_intent(state: BotState) -> Dict[str, Any]:
    """
    Nodo Clasificador Central:
    Utiliza el LLM (gpt-5.6-luna / gpt-4o-mini) con salida estructurada en JSON para determinar
    el idioma, intención (advisory, booking_qualification, upl_guardrail, greeting, manage_appointments),
    tema de servicio y estado de preparación documental según el historial de la conversación.
    """
    raw_text = state.get("user_message", "").strip()
    history = state.get("messages", [])
    clean_lower = raw_text.lower()

    # Fast-Path 0ms: Saludos estándar exactos sin necesidad de llamada a LLM
    greeting_es = {"hola", "buenos dias", "buenas tardes", "buenas noches", "buenas", "hola!", "hola buenas", "/start", "start"}
    greeting_en = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "hi!", "hello!"}
    
    if clean_lower in greeting_es:
        return {
            "language": "es",
            "intent": "greeting",
            "conversation_phase": "greeting",
            "service_topic": "GENERAL",
            "docs_status": "unknown",
            "upl_violation": False,
            "messages": [{"role": "user", "content": raw_text}]
        }
    elif clean_lower in greeting_en:
        return {
            "language": "en",
            "intent": "greeting",
            "conversation_phase": "greeting",
            "service_topic": "GENERAL",
            "docs_status": "unknown",
            "upl_violation": False,
            "messages": [{"role": "user", "content": raw_text}]
        }

    # 1. Clasificación Semántica Inteligente mediante LLM (OpenAI JSON Mode)
    if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-proj-mock") and settings.OPENAI_API_KEY != "your-openai-api-key-here":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            history_context = []
            for m in history[-4:]:
                if isinstance(m, dict):
                    history_context.append({"role": m.get("role", "user"), "content": m.get("content", "")})

            messages = [
                {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                *history_context,
                {"role": "user", "content": f"Mensaje a clasificar: \"{raw_text}\""}
            ]

            # Intentar clasificador ultra-rápido gpt-4o-mini o fallback a OPENAI_MODEL
            classifier_model = "gpt-4o-mini" if "gpt" in settings.OPENAI_MODEL else settings.OPENAI_MODEL
            try:
                completion = client.chat.completions.create(
                    model=classifier_model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_tokens=90
                )
            except Exception:
                completion = client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=messages,
                    response_format={"type": "json_object"}
                )

            result_json = json.loads(completion.choices[0].message.content)
            lang = result_json.get("language", state.get("language") or "es")
            intent = result_json.get("intent", "advisory")
            service_topic = result_json.get("service_topic", state.get("service_topic") or "GENERAL")
            if service_topic == "GENERAL":
                if state.get("service_topic") and state.get("service_topic") != "GENERAL":
                    service_topic = state.get("service_topic")
                elif history:
                    for m in reversed(history):
                        c = m.get("content", "").lower() if isinstance(m, dict) else str(m).lower()
                        if any(kw in c for kw in ["itin", "w-7", "w7", "tax", "1040"]):
                            service_topic = "ITIN"
                            break
                        elif any(kw in c for kw in ["notar", "notaria", "notary", "traducc", "apostill"]):
                            service_topic = "NOTARY"
                            break
                        elif any(kw in c for kw in ["inmigra", "immigra", "asilo", "asylum", "peticion", "i-130", "i-485", "green card", "visa", "spouse", "matrimonio", "esposo", "esposa"]):
                            service_topic = "IMMIGRATION"
                            break
                
            docs_status = result_json.get("docs_status", "unknown")
            upl_violation = bool(result_json.get("upl_violation", False) or intent == "upl_guardrail")

            # Seguridad: Respuestas contextuales cortas dentro de una conversación activa
            if history and len(history) > 0:
                # Si el usuario responde que no o que aún le faltan requisitos
                negative_responses = {"no", "no aun", "no aún", "todavia no", "todavía no", "no tengo", "no lo tengo", "aun no", "aún no", "no he cumplido", "no cumplo", "not yet", "no i don't", "no i dont", "missing", "dont have"}
                if clean_lower in negative_responses or any(clean_lower.startswith(w) for w in ["no,", "no.", "todavía no", "aún no", "no ", "not yet"]):
                    if intent == "greeting" or intent == "upl_guardrail":
                        intent = "advisory"
                    docs_status = "missing_docs"
                    upl_violation = False

                # Si el usuario responde afirmativamente que ya tiene los documentos listos
                affirmative_responses = {
                    "si", "sí", "si los tengo", "sí los tengo", "tengo todo", "ya tengo todo", "listo", "todo listo", "si ya tengo", "sí ya tengo",
                    "yes", "yes i have everything", "i have everything", "yes, i have everything", "yes i do", "i have all documents", "all ready",
                    "ready", "i'm ready", "im ready", "we have everything", "yes we have everything", "have everything", "all set"
                }
                ready_markers = [
                    "tengo los papeles", "tengo los documentos", "tengo mi pasaporte", "tengo todo listo", "estoy listo", "estoy lista",
                    "tengo los requisitos", "ya tengo los", "ya cuento con", "todo listo", "si tengo", "sí tengo",
                    "i have the documents", "i have my passport", "i have all documents", "documents ready", "ready to book", "all set",
                    "have everything", "i have everything", "yes i have everything", "got everything", "ready to schedule"
                ]
                if clean_lower in affirmative_responses or any(marker in clean_lower for marker in ready_markers) or any(clean_lower.startswith(w) for w in ["si,", "sí,", "si ya", "sí ya", "yes,", "yes "]):
                    intent = "booking_qualification"
                    docs_status = "ready_to_book"
                    upl_violation = False

            # Seguridad: Preguntar por documentos/requisitos o clarificar categorías NUNCA debe considerarse UPL
            doc_inquiry_markers = [
                "que necesito", "qué necesito", "que documentos", "qué documentos", "requisitos", "requirements",
                "what do i need", "documents", "papeles", "seria por", "sería por", "por asilo", "por matrimonio",
                "por peticion", "por petición", "formulario", "form", "enesito", "nesecito", "nececito"
            ]
            if any(marker in clean_lower for marker in doc_inquiry_markers):
                if intent == "upl_guardrail" or upl_violation:
                    intent = "advisory"
                    upl_violation = False

            phase = intent
            if intent == "upl_guardrail":
                phase = "upl_triggered"

            logger.info(f"Clasificación LLM completada: intent={intent}, topic={service_topic}, docs_status={docs_status}, lang={lang}, upl={upl_violation}")

            return {
                "language": lang,
                "intent": intent,
                "conversation_phase": phase,
                "service_topic": service_topic,
                "docs_status": docs_status,
                "upl_violation": upl_violation,
                "messages": [{"role": "user", "content": raw_text}]
            }
        except Exception as e:
            logger.warning(f"Error en clasificación con LLM, recurriendo a fallback heurístico: {e}")

    # 2. Fallback Heurístico (Resiliencia en modo offline o sin API Key)
    text = raw_text.lower()
    words = set(re.findall(r'\b[a-zA-ZáéíóúÁÉÍÓÚñÑ]+\b', text))
    en_keywords = {"hello", "hi", "appointment", "appointments", "schedule", "requirements", "how", "what", "lawyer", "can", "please", "thanks", "book", "documents", "passport", "ready", "taxes", "itin", "have"}
    es_keywords = {"hola", "buenos", "dias", "tardes", "necesito", "informacion", "tramite", "cita", "citas", "agendar", "abogado", "requisitos", "gracias", "documentos", "papeles", "pasaporte", "listo", "tengo", "declaracion", "asilo", "seria"}

    en_score = len(words.intersection(en_keywords))
    es_score = len(words.intersection(es_keywords))

    if en_score > es_score:
        detected_lang = "en"
    elif es_score > en_score:
        detected_lang = "es"
    else:
        detected_lang = state.get("language") or "es"

    lang = state.get("language") or detected_lang

    service_topic = state.get("service_topic") or "GENERAL"
    if any(kw in text for kw in ["itin", "w-7", "w7", "tax", "taxes", "impuesto", "impuestos", "declaracion", "1040"]):
        service_topic = "ITIN"
    elif any(kw in text for kw in ["notar", "notaria", "notario", "notary", "traducc", "traducir", "apostill", "certificad"]):
        service_topic = "NOTARY"
    elif any(kw in text for kw in ["inmigra", "immigra", "asilo", "asylum", "peticion", "i-130", "i130", "ajuste", "i-485", "i485", "daca", "green card", "residencia", "ciudadan", "parole", "n-400", "visa", "visas", "esposo", "esposa", "spouse", "marriage", "matrimonio"]):
        service_topic = "IMMIGRATION"
    elif service_topic == "GENERAL" and history:
        for m in reversed(history):
            c = m.get("content", "").lower() if isinstance(m, dict) else str(m).lower()
            if any(kw in c for kw in ["itin", "w-7", "w7", "tax", "1040"]):
                service_topic = "ITIN"
                break
            elif any(kw in c for kw in ["notar", "notaria", "notary", "traducc", "apostill"]):
                service_topic = "NOTARY"
                break
            elif any(kw in c for kw in ["inmigra", "immigra", "asilo", "asylum", "peticion", "i-130", "i-485", "green card", "visa", "spouse", "matrimonio", "esposo", "esposa"]):
                service_topic = "IMMIGRATION"
                break

    upl_violation = any(kw in text for kw in [
        "me van a deportar", "will i be deported", "puedo ganar mi caso", "can i win my case",
        "es legal si", "is it legal to", "consejo legal", "legal advice",
        "tengo probabilidades de ganar", "tengo posibilidad de ganar", "me aseguran que gano"
    ])

    ready_patterns = [
        "tengo los papeles", "tengo los documentos", "tengo mi pasaporte", "tengo todo listo", "estoy listo", "estoy lista",
        "tengo los requisitos", "ya tengo los", "ya cuento con", "i have the documents", "i have my passport",
        "i have all documents", "documents ready", "ready to book", "all set", "have everything", "i have everything", "yes i have everything",
        "quiero agendar", "deseo agendar", "agendar cita", "sacar cita", "programar cita", "solicitar cita",
        "book an appointment", "schedule an appointment", "book appointment", "make an appointment",
        "agendame", "dame una cita", "necesito agendar", "quiero una cita"
    ]
    is_ready_to_book = any(pat in text for pat in ready_patterns)

    if upl_violation:
        intent = "upl_guardrail"
        phase = "upl_triggered"
    elif any(w in text for w in ["mis citas", "my appointments", "cancelar cita", "reagendar cita"]):
        intent = "manage_appointments"
        phase = "manage_appointments"
    elif text in greeting_es or text in greeting_en:
        intent = "greeting"
        phase = "greeting"
    elif is_ready_to_book:
        intent = "booking_qualification"
        phase = "booking_qualification"
    else:
        intent = "advisory"
        phase = "advisory"

    docs_status = "ready_to_book" if is_ready_to_book else "unknown"

    return {
        "language": lang,
        "intent": intent,
        "conversation_phase": phase,
        "service_topic": service_topic,
        "docs_status": docs_status,
        "upl_violation": upl_violation,
        "messages": [{"role": "user", "content": raw_text}]
    }

def upl_guardrail_node(state: BotState) -> Dict[str, Any]:
    lang = state.get("language", "es")
    if lang == "en":
        msg = (
            "⚠️ **Important Legal Notice (UPL Guardrail):**\n\n"
            "As an AI assistant (VictorIA), I am strictly prohibited from providing legal counsel, predicting case outcomes, or assessing individual eligibility (Unauthorized Practice of Law).\n\n"
            "Every immigration case has unique nuances. To review your situation with full confidentiality and professional legal standing, we invite you to book a consultation with one of our licensed attorneys at La Victoria Foundation."
        )
        btn_queens = "📍 Queens, NY Branch"
        btn_dallas = "📍 Dallas, TX Branch"
    else:
        msg = (
            "⚠️ **Aviso Legal Importante:**\n\n"
            "Como asistente virtual (VictorIA), tengo estrictamente prohibido emitir dictámenes, evaluar probabilidades de éxito o dar asesoría jurídica particular (Guardrail UPL).\n\n"
            "Las leyes de inmigración son minuciosas y cada caso es único. Para analizar tu situación con total respaldo profesional y confidencialidad, te invitamos a agendar una consulta con uno de los abogados licenciados de La Victoria Foundation."
        )
        btn_queens = "📍 Sede Queens, NY"
        btn_dallas = "📍 Sede Dallas, TX"

    return {
        "response_text": msg,
        "show_buttons": True,
        "inline_keyboard_type": "branches",
        "inline_keyboard_options": [
            {"text": btn_queens, "callback_data": "branch_NY_QUEENS"},
            {"text": btn_dallas, "callback_data": "branch_TX_DALLAS"}
        ],
        "messages": [{"role": "assistant", "content": msg}]
    }

def document_advisory_node(state: BotState) -> Dict[str, Any]:
    """
    Flujo 1: Resolución de dudas y asesoría sobre requisitos de documentos.
    Responde con RAG + estructura de checklist en texto Markdown.
    NO adjunta botones forzados para permitir una conversación natural.
    """
    query = state.get("user_message", "")
    lang = state.get("language", "es")
    service_topic = state.get("service_topic", "GENERAL")
    
    # Búsqueda semántica RAG
    search_results = search_faq(query, limit=2)
    context_text = "\n\n".join([f"Fuente: {r['title']}\n{r['content']}" for r in search_results]) if search_results else ""

    history_messages = []
    for msg in state.get("messages", [])[-6:]:
        if isinstance(msg, dict):
            history_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

    answer = ""
    # Llamada a OpenAI si está configurada
    if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-proj-mock") and settings.OPENAI_API_KEY != "your-openai-api-key-here":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            system_content = f"{VICTORIA_SYSTEM_PROMPT}\n\nINFORMACIÓN DE SOPORTE (RAG):\n{context_text}"
            llm_messages = [{"role": "system", "content": system_content}]
            llm_messages.extend(history_messages)
            llm_messages.append({"role": "user", "content": query})

            completion = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=llm_messages
            )
            answer = completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Error en OpenAI API call: {e}")

    # Fallbacks enriquecidos y estructurados por tipo de trámite
    if not answer:
        if lang == "en":
            if service_topic == "ITIN":
                answer = (
                    "📋 **ITIN Number (Individual Taxpayer Identification Number) Guide:**\n\n"
                    "The ITIN is an IRS tax processing number for individuals who must file federal taxes but are not eligible for a Social Security Number (SSN).\n\n"
                    "**Required Documents Checklist:**\n"
                    "• **Form W-7:** Completed and signed application form.\n"
                    "• **Federal Tax Return:** Form 1040 (income taxes), unless meeting a specific exception.\n"
                    "• **Proof of Identity & Foreign Status:** An original, unexpired passport (or certified copy from issuing agency). Alternatively: National ID / Consular ID + certified Birth Certificate.\n\n"
                    "💡 *Note: An ITIN does not grant legal immigration status or work authorization.*\n\n"
                    "👉 **Do you currently have these documents ready, or do you have any questions about obtaining them?**"
                )
            elif service_topic == "NOTARY":
                answer = (
                    "✍️ **Notary & Certified Translation Services:**\n\n"
                    "At La Victoria Foundation, we provide official notary seals and certified translations for legal and immigration paperwork.\n\n"
                    "**Requirements Checklist:**\n"
                    "• Original documents to be notarized or translated (birth, marriage certificates, affidavits).\n"
                    "• Valid government-issued photo ID (Passport, State ID, Driver's License).\n"
                    "• Signers must be present for document notarization.\n\n"
                    "👉 **What documents do you need translated or notarized?**"
                )
            elif service_topic == "IMMIGRATION":
                answer = (
                    "🏛️ **Immigration Legal Services Overview:**\n\n"
                    "Our legal team assists with Family Petitions (I-130), Adjustment of Status (I-485), DACA renewals, Asylum orientation, and Naturalization (N-400).\n\n"
                    "**General Document Checklist:**\n"
                    "• Valid original passport or official identification.\n"
                    "• Prior immigration documents (I-94, previous notices, court documents if applicable).\n"
                    "• Certified civil certificates (birth, marriage) with certified English translations.\n\n"
                    "👉 **Tell me more about your situation: Which specific immigration process are you exploring?**"
                )
            else:
                answer = (
                    "🤝 **La Victoria Foundation Community Support:**\n\n"
                    "We offer guidance on ITIN numbers, immigration procedures, and certified notary services at our Queens, NY and Dallas, TX centers.\n\n"
                    "👉 **Feel free to ask any specific question about your paperwork or the documents required.**"
                )
        else:
            if service_topic == "ITIN":
                answer = (
                    "📋 **Guía y Requisitos para Trámite de Número ITIN:**\n\n"
                    "El ITIN es un número tributario emitido por el IRS para personas que necesitan declarar impuestos federales pero no son elegibles para un Número de Seguro Social (SSN).\n\n"
                    "**Checklist de Documentos Necesarios:**\n"
                    "• **Formulario W-7:** Solicitud oficial debidamente completada y firmada.\n"
                    "• **Declaración Federal de Impuestos (Form 1040):** Salvo que apliques a una excepción del IRS.\n"
                    "• **Documento de Identidad y Condición de Extranjero:** Pasaporte original vigente (es el documento principal). *Alternativa:* Cédula de identidad nacional o matrícula consular vigente + Acta de nacimiento oficial.\n\n"
                    "💡 *Nota importante: El ITIN no otorga estatus migratorio ni autorización de trabajo legal.*\n\n"
                    "👉 **¿Cuentas actualmente con estos documentos a la mano o requieres apoyo para tramitar alguno de ellos?**"
                )
            elif service_topic == "NOTARY":
                answer = (
                    "✍️ **Servicios Notariales y Traducciones Certificadas:**\n\n"
                    "En La Victoria Foundation brindamos sellos notariales y traducciones certificadas oficiales para procesos legales y de inmigración.\n\n"
                    "**Requisitos Documentales:**\n"
                    "• Documentos originales a certificar o traducir (actas de nacimiento, matrimonio, declaraciones juradas).\n"
                    "• Identificación oficial con fotografía vigente (Pasaporte, DNI, Licencia).\n"
                    "• Presencia física de los firmantes para trámites notariales.\n\n"
                    "👉 **¿Qué tipo de documento necesitas certificar o traducir?**"
                )
            elif service_topic == "IMMIGRATION":
                answer = (
                    "🏛️ **Orientación en Servicios de Inmigración:**\n\n"
                    "Acompañamos trámites de Petición Familiar (I-130), Ajuste de Estatus (Green Card), Asilo, Renovación DACA y Naturalización (N-400).\n\n"
                    "**Documentación Clave Requerida:**\n"
                    "• Pasaporte original vigente e identificación oficial.\n"
                    "• Historial o registros migratorios previos (I-94, permisos, notificaciones de USCIS o corte si aplican).\n"
                    "• Actas de estado civil (nacimiento, matrimonio) apostilladas o acompañadas de traducción certificada.\n\n"
                    "👉 **Cuéntame un poco más de tu caso: ¿Qué trámite migratorio te gustaría iniciar o revisar?**"
                )
            else:
                answer = (
                    "🤝 **Orientación Comunitaria - La Victoria Foundation:**\n\n"
                    "Brindamos acompañamiento en Número ITIN, servicios legales de inmigración y notaría en nuestras sedes de Queens, NY y Dallas, TX.\n\n"
                    "👉 **Escríbeme tu duda y con gusto te detallamos los requisitos y pasos a seguir.**"
                )

    return {
        "response_text": answer,
        "show_buttons": False,
        "inline_keyboard_type": None,
        "inline_keyboard_options": None,
        "messages": [{"role": "assistant", "content": answer}]
    }

def booking_qualification_node(state: BotState) -> Dict[str, Any]:
    """
    Flujo 2: Agendamiento calificado.
    Se activa cuando el usuario cuenta con los documentos o pide explícitamente agendar.
    Despliega de manera oportuna los botones para seleccionar la sede, incluyendo el servicio ya calificado.
    """
    lang = state.get("language", "es")
    service_topic = state.get("service_topic", "GENERAL")
    if service_topic not in ["ITIN", "IMMIGRATION", "NOTARY"]:
        for m in reversed(state.get("messages", [])):
            c = m.get("content", "").lower() if isinstance(m, dict) else str(m).lower()
            if any(kw in c for kw in ["itin", "w-7", "w7", "tax", "1040"]):
                service_topic = "ITIN"
                break
            elif any(kw in c for kw in ["notar", "notaria", "notary", "traducc", "apostill"]):
                service_topic = "NOTARY"
                break
            elif any(kw in c for kw in ["inmigra", "immigra", "asilo", "asylum", "peticion", "i-130", "i-485", "green card", "visa", "spouse", "matrimonio", "esposo", "esposa"]):
                service_topic = "IMMIGRATION"
                break

    topic_suffix = f"_{service_topic}" if service_topic in ["ITIN", "IMMIGRATION", "NOTARY"] else ""

    if lang == "en":
        service_label = "your consultation"
        if service_topic == "ITIN":
            service_label = "your ITIN processing appointment"
        elif service_topic == "IMMIGRATION":
            service_label = "your immigration legal consultation"
        elif service_topic == "NOTARY":
            service_label = "your notary appointment"

        msg = (
            f"🎉 **Great! You are ready to schedule {service_label}.**\n\n"
            "Please select your preferred branch to check available dates and time slots with our legal team:"
        )
        options = [
            {"text": "📍 Queens, NY (37-53 90th St)", "callback_data": f"branch_NY_QUEENS{topic_suffix}"},
            {"text": "📍 Dallas, TX (17762 Preston Rd)", "callback_data": f"branch_TX_DALLAS{topic_suffix}"}
        ]
    else:
        service_label = "tu consulta"
        if service_topic == "ITIN":
            service_label = "tu trámite de ITIN"
        elif service_topic == "IMMIGRATION":
            service_label = "tu asesoría legal de inmigración"
        elif service_topic == "NOTARY":
            service_label = "tu cita de notaría"

        msg = (
            f"🎉 **¡Excelente! Todo listo para coordinar {service_label}.**\n\n"
            "Por favor selecciona la sede de tu preferencia para ver los días y horarios disponibles:"
        )
        options = [
            {"text": "📍 Queens, NY (37-53 90th St)", "callback_data": f"branch_NY_QUEENS{topic_suffix}"},
            {"text": "📍 Dallas, TX (17762 Preston Rd)", "callback_data": f"branch_TX_DALLAS{topic_suffix}"}
        ]

    return {
        "service_topic": service_topic,
        "response_text": msg,
        "show_buttons": True,
        "inline_keyboard_type": "branches",
        "inline_keyboard_options": options,
        "messages": [{"role": "assistant", "content": msg}]
    }

def greeting_node(state: BotState) -> Dict[str, Any]:
    lang = state.get("language", "es")
    if lang == "en":
        msg = (
            "👋 Welcome to **La Victoria Foundation**!\n"
            "I am VictorIA, your bilingual virtual assistant.\n\n"
            "You can ask me any question about ITIN requirements, immigration services, or schedule an appointment with our legal team."
        )
        options = [
            {"text": "📅 Book Appointment", "callback_data": "start_booking"},
            {"text": "📄 My Appointments", "callback_data": "my_appointments"},
            {"text": "🌐 Language / Idioma", "callback_data": "set_lang_es"}
        ]
    else:
        msg = (
            "👋 ¡Bienvenido a **La Victoria Foundation**!\n"
            "Soy VictorIA, tu asistente virtual bilingüe.\n\n"
            "Puedes escribirme libremente tus preguntas sobre requisitos para Número ITIN, trámites de inmigración o agendar una cita con nuestro equipo legal."
        )
        options = [
            {"text": "📅 Agendar Cita", "callback_data": "start_booking"},
            {"text": "📄 Mis Citas", "callback_data": "my_appointments"},
            {"text": "🌐 Idioma / Language", "callback_data": "set_lang_en"}
        ]

    return {
        "response_text": msg,
        "show_buttons": True,
        "inline_keyboard_type": "main_menu",
        "inline_keyboard_options": options,
        "messages": [{"role": "assistant", "content": msg}]
    }

def manage_appointments_node(state: BotState) -> Dict[str, Any]:
    telegram_id = state.get("telegram_id")
    lang = state.get("language", "es")
    
    from app.db.session import SyncSessionLocal
    from app.models.entities import Client, Appointment, Branch, Lawyer, AppointmentStatus
    
    session = SyncSessionLocal()
    try:
        client = session.query(Client).filter(Client.telegram_id == str(telegram_id)).first() if telegram_id else None
        citas = []
        if client:
            citas = (
                session.query(Appointment)
                .filter(
                    Appointment.client_id == client.id,
                    Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.RESCHEDULED])
                )
                .order_by(Appointment.start_time.asc())
                .all()
            )

        if not citas:
            if lang == "en":
                msg = "📅 You currently have no active appointments scheduled.\n\nWould you like to schedule a new appointment?"
                options = [{"text": "📅 Book Appointment", "callback_data": "start_booking"}]
            else:
                msg = "📅 No tienes citas activas agendadas en este momento.\n\n¿Deseas programar una nueva cita?"
                options = [{"text": "📅 Agendar Cita", "callback_data": "start_booking"}]
            return {
                "response_text": msg,
                "show_buttons": True,
                "inline_keyboard_type": "none",
                "inline_keyboard_options": options,
                "messages": [{"role": "assistant", "content": msg}]
            }

        # Formatear la primera cita activa
        c = citas[0]
        branch = session.query(Branch).filter(Branch.id == c.branch_id).first()
        lawyer = session.query(Lawyer).filter(Lawyer.id == c.lawyer_id).first()
        date_str = c.start_time.strftime("%A, %d de %B %Y - %I:%M %p EST")

        if lang == "en":
            msg = (
                f"📌 **Your Active Appointment:**\n\n"
                f"• **Service:** {c.service_type.value}\n"
                f"• **Branch:** {branch.name if branch else 'Main'}\n"
                f"• **Attorney:** {lawyer.full_name if lawyer else 'To be assigned'}\n"
                f"• **Date & Time:** {date_str}\n"
                f"• **Status:** {c.status.value}\n\n"
                f"Select an option below to manage this appointment:"
            )
            options = [
                {"text": "🔄 Reschedule", "callback_data": f"reschedule_{c.id}"},
                {"text": "❌ Cancel", "callback_data": f"cancel_{c.id}"}
            ]
        else:
            msg = (
                f"📌 **Tu Cita Activa:**\n\n"
                f"• **Servicio:** {c.service_type.value}\n"
                f"• **Sede:** {branch.name if branch else 'Principal'}\n"
                f"• **Abogado:** {lawyer.full_name if lawyer else 'Por asignar'}\n"
                f"• **Fecha y Hora:** {date_str}\n"
                f"• **Estado:** {c.status.value}\n\n"
                f"Selecciona una opción para gestionar tu cita:"
            )
            options = [
                {"text": "🔄 Reagendar", "callback_data": f"reschedule_{c.id}"},
                {"text": "❌ Cancelar", "callback_data": f"cancel_{c.id}"}
            ]

        return {
            "response_text": msg,
            "show_buttons": True,
            "inline_keyboard_type": "manage_appointment",
            "inline_keyboard_options": options,
            "messages": [{"role": "assistant", "content": msg}]
        }
    finally:
        session.close()

