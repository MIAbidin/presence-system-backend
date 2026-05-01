# app/routers/admin_import.py
"""
Fase 9 — Import Data Massal endpoints.
Diregistrasi di app/main.py sebagai router terpisah agar
file admin.py tidak terlalu panjang.

Endpoints:
  POST /admin/import/mahasiswa          — import dari Excel
  POST /admin/import/dosen              — import dari Excel
  POST /admin/import/preview/mahasiswa  — preview tanpa insert
  POST /admin/import/preview/dosen      — preview tanpa insert
  GET  /admin/import/template/mahasiswa — download template Excel
  GET  /admin/import/template/dosen     — download template Excel
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.services import import_service

router = APIRouter(prefix="/admin/import", tags=["Admin — Import"])

ALLOWED_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/octet-stream",   # beberapa browser kirim ini untuk .xlsx
}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Endpoint ini hanya untuk admin kampus")
    return current_user


# ─── GET /admin/import/template/mahasiswa ────────────────────

@router.get("/template/mahasiswa")
def download_template_mahasiswa(
    _: User = Depends(require_admin),
):
    """Download template Excel kosong untuk import mahasiswa."""
    excel_bytes = import_service.generate_template_mahasiswa()
    return Response(
        content    = excel_bytes,
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers    = {
            "Content-Disposition": 'attachment; filename="template_import_mahasiswa.xlsx"'
        },
    )


# ─── GET /admin/import/template/dosen ────────────────────────

@router.get("/template/dosen")
def download_template_dosen(
    _: User = Depends(require_admin),
):
    """Download template Excel kosong untuk import dosen."""
    excel_bytes = import_service.generate_template_dosen()
    return Response(
        content    = excel_bytes,
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers    = {
            "Content-Disposition": 'attachment; filename="template_import_dosen.xlsx"'
        },
    )


# ─── POST /admin/import/preview/mahasiswa ────────────────────

@router.post("/preview/mahasiswa")
async def preview_import_mahasiswa(
    file: UploadFile = File(..., description="File Excel (.xlsx)"),
    _   : User       = Depends(require_admin),
):
    """
    Preview 5 baris pertama dari file Excel mahasiswa TANPA insert ke DB.
    Digunakan frontend untuk konfirmasi sebelum import sesungguhnya.
    """
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Ukuran file maksimal 5MB")

    try:
        result = import_service.preview_excel(file_bytes, "mahasiswa")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Gagal membaca file Excel: {str(e)}. Pastikan format file benar (.xlsx)"
        )

    return result


# ─── POST /admin/import/preview/dosen ────────────────────────

@router.post("/preview/dosen")
async def preview_import_dosen(
    file: UploadFile = File(..., description="File Excel (.xlsx)"),
    _   : User       = Depends(require_admin),
):
    """Preview 5 baris pertama dari file Excel dosen TANPA insert ke DB."""
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Ukuran file maksimal 5MB")

    try:
        result = import_service.preview_excel(file_bytes, "dosen")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Gagal membaca file Excel: {str(e)}. Pastikan format file benar (.xlsx)"
        )

    return result


# ─── POST /admin/import/mahasiswa ────────────────────────────

@router.post("/mahasiswa")
async def import_mahasiswa(
    file: UploadFile = File(..., description="File Excel (.xlsx)"),
    _   : User       = Depends(require_admin),
    db  : Session    = Depends(get_db),
):
    """
    Import data mahasiswa dari file Excel secara massal.

    Format Excel:
    - Baris 4: Header (NIM, Nama Lengkap, Email, Password, Program Studi, Keterangan)
    - Baris 5: Hint/contoh (dilewati)
    - Baris 6+: Data mahasiswa

    Return:
    - total: jumlah baris yang diproses
    - berhasil: jumlah yang berhasil diinsert
    - gagal: jumlah yang gagal
    - errors: detail baris yang gagal
    - preview: 5 baris pertama yang berhasil
    """
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Ukuran file maksimal 5MB")
    if len(file_bytes) < 100:
        raise HTTPException(status_code=400, detail="File terlalu kecil atau kosong")

    try:
        result = import_service.import_mahasiswa(db, file_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Gagal memproses file Excel: {str(e)}. Pastikan format file benar (.xlsx)"
        )

    return result


# ─── POST /admin/import/dosen ────────────────────────────────

@router.post("/dosen")
async def import_dosen(
    file: UploadFile = File(..., description="File Excel (.xlsx)"),
    _   : User       = Depends(require_admin),
    db  : Session    = Depends(get_db),
):
    """
    Import data dosen dari file Excel secara massal.

    Format sama dengan import mahasiswa, bedanya role = dosen
    dan kolom pertama adalah NIDN (bukan NIM).
    """
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Ukuran file maksimal 5MB")
    if len(file_bytes) < 100:
        raise HTTPException(status_code=400, detail="File terlalu kecil atau kosong")

    try:
        result = import_service.import_dosen(db, file_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Gagal memproses file Excel: {str(e)}. Pastikan format file benar (.xlsx)"
        )

    return result