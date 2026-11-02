# Implementation Plan — Tryout Labschool (backend + frontend)

**Versi 1.1 · 1 November 2026 (malam)** · menggantikan v1 (1 Nov sore).
Dasar: HANDOFF v1.3 (14 keputusan terkunci) + keputusan pemilik 1 Nov malam (di bawah).
Pelaksana kode: **Claude (Opus)**. Bank soal: **ChatGPT**. Bila limit Claude habis: **Codex** melanjutkan dari `HANDOFF-IMPLEMENTASI` (dokumen live) dan snapshot kode terakhir. Playtest/simulasi: Muse.

## Selisih v1 → v1.1

| Bagian | v1 | v1.1 |
|---|---|---|
| Pelaksana | Muse; Claude tidak mengedit kode | Claude (Opus) mengimplementasikan; ChatGPT bank soal; Codex cadangan |
| Tenggat tryout (§5 inv. 5, §12.2) | Submit setelah jendela tutup ditolak; `GRACE_SEC`=0 | Tryout yang **dimulai** sebelum Minggu 16.00 diterima sampai selesai, **maks 2 jam sejak mulai**. Jendela hanya dicek saat `start`; saat `submit` yang dicek hanya `deadline_at`. Tidak ada masa tenggang lain. Sudah ada di kit + tes. |
| Login orang tua | Tidak ada di tabel API | `POST /api/parent/login` email + PIN 6 angka, kunci 15 menit setelah 5 salah, tidak membocorkan email terdaftar. Sudah ada di kit + tes. |
| Tanggal peluncuran (§12.1) | Terbuka | **Selasa 3 Nov 2026.** Jendela tryout pertama Jumat 6 Nov 17.00, jadi kalender 12 akhir pekan **tidak bergeser**. |
| Diagnostik gratis (§12.6) | Terbuka (kit memakai A) | **A: kapan saja** (kecuali hari tes dan sesudahnya). |
| Waktu analisa (§8, §12.8) | Terbuka | **Bulk setelah jendela tutup** (Minggu 16.05–21.30), kunci drill 22.00. |
| Harga (§12.3) | Terbuka | Target **Rp500–700 rb per paket**; diskon pembeli awal lebih besar dan mengecil menjelang hari tes (harga naik walau sisa tryout berkurang). Angka per tahap = keputusan pemilik. |
| Jalur Prestasi | Belum ada | Keluarga lolos Prestasi (bukti diunggah) mendapat **kode diskon sekali pakai** untuk pesanan berikutnya, **boleh diteruskan** ke keluarga lain. Persentase = keputusan pemilik. |
| Wajib/tidak | — | **Himbauan, bukan paksaan** (keputusan 14). Teks UI/email: "dianjurkan". |
| Jumlah tes | 64 Python + 6 JS | **69 Python + 6 JS** (kit 14.17 WIB). |
| Analisa ke AI | "anonim" | Istilah resmi **pseudonim**. |

## 0. Isi paket dan status

| Artefak | Fungsi | Status |
|---|---|---|
| `reference/schedule.py` | Jendela drill/tryout, status jam, aturan bergabung, urutan tryout | lulus |
| `reference/analysis.py` | Skor biner, klasifikasi pola, matriks 2×2, status kesiapan, gabung drill | lulus |
| `reference/schema.sql` | Skema SQLite (WAL), siap dipindah ke Postgres | lulus |
| `reference/backend.py` | Logika app (`App.handle`): register, login anak/orang tua, start/submit, event, drill, pesanan, webhook, antrean analisa, admin | 69 tes lulus |
| `reference/bank.py` | Bank STUB 12 soal untuk uji | diganti loader bank JSON (P2) |
| `frontend/runner.js`, `frontend/api.js` | Runner tryout + klien API | 6 tes lulus |

Tes: `cd reference && python3 -m pytest -q` · `node frontend/runner.test.js` (Python 3.11+, Node 18+).

