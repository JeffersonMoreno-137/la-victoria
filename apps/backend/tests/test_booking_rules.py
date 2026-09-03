import pytest
from datetime import datetime, timedelta, date
import pytz
from app.services.booking_service import is_slot_valid_business_rules

EST = pytz.timezone("America/New_York")

def test_slot_minimum_24h_rule():
    now_est = EST.localize(datetime(2026, 9, 3, 10, 0, 0)) # Jueves 10:00 AM

    # Cita en 12 horas -> Inválida (menor a 24 horas)
    candidate_12h = now_est + timedelta(hours=12)
    assert is_slot_valid_business_rules(candidate_12h, now_est=now_est) is False

    # Cita en 23 horas y 59 minutos -> Inválida
    candidate_23h = now_est + timedelta(hours=23, minutes=59)
    assert is_slot_valid_business_rules(candidate_23h, now_est=now_est) is False

    # Cita en 25 horas exactas (Viernes 11:00 AM) -> Válida
    candidate_25h = now_est + timedelta(hours=25)
    assert is_slot_valid_business_rules(candidate_25h, now_est=now_est) is True

def test_slot_lunch_break_rule():
    now_est = EST.localize(datetime(2026, 9, 3, 8, 0, 0)) # Jueves 8:00 AM
    
    # Viernes a las 12:00 PM (Hora de almuerzo) -> Inválida
    lunch_candidate = EST.localize(datetime(2026, 9, 4, 12, 0, 0))
    assert is_slot_valid_business_rules(lunch_candidate, now_est=now_est) is False

    # Viernes a la 1:00 PM (13:00) -> Válida
    valid_after_lunch = EST.localize(datetime(2026, 9, 4, 13, 0, 0))
    assert is_slot_valid_business_rules(valid_after_lunch, now_est=now_est) is True

def test_slot_weekend_rules():
    now_est = EST.localize(datetime(2026, 9, 3, 8, 0, 0))

    # Sábado a las 10:00 AM -> Válido (9, 10, 11)
    sat_valid = EST.localize(datetime(2026, 9, 5, 10, 0, 0))
    assert is_slot_valid_business_rules(sat_valid, now_est=now_est) is True

    # Sábado a las 2:00 PM (14:00) -> Inválido
    sat_invalid = EST.localize(datetime(2026, 9, 5, 14, 0, 0))
    assert is_slot_valid_business_rules(sat_invalid, now_est=now_est) is False

    # Domingo a cualquier hora -> Inválido (Cerrado)
    sunday_candidate = EST.localize(datetime(2026, 9, 6, 10, 0, 0))
    assert is_slot_valid_business_rules(sunday_candidate, now_est=now_est) is False
