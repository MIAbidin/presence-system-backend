# app/routers/presensi.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.database.db import get_db
from app.models.user import User, UserRole
from app.models.presensi import Presensi, PresensiStatus
from app.models.sesi import SesiPresensi
from app.schemas.presensi import (
    PresensiRequest, PresensiResponse,
    UbahStatusRequest, RiwayatItemResponse
)
from app.services import presensi_service
from app.utils.image_utils import resize_image
from app.utils.export_utils import generate_excel_rekap
from app.routers.auth import get_current_user

router = APIRouter(prefix="/presensi", tags=["Presensi"])

ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png"}


def require_mahasiswa(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.mahasiswa:
        raise HTTPException(status_code=403, detail="Endpoint ini hanya untuk mahasiswa")
    return current_user


def require_dosen(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.dosen:
        raise HTTPException(status_code=403, detail="Endpoint ini hanya untuk dosen")
    return current_user


# ─── POST /presensi ───────────────────────────────────────

@router.post("", response_model=PresensiResponse)
async def lakukan_presensi(
    req        : PresensiRequest = Depends(),
    foto       : UploadFile = File(..., description="Foto wajah JPEG/PNG"),
    mahasiswa  : User = Depends(require_mahasiswa),
    db         : Session = Depends(get_db)
):
    """
    Endpoint utama presensi mahasiswa.
    - Mode offline: sertakan latitude & longitude
    - Mode online : sertakan kode_sesi 6 karakter
    Foto wajah wajib disertakan (multipart/form-data).
    """
    if foto.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Format file tidak didukung, gunakan JPEG atau PNG")

    image_bytes = await foto.read()
    if len(image_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Ukuran foto maksimal 5MB")

    image_bytes = resize_image(image_bytes)

    success, pesan, presensi = presensi_service.proses_presensi(
        db          = db,
        mahasiswa   = mahasiswa,
        sesi_id     = req.sesi_id,
        image_bytes = image_bytes,
        kode_sesi   = req.kode_sesi,
        latitude    = req.latitude,
        longitude   = req.longitude,
    )

    if not success:
        raise HTTPException(status_code=400, detail=pesan)

    return PresensiResponse(
        id             = presensi.id,
        status         = presensi.status.value,
        waktu_presensi = presensi.waktu_presensi,
        akurasi_wajah  = presensi.akurasi_wajah,
        mode_kelas     = presensi.mode_kelas.value,
        pesan          = pesan,
    )


# ─── GET /presensi/riwayat ────────────────────────────────

@router.get("/riwayat")
def get_riwayat(
    matakuliah_id : Optional[UUID] = None,
    mahasiswa     : User = Depends(require_mahasiswa),
    db            : Session = Depends(get_db)
):
    """
    Riwayat kehadiran mahasiswa yang sedang login.
    Opsional: filter dengan ?matakuliah_id=uuid
    """
    riwayat = presensi_service.get_riwayat_mahasiswa(db, mahasiswa.id, matakuliah_id)

    # Serialize manual karena butuh data dari relasi sesi
    result = []
    for p in riwayat:
        result.append({
            "id"            : str(p.id),
            "sesi_id"       : str(p.sesi_id),
            "pertemuan_ke"  : p.sesi.pertemuan_ke if p.sesi else None,
            "matakuliah"    : p.sesi.matakuliah.nama if p.sesi and p.sesi.matakuliah else "-",
            "status"        : p.status.value,
            "waktu_presensi": p.waktu_presensi.isoformat() if p.waktu_presensi else None,
            "akurasi_wajah" : p.akurasi_wajah,
            "mode_kelas"    : p.mode_kelas.value,
            "catatan"       : p.catatan,
        })

    # Hitung statistik per matakuliah
    statistik = presensi_service.hitung_persentase(riwayat)

    return {
        "total_pertemuan": len(riwayat),
        "statistik"      : statistik,
        "riwayat"        : result,
    }


# ─── GET /presensi/rekap/{sesi_id} ───────────────────────

@router.get("/rekap/{sesi_id}")
def get_rekap_sesi(
    sesi_id : UUID,
    dosen   : User = Depends(require_dosen),
    db      : Session = Depends(get_db)
):
    """Dosen lihat rekap lengkap satu sesi beserta statistik."""
    sesi = db.query(SesiPresensi).filter(SesiPresensi.id == sesi_id).first()
    if not sesi:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")

    presensi_list = presensi_service.get_rekap_sesi(db, sesi_id)
    statistik     = presensi_service.hitung_persentase(presensi_list)

    detail = [{
        "presensi_id"   : str(p.id),
        "mahasiswa_id"  : str(p.mahasiswa_id),
        "nim"           : p.mahasiswa.nim_nidn if p.mahasiswa else "-",
        "nama"          : p.mahasiswa.nama_lengkap if p.mahasiswa else "-",
        "status"        : p.status.value,
        "waktu_presensi": p.waktu_presensi.isoformat() if p.waktu_presensi else None,
        "akurasi_wajah" : p.akurasi_wajah,
        "mode_kelas"    : p.mode_kelas.value,
        "catatan"       : p.catatan,
        "diubah_oleh"   : str(p.diubah_oleh) if p.diubah_oleh else None,
    } for p in presensi_list]

    return {
        "sesi_id"       : str(sesi_id),
        "matakuliah"    : sesi.matakuliah.nama if sesi.matakuliah else "-",
        "pertemuan_ke"  : sesi.pertemuan_ke,
        "mode"          : sesi.mode.value,
        "waktu_buka"    : sesi.waktu_buka.isoformat(),
        "waktu_tutup"   : sesi.waktu_tutup.isoformat() if sesi.waktu_tutup else None,
        "statistik"     : statistik,
        "detail"        : detail,
    }


# ─── GET /presensi/rekap/{sesi_id}/export ────────────────

@router.get("/rekap/{sesi_id}/export")
def export_rekap_excel(
    sesi_id : UUID,
    dosen   : User = Depends(require_dosen),
    db      : Session = Depends(get_db)
):
    """
    Export rekap presensi satu sesi ke file Excel (.xlsx).
    File langsung didownload oleh client.
    """
    sesi = db.query(SesiPresensi).filter(SesiPresensi.id == sesi_id).first()
    if not sesi:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")

    presensi_list = presensi_service.get_rekap_sesi(db, sesi_id)

    nama_matakuliah = sesi.matakuliah.nama if sesi.matakuliah else "Matakuliah"
    nama_dosen      = dosen.nama_lengkap

    excel_bytes = generate_excel_rekap(
        presensi_list   = presensi_list,
        nama_matakuliah = nama_matakuliah,
        pertemuan_ke    = sesi.pertemuan_ke,
        nama_dosen      = nama_dosen,
        tanggal_sesi    = sesi.waktu_buka,
        mode_kelas      = sesi.mode.value,
    )

    filename = f"presensi_{nama_matakuliah.replace(' ', '_')}_pertemuan{sesi.pertemuan_ke}.xlsx"

    return Response(
        content     = excel_bytes,
        media_type  = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers     = {"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── PATCH /presensi/ubah-status (dosen) ─────────────────

@router.patch("/ubah-status")
def ubah_status(
    req   : UbahStatusRequest,
    dosen : User = Depends(require_dosen),
    db    : Session = Depends(get_db)
):
    """
    Dosen ubah status kehadiran mahasiswa secara manual.
    Contoh: Absen → Izin dengan keterangan.
    """
    success, pesan = presensi_service.ubah_status_manual(
        db          = db,
        presensi_id = req.presensi_id,
        dosen_id    = dosen.id,
        status_baru = req.status_baru,
        catatan     = req.catatan,
    )
    if not success:
        raise HTTPException(status_code=400, detail=pesan)
    return {"message": pesan}