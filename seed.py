"""
seed.py — Insert data dummy untuk testing.
Jalankan: python seed.py
Data: 1 admin, 2 dosen, 10 mahasiswa
Password semua akun: password123
"""
from app.database.db import SessionLocal, engine
from app.models.user import User, UserRole, Base
from app.services.auth_service import hash_password

# Pastikan tabel sudah ada
Base.metadata.create_all(bind=engine)

USERS = [
    # ── Admin ────────────────────────────────────────────
    {
        "nim_nidn"     : "ADMIN001",
        "nama_lengkap" : "Administrator Sistem",
        "email"        : "admin@kampus.ac.id",
        "role"         : UserRole.admin,
        "program_studi": "Sistem Informasi",
    },
    # ── Dosen ────────────────────────────────────────────
    {
        "nim_nidn"     : "1234567890",
        "nama_lengkap" : "Dr. Budi Santoso, M.Kom",
        "email"        : "budi.santoso@kampus.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "0987654321",
        "nama_lengkap" : "Siti Rahayu, S.T., M.T.",
        "email"        : "siti.rahayu@kampus.ac.id",
        "role"         : UserRole.dosen,
        "program_studi": "Sistem Informasi",
    },
    # ── Mahasiswa (10 orang) ─────────────────────────────
    {
        "nim_nidn"     : "2021001001",
        "nama_lengkap" : "Ahmad Fauzi",
        "email"        : "ahmad.fauzi@student.kampus.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "2021001002",
        "nama_lengkap" : "Dewi Lestari",
        "email"        : "dewi.lestari@student.kampus.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "2021001003",
        "nama_lengkap" : "Rizky Maulana",
        "email"        : "rizky.maulana@student.kampus.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "2021001004",
        "nama_lengkap" : "Nurul Hidayah",
        "email"        : "nurul.hidayah@student.kampus.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "2021001005",
        "nama_lengkap" : "Fajar Setiawan",
        "email"        : "fajar.setiawan@student.kampus.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "2021001006",
        "nama_lengkap" : "Anisa Putri",
        "email"        : "anisa.putri@student.kampus.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "2021001007",
        "nama_lengkap" : "Bagas Pratama",
        "email"        : "bagas.pratama@student.kampus.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "2021001008",
        "nama_lengkap" : "Indah Permata",
        "email"        : "indah.permata@student.kampus.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
    {
        "nim_nidn"     : "2021001009",
        "nama_lengkap" : "Dimas Ardiansyah",
        "email"        : "dimas.ardiansyah@student.kampus.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Sistem Informasi",
    },
    {
        "nim_nidn"     : "2021001010",
        "nama_lengkap" : "Sari Wulandari",
        "email"        : "sari.wulandari@student.kampus.ac.id",
        "role"         : UserRole.mahasiswa,
        "program_studi": "Teknik Informatika",
    },
]

def seed():
    db = SessionLocal()
    try:
        skipped = 0
        inserted = 0
        for data in USERS:
            # Cek apakah user sudah ada (hindari duplicate)
            existing = db.query(User).filter(User.nim_nidn == data["nim_nidn"]).first()
            if existing:
                print(f"  ⚠  Skip (sudah ada): {data['nama_lengkap']}")
                skipped += 1
                continue

            user = User(
                nim_nidn      = data["nim_nidn"],
                nama_lengkap  = data["nama_lengkap"],
                email         = data["email"],
                password_hash = hash_password("password123"),
                role          = data["role"],
                program_studi = data["program_studi"],
            )
            db.add(user)
            print(f"  ✓  Insert: {data['nama_lengkap']} ({data['role'].value})")
            inserted += 1

        db.commit()
        print(f"\n✅ Selesai! {inserted} user ditambahkan, {skipped} dilewati.")
        print("   Password semua akun: password123")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🌱 Seeding database presensi_db...\n")
    seed()