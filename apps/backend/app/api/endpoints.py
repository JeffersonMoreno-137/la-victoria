from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, date
from app.db.session import SyncSessionLocal
from app.models.entities import Appointment, Branch, Lawyer, Client, AppointmentStatus, BranchCode

router = APIRouter(prefix="/api", tags=["Admin Dashboard"])

def get_sync_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/metrics")
def get_dashboard_metrics(db: Session = Depends(get_sync_db)):
    total_appointments = db.query(func.count(Appointment.id)).scalar() or 0
    scheduled_appointments = db.query(func.count(Appointment.id)).filter(Appointment.status == AppointmentStatus.SCHEDULED).scalar() or 0
    cancelled_appointments = db.query(func.count(Appointment.id)).filter(Appointment.status == AppointmentStatus.CANCELLED).scalar() or 0
    rescheduled_appointments = db.query(func.count(Appointment.id)).filter(Appointment.status == AppointmentStatus.RESCHEDULED).scalar() or 0

    queens_count = (
        db.query(func.count(Appointment.id))
        .join(Branch)
        .filter(Branch.code == BranchCode.NY_QUEENS.value)
        .scalar() or 0
    )

    dallas_count = (
        db.query(func.count(Appointment.id))
        .join(Branch)
        .filter(Branch.code == BranchCode.TX_DALLAS.value)
        .scalar() or 0
    )

    return {
        "total_appointments": total_appointments,
        "scheduled_appointments": scheduled_appointments,
        "cancelled_appointments": cancelled_appointments,
        "rescheduled_appointments": rescheduled_appointments,
        "queens_appointments": queens_count,
        "dallas_appointments": dallas_count
    }

@router.get("/appointments")
def list_appointments(
    branch_code: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = 50,
    db: Session = Depends(get_sync_db)
):
    query = (
        db.query(Appointment, Branch, Lawyer, Client)
        .join(Branch, Appointment.branch_id == Branch.id)
        .join(Lawyer, Appointment.lawyer_id == Lawyer.id)
        .join(Client, Appointment.client_id == Client.id)
    )

    if branch_code:
        query = query.filter(Branch.code == branch_code)
    if status:
        query = query.filter(Appointment.status == status)

    rows = query.order_by(Appointment.start_time.desc()).limit(limit).all()

    results = []
    for appt, branch, lawyer, client in rows:
        results.append({
            "id": str(appt.id),
            "branch_id": str(branch.id),
            "branch_code": branch.code,
            "branch_name": branch.name,
            "lawyer_id": str(lawyer.id),
            "lawyer_name": lawyer.full_name,
            "client_name": client.full_name,
            "client_telegram_id": client.telegram_id,
            "service_type": appt.service_type.value,
            "start_time": appt.start_time.isoformat(),
            "end_time": appt.end_time.isoformat(),
            "status": appt.status.value,
            "created_at": appt.created_at.isoformat()
        })

    return results

@router.get("/branches")
def list_branches(db: Session = Depends(get_sync_db)):
    branches = db.query(Branch).all()
    results = []
    for b in branches:
        lawyers = db.query(Lawyer).filter(Lawyer.branch_id == b.id, Lawyer.is_active == True).order_by(Lawyer.priority_order).all()
        results.append({
            "id": str(b.id),
            "code": b.code,
            "name": b.name,
            "address": b.address,
            "lawyers": [{"id": str(l.id), "name": l.full_name, "priority": l.priority_order} for l in lawyers]
        })
    return results

from pydantic import BaseModel
from datetime import time, timedelta
from app.services.websocket_manager import ws_manager
from app.models.entities import ServiceType

class CreateAppointmentRequest(BaseModel):
    branch_code: str
    lawyer_id: str
    client_name: str
    service_type: str
    date: str  # YYYY-MM-DD
    hour: int  # 9..16

@router.post("/appointments")
async def create_appointment_endpoint(
    req: CreateAppointmentRequest,
    db: Session = Depends(get_sync_db)
):
    branch = db.query(Branch).filter(Branch.code == req.branch_code).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Sede no encontrada")
    
    # Resolver abogado por UUID o por alias l1..l6
    lawyer = None
    try:
        import uuid
        lawyer_uuid = uuid.UUID(req.lawyer_id)
        lawyer = db.query(Lawyer).filter(Lawyer.id == lawyer_uuid).first()
    except Exception:
        pass

    if not lawyer:
        # Fallback a alias l1..l6 o priority
        branch_lawyers = db.query(Lawyer).filter(Lawyer.branch_id == branch.id).order_by(Lawyer.priority_order).all()
        if req.lawyer_id in ['l1', 'l4'] and len(branch_lawyers) >= 1:
            lawyer = branch_lawyers[0]
        elif req.lawyer_id in ['l2', 'l5'] and len(branch_lawyers) >= 2:
            lawyer = branch_lawyers[1]
        elif req.lawyer_id in ['l3', 'l6'] and len(branch_lawyers) >= 3:
            lawyer = branch_lawyers[2]
        else:
            lawyer = branch_lawyers[0] if branch_lawyers else None

    if not lawyer:
        raise HTTPException(status_code=404, detail="Abogado no encontrado")

    # Obtener o crear cliente
    client = db.query(Client).filter(Client.full_name == req.client_name).first()
    if not client:
        import uuid
        client = Client(
            telegram_id=f"web_{uuid.uuid4().hex[:8]}",
            full_name=req.client_name,
            language="es"
        )
        db.add(client)
        db.commit()
        db.refresh(client)

    # Determinar tipo de servicio del enum
    srv_type = ServiceType.ITIN
    st_lower = req.service_type.lower()
    if "asilo" in st_lower or "petición" in st_lower or "ajuste" in st_lower or "i-130" in st_lower or "i-485" in st_lower or "inmigr" in st_lower:
        srv_type = ServiceType.IMMIGRATION
    elif "notar" in st_lower or "traducc" in st_lower:
        srv_type = ServiceType.NOTARY

    # Fechas
    d_parts = [int(p) for p in req.date.split("-")]
    start_dt = datetime(d_parts[0], d_parts[1], d_parts[2], req.hour, 0, 0)
    end_dt = start_dt + timedelta(hours=1)

    appt = Appointment(
        branch_id=branch.id,
        lawyer_id=lawyer.id,
        client_id=client.id,
        service_type=srv_type,
        start_time=start_dt,
        end_time=end_dt,
        status=AppointmentStatus.SCHEDULED
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    event_payload = {
        "event": "APPOINTMENT_CREATED",
        "appointment": {
            "id": str(appt.id),
            "branch_code": branch.code,
            "lawyer_id": str(lawyer.id),
            "lawyer_name": lawyer.full_name,
            "client_name": client.full_name,
            "service_type": req.service_type,
            "date": req.date,
            "hour": req.hour,
            "status": "SCHEDULED"
        }
    }

    # Emitir por WebSocket a todos los dashboards conectados
    await ws_manager.broadcast(event_payload)

    return {"status": "success", "appointment": event_payload["appointment"]}

@router.patch("/appointments/{appointment_id}/cancel")
async def cancel_appointment_endpoint(
    appointment_id: str,
    db: Session = Depends(get_sync_db)
):
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    appt.status = AppointmentStatus.CANCELLED
    db.commit()
    db.refresh(appt)

    event_payload = {
        "event": "APPOINTMENT_CANCELLED",
        "appointment": {
            "id": str(appt.id),
            "status": "CANCELLED"
        }
    }
    await ws_manager.broadcast(event_payload)
    return {"status": "success", "appointment": event_payload["appointment"]}

