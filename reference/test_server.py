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
    cfg.validate()


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
