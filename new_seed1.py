"""
seed_lengkap.py — Seed Data Lengkap & Realistis (Fase A–E)
===========================================================
Jalankan: python seed_lengkap.py

Mencakup:
  Fase 0 : 1 Super Admin + 3 Admin Fakultas
  Fase 1 : 8 Dosen (berbagai prodi)
  Fase 2 : 60 Mahasiswa (berbagai prodi & angkatan)
  Fase A : 20 Ruangan Kuliah (kuliah, lab, seminar) + koordinat GPS
  Fase D : 6 Program Studi terstruktur
  Fase B : 10 Matakuliah + Kelas per MK (A, B, C) + enrollment per kelas
  Fase 3 : Jadwal Pengganti
  Fase 4 : 40 Sesi Presensi (offline & online, selesai & aktif)
  Fase 5 : Data Presensi lengkap (hadir, terlambat, absen, izin, sakit)
  Fase 6 : KodeUsage untuk sesi online
  Fase E : Konfigurasi Sistem (5 default config)
  Lain   : FaceEmbedding placeholder + AuditLog contoh

Password semua akun: Password123!
"""

import uuid
import random
import secrets
import string
from datetime import datetime, timedelta, time, timezone, date
from zoneinfo import ZoneInfo

from app.database.db import SessionLocal, engine, Base
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
    return round(random.uniform(78.0, 98.5), 2)


def rand_kode():
    chars = (string.ascii_uppercase + string.digits).translate(
        str.maketrans("", "", "OI0L1")
    )
    return "".join(secrets.choice(chars) for _ in range(6))


def pw():
    return hash_password("Password123!")


# ═══════════════════════════════════════════════════════════════
# DATA DEFINITIONS
# ═══════════════════════════════════════════════════════════════

# ── PROGRAM STUDI ─────────────────────────────────────────────
PROGRAM_STUDI_DATA = [
    {
        "kode"    : "TIF",
        "nama"    : "Teknik Informatika",
        "fakultas": "Fakultas Komunikasi dan Informatika",
        "jenjang" : "S1",
    },
    {
        "kode"    : "SI",
        "nama"    : "Sistem Informasi",
        "fakultas": "Fakultas Komunikasi dan Informatika",
        "jenjang" : "S1",
    },
    {
        "kode"    : "IK",
        "nama"    : "Ilmu Komputer",
        "fakultas": "Fakultas Komunikasi dan Informatika",
        "jenjang" : "S1",
    },
    {
        "kode"    : "TK",
        "nama"    : "Teknik Komputer",
        "fakultas": "Fakultas Teknik",
        "jenjang" : "S1",
    },
    {
        "kode"    : "MI",
        "nama"    : "Manajemen Informatika",
        "fakultas": "Fakultas Komunikasi dan Informatika",
        "jenjang" : "D3",
    },
    {
        "kode"    : "TIF-S2",
        "nama"    : "Magister Teknik Informatika",
        "fakultas": "Fakultas Komunikasi dan Informatika",
        "jenjang" : "S2",
    },
]

# ── USERS ─────────────────────────────────────────────────────
SUPER_ADMIN_DATA = {
    "nim_nidn"     : "SUPERADMIN",
    "nama_lengkap" : "Wahyu Eko Putranto, S.T., M.T.",
    "email"        : "superadmin@unhas.ac.id",
    "role"         : UserRole.super_admin,
    "program_studi": "Divisi IT Kampus",
}

ADMIN_DATA = [
    {
        "nim_nidn"     : "ADMIN001",
        "nama_lengkap" : "Dr. Andi Mappangaja, S.Kom., M.M.",
        "email"        : "admin.fki@unhas.ac.id",
        "role"         : UserRole.admin,
        "program_studi": "Fakultas Komunikasi dan Informatika",
    },
    {
        "nim_nidn"     : "ADMIN002",
        "nama_lengkap" : "Hj. Rahmawati Usman, S.Pd., M.Si.",
        "email"        : "admin.ft@unhas.ac.id",
        "role"         : UserRole.admin,
        "program_studi": "Fakultas Teknik",
    },
    {
        "nim_nidn"     : "ADMIN003",
        "nama_lengkap" : "Muh. Syahril Ramadhan, A.Md.",
        "email"        : "admin.akademik@unhas.ac.id",
        "role"         : UserRole.admin,
        "program_studi": "Biro Administrasi Akademik",
    },
]

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
]

