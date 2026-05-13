"""
app/services/dosen_service.py
══════════════════════════════
BUGFIX: get_beranda_dosen sekarang membaca jadwal dari kelas_matakuliah
(bukan dari matakuliah.hari yang sering kosong).

Sebelumnya: filter berdasarkan matakuliah.hari → dosen yang jadwalnya
di kelas_matakuliah tidak muncul karena matakuliah.hari bisa NULL.

Sekarang: query kelas_matakuliah WHERE dosen_id = dosen.id AND hari = hari_ini
→ konsisten dengan jadwal_dosen_service.py (GET /dosen/jadwal/mingguan).
"""

import logging
from datetime import datetime, timezone, timedelta, date
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.matakuliah import Matakuliah
from app.models.kelas_matakuliah import KelasMatakuliah
from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
from app.models.sesi import SesiPresensi, SesiStatus
from app.models.presensi import Presensi, PresensiStatus
from app.models.jadwal_pengganti import JadwalPengganti

logger = logging.getLogger(__name__)

HARI_ORDER = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
WEEKDAY_TO_HARI = {
    0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis",
    4: "Jumat", 5: "Sabtu", 6: "Minggu",
}

WIB = ZoneInfo("Asia/Jakarta")


def _format_time(t):
    """Helper format time → 'HH:MM' string."""
    if t is None:
        return None
    if hasattr(t, "strftime"):
        return t.strftime("%H:%M")
    return str(t)[:5]


# ─── 3.1 — BERANDA DOSEN ─────────────────────────────────────

