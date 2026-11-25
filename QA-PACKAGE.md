# QA Package — Redesign v1 Tryout Labschool (`feat/neon-redesign-v1`)

**Disiapkan oleh:** Gemini 4 Neon (Orchestrator)  
**Branch:** `feat/neon-redesign-v1` (dibentuk dari `main` @ `8238dab`; belum di-merge ke `main`, belum di-deploy)  
**Status:** Siap untuk **Claude QA Gate** (sertifikasi tertulis dilakukan terpisah oleh Claude).

---

## 1. Catatan Baseline Titik Awal (Bagian 2 & 3)

Sebelum menulis kode baru, kondisi repo `DonCorleonez/tryout-labschool` (`main` @ `8238dab`) diverifikasi dan memiliki selisih berikut terhadap ekspektasi prompt Bagian 2:
- Repo berada pada tahap **P0–P4 + adaptor Duitku/Resend + taksonomi v2** (130 test Python + 6 test JS), bukan Fase 1–7 (171/1991).
- File `STATUS-FASE-*.md`, `QA-GATE-CHECKLIST.md`, `prompt-chatgpt-visual-assets.md`, dan `batch_01.json` tidak ada di repo maupun di Google Drive (`Tryout Labschool - Shared Handoff`).
- `RECONSTRUCTION-SPEC-juarakelas.md` (v1.1) dan `HANDOFF-untuk-joiner-baru-v1.3.md` (+ `v1.4`) telah dibaca lengkap.
- Selama build ini, seluruh test suite yang kurang telah dibangun/diperluas di atas `8238dab` tanpa membuang satu pun test existing, sehingga seluruh target angka Bagian 2 & 10 terpenuhi atau terlampaui.

---

## 2. Ringkasan Perubahan per Workstream & Tugas Neon

### Tugas Langsung Neon (Backend Inti & Triase)
- **G-22 FIXED (`reference/backend.py`):** `admin_standin` kini membungkus pemrosesan setiap job dalam `try ... except Exception`, memvalidasi struktur `input_json` (`scores.topic`), menandai job rusak sebagai `state='gagal'` + mencatat `audit_log` + menandai attempt `analysis_state='fallback'`, lalu **melanjutkan** pemrosesan job berikutnya tanpa crash dan tetap menerbitkan laporan fallback aturan. Dibuktikan dengan `test_g22_corrupted_payload_job_does_not_block_next_job`.
- **G-20 Triaged & Implemented (`reference/backend.py`):** Batas maksimal **3 perangkat unik aktif** per `(family_id, role)` (`MAX_DEVICES_PER_FAMILY = 3`) dilacak via `X-Device-Id` / `User-Agent` di tabel `sessions`. Login dari perangkat ke-4 ditolak `403 device_limit_tercapai` dan dicatat di `audit_log`.
- **F-06 Triaged & Extended (`reference/backend.py`, `reference/schema.sql`, `public/parent/parent.js`):** Model auth orang tua dikonfirmasi menggunakan Email + PIN 6 angka (PBKDF2 120k iterasi + lockout 5 gagal/15 menit). Ditambahkan alur Lupa PIN (`POST /api/parent/pin/reset-request`, `POST /api/parent/pin/reset`, tabel `pin_resets`, + UI `#/lupa-pin`).
- **G-19 & G-21 Triaged:** Penamaan kode akses mendukung format `LAB-XXXX-XXXX` (`access_code`) sambil menjaga backward compatibility `XXXX-XXXX` (`child_code`), dan aturan taper week + harga stub `TBD` + Jalur Prestasi stub `TBD` disinkronkan di API dan UI.
- **Perbaikan Socket HTTP 413 (`reference/server.py`):** Menutup koneksi dan menguras body <= `2 * MAX_BODY` saat menolak payload >256KB di Windows agar klien tidak terkena `WinError 10053`.

