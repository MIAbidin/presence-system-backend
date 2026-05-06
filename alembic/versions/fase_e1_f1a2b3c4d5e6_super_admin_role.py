"""fase E1 - tambah nilai super_admin ke enum userrole

Revision ID: fase_e1_f1a2b3c4d5e6
Revises: e980fdc1e1ce
Create Date: 2026-05-06 10:00:00.000000

Perubahan:
- ALTER TYPE userrole ADD VALUE 'super_admin'
  (PostgreSQL ENUM tidak bisa di-rollback — lihat catatan downgrade)

Cara rollback:
    PERINGATAN: PostgreSQL tidak mendukung DROP VALUE dari ENUM.
    Untuk rollback sejati, perlu recreate enum dan update semua kolom.
    Lihat fungsi downgrade() di bawah untuk prosedur manual.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "fase_e1_f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e980fdc1e1ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Tambah nilai 'super_admin' ke PostgreSQL ENUM userrole.

    IF NOT EXISTS memastikan idempoten — aman dijalankan ulang
    jika migration pernah gagal di tengah jalan.
    """
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'super_admin'")

    print("✓ Fase E1 upgrade selesai:")
    print("  - userrole ENUM: tambah nilai 'super_admin'")
    print("  CATATAN: Perubahan ini TIDAK bisa di-rollback di PostgreSQL.")
    print("  Nilai 'super_admin' akan tetap ada meski downgrade dijalankan.")


def downgrade() -> None:
    """
    PERINGATAN: PostgreSQL tidak mendukung DROP VALUE dari ENUM natively.

    Untuk rollback sejati, jalankan prosedur manual berikut di psql:

        -- 1. Pastikan tidak ada user dengan role super_admin
        UPDATE users SET role = 'admin' WHERE role = 'super_admin';

        -- 2. Buat enum baru tanpa super_admin
        CREATE TYPE userrole_new AS ENUM ('mahasiswa', 'dosen', 'admin');

        -- 3. Update kolom pakai cast
        ALTER TABLE users
            ALTER COLUMN role TYPE userrole_new
            USING role::text::userrole_new;

        -- 4. Hapus enum lama, rename enum baru
        DROP TYPE userrole;
        ALTER TYPE userrole_new RENAME TO userrole;

    Migration ini TIDAK menjalankan prosedur di atas secara otomatis
    karena berisiko kehilangan data jika ada user dengan role super_admin.
    """
    print("⚠️  Fase E1 downgrade: Nilai 'super_admin' TIDAK dihapus dari ENUM.")
    print("    PostgreSQL tidak mendukung DROP VALUE dari ENUM.")
    print("    Jalankan prosedur manual di docstring fungsi downgrade() jika diperlukan.")