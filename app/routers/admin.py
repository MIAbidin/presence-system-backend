"""
app/routers/admin.py
═════════════════════
Fase 3 — GET /admin/dashboard
Fase 4 — Manajemen Users (mahasiswa & dosen)

Endpoints:
  GET    /admin/dashboard
  GET    /admin/users
  POST   /admin/users
  PUT    /admin/users/{user_id}
  DELETE /admin/users/{user_id}          (soft delete)
  POST   /admin/users/{user_id}/reset-face
  POST   /admin/users/{user_id}/reset-password
  POST   /admin/users/{user_id}/face-diagnose
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.database.db import get_db
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.services import admin_service
from fastapi import HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Dependency ────────────────────────────────────────────────

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Endpoint ini hanya untuk admin kampus")
    return current_user


# ── Request schemas ───────────────────────────────────────────

class CreateUserRequest(BaseModel):
    nim_nidn      : str
    nama_lengkap  : str
    email         : str
    password      : str
    role          : str   # "mahasiswa" | "dosen"
    program_studi : str

    class Config:
        json_schema_extra = {"example": {
            "nim_nidn"     : "H071211099",
            "nama_lengkap" : "Budi Pratama",
            "email"        : "budi@student.ac.id",
            "password"     : "Password123!",
            "role"         : "mahasiswa",
            "program_studi": "Teknik Informatika",
        }}


class UpdateUserRequest(BaseModel):
    nama_lengkap  : Optional[str] = None
    email         : Optional[str] = None
    program_studi : Optional[str] = None
    is_active     : Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    password_baru: str

    class Config:
        json_schema_extra = {"example": {"password_baru": "NewPassword123!"}}


# ─── GET /admin/dashboard ─────────────────────────────────────

@router.get("/dashboard")
def get_dashboard(
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    """Beranda admin — semua statistik dalam satu request."""
    return admin_service.get_dashboard_stats(db)


# ─── GET /admin/users ─────────────────────────────────────────

@router.get("/users")
def list_users(
    role    : Optional[str] = Query(None, description="mahasiswa | dosen | admin"),
    search  : Optional[str] = Query(None, description="Cari NIM/nama/email"),
    page    : int           = Query(1,    ge=1),
    limit   : int           = Query(20,   ge=1, le=100),
    admin   : User          = Depends(require_admin),
    db      : Session       = Depends(get_db),
):
    """
    List semua user dengan pagination dan filter.
    Filter role: mahasiswa | dosen | admin
    Filter search: NIM/NIDN, nama, atau email (case-insensitive)
    """
    return admin_service.list_users(db, role=role, search=search, page=page, limit=limit)


# ─── POST /admin/users ────────────────────────────────────────

@router.post("/users", status_code=201)
def create_user(
    req  : CreateUserRequest,
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    """Buat akun user baru (mahasiswa atau dosen)."""
    success, pesan, user = admin_service.create_user(db, req)
    if not success:
        raise HTTPException(status_code=400, detail=pesan)
    return {"message": pesan, "user": user}


# ─── PUT /admin/users/{user_id} ───────────────────────────────

@router.put("/users/{user_id}")
def update_user(
    user_id: UUID,
    req    : UpdateUserRequest,
    admin  : User    = Depends(require_admin),
    db     : Session = Depends(get_db),
):
    """Update data user (nama, email, program studi, status aktif)."""
    success, pesan, user = admin_service.update_user(db, user_id, req)
    if not success:
        raise HTTPException(status_code=404, detail=pesan)
    return {"message": pesan, "user": user}


# ─── DELETE /admin/users/{user_id} ────────────────────────────

@router.delete("/users/{user_id}")
def delete_user(
    user_id: UUID,
    admin  : User    = Depends(require_admin),
    db     : Session = Depends(get_db),
):
    """Soft delete — set is_active = False."""
    success, pesan = admin_service.soft_delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail=pesan)
    return {"message": pesan}


# ─── POST /admin/users/{user_id}/reset-face ───────────────────

@router.post("/users/{user_id}/reset-face")
def reset_face(
    user_id: UUID,
    admin  : User    = Depends(require_admin),
    db     : Session = Depends(get_db),
):
    """Hapus semua data wajah + set is_face_registered = False."""
    success, pesan = admin_service.reset_face(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail=pesan)
    return {"message": pesan}


# ─── POST /admin/users/{user_id}/reset-password ───────────────

@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: UUID,
    req    : ResetPasswordRequest,
    admin  : User    = Depends(require_admin),
    db     : Session = Depends(get_db),
):
    """Admin reset password user tanpa perlu password lama."""
    success, pesan = admin_service.reset_password(db, user_id, req.password_baru)
    if not success:
        raise HTTPException(status_code=404, detail=pesan)
    return {"message": pesan}


# ─── POST /admin/users/{user_id}/face-diagnose ────────────────

@router.post("/users/{user_id}/face-diagnose")
def face_diagnose(
    user_id: UUID,
    admin  : User    = Depends(require_admin),
    db     : Session = Depends(get_db),
):
    """
    Diagnosa akurasi face recognition mahasiswa tertentu.
    Return semua jarak Euclidean ke setiap embedding tersimpan.
    Berguna untuk debug kasus mahasiswa gagal presensi.

    Note: endpoint ini tidak butuh foto — hanya menganalisis
    embedding yang sudah tersimpan di DB dan memberikan statistik.
    """
    result = admin_service.get_face_diagnose_info(db, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return result