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
        print("Semillado completado con éxito: 2 sedes y 6 abogados activos.")
    except Exception as e:
        session.rollback()
        print(f"Error durante el semillado: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    seed_database()
