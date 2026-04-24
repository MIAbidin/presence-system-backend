from pydantic import BaseModel
from typing import Optional
from uuid import UUID


# ─── REQUEST ─────────────────────────────────────────────

class LoginRequest(BaseModel):
    nim_nidn: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "nim_nidn": "2021001001",
                "password": "password123"
            }
        }


# ─── RESPONSE ────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    nim_nidn: str
    nama_lengkap: str
    email: str
    role: str
    program_studi: str
    is_face_registered: bool

    class Config:
        from_attributes = True  # agar bisa convert dari SQLAlchemy model


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─── REFRESH TOKEN ───────────────────────────────────────

class RefreshTokenRequest(BaseModel):
    refresh_token: str