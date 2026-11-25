import hashlib, hmac, json
import pytest
import backend as be
import bank
import schedule as sc

T = lambda s: s  # ISO string WIB, dikirim lewat header X-Sim-Time (mode playtest)


@pytest.fixture()
def app():
    return be.App(playtest=True, webhook_secret="s3cret", admin_token="adm")


def call(app, method, path, body=None, token=None, t="2026-11-04T10:00", admin=False, raw=None, headers=None, ip="1.1.1.1"):
    h = {"X-Sim-Time": t, **(headers or {})}
    if token: h["X-Token"] = token
    if admin: h["X-Admin-Token"] = "adm"
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")
    return app.handle(method, path, h, data, ip)


def register(app, t="2026-11-04T10:00"):
    st, r = call(app, "POST", "/api/parent/register", {"name": "Ibu Uji", "whatsapp": "081234567890", "email": "a@b.co", "campus": "Cibubur", "track": "Tes", "grade": "6", "consent": True, "pin": "123456"}, t=t)
    assert st == 200, r
    return r


def child(app, code, t="2026-11-04T10:00"):
    st, r = call(app, "POST", "/api/child/login", {"code": code}, t=t)
    assert st == 200, r
    return r["token"]


def pay(app, parent_tok, fam_t, event_id="e1", status="paid"):
    st, o = call(app, "POST", "/api/parent/orders", token=parent_tok, t=fam_t)
    assert st == 200
    body = json.dumps({"event_id": event_id, "order_ref": o["order"], "status": status}).encode()
    sig = hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    return o, call(app, "POST", "/api/webhooks/payment", raw=body, headers={"X-Signature": sig}, t=fam_t)


def full_family(app, t_join="2026-11-04T10:00", t_pay="2026-11-04T11:00"):
    r = register(app, t_join); ct = child(app, r["child_code"], t_join)
    pay(app, r["token"], t_pay)
    return r, ct


def run_tryout(app, ct, tid, t, answers=None):
    st, s = call(app, "POST", f"/api/child/tryouts/{tid}/start", token=ct, t=t)
    assert st == 200, s
    n = len(s["questions"])
    evs = [{"seq": i, "q": i, "kind": "visit", "ms": i * 5000} for i in range(1, n + 1)] + [{"seq": n + 1, "q": n, "kind": "end", "ms": (n + 1) * 5000}]
    call(app, "POST", f"/api/child/attempts/{s['attempt']}/events", {"events": evs}, token=ct, t=t)
    return s


# ---------- pendaftaran, login, privasi ----------
def test_register_validates_and_shows_code_once(app):
    st, r = call(app, "POST", "/api/parent/register", {"name": "", "whatsapp": "12", "email": "x", "consent": False, "pin": "1"})
    assert st == 422
    ok = register(app)
    assert ok["family_ref"].startswith("fam_") and len(ok["child_code"]) == 9
    row = app.db.execute("SELECT code_hash FROM families").fetchone()
    assert ok["child_code"] not in row["code_hash"] and len(row["code_hash"]) == 64        # kode disimpan sebagai hash


def test_child_login_does_not_leak_and_rate_limits(app):
    r = register(app)
    for i in range(be.MAX_LOGIN_FAILS):
        st, e = call(app, "POST", "/api/child/login", {"code": "SALAH-000"})
        assert st == 401 and e["error"] == "kode_tidak_dikenali"
    st, e = call(app, "POST", "/api/child/login", {"code": r["child_code"]})   # IP sama sudah terkunci
    assert st == 429
    st, _ = call(app, "POST", "/api/child/login", {"code": r["child_code"]}, ip="9.9.9.9")
    assert st == 200


def test_revoked_family_cannot_login_or_use_token(app):
    r = register(app); ct = child(app, r["child_code"])
    assert call(app, "POST", f"/api/admin/families/{r['family_ref']}/revoke", admin=True)[0] == 200
    assert call(app, "GET", "/api/child/home", token=ct)[0] == 403
    assert call(app, "POST", "/api/child/login", {"code": r["child_code"]}, ip="8.8.8.8")[0] == 403
    assert call(app, "POST", f"/api/admin/families/{r['family_ref']}/revoke")[0] == 403    # tanpa token admin


# ---------- jendela dan unlock ditegakkan di server ----------
@pytest.mark.parametrize("t", ["2026-11-10T10:00", "2026-11-13T16:00", "2026-11-15T16:05", "2026-11-16T07:05", "2027-01-23T10:00", "2027-01-27T10:00"])
def test_paid_family_cannot_start_tryout_outside_window(app, t):
    _, ct = full_family(app)
    st, e = call(app, "POST", "/api/child/tryouts/TO2-1/start", token=ct, t=t)
    assert st == 409 and e["error"] in ("jendela_tertutup", "tidak_tersedia_pada_jendela_ini")


