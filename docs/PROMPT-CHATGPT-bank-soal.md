# Prompt untuk ChatGPT — bank soal (tempel apa adanya, lampirkan BRIEF-CHATGPT-bank-soal.md)

---

Kamu adalah penyusun bank soal untuk produk tryout persiapan Jalur Tes SMP Labschool 2027 (siswa kelas 6 SD, Kurikulum Merdeka Fase C). Aturan lengkapnya ada di lampiran **BRIEF-CHATGPT-bank-soal.md**. Baca seluruhnya dulu. Bila prompt ini dan BRIEF berbeda, **prompt ini yang berlaku** (berisi pembaruan 2 Nov 2026).

## Pembaruan sejak BRIEF ditulis

1. **Soal diagnostik dipakai bersama oleh semua siswa.** Diagnostik gratis memakai SATU set soal yang sama untuk semua pendaftar dan bisa dilihat siapa saja yang mendaftar gratis. Konsekuensinya:
   - Butir diagnostik (batch 1) **tidak boleh dipakai ulang** di tryout berbayar mana pun. Tandai setiap butirnya dengan `"notes": "diagnostik"`.
   - Jangan membuat butir tryout berbayar yang hanya mengganti angka atau nama dari butir diagnostik.
2. **Template Matematika: pengecoh tidak boleh sama dengan kunci.** Validator program menjalankan setiap template pada 1.000 seed dan menolak template yang pada seed mana pun menghasilkan:
   - dua opsi teks yang sama, atau
   - dua opsi yang **nilainya** sama walau tulisannya beda (mis. `2/4` dan `1/2`, `Rp20.000` dan `Rp20000`).

   Contoh template di BRIEF §7 justru gagal, karena `a*b` bisa sama dengan `a+b` (a = b = 2). Pakai pola aman ini:
   ```python
   from fractions import Fraction

   def _pick(correct_val, cands, fmt):
       out, seen = [], {correct_val}
       for v in cands:                      # urutkan dari kesalahan anak yang paling umum
           if v is not None and v > 0 and v not in seen:
               out.append(fmt(v)); seen.add(v)
           if len(out) == 3: break
       return out                           # sediakan >= 5 calon supaya selalu dapat 3

   def mat_pec_tambah(rng):
       d = rng.choice([6, 8, 10, 12]); a = rng.randint(1, d // 2 - 1); b = rng.randint(1, d // 2 - 1)
       s = Fraction(a + b, d); f = lambda v: f"{v.numerator}/{v.denominator}"
       cands = [Fraction(a + b, 2 * d), Fraction(a * b, d), Fraction(a + b + 1, d), Fraction(a + b, d + 1), Fraction(a + b + 2, d)]
       return {"topic": "MAT-PEC", "level": 1, "stem": f"Hitung: {a}/{d} + {b}/{d} = ... (bentuk paling sederhana)",
               "correct": f(s), "distractors": _pick(s, cands, f),
               "explanation": "...", "shortcut": "..."}
   ```
   Setiap fungsi template harus bernama `mat_...`, berupa fungsi murni dengan stdlib saja, menerima `rng` (`random.Random`), dan mengembalikan tepat kunci `topic, level, stem, correct, distractors (3), explanation, shortcut`.
3. **Jumlah soal dan durasi resmi belum dipastikan.** Tetap pakai asumsi BRIEF §3 (40 soal: Kuantitatif 12, Pemahaman Bacaan 8, Verbal 6, IPA 8, IPS 6). Bila kamu bisa membaca Pedoman Jalur Tes 2027, laporkan angka resminya beserta kutipan halamannya di `catatan.md`, tapi **jangan** ubah komposisi sendiri.
4. Istilah di teks soal dan pembahasan: pakai "siswa" atau "kamu". Jangan pakai "keluarga".

## Yang divalidasi program (butir yang gagal salah satunya otomatis ditolak)