def get_beranda_dosen(db: Session, dosen: User) -> dict:
    """
    Satu endpoint untuk beranda dosen:
    - Jadwal hari ini (dari kelas_matakuliah, bukan matakuliah.hari)
    - Status sesi tiap kelas: belum_mulai / aktif / selesai
    - Info redirect ke tab Jadwal untuk semua MK

    BUGFIX: Sebelumnya menggunakan matakuliah.hari yang sering NULL
    (jadwal reguler tidak diisi kalau sudah pakai kelas_matakuliah).
    Sekarang query langsung ke kelas_matakuliah WHERE dosen_id = dosen.id.
    """
    # Gunakan WIB untuk hari ini
    now_wib  = datetime.now(WIB)
    hari_ini = WEEKDAY_TO_HARI.get(now_wib.weekday(), "")
    today_start = datetime.combine(date.today(), datetime.min.time())

    # ── Query 1: Kelas yang diampu dosen hari ini (dari kelas_matakuliah) ──
    # Ini adalah fix utama: pakai kelas_matakuliah bukan matakuliah.hari
    kelas_hari_ini = (
        db.query(KelasMatakuliah)
        .filter(
            KelasMatakuliah.dosen_id  == dosen.id,
            KelasMatakuliah.hari      == hari_ini,
            KelasMatakuliah.is_active == True,
        )
        .all()
    )

    # Bulk load matakuliah untuk kelas-kelas tersebut
    mk_ids_hari_ini = list({k.matakuliah_id for k in kelas_hari_ini if k.matakuliah_id})
    mk_map: dict = {}
    if mk_ids_hari_ini:
        mk_map = {
            mk.id: mk
            for mk in db.query(Matakuliah).filter(Matakuliah.id.in_(mk_ids_hari_ini)).all()
        }

    # ── Query 2: Semua sesi aktif dosen ──
    sesi_aktif_map: dict = {}
    for s in db.query(SesiPresensi).filter(
        SesiPresensi.dosen_id == dosen.id,
        SesiPresensi.status   == SesiStatus.aktif,
    ).all():
        sesi_aktif_map[s.matakuliah_id] = s

    # ── Query 3: Sesi terakhir hari ini ──
    sesi_hari_ini_map: dict = {}
    for s in db.query(SesiPresensi).filter(
        SesiPresensi.dosen_id   == dosen.id,
        SesiPresensi.waktu_buka >= today_start,
    ).order_by(SesiPresensi.waktu_buka.desc()).all():
        if s.matakuliah_id not in sesi_hari_ini_map:
            sesi_hari_ini_map[s.matakuliah_id] = s

    # ── Query 4: Jumlah mahasiswa per kelas ──
    kelas_ids = [k.id for k in kelas_hari_ini]
    jumlah_map: dict = {}
    if kelas_ids:
        from sqlalchemy import func
        rows = (
            db.query(
                MahasiswaMatakuliah.kelas_id,
                func.count(MahasiswaMatakuliah.id).label("cnt"),
            )
            .filter(MahasiswaMatakuliah.kelas_id.in_(kelas_ids))
            .group_by(MahasiswaMatakuliah.kelas_id)
            .all()
        )
        jumlah_map = {str(r.kelas_id): r.cnt for r in rows}

    # ── Query 5: Jadwal pengganti untuk pertemuan berikutnya ──
    # Hitung pertemuan_ke_berikutnya per MK
    from sqlalchemy import func as sqlfunc
    pertemuan_rows = (
        db.query(
            SesiPresensi.matakuliah_id,
            sqlfunc.count(SesiPresensi.id).label("selesai"),
        )
        .filter(
            SesiPresensi.matakuliah_id.in_(mk_ids_hari_ini),
            SesiPresensi.status == SesiStatus.selesai,
        )
        .group_by(SesiPresensi.matakuliah_id)
        .all()
    ) if mk_ids_hari_ini else []
    pertemuan_map = {r.matakuliah_id: r.selesai + 1 for r in pertemuan_rows}
    for mk_id in mk_ids_hari_ini:
        if mk_id not in pertemuan_map:
            pertemuan_map[mk_id] = 1

    jp_list = (
        db.query(JadwalPengganti)
        .filter(JadwalPengganti.matakuliah_id.in_(mk_ids_hari_ini))
        .all()
    ) if mk_ids_hari_ini else []
    jp_map: dict = {
        (jp.matakuliah_id, jp.pertemuan_ke): jp
        for jp in jp_list
    }

    # ── Susun jadwal hari ini ──
    jadwal_hari_ini = []
    for kelas in kelas_hari_ini:
        mk = mk_map.get(kelas.matakuliah_id)
        if not mk:
            continue

        sesi_aktif  = sesi_aktif_map.get(mk.id)
        sesi_kemarin = sesi_hari_ini_map.get(mk.id)

        if sesi_aktif:
            status_sesi = "aktif"
            sesi_ref    = sesi_aktif
        elif sesi_kemarin and sesi_kemarin.status.value == "selesai":
            status_sesi = "selesai"
            sesi_ref    = sesi_kemarin
        else:
            status_sesi = "belum_mulai"
            sesi_ref    = None

        pertemuan_ke = pertemuan_map.get(mk.id, 1)
        jp = jp_map.get((mk.id, pertemuan_ke))

        # Jam dari slot kelas atau dari matakuliah.jam_mulai sebagai fallback
        from app.utils.slot_utils import SLOT_MAPPING
        jam_mulai_str   = None
        jam_selesai_str = None
        if kelas.slot_mulai and kelas.slot_selesai:
            slot_m = SLOT_MAPPING.get(kelas.slot_mulai)
            slot_s = SLOT_MAPPING.get(kelas.slot_selesai)
            if slot_m and slot_s:
                jam_mulai_str   = slot_m[0].strftime("%H:%M")
                jam_selesai_str = slot_s[1].strftime("%H:%M")
        if not jam_mulai_str:
            jam_mulai_str   = _format_time(mk.jam_mulai)
            jam_selesai_str = _format_time(mk.jam_selesai)

        # Ruangan dari kelas atau fallback ke matakuliah
        ruangan_nama = None
        if kelas.ruangan:
            ruangan_nama = kelas.ruangan.nama or kelas.ruangan.kode
        if not ruangan_nama:
            ruangan_nama = mk.ruangan

        jadwal_hari_ini.append({
            "matakuliah_id"    : str(mk.id),
            "kode"             : mk.kode,
            "nama"             : mk.nama,
            "sks"              : mk.sks,
            "hari"             : kelas.hari,
            "kode_kelas"       : kelas.kode_kelas,
            "kelas_id"         : str(kelas.id),
            "slot_mulai"       : kelas.slot_mulai,
            "slot_selesai"     : kelas.slot_selesai,
            "jam_mulai"        : jam_mulai_str,
            "jam_selesai"      : jam_selesai_str,
            "ruangan"          : ruangan_nama,
            "izin_tamu"        : kelas.izin_tamu,
            "jumlah_mahasiswa" : jumlah_map.get(str(kelas.id), 0),
            "status_sesi"      : status_sesi,
            "sesi_id"          : str(sesi_ref.id)        if sesi_ref else None,
            "pertemuan_ke"     : sesi_ref.pertemuan_ke   if sesi_ref else pertemuan_ke,
            "kode_sesi"        : sesi_ref.kode_sesi      if sesi_ref else None,
            "detik_tersisa"    : _hitung_detik(sesi_ref) if sesi_ref else None,
            # Jadwal pengganti
            "ada_jadwal_pengganti"  : jp is not None,
            "jam_mulai_pengganti"   : _format_time(jp.jam_mulai_baru)   if jp else None,
            "jam_selesai_pengganti" : _format_time(jp.jam_selesai_baru) if jp else None,
            "ruangan_pengganti"     : jp.ruangan_baru                    if jp else None,
            "mode_pengganti"        : getattr(jp, "mode", None)          if jp else None,
        })

    # Urutkan berdasarkan jam_mulai
    jadwal_hari_ini.sort(key=lambda x: x.get("jam_mulai") or "99:99")

    # ── Semua matakuliah yang diampu (untuk info redirect di beranda) ──
    # Ambil semua kelas_matakuliah dosen, jadikan set MK unik
    semua_kelas = (
        db.query(KelasMatakuliah)
        .filter(
            KelasMatakuliah.dosen_id  == dosen.id,
            KelasMatakuliah.is_active == True,
        )
        .all()
    )
    semua_mk_ids = list({k.matakuliah_id for k in semua_kelas if k.matakuliah_id})
    semua_mk_map: dict = {}
    if semua_mk_ids:
        semua_mk_map = {
            mk.id: mk
            for mk in db.query(Matakuliah).filter(Matakuliah.id.in_(semua_mk_ids)).all()
        }

    semua_matakuliah = []
    for mk_id, mk in semua_mk_map.items():
        sesi_aktif = sesi_aktif_map.get(mk.id)
        semua_matakuliah.append({
            "matakuliah_id"  : str(mk.id),
            "kode"           : mk.kode,
            "nama"           : mk.nama,
            "sks"            : mk.sks,
            "ada_sesi_aktif" : sesi_aktif is not None,
            "sesi_id"        : str(sesi_aktif.id) if sesi_aktif else None,
        })

    return {
        "nama_dosen"      : dosen.nama_lengkap,
        "nidn"            : dosen.nim_nidn,
        "hari_ini"        : hari_ini,
        "tanggal"         : date.today().isoformat(),
        "jadwal_hari_ini" : jadwal_hari_ini,
        "semua_matakuliah": semua_matakuliah,
    }


