import logging
from datetime import datetime, timedelta, date
import pytz
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.core.config import get_settings
from app.agent.graph import build_bot_graph
from app.db.session import SyncSessionLocal
from app.models.entities import Client, Appointment, Branch, Lawyer, AppointmentStatus, Language, ServiceType, BranchCode
from app.services.booking_service import get_available_slots, assign_first_available_lawyer, get_now_est

settings = get_settings()
logger = logging.getLogger(__name__)

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
        "upl_violation": False,
        "selected_branch_code": None,
        "selected_service_type": None,
        "selected_date": None,
        "selected_slot": None,
        "response_text": "",
        "inline_keyboard_type": None,
        "inline_keyboard_options": None
    }
    
    result = graph.invoke(state_input)
    kb = build_inline_keyboard(result.get("inline_keyboard_options", []))
    await message.answer(result["response_text"], reply_markup=kb, parse_mode="Markdown")

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

    msg = "Language changed to English! How can I assist you today?" if selected == "en" else "¡Idioma cambiado a Español! ¿En qué puedo ayudarte hoy?"
    await callback.message.edit_text(msg)
    await callback.answer()

@dp.message(Command("mis_citas", "my_appointments"))
async def cmd_my_appointments(message: types.Message):
    session = SyncSessionLocal()
    try:
        client = session.query(Client).filter(Client.telegram_id == str(message.from_user.id)).first()
        if not client:
            await message.answer("No tienes citas registradas actualmente.")
            return

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
            await message.answer(
                "📅 No tienes citas activas agendadas en este momento.\n\n"
                "¿Deseas programar una nueva cita?",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📅 Agendar Cita", callback_data="start_booking")]
                ])
            )
            return

        for c in citas:
            branch = session.query(Branch).filter(Branch.id == c.branch_id).first()
            lawyer = session.query(Lawyer).filter(Lawyer.id == c.lawyer_id).first()
            date_str = c.start_time.strftime("%A, %d de %B %Y - %I:%M %p EST")
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔄 Reagendar", callback_data=f"reschedule_{c.id}"),
                    InlineKeyboardButton(text="❌ Cancelar", callback_data=f"cancel_{c.id}")
                ]
            ])
            await message.answer(
                f"📌 **Cita Confirmada**\n"
                f"• **Servicio:** {c.service_type.value}\n"
                f"• **Sede:** {branch.name if branch else 'Principal'}\n"
                f"• **Abogado asignado:** {lawyer.full_name if lawyer else 'Por asignar'}\n"
                f"• **Fecha y Hora:** {date_str}\n"
                f"• **Estado:** {c.status.value}",
                reply_markup=kb,
                parse_mode="Markdown"
            )
    finally:
        session.close()

@dp.callback_query(F.data.startswith("cancel_"))
async def cb_cancel_appointment(callback: types.CallbackQuery):
    appointment_id = callback.data.replace("cancel_", "")
    session = SyncSessionLocal()
    try:
        appt = session.query(Appointment).filter(Appointment.id == appointment_id).first()
        if appt:
            appt.status = AppointmentStatus.CANCELLED
            session.commit()
            await callback.message.edit_text("✅ **Tu cita ha sido cancelada exitosamente.** El horario ha sido liberado.", parse_mode="Markdown")
        else:
            await callback.message.edit_text("No se encontró la cita especificada.")
    finally:
        session.close()
    await callback.answer()

# Booking Flow Handlers
@dp.callback_query(F.data == "start_booking")
async def cb_start_booking(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Queens, NY (37-53 90th St)", callback_data="branch_NY_QUEENS")],
        [InlineKeyboardButton(text="📍 Dallas, TX (17762 Preston Rd)", callback_data="branch_TX_DALLAS")]
    ])
    await callback.message.edit_text("📍 Selecciona la sede para tu cita:", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("branch_"))
