import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
import pytz
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.chat_action import ChatActionSender
from app.core.config import get_settings
from app.agent.graph import build_bot_graph
from app.db.session import SyncSessionLocal
from app.models.entities import Client, Appointment, Branch, Lawyer, AppointmentStatus, Language, ServiceType, BranchCode
from app.services.booking_service import get_available_slots, assign_first_available_lawyer, get_now_est

settings = get_settings()
logger = logging.getLogger(__name__)

# Asegurar loop de asyncio en entornos Python 3.9 / uvloop
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN) if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_TOKEN != "mock_telegram_token_placeholder" else None
dp = Dispatcher()
graph = build_bot_graph()

# In-memory user booking state for inline navigation
user_booking_sessions = {}

def get_or_create_client(telegram_id: str, full_name: str = None) -> Client:
    session = SyncSessionLocal()
    try:
        client = session.query(Client).filter(Client.telegram_id == str(telegram_id)).first()
        if not client:
            client = Client(
                telegram_id=str(telegram_id),
                full_name=full_name or "Usuario Telegram",
                language=Language.ES
            )
            session.add(client)
            session.commit()
            session.refresh(client)
        return client
    finally:
        session.close()

def build_inline_keyboard(options: list, row_width: int = 2) -> InlineKeyboardMarkup:
    keyboard = []
    current_row = []
    for opt in options:
        current_row.append(InlineKeyboardButton(text=opt["text"], callback_data=opt["callback_data"]))
        if len(current_row) >= row_width:
            keyboard.append(current_row)
            current_row = []
    if current_row:
        keyboard.append(current_row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def safe_edit_message(target, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None, parse_mode: Optional[str] = "Markdown"):
    """
    Edita un mensaje de forma segura con fallback automático a texto plano
    si Telegram falla por caracteres especiales de Markdown.
    """
    try:
        if isinstance(target, types.CallbackQuery):
            await target.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await target.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        logger.warning(f"Error editando mensaje con parse_mode={parse_mode}: {e}. Reintentando sin parse_mode.")
        try:
            plain_text = text.replace("**", "").replace("*", "")
            if isinstance(target, types.CallbackQuery):
                await target.message.edit_text(plain_text, reply_markup=reply_markup, parse_mode=None)
            else:
                await target.edit_text(plain_text, reply_markup=reply_markup, parse_mode=None)
        except Exception as e2:
            logger.error(f"Fallo total al editar mensaje: {e2}")
            try:
                if isinstance(target, types.CallbackQuery):
                    await target.message.answer(text.replace("**", "").replace("*", ""), reply_markup=reply_markup)
            except Exception:
                pass

async def safe_send_message(target_message: types.Message, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None, parse_mode: Optional[str] = "Markdown"):
    """
    Envía un mensaje de forma segura con fallback automático a texto plano.
    """
    try:
        await target_message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        logger.warning(f"Error enviando mensaje con parse_mode={parse_mode}: {e}. Reintentando sin parse_mode.")
        try:
            plain_text = text.replace("**", "").replace("*", "")
            await target_message.answer(plain_text, reply_markup=reply_markup, parse_mode=None)
        except Exception as e2:
            logger.error(f"Fallo total al enviar mensaje: {e2}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    client = get_or_create_client(str(message.from_user.id), message.from_user.full_name)
    lang = client.language.value

    state_input = {
        "telegram_id": str(message.from_user.id),
        "user_name": message.from_user.full_name,
        "phone": None,
        "language": lang,
        "user_message": "/start",
        "messages": [],
        "intent": "greeting",
        "conversation_phase": "greeting",
        "service_topic": None,
        "docs_status": None,
        "upl_violation": False,
        "selected_branch_code": None,
        "selected_service_type": None,
        "selected_date": None,
        "selected_slot": None,
        "show_buttons": True,
        "response_text": "",
        "inline_keyboard_type": None,
        "inline_keyboard_options": None
    }
    
    config = {"configurable": {"thread_id": str(message.from_user.id)}}
    result = graph.invoke(state_input, config=config)
    kb = build_inline_keyboard(result.get("inline_keyboard_options", [])) if result.get("show_buttons") and result.get("inline_keyboard_options") else None
    await safe_send_message(message, result["response_text"], reply_markup=kb)

@dp.message(Command("idioma", "language"))
async def cmd_language(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇪🇸 Español", callback_data="set_lang_es"),
            InlineKeyboardButton(text="🇺🇸 English", callback_data="set_lang_en")
        ]
    ])
    await message.answer("Selecciona tu idioma preferido / Select your preferred language:", reply_markup=kb)

