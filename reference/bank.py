"""Bank soal STUB untuk uji backend. Bukan bank komersial.
Bank asli: blueprint -> generate -> validasi program -> review sampel (lihat IMPLEMENTATION-PLAN)."""
import random

_STATIC = [
    ("IPA", "Peredaran Darah", 1, "Bagian jantung yang menerima darah kaya oksigen dari paru-paru adalah ...", ["Serambi kiri", "Serambi kanan", "Bilik kanan", "Aorta"], 0),
    ("IPA", "Fotosintesis", 1, "Gas yang diserap daun untuk fotosintesis adalah ...", ["Oksigen", "Nitrogen", "Karbon dioksida", "Hidrogen"], 2),
    ("IPA", "Rangkaian Listrik", 2, "Rangkaian dengan satu jalur arus disebut rangkaian ...", ["Paralel", "Seri", "Campuran", "Terbuka"], 1),
    ("Bahasa Indonesia", "Kata Baku", 1, "Kata baku yang benar adalah ...", ["Analisa", "Analisis", "Analisys", "Anelisis"], 1),
    ("Bahasa Indonesia", "Tanda Baca", 1, "Kalimat dengan tanda baca paling tepat adalah ...", ["Dia pergi,membeli sayur.", "Dia pergi, membeli sayur.", "Dia pergi ,membeli sayur.", "Dia pergi . membeli sayur."], 1),
    ("IPS", "Peta dan Kenampakan", 2, "Selat antara Jawa dan Sumatra adalah Selat ...", ["Sunda", "Malaka", "Makassar", "Bali"], 0),
    ("Verbal", "Antonim", 1, "Antonim kata 'tekun' adalah ...", ["Rajin", "Malas", "Giat", "Gigih"], 1),
]


def get_questions(seed: int) -> list[dict]:
    """12 soal deterministik per seed: 5 Matematika (dihitung program) + 7 statis, urutan diacak."""
    r = random.Random(seed)
    qs = []
    for i in range(5):
        d = r.choice([6, 8, 10]); a = r.randint(1, d // 2 - 1); b = r.randint(1, d // 2 - 1)
        ans = f"{a + b}/{d}"
        wrong = {f"{a + b}/{d * 2}", f"{a + b + 1}/{d}", f"{abs(a - b)}/{d}", f"{a + b + 2}/{d}"} - {ans}
        opts = [ans] + sorted(wrong)[:3]
        r.shuffle(opts)
        qs.append({"id": f"m{seed}-{i}", "subject": "Matematika", "topic": "Pecahan", "level": 1, "q": f"Hitung: {a}/{d} + {b}/{d} = ...", "opts": opts, "ans": opts.index(ans)})
    for j, (s, t, lv, q, o, ai) in enumerate(_STATIC):
        correct = o[ai]; opts = o[:]; r.shuffle(opts)
        qs.append({"id": f"s{j}", "subject": s, "topic": t, "level": lv, "q": q, "opts": opts, "ans": opts.index(correct)})
    r.shuffle(qs)
    for n, q in enumerate(qs, 1):
        q["no"] = n
    return qs


def public(q: dict) -> dict:
    """Bentuk soal yang boleh dikirim ke browser SEBELUM submit: tanpa kunci dan pembahasan."""
    return {k: q[k] for k in ("no", "id", "subject", "topic", "level", "q", "opts")}
