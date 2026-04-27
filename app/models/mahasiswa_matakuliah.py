import uuid
from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint, Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.db import Base


class MahasiswaMatakuliah(Base):
    """
    Tabel relasi mahasiswa ↔ matakuliah.

    Kolom baru (Fase 1):
    - is_tamu   : True jika mahasiswa ini dari kelas lain yang diizinkan
    - kelas_asal: Label kelas asalnya, mis. "IF302 - Kelas B"
                  Diisi otomatis dari matakuliah resmi mahasiswa,
                  atau diisi manual saat dosen tambah tamu.

    Aturan:
    - Satu mahasiswa tidak bisa terdaftar DUA KALI di matakuliah yang sama
      (constraint UNIQUE tetap berlaku).
    - Mahasiswa asli kelas: is_tamu=False, kelas_asal=None
    - Mahasiswa tamu manual: is_tamu=True, kelas_asal="IF302 - Kelas B"
    - Mahasiswa tamu otomatis (izin_tamu=True): is_tamu=True, kelas_asal diisi sistem
    """
    __tablename__ = "mahasiswa_matakuliah"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mahasiswa_id   = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    matakuliah_id  = Column(
        UUID(as_uuid=True),
        ForeignKey("matakuliah.id", ondelete="CASCADE"),
        nullable=False
    )

    # ── BARU (Fase 1) ──────────────────────────────────────
    is_tamu    = Column(Boolean, default=False, nullable=False)
    # Contoh isi: "IF302 - Kelas B" atau "SI201 - Kelas A"
    # NULL jika mahasiswa asli kelas ini
    kelas_asal = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Satu mahasiswa tidak bisa mendaftar matakuliah yang sama 2x
    __table_args__ = (
        UniqueConstraint(
            "mahasiswa_id", "matakuliah_id",
            name="uq_mahasiswa_matakuliah"
        ),
    )

    mahasiswa  = relationship("User",        foreign_keys=[mahasiswa_id])
    matakuliah = relationship("Matakuliah",  foreign_keys=[matakuliah_id])