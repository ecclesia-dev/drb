#!/usr/bin/env python3
"""
Parse Catena Aurea djvu.txt OCR files from Archive.org.
Converts to TSV: BookAbbrev\tChapter:Verse\tAnnotation

Volume mapping:
- V1: Matthew Ch.1-14 (approx)
- V2: Matthew Ch.15-28
- V3: Mark (complete)
- V4: Luke Ch.1-12 (approx)
- V5: Luke Ch.13-24
- V6: John (complete)
"""

import re
import os
import sys

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = "/tmp/catena-raw"
OUTPUT_FILE = os.path.join(WORKSPACE, "aquinas-catena.tsv")

# Volume → (book_abbrev, vol_suffix)
VOLUMES = [
    ("V1", "Mt"),
    ("V2", "Mt"),
    ("V3", "Mk"),
    ("V4", "Lk"),
    ("V5", "Lk"),
    ("V6", "Jn"),
]

# Roman numeral converter
ROMAN_MAP = {
    'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7, 'viii': 8,
    'ix': 9, 'x': 10, 'xi': 11, 'xii': 12, 'xiii': 13, 'xiv': 14, 'xv': 15,
    'xvi': 16, 'xvii': 17, 'xviii': 18, 'xix': 19, 'xx': 20, 'xxi': 21,
    'xxii': 22, 'xxiii': 23, 'xxiv': 24, 'xxv': 25, 'xxvi': 26, 'xxvii': 27,
    'xxviii': 28
}

def roman_to_int(s):
    s = s.lower().strip().rstrip('.')
    return ROMAN_MAP.get(s, 0)

def parse_verse_range(ver_str):
    """
    Parse verse range strings like:
    "1" → [1]
    "1, 2" → [1, 2]
    "8 — 11" → [8, 9, 10, 11]
    "7 10" → [7, 8, 9, 10]
    "1 , 2" → [1, 2]
    "16" → [16]
    """
    # Normalize
    ver_str = ver_str.strip().rstrip('.')
    
    # Range with dash or em-dash
    m = re.match(r'^(\d+)\s*[—\-–]\s*(\d+)$', ver_str)
    if m:
        v1, v2 = int(m.group(1)), int(m.group(2))
        return list(range(v1, v2 + 1))
    
    # Range with space (like "7 10")
    m = re.match(r'^(\d+)\s+(\d+)$', ver_str)
    if m:
        v1, v2 = int(m.group(1)), int(m.group(2))
        if v2 > v1:
            return list(range(v1, v2 + 1))
        else:
            return [v1]
    
    # Multiple with comma
    if ',' in ver_str:
        parts = re.split(r'[,\s]+', ver_str)
        verses = []
        for p in parts:
            p = p.strip()
            if p.isdigit():
                verses.append(int(p))
        return verses if verses else [1]
    
    # Single number
    m = re.match(r'^(\d+)$', ver_str)
    if m:
        return [int(m.group(1))]
    
    return []

def is_header_line(line):
    """Check if this is a running header/footer line to skip."""
    line = line.strip()
    # Digitized by Google
    if 'digitized by' in line.lower() or 'google' in line.lower():
        return True
    # Running header: "ST. MATTHEW." or "GOSPEL ACCORDING TO ST. MATTHEW."
    if re.match(r'^(ST\.\s+MATTHEW|GOSPEL ACCORDING TO|GOSPEL OF ST\.|ST\.\s+MARK|ST\.\s+LUKE|ST\.\s+JOHN)', line, re.I):
        return True
    # Pure page number
    if re.match(r'^\d+\s*$', line):
        return True
    # "VOL. i. c" type lines
    if re.match(r'^VOL\.\s+[ivxIVX]+', line):
        return True
    # Empty
    if not line:
        return True
    return False

def classify_line(line):
    """
    Returns: ('chapter', num), ('verse', [v1, v2, ...]), ('skip', None), or ('text', line)
    """
    stripped = line.strip()
    
    if is_header_line(stripped):
        return ('skip', None)
    
    # Chapter header: "CHAP. I.", "CHAP. II.", "CHAP. III." etc.
    # Also variants: "CHAP. n.", "CHAP. Illr" (OCR errors)
    m = re.match(r'^CHAP\.\s+([IVXivx]+)\.?\s*$', stripped)
    if m:
        n = roman_to_int(m.group(1))
        if n > 0:
            return ('chapter', n)
        return ('skip', None)
    
    # Verse header: "VER. 1." or "VER. 1, 2." or "VER. 8 — 11." etc.
    # Sometimes: "VER. 1 , 2 . GOSPEL ACCORDING TO ST. MATTHEW."
    m = re.match(r'^VER\.\s+([\d\s,—\-–]+?)\.?\s*(GOSPEL|ST\.|$)', stripped)
    if m:
        ver_part = m.group(1).strip()
        verses = parse_verse_range(ver_part)
        if verses:
            return ('verse', verses)
        return ('skip', None)
    
    return ('text', stripped)

