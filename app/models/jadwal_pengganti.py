import uuid
from sqlalchemy import (
    Column, String, Integer, DateTime, Time,
    ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.db import Base


class JadwalPengganti(Base):
    """
    Jadwal pengganti / khusus untuk satu pertemuan tertentu.

    Tidak menimpa jadwal resmi di tabel matakuliah (yang diset admin).
    Hanya jadi "override" untuk pertemuan_ke tertentu.

    Contoh use case:
    - Pertemuan 5 dipindah dari Lab A-301 ke Ruang C-202
    - Pertemuan 8 dimajukan dari 08:00 jadi 10:00 karena ruang bentrok
    - Pertemuan 12 diganti ke mode Online karena cuaca buruk

    Update Fase B-1:
    - Tambah kolom `mode` (offline | online | null)
      null  = mode tidak berubah dari jadwal reguler kelas
      diisi = mode khusus untuk pertemuan ini (override)

    UNIQUE constraint: satu matakuliah + satu pertemuan = satu jadwal pengganti.
    Kalau dosen simpan ulang, UPDATE bukan INSERT baru.
    """
    __tablename__ = "jadwal_pengganti"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    matakuliah_id  = Column(
        UUID(as_uuid=True),
        ForeignKey("matakuliah.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    dosen_id       = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )

    # Pertemuan ke berapa yang diganti (1–16)
    pertemuan_ke   = Column(Integer, nullable=False)

    # Jam baru — nullable karena mungkin hanya ruangan/mode yang ganti
    jam_mulai_baru   = Column(Time, nullable=True)
    jam_selesai_baru = Column(Time, nullable=True)

    # Ruangan baru — nullable kalau tidak ganti ruangan
    ruangan_baru   = Column(String(50), nullable=True)

    # ── Fase B-1: Mode pertemuan pengganti ──────────────────────
    # nullable=True  → None berarti mode tidak berubah dari jadwal reguler
    # 'offline'      → pertemuan ini berubah ke tatap muka
    # 'online'       → pertemuan ini berubah ke online
    #
    # Gunakan create_type=False karena enum 'modekelas' sudah ada di DB
    # (dibuat saat migration tabel presensi / sesi_presensi).
    mode = Column(
        SAEnum(
            "offline", "online",
            name="modekelas",
            create_type=False,   # ← PENTING: enum sudah ada, jangan buat ulang
        ),
        nullable=True,
        default=None,
        comment=(
            "Mode pertemuan pengganti. "
            "NULL = tidak berubah dari mode reguler kelas. "
            "'offline' = ubah ke tatap muka. "
            "'online'  = ubah ke online."
        ),
    )

    # Keterangan tambahan dosen, mis. "Pindah karena ruang dipakai seminar"
    keterangan     = Column(Text, nullable=True)

    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relasi
    matakuliah = relationship("Matakuliah", back_populates="jadwal_pengganti")
    dosen      = relationship("User", foreign_keys=[dosen_id])

    # UNIQUE: satu matakuliah hanya boleh punya 1 jadwal pengganti per pertemuan
    from sqlalchemy import UniqueConstraint
    __table_args__ = (
        UniqueConstraint(
            "matakuliah_id", "pertemuan_ke",
            name="uq_jadwal_pengganti_mk_pertemuan"
        ),
    )