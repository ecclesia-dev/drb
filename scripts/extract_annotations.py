#!/usr/bin/env python3
"""
Extract annotations from Douai-Rheims HTML files and merge with scan TSV.
Output: douai-1609-annotations.tsv
"""

import os
import re
import sys
import csv
from pathlib import Path
from bs4 import BeautifulSoup
from collections import defaultdict
from datetime import date

_HERE = Path(__file__).parent.resolve()
_DRB_IOS = _HERE.parent / "drb-ios"
HTML_DIR = _DRB_IOS / "DouayRheims/sources/originaldouay"
SCAN_TSV = _HERE / "douai-1609.tsv"
OUT_TSV = _HERE / "douai-1609-annotations.tsv"
QA_DIR = _DRB_IOS / "qa"
QA_FILE = QA_DIR / f"douai-1609-unified-{date.today().isoformat()}.md"

NT_BOOKS = {
    'Mt','Mk','Lk','Jn','Acts','Rom','1Cor','2Cor','Gal','Eph','Phil','Col',
    '1Thes','2Thes','1Tim','2Tim','Tit','Phlm','Heb','Jas','1Pet','2Pet',
    '1Jn','2Jn','3Jn','Jude','Rev'
}

def classify_file(fname):
    """Return (book_abbrev, chapter_int) or None if file should be skipped."""
    name = fname.lower()

    # Skip index files — we prefer plain files
    if name.endswith('--index.html') or name.endswith('-index.html'):
        return None

    # Remove .html suffix
    stem = fname[:-5]  # preserve case for matching

    # Extract trailing chapter number
    m = re.search(r'(\d+)$', stem)
    chapter = int(m.group(1)) if m else 1

    stem_lower = stem.lower()

    # --- NT books ---
    if re.match(r'^matthew', stem_lower) or re.match(r'^mat\d*$', stem_lower):
        return ('Mt', chapter)
    if re.match(r'^mark', stem_lower):
        return ('Mk', chapter)
    if re.match(r'^luke', stem_lower):
        return ('Lk', chapter)
    # John: NOT I_John / II_John / III_John
    if re.match(r'^john', stem_lower):
        return ('Jn', chapter)
    if re.match(r'^acts', stem_lower):
        return ('Acts', chapter)
    if re.match(r'^romans', stem_lower):
        return ('Rom', chapter)
    if re.match(r'^galatians', stem_lower):
        return ('Gal', chapter)
    if re.match(r'^ephesians', stem_lower):
        return ('Eph', chapter)
    if re.match(r'^philippians', stem_lower):
        return ('Phil', chapter)
    if re.match(r'^colossians', stem_lower):
        return ('Col', chapter)
    if re.match(r'^hebrews', stem_lower):
        return ('Heb', chapter)
    if re.match(r'^james', stem_lower):
        return ('Jas', chapter)
    if re.match(r'^jude\d*$', stem_lower):
        return ('Jude', chapter)
    if re.match(r'^revelations', stem_lower):
        return ('Rev', chapter)
    if re.match(r'^i[-_]corinth', stem_lower) or re.match(r'^i_corinth', stem_lower):
        return ('1Cor', chapter)
    if re.match(r'^ii[-_]corinth', stem_lower) or re.match(r'^ii_corinth', stem_lower):
        return ('2Cor', chapter)
    if re.match(r'^i[-_]thessalonians', stem_lower) or re.match(r'^i_thessalonians', stem_lower):
        return ('1Thes', chapter)
    if re.match(r'^ii[-_]thessalonians', stem_lower) or re.match(r'^ii_thessalonians', stem_lower):
        return ('2Thes', chapter)
    if re.match(r'^i[-_]timothee', stem_lower) or re.match(r'^i_timothee', stem_lower):
        return ('1Tim', chapter)
    if re.match(r'^ii[-_]timothee', stem_lower) or re.match(r'^ii_timothee', stem_lower):
        return ('2Tim', chapter)
    if re.match(r'^titus', stem_lower):
        return ('Tit', chapter)
    if re.match(r'^philemon', stem_lower):
        return ('Phlm', chapter)
    if re.match(r'^i[-_]peter', stem_lower) or re.match(r'^i_peter', stem_lower):
        return ('1Pet', chapter)
    if re.match(r'^ii[-_]peter', stem_lower) or re.match(r'^ii_peter', stem_lower):
        return ('2Pet', chapter)
    if re.match(r'^iii[-_]john', stem_lower) or re.match(r'^iii_john', stem_lower):
        return ('3Jn', chapter)
    if re.match(r'^ii[-_]john', stem_lower) or re.match(r'^ii_john', stem_lower):
        return ('2Jn', chapter)
    if re.match(r'^i[-_]john', stem_lower) or re.match(r'^i_john', stem_lower):
        return ('1Jn', chapter)

    # --- OT books ---
    if re.match(r'^old--genesis', stem_lower) or re.match(r'^old-genesis', stem_lower) or re.match(r'^genesis', stem_lower):
        return ('Gn', chapter)
    if re.match(r'^old--psalms', stem_lower) or re.match(r'^old-psalms', stem_lower):
        return ('Ps', chapter)
    if re.match(r'^old--wisdom', stem_lower) or re.match(r'^old-wisdom', stem_lower):
        return ('Wis', chapter)
    if re.match(r'^old--lamentations', stem_lower) or re.match(r'^old-lamentations', stem_lower):
        return ('Lam', chapter)
    if re.match(r'^old--baruch', stem_lower) or re.match(r'^old-baruch', stem_lower):
        return ('Bar', chapter)
    if re.match(r'^old--daniel', stem_lower) or re.match(r'^old-daniel', stem_lower):
        return ('Dn', chapter)
    if re.match(r'^old--jonas', stem_lower) or re.match(r'^old-jonas', stem_lower):
        return ('Jon', chapter)
    if re.match(r'^old--sophonias', stem_lower) or re.match(r'^old-sophonias', stem_lower):
        return ('Zeph', chapter)
    if re.match(r'^old--ecclesiasticus', stem_lower) or re.match(r'^old-ecclesiasticus', stem_lower):
        return ('Sir', chapter)
    if re.match(r'^old--ruth', stem_lower) or re.match(r'^old-ruth', stem_lower):
        return ('Ruth', chapter)

    return None  # unrecognized — skip

