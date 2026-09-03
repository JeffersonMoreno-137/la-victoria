from datetime import datetime, timedelta, date, time
from typing import List, Dict, Optional
import pytz
from sqlalchemy.orm import Session
from app.models.entities import Branch, Lawyer, Appointment, AppointmentStatus, ServiceType, BranchCode

EST = pytz.timezone("America/New_York")

# Horarios base de lunes a viernes: 09:00 a 16:00 excluyendo 12:00
WEEKDAY_SLOT_HOURS = [9, 10, 11, 13, 14, 15, 16]

# Horarios base sábado: 09:00, 10:00, 11:00
SATURDAY_SLOT_HOURS = [9, 10, 11]

def get_now_est() -> datetime:
    return datetime.now(EST)

def is_slot_valid_business_rules(candidate_start: datetime, now_est: Optional[datetime] = None) -> bool:
    """
    Reglas de negocio:
    1. Antelación Mínima: Al menos 24 Horas exactas antes del inicio de la cita.
    2. Pausa de almuerzo: Bloqueo de 12:00 PM a 1:00 PM (hora 12).
    3. Domingo: Cerrado.
    4. Sábado: Solo 09:00, 10:00, 11:00.
    5. Lunes a Viernes: 09:00, 10:00, 11:00, 13:00, 14:00, 15:00, 16:00.
    """
    if now_est is None:
        now_est = get_now_est()

    if candidate_start.tzinfo is None:
        candidate_start = EST.localize(candidate_start)

    # 1. Regla +24 horas exactas
    if candidate_start < now_est + timedelta(hours=24):
        return False

    weekday = candidate_start.weekday() # 0 = Lunes, 5 = Sábado, 6 = Domingo
    hour = candidate_start.hour

    # 2. Bloqueo de almuerzo
    if hour == 12:
        return False

    # 3. Domingo cerrado
    if weekday == 6:
        return False

    # 4. Sábados
    if weekday == 5:
        return hour in SATURDAY_SLOT_HOURS

    # 5. Lunes a Viernes
    return hour in WEEKDAY_SLOT_HOURS

def get_available_slots(
    db: Session,
    branch_code: str,
    target_date: date,
    now_est: Optional[datetime] = None
) -> List[Dict]:
    """
    Devuelve las franjas horarias disponibles para una sede en una fecha determinada.
    Verifica que al menos un abogado de la sede no tenga cita activa en ese slot.
    """
    if now_est is None:
        now_est = get_now_est()

    branch = db.query(Branch).filter(Branch.code == branch_code).first()
    if not branch:
        return []

    # Abogados activos de la sede ordenados por prioridad L1, L2, L3
    lawyers = (
        db.query(Lawyer)
        .filter(Lawyer.branch_id == branch.id, Lawyer.is_active == True)
        .order_by(Lawyer.priority_order.asc())
        .all()
    )

    if not lawyers:
        return []

    weekday = target_date.weekday()
    if weekday == 6: # Domingo
        return []

    valid_hours = SATURDAY_SLOT_HOURS if weekday == 5 else WEEKDAY_SLOT_HOURS
    available_slots = []

    for hour in valid_hours:
        slot_dt = EST.localize(datetime.combine(target_date, time(hour=hour, minute=0)))
        
        # Validar regla +24h y almuerzo
        if not is_slot_valid_business_rules(slot_dt, now_est):
            continue

        slot_end_dt = slot_dt + timedelta(hours=1)
        # Convertir a naive UTC o timestamp para comparar con BD
        start_naive = slot_dt.replace(tzinfo=None)
        end_naive = slot_end_dt.replace(tzinfo=None)

        # Consultar abogados con citas en este slot (SCHEDULED o RESCHEDULED)
        booked_lawyer_ids = set(
            row[0] for row in db.query(Appointment.lawyer_id)
            .filter(
                Appointment.branch_id == branch.id,
                Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.RESCHEDULED]),
                Appointment.start_time < end_naive,
                Appointment.end_time > start_naive
            )
            .all()
        )

        # Buscar el primer abogado disponible (Algoritmo First Available L1 -> L2 -> L3)
        available_lawyer = next((l for l in lawyers if l.id not in booked_lawyer_ids), None)

        if available_lawyer:
            available_slots.append({
                "start_time": slot_dt.isoformat(),
                "display_time": f"{hour:02d}:00 - {hour+1:02d}:00 EST",
                "lawyer_id": str(available_lawyer.id),
                "lawyer_name": available_lawyer.full_name
            })

    return available_slots

def assign_first_available_lawyer(
    db: Session,
    branch_id,
    start_time: datetime,
    end_time: datetime
) -> Optional[Lawyer]:
    """
    Algoritmo First Available:
    Selecciona el primer abogado disponible según priority_order (L1 -> L2 -> L3)
    que no tenga citas solapadas en ese intervalo.
    """
    lawyers = (
        db.query(Lawyer)
        .filter(Lawyer.branch_id == branch_id, Lawyer.is_active == True)
        .order_by(Lawyer.priority_order.asc())
        .all()
    )

    start_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
    end_naive = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time

    for lawyer in lawyers:
        existing = (
            db.query(Appointment)
            .filter(
                Appointment.lawyer_id == lawyer.id,
                Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.RESCHEDULED]),
                Appointment.start_time < end_naive,
                Appointment.end_time > start_naive
            )
            .first()
        )
        if not existing:
            return lawyer

    return None
