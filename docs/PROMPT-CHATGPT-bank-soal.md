# Prompt ChatGPT — bank soal, versi 2 (2 Nov 2026 malam)

Cara pakai: tempel seluruh isi di bawah garis ke ChatGPT. Lampirkan `BRIEF-CHATGPT-bank-soal.md` dan berkas referensi soal yang ada (PDF buku latihan; bila lebih dari 25 MB, pecah per bab atau pakai versi terkompresi). Prompt ini menggantikan versi 1.

---

Kamu adalah penyusun bank soal untuk tryout persiapan **Jalur Tes SMP Labschool 2027**. Pesertanya siswa kelas 6 SD (Kurikulum Merdeka Fase C). Hasil kerjamu langsung dimuat oleh program, jadi formatnya harus lengkap dan persis. Bila prompt ini berbeda dengan BRIEF terlampir, **prompt ini yang berlaku**.

## 1. Tujuan

Hasilkan bank soal yang **lebih dari cukup** untuk satu musim (14 tryout + latihan drill, ditambah cadangan), dengan tipe, tingkat kesulitan, dan gaya yang **serupa dengan referensi**: berkas PDF dan sumber lain yang dilampirkan. Setiap soal wajib membawa label mata uji, topik, dan subtopik, kunci, pembahasan, dan cara cepat. Dengan begitu halaman hasil siswa bisa langsung menampilkan "salah berapa, di topik apa, dari mata uji apa" tanpa bantuan AI.

## 2. Cara memakai referensi (penting)

Referensi dipakai untuk mempelajari **tipe soal, pola berpikir yang diuji, tingkat kesulitan, dan gaya bahasa**, lalu membuat soal **baru** dengan variasi. Aturannya:
- Ganti konteks, tokoh, angka, urutan informasi, dan bentuk pertanyaan. Siswa yang pernah membaca referensi tidak boleh mengenali soalmu sebagai soal yang sama.
- Dilarang menyalin atau memparafrase dekat satu soal, bacaan, atau pembahasan tertentu dari referensi. Referensi adalah buku berbayar milik pihak lain.
- Catat tipe yang ditiru di bidang `ref_tipe`, misalnya `"analogi sebab-akibat; pola dari referensi Jilid 2 bab Verbal"`. Jangan menyalin teks soal referensi ke bidang ini.

## 3. Instrumen resmi (Pedoman Jalur Tes 2027, tabel "Instrumen Tes Seleksi")

| Mata uji (`subject`) | Isi menurut pedoman |
|---|---|
| Kuantitatif | analisis masalah berbentuk matematika: geometri, statistika, peluang, logika, aljabar |
| Pemahaman Bacaan | memahami, menginterpretasi, dan menganalisis teks berbagai topik |
| Verbal | kata beda, kosakata, sinonim, analogi verbal, klasifikasi kata, wacana (logika verbal), *missing word* |
| IPA, IPS | tes akademik mata pelajaran |
| Survei Karakter | opini pribadi (gotong royong, Bhinneka Tunggal Ika, dll.), **tidak dinilai** dan **belum** dikerjakan sekarang |

Format tes: satu daftar campur, satu soal per layar, pilihan ganda 4 opsi. **Komposisi kerja per tryout: 40 soal** = Kuantitatif 11, Pemahaman Bacaan 7, Verbal 7, IPA 10, IPS 5. Pedoman tidak menyebut jumlah per mata uji; angka ini perkiraan dari tryout pesaing.

## 4. Topik kanonik (`topic`) — pakai kode PERSIS ini

- **Kuantitatif:**
  - MAT-PEC Pecahan
  - MAT-KPK KPK dan FPB
  - MAT-PBD Perbandingan dan Skala
  - MAT-PSN Persen dan Uang
  - MAT-BIL Bilangan Bulat dan Operasi Hitung
  - MAT-GEO Geometri (bangun datar/ruang)
  - MAT-SAT Satuan dan Konversi
  - MAT-DAT Statistika (data, rata-rata)
  - MAT-POL Pola Bilangan
  - MAT-KEC Kecepatan, Jarak, Waktu
  - MAT-PEL Peluang
  - MAT-LOG Logika Matematika
  - MAT-ALJ Aljabar Sederhana
- **Pemahaman Bacaan:**
  - BAC-GAG Gagasan Utama
  - BAC-INF Informasi Tersurat dan Tersirat
  - BAC-SIM Simpulan dan Tujuan Penulis
  - BAC-MKN Makna Kata dalam Konteks
- **Verbal:**
  - VER-ANT Antonim
  - VER-SIN Sinonim
  - VER-ANA Analogi
  - VER-KLS Klasifikasi / Kata yang Berbeda
  - VER-KOS Kosakata
  - VER-LOG Logika Verbal (Wacana)
  - VER-MIS Melengkapi Kata yang Hilang
  - VER-BKU Kata Baku dan Tanda Baca
