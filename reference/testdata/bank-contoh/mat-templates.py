"""Contoh format template Matematika (BRIEF §7). Fungsi murni, hanya pustaka standar.
Pola aman: susun calon pengecoh dari kesalahan umum, buang yang sama NILAINYA dengan kunci/pengecoh lain,
lalu isi kekurangan dengan cadangan yang juga bermakna."""
from fractions import Fraction


def _pick(correct_val, cands, fmt):
    out, seen = [], {correct_val}
    for v in cands:
        if v is not None and v > 0 and v not in seen:
            out.append(fmt(v)); seen.add(v)
        if len(out) == 3: break
    return out


def mat_pec_tambah(rng):
    d = rng.choice([6, 8, 10, 12]); a = rng.randint(1, d // 2 - 1); b = rng.randint(1, d // 2 - 1)
    s = Fraction(a + b, d)
    f = lambda v: f"{v.numerator}/{v.denominator}"
    cands = [Fraction(a + b, 2 * d), Fraction(a * b, d), Fraction(a + b + 1, d), Fraction(a + b, d + 1), Fraction(a + b + 2, d), Fraction(abs(a - b) or 1, d)]
    return {"topic": "MAT-PEC", "level": 1, "stem": f"Hitung: {a}/{d} + {b}/{d} = ... (bentuk paling sederhana)",
            "correct": f(s), "distractors": _pick(s, cands, f),
            "explanation": "Penyebut sama, jadi pembilang dijumlahkan dan penyebut tetap, lalu disederhanakan. Menjumlahkan penyebut adalah kesalahan umum.",
            "shortcut": "Penyebut sama: jumlahkan atasnya saja, bawahnya tetap, lalu sederhanakan."}


def mat_psn_diskon(rng):
    harga = rng.choice([20, 40, 60, 80, 120, 150]) * 1000; p = rng.choice([10, 20, 25, 50])
    bayar = harga * (100 - p) // 100; potong = harga * p // 100
    rp = lambda v: "Rp" + f"{v:,}".replace(",", ".")
    cands = [potong, harga - p * 100, harga + potong, harga, harga - p * 1000, bayar - potong]
    return {"topic": "MAT-PSN", "level": 2, "stem": f"Harga sebuah tas {rp(harga)}. Tas itu didiskon {p}%. Berapa yang harus dibayar?",
            "correct": rp(bayar), "distractors": _pick(bayar, cands, rp),
            "explanation": "Diskon adalah potongan dari harga. Hitung potongan, lalu kurangkan dari harga awal. Pengecoh pertama hanya besar potongannya.",
            "shortcut": "Bayar = harga x (100 - diskon)/100."}
