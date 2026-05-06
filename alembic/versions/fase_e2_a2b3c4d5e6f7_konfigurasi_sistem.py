"""fase E2 - buat tabel konfigurasi_sistem dengan seed data default

Revision ID: fase_e2_a2b3c4d5e6f7
Revises: fase_e1_f1a2b3c4d5e6
Create Date: 2026-05-06 10:30:00.000000

Perubahan:
- CREATE TABLE konfigurasi_sistem
- INSERT seed data 5 konfigurasi default:
    face_threshold, geofencing_radius, timezone,
    maintenance_mode, max_foto_registrasi

Cara rollback:
    alembic downgrade fase_e1_f1a2b3c4d5e6
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa

revision: str = "fase_e2_a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "fase_e1_f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Buat tabel konfigurasi_sistem ──────────────────────
    op.create_table(
        "konfigurasi_sistem",

        sa.Column("id",          sa.UUID(),              nullable=False),
        sa.Column("key",         sa.String(length=100),  nullable=False,
                  comment="Identifier konfigurasi, contoh: face_threshold"),
        sa.Column("value",       sa.Text(),              nullable=False,
                  comment="Nilai konfigurasi (string). Parsing ke tipe asli dilakukan di service."),
        sa.Column("label",       sa.String(length=200),  nullable=True,
                  comment="Label yang tampil di UI admin"),
        sa.Column("deskripsi",   sa.Text(),              nullable=True,
                  comment="Penjelasan fungsi konfigurasi ini"),
        sa.Column("tipe",        sa.String(length=20),   nullable=False,
                  server_default=sa.text("'string'"),
                  comment="Tipe data: string | float | integer | boolean"),
        sa.Column("nilai_min",   sa.String(length=50),   nullable=True,
                  comment="Nilai minimum (untuk tipe float/integer)"),
        sa.Column("nilai_max",   sa.String(length=50),   nullable=True,
                  comment="Nilai maksimum (untuk tipe float/integer)"),
        sa.Column("is_readonly", sa.Boolean(),           nullable=False,
                  server_default=sa.text("FALSE"),
                  comment="True = tidak bisa diubah via API"),
        sa.Column("created_at",  sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at",  sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=True),

        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_konfigurasi_sistem_key"),
    )

    # Index untuk lookup cepat berdasarkan key
    op.create_index("ix_konfigurasi_sistem_key", "konfigurasi_sistem", ["key"], unique=True)

    # ── 2. Seed data: 5 konfigurasi default ───────────────────
    # Menggunakan op.bulk_insert untuk idempoten-friendly insert
    konfigurasi_table = sa.table(
        "konfigurasi_sistem",
        sa.column("id",          sa.String),
        sa.column("key",         sa.String),
        sa.column("value",       sa.String),
        sa.column("label",       sa.String),
        sa.column("deskripsi",   sa.String),
        sa.column("tipe",        sa.String),
        sa.column("nilai_min",   sa.String),
        sa.column("nilai_max",   sa.String),
        sa.column("is_readonly", sa.Boolean),
    )

    op.bulk_insert(konfigurasi_table, [
        {
            "id"         : str(uuid.uuid4()),
            "key"        : "face_threshold",
            "value"      : "0.9",
            "label"      : "Face Recognition Threshold",
            "deskripsi"  : (
                "Euclidean distance threshold untuk verifikasi wajah (setelah L2-normalize). "
                "Range valid: 0.0–2.0. "
                "Semakin kecil = lebih ketat (lebih sedikit yang lolos). "
                "Rekomendasi: 0.7–1.0. Default: 0.9."
            ),
            "tipe"       : "float",
            "nilai_min"  : "0.1",
            "nilai_max"  : "2.0",
            "is_readonly": False,
        },
        {
            "id"         : str(uuid.uuid4()),
            "key"        : "geofencing_radius",
            "value"      : "100",
            "label"      : "Radius Geofencing Presensi Offline",
            "deskripsi"  : (
                "Jarak maksimum (meter) antara lokasi mahasiswa dan koordinat ruang kelas "
                "agar presensi offline diterima. "
                "Nilai lebih besar = toleransi GPS drift lebih lebar. "
                "Default: 100 meter."
            ),
            "tipe"       : "integer",
            "nilai_min"  : "10",
            "nilai_max"  : "500",
            "is_readonly": False,
        },
        {
            "id"         : str(uuid.uuid4()),
            "key"        : "timezone",
            "value"      : "Asia/Jakarta",
            "label"      : "Timezone Server",
            "deskripsi"  : (
                "Timezone yang dipakai untuk perhitungan waktu presensi dan jadwal. "
                "Contoh: Asia/Jakarta (WIB), Asia/Makassar (WITA), Asia/Jayapura (WIT). "
                "Gunakan nama timezone IANA (pytz)."
            ),
            "tipe"       : "string",
            "nilai_min"  : None,
            "nilai_max"  : None,
            "is_readonly": False,
        },
        {
            "id"         : str(uuid.uuid4()),
            "key"        : "maintenance_mode",
            "value"      : "false",
            "label"      : "Mode Maintenance",
            "deskripsi"  : (
                "Jika 'true', semua endpoint presensi mahasiswa dinonaktifkan sementara "
                "(return 503). Berguna saat update sistem atau perbaikan database. "
                "Nilai: 'true' atau 'false'."
            ),
            "tipe"       : "boolean",
            "nilai_min"  : None,
            "nilai_max"  : None,
            "is_readonly": False,
        },
        {
            "id"         : str(uuid.uuid4()),
            "key"        : "max_foto_registrasi",
            "value"      : "8",
            "label"      : "Jumlah Foto Minimal Registrasi Wajah",
            "deskripsi"  : (
                "Jumlah foto yang harus diambil mahasiswa saat registrasi wajah "
                "sebelum is_face_registered ditandai True. "
                "Lebih banyak foto = akurasi verifikasi lebih baik. "
                "Default: 8 foto."
            ),
            "tipe"       : "integer",
            "nilai_min"  : "4",
            "nilai_max"  : "20",
            "is_readonly": False,
        },
    ])

    print("✓ Fase E2 upgrade selesai:")
    print("  - Tabel konfigurasi_sistem dibuat")
    print("  - Seed data 5 konfigurasi default diinsert:")
    print("    • face_threshold       = 0.9")
    print("    • geofencing_radius    = 100")
    print("    • timezone             = Asia/Jakarta")
    print("    • maintenance_mode     = false")
    print("    • max_foto_registrasi  = 8")


def downgrade() -> None:
    """
    Rollback — jalankan dengan: alembic downgrade fase_e1_f1a2b3c4d5e6
    PERINGATAN: Semua konfigurasi kustom yang diubah admin akan hilang!
    """
    op.drop_index("ix_konfigurasi_sistem_key", table_name="konfigurasi_sistem")
    op.drop_table("konfigurasi_sistem")

    print("✓ Fase E2 downgrade selesai — tabel konfigurasi_sistem dihapus")