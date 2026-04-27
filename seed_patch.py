# seed_patch.py
# ─────────────────────────────────────────────────────────────
# PATCH untuk seed.py yang sudah ada.
# Jalankan SETELAH alembic upgrade head untuk Fase 1.
#
# Apa yang dilakukan script ini:
# 1. Set izin_tamu = TRUE untuk matakuliah "Pemrograman Mobile"
#    (sebagai contoh matakuliah yang open untuk tamu)
# 2. Set izin_tamu = FALSE untuk matakuliah lain (default, tapi eksplisit)
# 3. Insert 2 contoh jadwal pengganti untuk testing
# 4. Insert 1 contoh mahasiswa tamu manual untuk testing
#
# Jalankan: python seed_patch.py
# ─────────────────────────────────────────────────────────────

from datetime import time
from app.database.db import SessionLocal
from app.models.matakuliah import Matakuliah
from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
from app.models.jadwal_pengganti import JadwalPengganti
from app.models.user import User, UserRole


def patch():
    db = SessionLocal()
    try:
        print("🔧 Menjalankan seed patch Fase 1...\n")

        # ── 1. Set izin_tamu per matakuliah ──────────────────
        mk_list = db.query(Matakuliah).all()

        for mk in mk_list:
            if mk.kode == "IF301":
                # Pemrograman Mobile: izin tamu aktif (untuk demo)
                mk.izin_tamu = True
                print(f"  ✓ {mk.nama} ({mk.kode}) → izin_tamu = TRUE")
            else:
                # Matakuliah lain: tertutup by default
                mk.izin_tamu = False
                print(f"  ✓ {mk.nama} ({mk.kode}) → izin_tamu = FALSE")

        db.flush()

        # ── 2. Insert contoh jadwal pengganti ────────────────
        mk_if301 = db.query(Matakuliah).filter(Matakuliah.kode == "IF301").first()
        dosen    = db.query(User).filter(User.role == UserRole.dosen).first()

        if mk_if301 and dosen:
            # Cek apakah sudah ada
            existing = db.query(JadwalPengganti).filter(
                JadwalPengganti.matakuliah_id == mk_if301.id,
                JadwalPengganti.pertemuan_ke  == 3,
            ).first()

            if not existing:
                jp = JadwalPengganti(
                    matakuliah_id    = mk_if301.id,
                    dosen_id         = dosen.id,
                    pertemuan_ke     = 3,
                    jam_mulai_baru   = time(10, 0),
                    jam_selesai_baru = time(12, 30),
                    ruangan_baru     = "C-202",
                    keterangan       = "Pindah ke C-202, 13 Apr — ruang Lab dipakai seminar"
                )
                db.add(jp)
                print(f"  ✓ Jadwal pengganti pertemuan 3 → 10:00–12:30, Ruang C-202")
            else:
                print(f"  ⚠ Jadwal pengganti pertemuan 3 sudah ada, skip")

        # ── 3. Insert contoh mahasiswa tamu manual ────────────
        mk_if301 = db.query(Matakuliah).filter(Matakuliah.kode == "IF301").first()
        mk_if302 = db.query(Matakuliah).filter(Matakuliah.kode == "IF302").first()

        # Ambil mahasiswa dari IF302 (Basis Data Lanjut) yang mau dijadikan tamu di IF301
        # Dalam seed asli, semua mahasiswa sudah enroll ke semua matakuliah.
        # Di sini kita update salah satunya jadi "tamu" sebagai contoh.
        if mk_if301 and mk_if302:
            # Cari Rizky Maulana (2021001003) sebagai contoh tamu
            rizky = db.query(User).filter(User.nim_nidn == "2021001003").first()

            if rizky and mk_if302:
                # Update row yang sudah ada di IF301 jadi status tamu
                row_di_if301 = db.query(MahasiswaMatakuliah).filter(
                    MahasiswaMatakuliah.mahasiswa_id  == rizky.id,
                    MahasiswaMatakuliah.matakuliah_id == mk_if301.id,
                ).first()

                if row_di_if301:
                    row_di_if301.is_tamu    = True
                    row_di_if301.kelas_asal = f"{mk_if302.kode} - Kelas B"
                    print(f"  ✓ {rizky.nama_lengkap} ditandai sebagai tamu "
                          f"di {mk_if301.nama} (kelas asal: {mk_if302.kode} Kelas B)")
                else:
                    print(f"  ⚠ Row MahasiswaMatakuliah tidak ditemukan untuk Rizky di IF301")
            else:
                print("  ⚠ Mahasiswa atau matakuliah tidak ditemukan, skip contoh tamu")

        db.commit()
        print("\n✅ Seed patch Fase 1 selesai!")
        print("\nData yang tersedia untuk testing:")
        print("  - Pemrograman Mobile (IF301): izin_tamu = TRUE")
        print("  - Basis Data Lanjut  (IF302): izin_tamu = FALSE")
        print("  - Jadwal pengganti pertemuan 3: 10:00–12:30, Ruang C-202")
        print("  - Rizky Maulana (2021001003): tamu di IF301, kelas asal IF302 Kelas B")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    patch()