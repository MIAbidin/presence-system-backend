# app/utils/geo_utils.py
# Update Fase E: radius geofencing tidak lagi hardcode 100m.
# Dibaca dari konfigurasi_sistem via superadmin_service.get_geofencing_radius(db).
import math
from typing import Optional
from sqlalchemy.orm import Session

# Fallback jika konfigurasi_sistem belum ada (sebelum Fase E)
RADIUS_DEFAULT = 100.0


def hitung_jarak_meter(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Hitung jarak dua titik GPS menggunakan rumus Haversine.
    Return: jarak dalam meter.
    """
    R = 6_371_000  # radius bumi dalam meter

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def dalam_radius(
    lat_mahasiswa : float,
    lng_mahasiswa : float,
    lat_kelas     : float,
    lng_kelas     : float,
    radius_meter  : float = RADIUS_DEFAULT,
) -> tuple[bool, float]:
    """
    Cek apakah mahasiswa berada dalam radius ruang kelas.
    Return: (dalam_radius, jarak_aktual_meter)

    Parameter radius_meter bersifat opsional — jika tidak diberikan,
    pakai RADIUS_DEFAULT (100m). Untuk radius dinamis dari DB,
    gunakan dalam_radius_db() di bawah.
    """
    jarak = hitung_jarak_meter(lat_mahasiswa, lng_mahasiswa, lat_kelas, lng_kelas)
    return jarak <= radius_meter, round(jarak, 2)


def dalam_radius_db(
    lat_mahasiswa : float,
    lng_mahasiswa : float,
    lat_kelas     : float,
    lng_kelas     : float,
    db            : Session,
) -> tuple[bool, float]:
    """
    Fase E: Cek radius menggunakan nilai dari konfigurasi_sistem.

    Versi ini dipakai di presensi_service.py sebagai pengganti
    dalam_radius() yang hardcode 100m.

    Fallback: jika konfigurasi_sistem belum ada → pakai RADIUS_DEFAULT (100m).
    """
    radius = _get_radius(db)
    return dalam_radius(lat_mahasiswa, lng_mahasiswa, lat_kelas, lng_kelas, radius)


def _get_radius(db: Optional[Session]) -> float:
    """
    Ambil radius geofencing dari konfigurasi_sistem.
    Fallback ke RADIUS_DEFAULT jika DB belum ada konfigurasi.
    """
    if db is None:
        return RADIUS_DEFAULT
    try:
        from app.services.superadmin_service import get_geofencing_radius
        return get_geofencing_radius(db)
    except Exception:
        return RADIUS_DEFAULT