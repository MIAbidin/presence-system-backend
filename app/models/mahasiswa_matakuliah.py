import uuid
from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.db import Base


class MahasiswaMatakuliah(Base):
    """
    Tabel relasi mahasiswa ↔ matakuliah.
    Merepresentasikan "mahasiswa ini mengambil matakuliah ini semester ini".
    Tanpa tabel ini backend tidak tahu jadwal/matakuliah milik siapa.
    """
    __tablename__ = "mahasiswa_matakuliah"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mahasiswa_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    matakuliah_id  = Column(UUID(as_uuid=True), ForeignKey("matakuliah.id", ondelete="CASCADE"), nullable=False)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    # Satu mahasiswa tidak bisa mendaftar matakuliah yang sama 2x
    __table_args__ = (
        UniqueConstraint("mahasiswa_id", "matakuliah_id", name="uq_mahasiswa_matakuliah"),
    )

    mahasiswa  = relationship("User",        foreign_keys=[mahasiswa_id])
    matakuliah = relationship("Matakuliah",  foreign_keys=[matakuliah_id])
