-- Skema SQLite (WAL) untuk backend komersial. Pindah ke Postgres: tipe sama, ganti AUTOINCREMENT dengan identity.
PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS families (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  public_ref    TEXT UNIQUE NOT NULL,            -- 'fam_xxx' (dikirim ke AI; bukan nama)
  code_hash     TEXT NOT NULL,                   -- hash kode keluarga (bukan teks asli)
  pin_hash      TEXT,                            -- hash PIN orang tua
  plan          TEXT NOT NULL DEFAULT 'free',    -- free | utama | kejar
  join_window   INTEGER NOT NULL DEFAULT 0,      -- jendela tempat diagnostik dimulai
  revoked       INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT NOT NULL
);
-- Data pemasaran dipisah dari data belajar agar permintaan hapus tidak saling menghapus.
CREATE TABLE IF NOT EXISTS marketing_leads (
  id INTEGER PRIMARY KEY AUTOINCREMENT, family_id INTEGER REFERENCES families(id) ON DELETE SET NULL,
  parent_name TEXT, whatsapp TEXT, email TEXT, campus TEXT, track TEXT, grade TEXT,
  consent_at TEXT NOT NULL, unsubscribed_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions (               -- token sesi (hash) untuk orang tua dan anak
  token_hash TEXT PRIMARY KEY, family_id INTEGER NOT NULL REFERENCES families(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK(role IN ('parent','child','admin')), device TEXT, created_at TEXT NOT NULL, last_seen TEXT
);
CREATE TABLE IF NOT EXISTS login_attempts (ip_hash TEXT NOT NULL, kind TEXT NOT NULL, at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS attempts (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  public_ref    TEXT UNIQUE NOT NULL,            -- 'att_xxx'
  family_id     INTEGER NOT NULL REFERENCES families(id) ON DELETE CASCADE,
  tryout_id     TEXT NOT NULL,                   -- 'DIAG' | 'TO10-1'
  window_k      INTEGER NOT NULL,
  started_at    TEXT NOT NULL, deadline_at TEXT NOT NULL,    -- timer dijaga server
  submitted_at  TEXT, auto_submitted INTEGER NOT NULL DEFAULT 0,
  question_ids  TEXT NOT NULL,                   -- JSON urutan soal
  score_json    TEXT,                            -- hasil penilaian deterministik
  rule_json     TEXT,                            -- klasifikasi + sinyal (aturan)
  analysis_state TEXT NOT NULL DEFAULT 'none',   -- none | menunggu | selesai | fallback
  UNIQUE(family_id, tryout_id)                   -- satu keluarga, satu tryout, satu kali
);
CREATE TABLE IF NOT EXISTS attempt_events (       -- jejak mentah dari frontend (idempoten per attempt+seq)
  attempt_id INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE, seq INTEGER NOT NULL,
  q_no INTEGER, kind TEXT NOT NULL,              -- answer | flag | visit | idle | leave | return
  value TEXT, client_ms INTEGER, server_at TEXT NOT NULL, PRIMARY KEY(attempt_id, seq)
);
CREATE TABLE IF NOT EXISTS attempt_answers (      -- keadaan akhir tiap soal
  attempt_id INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE, q_no INTEGER NOT NULL, question_id TEXT NOT NULL,
  chosen_idx INTEGER, correct_idx INTEGER, sec_raw REAL, sec_idle REAL, sec_clean REAL, visits INTEGER, flagged INTEGER,
  flag_toggles INTEGER, changes INTEGER, changed_correct_to_wrong INTEGER, rule_tag TEXT, PRIMARY KEY(attempt_id, q_no)
);
CREATE TABLE IF NOT EXISTS analysis_jobs (        -- antrean analisa (bulk / per tryout)
  id INTEGER PRIMARY KEY AUTOINCREMENT, attempt_id INTEGER UNIQUE NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
  state TEXT NOT NULL DEFAULT 'menunggu',        -- menunggu | berjalan | selesai | gagal
  provider TEXT, model TEXT, tokens_in INTEGER, tokens_out INTEGER, cost_usd REAL, latency_ms INTEGER,
  input_json TEXT NOT NULL,                      -- payload anonim yang dikirim
  output_json TEXT, error TEXT, created_at TEXT NOT NULL, finished_at TEXT
);
CREATE TABLE IF NOT EXISTS drill_assignments (
  id INTEGER PRIMARY KEY AUTOINCREMENT, family_id INTEGER NOT NULL REFERENCES families(id) ON DELETE CASCADE,
  source_window INTEGER NOT NULL, topic TEXT NOT NULL, focus TEXT NOT NULL, sessions INTEGER NOT NULL DEFAULT 2,
  created_at TEXT NOT NULL, UNIQUE(family_id, source_window, topic)
);
CREATE TABLE IF NOT EXISTS drill_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, assignment_id INTEGER NOT NULL REFERENCES drill_assignments(id) ON DELETE CASCADE,
  session_no INTEGER NOT NULL, started_at TEXT, finished_at TEXT, correct INTEGER, total INTEGER, detail_json TEXT,
  UNIQUE(assignment_id, session_no)
);
CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT, family_id INTEGER NOT NULL REFERENCES families(id) ON DELETE CASCADE,
  window_k INTEGER NOT NULL, status TEXT NOT NULL, headline TEXT, body_json TEXT NOT NULL, mode TEXT NOT NULL, -- ai | fallback
  published_at TEXT, emailed_at TEXT, UNIQUE(family_id, window_k)
);
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT, public_ref TEXT UNIQUE NOT NULL, family_id INTEGER NOT NULL REFERENCES families(id),
  plan TEXT NOT NULL, amount_idr INTEGER, status TEXT NOT NULL DEFAULT 'dibuat',  -- dibuat|menunggu|paid|failed|expired
  gateway TEXT, gateway_ref TEXT, created_at TEXT NOT NULL, paid_at TEXT
);
CREATE TABLE IF NOT EXISTS order_events (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL REFERENCES orders(id), kind TEXT NOT NULL, detail TEXT, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS webhook_events (gateway_event_id TEXT PRIMARY KEY, order_ref TEXT, signature_ok INTEGER NOT NULL, received_at TEXT NOT NULL, body TEXT); -- kunci idempotensi
CREATE TABLE IF NOT EXISTS discount_codes (code TEXT PRIMARY KEY, family_id INTEGER REFERENCES families(id), proof_hash TEXT UNIQUE NOT NULL, percent REAL, used_at TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT, action TEXT, detail TEXT, at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_attempts_family_window ON attempts(family_id, window_k);
CREATE INDEX IF NOT EXISTS idx_jobs_state ON analysis_jobs(state);
CREATE TABLE IF NOT EXISTS email_outbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT, family_id INTEGER REFERENCES families(id) ON DELETE CASCADE,
  kind TEXT NOT NULL, to_addr TEXT NOT NULL, subject TEXT NOT NULL, body_text TEXT NOT NULL,
  dedupe_key TEXT UNIQUE,                       -- satu email per kejadian (mis. paid:ord_x), aman bila dipanggil ulang
  status TEXT NOT NULL DEFAULT 'antre',         -- antre|terkirim|gagal|log
  attempts INTEGER NOT NULL DEFAULT 0, provider_id TEXT, error TEXT, created_at TEXT NOT NULL, sent_at TEXT
);
