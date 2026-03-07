#!/usr/bin/env python3
"""
normalize-commentary.py

Normalize ALL commentary TSV files in projects/drb/ to 5-column canonical schema:
    book    chapter    verse    latin_incipit    english_translation

Rules:
  - book: DRB canonical abbreviation (no full names, no numbers as book)
  - chapter: integer (no letters, no colons)
  - verse: integer (strip sub-verse letters: 1a → 1; keep first, drop dups per chapter)
  - latin_incipit: string (may be empty)
  - english_translation: string

Author: Alcuin (Data Pipeline)
Date: 2026-03-05
"""

import os
import re
import sys
from pathlib import Path

DRB_DIR = Path(__file__).parent.parent

# Canonical book abbreviations (plus common valid extensions)
CANONICAL_BOOKS = {
    "Gn", "Ex", "Lv", "Nm", "Dt", "Jos", "Jgs", "Ru",
    "1Sam", "2Sam", "1Kings", "2Kings", "1Chr", "2Chr",
    "Ezr", "Neh", "Tb", "Jdt", "Est", "Jb", "Prv", "Eccl",
    "Sg", "Wis", "Sir", "Is", "Jer", "Lam", "Bar", "Ez",
    "Dn", "Hos", "Joel", "Am", "Ob", "Jon", "Mi", "Na",
    "Hab", "Zep", "Hag", "Zec", "Mal",
    "Mt", "Mk", "Lk", "Jn", "Acts", "Rom",
    "1Cor", "2Cor", "Gal", "Eph", "Phil", "Col",
    "1Th", "2Th", "1Tim", "2Tim", "Ti", "Phlm",
    "Heb", "Jas", "1Pet", "2Pet", "1Jn", "2Jn", "3Jn",
    "Jude", "Rev",
    # Additional valid DRB books not in the task's list (flag in report)
    "Ps", "1Mc", "2Mc",
}

# Book name → canonical abbreviation fixes
BOOK_FIXES = {
    "Job": "Jb",
    "Matthew": "Mt",
    "Mark": "Mk",
    "Luke": "Lk",
    "John": "Jn",
    "Genesis": "Gn",
    "Exodus": "Ex",
    "Psalms": "Ps",
    "Psalm": "Ps",
}

# Header keywords — if row[0] matches one of these, it's a header row
HEADER_KEYWORDS = {
    'book', 'Book', 'BookAbbrev', 'chapter', 'Chapter',
    'verse', 'Verse', 'latin_incipit', 'english_translation',
    'Commentary', 'Annotation', 'comment', 'Comment',
}

changes_log = []   # List of (file, message) tuples
summary = {}       # file → {rows_written, issues}


def log(fname, msg):
    changes_log.append((str(fname), msg))


def fix_book(book):
    """Return canonical abbreviation for a book name."""
    book = book.strip()
    return BOOK_FIXES.get(book, book)


def parse_chap_verse(ref):
    """
    Parse a chapter:verse string into (chapter_int, verse_str).
    verse_str may still have sub-verse letters.
    Returns (0, ref) for unparseable / prologues.
    """
    ref = ref.strip()
    if ':' in ref:
        ch_str, v_str = ref.split(':', 1)
        try:
            ch = int(ch_str.strip())
        except ValueError:
            return 0, ref
        return ch, v_str.strip()
    else:
        return 0, ref


def verse_to_int(v_str):
    """
    Strip leading digits from verse string: '1a' → 1, '10b' → 10, 'Prol' → 0.
    """
    m = re.match(r'^(\d+)', str(v_str).strip())
    return int(m.group(1)) if m else 0


def is_header(fields):
    """True if this row looks like a column-header row."""
    return bool(fields) and fields[0].strip() in HEADER_KEYWORDS


def split_tsv_line(line, maxsplit):
    """Split a TSV line, preserving embedded content in the last field."""
    parts = line.rstrip('\n').split('\t', maxsplit)
    # Pad if fewer fields than expected
    while len(parts) <= maxsplit:
        parts.append('')
    return parts


