import uuid
from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint, Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.db import Base


class MahasiswaMatakuliah(Base):
    """
    Tabel relasi mahasiswa ↔ matakuliah.

    Kolom Fase 1:
    - is_tamu   : True jika mahasiswa ini dari kelas lain yang diizinkan
    - kelas_asal: Label kelas asalnya, mis. "IF302 - Kelas B"

    Kolom Fase B:
    - kelas_id  : FK ke kelas_matakuliah (nullable untuk backward compat).
                  NULL = enrollment lama sebelum Fase B,
                  filled = enrollment baru per kelas spesifik.
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

    # ── Fase 1 ─────────────────────────────────────────────
    is_tamu    = Column(Boolean, default=False, nullable=False)
    kelas_asal = Column(String(100), nullable=True)

    # ── Fase B: FK ke kelas_matakuliah (nullable, backward compat) ──
    # NULL = enrollment lama (sebelum multi-kelas)
    # filled = enrollment baru per kelas spesifik
    kelas_id   = Column(
        UUID(as_uuid=True),
        ForeignKey("kelas_matakuliah.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Satu mahasiswa tidak bisa mendaftar matakuliah yang sama 2x
    __table_args__ = (
        UniqueConstraint(
            "mahasiswa_id", "matakuliah_id",
            name="uq_mahasiswa_matakuliah"
        ),
    )

    mahasiswa  = relationship("User",              foreign_keys=[mahasiswa_id])
    matakuliah = relationship("Matakuliah",        foreign_keys=[matakuliah_id])

    # ── Fase B: relasi ke kelas ──────────────────────────────
    kelas      = relationship(
        "KelasMatakuliah",
        back_populates="mahasiswa",
        foreign_keys=[kelas_id],
    )