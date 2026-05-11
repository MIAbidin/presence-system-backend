"""
app/services/dosen_service.py
══════════════════════════════
Fase 3 — Business logic untuk endpoint dosen:
- 3.1  : Beranda dosen (jadwal hari ini + status sesi)
- 3.2  : Detail matakuliah (mahasiswa asli vs tamu, jadwal pengganti)
- 3.3  : Toggle izin tamu per matakuliah
- 3.4  : Tambah / hapus mahasiswa tamu manual
- 3.5  : Simpan / list jadwal pengganti per pertemuan
"""

import logging
from datetime import datetime, timezone, timedelta, date
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.matakuliah import Matakuliah
from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
from app.models.sesi import SesiPresensi, SesiStatus
from app.models.presensi import Presensi, PresensiStatus
from app.models.jadwal_pengganti import JadwalPengganti

logger = logging.getLogger(__name__)

# ── Konstanta hari ─────────────────────────────────────────────
HARI_ORDER = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
WEEKDAY_TO_HARI = {
    0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis",
    4: "Jumat", 5: "Sabtu", 6: "Minggu",
}


def _format_time(t):
    """Helper format time → 'HH:MM' string. Sudah ada di dosen_service.py."""
    if t is None:
        return None
    if hasattr(t, "strftime"):
        return t.strftime("%H:%M")
    return str(t)[:5]

# ─── 3.1 — BERANDA DOSEN ─────────────────────────────────────

def get_beranda_dosen(db: Session, dosen: User) -> dict:
    """
    Satu endpoint untuk beranda dosen:
    - Jadwal hari ini (per matakuliah yang pernah dibuat sesinya / semua)
    - Status sesi tiap matakuliah: belum_mulai / aktif / selesai
    - Semua matakuliah yang diampu (untuk section "Semua Matakuliah")
    """
    hari_ini = WEEKDAY_TO_HARI.get(datetime.now().weekday(), "")
    today_start = datetime.combine(date.today(), datetime.min.time())

    # Ambil matakuliah yang pernah dibuat sesinya oleh dosen ini
    sesi_list_all = db.query(SesiPresensi).filter(
        SesiPresensi.dosen_id == dosen.id
    ).all()
    mk_ids_pernah = list({s.matakuliah_id for s in sesi_list_all})

    # Kalau belum pernah buat sesi sama sekali → tampilkan semua matakuliah
    if mk_ids_pernah:
        mk_list = db.query(Matakuliah).filter(Matakuliah.id.in_(mk_ids_pernah)).all()
    else:
        mk_list = db.query(Matakuliah).all()

    # Sesi aktif saat ini (dosen ini)
    sesi_aktif_map: dict = {}
    for s in db.query(SesiPresensi).filter(
        SesiPresensi.dosen_id == dosen.id,
        SesiPresensi.status   == SesiStatus.aktif,
    ).all():
        sesi_aktif_map[s.matakuliah_id] = s

    # Sesi terakhir hari ini (dosen ini)
    sesi_hari_ini_map: dict = {}
    for s in db.query(SesiPresensi).filter(
        SesiPresensi.dosen_id  == dosen.id,
        SesiPresensi.waktu_buka >= today_start,
    ).order_by(SesiPresensi.waktu_buka.desc()).all():
        if s.matakuliah_id not in sesi_hari_ini_map:
            sesi_hari_ini_map[s.matakuliah_id] = s

    # Jumlah mahasiswa terdaftar (bulk)
    jumlah_mhs_map: dict = {}
    for mk in mk_list:
        jumlah_mhs_map[mk.id] = db.query(MahasiswaMatakuliah).filter(
            MahasiswaMatakuliah.matakuliah_id == mk.id
        ).count()

    # Susun jadwal hari ini
    jadwal_hari_ini = []
    for mk in mk_list:
        if mk.hari != hari_ini:
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

        jadwal_hari_ini.append({
            "matakuliah_id"  : str(mk.id),
            "kode"           : mk.kode,
            "nama"           : mk.nama,
            "sks"            : mk.sks,
            "hari"           : mk.hari,
            "jam_mulai"      : _format_time(mk.jam_mulai),
            "jam_selesai"    : _format_time(mk.jam_selesai),
            "ruangan"        : mk.ruangan,
            "izin_tamu"      : mk.izin_tamu,
            "jumlah_mahasiswa": jumlah_mhs_map.get(mk.id, 0),
            "status_sesi"    : status_sesi,
            "sesi_id"        : str(sesi_ref.id)         if sesi_ref else None,
            "pertemuan_ke"   : sesi_ref.pertemuan_ke    if sesi_ref else None,
            "kode_sesi"      : sesi_ref.kode_sesi       if sesi_ref else None,
            "detik_tersisa"  : _hitung_detik(sesi_ref)  if sesi_ref else None,
        })

    jadwal_hari_ini.sort(key=lambda x: x["jam_mulai"] or "99:99")

    # Semua matakuliah (section bawah)
    semua_matakuliah = []
    for mk in mk_list:
        sesi_aktif = sesi_aktif_map.get(mk.id)
        semua_matakuliah.append({
            "matakuliah_id"  : str(mk.id),
            "kode"           : mk.kode,
            "nama"           : mk.nama,
            "sks"            : mk.sks,
            "hari"           : mk.hari,
            "jam_mulai"      : _format_time(mk.jam_mulai),
            "jam_selesai"    : _format_time(mk.jam_selesai),
            "ruangan"        : mk.ruangan,
            "izin_tamu"      : mk.izin_tamu,
            "jumlah_mahasiswa": jumlah_mhs_map.get(mk.id, 0),
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
    """
    Detail matakuliah untuk halaman detail di Flutter dosen:
    - Info matakuliah
    - Daftar mahasiswa (asli vs tamu, dipisahkan)
    - Jadwal pengganti yang pernah dibuat
    - Riwayat sesi ringkas
    """
    mk = db.query(Matakuliah).filter(Matakuliah.id == matakuliah_id).first()
    if not mk:
        return None

    # Daftar mahasiswa
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

    # Jadwal pengganti
    jadwal_pengganti_list = db.query(JadwalPengganti).filter(
        JadwalPengganti.matakuliah_id == matakuliah_id
    ).order_by(JadwalPengganti.pertemuan_ke).all()

    jadwal_pengganti = [
        {
            "id"             : str(jp.id),
            "pertemuan_ke"   : jp.pertemuan_ke,
            "jam_mulai_baru" : _format_time(jp.jam_mulai_baru),
            "jam_selesai_baru": _format_time(jp.jam_selesai_baru),
            "ruangan_baru"   : jp.ruangan_baru,
            "keterangan"     : jp.keterangan,
            "created_at"     : jp.created_at.isoformat() if jp.created_at else None,
        }
        for jp in jadwal_pengganti_list
    ]

    # Riwayat sesi ringkas (10 terakhir)
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
            f"Izin tamu {mk.nama} diaktifkan. "
            "Mahasiswa dari kelas lain dapat langsung presensi."
        ) if izin_tamu else (
            f"Izin tamu {mk.nama} dinonaktifkan. "
            "Hanya mahasiswa terdaftar yang dapat presensi."
        ),
    }


