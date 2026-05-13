"""
new_seed1.py — Seed Data Lengkap & Realistis (Backend v3.5.0 — Fase A–E + B-1 selesai)
========================================================================================
Jalankan: python new_seed1.py

Mencakup semua model terbaru:
  Fase 0  : 1 Super Admin + 3 Admin Fakultas
  Fase 1  : 10 Dosen (berbagai prodi)
  Fase 2  : 80 Mahasiswa (berbagai prodi & angkatan)
  Fase A  : 25 Ruangan Kuliah (kuliah, lab, seminar) + koordinat GPS
  Fase D  : 8 Program Studi terstruktur
  Fase B  : 12 Matakuliah + Kelas per MK (A, B, C) + enrollment per kelas
  Fase B-1: Jadwal Pengganti dengan field mode (offline/online/null)
  Fase 4  : 50+ Sesi Presensi (offline & online, selesai & aktif)
  Fase 5  : Data Presensi lengkap (hadir, terlambat, absen, izin, sakit)
  Fase 6  : KodeUsage untuk sesi online
  Fase E  : Konfigurasi Sistem (5 default config) + Super Admin role
  Lain    : FaceEmbedding placeholder + AuditLog contoh + JadwalPengganti

Password semua akun: Password123!

Universitas: Universitas Hasanuddin (UNHAS) Makassar
Kampus: Tamalanrea, Makassar, Sulawesi Selatan
Koordinat pusat kampus: -5.1302, 119.4894
"""

import uuid
import random
import secrets
import string
from datetime import datetime, timedelta, time, timezone, date
from zoneinfo import ZoneInfo

from app.database.db import SessionLocal
from app.models.user import User, UserRole
from app.models.matakuliah import Matakuliah
from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
from app.models.sesi import SesiPresensi, SesiMode, SesiStatus
from app.models.kode_usage import KodeUsage
from app.models.presensi import Presensi, PresensiStatus, ModeKelas
from app.models.jadwal_pengganti import JadwalPengganti
from app.models.ruangan import Ruangan
from app.models.kelas_matakuliah import KelasMatakuliah
from app.models.program_studi import ProgramStudi
from app.models.konfigurasi_sistem import KonfigurasiSistem
from app.models.audit_log import AuditLog
from app.services.auth_service import hash_password

WIB = ZoneInfo("Asia/Jakarta")

# ─── HELPER ───────────────────────────────────────────────────

def utc_from_wib(y, mo, d, h, mi, s=0):
    wib_dt = datetime(y, mo, d, h, mi, s, tzinfo=WIB)
    return wib_dt.astimezone(timezone.utc).replace(tzinfo=None)


def rand_akurasi():
    """Akurasi wajah antara 76–99%."""
    return round(random.uniform(76.0, 99.2), 2)


def rand_kode():
    """Generate kode sesi 6 karakter alphanum (tanpa karakter ambigu)."""
    chars = (string.ascii_uppercase + string.digits).translate(
        str.maketrans("", "", "OI0L1")
    )
    return "".join(secrets.choice(chars) for _ in range(6))


def pw():
    return hash_password("Password123!")


# ─── Slot mapping (sama dengan slot_utils.py) ─────────────────
SLOT_JAM = {
    1 : (time(7,  0),  time(7,  50)),
    2 : (time(7, 50),  time(8,  40)),
    3 : (time(8, 40),  time(9,  30)),
    4 : (time(9, 30),  time(10, 20)),
    5 : (time(10, 20), time(11, 10)),
    6 : (time(11, 10), time(12,  0)),
    7 : (time(13,  0), time(13, 50)),
    8 : (time(13, 50), time(14, 40)),
    9 : (time(14, 40), time(15, 30)),
    10: (time(15, 30), time(16, 20)),
    11: (time(16, 20), time(17, 10)),
    12: (time(17, 10), time(18,  0)),
}

# ═══════════════════════════════════════════════════════════════
# DATA DEFINITIONS
# ═══════════════════════════════════════════════════════════════

# ── PROGRAM STUDI ─────────────────────────────────────────────
PROGRAM_STUDI_DATA = [
    {"kode": "TIF",    "nama": "Teknik Informatika",          "fakultas": "Fakultas Komunikasi dan Informatika", "jenjang": "S1"},
    {"kode": "SI",     "nama": "Sistem Informasi",            "fakultas": "Fakultas Komunikasi dan Informatika", "jenjang": "S1"},
    {"kode": "IK",     "nama": "Ilmu Komputer",               "fakultas": "Fakultas Komunikasi dan Informatika", "jenjang": "S1"},
    {"kode": "TK",     "nama": "Teknik Komputer",             "fakultas": "Fakultas Teknik",                     "jenjang": "S1"},
    {"kode": "MI",     "nama": "Manajemen Informatika",       "fakultas": "Fakultas Komunikasi dan Informatika", "jenjang": "D3"},
    {"kode": "MM",     "nama": "Matematika",                  "fakultas": "Fakultas Matematika dan IPA",         "jenjang": "S1"},
    {"kode": "TIF-S2", "nama": "Magister Teknik Informatika", "fakultas": "Fakultas Komunikasi dan Informatika", "jenjang": "S2"},
    {"kode": "EL",     "nama": "Teknik Elektro",              "fakultas": "Fakultas Teknik",                     "jenjang": "S1"},
]

# ── SUPER ADMIN & ADMIN ───────────────────────────────────────
SUPER_ADMIN_DATA = {
    "nim_nidn"     : "SUPERADMIN",
    "nama_lengkap" : "Wahyu Eko Putranto, S.T., M.T.",
    "email"        : "superadmin@unhas.ac.id",
    "role"         : UserRole.super_admin,
    "program_studi": "Divisi IT Kampus",
    "prodi_kode"   : None,
}

ADMIN_DATA = [
    {
        "nim_nidn"     : "ADMIN001",
        "nama_lengkap" : "Dr. Andi Mappangaja, S.Kom., M.M.",
        "email"        : "admin.fki@unhas.ac.id",
        "role"         : UserRole.admin,
        "program_studi": "Fakultas Komunikasi dan Informatika",
        "prodi_kode"   : None,
    },
    {
        "nim_nidn"     : "ADMIN002",
        "nama_lengkap" : "Hj. Rahmawati Usman, S.Pd., M.Si.",
        "email"        : "admin.ft@unhas.ac.id",
        "role"         : UserRole.admin,
        "program_studi": "Fakultas Teknik",
        "prodi_kode"   : None,
    },
    {
        "nim_nidn"     : "ADMIN003",
        "nama_lengkap" : "Muh. Syahril Ramadhan, A.Md.",
        "email"        : "admin.akademik@unhas.ac.id",
        "role"         : UserRole.admin,
        "program_studi": "Biro Administrasi Akademik",
        "prodi_kode"   : None,
    },
]

# ── DOSEN ─────────────────────────────────────────────────────
DOSEN_DATA = [
    {
        "nim_nidn"     : "0012038901",
        "nama_lengkap" : "Dr. Ir. Budi Santoso, M.T.",
        "email"        : "budi.santoso@unhas.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Teknik Informatika",
        "prodi_kode"   : "TIF",
    },
    {
        "nim_nidn"     : "0023047802",
        "nama_lengkap" : "Siti Rahayu Ningrum, S.T., M.Sc.",
        "email"        : "siti.rahayu@unhas.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Sistem Informasi",
        "prodi_kode"   : "SI",
    },
    {
        "nim_nidn"     : "0031056703",
        "nama_lengkap" : "Prof. Dr. Hendra Gunawan, M.Kom.",
        "email"        : "hendra.gunawan@unhas.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Teknik Informatika",
        "prodi_kode"   : "TIF",
    },
    {
        "nim_nidn"     : "0045069504",
        "nama_lengkap" : "Dewi Kusumawati, S.Si., M.Cs.",
        "email"        : "dewi.kusumawati@unhas.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Ilmu Komputer",
        "prodi_kode"   : "IK",
    },
    {
        "nim_nidn"     : "0056078405",
        "nama_lengkap" : "Rizal Fathurohman, M.T.",
        "email"        : "rizal.fathurohman@unhas.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Teknik Informatika",
        "prodi_kode"   : "TIF",
    },
    {
        "nim_nidn"     : "0067087306",
        "nama_lengkap" : "Nur Aisyah Putri, S.Kom., M.M.",
        "email"        : "nur.aisyah@unhas.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Sistem Informasi",
        "prodi_kode"   : "SI",
    },
    {
        "nim_nidn"     : "0078096207",
        "nama_lengkap" : "Ahmad Zulkifli Harun, S.T., M.Eng.",
        "email"        : "ahmad.zulkifli@unhas.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Teknik Komputer",
        "prodi_kode"   : "TK",
    },
    {
        "nim_nidn"     : "0089015108",
        "nama_lengkap" : "Indrawati Saleh, S.Kom., M.T.",
        "email"        : "indrawati.saleh@unhas.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Ilmu Komputer",
        "prodi_kode"   : "IK",
    },
    {
        "nim_nidn"     : "0091023409",
        "nama_lengkap" : "Fadhilah Rahmat, S.T., M.Sc.",
        "email"        : "fadhilah.rahmat@unhas.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Teknik Elektro",
        "prodi_kode"   : "EL",
    },
    {
        "nim_nidn"     : "0102034510",
        "nama_lengkap" : "Suryanti Muchlis, S.Si., M.Math.",
        "email"        : "suryanti.muchlis@unhas.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Matematika",
        "prodi_kode"   : "MM",
    },
]

