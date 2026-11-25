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


def _stub_questions(seed: int) -> list[dict]:
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


_BANK = None          # bankfile.Bank bila BANK_DIR dikonfigurasi; None = STUB


def configure(folder):
    """Muat bank berkas (tervalidasi). Mengembalikan objek Bank agar pemanggil bisa melapor/menolak start."""
    global _BANK
    if not folder:
        _BANK = None; return None
    from bankfile import Bank
    _BANK = Bank.load(folder)
    return _BANK


def get_questions(seed: int) -> list[dict]:
    """Soal deterministik per seed. Bank berkas bila ada, kalau tidak STUB (hanya untuk uji)."""
    if _BANK is not None and (_BANK.items or _BANK.templates):
        return _BANK.build_tryout(seed)
    return _stub_questions(seed)


def public(q: dict) -> dict:
    """Bentuk soal yang boleh dikirim ke browser SEBELUM submit: tanpa kunci dan pembahasan."""
    out = {k: q[k] for k in ("no", "id", "subject", "topic", "level", "q", "opts")}
    if q.get("passage"): out["passage"] = q["passage"]
    return out


def get_drill_questions(topic: str, seed: int, count: int = 5, exclude: set | None = None) -> list[dict]:
    """Ambil soal drill deterministik untuk `topic` tertentu (atau Pemeliharaan)."""
    if _BANK is not None and (_BANK.items or _BANK.templates):
        qs = _BANK.build_drill(topic, seed, count=count, exclude=exclude)
        if qs:
            return qs
    r = random.Random(seed)
    if topic == "Pemeliharaan":
        pool = [q for q in _stub_questions(seed) if q["level"] >= 1]
        r.shuffle(pool)
        out = pool[:count]
        for idx, q in enumerate(out, 1):
            q["no"] = idx
            q.setdefault("subtopic", q["topic"])
            q.setdefault("explanation", "Periksa kembali konsep dasar dan langkah pengerjaan soal ini.")
            q.setdefault("shortcut", "Eliminasi opsi yang paling tidak sesuai lebih dahulu.")
        return out
    # Cocokkan topik pada stub statis atau pecahan
    if topic.lower() == "pecahan":
        qs = [q for q in _stub_questions(seed) if q["topic"].lower() == "pecahan"]
        for i in range(len(qs), count):
            d = r.choice([6, 8, 10, 12]); a = r.randint(1, d // 2 - 1); b = r.randint(1, d // 2 - 1)
            ans = f"{a + b}/{d}"
            wrong = {f"{a + b}/{d * 2}", f"{a + b + 1}/{d}", f"{abs(a - b)}/{d}", f"{a + b + 2}/{d}"} - {ans}
            opts = [ans] + sorted(wrong)[:3]; r.shuffle(opts)
            qs.append({"id": f"dm{seed}-{i}", "subject": "Kuantitatif", "topic": "Pecahan", "subtopic": "Penjumlahan pecahan",
                       "level": 1, "q": f"Hitung: {a}/{d} + {b}/{d} = ...", "opts": opts, "ans": opts.index(ans),
                       "explanation": "Karena penyebut sudah sama, jumlahkan pembilang dan pertahankan penyebut.",
                       "shortcut": "Penyebut sama: jumlahkan bagian atasnya saja."})
        for idx, q in enumerate(qs[:count], 1):
            q["no"] = idx
            q.setdefault("subtopic", "Pecahan dasar")
            q.setdefault("explanation", "Samakan penyebut terlebih dahulu sebelum menjumlahkan pembilang.")
            q.setdefault("shortcut", "Penyebut sama: jumlahkan pembilangnya saja.")
        return qs[:count]
    matching = [x for x in _STATIC if x[1].lower() == topic.lower()]
    if matching:
        subj, tname, lvl, stem, o, ai = matching[0]
    else:
        subj, tname, lvl = "Latihan Terpandu", topic, 2
        stem = f"Manakah pernyataan yang paling tepat terkait topik {topic}?"
        o = [f"Konsep inti {topic} diterapkan sesuai kaidah", f"Mengabaikan prinsip dasar {topic}",
             f"Menukar hubungan sebab-akibat pada {topic}", f"Menggunakan definisi yang tidak berkaitan dengan {topic}"]
        ai = 0
    out = []
    for i in range(count):
        if i < len(matching):
            subj, tname, lvl, stem_i, opts_src, ans_i = matching[i]
        else:
            stem_i = stem if i == 0 else f"Latihan {i + 1} ({tname}): {stem}"
            opts_src, ans_i = o, ai
        correct = opts_src[ans_i]; opts = opts_src[:]; r.shuffle(opts)
        out.append({"no": i + 1, "id": f"dr-{seed}-{i}", "subject": subj, "topic": tname, "subtopic": tname,
                    "level": lvl, "q": stem_i, "opts": opts, "ans": opts.index(correct),
                    "explanation": f"Pembahasan untuk topik {tname}: perhatikan kata kunci utama pada soal sebelum memilih.",
                    "shortcut": f"Fokus pada ciri utama {tname} dan eliminasi opsi pengecoh."})
    return out
