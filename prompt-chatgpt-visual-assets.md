# Panduan & Prompt Aset Visual ChatGPT (Tryout Labschool v1)

Dokumen ini memetakan seluruh placeholder vektor di `public/assets/placeholders/*.svg` ke aset final bergaya **blocky/chunky 3D toy** (`public/assets/final/*.png`) yang dihasilkan menggunakan ChatGPT Image Generation (DALL-E / GPT-4o Image).

---

## 1. Arah Seni (Art Direction)

- **Gaya Visual:** Chunky 3D stylized toy blocks, tepi membulat halus (*beveled rounded cubes*), permukaan semi-matte seperti mainan kayu/plastik berkualitas tinggi, pencahayaan studio cerah dari kiri atas, dengan kontras warna tegas agar mudah terbaca oleh siswa kelas 6 SD.
- **Palet Warna Wajib:**
  - Sky Blue: `#38BDF8` (bayangan `#0284C7`)
  - Sun Gold: `#FFC93C` (bayangan `#D99B00`)
  - Coral Red: `#FF6B4A` (bayangan `#C9462B`)
  - Grass Green: `#58CC02` (bayangan `#3D9400`)
  - Grape Purple: `#8B5CF6` (bayangan `#6D28D9`)
  - Deep Navy Outline/Ink: `#172554`
- **Dunia & Tema:** Dunia belajar dan ruang kelas siswa Indonesia yang ceria, aman, dan penuh rasa ingin tahu.
- **Aturan Kepatuhan & Orisinalitas (WAJIB):**
  1. **Bebas Merek Dagang:** Dilarang menyertakan logo, tulisan, atau desain karakter bermerek dagang (tidak boleh ada logo Roblox, avatar R6/R15 resmi, atau merek sekolah apa pun).
  2. **Orisinalitas Penuh:** Tidak boleh memakai tema luar angkasa gelap, roket malam, atau maskot berang-berang/otter.
  3. **Tanpa Teks di Dalam Gambar:** Kecuali simbol matematika sederhana (`+`, `-`, `×`, `=`), jangan sertakan teks kalimat agar aset fleksibel di berbagai ukuran layar.
  4. **Latar Belakang Transparan:** Semua file PNG final wajib memiliki latar transparan murni (*true alpha transparency*), tanpa latar kotak/gradien, dan menyisakan *padding* aman 10%–15% di setiap sisi.

---

## 2. Tabel Pemetaan Placeholder -> Aset Final & Prompt ChatGPT

> **Suffix Prompt Global (tambahkan di akhir setiap prompt):**
> `Stylized chunky 3D toy aesthetic with rounded blocky geometry, vibrant saturated palette (sky blue #38BDF8, sun yellow #FFC93C, coral #FF6B4A, grass green #58CC02, grape purple #8B5CF6, dark navy accents #172554), soft studio lighting, clean 12% margin around subject, isolated on a completely transparent background, no text, no watermarks, no copyrighted characters or brand logos.`