# ── MAHASISWA (nim, nama, email, prodi_kode, angkatan) ────────
MAHASISWA_DATA = [
    # ── TIF 2021 (10 mhs) ──────────────────────────────────────
    ("H071211001", "Muhammad Rizky Pratama",       "rizky.pratama21@student.unhas.ac.id",    "TIF", 2021),
    ("H071211002", "Putri Amelia Sari",            "putri.amelia21@student.unhas.ac.id",     "TIF", 2021),
    ("H071211003", "Ahmad Farhan Maulana",         "farhan.maulana21@student.unhas.ac.id",   "TIF", 2021),
    ("H071211004", "Annisa Rahma Dewi",            "annisa.dewi21@student.unhas.ac.id",      "TIF", 2021),
    ("H071211005", "Bagas Eko Saputro",            "bagas.saputro21@student.unhas.ac.id",    "TIF", 2021),
    ("H071211006", "Cantika Nuraini",              "cantika.nuraini21@student.unhas.ac.id",  "TIF", 2021),
    ("H071211007", "Dimas Aditya Nugroho",         "dimas.nugroho21@student.unhas.ac.id",    "TIF", 2021),
    ("H071211008", "Elsa Permata Indah",           "elsa.permata21@student.unhas.ac.id",     "TIF", 2021),
    ("H071211009", "Faiz Akbar Ramadhan",          "faiz.ramadhan21@student.unhas.ac.id",    "TIF", 2021),
    ("H071211010", "Ghina Maudi Pratiwi",          "ghina.pratiwi21@student.unhas.ac.id",    "TIF", 2021),
    # ── TIF 2022 (8 mhs) ───────────────────────────────────────
    ("H071221001", "Hafizh Yusuf Kurniawan",       "hafizh.kurniawan22@student.unhas.ac.id", "TIF", 2022),
    ("H071221002", "Indira Cahyaningrum",          "indira.cahya22@student.unhas.ac.id",     "TIF", 2022),
    ("H071221003", "Jovan Aldriansyah",            "jovan.aldrian22@student.unhas.ac.id",    "TIF", 2022),
    ("H071221004", "Keisya Aurelia Putri",         "keisya.aurelia22@student.unhas.ac.id",   "TIF", 2022),
    ("H071221005", "Luthfi Hakim Ardiansyah",      "luthfi.hakim22@student.unhas.ac.id",     "TIF", 2022),
    ("H071221006", "Mardiyah Qonita",              "mardiyah.qonita22@student.unhas.ac.id",  "TIF", 2022),
    ("H071221007", "Naufal Zaki Firmansyah",       "naufal.zaki22@student.unhas.ac.id",      "TIF", 2022),
    ("H071221008", "Olga Pertiwi Maharani",        "olga.pertiwi22@student.unhas.ac.id",     "TIF", 2022),
    # ── TIF 2023 (5 mhs) ───────────────────────────────────────
    ("H071231001", "Miftahul Jannah Basri",        "miftah.basri23@student.unhas.ac.id",     "TIF", 2023),
    ("H071231002", "Nabil Rachmat Hidayat",        "nabil.rachmat23@student.unhas.ac.id",    "TIF", 2023),
    ("H071231003", "Olivia Setiawati Putri",       "olivia.setiawati23@student.unhas.ac.id", "TIF", 2023),
    ("H071231004", "Panji Surya Kencana",          "panji.surya23@student.unhas.ac.id",      "TIF", 2023),
    ("H071231005", "Qonita Azizah Mansur",         "qonita.mansur23@student.unhas.ac.id",    "TIF", 2023),
    # ── SI 2021 (10 mhs) ───────────────────────────────────────
    ("H071411001", "Maya Anggraeni Susanti",       "maya.anggraeni21@student.unhas.ac.id",   "SI",  2021),
    ("H071411002", "Naufal Dzikri Fauzan",         "naufal.fauzan21@student.unhas.ac.id",    "SI",  2021),
    ("H071411003", "Olivia Kurnia Dewi",           "olivia.kurnia21@student.unhas.ac.id",    "SI",  2021),
    ("H071411004", "Prasetyo Wibowo Nugroho",      "prasetyo.wibowo21@student.unhas.ac.id",  "SI",  2021),
    ("H071411005", "Qisthi Ramadhani",             "qisthi.ramadhani21@student.unhas.ac.id", "SI",  2021),
    ("H071411006", "Rafli Akbar Suhaimi",          "rafli.suhaimi21@student.unhas.ac.id",    "SI",  2021),
    ("H071411007", "Salsabila Nur Izzati",         "salsabila.izzati21@student.unhas.ac.id", "SI",  2021),
    ("H071411008", "Taufiq Hidayatullah",          "taufiq.hidayat21@student.unhas.ac.id",   "SI",  2021),
    ("H071411009", "Ulfa Maulidya Rahma",          "ulfa.rahma21@student.unhas.ac.id",       "SI",  2021),
    ("H071411010", "Vicky Ardiansyah Putra",       "vicky.ardiansyah21@student.unhas.ac.id", "SI",  2021),
    # ── SI 2022 (7 mhs) ────────────────────────────────────────
    ("H071421001", "Widya Astuti Ramadhani",       "widya.astuti22@student.unhas.ac.id",     "SI",  2022),
    ("H071421002", "Xaverius Bintang Pradana",     "xaverius.pradana22@student.unhas.ac.id", "SI",  2022),
    ("H071421003", "Yasmin Aulia Salsabila",       "yasmin.salsabila22@student.unhas.ac.id", "SI",  2022),
    ("H071421004", "Zaidan Farel Pratama",         "zaidan.farel22@student.unhas.ac.id",     "SI",  2022),
    ("H071421005", "Adinda Puspa Maharani",        "adinda.puspa22@student.unhas.ac.id",     "SI",  2022),
    ("H071421006", "Bagus Hermawan Saputra",       "bagus.hermawan22@student.unhas.ac.id",   "SI",  2022),
    ("H071421007", "Cahaya Rahmi Perdana",         "cahaya.rahmi22@student.unhas.ac.id",     "SI",  2022),
    # ── IK 2021 (8 mhs) ────────────────────────────────────────
    ("H071311001", "Bintang Ramadhan Putra",       "bintang.putra21@student.unhas.ac.id",    "IK",  2021),
    ("H071311002", "Chelsea Amanda Pratiwi",       "chelsea.pratiwi21@student.unhas.ac.id",  "IK",  2021),
    ("H071311003", "Daffa Arya Wicaksono",         "daffa.wicaksono21@student.unhas.ac.id",  "IK",  2021),
    ("H071311004", "Eka Putri Handayani",          "eka.handayani21@student.unhas.ac.id",    "IK",  2021),
    ("H071311005", "Farhan Septian Nugroho",       "farhan.septian21@student.unhas.ac.id",   "IK",  2021),
    ("H071311006", "Gilang Ramadhan Sanjaya",      "gilang.sanjaya21@student.unhas.ac.id",   "IK",  2021),
    ("H071311007", "Hana Salsabila Anwar",         "hana.anwar21@student.unhas.ac.id",       "IK",  2021),
    ("H071311008", "Ilham Syahputra Wahid",        "ilham.syahputra21@student.unhas.ac.id",  "IK",  2021),
    # ── IK 2022 (5 mhs) ────────────────────────────────────────
    ("H071321001", "Jessica Tamara Larasati",      "jessica.larasati22@student.unhas.ac.id", "IK",  2022),
    ("H071321002", "Kevin Ardianto Susilo",        "kevin.susilo22@student.unhas.ac.id",     "IK",  2022),
    ("H071321003", "Layla Sari Wulandari",         "layla.wulandari22@student.unhas.ac.id",  "IK",  2022),
    ("H071321004", "Maulana Dian Pratama",         "maulana.dian22@student.unhas.ac.id",     "IK",  2022),
    ("H071321005", "Nadia Kurniasih",              "nadia.kurniasih22@student.unhas.ac.id",  "IK",  2022),
    # ── TK 2021 (5 mhs) ────────────────────────────────────────
    ("H071511001", "Leonardo Devano Putra",        "leonardo.devano21@student.unhas.ac.id",  "TK",  2021),
    ("H071511002", "Maulana Ibrahim Hasbi",        "maulana.hasbi21@student.unhas.ac.id",    "TK",  2021),
    ("H071511003", "Nida Ul Hasanah",              "nida.hasanah21@student.unhas.ac.id",     "TK",  2021),
    ("H071511004", "Omar Dzaki Ramdhani",          "omar.dzaki21@student.unhas.ac.id",       "TK",  2021),
    ("H071511005", "Priadi Suryaningrat",          "priadi.surya21@student.unhas.ac.id",     "TK",  2021),
    # ── TK 2022 (5 mhs) ────────────────────────────────────────
    ("H071521001", "Qurrotu Aini Latifah",         "qurrotu.aini22@student.unhas.ac.id",     "TK",  2022),
    ("H071521002", "Raka Pratama Wijaya",          "raka.pratama22@student.unhas.ac.id",     "TK",  2022),
    ("H071521003", "Syifa Nur Rahmadani",          "syifa.nur22@student.unhas.ac.id",        "TK",  2022),
    ("H071521004", "Taofik Hidayat Permana",       "taofik.hidayat22@student.unhas.ac.id",   "TK",  2022),
    ("H071521005", "Ulfah Kharisma Dewi",          "ulfah.kharisma22@student.unhas.ac.id",   "TK",  2022),
    # ── MI 2022 (5 mhs) ────────────────────────────────────────
    ("H071641001", "Vira Claudia Santoso",         "vira.claudia22@student.unhas.ac.id",     "MI",  2022),
    ("H071641002", "Wahyu Tri Atmaja",             "wahyu.atmaja22@student.unhas.ac.id",     "MI",  2022),
    ("H071641003", "Xenofon Ariel Manuela",        "xenofon.ariel22@student.unhas.ac.id",    "MI",  2022),
    ("H071641004", "Yovita Ratna Kumala",          "yovita.ratna22@student.unhas.ac.id",     "MI",  2022),
    ("H071641005", "Zafira Khairunnisa",           "zafira.khairunnisa22@student.unhas.ac.id","MI", 2022),
    # ── EL 2021 (5 mhs) ────────────────────────────────────────
    ("H071711001", "Ardiansyah Syaiful",           "ardiansyah.syaiful21@student.unhas.ac.id","EL", 2021),
    ("H071711002", "Bunga Oktaviani",              "bunga.oktaviani21@student.unhas.ac.id",  "EL",  2021),
    ("H071711003", "Chairul Anwar Nasution",       "chairul.anwar21@student.unhas.ac.id",    "EL",  2021),
    ("H071711004", "Dini Cahyani Pratiwi",         "dini.cahyani21@student.unhas.ac.id",     "EL",  2021),
    ("H071711005", "Erlan Fatwa Mubarak",          "erlan.fatwa21@student.unhas.ac.id",      "EL",  2021),
    # ── MM 2022 (5 mhs) ────────────────────────────────────────
    ("H071851001", "Firda Amalia Putri",           "firda.amalia22@student.unhas.ac.id",     "MM",  2022),
    ("H071851002", "Gilang Aji Wibowo",            "gilang.aji22@student.unhas.ac.id",       "MM",  2022),
    ("H071851003", "Hasna Nabila Rahma",           "hasna.nabila22@student.unhas.ac.id",     "MM",  2022),
    ("H071851004", "Irfan Naufal Hakim",           "irfan.hakim22@student.unhas.ac.id",      "MM",  2022),
    ("H071851005", "Jihan Rizqiyah Utami",         "jihan.rizqiyah22@student.unhas.ac.id",   "MM",  2022),
]

