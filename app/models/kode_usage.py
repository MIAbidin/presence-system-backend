import uuid
from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.db import Base

class KodeUsage(Base):
    __tablename__ = "kode_usage"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sesi_id      = Column(UUID(as_uuid=True), ForeignKey("sesi_presensi.id", ondelete="CASCADE"), nullable=False)
    mahasiswa_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    used_at      = Column(DateTime(timezone=True), server_default=func.now())

    # Constraint: satu mahasiswa hanya bisa pakai kode satu sesi 1x
    __table_args__ = (
        UniqueConstraint("sesi_id", "mahasiswa_id", name="uq_kode_usage_sesi_mahasiswa"),
    )

    sesi      = relationship("SesiPresensi", back_populates="kode_usages")
    mahasiswa = relationship("User", foreign_keys=[mahasiswa_id])