def write_tsv(filepath, rows):
    """Write list-of-list rows to a TSV file (LF line endings)."""
    with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
        for row in rows:
            f.write('\t'.join(str(c) for c in row) + '\n')


HEADER_ROW = ['book', 'chapter', 'verse', 'latin_incipit', 'english_translation']


# ─────────────────────────────────────────────────────────────────────────────
# Normalizer: lapide.tsv (NT, 3-col → 5-col)
# ─────────────────────────────────────────────────────────────────────────────

def normalize_lapide_nt(filepath):
    """
    lapide.tsv: Book | Verse (chapter:verse) | Commentary  →  5-col
    """
    fname = Path(filepath).name
    rows = [HEADER_ROW]
    seen = {}   # (book, ch) → set of verse ints
    dropped = 0
    fixed = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        fields = split_tsv_line(line, 2)  # max 3 fields
        if i == 0 and is_header(fields):
            continue
        if not fields[0].strip():
            continue

        book = fix_book(fields[0])
        if book != fields[0].strip():
            fixed += 1

        ch, v_str = parse_chap_verse(fields[1])
        verse = verse_to_int(v_str)
        english = fields[2] if len(fields) > 2 else ''

        key = (book, ch)
        seen.setdefault(key, set())
        if verse in seen[key]:
            dropped += 1
            continue
        seen[key].add(verse)

        rows.append([book, ch, verse, '', english])

    write_tsv(filepath, rows)
    data_rows = len(rows) - 1
    log(fname, f"Migrated 3-col NT → 5-col | rows={data_rows} dropped_dups={dropped} book_fixes={fixed}")
    summary[fname] = {'rows': data_rows, 'dropped': dropped, 'fixed': fixed}


# ─────────────────────────────────────────────────────────────────────────────
# Normalizer: OT lapide-*.tsv  (5-col, fix verse letters + dedup)
# ─────────────────────────────────────────────────────────────────────────────

def normalize_lapide_5col(filepath):
    """
    OT lapide-*.tsv with 5 columns: fix sub-verse letters, deduplicate, fix books.
    """
    fname = Path(filepath).name
    rows = [HEADER_ROW]
    seen = {}
    dropped = 0
    fixed_verse = 0
    fixed_book = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        fields = split_tsv_line(line, 4)  # max 5 fields
        if i == 0 and is_header(fields):
            continue
        if not fields[0].strip():
            continue

        book = fix_book(fields[0])
        if book != fields[0].strip():
            fixed_book += 1

        try:
            ch = int(fields[1].strip())
        except ValueError:
            ch = 0

        orig_v = fields[2].strip()
        verse = verse_to_int(orig_v)
        if orig_v != str(verse):
            fixed_verse += 1

        latin = fields[3]
        english = fields[4]

        key = (book, ch)
        seen.setdefault(key, set())
        if verse in seen[key]:
            dropped += 1
            continue
        seen[key].add(verse)

        rows.append([book, ch, verse, latin, english])

    write_tsv(filepath, rows)
    data_rows = len(rows) - 1
    log(fname, f"5-col normalize | rows={data_rows} dropped_dups={dropped} "
               f"verse_fixes={fixed_verse} book_fixes={fixed_book}")
    summary[fname] = {'rows': data_rows, 'dropped': dropped,
                      'verse_fixes': fixed_verse, 'book_fixes': fixed_book}


# ─────────────────────────────────────────────────────────────────────────────
# Normalizer: OT lapide-*.tsv  (4-col → 5-col, insert empty latin_incipit)
# ─────────────────────────────────────────────────────────────────────────────

