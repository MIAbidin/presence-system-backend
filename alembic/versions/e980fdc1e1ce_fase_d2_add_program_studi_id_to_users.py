"""fase D2 - add program_studi_id to users

Revision ID: e980fdc1e1ce
Revises: 0e9f578bfa03
Create Date: 2026-05-05 21:04:40.932398

Perubahan:
- Tambah kolom program_studi_id (UUID, FK ke program_studi.id, nullable)
  ke tabel users untuk relasi terstruktur.
- Field string program_studi TETAP ada untuk backward compatibility.
  Kedua field bisa diisi bersamaan; program_studi_id adalah sumber kebenaran
  jika tersedia.
 

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e980fdc1e1ce'
down_revision: Union[str, Sequence[str], None] = '0e9f578bfa03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

 

def upgrade() -> None:
    # Tambah kolom program_studi_id (nullable — backward compat)
    # Row lama tetap valid dengan nilai NULL di kolom ini.
    op.add_column(
        "users",
        sa.Column(
            "program_studi_id",
            sa.UUID(),
            nullable=True,
            comment=(
                "FK ke program_studi.id. NULL = enrollment lama "
                "sebelum Fase D atau prodi belum ada di tabel program_studi. "
                "Field string program_studi tetap dipertahankan untuk backward compat."
            ),
        ),
    )
 
    # Foreign key ke tabel program_studi
    op.create_foreign_key(
        "fk_users_program_studi_id",
        "users",
        "program_studi",
        ["program_studi_id"],
        ["id"],
        ondelete="SET NULL",   # jika prodi dihapus, set NULL (tidak hapus user)
    )
 
    # Index untuk query filter mahasiswa/dosen per prodi
    op.create_index(
        "ix_users_program_studi_id",
        "users",
        ["program_studi_id"],
    )
 
    print("✓ Fase D2 upgrade selesai:")
    print("  - users.program_studi_id ditambahkan (UUID, nullable, FK ke program_studi.id)")
    print("  - FK: ondelete SET NULL — prodi dihapus tidak hapus user")
    print("  - Index ix_users_program_studi_id dibuat")
    print("  - Field string users.program_studi TETAP ada (backward compat)")
 
 
def downgrade() -> None:
    """
    Rollback — jalankan dengan: alembic downgrade 0e9f578bfa03
    """
    op.drop_index("ix_users_program_studi_id", table_name="users")
    op.drop_constraint("fk_users_program_studi_id", "users", type_="foreignkey")
    op.drop_column("users", "program_studi_id")
 
    print("✓ Fase D2 downgrade selesai — users.program_studi_id dihapus")