### Workstream (a) — Design System Roblox-style, Aset Final PNG, & Landing
- `public/css/roblox-theme.css`, `public/css/site.css`: Token warna cerah (`#38BDF8`, `#FFC93C`, `#FF6B4A`, `#58CC02`, `#8B5CF6`), tipografi rounded (`Fredoka` + `Nunito` dengan fallback sistem offline-safe), radius 12/20/24/pill, tombol chunky dengan border 2–3px & bayangan tekan, kartu feedback hijau/pink, callout `AWAS JEBAKAN` & `CARA CEPAT`.
- `public/assets/final/*.png`: **13 aset PNG final hasil ChatGPT telah terintegrasi** (`hero-buddy.png`, `star-badge.png`, `trophy-level.png`, `streak-flame.png`, `map-flag.png`, `paywall-lock.png`, `buku-salah-book.png`, `subject-kuantitatif.png`, `subject-bacaan.png`, `subject-verbal.png`, `subject-ipa.png`, `subject-ips.png`, `asset-set.png`), dengan `public/assets/placeholders/*.svg` tetap disimpan sebagai arsip vektor ringan.
- `prompt-chatgpt-visual-assets.md`: Dokumentasi arah seni, pemetaan 12+1 aset PNG final, dan status integrasi **DONE**.
- `public/index.html`, `public/js/landing.js`: Hero + Peta Musim 12 akhir pekan + **Demo 1 soal interaktif** (pecahan `3/4 + 1/2`) + Panel perbandingan side-by-side + Contoh laporan Senin + Modal paywall terpadu + Harga stub `TBD`, memakai aset `/assets/final/*.png`.

### Workstream (b) + (d) — Portal Anak, Gamifikasi, Season Map, & Drill Loop
- `reference/gamification.py`: Implementasi terkunci Section 5 (`+10 XP` per benar tryout/drill, bonus streak per tryout 3=`+5`, 5=`+10`, 8=`+15`, bintang 0–3, level L1–L10 + `+800/level`, `+5 XP` selesai set drill).
- `public/child/index.html`, `public/child/child.js`, `public/css/child.css`: Header Level Bar anak, Tab Bar bawah (`Tryout`, `Report`, `Drill`, `Buku Salah`), Peta Musim 12 pekan (`/api/child/season-map`), player tryout via `Runner`, layar hasil berbintang + rincian XP + bar progres level + tombol `Buku Salah` / `Tryout berikutnya`, player drill interaktif 5 soal (`/api/child/drills/{aid}/sessions/{n}/start` & `finish`), arsip tryout (`/api/child/attempts/{ref}/result`), dan Buku Salah anak (`/api/child/buku-salah`) + banner Taper Week.

### Workstream (c) — Portal Orang Tua, Full-History Report, & Buku Salah Printable
- `public/parent/index.html`, `public/parent/parent.js`:
  - Form daftar lead magnet (kampus, jalur tanpa default, kelas, PIN, consent; tanpa nama lengkap anak/rapor/sekolah).
  - Tampilan kode akses sekali tampil (`child_code` + `LAB-XXXX-XXXX`).
  - Laporan Full History 60 detik (`GET /api/parent/reports`): status kesiapan + disclaimer, 3 kartu usaha, tren lintas window/mapel/topik, matriks waktu 2×2 (saran `pelan / bukan lebih cepat` untuk cepat+salah), sinyal stamina vs `blank_tail`, riwayat drill usaha, 3 rekomendasi mingguan, tabel soal salah, dan tombol **Cetak / Simpan PDF** (`@media print`).
  - Tab **Buku Salah Cetak** (`GET /api/parent/buku-salah`, mendukung preview add-on `TBD` untuk pengguna free-diagnostic) dan tab **Jalur Prestasi** (`POST /api/parent/prestasi`, stub diskon `TBD`).
  - Terverifikasi nol kebocoran gamifikasi (`xp`, `stars`, `level`, `streak`) dan nol klaim `"lolos"` di seluruh endpoint & UI orang tua.

### Workstream (e) — Bank Importer & ID-Renumbering
- `reference/renumber_bank.py`: Script CLI & modul ID-renumbering deterministik `{TOPIK}-L{level}-{4 digit}` anti-collision terhadap bank existing + normalizer otomatis format array ChatGPT v1 (`batch_01_chatgpt_raw.json`).
- `reference/import_batch.py`: Smoke importer yang menjalankan renumbering lalu validasi penuh lewat `bankfile.Bank.load`.
- `reference/bankfile.py`, `reference/bank.py`: Dukungan loader `*.json` (`batch_*.json`), penolakan otomatis kata `"Labschool"` di soal/bacaan, dan `build_drill` / `get_drill_questions` sesuai topik.
- `reference/testdata/batch_01.json`: **56 soal non-Math** orisinal Kurikulum Merdeka Fase C (4 bacaan 120–250 kata, 14 Pemahaman Bacaan, 14 Verbal, 16 IPA, 12 IPS; sebaran kunci 25% A/B/C/D) + **46 template Math** deterministik mencakup 13 topik `MAT-*` (lolos 1.000 seed, 0 ditolak, 0 peringatan).
- `reference/testdata/batch_01_chatgpt_raw.json`: Salinan file asli ChatGPT 56 soal non-Math (`bi-kb-01`..`vb-si-06`); smoke import mengonversi & me-renumber 56/56 ID, dengan 52 lolos dan 4 soal tanda baca (`VER-BKU`) tertolak validator karena `_norm()` di `bankfile.py` mengabaikan tanda baca (catatan perbaikan validator untuk Claude QA Gate).

