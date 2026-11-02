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
