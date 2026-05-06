# app/routers/superadmin.py
"""
Router Super Admin (Fase E) — endpoint eksklusif untuk role 'super_admin'.

Endpoint:
  GET    /superadmin/admins               → list Admin Fakultas
  POST   /superadmin/admins               → buat Admin Fakultas baru
  GET    /superadmin/admins/{id}          → detail satu admin
  PUT    /superadmin/admins/{id}          → update data admin
  PATCH  /superadmin/admins/{id}/toggle   → aktifkan/nonaktifkan admin
  POST   /superadmin/admins/{id}/reset-password → reset password admin

  GET    /superadmin/konfigurasi          → list semua konfigurasi
  GET    /superadmin/konfigurasi/{key}    → detail satu konfigurasi
  PATCH  /superadmin/konfigurasi/{key}    → update satu konfigurasi
  PATCH  /superadmin/konfigurasi          → bulk update konfigurasi
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.schemas.superadmin import (
    AdminResponse,
    BuatAdminRequest,
    BulkUpdateKonfigurasiRequest,
    BulkUpdateKonfigurasiResponse,
    KonfigurasiResponse,
    ListAdminResponse,
    ResetPasswordAdminRequest,
    UpdateAdminRequest,
    UpdateKonfigurasiRequest,
)
from app.services import superadmin_service
from app.services.audit_service import tulis_audit_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/superadmin", tags=["Super Admin"])


# ─── DEPENDENCY: hanya super_admin ────────────────────────────

def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency — cek role super_admin.
    Mengembalikan 403 Forbidden jika bukan super_admin.
    """
    if current_user.role != UserRole.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Endpoint ini hanya bisa diakses oleh Super Admin (IT Kampus)",
        )
    return current_user


# ══════════════════════════════════════════════════════════════
# MANAJEMEN AKUN ADMIN FAKULTAS
# ══════════════════════════════════════════════════════════════

@router.get("/admins", response_model=ListAdminResponse)
def list_admins(
    search: Optional[str] = Query(None, description="Cari nama / NIM/NIDN / email"),
    page  : int           = Query(1,    ge=1),
    limit : int           = Query(20,   ge=1, le=100),
    db    : Session       = Depends(get_db),
    _     : User          = Depends(require_super_admin),
):
    """List semua akun Admin Fakultas (role='admin')."""
    result = superadmin_service.list_admins(db, search=search, page=page, limit=limit)
    return ListAdminResponse(
        total=result["total"],
        page=result["page"],
        limit=result["limit"],
        data=[AdminResponse.model_validate(u) for u in result["data"]],
    )


