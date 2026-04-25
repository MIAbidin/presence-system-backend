# app/services/home_service.py
"""
Service untuk endpoint beranda mahasiswa:
- GET /mahasiswa/home-summary
- GET /jadwal/hari-ini
- GET /jadwal/mingguan
"""
from datetime import datetime, date, timezone, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.matakuliah import Matakuliah
from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
from app.models.sesi import SesiPresensi, SesiStatus, SesiMode
from app.models.presensi import Presensi, PresensiStatus
from app.schemas.home import (
    HomeSummaryResponse, StatKehadiran, SesiAktifInfo, JadwalItem
)
from app.services.sesi_service import hitung_detik_tersisa


# Urutan hari dalam seminggu (Indonesia)
HARI_ORDER = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

# Mapping weekday() Python → nama hari Indonesia
WEEKDAY_TO_HARI = {
    0: "Senin",
    1: "Selasa",
    2: "Rabu",
    3: "Kamis",
    4: "Jumat",
    5: "Sabtu",
    6: "Minggu",
}


def _format_time(t) -> Optional[str]:
    """Konversi objek time / string ke format HH:MM."""
    if t is None:
        return None
    if hasattr(t, 'strftime'):
        return t.strftime("%H:%M")
    return str(t)[:5]


def get_matakuliah_mahasiswa(db: Session, mahasiswa_id: UUID) -> List[Matakuliah]:
    """Ambil semua matakuliah yang diambil mahasiswa ini."""
    rows = (
        db.query(MahasiswaMatakuliah)
        .filter(MahasiswaMatakuliah.mahasiswa_id == mahasiswa_id)
        .all()
    )
    if not rows:
        return []
    mk_ids = [r.matakuliah_id for r in rows]
    return db.query(Matakuliah).filter(Matakuliah.id.in_(mk_ids)).all()


def get_jadwal_hari_ini(db: Session, mahasiswa_id: UUID) -> List[JadwalItem]:
    """
    Jadwal matakuliah mahasiswa untuk hari ini,
    dilengkapi status presensi dan flag sesi aktif.
    """
    hari_ini = WEEKDAY_TO_HARI.get(datetime.now().weekday(), "")
    matakuliah_list = get_matakuliah_mahasiswa(db, mahasiswa_id)

    result: List[JadwalItem] = []

    for mk in matakuliah_list:
        # Filter hanya matakuliah hari ini
        if mk.hari and mk.hari != hari_ini:
            continue

        # Cek sesi aktif
        sesi_aktif = (
            db.query(SesiPresensi)
            .filter(
                SesiPresensi.matakuliah_id == mk.id,
                SesiPresensi.status == SesiStatus.aktif,
            )
            .first()
        )

        # Cek status presensi hari ini untuk sesi ini
        status_presensi = None
        if sesi_aktif or True:  # cek semua sesi hari ini
            today_start = datetime.combine(date.today(), datetime.min.time())
            # Cari presensi hari ini untuk matakuliah ini
            sesi_hari_ini = (
                db.query(SesiPresensi)
                .filter(
                    SesiPresensi.matakuliah_id == mk.id,
                    SesiPresensi.waktu_buka >= today_start,
                )
                .order_by(SesiPresensi.waktu_buka.desc())
                .first()
            )
            if sesi_hari_ini:
                presensi = (
                    db.query(Presensi)
                    .filter(
                        Presensi.mahasiswa_id == mahasiswa_id,
                        Presensi.sesi_id == sesi_hari_ini.id,
                    )
                    .first()
                )
                if presensi:
                    status_presensi = presensi.status.value

        result.append(JadwalItem(
            matakuliah_id   = mk.id,
            kode            = mk.kode,
            nama            = mk.nama,
            sks             = mk.sks,
            hari            = mk.hari,
            jam_mulai       = _format_time(mk.jam_mulai),
            jam_selesai     = _format_time(mk.jam_selesai),
            ruangan         = mk.ruangan,
            status_presensi = status_presensi,
            ada_sesi_aktif  = sesi_aktif is not None,
            sesi_id         = sesi_aktif.id if sesi_aktif else None,
        ))

    # Urutkan berdasarkan jam_mulai
    result.sort(key=lambda x: x.jam_mulai or "99:99")
    return result


def get_jadwal_mingguan(db: Session, mahasiswa_id: UUID) -> dict:
    """
    Jadwal semua matakuliah mahasiswa, dikelompokkan per hari.
    """
    matakuliah_list = get_matakuliah_mahasiswa(db, mahasiswa_id)
    grouped: dict = {hari: [] for hari in HARI_ORDER}

    for mk in matakuliah_list:
        hari = mk.hari or "Senin"  # default jika belum diset
        if hari not in grouped:
            grouped[hari] = []

        grouped[hari].append(JadwalItem(
            matakuliah_id = mk.id,
            kode          = mk.kode,
            nama          = mk.nama,
            sks           = mk.sks,
            hari          = mk.hari,
            jam_mulai     = _format_time(mk.jam_mulai),
            jam_selesai   = _format_time(mk.jam_selesai),
            ruangan       = mk.ruangan,
        ))

    # Urutkan setiap hari berdasarkan jam_mulai
    for hari in grouped:
        grouped[hari].sort(key=lambda x: x.jam_mulai or "99:99")

    # Bersihkan hari yang kosong — kembalikan semua agar frontend bisa render
    return {hari: grouped[hari] for hari in HARI_ORDER}


