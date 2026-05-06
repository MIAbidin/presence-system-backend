# app/models/konfigurasi_sistem.py
"""
Tabel konfigurasi_sistem — key-value store untuk parameter sistem.

Key yang dikelola Super Admin:
  face_threshold       → Euclidean distance threshold verifikasi wajah (default: 0.9)
  geofencing_radius    → Radius geofencing presensi offline dalam meter (default: 100)
  timezone             → Timezone server (default: Asia/Jakarta)
  maintenance_mode     → Nonaktifkan presensi sementara (default: false)
  max_foto_registrasi  → Jumlah foto minimal registrasi wajah (default: 8)
"""
import uuid

from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database.db import Base


class KonfigurasiSistem(Base):
    __tablename__ = "konfigurasi_sistem"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Key unik — dipakai sebagai identifier konfigurasi
    key         = Column(String(100), unique=True, nullable=False, index=True,
                         comment="Identifier konfigurasi, contoh: face_threshold")

    # Value selalu disimpan sebagai string — parsing dilakukan di service layer
    value       = Column(Text, nullable=False,
                         comment="Nilai konfigurasi (string). Parsing ke float/int/bool dilakukan di service.")

    # Metadata
    label       = Column(String(200), nullable=True,
                         comment="Label yang tampil di UI, contoh: 'Face Recognition Threshold'")
    deskripsi   = Column(Text, nullable=True,
                         comment="Penjelasan fungsi konfigurasi ini")
    tipe        = Column(String(20), nullable=False, default="string",
                         comment="Tipe data: string | float | integer | boolean")

    # Batas nilai (untuk validasi di UI)
    nilai_min   = Column(String(50), nullable=True,
                         comment="Nilai minimum (untuk tipe float/integer)")
    nilai_max   = Column(String(50), nullable=True,
                         comment="Nilai maksimum (untuk tipe float/integer)")

    # Hanya Super Admin yang boleh ubah
    is_readonly = Column(Boolean, default=False, nullable=False,
                         comment="True = tidak bisa diubah via API (hanya via migration)")

    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(),
                         onupdate=func.now())


# ─── Konstanta key yang valid ──────────────────────────────────────────────────
class KonfigKey:
    FACE_THRESHOLD      = "face_threshold"
    GEOFENCING_RADIUS   = "geofencing_radius"
    TIMEZONE            = "timezone"
    MAINTENANCE_MODE    = "maintenance_mode"
    MAX_FOTO_REGISTRASI = "max_foto_registrasi"

    ALL = {
        FACE_THRESHOLD,
        GEOFENCING_RADIUS,
        TIMEZONE,
        MAINTENANCE_MODE,
        MAX_FOTO_REGISTRASI,
    }