@dp.callback_query(F.data.startswith("set_lang_"))
async def cb_set_lang(callback: types.CallbackQuery):
    selected = callback.data.replace("set_lang_", "")
    session = SyncSessionLocal()
    try:
        client = session.query(Client).filter(Client.telegram_id == str(callback.from_user.id)).first()
        if client:
            client.language = Language.EN if selected == "en" else Language.ES
            session.commit()
    finally:
        session.close()

    if selected == "en":
        msg = (
            "🌐 *Language changed to English!*\n\n"
            "👋 Welcome to **La Victoria Foundation**!\n"
            "I am VictorIA, your bilingual virtual assistant.\n\n"
            "You can ask me any question about ITIN requirements, immigration services, or schedule an appointment with our legal team."
        )
        options = [
            {"text": "📅 Book Appointment", "callback_data": "start_booking"},
            {"text": "📄 My Appointments", "callback_data": "my_appointments"},
            {"text": "🌐 Idioma / Language", "callback_data": "set_lang_es"}
        ]
    else:
        msg = (
            "🌐 *¡Idioma cambiado a Español!*\n\n"
            "👋 ¡Bienvenido a **La Victoria Foundation**!\n"
            "Soy VictorIA, tu asistente virtual bilingüe.\n\n"
            "Puedes escribirme libremente tus preguntas sobre requisitos para Número ITIN, trámites de inmigración o agendar una cita con nuestro equipo legal."
        )
        options = [
            {"text": "📅 Agendar Cita", "callback_data": "start_booking"},
            {"text": "📄 Mis Citas", "callback_data": "my_appointments"},
            {"text": "🌐 Language / Idioma", "callback_data": "set_lang_en"}
        ]

    kb = build_inline_keyboard(options)
    await callback.message.edit_text(msg, reply_markup=kb, parse_mode="Markdown")
    await callback.answer("Language updated / Idioma actualizado")

async def display_user_appointments(telegram_id: str, user_name: str, target_message: types.Message = None, callback: types.CallbackQuery = None):
    client = get_or_create_client(telegram_id, user_name)
    lang = client.language.value if client else "es"

    session = SyncSessionLocal()
    try:
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
            empty_msg = (
                "📅 You don't have any active appointments scheduled at this moment.\n\n"
                "Would you like to schedule a new appointment?"
            ) if lang == "en" else (
                "📅 No tienes citas activas agendadas en este momento.\n\n"
                "¿Deseas programar una nueva cita?"
            )
            btn_book = "📅 Book Appointment" if lang == "en" else "📅 Agendar Cita"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=btn_book, callback_data="start_booking")]
            ])
            if callback:
                await callback.message.edit_text(empty_msg, reply_markup=kb)
            elif target_message:
                await target_message.answer(empty_msg, reply_markup=kb)
            return

        if callback:
            await callback.message.edit_text(
                "📋 **Your Scheduled Appointments:**" if lang == "en" else "📋 **Tus Citas Programadas:**",
                parse_mode="Markdown"
            )

        for c in citas:
            branch = session.query(Branch).filter(Branch.id == c.branch_id).first()
            lawyer = session.query(Lawyer).filter(Lawyer.id == c.lawyer_id).first()
            
            if lang == "en":
                date_str = c.start_time.strftime("%A, %B %d, %Y - %I:%M %p EST")
                service_val = {
                    "ITIN": "ITIN Number Processing",
                    "IMMIGRATION": "Immigration Legal Consultation",
                    "NOTARY": "Notary & Translations"
                }.get(c.service_type.name, c.service_type.value)
                appt_card = (
                    f"📌 **Confirmed Appointment**\n"
                    f"• **Service:** {service_val}\n"
                    f"• **Branch:** {branch.name if branch else 'Main'}\n"
                    f"• **Assigned Attorney:** {lawyer.full_name if lawyer else 'To be assigned'}\n"
                    f"• **Date & Time:** {date_str}\n"
                    f"• **Status:** {c.status.value}"
                )
                btn_reschedule = "🔄 Reschedule"
                btn_cancel = "❌ Cancel"
            else:
                date_str = c.start_time.strftime("%A, %d de %B %Y - %I:%M %p EST")
                service_val = {
                    "ITIN": "Trámite de ITIN Number",
                    "IMMIGRATION": "Asesoría Legal de Inmigración",
                    "NOTARY": "Notaría y Traducciones"
                }.get(c.service_type.name, c.service_type.value)
                appt_card = (
                    f"📌 **Cita Confirmada**\n"
                    f"• **Servicio:** {service_val}\n"
                    f"• **Sede:** {branch.name if branch else 'Principal'}\n"
                    f"• **Abogado asignado:** {lawyer.full_name if lawyer else 'Por asignar'}\n"
                    f"• **Fecha y Hora:** {date_str}\n"
                    f"• **Estado:** {c.status.value}"
                )
                btn_reschedule = "🔄 Reagendar"
                btn_cancel = "❌ Cancelar"

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text=btn_reschedule, callback_data=f"reschedule_{c.id}"),
                    InlineKeyboardButton(text=btn_cancel, callback_data=f"cancel_{c.id}")
                ]
            ])
            
            send_target = target_message or (callback.message if callback else None)
            if send_target:
                await send_target.answer(appt_card, reply_markup=kb, parse_mode="Markdown")
    finally:
        session.close()

