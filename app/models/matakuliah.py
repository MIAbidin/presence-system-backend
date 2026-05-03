import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, Time, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.db import Base


class Matakuliah(Base):
    __tablename__ = "matakuliah"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kode          = Column(String(20),  unique=True, nullable=False)
    nama          = Column(String(100), nullable=False)
    sks           = Column(Integer,     nullable=False)

    # Jadwal reguler (dipakai jika tidak ada kelas_matakuliah)
    hari          = Column(String(10),  nullable=True)
    jam_mulai     = Column(Time,        nullable=True)
    jam_selesai   = Column(Time,        nullable=True)
    ruangan       = Column(String(50),  nullable=True)

    # GPS ruang kelas (untuk geofencing mode offline)
    koordinat_lat = Column(Float,       nullable=True)
    koordinat_lng = Column(Float,       nullable=True)

    # ── Fase 1 ──────────────────────────────────────────────
    izin_tamu     = Column(Boolean, default=False, nullable=False)

    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    # Relasi ke jadwal pengganti
    jadwal_pengganti = relationship(
        "JadwalPengganti",
        back_populates="matakuliah",
        cascade="all, delete",
        order_by="JadwalPengganti.pertemuan_ke",
    )

    # ── Fase B: Relasi ke kelas_matakuliah ──────────────────
    kelas_list = relationship(
        "KelasMatakuliah",
        back_populates="matakuliah",
        cascade="all, delete",
        order_by="KelasMatakuliah.kode_kelas",
        foreign_keys="KelasMatakuliah.matakuliah_id",
    )