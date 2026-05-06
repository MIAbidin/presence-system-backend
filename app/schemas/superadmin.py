# app/schemas/superadmin.py
"""
Schema Pydantic untuk semua endpoint Super Admin (Fase E).
Mencakup: manajemen akun Admin Fakultas + konfigurasi sistem.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from uuid import UUID
from datetime import datetime


# ══════════════════════════════════════════════════════════════
# MANAJEMEN AKUN ADMIN FAKULTAS
# ══════════════════════════════════════════════════════════════

class BuatAdminRequest(BaseModel):
    """Body request saat Super Admin membuat akun Admin Fakultas baru."""
    nim_nidn     : str = Field(..., min_length=5, max_length=20,
                               description="NIM/NIDN unik untuk login")
    nama_lengkap : str = Field(..., min_length=3, max_length=100)
    email        : EmailStr
    password     : str = Field(..., min_length=8,
                               description="Password minimal 8 karakter")
    program_studi: str = Field(..., max_length=100,
                               description="Unit/fakultas yang dikelola admin ini")

    class Config:
        json_schema_extra = {
            "example": {
                "nim_nidn"     : "ADM001",
                "nama_lengkap" : "Budi Santoso",
                "email"        : "budi.santoso@kampus.ac.id",
                "password"     : "password123",
                "program_studi": "Fakultas Komunikasi dan Informatika",
            }
        }


class UpdateAdminRequest(BaseModel):
    """Body request saat update data Admin Fakultas. Semua field opsional."""
    nim_nidn     : Optional[str]      = Field(None, min_length=5, max_length=20)
    nama_lengkap : Optional[str]      = Field(None, min_length=3, max_length=100)
    email        : Optional[EmailStr] = None
    program_studi: Optional[str]      = Field(None, max_length=100)

    class Config:
        json_schema_extra = {
            "example": {
                "nama_lengkap" : "Budi Santoso S.Kom",
                "program_studi": "Fakultas Teknik",
            }
        }


class ResetPasswordAdminRequest(BaseModel):
    """Body request reset password Admin Fakultas oleh Super Admin."""
    password_baru: str = Field(..., min_length=8,
                               description="Password baru minimal 8 karakter")

    class Config:
        json_schema_extra = {"example": {"password_baru": "passwordbaru456"}}


class AdminResponse(BaseModel):
    """Response data satu akun Admin Fakultas."""
    id           : UUID
    nim_nidn     : str
    nama_lengkap : str
    email        : str
    role         : str
    program_studi: str
    is_active    : bool
    created_at   : datetime

    class Config:
        from_attributes = True


class ListAdminResponse(BaseModel):
    """Response list akun Admin Fakultas dengan pagination."""
    total : int
    page  : int
    limit : int
    data  : List[AdminResponse]


# ══════════════════════════════════════════════════════════════
# KONFIGURASI SISTEM
# ══════════════════════════════════════════════════════════════

class KonfigurasiResponse(BaseModel):
    """Response satu item konfigurasi sistem."""
    id         : UUID
    key        : str
    value      : str
    label      : Optional[str] = None
    deskripsi  : Optional[str] = None
    tipe       : str
    nilai_min  : Optional[str] = None
    nilai_max  : Optional[str] = None
    is_readonly: bool
    updated_at : Optional[datetime] = None

    class Config:
        from_attributes = True


class UpdateKonfigurasiRequest(BaseModel):
    """Body request update satu nilai konfigurasi."""
    value: str = Field(..., min_length=1,
                       description="Nilai baru (selalu string, divalidasi sesuai tipe di server)")

    class Config:
        json_schema_extra = {
            "examples": {
                "face_threshold"   : {"value": "0.85"},
                "geofencing_radius": {"value": "150"},
                "maintenance_mode" : {"value": "true"},
            }
        }


class BulkUpdateKonfigurasiRequest(BaseModel):
    """
    Body request update banyak konfigurasi sekaligus.
    Key harus ada di tabel konfigurasi_sistem.
    """
    konfigurasi: dict[str, str] = Field(
        ...,
        description="Dict {key: value_baru}, contoh: {'face_threshold': '0.85'}"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "konfigurasi": {
                    "face_threshold"    : "0.85",
                    "geofencing_radius" : "150",
                    "maintenance_mode"  : "false",
                }
            }
        }


class BulkUpdateKonfigurasiResponse(BaseModel):
    """Response bulk update konfigurasi."""
    berhasil: List[str]   # list key yang berhasil diupdate
    gagal   : List[dict]  # list {key, error} yang gagal
    pesan   : str