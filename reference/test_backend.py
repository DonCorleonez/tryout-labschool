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
    st, e = call(app, "POST", "/api/child/tryouts/TO2-1/start", token=ct, t="2026-11-14T10:05")
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


def test_order_after_gate_is_kejar_plan(app):
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