def test_start_hides_answers_and_blocks_second_start(app):
    _, ct = full_family(app)
    s = run_tryout(app, ct, "TO2-1", "2026-11-14T10:00")
    assert all(set(q) == {"no", "id", "subject", "topic", "level", "q", "opts"} for q in s["questions"])
    assert "ans" not in json.dumps(s) and "exp" not in json.dumps(s)
    st, s2 = call(app, "POST", "/api/child/tryouts/TO2-1/start", token=ct, t="2026-11-14T10:05")   # start ulang = lanjut, BUKAN attempt baru
    assert st == 200 and s2["resumed"] and s2["attempt"] == s["attempt"]
    assert app.db.execute("SELECT COUNT(*) FROM attempts WHERE tryout_id='TO2-1'").fetchone()[0] == 1
    call(app, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {}}, token=ct, t="2026-11-14T10:10")
    st, e = call(app, "POST", "/api/child/tryouts/TO2-1/start", token=ct, t="2026-11-14T10:15")
    assert st == 409 and e["error"] == "sudah_dikerjakan"


def test_second_tryout_in_intensive_weekend_requires_first_submitted(app):
    _, ct = full_family(app)
    t = "2027-01-09T10:00"
    st, e = call(app, "POST", "/api/child/tryouts/TO10-2/start", token=ct, t=t)
    assert st == 409 and e["error"] == "kumpulkan_tryout_pertama_dulu"
    s = run_tryout(app, ct, "TO10-1", t)
    assert call(app, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {}}, token=ct, t="2027-01-09T11:00")[0] == 200
    assert call(app, "POST", "/api/child/tryouts/TO10-2/start", token=ct, t="2027-01-09T11:05")[0] == 200


def test_started_before_close_is_accepted_until_two_hours_after_start(app):
    """Keputusan pemilik: mulai sebelum 16.00 => diterima sampai selesai, maks 2 jam sejak mulai."""
    _, ct = full_family(app)
    s = run_tryout(app, ct, "TO2-1", "2026-11-15T15:55")                       # Min 15.55, jendela tutup 16.00
    st, r = call(app, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {}}, token=ct, t="2026-11-15T17:40")
    assert st == 200 and r["analisa"] == "menunggu"                            # lewat 16.00 tetapi < 17.55
    assert app.db.execute("SELECT COUNT(*) n FROM analysis_jobs").fetchone()["n"] == 1


def test_submit_after_two_hours_is_rejected_and_nothing_stored(app):
    _, ct = full_family(app)
    s = run_tryout(app, ct, "TO2-1", "2026-11-15T15:55")
    st, e = call(app, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {}}, token=ct, t="2026-11-15T18:00")
    assert st == 409 and e["error"] == "waktu_habis"
    assert app.db.execute("SELECT COUNT(*) n FROM analysis_jobs").fetchone()["n"] == 0


def test_cannot_start_after_close_even_if_late_by_a_minute(app):
    _, ct = full_family(app)
    st, e = call(app, "POST", "/api/child/tryouts/TO2-1/start", token=ct, t="2026-11-15T16:01")
    assert st == 409 and e["error"] == "jendela_tertutup"


def test_parent_login_pin_lockout_and_no_leak(app):
    register(app)
    st, r = call(app, "POST", "/api/parent/login", {"email": "a@b.co", "pin": "123456"})
    assert st == 200 and r["token"] and r["family_ref"].startswith("fam_")
    assert "123456" not in app.db.execute("SELECT pin_hash FROM families").fetchone()["pin_hash"]      # PIN ber-salt, bukan teks asli
    for _ in range(be.PIN_MAX_FAILS):
        st, e = call(app, "POST", "/api/parent/login", {"email": "a@b.co", "pin": "000000"}, ip="9.9.9.9")
        assert st == 401 and e["error"] == "email_atau_pin_salah"
    st, e = call(app, "POST", "/api/parent/login", {"email": "a@b.co", "pin": "123456"}, ip="8.8.8.8")        # PIN benar pun ditolak saat terkunci
    assert st == 429 and e["error"] == "terkunci"
    assert call(app, "POST", "/api/parent/login", {"email": "a@b.co", "pin": "123456"}, t="2026-11-04T10:20")[0] == 200   # kunci habis
    assert call(app, "POST", "/api/parent/login", {"email": "tidak@ada.co", "pin": "123456"})[1]["error"] == "email_atau_pin_salah"


