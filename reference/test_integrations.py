"""Tes adaptor Duitku POP + Resend dan alur pesanan -> callback -> aktivasi -> email. Tanpa jaringan (transport palsu)."""
import hashlib, hmac, json
from urllib.parse import urlencode

import pytest

import backend as be
import integrations as ig

MC, KEY = "DS12345", "apikey-uji"


def fake_http(store, reply=None):
    def http(url, body, headers):
        store.append((url, body, headers))
        return reply or (200, {"merchantCode": MC, "reference": "DS1234526XYZ", "paymentUrl": "https://sandbox.duitku.com/pay/abc", "statusCode": "00", "statusMessage": "SUCCESS"})
    return http


def sig(amount, order):
    return hmac.new(KEY.encode(), (MC + str(amount) + order).encode(), hashlib.sha256).hexdigest()


def cb_form(order, amount=499000, result="00", ref="DS1234526XYZ", signature=None):
    return urlencode({"merchantCode": MC, "amount": str(amount), "merchantOrderId": order, "resultCode": result, "reference": ref,
                      "signature": signature or sig(amount, order), "paymentCode": "SP"}).encode()


def test_create_invoice_signature_and_body():
    calls = []
    g = ig.DuitkuGateway(MC, KEY, sandbox=True, http=fake_http(calls), clock=lambda: 1773728479616)
    out = g.create_invoice("ord_1", 499000, "a@b.co", "Paket", "https://x/cb", "https://x/ret")
    url, body, h = calls[0]
    assert url == "https://api-sandbox.duitku.com/api/merchant/createInvoice"
    assert h["x-duitku-signature"] == hmac.new(KEY.encode(), (MC + "1773728479616").encode(), hashlib.sha256).hexdigest()
    assert body["paymentAmount"] == 499000 and body["merchantOrderId"] == "ord_1" and out["payment_url"].startswith("https://")


def test_production_base_url():
    assert ig.DuitkuGateway(MC, KEY, sandbox=False).base == "https://api-prod.duitku.com"


def test_create_invoice_rejected_raises():
    g = ig.DuitkuGateway(MC, KEY, http=fake_http([], (200, {"statusCode": "01", "statusMessage": "x"})))
    with pytest.raises(ig.GatewayError):
        g.create_invoice("o", 1, "a@b.co", "p", "c", "r")


def test_missing_keys_refused():
    with pytest.raises(ig.GatewayError): ig.DuitkuGateway("", "")
    with pytest.raises(ig.GatewayError): ig.ResendMailer("", "")


@pytest.fixture
def app():
    calls, mails = [], []
    gw = ig.DuitkuGateway(MC, KEY, http=fake_http(calls))
    ml = ig.ResendMailer("re_test", "Tryout <halo@contoh.id>", http=lambda u, b, h: (mails.append((b, h)) or (200, {"id": "em_1"})))
    a = be.App(gateway=gw, mailer=ml, base_url="https://labschool.doncorleonez.my.id")
    a._calls, a._mails = calls, mails
    return a


def _parent(app):
    st, r = app.handle("POST", "/api/parent/register", {}, json.dumps({"name": "I", "whatsapp": "081234567890", "email": "ortu@contoh.id", "consent": True, "pin": "123456"}).encode())
    return r["token"]


def _cb(app, body):
    return app.handle("POST", "/api/webhooks/duitku", {"Content-Type": "application/x-www-form-urlencoded"}, body)


def test_full_flow_order_callback_activation_email(app):
    tok = _parent(app)
    st, o = app.handle("POST", "/api/parent/orders", {"X-Token": tok}, b"{}")
    assert st == 200 and o["payment_url"] == "https://sandbox.duitku.com/pay/abc" and o["amount_idr"] == 499000
    assert app._calls[0][1]["callbackUrl"] == "https://labschool.doncorleonez.my.id/api/webhooks/duitku"
    st, again = app.handle("POST", "/api/parent/orders", {"X-Token": tok}, b"{}")            # klik ganda: invoice sama, tidak buat baru
    assert again["order"] == o["order"] and len(app._calls) == 1
    assert _cb(app, cb_form(o["order"]))[0] == 200
    assert app.db.execute("SELECT plan FROM families").fetchone()[0] == "utama"
    assert _cb(app, cb_form(o["order"]))[1] == {"duplikat": True}                                # callback diulang Duitku
    assert app.flush_outbox() == 2                                                              # selamat datang + lunas
    subjects = [b["subject"] for b, h in app._mails]
    assert "Pembayaran diterima: paket utama aktif" in subjects and all(h["Idempotency-Key"] for b, h in app._mails)
    assert app.flush_outbox() == 0                                                              # tidak terkirim dua kali


def test_welcome_email_never_contains_child_code(app):
    st, r = app.handle("POST", "/api/parent/register", {}, json.dumps({"name": "I", "whatsapp": "081234567899", "email": "w@contoh.id", "consent": True, "pin": "123456"}).encode())
    app.flush_outbox()
    assert all(r["child_code"] not in b["text"] for b, h in app._mails)


def test_bad_signature_wrong_amount_and_failed_result(app):
    tok = _parent(app)
    o = app.handle("POST", "/api/parent/orders", {"X-Token": tok}, b"{}")[1]
    assert _cb(app, cb_form(o["order"], signature="0" * 64))[0] == 401
    assert _cb(app, cb_form(o["order"], amount=1000))[1]["error"] == "jumlah_tidak_cocok"     # tanda tangan sah tapi nominal beda
    assert _cb(app, cb_form(o["order"], result="01"))[1]["status"] == "failed"
    assert app.db.execute("SELECT plan FROM families").fetchone()[0] == "free"


def test_gateway_down_keeps_order_trace(app):
    app.gateway.http = lambda u, b, h: (_ for _ in ()).throw(OSError("down"))
    tok = _parent(app)
    st, e = app.handle("POST", "/api/parent/orders", {"X-Token": tok}, b"{}")
    assert st == 502 and e["error"] == "gateway_gagal"
    assert app.db.execute("SELECT status FROM orders").fetchone()[0] == "dibuat"
    assert app.db.execute("SELECT COUNT(*) FROM order_events WHERE kind='gateway_gagal'").fetchone()[0] == 1


def test_email_retry_then_gagal(app):
    _parent(app)
    app.mailer.http = lambda u, b, h: (500, {})
    for _ in range(5): app.flush_outbox()
    assert app.db.execute("SELECT status, attempts FROM email_outbox").fetchone()[:] == ("gagal", 5)


def test_duitku_route_absent_with_sim_gateway():
    assert be.App().handle("POST", "/api/webhooks/duitku", {"Content-Type": "application/x-www-form-urlencoded"}, b"a=1")[0] == 404


def test_from_env():
    assert isinstance(ig.gateway_from_env({}), ig.SimGateway) and isinstance(ig.mailer_from_env({}), ig.LogMailer)
    g = ig.gateway_from_env({"GATEWAY": "duitku", "DUITKU_MERCHANT_CODE": MC, "DUITKU_API_KEY": KEY, "DUITKU_SANDBOX": "0"})
    assert g.base.endswith("api-prod.duitku.com")