MAHASISWA_DATA = [
    # ── Teknik Informatika 2021 ──────────────────────────────
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
    # ── Teknik Informatika 2022 ──────────────────────────────
    ("H071221001", "Hafizh Yusuf Kurniawan",       "hafizh.kurniawan22@student.unhas.ac.id", "TIF", 2022),
    ("H071221002", "Indira Cahyaningrum",          "indira.cahya22@student.unhas.ac.id",     "TIF", 2022),
    ("H071221003", "Jovan Aldriansyah",            "jovan.aldrian22@student.unhas.ac.id",    "TIF", 2022),
    ("H071221004", "Keisya Aurelia Putri",         "keisya.aurelia22@student.unhas.ac.id",   "TIF", 2022),
    ("H071221005", "Luthfi Hakim Ardiansyah",      "luthfi.hakim22@student.unhas.ac.id",     "TIF", 2022),
    # ── Teknik Informatika 2023 ──────────────────────────────
    ("H071231001", "Miftahul Jannah Basri",        "miftah.basri23@student.unhas.ac.id",     "TIF", 2023),
    ("H071231002", "Nabil Rachmat Hidayat",        "nabil.rachmat23@student.unhas.ac.id",    "TIF", 2023),
    ("H071231003", "Olivia Setiawati",             "olivia.setiawati23@student.unhas.ac.id", "TIF", 2023),
    ("H071231004", "Panji Surya Kencana",          "panji.surya23@student.unhas.ac.id",      "TIF", 2023),
    ("H071231005", "Qonita Azizah Mansur",         "qonita.mansur23@student.unhas.ac.id",    "TIF", 2023),
    # ── Sistem Informasi 2021 ────────────────────────────────
    ("H071411001", "Maya Anggraeni Susanti",       "maya.anggraeni21@student.unhas.ac.id",   "SI", 2021),
    ("H071411002", "Naufal Dzikri Fauzan",         "naufal.fauzan21@student.unhas.ac.id",    "SI", 2021),
    ("H071411003", "Olivia Kurnia Dewi",           "olivia.kurnia21@student.unhas.ac.id",    "SI", 2021),
    ("H071411004", "Prasetyo Wibowo Nugroho",      "prasetyo.wibowo21@student.unhas.ac.id",  "SI", 2021),
    ("H071411005", "Qisthi Ramadhani",             "qisthi.ramadhani21@student.unhas.ac.id", "SI", 2021),
    ("H071411006", "Rafli Akbar Suhaimi",          "rafli.suhaimi21@student.unhas.ac.id",    "SI", 2021),
    ("H071411007", "Salsabila Nur Izzati",         "salsabila.izzati21@student.unhas.ac.id", "SI", 2021),
    ("H071411008", "Taufiq Hidayatullah",          "taufiq.hidayat21@student.unhas.ac.id",   "SI", 2021),
    ("H071411009", "Ulfa Maulidya Rahma",          "ulfa.rahma21@student.unhas.ac.id",       "SI", 2021),
    ("H071411010", "Vicky Ardiansyah",             "vicky.ardiansyah21@student.unhas.ac.id", "SI", 2021),
    # ── Sistem Informasi 2022 ────────────────────────────────
    ("H071421001", "Widya Astuti Ramadhani",       "widya.astuti22@student.unhas.ac.id",     "SI", 2022),
    ("H071421002", "Xaverius Bintang Pradana",     "xaverius.pradana22@student.unhas.ac.id", "SI", 2022),
    ("H071421003", "Yasmin Aulia Salsabila",       "yasmin.salsabila22@student.unhas.ac.id", "SI", 2022),
    ("H071421004", "Zaidan Farel Pratama",         "zaidan.farel22@student.unhas.ac.id",     "SI", 2022),
    ("H071421005", "Adinda Puspa Maharani",        "adinda.puspa22@student.unhas.ac.id",     "SI", 2022),
    # ── Ilmu Komputer 2021 ───────────────────────────────────
    ("H071311001", "Bintang Ramadhan Putra",       "bintang.putra21@student.unhas.ac.id",    "IK", 2021),
    ("H071311002", "Chelsea Amanda Pratiwi",       "chelsea.pratiwi21@student.unhas.ac.id",  "IK", 2021),
    ("H071311003", "Daffa Arya Wicaksono",         "daffa.wicaksono21@student.unhas.ac.id",  "IK", 2021),
    ("H071311004", "Eka Putri Handayani",          "eka.handayani21@student.unhas.ac.id",    "IK", 2021),
    ("H071311005", "Farhan Septian Nugroho",       "farhan.septian21@student.unhas.ac.id",   "IK", 2021),
    # ── Ilmu Komputer 2022 ───────────────────────────────────
    ("H071321001", "Gilang Ramadhan Sanjaya",      "gilang.sanjaya22@student.unhas.ac.id",   "IK", 2022),
    ("H071321002", "Hana Salsabila Anwar",         "hana.anwar22@student.unhas.ac.id",       "IK", 2022),
    ("H071321003", "Ilham Syahputra",              "ilham.syahputra22@student.unhas.ac.id",  "IK", 2022),
    ("H071321004", "Jessica Tamara Larasati",      "jessica.larasati22@student.unhas.ac.id", "IK", 2022),
    ("H071321005", "Kevin Ardianto Susilo",        "kevin.susilo22@student.unhas.ac.id",     "IK", 2022),
    # ── Teknik Komputer 2021 ─────────────────────────────────
    ("H071511001", "Leonardo Devano Putra",        "leonardo.devano21@student.unhas.ac.id",  "TK", 2021),
    ("H071511002", "Maulana Ibrahim Hasbi",        "maulana.hasbi21@student.unhas.ac.id",    "TK", 2021),
    ("H071511003", "Nida Ul Hasanah",              "nida.hasanah21@student.unhas.ac.id",     "TK", 2021),
    ("H071511004", "Omar Dzaki Ramdhani",          "omar.dzaki21@student.unhas.ac.id",       "TK", 2021),
    ("H071511005", "Priadi Suryaningrat",          "priadi.surya21@student.unhas.ac.id",     "TK", 2021),
    # ── Teknik Komputer 2022 ─────────────────────────────────
    ("H071521001", "Qurrotu Aini Latifah",         "qurrotu.aini22@student.unhas.ac.id",     "TK", 2022),
    ("H071521002", "Raka Pratama Wijaya",          "raka.pratama22@student.unhas.ac.id",     "TK", 2022),
    ("H071521003", "Syifa Nur Rahmadani",          "syifa.nur22@student.unhas.ac.id",        "TK", 2022),
    ("H071521004", "Taofik Hidayat Permana",       "taofik.hidayat22@student.unhas.ac.id",   "TK", 2022),
    ("H071521005", "Ulfah Kharisma Dewi",          "ulfah.kharisma22@student.unhas.ac.id",   "TK", 2022),
    # ── Manajemen Informatika 2022 ───────────────────────────
    ("H071641001", "Vira Claudia Santoso",         "vira.claudia22@student.unhas.ac.id",     "MI", 2022),
    ("H071641002", "Wahyu Tri Atmaja",             "wahyu.atmaja22@student.unhas.ac.id",     "MI", 2022),
    ("H071641003", "Xenofon Ariel Manuela",        "xenofon.ariel22@student.unhas.ac.id",    "MI", 2022),
    ("H071641004", "Yovita Ratna Kumala",          "yovita.ratna22@student.unhas.ac.id",     "MI", 2022),
    ("H071641005", "Zafira Khairunnisa",           "zafira.khairunnisa22@student.unhas.ac.id","MI", 2022),
]

# ── RUANGAN ───────────────────────────────────────────────────
# Koordinat GPS sekitar Kampus Unhas Tamalanrea, Makassar
RUANGAN_DATA = [
    # --- Ruang Kuliah ---
    {"kode": "J.Int.1",  "nama": "Ruang Kuliah J International 1", "tipe": "kuliah",  "kapasitas": 45, "gedung": "Gedung J",  "lantai": 1, "lat": -5.130245, "lng": 119.489432},
    {"kode": "J.Int.2",  "nama": "Ruang Kuliah J International 2", "tipe": "kuliah",  "kapasitas": 45, "gedung": "Gedung J",  "lantai": 1, "lat": -5.130280, "lng": 119.489500},
    {"kode": "J0403",    "nama": "Ruang Kuliah J Lantai 4 No.3",   "tipe": "kuliah",  "kapasitas": 40, "gedung": "Gedung J",  "lantai": 4, "lat": -5.130100, "lng": 119.489350},
    {"kode": "J0407",    "nama": "Ruang Kuliah J Lantai 4 No.7",   "tipe": "kuliah",  "kapasitas": 40, "gedung": "Gedung J",  "lantai": 4, "lat": -5.130120, "lng": 119.489380},
    {"kode": "J0408",    "nama": "Ruang Kuliah J Lantai 4 No.8",   "tipe": "kuliah",  "kapasitas": 40, "gedung": "Gedung J",  "lantai": 4, "lat": -5.130140, "lng": 119.489410},
    {"kode": "SW706",    "nama": "Ruang Kuliah SW Lantai 7 No.6",  "tipe": "kuliah",  "kapasitas": 50, "gedung": "Gedung SW", "lantai": 7, "lat": -5.132451, "lng": 119.491380},
    {"kode": "SW708",    "nama": "Ruang Kuliah SW Lantai 7 No.8",  "tipe": "kuliah",  "kapasitas": 50, "gedung": "Gedung SW", "lantai": 7, "lat": -5.132480, "lng": 119.491420},
    {"kode": "C-202",    "nama": "Ruang Kuliah C Lantai 2 No.2",   "tipe": "kuliah",  "kapasitas": 35, "gedung": "Gedung C",  "lantai": 2, "lat": -5.131100, "lng": 119.490271},
    {"kode": "C-204",    "nama": "Ruang Kuliah C Lantai 2 No.4",   "tipe": "kuliah",  "kapasitas": 35, "gedung": "Gedung C",  "lantai": 2, "lat": -5.131140, "lng": 119.490310},
    # --- Lab ---
    {"kode": "LABRPL",   "nama": "Lab Rekayasa Perangkat Lunak",   "tipe": "lab",     "kapasitas": 30, "gedung": "Gedung J",  "lantai": 2, "lat": -5.130873, "lng": 119.488950},
    {"kode": "LSITIF",   "nama": "Lab Sistem Terdistribusi & Jaringan", "tipe": "lab", "kapasitas": 28, "gedung": "Gedung J",  "lantai": 2, "lat": -5.130890, "lng": 119.489010},
    {"kode": "LJKTIF",   "nama": "Lab Jaringan Komputer TIF",      "tipe": "lab",     "kapasitas": 30, "gedung": "Gedung J",  "lantai": 3, "lat": -5.130620, "lng": 119.488800},
    {"kode": "LABAI",    "nama": "Lab Kecerdasan Artifisial",      "tipe": "lab",     "kapasitas": 25, "gedung": "Gedung J",  "lantai": 3, "lat": -5.130650, "lng": 119.488840},
    {"kode": "LABDB",    "nama": "Lab Basis Data",                 "tipe": "lab",     "kapasitas": 30, "gedung": "Gedung C",  "lantai": 1, "lat": -5.131340, "lng": 119.490800},
    {"kode": "LABMOBILE","nama": "Lab Mobile Computing",           "tipe": "lab",     "kapasitas": 25, "gedung": "Gedung C",  "lantai": 1, "lat": -5.131380, "lng": 119.490840},
    {"kode": "LABHW",    "nama": "Lab Hardware & Embedded Systems", "tipe": "lab",    "kapasitas": 24, "gedung": "Gedung SW", "lantai": 3, "lat": -5.132120, "lng": 119.491000},
    # --- Seminar / Aula ---
    {"kode": "JSEM1",    "nama": "Aula Seminar J Lantai 1",        "tipe": "seminar", "kapasitas": 150,"gedung": "Gedung J",  "lantai": 1, "lat": -5.130400, "lng": 119.489600},
    {"kode": "JSEM2",    "nama": "Ruang Sidang J Lantai 2",        "tipe": "seminar", "kapasitas": 60, "gedung": "Gedung J",  "lantai": 2, "lat": -5.130450, "lng": 119.489650},
    {"kode": "RVL200",   "nama": "Ruang Vicon & Livestream",       "tipe": "seminar", "kapasitas": 40, "gedung": "Gedung SW", "lantai": 2, "lat": -5.132200, "lng": 119.491100},
    {"kode": "AULA-FKI", "nama": "Aula Utama FKI",                "tipe": "seminar", "kapasitas": 300,"gedung": "Gedung FKI","lantai": 1, "lat": -5.129800, "lng": 119.488500},
]

