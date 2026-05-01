"""
app/routers/admin.py
═════════════════════
Fase 3 — GET /admin/dashboard
Fase 4 — Manajemen Users (mahasiswa & dosen)
Fase 6 — Manajemen Matakuliah + toggle izin_tamu

Endpoints:
  GET    /admin/dashboard
  GET    /admin/users
  POST   /admin/users
  PUT    /admin/users/{user_id}
  DELETE /admin/users/{user_id}
  POST   /admin/users/{user_id}/reset-face
  POST   /admin/users/{user_id}/reset-password
  POST   /admin/users/{user_id}/face-diagnose

  GET    /admin/matakuliah
  POST   /admin/matakuliah
  PUT    /admin/matakuliah/{mk_id}
  DELETE /admin/matakuliah/{mk_id}
  PATCH  /admin/matakuliah/{mk_id}/izin-tamu
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional

from app.database.db import get_db
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.services import admin_service
from fastapi import HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── Dependency ────────────────────────────────────────────────

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Endpoint ini hanya untuk admin kampus")
    return current_user


# ── Request schemas — Users ───────────────────────────────────

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
    nama_lengkap  : Optional[str]  = None
    email         : Optional[str]  = None
    program_studi : Optional[str]  = None
    is_active     : Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    password_baru: str

    class Config:
        json_schema_extra = {"example": {"password_baru": "NewPassword123!"}}


# ── Request schemas — Matakuliah ──────────────────────────────

HARI_VALID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


class CreateMatakuliahRequest(BaseModel):
    kode          : str             = Field(..., min_length=2, max_length=20)
    nama          : str             = Field(..., min_length=3, max_length=100)
    sks           : int             = Field(..., ge=1, le=8)
    hari          : Optional[str]   = Field(None, description="Senin|Selasa|Rabu|Kamis|Jumat|Sabtu|Minggu")
    jam_mulai     : Optional[str]   = Field(None, description="Format HH:MM, contoh: 08:00")
    jam_selesai   : Optional[str]   = Field(None, description="Format HH:MM, contoh: 10:30")
    ruangan       : Optional[str]   = Field(None, max_length=50)
    koordinat_lat : Optional[float] = None
    koordinat_lng : Optional[float] = None
    izin_tamu     : Optional[bool]  = False

    class Config:
        json_schema_extra = {"example": {
            "kode"         : "IF301",
            "nama"         : "Pemrograman Mobile",
            "sks"          : 3,
            "hari"         : "Senin",
            "jam_mulai"    : "08:00",
            "jam_selesai"  : "10:30",
            "ruangan"      : "Lab Komputer A-301",
            "koordinat_lat": -5.130245,
            "koordinat_lng": 119.489432,
            "izin_tamu"    : False,
        }}


class UpdateMatakuliahRequest(BaseModel):
    kode          : Optional[str]   = Field(None, min_length=2, max_length=20)
    nama          : Optional[str]   = Field(None, min_length=3, max_length=100)
    sks           : Optional[int]   = Field(None, ge=1, le=8)
    hari          : Optional[str]   = None
    jam_mulai     : Optional[str]   = None
    jam_selesai   : Optional[str]   = None
    ruangan       : Optional[str]   = Field(None, max_length=50)
    koordinat_lat : Optional[float] = None
    koordinat_lng : Optional[float] = None
    izin_tamu     : Optional[bool]  = None


class IzinTamuRequest(BaseModel):
    izin_tamu: bool

    class Config:
        json_schema_extra = {"example": {"izin_tamu": True}}


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
    return admin_service.list_users(db, role=role, search=search, page=page, limit=limit)


# ─── POST /admin/users ────────────────────────────────────────

@router.post("/users", status_code=201)
def create_user(
    req  : CreateUserRequest,
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
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
    result = admin_service.get_face_diagnose_info(db, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return result


# ════════════════════════════════════════════════════════════
# FASE 6 — MATAKULIAH ENDPOINTS
# ════════════════════════════════════════════════════════════

# ─── GET /admin/matakuliah ────────────────────────────────────

@router.get("/matakuliah")
def list_matakuliah(
    search : Optional[str] = Query(None, description="Cari kode, nama, atau ruangan"),
    page   : int           = Query(1,    ge=1),
    limit  : int           = Query(20,   ge=1, le=100),
    admin  : User          = Depends(require_admin),
    db     : Session       = Depends(get_db),
):
    """
    List semua matakuliah dengan pagination dan pencarian.
    Search: kode, nama, atau ruangan (case-insensitive).
    """
    return admin_service.list_matakuliah(db, search=search, page=page, limit=limit)


# ─── POST /admin/matakuliah ───────────────────────────────────

@router.post("/matakuliah", status_code=201)
def create_matakuliah(
    req  : CreateMatakuliahRequest,
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    """Buat matakuliah baru."""
    if req.hari and req.hari not in HARI_VALID:
        raise HTTPException(
            status_code=400,
            detail=f"Hari tidak valid. Pilih dari: {', '.join(HARI_VALID)}"
        )
    success, pesan, mk = admin_service.create_matakuliah(db, req)
    if not success:
        raise HTTPException(status_code=400, detail=pesan)
    return {"message": pesan, "matakuliah": mk}


# ─── PUT /admin/matakuliah/{mk_id} ────────────────────────────

@router.put("/matakuliah/{mk_id}")
def update_matakuliah(
    mk_id: UUID,
    req  : UpdateMatakuliahRequest,
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    """Update data matakuliah (semua field opsional)."""
    if req.hari and req.hari not in HARI_VALID:
        raise HTTPException(
            status_code=400,
            detail=f"Hari tidak valid. Pilih dari: {', '.join(HARI_VALID)}"
        )
    success, pesan, mk = admin_service.update_matakuliah(db, mk_id, req)
    if not success:
        raise HTTPException(status_code=404, detail=pesan)
    return {"message": pesan, "matakuliah": mk}


# ─── DELETE /admin/matakuliah/{mk_id} ─────────────────────────

@router.delete("/matakuliah/{mk_id}")
def delete_matakuliah(
    mk_id: UUID,
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    """Hapus matakuliah permanen (termasuk semua data terkait via cascade)."""
    success, pesan = admin_service.delete_matakuliah(db, mk_id)
    if not success:
        raise HTTPException(status_code=404, detail=pesan)
    return {"message": pesan}


# ─── PATCH /admin/matakuliah/{mk_id}/izin-tamu ────────────────

@router.patch("/matakuliah/{mk_id}/izin-tamu")
def toggle_izin_tamu(
    mk_id: UUID,
    req  : IzinTamuRequest,
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    """
    Toggle izin tamu per matakuliah langsung dari tabel.

    izin_tamu = true  → Mahasiswa dari kelas lain boleh presensi otomatis.
    izin_tamu = false → Hanya mahasiswa terdaftar yang bisa presensi.
    """
    success, pesan, mk = admin_service.toggle_izin_tamu_admin(db, mk_id, req.izin_tamu)
    if not success:
        raise HTTPException(status_code=404, detail=pesan)
    return {"message": pesan, "matakuliah": mk}

# ════════════════════════════════════════════════════════════
# FASE 7 — ENROLLMENT MANAGEMENT
# ════════════════════════════════════════════════════════════

class EnrollRequest(BaseModel):
    mahasiswa_id: UUID

class EnrollBulkRequest(BaseModel):
    mahasiswa_ids: List[UUID]

# ─── GET /admin/matakuliah/{mk_id}/mahasiswa ─────────────────

@router.get("/matakuliah/{mk_id}/mahasiswa")
def get_mahasiswa_matakuliah(
    mk_id: UUID,
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    result = admin_service.get_mahasiswa_matakuliah(db, mk_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Matakuliah tidak ditemukan")
    return result

# ─── POST /admin/matakuliah/{mk_id}/enroll ───────────────────

@router.post("/matakuliah/{mk_id}/enroll", status_code=201)
def enroll_mahasiswa(
    mk_id: UUID,
    req  : EnrollRequest,
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    success, pesan = admin_service.enroll_mahasiswa(db, mk_id, req.mahasiswa_id)
    if not success:
        raise HTTPException(status_code=400, detail=pesan)
    return {"message": pesan}

# ─── POST /admin/matakuliah/{mk_id}/enroll-bulk ──────────────

@router.post("/matakuliah/{mk_id}/enroll-bulk")
def enroll_bulk(
    mk_id: UUID,
    req  : EnrollBulkRequest,
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    result = admin_service.enroll_bulk(db, mk_id, req.mahasiswa_ids)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result

# ─── DELETE /admin/matakuliah/{mk_id}/unenroll/{mahasiswa_id} ─

@router.delete("/matakuliah/{mk_id}/unenroll/{mahasiswa_id}")
def unenroll_mahasiswa(
    mk_id       : UUID,
    mahasiswa_id: UUID,
    admin       : User    = Depends(require_admin),
    db          : Session = Depends(get_db),
):
    success, pesan = admin_service.unenroll_mahasiswa(db, mk_id, mahasiswa_id)
    if not success:
        raise HTTPException(status_code=400, detail=pesan)
    return {"message": pesan}

# ─── DELETE /admin/matakuliah/{mk_id}/tamu/{mahasiswa_id} ────

@router.delete("/matakuliah/{mk_id}/tamu/{mahasiswa_id}")
def hapus_tamu(
    mk_id       : UUID,
    mahasiswa_id: UUID,
    admin       : User    = Depends(require_admin),
    db          : Session = Depends(get_db),
):
    success, pesan = admin_service.hapus_tamu_admin(db, mk_id, mahasiswa_id)
    if not success:
        raise HTTPException(status_code=400, detail=pesan)
    return {"message": pesan}