@dp.message(Command("mis_citas", "my_appointments"))
async def cmd_my_appointments(message: types.Message):
    await display_user_appointments(
        telegram_id=str(message.from_user.id),
        user_name=message.from_user.full_name,
        target_message=message
    )

@dp.callback_query(F.data == "my_appointments")
async def cb_my_appointments(callback: types.CallbackQuery):
    await display_user_appointments(
        telegram_id=str(callback.from_user.id),
        user_name=callback.from_user.full_name,
        callback=callback
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("reschedule_"))
async def cb_reschedule_appointment(callback: types.CallbackQuery):
    appointment_id = callback.data.replace("reschedule_", "")
    session = SyncSessionLocal()
    try:
        appt = session.query(Appointment).filter(Appointment.id == appointment_id).first()
        if appt:
            branch = session.query(Branch).filter(Branch.id == appt.branch_id).first()
            user_booking_sessions[callback.from_user.id] = {
                "branch_code": branch.code if branch else "NY_QUEENS",
                "service_type": appt.service_type.name,
                "reschedule_appt_id": str(appt.id)
            }
            client = get_or_create_client(str(callback.from_user.id), callback.from_user.full_name)
            lang = client.language.value if client else "es"
            await render_date_picker(callback, lang)
        else:
            await callback.message.edit_text("No se encontró la cita a reagendar.")
    finally:
        session.close()
    await callback.answer()

@dp.callback_query(F.data.startswith("cancel_"))
async def cb_cancel_appointment(callback: types.CallbackQuery):
    appointment_id = callback.data.replace("cancel_", "")
    session = SyncSessionLocal()
    try:
        appt = session.query(Appointment).filter(Appointment.id == appointment_id).first()
        if appt:
            appt.status = AppointmentStatus.CANCELLED
            session.commit()
            
            # Notificar en tiempo real a todos los dashboards conectados vía WebSocket
            from app.services.websocket_manager import ws_manager
            asyncio.create_task(ws_manager.broadcast({
                "event": "APPOINTMENT_CANCELLED",
                "appointment": {
                    "id": str(appt.id),
                    "status": "CANCELLED"
                }
            }))

            client = get_or_create_client(str(callback.from_user.id), callback.from_user.full_name)
            lang = client.language.value if client else "es"
            cancel_msg = (
                "✅ **Your appointment has been successfully cancelled.** The time slot has been released."
                if lang == "en"
                else "✅ **Tu cita ha sido cancelada exitosamente.** El horario ha sido liberado."
            )
            await callback.message.edit_text(cancel_msg, parse_mode="Markdown")
        else:
            await callback.message.edit_text("No se encontró la cita especificada.")
    finally:
        session.close()
    await callback.answer()

