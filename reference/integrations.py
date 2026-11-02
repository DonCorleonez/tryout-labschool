"""Adaptor pihak ketiga: payment gateway (Duitku POP) dan email (Resend). Stdlib saja.

Semua kunci dari environment, tidak pernah dari kode/repo. Transport HTTP bisa disuntik supaya tes tidak menyentuh jaringan.
Sumber kontrak Duitku POP (dibaca 2 Nov 2026, docs.duitku.com/pop/en):
  createInvoice  POST {base}/api/merchant/createInvoice, header x-duitku-signature = HMAC_SHA256(merchantCode + timestamp, apiKey),
                 x-duitku-timestamp (ms, WIB), x-duitku-merchantcode. Body: paymentAmount, merchantOrderId, productDetails, email,
                 callbackUrl, returnUrl. Respon: reference, paymentUrl, statusCode "00".
  callback       POST form-urlencoded; signature = HMAC_SHA256(merchantCode + amount + merchantOrderId, apiKey);
                 resultCode "00" sukses, "01"/"02" gagal. Wajib balas HTTP 200, kalau tidak Duitku mengulang s.d. 5 kali.
Resend: POST https://api.resend.com/emails, Authorization: Bearer <key>, JSON {from, to, subject, text, html}, header Idempotency-Key.
"""
from __future__ import annotations

import hashlib, hmac, json, secrets, time, urllib.request

DUITKU_BASE = {"sandbox": "https://api-sandbox.duitku.com", "production": "https://api-prod.duitku.com"}


def _http_post_json(url, body: dict, headers: dict, timeout=20):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **headers}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read() or b"{}")


class GatewayError(Exception):
    pass


# ---------------- payment ----------------
class SimGateway:
    """Tanpa uang sungguhan. Dipakai lokal/playtest. Pembayaran diselesaikan lewat rute /api/playtest/.../pay."""
    name = "sim"

    def create_invoice(self, order_ref, amount, email, product, callback_url, return_url):
        return {"reference": "SIM-" + secrets.token_hex(3).upper(), "payment_url": None}

    def parse_callback(self, form: dict):
        raise GatewayError("sim tidak menerima callback")


class DuitkuGateway:
    name = "duitku"

    def __init__(self, merchant_code, api_key, sandbox=True, http=_http_post_json, clock=lambda: int(time.time() * 1000)):
        if not merchant_code or not api_key:
            raise GatewayError("DUITKU_MERCHANT_CODE dan DUITKU_API_KEY wajib diisi")
        self.code, self.key, self.http, self.clock = merchant_code, api_key, http, clock
        self.base = DUITKU_BASE["sandbox" if sandbox else "production"]

    def _hmac(self, s: str) -> str:
        return hmac.new(self.key.encode(), s.encode(), hashlib.sha256).hexdigest()

    def create_invoice(self, order_ref, amount, email, product, callback_url, return_url):
        ts = str(self.clock())
        headers = {"x-duitku-signature": self._hmac(self.code + ts), "x-duitku-timestamp": ts, "x-duitku-merchantcode": self.code}
        body = {"paymentAmount": int(amount), "merchantOrderId": order_ref, "productDetails": product[:255], "email": email[:255],
                "callbackUrl": callback_url, "returnUrl": return_url, "expiryPeriod": 60 * 24}
        try:
            status, out = self.http(self.base + "/api/merchant/createInvoice", body, headers)
        except Exception as e:                      # noqa: BLE001  jaringan/HTTP error -> pesanan tetap tercatat 'dibuat'
            raise GatewayError(f"createInvoice gagal: {type(e).__name__}") from e
        if status != 200 or out.get("statusCode") != "00" or not out.get("paymentUrl"):
            raise GatewayError(f"createInvoice ditolak: {out.get('statusCode')} {out.get('statusMessage')}")
        return {"reference": out["reference"], "payment_url": out["paymentUrl"]}

    def parse_callback(self, form: dict) -> dict:
        """Verifikasi tanda tangan. Kembalikan {ok, status, order_ref, amount, reference, event_id}."""
        g = lambda k: str(form.get(k, "") or "")
        expected = self._hmac(self.code + g("amount") + g("merchantOrderId"))
        ok = g("merchantCode") == self.code and hmac.compare_digest(expected, g("signature"))
        status = "paid" if g("resultCode") == "00" else "failed"
        try:
            amount = int(float(g("amount")))
        except ValueError:
            amount = -1
        return {"ok": ok, "status": status, "order_ref": g("merchantOrderId"), "amount": amount, "reference": g("reference"),
                "event_id": f"duitku:{g('reference')}:{g('resultCode')}"}


# ---------------- email ----------------
class LogMailer:
    """Tidak mengirim apa pun; outbox ditandai 'log'. Dipakai lokal/playtest sampai Resend siap."""
    name = "log"

    def send(self, to, subject, text, html=None, idem=None):
        return {"id": "log-" + secrets.token_hex(4)}


class ResendMailer:
    name = "resend"

    def __init__(self, api_key, sender, http=_http_post_json):
        if not api_key or not sender:
            raise GatewayError("RESEND_API_KEY dan MAIL_FROM wajib diisi")
        self.key, self.sender, self.http = api_key, sender, http

    def send(self, to, subject, text, html=None, idem=None):
        body = {"from": self.sender, "to": [to], "subject": subject, "text": text}
        if html: body["html"] = html
        headers = {"Authorization": "Bearer " + self.key}
        if idem: headers["Idempotency-Key"] = idem
        status, out = self.http("https://api.resend.com/emails", body, headers)
        if status not in (200, 201) or not out.get("id"):
            raise GatewayError(f"resend gagal: {status}")
        return {"id": out["id"]}


def gateway_from_env(e) -> object:
    kind = (e.get("GATEWAY") or "sim").lower()
    if kind == "sim": return SimGateway()
    if kind == "duitku":
        return DuitkuGateway(e.get("DUITKU_MERCHANT_CODE", ""), e.get("DUITKU_API_KEY", ""), sandbox=str(e.get("DUITKU_SANDBOX", "1")) in ("1", "true", "yes"))
    raise GatewayError("GATEWAY tidak dikenal: " + kind)


def mailer_from_env(e) -> object:
    kind = (e.get("MAIL") or "log").lower()
    if kind == "log": return LogMailer()
    if kind == "resend": return ResendMailer(e.get("RESEND_API_KEY", ""), e.get("MAIL_FROM", ""))
    raise GatewayError("MAIL tidak dikenal: " + kind)
