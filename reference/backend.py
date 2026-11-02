"""Backend referensi (stdlib + SQLite). Menegakkan aturan di SERVER: jendela, urutan, timer, kunci tidak bocor,
webhook bertanda tangan dan idempoten, data tryout dikumpulkan dulu lalu dianalisa belakangan.

Bukan kode produksi final; ini spesifikasi yang bisa dijalankan dan diuji. Muse boleh memindahkannya ke kerangka kerja pilihan
selama tes di test_backend.py tetap lulus.
"""
from __future__ import annotations

import hashlib, hmac, json, re, secrets, sqlite3, zlib
from datetime import datetime, timedelta
from pathlib import Path

import analysis as an
import bank
import schedule as sc

TRYOUT_LIMIT_SEC = 7200          # durasi satu tryout (placeholder sampai spesifikasi format final)
# KEPUTUSAN PEMILIK 2026-11-01: tryout yang DIMULAI sebelum jendela tutup (Min 16.00) diterima sampai selesai,
# paling lama TRYOUT_LIMIT_SEC (2 jam) sejak mulai. Tidak ada masa tenggang lain.
PIN_MAX_FAILS = 5                # per keluarga
PIN_LOCK_MIN = 15
PIN_ITER = 120_000
FREE_DIAG_ANYTIME = True         # kebijakan diagnostik gratis A (kapan saja) / B (hanya di jendela)
MAX_LOGIN_FAILS = 5              # per IP per 10 menit
IDR = {"utama": 499_000, "kejar": None}   # harga = keputusan pemilik (2 Nov 2026: paket utama Rp499.000; mode kejar belum ditetapkan)

iso = lambda d: d.isoformat()
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
def hash_pin(pin, salt=None):
    salt = salt or secrets.token_hex(8)
    return salt + "$" + hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), PIN_ITER).hex()


def check_pin(pin, stored):
    salt, _ = stored.split("$", 1)
    return hmac.compare_digest(hash_pin(pin, salt), stored)


DIAG_SEED = 20261106     # KEPUTUSAN PEMILIK 2 Nov: diagnostik = SATU set soal yang sama untuk semua siswa,
                         # supaya mendaftar ulang dengan akun lain tidak membuka soal baru. Ganti hanya dengan versi bank baru.
_seed = lambda fid, tid: DIAG_SEED if tid == "DIAG" else zlib.crc32(f"{fid}:{tid}".encode()) & 0xFFFF   # deterministik antar proses


class Err(Exception):
    def __init__(self, status, code, msg=""):
        self.status, self.code, self.msg = status, code, msg


