"""Tes integrasi HTTP: server sungguhan di port acak, klien urllib."""
import json, threading, urllib.request, urllib.error
from pathlib import Path

import pytest

import server as sv


def _req(base, method, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(r) as resp:
            raw = resp.read(); return resp.status, dict(resp.headers), raw
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


@pytest.fixture
def srv(tmp_path):
    pub = tmp_path / "public"; pub.mkdir(); (pub / "index.html").write_text("<h1>halo</h1>")
    (tmp_path / "rahasia.txt").write_text("JANGAN")
    def start(**kw):
        cfg = sv.Config(host="127.0.0.1", port=0, db_path=":memory:", public_dir=str(pub), **kw)
        s, app = sv.build(cfg)
        threading.Thread(target=s.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{s.server_address[1]}", s
    servers = []
    def factory(**kw):
        b, s = start(**kw); servers.append(s); return b
    yield factory
    for s in servers: s.shutdown(); s.server_close()


def test_api_roundtrip_register_and_child_login(srv):
    base = srv()
    st, _, raw = _req(base, "POST", "/api/parent/register", {"name": "Ibu", "whatsapp": "081234567890", "email": "a@b.co", "consent": True, "pin": "123456"})
    assert st == 200; code = json.loads(raw)["child_code"]
    st, h, raw = _req(base, "POST", "/api/child/login", {"code": code})
    assert st == 200 and json.loads(raw)["token"]
    assert h["Cache-Control"] == "no-store" and h["X-Content-Type-Options"] == "nosniff"


def test_errors_are_json_with_status(srv):
    base = srv()
    st, _, raw = _req(base, "GET", "/api/child/home")
    assert st == 401 and json.loads(raw)["error"] == "belum_masuk"
    st, _, raw = _req(base, "GET", "/api/tidak/ada")
    assert st == 404


def test_static_served_and_traversal_blocked(srv):
    base = srv()
    st, h, raw = _req(base, "GET", "/")
    assert st == 200 and b"halo" in raw and h["Content-Type"].startswith("text/html")
    st, _, raw = _req(base, "GET", "/../rahasia.txt")
    assert st == 404 and b"JANGAN" not in raw
    st, _, raw = _req(base, "GET", "/%2e%2e/rahasia.txt")
    assert st == 404 and b"JANGAN" not in raw


def test_sim_time_header_ignored_outside_playtest(srv):
    base = srv(playtest=False)
    reg = json.loads(_req(base, "POST", "/api/parent/register", {"name": "I", "whatsapp": "081234567890", "email": "x@y.co", "consent": True, "pin": "123456"})[2])
    tok = json.loads(_req(base, "POST", "/api/child/login", {"code": reg["child_code"]})[2])["token"]
    # jam sungguhan (Nov 2026 ke atas). Header sim ke hari tes TIDAK boleh berpengaruh.
    st, _, raw = _req(base, "GET", "/api/child/home", headers={"X-Token": tok, "X-Sim-Time": "2027-01-31T09:00"})
    assert st == 200 and json.loads(raw)["clock"] != "hari_tes"


def test_sim_time_header_works_in_playtest(srv):
    base = srv(playtest=True)
    reg = json.loads(_req(base, "POST", "/api/parent/register", {"name": "I", "whatsapp": "081234567890", "email": "x@y.co", "consent": True, "pin": "123456"})[2])
    tok = json.loads(_req(base, "POST", "/api/child/login", {"code": reg["child_code"]})[2])["token"]
    st, h, raw = _req(base, "GET", "/api/child/home", headers={"X-Token": tok, "X-Sim-Time": "2027-01-31T09:00"})
    assert json.loads(raw)["clock"] == "hari_tes" and "noindex" in h["X-Robots-Tag"]
    assert b"Disallow: /" in _req(base, "GET", "/robots.txt")[2]


def test_playtest_refused_on_production_host():
    cfg = sv.Config(playtest=True, public_host="tryout.contoh.id", production_hosts={"tryout.contoh.id"},
                    webhook_secret="s" * 32, admin_token="a" * 32, db_path="x.db")
    with pytest.raises(sv.ConfigError):
        cfg.validate()


def test_production_requires_real_secrets():
    cfg = sv.Config(public_host="tryout.contoh.id", production_hosts={"tryout.contoh.id"}, db_path="x.db")
    with pytest.raises(sv.ConfigError):
        cfg.validate()
    cfg.webhook_secret, cfg.admin_token = "s" * 32, "a" * 32
    with pytest.raises(sv.ConfigError):            # bank STUB dilarang di produksi
        cfg.validate()
    cfg.bank_dir = "bank"
    with pytest.raises(sv.ConfigError):            # gateway sim / mail log dilarang di produksi
        cfg.validate()
    cfg.env = {"GATEWAY": "duitku", "DUITKU_SANDBOX": "0", "MAIL": "resend"}
    cfg.validate()


def test_build_refuses_duitku_without_keys():
    with pytest.raises(sv.ConfigError):
        sv.build(sv.Config(port=0, db_path=":memory:", env={"GATEWAY": "duitku"}))


def test_config_from_env():
    c = sv.Config.from_env({"PLAYTEST": "1", "PUBLIC_HOST": "Play.Contoh.id", "PRODUCTION_HOSTS": "a.id, b.id", "PORT": "9000"})
    assert c.playtest and c.public_host == "play.contoh.id" and c.production_hosts == {"a.id", "b.id"} and c.port == 9000 and not c.is_production


def test_body_too_large_rejected(srv):
    base = srv()
    big = {"x": "a" * (sv.MAX_BODY + 10)}
    st, _, _ = _req(base, "POST", "/api/parent/register", big)
    assert st == 413


def test_webhook_over_http_uses_raw_body_signature(srv):
    import hmac, hashlib
    base = srv()
    body = json.dumps({"event_id": "e1", "order_ref": "ord_x", "status": "paid"}).encode()
    sig = hmac.new(b"dev-secret", body, hashlib.sha256).hexdigest()
    r = urllib.request.Request(base + "/api/webhooks/payment", data=body, method="POST", headers={"X-Signature": sig, "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(r); st = 200
    except urllib.error.HTTPError as e:
        st = e.code; out = json.loads(e.read())
    assert st == 404 and out["error"] == "pesanan_tidak_ada"     # tanda tangan diterima, pesanan memang tidak ada


def test_http_healthz_and_security_headers(srv):
    base = srv(playtest=False)
    st, h, raw = _req(base, "GET", "/healthz")
    assert st == 200 and json.loads(raw) == {"ok": True, "playtest": False}
    assert h["X-Frame-Options"] == "DENY" and "script-src 'self'" in h["Content-Security-Policy"]


def test_http_invalid_json_returns_400(srv):
    base = srv()
    r = urllib.request.Request(base + "/api/parent/register", data=b"{bad", method="POST", headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(r); st = 200
    except urllib.error.HTTPError as e:
        st = e.code; out = json.loads(e.read())
    assert st == 400 and out["error"] == "json_tidak_valid"


def test_http_unsupported_method_returns_405(srv):
    base = srv()
    st, _, raw = _req(base, "POST", "/index.html")
    assert st == 405 and json.loads(raw)["error"] == "metode"


def test_http_parent_login_and_reports_roundtrip(srv):
    base = srv(playtest=True)
    reg = json.loads(_req(base, "POST", "/api/parent/register", {"name": "Ibu H", "whatsapp": "081234567891", "email": "http@x.co", "consent": True, "pin": "123456"})[2])
    st, _, raw = _req(base, "POST", "/api/parent/login", {"email": "http@x.co", "pin": "123456"})
    assert st == 200
    pt = json.loads(raw)["token"]
    st2, _, raw2 = _req(base, "GET", "/api/parent/reports", headers={"X-Token": pt})
    assert st2 == 200 and "summary" in json.loads(raw2) and "trends" in json.loads(raw2)


def test_http_child_lab_code_and_season_map(srv):
    base = srv(playtest=True)
    reg = json.loads(_req(base, "POST", "/api/parent/register", {"name": "Ibu L", "whatsapp": "081234567892", "email": "lab@x.co", "consent": True, "pin": "123456"})[2])
    st, _, raw = _req(base, "POST", "/api/child/login", {"code": reg["access_code"]})
    assert st == 200
    ct = json.loads(raw)["token"]
    st2, _, raw2 = _req(base, "GET", "/api/child/season-map", headers={"X-Token": ct})
    assert st2 == 200 and len(json.loads(raw2)["windows"]) == 12


def test_http_child_tryout_submit_and_buku_salah(srv):
    base = srv(playtest=True)
    reg = json.loads(_req(base, "POST", "/api/parent/register", {"name": "Ibu B", "whatsapp": "081234567893", "email": "bs@x.co", "consent": True, "pin": "123456"})[2])
    ct = json.loads(_req(base, "POST", "/api/child/login", {"code": reg["child_code"]})[2])["token"]
    st, _, raw = _req(base, "POST", "/api/child/tryouts/DIAG/start", headers={"X-Token": ct, "X-Sim-Time": "2026-11-06T18:00"})
    assert st == 200
    att = json.loads(raw)["attempt"]
    st2, _, raw2 = _req(base, "POST", f"/api/child/attempts/{att}/submit", {"answers": {}}, headers={"X-Token": ct, "X-Sim-Time": "2026-11-06T18:20"})
    assert st2 == 200 and json.loads(raw2)["gamification"]["stars"] == 0
    st3, _, raw3 = _req(base, "GET", "/api/child/buku-salah", headers={"X-Token": ct})
    assert st3 == 200 and json.loads(raw3)["total"] == 12


def test_http_parent_buku_salah_and_prestasi_stub(srv):
    base = srv(playtest=True)
    reg = json.loads(_req(base, "POST", "/api/parent/register", {"name": "Ibu P", "whatsapp": "081234567894", "email": "pr@x.co", "consent": True, "pin": "123456"})[2])
    pt = reg["token"]
    st, _, raw = _req(base, "GET", "/api/parent/buku-salah", headers={"X-Token": pt})
    assert st == 200 and json.loads(raw)["addon_available"] is True
    st2, _, raw2 = _req(base, "POST", "/api/parent/prestasi", {"proof_ref": "JAPRES-001"}, headers={"X-Token": pt})
    assert st2 == 200 and json.loads(raw2)["discount_percent"] == "TBD"


def test_http_admin_standin_corrupted_job_recovery(srv):
    base = srv(playtest=True)
    reg = json.loads(_req(base, "POST", "/api/parent/register", {"name": "Ibu G", "whatsapp": "081234567895", "email": "g22@x.co", "consent": True, "pin": "123456"})[2])
    ct = json.loads(_req(base, "POST", "/api/child/login", {"code": reg["child_code"]})[2])["token"]
    s = json.loads(_req(base, "POST", "/api/child/tryouts/DIAG/start", headers={"X-Token": ct, "X-Sim-Time": "2026-11-06T18:00"})[2])
    _req(base, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {}}, headers={"X-Token": ct, "X-Sim-Time": "2026-11-06T18:10"})
    st, _, raw = _req(base, "POST", "/api/admin/analysis/standin", headers={"X-Admin-Token": "dev-admin"})
    assert st == 200 and json.loads(raw)["diproses"] == 1


def test_http_child_drill_start_and_finish(srv):
    base = srv(playtest=True)
    reg = json.loads(_req(base, "POST", "/api/parent/register", {"name": "Ibu D", "whatsapp": "081234567896", "email": "dr@x.co", "consent": True, "pin": "123456"}, headers={"X-Sim-Time": "2026-11-04T10:00"})[2])
    ct = json.loads(_req(base, "POST", "/api/child/login", {"code": reg["child_code"]})[2])["token"]
    s = json.loads(_req(base, "POST", "/api/child/tryouts/DIAG/start", headers={"X-Token": ct, "X-Sim-Time": "2026-11-06T18:00"})[2])
    _req(base, "POST", f"/api/child/attempts/{s['attempt']}/submit", {"answers": {}}, headers={"X-Token": ct, "X-Sim-Time": "2026-11-06T18:10"})
    _req(base, "POST", "/api/admin/analysis/standin", headers={"X-Admin-Token": "dev-admin", "X-Sim-Time": "2026-11-09T05:00"})
    dr = json.loads(_req(base, "GET", "/api/child/drills", headers={"X-Token": ct, "X-Sim-Time": "2026-11-09T10:00"})[2])["drills"][0]
    st, _, raw = _req(base, "GET", f"/api/child/drills/{dr['assignment']}/sessions/{dr['session']}/start", headers={"X-Token": ct, "X-Sim-Time": "2026-11-09T10:00"})
    assert st == 200 and len(json.loads(raw)["questions"]) == 5


def test_http_static_css_and_svg_assets_served(srv, tmp_path):
    base = srv()
    st, h, raw = _req(base, "GET", "/index.html")
    assert st == 200 and b"halo" in raw and h["Cache-Control"] == "no-cache"


def test_http_pin_reset_flow_roundtrip(srv):
    base = srv(playtest=True)
    _req(base, "POST", "/api/parent/register", {"name": "Ibu R", "whatsapp": "081234567897", "email": "rst@x.co", "consent": True, "pin": "123456"})
    st, _, raw = _req(base, "POST", "/api/parent/pin/reset-request", {"email": "rst@x.co"})
    assert st == 200 and json.loads(raw)["ok"] is True