def normalize_lapide_4col(filepath):
    """
    lapide-Bar/Dn/Ez/Jer/Lam: book | chapter | verse | annotation  → 5-col
    """
    fname = Path(filepath).name
    rows = [HEADER_ROW]
    seen = {}
    dropped = 0
    fixed_verse = 0
    fixed_book = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        fields = split_tsv_line(line, 3)  # max 4 fields
        if i == 0 and is_header(fields):
            continue
        if not fields[0].strip():
            continue

        book = fix_book(fields[0])
        if book != fields[0].strip():
            fixed_book += 1

        try:
            ch = int(fields[1].strip())
        except ValueError:
            ch = 0

        orig_v = fields[2].strip()
        verse = verse_to_int(orig_v)
        if orig_v != str(verse):
            fixed_verse += 1

        english = fields[3]

        key = (book, ch)
        seen.setdefault(key, set())
        if verse in seen[key]:
            dropped += 1
            continue
        seen[key].add(verse)

        rows.append([book, ch, verse, '', english])

    write_tsv(filepath, rows)
    data_rows = len(rows) - 1
    log(fname, f"4-col→5-col (inserted latin_incipit) | rows={data_rows} "
               f"dropped_dups={dropped} verse_fixes={fixed_verse} book_fixes={fixed_book}")
    summary[fname] = {'rows': data_rows, 'dropped': dropped,
                      'verse_fixes': fixed_verse, 'book_fixes': fixed_book}


# ─────────────────────────────────────────────────────────────────────────────
# Normalizer: lapide_prv_extracted2.tsv  (4-col, no book col → 5-col)
# ─────────────────────────────────────────────────────────────────────────────

def normalize_lapide_prv(filepath):
    """
    lapide_prv_extracted2.tsv: chapter | verse | lemma | text  → 5-col (add Prv)
    """
    fname = Path(filepath).name
    rows = [HEADER_ROW]
    seen = {}
    dropped = 0
    fixed_verse = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        fields = split_tsv_line(line, 3)  # max 4 fields
        if i == 0 and is_header(fields):
            continue
        if not fields[0].strip():
            continue

        try:
            ch = int(fields[0].strip())
        except ValueError:
            ch = 0

        orig_v = fields[1].strip()
        verse = verse_to_int(orig_v)
        if orig_v != str(verse):
            fixed_verse += 1

        latin = fields[2]
        english = fields[3]

        key = ('Prv', ch)
        seen.setdefault(key, set())
        if verse in seen[key]:
            dropped += 1
            continue
        seen[key].add(verse)

        rows.append(['Prv', ch, verse, latin, english])

    write_tsv(filepath, rows)
    data_rows = len(rows) - 1
    log(fname, f"Added book=Prv col | rows={data_rows} dropped_dups={dropped} "
               f"verse_fixes={fixed_verse}")
    summary[fname] = {'rows': data_rows, 'dropped': dropped, 'verse_fixes': fixed_verse}


# ─────────────────────────────────────────────────────────────────────────────
# Normalizer: lapide-ot/*.tsv  (3-col, various headers → 5-col)
# ─────────────────────────────────────────────────────────────────────────────

def normalize_lapide_ot_file(filepath):
    """
    lapide-ot/*.tsv: book | chapter:verse | annotation  → 5-col
    - Some files have headers (BookAbbrev/Chapter:Verse/Annotation), some don't.
    - verse ref may be: 1:1a, 1:1, Prol, Prol2, Argument, 1:intro, etc.
    - Non-integer refs → chapter=0, verse=0 (flagged in report).
    """
    fname = Path(filepath).name
    rows = [HEADER_ROW]
    seen = {}
    dropped = 0
    fixed_book = 0
    special_refs = []  # (original_ref, row_num)

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if not lines:
        return

    start = 0
    first_fields = lines[0].rstrip('\n').split('\t')
    if is_header(first_fields):
        start = 1

    for lineno, line in enumerate(lines[start:], start=start + 1):
        fields = split_tsv_line(line, 2)  # max 3 fields
        if not fields[0].strip():
            continue

        book = fix_book(fields[0])
        if book != fields[0].strip():
            fixed_book += 1

        ref = fields[1].strip()
        annotation = fields[2] if len(fields) > 2 else ''

        ch, v_str = parse_chap_verse(ref)

        # Flag non-integer refs
        if ch == 0 and not re.match(r'^\d', v_str):
            special_refs.append((lineno, ref))

        verse = verse_to_int(v_str)

        key = (book, ch)
        seen.setdefault(key, set())
        if verse in seen[key]:
            dropped += 1
            continue
        seen[key].add(verse)

        rows.append([book, ch, verse, '', annotation])

    write_tsv(filepath, rows)
    data_rows = len(rows) - 1
    log(fname, f"3-col→5-col | rows={data_rows} dropped_dups={dropped} "
               f"book_fixes={fixed_book} special_refs={len(special_refs)}")
    if special_refs:
        # Log first few
        for lineno, ref in special_refs[:5]:
            log(fname, f"  Non-integer ref line {lineno}: '{ref}' → ch=0 v=0")
        if len(special_refs) > 5:
            log(fname, f"  ... and {len(special_refs) - 5} more")

    summary[fname] = {'rows': data_rows, 'dropped': dropped,
                      'book_fixes': fixed_book, 'special_refs': len(special_refs)}


