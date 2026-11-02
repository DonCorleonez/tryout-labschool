"""CLI validator bank soal. Pakai:  python3 bankcheck.py FOLDER_BANK
Keluar dengan kode 1 bila ada butir ditolak. Laporan bisa ditempel apa adanya sebagai umpan balik ke ChatGPT."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bankfile import Bank  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__); sys.exit(2)
    b = Bank.load(sys.argv[1])
    print(b.report())
    sys.exit(1 if b.rejected else 0)