class App:
    def __init__(self, db_path=":memory:", now=None, webhook_secret="dev-secret", admin_token="dev-admin", playtest=False):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript((Path(__file__).with_name("schema.sql")).read_text())
        self._now = now or (lambda: datetime.now(sc.WIB))
        self.secret, self.admin_token, self.playtest = webhook_secret.encode(), admin_token, playtest
        self.routes = [(m, re.compile("^" + p + "$"), fn) for m, p, fn in [
            ("POST", r"/api/parent/register", self.register), ("POST", r"/api/parent/login", self.parent_login), ("POST", r"/api/child/login", self.child_login),
            ("GET", r"/api/child/home", self.child_home), ("POST", r"/api/child/tryouts/(?P<tid>[A-Z0-9-]+)/start", self.start),
            ("POST", r"/api/child/attempts/(?P<ref>att_\w+)/events", self.events), ("POST", r"/api/child/attempts/(?P<ref>att_\w+)/submit", self.submit),
            ("GET", r"/api/child/drills", self.drills), ("POST", r"/api/child/drills/(?P<aid>\d+)/sessions/(?P<n>\d+)/finish", self.drill_finish),
            ("POST", r"/api/parent/orders", self.order_new), ("POST", r"/api/webhooks/payment", self.webhook),
            ("GET", r"/api/parent/report/latest", self.report_latest), ("GET", r"/api/parent/home", self.parent_home),
            ("POST", r"/api/playtest/orders/(?P<oref>ord_\w+)/pay", self.playtest_pay),
            ("GET", r"/api/admin/queue", self.admin_queue), ("POST", r"/api/admin/analysis/standin", self.admin_standin),
            ("GET", r"/api/admin/export.jsonl", self.admin_export), ("POST", r"/api/admin/families/(?P<fref>fam_\w+)/revoke", self.admin_revoke)]]

    # ---------- infrastruktur ----------
    def now(self, headers=None):
        h = headers or {}
        if self.playtest and h.get("x-sim-time"):
            return datetime.fromisoformat(h["x-sim-time"]).replace(tzinfo=sc.WIB)
        return self._now()

    def handle(self, method, path, headers=None, body=b"", ip="0.0.0.0"):
        headers = {k.lower(): v for k, v in (headers or {}).items()}
        try:
            for m, rx, fn in self.routes:
                mt = rx.match(path) if m == method else None
                if mt:
                    ctx = {"h": headers, "raw": body, "ip": ip, "now": self.now(headers), "args": mt.groupdict()}
                    try:
                        ctx["json"] = json.loads(body) if body else {}
                    except ValueError:
                        raise Err(400, "json_tidak_valid")
                    out = fn(ctx)
                    self.db.commit()
                    return 200, out
            raise Err(404, "tidak_ada")
        except Err as e:
            self.db.rollback()
            return e.status, {"error": e.code, "message": e.msg}

    def _session(self, ctx, role):
        tok = ctx["h"].get("x-token", "")
        r = self.db.execute("SELECT s.*, f.public_ref, f.plan, f.join_window, f.revoked FROM sessions s JOIN families f ON f.id=s.family_id WHERE token_hash=? AND role=?", (sha(tok), role)).fetchone()
        if not r:
            raise Err(401, "belum_masuk")
        if r["revoked"]:
            raise Err(403, "akses_dinonaktifkan", "Minta orang tua menghubungi kami.")
        return r

    def _admin(self, ctx):
        if not hmac.compare_digest(ctx["h"].get("x-admin-token", ""), self.admin_token):
            raise Err(403, "bukan_admin")

    def _fam(self, fid):
        return self.db.execute("SELECT * FROM families WHERE id=?", (fid,)).fetchone()

    # ---------- orang tua ----------
    def register(self, c):
        j = c["json"]; errs = {}
        if not str(j.get("name", "")).strip(): errs["name"] = "wajib"
        if not re.match(r"^(\+62|62|0)8\d{7,11}$", re.sub(r"[\s-]", "", str(j.get("whatsapp", "")))): errs["whatsapp"] = "format"
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(j.get("email", ""))): errs["email"] = "format"
        if not j.get("consent"): errs["consent"] = "wajib"
        if not re.match(r"^\d{6}$", str(j.get("pin", ""))): errs["pin"] = "6 angka"
        if errs: raise Err(422, "validasi", json.dumps(errs))
        wa = re.sub(r"[\s-]", "", str(j["whatsapp"])); wa = "0" + wa[3:] if wa.startswith("+62") else ("0" + wa[2:] if wa.startswith("62") else wa)
        dup = self.db.execute("SELECT 1 FROM marketing_leads WHERE lower(email)=? OR replace(replace(replace(whatsapp,' ',''),'-',''),'+62','0')=? OR whatsapp=?",
                              (str(j["email"]).strip().lower(), wa, "62" + wa[1:])).fetchone()
        if dup: raise Err(409, "sudah_terdaftar", "Email atau nomor WhatsApp ini sudah terdaftar. Silakan masuk.")   # satu siswa, satu diagnostik gratis
        code = f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"
        ref = "fam_" + secrets.token_hex(5)
        cur = self.db.execute("INSERT INTO families(public_ref,code_hash,pin_hash,plan,join_window,created_at) VALUES(?,?,?,?,?,?)",
                              (ref, sha(code), hash_pin(str(j["pin"])), "free", sc.join_window(c["now"]), iso(c["now"])))
        fid = cur.lastrowid
        self.db.execute("INSERT INTO marketing_leads(family_id,parent_name,whatsapp,email,campus,track,grade,consent_at) VALUES(?,?,?,?,?,?,?,?)",
                        (fid, j["name"], j["whatsapp"], j["email"], j.get("campus"), j.get("track"), j.get("grade"), iso(c["now"])))
        tok = secrets.token_urlsafe(24)
        self.db.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?)", (sha(tok), fid, "parent", c["h"].get("user-agent", ""), iso(c["now"]), iso(c["now"])))
        return {"token": tok, "family_ref": ref, "child_code": code, "join_window": sc.join_window(c["now"])}   # kode asli hanya sekali

    def parent_login(self, c):
        """Masuk orang tua: email + PIN 6 angka. Salah >= PIN_MAX_FAILS dalam PIN_LOCK_MIN menit => terkunci (per keluarga)."""
        j = c["json"]; email = str(j.get("email", "")).strip().lower(); ip = sha(c["ip"])
        r = self.db.execute("SELECT f.* FROM marketing_leads m JOIN families f ON f.id=m.family_id WHERE lower(m.email)=? ORDER BY f.id DESC LIMIT 1", (email,)).fetchone()
        kind = f"parent:{r['id']}" if r else "parent:?"
        since = iso(c["now"] - timedelta(minutes=PIN_LOCK_MIN))
        fails = self.db.execute("SELECT COUNT(*) n FROM login_attempts WHERE kind=? AND at>?", (kind, since)).fetchone()["n"] if r else \
            self.db.execute("SELECT COUNT(*) n FROM login_attempts WHERE ip_hash=? AND kind='parent:?' AND at>?", (ip, since)).fetchone()["n"]
        if fails >= PIN_MAX_FAILS: raise Err(429, "terkunci", f"Terlalu banyak percobaan. Coba lagi dalam {PIN_LOCK_MIN} menit atau gunakan Lupa PIN.")
        if not r or not r["pin_hash"] or not check_pin(str(j.get("pin", "")), r["pin_hash"]):
            self.db.execute("INSERT INTO login_attempts VALUES(?,?,?)", (ip, kind, iso(c["now"]))); self.db.commit()
            raise Err(401, "email_atau_pin_salah", "Email atau PIN salah.")                 # tidak membocorkan email mana yang terdaftar
        if r["revoked"]: raise Err(403, "akses_dinonaktifkan")
        self.db.execute("DELETE FROM login_attempts WHERE kind=?", (kind,))
        tok = secrets.token_urlsafe(24)
        self.db.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?)", (sha(tok), r["id"], "parent", c["h"].get("user-agent", ""), iso(c["now"]), iso(c["now"])))
        return {"token": tok, "family_ref": r["public_ref"]}

    def report_latest(self, c):
        s = self._session(c, "parent")
        r = self.db.execute("SELECT * FROM reports WHERE family_id=? AND status='terbit' ORDER BY window_k DESC LIMIT 1", (s["family_id"],)).fetchone()
        if not r:
            pend = self.db.execute("SELECT COUNT(*) n FROM attempts WHERE family_id=? AND analysis_state='menunggu'", (s["family_id"],)).fetchone()["n"]
            return {"report": None, "menunggu_analisa": pend}
        w = sc.WINDOWS[r["window_k"] - 1]
        if s["plan"] != "free" and c["now"] < w.drill_open + timedelta(hours=1):          # laporan berbayar terbit Senin 07.00
            return {"report": None, "terbit_pada": iso(w.drill_open + timedelta(hours=1))}
        return {"report": {"window": r["window_k"], "headline": r["headline"], "body": json.loads(r["body_json"]), "mode": r["mode"]}}

    # ---------- anak ----------
    def child_login(self, c):
        ip = sha(c["ip"]); since = iso(c["now"] - timedelta(minutes=10))
        fails = self.db.execute("SELECT COUNT(*) n FROM login_attempts WHERE ip_hash=? AND kind='child' AND at>?", (ip, since)).fetchone()["n"]
        if fails >= MAX_LOGIN_FAILS: raise Err(429, "terlalu_sering")
        f = self.db.execute("SELECT * FROM families WHERE code_hash=?", (sha(str(c["json"].get("code", "")).upper().strip()),)).fetchone()
        if not f:
            self.db.execute("INSERT INTO login_attempts VALUES(?,?,?)", (ip, "child", iso(c["now"]))); self.db.commit()
            raise Err(401, "kode_tidak_dikenali", "Periksa lagi atau tanya orang tua.")        # tidak membocorkan keberadaan kode
        if f["revoked"]: raise Err(403, "akses_dinonaktifkan")
        tok = secrets.token_urlsafe(24)
        self.db.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?)", (sha(tok), f["id"], "child", c["h"].get("user-agent", ""), iso(c["now"]), iso(c["now"])))
        return {"token": tok}

    def _done_ids(self, fid, k):
        return {r["tryout_id"] for r in self.db.execute("SELECT tryout_id FROM attempts WHERE family_id=? AND window_k=? AND submitted_at IS NOT NULL", (fid, k))}

    def _access(self, s, tid, now):
        """Satu-satunya tempat keputusan 'boleh dibuka'. Dipakai home, start, dan submit."""
        st = sc.clock_state(now)
        used = self.db.execute("SELECT 1 FROM attempts WHERE family_id=? AND tryout_id=?", (s["family_id"], tid)).fetchone()
        if used: return "sudah_dikerjakan", None
        if s["plan"] == "free":
            if tid != "DIAG": return "paket_gratis_hanya_diagnostik", None
            if FREE_DIAG_ANYTIME and st.kind not in ("hari_tes", "post"): return "", s["join_window"] or 1
        if st.kind != "tryout": return "jendela_tertutup", None
        ids = sc.tryout_ids(s["join_window"], st.window.k, "utama" if s["plan"] != "free" else "free")
        if tid not in ids: return "tidak_tersedia_pada_jendela_ini", None
        if not sc.can_open_tryout(ids, self._done_ids(s["family_id"], st.window.k), tid): return "kumpulkan_tryout_pertama_dulu", None
        return "", st.window.k

    def child_home(self, c):
        s = self._session(c, "child"); st = sc.clock_state(c["now"]); out = {"clock": st.kind, "window": st.window.k if st.window else None, "tryouts": [], "drills": []}
        if st.kind == "tryout":
            ids = sc.tryout_ids(s["join_window"], st.window.k, "utama" if s["plan"] != "free" else "free")
            out["tryouts"] = [{"id": t, "state": self._tryout_state(s, t, st.window.k, c["now"])} for t in ids]
            out["closes_at"] = iso(st.closes_at)
        elif st.kind in ("drill", "taper"):
            out["drills"] = self._drill_rows(s["family_id"], st.window.k)
            out["pending"] = bool(self.db.execute("SELECT 1 FROM attempts WHERE family_id=? AND window_k=? AND analysis_state='menunggu'", (s["family_id"], st.window.k)).fetchone())
        return out

    def _tryout_state(self, s, tid, k, now):
        if tid in self._done_ids(s["family_id"], k): return "selesai"
        a = self.db.execute("SELECT deadline_at FROM attempts WHERE family_id=? AND tryout_id=? AND submitted_at IS NULL", (s["family_id"], tid)).fetchone()
        if a: return "berjalan" if now <= datetime.fromisoformat(a["deadline_at"]) else "terlewat"
        return "siap" if self._access(s, tid, now)[0] == "" else "terkunci"

    def start(self, c):
        s = self._session(c, "child"); tid = c["args"]["tid"]
        a = self.db.execute("SELECT * FROM attempts WHERE family_id=? AND tryout_id=? AND submitted_at IS NULL", (s["family_id"], tid)).fetchone()
        if a and c["now"] <= datetime.fromisoformat(a["deadline_at"]):        # lanjutkan (refresh/putus): soal & tenggat SAMA, tidak membuat attempt baru
            qs = {q["id"]: q for q in bank.get_questions(_seed(s["family_id"], tid))}
            return {"attempt": a["public_ref"], "deadline_at": a["deadline_at"], "resumed": True,
                    "questions": [bank.public(qs[i]) for i in json.loads(a["question_ids"])]}
        why, k = self._access(s, tid, c["now"])
        if why: raise Err(409, why)
        qs = bank.get_questions(_seed(s["family_id"], tid))
        w = sc.WINDOWS[k - 1]; deadline = c["now"] + timedelta(seconds=TRYOUT_LIMIT_SEC)      # tidak dipotong jendela tutup: mulai sebelum 16.00 => boleh selesai
        ref = "att_" + secrets.token_hex(5)
        self.db.execute("INSERT INTO attempts(public_ref,family_id,tryout_id,window_k,started_at,deadline_at,question_ids) VALUES(?,?,?,?,?,?,?)",
                        (ref, s["family_id"], tid, k, iso(c["now"]), iso(deadline), json.dumps([q["id"] for q in qs])))
        return {"attempt": ref, "deadline_at": iso(deadline), "questions": [bank.public(q) for q in qs]}   # TANPA kunci dan pembahasan

    def _attempt(self, c):
        s = self._session(c, "child")
        a = self.db.execute("SELECT * FROM attempts WHERE public_ref=? AND family_id=?", (c["args"]["ref"], s["family_id"])).fetchone()
        if not a: raise Err(404, "tidak_ada")
        return s, a

    def events(self, c):
        s, a = self._attempt(c)
        if a["submitted_at"]: raise Err(409, "sudah_dikumpulkan")
        n = 0
        for e in c["json"].get("events", []):
            cur = self.db.execute("INSERT OR IGNORE INTO attempt_events VALUES(?,?,?,?,?,?,?)", (a["id"], int(e["seq"]), e.get("q"), e["kind"], json.dumps(e.get("value")), e.get("ms"), iso(c["now"])))
            n += cur.rowcount
        return {"diterima": n}                                          # kirim ulang batch yang sama aman (idempoten)

    @staticmethod
    def aggregate(events, n_q):
        """Dari jejak mentah -> data per soal. Waktu idle dikeluarkan dari waktu bersih."""
        per = {i: {"visits": 0, "idle": 0.0, "raw": 0.0, "flag_toggles": 0, "hist": [], "enter": None} for i in range(1, n_q + 1)}
        cur = None
        for e in sorted(events, key=lambda x: x["seq"]):
            q, k, v, ms = e["q_no"], e["kind"], json.loads(e["value"]) if e["value"] else None, e["client_ms"] or 0
            if k == "visit":
                if cur: per[cur]["raw"] += (ms - per[cur]["enter"]) / 1000
                cur = q; per[q]["visits"] += 1; per[q]["enter"] = ms
            elif k == "idle" and q: per[q]["idle"] += float(v or 0)
            elif k == "answer" and q: per[q]["hist"].append(v)
            elif k == "flag" and q: per[q]["flag_toggles"] += 1
            elif k == "end" and cur: per[cur]["raw"] += (ms - per[cur]["enter"]) / 1000; cur = None
        return per

    def submit(self, c):
        s, a = self._attempt(c)
        if a["submitted_at"]:                                           # idempoten: kumpul ulang mengembalikan hasil yang sama
            return json.loads(a["score_json"]) | {"idempoten": True}
        now = c["now"]
        # Jendela hanya dicek saat MULAI (_access). Saat kumpul yang berlaku hanya batas durasi sejak mulai.
        if now > datetime.fromisoformat(a["deadline_at"]):
            raise Err(409, "waktu_habis", "Batas waktu pengerjaan sudah lewat; jawaban tidak dapat dikumpulkan.")
        qs = {q["id"]: q for q in bank.get_questions(_seed(s["family_id"], a["tryout_id"]))}
        order = json.loads(a["question_ids"]); ans_in = {int(k): v for k, v in c["json"].get("answers", {}).items()}
        evs = [dict(r) for r in self.db.execute("SELECT * FROM attempt_events WHERE attempt_id=?", (a["id"],))]
        per = self.aggregate(evs, len(order)); answers = []
        for n, qid in enumerate(order, 1):
            q = qs[qid]; p = per[n]; hist = p["hist"]; ch = ans_in.get(n)
            answers.append(an.Answer(qid, q["subject"], q["topic"], q["ans"], ch, an.clean_seconds(p["raw"], p["idle"]), flagged=bool(c["json"].get("flags", {}).get(str(n))),
                                     changes=max(0, len(hist) - 1), changed_correct_to_wrong=(len(hist) > 1 and q["ans"] in hist[:-1] and ch != q["ans"])))
        sco = an.score(answers); tags = an.classify(answers)
        times = [x.seconds for x in answers]; avg = sum(times) / len(times) if times else 0
        rule = {"tags": tags, "avg_sec": round(avg, 1), "stamina_drop": an.stamina_drop(answers), "blank_tail": an.blank_tail(answers), "matrix": an.time_matrix(sco["pct"], avg)}
        for n, (x, t) in enumerate(zip(answers, tags), 1):
            p = per[n]
            self.db.execute("INSERT INTO attempt_answers VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (a["id"], n, x.qid, x.chosen_idx, x.correct_idx, p["raw"], p["idle"], x.seconds, p["visits"], int(x.flagged), p["flag_toggles"], x.changes, int(x.changed_correct_to_wrong), t["tag"]))
        payload = self._payload(s, a, sco, rule, answers, qs)
        review = self._review(answers, qs, order)
        self.db.execute("UPDATE attempts SET submitted_at=?, score_json=?, rule_json=?, analysis_state='menunggu' WHERE id=?", (iso(now), json.dumps({"score": sco, "review": review}), json.dumps(rule), a["id"]))
        self.db.execute("INSERT INTO analysis_jobs(attempt_id,state,input_json,created_at) VALUES(?,?,?,?)", (a["id"], "menunggu", json.dumps(payload), iso(now)))
        return {"score": sco, "review": review, "analisa": "menunggu"}     # kunci baru boleh keluar SETELAH submit

    @staticmethod
    def _review(answers, qs, order):
        """Pembahasan pasca-submit (bahan Buku Salah). Hanya dipanggil SETELAH attempt tersimpan sebagai dikumpulkan."""
        return [{"no": n, "correct_idx": x.correct_idx, "chosen_idx": x.chosen_idx, "is_correct": x.chosen_idx == x.correct_idx,
                 "explanation": qs[qid].get("explanation", ""), "shortcut": qs[qid].get("shortcut", "")}
                for n, (x, qid) in enumerate(zip(answers, order), 1)]

    def _payload(self, s, a, sco, rule, answers, qs):
        """Payload anonim ke AI: pseudonim keluarga, tanpa nama/nomor/email."""
        return {"schema": "tryout-analysis-input/v1", "attempt_id": a["public_ref"], "family_ref": s["public_ref"], "window": a["window_k"],
                "scores": sco, "rule_signals": {k: v for k, v in rule.items() if k != "tags"},
                "questions": [{"no": n, "qid": x.qid, "subject": x.subject, "topic": x.topic, "correct_idx": x.correct_idx, "chosen_idx": x.chosen_idx,
                               "sec_clean": x.seconds, "flagged": x.flagged, "changes": x.changes, "changed_correct_to_wrong": x.changed_correct_to_wrong, "rule_tag": t["tag"]}
                              for n, (x, t) in enumerate(zip(answers, rule["tags"]), 1)]}

    # ---------- drill ----------
    def _drill_rows(self, fid, k):
        rows = []
        for r in self.db.execute("SELECT * FROM drill_assignments WHERE family_id=? AND source_window=? ORDER BY id", (fid, k)):
            done = {x["session_no"] for x in self.db.execute("SELECT session_no FROM drill_sessions WHERE assignment_id=? AND finished_at IS NOT NULL", (r["id"],))}
            for n in range(1, r["sessions"] + 1):
                rows.append({"assignment": r["id"], "topic": r["topic"], "session": n, "done": n in done})
        first = False
        for x in rows:
            x["state"] = "selesai" if x["done"] else ("siap" if not first else "terkunci"); first = first or not x["done"]
        return rows

    def drills(self, c):
        s = self._session(c, "child"); st = sc.clock_state(c["now"])
        if st.kind not in ("drill", "taper"): raise Err(409, "jendela_tertutup")
        return {"drills": self._drill_rows(s["family_id"], st.window.k)}

    def drill_finish(self, c):
        s = self._session(c, "child"); st = sc.clock_state(c["now"]); aid, n = int(c["args"]["aid"]), int(c["args"]["n"])
        if st.kind not in ("drill", "taper"): raise Err(409, "jendela_tertutup")
        row = next((x for x in self._drill_rows(s["family_id"], st.window.k) if x["assignment"] == aid and x["session"] == n), None)
        if not row: raise Err(404, "tidak_ada")
        if row["state"] != "siap": raise Err(409, "selesaikan_sesi_sebelumnya" if row["state"] == "terkunci" else "sudah_selesai")
        j = c["json"]; self.db.execute("INSERT OR REPLACE INTO drill_sessions(assignment_id,session_no,started_at,finished_at,correct,total) VALUES(?,?,?,?,?,?)", (aid, n, iso(c["now"]), iso(c["now"]), j.get("correct"), j.get("total")))
        return {"ok": True}

    # ---------- pembayaran ----------
    def order_new(self, c):
        s = self._session(c, "parent"); plan = "kejar" if c["now"] >= sc.GATE_PRESTASI else "utama"
        if s["plan"] in ("utama", "kejar"): raise Err(409, "paket_sudah_aktif")
        amount = IDR.get(plan)
        if amount is None: raise Err(409, "harga_belum_ditetapkan", "Paket ini belum dibuka.")    # invarian 14: harga dari server, bukan klien
        ref = "ord_" + secrets.token_hex(4); gw = "SIM-" + secrets.token_hex(3).upper()
        cur = self.db.execute("INSERT INTO orders(public_ref,family_id,plan,amount_idr,status,gateway,gateway_ref,created_at) VALUES(?,?,?,?,?,?,?,?)", (ref, s["family_id"], plan, amount, "menunggu", "sim", gw, iso(c["now"])))
        for kind, d in (("request_diterima_server", plan), ("dikirim_ke_gateway", gw)):
            self.db.execute("INSERT INTO order_events(order_id,kind,detail,at) VALUES(?,?,?,?)", (cur.lastrowid, kind, d, iso(c["now"])))
        return {"order": ref, "status": "menunggu", "gateway_ref": gw, "plan": plan, "amount_idr": amount}

    def _apply_payment(self, o, st, eid, now):
        if o["status"] != "paid":
            self.db.execute("UPDATE orders SET status=?, paid_at=? WHERE id=?", (st, iso(now) if st == "paid" else None, o["id"]))
            self.db.execute("INSERT INTO order_events(order_id,kind,detail,at) VALUES(?,?,?,?)", (o["id"], "webhook_" + st, eid, iso(now)))
            if st == "paid": self.db.execute("UPDATE families SET plan=? WHERE id=?", (o["plan"], o["family_id"]))

    def playtest_pay(self, c):
        """HANYA mode playtest: tombol 'bayar simulasi' tanpa gateway. Di produksi rute ini 404."""
        if not self.playtest: raise Err(404, "tidak_ada")
        s = self._session(c, "parent")
        o = self.db.execute("SELECT * FROM orders WHERE public_ref=? AND family_id=?", (c["args"]["oref"], s["family_id"])).fetchone()
        if not o: raise Err(404, "pesanan_tidak_ada")
        self._apply_payment(o, "paid", "playtest-" + secrets.token_hex(3), c["now"])
        return {"ok": True, "status": "paid"}

    def parent_home(self, c):
        s = self._session(c, "parent"); fid = s["family_id"]; st = sc.clock_state(c["now"])
        atts = [{"tryout": r["tryout_id"], "window": r["window_k"], "submitted_at": r["submitted_at"],
                 "pct": json.loads(r["score_json"])["score"]["pct"] if r["score_json"] else None}
                for r in self.db.execute("SELECT * FROM attempts WHERE family_id=? ORDER BY id", (fid,))]
        orders = [{"order": r["public_ref"], "status": r["status"], "amount_idr": r["amount_idr"], "created_at": r["created_at"]}
                  for r in self.db.execute("SELECT * FROM orders WHERE family_id=? ORDER BY id DESC LIMIT 5", (fid,))]
        offer = "kejar" if c["now"] >= sc.GATE_PRESTASI else "utama"
        return {"family_ref": s["public_ref"], "plan": s["plan"], "join_window": s["join_window"], "clock": st.kind,
                "window": st.window.k if st.window else None, "attempts": atts, "orders": orders,
                "offer": {"plan": offer, "amount_idr": IDR.get(offer), "tryouts": sc.total_for_family(sc.join_window(c["now"]), "utama")},
                "playtest": self.playtest}

    def webhook(self, c):
        sig = c["h"].get("x-signature", ""); ok = hmac.compare_digest(sig, hmac.new(self.secret, c["raw"], hashlib.sha256).hexdigest())
        j = c["json"]; eid = str(j.get("event_id", ""))
        if not ok:
            self.db.execute("INSERT OR IGNORE INTO webhook_events VALUES(?,?,?,?,?)", ("bad-" + secrets.token_hex(4), j.get("order_ref"), 0, iso(c["now"]), c["raw"].decode(errors="replace")[:500]))
            self.db.commit(); raise Err(401, "tanda_tangan_tidak_valid")
        if self.db.execute("SELECT 1 FROM webhook_events WHERE gateway_event_id=?", (eid,)).fetchone(): return {"duplikat": True}      # idempoten
        self.db.execute("INSERT INTO webhook_events VALUES(?,?,?,?,?)", (eid, j.get("order_ref"), 1, iso(c["now"]), c["raw"].decode(errors="replace")[:500]))
        o = self.db.execute("SELECT * FROM orders WHERE public_ref=?", (j.get("order_ref"),)).fetchone()
        if not o: raise Err(404, "pesanan_tidak_ada")
        st = {"paid": "paid", "failed": "failed", "expired": "expired"}.get(j.get("status"))
        if not st: raise Err(422, "status_tidak_dikenal")
        self._apply_payment(o, st, eid, c["now"])
        return {"ok": True, "status": st}

    # ---------- admin: antrean analisa (AI belakangan) ----------
    def admin_queue(self, c):
        self._admin(c)
        return {"jobs": [{"attempt": r["public_ref"], "state": r["state"], "chars": len(r["input_json"])} for r in self.db.execute("SELECT j.state, j.input_json, a.public_ref FROM analysis_jobs j JOIN attempts a ON a.id=j.attempt_id")]}

    def admin_export(self, c):
        self._admin(c)
        return {"jsonl": "\n".join(r["input_json"] for r in self.db.execute("SELECT input_json FROM analysis_jobs WHERE state='menunggu'"))}

    def admin_revoke(self, c):
        self._admin(c); self.db.execute("UPDATE families SET revoked=1 WHERE public_ref=?", (c["args"]["fref"],))
        self.db.execute("INSERT INTO audit_log(actor,action,detail,at) VALUES(?,?,?,?)", ("admin", "revoke", c["args"]["fref"], iso(c["now"]))); return {"ok": True}

    def admin_standin(self, c):
        """Pengganti AI: aturan. Panggilan AI sungguhan menggantikan fungsi ini dan menulis output_json yang sama bentuknya."""
        self._admin(c); jobs = self.db.execute("SELECT j.id, j.input_json, a.id aid, a.family_id, a.window_k FROM analysis_jobs j JOIN attempts a ON a.id=j.attempt_id WHERE j.state='menunggu'").fetchall(); fams = set()
        for j in jobs:
            p = json.loads(j["input_json"]); weak = an.weak_topics(p["scores"]["topic"])
            out = {"weak_topics": weak, "drill_spec": [{"topic": w["topic"], "focus": "konsep" if w["severity"] == "berat" else "ketelitian"} for w in weak[:2]]}
            self.db.execute("UPDATE analysis_jobs SET state='selesai', output_json=?, provider='standin', finished_at=? WHERE id=?", (json.dumps(out), iso(c["now"]), j["id"]))
            self.db.execute("UPDATE attempts SET analysis_state='selesai' WHERE id=?", (j["aid"],)); fams.add((j["family_id"], j["window_k"]))
        for fid, k in fams:                                                 # gabungkan per jendela: PROGRAM, bukan AI
            specs = [json.loads(r["output_json"])["weak_topics"] for r in self.db.execute("SELECT output_json FROM analysis_jobs j JOIN attempts a ON a.id=j.attempt_id WHERE a.family_id=? AND a.window_k=? AND j.state='selesai'", (fid, k))]
            merged = an.merge_drill_specs(specs)
            if not merged:                                                  # F-01: tidak ada topik lemah => 1 sesi pemeliharaan (keputusan 4)
                self.db.execute("INSERT OR IGNORE INTO drill_assignments(family_id,source_window,topic,focus,sessions,created_at) VALUES(?,?,?,?,?,?)", (fid, k, an.MAINT_TOPIC, "maintenance", 1, iso(c["now"])))
            for m in merged:
                self.db.execute("INSERT OR IGNORE INTO drill_assignments(family_id,source_window,topic,focus,sessions,created_at) VALUES(?,?,?,?,?,?)", (fid, k, m["topic"], "konsep" if m["severity"] == "berat" else "ketelitian", 2, iso(c["now"])))
            pcts = [json.loads(r["score_json"])["score"]["pct"] for r in self.db.execute("SELECT score_json FROM attempts WHERE family_id=? AND submitted_at IS NOT NULL ORDER BY id", (fid,))]
            status = an.readiness_status(pcts, bool(specs and any(specs)))
            self.db.execute("INSERT OR REPLACE INTO reports(family_id,window_k,status,headline,body_json,mode,published_at) VALUES(?,?,?,?,?,?,?)", (fid, k, "terbit", f"Status: {status}", json.dumps({"status": status, "pcts": pcts}), "standin", iso(c["now"])))
        return {"diproses": len(jobs)}