def test_strong_child_gets_maintenance_drill(app):
    r, ct = full_family(app)
    s = run_tryout(app, ct, "TO2-1", "2026-11-14T10:00")
    import bank
    ans = {str(n): q for n, q in enumerate([x["ans"] for x in bank.get_questions(be._seed(app.db.execute("SELECT id FROM families").fetchone()["id"], "TO2-1"))], 1)}
    assert call(app, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": ans}, token=ct, t="2026-11-14T10:30")[0] == 200
    call(app, "POST", "/api/admin/analysis/standin", admin=True, t="2026-11-16T05:00")
    d = call(app, "GET", "/api/child/drills", token=ct, t="2026-11-16T10:00")[1]["drills"]
    assert [x["topic"] for x in d] == ["Pemeliharaan"]


def test_submit_is_idempotent_and_reveals_keys_only_after(app):
    _, ct = full_family(app)
    s = run_tryout(app, ct, "TO2-1", "2026-11-14T10:00")
    st, r1 = call(app, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {"1": 0}}, token=ct, t="2026-11-14T10:30")
    st2, r2 = call(app, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {"1": 1}}, token=ct, t="2026-11-14T10:31")
    assert st == st2 == 200 and r2["idempoten"] and r1["score"] == r2["score"]
    assert "correct_idx" in r1["review"][0]
    assert app.db.execute("SELECT COUNT(*) n FROM analysis_jobs").fetchone()["n"] == 1


def test_events_are_idempotent_and_idle_is_excluded(app):
    _, ct = full_family(app)
    st, s = call(app, "POST", "/api/child/tryouts/TO2-1/start", token=ct, t="2026-11-14T10:00")
    ev = [{"seq": 1, "q": 1, "kind": "visit", "ms": 0}, {"seq": 2, "q": 1, "kind": "idle", "value": 40, "ms": 50000}, {"seq": 3, "q": 1, "kind": "answer", "value": 2, "ms": 60000}, {"seq": 4, "q": 1, "kind": "end", "ms": 100000}]
    a = call(app, "POST", f"/api/child/attempts/{s['attempt']}/events", {"events": ev}, token=ct, t="2026-11-14T10:01")[1]
    b = call(app, "POST", f"/api/child/attempts/{s['attempt']}/events", {"events": ev}, token=ct, t="2026-11-14T10:01")[1]
    assert a["diterima"] == 4 and b["diterima"] == 0
    rows = [dict(r) for r in app.db.execute("SELECT * FROM attempt_events")]
    per = be.App.aggregate(rows, 12)
    assert per[1]["raw"] == 100 and per[1]["idle"] == 40 and per[1]["visits"] == 1
    assert an_clean(per[1]) == 60


def an_clean(p):
    import analysis as an
    return an.clean_seconds(p["raw"], p["idle"])


# ---------- pembayaran ----------
def test_webhook_signature_idempotency_and_activation(app):
    r = register(app)
    st, o = call(app, "POST", "/api/parent/orders", token=r["token"])
    body = json.dumps({"event_id": "evt-1", "order_ref": o["order"], "status": "paid"}).encode()
    assert call(app, "POST", "/api/webhooks/payment", raw=body, headers={"X-Signature": "salah"})[0] == 401
    assert app.db.execute("SELECT plan FROM families").fetchone()["plan"] == "free"
    sig = hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    assert call(app, "POST", "/api/webhooks/payment", raw=body, headers={"X-Signature": sig})[1]["status"] == "paid"
    assert call(app, "POST", "/api/webhooks/payment", raw=body, headers={"X-Signature": sig})[1] == {"duplikat": True}
    assert app.db.execute("SELECT plan FROM families").fetchone()["plan"] == "utama"
    kinds = [x["kind"] for x in app.db.execute("SELECT kind FROM order_events")]
    assert kinds.count("webhook_paid") == 1 and "request_diterima_server" in kinds and "dikirim_ke_gateway" in kinds


def test_order_after_gate_is_kejar_plan(app, monkeypatch):
    monkeypatch.setitem(be.IDR, "kejar", 123)               # harga kejar belum ditetapkan pemilik; nilai uji saja
    r = register(app)
    o, (st, out) = pay(app, r["token"], "2026-12-12T10:00", "e2")
    assert st == 200 and app.db.execute("SELECT plan FROM families").fetchone()["plan"] == "kejar"


