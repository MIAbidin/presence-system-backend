"""
app/routers/admin_ruangan.py
═════════════════════════════
Fase A — Endpoint CRUD Ruangan Kuliah

Endpoints:
  GET    /admin/ruangan                        — list semua ruangan (admin)
  POST   /admin/ruangan                        — buat ruangan baru
  PUT    /admin/ruangan/{ruangan_id}           — update ruangan
  DELETE /admin/ruangan/{ruangan_id}           — hapus ruangan
  PATCH  /admin/ruangan/{ruangan_id}/toggle    — toggle is_active inline
  GET    /ruangan/aktif                        — list aktif (dropdown, no strict auth)

"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, Field

from app.database.db import get_db
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.services import admin_service

router = APIRouter(tags=["Admin — Ruangan"])


# ── Dependency ────────────────────────────────────────────────

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Endpoint ini hanya untuk admin kampus")
    return current_user


# ── Request Schemas ───────────────────────────────────────────

TIPE_VALID = ["kuliah", "lab", "seminar", "lainnya"]


class CreateRuanganRequest(BaseModel):
    kode          : str             = Field(..., min_length=2, max_length=20,
                                           description="Kode unik, contoh: J.Int.1, LABRPL")
    nama          : str             = Field(..., min_length=3, max_length=100,
                                           description="Nama lengkap ruangan")
    tipe          : Optional[str]   = Field(None, description="kuliah | lab | seminar | lainnya")
    kapasitas     : Optional[int]   = Field(None, ge=1, le=2000, description="Kapasitas kursi")
    gedung        : Optional[str]   = Field(None, max_length=50, description="Nama gedung")
    lantai        : Optional[int]   = Field(None, ge=1, le=50)
    koordinat_lat : Optional[float] = Field(None, ge=-90,  le=90)
    koordinat_lng : Optional[float] = Field(None, ge=-180, le=180)
    keterangan    : Optional[str]   = Field(None, description="Catatan tambahan")

    class Config:
        json_schema_extra = {"example": {
            "kode"         : "J.Int.1",
            "nama"         : "Ruang Kuliah J Int 1",
            "tipe"         : "kuliah",
            "kapasitas"    : 45,
            "gedung"       : "Gedung J",
            "lantai"       : 1,
            "koordinat_lat": -5.130245,
            "koordinat_lng": 119.489432,
            "keterangan"   : "AC, proyektor, kapasitas 45 kursi",
        }}


class UpdateRuanganRequest(BaseModel):
    kode          : Optional[str]   = Field(None, min_length=2, max_length=20)
    nama          : Optional[str]   = Field(None, min_length=3, max_length=100)
    tipe          : Optional[str]   = None
    kapasitas     : Optional[int]   = Field(None, ge=1, le=2000)
    gedung        : Optional[str]   = Field(None, max_length=50)
    lantai        : Optional[int]   = Field(None, ge=1, le=50)
    koordinat_lat : Optional[float] = Field(None, ge=-90, le=90)
    koordinat_lng : Optional[float] = Field(None, ge=-180, le=180)
    keterangan    : Optional[str]   = None
    is_active     : Optional[bool]  = None


class ToggleAktifRequest(BaseModel):
    is_active: bool

    class Config:
        json_schema_extra = {"example": {"is_active": False}}


# ════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS (prefix /admin/ruangan)
# ════════════════════════════════════════════════════════════

# ─── GET /admin/ruangan ───────────────────────────────────────

@router.get("/admin/ruangan")
def list_ruangan(
    search    : Optional[str] = Query(None, description="Cari kode, nama, atau gedung"),
    tipe      : Optional[str] = Query(None, description="kuliah | lab | seminar | lainnya | semua"),
    page      : int           = Query(1,    ge=1),
    limit     : int           = Query(20,   ge=1, le=100),
    admin     : User    = Depends(require_admin),
    db        : Session = Depends(get_db),
):
    """
    List semua ruangan dengan filter dan pagination.

    Filter opsional:
    - search: pencarian di kode, nama, gedung (case-insensitive)
    - tipe  : filter by tipe (kuliah/lab/seminar/lainnya/semua)
    - page  : halaman pagination
    - limit : jumlah item per halaman
    """
    return admin_service.list_ruangan(
        db, search=search, tipe=tipe, page=page, limit=limit
    )


# ─── POST /admin/ruangan ──────────────────────────────────────

@router.post("/admin/ruangan", status_code=201)
def create_ruangan(
    req  : CreateRuanganRequest,
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    """Buat ruangan baru."""
    success, pesan, ruangan = admin_service.create_ruangan(db, req)
    if not success:
        raise HTTPException(status_code=400, detail=pesan)
    return {"message": pesan, "ruangan": ruangan}


# ─── PUT /admin/ruangan/{ruangan_id} ─────────────────────────

@router.put("/admin/ruangan/{ruangan_id}")
def update_ruangan(
    ruangan_id: UUID,
    req       : UpdateRuanganRequest,
    admin     : User    = Depends(require_admin),
    db        : Session = Depends(get_db),
):
    """Update data ruangan (semua field opsional)."""
    success, pesan, ruangan = admin_service.update_ruangan(db, ruangan_id, req)
    if not success:
        raise HTTPException(status_code=404, detail=pesan)
    return {"message": pesan, "ruangan": ruangan}


# ─── DELETE /admin/ruangan/{ruangan_id} ──────────────────────

@router.delete("/admin/ruangan/{ruangan_id}")
def delete_ruangan(
    ruangan_id: UUID,
    admin     : User    = Depends(require_admin),
    db        : Session = Depends(get_db),
):
    """
    Hapus ruangan permanen.
    PERINGATAN: Akan gagal jika ruangan masih dipakai di matakuliah.
    """
    success, pesan = admin_service.delete_ruangan(db, ruangan_id)
    if not success:
        raise HTTPException(status_code=400, detail=pesan)
    return {"message": pesan}


# ─── PATCH /admin/ruangan/{ruangan_id}/toggle ────────────────

@router.patch("/admin/ruangan/{ruangan_id}/toggle")
def toggle_ruangan(
    ruangan_id: UUID,
    req       : ToggleAktifRequest,
    admin     : User    = Depends(require_admin),
    db        : Session = Depends(get_db),
):
    """
    Toggle status aktif/nonaktif ruangan tanpa membuka modal edit.
    Ruangan nonaktif tidak muncul di dropdown form.
    """
    success, pesan, ruangan = admin_service.toggle_ruangan_active(
        db, ruangan_id, req.is_active
    )
    if not success:
        raise HTTPException(status_code=404, detail=pesan)
    return {"message": pesan, "ruangan": ruangan}


# ─── GET /admin/ruangan/stats ────────────────────────────────

@router.get("/admin/ruangan/stats")
def get_ruangan_stats(
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    """Statistik ruangan untuk stat strip di halaman frontend."""
    return admin_service.get_ruangan_stats(db)


# ════════════════════════════════════════════════════════════
# PUBLIC ENDPOINT (prefix /ruangan) — untuk dropdown form
# ════════════════════════════════════════════════════════════

# ─── GET /ruangan/aktif ───────────────────────────────────────

@router.get("/ruangan/aktif")
def get_ruangan_aktif(
    tipe: Optional[str]  = Query(None, description="Filter tipe ruangan"),
    _   : User           = Depends(get_current_user),
    db  : Session        = Depends(get_db),
):
    """
    List ruangan yang aktif — untuk dropdown di form tambah/edit matakuliah & kelas.
    Tidak memerlukan role admin, cukup login.
    Return semua aktif (limit=1000) tanpa pagination untuk keperluan dropdown.
    """
    result = admin_service.list_ruangan(
        db, tipe=tipe, aktif_only=True, page=1, limit=1000
    )
    return result["items"]