# ── RUANGAN ───────────────────────────────────────────────────
# Koordinat GPS sekitar Kampus Unhas Tamalanrea, Makassar
RUANGAN_DATA = [
    # --- Ruang Kuliah Gedung J ---
    {"kode": "J.Int.1",   "nama": "Ruang Kuliah J International 1",       "tipe": "kuliah",  "kapasitas": 45, "gedung": "Gedung J",  "lantai": 1, "lat": -5.130245, "lng": 119.489432},
    {"kode": "J.Int.2",   "nama": "Ruang Kuliah J International 2",       "tipe": "kuliah",  "kapasitas": 45, "gedung": "Gedung J",  "lantai": 1, "lat": -5.130280, "lng": 119.489500},
    {"kode": "J.Int.3",   "nama": "Ruang Kuliah J International 3",       "tipe": "kuliah",  "kapasitas": 40, "gedung": "Gedung J",  "lantai": 1, "lat": -5.130310, "lng": 119.489540},
    {"kode": "J0403",     "nama": "Ruang Kuliah J Lantai 4 No.3",         "tipe": "kuliah",  "kapasitas": 40, "gedung": "Gedung J",  "lantai": 4, "lat": -5.130100, "lng": 119.489350},
    {"kode": "J0407",     "nama": "Ruang Kuliah J Lantai 4 No.7",         "tipe": "kuliah",  "kapasitas": 40, "gedung": "Gedung J",  "lantai": 4, "lat": -5.130120, "lng": 119.489380},
    {"kode": "J0408",     "nama": "Ruang Kuliah J Lantai 4 No.8",         "tipe": "kuliah",  "kapasitas": 40, "gedung": "Gedung J",  "lantai": 4, "lat": -5.130140, "lng": 119.489410},
    # --- Ruang Kuliah Gedung SW ---
    {"kode": "SW706",     "nama": "Ruang Kuliah SW Lantai 7 No.6",        "tipe": "kuliah",  "kapasitas": 50, "gedung": "Gedung SW", "lantai": 7, "lat": -5.132451, "lng": 119.491380},
    {"kode": "SW708",     "nama": "Ruang Kuliah SW Lantai 7 No.8",        "tipe": "kuliah",  "kapasitas": 50, "gedung": "Gedung SW", "lantai": 7, "lat": -5.132480, "lng": 119.491420},
    {"kode": "SW501",     "nama": "Ruang Kuliah SW Lantai 5 No.1",        "tipe": "kuliah",  "kapasitas": 45, "gedung": "Gedung SW", "lantai": 5, "lat": -5.132200, "lng": 119.491200},
    # --- Ruang Kuliah Gedung C ---
    {"kode": "C-202",     "nama": "Ruang Kuliah C Lantai 2 No.2",         "tipe": "kuliah",  "kapasitas": 35, "gedung": "Gedung C",  "lantai": 2, "lat": -5.131100, "lng": 119.490271},
    {"kode": "C-204",     "nama": "Ruang Kuliah C Lantai 2 No.4",         "tipe": "kuliah",  "kapasitas": 35, "gedung": "Gedung C",  "lantai": 2, "lat": -5.131140, "lng": 119.490310},
    {"kode": "C-301",     "nama": "Ruang Kuliah C Lantai 3 No.1",         "tipe": "kuliah",  "kapasitas": 50, "gedung": "Gedung C",  "lantai": 3, "lat": -5.131080, "lng": 119.490240},
    # --- Lab Gedung J ---
    {"kode": "LABRPL",    "nama": "Lab Rekayasa Perangkat Lunak",          "tipe": "lab",     "kapasitas": 30, "gedung": "Gedung J",  "lantai": 2, "lat": -5.130873, "lng": 119.488950},
    {"kode": "LSITIF",    "nama": "Lab Sistem Terdistribusi & Jaringan",   "tipe": "lab",     "kapasitas": 28, "gedung": "Gedung J",  "lantai": 2, "lat": -5.130890, "lng": 119.489010},
    {"kode": "LJKTIF",    "nama": "Lab Jaringan Komputer TIF",             "tipe": "lab",     "kapasitas": 30, "gedung": "Gedung J",  "lantai": 3, "lat": -5.130620, "lng": 119.488800},
    {"kode": "LABAI",     "nama": "Lab Kecerdasan Artifisial",             "tipe": "lab",     "kapasitas": 25, "gedung": "Gedung J",  "lantai": 3, "lat": -5.130650, "lng": 119.488840},
    {"kode": "LABDB",     "nama": "Lab Basis Data",                        "tipe": "lab",     "kapasitas": 30, "gedung": "Gedung C",  "lantai": 1, "lat": -5.131340, "lng": 119.490800},
    {"kode": "LABMOBILE", "nama": "Lab Mobile Computing",                  "tipe": "lab",     "kapasitas": 25, "gedung": "Gedung C",  "lantai": 1, "lat": -5.131380, "lng": 119.490840},
    {"kode": "LABHW",     "nama": "Lab Hardware & Embedded Systems",       "tipe": "lab",     "kapasitas": 24, "gedung": "Gedung SW", "lantai": 3, "lat": -5.132120, "lng": 119.491000},
    {"kode": "LABCYBER",  "nama": "Lab Keamanan Siber",                    "tipe": "lab",     "kapasitas": 20, "gedung": "Gedung J",  "lantai": 3, "lat": -5.130660, "lng": 119.488870},
    # --- Seminar / Aula ---
    {"kode": "JSEM1",     "nama": "Aula Seminar J Lantai 1",               "tipe": "seminar", "kapasitas": 150,"gedung": "Gedung J",  "lantai": 1, "lat": -5.130400, "lng": 119.489600},
    {"kode": "JSEM2",     "nama": "Ruang Sidang J Lantai 2",               "tipe": "seminar", "kapasitas": 60, "gedung": "Gedung J",  "lantai": 2, "lat": -5.130450, "lng": 119.489650},
    {"kode": "RVL200",    "nama": "Ruang Vicon & Livestream",               "tipe": "seminar", "kapasitas": 40, "gedung": "Gedung SW", "lantai": 2, "lat": -5.132200, "lng": 119.491100},
    {"kode": "AULA-FKI",  "nama": "Aula Utama FKI",                        "tipe": "seminar", "kapasitas": 300,"gedung": "Gedung FKI","lantai": 1, "lat": -5.129800, "lng": 119.488500},
    {"kode": "AULA-FT",   "nama": "Aula Utama Fakultas Teknik",            "tipe": "seminar", "kapasitas": 250,"gedung": "Gedung FT", "lantai": 1, "lat": -5.128900, "lng": 119.487800},
]

