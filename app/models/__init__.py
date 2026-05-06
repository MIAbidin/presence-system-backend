# app/models/__init__.py
# Update Fase E: tambah import KonfigurasiSistem
# Import semua model agar Alembic bisa autogenerate migration dengan benar.
# Urutan import tidak boleh berubah — ada dependency antar model.

from app.models.user import User
from app.models.face_embedding import FaceEmbedding
from app.models.matakuliah import Matakuliah
from app.models.jadwal_pengganti import JadwalPengganti
from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
from app.models.sesi import SesiPresensi
from app.models.kode_usage import KodeUsage
from app.models.presensi import Presensi
from app.models.ruangan import Ruangan
from app.models.kelas_matakuliah import KelasMatakuliah
from app.models.audit_log import AuditLog
from app.models.program_studi import ProgramStudi
from app.models.konfigurasi_sistem import KonfigurasiSistem   # ← Fase E