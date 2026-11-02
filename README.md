# Tryout Labschool

Tryout CBT mandiri untuk persiapan Jalur Tes SMP Labschool, dijual ke orang tua. Python stdlib + SQLite, frontend HTML/JS tanpa build.

## Jalankan lokal (mode playtest)
```
cd reference
PLAYTEST=1 DB_PATH=play.db python3 server.py        # http://127.0.0.1:8080
```
- Anak: `/child/?sim=2026-11-06T18:00` (parameter `sim` hanya berlaku saat PLAYTEST=1)
- Bank soal berkas: `BANK_DIR=/path/ke/bank` (validasi: `python3 bankcheck.py /path/ke/bank`)

## Tes
```
cd reference && python3 -m pytest -q
node frontend/runner.test.js
```

## Struktur
- `reference/` — server (`server.py`), logika app (`backend.py`), jadwal, analisa, bank soal + validator, tes.
- `public/` — halaman statis (anak, orang tua, landing) dan `js/runner.js`, `js/api.js`.
- `docs/` — rencana implementasi dan panduan deploy.
- `HANDOFF.md` — log kerja; `AGENTS.md` — aturan untuk agen kode.
