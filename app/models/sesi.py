"""
app/models/sesi.py
══════════════════
Update Fase 2.3:
- batas_terlambat sekarang nullable (None = tidak ada batas terlambat)
  Sebelumnya: default="15 minutes" dan tidak bisa NULL
  Sekarang  : nullable=True, default=timedelta(minutes=15)
              kalau NULL → semua presensi selama sesi aktif = Hadir
"""

import uuid
import enum
from datetime import timedelta

from sqlalchemy import Column, String, Integer, Enum, DateTime, Interval, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.db import Base


class SesiMode(str, enum.Enum):
    offline = "offline"
    online  = "online"


class SesiStatus(str, enum.Enum):
    aktif   = "aktif"
    selesai = "selesai"


class SesiPresensi(Base):
    __tablename__ = "sesi_presensi"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    matakuliah_id   = Column(UUID(as_uuid=True), ForeignKey("matakuliah.id"), nullable=False)
    dosen_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"),      nullable=False)
    mode            = Column(Enum(SesiMode),   nullable=False)
    kode_sesi       = Column(String(6), unique=True, nullable=True)
    kode_expire_at  = Column(DateTime(timezone=True), nullable=True)
    pertemuan_ke    = Column(Integer, nullable=False)
    waktu_buka      = Column(DateTime(timezone=True), server_default=func.now())
    waktu_tutup     = Column(DateTime(timezone=True), nullable=True)

    # ── Fase 2.3: nullable=True ──────────────────────────────
    # None  → tidak ada batas terlambat (semua presensi saat sesi aktif = Hadir)
    # timedelta → batas menit sebelum dicatat Terlambat
    batas_terlambat = Column(
        Interval,
        nullable=True,                          # ← diubah dari default="15 minutes"
        default=timedelta(minutes=15),          # default Python-level (bukan DB-level)
    )

    status          = Column(Enum(SesiStatus), default=SesiStatus.aktif)

    # Relasi
    dosen       = relationship("User",       foreign_keys=[dosen_id])
    matakuliah  = relationship("Matakuliah")
    kode_usages = relationship("KodeUsage",  back_populates="sesi", cascade="all, delete")