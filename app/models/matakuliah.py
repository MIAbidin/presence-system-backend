import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database.db import Base

class Matakuliah(Base):
    __tablename__ = "matakuliah"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kode          = Column(String(20), unique=True, nullable=False)
    nama          = Column(String(100), nullable=False)
    sks           = Column(Integer, nullable=False)
    koordinat_lat = Column(Float, nullable=True)   # koordinat GPS ruang kelas
    koordinat_lng = Column(Float, nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())