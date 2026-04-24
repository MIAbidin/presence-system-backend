# app/utils/geo_utils.py
import math

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
    lat_mahasiswa: float, lng_mahasiswa: float,
    lat_kelas: float,     lng_kelas: float,
    radius_meter: float = 100.0   # toleransi 100m untuk dalam gedung (GPS drift)
) -> tuple[bool, float]:
    """
    Cek apakah mahasiswa berada dalam radius ruang kelas.
    Return: (dalam_radius, jarak_aktual_meter)
    """
    jarak = hitung_jarak_meter(lat_mahasiswa, lng_mahasiswa, lat_kelas, lng_kelas)
    return jarak <= radius_meter, round(jarak, 2)