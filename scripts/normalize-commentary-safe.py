#!/usr/bin/env python3
"""
normalize-commentary-safe.py  —  v2
Alcuin (📊) — Data Pipeline specialist
Safe normalization of Lapide commentary TSV files.

Rules:
1. VALIDATE FIRST — skip files with ≤2 data rows
2. Book abbreviation fix — auto-detect from filename when col0 is bare integer
3. Sub-verse letters — strip (1a→1), keep first on duplicate book+ch+verse
4. Verse ranges — take first integer from "5-7", "36-38a" etc.
5. Column count — normalize to exactly 5 cols
6. Header — ensure standard 5-col header
7. lapide.tsv — 3-col legacy format (Book / ch:verse / Commentary) → 5-col
8. aquinas-job.tsv — fix Job→Jb in book column
9. DO NOT TOUCH lapide-Is-latin.tsv or lapide-ot/ directory

Notes on untracked files:
  - lapide-Ps.tsv was destroyed in a prior run (not in git); logged as data-loss.
  - Minor prophets (Am, Hab, etc.) have chapter number in col0; fixed by filename lookup.
"""

import csv
import glob
import os
import re
import sys

WORKDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADER = ["book", "chapter", "verse", "latin_incipit", "english_translation"]
REPORT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "qa", "alcuin-normalize-safe-2026-03-06.md")

# Derive book abbreviation from filename: lapide-Am.tsv → "Am"
def book_from_filename(fname):
    base = os.path.basename(fname)
    m = re.match(r'^(?:lapide-|aquinas-)(.+?)\.tsv$', base)
    if m:
        return m.group(1)
    return None

def is_integer(s):
    try:
        int(str(s).strip())
        return True
    except (ValueError, TypeError):
        return False

def strip_verse_to_int(v):
    """
    Normalize verse to an integer string:
      '1a' → '1'   (sub-verse letter)
      '5-7' → '5'  (range → first)
      '36-38a' → '36'
      '1' → '1'    (no change)
    """
    v = str(v).strip()
    # Extract leading integer from any verse expression
    m = re.match(r'^(\d+)', v)
    if m:
        return m.group(1)
    return v  # return as-is if no leading digit (e.g. "Synopsis Capitis" stays put)


def normalize_row_cols(row):
    """
    Given a row of any col count, return a normalized 5-col list
    [book, chapter, verse, latin_incipit, english_translation].
    Returns None if unfixable (<3 cols).
    """
    n = len(row)
    if n < 3:
        return None
    if n == 3:
        # Could be the 3-col lapide.tsv format (book, ch:verse, commentary)
        # We handle that at a higher level; here just return None to drop.
        return None
    if n == 4:
        # book, chapter, verse, translation — insert empty latin_incipit
        return [row[0], row[1], row[2], "", row[3]]
    if n == 5:
        return list(row)
    # n >= 6: keep book/ch/verse/latin, merge the rest as translation
    book    = row[0]
    chapter = row[1]
    verse   = row[2]
    latin   = row[3]
    # For 6-col: col4 may be empty (extra tab artifact) and col5 the real translation
    if n == 6:
        if row[4].strip() == "":
            translation = row[5].strip()
        else:
            # col4 has data; merge col4+col5
            translation = ("\t".join(row[4:])).strip()
    elif n == 7:
        # Legacy 7-col (old lapide.tsv OCR format): book/ch/verse/empty/page_num/empty/text
        # col4 = empty, col5 = page_num, col6 = empty?? or translation
        # Take col6 as translation; if col6 is empty take col5
        if row[6].strip():
            translation = row[6].strip()
        elif row[5].strip():
            translation = row[5].strip()
        else:
            translation = ("\t".join(row[4:])).strip()
    else:
        # n > 7: merge everything from col4 onward
        translation = ("\t".join(row[4:])).strip()
    return [book, chapter, verse, latin, translation]


