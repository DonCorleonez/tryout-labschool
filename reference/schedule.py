"""Jadwal jendela tryout/drill. Modul murni (tanpa I/O) untuk dipakai backend dan tes.

Aturan terkunci (HANDOFF v1.1):
- Drill   : Senin 06.00 - Jumat 15.00
- Tryout  : Jumat 17.00 - Minggu 16.00
- Dua jendela tidak pernah bersamaan; Jumat 15.00-17.00 adalah celah penyangga.
- Tryout per akhir pekan: 1x, kecuali jendela intensif ke-10 dan ke-11 = 2x.
- Sabtu 23 Jan 2027 (simulasi resmi sekolah) = blackout tryout.
Semua waktu WIB (UTC+7), disimpan sebagai datetime aware.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

WIB = timezone(timedelta(hours=7))

FIRST_FRIDAY = datetime(2026, 11, 6, tzinfo=WIB)
TEST_START = datetime(2027, 1, 31, 8, 0, tzinfo=WIB)
TEST_END = datetime(2027, 1, 31, 12, 0, tzinfo=WIB)
GATE_PRESTASI = datetime(2026, 12, 9, tzinfo=WIB)
BLACKOUT_DAY = datetime(2027, 1, 23, tzinfo=WIB)  # simulasi resmi sekolah

# jumlah tryout per jendela (akhir pekan) dan fasenya
PLAN = [1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 1]
PHASES = [
    "Diagnostik",
    "Fondasi", "Fondasi", "Fondasi", "Fondasi", "Fondasi",
    "Akselerasi", "Akselerasi", "Akselerasi",
    "Intensif", "Intensif",
    "Gladi bersih",
]
TOTAL_TRYOUTS = sum(PLAN)  # 14


@dataclass(frozen=True)
class Window:
    k: int                 # 1..12
    n_tryouts: int
    phase: str
    friday: datetime
    tryout_open: datetime
    tryout_close: datetime
    drill_open: datetime   # drill untuk hasil jendela ini, minggu berikutnya
    drill_close: datetime

    @property
    def is_taper(self) -> bool:
        return self.k == len(PLAN)


def build_windows() -> list[Window]:
    out = []
    for i, n in enumerate(PLAN):
        fri = FIRST_FRIDAY + timedelta(days=7 * i)
        out.append(Window(
            k=i + 1, n_tryouts=n, phase=PHASES[i], friday=fri,
            tryout_open=fri + timedelta(hours=17),
            tryout_close=fri + timedelta(days=2, hours=16),
            drill_open=fri + timedelta(days=3, hours=6),
            drill_close=fri + timedelta(days=7, hours=15),
        ))
    return out


WINDOWS = build_windows()


@dataclass(frozen=True)
class ClockState:
    kind: str                       # lihat KINDS
    window: Optional[Window] = None  # jendela sumber (tryout: jendela berjalan; drill: jendela asal hasil)
    opens_at: Optional[datetime] = None
    closes_at: Optional[datetime] = None


KINDS = ("pre", "tryout", "blackout", "drill", "taper", "gap", "proses", "jelang_tes", "hari_tes", "post")


def clock_state(now: datetime) -> ClockState:
    """Status jam sistem pada waktu `now`. Tepat satu jenis berlaku pada satu waktu."""
    w0 = WINDOWS[0]
    if now < w0.tryout_open:
        return ClockState("pre", None, opens_at=w0.tryout_open)

    for w in WINDOWS:
        if w.tryout_open <= now < w.tryout_close:
            day0 = BLACKOUT_DAY
            if day0 <= now < day0 + timedelta(days=1):
                return ClockState("blackout", w, closes_at=w.tryout_close)
            return ClockState("tryout", w, closes_at=w.tryout_close)
        if w.drill_open <= now < w.drill_close:
            return ClockState("taper" if w.is_taper else "drill", w, closes_at=w.drill_close)

    for i, w in enumerate(WINDOWS):
        if w.tryout_close <= now < w.drill_open:
            return ClockState("proses", w, opens_at=w.drill_open)
        nxt = WINDOWS[i + 1] if i + 1 < len(WINDOWS) else None
        if nxt and w.drill_close <= now < nxt.tryout_open:
            return ClockState("gap", nxt, opens_at=nxt.tryout_open)

    last = WINDOWS[-1]
    if last.drill_close <= now < TEST_START:
        return ClockState("jelang_tes", last, opens_at=TEST_START)
    if TEST_START <= now < TEST_END:
        return ClockState("hari_tes", last)
    return ClockState("post", last)


def current_window_index(now: datetime) -> int:
    """Jumlah jendela yang sudah mulai (tryout_open <= now). 0 bila belum mulai."""
    return sum(1 for w in WINDOWS if w.tryout_open <= now)


# ---------- paket dan urutan tryout per keluarga ----------

def join_window(now: datetime) -> int:
    """Jendela tempat pembeli baru memulai diagnostik: jendela yang sedang terbuka,
    atau jendela berikutnya bila tidak ada yang terbuka."""
    st = clock_state(now)
    if st.kind in ("tryout", "blackout"):
        return st.window.k if st.kind == "tryout" else min(st.window.k + 1, len(WINDOWS))
    for w in WINDOWS:
        if w.tryout_open > now:
            return w.k
    return len(WINDOWS)


def tryout_ids(join_k: int, k: int, plan: str = "utama") -> list[str]:
    """ID tryout yang tersedia untuk sebuah keluarga pada jendela k.

    - sebelum jendela gabung: kosong (tidak digulung)
    - jendela gabung: satu diagnostik
    - sesudahnya: mengikuti kalender kohort
    - paket gratis: hanya diagnostik
    """
    if join_k <= 0 or k < join_k:
        return []
    if k == join_k:
        return ["DIAG"]
    if plan == "free":
        return []
    return [f"TO{k}-{i}" for i in range(1, WINDOWS[k - 1].n_tryouts + 1)]


def total_for_family(join_k: int, plan: str = "utama") -> int:
    return sum(len(tryout_ids(join_k, w.k, plan)) for w in WINDOWS)


def can_open_tryout(ids: list[str], done: set[str], target: str) -> bool:
    """Tryout ke-2 di akhir pekan yang sama baru terbuka setelah yang pertama dikumpulkan."""
    if target not in ids:
        return False
    i = ids.index(target)
    return all(x in done for x in ids[:i])