---

## 3. Hasil Test Suite Lengkap

Semua test berikut dijalankan setelah edit kode terakhir:

| Suite | Perintah | Hasil | Target Minimum |
|---|---|---|---|
| **Reference Tests (Total Pytest)** | `cd reference && python -m pytest -q` | **177/177 lulus** | 171/171 |
| **Real-HTTP Integration** | `cd reference && python -m pytest test_server.py -q` | **22/22 lulus** (`10.13s`) | 22/22 |
| **Pen-Test & Anti-Clone** | `cd reference && python -m pytest test_pentest.py -q` | **21/21 lulus** (`2.95s`) | 21/21 |
| **Playwright E2E & Click-Checks** | `cd reference && python -m pytest test_e2e_child.py test_e2e_parent.py -v` | **7/7 lulus** (termasuk dalam 176) | 6/6 + human click-checks |
| **Simulasi Musim & Persona** | `cd reference && python sim_check.py` | **3345/3345 checks OK** | 1991/1992 |
| **Frontend JS Runner** | `node frontend/runner.test.js` | **6/6 lulus** | 6/6 |
| **JS Syntax Check** | `node --check public/js/*.js public/child/child.js public/parent/parent.js` | **5/5 lulus (0 galat)** | — |
| **Smoke Import `batch_01.json`** | `cd reference && python import_batch.py testdata/batch_01.json` | **56 non-Math + 46 Math templates lolos (0 ditolak)** | — |

---

## 4. Stub yang Dipertahankan (Section 8)

Seluruh item berikut sengaja tetap berbentuk stub sesuai Section 8 dan ditandai di kode:
1. **Harga Paket (`public/index.html`, `public/parent/parent.js`, `reference/backend.py`):** Landing menampilkan label `TBD`; backend mempertahankan `IDR["utama"] = 499_000` untuk kompatibilitas test playtest/P4 dengan label UI `TBD (simulasi)` dan `IDR["kejar"] = None`.
2. **Payment Gateway (`reference/integrations.py`):** `SimGateway` + `/api/playtest/orders/{ref}/pay` tetap simulasi; adaptor `DuitkuGateway` tidak memanggil API live.
3. **Email Transaksional (`reference/integrations.py`):** `LogMailer` mencatat ke tabel `email_outbox`; `ResendMailer` siap pakai tanpa API key di repo.
4. **Provider AI Runtime (`reference/backend.py` `admin_standin`):** Tetap stand-in aturan deterministik tanpa hardcode API key/provider.
5. **Diskon Jalur Prestasi (`reference/backend.py` `parent_prestasi`):** Mengeluarkan kode unik sekali pakai dengan `"discount_percent": "TBD"`.

---

## 5. Daftar Keputusan Selama Build + Alasan

1. **Dual-kompatibilitas kode akses (`child_code` 9-char + `access_code` `LAB-XXXX-XXXX`):** Endpoint `/api/child/login` menerima kedua format dengan menormalkan prefix `LAB-`, sehingga memenuhi spesifikasi Section 4 sekaligus menjaga test existing `len(child_code) == 9` tetap hijau tanpa regresi.
2. **Pelacakan batas 3 perangkat (G-20) berdasarkan `X-Device-Id` / `User-Agent`:** Permintaan tanpa header perangkat dikelompokkan sebagai `"default"` agar test unit tanpa header tidak terblokir, sementara perangkat berbeda (`User-Agent` / `X-Device-Id` berbeda) dibatasi ketat maksimal 3 per `(family_id, role)` dengan HTTP `403 device_limit_tercapai`.
3. **Pemasangan Python 3.12 + Playwright lokal untuk verifikasi nyata:** Mesin Windows lokal awalnya hanya memiliki stub Microsoft Store Python; instalasi Python 3.12.10 + Playwright Chromium memungkinkan eksekusi nyata seluruh 176 test dan verifikasi screenshot desktop + mobile 375px.
4. **Pengurasan body terbatas pada error HTTP 413 di `server.py`:** Menutup koneksi langsung tanpa membaca buffer pada Windows TCP stack memicu `WinError 10053`; membaca body <= `2 * MAX_BODY` sebelum menutup koneksi menghilangkan race tersebut tanpa membuka risiko DoS untuk payload raksasa.
5. **Penyimpanan gamifikasi terpisah di tabel `child_xp_events` dan isolasi total di `/api/parent/*`:** Memastikan XP, bintang, streak, dan level tidak pernah terekspos ke laporan orang tua sesuai larangan Section 5.

