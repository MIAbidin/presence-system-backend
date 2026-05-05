# app/models/__init__.py
# Import semua model agar Alembic bisa autogenerate migration dengan benar.
# Urutan import tidak boleh berubah — ada dependency antar model.

from app.models.user import User
from app.models.face_embedding import FaceEmbedding
from app.models.matakuliah import Matakuliah          # sudah ada + izin_tamu (baru)
from app.models.jadwal_pengganti import JadwalPengganti  # ← Fase 1
from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah  # sudah ada + is_tamu, kelas_asal, kelas_id (baru)
from app.models.sesi import SesiPresensi
from app.models.kode_usage import KodeUsage
from app.models.presensi import Presensi
from app.models.ruangan import Ruangan                # ← Fase A
from app.models.kelas_matakuliah import KelasMatakuliah  # ← Fase B
from app.models.audit_log import AuditLog
from app.models.program_studi import ProgramStudi  # ← Fase D