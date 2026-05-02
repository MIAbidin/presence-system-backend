"""
app/models/ruangan.py
══════════════════════
Fase A — Model tabel ruangan kuliah.

Ruangan adalah entitas terpisah dengan kode, tipe, kapasitas,
dan koordinat GPS yang dipakai untuk validasi presensi offline.
Menggantikan field ruangan (string) yang sebelumnya di tabel matakuliah.
"""
import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database.db import Base


class Ruangan(Base):
    """
    Tabel ruangan kuliah / lab / seminar.

    Tipe ruangan:
    - kuliah  : Ruang kuliah reguler (J.Int.1, J0403, SW706, dll)
    - lab     : Laboratorium (LABRPL, LSITIF, LJKTIF, dll)
    - seminar : Ruang seminar / aula (JSEM2, RVL200, dll)

    koordinat_lat & koordinat_lng dipakai untuk validasi GPS
    saat presensi mode offline — menggantikan koordinat di tabel matakuliah.
    """
    __tablename__ = "ruangan"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Kode unik ruangan — contoh: 'J.Int.1', 'LABRPL', 'JSEM2'
    kode          = Column(String(20),  unique=True, nullable=False, index=True)

    # Nama lengkap — contoh: 'Lab RPL', 'Ruang Kuliah J Lantai 4'
    nama          = Column(String(100), nullable=False)

    # kuliah | lab | seminar | lainnya
    tipe          = Column(String(30),  nullable=True)

    kapasitas     = Column(Integer, nullable=True)    # jumlah kursi/mahasiswa

    # Lokasi fisik
    gedung        = Column(String(50),  nullable=True)  # 'Gedung J', 'Gedung SW'
    lantai        = Column(Integer,     nullable=True)  # 1, 2, 3 ...

    # Koordinat GPS untuk geofencing presensi offline
    koordinat_lat = Column(Float, nullable=True)
    koordinat_lng = Column(Float, nullable=True)

    # Keterangan tambahan (akses, fasilitas, catatan)
    keterangan    = Column(Text, nullable=True)

    is_active     = Column(Boolean, default=True, nullable=False)

    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )