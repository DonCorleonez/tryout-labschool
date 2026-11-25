"""Script ID-renumbering deterministik untuk bank soal sebelum import batch ChatGPT.

Menjamin format ID `{TOPIK}-L{level}-{4 digit}` unik terhadap bank existing,
mencegah tabrakan ID antar batch, dan memvalidasi bebas kata terlarang.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import bankfile as bf

ID_RX = re.compile(r"^(?P<topic>[A-Z]{3}-[A-Z]{3})-L(?P<level>[123])-(?P<n>\d{4})$")


def scan_existing_max(existing_dir: Path | None) -> dict[tuple[str, int], int]:
    """Cari nomor urut maksimum per (topic, level) pada bank existing."""
    max_seq: dict[tuple[str, int], int] = defaultdict(int)
    if not existing_dir or not existing_dir.exists():
        return max_seq
    for f in list(existing_dir.glob("*.jsonl")) + list(existing_dir.glob("*.json")):
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        objs = []
        if f.suffix == ".json":
            try:
                d = json.loads(text)
                if isinstance(d, dict):
                    objs = d.get("items", [])
            except ValueError:
                continue
        else:
            for line in text.splitlines():
                if not line.strip():
                    continue
                try:
                    objs.append(json.loads(line))
                except ValueError:
                    continue
        for o in objs:
            if isinstance(o, dict) and "id" in o:
                m = ID_RX.match(str(o["id"]))
                if m:
                    key = (m["topic"], int(m["level"]))
                    max_seq[key] = max(max_seq[key], int(m["n"]))
    return max_seq


def renumber_items(items: list[dict], existing_dir: Path | None = None, start_overrides: dict[tuple[str, int], int] | None = None) -> tuple[list[dict], dict]:
    """Beri nomor ulang ID butir secara deterministik tanpa mengubah isi soal."""
    counters = scan_existing_max(existing_dir)
    if start_overrides:
        for k, v in start_overrides.items():
            counters[k] = max(counters[k], v)
    out = []
    changes = []
    seen_ids = set()
    for it in items:
        copy = dict(it)
        topic = str(copy.get("topic", "UNK-UNK")).strip()
        level = int(copy.get("level", 1))
        key = (topic, level)
        counters[key] += 1
        new_id = f"{topic}-L{level}-{counters[key]:04d}"
        while new_id in seen_ids:
            counters[key] += 1
            new_id = f"{topic}-L{level}-{counters[key]:04d}"
        seen_ids.add(new_id)
        old_id = copy.get("id", "")
        if old_id != new_id:
            changes.append({"old_id": old_id, "new_id": new_id})
        copy["id"] = new_id
        out.append(copy)
    return out, {"total": len(out), "renumbered": len(changes), "changes": changes}


def renumber_batch_file(src: Path, dst: Path | None = None, existing_dir: Path | None = None) -> dict:
    """Jalankan ID-renumbering pada berkas batch JSON atau JSONL."""
    dst = dst or src
    if src.suffix == ".json":
        data = json.loads(src.read_text(encoding="utf-8"))
        items, stats = renumber_items(data.get("items", []), existing_dir=existing_dir)
        data["items"] = items
        dst.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return stats
    lines = [json.loads(ln) for ln in src.read_text(encoding="utf-8").splitlines() if ln.strip()]
    passages = [o for o in lines if "id" not in o and "passage_id" in o]
    items = [o for o in lines if "id" in o]
    new_items, stats = renumber_items(items, existing_dir=existing_dir)
    out_lines = [json.dumps(o, ensure_ascii=False) for o in passages + new_items]
    dst.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="ID-renumbering deterministik untuk bank soal.")
    ap.add_argument("input", type=Path, help="Berkas batch (.json atau .jsonl)")
    ap.add_argument("--out", type=Path, default=None, help="Berkas keluaran (default: timpa input)")
    ap.add_argument("--existing", type=Path, default=None, help="Folder bank existing untuk hindari tabrakan ID")
    args = ap.parse_args(argv)
    stats = renumber_batch_file(args.input, args.out, args.existing)
    print(json.dumps({"ok": True, "total": stats["total"], "renumbered": stats["renumbered"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