# ── MATAKULIAH ────────────────────────────────────────────────
# Format: (kode, nama, sks, dosen_nidn_utama)
MATAKULIAH_DATA = [
    {
        "kode"       : "TIF3221308",
        "nama"       : "Logika dan Himpunan",
        "sks"        : 3,
        "dosen_nidn" : "0031056703",   # Hendra Gunawan
        "prodi"      : "TIF",
        "izin_tamu"  : False,
        # Kelas A & B (hari berbeda)
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0031056703", "ruangan_kode": "J.Int.1", "hari": "Senin",  "slot_mulai": 1, "slot_selesai": 3},
            {"kode_kelas": "B", "dosen_nidn": "0012038901", "ruangan_kode": "J0403",   "hari": "Selasa", "slot_mulai": 1, "slot_selesai": 3},
            {"kode_kelas": "C", "dosen_nidn": "0056078405", "ruangan_kode": "J.Int.2", "hari": "Rabu",   "slot_mulai": 4, "slot_selesai": 6},
        ],
    },
    {
        "kode"       : "TIF3232209",
        "nama"       : "Pemrograman Mobile",
        "sks"        : 3,
        "dosen_nidn" : "0012038901",   # Budi Santoso
        "prodi"      : "TIF",
        "izin_tamu"  : True,
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0012038901", "ruangan_kode": "LABMOBILE", "hari": "Senin",  "slot_mulai": 7, "slot_selesai": 9},
            {"kode_kelas": "B", "dosen_nidn": "0056078405", "ruangan_kode": "LABMOBILE", "hari": "Kamis",  "slot_mulai": 7, "slot_selesai": 9},
        ],
    },
    {
        "kode"       : "TIF4011401",
        "nama"       : "Kecerdasan Buatan",
        "sks"        : 3,
        "dosen_nidn" : "0031056703",
        "prodi"      : "TIF",
        "izin_tamu"  : True,
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0031056703", "ruangan_kode": "LABAI",  "hari": "Rabu",   "slot_mulai": 1, "slot_selesai": 3},
            {"kode_kelas": "B", "dosen_nidn": "0045069504", "ruangan_kode": "LABAI",  "hari": "Jumat",  "slot_mulai": 4, "slot_selesai": 6},
        ],
    },
    {
        "kode"       : "TIF3222101",
        "nama"       : "Basis Data Lanjut",
        "sks"        : 3,
        "dosen_nidn" : "0023047802",   # Siti Rahayu
        "prodi"      : "TIF",
        "izin_tamu"  : False,
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0023047802", "ruangan_kode": "LABDB",  "hari": "Selasa", "slot_mulai": 7, "slot_selesai": 9},
            {"kode_kelas": "B", "dosen_nidn": "0012038901", "ruangan_kode": "LABDB",  "hari": "Kamis",  "slot_mulai": 1, "slot_selesai": 3},
        ],
    },
    {
        "kode"       : "TIF2011301",
        "nama"       : "Pemrograman Berorientasi Objek",
        "sks"        : 3,
        "dosen_nidn" : "0012038901",
        "prodi"      : "TIF",
        "izin_tamu"  : False,
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0012038901", "ruangan_kode": "LABRPL",  "hari": "Rabu",   "slot_mulai": 7, "slot_selesai": 9},
            {"kode_kelas": "B", "dosen_nidn": "0056078405", "ruangan_kode": "LABRPL",  "hari": "Jumat",  "slot_mulai": 1, "slot_selesai": 3},
            {"kode_kelas": "C", "dosen_nidn": "0045069504", "ruangan_kode": "J0407",   "hari": "Senin",  "slot_mulai": 4, "slot_selesai": 6},
        ],
    },
    {
        "kode"       : "SI2234567",
        "nama"       : "Sistem Informasi Manajemen",
        "sks"        : 3,
        "dosen_nidn" : "0023047802",
        "prodi"      : "SI",
        "izin_tamu"  : False,
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0023047802", "ruangan_kode": "SW706",   "hari": "Kamis",  "slot_mulai": 1, "slot_selesai": 3},
            {"kode_kelas": "B", "dosen_nidn": "0067087306", "ruangan_kode": "SW708",   "hari": "Jumat",  "slot_mulai": 7, "slot_selesai": 9},
        ],
    },
    {
        "kode"       : "SI3013301",
        "nama"       : "Analisis dan Desain Sistem",
        "sks"        : 3,
        "dosen_nidn" : "0067087306",
        "prodi"      : "SI",
        "izin_tamu"  : True,
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0067087306", "ruangan_kode": "C-202",   "hari": "Jumat",  "slot_mulai": 1, "slot_selesai": 3},
            {"kode_kelas": "B", "dosen_nidn": "0023047802", "ruangan_kode": "C-204",   "hari": "Senin",  "slot_mulai": 10,"slot_selesai": 12},
        ],
    },
    {
        "kode"       : "IK2012201",
        "nama"       : "Algoritma dan Struktur Data",
        "sks"        : 4,
        "dosen_nidn" : "0045069504",
        "prodi"      : "IK",
        "izin_tamu"  : False,
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0045069504", "ruangan_kode": "LSITIF",  "hari": "Senin",  "slot_mulai": 7, "slot_selesai": 10},
            {"kode_kelas": "B", "dosen_nidn": "0089015108", "ruangan_kode": "J0408",   "hari": "Rabu",   "slot_mulai": 4, "slot_selesai": 7},
        ],
    },
    {
        "kode"       : "IK3012301",
        "nama"       : "Jaringan Komputer",
        "sks"        : 3,
        "dosen_nidn" : "0056078405",
        "prodi"      : "IK",
        "izin_tamu"  : True,
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0056078405", "ruangan_kode": "LJKTIF",  "hari": "Rabu",   "slot_mulai": 1, "slot_selesai": 3},
            {"kode_kelas": "B", "dosen_nidn": "0078096207", "ruangan_kode": "LABHW",   "hari": "Kamis",  "slot_mulai": 7, "slot_selesai": 9},
        ],
    },
    {
        "kode"       : "TK2011201",
        "nama"       : "Arsitektur Sistem Komputer",
        "sks"        : 3,
        "dosen_nidn" : "0078096207",
        "prodi"      : "TK",
        "izin_tamu"  : False,
        "kelas": [
            {"kode_kelas": "A", "dosen_nidn": "0078096207", "ruangan_kode": "LABHW",   "hari": "Selasa", "slot_mulai": 4, "slot_selesai": 6},
            {"kode_kelas": "B", "dosen_nidn": "0089015108", "ruangan_kode": "J0408",   "hari": "Jumat",  "slot_mulai": 7, "slot_selesai": 9},
        ],
    },
]

# Slot → (jam_mulai, jam_selesai)
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

HARI_TO_WEEKDAY = {
    "Senin": 0, "Selasa": 1, "Rabu": 2, "Kamis": 3,
    "Jumat": 4, "Sabtu": 5, "Minggu": 6,
}

# ── ENROLLMENT: Prodi → Matakuliah yang diambil ───────────────
# Format: {kode_mk: [(kelas, [nim_mahasiswa])]}
# Akan diisi otomatis di main seed

# ── KONFIGURASI SISTEM ────────────────────────────────────────
KONFIGURASI_DEFAULT = [
    {
        "key"        : "face_threshold",
        "value"      : "0.9",
        "label"      : "Face Recognition Threshold",
        "deskripsi"  : "Euclidean distance threshold untuk verifikasi wajah. Semakin kecil = lebih ketat. Range: 0.1–2.0. Default: 0.9.",
        "tipe"       : "float",
        "nilai_min"  : "0.1",
        "nilai_max"  : "2.0",
        "is_readonly": False,
    },
    {
        "key"        : "geofencing_radius",
        "value"      : "100",
        "label"      : "Radius Geofencing Presensi Offline (meter)",
        "deskripsi"  : "Jarak maksimum antara lokasi mahasiswa dan koordinat kelas. Default: 100m.",
        "tipe"       : "integer",
        "nilai_min"  : "10",
        "nilai_max"  : "500",
        "is_readonly": False,
    },
    {
        "key"        : "timezone",
        "value"      : "Asia/Jakarta",
        "label"      : "Timezone Server",
        "deskripsi"  : "Timezone IANA yang dipakai server. Default: Asia/Jakarta (WIB).",
        "tipe"       : "string",
        "nilai_min"  : None,
        "nilai_max"  : None,
        "is_readonly": False,
    },
    {
        "key"        : "maintenance_mode",
        "value"      : "false",
        "label"      : "Mode Maintenance",
        "deskripsi"  : "Jika 'true', semua endpoint presensi dinonaktifkan. Nilai: true/false.",
        "tipe"       : "boolean",
        "nilai_min"  : None,
        "nilai_max"  : None,
        "is_readonly": False,
    },
    {
        "key"        : "max_foto_registrasi",
        "value"      : "8",
        "label"      : "Jumlah Foto Minimal Registrasi Wajah",
        "deskripsi"  : "Jumlah foto yang harus diambil saat registrasi wajah. Default: 8.",
        "tipe"       : "integer",
        "nilai_min"  : "4",
        "nilai_max"  : "20",
        "is_readonly": False,
    },
]