def _hitung_detik(sesi: SesiPresensi) -> Optional[int]:
    if not sesi or not sesi.kode_expire_at:
        return None
    expire = sesi.kode_expire_at
    if expire.tzinfo is None:
        expire = expire.replace(tzinfo=timezone.utc)
    delta = expire - datetime.now(timezone.utc)
    return max(0, int(delta.total_seconds()))


# ─── 3.2 — DETAIL MATAKULIAH ─────────────────────────────────

def get_detail_matakuliah(
    db           : Session,
    dosen        : User,
    matakuliah_id: UUID,
) -> dict:
    mk = db.query(Matakuliah).filter(Matakuliah.id == matakuliah_id).first()
    if not mk:
        return None

    rows = db.query(MahasiswaMatakuliah).filter(
        MahasiswaMatakuliah.matakuliah_id == matakuliah_id
    ).all()

    mahasiswa_list = []
    for row in rows:
        mhs = row.mahasiswa
        if not mhs:
            continue
        mahasiswa_list.append({
            "mahasiswa_id" : str(mhs.id),
            "nim"          : mhs.nim_nidn,
            "nama_lengkap" : mhs.nama_lengkap,
            "program_studi": mhs.program_studi,
            "is_tamu"      : row.is_tamu,
            "kelas_asal"   : row.kelas_asal,
        })

    jadwal_pengganti_list = db.query(JadwalPengganti).filter(
        JadwalPengganti.matakuliah_id == matakuliah_id
    ).order_by(JadwalPengganti.pertemuan_ke).all()

    jadwal_pengganti = [
        {
            "id"              : str(jp.id),
            "pertemuan_ke"    : jp.pertemuan_ke,
            "jam_mulai_baru"  : _format_time(jp.jam_mulai_baru),
            "jam_selesai_baru": _format_time(jp.jam_selesai_baru),
            "ruangan_baru"    : jp.ruangan_baru,
            "mode"            : getattr(jp, "mode", None),
            "keterangan"      : jp.keterangan,
            "created_at"      : jp.created_at.isoformat() if jp.created_at else None,
        }
        for jp in jadwal_pengganti_list
    ]

    sesi_list = db.query(SesiPresensi).filter(
        SesiPresensi.matakuliah_id == matakuliah_id,
        SesiPresensi.dosen_id      == dosen.id,
    ).order_by(SesiPresensi.waktu_buka.desc()).limit(10).all()

    riwayat_sesi = []
    for sesi in sesi_list:
        total = db.query(Presensi).filter(Presensi.sesi_id == sesi.id).count()
        hadir = db.query(Presensi).filter(
            Presensi.sesi_id == sesi.id,
            Presensi.status.in_([PresensiStatus.hadir, PresensiStatus.terlambat])
        ).count()
        riwayat_sesi.append({
            "sesi_id"    : str(sesi.id),
            "mode"       : sesi.mode.value,
            "pertemuan_ke": sesi.pertemuan_ke,
            "waktu_buka" : sesi.waktu_buka.isoformat() if sesi.waktu_buka else None,
            "waktu_tutup": sesi.waktu_tutup.isoformat() if sesi.waktu_tutup else None,
            "status"     : sesi.status.value,
            "total_mhs"  : total,
            "hadir"      : hadir,
            "persentase" : round(hadir / total * 100, 1) if total else 0.0,
        })

    total_asli = sum(1 for m in mahasiswa_list if not m["is_tamu"])
    total_tamu = sum(1 for m in mahasiswa_list if m["is_tamu"])

    return {
        "matakuliah_id" : str(mk.id),
        "kode"          : mk.kode,
        "nama"          : mk.nama,
        "sks"           : mk.sks,
        "hari"          : mk.hari,
        "jam_mulai"     : _format_time(mk.jam_mulai),
        "jam_selesai"   : _format_time(mk.jam_selesai),
        "ruangan"       : mk.ruangan,
        "koordinat_lat" : mk.koordinat_lat,
        "koordinat_lng" : mk.koordinat_lng,
        "izin_tamu"     : mk.izin_tamu,
        "total_asli"    : total_asli,
        "total_tamu"    : total_tamu,
        "mahasiswa"     : mahasiswa_list,
        "jadwal_pengganti": jadwal_pengganti,
        "riwayat_sesi"  : riwayat_sesi,
    }


