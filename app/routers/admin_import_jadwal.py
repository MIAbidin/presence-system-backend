# app/routers/admin_import_jadwal.py
"""
Fase C — Endpoint import jadwal dari PDF/Excel kampus.
Diregistrasi di app/main.py sebagai router terpisah.

Endpoints:
  POST /admin/import/jadwal/preview  — upload PDF/Excel, parse, return preview tanpa insert
  POST /admin/import/jadwal          — upload PDF/Excel, parse, insert ke kelas_matakuliah
  GET  /admin/import/template/jadwal — download template Excel jadwal
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.services.jadwal_parser import parse_jadwal_file
from app.services.import_jadwal_service import (
    preview_import_jadwal,
    import_jadwal,
)
from app.services.jadwal_parser import generate_template_jadwal

router = APIRouter(prefix="/admin/import", tags=["Admin — Import Jadwal"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB (PDF bisa lebih besar dari Excel)


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Endpoint ini hanya untuk admin kampus")
    return current_user


# ─── GET /admin/import/template/jadwal ───────────────────────

@router.get("/template/jadwal")
def download_template_jadwal(
    _: User = Depends(require_admin),
):
    """
    Download template Excel untuk import jadwal.

    Kolom template:
    - Hari       : Senin / Selasa / Rabu / Kamis / Jumat / Sabtu
    - Ruangan *  : kode ruangan (J.Int.1, LABRPL, J0403, dst)
    - Slot *     : format '1-3', '7-8' (lihat mapping slot di sistem)
    - Kode MK *  : kode matakuliah (TIF3221308, SI2234567, dst)
    - Nama MK    : nama lengkap matakuliah (opsional jika MK sudah ada)
    - Dosen      : nama dosen (sistem cari otomatis via fuzzy match)
    - Kelas *    : A / B / C / X (bisa lebih dari 1, pisah koma)
    - Kode Akses : URL Google Classroom atau kode WA (opsional)

    Tips:
    - Kolom Hari bisa diisi sekali per blok hari, kosongkan baris berikutnya
    - Kelas bisa diisi "A,B" untuk membuat 2 kelas sekaligus dari 1 baris
    - Jika MK belum ada di sistem, akan dibuat otomatis dengan SKS default 3
    - Jika Ruangan belum ada, akan dibuat otomatis dengan kode tersebut
    - Jika Dosen tidak match nama di sistem, kelas tetap dibuat tapi tanpa dosen (warning)
    """
    excel_bytes = generate_template_jadwal()
    return Response(
        content    = excel_bytes,
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers    = {
            "Content-Disposition": 'attachment; filename="template_import_jadwal.xlsx"'
        },
    )


# ─── POST /admin/import/jadwal/preview ───────────────────────

@router.post("/jadwal/preview")
async def preview_jadwal(
    file : UploadFile = File(..., description="File PDF (.pdf) atau Excel (.xlsx/.xls)"),
    _    : User       = Depends(require_admin),
    db   : Session    = Depends(get_db),
):
    """
    Preview hasil parsing jadwal TANPA insert ke DB.

    Mendukung format file:
    - PDF : file jadwal kampus dalam format tabel (misal Jadwal_TIF_Gasal_2024_2025.pdf)
    - Excel : file jadwal dalam format .xlsx atau .xls

    Response berisi:
    - total    : jumlah baris yang berhasil di-parse
    - preview  : list hasil parsing (maks 50 baris)
    - counts   : { baru, diupdate, warning, error }
    - pesan    : ringkasan

    Setiap item preview berisi:
    - status        : 'baru' | 'diupdate' | 'warning' | 'error'
    - kode_mk       : kode matakuliah
    - nama_mk       : nama matakuliah
    - kode_kelas    : kode kelas (A/B/C/X)
    - hari          : hari kuliah
    - slot          : string slot (1-3, 7-8, dst)
    - jam           : jam hasil konversi slot (07:00 – 09:30)
    - kode_ruangan  : kode ruangan
    - dosen         : nama dosen dari file
    - dosen_matched : nama dosen yang ditemukan di sistem (null jika tidak match)
    - kode_akses    : URL atau kode WA
    - pesan         : keterangan status baris ini

    Status 'warning' artinya kelas akan tetap dibuat tapi dosen tidak match sistem.
    Perlu cross-check nama dosen di file dengan data di sistem.

    CATATAN: File PDF jadwal asli kampus mungkin memiliki variasi format.
    Pastikan hasil preview sudah benar sebelum melanjutkan ke import sesungguhnya.
    """
    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="File kosong")

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Ukuran file maksimal {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    filename = file.filename or "upload"

    try:
        parsed_rows = parse_jadwal_file(file_bytes, filename)
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e) + ". Hubungi admin IT untuk install dependency."
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Gagal membaca file: {str(e)}. "
                   "Pastikan file tidak terpassword dan format sesuai."
        )

    if not parsed_rows:
        raise HTTPException(
            status_code=422,
            detail=(
                "Parser tidak menemukan data jadwal dalam file ini. "
                "Kemungkinan format file berbeda dari yang didukung sistem. "
                "Coba gunakan template Excel yang tersedia di "
                "GET /admin/import/template/jadwal."
            )
        )

    return preview_import_jadwal(db, parsed_rows)


# ─── POST /admin/import/jadwal ────────────────────────────────

@router.post("/jadwal")
async def import_jadwal_endpoint(
    file : UploadFile = File(..., description="File PDF (.pdf) atau Excel (.xlsx/.xls)"),
    _    : User       = Depends(require_admin),
    db   : Session    = Depends(get_db),
):
    """
    Import jadwal ke database dari file PDF atau Excel.

    Proses per baris:
    1. Cari Matakuliah berdasarkan kode_mk
       → Jika tidak ada: buat otomatis dengan SKS default 3
    2. Cari Dosen berdasarkan nama (fuzzy match ILIKE)
       → Jika tidak match: kelas tetap dibuat tanpa dosen (status warning)
    3. Cari Ruangan berdasarkan kode_ruangan
       → Jika tidak ada: buat otomatis (nama = kode)
    4. Upsert KelasMatakuliah:
       → INSERT jika kelas belum ada (kode_mk + kode_kelas unik)
       → UPDATE jika sudah ada (update dosen/ruangan/slot/hari)

    Response:
    - total    : jumlah baris yang diproses
    - berhasil : jumlah kelas yang berhasil dibuat (termasuk warning)
    - diupdate : jumlah kelas yang diupdate (sudah ada sebelumnya)
    - warning  : jumlah kelas dibuat tapi dosen tidak match
    - error    : jumlah baris yang gagal (skip, tidak mempengaruhi baris lain)
    - errors   : detail baris yang gagal
    - preview  : contoh 10 kelas yang berhasil diimport
    - pesan    : ringkasan

    REKOMENDASI ALUR:
    1. Preview dulu dengan POST /admin/import/jadwal/preview
    2. Cek warning — update nama dosen di file jika perlu
    3. Baru jalankan POST /admin/import/jadwal

    PENTING: Operasi ini tidak bisa di-rollback setelah berhasil.
    Pastikan hasil preview sudah sesuai sebelum import sesungguhnya.
    """
    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="File kosong")

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Ukuran file maksimal {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    filename = file.filename or "upload"

    try:
        parsed_rows = parse_jadwal_file(file_bytes, filename)
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=str(e) + ". Hubungi admin IT untuk install dependency."
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Gagal membaca file: {str(e)}"
        )

    if not parsed_rows:
        raise HTTPException(
            status_code=422,
            detail=(
                "Parser tidak menemukan data jadwal dalam file ini. "
                "Coba gunakan template Excel: GET /admin/import/template/jadwal."
            )
        )

    try:
        result = import_jadwal(db, parsed_rows)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result