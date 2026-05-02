"""
app/routers/admin_audit.py
════════════════════════════
Fase 11 — Endpoint tambahan:
  GET  /admin/audit-log               — list aktivitas admin (dengan pagination)
  POST /admin/ganti-password          — admin ganti password sendiri
  GET  /admin/scheduler/status        — status APScheduler
  POST /admin/scheduler/start         — start scheduler (maintenance)
  POST /admin/scheduler/stop          — stop scheduler (maintenance)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.database.db import get_db
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.services import audit_service

router = APIRouter(prefix="/admin", tags=["Admin — Fase 11"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Endpoint ini hanya untuk admin kampus")
    return current_user


# ─── GET /admin/audit-log ─────────────────────────────────────

@router.get("/audit-log")
def get_audit_log(
    page    : int            = Query(1,    ge=1),
    limit   : int            = Query(50,   ge=1, le=200),
    admin_id: Optional[UUID] = Query(None, description="Filter by admin UUID"),
    entitas : Optional[str]  = Query(None, description="Filter by entitas: user, matakuliah, dll"),
    aksi    : Optional[str]  = Query(None, description="Filter by aksi (pencarian sebagian)"),
    admin   : User    = Depends(require_admin),
    db      : Session = Depends(get_db),
):
    """
    List semua log aktivitas admin.
    Diurutkan dari yang terbaru.

    Filter opsional:
    - admin_id : hanya tampilkan log dari admin tertentu
    - entitas  : filter by tipe entitas (user, matakuliah, enrollment, dll)
    - aksi     : pencarian sebagian nama aksi (ILIKE)
    """
    return audit_service.get_audit_logs(
        db,
        page=page, limit=limit,
        admin_id=admin_id,
        entitas=entitas,
        aksi=aksi,
    )


# ─── POST /admin/ganti-password ───────────────────────────────

class GantiPasswordRequest(BaseModel):
    password_lama : str = Field(..., min_length=1)
    password_baru : str = Field(..., min_length=6)
    konfirmasi    : str = Field(..., min_length=6)

    class Config:
        json_schema_extra = {
            "example": {
                "password_lama": "OldPassword123!",
                "password_baru": "NewPassword456!",
                "konfirmasi"   : "NewPassword456!",
            }
        }


@router.post("/ganti-password")
def ganti_password(
    req    : GantiPasswordRequest,
    request: Request,
    admin  : User    = Depends(require_admin),
    db     : Session = Depends(get_db),
):
    """
    Admin ganti password sendiri.
    Memerlukan password lama untuk verifikasi.
    """
    from app.services.auth_service import verify_password, hash_password

    # Verifikasi password lama
    if not verify_password(req.password_lama, admin.password_hash):
        raise HTTPException(status_code=400, detail="Password lama tidak sesuai")

    # Cek konfirmasi
    if req.password_baru != req.konfirmasi:
        raise HTTPException(status_code=400, detail="Konfirmasi password tidak cocok")

    admin.password_hash = hash_password(req.password_baru)
    db.commit()

    # Catat ke audit log
    ip = request.client.host if request.client else None
    audit_service.catat(
        db, admin.id,
        aksi       = "CHANGE_PASSWORD",
        entitas    = "user",
        entitas_id = str(admin.id),
        detail     = {"keterangan": "Admin mengubah password sendiri"},
        ip_address = ip,
    )
    db.commit()

    return {"message": "Password berhasil diubah. Silakan login ulang jika diperlukan."}


# ─── GET /admin/scheduler/status ──────────────────────────────

@router.get("/scheduler/status")
def get_scheduler_status(
    admin: User = Depends(require_admin),
):
    """
    Cek status APScheduler — running/stopped dan daftar jobs aktif.
    Data sama dengan GET /health tapi hanya bagian scheduler.
    """
    try:
        from app.scheduler import get_scheduler
        scheduler  = get_scheduler()
        is_running = scheduler.running
        jobs = [
            {
                "id"           : j.id,
                "name"         : j.name,
                "next_run_time": j.next_run_time.isoformat() if j.next_run_time else None,
                "trigger"      : str(j.trigger),
            }
            for j in scheduler.get_jobs()
        ] if is_running else []
        return {
            "running": is_running,
            "status" : "running" if is_running else "stopped",
            "jobs"   : jobs,
            "total_jobs": len(jobs),
        }
    except Exception as e:
        return {"running": False, "status": "error", "jobs": [], "error": str(e)}


# ─── POST /admin/scheduler/start ──────────────────────────────

@router.post("/scheduler/start")
def start_scheduler(
    request: Request,
    admin  : User    = Depends(require_admin),
    db     : Session = Depends(get_db),
):
    """
    Start APScheduler (jika sedang stopped).
    Digunakan setelah maintenance.
    """
    try:
        from app.scheduler import start_scheduler as _start
        _start()
        ip = request.client.host if request.client else None
        audit_service.catat(db, admin.id, aksi="SCHEDULER_START", ip_address=ip)
        db.commit()
        return {"message": "APScheduler berhasil distart", "status": "running"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal start scheduler: {str(e)}")


# ─── POST /admin/scheduler/stop ───────────────────────────────

@router.post("/scheduler/stop")
def stop_scheduler(
    request: Request,
    admin  : User    = Depends(require_admin),
    db     : Session = Depends(get_db),
):
    """
    Stop APScheduler (untuk keperluan maintenance).
    PERHATIAN: Sesi tidak akan ditutup otomatis saat scheduler berhenti.
    """
    try:
        from app.scheduler import stop_scheduler as _stop
        _stop()
        ip = request.client.host if request.client else None
        audit_service.catat(db, admin.id, aksi="SCHEDULER_STOP", ip_address=ip)
        db.commit()
        return {"message": "APScheduler berhasil dihentikan", "status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal stop scheduler: {str(e)}")