def extract_verse_num(text):
    """Extract leading verse number from annotation text."""
    m = re.match(r'^\s*(\d+)[.)]\s', text)
    if m:
        return int(m.group(1))
    # Try first 20 chars
    m = re.search(r'(\d+)', text[:20])
    if m:
        return int(m.group(1))
    return 0

def clean_text(text):
    """Clean annotation text."""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_from_html(fpath, book, chapter):
    """Extract all annotations from an HTML file. Returns list of (verse_int, cleaned_text)."""
    with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    soup = BeautifulSoup(content, 'html.parser')
    
    # Primary: Annotations2 spans
    spans = soup.find_all('span', id='Annotations2')
    
    # Fallback: files that use indenttext spans after an Annotations header
    if not spans:
        ann_marker = soup.find('span', id='Annotations')
        if ann_marker:
            # Find all siblings/subsequent nodes for indenttext spans
            # Get document position of Annotations marker
            all_tags = soup.find_all(['span'])
            ann_pos = None
            for i, tag in enumerate(all_tags):
                if tag.get('id') == 'Annotations':
                    ann_pos = i
                    break
            if ann_pos is not None:
                for tag in all_tags[ann_pos+1:]:
                    if tag.get('id') == 'indenttext':
                        # Only include if it looks like an annotation (starts with verse pattern)
                        text = tag.get_text()
                        if re.match(r'^\s*\d+[.)]\s', text) or re.match(r'^\s*<i>\d+', str(tag)):
                            spans.append(tag)
    
    results = []
    for span in spans:
        raw = span.get_text()
        verse = extract_verse_num(raw)
        cleaned = clean_text(raw)
        if cleaned:
            results.append((verse, cleaned))
    return results

