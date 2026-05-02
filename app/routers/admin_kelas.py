"""
app/routers/admin_kelas.py
═══════════════════════════
Fase B — Endpoint CRUD Kelas per Matakuliah

Endpoints:
  GET    /admin/matakuliah/{mk_id}/kelas                    — list semua kelas
  POST   /admin/matakuliah/{mk_id}/kelas                    — tambah kelas baru
  PUT    /admin/matakuliah/{mk_id}/kelas/{kelas_id}         — update kelas
  DELETE /admin/matakuliah/{mk_id}/kelas/{kelas_id}         — hapus kelas
  PATCH  /admin/kelas/{kelas_id}/izin-tamu                  — toggle izin tamu per kelas
  GET    /kelas/mahasiswa/{kelas_id}                        — mahasiswa terdaftar di kelas
  GET    /kelas/slot-options                                 — list slot yang tersedia (dropdown)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, List

from pydantic import BaseModel, Field

from app.database.db import get_db
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.services import kelas_service

router = APIRouter(tags=["Admin — Kelas Matakuliah"])

HARI_VALID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


# ── Dependency ────────────────────────────────────────────────

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Endpoint ini hanya untuk admin kampus")
    return current_user


def require_authenticated(current_user: User = Depends(get_current_user)) -> User:
    return current_user


# ── Request Schemas ───────────────────────────────────────────

class CreateKelasRequest(BaseModel):
    kode_kelas   : str            = Field(..., min_length=1, max_length=5,
                                          description="Kode kelas: A, B, C, X, dst")
    dosen_id     : Optional[UUID] = Field(None, description="UUID dosen pengampu")
    ruangan_id   : Optional[UUID] = Field(None, description="UUID ruangan (dari tabel ruangan)")
    hari         : Optional[str]  = Field(None, description="Senin|Selasa|Rabu|Kamis|Jumat|Sabtu|Minggu")
    slot_mulai   : Optional[int]  = Field(None, ge=1, le=12, description="Slot mulai 1-12")
    slot_selesai : Optional[int]  = Field(None, ge=1, le=12, description="Slot selesai 1-12")
    kode_akses   : Optional[str]  = Field(None, description="URL Google Classroom / kode WA / dll")
    izin_tamu    : bool           = Field(False, description="Izin mahasiswa kelas lain presensi")

    class Config:
        json_schema_extra = {"example": {
            "kode_kelas" : "A",
            "dosen_id"   : "uuid-dosen",
            "ruangan_id" : "uuid-ruangan",
            "hari"       : "Senin",
            "slot_mulai" : 1,
            "slot_selesai": 3,
            "kode_akses" : "https://classroom.google.com/c/abc123",
            "izin_tamu"  : False,
        }}


class UpdateKelasRequest(BaseModel):
    kode_kelas   : Optional[str]  = Field(None, min_length=1, max_length=5)
    dosen_id     : Optional[UUID] = None
    ruangan_id   : Optional[UUID] = None
    hari         : Optional[str]  = None
    slot_mulai   : Optional[int]  = Field(None, ge=1, le=12)
    slot_selesai : Optional[int]  = Field(None, ge=1, le=12)
    kode_akses   : Optional[str]  = None
    izin_tamu    : Optional[bool] = None
    is_active    : Optional[bool] = None


class IzinTamuKelasRequest(BaseModel):
    izin_tamu: bool

    class Config:
        json_schema_extra = {"example": {"izin_tamu": True}}


# ── GET /admin/matakuliah/{mk_id}/kelas ───────────────────────

@router.get("/admin/matakuliah/{mk_id}/kelas")
def list_kelas(
    mk_id: UUID,
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    """
    List semua kelas dari satu matakuliah.
    Return termasuk: dosen, ruangan, slot → jam, jumlah mahasiswa enrolled.
    """
    result = kelas_service.list_kelas(db, mk_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Matakuliah tidak ditemukan")
    return result


# ── POST /admin/matakuliah/{mk_id}/kelas ──────────────────────

@router.post("/admin/matakuliah/{mk_id}/kelas", status_code=201)
def create_kelas(
    mk_id: UUID,
    req  : CreateKelasRequest,
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    """
    Tambah kelas baru ke sebuah matakuliah.
    Kode kelas harus unik dalam satu matakuliah (A, B, C, dst).
    Jam otomatis dihitung dari slot_mulai dan slot_selesai.
    """
    if req.hari and req.hari not in HARI_VALID:
        raise HTTPException(
            status_code=400,
            detail=f"Hari tidak valid. Pilih dari: {', '.join(HARI_VALID)}"
        )
    if req.slot_mulai and req.slot_selesai and req.slot_selesai < req.slot_mulai:
        raise HTTPException(status_code=400, detail="slot_selesai harus >= slot_mulai")

    success, pesan, kelas = kelas_service.create_kelas(db, mk_id, req)
    if not success:
        raise HTTPException(status_code=400, detail=pesan)
    return {"message": pesan, "kelas": kelas}


# ── PUT /admin/matakuliah/{mk_id}/kelas/{kelas_id} ────────────

@router.put("/admin/matakuliah/{mk_id}/kelas/{kelas_id}")
def update_kelas(
    mk_id   : UUID,
    kelas_id: UUID,
    req     : UpdateKelasRequest,
    admin   : User    = Depends(require_admin),
    db      : Session = Depends(get_db),
):
    """Update data kelas. Semua field opsional (partial update)."""
    if req.hari and req.hari not in HARI_VALID:
        raise HTTPException(
            status_code=400,
            detail=f"Hari tidak valid. Pilih dari: {', '.join(HARI_VALID)}"
        )
    success, pesan, kelas = kelas_service.update_kelas(db, mk_id, kelas_id, req)
    if not success:
        raise HTTPException(status_code=404, detail=pesan)
    return {"message": pesan, "kelas": kelas}


# ── DELETE /admin/matakuliah/{mk_id}/kelas/{kelas_id} ─────────

@router.delete("/admin/matakuliah/{mk_id}/kelas/{kelas_id}")
def delete_kelas(
    mk_id   : UUID,
    kelas_id: UUID,
    admin   : User    = Depends(require_admin),
    db      : Session = Depends(get_db),
):
    """
    Hapus kelas.
    Akan gagal jika masih ada mahasiswa terdaftar di kelas ini.
    """
    success, pesan = kelas_service.delete_kelas(db, mk_id, kelas_id)
    if not success:
        raise HTTPException(status_code=400, detail=pesan)
    return {"message": pesan}


# ── PATCH /admin/kelas/{kelas_id}/izin-tamu ───────────────────

@router.patch("/admin/kelas/{kelas_id}/izin-tamu")
def toggle_izin_tamu_kelas(
    kelas_id: UUID,
    req     : IzinTamuKelasRequest,
    admin   : User    = Depends(require_admin),
    db      : Session = Depends(get_db),
):
    """
    Toggle izin tamu per kelas (override dari izin_tamu matakuliah).

    izin_tamu = true  → Mahasiswa kelas lain bisa presensi di kelas ini
    izin_tamu = false → Hanya mahasiswa terdaftar yang bisa presensi
    """
    success, pesan, kelas = kelas_service.toggle_izin_tamu_kelas(db, kelas_id, req.izin_tamu)
    if not success:
        raise HTTPException(status_code=404, detail=pesan)
    return {"message": pesan, "kelas": kelas}


# ── GET /kelas/mahasiswa/{kelas_id} ───────────────────────────

@router.get("/kelas/mahasiswa/{kelas_id}")
def get_mahasiswa_kelas(
    kelas_id: UUID,
    _       : User    = Depends(require_authenticated),
    db      : Session = Depends(get_db),
):
    """
    List mahasiswa terdaftar di kelas tertentu (asli + tamu).
    Accessible oleh semua user yang sudah login (admin, dosen, mahasiswa).
    """
    result = kelas_service.get_mahasiswa_kelas(db, kelas_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan")
    return result


# ── GET /kelas/slot-options ───────────────────────────────────

@router.get("/kelas/slot-options")
def get_slot_options(
    _: User = Depends(require_authenticated),
):
    """
    List semua slot yang tersedia beserta jam.
    Dipakai untuk dropdown di form tambah/edit kelas.
    """
    from app.utils.slot_utils import get_all_slots
    return get_all_slots()