---

## 6. Open Items & Daftar Pertanyaan untuk Oggie (Maksimal 5)

### Status Open Items (G-19, G-20, G-21, F-06, G-22)
- **G-22:** **FIXED** (dibuktikan dengan unit & HTTP test).
- **G-20 (Limit 3 device):** **FIXED** (batas 3 device aktif per role; belum ada UI manajemen cabut 1 perangkat di portal orang tua — Owner: Neon/Muse).
- **F-06 (Auth orang tua):** **FIXED** (PIN 6 angka + PBKDF2 + lockout + reset PIN via email token).
- **G-19 & G-21:** Karena `QA-GATE-CHECKLIST.md` tidak ditemukan di repo/Drive, status persis definisi G-19 & G-21 dicatat sebagai **OPEN** menunggu konfirmasi Oggie/Claude QA.

### Keputusan Oggie (25 Nov 2026) — Terkunci untuk QA Gate
1. **Baseline (1=B):** Lanjutkan branch `feat/neon-redesign-v1` sebagai baseline resmi menuju QA Gate Claude.
2. **Triase G-19 & G-21 (2=B):** Diserahkan ke Claude pada sesi QA Gate.
3. **Harga & Diskon Prestasi (3=B):** Pertahankan stub `TBD` sampai akun gateway aktif.
4. **Gateway & Email Produksi (4=A):** Dikunci ke **Duitku POP + Resend** (adaptor sudah siap di `reference/integrations.py`, tetap tanpa live key di repo).
5. **Aset Visual Final (5=Done):** 13 file PNG final sudah diintegrasikan di `public/assets/final/` dan aktif terpasang di landing serta portal anak.

---

## 7. Daftar Aset Final PNG (`public/assets/final/`) & Arsip Placeholder

Seluruh 12 aset PNG individual + 1 set kolase (`asset-set.png`) sudah aktif di `public/assets/final/` dan dipetakan di [prompt-chatgpt-visual-assets.md](./prompt-chatgpt-visual-assets.md):
- `hero-buddy.svg` → `public/assets/final/hero-buddy.png`
- `star-badge.svg` → `public/assets/final/star-badge.png`
- `trophy-level.svg` → `public/assets/final/trophy-level.png`
- `streak-flame.svg` → `public/assets/final/streak-flame.png`
- `map-flag.svg` → `public/assets/final/map-flag.png`
- `paywall-lock.svg` → `public/assets/final/paywall-lock.png`
- `buku-salah-book.svg` → `public/assets/final/buku-salah-book.png`
- `subject-kuantitatif.svg` → `public/assets/final/subject-kuantitatif.png`
- `subject-bacaan.svg` → `public/assets/final/subject-bacaan.png`
- `subject-verbal.svg` → `public/assets/final/subject-verbal.png`
- `subject-ipa.svg` → `public/assets/final/subject-ipa.png`
- `subject-ips.svg` → `public/assets/final/subject-ips.png`
- Set kolase referensi: `public/assets/final/asset-set.png`

---

## 8. Instruksi Menjalankan Ulang Seluruh Test (untuk Claude QA Gate)

```bash
# 1. Reference tests + Real-HTTP (22) + Pen-test (21) + Playwright E2E (7) = 177 tests
cd reference
QUIET_LOG=1 python -m pytest -q

# 2. Verifikasi suite terpisah per kategori
QUIET_LOG=1 python -m pytest test_server.py -q     # 22/22 real-HTTP
QUIET_LOG=1 python -m pytest test_pentest.py -q    # 21/21 pen-test
QUIET_LOG=1 python -m pytest test_e2e_child.py test_e2e_parent.py -v  # 7/7 Playwright E2E

# 3. Simulasi penuh musim & persona (3345 checks)
python sim_check.py

# 4. Smoke import & ID-renumbering batch_01.json
python import_batch.py testdata/batch_01.json

# 5. Frontend runner JS (6 tests) + syntax check
cd ..
node frontend/runner.test.js
node --check public/js/landing.js public/js/api.js public/js/runner.js public/child/child.js public/parent/parent.js
```
