# app/services/sesi_aktif_service.py
"""
Fase B-2 — Service: Ambil sesi aktif yang cocok dengan jadwal mahasiswa.

Logic utama:
1. Ambil semua MK yang diikuti mahasiswa (via mahasiswa_matakuliah)
2. Query sesi_presensi aktif yang matakuliah_id-nya ada di daftar tersebut
3. Filter: hari + jam sekarang harus dalam window jadwal MK (toleransi ±30 mnt)
4. Exclude sesi yang sudah dipresensi mahasiswa ini
5. Perkaya response dengan data matakuliah, kelas, dosen, ruangan

Hasil dipakai Flutter SesiDetectService untuk auto-detect mode presensi
tanpa mahasiswa harus pilih Offline/Online secara manual.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
from app.models.sesi import SesiPresensi, SesiStatus
from app.models.presensi import Presensi, PresensiStatus
from app.models.matakuliah import Matakuliah
from app.models.kelas_matakuliah import KelasMatakuliah
from app.models.ruangan import Ruangan
from app.models.user import User
from app.schemas.sesi_aktif import SesiAktifDetailResponse, SesiAktifWrapper

logger = logging.getLogger(__name__)

WIB = ZoneInfo("Asia/Jakarta")
HARI_MAP = {0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis", 4: "Jumat", 5: "Sabtu", 6: "Minggu"}

# Toleransi waktu: 30 menit sebelum jam_mulai sampai sesi ditutup
TOLERANSI_SEBELUM_MENIT = 30


def _hitung_detik_tersisa(sesi: SesiPresensi) -> Optional[int]:
    """Hitung sisa detik kode online. None untuk mode offline."""
    if not sesi.kode_expire_at:
        return None
    expire = sesi.kode_expire_at
    if expire.tzinfo is None:
        expire = expire.replace(tzinfo=timezone.utc)
    delta = expire - datetime.now(timezone.utc)
    return max(0, int(delta.total_seconds()))


def _dalam_window_jadwal(kelas: KelasMatakuliah, now_wib: datetime) -> bool:
    """
    Cek apakah jam sekarang (WIB) masuk window jadwal kelas.

    Window = (jam_mulai - TOLERANSI) sampai jam_selesai.
    Toleransi 30 menit memungkinkan mahasiswa scan wajah lebih awal
    sedikit sebelum kelas resmi dimulai.

    Jika kelas tidak punya slot → return True (tidak filter berdasarkan jam).
    """
    from app.utils.slot_utils import SLOT_MAPPING

    if kelas.slot_mulai is None or kelas.slot_selesai is None:
        return True  # Tidak ada info jadwal → izinkan saja

    slot_mulai_info   = SLOT_MAPPING.get(kelas.slot_mulai)
    slot_selesai_info = SLOT_MAPPING.get(kelas.slot_selesai)
    if not slot_mulai_info or not slot_selesai_info:
        return True

    jam_mulai   = slot_mulai_info[0]   # datetime.time
    jam_selesai = slot_selesai_info[1] # datetime.time

    # Buat batas window hari ini di WIB
    today = now_wib.date()

    from datetime import datetime as dt, time as dtime
    batas_buka   = dt.combine(today, jam_mulai, tzinfo=WIB) - timedelta(minutes=TOLERANSI_SEBELUM_MENIT)
    batas_tutup  = dt.combine(today, jam_selesai, tzinfo=WIB) + timedelta(minutes=5)  # sedikit toleransi setelah selesai

    return batas_buka <= now_wib <= batas_tutup


def get_sesi_aktif_mahasiswa_detail(
    db          : Session,
    mahasiswa_id: UUID,
) -> SesiAktifWrapper:
    """
    Ambil satu sesi aktif yang paling cocok dengan jadwal mahasiswa saat ini.

    Alur:
    1. Cari enrollment mahasiswa → dapat list matakuliah_id + kelas_id
    2. Query sesi aktif yang matakuliah_id-nya cocok
    3. Filter hari sesuai hari ini (WIB)
    4. Filter window jam (toleransi ±30 mnt dari jam_mulai kelas)
    5. Exclude yang sudah dipresensi
    6. Perkaya dengan data lengkap
    7. Return sesi pertama yang cocok (prioritas: offline dulu, lalu online)

    Return SesiAktifWrapper — tidak pernah raise 404.
    """
    now_utc = datetime.now(timezone.utc)
    now_wib = now_utc.astimezone(WIB)
    hari_ini = HARI_MAP.get(now_wib.weekday(), "")

    # ── 1. Enrollment mahasiswa ──────────────────────────────
    enrollments = (
        db.query(MahasiswaMatakuliah)
        .filter(MahasiswaMatakuliah.mahasiswa_id == mahasiswa_id)
        .all()
    )
    if not enrollments:
        logger.debug(f"Mahasiswa {mahasiswa_id} tidak enrolled di MK manapun")
        return SesiAktifWrapper(ada_sesi=False, sesi=None)

    mk_ids   = [e.matakuliah_id for e in enrollments]
    # Map matakuliah_id → kelas_id (untuk lookup kelas yang diikuti mahasiswa)
    mk_kelas_map: dict = {e.matakuliah_id: e.kelas_id for e in enrollments}

    # ── 2. Sesi aktif untuk MK yang diikuti ─────────────────
    sesi_list = (
        db.query(SesiPresensi)
        .filter(
            SesiPresensi.matakuliah_id.in_(mk_ids),
            SesiPresensi.status == SesiStatus.aktif,
        )
        .all()
    )
    if not sesi_list:
        logger.debug(f"Tidak ada sesi aktif untuk mahasiswa {mahasiswa_id}")
        return SesiAktifWrapper(ada_sesi=False, sesi=None)

    # ── 3. Sudah presensi di sesi mana? ─────────────────────
    sesi_ids = [s.id for s in sesi_list]
    sudah_presensi_sesi_ids = {
        p.sesi_id
        for p in db.query(Presensi).filter(
            Presensi.mahasiswa_id == mahasiswa_id,
            Presensi.sesi_id.in_(sesi_ids),
        ).all()
    }

    # ── 4. Bulk load data pendukung ──────────────────────────
    mk_map = {
        mk.id: mk for mk in
        db.query(Matakuliah).filter(Matakuliah.id.in_(mk_ids)).all()
    }

    # Ambil kelas yang diikuti mahasiswa per MK
    kelas_ids = [kid for kid in mk_kelas_map.values() if kid is not None]
    kelas_obj_map = {}
    if kelas_ids:
        kelas_obj_map = {
            k.id: k for k in
            db.query(KelasMatakuliah).filter(KelasMatakuliah.id.in_(kelas_ids)).all()
        }

    # Kumpulkan ruangan_id dari kelas
    ruangan_ids = [k.ruangan_id for k in kelas_obj_map.values() if k.ruangan_id]
    ruangan_map = {}
    if ruangan_ids:
        ruangan_map = {
            r.id: r for r in
            db.query(Ruangan).filter(Ruangan.id.in_(ruangan_ids)).all()
        }

    # Dosen dari masing-masing kelas
    dosen_ids = [k.dosen_id for k in kelas_obj_map.values() if k.dosen_id]
    # Tambah dosen dari sesi_presensi sebagai fallback
    dosen_ids += [s.dosen_id for s in sesi_list if s.dosen_id]
    dosen_ids = list(set(dosen_ids))
    dosen_map = {}
    if dosen_ids:
        dosen_map = {
            u.id: u for u in
            db.query(User).filter(User.id.in_(dosen_ids)).all()
        }

    # ── 5. Filter dan pilih sesi terbaik ────────────────────
    kandidat = []
    for sesi in sesi_list:
        # Skip yang sudah dipresensi
        if sesi.id in sudah_presensi_sesi_ids:
            continue

        mk       = mk_map.get(sesi.matakuliah_id)
        kelas_id = mk_kelas_map.get(sesi.matakuliah_id)
        kelas    = kelas_obj_map.get(kelas_id) if kelas_id else None

        # Filter hari
        if kelas and kelas.hari and kelas.hari != hari_ini:
            logger.debug(
                f"Skip sesi {sesi.id}: hari kelas {kelas.hari} != hari ini {hari_ini}"
            )
            continue

        # Filter window jam (hanya jika kelas punya info slot)
        if kelas and not _dalam_window_jadwal(kelas, now_wib):
            logger.debug(
                f"Skip sesi {sesi.id}: di luar window jam kelas"
            )
            continue

        kandidat.append((sesi, mk, kelas, kelas_id))

    if not kandidat:
        logger.debug(
            f"Tidak ada sesi yang cocok hari ini ({hari_ini}) untuk mahasiswa {mahasiswa_id}"
        )
        return SesiAktifWrapper(ada_sesi=False, sesi=None)

    # ── 6. Prioritaskan: offline dulu, lalu online ───────────
    # Jika ada sesi offline aktif, presensi tatap muka lebih relevan
    kandidat.sort(key=lambda x: (0 if x[0].mode.value == "offline" else 1))
    sesi, mk, kelas, kelas_id = kandidat[0]

    # ── 7. Kumpulkan data lengkap untuk response ─────────────
    ruangan     = None
    dosen_nama  = None
    kode_kelas  = None
    koord_lat   = None
    koord_lng   = None
    ruangan_nama= None

    if kelas:
        kode_kelas = kelas.kode_kelas
        # Dosen dari kelas
        if kelas.dosen_id:
            dosen = dosen_map.get(kelas.dosen_id)
            if dosen:
                dosen_nama = dosen.nama_lengkap
        # Ruangan dari kelas
        if kelas.ruangan_id:
            r = ruangan_map.get(kelas.ruangan_id)
            if r:
                ruangan_nama = r.nama
                koord_lat    = r.koordinat_lat
                koord_lng    = r.koordinat_lng

    # Fallback dosen dari sesi_presensi jika kelas tidak punya dosen
    if not dosen_nama and sesi.dosen_id:
        dosen = dosen_map.get(sesi.dosen_id)
        if dosen:
            dosen_nama = dosen.nama_lengkap

    # Fallback koordinat dari matakuliah jika kelas tidak punya ruangan
    if koord_lat is None and mk:
        koord_lat = mk.koordinat_lat
        koord_lng = mk.koordinat_lng
        ruangan_nama = mk.ruangan  # string field lama

    detik = _hitung_detik_tersisa(sesi)

    logger.info(
        f"Sesi aktif ditemukan untuk mahasiswa {mahasiswa_id}: "
        f"sesi_id={sesi.id}, mode={sesi.mode.value}, MK={mk.nama if mk else '-'}, "
        f"kelas={kode_kelas}"
    )

    detail = SesiAktifDetailResponse(
        sesi_id         = sesi.id,
        mode            = sesi.mode.value,
        pertemuan_ke    = sesi.pertemuan_ke,
        waktu_buka      = sesi.waktu_buka,
        detik_tersisa   = detik,
        matakuliah_id   = sesi.matakuliah_id,
        matakuliah_nama = mk.nama if mk else "-",
        matakuliah_kode = mk.kode if mk else "-",
        kelas_id        = kelas_id,
        kode_kelas      = kode_kelas,
        dosen_nama      = dosen_nama,
        ruangan         = ruangan_nama,
        koordinat_lat   = koord_lat,
        koordinat_lng   = koord_lng,
    )

    return SesiAktifWrapper(ada_sesi=True, sesi=detail)