- **IPA:**
  - IPA-PDR Peredaran Darah dan Pernapasan
  - IPA-PEN Pencernaan dan Gizi
  - IPA-FOT Fotosintesis dan Tumbuhan
  - IPA-LIS Listrik dan Rangkaian
  - IPA-MAG Magnet
  - IPA-GYA Gaya, Gerak, dan Energi
  - IPA-CAH Cahaya dan Bunyi
  - IPA-WUJ Zat, Wujud, dan Perubahannya
  - IPA-EKO Ekosistem dan Makhluk Hidup
  - IPA-BMI Bumi dan Tata Surya
- **IPS:**
  - IPS-PET Peta dan Kenampakan Alam
  - IPS-EKN Kegiatan Ekonomi
  - IPS-KEB Keberagaman dan Kehidupan Sosial
  - IPS-SEJ Sejarah dan Peninggalan
  - IPS-IDN Wilayah Indonesia dan ASEAN

Topik baru tidak boleh dipakai. Usulkan di `catatan.md`. `subtopic` bebas tapi spesifik dan konsisten (3–60 karakter), misalnya "Pecahan campuran", "Rangkaian paralel", "Analogi alat-fungsi".

## 5. Format output (dimuat program apa adanya)

**Butir non-Matematika**: berkas `.jsonl`, satu objek JSON per baris:
```json
{"id":"IPA-CAH-L2-0003","version":1,"subject":"IPA","topic":"IPA-CAH","subtopic":"Pembiasan cahaya","level":2,"type":"pg4","passage_id":null,
 "stem":"...","options":["...","...","...","..."],"answer_idx":2,
 "explanation":"Mengapa kunci benar (2-4 kalimat) dan mengapa pengecoh terkuat salah.",
 "shortcut":"Cara cepat yang berlaku umum, 1-2 kalimat.","shortcut_scope":"umum","est_seconds":75,
 "image":null,"ambiguous":false,"ref_tipe":"...","notes":""}
```
- `id` = `{TOPIK}-L{level}-{4 digit}`, unik, tidak pernah dipakai ulang. Perbaikan soal = naikkan `version` dengan `id` tetap.
- `subject` salah satu dari: `Kuantitatif`, `Pemahaman Bacaan`, `Verbal`, `IPA`, `IPS`, dan harus cocok dengan topiknya.
- `level`: 1 = langsung/pemahaman dasar, 2 = penerapan 1–2 langkah, 3 = penalaran/HOTS. `est_seconds`: L1 30–60, L2 60–90, L3 90–150.
- Bacaan ditulis sebagai baris tersendiri: `{"passage_id":"BAC-P-0012","topic":"BAC-GAG","text":"..."}` (120–250 kata, orisinal), lalu 3–4 butir BAC-* yang merujuk `passage_id` itu, **dalam berkas yang sama**.

**Kuantitatif = template Python**, bukan butir JSONL, supaya kunci dihitung program:
```python
from fractions import Fraction

def _pick(correct_val, cands, fmt):
    out, seen = [], {correct_val}
    for v in cands:                      # urutkan dari kesalahan siswa yang paling umum
        if v is not None and v > 0 and v not in seen:
            out.append(fmt(v)); seen.add(v)
        if len(out) == 3: break
    return out                           # sediakan >= 5 calon supaya selalu dapat 3

def mat_pec_tambah(rng):
    d = rng.choice([6, 8, 10, 12]); a = rng.randint(1, d // 2 - 1); b = rng.randint(1, d // 2 - 1)
    s = Fraction(a + b, d); f = lambda v: f"{v.numerator}/{v.denominator}"
    cands = [Fraction(a + b, 2 * d), Fraction(a * b, d), Fraction(a + b + 1, d), Fraction(a + b, d + 1), Fraction(a + b + 2, d)]
    return {"topic": "MAT-PEC", "subtopic": "Penjumlahan pecahan berpenyebut sama", "level": 1,
            "stem": f"Hitung: {a}/{d} + {b}/{d} = ... (bentuk paling sederhana)",
            "correct": f(s), "distractors": _pick(s, cands, f),
            "explanation": "...", "shortcut": "..."}
```
Aturan template:
- Nama fungsi `mat_...`, fungsi murni, stdlib saja.
- Mengembalikan tepat `topic, subtopic, level, stem, correct, distractors (3), explanation, shortcut`.
- Program menjalankan setiap template pada 1.000 seed dan **menolaknya** bila pada seed mana pun ada dua opsi yang tulisannya sama atau **nilainya** sama (`2/4` dan `1/2`), atau bila fungsi galat.
- Contoh di BRIEF §7 justru gagal (`a*b` bisa sama dengan `a+b`), jadi pakai pola `_pick` di atas.
- Variasikan struktur soal (cerita, tabel dalam teks, perbandingan), bukan hanya angkanya.

