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
            "branch_code": branch.code,
            "branch_name": branch.name,
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
        lawyers = db.query(Lawyer).filter(Lawyer.branch_id == b.id, Lawyer.is_active == True).all()
        results.append({
            "id": str(b.id),
            "code": b.code,
            "name": b.name,
            "address": b.address,
            "lawyers": [{"id": str(l.id), "name": l.full_name, "priority": l.priority_order} for l in lawyers]
        })
    return results
