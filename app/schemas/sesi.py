"""
app/schemas/sesi.py
════════════════════
Update Fase 2:
- BukaSesiRequest: tambah mulai_dari_jam_jadwal (bool) dan
  batas_terlambat_menit (Optional[int], None = tidak ada batas)
- SesiResponse: tambah batas_terlambat_menit di response
"""

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.models.sesi import SesiMode


# ─── REQUEST ──────────────────────────────────────────────────

class BukaSesiRequest(BaseModel):
    matakuliah_id         : UUID
    mode                  : SesiMode
    pertemuan_ke          : int = Field(..., ge=1, le=16)

    # Fase 2.3: None = tidak ada batas terlambat
    # Kirim null dari Flutter → semua presensi saat sesi aktif = Hadir
    batas_terlambat_menit : Optional[int] = Field(
        default=15,
        ge=0,
        le=120,
        description=(
            "Menit batas terlambat. "
            "0 = tidak ada toleransi (langsung Terlambat). "
            "null = tidak ada batas (semua presensi = Hadir selama sesi aktif)."
        )
    )

    # Hanya wajib untuk mode online
    durasi_menit          : Optional[int] = Field(
        default=None,
        ge=15,
        le=180,
        description="Durasi kode aktif (menit) — wajib untuk mode online"
    )

    # Fase 2.1: pakai jam_mulai matakuliah sebagai waktu_buka
    mulai_dari_jam_jadwal : bool = Field(
        default=False,
        description=(
            "True → waktu_buka diambil dari jam_mulai matakuliah hari ini "
            "(cocok jika dosen buka sesi sedikit terlambat tapi mau waktu mulai tetap sesuai jadwal). "
            "False → waktu_buka = sekarang (default)."
        )
    )

    class Config:
        json_schema_extra = {
            "example": {
                "matakuliah_id"        : "uuid-matakuliah",
                "mode"                 : "offline",
                "pertemuan_ke"         : 3,
                "batas_terlambat_menit": 15,
                "durasi_menit"         : None,
                "mulai_dari_jam_jadwal": True,
            }
        }


# ─── RESPONSE ─────────────────────────────────────────────────

class SesiResponse(BaseModel):
    id             : UUID
    mode           : str
    kode_sesi      : Optional[str]      = None
    kode_expire_at : Optional[datetime] = None
    pertemuan_ke   : int
    waktu_buka     : datetime
    status         : str
    detik_tersisa  : Optional[int]      = None

    # Fase 2.3: None = tidak ada batas terlambat
    batas_terlambat_menit : Optional[int] = Field(
        default=None,
        description="Menit batas terlambat. null = tidak ada batas."
    )

    class Config:
        from_attributes = True


# ─── EXTEND REQUEST ───────────────────────────────────────────

class ExtendKodeRequest(BaseModel):
    sesi_id        : UUID
    tambahan_menit : int = Field(..., ge=15, le=60)