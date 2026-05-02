# app/utils/slot_utils.py
"""
Mapping slot perkuliahan (1–12) ke jam nyata.
Satu slot = 50 menit. Slot 7 dimulai setelah Zuhur (13:00 WIB).

Dipakai di:
- KelasMatakuliah.slot_mulai / slot_selesai
- Import jadwal dari PDF/Excel
- Tampilan frontend (jam otomatis dari pilih slot)
"""
from datetime import time
from typing import Optional, Tuple


SLOT_MAPPING: dict[int, Tuple[time, time]] = {
    1 : (time(7,  0),  time(7,  50)),
    2 : (time(7, 50),  time(8,  40)),
    3 : (time(8, 40),  time(9,  30)),
    4 : (time(9, 30),  time(10, 20)),
    5 : (time(10, 20), time(11, 10)),
    6 : (time(11, 10), time(12,  0)),
    7 : (time(13,  0), time(13, 50)),   # setelah Zuhur
    8 : (time(13, 50), time(14, 40)),
    9 : (time(14, 40), time(15, 30)),
    10: (time(15, 30), time(16, 20)),
    11: (time(16, 20), time(17, 10)),
    12: (time(17, 10), time(18,  0)),
}

# Mapping balik: dari jam mulai ke nomor slot
_JAM_KE_SLOT: dict[time, int] = {v[0]: k for k, v in SLOT_MAPPING.items()}


def slot_ke_jam(slot_mulai: int, slot_selesai: int) -> Tuple[time, time]:
    """
    Return (jam_mulai, jam_selesai) dari slot_mulai dan slot_selesai.

    Contoh: slot_ke_jam(1, 3) → (time(7,0), time(9,30))
    """
    if slot_mulai not in SLOT_MAPPING:
        raise ValueError(f"slot_mulai {slot_mulai} tidak valid (1–12)")
    if slot_selesai not in SLOT_MAPPING:
        raise ValueError(f"slot_selesai {slot_selesai} tidak valid (1–12)")
    if slot_selesai < slot_mulai:
        raise ValueError("slot_selesai harus >= slot_mulai")

    jam_mulai   = SLOT_MAPPING[slot_mulai][0]
    jam_selesai = SLOT_MAPPING[slot_selesai][1]
    return jam_mulai, jam_selesai


def slot_ke_str(slot_mulai: int, slot_selesai: int) -> str:
    """
    Return string jam yang mudah dibaca.
    Contoh: "07:00 – 09:30" untuk slot 1–3
    """
    jam_mulai, jam_selesai = slot_ke_jam(slot_mulai, slot_selesai)
    return f"{jam_mulai.strftime('%H:%M')} – {jam_selesai.strftime('%H:%M')}"


def jam_ke_slot(jam: time) -> Optional[int]:
    """
    Cari nomor slot berdasarkan jam mulai.
    Return None jika tidak match persis.
    """
    return _JAM_KE_SLOT.get(jam)


def get_slot_sekarang() -> Optional[int]:
    """
    Return slot yang sedang aktif sekarang (WIB).
    Dipakai di dashboard untuk menampilkan kelas aktif.
    Return None jika di luar jam kuliah.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    now = datetime.now(ZoneInfo("Asia/Jakarta")).time()
    for slot_num, (mulai, selesai) in SLOT_MAPPING.items():
        if mulai <= now <= selesai:
            return slot_num
    return None


def get_all_slots() -> list[dict]:
    """
    Return semua slot sebagai list dict — untuk dropdown frontend.
    """
    return [
        {
            "slot"       : s,
            "jam_mulai"  : SLOT_MAPPING[s][0].strftime("%H:%M"),
            "jam_selesai": SLOT_MAPPING[s][1].strftime("%H:%M"),
            "label"      : f"Slot {s} ({SLOT_MAPPING[s][0].strftime('%H:%M')} – {SLOT_MAPPING[s][1].strftime('%H:%M')})",
        }
        for s in sorted(SLOT_MAPPING)
    ]