"""
Push notification via Firebase Cloud Messaging (FCM).
Setup: pip install firebase-admin
Taruh credentials JSON di path yang dikonfigurasi di .env sebagai FCM_CREDENTIALS_PATH.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-init firebase agar server tetap bisa jalan walau FCM belum dikonfigurasi
_firebase_initialized = False


def _init_firebase():
    """Inisialisasi Firebase Admin SDK sekali saja (lazy)."""
    global _firebase_initialized
    if _firebase_initialized:
        return True
    try:
        import firebase_admin
        from firebase_admin import credentials
        import os

        cred_path = os.getenv("FCM_CREDENTIALS_PATH", "")
        if not cred_path or not os.path.exists(cred_path):
            logger.warning("FCM_CREDENTIALS_PATH tidak dikonfigurasi atau file tidak ada. "
                           "Push notification dinonaktifkan.")
            return False

        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)

        _firebase_initialized = True
        return True
    except ImportError:
        logger.warning("firebase-admin belum diinstall. Jalankan: pip install firebase-admin")
        return False
    except Exception as e:
        logger.error(f"Gagal inisialisasi Firebase: {e}")
        return False


def kirim_notifikasi(
    device_token : str,
    judul        : str,
    isi          : str,
    data         : Optional[dict] = None,
) -> bool:
    """
    Kirim push notification ke satu device via FCM.

    Args:
        device_token : FCM token perangkat penerima
        judul        : Judul notifikasi
        isi          : Isi/body notifikasi
        data         : Dict payload tambahan (opsional)

    Returns:
        True jika berhasil, False jika gagal
    """
    if not _init_firebase():
        return False

    try:
        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(
                title=judul,
                body =isi,
            ),
            data ={str(k): str(v) for k, v in (data or {}).items()},
            token=device_token,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound         ="default",
                    click_action  ="FLUTTER_NOTIFICATION_CLICK",
                    channel_id    ="presensi_channel",
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default"),
                ),
            ),
        )

        response = messaging.send(message)
        logger.info(f"Notifikasi terkirim: {response}")
        return True

    except Exception as e:
        logger.error(f"Gagal kirim notifikasi ke {device_token[:20]}...: {e}")
        return False


def kirim_notifikasi_presensi_berhasil(
    device_token    : str,
    nama_mahasiswa  : str,
    status          : str,   # 'hadir' | 'terlambat'
    nama_matakuliah : str,
    akurasi         : float,
    sesi_id         : str,
) -> bool:
    """Notifikasi konfirmasi presensi berhasil ke mahasiswa."""
    emoji = "✅" if status == "hadir" else "⏰"
    return kirim_notifikasi(
        device_token=device_token,
        judul=f"{emoji} Presensi {status.upper()}",
        isi  =f"Kamu telah presensi {nama_matakuliah} dengan akurasi {akurasi:.1f}%",
        data ={
            "type"      : "presensi_berhasil",
            "status"    : status,
            "sesi_id"   : sesi_id,
            "akurasi"   : str(akurasi),
        },
    )


def kirim_notifikasi_presensi_gagal(
    device_token    : str,
    alasan          : str,
) -> bool:
    """Notifikasi presensi gagal ke mahasiswa."""
    return kirim_notifikasi(
        device_token=device_token,
        judul="❌ Presensi Gagal",
        isi  =alasan,
        data ={"type": "presensi_gagal"},
    )


def kirim_notifikasi_sesi_dibuka(
    device_tokens   : list[str],
    nama_matakuliah : str,
    mode            : str,
    pertemuan_ke    : int,
) -> int:
    """
    Notifikasi ke semua mahasiswa bahwa sesi baru dibuka.
    Return jumlah notifikasi yang berhasil dikirim.
    """
    if not _init_firebase():
        return 0

    emoji  = "💻" if mode == "online" else "📍"
    judul  = f"{emoji} Sesi {nama_matakuliah} Dibuka"
    isi    = f"Pertemuan ke-{pertemuan_ke} ({mode}). Segera lakukan presensi!"
    sukses = 0

    for token in device_tokens:
        if kirim_notifikasi(token, judul, isi, {"type": "sesi_dibuka", "mode": mode}):
            sukses += 1

    logger.info(f"Notifikasi sesi dibuka: {sukses}/{len(device_tokens)} terkirim")
    return sukses


def kirim_notifikasi_kode_akan_expired(
    device_tokens   : list[str],
    nama_matakuliah : str,
    sisa_menit      : int,
) -> int:
    """Peringatan kode sesi akan expired (dipanggil dari scheduler/background task)."""
    if not _init_firebase():
        return 0

    sukses = 0
    for token in device_tokens:
        if kirim_notifikasi(
            token,
            judul=f"⚠️ Kode Sesi Hampir Expired",
            isi  =f"Kode {nama_matakuliah} akan expired dalam {sisa_menit} menit!",
            data ={"type": "kode_hampir_expired"},
        ):
            sukses += 1
    return sukses