def test_failed_payment_does_not_activate(app):
    r = register(app)
    pay(app, r["token"], "2026-11-04T11:00", "e3", status="failed")
    assert app.db.execute("SELECT plan FROM families").fetchone()["plan"] == "free"


# ---------- data dikumpulkan dulu, AI belakangan ----------
def test_payload_is_pseudonymous_and_complete(app):
    r, ct = full_family(app)
    s = run_tryout(app, ct, "TO2-1", "2026-11-14T10:00")
    call(app, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {"1": 0, "2": 1}, "flags": {"2": True}}, token=ct, t="2026-11-14T10:30")
    raw = app.db.execute("SELECT input_json FROM analysis_jobs").fetchone()["input_json"]
    for pii in ("Ibu Uji", "081234567890", "a@b.co", r["child_code"]):
        assert pii not in raw
    p = json.loads(raw)
    assert p["family_ref"] == r["family_ref"] and len(p["questions"]) == 12
    assert {"sec_clean", "flagged", "changes", "changed_correct_to_wrong", "rule_tag"} <= set(p["questions"][0])


def test_drill_not_assigned_until_analysis_then_sequential(app):
    r, ct = full_family(app)
    s = run_tryout(app, ct, "TO2-1", "2026-11-14T10:00")
    call(app, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {}}, token=ct, t="2026-11-14T10:30")   # semua kosong -> banyak topik lemah
    home = call(app, "GET", "/api/child/home", token=ct, t="2026-11-16T10:00")[1]
    assert home["clock"] == "drill" and home["drills"] == [] and home["pending"] is True
    assert call(app, "POST", "/api/admin/analysis/standin", admin=True, t="2026-11-16T05:00")[1]["diproses"] == 1
    d = call(app, "GET", "/api/child/drills", token=ct, t="2026-11-16T10:00")[1]["drills"]
    assert 1 <= len({x["topic"] for x in d}) <= 2 and [x["state"] for x in d][:2] == ["siap", "terkunci"]
    a = d[0]["assignment"]
    assert call(app, "POST", f"/api/child/drills/{a}/sessions/2/finish", {"correct": 3, "total": 5}, token=ct, t="2026-11-16T10:05")[1]["error"] == "selesaikan_sesi_sebelumnya"
    assert call(app, "POST", f"/api/child/drills/{a}/sessions/1/finish", {"correct": 3, "total": 5}, token=ct, t="2026-11-16T10:06")[0] == 200
    assert call(app, "POST", f"/api/child/drills/{a}/sessions/1/finish", {"correct": 3, "total": 5}, token=ct, t="2026-11-16T10:07")[1]["error"] == "sudah_selesai"
    assert call(app, "GET", "/api/child/drills", token=ct, t="2026-11-14T10:00")[0] == 409           # jendela tryout: drill tertutup
    assert call(app, "POST", f"/api/child/drills/{a}/sessions/2/finish", {"correct": 4, "total": 5}, token=ct, t="2026-11-13T16:00")[0] == 409   # celah


def test_paid_report_publishes_monday_0700_and_free_report_after_analysis(app):
    r, ct = full_family(app)
    s = run_tryout(app, ct, "TO2-1", "2026-11-14T10:00")
    call(app, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {}}, token=ct, t="2026-11-14T10:30")
    assert call(app, "GET", "/api/parent/report/latest", token=r["token"], t="2026-11-15T20:00")[1]["report"] is None
    call(app, "POST", "/api/admin/analysis/standin", admin=True, t="2026-11-15T22:00")
    early = call(app, "GET", "/api/parent/report/latest", token=r["token"], t="2026-11-16T06:30")[1]
    assert early["report"] is None and "terbit_pada" in early
    rep = call(app, "GET", "/api/parent/report/latest", token=r["token"], t="2026-11-16T07:05")[1]["report"]
    assert rep["window"] == 2 and rep["body"]["status"] in ("Belum Siap", "Mengejar", "Siap Diuji")


def test_free_family_gets_one_diagnostic_anytime_then_locked(app):
    r = register(app); ct = child(app, r["child_code"])
    s = run_tryout(app, ct, "DIAG", "2026-11-04T10:00")
    assert call(app, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {}}, token=ct, t="2026-11-04T10:20")[0] == 200
    assert call(app, "POST", "/api/child/tryouts/TO2-1/start", token=ct, t="2026-11-14T10:00")[1]["error"] == "paket_gratis_hanya_diagnostik"


