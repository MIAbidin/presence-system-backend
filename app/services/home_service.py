# app/services/home_service.py
"""
Service untuk endpoint beranda mahasiswa.

Update Fase B-5:
- get_jadwal_hari_ini()    → sertakan mode_efektif & jadwal_pengganti_info
- get_jadwal_mingguan()    → sertakan mode_efektif & jadwal_pengganti_info
- get_jadwal_per_hari()    → helper baru, dipakai router jadwal.py

Logic mode_efektif:
  1. Hitung pertemuan_ke_berikutnya = jumlah sesi selesai di MK ini + 1
  2. Cek tabel jadwal_pengganti untuk (matakuliah_id, pertemuan_ke_berikutnya)
  3. Jika ada & mode diisi  → mode_efektif = jadwal_pengganti.mode
  4. Jika ada & mode null   → mode_efektif = None (tidak berubah, banner tetap tampil)
  5. Jika tidak ada         → mode_efektif = None, has_jadwal_pengganti = False

Semua query dilakukan secara bulk (tidak ada N+1 loop).
"""
from datetime import datetime, date, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User
from app.models.matakuliah import Matakuliah
from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
from app.models.sesi import SesiPresensi, SesiStatus
from app.models.presensi import Presensi, PresensiStatus
from app.models.jadwal_pengganti import JadwalPengganti
from app.schemas.home import (
    HomeSummaryResponse, StatKehadiran, SesiAktifInfo,
    JadwalItem, JadwalPenggantiInfo,
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


# ─── HELPER: hitung pertemuan_ke_berikutnya per MK (bulk) ─────

def _bulk_pertemuan_berikutnya(
    db    : Session,
    mk_ids: list,
) -> dict:
    """
    Hitung pertemuan_ke_berikutnya untuk setiap matakuliah.
    = jumlah sesi dengan status 'selesai' + 1.
    Return dict: matakuliah_id → pertemuan_ke_berikutnya (int)
    """
    if not mk_ids:
        return {}

    rows = (
        db.query(
            SesiPresensi.matakuliah_id,
            func.count(SesiPresensi.id).label("selesai"),
        )
        .filter(
            SesiPresensi.matakuliah_id.in_(mk_ids),
            SesiPresensi.status == SesiStatus.selesai,
        )
        .group_by(SesiPresensi.matakuliah_id)
        .all()
    )
    result = {r.matakuliah_id: r.selesai + 1 for r in rows}
    # MK yang belum pernah punya sesi selesai → pertemuan ke-1
    for mk_id in mk_ids:
        if mk_id not in result:
            result[mk_id] = 1
    return result


# ─── HELPER: bulk load jadwal_pengganti ───────────────────────

def _bulk_jadwal_pengganti(
    db              : Session,
    mk_pertemuan_map: dict,   # {matakuliah_id: pertemuan_ke_berikutnya}
) -> dict:
    """
    Ambil jadwal_pengganti untuk setiap (matakuliah_id, pertemuan_ke_berikutnya).
    Return dict: matakuliah_id → JadwalPengganti | None

    Satu query mengambil semua, lalu difilter di Python untuk
    matching pertemuan_ke yang tepat.
    """
    if not mk_pertemuan_map:
        return {}

    mk_ids = list(mk_pertemuan_map.keys())
    jp_list = (
        db.query(JadwalPengganti)
        .filter(JadwalPengganti.matakuliah_id.in_(mk_ids))
        .all()
    )

    result: dict = {}
    for jp in jp_list:
        target_ptm = mk_pertemuan_map.get(jp.matakuliah_id)
        if target_ptm is not None and jp.pertemuan_ke == target_ptm:
            result[jp.matakuliah_id] = jp

    return result


# ─── HELPER: bangun JadwalPenggantiInfo ───────────────────────

def _build_jp_info(jp: Optional[JadwalPengganti]) -> Optional[JadwalPenggantiInfo]:
    """Konversi model JadwalPengganti ke schema JadwalPenggantiInfo."""
    if jp is None:
        return None
    return JadwalPenggantiInfo(
        pertemuan_ke     = jp.pertemuan_ke,
        jam_mulai_baru   = _format_time(jp.jam_mulai_baru),
        jam_selesai_baru = _format_time(jp.jam_selesai_baru),
        ruangan_baru     = jp.ruangan_baru,
        mode             = getattr(jp, "mode", None),   # nullable — Fase B-1
        keterangan       = jp.keterangan,
    )


# ─── GET MATAKULIAH MAHASISWA ─────────────────────────────────

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


# ─── GET STAT KEHADIRAN ───────────────────────────────────────

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


# ─── GET JADWAL HARI INI ──────────────────────────────────────

def get_jadwal_hari_ini(db: Session, mahasiswa_id: UUID) -> List[JadwalItem]:
    """
    Jadwal matakuliah mahasiswa untuk hari ini.

    Fase B-5: setiap item dilengkapi mode_efektif, has_jadwal_pengganti,
    dan jadwal_pengganti_info untuk pertemuan berikutnya.

    Total query: 6 (vs sebelumnya 4 — tambah 2 untuk JP data).
    """
    hari_ini = WEEKDAY_TO_HARI.get(datetime.now().weekday(), "")

    # Query 1: enrollment mahasiswa
    rows = (
        db.query(MahasiswaMatakuliah)
        .filter(MahasiswaMatakuliah.mahasiswa_id == mahasiswa_id)
        .all()
    )
    if not rows:
        return []

    mk_ids = [r.matakuliah_id for r in rows]

    # Query 2: matakuliah hari ini
    matakuliah_list = (
        db.query(Matakuliah)
        .filter(Matakuliah.id.in_(mk_ids), Matakuliah.hari == hari_ini)
        .all()
    )
    if not matakuliah_list:
        return []

    mk_ids_hari_ini = [mk.id for mk in matakuliah_list]

    # Query 3: sesi aktif (bulk)
    sesi_aktif_list = (
        db.query(SesiPresensi)
        .filter(
            SesiPresensi.matakuliah_id.in_(mk_ids_hari_ini),
            SesiPresensi.status == SesiStatus.aktif,
        )
        .all()
    )
    sesi_aktif_map = {s.matakuliah_id: s for s in sesi_aktif_list}

    # Query 4: sesi hari ini (untuk cek status presensi)
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

    # Query 5: presensi mahasiswa (bulk)
    sesi_ids_hari_ini = [s.id for s in sesi_hari_ini_list]
    presensi_map: dict = {}
    if sesi_ids_hari_ini:
        for p in db.query(Presensi).filter(
            Presensi.mahasiswa_id == mahasiswa_id,
            Presensi.sesi_id.in_(sesi_ids_hari_ini),
        ).all():
            presensi_map[p.sesi_id] = p

    # ── Fase B-5: Query 6 — jadwal pengganti ─────────────────
    pertemuan_map = _bulk_pertemuan_berikutnya(db, mk_ids_hari_ini)
    jp_map        = _bulk_jadwal_pengganti(db, pertemuan_map)

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

        # ── Fase B-5: mode_efektif & jadwal_pengganti_info ───
        jp     = jp_map.get(mk.id)
        jp_info = _build_jp_info(jp)
        mode_efektif = None
        if jp is not None:
            mode_efektif = getattr(jp, "mode", None)  # bisa None (tidak berubah)

        result.append(JadwalItem(
            matakuliah_id         = mk.id,
            kode                  = mk.kode,
            nama                  = mk.nama,
            sks                   = mk.sks,
            hari                  = mk.hari,
            jam_mulai             = _format_time(mk.jam_mulai),
            jam_selesai           = _format_time(mk.jam_selesai),
            ruangan               = mk.ruangan,
            status_presensi       = status_presensi,
            ada_sesi_aktif        = sesi_aktif is not None,
            sesi_id               = sesi_aktif.id if sesi_aktif else None,
            # Fase B-5
            mode_efektif          = mode_efektif,
            has_jadwal_pengganti  = jp is not None,
            jadwal_pengganti_info = jp_info,
        ))

    result.sort(key=lambda x: x.jam_mulai or "99:99")
    return result


# ─── GET JADWAL MINGGUAN ──────────────────────────────────────

def get_jadwal_mingguan(db: Session, mahasiswa_id: UUID) -> dict:
    """
    Jadwal seminggu penuh dikelompokkan per hari.

    Fase B-5: setiap item dilengkapi mode_efektif, has_jadwal_pengganti,
    dan jadwal_pengganti_info.

    Karena mingguan mencakup banyak MK, bulk query JP dilakukan sekali
    untuk semua MK yang diikuti mahasiswa.
    """
    matakuliah_list = get_matakuliah_mahasiswa(db, mahasiswa_id)
    if not matakuliah_list:
        return {hari: [] for hari in HARI_ORDER}

    # ── Fase B-5: bulk jadwal pengganti untuk semua MK ───────
    mk_ids_all    = [mk.id for mk in matakuliah_list]
    pertemuan_map = _bulk_pertemuan_berikutnya(db, mk_ids_all)
    jp_map        = _bulk_jadwal_pengganti(db, pertemuan_map)

    grouped: dict = {hari: [] for hari in HARI_ORDER}

    for mk in matakuliah_list:
        hari = mk.hari or "Senin"
        if hari not in grouped:
            grouped[hari] = []

        jp      = jp_map.get(mk.id)
        jp_info = _build_jp_info(jp)
        mode_efektif = getattr(jp, "mode", None) if jp is not None else None

        grouped[hari].append(JadwalItem(
            matakuliah_id         = mk.id,
            kode                  = mk.kode,
            nama                  = mk.nama,
            sks                   = mk.sks,
            hari                  = mk.hari,
            jam_mulai             = _format_time(mk.jam_mulai),
            jam_selesai           = _format_time(mk.jam_selesai),
            ruangan               = mk.ruangan,
            # Fase B-5
            mode_efektif          = mode_efektif,
            has_jadwal_pengganti  = jp is not None,
            jadwal_pengganti_info = jp_info,
        ))

    for hari in grouped:
        grouped[hari].sort(key=lambda x: x.jam_mulai or "99:99")

    return {hari: grouped[hari] for hari in HARI_ORDER}


# ─── GET JADWAL PER HARI (helper untuk router) ────────────────

def get_jadwal_per_hari(
    db           : Session,
    mahasiswa_id : UUID,
    nama_hari    : str,
) -> List[JadwalItem]:
    """
    Jadwal untuk satu hari tertentu (dipakai GET /jadwal/hari/{nama_hari}).

    Fase B-5: sertakan mode_efektif & jadwal_pengganti_info.
    """
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
        .filter(Matakuliah.id.in_(mk_ids), Matakuliah.hari == nama_hari)
        .all()
    )
    if not matakuliah_list:
        return []

    # Fase B-5: bulk JP untuk hari ini
    mk_ids_hari = [mk.id for mk in matakuliah_list]
    pertemuan_map = _bulk_pertemuan_berikutnya(db, mk_ids_hari)
    jp_map        = _bulk_jadwal_pengganti(db, pertemuan_map)

    result: List[JadwalItem] = []
    for mk in matakuliah_list:
        jp      = jp_map.get(mk.id)
        jp_info = _build_jp_info(jp)
        mode_efektif = getattr(jp, "mode", None) if jp is not None else None

        result.append(JadwalItem(
            matakuliah_id         = mk.id,
            kode                  = mk.kode,
            nama                  = mk.nama,
            sks                   = mk.sks,
            hari                  = mk.hari,
            jam_mulai             = _format_time(mk.jam_mulai),
            jam_selesai           = _format_time(mk.jam_selesai),
            ruangan               = mk.ruangan,
            # Fase B-5
            mode_efektif          = mode_efektif,
            has_jadwal_pengganti  = jp is not None,
            jadwal_pengganti_info = jp_info,
        ))

    result.sort(key=lambda x: x.jam_mulai or "99:99")
    return result


# ─── GET SESI AKTIF MAHASISWA ─────────────────────────────────

def get_sesi_aktif_mahasiswa(db: Session, mahasiswa_id: UUID) -> List[SesiAktifInfo]:
    """OPTIMIZED: 3 query total, bukan loop query per sesi."""
    rows = (
        db.query(MahasiswaMatakuliah)
        .filter(MahasiswaMatakuliah.mahasiswa_id == mahasiswa_id)
        .all()
    )
    if not rows:
        return []

    mk_ids = [r.matakuliah_id for r in rows]

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

    sesi_ids = [s.id for s in sesi_list]
    sudah_presensi_set = set(
        p.sesi_id for p in db.query(Presensi).filter(
            Presensi.mahasiswa_id == mahasiswa_id,
            Presensi.sesi_id.in_(sesi_ids),
            Presensi.status.in_([PresensiStatus.hadir, PresensiStatus.terlambat]),
        ).all()
    )

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


# ─── GET HOME SUMMARY ─────────────────────────────────────────

def get_home_summary(db: Session, mahasiswa: User) -> HomeSummaryResponse:
    """Total query: ~8 query (jadwal hari ini sudah termasuk query JP)."""
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