# ─── 3.3 — TOGGLE IZIN TAMU ──────────────────────────────────

def toggle_izin_tamu(
    db           : Session,
    matakuliah_id: UUID,
    izin_tamu    : bool,
) -> dict:
    mk = db.query(Matakuliah).filter(Matakuliah.id == matakuliah_id).first()
    if not mk:
        return None

    mk.izin_tamu = izin_tamu
    db.commit()
    db.refresh(mk)

    return {
        "matakuliah_id": str(mk.id),
        "nama"         : mk.nama,
        "izin_tamu"    : mk.izin_tamu,
        "pesan"        : (
            f"Izin tamu {mk.nama} diaktifkan."
        ) if izin_tamu else (
            f"Izin tamu {mk.nama} dinonaktifkan."
        ),
    }


# ─── 3.4 — TAMBAH / HAPUS TAMU MANUAL ────────────────────────

def tambah_tamu_manual(
    db           : Session,
    matakuliah_id: UUID,
    nim          : str,
) -> tuple[bool, str, Optional[dict]]:
    mhs = db.query(User).filter(
        User.nim_nidn == nim.strip(),
        User.role     == UserRole.mahasiswa,
    ).first()

    if not mhs:
        return False, f"Mahasiswa dengan NIM {nim} tidak ditemukan", None

    existing = db.query(MahasiswaMatakuliah).filter(
        MahasiswaMatakuliah.mahasiswa_id  == mhs.id,
        MahasiswaMatakuliah.matakuliah_id == matakuliah_id,
    ).first()

    if existing:
        if existing.is_tamu:
            return False, f"{mhs.nama_lengkap} sudah terdaftar sebagai tamu", None
        else:
            return False, f"{mhs.nama_lengkap} sudah terdaftar sebagai mahasiswa asli", None

    row_asli = db.query(MahasiswaMatakuliah).filter(
        MahasiswaMatakuliah.mahasiswa_id  == mhs.id,
        MahasiswaMatakuliah.matakuliah_id != matakuliah_id,
        MahasiswaMatakuliah.is_tamu       == False,
    ).first()

    kelas_asal = None
    if row_asli and row_asli.matakuliah:
        kelas_asal = f"{row_asli.matakuliah.kode} - {row_asli.matakuliah.nama}"

    db.add(MahasiswaMatakuliah(
        mahasiswa_id  = mhs.id,
        matakuliah_id = matakuliah_id,
        is_tamu       = True,
        kelas_asal    = kelas_asal,
    ))
    db.commit()

    return True, f"{mhs.nama_lengkap} berhasil ditambahkan sebagai tamu", {
        "mahasiswa_id" : str(mhs.id),
        "nim"          : mhs.nim_nidn,
        "nama_lengkap" : mhs.nama_lengkap,
        "program_studi": mhs.program_studi,
        "is_tamu"      : True,
        "kelas_asal"   : kelas_asal,
    }


