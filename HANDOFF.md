# HANDOFF — log implementasi (paling baru di bawah)

Sumber kebenaran kode sejak 2 Nov 2026 = repo ini. Dokumen Drive `impl-build/HANDOFF-IMPLEMENTASI (live)` hanya arsip P0–P3.

## Keputusan pemilik yang sudah terkunci (ringkas)
- Tenggat: tryout yang dimulai sebelum Minggu 16.00 diterima sampai selesai, maks 2 jam sejak mulai. Tidak ada grace lain.
- Peluncuran Selasa 3 Nov 2026; jendela tryout pertama Jumat 6 Nov 17.00 (kalender tidak bergeser).
- Cakupan rilis 3 Nov (DISETUJUI 2 Nov): landing + daftar + diagnostik gratis. Penjualan berbayar menyusul setelah gateway dipilih.
- Harga paket utama: **Rp499.000** (2 Nov). Skema diskon pembeli awal (v1.1) belum diberi angka; sementara harga tunggal.
- Domain uji pemilik: **labschool.doncorleonez.my.id** (playtest dulu).
- Login orang tua: email + PIN. Diagnostik gratis kapan saja. Analisa AI bulk setelah jendela tutup. Kode diskon Prestasi sekali pakai, boleh diteruskan.
- Implementasi: Claude (Opus); bank soal: ChatGPT; cadangan: Codex.

- (2 Nov sore) Diagnostik gratis: SATU kali per siswa dan SATU set soal yang sama untuk semua (`backend.DIAG_SEED`), supaya akun ganda tidak membuka soal baru. Email/WA yang sudah terdaftar ditolak (409 `sudah_terdaftar`). Keluarga yang bayar belakangan tidak mengulang diagnostik.
- (2 Nov sore) Midtrans DITUNDA (jangan kerjakan P5 dulu). UI memakai istilah "siswa"/"anak", bukan "keluarga".

## Keputusan terbuka (jangan ditebak)
1. Jumlah soal & durasi per tryout: pemilik minta "sesuai aslinya". Angka resmi ada di Pedoman Jalur Tes 2027 (PDF psb.labschool-unj.sch.id) yang belum bisa dibaca agen; tunggu PDF dilampirkan. Sementara: 40 soal / 120 menit (`bankfile.COMPOSITION`, `backend.TRYOUT_LIMIT_SEC`). Catatan: satu sumber sekunder menyebut tes asli memakai CAT (adaptif) — perlu dicek di pedoman.
2. Payment gateway: usulan Midtrans (lihat docs/IMPLEMENTATION-PLAN.md §12). Menunggu pilihan + akun pemilik.
3. Email transaksional: usulan Resend (gratis 3.000/bulan, 100/hari). Menunggu pilihan + domain pengirim.
4. Angka diskon pembeli awal dan persentase kode Prestasi.

## Log

### P0–P3 (1 Nov, Claude) — lihat riwayat commit
- P0: kit 14.17 dipulihkan; plan v1.1.
- P1: `reference/server.py` HTTP stdlib + guard playtest/produksi.
- P2: `reference/bankfile.py` + `bankcheck.py` (validator sesuai BRIEF ChatGPT), loader `BANK_DIR`.
- P3: lanjut-setelah-refresh, pembahasan pasca-submit; layar anak `public/child/` + e2e Chromium.

### 2 Nov — repo GitHub dibuat (Claude)
- Riwayat kit digabung ke repo ini. Ditambah AGENTS.md, README, CI (GitHub Actions: pytest + Playwright + runner.test.js).
- BERIKUTNYA: P4 layar orang tua + landing.

### P4 — 2 Nov (Claude)
- Backend: `IDR["utama"]=499_000`; pesanan memakai harga server (klien diabaikan), 409 `paket_sudah_aktif`, 409 `harga_belum_ditetapkan` untuk kejar. `GET /api/parent/home`. `POST /api/playtest/orders/{ref}/pay` hanya hidup saat PLAYTEST (404 di produksi). Refaktor `_apply_payment` dipakai webhook + playtest.
- Frontend: landing `public/index.html` + `css/site.css` + `js/landing.js` (kalender 12 akhir pekan menuju 31 Jan sebagai elemen utama; palet seragam SD-SMP; font sistem karena registry font tidak terjangkau dari lingkungan Claude — boleh self-host Plus Jakarta Sans (OFL) nanti). Area orang tua `public/parent/` (daftar dengan validasi per kolom, kode anak tampil sekali + salin, masuk email+PIN, dashboard paket/laporan/tryout, tombol beli + bayar simulasi hanya di playtest; di produksi tertulis "Pembayaran online segera dibuka").
- Tes: +5 backend, +3 e2e (`test_e2e_parent.py`). Total 113 Python + 6 JS.
- Deploy uji: `docs/DEPLOY.md` (systemd + Cloudflare Tunnel untuk labschool.doncorleonez.my.id, PLAYTEST=1).
- Catatan terbuka: keluarga yang daftar lama lalu bayar belakangan tetap memakai `join_window` saat daftar (diagnostik tidak diulang); cek apakah sesuai keinginan pemilik.
- BERIKUTNYA: P5 gateway (menunggu pilihan pemilik; siapkan adaptor Midtrans Snap + verifikasi signature `sha512(order_id+status_code+gross_amount+server_key)`), atau P6 adaptor email (log-only + Resend), atau sesi drill + Buku Salah kumulatif. Format soal resmi menunggu PDF Pedoman.

### 2 Nov sore — diagnostik tetap + copy landing (Claude)
- `DIAG_SEED`: soal diagnostik identik untuk semua siswa; tryout berbayar tetap berbeda per siswa. Cegah daftar ulang dengan email atau WA yang sama (format 08/62/+62 dinormalkan).
- Landing ditulis ulang dari 6 pain point riset (dokumen konsep bab 3): hero "Jangan tunggu pengumuman...", blok "Yang paling sering dikeluhkan orang tua" (5 kutipan + jawaban), contoh laporan dengan status Mengejar dan tiga aksi, perbandingan dengan biaya les, FAQ privasi. "Kode keluarga" -> "kode siswa" di layar anak dan orang tua.
- PERHATIAN sebelum penjualan berbayar dibuka: copy menjanjikan pengingat email dan laporan Senin otomatis; keduanya baru nyata setelah P6 (email) dan cron laporan. Jangan buka penjualan sebelum itu.
- Tes: 118 Python + 6 JS lulus.
- BERIKUTNYA (Midtrans ditunda): P6 adaptor email (log-only + Resend) dan cron laporan Senin, atau sesi drill + Buku Salah kumulatif.
