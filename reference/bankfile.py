"""Bank soal berkas: muat + validasi butir JSONL dan template Matematika sesuai BRIEF-CHATGPT-bank-soal.md (1 Nov 2026).

Berkas di BANK_DIR:
  *.jsonl          satu objek per baris: butir (punya "id") atau bacaan (punya "passage_id" + "text", tanpa "id")
  *templates*.py   fungsi Python murni `mat_*(rng)` -> {topic, level, stem, correct, distractors[3], explanation, shortcut}
Validator dipakai di dua tempat: CLI `python3 bankcheck.py DIR` (umpan balik ke ChatGPT) dan saat server memuat bank
(butir gagal / ambiguous TIDAK dimuat).
"""
from __future__ import annotations

import importlib.util, json, random, re
from collections import Counter
from pathlib import Path

# ---- taksonomi kanonik (BRIEF §4) ----
TAXONOMY = {
    "Kuantitatif": {"MAT-PEC": "Pecahan", "MAT-KPK": "KPK dan FPB", "MAT-PBD": "Perbandingan dan Skala", "MAT-PSN": "Persen dan Uang",
                    "MAT-BIL": "Bilangan Bulat dan Operasi Hitung", "MAT-GEO": "Bangun Datar dan Bangun Ruang", "MAT-SAT": "Satuan dan Konversi",
                    "MAT-DAT": "Data dan Rata-rata", "MAT-POL": "Pola Bilangan", "MAT-KEC": "Kecepatan, Jarak, Waktu"},
    "Pemahaman Bacaan": {"BAC-GAG": "Gagasan Utama", "BAC-INF": "Informasi Tersurat dan Tersirat", "BAC-SIM": "Simpulan dan Tujuan Penulis",
                         "BAC-MKN": "Makna Kata dalam Konteks"},
    "Verbal": {"VER-ANT": "Antonim", "VER-SIN": "Sinonim", "VER-ANA": "Analogi", "VER-KLS": "Klasifikasi / Kata yang Berbeda",
               "VER-BKU": "Kata Baku dan Tanda Baca"},
    "IPA": {"IPA-PDR": "Peredaran Darah dan Pernapasan", "IPA-FOT": "Fotosintesis dan Tumbuhan", "IPA-LIS": "Listrik dan Rangkaian",
            "IPA-GYA": "Gaya, Gerak, dan Energi", "IPA-WUJ": "Zat, Wujud, dan Perubahannya", "IPA-EKO": "Ekosistem dan Makhluk Hidup",
            "IPA-BMI": "Bumi dan Tata Surya"},
    "IPS": {"IPS-PET": "Peta dan Kenampakan Alam", "IPS-EKN": "Kegiatan Ekonomi", "IPS-KEB": "Keberagaman dan Kehidupan Sosial",
            "IPS-SEJ": "Sejarah dan Peninggalan", "IPS-IDN": "Wilayah Indonesia dan ASEAN"},
}
TOPIC_SUBJECT = {code: subj for subj, d in TAXONOMY.items() for code in d}
TOPIC_NAME = {code: name for d in TAXONOMY.values() for code, name in d.items()}

# komposisi SEMENTARA per tryout (BRIEF §3; belum dikunci pemilik)
COMPOSITION = {"Kuantitatif": 12, "Pemahaman Bacaan": 8, "Verbal": 6, "IPA": 8, "IPS": 6}
FORBIDDEN_OPTS = re.compile(r"^(semua (benar|salah|jawaban)|.*\b[a-d] dan [a-d] benar\b|tidak ada (yang )?benar)", re.I)
ID_RX = re.compile(r"^(?P<topic>[A-Z]{3}-[A-Z]{3})-L(?P<level>[123])-(?P<n>\d{4})$")
REQ = ("id", "version", "subject", "topic", "level", "type", "stem", "options", "answer_idx", "explanation", "shortcut", "est_seconds")
_norm = lambda s: re.sub(r"\W+", " ", str(s).lower()).strip()


