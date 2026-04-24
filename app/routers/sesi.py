from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.database.db import get_db
from app.models.user import User
from app.models.sesi import SesiPresensi, SesiStatus
from app.models.presensi import Presensi, PresensiStatus
from app.schemas.sesi import BukaSesiRequest, SesiResponse, ExtendKodeRequest
from app.services import sesi_service
from app.routers.auth import get_current_user

router = APIRouter(prefix="/sesi", tags=["Manajemen Sesi"])


def require_dosen(current_user: User = Depends(get_current_user)):
    """Dependency — pastikan yang mengakses adalah dosen."""
    if current_user.role.value != "dosen":
        raise HTTPException(status_code=403, detail="Hanya dosen yang dapat mengelola sesi")
    return current_user


# ─── POST /sesi/buka ──────────────────────────────────────

@router.post("/buka", response_model=SesiResponse)
def buka_sesi(
    req   : BukaSesiRequest,
    dosen : User = Depends(require_dosen),
    db    : Session = Depends(get_db)
):
    """
    Dosen membuka sesi presensi baru (offline atau online).
    Mode online: sistem otomatis generate kode + set timer.
    """
    try:
        sesi = sesi_service.buka_sesi(
            db                    = db,
            dosen_id              = dosen.id,
            matakuliah_id         = req.matakuliah_id,
            mode                  = req.mode,
            pertemuan_ke          = req.pertemuan_ke,
            batas_terlambat_menit = req.batas_terlambat,
            durasi_menit          = req.durasi_menit
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
        detik_tersisa  = detik
    )


# ─── POST /sesi/tutup ─────────────────────────────────────

@router.post("/tutup")
def tutup_sesi(
    sesi_id: UUID,
    dosen  : User = Depends(require_dosen),
    db     : Session = Depends(get_db)
):
    """Dosen menutup sesi. Kode online langsung hangus."""
    success, pesan = sesi_service.tutup_sesi(db, sesi_id, dosen.id)
    if not success:
        raise HTTPException(status_code=404, detail=pesan)
    return {"message": pesan}


# ─── POST /sesi/extend ────────────────────────────────────

@router.post("/extend", response_model=SesiResponse)
def extend_kode(
    req  : ExtendKodeRequest,
    dosen: User = Depends(require_dosen),
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
        waktu_buka=sesi.waktu_buka, status=sesi.status.value, detik_tersisa=detik
    )


# ─── POST /sesi/regen-kode ────────────────────────────────

@router.post("/regen-kode", response_model=SesiResponse)
def regen_kode(
    sesi_id     : UUID,
    durasi_menit: int = 30,
    dosen       : User = Depends(require_dosen),
    db          : Session = Depends(get_db)
):
    """
    Dosen generate kode baru — kode lama LANGSUNG hangus.
    Mahasiswa yang belum presensi wajib pakai kode baru.
    """
    success, pesan, sesi = sesi_service.regen_kode(db, sesi_id, dosen.id, durasi_menit)
    if not success:
        raise HTTPException(status_code=400, detail=pesan)

    detik = sesi_service.hitung_detik_tersisa(sesi)
    return SesiResponse(
        id=sesi.id, mode=sesi.mode.value, kode_sesi=sesi.kode_sesi,
        kode_expire_at=sesi.kode_expire_at, pertemuan_ke=sesi.pertemuan_ke,
        waktu_buka=sesi.waktu_buka, status=sesi.status.value, detik_tersisa=detik
    )


# ─── GET /sesi/aktif ──────────────────────────────────────

@router.get("/aktif")
def cek_sesi_aktif(
    matakuliah_id: UUID,
    db           : Session = Depends(get_db),
    _            : User = Depends(get_current_user)
):
    """Mahasiswa cek apakah ada sesi aktif untuk matakuliahnya."""
    sesi = sesi_service.get_sesi_aktif(db, matakuliah_id)
    if not sesi:
        return {"ada_sesi": False, "sesi": None}

    detik = sesi_service.hitung_detik_tersisa(sesi)
    return {
        "ada_sesi"    : True,
        "sesi"        : {
            "id"           : sesi.id,
            "mode"         : sesi.mode.value,
            "waktu_buka"   : sesi.waktu_buka,
            "detik_tersisa": detik,
            # kode TIDAK dikembalikan di sini — mahasiswa input manual
        }
    }


# ─── GET /sesi/{sesi_id}/peserta ──────────────────────────

@router.get("/{sesi_id}/peserta")
def get_peserta(
    sesi_id: UUID,
    dosen  : User = Depends(require_dosen),
    db     : Session = Depends(get_db)
):
    """
    Dosen lihat daftar hadir real-time.
    Dipolling setiap 5 detik dari dashboard dosen.
    """
    sesi = db.query(SesiPresensi).filter(SesiPresensi.id == sesi_id).first()
    if not sesi:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")

    presensi_list = db.query(Presensi).filter(Presensi.sesi_id == sesi_id).all()

    hadir     = [p for p in presensi_list if p.status == PresensiStatus.hadir]
    terlambat = [p for p in presensi_list if p.status == PresensiStatus.terlambat]
    absen     = [p for p in presensi_list if p.status == PresensiStatus.absen]

    return {
        "sesi_id"   : sesi_id,
        "ringkasan" : {
            "hadir"    : len(hadir),
            "terlambat": len(terlambat),
            "absen"    : len(absen),
        },
        "detail": [{
            "mahasiswa_id"  : p.mahasiswa_id,
            "status"        : p.status.value,
            "waktu_presensi": p.waktu_presensi,
            "akurasi_wajah" : p.akurasi_wajah,
            "mode_kelas"    : p.mode_kelas.value,
        } for p in presensi_list]
    }

# ─── GET /sesi/aktif-dosen ────────────────────────────────────

@router.get("/aktif-dosen")
def get_sesi_aktif_dosen(
     dosen : User = Depends(require_dosen),
     db    : Session = Depends(get_db)
):
     """
     Ambil semua sesi aktif yang dibuat oleh dosen yang sedang login.
     Dipakai oleh dashboard dosen saat tidak ada sesi_id yang di-pass.
     """
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