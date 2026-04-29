"""
Seed khusus:
Budi Santoso mengajar 3 matakuliah di hari Rabu
"""

from app.database.db import SessionLocal
from app.models.user import User, UserRole
from app.models.matakuliah import Matakuliah
from app.services.auth_service import hash_password
from datetime import time

def seed():
    db = SessionLocal()
    try:
        print("=== SEED BUDI SANTOSO (RABU) ===")

        # ── 1. DOSEN ─────────────────────────────
        dosen = db.query(User).filter(User.nim_nidn == "0012038901").first()

        if not dosen:
            dosen = User(
                nim_nidn="0012038901",
                nama_lengkap="Dr. Ir. Budi Santoso, M.T.",
                email="budi.santoso@universitashasanuddin.ac.id",
                password_hash=hash_password("Password123!"),
                role=UserRole.dosen,
                program_studi="Teknik Informatika",
                is_active=True,
            )
            db.add(dosen)
            db.flush()
            print("✓ Dosen dibuat")
        else:
            print("⚠ Dosen sudah ada")

        # ── 2. MATAKULIAH RABU (3 MATKUL) ────────
        matkul_list = [
            {
                "kode": "IFR1",
                "nama": "Machine Learning",
                "jam_mulai": time(8, 0),
                "jam_selesai": time(10, 0),
            },
            {
                "kode": "IFR2",
                "nama": "Deep Learning",
                "jam_mulai": time(10, 30),
                "jam_selesai": time(12, 30),
            },
            {
                "kode": "IFR3",
                "nama": "Computer Vision",
                "jam_mulai": time(13, 30),
                "jam_selesai": time(15, 30),
            },
        ]

        for mk_data in matkul_list:
            existing = db.query(Matakuliah).filter(Matakuliah.kode == mk_data["kode"]).first()

            if existing:
                print(f"⚠ Skip: {mk_data['nama']}")
                continue

            mk = Matakuliah(
                kode=mk_data["kode"],
                nama=mk_data["nama"],
                sks=3,
                hari="Rabu",
                jam_mulai=mk_data["jam_mulai"],
                jam_selesai=mk_data["jam_selesai"],
                ruangan="Lab AI",
                koordinat_lat=-5.1300,
                koordinat_lng=119.4890,
                izin_tamu=True,
            )

            db.add(mk)
            db.flush()

            print(f"✓ {mk.kode} - {mk.nama} (Rabu)")

        db.commit()

        print("\n=== SELESAI ===")
        print("Budi Santoso sekarang mengajar 3 matkul di hari Rabu")

    except Exception as e:
        db.rollback()
        print("ERROR:", e)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
