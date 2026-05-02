"""fase A - create ruangan table

Revision ID: 3142b2fea76c
Revises: 45f321d31646
Create Date: 2026-05-02 20:03:44.841655

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3142b2fea76c'
down_revision: Union[str, Sequence[str], None] = '45f321d31646'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Buat tabel ruangan."""
    op.create_table(
        'ruangan',
        sa.Column('id',            sa.UUID(),              nullable=False),
        sa.Column('kode',          sa.String(length=20),   nullable=False),
        sa.Column('nama',          sa.String(length=100),  nullable=False),
        sa.Column('tipe',          sa.String(length=30),   nullable=True),
        sa.Column('kapasitas',     sa.Integer(),           nullable=True),
        sa.Column('gedung',        sa.String(length=50),   nullable=True),
        sa.Column('lantai',        sa.Integer(),           nullable=True),
        sa.Column('koordinat_lat', sa.Float(),             nullable=True),
        sa.Column('koordinat_lng', sa.Float(),             nullable=True),
        sa.Column('keterangan',    sa.Text(),              nullable=True),
        sa.Column('is_active',     sa.Boolean(),           nullable=False,
                  server_default=sa.text('TRUE')),
        sa.Column('created_at',    sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at',    sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('kode', name='uq_ruangan_kode'),
    )
 
    # Index untuk pencarian cepat berdasarkan kode dan tipe
    op.create_index('ix_ruangan_kode',      'ruangan', ['kode'])
    op.create_index('ix_ruangan_tipe',      'ruangan', ['tipe'])
    op.create_index('ix_ruangan_is_active', 'ruangan', ['is_active'])
 
    print("✓ Fase A: Tabel ruangan berhasil dibuat")
    print("  Kolom: id, kode, nama, tipe, kapasitas, gedung, lantai,")
    print("         koordinat_lat, koordinat_lng, keterangan, is_active, created_at, updated_at")
    print("  Index: kode (unique), tipe, is_active")
 
 
def downgrade() -> None:
    """Hapus tabel ruangan."""
    op.drop_index('ix_ruangan_is_active', table_name='ruangan')
    op.drop_index('ix_ruangan_tipe',      table_name='ruangan')
    op.drop_index('ix_ruangan_kode',      table_name='ruangan')
    op.drop_table('ruangan')
    print("✓ Fase A downgrade: Tabel ruangan berhasil dihapus")