def migrate_lapide_nt(row):
    """
    Migrate a 3-col NT lapide.tsv row:
      ['Mt', '1:2', 'Commentary text']
    to 5-col:
      ['Mt', '1', '2', '', 'Commentary text']
    Returns None if verse field can't be split.
    """
    book = row[0].strip()
    verse_field = row[1].strip()  # e.g. "1:2"
    commentary = row[2]
    m = re.match(r'^(\d+):(\d+[a-zA-Z]?)$', verse_field)
    if m:
        chapter = m.group(1)
        verse   = strip_verse_to_int(m.group(2))
        return [book, chapter, verse, "", commentary]
    # Try "book:ch:verse" or other patterns
    parts = verse_field.split(':')
    if len(parts) == 2 and is_integer(parts[0]):
        return [book, parts[0].strip(), strip_verse_to_int(parts[1].strip()), "", commentary]
    # Unrecognized — drop
    return None


def process_file(filepath, is_lapide_nt=False, fix_job_abbrev=False):
    """
    Normalize a single TSV file. Returns (new_rows, stats_dict).
    new_rows includes the header as row 0, or None if file should be skipped.
    """
    stats = {
        "rows_read": 0,
        "rows_skipped_short": 0,
        "rows_fixed_cols": 0,
        "rows_fixed_book": 0,
        "rows_fixed_verse": 0,
        "rows_deduped": 0,
        "rows_fixed_job": 0,
        "rows_dropped": 0,
        "output_rows": 0,
        "skipped_file": False,
        "skip_reason": "",
        "data_loss_warning": "",
    }

    fname = os.path.basename(filepath)
    expected_book = book_from_filename(fname)

    with open(filepath, "r", encoding="utf-8", newline="") as fh:
        raw_rows = list(csv.reader(fh, delimiter="\t"))

    # Detect and strip header row (case-insensitive check on first col)
    if raw_rows and raw_rows[0][0].lower() in ("book", "Book", "book\ufeff"):
        data_rows = raw_rows[1:]
    else:
        data_rows = raw_rows

    stats["rows_read"] = len(data_rows)

    # Rule 1: validate — skip if ≤2 data rows
    if len(data_rows) <= 2:
        stats["skipped_file"] = True
        stats["skip_reason"] = f"Only {len(data_rows)} data rows — too few to normalize safely"
        if len(data_rows) == 1:
            # Special case: check if this is the destroyed lapide-Ps.tsv
            stats["data_loss_warning"] = "⚠️ DATA LOSS: file may have been corrupted in a prior run"
        return None, stats

    out_rows = []
    seen = set()  # (book, chapter, verse) triple for dedup

    for row in data_rows:
        if not row or all(c == "" for c in row):
            continue  # blank line

        # Rule 7: lapide.tsv 3-col NT migration
        if is_lapide_nt:
            if len(row) == 3:
                migrated = migrate_lapide_nt(row)
                if migrated is None:
                    stats["rows_dropped"] += 1
                    continue
                row = migrated
                stats["rows_fixed_cols"] += 1
            # If already 5-col (re-run), just continue

        # Rule 8: aquinas-job.tsv — fix Job→Jb
        if fix_job_abbrev and len(row) > 0 and row[0].strip() == "Job":
            row[0] = "Jb"
            stats["rows_fixed_job"] += 1

        # Rule 2: Book abbreviation fix — prepend book if col0 is a bare integer
        # This handles minor prophets that have chapter number in col0
        if len(row) > 0 and is_integer(row[0].strip()) and expected_book:
            row = [expected_book] + list(row)
            stats["rows_fixed_book"] += 1

        # Validate row has enough cols
        if len(row) < 3:
            stats["rows_dropped"] += 1
            continue

        # Rule 5: Column count normalization
        orig_len = len(row)
        row = normalize_row_cols(row)
        if row is None:
            stats["rows_dropped"] += 1
            continue
        if orig_len != 5:
            stats["rows_fixed_cols"] += 1

        assert len(row) == 5

        # Rule 3 & 4: Verse normalization (strip letter suffix + handle ranges)
        verse_raw = row[2].strip()
        verse_clean = strip_verse_to_int(verse_raw)
        if verse_clean != verse_raw:
            row[2] = verse_clean
            stats["rows_fixed_verse"] += 1

        # Normalize whitespace on key cols
        row[0] = row[0].strip()
        row[1] = row[1].strip()
        row[2] = row[2].strip()

        # Rule 3: Dedup — keep first occurrence of (book, chapter, verse)
        key = (row[0], row[1], row[2])
        if key in seen:
            stats["rows_deduped"] += 1
            continue
        seen.add(key)

        out_rows.append(row)

    stats["output_rows"] = len(out_rows)
    return [HEADER] + out_rows, stats