# Booking Flow Handlers
@dp.callback_query(F.data == "start_booking")
async def cb_start_booking(callback: types.CallbackQuery):
    client = get_or_create_client(str(callback.from_user.id), callback.from_user.full_name)
    lang = client.language.value if client else "es"

    if lang == "en":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📍 Queens, NY (37-53 90th St)", callback_data="branch_NY_QUEENS")],
            [InlineKeyboardButton(text="📍 Dallas, TX (17762 Preston Rd)", callback_data="branch_TX_DALLAS")]
        ])
        await callback.message.edit_text("📍 Please select your preferred branch:", reply_markup=kb)
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📍 Queens, NY (37-53 90th St)", callback_data="branch_NY_QUEENS")],
            [InlineKeyboardButton(text="📍 Dallas, TX (17762 Preston Rd)", callback_data="branch_TX_DALLAS")]
        ])
        await callback.message.edit_text("📍 Selecciona la sede para tu cita:", reply_markup=kb)
    await callback.answer()

async def render_date_picker(callback: types.CallbackQuery, lang: str):
    now_est = get_now_est()
    start_date = (now_est + timedelta(days=1)).date()
    
    date_buttons = []
    current_d = start_date
    while len(date_buttons) < 4:
        if current_d.weekday() != 6: # Excluir domingo
            if lang == "es":
                day_names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
                month_names = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
                day_label = f"{day_names[current_d.weekday()]} {current_d.day} {month_names[current_d.month]}"
            else:
                day_label = current_d.strftime("%a %b %d")
            date_buttons.append([InlineKeyboardButton(text=f"📅 {day_label}", callback_data=f"date_{current_d.isoformat()}")])
        current_d += timedelta(days=1)

    prompt_msg = "📆 Selecciona el día de tu cita (+24h de anticipación):" if lang == "es" else "📆 Select the day for your appointment (+24h advance):"
    await callback.message.edit_text(prompt_msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=date_buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("branch_"))
async def cb_select_branch(callback: types.CallbackQuery):
    raw_data = callback.data.replace("branch_", "")
    
    branch_code = "NY_QUEENS"
    service_type = None
    
    if raw_data.startswith("NY_QUEENS"):
        branch_code = "NY_QUEENS"
        rem = raw_data[len("NY_QUEENS"):].lstrip("_")
        if rem in ["ITIN", "IMMIGRATION", "NOTARY"]:
            service_type = rem
    elif raw_data.startswith("TX_DALLAS"):
        branch_code = "TX_DALLAS"
        rem = raw_data[len("TX_DALLAS"):].lstrip("_")
        if rem in ["ITIN", "IMMIGRATION", "NOTARY"]:
            service_type = rem
    else:
        branch_code = raw_data

    session_data = user_booking_sessions.get(callback.from_user.id, {})
    session_data["branch_code"] = branch_code
    if service_type:
        session_data["service_type"] = service_type
    user_booking_sessions[callback.from_user.id] = session_data

    client = get_or_create_client(str(callback.from_user.id), callback.from_user.full_name)
    lang = client.language.value if client else "es"

    # Si ya tenemos el tipo de servicio (porque vino precalificado de la conversación), saltamos directo al selector de fechas
    effective_service = service_type or session_data.get("service_type")
    if effective_service and effective_service in ["ITIN", "IMMIGRATION", "NOTARY"]:
        await render_date_picker(callback, lang)
        return

    # Si no hay servicio especificado (ej. inicio desde /start -> Agendar Cita), mostramos el menú de servicios
    if lang == "en":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📄 ITIN Number Processing", callback_data="service_ITIN")],
            [InlineKeyboardButton(text="🏛️ Immigration Legal Consultation", callback_data="service_IMMIGRATION")],
            [InlineKeyboardButton(text="✍️ Notary & Translations", callback_data="service_NOTARY")]
        ])
        await callback.message.edit_text("📑 Select the type of service you need:", reply_markup=kb)
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📄 Trámite de ITIN Number", callback_data="service_ITIN")],
            [InlineKeyboardButton(text="🏛️ Asesoría de Inmigración", callback_data="service_IMMIGRATION")],
            [InlineKeyboardButton(text="✍️ Notaría y Traducciones", callback_data="service_NOTARY")]
        ])
        await callback.message.edit_text("📑 Selecciona el tipo de servicio:", reply_markup=kb)
    await callback.answer()

