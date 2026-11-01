"""Server HTTP produksi/playtest (stdlib) di atas App.handle.

Jalankan:  python3 server.py            (baca konfigurasi dari environment, lihat Config)
Satu proses, ThreadingHTTPServer + satu kunci untuk SQLite (penulis tunggal; cukup untuk ratusan keluarga).
"""
from __future__ import annotations

import json, mimetypes, os, sys, threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backend import App  # noqa: E402

MAX_BODY = 256 * 1024
DEV_SECRETS = {"dev-secret", "dev-admin", ""}


class ConfigError(Exception):
    pass


@dataclass
class Config:
    host: str = "127.0.0.1"
    port: int = 8080
    db_path: str = "tryout.db"
    webhook_secret: str = "dev-secret"
    admin_token: str = "dev-admin"
    playtest: bool = False
    public_host: str = "localhost"                       # host yang dilayani (mis. playtest.contoh.id)
    production_hosts: set = field(default_factory=set)   # host yang dianggap produksi
    public_dir: str = str(Path(__file__).resolve().parent.parent / "public")
    trust_proxy: bool = False                            # True bila di belakang Cloudflare Tunnel/reverse proxy

    @classmethod
    def from_env(cls, env=None) -> "Config":
        e = os.environ if env is None else env
        flag = lambda k: str(e.get(k, "")).strip().lower() in ("1", "true", "yes")
        c = cls()
        c.host = e.get("HOST", c.host); c.port = int(e.get("PORT", c.port))
        c.db_path = e.get("DB_PATH", c.db_path)
        c.webhook_secret = e.get("WEBHOOK_SECRET", c.webhook_secret); c.admin_token = e.get("ADMIN_TOKEN", c.admin_token)
        c.playtest = flag("PLAYTEST"); c.trust_proxy = flag("TRUST_PROXY")
        c.public_host = e.get("PUBLIC_HOST", c.public_host).strip().lower()
        c.production_hosts = {h.strip().lower() for h in e.get("PRODUCTION_HOSTS", "").split(",") if h.strip()}
        c.public_dir = e.get("PUBLIC_DIR", c.public_dir)
        return c

    @property
    def is_production(self) -> bool:
        return self.public_host in self.production_hosts

    def validate(self) -> None:
        """Invarian 13: mode playtest (X-Sim-Time) tidak boleh hidup di domain produksi."""
        if self.is_production and self.playtest:
            raise ConfigError("PLAYTEST=1 dilarang di host produksi " + self.public_host)
        if self.is_production and (self.webhook_secret in DEV_SECRETS or self.admin_token in DEV_SECRETS):
            raise ConfigError("WEBHOOK_SECRET dan ADMIN_TOKEN wajib diisi nilai rahasia di produksi")
        if self.is_production and self.db_path == ":memory:":
            raise ConfigError("DB_PATH :memory: tidak boleh di produksi")


SEC_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'",
}


def make_handler(app: App, cfg: Config, lock: threading.Lock):
    public = Path(cfg.public_dir).resolve()

    class H(BaseHTTPRequestHandler):
        server_version = "tryout"
        sys_version = ""

        def log_message(self, fmt, *args):            # log tanpa data pribadi: metode, jalur, status saja
            if os.environ.get("QUIET_LOG"): return
            sys.stderr.write("%s %s\n" % (self.log_date_time_string(), fmt % args))

        def _ip(self):
            if cfg.trust_proxy:
                v = self.headers.get("CF-Connecting-IP") or (self.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
                if v: return v
            return self.client_address[0]

        def _send(self, status, body: bytes, ctype: str, extra=None):
            self.send_response(status)
            self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
            for k, v in SEC_HEADERS.items(): self.send_header(k, v)
            if cfg.playtest: self.send_header("X-Robots-Tag", "noindex, nofollow")
            for k, v in (extra or {}).items(): self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD": self.wfile.write(body)

        def _json(self, status, obj):
            self._send(status, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8", {"Cache-Control": "no-store"})

        def _api(self, path):
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY: return self._json(413, {"error": "terlalu_besar"})
            body = self.rfile.read(n) if n else b""
            hdrs = dict(self.headers.items())
            if not cfg.playtest: hdrs = {k: v for k, v in hdrs.items() if k.lower() != "x-sim-time"}
            with lock:
                status, out = app.handle(self.command, path, hdrs, body, ip=self._ip())
            self._json(status, out)

        def _static(self, path):
            if path == "/robots.txt" and cfg.playtest:
                return self._send(200, b"User-agent: *\nDisallow: /\n", "text/plain; charset=utf-8")
            rel = unquote(path).lstrip("/")
            p = (public / rel).resolve()
            if public not in p.parents and p != public: return self._json(404, {"error": "tidak_ada"})
            if p.is_dir(): p = p / "index.html"
            if not p.is_file(): return self._json(404, {"error": "tidak_ada"})
            ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"): ctype += "; charset=utf-8"
            self._send(200, p.read_bytes(), ctype, {"Cache-Control": "no-cache"})

        def _route(self):
            path = urlsplit(self.path).path
            try:
                if path == "/healthz": return self._json(200, {"ok": True, "playtest": cfg.playtest})
                if path.startswith("/api/"): return self._api(path)
                if self.command in ("GET", "HEAD"): return self._static(path)
                return self._json(405, {"error": "metode"})
            except Exception:                         # jangan bocorkan stack trace ke klien
                import traceback; traceback.print_exc()
                return self._json(500, {"error": "galat_server"})

        do_GET = do_POST = do_HEAD = _route

    return H


def build(cfg: Config):
    cfg.validate()
    app = App(db_path=cfg.db_path, webhook_secret=cfg.webhook_secret, admin_token=cfg.admin_token, playtest=cfg.playtest)
    if cfg.db_path != ":memory:":
        app.db.execute("PRAGMA journal_mode=WAL")
    srv = ThreadingHTTPServer((cfg.host, cfg.port), make_handler(app, cfg, threading.Lock()))
    srv.daemon_threads = True
    return srv, app


def main():
    cfg = Config.from_env()
    try:
        srv, _ = build(cfg)
    except ConfigError as e:
        sys.stderr.write("KONFIGURASI DITOLAK: %s\n" % e); sys.exit(2)
    print(f"tryout server di http://{cfg.host}:{srv.server_address[1]} (playtest={cfg.playtest}, host={cfg.public_host})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