def validate_item(it: dict, passages: set) -> list[str]:
    """Daftar alasan gagal (kosong = lolos). Peringatan non-fatal tidak di sini."""
    e = [f"bidang '{k}' tidak ada" for k in REQ if k not in it]
    if e: return e
    m = ID_RX.match(str(it["id"]))
    if not m: e.append("format id harus {TOPIK}-L{level}-{4 digit}")
    elif m["topic"] != it["topic"] or int(m["level"]) != it["level"]: e.append("id tidak cocok dengan topic/level")
    if it["topic"] not in TOPIC_SUBJECT: e.append(f"topik '{it['topic']}' bukan topik kanonik")
    elif TOPIC_SUBJECT[it["topic"]] != it["subject"]: e.append(f"subject harus '{TOPIC_SUBJECT[it['topic']]}' untuk {it['topic']}")
    if it["topic"].startswith("MAT-"): e.append("Kuantitatif wajib template, bukan butir JSONL")
    if it["level"] not in (1, 2, 3): e.append("level harus 1, 2, atau 3")
    if it["type"] != "pg4": e.append("type harus 'pg4'")
    if not isinstance(it["version"], int) or it["version"] < 1: e.append("version harus bilangan bulat >= 1")
    o = it["options"]
    if not (isinstance(o, list) and len(o) == 4 and all(isinstance(x, str) and x.strip() for x in o)): e.append("options harus 4 teks tidak kosong")
    else:
        if len({_norm(x) for x in o}) != 4: e.append("ada opsi duplikat")
        if any(FORBIDDEN_OPTS.match(x.strip()) for x in o): e.append("opsi terlarang (semua benar/salah, A dan B benar, ...)")
        if isinstance(it["answer_idx"], int) and 0 <= it["answer_idx"] <= 3:
            key = _norm(o[it["answer_idx"]])
            if len(key) >= 5 and key in _norm(it["stem"]) and not any(len(_norm(x)) >= 5 and _norm(x) in _norm(it["stem"]) for i, x in enumerate(o) if i != it["answer_idx"]):
                e.append("kunci bocor di stem (teks kunci muncul di soal)")
    if not (isinstance(it["answer_idx"], int) and 0 <= it["answer_idx"] <= 3): e.append("answer_idx harus 0-3")
    if len(str(it["stem"]).strip()) < 8: e.append("stem terlalu pendek")
    if len(str(it["explanation"]).strip()) < 20: e.append("explanation kosong/terlalu pendek")
    if len(str(it["shortcut"]).strip()) < 10: e.append("shortcut kosong/terlalu pendek")
    if it.get("shortcut_scope", "umum") not in ("umum", "terbatas"): e.append("shortcut_scope harus 'umum' atau 'terbatas'")
    if not (isinstance(it["est_seconds"], int) and 15 <= it["est_seconds"] <= 300): e.append("est_seconds 15-300")
    if it.get("image") not in (None, {}): e.append("batch awal tidak boleh bergambar (image harus null)")
    pid = it.get("passage_id")
    if it["topic"].startswith("BAC-") and not pid: e.append("soal bacaan wajib passage_id")
    if pid and pid not in passages: e.append(f"passage_id '{pid}' tidak ditemukan")
    return e


def _num(x):
    from fractions import Fraction
    t = str(x).replace("Rp", "").replace(".", "").replace(" ", "").replace(",", ".")
    try:
        return Fraction(t)
    except (ValueError, ZeroDivisionError):
        return None


def _same_value(opts) -> bool:
    vals = [_num(o) for o in opts]
    return all(v is not None for v in vals) and len(set(vals)) != len(vals)