Aturan kerja: kode `reference/` adalah spesifikasi yang dapat dijalankan. Setiap perubahan harus menjaga semua tes lulus; perilaku baru datang bersama tesnya.

## 1. Keputusan arsitektur

1. Satu aplikasi Python stdlib + SQLite WAL, di belakang Cloudflare Tunnel atau satu VPS. Pindah ke Postgres + FastAPI bila >500 keluarga aktif atau perlu >1 proses penulis.
2. Frontend HTML + modul JS biasa, tanpa framework dan tanpa build.
3. Landing dan laporan di-render server; layar anak = halaman klien yang bicara ke API.
4. Bank soal, prompt AI, ambang, logika drill, template laporan hanya di server.
5. Mode `PLAYTEST=1` menerima `X-Sim-Time`; server **menolak start** bila `PLAYTEST=1` dan `PUBLIC_HOST` adalah domain produksi.

## 2. Alur data (data dulu, AI belakangan)

```
anak mengerjakan → event idempoten → submit (server: cek deadline_at, skor, klasifikasi aturan)
 → simpan jawaban + metrik per soal → analysis_job(menunggu) dengan payload pseudonim
 → Minggu 16.00 jendela tutup → Minggu 16.05–21.30 analisa bulk (AI atau stand-in aturan)
 → program menggabungkan spesifikasi drill per jendela (maks 2 topik) → Minggu 22.00 dikunci
 → Senin 06.00 drill buka; Senin 07.00 laporan terbit + email
```
Tryout yang dimulai 15.59 boleh dikumpulkan sampai 17.59; job analisanya ikut batch bulk berikutnya yang masih sebelum 22.00 (cron mengulang tiap 30 menit sampai 21.30). Hasil langsung (skor, pembahasan, Buku Salah) tidak menunggu AI. Analisa gagal/telat → laporan fallback dari aturan.

Kontrak payload `tryout-analysis-input/v1` dan keluaran JSON ketat: tidak berubah dari v1 (lihat §2 v1; ringkas: pseudonim, per soal qid/topik/kunci/pilihan/detik/ragu/ubah; keluaran headline, strengths, weaknesses, time_analysis, parent_advice ≤3, drill_spec ≤2 topik; validator menolak topik yang tidak ada di input, klaim lolos, dan angka karangan).

## 3. Model data dan mesin status
Tidak berubah dari v1 (`reference/schema.sql`). Tambahan v1.1: tabel `price_tiers` (tahap harga) dan pemakaian `discount_codes` untuk kode Prestasi (P5).

## 4. Kontrak API

| Metode · Jalur | Auth | Perilaku | Galat |
|---|---|---|---|
| POST `/api/parent/register` | – | Buat keluarga (paket gratis) + kode anak (tampil sekali) + PIN | 422 |
| POST `/api/parent/login` | – | Email + PIN; kunci 15 menit setelah 5 salah | 401 `email_atau_pin_salah`, 403, 429 `terkunci` |
| POST `/api/child/login` | – | Kode keluarga → sesi anak; 5 gagal/10 menit/IP | 401, 403, 429 |
| GET `/api/child/home` | anak | Status jam, tryout (siap/terkunci/selesai), drill, `pending` | 401, 403 |
| POST `/api/child/tryouts/{id}/start` | anak | Satu-satunya keputusan unlock; soal tanpa kunci; `deadline_at` = mulai + 2 jam | 409 `jendela_tertutup`, `sudah_dikerjakan`, `kumpulkan_tryout_pertama_dulu`, `paket_gratis_hanya_diagnostik` |
| POST `/api/child/attempts/{ref}/events` | anak | Batch event idempoten per `seq` | 409 `sudah_dikumpulkan` |
| POST `/api/child/attempts/{ref}/submit` | anak | Cek `deadline_at` saja; skor; klasifikasi; antre analisa; idempoten | 409 `waktu_habis` |
| GET `/api/child/drills` · POST `.../sessions/{n}/finish` | anak | Jendela drill; berurutan | 409 |
| POST `/api/parent/orders` | orang tua | Harga dari tahap aktif; kode diskon opsional | 422 kode |
| POST `/api/webhooks/payment` | HMAC | Idempoten; `paid` mengaktifkan paket | 401 |
| GET `/api/parent/report/latest` | orang tua | Berbayar terbit Senin 07.00 | – |
| GET/POST `/api/admin/*` | token admin | Antrean, ekspor JSONL, stand-in, cabut | 403 |