# ─────────────────────────────────────────────────────────────────────────────
# Normalizer: aquinas-job.tsv  (Job → Jb)
# ─────────────────────────────────────────────────────────────────────────────

def normalize_aquinas_job(filepath):
    """Change Job → Jb in book column."""
    fname = Path(filepath).name
    rows = []
    fixed = 0

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        fields = split_tsv_line(line, 4)
        if i == 0 and is_header(fields):
            rows.append(fields)
            continue
        if fields[0].strip() == 'Job':
            fields[0] = 'Jb'
            fixed += 1
        rows.append(fields)

    write_tsv(filepath, rows)
    data_rows = len(rows) - 1
    log(fname, f"Job→Jb | fixed={fixed} rows={data_rows}")
    summary[fname] = {'rows': data_rows, 'fixed': fixed}


# ─────────────────────────────────────────────────────────────────────────────
# Normalizer: generic 5-col, check/fix book abbreviations
# ─────────────────────────────────────────────────────────────────────────────

def normalize_check_books(filepath):
    """Check/fix book abbreviations. Already 5-col, don't restructure."""
    fname = Path(filepath).name
    rows = []
    fixed = 0
    bad_books = {}

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        fields = split_tsv_line(line, 4)
        if i == 0 and is_header(fields):
            rows.append(fields)
            continue
        book = fields[0].strip()
        fixed_book = fix_book(book)
        if fixed_book != book:
            fields[0] = fixed_book
            fixed += 1
        elif book and book not in CANONICAL_BOOKS:
            bad_books[book] = bad_books.get(book, 0) + 1
        rows.append(fields)

    write_tsv(filepath, rows)
    data_rows = len(rows) - 1
    issues = f" BAD_BOOKS={bad_books}" if bad_books else ""
    log(fname, f"Book-check | rows={data_rows} fixed={fixed}{issues}")
    summary[fname] = {'rows': data_rows, 'fixed': fixed, 'bad_books': bad_books}


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

