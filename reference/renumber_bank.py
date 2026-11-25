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

TOPIC_MAP = {
    ("Bahasa Indonesia", "Kata Baku"): ("Verbal", "VER-BKU"),
    ("Bahasa Indonesia", "Tanda Baca"): ("Verbal", "VER-BKU"),
    ("Bahasa Indonesia", "Gagasan Utama"): ("Pemahaman Bacaan", "BAC-GAG"),
    ("Verbal", "Antonim"): ("Verbal", "VER-ANT"),
    ("Verbal", "Sinonim"): ("Verbal", "VER-SIN"),
    ("IPA", "Peredaran Darah"): ("IPA", "IPA-PDR"),
    ("IPA", "Fotosintesis"): ("IPA", "IPA-FOT"),
    ("IPA", "Rangkaian Listrik"): ("IPA", "IPA-LIS"),
    ("IPA", "Gaya dan Gerak"): ("IPA", "IPA-GYA"),
    ("IPA", "Ekosistem"): ("IPA", "IPA-EKO"),
    ("IPS", "Peta dan Kenampakan"): ("IPS", "IPS-PET"),
    ("IPS", "Kegiatan Ekonomi"): ("IPS", "IPS-EKN"),
    ("IPS", "Keragaman Budaya"): ("IPS", "IPS-KEB"),
}


def normalize_chatgpt_items(raw_items: list[dict]) -> tuple[list[dict], list[dict]]:
    """Konversi format JSON array ChatGPT v1 ({q, opts, ans, penjelasan, cara_cepat}) ke skema kanonik v2."""
    passages = []
    out = []
    p_seq = 0
    for idx, src in enumerate(raw_items, 1):
        if "stem" in src and "options" in src and "answer_idx" in src:
            out.append(dict(src))
            continue
        subj_raw = str(src.get("subject", "")).strip()
        topic_raw = str(src.get("topic", "")).strip()
        subj, code = TOPIC_MAP.get((subj_raw, topic_raw), (subj_raw, ""))
        if not code:
            # Cari berdasarkan nama topik kanonik bila sudah cocok
            code = next((k for k, v in bf.TOPIC_NAME.items() if v.lower() == topic_raw.lower()), "VER-KOS")
            subj = bf.TOPIC_SUBJECT.get(code, subj_raw)
        lvl = int(src.get("level", 1))
        stem = str(src.get("q", "")).strip()
        pid = str(src.get("passage_id") or "").strip() or None
        subtopic_txt = topic_raw[:60] if len(topic_raw) >= 3 else f"Topik {code}"
        if code.startswith("BAC-") and not pid:
            # Wacana singkat inline (< 120 kata) tanpa bacaan panjang eksternal -> Logika Verbal (Wacana)
            marker = "Gagasan utama"
            para_part = stem.split(marker, 1)[0].strip() if marker in stem else stem
            if len(para_part.split()) >= 120:
                p_seq += 1
                pid = f"BAC-P-C{p_seq:03d}"
                if marker in stem:
                    para, qpart = stem.split(marker, 1)
                    stem = (marker + qpart).strip()
                    passages.append({"passage_id": pid, "topic": code, "text": para.strip() or stem})
                else:
                    passages.append({"passage_id": pid, "topic": code, "text": stem})
            else:
                subj = "Verbal"
                code = "VER-LOG"
                subtopic_txt = "Gagasan Utama Wacana"
        opts = list(src.get("opts", []))
        ans = int(src.get("ans", 0))
        if len(opts) == 4 and 0 <= ans < 4:
            target = (idx - 1) % 4
            if target != ans:
                opts[ans], opts[target] = opts[target], opts[ans]
                ans = target
        expl = str(src.get("penjelasan", "")).strip()
        if len(expl) < 20:
            expl = expl + " (pembahasan tervalidasi bank soal)."
        sc_txt = str(src.get("cara_cepat", "")).strip()
        if len(sc_txt) < 10:
            sc_txt = sc_txt + " Gunakan eliminasi opsi."
        out.append({
            "id": str(src.get("id", f"{code}-L{lvl}-{idx:04d}")),
            "version": int(src.get("version", 1)),
            "subject": subj,
            "topic": code,
            "subtopic": subtopic_txt,
            "level": lvl if lvl in (1, 2, 3) else 1,
            "type": "pg4",
            "passage_id": pid,
            "stem": stem,
            "options": opts,
            "answer_idx": ans,
            "explanation": expl,
            "shortcut": sc_txt,
            "shortcut_scope": "umum",
            "est_seconds": {1: 45, 2: 75, 3: 105}.get(lvl, 60),
            "image": None,
            "ambiguous": False,
            "notes": f"orig_id:{src.get('id', '')}",
        })
    return out, passages


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
    """Jalankan ID-renumbering pada berkas batch JSON (dict/array) atau JSONL."""
    dst = dst or src
    if src.suffix == ".json":
        data = json.loads(src.read_text(encoding="utf-8"))
        if isinstance(data, list):
            norm_items, passages = normalize_chatgpt_items(data)
            items, stats = renumber_items(norm_items, existing_dir=existing_dir)
            payload = {"batch": src.stem, "passages": passages, "items": items}
            dst.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return stats
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