def test_bank_public_view_has_no_key():
    qs = bank.get_questions(7)
    assert len(qs) == 12 and all("ans" not in bank.public(q) for q in qs)
    assert all(len(set(q["opts"])) == 4 and 0 <= q["ans"] < 4 for q in qs)


# ---------- P3: lanjut setelah refresh, pembahasan pasca-submit ----------
def _child(app):
    st, r = call(app, "POST", "/api/parent/register", {"name": "Ibu", "whatsapp": "081234567890", "email": "r@s.co", "consent": True, "pin": "123456"})
    return call(app, "POST", "/api/child/login", {"code": r["child_code"]})[1]["token"]


def test_start_again_resumes_same_attempt_until_deadline(app):
    tok = _child(app)
    st, s1 = call(app, "POST", "/api/child/tryouts/DIAG/start", token=tok, t="2026-11-06T18:00")
    st, s2 = call(app, "POST", "/api/child/tryouts/DIAG/start", token=tok, t="2026-11-06T19:30")
    assert st == 200 and s2["resumed"] and s2["attempt"] == s1["attempt"] and s2["deadline_at"] == s1["deadline_at"]
    assert [q["id"] for q in s2["questions"]] == [q["id"] for q in s1["questions"]] and all("ans" not in q for q in s2["questions"])
    assert call(app, "GET", "/api/child/home", token=tok, t="2026-11-06T19:30")[1]["tryouts"][0]["state"] == "berjalan"
    st, e = call(app, "POST", "/api/child/tryouts/DIAG/start", token=tok, t="2026-11-06T20:01")      # lewat 2 jam: tidak bisa dilanjut
    assert st == 409 and e["error"] == "sudah_dikerjakan"
    assert call(app, "GET", "/api/child/home", token=tok, t="2026-11-06T20:01")[1]["tryouts"][0]["state"] == "terlewat"


def test_review_with_explanation_only_after_submit_and_idempotent(app):
    tok = _child(app)
    st, s = call(app, "POST", "/api/child/tryouts/DIAG/start", token=tok, t="2026-11-06T18:00")
    assert all("explanation" not in q for q in s["questions"])
    st, r1 = call(app, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {"1": 0}}, token=tok, t="2026-11-06T18:30")
    assert st == 200 and len(r1["review"]) == len(s["questions"]) and "explanation" in r1["review"][0]
    st, r2 = call(app, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {"1": 1}}, token=tok, t="2026-11-06T18:31")
    assert r2["idempoten"] and r2["review"] == r1["review"] and r2["score"] == r1["score"]


# ---------- P4: harga, dashboard orang tua, bayar simulasi playtest ----------
def _parent(app, email="p4@x.co"):
    st, r = call(app, "POST", "/api/parent/register", {"name": "Ibu", "whatsapp": "081234567890", "email": email, "consent": True, "pin": "123456"})
    return r["token"]


def test_order_amount_comes_from_server_price(app):
    pt = _parent(app)
    st, o = call(app, "POST", "/api/parent/orders", {"amount_idr": 1}, token=pt)          # harga kiriman klien diabaikan
    assert st == 200 and o["amount_idr"] == 499_000 and o["plan"] == "utama"
    assert app.db.execute("SELECT amount_idr FROM orders WHERE public_ref=?", (o["order"],)).fetchone()[0] == 499_000


def test_kejar_plan_without_price_is_not_sold(app):
    pt = _parent(app, "k@x.co")
    st, e = call(app, "POST", "/api/parent/orders", {}, token=pt, t="2026-12-10T10:00")
    assert st == 409 and e["error"] == "harga_belum_ditetapkan"


def test_parent_home_and_playtest_pay_activates_once(app):
    pt = _parent(app, "h@x.co")
    st, h = call(app, "GET", "/api/parent/home", token=pt)
    assert st == 200 and h["plan"] == "free" and h["offer"]["amount_idr"] == 499_000 and h["playtest"]
    o = call(app, "POST", "/api/parent/orders", {}, token=pt)[1]
    assert call(app, "POST", f"/api/playtest/orders/{o['order']}/pay", token=pt)[0] == 200
    h = call(app, "GET", "/api/parent/home", token=pt)[1]
    assert h["plan"] == "utama" and h["orders"][0]["status"] == "paid"
    st, e = call(app, "POST", "/api/parent/orders", {}, token=pt)
    assert st == 409 and e["error"] == "paket_sudah_aktif"


