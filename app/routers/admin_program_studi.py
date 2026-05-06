"""
app/routers/admin_program_studi.py
════════════════════════════════════
Fase D — Manajemen Program Studi

Endpoints:
  GET    /admin/program-studi          List semua program studi (admin, paginasi)
  POST   /admin/program-studi          Buat program studi baru
  PUT    /admin/program-studi/{id}     Update program studi
  DELETE /admin/program-studi/{id}     Hapus program studi (cek user aktif)
  PATCH  /admin/program-studi/{id}/toggle  Toggle is_active
  GET    /admin/program-studi/stats    Statistik untuk stat strip frontend

  GET    /program-studi/aktif          List prodi aktif untuk dropdown (no auth ketat)
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.database.db import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.services import admin_service
from pydantic import BaseModel, Field

# ── Dua router: satu /admin/* (butuh admin), satu publik ─────

router_admin = APIRouter(prefix="/admin/program-studi", tags=["Admin — Program Studi"])
router_publik = APIRouter(prefix="/program-studi", tags=["Program Studi"])

# Gabungkan keduanya ke satu variabel agar main.py cukup include satu router
router = APIRouter()


# ── Dependency ────────────────────────────────────────────────

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    from app.models.user import UserRole
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=403,
            detail="Endpoint ini hanya untuk admin kampus",
        )
    return current_user


# ── Request schemas ───────────────────────────────────────────

JENJANG_VALID = ["D3", "D4", "S1", "S2", "S3"]


class CreateProgramStudiRequest(BaseModel):
    kode     : str           = Field(..., min_length=2, max_length=10,
                                     description="Kode unik prodi, contoh: TIF, SI, IK")
    nama     : str           = Field(..., min_length=3, max_length=100)
    fakultas : Optional[str] = Field(None, max_length=100)
    jenjang  : Optional[str] = Field(None, description="D3 | D4 | S1 | S2 | S3")

    class Config:
        json_schema_extra = {"example": {
            "kode"    : "TIF",
            "nama"    : "Teknik Informatika",
            "fakultas": "Fakultas Komunikasi dan Informatika",
            "jenjang" : "S1",
        }}


class UpdateProgramStudiRequest(BaseModel):
    kode     : Optional[str] = Field(None, min_length=2, max_length=10)
    nama     : Optional[str] = Field(None, min_length=3, max_length=100)
    fakultas : Optional[str] = Field(None, max_length=100)
    jenjang  : Optional[str] = None
    is_active: Optional[bool] = None


class ToggleProgramStudiRequest(BaseModel):
    is_active: bool

    class Config:
        json_schema_extra = {"example": {"is_active": False}}


# ══════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS  (prefix: /admin/program-studi)
# ══════════════════════════════════════════════════════════════

# ── GET /admin/program-studi ──────────────────────────────────

@router.get("/admin/program-studi", tags=["Admin — Program Studi"])
def list_program_studi(
    search : Optional[str] = Query(None, description="Cari kode, nama, atau fakultas"),
    jenjang: Optional[str] = Query(None, description="Filter jenjang: D3 | D4 | S1 | S2 | S3"),
    page   : int           = Query(1,    ge=1),
    limit  : int           = Query(20,   ge=1, le=100),
    admin  : User          = Depends(require_admin),
    db     : Session       = Depends(get_db),
):
    """
    List semua program studi dengan pagination dan pencarian.

    Search mencakup: kode, nama, dan fakultas (case-insensitive).
    Response menyertakan jumlah mahasiswa dan dosen aktif per prodi.
    """
    return admin_service.list_program_studi(
        db,
        search=search,
        jenjang=jenjang,
        page=page,
        limit=limit,
    )


# ── GET /admin/program-studi/stats ───────────────────────────

@router.get("/admin/program-studi/stats", tags=["Admin — Program Studi"])
def get_program_studi_stats(
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    """
    Statistik program studi untuk stat strip di halaman frontend.
    Return: total, aktif, per jenjang (S1, D3, D4).
    """
    return admin_service.get_program_studi_stats(db)


# ── POST /admin/program-studi ─────────────────────────────────

@router.post("/admin/program-studi", status_code=201, tags=["Admin — Program Studi"])
def create_program_studi(
    req  : CreateProgramStudiRequest,
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    """
    Buat program studi baru.

    - Kode otomatis di-uppercase (tif → TIF).
    - Kode harus unik.
    - Jenjang harus salah satu dari: D3, D4, S1, S2, S3.
    """
    if req.jenjang and req.jenjang not in JENJANG_VALID:
        raise HTTPException(
            status_code=400,
            detail=f"Jenjang tidak valid. Pilih dari: {', '.join(JENJANG_VALID)}",
        )

    success, pesan, prodi = admin_service.create_program_studi(db, req)
    if not success:
        raise HTTPException(status_code=400, detail=pesan)
    return {"message": pesan, "program_studi": prodi}


# ── PUT /admin/program-studi/{prodi_id} ───────────────────────

@router.put("/admin/program-studi/{prodi_id}", tags=["Admin — Program Studi"])
def update_program_studi(
    prodi_id: UUID,
    req     : UpdateProgramStudiRequest,
    admin   : User    = Depends(require_admin),
    db      : Session = Depends(get_db),
):
    """
    Update data program studi (semua field opsional — partial update).

    Jika kode berubah, dicek duplikat terlebih dahulu.
    """
    if req.jenjang and req.jenjang not in JENJANG_VALID:
        raise HTTPException(
            status_code=400,
            detail=f"Jenjang tidak valid. Pilih dari: {', '.join(JENJANG_VALID)}",
        )

    success, pesan, prodi = admin_service.update_program_studi(db, prodi_id, req)
    if not success:
        raise HTTPException(status_code=404, detail=pesan)
    return {"message": pesan, "program_studi": prodi}


# ── DELETE /admin/program-studi/{prodi_id} ────────────────────

@router.delete("/admin/program-studi/{prodi_id}", tags=["Admin — Program Studi"])
def delete_program_studi(
    prodi_id: UUID,
    admin   : User    = Depends(require_admin),
    db      : Session = Depends(get_db),
):
    """
    Hapus program studi.

    GAGAL jika masih ada mahasiswa/dosen aktif yang terdaftar di prodi ini
    (via kolom program_studi_id). Pindahkan atau nonaktifkan mereka terlebih
    dahulu sebelum menghapus.

    Jika berhasil dihapus, kolom program_studi_id di tabel users akan di-SET NULL
    secara otomatis (via FK ondelete='SET NULL').
    """
    success, pesan = admin_service.delete_program_studi(db, prodi_id)
    if not success:
        raise HTTPException(status_code=400, detail=pesan)
    return {"message": pesan}


# ── PATCH /admin/program-studi/{prodi_id}/toggle ─────────────

@router.patch("/admin/program-studi/{prodi_id}/toggle", tags=["Admin — Program Studi"])
def toggle_program_studi(
    prodi_id: UUID,
    req     : ToggleProgramStudiRequest,
    admin   : User    = Depends(require_admin),
    db      : Session = Depends(get_db),
):
    """
    Toggle status aktif program studi tanpa membuka modal edit.

    is_active = false → prodi tidak muncul di dropdown form mahasiswa/dosen baru,
                        tapi data lama tetap valid.
    """
    success, pesan, prodi = admin_service.toggle_program_studi(
        db, prodi_id, req.is_active
    )
    if not success:
        raise HTTPException(status_code=404, detail=pesan)
    return {"message": pesan, "program_studi": prodi}


# ══════════════════════════════════════════════════════════════
# PUBLIK ENDPOINT  (prefix: /program-studi)
# Digunakan oleh form Tambah Mahasiswa / Tambah Dosen sebagai dropdown
# ══════════════════════════════════════════════════════════════

# ── GET /program-studi/aktif ──────────────────────────────────

@router.get("/program-studi/aktif", tags=["Program Studi"])
def list_program_studi_aktif(
    jenjang: Optional[str] = Query(None, description="Filter jenjang: D3 | D4 | S1 | S2 | S3"),
    db     : Session       = Depends(get_db),
    _      : User          = Depends(get_current_user),   # cukup login, tidak harus admin
):
    """
    List program studi yang aktif untuk dropdown di form tambah mahasiswa/dosen.

    Tidak memerlukan role admin — cukup login.
    Tidak ada pagination (return semua yang aktif, biasanya < 50 prodi).
    """
    result = admin_service.list_program_studi(
        db,
        jenjang=jenjang,
        aktif_only=True,
        page=1,
        limit=200,   # ambil semua — untuk dropdown tidak perlu paginasi
    )
    # Return flat list saja (tanpa wrapper pagination) agar lebih mudah di frontend
    return {
        "items": result["items"],
        "total": result["total"],
    }