# ─── 3.4 — TAMBAH / HAPUS TAMU MANUAL ────────────────────────

def tambah_tamu_manual(
    db           : Session,
    matakuliah_id: UUID,
    nim          : str,
) -> tuple[bool, str, Optional[dict]]:
    """
    Dosen tambah mahasiswa tamu secara manual berdasarkan NIM.
    Return: (success, pesan, data_mahasiswa)
    """
    # Cari mahasiswa berdasarkan NIM
    mhs = db.query(User).filter(
        User.nim_nidn == nim.strip(),
        User.role     == UserRole.mahasiswa,
    ).first()

    if not mhs:
        return False, f"Mahasiswa dengan NIM {nim} tidak ditemukan", None

    # Cek sudah terdaftar
    existing = db.query(MahasiswaMatakuliah).filter(
        MahasiswaMatakuliah.mahasiswa_id  == mhs.id,
        MahasiswaMatakuliah.matakuliah_id == matakuliah_id,
    ).first()

    if existing:
        if existing.is_tamu:
            return False, f"{mhs.nama_lengkap} sudah terdaftar sebagai tamu", None
        else:
            return False, f"{mhs.nama_lengkap} sudah terdaftar sebagai mahasiswa asli kelas ini", None

    # Cari kelas asal mahasiswa (matakuliah pertama yang bukan tamu)
    row_asli = db.query(MahasiswaMatakuliah).filter(
        MahasiswaMatakuliah.mahasiswa_id  == mhs.id,
        MahasiswaMatakuliah.matakuliah_id != matakuliah_id,
        MahasiswaMatakuliah.is_tamu       == False,  # noqa: E712
    ).first()

    kelas_asal = None
    if row_asli and row_asli.matakuliah:
        kelas_asal = f"{row_asli.matakuliah.kode} - {row_asli.matakuliah.nama}"

    # Insert tamu
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
    """
    Hapus akses tamu mahasiswa dari matakuliah.
    Hanya bisa hapus kalau is_tamu = TRUE.
    Mahasiswa asli tidak bisa dihapus lewat endpoint ini.
    """
    row = db.query(MahasiswaMatakuliah).filter(
        MahasiswaMatakuliah.mahasiswa_id  == mahasiswa_id,
        MahasiswaMatakuliah.matakuliah_id == matakuliah_id,
    ).first()

    if not row:
        return False, "Mahasiswa tidak terdaftar di matakuliah ini"

    if not row.is_tamu:
        return False, "Tidak dapat menghapus mahasiswa asli lewat endpoint ini. Hubungi admin kampus."

    mhs_nama = row.mahasiswa.nama_lengkap if row.mahasiswa else "Mahasiswa"
    db.delete(row)
    db.commit()
    return True, f"{mhs_nama} berhasil dihapus dari daftar tamu"


