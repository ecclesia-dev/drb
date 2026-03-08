#!/usr/bin/env python3
"""
Merge all Douai 1609 annotation TSVs into a single deduplicated output.

Sources:
  - douai-1609-annotations.tsv  (website source — NT + some OT from HTML)
  - douai-1609-pentateuch.tsv   (scan-pdf — Gn/Ex/Lv/Nm/Dt)
  - douai-1609-historical.tsv   (scan-pdf — historical books)
  - douai-1609-wisdom.tsv       (scan-pdf — wisdom books)
  - douai-1609-prophets.tsv     (scan-pdf — major prophets)
  - douai-1609-minor-prophets.tsv (scan-pdf — all 12 minor prophets)

Output: douai-1609-final.tsv
Dedup key: (BookAbbrev, Chapter:Verse, first 50 chars of Annotation)
Sort: by canonical book order, then chapter, then verse
"""

import csv
import os
from pathlib import Path

DRB_DIR = Path(__file__).parent

SOURCES = [
    "douai-1609-annotations.tsv",
    "douai-1609-pentateuch.tsv",
    "douai-1609-historical.tsv",
    "douai-1609-wisdom.tsv",
    "douai-1609-prophets.tsv",
    "douai-1609-minor-prophets.tsv",
]

OUTPUT = DRB_DIR / "douai-1609-final.tsv"

# Canonical OT book order (DRB/Vulgate order)
BOOK_ORDER = [
    "Gn","Ex","Lv","Nm","Dt",
    "Jos","Jgs","Ru",
    "1Sam","2Sam","1Kings","2Kings",
    "1Chr","2Chr","Ezr","Neh",
    "Tb","Jdt","Est","1Mc","2Mc",
    "Jb","Ps","Prv","Eccl","Sg","Wis","Sir",
    "Is","Jer","Lam","Bar","Ez","Dn",
    "Hos","Joel","Am","Ob","Jon","Mic","Nah","Hab","Zeph","Hag","Zech","Mal",
    # NT
    "Mt","Mk","Lk","Jn","Acts",
    "Rom","1Cor","2Cor","Gal","Eph","Phil","Col",
    "1Thes","2Thes","1Tim","2Tim","Tit","Phlm","Heb",
    "Jas","1Pet","2Pet","1Jn","2Jn","3Jn","Jude","Rev",
    # Extras
    "Apc","Ps119",
]

BOOK_INDEX = {b: i for i, b in enumerate(BOOK_ORDER)}

def sort_key(row):
    book = row.get("BookAbbrev", "")
    ref = row.get("Chapter:Verse", "0:0")
    parts = ref.split(":")
    try:
        ch = int(parts[0]) if parts else 0
    except ValueError:
        ch = 0
    try:
        vs = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        vs = 0
    return (BOOK_INDEX.get(book, 9999), ch, vs)

def dedup_key(row):
    ann = row.get("Annotation", "")
    return (row.get("BookAbbrev",""), row.get("Chapter:Verse",""), ann[:50])

def load_tsv(path):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            # Normalize column names
            normalized = {}
            for k, v in row.items():
                if k:
                    normalized[k.strip()] = (v or "").strip()
            rows.append(normalized)
    return rows

def main():
    all_rows = []
    seen_keys = set()

    for src in SOURCES:
        path = DRB_DIR / src
        if not path.exists():
            print(f"  MISSING: {src}")
            continue
        rows = load_tsv(path)
        added = 0
        for row in rows:
            key = dedup_key(row)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            # Ensure all expected columns exist
            row.setdefault("BookAbbrev", "")
            row.setdefault("Chapter:Verse", "")
            row.setdefault("Annotation", "")
            row.setdefault("Source", "scan-pdf")
            all_rows.append(row)
            added += 1
        print(f"  {src}: {len(rows)} rows, {added} unique added")

    # Sort
    all_rows.sort(key=sort_key)

    # Write output
    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["BookAbbrev","Chapter:Verse","Annotation","Source"],
                                delimiter='\t', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nOutput: {OUTPUT}")
    print(f"Total rows: {len(all_rows)}")

if __name__ == "__main__":
    main()