SERVICE_REQUIREMENTS = {
    "ITIN": {
        "title_es": "📄 Trámite de Número ITIN (Formulario W-7)",
        "title_en": "📄 ITIN Number Processing (Form W-7)",
        "docs_es": (
            "📋 **Requisitos Obligatorios para la Cita de ITIN:**\n\n"
            "1. **Pasaporte original vigente** (o Cédula Nacional/Consular + Acta de Nacimiento oficial).\n"
            "2. **Declaración federal de impuestos (Formulario 1040)** si aplica.\n"
            "3. **Documentos de dependientes** (si se incluirán en la declaración).\n\n"
            "⚠️ *Para poder procesar tu solicitud ante el IRS sin rechazos, es indispensable presentar estos documentos el día de tu cita.*"
        ),
        "docs_en": (
            "📋 **Mandatory Requirements for ITIN Appointment:**\n\n"
            "1. **Original, unexpired passport** (or National/Consular ID + official Birth Certificate).\n"
            "2. **Federal tax return (Form 1040)** if applicable.\n"
            "3. **Dependents documentation** (if claiming dependents).\n\n"
            "⚠️ *To submit your application to the IRS without delays, you must bring these documents to your appointment.*"
        ),
    },
    "IMMIGRATION": {
        "title_es": "🏛️ Asesoría Legal de Inmigración",
        "title_en": "🏛️ Immigration Legal Consultation",
        "docs_es": (
            "📋 **Requisitos y Documentos para tu Asesoría Migratoria:**\n\n"
            "1. **Pasaporte vigente** o documento de identidad oficial con foto.\n"
            "2. **Historial migratorio previo** (I-94, notificaciones de USCIS, permisos o documentos de corte si aplican).\n"
            "3. **Actas de estado civil** (nacimiento, matrimonio) según el trámite a evaluar.\n\n"
            "⚠️ *Tener tus registros migratorios organizados permitirá al abogado analizar tu caso con total precisión.*"
        ),
        "docs_en": (
            "📋 **Requirements for Immigration Legal Consultation:**\n\n"
            "1. **Unexpired passport** or government-issued photo ID.\n"
            "2. **Prior immigration records** (I-94, USCIS notices, work permits or court records if applicable).\n"
            "3. **Civil certificates** (birth, marriage) relevant to your process.\n\n"
            "⚠️ *Having your immigration paperwork ready allows the attorney to accurately assess your case.*"
        ),
    },
    "NOTARY": {
        "title_es": "✍️ Notaría y Traducciones Certificadas",
        "title_en": "✍️ Notary & Certified Translations",
        "docs_es": (
            "📋 **Requisitos para Servicios Notariales y Traducciones:**\n\n"
            "1. **Documentos originales** que deseas notarizar o traducir.\n"
            "2. **Identificación oficial con foto vigente** (Pasaporte, Licencia de conducir o DNI).\n"
            "3. **Presencia física** de las personas firmantes para sellos notariales.\n\n"
            "⚠️ *Para traducciones certificadas, asegúrate de traer los documentos originales o copias legibles completas.*"
        ),
        "docs_en": (
            "📋 **Requirements for Notary & Certified Translations:**\n\n"
            "1. **Original documents** to be notarized or translated.\n"
            "2. **Valid government-issued photo ID** (Passport, State ID, Driver's License).\n"
            "3. **Signers must be present** in person for document notarization.\n\n"
            "⚠️ *For certified translations, please bring original or clear complete copies.*"
        ),
    }
}

