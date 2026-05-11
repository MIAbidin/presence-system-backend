"""
app/routers/sesi.py
════════════════════
Fase 3.6 — Perbaikan GET /sesi/{sesi_id}/peserta
Fase B-2  — GET /sesi/aktif-mahasiswa (response lengkap, auto-detect mode)
Fase B-3  — GET /sesi/aktif-tamu (list sesi untuk TamuSesiListScreen Flutter)
Fase B-6  — POST /sesi/buka: kirim notifikasi ke mahasiswa TANPA kode_sesi di payload FCM.
             Kode hanya dibagikan dosen manual via WhatsApp/Zoom.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.database.db import get_db
from app.models.user import User, UserRole
from app.models.sesi import SesiPresensi, SesiStatus, SesiMode
from app.models.presensi import Presensi, PresensiStatus
from app.schemas.sesi import BukaSesiRequest, SesiResponse, ExtendKodeRequest

# ── Fase B-2 ──────────────────────────────────────────────────
from app.schemas.sesi_aktif import SesiAktifWrapper
from app.services.sesi_aktif_service import get_sesi_aktif_mahasiswa_detail

# ── Fase B-3 ──────────────────────────────────────────────────
from app.schemas.sesi_tamu import SesiTamuListResponse
from app.services.sesi_tamu_service import get_sesi_aktif_tamu

from app.services import sesi_service
from app.routers.auth import get_current_user

router = APIRouter(prefix="/sesi", tags=["Manajemen Sesi"])


def require_dosen(current_user: User = Depends(get_current_user)):
    if current_user.role.value != "dosen":
        raise HTTPException(
            status_code=403,
            detail="Hanya dosen yang dapat mengelola sesi"
        )
    return current_user


# ─── POST /sesi/buka ──────────────────────────────────────────

@router.post("/buka", response_model=SesiResponse)
def buka_sesi(
    req  : BukaSesiRequest,
    dosen: User    = Depends(require_dosen),
    db   : Session = Depends(get_db)
):
    """
    Dosen membuka sesi presensi baru (offline atau online).

    Fase 2.1: mulai_dari_jam_jadwal=True → waktu_buka diambil dari jam_mulai
    matakuliah hari ini (bukan jam sekarang).

    Fase 2.3: batas_terlambat_menit=None → tidak ada batas terlambat,
    semua presensi selama sesi aktif = Hadir.

    Fase B-6: Setelah sesi berhasil dibuat, kirim push notification ke semua
    mahasiswa terdaftar di matakuliah ini. Payload FCM TIDAK menyertakan
    kode_sesi — kode hanya dibagikan dosen secara manual via WhatsApp/Zoom
    agar hanya mahasiswa yang aktif di sesi yang bisa presensi online.
    """
    try:
        sesi = sesi_service.buka_sesi(
            db                    = db,
            dosen_id              = dosen.id,
            matakuliah_id         = req.matakuliah_id,
            mode                  = req.mode,
            pertemuan_ke          = req.pertemuan_ke,
            batas_terlambat_menit = req.batas_terlambat_menit,
            durasi_menit          = req.durasi_menit,
            mulai_dari_jam_jadwal = req.mulai_dari_jam_jadwal,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ── Fase B-6: Kirim notifikasi ke mahasiswa (background, non-blocking) ──
    # Dilakukan setelah commit agar sesi sudah benar-benar tersimpan.
    # Error notifikasi tidak menggagalkan response buka sesi.
    _kirim_notifikasi_sesi_dibuka_background(db, sesi)

    detik = sesi_service.hitung_detik_tersisa(sesi)
    return SesiResponse(
        id             = sesi.id,
        mode           = sesi.mode.value,
        kode_sesi      = sesi.kode_sesi,
        kode_expire_at = sesi.kode_expire_at,
        pertemuan_ke   = sesi.pertemuan_ke,
        waktu_buka     = sesi.waktu_buka,
        status         = sesi.status.value,
        detik_tersisa  = detik,
        batas_terlambat_menit = (
            int(sesi.batas_terlambat.total_seconds() // 60)
            if sesi.batas_terlambat else None
        ),
    )


def _kirim_notifikasi_sesi_dibuka_background(
    db  : Session,
    sesi: SesiPresensi,
) -> None:
    """
    Fase B-6 — Kirim notifikasi ke semua mahasiswa terdaftar di matakuliah sesi.

    Dipisah ke fungsi sendiri agar:
    1. Mudah diuji secara terpisah
    2. Error tidak membatalkan response buka_sesi
    3. Logging terpusat

    Payload FCM yang dikirim ke mahasiswa:
    - type: 'sesi_dibuka'
    - mode: 'offline' | 'online'
    - pertemuan_ke: angka pertemuan
    - nama_matakuliah: nama MK
    TIDAK ada kode_sesi (Fase B-6).
    """
    try:
        from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
        from app.models.user import User as UserModel
        from app.models.matakuliah import Matakuliah
        from app.services.notification_service import kirim_notifikasi_sesi_dibuka

        # Ambil nama matakuliah
        mk = db.query(Matakuliah).filter(
            Matakuliah.id == sesi.matakuliah_id
        ).first()
        nama_mk = mk.nama if mk else "Matakuliah"

        # Ambil FCM token semua mahasiswa yang enrolled di MK ini
        rows = (
            db.query(MahasiswaMatakuliah)
            .filter(MahasiswaMatakuliah.matakuliah_id == sesi.matakuliah_id)
            .all()
        )
        mhs_ids = [r.mahasiswa_id for r in rows]
        if not mhs_ids:
            import logging
            logging.getLogger(__name__).debug(
                f"Tidak ada mahasiswa terdaftar di MK {sesi.matakuliah_id}, "
                "skip notifikasi."
            )
            return

        # Ambil FCM token yang tidak null
        users = (
            db.query(UserModel)
            .filter(
                UserModel.id.in_(mhs_ids),
                UserModel.fcm_token.isnot(None),
                UserModel.is_active == True,
            )
            .all()
        )
        device_tokens = [u.fcm_token for u in users if u.fcm_token]

        if not device_tokens:
            import logging
            logging.getLogger(__name__).debug(
                f"Tidak ada FCM token terdaftar untuk MK {sesi.matakuliah_id}."
            )
            return

        # Fase B-6: kirim_notifikasi_sesi_dibuka sudah tidak menyertakan kode_sesi
        terkirim = kirim_notifikasi_sesi_dibuka(
            device_tokens   = device_tokens,
            nama_matakuliah = nama_mk,
            mode            = sesi.mode.value,
            pertemuan_ke    = sesi.pertemuan_ke,
        )

        import logging
        logging.getLogger(__name__).info(
            f"[Fase B-6] Notifikasi sesi dibuka: {terkirim}/{len(device_tokens)} "
            f"terkirim ke mahasiswa MK {nama_mk} (pertemuan {sesi.pertemuan_ke}, "
            f"mode {sesi.mode.value}). Kode TIDAK disertakan di payload."
        )

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            f"[Fase B-6] Gagal kirim notifikasi sesi dibuka (non-fatal): {e}"
        )


# ─── POST /sesi/tutup ─────────────────────────────────────────

@router.post("/tutup")
def tutup_sesi(
    sesi_id: UUID,
    dosen  : User    = Depends(require_dosen),
    db     : Session = Depends(get_db)
):
    """Dosen menutup sesi manual. Kode online langsung hangus."""
    success, pesan = sesi_service.tutup_sesi(db, sesi_id, dosen.id)
    if not success:
        raise HTTPException(status_code=404, detail=pesan)
    return {"message": pesan}


# ─── POST /sesi/extend ────────────────────────────────────────

@router.post("/extend", response_model=SesiResponse)
def extend_kode(
    req  : ExtendKodeRequest,
    dosen: User    = Depends(require_dosen),
    db   : Session = Depends(get_db)
):
    """Dosen perpanjang durasi kode tanpa generate kode baru."""
    success, pesan, sesi = sesi_service.extend_kode(
        db, req.sesi_id, dosen.id, req.tambahan_menit
    )
    if not success:
        raise HTTPException(status_code=400, detail=pesan)

    detik = sesi_service.hitung_detik_tersisa(sesi)
    return SesiResponse(
        id=sesi.id, mode=sesi.mode.value, kode_sesi=sesi.kode_sesi,
        kode_expire_at=sesi.kode_expire_at, pertemuan_ke=sesi.pertemuan_ke,
        waktu_buka=sesi.waktu_buka, status=sesi.status.value,
        detik_tersisa=detik,
        batas_terlambat_menit=None,
    )


# ─── POST /sesi/regen-kode ────────────────────────────────────

@router.post("/regen-kode", response_model=SesiResponse)
def regen_kode(
    sesi_id     : UUID,
    durasi_menit: int = 30,
    dosen       : User    = Depends(require_dosen),
    db          : Session = Depends(get_db)
):
    """Dosen generate kode baru — kode lama LANGSUNG hangus."""
    success, pesan, sesi = sesi_service.regen_kode(db, sesi_id, dosen.id, durasi_menit)
    if not success:
        raise HTTPException(status_code=400, detail=pesan)

    detik = sesi_service.hitung_detik_tersisa(sesi)
    return SesiResponse(
        id=sesi.id, mode=sesi.mode.value, kode_sesi=sesi.kode_sesi,
        kode_expire_at=sesi.kode_expire_at, pertemuan_ke=sesi.pertemuan_ke,
        waktu_buka=sesi.waktu_buka, status=sesi.status.value,
        detik_tersisa=detik,
        batas_terlambat_menit=None,
    )


# ─── GET /sesi/riwayat-dosen ──────────────────────────────────

@router.get("/riwayat-dosen")
def get_riwayat_sesi_dosen(
    dosen: User    = Depends(require_dosen),
    db   : Session = Depends(get_db),
    limit: int     = 50,
    skip : int     = 0,
):
    """
    Ambil semua riwayat sesi yang pernah dibuat dosen yang sedang login.
    Diurutkan dari yang terbaru.
    """
    from collections import defaultdict

    sesi_list = (
        db.query(SesiPresensi)
        .filter(SesiPresensi.dosen_id == dosen.id)
        .order_by(SesiPresensi.waktu_buka.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    if not sesi_list:
        return {"total": 0, "sesi_list": []}

    sesi_ids = [s.id for s in sesi_list]
    all_presensi = (
        db.query(Presensi)
        .filter(Presensi.sesi_id.in_(sesi_ids))
        .all()
    )

    presensi_by_sesi: dict = defaultdict(list)
    for p in all_presensi:
        presensi_by_sesi[p.sesi_id].append(p)

    result = []
    for sesi in sesi_list:
        mk            = sesi.matakuliah
        presensi_sesi = presensi_by_sesi.get(sesi.id, [])

        total     = len(presensi_sesi)
        hadir     = sum(1 for p in presensi_sesi if p.status == PresensiStatus.hadir)
        terlambat = sum(1 for p in presensi_sesi if p.status == PresensiStatus.terlambat)
        absen     = sum(1 for p in presensi_sesi if p.status == PresensiStatus.absen)
        izin      = sum(1 for p in presensi_sesi if p.status == PresensiStatus.izin)
        sakit     = sum(1 for p in presensi_sesi if p.status == PresensiStatus.sakit)
        efektif   = hadir + terlambat
        persentase = round(efektif / total * 100, 1) if total else 0.0

        result.append({
            "sesi_id"     : str(sesi.id),
            "mode"        : sesi.mode.value,
            "pertemuan_ke": sesi.pertemuan_ke,
            "matakuliah"  : mk.nama if mk else "-",
            "kode_mk"     : mk.kode if mk else "-",
            "status"      : sesi.status.value,
            "waktu_buka"  : sesi.waktu_buka.isoformat()  if sesi.waktu_buka  else None,
            "waktu_tutup" : sesi.waktu_tutup.isoformat() if sesi.waktu_tutup else None,
            "total_mhs"   : total,
            "hadir"       : hadir,
            "terlambat"   : terlambat,
            "absen"       : absen,
            "izin"        : izin,
            "sakit"       : sakit,
            "persentase"  : persentase,
        })

    return {
        "total"    : len(result),
        "sesi_list": result,
    }


# ─── GET /sesi/cek-kode ───────────────────────────────────────

@router.get("/cek-kode")
def cek_kode_sesi(
    kode        : str,
    current_user: User    = Depends(get_current_user),
    db          : Session = Depends(get_db),
):
    """
    Mahasiswa cek apakah kode sesi valid sebelum scan wajah.
    Endpoint: GET /sesi/cek-kode?kode=A7X3K2
    """
    valid, pesan, sesi = sesi_service.validasi_kode(db, kode, current_user.id)
    if not valid:
        raise HTTPException(status_code=400, detail=pesan)

    return {
        "ada_sesi": True,
        "pesan"   : "Kode valid",
        "sesi": {
            "id"           : str(sesi.id),
            "mode"         : sesi.mode.value,
            "matakuliah_id": str(sesi.matakuliah_id),
            "matakuliah"   : sesi.matakuliah.nama if sesi.matakuliah else "-",
            "pertemuan_ke" : sesi.pertemuan_ke,
            "waktu_buka"   : sesi.waktu_buka.isoformat() if sesi.waktu_buka else None,
            "detik_tersisa": sesi_service.hitung_detik_tersisa(sesi),
        }
    }


# ─── GET /sesi/aktif-tamu ─────────────────────────────────────
# FASE B-3: Route statis — HARUS sebelum GET /sesi/aktif dan GET /sesi/aktif-mahasiswa
# agar tidak ditangkap sebagai path parameter {sesi_id}

@router.get("/aktif-tamu", response_model=SesiTamuListResponse)
def get_sesi_aktif_untuk_tamu(
    current_user: User    = Depends(get_current_user),
    db          : Session = Depends(get_db),
):
    """
    Fase B-3 — List sesi aktif yang bisa diikuti mahasiswa sebagai tamu.

    Dipakai TamuSesiListScreen Flutter v2.1.0.
    Dipanggil saat mahasiswa tap 'Ikut sebagai Tamu' di ScanScreen
    (ketika tidak ada jadwal aktif untuk mahasiswa tersebut).

    Sesi muncul di list jika memenuhi SALAH SATU syarat:
    - Dosen sudah daftarkan mahasiswa ini secara manual (is_tamu=True)
    - Kelas memiliki izin_tamu=True (siapapun boleh masuk)

    Sesi TIDAK muncul jika:
    - Mahasiswa sudah enrolled sebagai mahasiswa ASLI di MK tersebut
      → gunakan alur presensi normal via GET /sesi/aktif-mahasiswa
    - Mahasiswa sudah punya record presensi di sesi ini

    Selalu return HTTP 200. Dosen/admin mendapat list kosong.

    izin_tamu_source per item:
    - 'manual' → didaftarkan dosen (tampil lebih atas)
    - 'auto'   → kelas buka izin tamu
    """
    # Dosen/admin tidak menggunakan alur tamu
    if current_user.role != UserRole.mahasiswa:
        return SesiTamuListResponse(sesi_list=[], total=0, pesan=None)

    return get_sesi_aktif_tamu(db, current_user.id)


# ─── GET /sesi/aktif ──────────────────────────────────────────
# Endpoint lama — tetap ada untuk kompatibilitas

@router.get("/aktif")
def cek_sesi_aktif(
    matakuliah_id: UUID,
    db           : Session = Depends(get_db),
    _            : User    = Depends(get_current_user)
):
    """Mahasiswa cek apakah ada sesi aktif untuk matakuliahnya."""
    sesi = sesi_service.get_sesi_aktif(db, matakuliah_id)
    if not sesi:
        return {"ada_sesi": False, "sesi": None}

    return {
        "ada_sesi": True,
        "sesi": {
            "id"          : str(sesi.id),
            "mode"        : sesi.mode.value,
            "waktu_buka"  : sesi.waktu_buka.isoformat() if sesi.waktu_buka else None,
            "detik_tersisa": sesi_service.hitung_detik_tersisa(sesi),
        }
    }


# ─── GET /sesi/aktif-mahasiswa ────────────────────────────────
# FASE B-2: Endpoint baru — response lengkap untuk auto-detect mode Flutter

@router.get("/aktif-mahasiswa", response_model=SesiAktifWrapper)
def get_sesi_aktif_mahasiswa(
    current_user: User    = Depends(get_current_user),
    db          : Session = Depends(get_db),
):
    """
    Fase B-2 — Ambil sesi aktif yang cocok dengan jadwal mahasiswa saat ini.

    Berbeda dengan GET /sesi/aktif yang perlu matakuliah_id sebagai parameter,
    endpoint ini otomatis mencari sesi berdasarkan:
    - Jadwal MK yang diikuti mahasiswa (via mahasiswa_matakuliah)
    - Hari ini (WIB) dan window jam ±30 menit dari jam_mulai kelas
    - Belum dipresensi oleh mahasiswa ini

    Dipakai Flutter SesiDetectService untuk auto-detect mode presensi.
    Tidak ada lagi pilihan mode manual — sistem yang menentukan.

    Flutter logic berdasarkan response:
    - ada_sesi=false             → tampil tombol 'Ikut sebagai Tamu'
    - ada_sesi=true, mode=online → navigate ke KodeSesiScreen (auto)
    - ada_sesi=true, mode=offline→ langsung buka kamera + validasi GPS

    Selalu return HTTP 200, tidak pernah 404.
    """
    # Dosen/admin yang hit endpoint ini → return false (bukan error)
    if current_user.role != UserRole.mahasiswa:
        return SesiAktifWrapper(ada_sesi=False, sesi=None)

    return get_sesi_aktif_mahasiswa_detail(db, current_user.id)


# ─── GET /sesi/aktif-dosen ────────────────────────────────────

@router.get("/aktif-dosen")
def get_sesi_aktif_dosen(
    dosen: User    = Depends(require_dosen),
    db   : Session = Depends(get_db)
):
    """Ambil semua sesi aktif yang dibuat oleh dosen yang sedang login."""
    from app.models.matakuliah import Matakuliah
    sesi_list = db.query(SesiPresensi).filter(
        SesiPresensi.dosen_id == dosen.id,
        SesiPresensi.status   == SesiStatus.aktif
    ).order_by(SesiPresensi.waktu_buka.desc()).all()

    result = []
    for sesi in sesi_list:
        mk = db.query(Matakuliah).filter(Matakuliah.id == sesi.matakuliah_id).first()
        result.append({
            "id"          : str(sesi.id),
            "mode"        : sesi.mode.value,
            "kode_sesi"   : sesi.kode_sesi,
            "pertemuan_ke": sesi.pertemuan_ke,
            "waktu_buka"  : sesi.waktu_buka.isoformat(),
            "matakuliah"  : mk.nama if mk else "-",
            "detik_tersisa": sesi_service.hitung_detik_tersisa(sesi),
        })

    return {"sesi_list": result}


# ─── GET /sesi/{sesi_id}/peserta ─────────────────────────────
# FIX 3.6: Query bulk, return is_tamu + kelas_asal yang benar

@router.get("/{sesi_id}/peserta")
def get_peserta(
    sesi_id: UUID,
    dosen  : User    = Depends(require_dosen),
    db     : Session = Depends(get_db)
):
    """
    Dosen lihat daftar hadir real-time. Dipolling setiap 5 detik.

    Fase 3.6 Fix:
    - Query bulk untuk mahasiswa_matakuliah (tidak loop N+1)
    - Return is_tamu dan kelas_asal yang benar untuk label tamu di Flutter
    - Return nama dan NIM yang selalu terisi (join ke users)
    """
    sesi = db.query(SesiPresensi).filter(SesiPresensi.id == sesi_id).first()
    if not sesi:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan")

    presensi_list = db.query(Presensi).filter(Presensi.sesi_id == sesi_id).all()

    from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
    mk_rows = db.query(MahasiswaMatakuliah).filter(
        MahasiswaMatakuliah.matakuliah_id == sesi.matakuliah_id
    ).all()
    mk_row_map = {str(row.mahasiswa_id): row for row in mk_rows}

    hadir     = sum(1 for p in presensi_list if p.status == PresensiStatus.hadir)
    terlambat = sum(1 for p in presensi_list if p.status == PresensiStatus.terlambat)
    absen     = sum(1 for p in presensi_list if p.status == PresensiStatus.absen)

    detail = []
    for p in presensi_list:
        mhs     = p.mahasiswa
        mk_row  = mk_row_map.get(str(p.mahasiswa_id))

        detail.append({
            "presensi_id"   : str(p.id),
            "mahasiswa_id"  : str(p.mahasiswa_id),
            "nim"           : mhs.nim_nidn      if mhs else "-",
            "nama"          : mhs.nama_lengkap  if mhs else "-",
            "status"        : p.status.value,
            "waktu_presensi": p.waktu_presensi.isoformat() if p.waktu_presensi else None,
            "akurasi_wajah" : p.akurasi_wajah,
            "mode_kelas"    : p.mode_kelas.value,
            "catatan"       : p.catatan,
            "is_tamu"       : mk_row.is_tamu    if mk_row else False,
            "kelas_asal"    : mk_row.kelas_asal if mk_row else None,
        })

    status_order = {"hadir": 0, "terlambat": 1, "izin": 2, "sakit": 3, "absen": 4}
    detail.sort(key=lambda x: (
        status_order.get(x["status"], 99),
        -(int(x["waktu_presensi"].replace("T", "").replace(":", "").replace("-", "")[:14])
          if x["waktu_presensi"] else 0)
    ))

    return {
        "sesi_id"   : str(sesi_id),
        "mode"      : sesi.mode.value,
        "pertemuan_ke": sesi.pertemuan_ke,
        "matakuliah": sesi.matakuliah.nama if sesi.matakuliah else "-",
        "ringkasan" : {
            "hadir"    : hadir,
            "terlambat": terlambat,
            "absen"    : absen,
            "total"    : len(presensi_list),
        },
        "detail": detail,
    }