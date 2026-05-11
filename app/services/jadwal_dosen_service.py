# app/services/jadwal_dosen_service.py
"""
Fase B-4 — Service: Jadwal Mingguan Dosen.

Endpoint: GET /dosen/jadwal/mingguan
Dipanggil dari: JadwalDosenScreen Flutter v2.1.0

Screen baru di Flutter dosen yang menampilkan:
- Tab Hari Ini: kelas yang dijadwalkan hari ini + status sesi
- Tab Mingguan: semua kelas dikelompokkan per hari (Senin–Minggu)

Data bersumber dari tabel kelas_matakuliah dimana dosen_id cocok
dengan dosen yang login. Setiap kelas diperkaya dengan:
- Info matakuliah (nama, kode, SKS)
- Info ruangan (nama, koordinat GPS)
- Slot waktu → jam nyata (via SLOT_MAPPING)
- Jumlah mahasiswa enrolled (asli + tamu)
- Status sesi hari ini (aktif/selesai/belum_dibuka)
- Info jadwal pengganti jika ada untuk pertemuan berikutnya

Query strategy (menghindari N+1):
1. Satu query kelas_matakuliah WHERE dosen_id = current_dosen
2. Bulk load matakuliah, ruangan dalam satu query masing-masing
3. Bulk load enrolled count per kelas (GROUP BY kelas_id)
4. Bulk load sesi aktif + sesi selesai hari ini
5. Bulk load jadwal_pengganti untuk pertemuan berikutnya
6. Proses pengelompokan di Python — tidak ada loop query
"""

import logging
from datetime import datetime, timezone, date, timedelta
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User
from app.models.matakuliah import Matakuliah
from app.models.kelas_matakuliah import KelasMatakuliah
from app.models.ruangan import Ruangan
from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
from app.models.sesi import SesiPresensi, SesiStatus
from app.models.jadwal_pengganti import JadwalPengganti
from app.schemas.jadwal_dosen import (
    JadwalMingguanDosenItem,
    JadwalMingguanDosenResponse,
    JadwalPenggantiInfoItem,
    HARI_ORDER,
)
from app.utils.slot_utils import SLOT_MAPPING

logger = logging.getLogger(__name__)

WIB = ZoneInfo("Asia/Jakarta")
WEEKDAY_TO_HARI = {
    0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis",
    4: "Jumat", 5: "Sabtu", 6: "Minggu",
}