- Semua bidang wajib ada: `id, version, subject, topic, level, type, stem, options, answer_idx, explanation, shortcut, est_seconds`.
- Format `id` = `{TOPIK}-L{level}-{4 digit}` dan harus cocok dengan `topic` dan `level` butir itu. Contoh: `IPA-FOT-L2-0007`.
- `topic` harus salah satu dari 31 kode kanonik, dan `subject` harus cocok dengan topiknya. Topik `MAT-*` hanya boleh berupa template, tidak boleh butir JSONL.
- `type` = `"pg4"`. `options` = tepat 4 teks yang berbeda (tidak peka huruf besar dan tanda baca). `answer_idx` = 0–3.
- Opsi terlarang: "semua benar/salah", "A dan B benar", "tidak ada yang benar".
- Teks kunci tidak boleh muncul utuh di stem.
- Panjang minimum: `explanation` ≥ 20 karakter, `shortcut` ≥ 10 karakter. `est_seconds` 15–300. `image` = `null`.
- Soal BAC-* wajib punya `passage_id` yang bacaannya ada di berkas yang sama. Bacaan ditulis sebagai baris sendiri `{"passage_id": ..., "topic": ..., "text": ...}`, panjangnya 120–250 kata.
- Stem kembar (dengan bacaan yang sama) ditolak.
- Butir dengan `"ambiguous": true` tidak dimuat sampai ditinjau manusia.
- Peringatan, bukan penolakan: sebaran kunci di luar 22–28% per huruf.

## Tugasmu sekarang: Batch 0 (secepatnya; batas semula Senin 2 Nov 12.00 sudah lewat)

Buat 3 berkas:
1. `batch-00-contoh.jsonl` berisi:
   - 3 butir IPA/IPS,
   - 2 butir Verbal,
   - 1 bacaan + 4 butir Pemahaman Bacaan.

   Semuanya level campuran, dengan sebaran kunci serata mungkin.
2. `batch-00-mat-templates.py` berisi 2 template Matematika dari 2 topik MAT berbeda, plus 3 contoh keluaran (seed 1, 2, 3) dalam komentar di bawah tiap fungsi.
3. `batch-00-catatan.md` berisi:
   - jumlah butir per topik dan level,
   - sebaran kunci A/B/C/D,
   - hasil daftar periksa BRIEF §9 (centang per butir),
   - butir yang kamu ragukan dan alasannya,
   - pertanyaan untuk pemilik.

Setelah batch 0 diterima validator, lanjut ke **Batch 1 = diagnostik lengkap 40 butir, batas Rabu 4 Nov 10.00 WIB** (diagnostik gratis sudah dibuka untuk umum, jadi batch ini paling mendesak) (sebaran level Diagnostik: L1 40%, L2 40%, L3 20%). Semua butirnya diberi `"notes": "diagnostik"`, dan Kuantitatif berupa template. Jangan mulai Batch 1 sebelum ada umpan balik format.

## Cara menyerahkan

- Keluarkan setiap berkas dalam **satu blok kode utuh** dengan nama berkas di atasnya. Jangan potong, dan jangan tulis "dan seterusnya".
- JSONL: satu objek per baris, UTF-8, tanpa koma di akhir baris, tanpa komentar.
- Jangan menulis "sudah diverifikasi". Verifikasi dilakukan program (`python3 bankcheck.py FOLDER`) dan peninjau manusia.

## Larangan (ringkas dari BRIEF)

Semua stem, bacaan, opsi, dan pembahasan harus orisinal. Dilarang memparafrase buku soal, soal tahun lalu, atau "bocoran". Gunakan nama tokoh fiktif. Hindari merek, politik, agama, dan isu sensitif. Bahasa Indonesia baku setingkat kelas 6. Soal tidak boleh bergambar dulu. Tidak boleh ada soal yang dua jawabannya bisa dibela.

Mulai dengan menuliskan dalam 5 kalimat pemahamanmu atas tugas ini, lalu langsung buat batch 0.
