"""Membuat ulang fixture bank-contoh/batch-00-contoh.jsonl dan bank-rusak/batch-99-rusak.jsonl. Jalankan dari folder ini."""
import json, os

P = {"passage_id": "BAC-P-0001", "topic": "BAC-GAG", "text": (
    "Setiap Sabtu pagi, Raka dan adiknya, Sari, membantu nenek merawat kebun kecil di belakang rumah. "
    "Kebun itu berisi cabai, tomat, dan beberapa pohon pisang. Nenek selalu berkata bahwa tanaman perlu dirawat dengan sabar. "
    "Raka bertugas menyiram tanaman sebelum matahari terlalu terik, sedangkan Sari mencabuti rumput liar di sela-sela bedengan. "
    "Suatu hari, daun tomat mulai menguning. Raka khawatir tanamannya akan mati. Nenek lalu mengajak mereka memeriksa tanah. "
    "Ternyata tanah di sekitar tomat terlalu basah karena Raka menyiram terlalu banyak. Nenek menjelaskan bahwa akar juga memerlukan udara. "
    "Jika tanah selalu tergenang, akar sulit bernapas dan daun bisa menguning. Sejak hari itu, Raka menyentuh tanah lebih dulu sebelum menyiram. "
    "Bila tanah masih lembap, ia menunggu sampai sore. Dua minggu kemudian, daun tomat kembali hijau dan buahnya mulai muncul. "
    "Sari tertawa dan berkata bahwa kakaknya kini sudah menjadi petani yang teliti.")}


def it(i, subj, topic, lvl, stem, opts, ans, pid=None, amb=False):
    return {"id": f"{topic}-L{lvl}-{i:04d}", "version": 1, "subject": subj, "topic": topic, "subtopic": "Subtopik contoh", "level": lvl, "type": "pg4", "passage_id": pid, "stem": stem,
            "options": opts, "answer_idx": ans, "explanation": "Pembahasan contoh yang menjelaskan mengapa kunci benar dan pengecoh salah.",
            "shortcut": "Cara cepat contoh yang berlaku umum.", "shortcut_scope": "umum", "est_seconds": 60, "image": None, "ambiguous": amb, "notes": ""}


good = [P,
    it(1, "Pemahaman Bacaan", "BAC-GAG", 1, "Gagasan utama bacaan tersebut adalah ...", ["Kebun nenek berisi cabai dan tomat", "Merawat tanaman perlu kesabaran dan ketelitian", "Sari suka mencabuti rumput liar", "Pohon pisang tumbuh di belakang rumah"], 1, "BAC-P-0001"),
    it(2, "Pemahaman Bacaan", "BAC-INF", 1, "Mengapa daun tomat menguning?", ["Tanah terlalu basah", "Tanaman kurang pupuk", "Matahari terlalu terik", "Rumput liar terlalu banyak"], 0, "BAC-P-0001"),
    it(3, "Pemahaman Bacaan", "BAC-SIM", 2, "Sikap Raka setelah mendengar penjelasan nenek menunjukkan bahwa Raka ...", ["Malas menyiram tanaman", "Takut kepada nenek", "Mau belajar dari kesalahan", "Ingin berhenti berkebun"], 2, "BAC-P-0001"),
    it(4, "Pemahaman Bacaan", "BAC-MKN", 2, "Kata 'tergenang' dalam bacaan paling dekat artinya dengan ...", ["Kering sekali", "Tertutup rumput", "Penuh pupuk", "Terendam air"], 3, "BAC-P-0001"),
    it(1, "IPA", "IPA-FOT", 1, "Gas yang diambil daun dari udara untuk membuat makanan adalah ...", ["Oksigen", "Karbon dioksida", "Nitrogen", "Uap air"], 1),
    it(1, "IPA", "IPA-LIS", 2, "Dua lampu dipasang berderet dalam satu jalur. Bila satu lampu putus, lampu lainnya ...", ["Tetap menyala terang", "Menyala lebih terang", "Ikut padam", "Menyala berkedip"], 2),
    it(1, "IPA", "IPA-WUJ", 1, "Perubahan wujud dari padat menjadi cair disebut ...", ["Mencair", "Membeku", "Menguap", "Mengembun"], 0),
    it(1, "IPS", "IPS-PET", 1, "Garis khayal yang membagi bumi menjadi belahan utara dan selatan adalah ...", ["Garis bujur", "Garis khatulistiwa", "Garis pantai", "Garis kontur"], 1),
    it(1, "IPS", "IPS-EKN", 1, "Kegiatan menyalurkan barang dari produsen ke konsumen disebut ...", ["Produksi", "Konsumsi", "Distribusi", "Investasi"], 2),
    it(1, "Verbal", "VER-ANT", 1, "Lawan kata 'hemat' adalah ...", ["Irit", "Cermat", "Teliti", "Boros"], 3),
    it(1, "Verbal", "VER-SIN", 1, "Persamaan kata 'cerdik' adalah ...", ["Pandai", "Malas", "Lambat", "Ceroboh"], 0),
    it(2, "IPA", "IPA-EKO", 2, "Contoh butir ragu yang ditandai penulis ...", ["Satu", "Dua", "Tiga", "Empat"], 0, amb=True),
]
bad = [it(1, "IPA", "IPA-XXX", 1, "Topik tidak kanonik ...", ["a1", "b1", "c1", "d1"], 0),
    it(2, "IPS", "IPA-FOT", 1, "Subject salah untuk topik ...", ["a2", "b2", "c2", "d2"], 0),
    it(3, "IPA", "IPA-FOT", 1, "Opsi kembar di soal ini ...", ["Sama", "sama", "Beda", "Lain"], 0),
    it(4, "IPA", "IPA-FOT", 1, "Opsi terlarang di soal ini ...", ["Semua benar", "Daun", "Akar", "Batang"], 1),
    it(5, "IPA", "IPA-FOT", 1, "Bagian tumbuhan bernama klorofil hijau berfungsi menangkap ...", ["Klorofil hijau", "Cahaya", "Air", "Udara"], 0),
    it(6, "IPA", "IPA-FOT", 1, "Kunci di luar rentang ...", ["a6", "b6", "c6", "d6"], 4),
    it(7, "Pemahaman Bacaan", "BAC-GAG", 1, "Bacaan hilang ...", ["a7", "b7", "c7", "d7"], 0, "BAC-P-9999"),
    it(8, "Kuantitatif", "MAT-PEC", 1, "Matematika bukan template ...", ["a8", "b8", "c8", "d8"], 0)]
x = it(9, "IPA", "IPA-FOT", 1, "Id tidak cocok level ...", ["a9", "b9", "c9", "d9"], 0); x["id"] = "IPA-FOT-L2-0009"; bad.append(x)

if __name__ == "__main__":
    os.makedirs("bank-contoh", exist_ok=True); os.makedirs("bank-rusak", exist_ok=True)
    open("bank-contoh/batch-00-contoh.jsonl", "w").write("\n".join(json.dumps(o, ensure_ascii=False) for o in good) + "\n")
    open("bank-rusak/batch-99-rusak.jsonl", "w").write("\n".join(json.dumps(o, ensure_ascii=False) for o in bad) + "\n{bukan json\n")
