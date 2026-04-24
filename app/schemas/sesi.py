# app/schemas/sesi.py
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.models.sesi import SesiMode

class BukaSesiRequest(BaseModel):
    matakuliah_id   : UUID
    mode            : SesiMode
    durasi_menit    : Optional[int] = Field(None, ge=15, le=180,
                        description="Durasi kode aktif (menit) — wajib untuk mode online")
    batas_terlambat : int = Field(15, ge=1, le=60,
                        description="Menit sebelum dicatat Terlambat")
    pertemuan_ke    : int = Field(..., ge=1, le=16)

    class Config:
        json_schema_extra = {"example": {
            "matakuliah_id"  : "uuid-matakuliah",
            "mode"           : "online",
            "durasi_menit"   : 30,
            "batas_terlambat": 15,
            "pertemuan_ke"   : 3
        }}

class SesiResponse(BaseModel):
    id             : UUID
    mode           : str
    kode_sesi      : Optional[str] = None
    kode_expire_at : Optional[datetime] = None
    pertemuan_ke   : int
    waktu_buka     : datetime
    status         : str
    detik_tersisa  : Optional[int] = None   # countdown untuk frontend

    class Config:
        from_attributes = True

class ExtendKodeRequest(BaseModel):
    sesi_id        : UUID
    tambahan_menit : int = Field(..., ge=15, le=60)