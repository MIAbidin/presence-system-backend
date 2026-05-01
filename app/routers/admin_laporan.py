# app/routers/admin_laporan.py
"""
Fase 10 — Laporan Global endpoints.
Diregistrasi di app/main.py sebagai router terpisah.

Endpoints:
  GET /admin/laporan                    — rekap global dengan filter
  GET /admin/laporan/detail             — detail satu sesi atau semua sesi satu MK
  GET /admin/laporan/export/excel       — download Excel
  GET /admin/laporan/export/pdf         — download PDF
  GET /admin/laporan/mahasiswa/{user_id} — rekap satu mahasiswa
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import date
from typing import Optional

from app.database.db import get_db
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.services import laporan_service

router = APIRouter(prefix="/admin/laporan", tags=["Admin — Laporan"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Endpoint ini hanya untuk admin kampus")
    return current_user


# ─── GET /admin/laporan ───────────────────────────────────────

@router.get("")
def get_laporan_global(
    matakuliah_id   : Optional[UUID] = Query(None, description="Filter by matakuliah UUID"),
    dosen_id        : Optional[UUID] = Query(None, description="Filter by dosen UUID"),
    program_studi   : Optional[str]  = Query(None, description="Filter by program studi mahasiswa"),
    periode_mulai   : Optional[date] = Query(None, description="Tanggal mulai periode (YYYY-MM-DD)"),
    periode_selesai : Optional[date] = Query(None, description="Tanggal selesai periode (YYYY-MM-DD)"),
    mode            : Optional[str]  = Query(None, description="offline | online"),
    page            : int            = Query(1,    ge=1),
    limit           : int            = Query(20,   ge=1, le=100),
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    """
    Rekap kehadiran global per matakuliah.

    Setiap item menampilkan:
    - Info matakuliah + dosen utama
    - Total pertemuan (sesi selesai)
    - Statistik kehadiran: hadir, terlambat, absen, izin, sakit
    - Persentase kehadiran efektif

    Diurutkan dari persentase kehadiran terendah (butuh perhatian lebih).
    """
    return laporan_service.get_laporan_global(
        db,
        matakuliah_id  = matakuliah_id,
        dosen_id       = dosen_id,
        program_studi  = program_studi,
        periode_mulai  = periode_mulai,
        periode_selesai= periode_selesai,
        mode           = mode,
        page           = page,
        limit          = limit,
    )


# ─── GET /admin/laporan/detail ────────────────────────────────

@router.get("/detail")
def get_laporan_detail(
    matakuliah_id: Optional[UUID] = Query(None, description="UUID matakuliah"),
    sesi_id      : Optional[UUID] = Query(None, description="UUID sesi — jika diisi, tampilkan detail satu sesi"),
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    """
    Detail laporan.

    Mode 1 — sesi_id diisi:
      Return daftar lengkap mahasiswa beserta status presensinya di sesi tsb.

    Mode 2 — matakuliah_id diisi (tanpa sesi_id):
      Return semua sesi MK tersebut beserta statistik per pertemuan.
    """
    if not matakuliah_id and not sesi_id:
        raise HTTPException(
            status_code=400,
            detail="Berikan matakuliah_id atau sesi_id"
        )

    result = laporan_service.get_laporan_detail(db, matakuliah_id, sesi_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ─── GET /admin/laporan/export/excel ─────────────────────────

@router.get("/export/excel")
def export_excel(
    matakuliah_id   : Optional[UUID] = Query(None),
    dosen_id        : Optional[UUID] = Query(None),
    program_studi   : Optional[str]  = Query(None),
    periode_mulai   : Optional[date] = Query(None),
    periode_selesai : Optional[date] = Query(None),
    mode            : Optional[str]  = Query(None),
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    """
    Export laporan rekap global ke file Excel (.xlsx).
    File langsung didownload oleh browser.
    """
    excel_bytes = laporan_service.export_laporan_excel(
        db,
        matakuliah_id  = matakuliah_id,
        dosen_id       = dosen_id,
        program_studi  = program_studi,
        periode_mulai  = periode_mulai,
        periode_selesai= periode_selesai,
        mode           = mode,
    )

    # Build filename dinamis
    parts = ["laporan_kehadiran"]
    if periode_mulai:
        parts.append(periode_mulai.strftime("%Y%m%d"))
    if periode_selesai:
        parts.append(f"sd{periode_selesai.strftime('%Y%m%d')}")
    filename = "_".join(parts) + ".xlsx"

    return Response(
        content     = excel_bytes,
        media_type  = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers     = {"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── GET /admin/laporan/export/pdf ───────────────────────────

@router.get("/export/pdf")
def export_pdf(
    matakuliah_id   : Optional[UUID] = Query(None),
    dosen_id        : Optional[UUID] = Query(None),
    program_studi   : Optional[str]  = Query(None),
    periode_mulai   : Optional[date] = Query(None),
    periode_selesai : Optional[date] = Query(None),
    mode            : Optional[str]  = Query(None),
    admin: User    = Depends(require_admin),
    db   : Session = Depends(get_db),
):
    """
    Export laporan rekap global ke PDF.
    File langsung didownload oleh browser.
    """
    try:
        pdf_bytes = laporan_service.export_laporan_pdf(
            db,
            matakuliah_id  = matakuliah_id,
            dosen_id       = dosen_id,
            program_studi  = program_studi,
            periode_mulai  = periode_mulai,
            periode_selesai= periode_selesai,
            mode           = mode,
        )
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="reportlab belum terinstall. Jalankan: pip install reportlab"
        )

    parts = ["laporan_kehadiran"]
    if periode_mulai:
        parts.append(periode_mulai.strftime("%Y%m%d"))
    filename = "_".join(parts) + ".pdf"

    return Response(
        content    = pdf_bytes,
        media_type = "application/pdf",
        headers    = {"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── GET /admin/laporan/mahasiswa/{user_id} ───────────────────

@router.get("/mahasiswa/{user_id}")
def get_laporan_mahasiswa(
    user_id: UUID,
    admin  : User    = Depends(require_admin),
    db     : Session = Depends(get_db),
):
    """
    Rekap kehadiran satu mahasiswa di seluruh matakuliah yang pernah diikuti.

    Response berisi:
    - Data diri mahasiswa
    - Statistik global (total seluruh MK)
    - Detail per matakuliah: persentase, riwayat per pertemuan
    """
    result = laporan_service.get_laporan_mahasiswa(db, user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result