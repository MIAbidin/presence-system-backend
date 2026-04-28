"""
app/schemas/dosen.py
═════════════════════
Schema Pydantic untuk semua endpoint dosen Fase 3:
- 3.1 Beranda dosen
- 3.2 Detail matakuliah
- 3.3 Toggle izin tamu
- 3.4 Tambah/hapus mahasiswa tamu manual
- 3.5 Jadwal pengganti
- 3.6 Peserta sesi (sudah ada, diperluas)
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


# ════════════════════════════════════════════════════════════
# 3.1 — BERANDA DOSEN
# ════════════════════════════════════════════════════════════

class JadwalHariIniDosenItem(BaseModel):
    """Satu matakuliah dalam jadwal hari ini dosen."""
    matakuliah_id   : UUID
    kode            : str
    nama            : str
    sks             : int
    hari            : Optional[str]  = None
    jam_mulai       : Optional[str]  = None   # "08:00"
    jam_selesai     : Optional[str]  = None   # "09:40"
    ruangan         : Optional[str]  = None
    pertemuan_ke_berikutnya : int    = 1      # pertemuan ke berapa berikutnya

    # Status sesi hari ini
    status_sesi     : str            = "belum_mulai"
    # "belum_mulai" | "aktif" | "selesai"
    sesi_id         : Optional[UUID] = None   # ada kalau aktif atau selesai hari ini

    # Statistik cepat kalau sesi sudah aktif/selesai
    jumlah_hadir    : int = 0
    jumlah_terlambat: int = 0
    jumlah_absen    : int = 0
    total_mahasiswa : int = 0

    # Info jadwal pengganti (kalau ada)
    ada_jadwal_pengganti : bool          = False
    jam_mulai_pengganti  : Optional[str] = None
    jam_selesai_pengganti: Optional[str] = None
    ruangan_pengganti    : Optional[str] = None

    class Config:
        from_attributes = True


class MatakuliahRingkasanItem(BaseModel):
    """Item di section 'Semua Matakuliah' beranda dosen."""
    matakuliah_id   : UUID
    kode            : str
    nama            : str
    sks             : int
    hari            : Optional[str] = None
    jam_mulai       : Optional[str] = None
    jam_selesai     : Optional[str] = None
    ruangan         : Optional[str] = None
    total_mahasiswa : int = 0
    total_pertemuan_selesai: int = 0

    class Config:
        from_attributes = True


class BerandaDosenResponse(BaseModel):
    """Response GET /dosen/beranda — satu hit untuk semua data beranda."""
    nama_dosen      : str
    nidn            : str
    jadwal_hari_ini : List[JadwalHariIniDosenItem]
    semua_matakuliah: List[MatakuliahRingkasanItem]
    total_sesi_aktif: int = 0


# ════════════════════════════════════════════════════════════
# 3.2 — DETAIL MATAKULIAH
# ════════════════════════════════════════════════════════════

class MahasiswaDetailItem(BaseModel):
    """Satu mahasiswa dalam daftar detail matakuliah."""
    mahasiswa_id    : UUID
    nim             : str
    nama_lengkap    : str
    program_studi   : str
    is_face_registered: bool
    is_tamu         : bool
    kelas_asal      : Optional[str] = None  # diisi kalau is_tamu=True

    # Statistik kehadiran di matakuliah ini
    total_hadir     : int   = 0
    total_terlambat : int   = 0
    total_absen     : int   = 0
    persentase_hadir: float = 0.0

    class Config:
        from_attributes = True


class JadwalPenggantiItem(BaseModel):
    """Satu item jadwal pengganti."""
    id               : UUID
    pertemuan_ke     : int
    jam_mulai_baru   : Optional[str] = None  # "10:00"
    jam_selesai_baru : Optional[str] = None
    ruangan_baru     : Optional[str] = None
    keterangan       : Optional[str] = None
    created_at       : datetime

    class Config:
        from_attributes = True


class RiwayatSesiItem(BaseModel):
    """Satu sesi di tab Riwayat detail matakuliah."""
    sesi_id         : UUID
    pertemuan_ke    : int
    mode            : str
    waktu_buka      : datetime
    waktu_tutup     : Optional[datetime] = None
    status          : str
    jumlah_hadir    : int = 0
    jumlah_terlambat: int = 0
    jumlah_absen    : int = 0
    total_mahasiswa : int = 0
    persentase_hadir: float = 0.0

    class Config:
        from_attributes = True


class DetailMatakuliahResponse(BaseModel):
    """Response GET /dosen/matakuliah/{mk_id}."""
    matakuliah_id   : UUID
    kode            : str
    nama            : str
    sks             : int
    hari            : Optional[str] = None
    jam_mulai       : Optional[str] = None
    jam_selesai     : Optional[str] = None
    ruangan         : Optional[str] = None
    koordinat_lat   : Optional[float] = None
    koordinat_lng   : Optional[float] = None
    izin_tamu       : bool

    # Tab Mahasiswa
    mahasiswa_asli  : List[MahasiswaDetailItem] = []
    mahasiswa_tamu  : List[MahasiswaDetailItem] = []
    total_mahasiswa : int = 0

    # Tab Jadwal
    jadwal_pengganti: List[JadwalPenggantiItem] = []

    # Tab Riwayat
    riwayat_sesi    : List[RiwayatSesiItem] = []

    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════
# 3.3 — TOGGLE IZIN TAMU
# ════════════════════════════════════════════════════════════

class IzinTamuRequest(BaseModel):
    izin_tamu: bool = Field(
        ...,
        description="True = mahasiswa kelas lain bisa langsung presensi tanpa izin manual"
    )

    class Config:
        json_schema_extra = {"example": {"izin_tamu": True}}


class IzinTamuResponse(BaseModel):
    matakuliah_id : UUID
    nama          : str
    izin_tamu     : bool
    pesan         : str


# ════════════════════════════════════════════════════════════
# 3.4 — TAMBAH/HAPUS TAMU MANUAL
# ════════════════════════════════════════════════════════════

class TambahTamuRequest(BaseModel):
    nim: str = Field(
        ...,
        min_length=8,
        max_length=20,
        description="NIM mahasiswa yang akan ditambahkan sebagai tamu"
    )

    class Config:
        json_schema_extra = {"example": {"nim": "2021001003"}}


class TambahTamuResponse(BaseModel):
    pesan           : str
    mahasiswa_id    : UUID
    nim             : str
    nama_lengkap    : str
    kelas_asal      : Optional[str] = None


# ════════════════════════════════════════════════════════════
# 3.5 — JADWAL PENGGANTI
# ════════════════════════════════════════════════════════════

class JadwalPenggantiRequest(BaseModel):
    pertemuan_ke      : int = Field(..., ge=1, le=16)
    jam_mulai_baru    : Optional[str] = Field(
        None,
        description="Format HH:MM, contoh: 10:00"
    )
    jam_selesai_baru  : Optional[str] = Field(
        None,
        description="Format HH:MM, contoh: 12:30"
    )
    ruangan_baru      : Optional[str] = Field(None, max_length=50)
    keterangan        : Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "pertemuan_ke"    : 5,
                "jam_mulai_baru"  : "10:00",
                "jam_selesai_baru": "12:30",
                "ruangan_baru"    : "C-202",
                "keterangan"      : "Pindah ruang karena Lab A-301 dipakai seminar"
            }
        }