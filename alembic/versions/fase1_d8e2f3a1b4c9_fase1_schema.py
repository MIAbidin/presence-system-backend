"""fase 1 - tambah izin_tamu di matakuliah, is_tamu+kelas_asal di mahasiswa_matakuliah, tabel jadwal_pengganti

Revision ID: fase1_d8e2f3a1b4c9
Revises: c1a2b3d4e5f6
Create Date: 2026-04-27 10:00:00.000000

Perubahan:
1. Tabel matakuliah          → tambah kolom izin_tamu (BOOLEAN, default FALSE)
2. Tabel mahasiswa_matakuliah → tambah kolom is_tamu (BOOLEAN), kelas_asal (VARCHAR)
3. Tabel jadwal_pengganti    → CREATE TABLE baru

Cara rollback:
    alembic downgrade c1a2b3d4e5f6
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# ─── Revision identifiers ─────────────────────────────────────
revision: str = 'fase1_d8e2f3a1b4c9'
down_revision: Union[str, Sequence[str], None] = 'c1a2b3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ─── UPGRADE ──────────────────────────────────────────────────

def upgrade() -> None:
    """
    Upgrade schema — jalankan dengan: alembic upgrade head
    """

    # ── 1. Tambah kolom izin_tamu ke tabel matakuliah ────────
    # Default FALSE artinya sistem tertutup by default.
    # Dosen harus aktifkan manual per matakuliah.
    op.add_column(
        'matakuliah',
        sa.Column(
            'izin_tamu',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('FALSE'),   # aman untuk row existing
            comment='Jika TRUE, mahasiswa kelas lain bisa presensi tanpa izin manual'
        )
    )

    # ── 2. Tambah kolom is_tamu ke tabel mahasiswa_matakuliah ─
    op.add_column(
        'mahasiswa_matakuliah',
        sa.Column(
            'is_tamu',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('FALSE'),   # semua row existing = bukan tamu
            comment='TRUE jika mahasiswa ini berasal dari kelas/matakuliah lain'
        )
    )

    # ── 3. Tambah kolom kelas_asal ke tabel mahasiswa_matakuliah
    op.add_column(
        'mahasiswa_matakuliah',
        sa.Column(
            'kelas_asal',
            sa.String(length=100),
            nullable=True,                     # NULL untuk mahasiswa asli kelas
            comment='Contoh: IF302 - Kelas B. Diisi otomatis atau manual oleh dosen'
        )
    )

    # ── 4. Buat tabel jadwal_pengganti ────────────────────────
    op.create_table(
        'jadwal_pengganti',

        sa.Column('id',            sa.UUID(),             nullable=False),
        sa.Column('matakuliah_id', sa.UUID(),             nullable=False),
        sa.Column('dosen_id',      sa.UUID(),             nullable=False),
        sa.Column('pertemuan_ke',  sa.Integer(),          nullable=False),
        sa.Column('jam_mulai_baru',   sa.Time(),          nullable=True),
        sa.Column('jam_selesai_baru', sa.Time(),          nullable=True),
        sa.Column('ruangan_baru',  sa.String(length=50),  nullable=True),
        sa.Column('keterangan',    sa.Text(),             nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=True
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=True
        ),

        # Primary key
        sa.PrimaryKeyConstraint('id'),

        # Foreign keys
        sa.ForeignKeyConstraint(
            ['matakuliah_id'], ['matakuliah.id'],
            ondelete='CASCADE',
            name='fk_jadwal_pengganti_matakuliah'
        ),
        sa.ForeignKeyConstraint(
            ['dosen_id'], ['users.id'],
            name='fk_jadwal_pengganti_dosen'
        ),

        # Constraint unik: 1 matakuliah hanya boleh 1 jadwal pengganti per pertemuan
        sa.UniqueConstraint(
            'matakuliah_id', 'pertemuan_ke',
            name='uq_jadwal_pengganti_mk_pertemuan'
        ),
    )

    # ── 5. Index untuk query cepat ────────────────────────────
    # Sistem sering query "jadwal pengganti matakuliah X pertemuan Y"
    op.create_index(
        'ix_jadwal_pengganti_matakuliah_pertemuan',
        'jadwal_pengganti',
        ['matakuliah_id', 'pertemuan_ke']
    )

    # Index untuk filter mahasiswa tamu di list
    op.create_index(
        'ix_mahasiswa_matakuliah_is_tamu',
        'mahasiswa_matakuliah',
        ['matakuliah_id', 'is_tamu']
    )

    print("✓ Fase 1 upgrade selesai:")
    print("  - matakuliah.izin_tamu       ditambahkan (default FALSE)")
    print("  - mahasiswa_matakuliah.is_tamu    ditambahkan (default FALSE)")
    print("  - mahasiswa_matakuliah.kelas_asal ditambahkan (nullable)")
    print("  - tabel jadwal_pengganti     dibuat")
    print("  - 2 index baru               dibuat")


# ─── DOWNGRADE ────────────────────────────────────────────────

def downgrade() -> None:
    """
    Rollback — jalankan dengan: alembic downgrade c1a2b3d4e5f6
    PERINGATAN: Semua data jadwal_pengganti dan flag tamu akan hilang!
    """

    # Hapus index dulu sebelum drop kolom/tabel
    op.drop_index('ix_mahasiswa_matakuliah_is_tamu',        table_name='mahasiswa_matakuliah')
    op.drop_index('ix_jadwal_pengganti_matakuliah_pertemuan', table_name='jadwal_pengganti')

    # Drop tabel jadwal_pengganti
    op.drop_table('jadwal_pengganti')

    # Drop kolom dari mahasiswa_matakuliah
    op.drop_column('mahasiswa_matakuliah', 'kelas_asal')
    op.drop_column('mahasiswa_matakuliah', 'is_tamu')

    # Drop kolom dari matakuliah
    op.drop_column('matakuliah', 'izin_tamu')

    print("✓ Fase 1 downgrade selesai — semua perubahan di-rollback")