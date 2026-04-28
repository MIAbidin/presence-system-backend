"""fase2 - batas_terlambat nullable di sesi_presensi

Revision ID: fase2_a1b2c3d4e5f6
Revises: fase1_d8e2f3a1b4c9
Create Date: 2026-04-28 10:00:00.000000

Perubahan:
- sesi_presensi.batas_terlambat → nullable=True
  (None = tidak ada batas terlambat, semua presensi selama sesi aktif = Hadir)

Cara rollback:
    alembic downgrade fase1_d8e2f3a1b4c9
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'fase2_a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'fase1_d8e2f3a1b4c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Ubah kolom batas_terlambat di sesi_presensi menjadi nullable.
    Row yang sudah ada (nilai '00:15:00') tidak terpengaruh — nilainya tetap.
    Row baru yang dikirim null → tidak ada batas terlambat.
    """
    # Hapus server_default dulu (kalau ada), baru ubah nullable
    op.alter_column(
        'sesi_presensi',
        'batas_terlambat',
        existing_type    = sa.Interval(),
        nullable         = True,       # ← dari NOT NULL ke nullable
        existing_nullable= False,
        existing_server_default=None,  # tidak ada server_default sebelumnya
    )

    print("✓ Fase 2: sesi_presensi.batas_terlambat sekarang nullable")
    print("  NULL  = tidak ada batas terlambat (semua presensi = Hadir)")
    print("  Value = batas menit sebelum dicatat Terlambat")


def downgrade() -> None:
    """
    Rollback: kembalikan batas_terlambat ke NOT NULL.
    PERINGATAN: row dengan batas_terlambat = NULL akan error!
    Jalankan UPDATE dulu sebelum downgrade:
      UPDATE sesi_presensi SET batas_terlambat = '15 minutes'
      WHERE batas_terlambat IS NULL;
    """
    # Update NULL ke 15 menit sebelum set NOT NULL
    op.execute(
        "UPDATE sesi_presensi "
        "SET batas_terlambat = interval '15 minutes' "
        "WHERE batas_terlambat IS NULL"
    )

    op.alter_column(
        'sesi_presensi',
        'batas_terlambat',
        existing_type    = sa.Interval(),
        nullable         = False,
        existing_nullable= True,
    )

    print("✓ Fase 2 downgrade: batas_terlambat kembali NOT NULL")