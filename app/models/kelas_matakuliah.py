"""
app/models/kelas_matakuliah.py
═══════════════════════════════
Fase B — Model tabel kelas_matakuliah.

Satu matakuliah bisa punya banyak kelas (A, B, C, X, dll).
Setiap kelas punya dosen, ruangan, hari, dan slot waktu sendiri.
Slot 1–12 dipetakan ke jam nyata via slot_utils.py.
"""
import uuid
from sqlalchemy import (
    Column, String, SmallInteger, Boolean, Text,
    ForeignKey, UniqueConstraint, DateTime
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.db import Base


class KelasMatakuliah(Base):
    """
    Tabel kelas per matakuliah.

    Contoh penggunaan nyata:
    - TIF3221308 Logika & Himpunan → Kelas A, B, C, D, X
    - Setiap kelas bisa dosen & ruangan berbeda

    kode_kelas : 'A', 'B', 'C', 'D', 'X'
    slot_mulai : 1–12 (dipetakan ke jam via SLOT_MAPPING di slot_utils.py)
    slot_selesai: 1–12
    kode_akses : URL Google Classroom / kode WA / dll
    """
    __tablename__ = "kelas_matakuliah"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    matakuliah_id  = Column(
        UUID(as_uuid=True),
        ForeignKey("matakuliah.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kode_kelas     = Column(String(5), nullable=False)   # 'A', 'B', 'X', dll
    dosen_id       = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    ruangan_id     = Column(
        UUID(as_uuid=True),
        ForeignKey("ruangan.id"),
        nullable=True,
    )

    hari           = Column(String(10), nullable=True)   # 'Senin', 'Selasa', dst
    slot_mulai     = Column(SmallInteger, nullable=True) # 1–12
    slot_selesai   = Column(SmallInteger, nullable=True) # 1–12

    # URL akses kelas: Google Classroom, link WA, dll
    kode_akses     = Column(Text, nullable=True)

    # Toggle izin tamu per kelas (override izin_tamu di matakuliah)
    izin_tamu      = Column(Boolean, default=False, nullable=False)
    is_active      = Column(Boolean, default=True,  nullable=False)

    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Satu matakuliah tidak boleh punya kode_kelas yang sama dua kali
    __table_args__ = (
        UniqueConstraint(
            "matakuliah_id", "kode_kelas",
            name="uq_kelas_matakuliah_mk_kode",
        ),
    )

    # Relasi
    matakuliah = relationship("Matakuliah",    foreign_keys=[matakuliah_id],
                               back_populates="kelas_list")
    dosen      = relationship("User",          foreign_keys=[dosen_id])
    ruangan    = relationship("Ruangan",       foreign_keys=[ruangan_id])
    mahasiswa  = relationship("MahasiswaMatakuliah",
                               back_populates="kelas",
                               foreign_keys="MahasiswaMatakuliah.kelas_id")