def main():
    QA_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Process HTML files
    print("Step 1: Extracting from HTML files...")
    html_files = sorted(HTML_DIR.glob("*.html"))
    
    # website_data: dict of (book, chapter) -> list of (verse, text)
    website_data = defaultdict(list)
    # Track which (book, chapter) pairs we have from website
    website_coverage = defaultdict(set)  # book -> set of chapters
    
    parse_errors = []
    file_count = 0
    skipped_index = 0
    skipped_unknown = 0

    for fpath in html_files:
        result = classify_file(fpath.name)
        if result is None:
            if '--index' in fpath.name.lower() or fpath.name.lower().endswith('index.html'):
                skipped_index += 1
            else:
                skipped_unknown += 1
                # Only warn if it has annotations
                with open(fpath) as f:
                    c = f.read()
                if 'Annotations2' in c:
                    parse_errors.append(f"UNRECOGNIZED file with annotations: {fpath.name}")
            continue
        
        book, chapter = result
        annotations = extract_from_html(fpath, book, chapter)
        
        if annotations:
            for verse, text in annotations:
                website_data[(book, chapter)].append((verse, text))
            website_coverage[book].add(chapter)
        
        file_count += 1

    print(f"  Processed {file_count} files, skipped {skipped_index} index files, {skipped_unknown} unrecognized")
    
    # Build website rows
    website_rows = []
    # Track (book, ch, verse) occurrences for dedup
    verse_counts = defaultdict(int)  # (book, chapter, verse) -> count seen so far
    
    # Sort by book, chapter, verse for clean output
    # First collect all
    all_web = []
    for (book, chapter), ann_list in website_data.items():
        for verse, text in ann_list:
            all_web.append((book, chapter, verse, text))
    
    # Sort
    def sort_key(row):
        book_order = ['Gn','Ex','Lv','Nm','Dt','Jos','Jdg','Ru','1Sam','2Sam','1Kgs','2Kgs',
                      '1Chr','2Chr','Ezr','Neh','Tob','Jdt','Est','1Mac','2Mac','Job','Ps','Prv',
                      'Eccl','Song','Wis','Sir','Is','Jer','Lam','Bar','Ez','Dn','Hos','Jl','Am',
                      'Ob','Jon','Mi','Na','Hab','Zeph','Hg','Zech','Mal',
                      'Mt','Mk','Lk','Jn','Acts','Rom','1Cor','2Cor','Gal','Eph','Phil','Col',
                      '1Thes','2Thes','1Tim','2Tim','Tit','Phlm','Heb','Jas','1Pet','2Pet',
                      '1Jn','2Jn','3Jn','Jude','Rev']
        b, ch, v, t = row
        bi = book_order.index(b) if b in book_order else 999
        return (bi, ch, v)
    
    all_web.sort(key=sort_key)
    
    for book, chapter, verse, text in all_web:
        cv = f"{chapter}:{verse}"
        key = (book, chapter, verse)
        verse_counts[key] += 1
        # If more than one annotation for same verse, they stay as separate rows (same cv)
        website_rows.append({
            'BookAbbrev': book,
            'Chapter:Verse': cv,
            'Annotation': text,
            'Source': 'website'
        })
    
    print(f"  Website rows: {len(website_rows)}")

    # Step 2: Load scan data
    print("Step 2: Loading scan data...")
    scan_rows = []
    scan_coverage = defaultdict(set)  # book -> chapters in scan
    
    with open(SCAN_TSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            book = row['BookAbbrev']
            cv = row['Chapter:Verse']
            ann = row['Annotation']
            # Parse chapter from cv
            parts = cv.split(':')
            try:
                ch = int(parts[0])
            except:
                ch = 0
            scan_coverage[book].add(ch)
            scan_rows.append({'BookAbbrev': book, 'Chapter:Verse': cv, 'Annotation': ann, 'Source': 'scan'})
    
    print(f"  Scan rows total: {len(scan_rows)}")

    # Step 3: Merge — only include scan rows for OT books/chapters not in website
    print("Step 3: Deduplicating and merging...")
    
    merged_rows = list(website_rows)  # start with all website rows
    
    included_scan = 0
    skipped_scan_nt = 0
    skipped_scan_covered = 0
    
    for row in scan_rows:
        book = row['BookAbbrev']
        cv = row['Chapter:Verse']
        parts = cv.split(':')
        try:
            ch = int(parts[0])
        except:
            ch = 0
        
        # Skip NT books
        if book in NT_BOOKS:
            skipped_scan_nt += 1
            continue
        
        # Skip if website already has this book+chapter
        if ch in website_coverage.get(book, set()):
            skipped_scan_covered += 1
            continue
        
        merged_rows.append(row)
        included_scan += 1
    
    print(f"  Included {included_scan} scan rows")
    print(f"  Skipped {skipped_scan_nt} scan rows (NT books)")
    print(f"  Skipped {skipped_scan_covered} scan rows (covered by website)")

    # Step 4: Write output TSV
    print("Step 4: Writing output TSV...")
    with open(OUT_TSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['BookAbbrev','Chapter:Verse','Annotation','Source'], delimiter='\t')
        writer.writeheader()
        for row in merged_rows:
            writer.writerow(row)
    
    print(f"  Written: {OUT_TSV}")
    print(f"  Total rows: {len(merged_rows)}")

    # --- Summary stats ---
    books_in_output = sorted(set(r['BookAbbrev'] for r in merged_rows))
    scan_books = sorted(set(r['BookAbbrev'] for r in merged_rows if r['Source'] == 'scan'))
    
    print(f"\n=== SUMMARY ===")
    print(f"Total rows: {len(merged_rows)}")
    print(f"Website rows: {len(website_rows)}")
    print(f"Scan rows included: {included_scan}")
    print(f"Books covered: {len(books_in_output)}: {', '.join(books_in_output)}")
    print(f"Books with scan-only coverage: {', '.join(scan_books) if scan_books else '(none)'}")

    # --- QA Report ---
    print(f"\nStep 5: Writing QA report...")
    
    # Per-book row counts
    book_counts = defaultdict(int)
    book_chapters = defaultdict(set)
    book_source = defaultdict(set)
    for row in merged_rows:
        b = row['BookAbbrev']
        book_counts[b] += 1
        cv = row['Chapter:Verse']
        try:
            ch = int(cv.split(':')[0])
            book_chapters[b].add(ch)
        except:
            pass
        book_source[b].add(row['Source'])
    
    # Genesis ch.49 comparison
    gn49_web = [r for r in website_rows if r['BookAbbrev'] == 'Gn' and r['Chapter:Verse'].startswith('49:')]
    gn49_scan = [r for r in merged_rows if r['BookAbbrev'] == 'Gn' and r['Chapter:Verse'].startswith('49:') and r['Source'] == 'scan']

    with open(QA_FILE, 'w', encoding='utf-8') as qa:
        qa.write(f"# Douai-Rheims Unified Annotations QA Report\n")
        qa.write(f"Generated: {date.today().isoformat()}\n\n")
        qa.write(f"## Summary\n")
        qa.write(f"- Total rows: {len(merged_rows)}\n")
        qa.write(f"- Website rows: {len(website_rows)}\n")
        qa.write(f"- Scan rows included: {included_scan}\n")
        qa.write(f"- Books covered: {len(books_in_output)}\n\n")
        
        qa.write(f"## Per-Book Row Counts\n\n")
        qa.write(f"| Book | Rows | Chapters | Source(s) |\n")
        qa.write(f"|------|------|----------|-----------|\n")
        for b in books_in_output:
            chs = sorted(book_chapters[b])
            ch_str = f"{min(chs)}-{max(chs)}" if chs else "?"
            src = ', '.join(sorted(book_source[b]))
            qa.write(f"| {b} | {book_counts[b]} | {ch_str} ({len(chs)} chapters) | {src} |\n")
        
        qa.write(f"\n## Books with Scan-Only Coverage\n")
        if scan_books:
            for b in scan_books:
                chs = sorted(book_chapters[b])
                qa.write(f"- {b}: chapters {chs}\n")
        else:
            qa.write("(none — all covered by website)\n")
        
        qa.write(f"\n## Chapter Coverage Gaps\n")
        qa.write("Books where chapter coverage is non-contiguous:\n\n")
        for b in books_in_output:
            chs = sorted(book_chapters[b])
            if not chs:
                continue
            expected = set(range(min(chs), max(chs)+1))
            missing = expected - set(chs)
            if missing:
                qa.write(f"- **{b}**: missing chapters {sorted(missing)}\n")
        
        qa.write(f"\n## Books with Only Verse 0 (Unknown Verse)\n")
        verse_zero = defaultdict(int)
        for row in merged_rows:
            cv = row['Chapter:Verse']
            if cv.endswith(':0'):
                verse_zero[row['BookAbbrev']] += 1
        for b, cnt in sorted(verse_zero.items()):
            qa.write(f"- {b}: {cnt} annotations with unknown verse\n")
        
        qa.write(f"\n## Parse Errors / Warnings\n")
        if parse_errors:
            for e in parse_errors:
                qa.write(f"- {e}\n")
        else:
            qa.write("(none)\n")
        
        qa.write(f"\n## Genesis Ch.49 Comparison\n")
        qa.write(f"Website has {len(gn49_web)} annotations for Gn 49.\n")
        qa.write(f"Scan has {len(gn49_scan)} annotations for Gn 49 (after merge rules).\n\n")
        if gn49_web:
            qa.write("**Website Gn 49 (first entry, first 100 chars):**\n")
            qa.write(f"```\n{gn49_web[0]['Annotation'][:100]}\n```\n\n")
        if gn49_scan:
            qa.write("**Scan Gn 49 (first entry, first 100 chars):**\n")
            qa.write(f"```\n{gn49_scan[0]['Annotation'][:100]}\n```\n\n")
        elif gn49_web:
            # Check raw scan for Gn 49 before merge filter
            raw_gn49_scan = [r for r in scan_rows if r['BookAbbrev'] == 'Gn' and r['Chapter:Verse'].startswith('49:')]
            if raw_gn49_scan:
                qa.write("**Scan Gn 49 (first entry, first 100 chars — excluded by merge rules):**\n")
                qa.write(f"```\n{raw_gn49_scan[0]['Annotation'][:100]}\n```\n\n")
                if gn49_web[0]['Annotation'][:100] == raw_gn49_scan[0]['Annotation'][:100]:
                    qa.write("→ First 100 chars are IDENTICAL between sources.\n")
                else:
                    qa.write("→ First 100 chars DIFFER between sources.\n")
        
        qa.write(f"\n## Files Processed\n")
        qa.write(f"- HTML files processed: {file_count}\n")
        qa.write(f"- Index files skipped: {skipped_index}\n")
        qa.write(f"- Unrecognized files skipped: {skipped_unknown}\n")
    
    print(f"  QA report: {QA_FILE}")
    print("\nDone.")

if __name__ == '__main__':
    main()