# ═══════════════════════════════════════════════════════════════
# MAIN SEED
# ═══════════════════════════════════════════════════════════════

def seed():
    db = SessionLocal()
    try:
        print("=" * 70)
        print("  SEED LENGKAP — Presensi Face Recognition v3.4 (Fase A–E)")
        print("=" * 70)

        # ── [1] PROGRAM STUDI ─────────────────────────────────────
        print("\n[1/10] Program Studi...")
        prodi_map = {}
        for data in PROGRAM_STUDI_DATA:
            ex = db.query(ProgramStudi).filter(ProgramStudi.kode == data["kode"]).first()
            if ex:
                prodi_map[data["kode"]] = ex
                continue
            prodi = ProgramStudi(**data, is_active=True)
            db.add(prodi)
            db.flush()
            prodi_map[data["kode"]] = prodi
            print(f"  ✓ {data['kode']} — {data['nama']}")
        db.flush()
        print(f"  → Total: {len(prodi_map)} program studi")

        # ── [2] USERS ─────────────────────────────────────────────
        print("\n[2/10] Users (Super Admin, Admin, Dosen, Mahasiswa)...")
        users_by_nim = {}

        # Super Admin
        all_user_defs = [(SUPER_ADMIN_DATA, None)] + \
                        [(d, None) for d in ADMIN_DATA] + \
                        [(d, d.get("prodi_kode")) for d in DOSEN_DATA]

        for data, prodi_kode in all_user_defs:
            ex = db.query(User).filter(User.nim_nidn == data["nim_nidn"]).first()
            if ex:
                users_by_nim[data["nim_nidn"]] = ex
                continue
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
        for nim, nama, email, prodi_kode, angkatan in MAHASISWA_DATA:
            ex = db.query(User).filter(User.nim_nidn == nim).first()
            if ex:
                users_by_nim[nim] = ex
                continue
            u = User(
                nim_nidn           = nim,
                nama_lengkap       = nama,
                email              = email,
                password_hash      = pw(),
                role               = UserRole.mahasiswa,
                program_studi      = prodi_map[prodi_kode].nama if prodi_kode in prodi_map else prodi_kode,
                program_studi_id   = prodi_map[prodi_kode].id if prodi_kode in prodi_map else None,
                is_face_registered = True,   # anggap sudah daftar wajah
                is_active          = True,
            )
            db.add(u)
            db.flush()
            users_by_nim[nim] = u

        db.flush()
        total_users = db.query(User).count()
        print(f"  → Total users di DB: {total_users}")

        # ── [3] RUANGAN ───────────────────────────────────────────
        print("\n[3/10] Ruangan...")
        ruangan_map = {}
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
            tipe_badge = {"kuliah": "📚", "lab": "🖥️", "seminar": "🎤"}.get(r["tipe"], "🏫")
            print(f"  ✓ {tipe_badge} {r['kode']} — {r['nama']} (kap. {r['kapasitas']})")
        db.flush()
        print(f"  → Total: {len(ruangan_map)} ruangan")

        # ── [4] MATAKULIAH + KELAS ────────────────────────────────
        print("\n[4/10] Matakuliah & Kelas...")
        mk_map   = {}   # kode_mk → Matakuliah
        kelas_map = {}  # (kode_mk, kode_kelas) → KelasMatakuliah

        for mk_data in MATAKULIAH_DATA:
            # Ambil jam reguler dari kelas pertama
            kls0 = mk_data["kelas"][0]
            jam_mulai   = SLOT_JAM[kls0["slot_mulai"]][0]
            jam_selesai = SLOT_JAM[kls0["slot_selesai"]][1]

            ruangan_str = kls0["ruangan_kode"]  # simpan string (backward compat)

            # Cari koordinat GPS dari ruangan kelas pertama
            r0 = ruangan_map.get(ruangan_str)
            lat = r0.koordinat_lat if r0 else None
            lng = r0.koordinat_lng if r0 else None

            ex_mk = db.query(Matakuliah).filter(Matakuliah.kode == mk_data["kode"]).first()
            if not ex_mk:
                mk_obj = Matakuliah(
                    kode          = mk_data["kode"],
                    nama          = mk_data["nama"],
                    sks           = mk_data["sks"],
                    hari          = kls0["hari"],
                    jam_mulai     = jam_mulai,
                    jam_selesai   = jam_selesai,
                    ruangan       = ruangan_str,
                    koordinat_lat = lat,
                    koordinat_lng = lng,
                    izin_tamu     = mk_data["izin_tamu"],
                )
                db.add(mk_obj)
                db.flush()
                print(f"  ✓ {mk_data['kode']} — {mk_data['nama']} ({len(mk_data['kelas'])} kelas)")
            else:
                mk_obj = ex_mk

            mk_map[mk_data["kode"]] = mk_obj

            # Buat kelas-kelas
            for kls_data in mk_data["kelas"]:
                ex_kls = db.query(KelasMatakuliah).filter(
                    KelasMatakuliah.matakuliah_id == mk_obj.id,
                    KelasMatakuliah.kode_kelas    == kls_data["kode_kelas"],
                ).first()
                if ex_kls:
                    kelas_map[(mk_data["kode"], kls_data["kode_kelas"])] = ex_kls
                    continue

                dosen = users_by_nim.get(kls_data["dosen_nidn"])
                ruangan = ruangan_map.get(kls_data["ruangan_kode"])

                kls_obj = KelasMatakuliah(
                    matakuliah_id = mk_obj.id,
                    kode_kelas    = kls_data["kode_kelas"],
                    dosen_id      = dosen.id if dosen else None,
                    ruangan_id    = ruangan.id if ruangan else None,
                    hari          = kls_data["hari"],
                    slot_mulai    = kls_data["slot_mulai"],
                    slot_selesai  = kls_data["slot_selesai"],
                    izin_tamu     = mk_data["izin_tamu"],
                    is_active     = True,
                )
                db.add(kls_obj)
                db.flush()
                kelas_map[(mk_data["kode"], kls_data["kode_kelas"])] = kls_obj

        db.flush()

        # ── [5] ENROLLMENT ────────────────────────────────────────
        print("\n[5/10] Enrollment (Mahasiswa → Kelas)...")
        # Distribusi mahasiswa ke kelas berdasarkan prodi dan angkatan
        enrollment_rules = [
            # TIF3221308 Logika dan Himpunan — semua TIF 2022
            ("TIF3221308", "A", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "TIF" and angk == 2022]),
            ("TIF3221308", "B", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "TIF" and angk == 2021][:8]),
            ("TIF3221308", "C", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "TIF" and angk == 2023]),
            # TIF3232209 Pemrograman Mobile — TIF 2021 kelas A, TIF 2022 kelas B
            ("TIF3232209", "A", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "TIF" and angk == 2021]),
            ("TIF3232209", "B", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "TIF" and angk == 2022]),
            # TIF4011401 Kecerdasan Buatan — TIF 2021 + IK 2021
            ("TIF4011401", "A", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "TIF" and angk == 2021][:8]),
            ("TIF4011401", "B", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "IK" and angk == 2021]),
            # TIF3222101 Basis Data Lanjut — TIF 2021 & 2022
            ("TIF3222101", "A", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "TIF" and angk == 2021]),
            ("TIF3222101", "B", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "TIF" and angk == 2022]),
            # TIF2011301 PBO — TIF 2022 + 2023
            ("TIF2011301", "A", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "TIF" and angk == 2022]),
            ("TIF2011301", "B", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "TIF" and angk == 2023]),
            ("TIF2011301", "C", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "SI" and angk == 2022]),
            # SI2234567 SIM — SI 2021 kelas A, SI 2022 kelas B
            ("SI2234567",  "A", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "SI" and angk == 2021]),
            ("SI2234567",  "B", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "SI" and angk == 2022]),
            # SI3013301 Analisis Desain Sistem — SI 2021
            ("SI3013301",  "A", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "SI" and angk == 2021]),
            ("SI3013301",  "B", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "SI" and angk == 2022]),
            # IK2012201 Algoritma — IK 2021 + 2022
            ("IK2012201",  "A", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "IK" and angk == 2021]),
            ("IK2012201",  "B", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "IK" and angk == 2022]),
            # IK3012301 Jaringan Komputer — IK 2021 + TK 2021
            ("IK3012301",  "A", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "IK" and angk == 2021]),
            ("IK3012301",  "B", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "TK" and angk == 2021]),
            # TK2011201 Arsitektur — TK 2021 + TK 2022
            ("TK2011201",  "A", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "TK" and angk == 2021]),
            ("TK2011201",  "B", [nim for nim, *_, prodi, angk in MAHASISWA_DATA if prodi == "TK" and angk == 2022]),
        ]

        enroll_count = 0
        # Tamu manual: beberapa SI masuk ke kelas TIF (izin_tamu=True)
        TAMU = [
            ("TIF4011401", "A", "H071411001", True),
            ("TIF4011401", "A", "H071411002", True),
            ("TIF3232209", "A", "H071411003", True),
            ("IK3012301",  "A", "H071411004", True),
            ("SI3013301",  "A", "H071211001", True),
        ]

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
                    ))
                    enroll_count += 1

        # Mahasiswa tamu
        for kode_mk, kode_kelas, nim, is_tamu in TAMU:
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
                    kelas_asal    = f"{user.program_studi} — Kelas Reguler",
                ))
                enroll_count += 1

        db.flush()
        print(f"  → Total enrollment: {enroll_count} record")

        # ── [6] JADWAL PENGGANTI ──────────────────────────────────
        print("\n[6/10] Jadwal Pengganti...")
        jadwal_pengganti_list = [
            {
                "kode_mk"        : "TIF3232209",
                "dosen_nidn"     : "0012038901",
                "pertemuan_ke"   : 5,
                "jam_mulai_baru" : time(10, 0),
                "jam_selesai_baru": time(12, 30),
                "ruangan_baru"   : "C-202",
                "keterangan"     : "Ruang Lab Mobile sedang perbaikan AC, pindah ke C-202",
            },
            {
                "kode_mk"        : "TIF3222101",
                "dosen_nidn"     : "0023047802",
                "pertemuan_ke"   : 8,
                "jam_mulai_baru" : time(10, 0),
                "jam_selesai_baru": time(12, 30),
                "ruangan_baru"   : None,
                "keterangan"     : "Dosen ada jadwal rapat pimpinan, kelas dimajukan ke siang",
            },
            {
                "kode_mk"        : "SI2234567",
                "dosen_nidn"     : "0023047802",
                "pertemuan_ke"   : 3,
                "jam_mulai_baru" : None,
                "jam_selesai_baru": None,
                "ruangan_baru"   : "AULA-FKI",
                "keterangan"     : "Kuliah tamu dari industri — dipindah ke Aula FKI",
            },
            {
                "kode_mk"        : "TIF4011401",
                "dosen_nidn"     : "0031056703",
                "pertemuan_ke"   : 10,
                "jam_mulai_baru" : time(13, 0),
                "jam_selesai_baru": time(15, 30),
                "ruangan_baru"   : "JSEM1",
                "keterangan"     : "Presentasi tugas besar — ruang diperbesar ke Aula J",
            },
        ]

        for jp in jadwal_pengganti_list:
            mk    = mk_map.get(jp["kode_mk"])
            dosen = users_by_nim.get(jp["dosen_nidn"])
            if not mk or not dosen:
                continue
            ex = db.query(JadwalPengganti).filter(
                JadwalPengganti.matakuliah_id == mk.id,
                JadwalPengganti.pertemuan_ke  == jp["pertemuan_ke"],
            ).first()
            if not ex:
                db.add(JadwalPengganti(
                    matakuliah_id    = mk.id,
                    dosen_id         = dosen.id,
                    pertemuan_ke     = jp["pertemuan_ke"],
                    jam_mulai_baru   = jp["jam_mulai_baru"],
                    jam_selesai_baru = jp["jam_selesai_baru"],
                    ruangan_baru     = jp["ruangan_baru"],
                    keterangan       = jp["keterangan"],
                ))
                print(f"  ✓ Pertemuan {jp['pertemuan_ke']} {jp['kode_mk']}: {jp['keterangan'][:55]}...")
        db.flush()

        # ── [7] SESI PRESENSI HISTORIS ────────────────────────────
        print("\n[7/10] Sesi Presensi Historis...")
        sesi_map = {}  # (kode_mk, pertemuan) → SesiPresensi

        # Semester dimulai 3 Maret 2026
        # Minggu ke-1 = 3 Mar, ke-2 = 10 Mar, ..., ke-9 = 28 Apr

        def hari_mulai(hari_nama: str, minggu_ke: int, jam: time) -> datetime:
            """Hitung tanggal sesi untuk minggu ke-N semester ini (WIB)."""
            base = {
                "Senin" : datetime(2026, 3, 2),
                "Selasa": datetime(2026, 3, 3),
                "Rabu"  : datetime(2026, 3, 4),
                "Kamis" : datetime(2026, 3, 5),
                "Jumat" : datetime(2026, 3, 6),
                "Sabtu" : datetime(2026, 3, 7),
            }
            tgl = base[hari_nama] + timedelta(weeks=minggu_ke - 1)
            return tgl.replace(hour=jam.hour, minute=jam.minute + random.randint(0, 5))

        # Definisi sesi historis per MK
        sesi_historis = []
        for mk_data in MATAKULIAH_DATA:
            kls0 = mk_data["kelas"][0]
            hari = kls0["hari"]
            jam_buka   = SLOT_JAM[kls0["slot_mulai"]][0]
            jam_tutup  = SLOT_JAM[kls0["slot_selesai"]][1]
            dosen_nidn = kls0["dosen_nidn"]

            # Mode: 80% offline, 20% online (acak per pertemuan)
            for ptm in range(1, 10):   # 9 pertemuan sudah selesai
                mode = SesiMode.online if random.random() < 0.2 else SesiMode.offline
                batas_menit = random.choice([15, 15, 20, None])  # None = tanpa batas
                sesi_historis.append({
                    "kode_mk"    : mk_data["kode"],
                    "dosen_nidn" : dosen_nidn,
                    "mode"       : mode,
                    "pertemuan"  : ptm,
                    "hari"       : hari,
                    "jam_buka"   : jam_buka,
                    "jam_tutup"  : jam_tutup,
                    "batas_menit": batas_menit,
                    "minggu_ke"  : ptm,
                })

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

            dt_buka  = hari_mulai(s_def["hari"], s_def["minggu_ke"], s_def["jam_buka"])
            dt_tutup = hari_mulai(s_def["hari"], s_def["minggu_ke"], s_def["jam_tutup"])
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

        db.flush()
        print(f"  → Total sesi historis: {len(sesi_map)}")

        # ── [8] DATA PRESENSI ─────────────────────────────────────
        print("\n[8/10] Data Presensi...")
        presensi_count = 0
        ku_count       = 0

        for (kode_mk, pertemuan), sesi in sesi_map.items():
            if sesi.status != SesiStatus.selesai:
                continue

            mk = mk_map.get(kode_mk)
            if not mk:
                continue

            # Ambil mahasiswa terdaftar di MK ini
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

                # Distribusi realistis
                r = random.random()
                if r < 0.70:
                    status = PresensiStatus.hadir
                    delta  = random.randint(0, 12)
                elif r < 0.83:
                    status = PresensiStatus.terlambat
                    batas_m = int(sesi.batas_terlambat.total_seconds() // 60) if sesi.batas_terlambat else 15
                    delta  = random.randint(batas_m + 1, batas_m + 30)
                elif r < 0.90:
                    status = PresensiStatus.absen
                    delta  = 0
                elif r < 0.95:
                    status = PresensiStatus.izin
                    delta  = 0
                else:
                    status = PresensiStatus.sakit
                    delta  = 0

                waktu_p  = None
                akurasi  = None
                lat, lng = None, None

                if status in (PresensiStatus.hadir, PresensiStatus.terlambat):
                    waktu_p = (buka_utc + timedelta(minutes=delta)).replace(tzinfo=None)
                    akurasi = rand_akurasi()
                    if sesi.mode == SesiMode.offline:
                        r0 = ruangan_map.get(mk.ruangan)
                        if r0 and r0.koordinat_lat:
                            lat = r0.koordinat_lat + random.uniform(-0.0003, 0.0003)
                            lng = r0.koordinat_lng + random.uniform(-0.0003, 0.0003)

                presensi = Presensi(
                    mahasiswa_id   = enroll.mahasiswa_id,
                    sesi_id        = sesi.id,
                    status         = status,
                    waktu_presensi = waktu_p,
                    akurasi_wajah  = akurasi,
                    mode_kelas     = ModeKelas(sesi.mode.value),
                    latitude       = lat,
                    longitude      = lng,
                )
                db.add(presensi)
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
        print(f"  → Total presensi: {presensi_count} record")
        print(f"  → Total kode usage: {ku_count} record")

        # ── [9] SESI AKTIF (untuk testing real-time) ──────────────
        print("\n[9/10] Sesi Aktif (testing real-time)...")
        aktif_defs = [
            {
                "kode_mk"    : "TIF3232209",
                "dosen_nidn" : "0012038901",
                "kode_kelas" : "A",
                "mode"       : SesiMode.offline,
                "pertemuan"  : 10,
                "buka_menit" : 25,
                "batas_menit": 15,
            },
            {
                "kode_mk"    : "SI2234567",
                "dosen_nidn" : "0023047802",
                "kode_kelas" : "A",
                "mode"       : SesiMode.online,
                "pertemuan"  : 10,
                "buka_menit" : 15,
                "batas_menit": None,
            },
            {
                "kode_mk"    : "IK2012201",
                "dosen_nidn" : "0045069504",
                "kode_kelas" : "A",
                "mode"       : SesiMode.offline,
                "pertemuan"  : 10,
                "buka_menit" : 40,
                "batas_menit": 20,
            },
        ]

        for a_def in aktif_defs:
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
                print(f"  ⚠ Skip: sesi aktif {a_def['kode_mk']} Ptm-{a_def['pertemuan']} sudah ada")
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

            mode_str = f"💻 Online (kode: {kode_sesi})" if kode_sesi else "📍 Offline"
            print(f"  ✓ AKTIF: {a_def['kode_mk']} Kelas {a_def['kode_kelas']} Ptm-{a_def['pertemuan']} — {mode_str}")

            # Simulasikan beberapa mahasiswa sudah presensi
            kelas_obj = kelas_map.get((a_def["kode_mk"], a_def["kode_kelas"]))
            if kelas_obj:
                enrolled = db.query(MahasiswaMatakuliah).filter(
                    MahasiswaMatakuliah.matakuliah_id == mk.id,
                    MahasiswaMatakuliah.kelas_id      == kelas_obj.id,
                ).all()
                sudah_hadir = random.sample(enrolled, min(len(enrolled), int(len(enrolled) * 0.55)))
                buka_utc = datetime.now(timezone.utc) - timedelta(minutes=a_def["buka_menit"])

                for enroll in sudah_hadir:
                    delta = random.randint(0, a_def["buka_menit"] - 1)
                    batas_m = a_def["batas_menit"] or 15
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
                print(f"    → {len(sudah_hadir)} mahasiswa sudah presensi di sesi ini")

        # ── [10] KONFIGURASI SISTEM ───────────────────────────────
        print("\n[10/10] Konfigurasi Sistem & Audit Log...")
        for kfg in KONFIGURASI_DEFAULT:
            ex = db.query(KonfigurasiSistem).filter(
                KonfigurasiSistem.key == kfg["key"]
            ).first()
            if not ex:
                db.add(KonfigurasiSistem(**kfg))
                print(f"  ✓ Config: {kfg['key']} = {kfg['value']}")
        db.flush()

        # Audit log contoh
        super_admin = users_by_nim.get("SUPERADMIN")
        if super_admin:
            audit_contoh = [
                ("SEED_DATABASE",     "system",    None,                "Seed data awal database"),
                ("CREATE_PROGRAM_STUDI", "program_studi", None,        f"6 program studi diinsert"),
                ("CREATE_RUANGAN",    "ruangan",   None,                f"20 ruangan diinsert"),
                ("UPDATE_KONFIGURASI","konfigurasi_sistem","face_threshold","face_threshold diset ke 0.9"),
            ]
            for aksi, entitas, eid, detail in audit_contoh:
                db.add(AuditLog(
                    admin_id   = super_admin.id,
                    aksi       = aksi,
                    entitas    = entitas,
                    entitas_id = eid,
                    detail     = detail,
                    ip_address = "127.0.0.1",
                ))
        db.flush()

        # ── COMMIT ────────────────────────────────────────────────
        db.commit()

        # ── RINGKASAN ─────────────────────────────────────────────
        total_sesi     = db.query(SesiPresensi).count()
        total_aktif    = db.query(SesiPresensi).filter(SesiPresensi.status == SesiStatus.aktif).count()
        total_presensi = db.query(Presensi).count()
        total_enroll   = db.query(MahasiswaMatakuliah).count()
        total_kelas    = db.query(KelasMatakuliah).count()
        total_ruangan  = db.query(Ruangan).count()

        print("\n" + "=" * 70)
        print("  ✅  SEED BERHASIL!")
        print("=" * 70)
        print(f"""
  Data yang di-insert:
  ├── Program Studi : {len(prodi_map)} prodi
  ├── Super Admin   : 1 akun
  ├── Admin Fakultas: {len(ADMIN_DATA)} akun
  ├── Dosen         : {len(DOSEN_DATA)} akun
  ├── Mahasiswa     : {len(MAHASISWA_DATA)} akun
  ├── Ruangan       : {total_ruangan} (kuliah, lab, seminar)
  ├── Matakuliah    : {len(mk_map)} MK
  ├── Kelas         : {total_kelas} kelas per MK
  ├── Enrollment    : {total_enroll} record
  ├── Sesi Presensi : {total_sesi} ({total_aktif} aktif sekarang)
  └── Data Presensi : {total_presensi} record
        """)

        print("  ─── Akun Login ─────────────────────────────────────────────")
        print("  Password semua akun: Password123!")
        print()
        print("  [Super Admin — IT Kampus]")
        print("   NIM/NIDN: SUPERADMIN")
        print()
        print("  [Admin Fakultas]")
        for a in ADMIN_DATA:
            print(f"   NIM/NIDN: {a['nim_nidn']:<12}  ({a['nama_lengkap']})")
        print()
        print("  [Dosen]")
        for d in DOSEN_DATA[:4]:
            print(f"   NIDN: {d['nim_nidn']:<14}  {d['nama_lengkap']}")
        print()
        print("  [Mahasiswa (contoh)]")
        samples = [
            ("H071211001", "Muhammad Rizky Pratama",    "TIF 2021"),
            ("H071411001", "Maya Anggraeni Susanti",    "SI 2021"),
            ("H071311001", "Bintang Ramadhan Putra",    "IK 2021"),
            ("H071511001", "Leonardo Devano Putra",     "TK 2021"),
            ("H071641001", "Vira Claudia Santoso",      "MI 2022"),
        ]
        for nim, nama, prodi in samples:
            print(f"   NIM: {nim:<14}  {nama:<30} ({prodi})")

        aktif_sesi_list = db.query(SesiPresensi).filter(
            SesiPresensi.status    == SesiStatus.aktif,
            SesiPresensi.kode_sesi != None,
        ).all()
        if aktif_sesi_list:
            print()
            print("  ─── Kode Sesi Online Aktif ──────────────────────────────────")
            for s in aktif_sesi_list:
                mk = mk_map.get(
                    next((k for k, v in mk_map.items() if v.id == s.matakuliah_id), None)
                )
                nama_mk = mk.nama[:35] if mk else "-"
                print(f"   Kode: {s.kode_sesi}  →  {nama_mk}")

        print()
        print("  ─── Konfigurasi Sistem ──────────────────────────────────────")
        for kfg in KONFIGURASI_DEFAULT:
            print(f"   {kfg['key']:<24} = {kfg['value']}")

        print()
        print("=" * 70)

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