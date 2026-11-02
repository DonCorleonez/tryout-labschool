# AGENTS.md — aturan untuk agen kode (Claude, Codex, dll.)

Baca berurutan sebelum menyentuh kode:
1. `HANDOFF.md` — log kerja terbaru dan potongan BERIKUTNYA. Kerjakan dari sana.
2. `docs/IMPLEMENTATION-PLAN.md` — kontrak API, invarian, urutan potongan.
3. Keputusan produk terkunci ada di Drive pemilik: `HANDOFF-untuk-joiner-baru.md` v1.3 (14 keputusan). Bila ragu, ikuti dokumen itu dan tanya pemilik.

## Cara kerja
- Satu potongan kecil = kode + tes + entri baru di `HANDOFF.md` + commit. Jangan menumpuk banyak potongan tanpa commit.
- Semua tes wajib lulus sebelum commit:
  ```
  cd reference && python3 -m pytest -q      # termasuk e2e Chromium bila Playwright terpasang
  node frontend/runner.test.js
  ```
- Python stdlib saja di server (tanpa dependensi pip di produksi). Frontend tanpa framework dan tanpa build. Tidak ada script inline (CSP `script-src 'self'`).
- Bahasa UI: Indonesia, setara kelas 6 untuk layar anak. Pakai "dianjurkan", bukan "wajib" (keputusan 14: himbauan, bukan paksaan).

## Tidak boleh
- Mengirim kunci jawaban, pembahasan, bank soal, prompt AI, atau logika drill ke browser sebelum submit.
- Mengizinkan `PLAYTEST=1` di host produksi.
- Mengubah aturan tenggat: tryout yang **dimulai** sebelum Minggu 16.00 diterima sampai selesai, maks 2 jam sejak mulai; tidak ada masa tenggang lain.
- Mengarang harga, gateway, domain, jumlah soal resmi: tanyakan pemilik (lihat "Keputusan terbuka" di HANDOFF.md).
- Menaruh rahasia (kunci API, token) di repo. Semua lewat environment.
- Menaruh data pribadi anak atau isi buku soal berbayar di repo.
