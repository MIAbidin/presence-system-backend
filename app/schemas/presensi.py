# app/schemas/presensi.py
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


# ─── REQUEST ─────────────────────────────────────────────

class PresensiRequest(BaseModel):
    sesi_id   : UUID
    kode_sesi : Optional[str] = None    # wajib untuk mode online
    latitude  : Optional[float] = None  # wajib untuk mode offline
    longitude : Optional[float] = None

    class Config:
        json_schema_extra = {"example": {
            "sesi_id"  : "uuid-sesi-di-sini",
            "kode_sesi": "A7X3K2",   # isi untuk online, kosongkan untuk offline
            "latitude" : None,
            "longitude": None,
        }}


class UbahStatusRequest(BaseModel):
    presensi_id : UUID
    status_baru : str = Field(
        ...,
        description="hadir / terlambat / absen / izin / sakit"
    )
    catatan : Optional[str] = None


# ─── RESPONSE ────────────────────────────────────────────

class PresensiResponse(BaseModel):
    id             : UUID
    status         : str
    waktu_presensi : Optional[datetime]
    akurasi_wajah  : Optional[float]
    mode_kelas     : str
    pesan          : str

    class Config:
        from_attributes = True


class RiwayatItemResponse(BaseModel):
    id              : UUID
    sesi_id         : UUID
    status          : str
    waktu_presensi  : Optional[datetime]
    akurasi_wajah   : Optional[float]
    mode_kelas      : str
    catatan         : Optional[str]
    pertemuan_ke    : Optional[int] = None   # dari relasi sesi

    class Config:
        from_attributes = True