# ── MATAKULIAH ────────────────────────────────────────────────
MATAKULIAH_DATA = [
    # ── TIF ──────────────────────────────────────────────────
    {
        "kode": "TIF3221308", "nama": "Logika dan Himpunan",               "sks": 3, "prodi": "TIF",
        "izin_tamu": False, "dosen_utama_nidn": "0031056703",
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0031056703", "ruangan": "J.Int.1",  "hari": "Senin",  "slot_m": 1, "slot_s": 3},
            {"kode_kelas": "B", "dosen_nidn": "0012038901", "ruangan": "J0403",    "hari": "Selasa", "slot_m": 1, "slot_s": 3},
            {"kode_kelas": "C", "dosen_nidn": "0056078405", "ruangan": "J.Int.2",  "hari": "Rabu",   "slot_m": 4, "slot_s": 6},
        ],
    },
    {
        "kode": "TIF3232209", "nama": "Pemrograman Mobile",                "sks": 3, "prodi": "TIF",
        "izin_tamu": True, "dosen_utama_nidn": "0012038901",
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0012038901", "ruangan": "LABMOBILE","hari": "Senin",  "slot_m": 7, "slot_s": 9},
            {"kode_kelas": "B", "dosen_nidn": "0056078405", "ruangan": "LABMOBILE","hari": "Kamis",  "slot_m": 7, "slot_s": 9},
        ],
    },
    {
        "kode": "TIF4011401", "nama": "Kecerdasan Buatan",                 "sks": 3, "prodi": "TIF",
        "izin_tamu": True, "dosen_utama_nidn": "0031056703",
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0031056703", "ruangan": "LABAI",    "hari": "Rabu",   "slot_m": 1, "slot_s": 3},
            {"kode_kelas": "B", "dosen_nidn": "0045069504", "ruangan": "LABAI",    "hari": "Jumat",  "slot_m": 4, "slot_s": 6},
        ],
    },
    {
        "kode": "TIF3222101", "nama": "Basis Data Lanjut",                 "sks": 3, "prodi": "TIF",
        "izin_tamu": False, "dosen_utama_nidn": "0023047802",
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0023047802", "ruangan": "LABDB",    "hari": "Selasa", "slot_m": 7, "slot_s": 9},
            {"kode_kelas": "B", "dosen_nidn": "0012038901", "ruangan": "LABDB",    "hari": "Kamis",  "slot_m": 1, "slot_s": 3},
        ],
    },
    {
        "kode": "TIF2011301", "nama": "Pemrograman Berorientasi Objek",    "sks": 3, "prodi": "TIF",
        "izin_tamu": False, "dosen_utama_nidn": "0012038901",
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0012038901", "ruangan": "LABRPL",   "hari": "Rabu",   "slot_m": 7, "slot_s": 9},
            {"kode_kelas": "B", "dosen_nidn": "0056078405", "ruangan": "LABRPL",   "hari": "Jumat",  "slot_m": 1, "slot_s": 3},
            {"kode_kelas": "C", "dosen_nidn": "0045069504", "ruangan": "J0407",    "hari": "Senin",  "slot_m": 4, "slot_s": 6},
        ],
    },
    {
        "kode": "TIF3243105", "nama": "Keamanan Jaringan Komputer",        "sks": 3, "prodi": "TIF",
        "izin_tamu": True, "dosen_utama_nidn": "0056078405",
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0056078405", "ruangan": "LABCYBER", "hari": "Selasa", "slot_m": 4, "slot_s": 6},
            {"kode_kelas": "B", "dosen_nidn": "0089015108", "ruangan": "LSITIF",   "hari": "Kamis",  "slot_m": 4, "slot_s": 6},
        ],
    },
    # ── SI ───────────────────────────────────────────────────
    {
        "kode": "SI2234567", "nama": "Sistem Informasi Manajemen",         "sks": 3, "prodi": "SI",
        "izin_tamu": False, "dosen_utama_nidn": "0023047802",
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0023047802", "ruangan": "SW706",    "hari": "Kamis",  "slot_m": 1, "slot_s": 3},
            {"kode_kelas": "B", "dosen_nidn": "0067087306", "ruangan": "SW708",    "hari": "Jumat",  "slot_m": 7, "slot_s": 9},
        ],
    },
    {
        "kode": "SI3013301", "nama": "Analisis dan Desain Sistem",         "sks": 3, "prodi": "SI",
        "izin_tamu": True, "dosen_utama_nidn": "0067087306",
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0067087306", "ruangan": "C-202",    "hari": "Jumat",  "slot_m": 1, "slot_s": 3},
            {"kode_kelas": "B", "dosen_nidn": "0023047802", "ruangan": "C-204",    "hari": "Senin",  "slot_m": 10,"slot_s": 12},
        ],
    },
    # ── IK ───────────────────────────────────────────────────
    {
        "kode": "IK2012201", "nama": "Algoritma dan Struktur Data",        "sks": 4, "prodi": "IK",
        "izin_tamu": False, "dosen_utama_nidn": "0045069504",
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0045069504", "ruangan": "LSITIF",   "hari": "Senin",  "slot_m": 7, "slot_s": 10},
            {"kode_kelas": "B", "dosen_nidn": "0089015108", "ruangan": "J0408",    "hari": "Rabu",   "slot_m": 4, "slot_s": 7},
        ],
    },
    {
        "kode": "IK3012301", "nama": "Jaringan Komputer",                  "sks": 3, "prodi": "IK",
        "izin_tamu": True, "dosen_utama_nidn": "0056078405",
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0056078405", "ruangan": "LJKTIF",   "hari": "Rabu",   "slot_m": 1, "slot_s": 3},
            {"kode_kelas": "B", "dosen_nidn": "0078096207", "ruangan": "LABHW",    "hari": "Kamis",  "slot_m": 7, "slot_s": 9},
        ],
    },
    # ── TK ───────────────────────────────────────────────────
    {
        "kode": "TK2011201", "nama": "Arsitektur Sistem Komputer",         "sks": 3, "prodi": "TK",
        "izin_tamu": False, "dosen_utama_nidn": "0078096207",
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0078096207", "ruangan": "LABHW",    "hari": "Selasa", "slot_m": 4, "slot_s": 6},
            {"kode_kelas": "B", "dosen_nidn": "0091023409", "ruangan": "J0408",    "hari": "Jumat",  "slot_m": 7, "slot_s": 9},
        ],
    },
    # ── MM ───────────────────────────────────────────────────
    {
        "kode": "MM2021101", "nama": "Statistika Matematika",              "sks": 3, "prodi": "MM",
        "izin_tamu": True, "dosen_utama_nidn": "0102034510",
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0102034510", "ruangan": "C-301",    "hari": "Selasa", "slot_m": 1, "slot_s": 3},
            {"kode_kelas": "B", "dosen_nidn": "0102034510", "ruangan": "C-301",    "hari": "Kamis",  "slot_m": 4, "slot_s": 6},
        ],
    },
]

# ── Enrollment rules: (kode_mk, kode_kelas, [NIM list]) ──────
def build_enrollment_rules():
    """Bangun aturan enrollment berdasarkan data mahasiswa."""
    tif_21 = [n for n, *_, p, a in MAHASISWA_DATA if p == "TIF" and a == 2021]
    tif_22 = [n for n, *_, p, a in MAHASISWA_DATA if p == "TIF" and a == 2022]
    tif_23 = [n for n, *_, p, a in MAHASISWA_DATA if p == "TIF" and a == 2023]
    si_21  = [n for n, *_, p, a in MAHASISWA_DATA if p == "SI"  and a == 2021]
    si_22  = [n for n, *_, p, a in MAHASISWA_DATA if p == "SI"  and a == 2022]
    ik_21  = [n for n, *_, p, a in MAHASISWA_DATA if p == "IK"  and a == 2021]
    ik_22  = [n for n, *_, p, a in MAHASISWA_DATA if p == "IK"  and a == 2022]
    tk_21  = [n for n, *_, p, a in MAHASISWA_DATA if p == "TK"  and a == 2021]
    tk_22  = [n for n, *_, p, a in MAHASISWA_DATA if p == "TK"  and a == 2022]
    mm_22  = [n for n, *_, p, a in MAHASISWA_DATA if p == "MM"  and a == 2022]

    return [
        # TIF3221308 Logika dan Himpunan
        ("TIF3221308", "A", tif_22),
        ("TIF3221308", "B", tif_21[:8]),
        ("TIF3221308", "C", tif_23),
        # TIF3232209 Pemrograman Mobile
        ("TIF3232209", "A", tif_21),
        ("TIF3232209", "B", tif_22),
        # TIF4011401 Kecerdasan Buatan
        ("TIF4011401", "A", tif_21[:8]),
        ("TIF4011401", "B", ik_21[:5]),
        # TIF3222101 Basis Data Lanjut
        ("TIF3222101", "A", tif_21),
        ("TIF3222101", "B", tif_22),
        # TIF2011301 PBO
        ("TIF2011301", "A", tif_22),
        ("TIF2011301", "B", tif_23),
        ("TIF2011301", "C", si_22[:5]),
        # TIF3243105 Keamanan Jaringan
        ("TIF3243105", "A", tif_21[:7]),
        ("TIF3243105", "B", ik_21[:5]),
        # SI2234567 SIM
        ("SI2234567",  "A", si_21),
        ("SI2234567",  "B", si_22),
        # SI3013301 Analisis Desain
        ("SI3013301",  "A", si_21),
        ("SI3013301",  "B", si_22),
        # IK2012201 Algoritma
        ("IK2012201",  "A", ik_21),
        ("IK2012201",  "B", ik_22),
        # IK3012301 Jaringan Komputer
        ("IK3012301",  "A", ik_21),
        ("IK3012301",  "B", tk_21[:4]),
        # TK2011201 Arsitektur
        ("TK2011201",  "A", tk_21),
        ("TK2011201",  "B", tk_22),
        # MM2021101 Statistika
        ("MM2021101",  "A", mm_22),
        ("MM2021101",  "B", ik_22[:3]),
    ]


