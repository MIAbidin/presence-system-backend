"""
seed.py — Data dummy lengkap & realistis untuk Aplikasi Presensi Face Recognition
===================================================================================
Jalankan: python new_seed.py

Konten:
  - 1 Admin
  - 6 Dosen (berbagai prodi)
  - 40 Mahasiswa (berbagai prodi & angkatan)
  - 8 Matakuliah (lengkap dengan jadwal & koordinat GPS)
  - Enrollment mahasiswa ke matakuliah
  - 3 contoh Jadwal Pengganti
  - 24 Sesi Presensi (offline & online, aktif & selesai)
  - Data Presensi lengkap (hadir, terlambat, absen, izin, sakit)
  - Kode Usage untuk sesi online

Password semua akun: Password123!
"""

import uuid
import random
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
from app.services.auth_service import hash_password

WIB = ZoneInfo("Asia/Jakarta")

# ─── DATA USERS ───────────────────────────────────────────────

ADMIN_DATA = [
    {
        "nim_nidn"     : "ADMIN001",
        "nama_lengkap" : "Ahmad Firdaus, S.Kom",
        "email"        : "admin@universitashasanuddin.ac.id",
        "role"         : UserRole.admin,
        "program_studi": "Teknologi Informasi",
    },
]

DOSEN_DATA = [
    {
        "nim_nidn"     : "0012038901",
        "nama_lengkap" : "Dr. Ir. Budi Santoso, M.T.",
        "email"        : "budi.santoso@universitashasanuddin.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "0023047802",
        "nama_lengkap" : "Siti Rahayu Ningrum, S.T., M.Sc.",
        "email"        : "siti.rahayu@universitashasanuddin.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "0031056703",
        "nama_lengkap" : "Prof. Dr. Hendra Gunawan, M.Kom.",
        "email"        : "hendra.gunawan@universitashasanuddin.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "0045069504",
        "nama_lengkap" : "Dewi Kusumawati, S.Si., M.Cs.",
        "email"        : "dewi.kusumawati@universitashasanuddin.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Ilmu Komputer",
    },
    {
        "nim_nidn"     : "0056078405",
        "nama_lengkap" : "Rizal Fathurohman, M.T.",
        "email"        : "rizal.fathurohman@universitashasanuddin.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "0067087306",
        "nama_lengkap" : "Nur Aisyah Putri, S.Kom., M.M.",
        "email"        : "nur.aisyah@universitashasanuddin.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Sistem Informasi",
    },
]

