# app/routers/mahasiswa.py
"""
Endpoint khusus mahasiswa:
  GET /mahasiswa/home-summary   — semua data beranda dalam 1 request
  GET /mahasiswa/profil         — data profil + face status
  PATCH /mahasiswa/fcm-token    — update FCM token saat app dibuka
  GET /mahasiswa/matakuliah     — daftar matakuliah yang diambil mahasiswa ini
  POST /mahasiswa/matakuliah/{mk_id}/daftar  — daftar ke matakuliah (admin/self)
  DELETE /mahasiswa/matakuliah/{mk_id}        — keluar dari matakuliah
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.database.db import get_db
from app.models.user import User, UserRole
from app.models.matakuliah import Matakuliah
from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
from app.models.face_embedding import FaceEmbedding
from app.routers.auth import get_current_user
from app.services import home_service
from app.schemas.home import HomeSummaryResponse

router = APIRouter(prefix="/mahasiswa", tags=["Mahasiswa"])


def require_mahasiswa(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.mahasiswa:
        raise HTTPException(status_code=403, detail="Endpoint ini hanya untuk mahasiswa")
    return current_user


# ─── GET /mahasiswa/home-summary ─────────────────────────────

@router.get("/home-summary", response_model=HomeSummaryResponse)
def home_summary(
    mahasiswa : User    = Depends(require_mahasiswa),
    db        : Session = Depends(get_db),
):
    """
    Satu endpoint yang mereturn semua data beranda:
    - Statistik kehadiran semester
    - Jadwal hari ini + status presensi
    - Sesi aktif yang belum diikuti mahasiswa
    - Jumlah presensi hari ini

    Flutter cukup hit 1 kali saat homepage dibuka.
    """
    return home_service.get_home_summary(db, mahasiswa)


# ─── GET /mahasiswa/profil ───────────────────────────────────

@router.get("/profil")
def get_profil(
    mahasiswa : User    = Depends(require_mahasiswa),
    db        : Session = Depends(get_db),
):
    """Data profil lengkap + jumlah foto wajah terdaftar."""
    total_foto = (
        db.query(FaceEmbedding)
        .filter(FaceEmbedding.user_id == mahasiswa.id)
        .count()
    )
    return {
        "id"               : str(mahasiswa.id),
        "nim"              : mahasiswa.nim_nidn,
        "nama_lengkap"     : mahasiswa.nama_lengkap,
        "email"            : mahasiswa.email,
        "program_studi"    : mahasiswa.program_studi,
        "is_face_registered": mahasiswa.is_face_registered,
        "total_foto_wajah" : total_foto,
        "foto_dibutuhkan"  : max(0, 8 - total_foto),
    }


# ─── PATCH /mahasiswa/fcm-token ──────────────────────────────

@router.patch("/fcm-token")
def update_fcm_token(
    token     : str,
    current_user: User    = Depends(get_current_user),
    db        : Session = Depends(get_db),
):
    """
    Simpan/perbarui FCM token perangkat.
    Dipanggil Flutter saat app pertama kali dibuka setelah login.
    """
    current_user.fcm_token = token
    db.commit()
    return {"message": "FCM token diperbarui"}


# ─── GET /mahasiswa/matakuliah ───────────────────────────────

@router.get("/matakuliah")
def get_matakuliah_saya(
    mahasiswa : User    = Depends(require_mahasiswa),
    db        : Session = Depends(get_db),
):
    """Daftar matakuliah yang diambil mahasiswa ini beserta info jadwal."""
    matakuliah_list = home_service.get_matakuliah_mahasiswa(db, mahasiswa.id)
    return [
        {
            "id"          : str(mk.id),
            "kode"        : mk.kode,
            "nama"        : mk.nama,
            "sks"         : mk.sks,
            "hari"        : mk.hari,
            "jam_mulai"   : mk.jam_mulai.strftime("%H:%M") if mk.jam_mulai else None,
            "jam_selesai" : mk.jam_selesai.strftime("%H:%M") if mk.jam_selesai else None,
            "ruangan"     : mk.ruangan,
            "koordinat_lat": mk.koordinat_lat,
            "koordinat_lng": mk.koordinat_lng,
        }
        for mk in matakuliah_list
    ]


# ─── POST /mahasiswa/matakuliah/{mk_id}/daftar ───────────────

@router.post("/matakuliah/{mk_id}/daftar")
def daftar_matakuliah(
    mk_id     : UUID,
    mahasiswa : User    = Depends(require_mahasiswa),
    db        : Session = Depends(get_db),
):
    """
    Daftarkan mahasiswa ke sebuah matakuliah.
    Bisa dipanggil sendiri oleh mahasiswa atau oleh admin via endpoint lain.
    """
    mk = db.query(Matakuliah).filter(Matakuliah.id == mk_id).first()
    if not mk:
        raise HTTPException(status_code=404, detail="Matakuliah tidak ditemukan")

    # Cek sudah terdaftar
    existing = (
        db.query(MahasiswaMatakuliah)
        .filter(
            MahasiswaMatakuliah.mahasiswa_id  == mahasiswa.id,
            MahasiswaMatakuliah.matakuliah_id == mk_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Sudah terdaftar di matakuliah ini")

    db.add(MahasiswaMatakuliah(mahasiswa_id=mahasiswa.id, matakuliah_id=mk_id))
    db.commit()
    return {"message": f"Berhasil terdaftar di {mk.nama}"}


# ─── DELETE /mahasiswa/matakuliah/{mk_id} ────────────────────

@router.delete("/matakuliah/{mk_id}")
def keluar_matakuliah(
    mk_id     : UUID,
    mahasiswa : User    = Depends(require_mahasiswa),
    db        : Session = Depends(get_db),
):
    """Hapus pendaftaran mahasiswa dari sebuah matakuliah."""
    row = (
        db.query(MahasiswaMatakuliah)
        .filter(
            MahasiswaMatakuliah.mahasiswa_id  == mahasiswa.id,
            MahasiswaMatakuliah.matakuliah_id == mk_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Tidak terdaftar di matakuliah ini")

    db.delete(row)
    db.commit()
    return {"message": "Berhasil keluar dari matakuliah"}