def clean_commentary(text):
    """Clean and normalize commentary text."""
    # Remove footnote markers (single letters at start, superscripts)
    # Remove page artifact numbers
    text = re.sub(r'\b\d{2,3}\b(?=\s+[A-Z])', '', text)  # page numbers in text
    # Remove Digitized by artifacts
    text = re.sub(r'Digitized by [A-Za-z]+', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove lone letters at end (OCR footnote artifacts)
    text = re.sub(r'\s+[a-z]\s*$', '', text)
    # Remove empty brackets
    text = re.sub(r'\[\s*\]', '', text)
    return text

def is_gem(text):
    """Heuristic: mark especially significant passages."""
    gem_phrases = [
        'God became man', 'Word was made flesh', 'incarnation',
        'mother of god', 'ever-virgin', 'resurrection of',
        'blessed trinity', 'hypostatic union', 'real presence',
        'transubstantiation', 'eternal generation',
        'mystical body', 'baptism regenerates',
        'primacy of peter', 'keys of the kingdom',
        'judge the living and the dead',
    ]
    tl = text.lower()
    for p in gem_phrases:
        if p in tl and len(text) > 300:
            return True
    return False

def parse_volume(filepath, book_abbrev):
    """Parse a single djvu.txt file, return list of (book, ch:v, annotation)."""
    print(f"  Parsing {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    
    results = []
    
    # State
    current_chapter = 0
    current_verses = []
    current_text_lines = []
    last_chapter_seen = 0  # Track chapter transitions
    
    def flush():
        """Flush current verse commentary to results."""
        if current_verses and current_text_lines:
            commentary = ' '.join(current_text_lines)
            commentary = clean_commentary(commentary)
            if len(commentary) > 50:  # Skip trivial
                if is_gem(commentary):
                    commentary += ' # GEM'
                for v in current_verses:
                    results.append((book_abbrev, f"{current_chapter}:{v}", commentary))
    
    for line in lines:
        kind, value = classify_line(line)
        
        if kind == 'skip':
            continue
        
        elif kind == 'chapter':
            ch_num = value
            # Only register a chapter change when we see a NEW chapter number
            if ch_num != current_chapter:
                if ch_num > current_chapter or ch_num == 1:
                    # Flush current verse
                    flush()
                    current_chapter = ch_num
                    current_verses = [1]  # Default to verse 1
                    current_text_lines = []
                    last_chapter_seen = ch_num
                    print(f"    Chapter {ch_num}")
        
        elif kind == 'verse':
            verses = value
            # Only register a verse change if verses actually changed
            if verses != current_verses:
                flush()
                current_verses = verses
                current_text_lines = []
        
        elif kind == 'text':
            # Skip very short lines (likely artifacts)
            if len(value) > 3:
                current_text_lines.append(value)
    
    # Final flush
    flush()
    
    print(f"    → {len(results)} verse entries")
    return results

def deduplicate_verses(rows):
    """Merge duplicate verse entries (can happen when same verse appears in two volumes)."""
    seen = {}
    deduped = []
    for (book, ref, ann) in rows:
        key = (book, ref)
        if key not in seen:
            seen[key] = True
            deduped.append((book, ref, ann))
        else:
            # Append additional commentary
            pass  # For now, keep first occurrence
    return deduped

def main():
    print("=== Catena Aurea Parser ===")
    print(f"Input dir: {INPUT_DIR}")
    print(f"Output: {OUTPUT_FILE}")
    
    all_rows = []
    
    for (vol_suffix, book_abbrev) in VOLUMES:
        filepath = os.path.join(INPUT_DIR, f"vol{vol_suffix}.txt")
        if not os.path.exists(filepath):
            print(f"WARNING: {filepath} not found, skipping")
            continue
        
        print(f"\nVolume {vol_suffix} → {book_abbrev}")
        rows = parse_volume(filepath, book_abbrev)
        all_rows.extend(rows)
        
        # Write after each volume
        print(f"  Cumulative rows: {len(all_rows)}")
    
    # Deduplicate
    all_rows = deduplicate_verses(all_rows)
    
    # Sort by book/chapter/verse
    book_order = {'Mt': 0, 'Mk': 1, 'Lk': 2, 'Jn': 3}
    def sort_key(row):
        book, ref, _ = row
        ch, v = ref.split(':')
        return (book_order.get(book, 99), int(ch), int(v))
    
    all_rows.sort(key=sort_key)
    
    # Write output
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("Book\tVerse\tCommentary\n")
        for (book, ref, ann) in all_rows:
            ann_clean = ann.replace('\t', ' ').replace('\n', ' ')
            f.write(f"{book}\t{ref}\t{ann_clean}\n")
    
    print(f"\n=== DONE: {len(all_rows)} rows → {OUTPUT_FILE} ===")
    
    # Stats
    from collections import Counter
    book_counts = Counter(row[0] for row in all_rows)
    for book in ['Mt', 'Mk', 'Lk', 'Jn']:
        print(f"  {book}: {book_counts.get(book, 0)} verses")

if __name__ == '__main__':
    main()
