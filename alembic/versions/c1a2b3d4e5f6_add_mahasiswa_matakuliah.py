"""add mahasiswa_matakuliah table and jadwal fields to matakuliah

Revision ID: c1a2b3d4e5f6
Revises: 47d78292e206
Create Date: 2026-04-25 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c1a2b3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '47d78292e206'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Tambah kolom jadwal ke tabel matakuliah ───────────
    op.add_column('matakuliah', sa.Column('hari',        sa.String(length=10), nullable=True))
    op.add_column('matakuliah', sa.Column('jam_mulai',   sa.Time(),            nullable=True))
    op.add_column('matakuliah', sa.Column('jam_selesai', sa.Time(),            nullable=True))
    op.add_column('matakuliah', sa.Column('ruangan',     sa.String(length=50), nullable=True))

    # ── Buat tabel relasi mahasiswa ↔ matakuliah ──────────
    op.create_table(
        'mahasiswa_matakuliah',
        sa.Column('id',            sa.UUID(),  nullable=False),
        sa.Column('mahasiswa_id',  sa.UUID(),  nullable=False),
        sa.Column('matakuliah_id', sa.UUID(),  nullable=False),
        sa.Column('created_at',    sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['mahasiswa_id'],  ['users.id'],       ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['matakuliah_id'], ['matakuliah.id'],  ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mahasiswa_id', 'matakuliah_id',
                            name='uq_mahasiswa_matakuliah'),
    )


def downgrade() -> None:
    op.drop_table('mahasiswa_matakuliah')
    op.drop_column('matakuliah', 'ruangan')
    op.drop_column('matakuliah', 'jam_selesai')
    op.drop_column('matakuliah', 'jam_mulai')
    op.drop_column('matakuliah', 'hari')