Belum ada (urut prioritas): server HTTP nyata (P1), bank JSON + validator (P2), layar anak (P3), layar orang tua + laporan (P4), harga bertahap + kode Prestasi + adaptor gateway (P5), email transaksional (P6), analisa AI nyata + bulk runner (P7), arsip PDF/Buku Salah cetak, rotasi kode, kebijakan hapus data.

## 5. Invarian (setiap butir punya tes)

1. Tryout dan drill tidak pernah terbuka bersamaan.
2. Browser tidak menerima kunci/pembahasan sebelum submit; tidak ada endpoint borongan bank.
3. Unlock dicek di server pada `start`.
4. Tryout kedua di akhir pekan intensif baru terbuka setelah yang pertama dikumpulkan (batas teknis, bukan kewajiban).
5. **Start setelah jendela tutup ditolak. Tryout yang sudah dimulai diterima sampai `deadline_at` (mulai + 2 jam); submit lewat `deadline_at` ditolak dan tidak menyimpan apa pun.**
6. Submit dan event idempoten.
7. Skor deterministik dari kunci; AI tidak menulis skor, kunci, atau status.
8. Payload ke AI pseudonim (tanpa nama, nomor, email, kode).
9. Webhook: tanda tangan salah ditolak; duplikat diabaikan; aktivasi tepat sekali.
10. Kode keluarga dan PIN hanya disimpan sebagai hash.
11. Keluarga dicabut tidak bisa login/memakai token lama.
12. Yang terlewat tidak digulung; pembeli baru mulai dari diagnostik di jendela terdekat.
13. **Baru:** `PLAYTEST=1` tidak bisa jalan di domain produksi.
14. **Baru:** harga pesanan diambil dari tahap harga server pada saat pesanan dibuat, bukan dari klien.

## 6. Rencana frontend
Tidak berubah dari v1: `public/` (landing server-side, `parent/`, `child/`, `js/api.js`, `js/runner.js`, `css/`). Persyaratan UX: satu soal per layar, grid berlegenda bentuk, layar periksa, tombol Kumpulkan selalu memberi status, pintasan A–D/N/P, kontras ≥4,5:1, tombol ≥44 px, bahasa kelas 6, kata "dianjurkan" bukan "wajib". Landing dan laporan mingguan tidak boleh tampak seperti desain AI generik.

## 7. Prasyarat non-kode
- **Spesifikasi Format Tes v1** (jumlah soal, durasi, komposisi). Sampai ada: `TRYOUT_LIMIT_SEC`=7200 dan jumlah soal = placeholder.
- **Bank soal (ChatGPT)** mengikuti format `docs/BANK-FORMAT.md` (dibuat di P2) dan lolos validator sebelum dimuat. Matematika: template deterministik.
- Syarat pembelian, kebijakan privasi (UU PDP), kebijakan diskon tertulis sebelum halaman jual dibuka.

## 8. Pekerjaan terjadwal (WIB)