def hapus_tamu(
    db           : Session,
    matakuliah_id: UUID,
    mahasiswa_id : UUID,
) -> tuple[bool, str]:
    row = db.query(MahasiswaMatakuliah).filter(
        MahasiswaMatakuliah.mahasiswa_id  == mahasiswa_id,
        MahasiswaMatakuliah.matakuliah_id == matakuliah_id,
    ).first()

    if not row:
        return False, "Mahasiswa tidak terdaftar di matakuliah ini"

    if not row.is_tamu:
        return False, "Tidak dapat menghapus mahasiswa asli lewat endpoint ini."

    mhs_nama = row.mahasiswa.nama_lengkap if row.mahasiswa else "Mahasiswa"
    db.delete(row)
    db.commit()
    return True, f"{mhs_nama} berhasil dihapus dari daftar tamu"


# ─── 3.5 — JADWAL PENGGANTI ──────────────────────────────────

def simpan_jadwal_pengganti(
    db, dosen, matakuliah_id, pertemuan_ke, jam_mulai_baru,
    jam_selesai_baru, ruangan_baru, keterangan, mode=None,
):
    from datetime import time as dtime
    from app.models.matakuliah import Matakuliah

    def parse_jam(jam_str):
        if not jam_str:
            return None
        try:
            h, m = jam_str.split(":")
            return dtime(int(h), int(m))
        except Exception:
            return None

    mk = db.query(Matakuliah).filter(Matakuliah.id == matakuliah_id).first()
    if not mk:
        return False, "Matakuliah tidak ditemukan", None

    mode_valid = {None, "offline", "online"}
    if mode not in mode_valid:
        return False, f"Mode tidak valid: '{mode}'.", None

    existing = db.query(JadwalPengganti).filter(
        JadwalPengganti.matakuliah_id == matakuliah_id,
        JadwalPengganti.pertemuan_ke  == pertemuan_ke,
    ).first()

    jam_mulai_obj   = parse_jam(jam_mulai_baru)
    jam_selesai_obj = parse_jam(jam_selesai_baru)

    if existing:
        existing.jam_mulai_baru   = jam_mulai_obj
        existing.jam_selesai_baru = jam_selesai_obj
        existing.ruangan_baru     = ruangan_baru
        existing.keterangan       = keterangan
        existing.dosen_id         = dosen.id
        existing.mode             = mode
        db.commit()
        db.refresh(existing)
        jp   = existing
        aksi = "diperbarui"
    else:
        jp = JadwalPengganti(
            matakuliah_id    = matakuliah_id,
            dosen_id         = dosen.id,
            pertemuan_ke     = pertemuan_ke,
            jam_mulai_baru   = jam_mulai_obj,
            jam_selesai_baru = jam_selesai_obj,
            ruangan_baru     = ruangan_baru,
            keterangan       = keterangan,
            mode             = mode,
        )
        db.add(jp)
        db.commit()
        db.refresh(jp)
        aksi = "disimpan"

    return True, f"Jadwal pengganti pertemuan {pertemuan_ke} berhasil {aksi}", {
        "id"              : str(jp.id),
        "pertemuan_ke"    : jp.pertemuan_ke,
        "jam_mulai_baru"  : _format_time(jp.jam_mulai_baru),
        "jam_selesai_baru": _format_time(jp.jam_selesai_baru),
        "ruangan_baru"    : jp.ruangan_baru,
        "mode"            : jp.mode,
        "keterangan"      : jp.keterangan,
    }