def test_playtest_pay_route_absent_in_production():
    prod = be.App(playtest=False)
    st, r = prod.handle("POST", "/api/parent/register", {}, json.dumps({"name": "I", "whatsapp": "081234567890", "email": "z@x.co", "consent": True, "pin": "123456"}).encode())
    o = prod.handle("POST", "/api/parent/orders", {"X-Token": r["token"]}, b"")[1]
    st, e = prod.handle("POST", f"/api/playtest/orders/{o['order']}/pay", {"X-Token": r["token"]}, b"")
    assert st == 404 and prod.db.execute("SELECT plan FROM families").fetchone()[0] == "free"


def test_child_token_cannot_use_parent_endpoints(app):
    st, r = call(app, "POST", "/api/parent/register", {"name": "I", "whatsapp": "081234567890", "email": "c@x.co", "consent": True, "pin": "123456"})
    ct = call(app, "POST", "/api/child/login", {"code": r["child_code"]})[1]["token"]
    assert call(app, "GET", "/api/parent/home", token=ct)[0] == 401
    assert call(app, "POST", "/api/parent/orders", {}, token=ct)[0] == 401


# ---------- 2 Nov: diagnostik satu set soal, tidak bisa daftar ulang ----------
def test_diagnostic_question_set_is_identical_for_everyone(app):
    sets = []
    for i in range(3):
        st, r = call(app, "POST", "/api/parent/register", {"name": "I", "whatsapp": f"08123456789{i}", "email": f"d{i}@x.co", "consent": True, "pin": "123456"})
        ct = call(app, "POST", "/api/child/login", {"code": r["child_code"]})[1]["token"]
        sets.append([q["id"] for q in call(app, "POST", "/api/child/tryouts/DIAG/start", token=ct)[1]["questions"]])
    assert sets[0] == sets[1] == sets[2]


def test_paid_tryouts_still_differ_per_student():
    assert be._seed(1, "TO2-1") != be._seed(2, "TO2-1") and be._seed(1, "DIAG") == be._seed(2, "DIAG")


@pytest.mark.parametrize("email,wa", [("SAMA@x.co", "089999999999"), ("lain@x.co", "+62 812-3456-7890"), ("lain2@x.co", "6281234567890")])
def test_same_email_or_whatsapp_cannot_register_twice(app, email, wa):
    assert call(app, "POST", "/api/parent/register", {"name": "I", "whatsapp": "081234567890", "email": "sama@x.co", "consent": True, "pin": "123456"})[0] == 200
    st, e = call(app, "POST", "/api/parent/register", {"name": "I", "whatsapp": wa, "email": email, "consent": True, "pin": "123456"})
    assert st == 409 and e["error"] == "sudah_terdaftar"


# ---------- Neon redesign v1: G-22, G-20, F-06, gamifikasi, drill, Buku Salah, full history ----------
def test_g22_corrupted_payload_job_does_not_block_next_job(app):
    r1 = call(app, "POST", "/api/parent/register", {"name": "Ibu 1", "whatsapp": "081211111111", "email": "g1@x.co", "consent": True, "pin": "123456"}, t="2026-11-04T10:00")[1]
    r2 = call(app, "POST", "/api/parent/register", {"name": "Ibu 2", "whatsapp": "081222222222", "email": "g2@x.co", "consent": True, "pin": "123456"}, t="2026-11-04T10:00")[1]
    ct1, ct2 = child(app, r1["child_code"]), child(app, r2["child_code"])
    s1 = run_tryout(app, ct1, "DIAG", "2026-11-06T18:00")
    s2 = run_tryout(app, ct2, "DIAG", "2026-11-06T18:00")
    call(app, "POST", f"/api/child/attempts/{s1['attempt']}/submit", {"answers": {}}, token=ct1, t="2026-11-06T18:10")
    call(app, "POST", f"/api/child/attempts/{s2['attempt']}/submit", {"answers": {}}, token=ct2, t="2026-11-06T18:10")
    # Korupsi job pertama secara eksplisit (skenario G-22)
    app.db.execute("UPDATE analysis_jobs SET input_json='{corrupted_json' WHERE id=1")
    app.db.commit()
    st, res = call(app, "POST", "/api/admin/analysis/standin", admin=True, t="2026-11-08T22:00")
    assert st == 200 and res["gagal"] == 1 and res["diproses"] == 1
    j1 = app.db.execute("SELECT state, error FROM analysis_jobs WHERE id=1").fetchone()
    j2 = app.db.execute("SELECT state FROM analysis_jobs WHERE id=2").fetchone()
    assert j1["state"] == "gagal" and "corrupted_payload" in j1["error"] and j2["state"] == "selesai"
    # Keluarga 1 tetap menerima laporan fallback aturan dan drill fallback
    rep1 = call(app, "GET", "/api/parent/report/latest", token=r1["token"], t="2026-11-09T07:05")[1]["report"]
    assert rep1 is not None and rep1["mode"] == "fallback"


