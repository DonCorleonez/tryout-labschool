"""Tes P2: validator bank, template, perakit tryout, dan integrasi ke backend."""
import json, random
from pathlib import Path

import pytest

import bank
import bankfile as bf
from backend import App
import schedule as sc

HERE = Path(__file__).parent
GOOD, BAD = HERE / "testdata/bank-contoh", HERE / "testdata/bank-rusak"
SMALL = {"Kuantitatif": 3, "Pemahaman Bacaan": 4, "Verbal": 2, "IPA": 2, "IPS": 2}


def test_sample_bank_loads_and_excludes_ambiguous():
    b = bf.Bank.load(GOOD)
    assert len(b.items) == 11 and len(b.passages) == 1 and set(b.templates) == {"mat_pec_tambah", "mat_psn_diskon"}
    assert "IPA-EKO-L2-0002" not in b.items
    assert [r[1] for r in b.rejected] == ["IPA-EKO-L2-0002"]


@pytest.mark.parametrize("iid,reason", [
    ("IPA-XXX-L1-0001", "bukan topik kanonik"), ("IPA-FOT-L1-0002", "subject harus"), ("IPA-FOT-L1-0003", "opsi duplikat"),
    ("IPA-FOT-L1-0004", "opsi terlarang"), ("IPA-FOT-L1-0005", "kunci bocor"), ("IPA-FOT-L1-0006", "answer_idx"),
    ("BAC-GAG-L1-0007", "passage_id"), ("MAT-PEC-L1-0008", "wajib template"), ("IPA-FOT-L2-0009", "id tidak cocok"), ("baris 10", "JSON tidak valid")])
def test_broken_items_rejected_with_reason(iid, reason):
    rej = {r[1]: " ".join(r[2]) for r in bf.Bank.load(BAD).rejected}
    assert reason in rej[iid]


def test_bank_with_rejects_has_no_items_from_broken_file():
    assert bf.Bank.load(BAD).items == {}


def test_template_collisions_are_caught():
    def bad_tpl(rng):                                   # pola contoh brief: a*b bisa sama dengan a+b (2*2 = 2+2)
        a = rng.choice([2, 3]); b = 2; d = 8
        return {"topic": "MAT-PEC", "subtopic": "uji", "level": 1, "stem": "x", "correct": f"{a + b}/{d}", "distractors": [f"{a * b}/{d}", "1/9", "2/9"],
                "explanation": "e" * 25, "shortcut": "s" * 12}
    assert any("kembar" in x for x in bf.check_template(bad_tpl, 50))


def test_equivalent_fraction_options_caught():
    out = {"topic": "MAT-PEC", "subtopic": "uji", "level": 1, "stem": "x", "correct": "1/2", "distractors": ["2/4", "1/3", "3/4"], "explanation": "e" * 25, "shortcut": "s" * 12}
    assert any("bernilai sama" in x for x in bf.validate_template_output(out))


def test_template_exception_is_reported_not_raised():
    def boom(rng): raise ZeroDivisionError("x")
    assert "galat: ZeroDivisionError" in bf.check_template(boom, 5)[0]


def test_build_tryout_deterministic_shuffled_and_key_correct():
    b = bf.Bank.load(GOOD)
    t1, t2, t3 = b.build_tryout(7, SMALL), b.build_tryout(7, SMALL), b.build_tryout(8, SMALL)
    assert t1 == t2 and [q["id"] for q in t1] != [q["id"] for q in t3] or [q["opts"] for q in t1] != [q["opts"] for q in t3]
    assert [q["no"] for q in t1] == list(range(1, len(t1) + 1)) and len(t1) == sum(SMALL.values())
    for q in t1:
        src = b.items.get(q["id"])
        if src: assert q["opts"][q["ans"]] == src["options"][src["answer_idx"]]
        assert q["topic"] == bf.TOPIC_NAME[q["topic_code"]]


def test_reading_questions_stay_together_with_passage():
    t = bf.Bank.load(GOOD).build_tryout(3, SMALL)
    bac = [q for q in t if q["subject"] == "Pemahaman Bacaan"]
    assert len(bac) == 4 and all(q["passage"]["id"] == "BAC-P-0001" for q in bac)
    nos = [q["no"] for q in bac]
    assert nos == list(range(nos[0], nos[0] + 4))


def test_exclude_prefers_unseen_items_when_stock_allows():
    b = bf.Bank.load(GOOD)
    seen = {q["id"] for q in b.build_tryout(1, {"IPA": 1})}
    nxt = {q["id"] for q in b.build_tryout(1, {"IPA": 1}, exclude=seen)}
    assert not (seen & nxt)


def test_public_view_has_passage_but_no_key_or_explanation():
    q = bf.Bank.load(GOOD).build_tryout(3, SMALL)
    pub = [bank.public(x) for x in q]
    assert all("ans" not in p and "explanation" not in p and "shortcut" not in p for p in pub)
    assert any("passage" in p for p in pub)


def test_backend_uses_file_bank_and_scores_by_its_keys():
    bank.configure(GOOD)
    try:
        bank._BANK.build_tryout.__func__  # noqa: B018  (memastikan objek Bank)
        orig = bf.COMPOSITION.copy(); bf.COMPOSITION.clear(); bf.COMPOSITION.update(SMALL)
        now = [sc.FIRST_FRIDAY.replace(hour=18)]
        app = App(now=lambda: now[0])
        st, r = app.handle("POST", "/api/parent/register", body=json.dumps({"name": "I", "whatsapp": "081234567890", "email": "a@b.co", "consent": True, "pin": "123456"}).encode())
        tok = app.handle("POST", "/api/child/login", body=json.dumps({"code": r["child_code"]}).encode())[1]["token"]
        st, s = app.handle("POST", "/api/child/tryouts/DIAG/start", {"X-Token": tok})
        assert st == 200 and len(s["questions"]) == sum(SMALL.values())
        assert all("ans" not in q for q in s["questions"])
        full = bank.get_questions(__import__("backend")._seed(1, "DIAG"))
        answers = {str(q["no"]): q["ans"] for q in full}                 # semua benar
        st, out = app.handle("POST", f"/api/child/attempts/{s['attempt']}/submit", {"X-Token": tok}, json.dumps({"answers": answers}).encode())
        assert st == 200 and out["score"]["pct"] == 100
    finally:
        bf.COMPOSITION.clear(); bf.COMPOSITION.update(orig); bank.configure(None)


def test_stub_used_when_no_bank_configured():
    bank.configure(None)
    assert len(bank.get_questions(1)) == 12