def validate_template_output(out: dict) -> list[str]:
    e = []
    for k in ("topic", "level", "stem", "correct", "distractors", "explanation", "shortcut"):
        if k not in out: e.append(f"keluaran tanpa '{k}'")
    if e: return e
    if out["topic"] not in TOPIC_SUBJECT or not out["topic"].startswith("MAT-"): e.append("topik template harus MAT-* kanonik")
    if out["level"] not in (1, 2, 3): e.append("level 1-3")
    d = out["distractors"]
    if not (isinstance(d, list) and len(d) == 3): e.append("distractors harus 3")
    else:
        allv = [_norm(out["correct"])] + [_norm(x) for x in d]
        if len(set(allv)) != 4: e.append("kunci/pengecoh kembar")
        elif _same_value([out["correct"], *d]): e.append("dua opsi bernilai sama (mis. 2/4 dan 1/2)")
        if any(not str(x).strip() for x in [out["correct"], *d]): e.append("opsi kosong")
    if len(str(out["explanation"])) < 20 or len(str(out["shortcut"])) < 10: e.append("explanation/shortcut terlalu pendek")
    return e


def load_templates(path: Path) -> dict:
    """Muat fungsi mat_* dari berkas Python. Berkas template ditinjau manusia sebelum ditaruh di server."""
    spec = importlib.util.spec_from_file_location("tpl_" + path.stem.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return {n: f for n, f in vars(mod).items() if n.startswith("mat_") and callable(f)}


def check_template(fn, seeds: int = 1000) -> list[str]:
    errs = Counter()
    for s in range(seeds):
        try:
            for x in validate_template_output(fn(random.Random(s))): errs[x] += 1
        except Exception as ex:                       # noqa: BLE001
            errs[f"galat: {type(ex).__name__}: {ex}"] += 1
    return [f"{msg} ({n}/{seeds} seed)" for msg, n in errs.most_common()]


class Bank:
    """Bank tervalidasi di memori. Hanya butir lolos & tidak ambiguous yang bisa dipakai tryout."""

    def __init__(self):
        self.items, self.passages, self.templates = {}, {}, {}
        self.rejected: list[tuple[str, str, list[str]]] = []      # (berkas, id, alasan)
        self.warnings: list[str] = []

    @classmethod
    def load(cls, folder) -> "Bank":
        b = cls(); folder = Path(folder); raw = []
        for f in sorted(folder.glob("*.jsonl")):
            for ln, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip(): continue
                try:
                    o = json.loads(line)
                except ValueError as ex:
                    b.rejected.append((f.name, f"baris {ln}", [f"JSON tidak valid: {ex}"])); continue
                if "id" not in o and "passage_id" in o and "text" in o:
                    words = len(str(o["text"]).split())
                    if not 120 <= words <= 250: b.warnings.append(f"{f.name}: bacaan {o['passage_id']} {words} kata (target 120-250)")
                    b.passages[o["passage_id"]] = o
                else:
                    raw.append((f.name, ln, o))
        seen_stem = {}
        for fname, ln, it in raw:
            iid = str(it.get("id", f"baris {ln}"))
            errs = validate_item(it, set(b.passages))
            if iid in b.items: errs.append("id duplikat")
            st = _norm(it.get("stem", "")) + "|" + str(it.get("passage_id"))
            if st in seen_stem and not errs: errs.append(f"stem kembar dengan {seen_stem[st]}")
            if errs:
                b.rejected.append((fname, iid, errs)); continue
            seen_stem[st] = iid
            if it.get("ambiguous"):
                b.rejected.append((fname, iid, ["ditandai ambiguous: tunggu tinjauan manusia"])); continue
            b.items[iid] = it
        for f in sorted(folder.glob("*templates*.py")):
            try:
                fns = load_templates(f)
            except Exception as ex:                   # noqa: BLE001
                b.rejected.append((f.name, "(modul)", [f"gagal dimuat: {ex}"])); continue
            for n, fn in fns.items():
                errs = check_template(fn)
                if errs: b.rejected.append((f.name, n, errs))
                else: b.templates[n] = fn
        return b

    # ---- laporan untuk ChatGPT/peninjau ----
    def report(self) -> str:
        it = list(self.items.values())
        keys = Counter("ABCD"[x["answer_idx"]] for x in it); n = len(it) or 1
        lines = [f"Butir lolos: {len(it)} · bacaan: {len(self.passages)} · template lolos: {len(self.templates)} · ditolak: {len(self.rejected)}",
                 "Sebaran kunci: " + ", ".join(f"{k} {keys[k] * 100 / n:.0f}%" for k in "ABCD") +
                 ("  [PERINGATAN: di luar 22-28%]" if it and any(not 22 <= keys[k] * 100 / n <= 28 for k in "ABCD") else ""),
                 "Per mata uji: " + ", ".join(f"{s} {c}" for s, c in Counter(x["subject"] for x in it).most_common()),
                 "Per level: " + ", ".join(f"L{l} {c}" for l, c in sorted(Counter(x["level"] for x in it).items()))]
        tpl_topics = Counter()
        for fn in self.templates.values(): tpl_topics[fn(random.Random(0))["topic"]] += 1
        if tpl_topics: lines.append("Template per topik: " + ", ".join(f"{t} {c}" for t, c in sorted(tpl_topics.items())))
        lines += [f"PERINGATAN {w}" for w in self.warnings]
        for fname, iid, errs in self.rejected:
            lines.append(f"DITOLAK {fname} {iid}: " + "; ".join(errs))
        return "\n".join(lines)

    # ---- perakit tryout ----
    def build_tryout(self, seed: int, composition: dict | None = None, exclude: set | None = None) -> list[dict]:
        """Soal deterministik per seed dalam bentuk yang sama dengan bank STUB (id, subject, topic, level, q, opts, ans, no)
        plus topic_code, passage, explanation, shortcut. Butir di `exclude` (sudah pernah dikerjakan) dihindari bila stok cukup."""
        r = random.Random(seed); comp = composition or COMPOSITION; exclude = exclude or set(); out = []
        def add(qid, subj, code, lvl, stem, opts, ans_text, expl, sc, passage=None):
            opts = opts[:]; r.shuffle(opts)
            out.append({"id": qid, "subject": subj, "topic": TOPIC_NAME[code], "topic_code": code, "level": lvl, "q": stem,
                        "opts": opts, "ans": opts.index(ans_text), "explanation": expl, "shortcut": sc, "passage": passage})
        for subj, n in comp.items():
            if subj == "Kuantitatif":
                names = sorted(self.templates); r.shuffle(names)
                for i in range(min(n, len(names) * 3)):
                    name = names[i % len(names)]; t = self.templates[name](random.Random(seed * 1000 + i))
                    add(f"{name}#{seed}-{i}", subj, t["topic"], t["level"], t["stem"], [t["correct"], *t["distractors"]], t["correct"], t["explanation"], t["shortcut"])
                continue
            pool = [x for x in self.items.values() if x["subject"] == subj]
            fresh = [x for x in pool if x["id"] not in exclude]
            pool = fresh if len(fresh) >= n else pool
            pool.sort(key=lambda x: x["id"]); r.shuffle(pool)
            if subj == "Pemahaman Bacaan":                # ambil per bacaan agar soalnya berurutan
                by_p = {}
                for x in pool: by_p.setdefault(x["passage_id"], []).append(x)
                picked = []
                for pid in sorted(by_p, key=lambda p: r.random()):
                    if len(picked) >= n: break
                    picked += sorted(by_p[pid], key=lambda x: x["id"])[: n - len(picked)]
            else:
                picked = pool[:n]
            for x in picked:
                p = self.passages.get(x.get("passage_id"))
                add(x["id"], subj, x["topic"], x["level"], x["stem"], x["options"], x["options"][x["answer_idx"]], x["explanation"], x["shortcut"],
                    {"id": p["passage_id"], "text": p["text"]} if p else None)
        for n_, q in enumerate(out, 1): q["no"] = n_
        return out
