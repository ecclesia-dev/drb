#!/usr/bin/env python3
"""
Scrape Aquinas Catena Aurea from CCEL.
Outputs TSV: BookAbbrev\tChapter:Verse\tAnnotation
"""

import requests
import re
import time
import os
from bs4 import BeautifulSoup

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(WORKSPACE, "aquinas-catena.tsv")

# Roman numerals map
ROMAN = {
    'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7, 'viii': 8,
    'ix': 9, 'x': 10, 'xi': 11, 'xii': 12, 'xiii': 13, 'xiv': 14, 'xv': 15,
    'xvi': 16, 'xvii': 17, 'xviii': 18, 'xix': 19, 'xx': 20, 'xxi': 21,
    'xxii': 22, 'xxiii': 23, 'xxiv': 24, 'xxv': 25, 'xxvi': 26, 'xxvii': 27,
    'xxviii': 28
}

# Gospel books: (ccel_book_id, book_abbrev, num_chapters)
GOSPELS = [
    ('catena1', 'Mt', 28),
    ('catena2', 'Mk', 16),
    ('catena3', 'Lk', 24),
    ('catena4', 'Jn', 21),
]

def roman_to_int(s):
    return ROMAN.get(s.lower(), 0)

def int_to_roman(n):
    for r, v in ROMAN.items():
        if v == n:
            return r
    return None

def fetch_chapter(book_id, chapter_num):
    """Fetch a chapter from CCEL."""
    roman = int_to_roman(chapter_num)
    if not roman:
        print(f"  Cannot convert {chapter_num} to Roman numeral")
        return None
    url = f"https://www.ccel.org/ccel/aquinas/{book_id}.ii.{roman}.html"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            return resp.text
        else:
            print(f"  HTTP {resp.status_code} for {url}")
            return None
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None

def clean_text(text):
    """Clean text for TSV output."""
    # Remove multiple spaces/newlines
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove tab chars (TSV safety)
    text = text.replace('\t', ' ')
    # Remove leading page numbers like "9\n" or "25\n"
    text = re.sub(r'^\d+\s+', '', text)
    return text

def parse_chapter(html_text, book_abbrev, chapter_num):
    """
    Parse chapter HTML and return list of (verse_ref, annotation) tuples.
    verse_ref = "Chapter:Verse" e.g. "1:1"
    """
    soup = BeautifulSoup(html_text, 'lxml')
    
    # Get the main content - try to find article/main or body text
    # CCEL pages have content in <body>
    body = soup.find('body') or soup
    
    # Extract all text
    full_text = body.get_text(separator='\n')
    
    # Remove the security/header lines that appear in CLI fetch
    # These are actual page content from CCEL
    
    results = []
    
    # Split by verse markers
    # Pattern 1: "[Ver. N.]" at start
    # Pattern 2: "N. Text of verse..." at start of line  
    # Pattern 3: "N-M. Text..." for verse ranges
    
    # Split text into segments by verse headers
    # Look for patterns like:
    # - Line starting with just a number or range followed by period and space
    # - "[Ver. N.]" 
    
    lines = full_text.split('\n')
    
    current_verses = []
    current_comment = []
    
    # Verse header patterns
    ver_pattern1 = re.compile(r'^\[?Ver\.?\s*(\d+)\.?\]?\s*(.*)$', re.IGNORECASE)
    ver_pattern2 = re.compile(r'^(\d+)[–\-](\d+)\.\s+(.*)$')
    ver_pattern3 = re.compile(r'^(\d+)\.\s+([A-Z\[\(].*)$')  # "N. Capital letter text"
    
    # Additional heuristic: page number only lines
    page_num_pattern = re.compile(r'^\d+$')
    
    def flush_current():
        """Flush current_verses + current_comment to results."""
        if current_verses and current_comment:
            comment_text = ' '.join(current_comment).strip()
            comment_text = clean_text(comment_text)
            if len(comment_text) > 20:  # Skip trivial entries
                for v in current_verses:
                    results.append((f"{chapter_num}:{v}", comment_text))
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Skip page numbers
        if page_num_pattern.match(line):
            continue
        
        # Check for "[Ver. N.]" pattern
        m = ver_pattern1.match(line)
        if m:
            flush_current()
            current_verses = [int(m.group(1))]
            rest = m.group(2).strip()
            current_comment = [rest] if rest else []
            continue
        
        # Check for "N-M. text" pattern (verse range)
        m = ver_pattern2.match(line)
        if m:
            flush_current()
            v_start = int(m.group(1))
            v_end = int(m.group(2))
            current_verses = list(range(v_start, v_end + 1))
            rest = m.group(3).strip()
            current_comment = [rest] if rest else []
            continue
        
        # Check for "N. text" pattern - only if starts with capital or bracket
        m = ver_pattern3.match(line)
        if m:
            flush_current()
            current_verses = [int(m.group(1))]
            rest = m.group(2).strip()
            current_comment = [rest] if rest else []
            continue
        
        # Otherwise, accumulate to current comment
        if current_verses:
            current_comment.append(line)
    
    # Flush final
    flush_current()
    
    return results