def hapus_jadwal_pengganti(
    db           : Session,
    matakuliah_id: UUID,
    pertemuan_ke : int,
) -> tuple[bool, str]:
    jp = db.query(JadwalPengganti).filter(
        JadwalPengganti.matakuliah_id == matakuliah_id,
        JadwalPengganti.pertemuan_ke  == pertemuan_ke,
    ).first()

    if not jp:
        return False, "Jadwal pengganti tidak ditemukan"

    db.delete(jp)
    db.commit()
    return True, f"Jadwal pengganti pertemuan {pertemuan_ke} berhasil dihapus"


def get_jadwal_pengganti_list(db, matakuliah_id) -> list:
    jp_list = db.query(JadwalPengganti).filter(
        JadwalPengganti.matakuliah_id == matakuliah_id
    ).order_by(JadwalPengganti.pertemuan_ke).all()

    return [
        {
            "id"              : str(jp.id),
            "pertemuan_ke"    : jp.pertemuan_ke,
            "jam_mulai_baru"  : _format_time(jp.jam_mulai_baru),
            "jam_selesai_baru": _format_time(jp.jam_selesai_baru),
            "ruangan_baru"    : jp.ruangan_baru,
            "mode"            : getattr(jp, "mode", None),
            "keterangan"      : jp.keterangan,
            "created_at"      : jp.created_at.isoformat() if jp.created_at else None,
            "updated_at"      : jp.updated_at.isoformat() if jp.updated_at else None,
        }
        for jp in jp_list
    ]