async def cb_select_branch(callback: types.CallbackQuery):
    branch_code = callback.data.replace("branch_", "")
    user_booking_sessions[callback.from_user.id] = {"branch_code": branch_code}

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Trámite de ITIN Number", callback_data="service_ITIN")],
        [InlineKeyboardButton(text="🏛️ Asesoría de Inmigración", callback_data="service_IMMIGRATION")],
        [InlineKeyboardButton(text="✍️ Notaría y Traducciones", callback_data="service_NOTARY")]
    ])
    await callback.message.edit_text("📑 Selecciona el tipo de servicio:", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("service_"))
async def cb_select_service(callback: types.CallbackQuery):
    service_type = callback.data.replace("service_", "")
    session_data = user_booking_sessions.get(callback.from_user.id, {})
    session_data["service_type"] = service_type
    user_booking_sessions[callback.from_user.id] = session_data

    # Generar próximos 4 días válidos (respetando +24h)
    now_est = get_now_est()
    start_date = (now_est + timedelta(days=1)).date()
    
    date_buttons = []
    current_d = start_date
    while len(date_buttons) < 4:
        if current_d.weekday() != 6: # Excluir domingo
            day_label = current_d.strftime("%a %d %b")
            date_buttons.append([InlineKeyboardButton(text=f"📅 {day_label}", callback_data=f"date_{current_d.isoformat()}")])
        current_d += timedelta(days=1)

    await callback.message.edit_text("📆 Selecciona el día de tu cita (+24h anticipación):", reply_markup=InlineKeyboardMarkup(inline_keyboard=date_buttons))
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

@dp.callback_query(F.data.startswith("slot_"))
async def cb_confirm_slot(callback: types.CallbackQuery):
    slot_iso = callback.data.replace("slot_", "")
    slot_start = datetime.fromisoformat(slot_iso)
    slot_end = slot_start + timedelta(hours=1)

    session_data = user_booking_sessions.get(callback.from_user.id, {})
    branch_code = session_data.get("branch_code", "NY_QUEENS")
    service_type = session_data.get("service_type", "ITIN")

    session = SyncSessionLocal()
    try:
        client = get_or_create_client(str(callback.from_user.id), callback.from_user.full_name)
        branch = session.query(Branch).filter(Branch.code == branch_code).first()
        
        # Algoritmo First Available
        lawyer = assign_first_available_lawyer(session, branch.id, slot_start, slot_end)
        if not lawyer:
            await callback.message.edit_text("Lo sentimos, este slot acaba de ser ocupado. Por favor elige otro horario.")
            return

        new_appt = Appointment(
            branch_id=branch.id,
            lawyer_id=lawyer.id,
            client_id=client.id,
            service_type=ServiceType[service_type],
            start_time=slot_start.replace(tzinfo=None),
            end_time=slot_end.replace(tzinfo=None),
            status=AppointmentStatus.SCHEDULED
        )
        session.add(new_appt)
        session.commit()

        await callback.message.edit_text(
            f"🎉 **¡Cita Agendada con Éxito!**\n\n"
            f"• **Sede:** {branch.name} ({branch.address})\n"
            f"• **Abogado Asignado:** {lawyer.full_name}\n"
            f"• **Servicio:** {service_type}\n"
            f"• **Horario:** {slot_start.strftime('%A, %d de %B %Y - %I:%M %p EST')}\n\n"
            f"Para consultar o reagendar, usa el comando /mis_citas.",
            parse_mode="Markdown"
        )
    finally:
        session.close()
    await callback.answer()

# Entrada Libre de Texto (RAG + Guardrails + Conversación Abierta)
@dp.message(F.text)
async def handle_free_text(message: types.Message):
    client = get_or_create_client(str(message.from_user.id), message.from_user.full_name)
    
    state_input = {
        "telegram_id": str(message.from_user.id),
        "user_name": message.from_user.full_name,
        "phone": None,
        "language": client.language.value,
        "user_message": message.text,
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

    result = graph.invoke(state_input)
    kb = build_inline_keyboard(result.get("inline_keyboard_options", [])) if result.get("inline_keyboard_options") else None
    await message.answer(result["response_text"], reply_markup=kb, parse_mode="Markdown")