def test_g20_device_limit_3_per_family(app):
    r = register(app)
    for i in range(1, 4):
        st, _ = call(app, "POST", "/api/child/login", {"code": r["child_code"]}, headers={"X-Device-Id": f"hp-{i}"})
        assert st == 200
    st4, e4 = call(app, "POST", "/api/child/login", {"code": r["child_code"]}, headers={"X-Device-Id": "hp-4"})
    assert st4 == 403 and e4["error"] == "device_limit_tercapai"


def test_lab_access_code_format_and_login_compatible(app):
    r = register(app)
    assert r["access_code"] == f"LAB-{r['child_code']}"
    st, cl = call(app, "POST", "/api/child/login", {"code": r["access_code"]})
    assert st == 200 and cl["token"]


def test_f06_parent_pin_reset_flow(app):
    register(app)
    st, res = call(app, "POST", "/api/parent/pin/reset-request", {"email": "a@b.co"})
    assert st == 200 and res["ok"] is True
    body = app.db.execute("SELECT body_text FROM email_outbox WHERE kind='reset_pin'").fetchone()["body_text"]
    tok = body.split(": ")[-1].strip()
    assert call(app, "POST", "/api/parent/pin/reset", {"token": tok, "pin": "654321"})[0] == 200
    assert call(app, "POST", "/api/parent/login", {"email": "a@b.co", "pin": "654321"})[0] == 200


def test_gamification_xp_streaks_stars_and_levels():
    import gamification as gm
    # 12 soal: 8 benar beruntun (hits 3, 5, 8 -> +5 +10 +15 = +30), lalu 1 salah, lalu 3 benar -> 11/12 = 91.7% -> 3 bintang
    seq = [True] * 8 + [False] + [True] * 3
    res = gm.score_tryout_xp(seq, 91.7)
    assert res["base_xp"] == 110 and res["streak_bonus"] == 30 and res["total_xp"] == 140 and res["stars"] == 3
    assert gm.stars_for_pct(89.9) == 2 and gm.stars_for_pct(74.9) == 1 and gm.stars_for_pct(59.9) == 0
    assert gm.level_info(0)["level"] == 1 and gm.level_info(100)["level"] == 2 and gm.level_info(3200)["level"] == 10
    assert gm.level_info(4000)["level"] == 11


def test_gamification_isolated_from_parent_reports(app):
    r, ct = full_family(app)
    s = run_tryout(app, ct, "TO2-1", "2026-11-14T10:00")
    st, sub = call(app, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {"1": 0}}, token=ct, t="2026-11-14T10:30")
    assert st == 200 and "gamification" in sub
    call(app, "POST", "/api/admin/analysis/standin", admin=True, t="2026-11-16T05:00")
    st_rep, rep = call(app, "GET", "/api/parent/reports", token=r["token"], t="2026-11-16T10:00")
    assert st_rep == 200 and len(rep["trends"]) == 1
    dumped = json.dumps(rep).lower()
    for banned in ('"xp"', '"stars"', '"level"', '"streak"', "pasti bisa", "dijamin lolos"):
        assert banned not in dumped


def test_drill_interactive_start_finish_adds_wrong_to_buku_salah(app):
    r, ct = full_family(app)
    s = run_tryout(app, ct, "TO2-1", "2026-11-14T10:00")
    call(app, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {}}, token=ct, t="2026-11-14T10:30")
    call(app, "POST", "/api/admin/analysis/standin", admin=True, t="2026-11-16T05:00")
    d = call(app, "GET", "/api/child/drills", token=ct, t="2026-11-16T10:00")[1]["drills"][0]
    st_s, ds = call(app, "GET", f"/api/child/drills/{d['assignment']}/sessions/{d['session']}/start", token=ct, t="2026-11-16T10:05")
    assert st_s == 200 and len(ds["questions"]) == 5 and "ans" not in json.dumps(ds)
    st_f, df = call(app, "POST", f"/api/child/drills/{d['assignment']}/sessions/{d['session']}/finish", {"answers": {"1": 0}}, token=ct, t="2026-11-16T10:10")
    assert st_f == 200 and df["ok"] and len(df["review"]) == 5
    bs = call(app, "GET", "/api/child/buku-salah", token=ct, t="2026-11-16T10:15")[1]
    assert any(x["source_type"] == "drill" for x in bs["items"])