@dp.callback_query(F.data.startswith("service_"))
async def cb_select_service(callback: types.CallbackQuery):
    service_type = callback.data.replace("service_", "")
    session_data = user_booking_sessions.get(callback.from_user.id, {})
    session_data["service_type"] = service_type
    user_booking_sessions[callback.from_user.id] = session_data

    client = get_or_create_client(str(callback.from_user.id), callback.from_user.full_name)
    lang = client.language.value if client else "es"

    req_info = SERVICE_REQUIREMENTS.get(service_type, SERVICE_REQUIREMENTS["ITIN"])
    docs_text = req_info["docs_en"] if lang == "en" else req_info["docs_es"]

    btn_yes = "✅ Sí, tengo los requisitos listos" if lang == "es" else "✅ Yes, I have the requirements ready"
    btn_help = "❓ Tengo dudas / Me falta alguno" if lang == "es" else "❓ I have questions / Missing documents"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_yes, callback_data=f"confirm_docs_{service_type}")],
        [InlineKeyboardButton(text=btn_help, callback_data=f"need_help_{service_type}")]
    ])

    await callback.message.edit_text(
        f"{docs_text}\n\n"
        f"👉 **{'¿Cuentas con estos documentos listos para tu cita?' if lang == 'es' else 'Do you have these documents ready for your appointment?'}**",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("confirm_docs_"))
async def cb_confirm_docs(callback: types.CallbackQuery):
    service_type = callback.data.replace("confirm_docs_", "")
    session_data = user_booking_sessions.get(callback.from_user.id, {})
    session_data["service_type"] = service_type
    user_booking_sessions[callback.from_user.id] = session_data

    client = get_or_create_client(str(callback.from_user.id), callback.from_user.full_name)
    lang = client.language.value if client else "es"

    await render_date_picker(callback, lang)

@dp.callback_query(F.data.startswith("need_help_"))
async def cb_need_help(callback: types.CallbackQuery):
    service_type = callback.data.replace("need_help_", "")
    client = get_or_create_client(str(callback.from_user.id), callback.from_user.full_name)
    lang = client.language.value if client else "es"

    if lang == "en":
        msg = (
            "🤝 **No worries! We are here to guide you.**\n\n"
            "You don't need to rush into booking an appointment if you are missing any required document. "
            "Please write your question directly in this chat, and I will explain how to obtain or verify your paperwork step by step."
        )
    else:
        msg = (
            "🤝 **¡No te preocupes! Estamos para orientarte.**\n\n"
            "No es necesario agendar una cita hasta que tengas claros tus documentos. "
            "Escríbeme libremente tu consulta aquí en el chat y te explicaré paso a paso cómo obtener o validar cada requisito antes de programar tu visita."
        )

    await callback.message.edit_text(msg, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("date_"))
async def cb_select_date(callback: types.CallbackQuery):
    target_date_str = callback.data.replace("date_", "")
    target_date = date.fromisoformat(target_date_str)
    
    session_data = user_booking_sessions.get(callback.from_user.id, {})
    session_data["target_date"] = target_date_str
    user_booking_sessions[callback.from_user.id] = session_data

    branch_code = session_data.get("branch_code", "NY_QUEENS")

    session = SyncSessionLocal()
    try:
        available_slots = get_available_slots(session, branch_code, target_date)
        if not available_slots:
            await callback.message.edit_text(
                "❌ No hay horarios disponibles para la fecha seleccionada. Por favor selecciona otro día.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Seleccionar otro día", callback_data=f"branch_{branch_code}")]
                ])
            )
            return

        slot_buttons = []
        for s in available_slots:
            time_iso = s["start_time"]
            slot_buttons.append([InlineKeyboardButton(text=f"⏰ {s['display_time']}", callback_data=f"slot_{time_iso}")])

        await callback.message.edit_text("⏰ Selecciona una hora disponible (Excluye almuerzo 12-1pm):", reply_markup=InlineKeyboardMarkup(inline_keyboard=slot_buttons))
    finally:
        session.close()
    await callback.answer()

# Candados de agendamiento para evitar doble clic o múltiples clics concurrentes
booking_locks = set()