# Mahasiswa tamu manual: (kode_mk, kode_kelas, nim, kelas_asal_hint)
TAMU_DATA = [
    ("TIF4011401", "A", "H071411001", "Sistem Informasi — Kelas Reguler"),
    ("TIF4011401", "A", "H071411002", "Sistem Informasi — Kelas Reguler"),
    ("TIF3232209", "A", "H071411003", "Sistem Informasi — Kelas Reguler"),
    ("TIF3243105", "A", "H071411005", "Sistem Informasi — Kelas Reguler"),
    ("SI3013301",  "A", "H071211001", "Teknik Informatika — Kelas Reguler"),
    ("IK3012301",  "B", "H071411004", "Sistem Informasi — Kelas Reguler"),
    ("MM2021101",  "A", "H071511001", "Teknik Komputer — Kelas Reguler"),
]

# ── KONFIGURASI SISTEM ────────────────────────────────────────
KONFIGURASI_DEFAULT = [
    {
        "key": "face_threshold",       "value": "0.9",
        "label": "Face Recognition Threshold",
        "deskripsi": "Euclidean distance threshold untuk verifikasi wajah. Range: 0.1–2.0. Default: 0.9.",
        "tipe": "float", "nilai_min": "0.1", "nilai_max": "2.0", "is_readonly": False,
    },
    {
        "key": "geofencing_radius",    "value": "100",
        "label": "Radius Geofencing Presensi Offline (meter)",
        "deskripsi": "Jarak maksimum antara mahasiswa dan koordinat ruang kelas. Default: 100m.",
        "tipe": "integer", "nilai_min": "10", "nilai_max": "500", "is_readonly": False,
    },
    {
        "key": "timezone",             "value": "Asia/Jakarta",
        "label": "Timezone Server",
        "deskripsi": "Timezone IANA yang dipakai server. Default: Asia/Jakarta (WIB).",
        "tipe": "string", "nilai_min": None, "nilai_max": None, "is_readonly": False,
    },
    {
        "key": "maintenance_mode",     "value": "false",
        "label": "Mode Maintenance",
        "deskripsi": "Jika 'true', semua endpoint presensi dinonaktifkan sementara.",
        "tipe": "boolean", "nilai_min": None, "nilai_max": None, "is_readonly": False,
    },
    {
        "key": "max_foto_registrasi",  "value": "8",
        "label": "Jumlah Foto Minimal Registrasi Wajah",
        "deskripsi": "Jumlah foto yang harus diambil saat registrasi wajah. Default: 8.",
        "tipe": "integer", "nilai_min": "4", "nilai_max": "20", "is_readonly": False,
    },
]


# ═══════════════════════════════════════════════════════════════
# MAIN SEED
# ═══════════════════════════════════════════════════════════════