@router.post("/admins", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
def buat_admin(
    req          : BuatAdminRequest,
    db           : Session = Depends(get_db),
    current_user : User    = Depends(require_super_admin),
):
    """Buat akun Admin Fakultas baru."""
    try:
        admin = superadmin_service.buat_admin(db, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    tulis_audit_log(
        db          = db,
        admin_id    = current_user.id,
        aksi        = "BUAT_ADMIN",
        entitas     = "users",
        entitas_id  = str(admin.id),
        detail      = f"Buat akun admin: {admin.nim_nidn} — {admin.nama_lengkap}",
    )
    return AdminResponse.model_validate(admin)


@router.get("/admins/{admin_id}", response_model=AdminResponse)
def detail_admin(
    admin_id : UUID,
    db       : Session = Depends(get_db),
    _        : User    = Depends(require_super_admin),
):
    """Ambil detail satu akun Admin Fakultas."""
    admin = superadmin_service.get_admin(db, admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin tidak ditemukan")
    return AdminResponse.model_validate(admin)


@router.put("/admins/{admin_id}", response_model=AdminResponse)
def update_admin(
    admin_id     : UUID,
    req          : UpdateAdminRequest,
    db           : Session = Depends(get_db),
    current_user : User    = Depends(require_super_admin),
):
    """Update data Admin Fakultas."""
    try:
        admin = superadmin_service.update_admin(db, admin_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    tulis_audit_log(
        db         = db,
        admin_id   = current_user.id,
        aksi       = "UPDATE_ADMIN",
        entitas    = "users",
        entitas_id = str(admin_id),
        detail     = f"Update data admin: {admin.nim_nidn}",
    )
    return AdminResponse.model_validate(admin)


@router.patch("/admins/{admin_id}/toggle", response_model=AdminResponse)
def toggle_admin(
    admin_id     : UUID,
    is_active    : bool,
    db           : Session = Depends(get_db),
    current_user : User    = Depends(require_super_admin),
):
    """
    Aktifkan / nonaktifkan akun Admin Fakultas.
    Super Admin tidak bisa menonaktifkan dirinya sendiri.
    """
    if admin_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Super Admin tidak bisa menonaktifkan akun sendiri",
        )

    try:
        admin = superadmin_service.toggle_admin_aktif(db, admin_id, is_active)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    status_str = "diaktifkan" if is_active else "dinonaktifkan"
    tulis_audit_log(
        db         = db,
        admin_id   = current_user.id,
        aksi       = "TOGGLE_ADMIN",
        entitas    = "users",
        entitas_id = str(admin_id),
        detail     = f"Admin {admin.nim_nidn} {status_str}",
    )
    return AdminResponse.model_validate(admin)


@router.post("/admins/{admin_id}/reset-password")
def reset_password_admin(
    admin_id     : UUID,
    req          : ResetPasswordAdminRequest,
    db           : Session = Depends(get_db),
    current_user : User    = Depends(require_super_admin),
):
    """Reset password Admin Fakultas."""
    try:
        superadmin_service.reset_password_admin(db, admin_id, req.password_baru)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    tulis_audit_log(
        db         = db,
        admin_id   = current_user.id,
        aksi       = "RESET_PASSWORD_ADMIN",
        entitas    = "users",
        entitas_id = str(admin_id),
        detail     = "Reset password admin oleh Super Admin",
    )
    return {"message": "Password admin berhasil direset"}


# ══════════════════════════════════════════════════════════════
# KONFIGURASI SISTEM
# ══════════════════════════════════════════════════════════════

@router.get("/konfigurasi", response_model=list[KonfigurasiResponse])
def list_konfigurasi(
    db : Session = Depends(get_db),
    _  : User    = Depends(require_super_admin),
):
    """List semua konfigurasi sistem."""
    items = superadmin_service.list_konfigurasi(db)
    return [KonfigurasiResponse.model_validate(k) for k in items]


@router.get("/konfigurasi/{key}", response_model=KonfigurasiResponse)
def detail_konfigurasi(
    key : str,
    db  : Session = Depends(get_db),
    _   : User    = Depends(require_super_admin),
):
    """Ambil detail satu konfigurasi berdasarkan key."""
    konfig = superadmin_service.get_konfigurasi(db, key)
    if not konfig:
        raise HTTPException(
            status_code=404,
            detail=f"Konfigurasi '{key}' tidak ditemukan",
        )
    return KonfigurasiResponse.model_validate(konfig)


@router.patch("/konfigurasi/{key}", response_model=KonfigurasiResponse)
def update_konfigurasi(
    key          : str,
    req          : UpdateKonfigurasiRequest,
    db           : Session = Depends(get_db),
    current_user : User    = Depends(require_super_admin),
):
    """Update satu nilai konfigurasi sistem."""
    try:
        konfig = superadmin_service.update_konfigurasi(db, key, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    tulis_audit_log(
        db         = db,
        admin_id   = current_user.id,
        aksi       = "UPDATE_KONFIGURASI",
        entitas    = "konfigurasi_sistem",
        entitas_id = key,
        detail     = f"Konfigurasi '{key}' diubah → '{req.value}'",
    )
    return KonfigurasiResponse.model_validate(konfig)


@router.patch("/konfigurasi", response_model=BulkUpdateKonfigurasiResponse)
def bulk_update_konfigurasi(
    req          : BulkUpdateKonfigurasiRequest,
    db           : Session = Depends(get_db),
    current_user : User    = Depends(require_super_admin),
):
    """
    Update banyak konfigurasi sekaligus.
    Konfigurasi yang gagal (readonly / tidak ditemukan / nilai tidak valid)
    dilaporkan di field 'gagal' tanpa menghentikan update yang lain.
    """
    berhasil = []
    gagal    = []

    for key, value in req.konfigurasi.items():
        try:
            update_req = UpdateKonfigurasiRequest(value=value)
            superadmin_service.update_konfigurasi(db, key, update_req)
            berhasil.append(key)
        except ValueError as e:
            gagal.append({"key": key, "error": str(e)})

    if berhasil:
        tulis_audit_log(
            db         = db,
            admin_id   = current_user.id,
            aksi       = "BULK_UPDATE_KONFIGURASI",
            entitas    = "konfigurasi_sistem",
            entitas_id = ",".join(berhasil),
            detail     = f"Bulk update {len(berhasil)} konfigurasi: {berhasil}",
        )

    return BulkUpdateKonfigurasiResponse(
        berhasil = berhasil,
        gagal    = gagal,
        pesan    = (
            f"{len(berhasil)} konfigurasi berhasil diupdate"
            + (f", {len(gagal)} gagal" if gagal else "")
        ),
    )