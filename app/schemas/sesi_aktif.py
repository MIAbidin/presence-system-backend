# app/schemas/sesi_aktif.py
"""
Schema Pydantic untuk endpoint sesi aktif (Fase B-2).

Memperkaya response GET /sesi/aktif agar Flutter SesiDetectService
bisa auto-detect mode presensi tanpa mahasiswa memilih manual.

Field yang ditambahkan:
- matakuliah_nama, matakuliah_kode
- kelas_id, kode_kelas (A/B/C)
- dosen_nama
- ruangan (nama ruangan)
- koordinat_lat, koordinat_lng (untuk validasi GPS offline)
- detik_tersisa (countdown untuk online)
- pertemuan_ke
"""
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class SesiAktifDetailResponse(BaseModel):
    """
    Response lengkap satu sesi aktif untuk mahasiswa.
    Dipakai oleh SesiDetectService di Flutter untuk auto-detect mode.

    Flutter logic:
    - Jika mode == 'online'  → navigate ke KodeSesiScreen otomatis
    - Jika mode == 'offline' → langsung buka kamera + validasi GPS
    - Jika sesi == null      → tampil tombol 'Ikut sebagai Tamu'
    """

    # ── Info sesi ────────────────────────────────────────────
    sesi_id         : UUID
    mode            : str        # 'offline' | 'online'
    pertemuan_ke    : int
    waktu_buka      : Optional[datetime] = None
    detik_tersisa   : Optional[int]      = None  # hanya untuk online (countdown kode)

    # ── Info matakuliah ──────────────────────────────────────
    matakuliah_id   : UUID
    matakuliah_nama : str
    matakuliah_kode : str

    # ── Info kelas (Fase B) ──────────────────────────────────
    kelas_id        : Optional[UUID] = None  # NULL = enrollment lama sebelum Fase B
    kode_kelas      : Optional[str]  = None  # 'A' | 'B' | 'C' | None

    # ── Info dosen ───────────────────────────────────────────
    dosen_nama      : Optional[str]  = None

    # ── Info ruangan / lokasi (untuk mode offline) ──────────
    ruangan         : Optional[str]  = None  # nama ruangan
    koordinat_lat   : Optional[float]= None  # GPS lat ruang kelas
    koordinat_lng   : Optional[float]= None  # GPS lng ruang kelas

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "sesi_id"        : "uuid-sesi",
                "mode"           : "offline",
                "pertemuan_ke"   : 10,
                "waktu_buka"     : "2026-05-11T07:05:00Z",
                "detik_tersisa"  : None,
                "matakuliah_id"  : "uuid-mk",
                "matakuliah_nama": "Pemrograman Mobile",
                "matakuliah_kode": "TIF3232209",
                "kelas_id"       : "uuid-kelas",
                "kode_kelas"     : "A",
                "dosen_nama"     : "Dr. Ir. Budi Santoso, M.T.",
                "ruangan"        : "Lab Mobile Computing",
                "koordinat_lat"  : -5.131380,
                "koordinat_lng"  : 119.490840,
            }
        }


class SesiAktifWrapper(BaseModel):
    """
    Wrapper response untuk GET /sesi/aktif.

    Jika tidak ada sesi aktif yang cocok dengan jadwal mahasiswa:
      { "ada_sesi": false, "sesi": null }

    Jika ada sesi aktif:
      { "ada_sesi": true, "sesi": { ...SesiAktifDetailResponse... } }

    Flutter mengecek 'ada_sesi' dulu, baru akses 'sesi'.
    Tidak pernah return 404 — selalu 200 dengan ada_sesi=false.
    """
    ada_sesi : bool
    sesi     : Optional[SesiAktifDetailResponse] = None