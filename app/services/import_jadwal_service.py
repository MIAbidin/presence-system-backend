# app/services/import_jadwal_service.py
"""
Fase C — Business logic untuk import jadwal dari hasil parsing PDF/Excel.

Alur:
1. Terima list[dict] dari jadwal_parser.py
2. Per baris:
   a. Cari/buat Matakuliah berdasarkan kode_mk
   b. Cari Dosen berdasarkan nama (ILIKE fuzzy match) → warning jika tidak ketemu
   c. Cari/buat Ruangan berdasarkan kode_ruangan
   d. Upsert KelasMatakuliah (update jika sudah ada, insert jika belum)
3. Return summary: total, berhasil, diupdate, warning, error
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.models.matakuliah import Matakuliah
from app.models.user import User, UserRole
from app.models.ruangan import Ruangan
from app.models.kelas_matakuliah import KelasMatakuliah
from app.utils.slot_utils import SLOT_MAPPING

logger = logging.getLogger(__name__)


# ── Type definitions ──────────────────────────────────────────

class ImportJadwalRow:
    """Satu baris hasil parse yang siap diimport."""
    hari         : Optional[str]
    kode_ruangan : Optional[str]
    slot_mulai   : Optional[int]
    slot_selesai : Optional[int]
    kode_mk      : Optional[str]
    nama_mk      : Optional[str]
    dosen        : Optional[str]
    kode_kelas   : Optional[str]
    kode_akses   : Optional[str]


# ── Status codes ──────────────────────────────────────────────
STATUS_BARU      = "baru"       # akan di-INSERT
STATUS_UPDATE    = "diupdate"   # akan di-UPDATE (kelas sudah ada)
STATUS_WARNING   = "warning"    # dosen tidak match, kelas tetap dibuat
STATUS_ERROR     = "error"      # tidak bisa diproses

# ─────────────────────────────────────────────────────────────
# PREVIEW (tanpa insert ke DB)
# ─────────────────────────────────────────────────────────────

def preview_import_jadwal(db: Session, parsed_rows: list[dict]) -> dict:
    """
    Preview hasil parsing TANPA insert ke DB.
    Return: { total, preview (max 50 baris), counts }
    """
    if not parsed_rows:
        return {
            "total"  : 0,
            "preview": [],
            "counts" : {"baru": 0, "diupdate": 0, "warning": 0, "error": 0},
            "pesan"  : "Tidak ada data yang dapat di-parse dari file",
        }

    preview = []
    counts  = {"baru": 0, "diupdate": 0, "warning": 0, "error": 0}

    for row in parsed_rows:
        result = _evaluate_row(db, row)
        counts[result["status"]] = counts.get(result["status"], 0) + 1
        if len(preview) < 50:
            preview.append(result)

    return {
        "total"  : len(parsed_rows),
        "preview": preview,
        "counts" : counts,
        "pesan"  : _build_summary_pesan(len(parsed_rows), counts),
    }


# ─────────────────────────────────────────────────────────────
# IMPORT SESUNGGUHNYA (insert/update ke DB)
# ─────────────────────────────────────────────────────────────

def import_jadwal(db: Session, parsed_rows: list[dict]) -> dict:
    """
    Import jadwal ke DB.
    Return: { total, berhasil, diupdate, warning, error, errors, preview }
    """
    if not parsed_rows:
        return {
            "total"   : 0,
            "berhasil": 0,
            "diupdate": 0,
            "warning" : 0,
            "error"   : 0,
            "errors"  : [],
            "preview" : [],
            "pesan"   : "Tidak ada data yang dapat diimport",
        }

    result_summary = {
        "total"   : len(parsed_rows),
        "berhasil": 0,
        "diupdate": 0,
        "warning" : 0,
        "error"   : 0,
        "errors"  : [],
        "preview" : [],
    }

    for idx, row in enumerate(parsed_rows):
        try:
            status, detail = _import_one_row(db, row)

            if status in (STATUS_BARU, STATUS_WARNING):
                result_summary["berhasil"] += 1
                if status == STATUS_WARNING:
                    result_summary["warning"] += 1
                if len(result_summary["preview"]) < 10:
                    result_summary["preview"].append({**detail, "status": status})

            elif status == STATUS_UPDATE:
                result_summary["diupdate"] += 1
                if len(result_summary["preview"]) < 10:
                    result_summary["preview"].append({**detail, "status": status})

            elif status == STATUS_ERROR:
                result_summary["error"] += 1
                result_summary["errors"].append({
                    "baris" : idx + 1,
                    "kode_mk": row.get("kode_mk", "-"),
                    "kelas" : row.get("kode_kelas", "-"),
                    "pesan" : detail.get("pesan", "Error tidak diketahui"),
                })

        except Exception as e:
            logger.error(f"Error import row {idx+1}: {e}", exc_info=True)
            result_summary["error"] += 1
            result_summary["errors"].append({
                "baris" : idx + 1,
                "kode_mk": row.get("kode_mk", "-"),
                "kelas" : row.get("kode_kelas", "-"),
                "pesan" : str(e),
            })

    # Commit semua sekaligus jika ada yang berhasil
    if result_summary["berhasil"] + result_summary["diupdate"] > 0:
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Commit error: {e}", exc_info=True)
            raise ValueError(f"Gagal menyimpan data ke database: {str(e)}")

    result_summary["pesan"] = _build_import_pesan(result_summary)
    return result_summary


# ─────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────

def _evaluate_row(db: Session, row: dict) -> dict:
    """
    Evaluasi satu baris tanpa insert — return status dan info detail.
    Dipakai saat preview.
    """
    kode_mk    = row.get("kode_mk")
    nama_mk    = row.get("nama_mk")
    kode_kelas = row.get("kode_kelas")
    hari       = row.get("hari")
    slot_mulai = row.get("slot_mulai")
    slot_selesai = row.get("slot_selesai")
    dosen_nama = row.get("dosen")
    kode_ruangan = row.get("kode_ruangan")
    kode_akses = row.get("kode_akses")

    # Validasi minimal
    if not kode_mk:
        return {
            "status"      : STATUS_ERROR,
            "kode_mk"     : "-",
            "nama_mk"     : nama_mk or "-",
            "kode_kelas"  : kode_kelas or "-",
            "hari"        : hari,
            "slot"        : _fmt_slot(slot_mulai, slot_selesai),
            "jam"         : _fmt_jam(slot_mulai, slot_selesai),
            "kode_ruangan": kode_ruangan or "-",
            "dosen"       : dosen_nama or "-",
            "kode_akses"  : kode_akses,
            "pesan"       : "Kode MK tidak ditemukan dalam baris ini",
        }

    if not kode_kelas:
        return {
            "status"      : STATUS_ERROR,
            "kode_mk"     : kode_mk,
            "nama_mk"     : nama_mk or "-",
            "kode_kelas"  : "-",
            "hari"        : hari,
            "slot"        : _fmt_slot(slot_mulai, slot_selesai),
            "jam"         : _fmt_jam(slot_mulai, slot_selesai),
            "kode_ruangan": kode_ruangan or "-",
            "dosen"       : dosen_nama or "-",
            "kode_akses"  : kode_akses,
            "pesan"       : "Kode kelas (A/B/C/X) tidak terdeteksi",
        }

    # Cek apakah sudah ada
    mk = db.query(Matakuliah).filter(
        func.upper(Matakuliah.kode) == kode_mk.upper()
    ).first()

    kelas_exists = False
    if mk:
        kelas_exists = db.query(KelasMatakuliah).filter(
            KelasMatakuliah.matakuliah_id == mk.id,
            KelasMatakuliah.kode_kelas    == kode_kelas.upper(),
        ).first() is not None

    # Cek dosen match
    dosen_obj   = _find_dosen(db, dosen_nama) if dosen_nama else None
    dosen_status = "match" if dosen_obj else ("not_found" if dosen_nama else "empty")

    status = STATUS_UPDATE if kelas_exists else STATUS_BARU
    if dosen_status == "not_found":
        status = STATUS_WARNING

    return {
        "status"      : status,
        "kode_mk"     : kode_mk,
        "nama_mk"     : nama_mk or (mk.nama if mk else "-"),
        "kode_kelas"  : kode_kelas,
        "hari"        : hari,
        "slot"        : _fmt_slot(slot_mulai, slot_selesai),
        "jam"         : _fmt_jam(slot_mulai, slot_selesai),
        "kode_ruangan": kode_ruangan or "-",
        "dosen"       : dosen_nama or "-",
        "dosen_matched": dosen_obj.nama_lengkap if dosen_obj else None,
        "kode_akses"  : kode_akses,
        "pesan"       : _build_row_pesan(status, dosen_status, kode_mk, kode_kelas),
    }


def _import_one_row(db: Session, row: dict) -> tuple[str, dict]:
    """
    Import satu baris ke DB.
    Return: (status, detail_dict)
    """
    kode_mk      = (row.get("kode_mk") or "").strip().upper()
    nama_mk      = (row.get("nama_mk") or "").strip()
    kode_kelas   = (row.get("kode_kelas") or "").strip().upper()
    hari         = row.get("hari")
    slot_mulai   = row.get("slot_mulai")
    slot_selesai = row.get("slot_selesai")
    dosen_nama   = (row.get("dosen") or "").strip() or None
    kode_ruangan = (row.get("kode_ruangan") or "").strip() or None
    kode_akses   = (row.get("kode_akses") or "").strip() or None

    # Validasi minimal
    if not kode_mk:
        return STATUS_ERROR, {"pesan": "Kode MK tidak ditemukan"}
    if not kode_kelas:
        return STATUS_ERROR, {"pesan": "Kode kelas tidak terdeteksi"}

    # ── 1. Cari atau buat Matakuliah ──────────────────────────
    mk = db.query(Matakuliah).filter(
        func.upper(Matakuliah.kode) == kode_mk
    ).first()

    if not mk:
        # Buat matakuliah baru dari data parsing
        mk = Matakuliah(
            kode      = kode_mk,
            nama      = nama_mk or kode_mk,
            sks       = 3,   # default, bisa diupdate manual nanti
            hari      = hari,
            izin_tamu = False,
        )
        db.add(mk)
        db.flush()  # dapat ID
        logger.info(f"MK baru dibuat: {kode_mk} — {mk.nama}")

    # ── 2. Cari Dosen ─────────────────────────────────────────
    dosen_obj   = _find_dosen(db, dosen_nama) if dosen_nama else None
    dosen_id    = dosen_obj.id if dosen_obj else None
    is_warning  = (dosen_nama is not None and dosen_obj is None)

    # ── 3. Cari atau buat Ruangan ─────────────────────────────
    ruangan_id = None
    if kode_ruangan:
        ruangan = db.query(Ruangan).filter(
            func.upper(Ruangan.kode) == kode_ruangan.upper()
        ).first()
        if not ruangan:
            # Buat ruangan baru dengan kode tersebut
            ruangan = Ruangan(
                kode      = kode_ruangan.upper(),
                nama      = kode_ruangan,   # nama sementara = kode
                is_active = True,
            )
            db.add(ruangan)
            db.flush()
            logger.info(f"Ruangan baru dibuat otomatis: {kode_ruangan}")
        ruangan_id = ruangan.id

    # ── 4. Upsert KelasMatakuliah ─────────────────────────────
    existing = db.query(KelasMatakuliah).filter(
        KelasMatakuliah.matakuliah_id == mk.id,
        KelasMatakuliah.kode_kelas    == kode_kelas,
    ).first()

    status = STATUS_UPDATE if existing else STATUS_BARU

    if existing:
        # UPDATE: hanya update field yang ada di baris ini
        if dosen_id is not None:
            existing.dosen_id = dosen_id
        if ruangan_id is not None:
            existing.ruangan_id = ruangan_id
        if hari is not None:
            existing.hari = hari
        if slot_mulai is not None:
            existing.slot_mulai = slot_mulai
        if slot_selesai is not None:
            existing.slot_selesai = slot_selesai
        if kode_akses is not None:
            existing.kode_akses = kode_akses
    else:
        # INSERT baru
        kelas = KelasMatakuliah(
            matakuliah_id = mk.id,
            kode_kelas    = kode_kelas,
            dosen_id      = dosen_id,
            ruangan_id    = ruangan_id,
            hari          = hari,
            slot_mulai    = slot_mulai,
            slot_selesai  = slot_selesai,
            kode_akses    = kode_akses,
            izin_tamu     = False,
            is_active     = True,
        )
        db.add(kelas)

    db.flush()

    detail = {
        "kode_mk"   : kode_mk,
        "nama_mk"   : mk.nama,
        "kode_kelas": kode_kelas,
        "hari"      : hari,
        "slot"      : _fmt_slot(slot_mulai, slot_selesai),
        "jam"       : _fmt_jam(slot_mulai, slot_selesai),
        "dosen"     : dosen_obj.nama_lengkap if dosen_obj else dosen_nama,
        "ruangan"   : kode_ruangan,
        "kode_akses": kode_akses,
        "pesan"     : _build_row_pesan(
            STATUS_WARNING if is_warning else status,
            "not_found" if is_warning else "match",
            kode_mk, kode_kelas
        ),
    }

    final_status = STATUS_WARNING if is_warning else status
    return final_status, detail


# ─────────────────────────────────────────────────────────────
# LOOKUP HELPERS
# ─────────────────────────────────────────────────────────────

def _find_dosen(db: Session, nama: Optional[str]) -> Optional[User]:
    """
    Cari dosen berdasarkan nama dengan fuzzy match (ILIKE).
    Strategi:
    1. Exact match (case-insensitive)
    2. Contains match
    3. Partial match tiap kata
    """
    if not nama:
        return None

    nama_clean = nama.strip()

    # Exact match
    dosen = db.query(User).filter(
        User.role == UserRole.dosen,
        func.lower(User.nama_lengkap) == nama_clean.lower(),
    ).first()
    if dosen:
        return dosen

    # Contains match
    dosen = db.query(User).filter(
        User.role == UserRole.dosen,
        func.lower(User.nama_lengkap).like(f"%{nama_clean.lower()}%"),
    ).first()
    if dosen:
        return dosen

    # Partial match: cari berdasarkan kata pertama dan terakhir
    words = [w for w in nama_clean.split() if len(w) > 2]
    if words:
        # Coba match salah satu kata utama
        for word in words:
            if len(word) > 3:  # hindari matching kata pendek seperti "Dr." atau "M.T."
                dosen = db.query(User).filter(
                    User.role == UserRole.dosen,
                    func.lower(User.nama_lengkap).like(f"%{word.lower()}%"),
                ).first()
                if dosen:
                    return dosen

    return None


# ─────────────────────────────────────────────────────────────
# FORMATTING HELPERS
# ─────────────────────────────────────────────────────────────

def _fmt_slot(slot_mulai: Optional[int], slot_selesai: Optional[int]) -> Optional[str]:
    """Format slot ke string: '1-3', '7-8', dst."""
    if slot_mulai is None:
        return None
    if slot_selesai is None or slot_selesai == slot_mulai:
        return str(slot_mulai)
    return f"{slot_mulai}-{slot_selesai}"


def _fmt_jam(slot_mulai: Optional[int], slot_selesai: Optional[int]) -> Optional[str]:
    """Format slot ke jam: '07:00 – 09:30', dst."""
    if not slot_mulai or not slot_selesai:
        return None
    try:
        jam_m = SLOT_MAPPING.get(slot_mulai)
        jam_s = SLOT_MAPPING.get(slot_selesai)
        if jam_m and jam_s:
            return f"{jam_m[0].strftime('%H:%M')} – {jam_s[1].strftime('%H:%M')}"
    except Exception:
        pass
    return None


def _build_row_pesan(
    status       : str,
    dosen_status : str,
    kode_mk      : str,
    kode_kelas   : str,
) -> str:
    if status == STATUS_ERROR:
        return "Tidak dapat diproses"
    if status == STATUS_UPDATE:
        return f"{kode_mk} Kelas {kode_kelas} akan diupdate"
    if dosen_status == "not_found":
        return f"{kode_mk} Kelas {kode_kelas} — dosen tidak ditemukan di sistem (akan dibuat tanpa dosen)"
    return f"{kode_mk} Kelas {kode_kelas} akan dibuat baru"


def _build_summary_pesan(total: int, counts: dict) -> str:
    parts = [f"Ditemukan {total} baris"]
    if counts.get("baru", 0) > 0:
        parts.append(f"{counts['baru']} baru")
    if counts.get("diupdate", 0) > 0:
        parts.append(f"{counts['diupdate']} akan diupdate")
    if counts.get("warning", 0) > 0:
        parts.append(f"{counts['warning']} warning (dosen tidak match)")
    if counts.get("error", 0) > 0:
        parts.append(f"{counts['error']} error")
    return " · ".join(parts)


def _build_import_pesan(r: dict) -> str:
    sukses = r["berhasil"] + r["diupdate"]
    parts = [f"{sukses} kelas berhasil diimport/diupdate"]
    if r["warning"] > 0:
        parts.append(f"{r['warning']} tanpa dosen (cek warning)")
    if r["error"] > 0:
        parts.append(f"{r['error']} baris gagal")
    return " · ".join(parts)