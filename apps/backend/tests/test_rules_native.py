import sys
import os
from datetime import datetime, timedelta, date, time
import unittest

# Asegurar que apps/backend está en el PYTHONPATH
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Mock simple de zona horaria si no está pytz instalado aún en el sistema base
from datetime import tzinfo

class SimpleEST(tzinfo):
    def utcoffset(self, dt):
        return timedelta(hours=-5)
    def tzname(self, dt):
        return "EST"
    def dst(self, dt):
        return timedelta(0)

WEEKDAY_SLOT_HOURS = [9, 10, 11, 13, 14, 15, 16]
SATURDAY_SLOT_HOURS = [9, 10, 11]

def is_slot_valid_business_rules(candidate_start: datetime, now_est: datetime) -> bool:
    # 1. Regla +24 horas exactas
    if candidate_start < now_est + timedelta(hours=24):
        return False

    weekday = candidate_start.weekday() # 0 = Lunes, 5 = Sábado, 6 = Domingo
    hour = candidate_start.hour

    # 2. Bloqueo de almuerzo (12:00 PM a 1:00 PM)
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

class TestBookingBusinessRules(unittest.TestCase):

    def setUp(self):
        self.tz = SimpleEST()
        # Jueves 3 de Septiembre 10:00 AM
        self.now_est = datetime(2026, 9, 3, 10, 0, 0, tzinfo=self.tz)

    def test_minimum_24h_rejection(self):
        # Cita en 12h
        slot_12h = self.now_est + timedelta(hours=12)
        self.assertFalse(is_slot_valid_business_rules(slot_12h, self.now_est))

        # Cita en 23h 59m
        slot_almost_24h = self.now_est + timedelta(hours=23, minutes=59)
        self.assertFalse(is_slot_valid_business_rules(slot_almost_24h, self.now_est))

    def test_minimum_24h_acceptance(self):
        # Cita en 25 horas exactas (Viernes 11:00 AM)
        slot_25h = self.now_est + timedelta(hours=25)
        self.assertTrue(is_slot_valid_business_rules(slot_25h, self.now_est))

    def test_lunch_break_rejection(self):
        # Viernes 12:00 PM (hora de almuerzo inhabilitada)
        lunch_slot = datetime(2026, 9, 4, 12, 0, 0, tzinfo=self.tz)
        self.assertFalse(is_slot_valid_business_rules(lunch_slot, self.now_est))

        # Viernes 1:00 PM (13:00) válido tras almuerzo
        post_lunch_slot = datetime(2026, 9, 4, 13, 0, 0, tzinfo=self.tz)
        self.assertTrue(is_slot_valid_business_rules(post_lunch_slot, self.now_est))

    def test_weekend_rules(self):
        # Sábado 10:00 AM -> Válido
        sat_valid = datetime(2026, 9, 5, 10, 0, 0, tzinfo=self.tz)
        self.assertTrue(is_slot_valid_business_rules(sat_valid, self.now_est))

        # Sábado 2:00 PM (14:00) -> Inválido
        sat_invalid = datetime(2026, 9, 5, 14, 0, 0, tzinfo=self.tz)
        self.assertFalse(is_slot_valid_business_rules(sat_invalid, self.now_est))

        # Domingo -> Cerrado
        sunday_slot = datetime(2026, 9, 6, 10, 0, 0, tzinfo=self.tz)
        self.assertFalse(is_slot_valid_business_rules(sunday_slot, self.now_est))

if __name__ == "__main__":
    unittest.main()
