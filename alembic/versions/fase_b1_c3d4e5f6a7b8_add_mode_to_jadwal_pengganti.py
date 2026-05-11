"""fase B1 - add mode column to jadwal_pengganti

Revision ID: fase_b1_c3d4e5f6a7b8
Revises: fase_e2_a2b3c4d5e6f7
Create Date: 2026-05-11 00:00:00.000000

Perubahan:
- ALTER TABLE jadwal_pengganti ADD COLUMN mode modekelas NULL
  (NULL = mode tidak berubah dari jadwal reguler kelas)

Catatan penting:
  Enum 'modekelas' sudah ada di PostgreSQL karena dipakai oleh tabel
  presensi (kolom mode_kelas) dan sesi_presensi (kolom mode).
  Kita TIDAK membuat enum baru — cukup referensikan yang sudah ada
  dengan create_type=False di SQLAlchemy dan MENGGUNAKAN TYPE modekelas
  langsung di SQL ALTER.

Cara rollback:
    alembic downgrade fase_e2_a2b3c4d5e6f7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "fase_b1_c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "fase_e2_a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Tambah kolom mode ke tabel jadwal_pengganti.

    Menggunakan tipe enum 'modekelas' yang sudah ada di database
    (dibuat saat migration create_presensi_table).

    Kolom dibuat nullable (NULL = mode tidak berubah dari jadwal reguler).
    """
    op.add_column(
        "jadwal_pengganti",
        sa.Column(
            "mode",
            # Gunakan sa.Enum dengan create_type=False karena enum 'modekelas'
            # sudah ada di PostgreSQL — jangan buat ulang agar tidak conflict.
            sa.Enum(
                "offline",
                "online",
                name="modekelas",
                create_type=False,
            ),
            nullable=True,
            comment=(
                "Mode pertemuan pengganti. "
                "NULL = tidak berubah dari mode reguler kelas. "
                "'offline' = ubah ke tatap muka. "
                "'online' = ubah ke online."
            ),
        ),
    )

    print("✓ Fase B-1 upgrade selesai:")
    print("  - jadwal_pengganti.mode ditambahkan (modekelas enum, nullable)")
    print("  - NULL = mode tidak berubah dari jadwal reguler kelas")
    print("  - 'offline' / 'online' = mode khusus pertemuan pengganti ini")
    print("  - Enum 'modekelas' sudah ada di DB, tidak dibuat ulang")


def downgrade() -> None:
    """
    Hapus kolom mode dari tabel jadwal_pengganti.

    Enum 'modekelas' TIDAK dihapus karena masih dipakai
    oleh tabel presensi dan sesi_presensi.
    """
    op.drop_column("jadwal_pengganti", "mode")

    print("✓ Fase B-1 downgrade selesai:")
    print("  - jadwal_pengganti.mode dihapus")
    print("  - Enum 'modekelas' tetap ada (masih dipakai tabel lain)")