def get_stat_kehadiran(db: Session, mahasiswa_id: UUID) -> StatKehadiran:
    """Hitung statistik kehadiran mahasiswa untuk seluruh semester."""
    presensi_list = (
        db.query(Presensi)
        .filter(Presensi.mahasiswa_id == mahasiswa_id)
        .all()
    )

    total      = len(presensi_list)
    hadir      = sum(1 for p in presensi_list if p.status == PresensiStatus.hadir)
    terlambat  = sum(1 for p in presensi_list if p.status == PresensiStatus.terlambat)
    absen      = sum(1 for p in presensi_list if p.status == PresensiStatus.absen)
    izin       = sum(1 for p in presensi_list if p.status == PresensiStatus.izin)
    sakit      = sum(1 for p in presensi_list if p.status == PresensiStatus.sakit)
    efektif    = hadir + terlambat
    persentase = round(efektif / total * 100, 1) if total else 0.0

    return StatKehadiran(
        total_pertemuan = total,
        hadir           = hadir,
        terlambat       = terlambat,
        absen           = absen,
        izin            = izin,
        sakit           = sakit,
        hadir_efektif   = efektif,
        persentase      = persentase,
    )


def get_sesi_aktif_mahasiswa(db: Session, mahasiswa_id: UUID) -> List[SesiAktifInfo]:
    """
    Cari semua sesi yang sedang aktif untuk matakuliah yang diambil mahasiswa ini,
    dan mahasiswa belum presensi di sesi tersebut.
    """
    matakuliah_list = get_matakuliah_mahasiswa(db, mahasiswa_id)
    if not matakuliah_list:
        return []

    mk_ids = [mk.id for mk in matakuliah_list]

    sesi_list = (
        db.query(SesiPresensi)
        .filter(
            SesiPresensi.matakuliah_id.in_(mk_ids),
            SesiPresensi.status == SesiStatus.aktif,
        )
        .all()
    )

    result: List[SesiAktifInfo] = []
    for sesi in sesi_list:
        # Lewati jika mahasiswa sudah presensi di sesi ini
        sudah_presensi = (
            db.query(Presensi)
            .filter(
                Presensi.mahasiswa_id == mahasiswa_id,
                Presensi.sesi_id == sesi.id,
                Presensi.status.in_([PresensiStatus.hadir, PresensiStatus.terlambat]),
            )
            .first()
        )
        if sudah_presensi:
            continue

        mk = next((m for m in matakuliah_list if m.id == sesi.matakuliah_id), None)
        result.append(SesiAktifInfo(
            sesi_id         = sesi.id,
            matakuliah_nama = mk.nama if mk else "-",
            mode            = sesi.mode.value,
            detik_tersisa   = hitung_detik_tersisa(sesi),
            pertemuan_ke    = sesi.pertemuan_ke,
        ))

    return result


def get_home_summary(db: Session, mahasiswa: User) -> HomeSummaryResponse:
    """
    Kumpulkan semua data untuk halaman beranda dalam satu fungsi.
    Dipanggil oleh GET /mahasiswa/home-summary.
    """
    # Stat semester
    stat = get_stat_kehadiran(db, mahasiswa.id)

    # Jadwal hari ini
    jadwal_hari_ini = get_jadwal_hari_ini(db, mahasiswa.id)

    # Sesi aktif
    sesi_aktif = get_sesi_aktif_mahasiswa(db, mahasiswa.id)

    # Presensi hari ini (jumlah yang sudah dilakukan)
    today_start = datetime.combine(date.today(), datetime.min.time())
    presensi_hari_ini = (
        db.query(Presensi)
        .filter(
            Presensi.mahasiswa_id == mahasiswa.id,
            Presensi.waktu_presensi >= today_start,
            Presensi.status.in_([PresensiStatus.hadir, PresensiStatus.terlambat]),
        )
        .count()
    )

    return HomeSummaryResponse(
        nama_mahasiswa     = mahasiswa.nama_lengkap,
        nim                = mahasiswa.nim_nidn,
        is_face_registered = mahasiswa.is_face_registered,
        stat_semester      = stat,
        presensi_hari_ini  = presensi_hari_ini,
        jadwal_hari_ini    = jadwal_hari_ini,
        sesi_aktif         = sesi_aktif,
    )