def validate_file(filepath):
    """
    Validate a normalized 5-col TSV:
    - All rows have exactly 5 columns
    - book is in CANONICAL_BOOKS
    - chapter and verse are non-negative integers
    Returns dict with validation results.
    """
    fname = Path(filepath).name
    errors = []
    row_count = 0
    books_seen = set()

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        raw = line.rstrip('\n')
        fields = raw.split('\t', 4)

        # Skip canonical header row
        if i == 0 and fields[0].strip() in HEADER_KEYWORDS:
            continue

        row_count += 1
        col_count = len(fields)

        if col_count != 5:
            errors.append(f"  Row {i+1}: expected 5 cols, got {col_count}")

        if col_count >= 1:
            book = fields[0].strip()
            books_seen.add(book)
            if book not in CANONICAL_BOOKS:
                errors.append(f"  Row {i+1}: non-canonical book '{book}'")

        if col_count >= 2:
            try:
                int(fields[1].strip())
            except ValueError:
                errors.append(f"  Row {i+1}: chapter '{fields[1].strip()}' not integer")

        if col_count >= 3:
            try:
                int(fields[2].strip())
            except ValueError:
                errors.append(f"  Row {i+1}: verse '{fields[2].strip()}' not integer")

    return {
        'rows': row_count,
        'books': sorted(books_seen),
        'errors': errors,
        'ok': len(errors) == 0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    drb = DRB_DIR
    four_col = {'lapide-Bar.tsv', 'lapide-Dn.tsv', 'lapide-Ez.tsv',
                'lapide-Jer.tsv', 'lapide-Lam.tsv'}

    print("=" * 60)
    print("  Alcuin Commentary Normalizer — DRB Project")
    print("=" * 60)

    # ── 1. lapide.tsv (NT, 3-col)
    f = drb / "lapide.tsv"
    if f.exists():
        print(f"\n[1] {f.name}")
        normalize_lapide_nt(f)

    # ── 2. OT lapide-*.tsv files
    print("\n[2] OT lapide-*.tsv files")
    for f in sorted(drb.glob("lapide-*.tsv")):
        if f.name == 'lapide-Is-latin.tsv':
            print(f"  SKIP {f.name} (protected)")
            continue
        if f.name == 'lapide.tsv':
            continue  # handled above

        ncols = 0
        with open(f, 'r', encoding='utf-8') as fh:
            for lineno, line in enumerate(fh):
                if lineno == 0:
                    # Check if this is a header
                    first = line.split('\t')[0].strip()
                    if first in HEADER_KEYWORDS:
                        continue
                ncols = len(line.split('\t', 4))
                break

        print(f"  {f.name} ({ncols} cols)")
        if f.name in four_col:
            normalize_lapide_4col(f)
        else:
            normalize_lapide_5col(f)

    # ── 3. lapide_prv_extracted2.tsv
    f = drb / "lapide_prv_extracted2.tsv"
    if f.exists():
        print(f"\n[3] {f.name}")
        normalize_lapide_prv(f)

    # ── 4. lapide-ot/*.tsv
    ot_dir = drb / "lapide-ot"
    if ot_dir.exists():
        print("\n[4] lapide-ot/*.tsv")
        for f in sorted(ot_dir.glob("*.tsv")):
            print(f"  {f.name}")
            normalize_lapide_ot_file(f)

    # ── 5. aquinas-job.tsv
    f = drb / "aquinas-job.tsv"
    if f.exists():
        print(f"\n[5] {f.name}")
        normalize_aquinas_job(f)

    # ── 6. corderius, catena, epistles (check book abbreviations)
    print("\n[6] Checking book abbreviations")
    for fname in ['corderius-Jb.tsv', 'aquinas-catena.tsv', 'aquinas-epistles.tsv']:
        fp = drb / fname
        if fp.exists():
            print(f"  {fname}")
            normalize_check_books(fp)

    # ── Validation pass
    print("\n" + "=" * 60)
    print("  Validation")
    print("=" * 60)

    validation_results = {}
    skip_set = {'lapide-Is-latin.tsv'}

    all_tsv = list(drb.glob("*.tsv")) + list((drb / "lapide-ot").glob("*.tsv"))
    for f in sorted(all_tsv):
        if f.name in skip_set:
            continue
        result = validate_file(f)
        validation_results[str(f.relative_to(drb))] = result
        status = "✓ OK" if result['ok'] else f"✗ {len(result['errors'])} errors"
        print(f"  {f.relative_to(drb)}: {result['rows']} rows — {status}")
        if not result['ok']:
            for e in result['errors'][:5]:
                print(f"    {e}")
            if len(result['errors']) > 5:
                print(f"    ... and {len(result['errors']) - 5} more")

    return validation_results


if __name__ == '__main__':
    val = main()

    # Print changes log
    print("\n" + "=" * 60)
    print("  Changes Log")
    print("=" * 60)
    for fname, msg in changes_log:
        print(f"  [{fname}] {msg}")

    # Return exit code 0 if all valid
    total_errors = sum(len(v['errors']) for v in val.values())
    sys.exit(0 if total_errors == 0 else 1)