def identify_gem_passages(annotation):
    """Mark especially significant passages with # GEM."""
    # Heuristics for significant passages:
    # - Long, substantive theological commentary
    # - Mentions of key doctrines
    gem_keywords = [
        'incarnation', 'resurrection', 'trinity', 'the word was made flesh',
        'son of god', 'holy ghost', 'mother of god', 'virgin', 'baptism',
        'eucharist', 'salvation', 'redemption', 'kingdom of heaven',
        'eternal life', 'grace', 'faith', 'charity', 'love of god',
        'mystical', 'spiritual sense', 'allegorical'
    ]
    ann_lower = annotation.lower()
    for kw in gem_keywords:
        if kw in ann_lower and len(annotation) > 500:
            return annotation + ' # GEM'
    return annotation

def process_book(book_id, book_abbrev, num_chapters):
    """Process a full Gospel book."""
    print(f"\n=== Processing {book_abbrev} ({num_chapters} chapters) ===")
    
    all_rows = []
    
    for ch in range(1, num_chapters + 1):
        print(f"  Fetching {book_abbrev} Chapter {ch}...")
        html = fetch_chapter(book_id, ch)
        if not html:
            print(f"  SKIPPED: No content for {book_abbrev} {ch}")
            continue
        
        rows = parse_chapter(html, book_abbrev, ch)
        print(f"    Parsed {len(rows)} verse entries")
        
        for (ref, annotation) in rows:
            annotation = identify_gem_passages(annotation)
            all_rows.append((book_abbrev, ref, annotation))
        
        # Write incrementally after each chapter
        write_rows(all_rows, book_abbrev, ch, num_chapters)
        
        # Polite delay
        time.sleep(1.5)
    
    return all_rows

def write_rows(rows, book_abbrev, current_ch, total_ch):
    """Write rows to TSV file (append mode for incrementality)."""
    # We'll write the full file each time for simplicity (small enough)
    pass  # We'll do final write per book

def write_tsv(rows, output_file, mode='a'):
    """Write rows to TSV file."""
    with open(output_file, mode, encoding='utf-8') as f:
        for (book, ref, annotation) in rows:
            # Escape newlines in annotation
            annotation = annotation.replace('\n', ' ')
            f.write(f"{book}\t{ref}\t{annotation}\n")

def main():
    print("=== Aquinas Catena Aurea Scraper ===")
    print(f"Output: {OUTPUT_FILE}")
    
    # Initialize output file with header
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("Book\tVerse\tCommentary\n")
    
    total_rows = 0
    
    for (book_id, book_abbrev, num_chapters) in GOSPELS:
        rows = process_book(book_id, book_abbrev, num_chapters)
        if rows:
            write_tsv(rows, OUTPUT_FILE, mode='a')
            total_rows += len(rows)
            print(f"  Written {len(rows)} rows for {book_abbrev}")
    
    print(f"\n=== DONE: {total_rows} total rows written to {OUTPUT_FILE} ===")

if __name__ == '__main__':
    main()