@dp.callback_query(F.data.startswith("slot_"))
async def cb_confirm_slot(callback: types.CallbackQuery):
    await callback.answer("Procesando tu cita...")

    lock_key = f"{callback.from_user.id}_{callback.data}"
    if lock_key in booking_locks:
        return
    booking_locks.add(lock_key)

    slot_iso = callback.data.replace("slot_", "")
    slot_start = datetime.fromisoformat(slot_iso)
    slot_end = slot_start + timedelta(hours=1)

    session_data = user_booking_sessions.get(callback.from_user.id, {})
    branch_code = session_data.get("branch_code", "NY_QUEENS")
    service_type = session_data.get("service_type", "ITIN")
    reschedule_appt_id = session_data.get("reschedule_appt_id")

    session = SyncSessionLocal()
    try:
        client = get_or_create_client(str(callback.from_user.id), callback.from_user.full_name)
        lang = client.language.value if client else "es"
        branch = session.query(Branch).filter(Branch.code == branch_code).first()
        
        start_naive = slot_start.replace(tzinfo=None)
        end_naive = slot_end.replace(tzinfo=None)

        # Validación anti-duplicado: ¿El usuario ya tiene una cita agendada en este slot?
        existing_user_appt = session.query(Appointment).filter(
            Appointment.client_id == client.id,
            Appointment.status == AppointmentStatus.SCHEDULED,
            Appointment.start_time == start_naive
        ).first()

        if existing_user_appt:
            already_msg = (
                "ℹ️ **You already have a confirmed appointment for this time slot.** You can check or manage your bookings with the options below:"
                if lang == "en"
                else "ℹ️ **Ya tienes una cita confirmada para este mismo horario.** Puedes consultar o gestionar tus citas con las opciones abajo:"
            )
            btn_manage = "📄 My Appointments" if lang == "en" else "📄 Mis Citas"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=btn_manage, callback_data="my_appointments")]
            ])
            await safe_edit_message(callback, already_msg, reply_markup=kb)
            return

        # Algoritmo First Available
        lawyer = assign_first_available_lawyer(session, branch.id, slot_start, slot_end)
        if not lawyer:
            no_slot_msg = (
                "Sorry, this time slot was just fully booked. Please choose another time slot."
                if lang == "en"
                else "Lo sentimos, este horario acaba de ser ocupado por completo. Por favor elige otro horario."
            )
            await safe_edit_message(callback, no_slot_msg)
            return

        new_appt = Appointment(
            branch_id=branch.id,
            lawyer_id=lawyer.id,
            client_id=client.id,
            service_type=ServiceType[service_type],
            start_time=start_naive,
            end_time=end_naive,
            status=AppointmentStatus.SCHEDULED
        )
        session.add(new_appt)

        # Si era un reagendamiento, cancelar la cita anterior
        if reschedule_appt_id:
            old_appt = session.query(Appointment).filter(Appointment.id == reschedule_appt_id).first()
            if old_appt:
                old_appt.status = AppointmentStatus.CANCELLED
                from app.services.websocket_manager import ws_manager
                asyncio.create_task(ws_manager.broadcast({
                    "event": "APPOINTMENT_CANCELLED",
                    "appointment": {
                        "id": str(old_appt.id),
                        "status": "CANCELLED"
                    }
                }))

        session.commit()
        session.refresh(new_appt)

        # Limpiar la sesión en memoria para evitar reintentos accidentales
        user_booking_sessions.pop(callback.from_user.id, None)

        # Transmitir en tiempo real a todos los dashboards conectados via WebSocket
        from app.services.websocket_manager import ws_manager
        asyncio.create_task(ws_manager.broadcast({
            "event": "APPOINTMENT_CREATED",
            "appointment": {
                "id": str(new_appt.id),
                "branch_code": branch.code,
                "lawyer_id": str(lawyer.id),
                "lawyer_name": lawyer.full_name,
                "client_name": client.full_name,
                "service_type": service_type,
                "date": slot_start.strftime("%Y-%m-%d"),
                "hour": slot_start.hour,
                "status": "SCHEDULED"
            }
        }))

        if lang == "en":
            service_display = {
                "ITIN": "ITIN Number Processing",
                "IMMIGRATION": "Immigration Legal Consultation",
                "NOTARY": "Notary & Translations"
            }.get(service_type, service_type)
            confirmation_text = (
                f"🎉 **Appointment Scheduled Successfully!**\n\n"
                f"• **Branch:** {branch.name} ({branch.address})\n"
                f"• **Assigned Attorney:** {lawyer.full_name}\n"
                f"• **Service:** {service_display}\n"
                f"• **Schedule:** {slot_start.strftime('%A, %B %d, %Y - %I:%M %p EST')}\n\n"
                f"You can review or manage your bookings anytime using the button below or typing /my_appointments."
            )
            btn_manage = "📄 My Appointments"
            btn_book_another = "📅 Book Another"
        else:
            service_display = {
                "ITIN": "Trámite de ITIN Number",
                "IMMIGRATION": "Asesoría Legal de Inmigración",
                "NOTARY": "Notaría y Traducciones"
            }.get(service_type, service_type)
            confirmation_text = (
                f"🎉 **¡Cita Agendada con Éxito!**\n\n"
                f"• **Sede:** {branch.name} ({branch.address})\n"
                f"• **Abogado Asignado:** {lawyer.full_name}\n"
                f"• **Servicio:** {service_display}\n"
                f"• **Horario:** {slot_start.strftime('%A, %d de %B %Y - %I:%M %p EST')}\n\n"
                f"Puedes consultar o reagendar tus citas en cualquier momento usando el botón abajo o escribiendo /mis_citas."
            )
            btn_manage = "📄 Mis Citas"
            btn_book_another = "📅 Agendar Otra Cita"

        confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=btn_manage, callback_data="my_appointments"),
                InlineKeyboardButton(text=btn_book_another, callback_data="start_booking")
            ]
        ])

        await safe_edit_message(callback, confirmation_text, reply_markup=confirm_kb)
    finally:
        session.close()
        booking_locks.discard(lock_key)

