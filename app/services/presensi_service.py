from datetime import datetime
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.presensi import Presensi, PresensiStatus, ModeKelas
from app.models.sesi import SesiPresensi, SesiStatus, SesiMode
from app.models.user import User
from app.services import face_service, sesi_service
from app.utils.geo_utils import dalam_radius


# ─────────────────────────────────────────────
# PROSES PRESENSI UTAMA
# ─────────────────────────────────────────────
def proses_presensi(
    db: Session,
    mahasiswa: User,
    sesi_id: UUID,
    image_bytes: bytes,
    kode_sesi: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Tuple[bool, str, Optional[Presensi]]:

    # 1. Cek sesi aktif
    sesi = db.query(SesiPresensi).filter(
        SesiPresensi.id == sesi_id,
        SesiPresensi.status == SesiStatus.aktif
    ).first()

    if not sesi:
        return False, "Sesi tidak ditemukan atau sudah ditutup", None

    # 2. Cek presensi duplikat
    sudah = db.query(Presensi).filter(
        Presensi.mahasiswa_id == mahasiswa.id,
        Presensi.sesi_id == sesi_id,
        Presensi.status.in_([PresensiStatus.hadir, PresensiStatus.terlambat])
    ).first()

    if sudah:
        return False, "Anda sudah melakukan presensi", None

    # 3a. MODE OFFLINE (GPS)
    if sesi.mode == SesiMode.offline:
        if latitude is None or longitude is None:
            return False, "GPS wajib untuk mode offline", None

        matakuliah = sesi.matakuliah
        if not matakuliah or matakuliah.koordinat_lat is None:
            return False, "Koordinat kelas belum diset", None

        ok, jarak = dalam_radius(
            lat_mahasiswa=latitude,
            lng_mahasiswa=longitude,
            lat_kelas=matakuliah.koordinat_lat,
            lng_kelas=matakuliah.koordinat_lng,
            radius_meter=100.0
        )

        if not ok:
            return False, f"Di luar radius kelas ({jarak:.0f}m)", None

    # 3b. MODE ONLINE (kode sesi)
    if sesi.mode == SesiMode.online:
        if not kode_sesi:
            return False, "Kode sesi wajib", None

        valid, pesan, _ = sesi_service.validasi_kode(db, kode_sesi, mahasiswa.id)
        if not valid:
            return False, pesan, None

    # 4. Cek face registration
    if not mahasiswa.is_face_registered:
        return False, "Wajah belum terdaftar", None

    # 5. FACE RECOGNITION (SAFE)
    try:
        passed, akurasi, pesan = face_service.verify_face(
            db, mahasiswa.id, image_bytes
        )
    except Exception as e:
        return False, f"Error verifikasi wajah: {str(e)}", None

    if not passed:
        return False, pesan, None

    # 6. Tentukan status waktu
    now = datetime.utcnow()

    if not sesi.waktu_buka or not sesi.batas_terlambat:
        return False, "Waktu sesi belum lengkap", None

    batas_terlambat = sesi.waktu_buka + sesi.batas_terlambat

    status = (
        PresensiStatus.terlambat
        if now > batas_terlambat
        else PresensiStatus.hadir
    )

    # 7. SIMPAN PRESENSI
    presensi = Presensi(
        mahasiswa_id=mahasiswa.id,
        sesi_id=sesi_id,
        status=status,
        waktu_presensi=now,
        akurasi_wajah=akurasi,
        mode_kelas=ModeKelas(sesi.mode.value),
        latitude=latitude,
        longitude=longitude,
    )

    db.add(presensi)

    # 8. tandai kode dipakai (online)
    if sesi.mode == SesiMode.online:
        sesi_service.tandai_kode_dipakai(db, sesi_id, mahasiswa.id)

    db.commit()
    db.refresh(presensi)

    return True, f"Presensi berhasil ({status.value})", presensi


# ─────────────────────────────────────────────
# UBAH STATUS MANUAL (DOSEN)
# ─────────────────────────────────────────────
def ubah_status_manual(
    db: Session,
    presensi_id: UUID,
    dosen_id: UUID,
    status_baru: str,
    catatan: Optional[str] = None
) -> Tuple[bool, str]:

    presensi = db.query(Presensi).filter(
        Presensi.id == presensi_id
    ).first()

    if not presensi:
        return False, "Data tidak ditemukan"

    try:
        status_enum = PresensiStatus(status_baru)
    except ValueError:
        return False, f"Status tidak valid"

    presensi.status = status_enum
    presensi.catatan = catatan
    presensi.diubah_oleh = dosen_id

    db.commit()

    return True, "Status berhasil diubah"


# ─────────────────────────────────────────────
# RIWAYAT MAHASISWA
# ─────────────────────────────────────────────
def get_riwayat_mahasiswa(
    db: Session,
    mahasiswa_id: UUID,
    matakuliah_id: Optional[UUID] = None
):
    query = db.query(Presensi).filter(
        Presensi.mahasiswa_id == mahasiswa_id
    )

    if matakuliah_id:
        query = query.join(SesiPresensi).filter(
            SesiPresensi.matakuliah_id == matakuliah_id
        )

    return query.order_by(Presensi.created_at.desc()).all()


# ─────────────────────────────────────────────
# REKAP SESI
# ─────────────────────────────────────────────
def get_rekap_sesi(db: Session, sesi_id: UUID):
    return db.query(Presensi).filter(
        Presensi.sesi_id == sesi_id
    ).all()


# ─────────────────────────────────────────────
# HITUNG STATISTIK
# ─────────────────────────────────────────────
def hitung_persentase(presensi_list: list):

    total = len(presensi_list)

    hadir = sum(p.status == PresensiStatus.hadir for p in presensi_list)
    terlambat = sum(p.status == PresensiStatus.terlambat for p in presensi_list)
    absen = sum(p.status == PresensiStatus.absen for p in presensi_list)
    izin = sum(p.status == PresensiStatus.izin for p in presensi_list)
    sakit = sum(p.status == PresensiStatus.sakit for p in presensi_list)

    efektif = hadir + terlambat
    persen = round((efektif / total * 100), 1) if total else 0

    return {
        "total": total,
        "hadir": hadir,
        "terlambat": terlambat,
        "absen": absen,
        "izin": izin,
        "sakit": sakit,
        "hadir_efektif": efektif,
        "persentase": persen,
    }
