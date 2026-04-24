from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.user import User
from app.models.matakuliah import Matakuliah
from app.models.sesi import SesiPresensi, SesiStatus
from app.routers.auth import get_current_user

router = APIRouter(prefix="/matakuliah", tags=["Matakuliah"])


@router.get("/saya")
def get_matakuliah_saya(
    current_user: User = Depends(get_current_user),
    db          : Session = Depends(get_db)
):
    """
    Ambil daftar matakuliah yang pernah dibuat sesinya oleh dosen ini.
    Jika dosen belum pernah membuat sesi, kembalikan semua matakuliah (admin).
    """
    if current_user.role.value == "dosen":
        # Ambil matakuliah dari sesi yang pernah dibuat dosen ini
        sesi_list = db.query(SesiPresensi).filter(
            SesiPresensi.dosen_id == current_user.id
        ).all()

        # Deduplikasi matakuliah_id
        mk_ids  = list({s.matakuliah_id for s in sesi_list})

        if mk_ids:
            mk_list = db.query(Matakuliah).filter(
                Matakuliah.id.in_(mk_ids)
            ).all()
        else:
            # Dosen belum pernah buat sesi — kembalikan semua matakuliah
            mk_list = db.query(Matakuliah).all()
    else:
        # Admin: semua matakuliah
        mk_list = db.query(Matakuliah).all()

    return [
        {
            "id"  : str(mk.id),
            "kode": mk.kode,
            "nama": mk.nama,
            "sks" : mk.sks,
        }
        for mk in mk_list
    ]


@router.get("/semua")
def get_semua_matakuliah(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Ambil semua matakuliah (untuk admin)."""
    mk_list = db.query(Matakuliah).all()
    return [
        {
            "id"            : str(mk.id),
            "kode"          : mk.kode,
            "nama"          : mk.nama,
            "sks"           : mk.sks,
            "koordinat_lat" : mk.koordinat_lat,
            "koordinat_lng" : mk.koordinat_lng,
        }
        for mk in mk_list
    ]