# Entrada Libre de Texto (RAG + Guardrails + Conversación Abierta)
@dp.message(F.text)
async def handle_free_text(message: types.Message):
    client = get_or_create_client(str(message.from_user.id), message.from_user.full_name)
    
    state_input = {
        "telegram_id": str(message.from_user.id),
        "user_name": message.from_user.full_name,
        "language": client.language.value,
        "user_message": message.text,
    }

    config = {"configurable": {"thread_id": str(message.from_user.id)}}

    try:
        # Indicador 'escribiendo...' activo durante la inferencia y cerrado antes de responder
        if bot:
            async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id, interval=3.0):
                result = await asyncio.to_thread(graph.invoke, state_input, config)
        else:
            result = await asyncio.to_thread(graph.invoke, state_input, config)

        detected_lang = result.get("language")
        if detected_lang and detected_lang in ["es", "en"] and detected_lang != client.language.value:
            session = SyncSessionLocal()
            try:
                c = session.query(Client).filter(Client.telegram_id == str(message.from_user.id)).first()
                if c:
                    c.language = Language.EN if detected_lang == "en" else Language.ES
                    session.commit()
            finally:
                session.close()

        show_buttons = result.get("show_buttons", False)
        kb = build_inline_keyboard(result.get("inline_keyboard_options", [])) if show_buttons and result.get("inline_keyboard_options") else None
        
        try:
            await message.answer(result["response_text"], reply_markup=kb, parse_mode="Markdown")
        except Exception:
            # Fallback en caso de que algún carácter especial rompa el parser de Markdown
            await message.answer(result["response_text"], reply_markup=kb)

    except Exception as e:
        logger.error(f"Error procesando mensaje en grafo: {e}")
        await message.answer(
            "Lo siento, ocurrió una interrupción al procesar tu consulta. Por favor inténtalo de nuevo o selecciona una de las opciones del menú:",
            reply_markup=build_inline_keyboard([
                {"text": "📅 Agendar Cita", "callback_data": "start_booking"},
                {"text": "📄 Mis Citas", "callback_data": "my_appointments"}
            ])
        )