| Jadwal | Tugas |
|---|---|
| Minggu 16.00 | Jendela tryout tutup (start ditolak); tryout berjalan tetap bisa dikumpulkan sampai `deadline_at` |
| Minggu 16.05, lalu tiap 30 menit s.d. 21.30 | Analisa bulk semua job `menunggu`; ulang gagal 2× lalu fallback |
| Minggu 18.05 | Tandai tryout dimulai tapi tak dikumpulkan (lewat `deadline_at`) sebagai terlewat |
| Minggu 22.00 | Kunci spesifikasi drill; bangun laporan |
| Senin 06.00 / 07.00 | Drill buka + pengingat / laporan terbit + email |
| Kamis 18.00 | Pengingat drill (himbauan) |
| Jumat 15.00 / 17.00 | Drill tutup / tryout buka + email |
| Minggu 12.00 | Pengingat tryout (himbauan) |
| Tiap 15 menit | Rekonsiliasi pesanan `menunggu` |
| 02.00 | Cadangan DB, cek disk, ringkasan biaya AI |

## 9. Keamanan dan privasi
Tidak berubah dari v1. PIN sudah memakai PBKDF2 (120k iterasi); token sesi dan kode keluarga sebagai SHA-256.

## 10. Deploy
Lingkungan `playtest` (publik, `PLAYTEST=1`, noindex) dan `produksi`. Variabel: `DB_PATH`, `WEBHOOK_SECRET`, `ADMIN_TOKEN`, `PLAYTEST`, `PUBLIC_HOST`, `BANK_DIR`, `AI_PROVIDER`, `AI_MODEL`, `AI_KEY`, `SMTP_*`, `GATEWAY_*`.

## 11. Urutan kerja (potongan kecil; tiap potongan → tes lulus → snapshot + update HANDOFF)

| # | Potongan | Selesai bila |
|---|---|---|
| P1 | `server.py`: HTTP stdlib di atas `App.handle`, statis `public/`, guard playtest, config env | Tes integrasi HTTP lulus |
| P2 | Format bank JSON + validator + loader (ganti STUB) | Validator menolak contoh rusak; backend memakai loader; tes lulus |
| P3 | Layar anak: login → dashboard → tryout/periksa → hasil | Skenario anak lulus di Chromium (Playwright) |
| P4 | Layar orang tua: daftar, masuk, dashboard, laporan | Skenario orang tua lulus di Chromium |
| P5 | Harga bertahap + kode Prestasi + adaptor gateway (sim dulu) | Tes harga & kode lulus |
| P6 | Email transaksional (adaptor; log-only sampai penyedia dipilih) | Tes lulus |
| P7 | Bulk runner AI + validator keluaran + catat biaya | 30 payload playtest lolos validator |
| P8 | Cron + deploy playtest publik | Jalan di domain playtest |

**Rilis 3 Nov (usulan minimum, butuh persetujuan pemilik):** landing + daftar + diagnostik gratis (P1–P4) dengan bank soal awal dari ChatGPT. Penjualan paket berbayar dibuka setelah gateway dipilih (P5); jendela berbayar pertama Jumat 6 Nov.

## 12. Keputusan yang masih memblokir
1. Payment gateway (Midtrans/Xendit) dan penyedia email — memblokir penjualan berbayar.
2. Spesifikasi format tes (jumlah soal, durasi per tryout).
3. Angka harga per tahap dan tanggal pergantian tahap; persentase diskon kode Prestasi; perlakuan sisa akses setelah lolos Prestasi.
4. Domain dan host publik.
5. Penyedia AI runtime final (setelah uji biaya bulk).
6. Masa simpan data; tinjauan hukum privasi.
7. Persetujuan cakupan Rilis 3 Nov (§11).

## 13. QA gate sebelum rilis
Semua tes lulus terhadap server HTTP nyata · uji penetrasi ringan (URL tryout terkunci, token anak ke endpoint orang tua, ulang webhook, `X-Sim-Time` di produksi) · cek acak 10% bank + semua butir bertanda · konsistensi angka dokumen vs kode · laporan fallback terbit saat AI gagal · simulasi ratusan skenario tanpa pelanggaran invarian. Karena Claude kini juga pelaksana, QA gate dijalankan oleh **agen terpisah yang tidak ikut menulis kode** (atau Muse), bukan menilai pekerjaannya sendiri.