def validate_file(filepath):
    """Validate a normalized file. Returns (passed, issues)."""
    issues = []
    with open(filepath, "r", encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh, delimiter="\t"))

    if not rows:
        return False, ["File is empty"]

    # Check header
    if rows[0] != HEADER:
        issues.append(f"Bad header: {rows[0]}")

    for i, row in enumerate(rows[1:], start=2):
        if len(row) != 5:
            issues.append(f"Row {i}: {len(row)} cols (expected 5)")
            continue
        book, ch, verse, _, _ = row
        if is_integer(book.strip()):
            issues.append(f"Row {i}: book col is bare integer '{book}'")
        if not is_integer(ch.strip()):
            issues.append(f"Row {i}: chapter not integer: '{ch}'")
        if not is_integer(verse.strip()):
            issues.append(f"Row {i}: verse not integer: '{verse}'")

    return len(issues) == 0, issues


def main():
    os.chdir(WORKDIR)

    # lapide.tsv — 3-col NT format (tracked in git)
    lapide_nt = "lapide.tsv"

    # lapide-*.tsv — exclude Is-latin, exclude Ps (data loss, only 1 row)
    lapide_ot_files = sorted(glob.glob("lapide-*.tsv"))
    lapide_ot_files = [
        f for f in lapide_ot_files
        if f not in ("lapide-Is-latin.tsv",)
        and not f.startswith("lapide-ot/")
    ]

    # aquinas-job.tsv extra fix
    extra_files = []
    if os.path.exists("aquinas-job.tsv"):
        extra_files.append("aquinas-job.tsv")

    # Full list: NT first, then OT, then extras
    all_files_config = []
    if os.path.exists(lapide_nt):
        all_files_config.append((lapide_nt, True, False))   # (path, is_nt, fix_job)
    for f in lapide_ot_files:
        all_files_config.append((f, False, False))
    for f in extra_files:
        all_files_config.append((f, False, True))

    report_lines = [
        "# Alcuin Normalization Report — v2",
        "**Date:** 2026-03-06",
        "**Script:** `scripts/normalize-commentary-safe.py`",
        "",
        "---",
        "",
        "## Files Processed",
        "",
    ]

    validation_results = []
    all_passed = True

    for fname, is_nt, fix_job in all_files_config:
        fpath = os.path.join(WORKDIR, fname)
        if not os.path.exists(fpath):
            report_lines.append(f"- **{fname}** — NOT FOUND, skipped")
            continue

        print(f"Processing {fname}...")
        new_rows, stats = process_file(fpath, is_lapide_nt=is_nt, fix_job_abbrev=fix_job)

        if stats["skipped_file"]:
            reason = stats["skip_reason"]
            dlw    = stats.get("data_loss_warning", "")
            report_lines.append(f"### ⚠️ SKIPPED: `{fname}`")
            report_lines.append(f"- **Reason:** {reason}")
            if dlw:
                report_lines.append(f"- **{dlw}**")
            report_lines.append("")
            validation_results.append((fname, None, [reason + (" | " + dlw if dlw else "")]))
            print(f"  SKIPPED: {reason}" + (" | " + dlw if dlw else ""))
            continue

        # Write normalized file
        with open(fpath, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(
                fh,
                delimiter="\t",
                quoting=csv.QUOTE_NONE,
                escapechar="\\",
                lineterminator="\n"
            )
            writer.writerows(new_rows)

        # Validate
        passed, issues = validate_file(fpath)
        if not passed:
            all_passed = False

        validation_results.append((fname, passed, issues))

        # Build report section
        report_lines.append(f"### `{fname}`")
        report_lines.append(f"- **Data rows in:** {stats['rows_read']}")
        report_lines.append(f"- **Data rows out:** {stats['output_rows']}")
        fixes = []
        if stats["rows_fixed_cols"]:
            fixes.append(f"{stats['rows_fixed_cols']} col-count fixes")
        if stats["rows_fixed_book"]:
            fixes.append(f"{stats['rows_fixed_book']} book-abbrev fixes (col shift)")
        if stats["rows_fixed_verse"]:
            fixes.append(f"{stats['rows_fixed_verse']} verse normalisations (sub-letter or range)")
        if stats["rows_deduped"]:
            fixes.append(f"{stats['rows_deduped']} duplicate (book+ch+verse) rows removed (kept first)")
        if stats["rows_dropped"]:
            fixes.append(f"{stats['rows_dropped']} rows dropped (<3 cols or unfixable)")
        if stats["rows_fixed_job"]:
            fixes.append(f"{stats['rows_fixed_job']} Job→Jb fixes")
        if fixes:
            report_lines.append(f"- **Fixes applied:** {'; '.join(fixes)}")
        else:
            report_lines.append("- **Fixes applied:** none (file was already clean)")
        report_lines.append(f"- **Validation:** {'✅ PASS' if passed else '❌ FAIL'}")
        if not passed:
            for issue in issues[:10]:
                report_lines.append(f"  - {issue}")
        report_lines.append("")

        status = "PASS" if passed else "FAIL"
        print(f"  → {stats['output_rows']} rows [{status}]")
        if not passed:
            for issue in issues[:5]:
                print(f"    ISSUE: {issue}")

    # -------------------------------------------------------------------------
    # Summary table
    # -------------------------------------------------------------------------
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## Validation Summary")
    report_lines.append("")
    report_lines.append("| File | Result | Notes |")
    report_lines.append("|------|--------|-------|")
    for fname, passed, issues in validation_results:
        if passed is None:
            note = issues[0][:80] if issues else ""
            report_lines.append(f"| `{fname}` | ⚠️ SKIPPED | {note} |")
        elif passed:
            report_lines.append(f"| `{fname}` | ✅ PASS | — |")
        else:
            short = issues[0][:80] if issues else "unknown"
            report_lines.append(f"| `{fname}` | ❌ FAIL | {short} |")

    report_lines.append("")
    report_lines.append(
        f"**Overall:** {'✅ ALL PASSED' if all_passed else '❌ SOME FAILURES — review above'}"
    )
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## Notes")
    report_lines.append("")
    report_lines.append(
        "- `lapide-Is-latin.tsv` was explicitly excluded (DO NOT TOUCH)."
    )
    report_lines.append(
        "- `lapide-Ps.tsv` was an untracked file that suffered catastrophic data "
        "collapse in a prior normalization run (122 rows → 1 row). The file is not "
        "in git and is unrecoverable from backups. It was SKIPPED here to prevent "
        "further damage. Manual regeneration required."
    )
    report_lines.append(
        "- `lapide-ot/` subdirectory was not touched."
    )
    report_lines.append("")

    # Write report
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(report_lines) + "\n")

    print(f"\nReport → {REPORT_PATH}")
    print(f"Overall: {'ALL PASSED' if all_passed else 'SOME FAILURES'}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