def test_child_result_endpoint_and_taper_flag(app):
    _, ct = full_family(app)
    s = run_tryout(app, ct, "DIAG", "2026-11-06T18:00")
    call(app, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {"1": 0}}, token=ct, t="2026-11-06T18:20")
    st, res = call(app, "GET", f"/api/child/attempts/{s['attempt']}/result", token=ct, t="2026-11-06T18:25")
    assert st == 200 and len(res["questions"]) == 12 and "gamification" in res
    home_taper = call(app, "GET", "/api/child/home", token=ct, t="2027-01-26T10:00")[1]
    assert home_taper["clock"] == "taper" and home_taper["taper"] is True


def test_prestasi_claim_stub_and_duplicate_proof_rejected(app):
    r1 = register(app, "2026-11-04T10:00")
    r2 = call(app, "POST", "/api/parent/register", {"name": "Ibu 2", "whatsapp": "081234567891", "email": "b@c.co", "consent": True, "pin": "123456"}, t="2026-11-04T10:00")[1]
    st1, p1 = call(app, "POST", "/api/parent/prestasi", {"proof_ref": "SURAT-PRESTASI-99"}, token=r1["token"])
    assert st1 == 200 and p1["discount_percent"] == "TBD" and p1["discount_code"].startswith("PRESTASI-")
    st2, p2 = call(app, "POST", "/api/parent/prestasi", {"proof_ref": "SURAT-PRESTASI-99"}, token=r2["token"])
    assert st2 == 409 and p2["error"] == "bukti_sudah_dipakai"


def test_drill_finish_ignores_client_score_and_computes_on_server(app):
    _, ct = full_family(app)
    s = run_tryout(app, ct, "TO2-1", "2026-11-14T10:00")
    call(app, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {}}, token=ct, t="2026-11-14T10:30")
    call(app, "POST", "/api/admin/analysis/standin", admin=True, t="2026-11-16T05:00")
    d = call(app, "GET", "/api/child/drills", token=ct, t="2026-11-16T10:00")[1]["drills"][0]
    aid = d["assignment"]

    # Sesi 1: klien mengirim correct=5, total=5 tanpa answers -> server wajib hitung 0/5 dan base_xp=0
    call(app, "GET", f"/api/child/drills/{aid}/sessions/1/start", token=ct, t="2026-11-16T10:05")
    st1, f1 = call(app, "POST", f"/api/child/drills/{aid}/sessions/1/finish", {"correct": 5, "total": 5}, token=ct, t="2026-11-16T10:06")
    assert st1 == 200 and f1["correct"] == 0 and f1["total"] == 5
    assert f1["gamification"]["base_xp"] == 0 and f1["gamification"]["completion_xp"] == 5
    assert f1["gamification"]["total_xp"] == 5

    # Sesi 2: klien mengirim answers valid + bogus correct=0, total=99 -> server hitung dari answers
    call(app, "GET", f"/api/child/drills/{aid}/sessions/2/start", token=ct, t="2026-11-16T10:10")
    qs2 = bank.get_drill_questions(d["topic"], app._drill_seed(1, aid, 2), count=5)
    ans2 = {str(i): q["ans"] for i, q in enumerate(qs2, 1)}
    st2, f2 = call(app, "POST", f"/api/child/drills/{aid}/sessions/2/finish", {"answers": ans2, "correct": 0, "total": 99}, token=ct, t="2026-11-16T10:11")
    assert st2 == 200 and f2["correct"] == 5 and f2["total"] == 5
    assert f2["gamification"]["base_xp"] == 50 and f2["gamification"]["total_xp"] == 55


def test_g20_same_user_agent_four_device_ids_blocked_and_relogin_allowed(app):
    r = register(app)
    same_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
    for i in range(1, 4):
        st, _ = call(app, "POST", "/api/child/login", {"code": r["child_code"]}, headers={"User-Agent": same_ua, "X-Device-Id": f"dev_browser_{i}"})
        assert st == 200
    # Login ulang dari perangkat 2 yang sama tetap diizinkan tanpa menambah slot
    st_re, _ = call(app, "POST", "/api/child/login", {"code": r["child_code"]}, headers={"User-Agent": same_ua, "X-Device-Id": "dev_browser_2"})
    assert st_re == 200
    # Perangkat ke-4 unik ditolak walau User-Agent identik
    st4, e4 = call(app, "POST", "/api/child/login", {"code": r["child_code"]}, headers={"User-Agent": same_ua, "X-Device-Id": "dev_browser_4"})
    assert st4 == 403 and e4["error"] == "device_limit_tercapai"