| No | Placeholder SVG (`public/assets/placeholders/`) | File Final (`public/assets/final/`) | Ukuran Output | Kegunaan UI | Prompt ChatGPT Image Generation |
|---:|---|---|---|---|---|
| 1 | `hero-buddy.svg` | `hero-buddy.png` | `1024×1024` (PNG transparan) | Ilustrasi utama Hero Landing & Ruang Anak | `A cheerful original Grade 6 Indonesian student character in chunky 3D blocky toy style, wearing a crisp white and sky-blue (#38BDF8) school vest with a small golden star pin, a coral-red (#FF6B4A) backpack, and a grape-purple (#8B5CF6) cap, waving warmly while holding an oversized chunky yellow pencil (#FFC93C). Friendly expressive eyes, front three-quarter pose.` + *Global Suffix* |
| 2 | `star-badge.svg` | `star-badge.png` | `512×512` (PNG transparan) | Lencana bintang hasil tryout & ringkasan mingguan | `A chunky 3D toy reward badge shaped like a rounded sky-blue (#38BDF8) shield with three plump golden stars (#FFC93C) arranged in an arc and a grass-green (#58CC02) ribbon bar at the bottom.` + *Global Suffix* |
| 3 | `trophy-level.svg` | `trophy-level.png` | `512×512` (PNG transparan) | Lencana level belajar & pencapaian kesiapan | `A chunky 3D blocky golden trophy cup (#FFC93C) with thick rounded handles, a small white star emblem in the center, sitting on a grape-purple (#8B5CF6) rectangular block pedestal.` + *Global Suffix* |
| 4 | `streak-flame.svg` | `streak-flame.png` | `512×512` (PNG transparan) | Indikator konsistensi mingguan (streak) | `A chunky 3D stylized flame icon in vibrant coral-orange (#FF6B4A) with a bright sun-yellow (#FFC93C) inner core, nestled inside a rounded cream-and-navy badge frame.` + *Global Suffix* |
| 5 | `map-flag.svg` | `map-flag.png` | `512×512` (PNG transparan) | Penanda Hari Tes pada Peta Musim 12 akhir pekan | `A chunky 3D checkered finish flag on a golden flagpole (#FFC93C) topped with a coral-red (#FF6B4A) ball, planted into a small grass-green (#58CC02) rounded block base.` + *Global Suffix* |
| 6 | `paywall-lock.svg` | `paywall-lock.png` | `512×512` (PNG transparan) | Modal pratinjau akses & penanda fitur paket musim | `A chunky 3D golden padlock (#FFC93C) with a thick rounded silver shackle and a glowing white star emblem embossed on the front body, playful and friendly look.` + *Global Suffix* |
| 7 | `buku-salah-book.svg` | `buku-salah-book.png` | `512×512` (PNG transparan) | Ikon tab & kartu fitur Buku Salah | `A chunky 3D hardcover study notebook in coral-red (#FF6B4A) with a rounded spine, featuring a golden yellow (#FFC93C) sticky badge with a clean green checkmark on the cover.` + *Global Suffix* |
| 8 | `subject-kuantitatif.svg` | `subject-kuantitatif.png` | `512×512` (PNG transparan) | Ikon mata uji Kuantitatif | `A chunky 3D 2x2 grid of colorful rounded toy blocks in sky-blue (#38BDF8), sun-yellow (#FFC93C), grass-green (#58CC02), and coral (#FF6B4A) embossed with bold simple +, -, ×, = math symbols.` + *Global Suffix* |
| 9 | `subject-bacaan.svg` | `subject-bacaan.png` | `512×512` (PNG transparan) | Ikon mata uji Pemahaman Bacaan | `A chunky 3D open hardcover storybook on a grass-green (#58CC02) rounded tile, paired with a bright sun-yellow (#FFC93C) magnifying glass resting playfully on the right page.` + *Global Suffix* |
| 10 | `subject-verbal.svg` | `subject-verbal.png` | `512×512` (PNG transparan) | Ikon mata uji Verbal | `Two overlapping chunky 3D rounded speech bubbles in white and sun-yellow (#FFC93C) on a grape-purple (#8B5CF6) tile, representing clear communication and vocabulary.` + *Global Suffix* |
| 11 | `subject-ipa.svg` | `subject-ipa.png` | `512×512` (PNG transparan) | Ikon mata uji IPA | `A chunky 3D rounded science Erlenmeyer flask filled with bright sky-blue (#38BDF8) bubbling liquid and a coral (#FF6B4A) stopper, framed on a warm sun-yellow (#FFC93C) rounded tile.` + *Global Suffix* |
| 12 | `subject-ips.svg` | `subject-ips.png` | `512×512` (PNG transparan) | Ikon mata uji IPS | `A chunky 3D stylized globe in sky-blue (#38BDF8) oceans and grass-green (#58CC02) continents with a small golden compass pointer (#FFC93C), resting on a coral-red (#FF6B4A) rounded tile.` + *Global Suffix* |

---

## 3. Cara Mengganti Placeholder dengan Aset Final

1. Generate masing-masing file PNG menggunakan prompt di atas, lalu verifikasi transparansi latar dan dimensi.
2. Simpan di `public/assets/final/<nama-file>.png`.
3. Perbarui referensi `src="/assets/placeholders/<nama>.svg"` di halaman terkait menjadi `/assets/final/<nama>.png` (atau gunakan fallback `<picture>` / `img`).
