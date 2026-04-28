"""
app/routers/sesi.py
════════════════════
Update Fase 2:
- BukaSesiRequest: tambah mulai_dari_jam_jadwal dan batas_terlambat opsional (None)
- Endpoint GET /sesi/aktif-dosen tetap ada
- Endpoint GET /sesi/cek-kode tetap ada
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.database.db import get_db
from app.models.user import User
from app.models.sesi import SesiPresensi, SesiStatus, SesiMode
from app.models.presensi import Presensi, PresensiStatus
from app.schemas.sesi import BukaSesiRequest, SesiResponse, ExtendKodeRequest
from app.services import sesi_service
from app.routers.auth import get_current_user

router = APIRouter(prefix="/sesi", tags=["Manajemen Sesi"])


def require_dosen(current_user: User = Depends(get_current_user)):
    if current_user.role.value != "dosen":
        raise HTTPException(
            status_code=403,
            detail="Hanya dosen yang dapat mengelola sesi"
        )
    return current_user


# ─── POST /sesi/buka ──────────────────────────────────────────

@router.post("/buka", response_model=SesiResponse)
def buka_sesi(
    req  : BukaSesiRequest,
    dosen: User    = Depends(require_dosen),
    db   : Session = Depends(get_db)
):
    """
    Dosen membuka sesi presensi baru (offline atau online).

    Fase 2.1: mulai_dari_jam_jadwal=True → waktu_buka diambil dari jam_mulai
    matakuliah hari ini (bukan jam sekarang).

    Fase 2.3: batas_terlambat_menit=None → tidak ada batas terlambat,
    semua presensi selama sesi aktif = Hadir.
    """
    try:
        sesi = sesi_service.buka_sesi(
            db                    = db,
            dosen_id              = dosen.id,
            matakuliah_id         = req.matakuliah_id,
            mode                  = req.mode,
            pertemuan_ke          = req.pertemuan_ke,
            batas_terlambat_menit = req.batas_terlambat_menit,
            durasi_menit          = req.durasi_menit,
            mulai_dari_jam_jadwal = req.mulai_dari_jam_jadwal,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    detik = sesi_service.hitung_detik_tersisa(sesi)
    return SesiResponse(
        id             = sesi.id,
        mode           = sesi.mode.value,
        kode_sesi      = sesi.kode_sesi,
        kode_expire_at = sesi.kode_expire_at,
        pertemuan_ke   = sesi.pertemuan_ke,
        waktu_buka     = sesi.waktu_buka,
        status         = sesi.status.value,
        detik_tersisa  = detik,
        batas_terlambat_menit = (
            int(sesi.batas_terlambat.total_seconds() // 60)
            if sesi.batas_terlambat else None
        ),
    )


# ─── POST /sesi/tutup ─────────────────────────────────────────

@router.post("/tutup")
def tutup_sesi(
    sesi_id: UUID,
    dosen  : User    = Depends(require_dosen),
    db     : Session = Depends(get_db)
):
    """Dosen menutup sesi manual. Kode online langsung hangus."""
    success, pesan = sesi_service.tutup_sesi(db, sesi_id, dosen.id)
    if not success:
        raise HTTPException(status_code=404, detail=pesan)
    return {"message": pesan}


# ─── POST /sesi/extend ────────────────────────────────────────

@router.post("/extend", response_model=SesiResponse)
def extend_kode(
    req  : ExtendKodeRequest,
    dosen: User    = Depends(require_dosen),
    db   : Session = Depends(get_db)
):
    """Dosen perpanjang durasi kode tanpa generate kode baru."""
    success, pesan, sesi = sesi_service.extend_kode(
        db, req.sesi_id, dosen.id, req.tambahan_menit
    )
    if not success:
        raise HTTPException(status_code=400, detail=pesan)

    detik = sesi_service.hitung_detik_tersisa(sesi)
    return SesiResponse(
        id=sesi.id, mode=sesi.mode.value, kode_sesi=sesi.kode_sesi,
        kode_expire_at=sesi.kode_expire_at, pertemuan_ke=sesi.pertemuan_ke,
        waktu_buka=sesi.waktu_buka, status=sesi.status.value,
        detik_tersisa=detik,
        batas_terlambat_menit=None,
    )


# ─── POST /sesi/regen-kode ────────────────────────────────────

@router.post("/regen-kode", response_model=SesiResponse)
def regen_kode(
    sesi_id     : UUID,
    durasi_menit: int = 30,
    dosen       : User    = Depends(require_dosen),
    db          : Session = Depends(get_db)
):
    """Dosen generate kode baru — kode lama LANGSUNG hangus."""
    success, pesan, sesi = sesi_service.regen_kode(db, sesi_id, dosen.id, durasi_menit)
    if not success:
        raise HTTPException(status_code=400, detail=pesan)

    detik = sesi_service.hitung_detik_tersisa(sesi)
    return SesiResponse(
        id=sesi.id, mode=sesi.mode.value, kode_sesi=sesi.kode_sesi,
        kode_expire_at=sesi.kode_expire_at, pertemuan_ke=sesi.pertemuan_ke,
        waktu_buka=sesi.waktu_buka, status=sesi.status.value,
        detik_tersisa=detik,
        batas_terlambat_menit=None,
    )


# ─── GET /sesi/cek-kode ───────────────────────────────────────

@router.get("/cek-kode")
def cek_kode_sesi(
    kode        : str,
    current_user: User    = Depends(get_current_user),
    db          : Session = Depends(get_db),
):
    """
    Mahasiswa cek apakah kode sesi valid sebelum scan wajah.
    Endpoint: GET /sesi/cek-kode?kode=A7X3K2
    """
    valid, pesan, sesi = sesi_service.validasi_kode(db, kode, current_user.id)
    if not valid:
        raise HTTPException(status_code=400, detail=pesan)

    return {
        "ada_sesi": True,
        "pesan"   : "Kode valid",
        "sesi": {
            "id"           : str(sesi.id),
            "mode"         : sesi.mode.value,
            "matakuliah_id": str(sesi.matakuliah_id),
            "matakuliah"   : sesi.matakuliah.nama if sesi.matakuliah else "-",
            "pertemuan_ke" : sesi.pertemuan_ke,
            "waktu_buka"   : sesi.waktu_buka.isoformat() if sesi.waktu_buka else None,
            "detik_tersisa": sesi_service.hitung_detik_tersisa(sesi),
        }
    }


# ─── GET /sesi/aktif ──────────────────────────────────────────

@router.get("/aktif")
def cek_sesi_aktif(
    matakuliah_id: UUID,
    db           : Session = Depends(get_db),
    _            : User    = Depends(get_current_user)
):
    """Mahasiswa cek apakah ada sesi aktif untuk matakuliahnya."""
    sesi = sesi_service.get_sesi_aktif(db, matakuliah_id)
    if not sesi:
        return {"ada_sesi": False, "sesi": None}

    return {
        "ada_sesi": True,
        "sesi": {
            "id"          : str(sesi.id),
            "mode"        : sesi.mode.value,
            "waktu_buka"  : sesi.waktu_buka.isoformat() if sesi.waktu_buka else None,
            "detik_tersisa": sesi_service.hitung_detik_tersisa(sesi),
        }
    }


# ─── GET /sesi/aktif-dosen ────────────────────────────────────

@router.get("/aktif-dosen")
def get_sesi_aktif_dosen(
    dosen: User    = Depends(require_dosen),
    db   : Session = Depends(get_db)
):
    """Ambil semua sesi aktif yang dibuat oleh dosen yang sedang login."""
    from app.models.matakuliah import Matakuliah
    sesi_list = db.query(SesiPresensi).filter(
        SesiPresensi.dosen_id == dosen.id,
        SesiPresensi.status   == SesiStatus.aktif
    ).order_by(SesiPresensi.waktu_buka.desc()).all()

    result = []
    for sesi in sesi_list:
        mk = db.query(Matakuliah).filter(Matakuliah.id == sesi.matakuliah_id).first()
        result.append({
            "id"          : str(sesi.id),
            "mode"        : sesi.mode.value,
            "kode_sesi"   : sesi.kode_sesi,
            "pertemuan_ke": sesi.pertemuan_ke,
            "waktu_buka"  : sesi.waktu_buka.isoformat(),
            "matakuliah"  : mk.nama if mk else "-",
            "detik_tersisa": sesi_service.hitung_detik_tersisa(sesi),
        })

    return {"sesi_list": result}


# ─── GET /sesi/{sesi_id}/peserta ──────────────────────────────

@router.get("/{sesi_id}/peserta")
def get_peserta(
    sesi_id: UUID,
    dosen  : User    = Depends(require_dosen),
    db     : Session = Depends(get_db)
):
    """
    Dosen lihat daftar hadir real-time.
    Update Fase 3.6: return nama, NIM, is_tamu, kelas_asal.
    Dipolling setiap 5 detik dari dashboard dosen.
    """
    sesi = db.query(SesiPresensi).filter(SesiPresensi.id == sesi_id).first()
    if not sesi:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")

    presensi_list = db.query(Presensi).filter(Presensi.sesi_id == sesi_id).all()

    hadir     = sum(1 for p in presensi_list if p.status == PresensiStatus.hadir)
    terlambat = sum(1 for p in presensi_list if p.status == PresensiStatus.terlambat)
    absen     = sum(1 for p in presensi_list if p.status == PresensiStatus.absen)

    detail = []
    for p in presensi_list:
        mhs = p.mahasiswa
        # Ambil info tamu dari mahasiswa_matakuliah
        from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
        mk_row = db.query(MahasiswaMatakuliah).filter(
            MahasiswaMatakuliah.mahasiswa_id  == p.mahasiswa_id,
            MahasiswaMatakuliah.matakuliah_id == sesi.matakuliah_id,
        ).first()

        detail.append({
            "presensi_id"   : str(p.id),
            "mahasiswa_id"  : str(p.mahasiswa_id),
            "nim"           : mhs.nim_nidn      if mhs else "-",
            "nama"          : mhs.nama_lengkap  if mhs else "-",
            "status"        : p.status.value,
            "waktu_presensi": p.waktu_presensi.isoformat() if p.waktu_presensi else None,
            "akurasi_wajah" : p.akurasi_wajah,
            "mode_kelas"    : p.mode_kelas.value,
            "catatan"       : p.catatan,
            # Fase 2.4: info tamu
            "is_tamu"       : mk_row.is_tamu    if mk_row else False,
            "kelas_asal"    : mk_row.kelas_asal if mk_row else None,
        })

    return {
        "sesi_id"   : str(sesi_id),
        "ringkasan" : {
            "hadir"    : hadir,
            "terlambat": terlambat,
            "absen"    : absen,
        },
        "detail": detail,
    }