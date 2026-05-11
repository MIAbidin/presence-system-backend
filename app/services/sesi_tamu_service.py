# app/services/sesi_tamu_service.py
"""
Fase B-3 — Service: Ambil sesi aktif yang bisa diikuti mahasiswa sebagai tamu.

Endpoint: GET /sesi/aktif-tamu
Dipanggil dari: TamuSesiListScreen Flutter v2.1.0
Trigger: Mahasiswa tap 'Ikut sebagai Tamu' di ScanScreen ketika sistem
         mendeteksi tidak ada sesi aktif untuk jadwalnya sendiri.

Logic utama (mahasiswa X ingin masuk sebagai tamu ke kelas Y):
─────────────────────────────────────────────────────────────────
Sesi MUNCUL di list jika memenuhi SALAH SATU syarat:

  Syarat 1 — Tamu manual:
    Mahasiswa X sudah didaftarkan oleh dosen di mahasiswa_matakuliah
    dengan is_tamu=TRUE untuk matakuliah yang sesi-nya sedang aktif.

  Syarat 2 — Izin tamu otomatis:
    Kelas (kelas_matakuliah.izin_tamu=TRUE) atau matakuliah
    (matakuliah.izin_tamu=TRUE) membuka izin tamu untuk siapapun.

Sesi TIDAK MUNCUL jika:
  - Mahasiswa sudah enrolled sebagai mahasiswa ASLI (is_tamu=FALSE)
    di MK tersebut → gunakan alur presensi normal
  - Mahasiswa sudah punya record presensi (hadir/terlambat) di sesi ini
  - Sesi tidak aktif (status != 'aktif')

Urutan hasil: sesi 'manual' dulu (lebih tinggi prioritasnya), lalu 'auto'.
Dalam kelompok yang sama, diurutkan berdasarkan jam mulai.

Query strategy (efisien, menghindari N+1):
1. Satu query sesi aktif semua
2. Satu query mahasiswa_matakuliah untuk mahasiswa ini
3. Satu query presensi yang sudah ada untuk exclude
4. Bulk load matakuliah, kelas, ruangan, dosen dalam satu query masing-masing
5. Proses di Python — tidak ada loop query
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
from app.schemas.sesi_tamu import SesiTamuItem, SesiTamuListResponse

logger = logging.getLogger(__name__)

WIB = ZoneInfo("Asia/Jakarta")

# Mapping slot ke jam — sesuai slot_utils.py
from app.utils.slot_utils import SLOT_MAPPING


def _hitung_detik_tersisa(sesi: SesiPresensi) -> Optional[int]:
    """Hitung sisa detik kode online. Return None untuk mode offline."""
    if not sesi.kode_expire_at:
        return None
    expire = sesi.kode_expire_at
    if expire.tzinfo is None:
        expire = expire.replace(tzinfo=timezone.utc)
    delta = expire - datetime.now(timezone.utc)
    return max(0, int(delta.total_seconds()))


def _get_jam_dari_kelas(kelas: Optional[KelasMatakuliah]) -> tuple[Optional[str], Optional[str]]:
    """
    Ambil jam_mulai dan jam_selesai dari slot mapping kelas.
    Return: (jam_mulai_str, jam_selesai_str) atau (None, None).
    """
    if not kelas or kelas.slot_mulai is None or kelas.slot_selesai is None:
        return None, None

    slot_m = SLOT_MAPPING.get(kelas.slot_mulai)
    slot_s = SLOT_MAPPING.get(kelas.slot_selesai)

    if not slot_m or not slot_s:
        return None, None

    return slot_m[0].strftime("%H:%M"), slot_s[1].strftime("%H:%M")


def get_sesi_aktif_tamu(
    db          : Session,
    mahasiswa_id: UUID,
) -> SesiTamuListResponse:
    """
    Ambil semua sesi aktif yang bisa diikuti mahasiswa sebagai tamu.

    Return SesiTamuListResponse — selalu HTTP 200, tidak pernah raise exception.
    List kosong jika tidak ada sesi yang tersedia.

    Prioritas urutan hasil:
    1. Sesi 'manual' (dosen daftarkan mahasiswa ini) — teratas
    2. Sesi 'auto' (kelas/MK buka izin tamu) — di bawahnya
    Dalam masing-masing kelompok, diurutkan dari jam mulai lebih awal.
    """
    try:
        return _get_sesi_aktif_tamu_impl(db, mahasiswa_id)
    except Exception as e:
        logger.error(
            f"[sesi_tamu_service] Error get_sesi_aktif_tamu "
            f"mahasiswa_id={mahasiswa_id}: {e}",
            exc_info=True,
        )
        # Jangan crash — kembalikan list kosong dengan pesan error
        return SesiTamuListResponse(
            sesi_list=[],
            total=0,
            pesan="Terjadi kesalahan saat memuat daftar sesi. Coba lagi.",
        )


def _get_sesi_aktif_tamu_impl(
    db          : Session,
    mahasiswa_id: UUID,
) -> SesiTamuListResponse:
    """
    Implementasi utama — dipisah agar error handling bersih.
    """

    # ── 1. Ambil semua sesi yang sedang aktif ────────────────
    semua_sesi_aktif = (
        db.query(SesiPresensi)
        .filter(SesiPresensi.status == SesiStatus.aktif)
        .all()
    )

    if not semua_sesi_aktif:
        logger.debug("Tidak ada sesi aktif sama sekali di sistem")
        return SesiTamuListResponse(sesi_list=[], total=0)

    semua_mk_ids  = list({s.matakuliah_id for s in semua_sesi_aktif})
    semua_sesi_ids = [s.id for s in semua_sesi_aktif]

    # ── 2. Enrollment mahasiswa ini (asli maupun tamu) ───────
    # Dipakai untuk:
    #   a. Exclude MK yang sudah diikuti sebagai mahasiswa ASLI
    #      (bukan tamu) → gunakan alur presensi normal
    #   b. Identifikasi MK yang sudah diikuti sebagai TAMU
    #      → muncul di list dengan izin_tamu_source='manual'
    enrollment_rows = (
        db.query(MahasiswaMatakuliah)
        .filter(
            MahasiswaMatakuliah.mahasiswa_id  == mahasiswa_id,
            MahasiswaMatakuliah.matakuliah_id.in_(semua_mk_ids),
        )
        .all()
    )

    # Set matakuliah_id yang sudah diikuti sebagai mahasiswa ASLI
    mk_asli_ids: set = {
        row.matakuliah_id
        for row in enrollment_rows
        if not row.is_tamu
    }

    # Set matakuliah_id yang sudah diikuti sebagai TAMU
    mk_tamu_ids: set = {
        row.matakuliah_id
        for row in enrollment_rows
        if row.is_tamu
    }

    # ── 3. Sesi yang sudah dipresensi — exclude dari hasil ───
    sudah_presensi_sesi_ids: set = {
        p.sesi_id
        for p in db.query(Presensi).filter(
            Presensi.mahasiswa_id == mahasiswa_id,
            Presensi.sesi_id.in_(semua_sesi_ids),
            # Exclude hanya yang sudah hadir/terlambat
            # Absen/izin/sakit yang di-insert scheduler bisa di-override
            Presensi.status.in_([PresensiStatus.hadir, PresensiStatus.terlambat]),
        ).all()
    }

    # ── 4. Bulk load data pendukung ──────────────────────────
    # 4a. Matakuliah
    mk_map: dict = {
        mk.id: mk
        for mk in db.query(Matakuliah).filter(Matakuliah.id.in_(semua_mk_ids)).all()
    }

    # 4b. Kelas yang terkait dengan sesi aktif
    #     Cari kelas_id via kelas_matakuliah.matakuliah_id
    kelas_list = (
        db.query(KelasMatakuliah)
        .filter(
            KelasMatakuliah.matakuliah_id.in_(semua_mk_ids),
            KelasMatakuliah.is_active == True,
        )
        .all()
    )
    # Map: matakuliah_id → list kelas (satu MK bisa punya beberapa kelas)
    mk_kelas_map: dict = {}
    for k in kelas_list:
        mk_kelas_map.setdefault(k.matakuliah_id, []).append(k)

    # 4c. Ruangan dari kelas
    ruangan_ids = list({k.ruangan_id for k in kelas_list if k.ruangan_id})
    ruangan_map: dict = {}
    if ruangan_ids:
        ruangan_map = {
            r.id: r
            for r in db.query(Ruangan).filter(Ruangan.id.in_(ruangan_ids)).all()
        }

    # 4d. Dosen dari sesi dan kelas
    dosen_ids = list({
        *[s.dosen_id for s in semua_sesi_aktif if s.dosen_id],
        *[k.dosen_id for k in kelas_list if k.dosen_id],
    })
    dosen_map: dict = {}
    if dosen_ids:
        dosen_map = {
            u.id: u
            for u in db.query(User).filter(User.id.in_(dosen_ids)).all()
        }

    # ── 5. Filter dan klasifikasi sesi ───────────────────────
    sesi_manual: list[SesiTamuItem] = []
    sesi_auto  : list[SesiTamuItem] = []

    for sesi in semua_sesi_aktif:
        mk_id = sesi.matakuliah_id

        # Skip jika sudah presensi
        if sesi.id in sudah_presensi_sesi_ids:
            logger.debug(f"Skip sesi {sesi.id}: mahasiswa sudah presensi")
            continue

        # Skip jika mahasiswa adalah mahasiswa ASLI di MK ini
        # → gunakan alur presensi normal GET /sesi/aktif-mahasiswa
        if mk_id in mk_asli_ids:
            logger.debug(f"Skip sesi {sesi.id}: mahasiswa sudah enrolled asli di MK {mk_id}")
            continue

        mk = mk_map.get(mk_id)
        if not mk:
            logger.warning(f"Skip sesi {sesi.id}: matakuliah {mk_id} tidak ditemukan di DB")
            continue

        # ── Tentukan apakah mahasiswa boleh masuk sebagai tamu ──

        # Cek Syarat 1: Sudah terdaftar manual sebagai tamu di MK ini
        is_tamu_manual = mk_id in mk_tamu_ids

        # Cek Syarat 2: Kelas atau MK membuka izin tamu
        # Ambil semua kelas untuk MK ini, cek apakah ada yang izin_tamu=True
        kelas_mk = mk_kelas_map.get(mk_id, [])
        is_izin_tamu_kelas = any(k.izin_tamu for k in kelas_mk)
        is_izin_tamu_mk    = mk.izin_tamu

        # Jika tidak memenuhi syarat manapun → skip
        if not is_tamu_manual and not is_izin_tamu_kelas and not is_izin_tamu_mk:
            logger.debug(
                f"Skip sesi {sesi.id}: MK {mk.kode} tidak izinkan tamu, "
                f"mahasiswa tidak terdaftar sebagai tamu"
            )
            continue

        # ── Kumpulkan data lengkap untuk item response ──────────

        # Untuk izin tamu, ambil kelas pertama yang mengizinkan
        # (atau kelas pertama untuk MK yang izin_tamu=True di level MK)
        target_kelas: Optional[KelasMatakuliah] = None
        if kelas_mk:
            if is_tamu_manual or is_izin_tamu_mk:
                # Semua kelas boleh → ambil kelas pertama berdasarkan kode_kelas
                target_kelas = sorted(kelas_mk, key=lambda k: k.kode_kelas)[0]
            else:
                # Hanya kelas dengan izin_tamu=True
                kelas_tamu = [k for k in kelas_mk if k.izin_tamu]
                if kelas_tamu:
                    target_kelas = sorted(kelas_tamu, key=lambda k: k.kode_kelas)[0]

        # Info kelas
        kelas_id   = target_kelas.id          if target_kelas else None
        kode_kelas = target_kelas.kode_kelas  if target_kelas else None
        hari       = target_kelas.hari        if target_kelas else mk.hari

        # Jam dari slot mapping
        jam_mulai, jam_selesai = _get_jam_dari_kelas(target_kelas)
        if not jam_mulai and mk.jam_mulai:
            jam_mulai   = mk.jam_mulai.strftime("%H:%M")
        if not jam_selesai and mk.jam_selesai:
            jam_selesai = mk.jam_selesai.strftime("%H:%M")

        # Dosen: dari kelas dulu, fallback ke sesi
        dosen_nama: Optional[str] = None
        if target_kelas and target_kelas.dosen_id:
            d = dosen_map.get(target_kelas.dosen_id)
            if d:
                dosen_nama = d.nama_lengkap
        if not dosen_nama and sesi.dosen_id:
            d = dosen_map.get(sesi.dosen_id)
            if d:
                dosen_nama = d.nama_lengkap

        # Ruangan dan koordinat
        ruangan_nama: Optional[str]  = None
        koord_lat   : Optional[float] = None
        koord_lng   : Optional[float] = None

        if target_kelas and target_kelas.ruangan_id:
            r = ruangan_map.get(target_kelas.ruangan_id)
            if r:
                ruangan_nama = r.nama
                koord_lat    = r.koordinat_lat
                koord_lng    = r.koordinat_lng

        # Fallback ke field string lama di matakuliah
        if not ruangan_nama:
            ruangan_nama = mk.ruangan
        if koord_lat is None:
            koord_lat = mk.koordinat_lat
            koord_lng = mk.koordinat_lng

        # Sumber izin tamu
        izin_tamu_source = "manual" if is_tamu_manual else "auto"

        item = SesiTamuItem(
            sesi_id          = sesi.id,
            mode             = sesi.mode.value,
            pertemuan_ke     = sesi.pertemuan_ke,
            waktu_buka       = sesi.waktu_buka,
            matakuliah_id    = mk.id,
            matakuliah_nama  = mk.nama,
            matakuliah_kode  = mk.kode,
            kelas_id         = kelas_id,
            kode_kelas       = kode_kelas,
            dosen_nama       = dosen_nama,
            ruangan          = ruangan_nama,
            jam_mulai        = jam_mulai,
            jam_selesai      = jam_selesai,
            hari             = hari,
            koordinat_lat    = koord_lat,
            koordinat_lng    = koord_lng,
            izin_tamu_source = izin_tamu_source,
            detik_tersisa    = _hitung_detik_tersisa(sesi),
        )

        if izin_tamu_source == "manual":
            sesi_manual.append(item)
        else:
            sesi_auto.append(item)

    # ── 6. Urutkan dan gabungkan ─────────────────────────────
    # Manual dulu, lalu auto. Dalam masing-masing kelompok,
    # urutkan berdasarkan jam_mulai (lebih pagi dulu).
    def sort_key(item: SesiTamuItem) -> str:
        return item.jam_mulai or "99:99"

    sesi_manual.sort(key=sort_key)
    sesi_auto.sort(key=sort_key)

    hasil = sesi_manual + sesi_auto

    logger.info(
        f"[sesi_tamu_service] mahasiswa_id={mahasiswa_id} → "
        f"{len(sesi_manual)} sesi manual + {len(sesi_auto)} sesi auto "
        f"= {len(hasil)} total"
    )

    return SesiTamuListResponse(
        sesi_list=hasil,
        total=len(hasil),
        pesan=None if hasil else (
            "Tidak ada sesi yang tersedia untuk Anda sebagai tamu. "
            "Minta dosen untuk menambahkan Anda atau mengaktifkan izin tamu kelas."
        ),
    )