def seed():
    db = SessionLocal()
    try:
        print("=" * 72)
        print("  SEED v3.5.0 — Presensi Face Recognition (Fase A–E + B-1)")
        print("=" * 72)

        # ── [1] PROGRAM STUDI ─────────────────────────────────────
        print("\n[1/11] Program Studi...")
        prodi_map: dict = {}
        for data in PROGRAM_STUDI_DATA:
            ex = db.query(ProgramStudi).filter(ProgramStudi.kode == data["kode"]).first()
            if ex:
                prodi_map[data["kode"]] = ex
                continue
            prodi = ProgramStudi(**data, is_active=True)
            db.add(prodi)
            db.flush()
            prodi_map[data["kode"]] = prodi
            print(f"  ✓ {data['kode']} — {data['nama']} ({data['jenjang']})")
        db.flush()
        print(f"  → {len(prodi_map)} program studi")

        # ── [2] USERS ─────────────────────────────────────────────
        print("\n[2/11] Users (Super Admin, Admin, Dosen, Mahasiswa)...")
        users_by_nim: dict = {}

        all_staff = (
            [SUPER_ADMIN_DATA]
            + ADMIN_DATA
            + DOSEN_DATA
        )

        for data in all_staff:
            ex = db.query(User).filter(User.nim_nidn == data["nim_nidn"]).first()
            if ex:
                users_by_nim[data["nim_nidn"]] = ex
                continue
            prodi_kode = data.get("prodi_kode")
            u = User(
                nim_nidn           = data["nim_nidn"],
                nama_lengkap       = data["nama_lengkap"],
                email              = data["email"],
                password_hash      = pw(),
                role               = data["role"],
                program_studi      = data["program_studi"],
                program_studi_id   = prodi_map[prodi_kode].id if prodi_kode and prodi_kode in prodi_map else None,
                is_face_registered = False,
                is_active          = True,
            )
            db.add(u)
            db.flush()
            users_by_nim[data["nim_nidn"]] = u
            lbl = {"mahasiswa":"Mhs","dosen":"Dsn","admin":"Adm","super_admin":"SA"}[data["role"].value]
            print(f"  ✓ [{lbl}] {data['nama_lengkap']}")

        # Mahasiswa
        mhs_count = 0
        for nim, nama, email, prodi_kode, angkatan in MAHASISWA_DATA:
            ex = db.query(User).filter(User.nim_nidn == nim).first()
            if ex:
                users_by_nim[nim] = ex
                continue
            prodi = prodi_map.get(prodi_kode)
            u = User(
                nim_nidn           = nim,
                nama_lengkap       = nama,
                email              = email,
                password_hash      = pw(),
                role               = UserRole.mahasiswa,
                program_studi      = prodi.nama if prodi else prodi_kode,
                program_studi_id   = prodi.id if prodi else None,
                is_face_registered = True,  # sudah registrasi wajah
                is_active          = True,
            )
            db.add(u)
            db.flush()
            users_by_nim[nim] = u
            mhs_count += 1

        db.flush()
        total_u = db.query(User).count()
        print(f"  → {mhs_count} mahasiswa baru. Total users di DB: {total_u}")

        # ── [3] RUANGAN ───────────────────────────────────────────
        print("\n[3/11] Ruangan...")
        ruangan_map: dict = {}
        for r in RUANGAN_DATA:
            ex = db.query(Ruangan).filter(Ruangan.kode == r["kode"]).first()
            if ex:
                ruangan_map[r["kode"]] = ex
                continue
            obj = Ruangan(
                kode          = r["kode"],
                nama          = r["nama"],
                tipe          = r["tipe"],
                kapasitas     = r["kapasitas"],
                gedung        = r["gedung"],
                lantai        = r["lantai"],
                koordinat_lat = r["lat"],
                koordinat_lng = r["lng"],
                is_active     = True,
            )
            db.add(obj)
            db.flush()
            ruangan_map[r["kode"]] = obj
            tipe_ico = {"kuliah": "📚", "lab": "🖥️", "seminar": "🎤"}.get(r["tipe"], "🏫")
            print(f"  ✓ {tipe_ico} {r['kode']:<12} {r['nama'][:45]} (kap. {r['kapasitas']})")
        db.flush()
        print(f"  → {len(ruangan_map)} ruangan")

        # ── [4] MATAKULIAH + KELAS ────────────────────────────────
        print("\n[4/11] Matakuliah & Kelas...")
        mk_map   : dict = {}
        kelas_map: dict = {}  # (kode_mk, kode_kelas) → KelasMatakuliah

        for mk_data in MATAKULIAH_DATA:
            kls0        = mk_data["kelas"][0]
            jam_mulai   = SLOT_JAM[kls0["slot_m"]][0]
            jam_selesai = SLOT_JAM[kls0["slot_s"]][1]
            r0          = ruangan_map.get(kls0["ruangan"])

            ex_mk = db.query(Matakuliah).filter(Matakuliah.kode == mk_data["kode"]).first()
            if not ex_mk:
                mk_obj = Matakuliah(
                    kode          = mk_data["kode"],
                    nama          = mk_data["nama"],
                    sks           = mk_data["sks"],
                    hari          = kls0["hari"],
                    jam_mulai     = jam_mulai,
                    jam_selesai   = jam_selesai,
                    ruangan       = kls0["ruangan"],
                    koordinat_lat = r0.koordinat_lat if r0 else None,
                    koordinat_lng = r0.koordinat_lng if r0 else None,
                    izin_tamu     = mk_data["izin_tamu"],
                )
                db.add(mk_obj)
                db.flush()
                n_kelas = len(mk_data["kelas"])
                print(f"  ✓ {mk_data['kode']:<14} {mk_data['nama'][:38]:<38} ({n_kelas} kelas)")
            else:
                mk_obj = ex_mk

            mk_map[mk_data["kode"]] = mk_obj

            for kls in mk_data["kelas"]:
                ex_k = db.query(KelasMatakuliah).filter(
                    KelasMatakuliah.matakuliah_id == mk_obj.id,
                    KelasMatakuliah.kode_kelas    == kls["kode_kelas"],
                ).first()
                if ex_k:
                    kelas_map[(mk_data["kode"], kls["kode_kelas"])] = ex_k
                    continue

                dosen   = users_by_nim.get(kls["dosen_nidn"])
                ruangan = ruangan_map.get(kls["ruangan"])

                k_obj = KelasMatakuliah(
                    matakuliah_id = mk_obj.id,
                    kode_kelas    = kls["kode_kelas"],
                    dosen_id      = dosen.id if dosen else None,
                    ruangan_id    = ruangan.id if ruangan else None,
                    hari          = kls["hari"],
                    slot_mulai    = kls["slot_m"],
                    slot_selesai  = kls["slot_s"],
                    izin_tamu     = mk_data["izin_tamu"],
                    is_active     = True,
                )
                db.add(k_obj)
                db.flush()
                kelas_map[(mk_data["kode"], kls["kode_kelas"])] = k_obj

        db.flush()
        print(f"  → {len(mk_map)} matakuliah, {len(kelas_map)} kelas")

        # ── [5] ENROLLMENT ────────────────────────────────────────
        print("\n[5/11] Enrollment (Mahasiswa → Kelas)...")
        enrollment_rules = build_enrollment_rules()
        enroll_count = 0

        for kode_mk, kode_kelas, nim_list in enrollment_rules:
            kelas_obj = kelas_map.get((kode_mk, kode_kelas))
            mk_obj    = mk_map.get(kode_mk)
            if not kelas_obj or not mk_obj:
                continue
            for nim in nim_list:
                user = users_by_nim.get(nim)
                if not user:
                    continue
                ex = db.query(MahasiswaMatakuliah).filter(
                    MahasiswaMatakuliah.mahasiswa_id  == user.id,
                    MahasiswaMatakuliah.matakuliah_id == mk_obj.id,
                ).first()
                if not ex:
                    db.add(MahasiswaMatakuliah(
                        mahasiswa_id  = user.id,
                        matakuliah_id = mk_obj.id,
                        kelas_id      = kelas_obj.id,
                        is_tamu       = False,
                        kelas_asal    = None,
                    ))
                    enroll_count += 1

        # Tamu manual
        for kode_mk, kode_kelas, nim, kelas_asal in TAMU_DATA:
            kelas_obj = kelas_map.get((kode_mk, kode_kelas))
            mk_obj    = mk_map.get(kode_mk)
            user      = users_by_nim.get(nim)
            if not kelas_obj or not mk_obj or not user:
                continue
            ex = db.query(MahasiswaMatakuliah).filter(
                MahasiswaMatakuliah.mahasiswa_id  == user.id,
                MahasiswaMatakuliah.matakuliah_id == mk_obj.id,
            ).first()
            if not ex:
                db.add(MahasiswaMatakuliah(
                    mahasiswa_id  = user.id,
                    matakuliah_id = mk_obj.id,
                    kelas_id      = kelas_obj.id,
                    is_tamu       = True,
                    kelas_asal    = kelas_asal,
                ))
                enroll_count += 1
                print(f"  ✓ Tamu: {user.nama_lengkap} → {kode_mk} Kelas {kode_kelas}")

        db.flush()
        print(f"  → {enroll_count} record enrollment baru")

        # ── [6] JADWAL PENGGANTI (Fase B-1: include field mode) ───
        print("\n[6/11] Jadwal Pengganti (Fase B-1: dengan field mode)...")
        JADWAL_PENGGANTI_DATA = [
            {
                "kode_mk": "TIF3232209", "dosen_nidn": "0012038901", "pertemuan_ke": 5,
                "jam_mulai_baru": time(10, 0), "jam_selesai_baru": time(12, 30),
                "ruangan_baru": "C-202", "mode": None,
                "keterangan": "Ruang Lab Mobile sedang perbaikan AC, pindah ke C-202",
            },
            {
                "kode_mk": "TIF3222101", "dosen_nidn": "0023047802", "pertemuan_ke": 8,
                "jam_mulai_baru": time(10, 0), "jam_selesai_baru": time(12, 30),
                "ruangan_baru": None, "mode": "online",
                "keterangan": "Dosen ada jadwal rapat pimpinan, pertemuan ke-8 dialihkan ke online",
            },
            {
                "kode_mk": "SI2234567", "dosen_nidn": "0023047802", "pertemuan_ke": 3,
                "jam_mulai_baru": None, "jam_selesai_baru": None,
                "ruangan_baru": "AULA-FKI", "mode": None,
                "keterangan": "Kuliah tamu dari PT Telkom Indonesia — dipindah ke Aula FKI",
            },
            {
                "kode_mk": "TIF4011401", "dosen_nidn": "0031056703", "pertemuan_ke": 10,
                "jam_mulai_baru": time(13, 0), "jam_selesai_baru": time(15, 30),
                "ruangan_baru": "JSEM1", "mode": None,
                "keterangan": "Presentasi tugas besar — ruang diperbesar ke Aula J",
            },
            {
                "kode_mk": "IK2012201", "dosen_nidn": "0045069504", "pertemuan_ke": 6,
                "jam_mulai_baru": None, "jam_selesai_baru": None,
                "ruangan_baru": None, "mode": "online",
                "keterangan": "Pertemuan 6 dilaksanakan online melalui Zoom karena cuaca ekstrem",
            },
            {
                "kode_mk": "TIF3221308", "dosen_nidn": "0031056703", "pertemuan_ke": 12,
                "jam_mulai_baru": time(9, 30), "jam_selesai_baru": time(12, 0),
                "ruangan_baru": "J.Int.3", "mode": "offline",
                "keterangan": "Ujian tengah semester — ruang dipindah dan jam diubah",
            },
            {
                "kode_mk": "SI3013301", "dosen_nidn": "0067087306", "pertemuan_ke": 7,
                "jam_mulai_baru": time(13, 0), "jam_selesai_baru": time(15, 30),
                "ruangan_baru": "SW501", "mode": None,
                "keterangan": "Pindah ruang karena C-202 digunakan untuk seminar prodi",
            },
        ]

        for jp in JADWAL_PENGGANTI_DATA:
            mk    = mk_map.get(jp["kode_mk"])
            dosen = users_by_nim.get(jp["dosen_nidn"])
            if not mk or not dosen:
                continue
            ex = db.query(JadwalPengganti).filter(
                JadwalPengganti.matakuliah_id == mk.id,
                JadwalPengganti.pertemuan_ke  == jp["pertemuan_ke"],
            ).first()
            if not ex:
                mode_icon = {"online": "💻", "offline": "📍", None: "📋"}[jp.get("mode")]
                db.add(JadwalPengganti(
                    matakuliah_id    = mk.id,
                    dosen_id         = dosen.id,
                    pertemuan_ke     = jp["pertemuan_ke"],
                    jam_mulai_baru   = jp["jam_mulai_baru"],
                    jam_selesai_baru = jp["jam_selesai_baru"],
                    ruangan_baru     = jp["ruangan_baru"],
                    mode             = jp.get("mode"),
                    keterangan       = jp["keterangan"],
                ))
                print(f"  ✓ {mode_icon} {jp['kode_mk']} Ptm-{jp['pertemuan_ke']:02d}: {jp['keterangan'][:55]}...")
        db.flush()

        # ── [7] SESI HISTORIS ─────────────────────────────────────
        print("\n[7/11] Sesi Presensi Historis (Fase 1–9)...")
        sesi_map: dict = {}

        def hari_mulai_dt(hari_nama: str, minggu_ke: int, jam: time) -> datetime:
            """Tanggal sesi untuk minggu ke-N semester ini (mulai 2 Mar 2026)."""
            base = {
                "Senin" : datetime(2026, 3, 2),
                "Selasa": datetime(2026, 3, 3),
                "Rabu"  : datetime(2026, 3, 4),
                "Kamis" : datetime(2026, 3, 5),
                "Jumat" : datetime(2026, 3, 6),
                "Sabtu" : datetime(2026, 3, 7),
            }
            tgl = base[hari_nama] + timedelta(weeks=minggu_ke - 1)
            return tgl.replace(hour=jam.hour, minute=jam.minute + random.randint(0, 8))

        # Buat 9 pertemuan historis untuk setiap MK (kelas pertama sebagai basis)
        sesi_historis = []
        for mk_data in MATAKULIAH_DATA:
            kls0        = mk_data["kelas"][0]
            hari        = kls0["hari"]
            jam_buka    = SLOT_JAM[kls0["slot_m"]][0]
            jam_tutup   = SLOT_JAM[kls0["slot_s"]][1]
            dosen_nidn  = kls0["dosen_nidn"]

            for ptm in range(1, 10):
                # 25% sesi online, 75% offline — lebih variatif
                mode = SesiMode.online if random.random() < 0.25 else SesiMode.offline
                batas_pilihan = [10, 15, 15, 20, None]  # None = tanpa batas
                sesi_historis.append({
                    "kode_mk"    : mk_data["kode"],
                    "dosen_nidn" : dosen_nidn,
                    "mode"       : mode,
                    "pertemuan"  : ptm,
                    "hari"       : hari,
                    "jam_buka"   : jam_buka,
                    "jam_tutup"  : jam_tutup,
                    "batas_menit": random.choice(batas_pilihan),
                    "minggu_ke"  : ptm,
                })

        sesi_count = 0
        for s_def in sesi_historis:
            mk    = mk_map.get(s_def["kode_mk"])
            dosen = users_by_nim.get(s_def["dosen_nidn"])
            if not mk or not dosen:
                continue

            ex = db.query(SesiPresensi).filter(
                SesiPresensi.matakuliah_id == mk.id,
                SesiPresensi.dosen_id      == dosen.id,
                SesiPresensi.pertemuan_ke  == s_def["pertemuan"],
            ).first()
            if ex:
                sesi_map[(s_def["kode_mk"], s_def["pertemuan"])] = ex
                continue

            dt_buka  = hari_mulai_dt(s_def["hari"], s_def["minggu_ke"], s_def["jam_buka"])
            dt_tutup = hari_mulai_dt(s_def["hari"], s_def["minggu_ke"], s_def["jam_tutup"])
            buka_utc  = utc_from_wib(dt_buka.year,  dt_buka.month,  dt_buka.day,  dt_buka.hour,  dt_buka.minute)
            tutup_utc = utc_from_wib(dt_tutup.year, dt_tutup.month, dt_tutup.day, dt_tutup.hour, dt_tutup.minute)

            batas = timedelta(minutes=s_def["batas_menit"]) if s_def["batas_menit"] is not None else None

            kode_sesi = rand_kode() if s_def["mode"] == SesiMode.online else None
            kode_exp  = (buka_utc + timedelta(minutes=90)) if kode_sesi else None

            sesi = SesiPresensi(
                matakuliah_id  = mk.id,
                dosen_id       = dosen.id,
                mode           = s_def["mode"],
                kode_sesi      = kode_sesi,
                kode_expire_at = kode_exp,
                pertemuan_ke   = s_def["pertemuan"],
                waktu_buka     = buka_utc,
                waktu_tutup    = tutup_utc,
                batas_terlambat= batas,
                status         = SesiStatus.selesai,
            )
            db.add(sesi)
            db.flush()
            sesi_map[(s_def["kode_mk"], s_def["pertemuan"])] = sesi
            sesi_count += 1

        db.flush()
        print(f"  → {sesi_count} sesi historis baru")

        # ── [8] DATA PRESENSI ─────────────────────────────────────
        print("\n[8/11] Data Presensi (distribusi realistis)...")
        presensi_count = 0
        ku_count       = 0

        for (kode_mk, pertemuan), sesi in sesi_map.items():
            if sesi.status != SesiStatus.selesai:
                continue

            mk = mk_map.get(kode_mk)
            if not mk:
                continue

            enrollments = db.query(MahasiswaMatakuliah).filter(
                MahasiswaMatakuliah.matakuliah_id == mk.id
            ).all()

            buka_utc = sesi.waktu_buka
            if buka_utc.tzinfo is None:
                buka_utc = buka_utc.replace(tzinfo=timezone.utc)

            for enroll in enrollments:
                ex_p = db.query(Presensi).filter(
                    Presensi.mahasiswa_id == enroll.mahasiswa_id,
                    Presensi.sesi_id      == sesi.id,
                ).first()
                if ex_p:
                    continue

                # Distribusi kehadiran realistis:
                # hadir 68%, terlambat 14%, absen 8%, izin 6%, sakit 4%
                r = random.random()
                if r < 0.68:
                    status = PresensiStatus.hadir
                    delta  = random.randint(0, 12)
                elif r < 0.82:
                    status = PresensiStatus.terlambat
                    batas_m = int(sesi.batas_terlambat.total_seconds() // 60) if sesi.batas_terlambat else 15
                    delta  = random.randint(batas_m + 1, batas_m + 28)
                elif r < 0.90:
                    status = PresensiStatus.absen
                    delta  = 0
                elif r < 0.96:
                    status = PresensiStatus.izin
                    delta  = 0
                else:
                    status = PresensiStatus.sakit
                    delta  = 0

                waktu_p = None
                akurasi = None
                lat, lng = None, None

                if status in (PresensiStatus.hadir, PresensiStatus.terlambat):
                    waktu_p = (buka_utc + timedelta(minutes=delta)).replace(tzinfo=None)
                    akurasi = rand_akurasi()
                    if sesi.mode == SesiMode.offline:
                        r0 = ruangan_map.get(mk.ruangan)
                        if r0 and r0.koordinat_lat:
                            lat = r0.koordinat_lat + random.uniform(-0.0003, 0.0003)
                            lng = r0.koordinat_lng + random.uniform(-0.0003, 0.0003)

                db.add(Presensi(
                    mahasiswa_id   = enroll.mahasiswa_id,
                    sesi_id        = sesi.id,
                    status         = status,
                    waktu_presensi = waktu_p,
                    akurasi_wajah  = akurasi,
                    mode_kelas     = ModeKelas(sesi.mode.value),
                    latitude       = lat,
                    longitude      = lng,
                ))
                presensi_count += 1

                # KodeUsage untuk online
                if sesi.mode == SesiMode.online and status in (PresensiStatus.hadir, PresensiStatus.terlambat):
                    ex_ku = db.query(KodeUsage).filter(
                        KodeUsage.sesi_id      == sesi.id,
                        KodeUsage.mahasiswa_id == enroll.mahasiswa_id,
                    ).first()
                    if not ex_ku:
                        db.add(KodeUsage(
                            sesi_id      = sesi.id,
                            mahasiswa_id = enroll.mahasiswa_id,
                            used_at      = waktu_p,
                        ))
                        ku_count += 1

        db.flush()
        print(f"  → {presensi_count} presensi, {ku_count} kode usage")

        # ── [9] SESI AKTIF (untuk testing real-time) ──────────────
        print("\n[9/11] Sesi Aktif (untuk testing real-time)...")
        SESI_AKTIF_DATA = [
            {
                "kode_mk": "TIF3232209", "dosen_nidn": "0012038901", "kode_kelas": "A",
                "mode": SesiMode.offline, "pertemuan": 10, "buka_menit": 30, "batas_menit": 15,
            },
            {
                "kode_mk": "SI2234567",  "dosen_nidn": "0023047802", "kode_kelas": "A",
                "mode": SesiMode.online,  "pertemuan": 10, "buka_menit": 18, "batas_menit": None,
            },
            {
                "kode_mk": "IK2012201", "dosen_nidn": "0045069504", "kode_kelas": "A",
                "mode": SesiMode.offline, "pertemuan": 10, "buka_menit": 45, "batas_menit": 20,
            },
        ]

        for a_def in SESI_AKTIF_DATA:
            mk    = mk_map.get(a_def["kode_mk"])
            dosen = users_by_nim.get(a_def["dosen_nidn"])
            if not mk or not dosen:
                continue

            ex_aktif = db.query(SesiPresensi).filter(
                SesiPresensi.matakuliah_id == mk.id,
                SesiPresensi.pertemuan_ke  == a_def["pertemuan"],
                SesiPresensi.status        == SesiStatus.aktif,
            ).first()
            if ex_aktif:
                print(f"  ⚠ Skip: {a_def['kode_mk']} Ptm-{a_def['pertemuan']} sudah aktif")
                continue

            waktu_buka = (datetime.now(timezone.utc) - timedelta(minutes=a_def["buka_menit"])).replace(tzinfo=None)
            batas = timedelta(minutes=a_def["batas_menit"]) if a_def["batas_menit"] else None

            kode_sesi = None
            kode_exp  = None
            if a_def["mode"] == SesiMode.online:
                kode_sesi = rand_kode()
                kode_exp  = (datetime.now(timezone.utc) + timedelta(minutes=50)).replace(tzinfo=None)

            sesi_aktif = SesiPresensi(
                matakuliah_id  = mk.id,
                dosen_id       = dosen.id,
                mode           = a_def["mode"],
                kode_sesi      = kode_sesi,
                kode_expire_at = kode_exp,
                pertemuan_ke   = a_def["pertemuan"],
                waktu_buka     = waktu_buka,
                batas_terlambat= batas,
                status         = SesiStatus.aktif,
            )
            db.add(sesi_aktif)
            db.flush()

            mode_icon = "💻" if a_def["mode"] == SesiMode.online else "📍"
            kode_info = f"| Kode: {kode_sesi}" if kode_sesi else ""
            print(f"  ✓ AKTIF {mode_icon} {a_def['kode_mk']} Kelas {a_def['kode_kelas']} Ptm-{a_def['pertemuan']} {kode_info}")

            # Simulasi beberapa mahasiswa sudah hadir di sesi aktif
            kelas_obj = kelas_map.get((a_def["kode_mk"], a_def["kode_kelas"]))
            if kelas_obj:
                enrolled = db.query(MahasiswaMatakuliah).filter(
                    MahasiswaMatakuliah.matakuliah_id == mk.id,
                    MahasiswaMatakuliah.kelas_id      == kelas_obj.id,
                ).all()
                hadir_ratio = random.uniform(0.40, 0.65)
                sudah_hadir = random.sample(enrolled, min(len(enrolled), int(len(enrolled) * hadir_ratio)))
                buka_utc    = datetime.now(timezone.utc) - timedelta(minutes=a_def["buka_menit"])
                batas_m     = a_def.get("batas_menit") or 15

                for enroll in sudah_hadir:
                    delta = random.randint(0, max(a_def["buka_menit"] - 2, 1))
                    st = PresensiStatus.hadir if delta <= batas_m else PresensiStatus.terlambat
                    wp = (buka_utc + timedelta(minutes=delta)).replace(tzinfo=None)
                    lat, lng = None, None
                    if a_def["mode"] == SesiMode.offline:
                        r0 = ruangan_map.get(mk.ruangan)
                        if r0 and r0.koordinat_lat:
                            lat = r0.koordinat_lat + random.uniform(-0.0002, 0.0002)
                            lng = r0.koordinat_lng + random.uniform(-0.0002, 0.0002)
                    db.add(Presensi(
                        mahasiswa_id   = enroll.mahasiswa_id,
                        sesi_id        = sesi_aktif.id,
                        status         = st,
                        waktu_presensi = wp,
                        akurasi_wajah  = rand_akurasi(),
                        mode_kelas     = ModeKelas(a_def["mode"].value),
                        latitude       = lat,
                        longitude      = lng,
                    ))
                    if a_def["mode"] == SesiMode.online:
                        db.add(KodeUsage(
                            sesi_id      = sesi_aktif.id,
                            mahasiswa_id = enroll.mahasiswa_id,
                            used_at      = wp,
                        ))
                db.flush()
                print(f"    → {len(sudah_hadir)} mhs sudah presensi di sesi aktif")

        # ── [10] KONFIGURASI SISTEM (Fase E) ──────────────────────
        print("\n[10/11] Konfigurasi Sistem (Fase E)...")
        for kfg in KONFIGURASI_DEFAULT:
            ex = db.query(KonfigurasiSistem).filter(
                KonfigurasiSistem.key == kfg["key"]
            ).first()
            if not ex:
                db.add(KonfigurasiSistem(**kfg))
                print(f"  ✓ {kfg['key']:<25} = {kfg['value']}")
        db.flush()

        # ── [11] AUDIT LOG ────────────────────────────────────────
        print("\n[11/11] Audit Log (contoh aktivitas)...")
        super_admin = users_by_nim.get("SUPERADMIN")
        admin1      = users_by_nim.get("ADMIN001")

        if super_admin:
            audit_entries = [
                ("SEED_DATABASE",       "system",           None,                  "Seed data awal database v3.5.0"),
                ("CREATE_PROGRAM_STUDI","program_studi",    None,                  f"{len(prodi_map)} program studi diinsert"),
                ("CREATE_RUANGAN",      "ruangan",          None,                  f"{len(ruangan_map)} ruangan diinsert"),
                ("UPDATE_KONFIGURASI",  "konfigurasi_sistem","face_threshold",     "face_threshold diset ke 0.9"),
                ("BUAT_ADMIN",          "users",            "ADMIN001",            "Buat akun Admin Fakultas FKI"),
            ]
            for aksi, entitas, eid, detail in audit_entries:
                db.add(AuditLog(
                    admin_id   = super_admin.id,
                    aksi       = aksi,
                    entitas    = entitas,
                    entitas_id = eid,
                    detail     = detail,
                    ip_address = "127.0.0.1",
                ))
            print(f"  ✓ {len(audit_entries)} audit log dari Super Admin")

        if admin1:
            audit_admin = [
                ("CREATE_USER",         "users",            "H071211001",          "Tambah mahasiswa Muhammad Rizky Pratama"),
                ("ENROLL_MAHASISWA",    "enrollment",       "TIF3232209",          "Bulk enroll 10 mahasiswa ke TIF3232209"),
                ("UPDATE_MATAKULIAH",   "matakuliah",       "TIF3232209",          "Update jadwal TIF3232209: tambah kelas B"),
                ("RESET_FACE",          "users",            "H071221003",          "Reset data wajah mahasiswa Jovan Aldriansyah"),
            ]
            for aksi, entitas, eid, detail in audit_admin:
                db.add(AuditLog(
                    admin_id   = admin1.id,
                    aksi       = aksi,
                    entitas    = entitas,
                    entitas_id = eid,
                    detail     = detail,
                    ip_address = "10.0.1.55",
                ))
            print(f"  ✓ {len(audit_admin)} audit log dari Admin FKI")
        db.flush()

        # ── COMMIT ────────────────────────────────────────────────
        db.commit()

        # ── RINGKASAN ─────────────────────────────────────────────
        from sqlalchemy import func as sqfunc
        total_sesi      = db.query(SesiPresensi).count()
        total_aktif     = db.query(SesiPresensi).filter(SesiPresensi.status == SesiStatus.aktif).count()
        total_presensi  = db.query(Presensi).count()
        total_enroll    = db.query(MahasiswaMatakuliah).count()
        total_kelas_db  = db.query(KelasMatakuliah).count()
        total_ruangan   = db.query(Ruangan).count()
        total_jp        = db.query(JadwalPengganti).count()

        print("\n" + "=" * 72)
        print("  ✅  SEED BERHASIL — Backend v3.5.0 (Fase A–E + B-1)")
        print("=" * 72)
        print(f"""
  Data yang di-insert/tersedia:
  ├── Program Studi    : {len(prodi_map)} prodi (S1, D3, S2)
  ├── Super Admin      : 1 akun
  ├── Admin Fakultas   : {len(ADMIN_DATA)} akun
  ├── Dosen            : {len(DOSEN_DATA)} akun
  ├── Mahasiswa        : {len(MAHASISWA_DATA)} akun
  ├── Ruangan          : {total_ruangan} (kuliah, lab, seminar)
  ├── Matakuliah       : {len(mk_map)} MK
  ├── Kelas            : {total_kelas_db} kelas per MK
  ├── Enrollment       : {total_enroll} record (asli + tamu)
  ├── Jadwal Pengganti : {total_jp} (termasuk field mode Fase B-1)
  ├── Sesi Presensi    : {total_sesi} ({total_aktif} aktif sekarang)
  └── Data Presensi    : {total_presensi} record
        """)

        print("  ─── Akun Login ─────────────────────────────────────────────")
        print("  Password semua akun: Password123!")
        print()
        print("  [Super Admin — IT Kampus]")
        print("   NIM/NIDN : SUPERADMIN")
        print()
        print("  [Admin Fakultas]")
        for a in ADMIN_DATA:
            print(f"   {a['nim_nidn']:<10}  {a['nama_lengkap']}")
        print()
        print("  [Dosen (sample)]")
        for d in DOSEN_DATA[:5]:
            print(f"   {d['nim_nidn']:<14}  {d['nama_lengkap']}")
        print()
        print("  [Mahasiswa (sample)]")
        samples = [
            ("H071211001", "Muhammad Rizky Pratama",    "TIF 2021"),
            ("H071221001", "Hafizh Yusuf Kurniawan",    "TIF 2022"),
            ("H071411001", "Maya Anggraeni Susanti",    "SI 2021"),
            ("H071311001", "Bintang Ramadhan Putra",    "IK 2021"),
            ("H071511001", "Leonardo Devano Putra",     "TK 2021"),
            ("H071641001", "Vira Claudia Santoso",      "MI 2022"),
            ("H071711001", "Ardiansyah Syaiful",        "EL 2021"),
            ("H071851001", "Firda Amalia Putri",        "MM 2022"),
        ]
        for nim, nama, prodi in samples:
            print(f"   {nim:<14}  {nama:<30} ({prodi})")

        # Sesi online aktif
        aktif_online = db.query(SesiPresensi).filter(
            SesiPresensi.status    == SesiStatus.aktif,
            SesiPresensi.kode_sesi.isnot(None),
        ).all()
        if aktif_online:
            print()
            print("  ─── Kode Sesi Online Aktif ──────────────────────────────")
            for s in aktif_online:
                mk = next((v for v in mk_map.values() if v.id == s.matakuliah_id), None)
                nama_mk = mk.nama[:35] if mk else "?"
                print(f"   {s.kode_sesi}  →  {nama_mk}")

        print()
        print("  ─── Konfigurasi Sistem ──────────────────────────────────")
        for kfg in KONFIGURASI_DEFAULT:
            print(f"   {kfg['key']:<26} = {kfg['value']}")

        print()
        print("  ─── Jadwal Pengganti dengan Mode (Fase B-1) ────────────")
        jp_daftar = db.query(JadwalPengganti).all()
        for jp in jp_daftar:
            mk = next((v for v in mk_map.values() if v.id == jp.matakuliah_id), None)
            mode_str = jp.mode or "(mode tidak berubah)"
            print(f"   {mk.kode if mk else '?'} Ptm-{jp.pertemuan_ke:02d}: mode={mode_str}")

        print()
        print("=" * 72)

    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed()