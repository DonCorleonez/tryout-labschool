"""Importer batch soal: menjalankan ID-renumbering lalu memvalidasi seluruh butir + template."""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

import bankfile as bf
import renumber_bank as rb


def import_batch(batch_path: Path, existing_dir: Path | None = None, dest_dir: Path | None = None) -> dict:
    """Renumber -> validasi via Bank.load -> kembalikan ringkasan hasil import."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        staged = tmp_dir / batch_path.name
        stats = rb.renumber_batch_file(batch_path, staged, existing_dir=existing_dir)
        b = bf.Bank.load(tmp_dir)
        summary = {
            "items_loaded": len(b.items),
            "passages_loaded": len(b.passages),
            "templates_loaded": len(b.templates),
            "rejected_count": len(b.rejected),
            "rejected": b.rejected,
            "warnings": b.warnings,
            "renumbered": stats["renumbered"],
            "report": b.report(),
        }
        if dest_dir and len(b.rejected) == 0:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(staged, dest_dir / batch_path.name)
        return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Smoke import & validasi batch bank soal.")
    ap.add_argument("batch", type=Path, help="Berkas batch JSON/JSONL")
    ap.add_argument("--existing", type=Path, default=None, help="Folder bank existing")
    ap.add_argument("--dest", type=Path, default=None, help="Folder tujuan jika validasi 0 ditolak")
    args = ap.parse_args(argv)
    res = import_batch(args.batch, existing_dir=args.existing, dest_dir=args.dest)
    print(res["report"])
    if res["rejected_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
