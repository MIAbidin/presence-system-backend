"""
app/routers/admin.py
═════════════════════
Fase 3 — Router admin:
  GET /admin/dashboard   — statistik + grafik + scheduler status
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.services import admin_service
from fastapi import HTTPException

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency — pastikan hanya admin yang bisa akses."""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=403,
            detail="Endpoint ini hanya untuk admin kampus"
        )
    return current_user


# ─── GET /admin/dashboard ─────────────────────────────────────

@router.get("/dashboard")
def get_dashboard(
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    """
    Beranda admin — semua data statistik dalam satu request.

    Response:
    - total_mahasiswa, total_dosen, total_matakuliah
    - total_presensi_hari_ini, total_sesi_aktif, akurasi_rata_rata
    - grafik_kehadiran_7_hari: array [{tanggal, hadir, absen}]
    - distribusi_status: array [{status, jumlah, persen, warna}]
    - top_mk_kehadiran_terendah: array 5 MK [{kode, nama, persentase}]
    - scheduler_status: {running, status, jobs}
    """
    return admin_service.get_dashboard_stats(db)
