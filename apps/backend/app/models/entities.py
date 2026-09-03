import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Integer, Boolean, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.db.session import Base

class BranchCode(str, Enum):
    NY_QUEENS = "NY_QUEENS"
    TX_DALLAS = "TX_DALLAS"

class ServiceType(str, Enum):
    ITIN = "ITIN"
    IMMIGRATION = "IMMIGRATION"
    NOTARY = "NOTARY"

class AppointmentStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    RESCHEDULED = "RESCHEDULED"

class Language(str, Enum):
    ES = "es"
    EN = "en"

class Branch(Base):
    __tablename__ = "branches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True) # NY_QUEENS, TX_DALLAS
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    timezone = Column(String(50), default="America/New_York", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    lawyers = relationship("Lawyer", back_populates="branch", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="branch")

class Lawyer(Base):
    __tablename__ = "lawyers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    priority_order = Column(Integer, nullable=False, default=1) # 1 for L1, 2 for L2, 3 for L3 (First Available algorithm)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    branch = relationship("Branch", back_populates="lawyers")
    appointments = relationship("Appointment", back_populates="lawyer")

class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_id = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(150), nullable=True)
    phone = Column(String(50), nullable=True)
    language = Column(SQLEnum(Language), default=Language.ES, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    appointments = relationship("Appointment", back_populates="client")

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False, index=True)
    lawyer_id = Column(UUID(as_uuid=True), ForeignKey("lawyers.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    service_type = Column(SQLEnum(ServiceType), nullable=False)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    status = Column(SQLEnum(AppointmentStatus), default=AppointmentStatus.SCHEDULED, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    branch = relationship("Branch", back_populates="appointments")
    lawyer = relationship("Lawyer", back_populates="appointments")
    client = relationship("Client", back_populates="appointments")

class FAQDocument(Base):
    __tablename__ = "faq_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    source_file = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False) # ITIN, IMMIGRATION, GENERAL
    language = Column(SQLEnum(Language), default=Language.ES, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True) # text-embedding-3-small dimension
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
