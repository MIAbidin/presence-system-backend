"""
app/models/program_studi.py
════════════════════════════
Fase D — Tabel program_studi
"""
import uuid
import enum

from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database.db import Base


class JenjangEnum(str, enum.Enum):
    D3 = "D3"
    D4 = "D4"
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"


class ProgramStudi(Base):
    __tablename__ = "program_studi"

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kode     = Column(String(10),  unique=True, nullable=False)   # 'TIF', 'SI', 'IK'
    nama     = Column(String(100), nullable=False)                # 'Teknik Informatika'
    fakultas = Column(String(100), nullable=True)                 # 'Fakultas Komunikasi dan Informatika'
    jenjang  = Column(String(5),   nullable=True)                 # 'S1', 'D3', 'D4', 'S2', 'S3'
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())