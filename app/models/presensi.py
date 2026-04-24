import uuid
import enum
from sqlalchemy import Column, Float, Text, Enum, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.db import Base

class PresensiStatus(str, enum.Enum):
    hadir    = "hadir"
    terlambat = "terlambat"
    absen    = "absen"
    izin     = "izin"
    sakit    = "sakit"

class ModeKelas(str, enum.Enum):
    offline = "offline"
    online  = "online"

class Presensi(Base):
    __tablename__ = "presensi"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mahasiswa_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    sesi_id         = Column(UUID(as_uuid=True), ForeignKey("sesi_presensi.id"), nullable=False)
    status          = Column(Enum(PresensiStatus), nullable=False)
    waktu_presensi  = Column(DateTime(timezone=True), nullable=True)   # NULL = absen
    akurasi_wajah   = Column(Float, nullable=True)                     # skor 0–100
    mode_kelas      = Column(Enum(ModeKelas), nullable=False)
    latitude        = Column(Float, nullable=True)                     # GPS mode offline
    longitude       = Column(Float, nullable=True)
    catatan         = Column(Text, nullable=True)                      # keterangan manual dosen
    diubah_oleh     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    # Relasi
    mahasiswa   = relationship("User", foreign_keys=[mahasiswa_id])
    sesi        = relationship("SesiPresensi")
    pengubah    = relationship("User", foreign_keys=[diubah_oleh])