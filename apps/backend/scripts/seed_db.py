import os
import sys
import uuid
from datetime import datetime

# Asegurar que apps/backend está en el PYTHONPATH
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import text
from app.db.session import sync_engine, SyncSessionLocal, Base
from app.models.entities import Branch, Lawyer, BranchCode

def seed_database():
    print("Iniciando semillado de base de datos La Victoria...")

    # Activar extensiones en PostgreSQL
    with sync_engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        conn.commit()

    # Crear tablas si no existen
    Base.metadata.create_all(bind=sync_engine)

    session = SyncSessionLocal()
    try:
        # Verificar si las sedes ya existen
        queens = session.query(Branch).filter_by(code=BranchCode.NY_QUEENS.value).first()
        if not queens:
            queens = Branch(
                id=uuid.uuid4(),
                code=BranchCode.NY_QUEENS.value,
                name="Sede Queens, NY",
                address="37-53 90th Street, Queens, NY 11372",
                timezone="America/New_York"
            )
            session.add(queens)
            session.flush()
            print("Sede Queens creada exitosamente.")

            # Crear 3 abogados para Queens (First Available L1 -> L2 -> L3)
            lawyers_queens = [
                Lawyer(
                    id=uuid.uuid4(),
                    branch_id=queens.id,
                    full_name="Abg. Carlos Mendoza",
                    email="cmendoza@lavictoriafoundation.org",
                    priority_order=1,
                    is_active=True
                ),
                Lawyer(
                    id=uuid.uuid4(),
                    branch_id=queens.id,
                    full_name="Abg. Sofia Ramirez",
                    email="sramirez@lavictoriafoundation.org",
                    priority_order=2,
                    is_active=True
                ),
                Lawyer(
                    id=uuid.uuid4(),
                    branch_id=queens.id,
                    full_name="Abg. Michael Chen",
                    email="mchen@lavictoriafoundation.org",
                    priority_order=3,
                    is_active=True
                )
            ]
            session.add_all(lawyers_queens)
            print("3 Abogados asignados para Queens (L1, L2, L3).")

        dallas = session.query(Branch).filter_by(code=BranchCode.TX_DALLAS.value).first()
        if not dallas:
            dallas = Branch(
                id=uuid.uuid4(),
                code=BranchCode.TX_DALLAS.value,
                name="Sede Dallas, TX",
                address="17762 Preston Rd, Ste 200, Dallas, TX 75252",
                timezone="America/New_York"
            )
            session.add(dallas)
            session.flush()
            print("Sede Dallas creada exitosamente.")

            # Crear 3 abogados para Dallas (First Available L1 -> L2 -> L3)
            lawyers_dallas = [
                Lawyer(
                    id=uuid.uuid4(),
                    branch_id=dallas.id,
                    full_name="Abg. Elena Morales",
                    email="emorales@lavictoriafoundation.org",
                    priority_order=1,
                    is_active=True
                ),
                Lawyer(
                    id=uuid.uuid4(),
                    branch_id=dallas.id,
                    full_name="Abg. David Hernandez",
                    email="dhernandez@lavictoriafoundation.org",
                    priority_order=2,
                    is_active=True
                ),
                Lawyer(
                    id=uuid.uuid4(),
                    branch_id=dallas.id,
                    full_name="Abg. Laura Vasquez",
                    email="lvasquez@lavictoriafoundation.org",
                    priority_order=3,
                    is_active=True
                )
            ]
            session.add_all(lawyers_dallas)
            print("3 Abogados asignados para Dallas (L1, L2, L3).")

        session.commit()

        # Semillar Citas de Demostración para 3 de Septiembre 2026 si no existen
        from app.models.entities import Client, Appointment, ServiceType, AppointmentStatus, Language
        
        sample_client_1 = session.query(Client).filter_by(telegram_id="tg_1001").first()
        if not sample_client_1:
            sample_client_1 = Client(id=uuid.uuid4(), telegram_id="tg_1001", full_name="Carlos Mendoza", phone="+17185550101", language=Language.ES)
            sample_client_2 = Client(id=uuid.uuid4(), telegram_id="tg_1002", full_name="Maria Gomez", phone="+17185550102", language=Language.ES)
            sample_client_3 = Client(id=uuid.uuid4(), telegram_id="tg_1003", full_name="Juan Diaz", phone="+17185550103", language=Language.ES)
            sample_client_4 = Client(id=uuid.uuid4(), telegram_id="tg_1004", full_name="Elena Perez", phone="+17185550104", language=Language.ES)
            sample_client_5 = Client(id=uuid.uuid4(), telegram_id="tg_1005", full_name="Roberto Soto", phone="+17185550105", language=Language.ES)
            session.add_all([sample_client_1, sample_client_2, sample_client_3, sample_client_4, sample_client_5])
            session.flush()

            # Obtener abogados de Queens
            queens_lawyers = session.query(Lawyer).filter_by(branch_id=queens.id).order_by(Lawyer.priority_order).all()
            l1 = queens_lawyers[0]
            l2 = queens_lawyers[1]
            l3 = queens_lawyers[2]

            appointments_seed = [
                Appointment(
                    id=uuid.uuid4(),
                    branch_id=queens.id,
                    lawyer_id=l1.id,
                    client_id=sample_client_1.id,
                    service_type=ServiceType.ITIN,
                    start_time=datetime(2026, 9, 3, 9, 0, 0),
                    end_time=datetime(2026, 9, 3, 10, 0, 0),
                    status=AppointmentStatus.SCHEDULED,
                    notes="Trámite inicial Form W-7"
                ),
                Appointment(
                    id=uuid.uuid4(),
                    branch_id=queens.id,
                    lawyer_id=l2.id,
                    client_id=sample_client_2.id,
                    service_type=ServiceType.IMMIGRATION,
                    start_time=datetime(2026, 9, 3, 10, 0, 0),
                    end_time=datetime(2026, 9, 3, 11, 0, 0),
                    status=AppointmentStatus.SCHEDULED,
                    notes="Entrevista preparatoria de Asilo"
                ),
                Appointment(
                    id=uuid.uuid4(),
                    branch_id=queens.id,
                    lawyer_id=l3.id,
                    client_id=sample_client_3.id,
                    service_type=ServiceType.IMMIGRATION,
                    start_time=datetime(2026, 9, 3, 11, 0, 0),
                    end_time=datetime(2026, 9, 3, 12, 0, 0),
                    status=AppointmentStatus.SCHEDULED,
                    notes="Petición Familiar cónyuge ciudadano"
                ),
                Appointment(
                    id=uuid.uuid4(),
                    branch_id=queens.id,
                    lawyer_id=l1.id,
                    client_id=sample_client_4.id,
                    service_type=ServiceType.NOTARY,
                    start_time=datetime(2026, 9, 3, 14, 0, 0),
                    end_time=datetime(2026, 9, 3, 15, 0, 0),
                    status=AppointmentStatus.SCHEDULED,
                    notes="Certificación notarial y apostilla"
                ),
                Appointment(
                    id=uuid.uuid4(),
                    branch_id=queens.id,
                    lawyer_id=l2.id,
                    client_id=sample_client_5.id,
                    service_type=ServiceType.IMMIGRATION,
                    start_time=datetime(2026, 9, 3, 15, 0, 0),
                    end_time=datetime(2026, 9, 3, 16, 0, 0),
                    status=AppointmentStatus.SCHEDULED,
                    notes="Ajuste de estatus con permiso de trabajo"
                )
            ]
            session.add_all(appointments_seed)
            session.commit()
            print("5 Citas para el 3 de Septiembre 2026 guardadas en la base de datos PostgreSQL.")

        print("Semillado completado con éxito: 2 sedes, 6 abogados y citas activas.")
    except Exception as e:
        session.rollback()
        print(f"Error durante el semillado: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    seed_database()
