"""Penilaian, klasifikasi pola, matriks waktu, status kesiapan, dan penggabungan spesifikasi drill.

Semua fungsi murni. AI runtime TIDAK menyentuh modul ini: skor dan klasifikasi
adalah fakta yang diberikan ke AI, bukan hasil AI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Optional

# --- ambang DRAFT (perlu persetujuan pemilik; sumber nilai ada di HANDOFF/PDF) ---
WEAK_TOPIC_PCT = 70          # topik di bawah ini = lemah (sama dengan MVP)
SLOW_FACTOR = 1.5            # > 1.5x median = lambat
FAST_FACTOR = 0.5            # < 0.5x median = sangat cepat
SLOW_AVG_SEC = 125           # rata-rata detik/soal (acuan awal sampai ada data kohort)
STATUS_SIAP_MIN = 80         # rata-rata 2 tryout terakhir
STATUS_BELUM_MAX = 60
GOOD_SCORE = 70              # batas "nilai bagus" pada matriks 2x2
MAX_DRILL_TOPICS = 2


@dataclass
class Answer:
    qid: str
    subject: str
    topic: str
    correct_idx: int
    chosen_idx: Optional[int]        # None = kosong
    seconds: float                   # sudah dibersihkan dari waktu idle
    flagged: bool = False
    changes: int = 0                 # berapa kali jawaban diubah
    changed_correct_to_wrong: bool = False


def score(answers: list[Answer]) -> dict:
    """Penilaian biner deterministik. Satu-satunya penentu nilai."""
    subj: dict[str, dict] = {}
    topic: dict[str, dict] = {}
    correct = 0
    for a in answers:
        ok = a.chosen_idx is not None and a.chosen_idx == a.correct_idx
        correct += ok
        for bucket, key in ((subj, a.subject), (topic, a.topic)):
            b = bucket.setdefault(key, {"c": 0, "t": 0})
            b["t"] += 1
            b["c"] += ok
    total = len(answers)
    return {"correct": correct, "total": total,
            "pct": round(100 * correct / total, 1) if total else 0.0,
            "subject": subj, "topic": topic}


def classify(answers: list[Answer]) -> list[dict]:
    """Label pola per soal berdasarkan median waktu tryout itu sendiri (bukan AI).

    tag: 'kosong' | 'cepat_salah' (tebak/kurang teliti) | 'konsep' (salah lambat atau ragu)
         | 'salah' (biasa) | 'benar_lambat' | 'benar'
    """
    times = [a.seconds for a in answers if a.seconds > 0]
    med = median(times) if times else 1.0
    out = []
    for a in answers:
        ok = a.chosen_idx is not None and a.chosen_idx == a.correct_idx
        if a.chosen_idx is None:
            tag = "kosong"
        elif not ok:
            if a.seconds < FAST_FACTOR * med and not a.flagged:
                tag = "cepat_salah"
            elif a.seconds > SLOW_FACTOR * med or a.flagged:
                tag = "konsep"
            else:
                tag = "salah"
        else:
            tag = "benar_lambat" if a.seconds > SLOW_FACTOR * med else "benar"
        out.append({"qid": a.qid, "topic": a.topic, "subject": a.subject, "tag": tag})
    return out


def time_matrix(pct: float, avg_seconds: float) -> dict:
    """Matriks 2x2 nilai x kecepatan (Bab 11). Saran tidak pernah 'lebih cepat' untuk nilai jelek + cepat."""
    good = pct >= GOOD_SCORE
    slow = avg_seconds >= SLOW_AVG_SEC
    cell = {
        (True, False): ("efisien", "Jaga ketelitian, jangan menambah volume latihan."),
        (True, True): ("paham_belum_lancar", "Latih kelancaran: lewati soal sulit lebih dulu, kembali bila waktu tersisa."),
        (False, False): ("terburu_buru", "Minta anak pelan: baca soal sampai habis, tandai ragu daripada menebak. Targetnya lebih teliti, bukan lebih cepat."),
        (False, True): ("konsep_belum_paham", "Kembali ke konsep level bawah dulu. Jangan didesak lebih cepat; kecepatan menyusul setelah paham."),
    }[(good, slow)]
    return {"good": good, "slow": slow, "cell": cell[0], "advice": cell[1]}


MAINT_TOPIC = "Pemeliharaan"          # sesi drill bagi anak tanpa topik lemah


def stamina_drop(answers: list[Answer]) -> bool:
    """Akurasi (hanya soal TERJAWAB) sepertiga terakhir turun >= 20 poin dibanding sepertiga pertama.
    Soal kosong tidak dihitung salah di sini; lihat blank_tail() untuk sinyal terpisah."""
    n = len(answers)
    if n < 6:
        return False
    third = n // 3
    def acc(part):
        part = [a for a in part if a.chosen_idx is not None]
        return None if len(part) < 3 else 100 * sum(1 for a in part if a.chosen_idx == a.correct_idx) / len(part)
    f, l = acc(answers[:third]), acc(answers[-third:])
    return f is not None and l is not None and f - l >= 20


def blank_tail(answers: list[Answer]) -> bool:
    """Banyak soal kosong di sepertiga terakhir (>= 3): biasanya waktu habis, bukan kelelahan."""
    third = len(answers) // 3
    return third > 0 and sum(1 for a in answers[-third:] if a.chosen_idx is None) >= 3


def weak_topics(topic_scores: dict) -> list[dict]:
    """Topik di bawah ambang, terparah dulu. severity: 'berat' < 50 <= 'sedang' < 70."""
    out = []
    for name, v in topic_scores.items():
        pct = round(100 * v["c"] / v["t"]) if v["t"] else 0
        if pct < WEAK_TOPIC_PCT:
            out.append({"topic": name, "c": v["c"], "t": v["t"], "pct": pct,
                        "severity": "berat" if pct < 50 else "sedang"})
    out.sort(key=lambda x: (x["pct"], -x["t"]))
    return out


def merge_drill_specs(specs: list[list[dict]], limit: int = MAX_DRILL_TOPICS) -> list[dict]:
    """Gabungkan daftar topik lemah dari beberapa tryout dalam satu jendela.

    Dilakukan PROGRAM (bukan AI) saat jendela tutup: satu topik dihitung sekali
    dengan pct terburuk; urut dari terparah; dipotong `limit` topik.
    """
    worst: dict[str, dict] = {}
    for spec in specs:
        for w in spec:
            cur = worst.get(w["topic"])
            if cur is None or w["pct"] < cur["pct"]:
                worst[w["topic"]] = w
    merged = sorted(worst.values(), key=lambda x: (x["pct"], x["topic"]))
    return merged[:limit]


def readiness_status(last_two_pct: list[float], any_weak_topic: bool) -> str:
    """Tiga label baku. Bukan prediksi lolos."""
    if not last_two_pct:
        return "Belum Siap"
    avg = sum(last_two_pct[-2:]) / len(last_two_pct[-2:])
    if avg < STATUS_BELUM_MAX:
        return "Belum Siap"
    if avg >= STATUS_SIAP_MIN and not any_weak_topic:
        return "Siap Diuji"
    return "Mengejar"


def clean_seconds(raw_seconds: float, idle_seconds: float, cap: float = 600.0) -> float:
    """Buang waktu idle (tab tidak aktif) dan batasi durasi per soal."""
    return max(0.0, min(raw_seconds - idle_seconds, cap))
