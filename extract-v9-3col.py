#!/usr/bin/env python3
"""
extract-v9-3col.py

Extract a 3-column TSV (BookAbbrev, Chapter:Verse, Annotation) from the
5-column v9 Douai 1609 source file.

v9 schema: BookAbbrev | Chapter:Verse | VerseQuote | Commentary | Status

Rows where Commentary is empty are skipped.

Usage:
    python3 extract-v9-3col.py <source.tsv> [output.tsv]

If output.tsv is omitted, writes to douai-1609-v9-3col.tsv in the same
directory as this script.
"""

import csv
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <source.tsv> [output.tsv]", file=sys.stderr)
        sys.exit(1)

    src = Path(sys.argv[1])
    if len(sys.argv) >= 3:
        dst = Path(sys.argv[2])
    else:
        dst = Path(__file__).parent / "douai-1609-v9-3col.tsv"

    rows_read = 0
    rows_written = 0
    rows_skipped = 0

    with src.open(newline="", encoding="utf-8") as infile, \
         dst.open("w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile, delimiter="\t")
        writer = csv.writer(outfile, delimiter="\t", lineterminator="\n",
                            quoting=csv.QUOTE_MINIMAL)

        # Write header
        writer.writerow(["BookAbbrev", "Chapter:Verse", "Annotation"])

        for row in reader:
            rows_read += 1
            commentary = row.get("Commentary", "").strip()
            if not commentary:
                rows_skipped += 1
                continue
            writer.writerow([
                row["BookAbbrev"].strip(),
                row["Chapter:Verse"].strip(),
                commentary,
            ])
            rows_written += 1

    print(f"Source rows read    : {rows_read}")
    print(f"Rows with commentary: {rows_written}")
    print(f"Rows skipped (empty): {rows_skipped}")
    print(f"Output written to   : {dst}")


if __name__ == "__main__":
    main()
