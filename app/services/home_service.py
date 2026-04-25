# app/services/home_service.py
"""
Service untuk endpoint beranda mahasiswa.
VERSI OPTIMIZED — semua data diambil dengan bulk query, bukan N+1 loop.
"""
from datetime import datetime, date
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.matakuliah import Matakuliah
from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
from app.models.sesi import SesiPresensi, SesiStatus
from app.models.presensi import Presensi, PresensiStatus
from app.schemas.home import (
    HomeSummaryResponse, StatKehadiran, SesiAktifInfo, JadwalItem
)
from app.services.sesi_service import hitung_detik_tersisa

HARI_ORDER = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
WEEKDAY_TO_HARI = {
    0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis",
    4: "Jumat", 5: "Sabtu", 6: "Minggu",
}


def _format_time(t) -> Optional[str]:
    if t is None:
        return None
    if hasattr(t, 'strftime'):
        return t.strftime("%H:%M")
    return str(t)[:5]


def get_matakuliah_mahasiswa(db: Session, mahasiswa_id: UUID) -> List[Matakuliah]:
    rows = (
        db.query(MahasiswaMatakuliah)
        .filter(MahasiswaMatakuliah.mahasiswa_id == mahasiswa_id)
        .all()
    )
    if not rows:
        return []
    mk_ids = [r.matakuliah_id for r in rows]
    return db.query(Matakuliah).filter(Matakuliah.id.in_(mk_ids)).all()


def get_stat_kehadiran(db: Session, mahasiswa_id: UUID) -> StatKehadiran:
    presensi_list = (
        db.query(Presensi)
        .filter(Presensi.mahasiswa_id == mahasiswa_id)
        .all()
    )
    total     = len(presensi_list)
    hadir     = sum(1 for p in presensi_list if p.status == PresensiStatus.hadir)
    terlambat = sum(1 for p in presensi_list if p.status == PresensiStatus.terlambat)
    absen     = sum(1 for p in presensi_list if p.status == PresensiStatus.absen)
    izin      = sum(1 for p in presensi_list if p.status == PresensiStatus.izin)
    sakit     = sum(1 for p in presensi_list if p.status == PresensiStatus.sakit)
    efektif   = hadir + terlambat
    persen    = round(efektif / total * 100, 1) if total else 0.0
    return StatKehadiran(
        total_pertemuan=total, hadir=hadir, terlambat=terlambat,
        absen=absen, izin=izin, sakit=sakit,
        hadir_efektif=efektif, persentase=persen,
    )


def get_jadwal_hari_ini(db: Session, mahasiswa_id: UUID) -> List[JadwalItem]:
    """
    OPTIMIZED: 4 query total, bukan N query per matakuliah.
    """
    hari_ini = WEEKDAY_TO_HARI.get(datetime.now().weekday(), "")

    # Query 1: matakuliah mahasiswa hari ini
    rows = (
        db.query(MahasiswaMatakuliah)
        .filter(MahasiswaMatakuliah.mahasiswa_id == mahasiswa_id)
        .all()
    )
    if not rows:
        return []

    mk_ids = [r.matakuliah_id for r in rows]
    matakuliah_list = (
        db.query(Matakuliah)
        .filter(Matakuliah.id.in_(mk_ids), Matakuliah.hari == hari_ini)
        .all()
    )
    if not matakuliah_list:
        return []

    mk_ids_hari_ini = [mk.id for mk in matakuliah_list]

    # Query 2: semua sesi aktif untuk matakuliah hari ini (bulk)
    sesi_aktif_list = (
        db.query(SesiPresensi)
        .filter(
            SesiPresensi.matakuliah_id.in_(mk_ids_hari_ini),
            SesiPresensi.status == SesiStatus.aktif,
        )
        .all()
    )
    sesi_aktif_map = {s.matakuliah_id: s for s in sesi_aktif_list}

    # Query 3: semua sesi hari ini untuk matakuliah hari ini (bulk)
    today_start = datetime.combine(date.today(), datetime.min.time())
    sesi_hari_ini_list = (
        db.query(SesiPresensi)
        .filter(
            SesiPresensi.matakuliah_id.in_(mk_ids_hari_ini),
            SesiPresensi.waktu_buka >= today_start,
        )
        .order_by(SesiPresensi.waktu_buka.desc())
        .all()
    )
    sesi_hari_ini_map: dict = {}
    for s in sesi_hari_ini_list:
        if s.matakuliah_id not in sesi_hari_ini_map:
            sesi_hari_ini_map[s.matakuliah_id] = s

    # Query 4: presensi mahasiswa di sesi-sesi hari ini (bulk)
    sesi_ids_hari_ini = [s.id for s in sesi_hari_ini_list]
    presensi_map: dict = {}
    if sesi_ids_hari_ini:
        for p in db.query(Presensi).filter(
            Presensi.mahasiswa_id == mahasiswa_id,
            Presensi.sesi_id.in_(sesi_ids_hari_ini),
        ).all():
            presensi_map[p.sesi_id] = p

    # Susun result — tidak ada query di dalam loop ini
    result: List[JadwalItem] = []
    for mk in matakuliah_list:
        sesi_aktif    = sesi_aktif_map.get(mk.id)
        sesi_hari_ini = sesi_hari_ini_map.get(mk.id)

        status_presensi = None
        if sesi_hari_ini:
            presensi = presensi_map.get(sesi_hari_ini.id)
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

    result.sort(key=lambda x: x.jam_mulai or "99:99")
    return result


