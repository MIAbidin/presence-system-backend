"""fase B - kelas matakuliah

Revision ID: c248e6e34f29
Revises: 3142b2fea76c
Create Date: 2026-05-02 20:31:54.759949

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c248e6e34f29'
down_revision: Union[str, Sequence[str], None] = '3142b2fea76c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Buat tabel kelas_matakuliah ─────────────────────
    op.create_table(
        "kelas_matakuliah",
 
        sa.Column("id",            sa.UUID(),              nullable=False),
        sa.Column("matakuliah_id", sa.UUID(),              nullable=False),
        sa.Column("kode_kelas",    sa.String(length=5),   nullable=False),
        sa.Column("dosen_id",      sa.UUID(),              nullable=True),
        sa.Column("ruangan_id",    sa.UUID(),              nullable=True),
        sa.Column("hari",          sa.String(length=10),  nullable=True),
        sa.Column("slot_mulai",    sa.SmallInteger(),      nullable=True),
        sa.Column("slot_selesai",  sa.SmallInteger(),      nullable=True),
        sa.Column("kode_akses",    sa.Text(),              nullable=True),
        sa.Column("izin_tamu",     sa.Boolean(),           nullable=False,
                  server_default=sa.text("FALSE")),
        sa.Column("is_active",     sa.Boolean(),           nullable=False,
                  server_default=sa.text("TRUE")),
        sa.Column("created_at",    sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at",    sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=True),
 
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["matakuliah_id"], ["matakuliah.id"],
            ondelete="CASCADE",
            name="fk_kelas_matakuliah_mk"
        ),
        sa.ForeignKeyConstraint(
            ["dosen_id"], ["users.id"],
            name="fk_kelas_matakuliah_dosen"
        ),
        sa.ForeignKeyConstraint(
            ["ruangan_id"], ["ruangan.id"],
            ondelete="SET NULL",
            name="fk_kelas_matakuliah_ruangan"
        ),
        sa.UniqueConstraint(
            "matakuliah_id", "kode_kelas",
            name="uq_kelas_matakuliah_mk_kode"
        ),
    )
 
    # Index untuk query cepat
    op.create_index("ix_kelas_matakuliah_mk",
                    "kelas_matakuliah", ["matakuliah_id"])
    op.create_index("ix_kelas_matakuliah_dosen",
                    "kelas_matakuliah", ["dosen_id"])
 
    # ── 2. Tambah kelas_id ke mahasiswa_matakuliah ─────────
    # nullable=True untuk backward compat — enrollment lama tetap valid
    op.add_column(
        "mahasiswa_matakuliah",
        sa.Column(
            "kelas_id",
            sa.UUID(),
            nullable=True,
            comment="FK ke kelas_matakuliah. NULL = enrollment lama (sebelum Fase B)"
        ),
    )
    op.create_foreign_key(
        "fk_mahasiswa_matakuliah_kelas",
        "mahasiswa_matakuliah", "kelas_matakuliah",
        ["kelas_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_mahasiswa_matakuliah_kelas_id",
        "mahasiswa_matakuliah", ["kelas_id"]
    )
 
    print("✓ Fase B upgrade selesai:")
    print("  - Tabel kelas_matakuliah dibuat")
    print("  - mahasiswa_matakuliah.kelas_id ditambahkan (nullable, backward compat)")
 
 
def downgrade() -> None:
    # Urutan: hapus FK dulu, baru kolom, baru tabel
    op.drop_index("ix_mahasiswa_matakuliah_kelas_id",
                  table_name="mahasiswa_matakuliah")
    op.drop_constraint("fk_mahasiswa_matakuliah_kelas",
                       "mahasiswa_matakuliah", type_="foreignkey")
    op.drop_column("mahasiswa_matakuliah", "kelas_id")
 
    op.drop_index("ix_kelas_matakuliah_dosen",
                  table_name="kelas_matakuliah")
    op.drop_index("ix_kelas_matakuliah_mk",
                  table_name="kelas_matakuliah")
    op.drop_table("kelas_matakuliah")
 
    print("✓ Fase B downgrade selesai")
 