## 6. Ditolak otomatis bila…

- Ada bidang wajib yang kosong.
- `id` tidak cocok dengan topik/level.
- Topik bukan kode kanonik, atau subject tidak cocok dengan topik.
- Opsi bukan 4 teks unik.
- `answer_idx` di luar 0–3.
- Ada opsi "semua benar/salah", "A dan B benar", atau "tidak ada yang benar".
- Teks kunci muncul utuh di stem.
- Pembahasan kurang dari 20 karakter, atau cara cepat kurang dari 10 karakter.
- `image` tidak `null`.
- Bacaan hilang, atau stem kembar.
- `ambiguous: true` (ditahan sampai ditinjau manusia).

Peringatan (bukan penolakan): sebaran kunci di luar 22–28% per huruf.

## 7. Target volume (lebih dari cukup, termasuk cadangan ±30%)

| Mata uji | Target butir/template | Catatan |
|---|---|---|
| Pemahaman Bacaan | ≥ 45 bacaan, ≥ 170 butir | 3–4 butir per bacaan, sebar 4 topik |
| Verbal | ≥ 170 butir | ≥ 15 per topik, utamakan ANA, KLS, SIN, ANT, MIS |
| IPA | ≥ 230 butir | ≥ 18 per topik |
| IPS | ≥ 110 butir | ≥ 18 per topik |
| Kuantitatif | ≥ 80 template | ≥ 6 per topik (≥ 2 per level), variasi struktur |

Sebaran level per tryout: Diagnostik 40/40/20 (L1/L2/L3), Fondasi 40/45/15, Akselerasi 25/50/25, Intensif dan Gladi 15/45/40. Buat cukup L3 untuk fase akhir.

## 8. Urutan kerja dan ukuran kiriman

Kirim per batch, **maksimal 25 butir atau 6 template per jawaban** supaya tidak terpotong. Setiap berkas dalam satu blok kode utuh, dengan nama berkas di atasnya. Jangan menulis "dan seterusnya".

1. **Batch 0 (sekarang): uji format.**
   - Berkas `batch-00-contoh.jsonl`: 3 IPA/IPS, 2 Verbal, 1 bacaan + 4 butir Bacaan.
   - Berkas `batch-00-mat-templates.py`: 2 template dari 2 topik MAT berbeda, plus 3 contoh keluaran (seed 1, 2, 3) dalam komentar.
   - Berkas `batch-00-catatan.md`.
   - Tunggu umpan balik validator sebelum lanjut.
2. **Batch 1: diagnostik lengkap 40 soal** (komposisi §3, sebaran 40/40/20). Batas **Rabu 4 Nov 10.00 WIB**, paling mendesak karena diagnostik gratis sudah dibuka.
   - Semua butir diberi `"notes":"diagnostik"`.
   - Soal ini dilihat semua pendaftar gratis, jadi **jangan dipakai ulang** dan jangan dibuat variasi dekatnya untuk tryout berbayar.
3. **Batch 2 dan seterusnya:** isi stok per mata uji sampai target §7. Nama berkas: `batch-NN-<mapel>.jsonl` / `batch-NN-mat-templates.py`.

## 9. `catatan.md` per batch (wajib)

- Jumlah butir per mata uji, per topik, dan per level.
- Sebaran kunci A/B/C/D.
- Daftar periksa BRIEF §9 (centang).
- Tipe referensi yang ditiru.
- Butir yang kamu ragukan beserta alasannya.
- Usulan topik baru.
- Pertanyaan untuk pemilik.

Jangan menulis "sudah diverifikasi". Verifikasi dilakukan program (`python3 bankcheck.py FOLDER`) dan peninjau manusia (10% acak + semua butir yang ditandai).

## 10. Larangan

- Isi harus orisinal. Tidak ada soal "bocoran" dan tidak ada klaim soal asli.
- Pakai nama tokoh fiktif. Hindari merek, politik, agama, SARA, dan kekerasan.
- Bahasa Indonesia baku setingkat kelas 6. Sapa pembaca dengan "kamu" atau "siswa".
- Tidak boleh ada soal yang dua jawabannya bisa dibela.
- Tidak boleh soal bergambar untuk sekarang. Soal harus bisa dijawab hanya dari teks.

Mulai dengan menuliskan pemahamanmu atas tugas ini dalam 5 kalimat, lalu langsung buat batch 0.
