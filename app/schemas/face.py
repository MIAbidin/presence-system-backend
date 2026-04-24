# app/schemas/face.py
from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class FaceRegisterResponse(BaseModel):
    message: str
    foto_index: int
    total_terdaftar: int
    is_complete: bool  # True jika sudah >= 8 foto

class FaceVerifyResponse(BaseModel):
    passed: bool
    akurasi: float        # skor 0.0 – 100.0
    mahasiswa_id: Optional[UUID] = None
    pesan: str