def get_jadwal_mingguan(db: Session, mahasiswa_id: UUID) -> dict:
    matakuliah_list = get_matakuliah_mahasiswa(db, mahasiswa_id)
    grouped: dict = {hari: [] for hari in HARI_ORDER}

    for mk in matakuliah_list:
        hari = mk.hari or "Senin"
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

    for hari in grouped:
        grouped[hari].sort(key=lambda x: x.jam_mulai or "99:99")

    return {hari: grouped[hari] for hari in HARI_ORDER}


def get_sesi_aktif_mahasiswa(db: Session, mahasiswa_id: UUID) -> List[SesiAktifInfo]:
    """
    OPTIMIZED: 3 query total, bukan loop query per sesi.
    """
    rows = (
        db.query(MahasiswaMatakuliah)
        .filter(MahasiswaMatakuliah.mahasiswa_id == mahasiswa_id)
        .all()
    )
    if not rows:
        return []

    mk_ids = [r.matakuliah_id for r in rows]

    # Query 1: semua sesi aktif
    sesi_list = (
        db.query(SesiPresensi)
        .filter(
            SesiPresensi.matakuliah_id.in_(mk_ids),
            SesiPresensi.status == SesiStatus.aktif,
        )
        .all()
    )
    if not sesi_list:
        return []

    # Query 2: presensi yang sudah ada (bulk, tidak loop)
    sesi_ids = [s.id for s in sesi_list]
    sudah_presensi_set = set(
        p.sesi_id for p in db.query(Presensi).filter(
            Presensi.mahasiswa_id == mahasiswa_id,
            Presensi.sesi_id.in_(sesi_ids),
            Presensi.status.in_([PresensiStatus.hadir, PresensiStatus.terlambat]),
        ).all()
    )

    # Query 3: info matakuliah (bulk)
    mk_map = {
        mk.id: mk for mk in
        db.query(Matakuliah).filter(Matakuliah.id.in_(mk_ids)).all()
    }

    result: List[SesiAktifInfo] = []
    for sesi in sesi_list:
        if sesi.id in sudah_presensi_set:
            continue
        mk = mk_map.get(sesi.matakuliah_id)
        result.append(SesiAktifInfo(
            sesi_id         = sesi.id,
            matakuliah_nama = mk.nama if mk else "-",
            mode            = sesi.mode.value,
            detik_tersisa   = hitung_detik_tersisa(sesi),
            pertemuan_ke    = sesi.pertemuan_ke,
        ))

    return result


def get_home_summary(db: Session, mahasiswa: User) -> HomeSummaryResponse:
    """Total query: ~8 query (vs sebelumnya bisa 20+ query)."""
    stat            = get_stat_kehadiran(db, mahasiswa.id)
    jadwal_hari_ini = get_jadwal_hari_ini(db, mahasiswa.id)
    sesi_aktif      = get_sesi_aktif_mahasiswa(db, mahasiswa.id)

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