def _fmt_slot_jam(slot_mulai: Optional[int], slot_selesai: Optional[int]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Konversi slot_mulai dan slot_selesai ke string jam.
    Return: (jam_mulai_str, jam_selesai_str, jam_range_str)
    Contoh: (1, 3) → ("07:00", "09:30", "07:00 – 09:30")
    """
    if slot_mulai is None or slot_selesai is None:
        return None, None, None

    slot_m = SLOT_MAPPING.get(slot_mulai)
    slot_s = SLOT_MAPPING.get(slot_selesai)

    if not slot_m or not slot_s:
        return None, None, None

    jam_mulai   = slot_m[0].strftime("%H:%M")
    jam_selesai = slot_s[1].strftime("%H:%M")
    jam_range   = f"{jam_mulai} – {jam_selesai}"

    return jam_mulai, jam_selesai, jam_range


def _fmt_time(t) -> Optional[str]:
    """Format time object ke string HH:MM."""
    if t is None:
        return None
    if hasattr(t, "strftime"):
        return t.strftime("%H:%M")
    return str(t)[:5]


def _hitung_pertemuan_berikutnya(db: Session, kelas: KelasMatakuliah) -> int:
    """
    Hitung nomor pertemuan berikutnya untuk kelas ini.
    Berdasarkan jumlah sesi selesai yang sudah ada untuk MK ini.
    Minimal 1.
    """
    jumlah_selesai = (
        db.query(func.count(SesiPresensi.id))
        .filter(
            SesiPresensi.matakuliah_id == kelas.matakuliah_id,
            SesiPresensi.status        == SesiStatus.selesai,
        )
        .scalar()
    ) or 0
    return jumlah_selesai + 1


def get_jadwal_mingguan_dosen(
    db   : Session,
    dosen: User,
) -> JadwalMingguanDosenResponse:
    """
    Ambil jadwal mingguan dosen — semua kelas yang diampu per hari.

    Return JadwalMingguanDosenResponse — tidak pernah raise exception,
    selalu return HTTP 200 dengan data kosong jika tidak ada jadwal.
    """
    try:
        return _get_jadwal_mingguan_impl(db, dosen)
    except Exception as e:
        logger.error(
            f"[jadwal_dosen_service] Error get_jadwal_mingguan_dosen "
            f"dosen_id={dosen.id}: {e}",
            exc_info=True,
        )
        # Kembalikan response kosong — jangan crash
        now_wib  = datetime.now(WIB)
        hari_ini = WEEKDAY_TO_HARI.get(now_wib.weekday(), "Senin")
        return JadwalMingguanDosenResponse(
            nama_dosen       = dosen.nama_lengkap,
            nidn             = dosen.nim_nidn,
            hari_ini         = hari_ini,
            total_kelas      = 0,
            total_sesi_aktif = 0,
            jadwal_per_hari  = {h: [] for h in HARI_ORDER},
        )


def _get_jadwal_mingguan_impl(
    db   : Session,
    dosen: User,
) -> JadwalMingguanDosenResponse:
    """Implementasi utama — dipisah agar error handling bersih."""

    now_wib  = datetime.now(WIB)
    hari_ini = WEEKDAY_TO_HARI.get(now_wib.weekday(), "Senin")

    # ── 1. Ambil semua kelas yang diampu dosen ───────────────
    kelas_list = (
        db.query(KelasMatakuliah)
        .filter(
            KelasMatakuliah.dosen_id  == dosen.id,
            KelasMatakuliah.is_active == True,
        )
        .order_by(KelasMatakuliah.hari, KelasMatakuliah.slot_mulai)
        .all()
    )

    if not kelas_list:
        logger.debug(f"Dosen {dosen.id} tidak mengampu kelas manapun")
        return JadwalMingguanDosenResponse(
            nama_dosen       = dosen.nama_lengkap,
            nidn             = dosen.nim_nidn,
            hari_ini         = hari_ini,
            total_kelas      = 0,
            total_sesi_aktif = 0,
            jadwal_per_hari  = {h: [] for h in HARI_ORDER},
        )

    # ── 2. Bulk load data pendukung ──────────────────────────
    mk_ids      = list({k.matakuliah_id for k in kelas_list if k.matakuliah_id})
    ruangan_ids = list({k.ruangan_id    for k in kelas_list if k.ruangan_id})
    kelas_ids   = [k.id for k in kelas_list]

    # 2a. Matakuliah
    mk_map: dict = {}
    if mk_ids:
        mk_map = {
            mk.id: mk for mk in
            db.query(Matakuliah).filter(Matakuliah.id.in_(mk_ids)).all()
        }

    # 2b. Ruangan
    ruangan_map: dict = {}
    if ruangan_ids:
        ruangan_map = {
            r.id: r for r in
            db.query(Ruangan).filter(Ruangan.id.in_(ruangan_ids)).all()
        }

    # 2c. Enrolled count per kelas (asli + tamu)
    enrolled_rows = (
        db.query(
            MahasiswaMatakuliah.kelas_id,
            func.count(MahasiswaMatakuliah.id).label("total"),
            func.sum(
                func.cast(MahasiswaMatakuliah.is_tamu, db.bind.dialect.type_descriptor(
                    __import__('sqlalchemy', fromlist=['Integer']).Integer()
                ))
            ).label("tamu"),
        )
        .filter(MahasiswaMatakuliah.kelas_id.in_(kelas_ids))
        .group_by(MahasiswaMatakuliah.kelas_id)
        .all()
    )
    enrolled_map: dict = {
        str(r.kelas_id): {"total": r.total or 0, "tamu": r.tamu or 0}
        for r in enrolled_rows
    }

    # 2d. Sesi aktif hari ini (untuk status sesi)
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end   = today_start + timedelta(days=1)

    # Sesi yang sedang aktif — by matakuliah_id
    sesi_aktif_map: dict = {}
    for s in (
        db.query(SesiPresensi)
        .filter(
            SesiPresensi.matakuliah_id.in_(mk_ids),
            SesiPresensi.status == SesiStatus.aktif,
        )
        .all()
    ):
        # Satu MK bisa punya max 1 sesi aktif
        sesi_aktif_map[s.matakuliah_id] = s

    # Sesi yang selesai hari ini — ambil yang terbaru per MK
    sesi_selesai_hari_ini_map: dict = {}
    for s in (
        db.query(SesiPresensi)
        .filter(
            SesiPresensi.matakuliah_id.in_(mk_ids),
            SesiPresensi.status      == SesiStatus.selesai,
            SesiPresensi.waktu_tutup >= today_start,
            SesiPresensi.waktu_tutup <  today_end,
        )
        .order_by(SesiPresensi.waktu_tutup.desc())
        .all()
    ):
        if s.matakuliah_id not in sesi_selesai_hari_ini_map:
            sesi_selesai_hari_ini_map[s.matakuliah_id] = s

    # 2e. Hitung pertemuan berikutnya per MK (jumlah sesi selesai + 1)
    pertemuan_count_rows = (
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
    pertemuan_map: dict = {
        r.matakuliah_id: r.selesai + 1
        for r in pertemuan_count_rows
    }

    # 2f. Jadwal pengganti untuk pertemuan berikutnya
    # Ambil semua jadwal pengganti untuk MK yang diampu dosen ini
    pertemuan_targets = list(pertemuan_map.values())
    jp_list: list = []
    if mk_ids:
        jp_list = (
            db.query(JadwalPengganti)
            .filter(
                JadwalPengganti.matakuliah_id.in_(mk_ids),
                JadwalPengganti.dosen_id == dosen.id,
            )
            .all()
        )
    # Map: (matakuliah_id, pertemuan_ke) → JadwalPengganti
    jp_map: dict = {
        (jp.matakuliah_id, jp.pertemuan_ke): jp
        for jp in jp_list
    }

    # ── 3. Hitung total sesi aktif ───────────────────────────
    total_sesi_aktif = len(sesi_aktif_map)

    # ── 4. Bangun item jadwal per kelas ──────────────────────
    jadwal_per_hari: dict = {h: [] for h in HARI_ORDER}

    for kelas in kelas_list:
        mk      = mk_map.get(kelas.matakuliah_id)
        ruangan = ruangan_map.get(kelas.ruangan_id) if kelas.ruangan_id else None

        if not mk:
            logger.warning(
                f"Kelas {kelas.id} referensi matakuliah_id {kelas.matakuliah_id} "
                "tidak ditemukan — skip"
            )
            continue

        # Jam dari slot mapping
        jam_mulai, jam_selesai, jam_range = _fmt_slot_jam(
            kelas.slot_mulai, kelas.slot_selesai
        )

        # Enrolled count
        enrolled_info = enrolled_map.get(str(kelas.id), {"total": 0, "tamu": 0})

        # Status sesi hari ini
        status_sesi: Optional[str] = None
        sesi_id    : Optional[UUID] = None

        if kelas.hari == hari_ini:
            # Cek sesi aktif
            sesi_aktif = sesi_aktif_map.get(kelas.matakuliah_id)
            if sesi_aktif:
                status_sesi = "aktif"
                sesi_id     = sesi_aktif.id
            else:
                # Cek sesi selesai hari ini
                sesi_selesai = sesi_selesai_hari_ini_map.get(kelas.matakuliah_id)
                if sesi_selesai:
                    status_sesi = "selesai"
                    sesi_id     = sesi_selesai.id
                else:
                    status_sesi = "belum_dibuka"

        # Pertemuan berikutnya
        pertemuan_ke_berikutnya = pertemuan_map.get(kelas.matakuliah_id, 1)

        # Jadwal pengganti untuk pertemuan berikutnya
        ada_jp       = False
        jp_info      = None
        jp_obj = jp_map.get((kelas.matakuliah_id, pertemuan_ke_berikutnya))
        if jp_obj:
            ada_jp  = True
            jp_info = JadwalPenggantiInfoItem(
                jp_id            = jp_obj.id,
                pertemuan_ke     = jp_obj.pertemuan_ke,
                jam_mulai_baru   = _fmt_time(jp_obj.jam_mulai_baru),
                jam_selesai_baru = _fmt_time(jp_obj.jam_selesai_baru),
                ruangan_baru     = jp_obj.ruangan_baru,
                mode             = jp_obj.mode if hasattr(jp_obj, 'mode') else None,
                keterangan       = jp_obj.keterangan,
            )

        item = JadwalMingguanDosenItem(
            kelas_id         = kelas.id,
            kode_kelas       = kelas.kode_kelas,
            matakuliah_id    = mk.id,
            matakuliah_kode  = mk.kode,
            matakuliah_nama  = mk.nama,
            sks              = mk.sks,
            hari             = kelas.hari,
            slot_mulai       = kelas.slot_mulai,
            slot_selesai     = kelas.slot_selesai,
            jam_mulai        = jam_mulai,
            jam_selesai      = jam_selesai,
            jam_range        = jam_range,
            ruangan_id       = ruangan.id           if ruangan else None,
            kode_ruangan     = ruangan.kode         if ruangan else None,
            nama_ruangan     = ruangan.nama         if ruangan else None,
            koordinat_lat    = ruangan.koordinat_lat if ruangan else None,
            koordinat_lng    = ruangan.koordinat_lng if ruangan else None,
            jumlah_mahasiswa = enrolled_info["total"],
            jumlah_tamu      = enrolled_info["tamu"],
            status_sesi      = status_sesi,
            sesi_id          = sesi_id,
            pertemuan_ke_berikutnya = pertemuan_ke_berikutnya,
            ada_jadwal_pengganti    = ada_jp,
            jadwal_pengganti        = jp_info,
            izin_tamu        = kelas.izin_tamu,
        )

        # Kelompokkan per hari — gunakan hari kelas, default ke hari pertama jika null
        hari_kelas = kelas.hari or "Senin"
        if hari_kelas in jadwal_per_hari:
            jadwal_per_hari[hari_kelas].append(item)
        else:
            logger.warning(f"Hari tidak valid '{hari_kelas}' di kelas {kelas.id} — skip")

    # ── 5. Sort tiap hari berdasarkan slot_mulai ─────────────
    for hari in HARI_ORDER:
        jadwal_per_hari[hari].sort(
            key=lambda x: (x.slot_mulai or 99, x.kode_kelas or "")
        )

    logger.info(
        f"[jadwal_dosen_service] dosen_id={dosen.id} → "
        f"total_kelas={len(kelas_list)}, "
        f"total_sesi_aktif={total_sesi_aktif}"
    )

    return JadwalMingguanDosenResponse(
        nama_dosen       = dosen.nama_lengkap,
        nidn             = dosen.nim_nidn,
        hari_ini         = hari_ini,
        total_kelas      = len(kelas_list),
        total_sesi_aktif = total_sesi_aktif,
        jadwal_per_hari  = jadwal_per_hari,
    )