MAHASISWA_DATA = [
    # ── Teknik Informatika 2021 ─────────────────────────────
    {
        "nim_nidn"     : "H071211001",
        "nama_lengkap" : "Muhammad Rizky Pratama",
        "email"        : "rizky.pratama21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "H071211002",
        "nama_lengkap" : "Putri Amelia Sari",
        "email"        : "putri.amelia21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "H071211003",
        "nama_lengkap" : "Ahmad Farhan Maulana",
        "email"        : "farhan.maulana21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "H071211004",
        "nama_lengkap" : "Annisa Rahma Dewi",
        "email"        : "annisa.dewi21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "H071211005",
        "nama_lengkap" : "Bagas Eko Saputro",
        "email"        : "bagas.saputro21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "H071211006",
        "nama_lengkap" : "Cantika Nuraini",
        "email"        : "cantika.nuraini21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "H071211007",
        "nama_lengkap" : "Dimas Aditya Nugroho",
        "email"        : "dimas.nugroho21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "H071211008",
        "nama_lengkap" : "Elsa Permata Indah",
        "email"        : "elsa.permata21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "H071211009",
        "nama_lengkap" : "Faiz Akbar Ramadhan",
        "email"        : "faiz.ramadhan21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "H071211010",
        "nama_lengkap" : "Ghina Maudi Pratiwi",
        "email"        : "ghina.pratiwi21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    # ── Teknik Informatika 2022 ─────────────────────────────
    {
        "nim_nidn"     : "H071221001",
        "nama_lengkap" : "Hafizh Yusuf Kurniawan",
        "email"        : "hafizh.kurniawan22@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "H071221002",
        "nama_lengkap" : "Indira Cahyaningrum",
        "email"        : "indira.cahya22@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "H071221003",
        "nama_lengkap" : "Jovan Aldriansyah",
        "email"        : "jovan.aldrian22@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "H071221004",
        "nama_lengkap" : "Keisya Aurelia Putri",
        "email"        : "keisya.aurelia22@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "H071221005",
        "nama_lengkap" : "Luthfi Hakim Ardiansyah",
        "email"        : "luthfi.hakim22@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    # ── Sistem Informasi 2021 ───────────────────────────────
    {
        "nim_nidn"     : "H071411001",
        "nama_lengkap" : "Maya Anggraeni Susanti",
        "email"        : "maya.anggraeni21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "H071411002",
        "nama_lengkap" : "Naufal Dzikri Fauzan",
        "email"        : "naufal.fauzan21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "H071411003",
        "nama_lengkap" : "Olivia Kurnia Dewi",
        "email"        : "olivia.kurnia21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "H071411004",
        "nama_lengkap" : "Prasetyo Wibowo Nugroho",
        "email"        : "prasetyo.wibowo21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "H071411005",
        "nama_lengkap" : "Qisthi Ramadhani",
        "email"        : "qisthi.ramadhani21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "H071411006",
        "nama_lengkap" : "Rafli Akbar Suhaimi",
        "email"        : "rafli.suhaimi21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "H071411007",
        "nama_lengkap" : "Salsabila Nur Izzati",
        "email"        : "salsabila.izzati21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "H071411008",
        "nama_lengkap" : "Taufiq Hidayatullah",
        "email"        : "taufiq.hidayat21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "H071411009",
        "nama_lengkap" : "Ulfa Maulidya Rahma",
        "email"        : "ulfa.rahma21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "H071411010",
        "nama_lengkap" : "Vicky Ardiansyah",
        "email"        : "vicky.ardiansyah21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    # ── Sistem Informasi 2022 ───────────────────────────────
    {
        "nim_nidn"     : "H071421001",
        "nama_lengkap" : "Widya Astuti Ramadhani",
        "email"        : "widya.astuti22@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "H071421002",
        "nama_lengkap" : "Xaverius Bintang Pradana",
        "email"        : "xaverius.pradana22@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "H071421003",
        "nama_lengkap" : "Yasmin Aulia Salsabila",
        "email"        : "yasmin.salsabila22@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "H071421004",
        "nama_lengkap" : "Zaidan Farel Pratama",
        "email"        : "zaidan.farel22@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "H071421005",
        "nama_lengkap" : "Adinda Puspa Maharani",
        "email"        : "adinda.puspa22@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    # ── Ilmu Komputer 2021 ──────────────────────────────────
    {
        "nim_nidn"     : "H071311001",
        "nama_lengkap" : "Bintang Ramadhan Putra",
        "email"        : "bintang.putra21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Ilmu Komputer",
    },
    {
        "nim_nidn"     : "H071311002",
        "nama_lengkap" : "Chelsea Amanda Pratiwi",
        "email"        : "chelsea.pratiwi21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Ilmu Komputer",
    },
    {
        "nim_nidn"     : "H071311003",
        "nama_lengkap" : "Daffa Arya Wicaksono",
        "email"        : "daffa.wicaksono21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Ilmu Komputer",
    },
    {
        "nim_nidn"     : "H071311004",
        "nama_lengkap" : "Eka Putri Handayani",
        "email"        : "eka.handayani21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Ilmu Komputer",
    },
    {
        "nim_nidn"     : "H071311005",
        "nama_lengkap" : "Farhan Septian Nugroho",
        "email"        : "farhan.septian21@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Ilmu Komputer",
    },
    # ── Ilmu Komputer 2022 ──────────────────────────────────
    {
        "nim_nidn"     : "H071321001",
        "nama_lengkap" : "Gilang Ramadhan Sanjaya",
        "email"        : "gilang.sanjaya22@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Ilmu Komputer",
    },
    {
        "nim_nidn"     : "H071321002",
        "nama_lengkap" : "Hana Salsabila Anwar",
        "email"        : "hana.anwar22@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Ilmu Komputer",
    },
    {
        "nim_nidn"     : "H071321003",
        "nama_lengkap" : "Ilham Syahputra",
        "email"        : "ilham.syahputra22@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Ilmu Komputer",
    },
    {
        "nim_nidn"     : "H071321004",
        "nama_lengkap" : "Jessica Tamara Larasati",
        "email"        : "jessica.larasati22@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Ilmu Komputer",
    },
    {
        "nim_nidn"     : "H071321005",
        "nama_lengkap" : "Kevin Ardianto Susilo",
        "email"        : "kevin.susilo22@student.unhas.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Ilmu Komputer",
    },
]

# ─── DATA MATAKULIAH ──────────────────────────────────────────
# Koordinat GPS sekitar kampus Universitas Hasanuddin Makassar
# (lat: -5.13, lng: 119.49)

MATAKULIAH_DATA = [
    {
        "kode"          : "IF301",
        "nama"          : "Pemrograman Mobile",
        "sks"           : 3,
        "hari"          : "Senin",
        "jam_mulai"     : time(8, 0),
        "jam_selesai"   : time(10, 30),
        "ruangan"       : "Lab Komputer A-301",
        "koordinat_lat" : -5.130245,
        "koordinat_lng" : 119.489432,
        "izin_tamu"     : True,
        "dosen_key"     : "0012038901",   # Budi Santoso
    },
    {
        "kode"          : "IF302",
        "nama"          : "Basis Data Lanjut",
        "sks"           : 3,
        "hari"          : "Selasa",
        "jam_mulai"     : time(13, 0),
        "jam_selesai"   : time(15, 30),
        "ruangan"       : "Ruang Kuliah B-202",
        "koordinat_lat" : -5.131100,
        "koordinat_lng" : 119.490271,
        "izin_tamu"     : False,
        "dosen_key"     : "0023047802",   # Siti Rahayu
    },
    {
        "kode"          : "IF401",
        "nama"          : "Kecerdasan Buatan",
        "sks"           : 3,
        "hari"          : "Rabu",
        "jam_mulai"     : time(10, 0),
        "jam_selesai"   : time(12, 30),
        "ruangan"       : "Lab Komputer B-105",
        "koordinat_lat" : -5.129873,
        "koordinat_lng" : 119.488950,
        "izin_tamu"     : True,
        "dosen_key"     : "0031056703",   # Hendra Gunawan
    },
    {
        "kode"          : "SI201",
        "nama"          : "Sistem Informasi Manajemen",
        "sks"           : 3,
        "hari"          : "Kamis",
        "jam_mulai"     : time(8, 0),
        "jam_selesai"   : time(10, 30),
        "ruangan"       : "Ruang Kuliah C-101",
        "koordinat_lat" : -5.132451,
        "koordinat_lng" : 119.491380,
        "izin_tamu"     : False,
        "dosen_key"     : "0023047802",   # Siti Rahayu
    },
    {
        "kode"          : "SI301",
        "nama"          : "Analisis dan Desain Sistem",
        "sks"           : 3,
        "hari"          : "Jumat",
        "jam_mulai"     : time(10, 0),
        "jam_selesai"   : time(12, 30),
        "ruangan"       : "Ruang Kuliah A-204",
        "koordinat_lat" : -5.130780,
        "koordinat_lng" : 119.489110,
        "izin_tamu"     : True,
        "dosen_key"     : "0067087306",   # Nur Aisyah
    },
    {
        "kode"          : "IK201",
        "nama"          : "Algoritma dan Struktur Data",
        "sks"           : 4,
        "hari"          : "Senin",
        "jam_mulai"     : time(13, 0),
        "jam_selesai"   : time(16, 0),
        "ruangan"       : "Lab Komputer C-210",
        "koordinat_lat" : -5.131620,
        "koordinat_lng" : 119.490800,
        "izin_tamu"     : False,
        "dosen_key"     : "0045069504",   # Dewi Kusumawati
    },
    {
        "kode"          : "IK301",
        "nama"          : "Jaringan Komputer",
        "sks"           : 3,
        "hari"          : "Rabu",
        "jam_mulai"     : time(7, 30),
        "jam_selesai"   : time(10, 0),
        "ruangan"       : "Lab Jaringan D-115",
        "koordinat_lat" : -5.129340,
        "koordinat_lng" : 119.488620,
        "izin_tamu"     : True,
        "dosen_key"     : "0056078405",   # Rizal Fathurohman
    },
    {
        "kode"          : "IF201",
        "nama"          : "Pemrograman Berorientasi Objek",
        "sks"           : 3,
        "hari"          : "Kamis",
        "jam_mulai"     : time(13, 0),
        "jam_selesai"   : time(15, 30),
        "ruangan"       : "Lab Komputer A-205",
        "koordinat_lat" : -5.130455,
        "koordinat_lng" : 119.489740,
        "izin_tamu"     : False,
        "dosen_key"     : "0012038901",   # Budi Santoso
    },
]

# ─── MAPPING ENROLLMENT (matakuliah → program studi yang ikut) ─
# Format: {kode_mk: [list nim mahasiswa]}
# Mahasiswa dari prodi terkait didaftarkan otomatis

ENROLLMENT_MAP = {
    "IF301" : [m["nim_nidn"] for m in MAHASISWA_DATA if m["program_studi"] == "Teknik Informatika"],
    "IF302" : [m["nim_nidn"] for m in MAHASISWA_DATA if m["program_studi"] == "Teknik Informatika"],
    "IF401" : [m["nim_nidn"] for m in MAHASISWA_DATA if m["program_studi"] in ("Teknik Informatika", "Ilmu Komputer")],
    "SI201" : [m["nim_nidn"] for m in MAHASISWA_DATA if m["program_studi"] == "Sistem Informasi"],
    "SI301" : [m["nim_nidn"] for m in MAHASISWA_DATA if m["program_studi"] == "Sistem Informasi"],
    "IK201" : [m["nim_nidn"] for m in MAHASISWA_DATA if m["program_studi"] == "Ilmu Komputer"],
    "IK301" : [m["nim_nidn"] for m in MAHASISWA_DATA if m["program_studi"] in ("Ilmu Komputer", "Teknik Informatika")],
    "IF201" : [m["nim_nidn"] for m in MAHASISWA_DATA if m["program_studi"] in ("Teknik Informatika", "Sistem Informasi")],
}

# Mahasiswa tamu (is_tamu=True): tambahkan beberapa mahasiswa dari prodi lain
# Format: {kode_mk: [list nim yang jadi tamu]}
TAMU_MAP = {
    "IF301": ["H071411001", "H071411002"],   # Mhs SI ikut matkul IF sbg tamu
    "IF401": ["H071411003", "H071411004"],
    "IK301": ["H071411005"],
    "SI301": ["H071211001"],                 # Mhs TI ikut matkul SI sbg tamu
}

# ─── HELPER ───────────────────────────────────────────────────

def utc_from_wib(y, mo, d, h, mi, s=0):
    """Buat datetime WIB lalu convert ke UTC untuk disimpan di DB."""
    wib_dt = datetime(y, mo, d, h, mi, s, tzinfo=WIB)
    return wib_dt.astimezone(timezone.utc).replace(tzinfo=None)


def rand_akurasi():
    """Akurasi wajah antara 78–98%."""
    return round(random.uniform(78.0, 98.5), 2)


def rand_kode():
    import secrets, string
    chars = (string.ascii_uppercase + string.digits).replace("O","").replace("I","").replace("0","").replace("L","").replace("1","")
    return "".join(secrets.choice(chars) for _ in range(6))


# ─── MAIN SEED ────────────────────────────────────────────────

def seed():
    db = SessionLocal()
    try:
        print("=" * 65)
        print("  SEED DATA — Aplikasi Presensi Face Recognition")
        print("=" * 65)

        # ── 1. USERS ────────────────────────────────────────────
        print("\n[1/7] Insert Users...")
        all_user_data = ADMIN_DATA + DOSEN_DATA + MAHASISWA_DATA
        users_by_nim  = {}

        for data in all_user_data:
            existing = db.query(User).filter(User.nim_nidn == data["nim_nidn"]).first()
            if existing:
                print(f"  ⚠ Skip  : {data['nama_lengkap']} ({data['nim_nidn']})")
                users_by_nim[data["nim_nidn"]] = existing
                continue

            user = User(
                nim_nidn      = data["nim_nidn"],
                nama_lengkap  = data["nama_lengkap"],
                email         = data["email"],
                password_hash = hash_password("Password123!"),
                role          = data["role"],
                program_studi = data["program_studi"],
                is_face_registered = (data["role"] == UserRole.mahasiswa),
                is_active     = True,
            )
            db.add(user)
            db.flush()
            users_by_nim[data["nim_nidn"]] = user
            role_label = {"mahasiswa": "Mhs", "dosen": "Dsn", "admin": "Adm"}[data["role"].value]
            print(f"  ✓ [{role_label}] {data['nama_lengkap']}")

        db.flush()
        print(f"  → Total users: {len(users_by_nim)}")

        # ── 2. MATAKULIAH ────────────────────────────────────────
        print("\n[2/7] Insert Matakuliah...")
        matakuliah_by_kode = {}

        for mk_data in MATAKULIAH_DATA:
            existing = db.query(Matakuliah).filter(Matakuliah.kode == mk_data["kode"]).first()
            if existing:
                print(f"  ⚠ Skip  : {mk_data['nama']}")
                matakuliah_by_kode[mk_data["kode"]] = existing
                continue

            mk = Matakuliah(
                kode          = mk_data["kode"],
                nama          = mk_data["nama"],
                sks           = mk_data["sks"],
                hari          = mk_data["hari"],
                jam_mulai     = mk_data["jam_mulai"],
                jam_selesai   = mk_data["jam_selesai"],
                ruangan       = mk_data["ruangan"],
                koordinat_lat = mk_data["koordinat_lat"],
                koordinat_lng = mk_data["koordinat_lng"],
                izin_tamu     = mk_data["izin_tamu"],
            )
            db.add(mk)
            db.flush()
            matakuliah_by_kode[mk_data["kode"]] = mk
            tamu_info = " (izin tamu ✓)" if mk_data["izin_tamu"] else ""
            print(f"  ✓ {mk_data['kode']} — {mk_data['nama']}{tamu_info}")

        db.flush()

        # ── 3. ENROLLMENT ────────────────────────────────────────
        print("\n[3/7] Insert Enrollment (mahasiswa ↔ matakuliah)...")
        enroll_count = 0

        for kode_mk, nim_list in ENROLLMENT_MAP.items():
            mk = matakuliah_by_kode.get(kode_mk)
            if not mk:
                continue
            for nim in nim_list:
                user = users_by_nim.get(nim)
                if not user:
                    continue
                existing = db.query(MahasiswaMatakuliah).filter(
                    MahasiswaMatakuliah.mahasiswa_id  == user.id,
                    MahasiswaMatakuliah.matakuliah_id == mk.id,
                ).first()
                if not existing:
                    db.add(MahasiswaMatakuliah(
                        mahasiswa_id  = user.id,
                        matakuliah_id = mk.id,
                        is_tamu       = False,
                        kelas_asal    = None,
                    ))
                    enroll_count += 1

        # Tambahkan mahasiswa tamu
        for kode_mk, nim_list in TAMU_MAP.items():
            mk = matakuliah_by_kode.get(kode_mk)
            if not mk:
                continue
            for nim in nim_list:
                user = users_by_nim.get(nim)
                if not user:
                    continue
                existing = db.query(MahasiswaMatakuliah).filter(
                    MahasiswaMatakuliah.mahasiswa_id  == user.id,
                    MahasiswaMatakuliah.matakuliah_id == mk.id,
                ).first()
                if not existing:
                    kelas_asal = f"{user.program_studi} — Kelas Reguler"
                    db.add(MahasiswaMatakuliah(
                        mahasiswa_id  = user.id,
                        matakuliah_id = mk.id,
                        is_tamu       = True,
                        kelas_asal    = kelas_asal,
                    ))
                    enroll_count += 1

        db.flush()
        print(f"  → Total enrollment: {enroll_count} record")

        # ── 4. JADWAL PENGGANTI ──────────────────────────────────
        print("\n[4/7] Insert Jadwal Pengganti...")

        jadwal_pengganti_list = [
            {
                "kode_mk"        : "IF301",
                "dosen_nidn"     : "0012038901",
                "pertemuan_ke"   : 5,
                "jam_mulai_baru" : time(10, 0),
                "jam_selesai_baru": time(12, 30),
                "ruangan_baru"   : "Lab Komputer B-105",
                "keterangan"     : "Ruang A-301 dipakai ujian tengah semester, pindah ke B-105",
            },
            {
                "kode_mk"        : "IF302",
                "dosen_nidn"     : "0023047802",
                "pertemuan_ke"   : 8,
                "jam_mulai_baru" : time(10, 0),
                "jam_selesai_baru": time(12, 30),
                "ruangan_baru"   : None,
                "keterangan"     : "Pertemuan 8 dimajukan ke pagi karena dosen ada rapat sore",
            },
            {
                "kode_mk"        : "SI201",
                "dosen_nidn"     : "0023047802",
                "pertemuan_ke"   : 3,
                "jam_mulai_baru" : None,
                "jam_selesai_baru": None,
                "ruangan_baru"   : "Aula Gedung D",
                "keterangan"     : "Kuliah tamu — pindah ke Aula untuk menampung semua mahasiswa",
            },
        ]

        for jp_data in jadwal_pengganti_list:
            mk     = matakuliah_by_kode.get(jp_data["kode_mk"])
            dosen  = users_by_nim.get(jp_data["dosen_nidn"])
            if not mk or not dosen:
                continue
            existing = db.query(JadwalPengganti).filter(
                JadwalPengganti.matakuliah_id == mk.id,
                JadwalPengganti.pertemuan_ke  == jp_data["pertemuan_ke"],
            ).first()
            if not existing:
                db.add(JadwalPengganti(
                    matakuliah_id    = mk.id,
                    dosen_id         = dosen.id,
                    pertemuan_ke     = jp_data["pertemuan_ke"],
                    jam_mulai_baru   = jp_data["jam_mulai_baru"],
                    jam_selesai_baru = jp_data["jam_selesai_baru"],
                    ruangan_baru     = jp_data["ruangan_baru"],
                    keterangan       = jp_data["keterangan"],
                ))
                print(f"  ✓ {jp_data['kode_mk']} — Pertemuan {jp_data['pertemuan_ke']}: {jp_data['keterangan'][:55]}...")

        db.flush()

        # ── 5. SESI PRESENSI ─────────────────────────────────────
        print("\n[5/7] Insert Sesi Presensi...")

        # Definisi sesi historis (selesai) + sesi hari ini (bisa aktif)
        # Tanggal mulai semester: 3 Maret 2026
        # Sekarang sekitar: 29 April 2026

        sesi_defs = [
            # ── IF301 Pemrograman Mobile (Budi Santoso) ──────────
            *[{
                "kode_mk"    : "IF301",
                "dosen_nidn" : "0012038901",
                "mode"       : SesiMode.offline,
                "pertemuan"  : i,
                "tanggal_wib": (datetime(2026, 3, 2) + timedelta(weeks=i - 1)).replace(hour=8, minute=5),
                "selesai_wib": (datetime(2026, 3, 2) + timedelta(weeks=i - 1)).replace(hour=10, minute=35),
                "status"     : SesiStatus.selesai,
                "batas_menit": 15,
            } for i in range(1, 9)],
            # Sesi IF301 online (pertemuan 9 — karena hujan deras)
            {
                "kode_mk"    : "IF301",
                "dosen_nidn" : "0012038901",
                "mode"       : SesiMode.online,
                "pertemuan"  : 9,
                "tanggal_wib": datetime(2026, 4, 27, 8, 10),
                "selesai_wib": datetime(2026, 4, 27, 10, 30),
                "status"     : SesiStatus.selesai,
                "batas_menit": 20,
            },

            # ── IF302 Basis Data Lanjut (Siti Rahayu) ────────────
            *[{
                "kode_mk"    : "IF302",
                "dosen_nidn" : "0023047802",
                "mode"       : SesiMode.offline,
                "pertemuan"  : i,
                "tanggal_wib": (datetime(2026, 3, 3) + timedelta(weeks=i - 1)).replace(hour=13, minute=3),
                "selesai_wib": (datetime(2026, 3, 3) + timedelta(weeks=i - 1)).replace(hour=15, minute=32),
                "status"     : SesiStatus.selesai,
                "batas_menit": 15,
            } for i in range(1, 8)],

            # ── SI201 Sistem Informasi Manajemen (Siti Rahayu) ───
            *[{
                "kode_mk"    : "SI201",
                "dosen_nidn" : "0023047802",
                "mode"       : SesiMode.offline,
                "pertemuan"  : i,
                "tanggal_wib": (datetime(2026, 3, 5) + timedelta(weeks=i - 1)).replace(hour=8, minute=2),
                "selesai_wib": (datetime(2026, 3, 5) + timedelta(weeks=i - 1)).replace(hour=10, minute=31),
                "status"     : SesiStatus.selesai,
                "batas_menit": 15,
            } for i in range(1, 6)],
            # SI201 online
            {
                "kode_mk"    : "SI201",
                "dosen_nidn" : "0023047802",
                "mode"       : SesiMode.online,
                "pertemuan"  : 6,
                "tanggal_wib": datetime(2026, 4, 10, 8, 5),
                "selesai_wib": datetime(2026, 4, 10, 10, 30),
                "status"     : SesiStatus.selesai,
                "batas_menit": None,   # tidak ada batas terlambat
            },

            # ── IF401 Kecerdasan Buatan (Hendra Gunawan) ─────────
            *[{
                "kode_mk"    : "IF401",
                "dosen_nidn" : "0031056703",
                "mode"       : SesiMode.offline,
                "pertemuan"  : i,
                "tanggal_wib": (datetime(2026, 3, 4) + timedelta(weeks=i - 1)).replace(hour=10, minute=5),
                "selesai_wib": (datetime(2026, 3, 4) + timedelta(weeks=i - 1)).replace(hour=12, minute=33),
                "status"     : SesiStatus.selesai,
                "batas_menit": 15,
            } for i in range(1, 7)],

            # ── IK201 Algoritma & Struktur Data (Dewi Kusumawati) ─
            *[{
                "kode_mk"    : "IK201",
                "dosen_nidn" : "0045069504",
                "mode"       : SesiMode.offline,
                "pertemuan"  : i,
                "tanggal_wib": (datetime(2026, 3, 2) + timedelta(weeks=i - 1)).replace(hour=13, minute=7),
                "selesai_wib": (datetime(2026, 3, 2) + timedelta(weeks=i - 1)).replace(hour=16, minute=5),
                "status"     : SesiStatus.selesai,
                "batas_menit": 10,
            } for i in range(1, 6)],
        ]

        sesi_by_key = {}   # key: (kode_mk, pertemuan)

        for s_def in sesi_defs:
            key = (s_def["kode_mk"], s_def["pertemuan"])
            mk    = matakuliah_by_kode.get(s_def["kode_mk"])
            dosen = users_by_nim.get(s_def["dosen_nidn"])
            if not mk or not dosen:
                continue

            existing_sesi = db.query(SesiPresensi).filter(
                SesiPresensi.matakuliah_id == mk.id,
                SesiPresensi.dosen_id      == dosen.id,
                SesiPresensi.pertemuan_ke  == s_def["pertemuan"],
            ).first()
            if existing_sesi:
                sesi_by_key[key] = existing_sesi
                continue

            waktu_buka  = utc_from_wib(
                s_def["tanggal_wib"].year, s_def["tanggal_wib"].month,
                s_def["tanggal_wib"].day,  s_def["tanggal_wib"].hour,
                s_def["tanggal_wib"].minute)
            waktu_tutup = utc_from_wib(
                s_def["selesai_wib"].year, s_def["selesai_wib"].month,
                s_def["selesai_wib"].day,  s_def["selesai_wib"].hour,
                s_def["selesai_wib"].minute) if s_def["status"] == SesiStatus.selesai else None

            batas = (timedelta(minutes=s_def["batas_menit"])
                     if s_def.get("batas_menit") is not None else None)

            # Kode sesi untuk online
            kode_sesi      = None
            kode_expire_at = None
            if s_def["mode"] == SesiMode.online and s_def["status"] == SesiStatus.selesai:
                kode_sesi      = rand_kode()
                kode_expire_at = waktu_buka + timedelta(minutes=90)

            sesi = SesiPresensi(
                matakuliah_id  = mk.id,
                dosen_id       = dosen.id,
                mode           = s_def["mode"],
                kode_sesi      = kode_sesi,
                kode_expire_at = kode_expire_at,
                pertemuan_ke   = s_def["pertemuan"],
                waktu_buka     = waktu_buka,
                waktu_tutup    = waktu_tutup,
                batas_terlambat= batas,
                status         = s_def["status"],
            )
            db.add(sesi)
            db.flush()
            sesi_by_key[key] = sesi
            mode_label = "📍 Offline" if s_def["mode"] == SesiMode.offline else "💻 Online "
            print(f"  ✓ {s_def['kode_mk']} Ptm-{s_def['pertemuan']:02d} {mode_label}  {s_def['tanggal_wib'].strftime('%d %b %Y')}")

        db.flush()

        # ── 6. PRESENSI ──────────────────────────────────────────
        print("\n[6/7] Insert Data Presensi...")

        presensi_count = 0
        kode_usage_count = 0

        for key, sesi in sesi_by_key.items():
            kode_mk, pertemuan = key
            if sesi.status != SesiStatus.selesai:
                continue

            # Ambil mahasiswa yang terdaftar di matakuliah ini
            enrollments = db.query(MahasiswaMatakuliah).filter(
                MahasiswaMatakuliah.matakuliah_id == sesi.matakuliah_id
            ).all()

            waktu_buka_utc = sesi.waktu_buka
            if waktu_buka_utc.tzinfo is None:
                waktu_buka_utc = waktu_buka_utc.replace(tzinfo=timezone.utc)

            for enroll in enrollments:
                # Cek sudah ada presensi
                existing_p = db.query(Presensi).filter(
                    Presensi.mahasiswa_id == enroll.mahasiswa_id,
                    Presensi.sesi_id      == sesi.id,
                ).first()
                if existing_p:
                    continue

                # Distribusi kehadiran realistis
                # 72% hadir, 12% terlambat, 7% absen, 5% izin, 4% sakit
                rand = random.random()
                if rand < 0.72:
                    status = PresensiStatus.hadir
                    # Waktu presensi: 0–12 menit setelah buka sesi
                    delta_menit = random.randint(0, 12)
                elif rand < 0.84:
                    status = PresensiStatus.terlambat
                    batas_m = int(sesi.batas_terlambat.total_seconds() // 60) if sesi.batas_terlambat else 15
                    delta_menit = random.randint(batas_m + 1, batas_m + 25)
                elif rand < 0.91:
                    status = PresensiStatus.absen
                elif rand < 0.96:
                    status = PresensiStatus.izin
                else:
                    status = PresensiStatus.sakit

                waktu_presensi = None
                akurasi        = None
                lat            = None
                lng            = None

                if status in (PresensiStatus.hadir, PresensiStatus.terlambat):
                    waktu_presensi = (waktu_buka_utc + timedelta(minutes=delta_menit)).replace(tzinfo=None)
                    akurasi        = rand_akurasi()
                    if sesi.mode == SesiMode.offline:
                        # GPS sedikit di sekitar koordinat kelas (dalam 80m)
                        mk = db.query(Matakuliah).filter(Matakuliah.id == sesi.matakuliah_id).first()
                        if mk and mk.koordinat_lat:
                            lat = mk.koordinat_lat + random.uniform(-0.0004, 0.0004)
                            lng = mk.koordinat_lng + random.uniform(-0.0004, 0.0004)

                presensi = Presensi(
                    mahasiswa_id   = enroll.mahasiswa_id,
                    sesi_id        = sesi.id,
                    status         = status,
                    waktu_presensi = waktu_presensi,
                    akurasi_wajah  = akurasi,
                    mode_kelas     = ModeKelas(sesi.mode.value),
                    latitude       = lat,
                    longitude      = lng,
                )
                db.add(presensi)
                presensi_count += 1

                # Kode usage untuk sesi online
                if sesi.mode == SesiMode.online and status in (PresensiStatus.hadir, PresensiStatus.terlambat):
                    existing_ku = db.query(KodeUsage).filter(
                        KodeUsage.sesi_id      == sesi.id,
                        KodeUsage.mahasiswa_id == enroll.mahasiswa_id,
                    ).first()
                    if not existing_ku:
                        db.add(KodeUsage(
                            sesi_id      = sesi.id,
                            mahasiswa_id = enroll.mahasiswa_id,
                            used_at      = waktu_presensi,
                        ))
                        kode_usage_count += 1

        db.flush()
        print(f"  → Total presensi  : {presensi_count} record")
        print(f"  → Total kode usage: {kode_usage_count} record")

        # ── 7. SESI AKTIF (hari ini — untuk testing real-time) ──
        print("\n[7/7] Insert Sesi Aktif (untuk testing)...")

        aktif_defs = [
            {
                "kode_mk"    : "IF301",
                "dosen_nidn" : "0012038901",
                "mode"       : SesiMode.offline,
                "pertemuan"  : 10,
                "buka_menit" : 30,   # dibuka 30 menit lalu
                "batas_menit": 15,
            },
            {
                "kode_mk"    : "SI201",
                "dosen_nidn" : "0023047802",
                "mode"       : SesiMode.online,
                "pertemuan"  : 7,
                "buka_menit" : 20,
                "batas_menit": None,
            },
        ]

        for a_def in aktif_defs:
            mk    = matakuliah_by_kode.get(a_def["kode_mk"])
            dosen = users_by_nim.get(a_def["dosen_nidn"])
            if not mk or not dosen:
                continue

            existing_aktif = db.query(SesiPresensi).filter(
                SesiPresensi.matakuliah_id == mk.id,
                SesiPresensi.pertemuan_ke  == a_def["pertemuan"],
                SesiPresensi.status        == SesiStatus.aktif,
            ).first()
            if existing_aktif:
                print(f"  ⚠ Skip  : Sesi aktif {a_def['kode_mk']} Ptm-{a_def['pertemuan']} sudah ada")
                continue

            waktu_buka = datetime.now(timezone.utc) - timedelta(minutes=a_def["buka_menit"])
            waktu_buka = waktu_buka.replace(tzinfo=None)

            batas = (timedelta(minutes=a_def["batas_menit"])
                     if a_def.get("batas_menit") is not None else None)

            kode_sesi      = None
            kode_expire_at = None
            if a_def["mode"] == SesiMode.online:
                kode_sesi      = rand_kode()
                kode_expire_at = (datetime.now(timezone.utc) + timedelta(minutes=40)).replace(tzinfo=None)

            sesi_aktif = SesiPresensi(
                matakuliah_id  = mk.id,
                dosen_id       = dosen.id,
                mode           = a_def["mode"],
                kode_sesi      = kode_sesi,
                kode_expire_at = kode_expire_at,
                pertemuan_ke   = a_def["pertemuan"],
                waktu_buka     = waktu_buka,
                waktu_tutup    = None,
                batas_terlambat= batas,
                status         = SesiStatus.aktif,
            )
            db.add(sesi_aktif)
            db.flush()

            mode_label = "💻 Online " if a_def["mode"] == SesiMode.online else "📍 Offline"
            kode_info  = f" | Kode: {kode_sesi}" if kode_sesi else ""
            print(f"  ✓ Sesi AKTIF: {a_def['kode_mk']} Ptm-{a_def['pertemuan']} {mode_label}{kode_info}")

            # Insert beberapa presensi untuk sesi aktif (yang sudah hadir)
            enrollments = db.query(MahasiswaMatakuliah).filter(
                MahasiswaMatakuliah.matakuliah_id == mk.id
            ).all()
            hadir_count = int(len(enrollments) * random.uniform(0.35, 0.60))
            hadir_count = min(hadir_count, len(enrollments))

            chosen = random.sample(enrollments, hadir_count)
            buka_utc = datetime.now(timezone.utc) - timedelta(minutes=a_def["buka_menit"])
            batas_m  = a_def.get("batas_menit") or 15

            for enroll in chosen:
                delta = random.randint(0, a_def["buka_menit"] - 1)
                if delta <= batas_m:
                    st = PresensiStatus.hadir
                else:
                    st = PresensiStatus.terlambat

                wp = (buka_utc + timedelta(minutes=delta)).replace(tzinfo=None)

                lat, lng = None, None
                if a_def["mode"] == SesiMode.offline and mk.koordinat_lat:
                    lat = mk.koordinat_lat + random.uniform(-0.0003, 0.0003)
                    lng = mk.koordinat_lng + random.uniform(-0.0003, 0.0003)

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

                if a_def["mode"] == SesiMode.online and st in (PresensiStatus.hadir, PresensiStatus.terlambat):
                    db.add(KodeUsage(
                        sesi_id      = sesi_aktif.id,
                        mahasiswa_id = enroll.mahasiswa_id,
                        used_at      = wp,
                    ))

            db.flush()
            print(f"  → {hadir_count} mahasiswa sudah presensi di sesi aktif ini")

        # ── COMMIT ────────────────────────────────────────────────
        db.commit()

        # ── RINGKASAN ────────────────────────────────────────────
        print("\n" + "=" * 65)
        print("  ✅  SEED BERHASIL!")
        print("=" * 65)
        print(f"\n  Users   : {len(all_user_data)}")
        print(f"  Dosen   : {len(DOSEN_DATA)}")
        print(f"  Mahasiswa: {len(MAHASISWA_DATA)}")
        print(f"  Matakuliah: {len(MATAKULIAH_DATA)}")

        total_sesi = db.query(SesiPresensi).count()
        total_aktif = db.query(SesiPresensi).filter(SesiPresensi.status == SesiStatus.aktif).count()
        total_presensi = db.query(Presensi).count()
        print(f"  Sesi    : {total_sesi} total ({total_aktif} aktif sekarang)")
        print(f"  Presensi: {total_presensi} record")

        print("\n  ─── Akun untuk login ───────────────────────────────────")
        print("  Password semua akun: Password123!")
        print()
        print("  [Admin]")
        print("   NIM/NIDN : ADMIN001")
        print()
        print("  [Dosen — Budi Santoso (IF301, IF201)]")
        print("   NIDN     : 0012038901")
        print()
        print("  [Dosen — Siti Rahayu (IF302, SI201)]")
        print("   NIDN     : 0023047802")
        print()
        print("  [Dosen — Hendra Gunawan (IF401)]")
        print("   NIDN     : 0031056703")
        print()
        print("  [Mahasiswa TI 2021 — Muhammad Rizky Pratama]")
        print("   NIM      : H071211001")
        print()
        print("  [Mahasiswa SI 2021 — Maya Anggraeni Susanti]")
        print("   NIM      : H071411001")
        print()
        print("  [Mahasiswa IK 2021 — Bintang Ramadhan Putra]")
        print("   NIM      : H071311001")

        # Cetak kode sesi aktif
        aktif_sesi = db.query(SesiPresensi).filter(
            SesiPresensi.status    == SesiStatus.aktif,
            SesiPresensi.kode_sesi != None,
        ).all()
        if aktif_sesi:
            print()
            print("  ─── Kode Sesi Online Aktif ─────────────────────────────")
            for s in aktif_sesi:
                mk = db.query(Matakuliah).filter(Matakuliah.id == s.matakuliah_id).first()
                print(f"   {mk.kode if mk else '?'} — {mk.nama[:35] if mk else '?':<35} Kode: {s.kode_sesi}")

        print()
        print("=" * 65)

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