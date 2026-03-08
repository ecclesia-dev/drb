#!/usr/bin/env python3
"""Extract NT annotation gaps from HTML mirror and append to TSV.

These chapters use inline tooltip2 spans (not Annotations2 sections).
We extract from class="tooltip" and class="tooltipP" spans only
(NOT tooltipR which are just cross-references/citations).
"""

import re
import sys
from pathlib import Path
from collections import defaultdict

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
except ImportError:
    print("Installing beautifulsoup4...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4", "-q"])
    from bs4 import BeautifulSoup, NavigableString, Tag

_HERE = Path(__file__).parent.resolve()
_DRB_IOS = _HERE.parent / "drb-ios"
HTML_DIR = _DRB_IOS / "DouayRheims/sources/originaldouay"
TSV_PATH = _HERE / "douai-1609-annotations.tsv"

WHITESPACE_RE = re.compile(r'\s+')
# Match verse numbers like <b>1. </b> or <b>1) </b>
VERSE_BOLD_RE = re.compile(r'^\s*(\d+)[.)]\s*$')

CHAPTERS_TO_EXTRACT = [
    # (BookAbbrev, chapter, html_filename)
    ("Acts",  9,  "acts9.html"),
    ("Acts",  16, "acts16.html"),
    ("Acts",  18, "acts18.html"),
    ("Acts",  22, "acts22.html"),
    ("Acts",  24, "acts24.html"),
    ("Acts",  25, "acts25.html"),
    ("Acts",  26, "acts26.html"),
    ("Rev",   7,  "revelations7.html"),
    ("Rev",   8,  "revelations8.html"),
    ("Rev",   10, "revelations10.html"),
    ("Rev",   15, "revelations15.html"),
    ("Rev",   16, "revelations16.html"),
    ("Rev",   18, "revelations18.html"),
    ("1Cor",  16, "I_Corinth16.html"),
    ("1Pet",  1,  "I_Peter.html"),
    ("2Pet",  2,  "II_Peter2.html"),
    ("Heb",   2,  "hebrews2.html"),
    ("Heb",   3,  "hebrews3.html"),
    ("3Jn",   1,  "III_John.html"),
    ("Col",   4,  "colossians4.html"),
    ("Eph",   3,  "ephesians3.html"),
    ("Eph",   6,  "ephesians6.html"),
    ("1Thes", 3,  "I_Thessalonians3.html"),
    ("2Thes", 1,  "II_Thessalonians.html"),
    ("Jn",    7,  "john7.html"),
    ("Jn",    18, "john18.html"),
    ("Tit",   2,  "titus2.html"),
    ("Rom",   15, "romans15.html"),
]


def extract_annotations_from_tooltips(html_file):
    """
    Walk the HTML body in document order.
    Track the most recently seen verse number (from <b>N. </b> or <b>N) </b>).
    For each container span with tooltip or tooltipP class, extract the annotation.
    Skip tooltipR (cross-references only).
    Returns list of (verse_num, annotation_text).
    """
    with open(html_file, 'r', encoding='utf-8', errors='replace') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    body = soup.body or soup

    results = []
    current_verse = 0

    def walk(node):
        nonlocal current_verse
        if isinstance(node, NavigableString):
            return
        if not isinstance(node, Tag):
            return

        # Check if this is a <b> tag with just a verse number
        if node.name == 'b' and not node.get('class'):
            text = node.get_text()
            m = VERSE_BOLD_RE.match(text.strip())
            if m:
                current_verse = int(m.group(1))
                return  # Don't recurse into this b tag

        # Check if this is a container span with tooltip/tooltipP (annotation)
        classes = node.get('class', [])
        if isinstance(classes, str):
            classes = [classes]

        if node.name == 'b' and 'tooltip' in classes and 'tooltipR' not in classes:
            # This is an annotation tooltip (not a reference)
            # The annotation text is inside span.tooltip2
            tooltip_span = node.find('span', class_='tooltip2')
            if tooltip_span:
                text = tooltip_span.get_text(separator=' ')
                text = WHITESPACE_RE.sub(' ', text).strip()
                if text:
                    results.append((current_verse, text))
            return  # Don't recurse further

        # Skip tooltipR entirely (cross-references)
        if node.name == 'b' and 'tooltipR' in classes:
            return

        # Recurse into children
        for child in node.children:
            walk(child)

    walk(body)
    return results


rows_added = defaultdict(int)
files_not_found = []
zero_span_chapters = []
new_rows = []  # kept for sample display only

# Group chapters by book so we flush after each book completes
from itertools import groupby
from operator import itemgetter

for book, chapters in groupby(CHAPTERS_TO_EXTRACT, key=itemgetter(0)):
    book_rows = []
    for (b, chap, fname) in chapters:
        fpath = HTML_DIR / fname
        if not fpath.exists():
            files_not_found.append((b, chap, fname))
            continue

        annotations = extract_annotations_from_tooltips(fpath)
        if not annotations:
            zero_span_chapters.append((b, chap, fname))
            continue

        for (verse, text) in annotations:
            col2 = f"{chap}:{verse}"
            safe_text = text.replace('\t', ' ')
            book_rows.append(f"{b}\t{col2}\t{safe_text}\twebsite\n")
            rows_added[b] += 1

    # Flush immediately after each book — don't batch
    if book_rows:
        with open(TSV_PATH, 'a', encoding='utf-8') as f:
            f.writelines(book_rows)
        print(f"  [{book}] flushed {len(book_rows)} rows to disk")
        new_rows.extend(book_rows)

# Summary
print("=== Summary ===")
print(f"Total rows added: {sum(rows_added.values())}")
print("\nRows added per book:")
for book, count in sorted(rows_added.items()):
    print(f"  {book}: {count}")

if files_not_found:
    print("\nFiles NOT found (skipped):")
    for (book, chap, fname) in files_not_found:
        print(f"  {book} ch{chap} -> {fname}")
else:
    print("\nAll files found. ✓")

if zero_span_chapters:
    print("\nChapters with 0 annotations extracted:")
    for (book, chap, fname) in zero_span_chapters:
        print(f"  {book} ch{chap} -> {fname}")
else:
    print("All chapters had annotations. ✓")

# Show a sample of what was extracted
print("\n=== Sample rows (first 5) ===")
for row in new_rows[:5]:
    parts = row.strip().split('\t')
    print(f"  {parts[0]} {parts[1]}: {parts[2][:80]}...")
