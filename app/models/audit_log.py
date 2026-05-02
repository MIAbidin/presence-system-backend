"""app/models/audit_log.py — model tabel audit_log."""
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.db import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Contoh aksi: "CREATE_USER", "UPDATE_MATAKULIAH", "DELETE_MAHASISWA",
    #              "RESET_FACE", "RESET_PASSWORD", "TOGGLE_IZIN_TAMU",
    #              "IMPORT_MAHASISWA", "EXPORT_LAPORAN"
    aksi       = Column(String(100), nullable=False)

    # Entitas yang dioperasikan: "user", "matakuliah", "enrollment", dll
    entitas    = Column(String(50),  nullable=True)

    # UUID atau identifier entitas (bisa berisi nim/nidn juga)
    entitas_id = Column(String(100), nullable=True)

    # Detail dalam format JSON string atau plain text
    detail     = Column(Text, nullable=True)

    # IP address pengirim request
    ip_address = Column(String(45), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relasi
    admin = relationship("User", foreign_keys=[admin_id])