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

    # Jadwal reguler
    hari          = Column(String(10),  nullable=True)   # 'Senin','Selasa',dst
    jam_mulai     = Column(Time,        nullable=True)   # '08:00'
    jam_selesai   = Column(Time,        nullable=True)   # '09:40'
    ruangan       = Column(String(50),  nullable=True)   # 'Lab A-301'

    # GPS ruang kelas (untuk geofencing mode offline)
    koordinat_lat = Column(Float,       nullable=True)
    koordinat_lng = Column(Float,       nullable=True)

    # ── BARU (Fase 1) ──────────────────────────────────────
    # Toggle: apakah mahasiswa dari kelas/matakuliah lain boleh
    # presensi di sesi ini TANPA perlu diizinkan manual oleh dosen.
    # TRUE  → siapapun yang punya wajah terdaftar bisa presensi
    # FALSE → hanya yang ada di daftar mahasiswa kelas ini (+ tamu manual)
    izin_tamu     = Column(Boolean, default=False, nullable=False)

    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    # Relasi ke jadwal pengganti (baru di Fase 1)
    jadwal_pengganti = relationship(
        "JadwalPengganti",
        back_populates="matakuliah",
        cascade="all, delete",
        order_by="JadwalPengganti.pertemuan_ke",
    )