# ─── 3.5 — JADWAL PENGGANTI ──────────────────────────────────

def simpan_jadwal_pengganti(
    db               ,
    dosen            ,
    matakuliah_id    ,
    pertemuan_ke  : int,
    jam_mulai_baru   ,
    jam_selesai_baru ,
    ruangan_baru     ,
    keterangan       ,
    mode             = None,   # ← BARU Fase B-1: 'offline' | 'online' | None
):
    """
    Simpan jadwal pengganti. Kalau sudah ada untuk pertemuan ini → UPDATE.
    Kalau belum ada → INSERT.
 
    Update Fase B-1:
    - Parameter mode ditambahkan (Optional[str], default None)
    - None = mode tidak berubah dari jadwal reguler kelas
    - 'offline' / 'online' = mode khusus untuk pertemuan ini
    - mode disimpan ke kolom jadwal_pengganti.mode di database
    - mode disertakan di dict response
    """
    from datetime import time as dtime
    from app.models.matakuliah import Matakuliah
    from app.models.jadwal_pengganti import JadwalPengganti
 
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
 
    # Validasi mode
    mode_valid = {None, "offline", "online"}
    if mode not in mode_valid:
        return False, f"Mode tidak valid: '{mode}'. Pilih: 'offline', 'online', atau kosongkan.", None
 
    # Cek sudah ada jadwal pengganti untuk pertemuan ini
    existing = db.query(JadwalPengganti).filter(
        JadwalPengganti.matakuliah_id == matakuliah_id,
        JadwalPengganti.pertemuan_ke  == pertemuan_ke,
    ).first()
 
    jam_mulai_obj   = parse_jam(jam_mulai_baru)
    jam_selesai_obj = parse_jam(jam_selesai_baru)
 
    if existing:
        # UPDATE: semua field termasuk mode
        existing.jam_mulai_baru   = jam_mulai_obj
        existing.jam_selesai_baru = jam_selesai_obj
        existing.ruangan_baru     = ruangan_baru
        existing.keterangan       = keterangan
        existing.dosen_id         = dosen.id
        existing.mode             = mode        # ← Fase B-1
        db.commit()
        db.refresh(existing)
        jp   = existing
        aksi = "diperbarui"
    else:
        # INSERT baru
        jp = JadwalPengganti(
            matakuliah_id    = matakuliah_id,
            dosen_id         = dosen.id,
            pertemuan_ke     = pertemuan_ke,
            jam_mulai_baru   = jam_mulai_obj,
            jam_selesai_baru = jam_selesai_obj,
            ruangan_baru     = ruangan_baru,
            keterangan       = keterangan,
            mode             = mode,            # ← Fase B-1
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
        "mode"            : jp.mode,            # ← Fase B-1
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
    """
    List semua jadwal pengganti untuk matakuliah ini.
 
    Update Fase B-1: sertakan field 'mode' di setiap item.
    """
    from app.models.jadwal_pengganti import JadwalPengganti
 
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
            "mode"            : jp.mode,        # ← Fase B-1
            "keterangan"      : jp.keterangan,
            "created_at"      : jp.created_at.isoformat() if jp.created_at else None,
            "updated_at"      : jp.updated_at.isoformat() if jp.updated_at else None,
        }
        for jp in jp_list
    ]