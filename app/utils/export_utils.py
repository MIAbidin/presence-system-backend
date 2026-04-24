# app/utils/export_utils.py
import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from typing import List
from app.models.presensi import Presensi
from app.models.user import User

def generate_excel_rekap(
    presensi_list : List[Presensi],
    nama_matakuliah: str,
    pertemuan_ke  : int
) -> bytes:
    """
    Generate file Excel rekap presensi satu sesi.
    Return bytes — langsung bisa dikirim sebagai file response.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = f"Presensi Pertemuan {pertemuan_ke}"

    # ── Style ──────────────────────────────────────────
    header_font    = Font(bold=True, color="FFFFFF", size=11)
    header_fill    = PatternFill("solid", fgColor="1E3A5F")
    center         = Alignment(horizontal="center", vertical="center")
    thin           = Side(style="thin", color="CBD5E1")
    border         = Border(left=thin, right=thin, top=thin, bottom=thin)

    STATUS_COLOR = {
        "hadir"    : "DCFCE7",
        "terlambat": "FEF3C7",
        "absen"    : "FEE2E2",
        "izin"     : "DBEAFE",
        "sakit"    : "F3E8FF",
    }

    # ── Judul ──────────────────────────────────────────
    ws.merge_cells("A1:G1")
    ws["A1"] = f"Rekap Presensi — {nama_matakuliah} — Pertemuan {pertemuan_ke}"
    ws["A1"].font      = Font(bold=True, size=13, color="1E3A5F")
    ws["A1"].alignment = center

    # ── Header kolom ───────────────────────────────────
    headers = ["No", "NIM", "Nama Mahasiswa", "Status", "Waktu Presensi", "Akurasi Wajah", "Mode Kelas"]
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=2, column=col, value=h)
        cell.font      = header_font
        cell.fill      = header_fill
        cell.alignment = center
        cell.border    = border

    # ── Data ───────────────────────────────────────────
    for i, p in enumerate(presensi_list, start=1):
        row = i + 2
        status_str = p.status.value if p.status else "-"
        fill_color = STATUS_COLOR.get(status_str, "FFFFFF")
        row_fill   = PatternFill("solid", fgColor=fill_color)

        values = [
            i,
            p.mahasiswa.nim_nidn if p.mahasiswa else "-",
            p.mahasiswa.nama_lengkap if p.mahasiswa else "-",
            status_str.upper(),
            p.waktu_presensi.strftime("%H:%M:%S") if p.waktu_presensi else "-",
            f"{p.akurasi_wajah:.1f}%" if p.akurasi_wajah else "-",
            p.mode_kelas.value if p.mode_kelas else "-",
        ]

        for col, val in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.border    = border
            cell.alignment = center
            cell.fill      = row_fill

    # ── Lebar kolom ────────────────────────────────────
    col_widths = [5, 15, 28, 12, 18, 15, 12]
    for i, w in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # ── Simpan ke bytes ────────────────────────────────
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()