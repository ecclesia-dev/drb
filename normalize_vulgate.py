#!/usr/bin/env python3
"""Normalize vulgate.tsv (LukeSmithxyz/vul) to haydock-compatible format.

Input:  BookFull  BookAbbrev  BookNum  Chapter  Verse  Text  (\r\n endings)
Output: DRBBookName  Chapter:Verse  LatinText  (\n endings)
"""

import sys

BOOK_MAP = {
    "Genesis": "Genesis",
    "Exodus": "Exodus",
    "Leviticus": "Leviticus",
    "Numbers": "Numbers",
    "Deuteronomy": "Deuteronomy",
    "Joshua": "Josue",
    "Judges": "Judges",
    "Ruth": "Ruth",
    "1 Samuel": "1 Kings",
    "2 Samuel": "2 Kings",
    "1 Kings": "3 Kings",
    "2 King": "4 Kings",
    "1 Chronicles": "1 Paralipomenon",
    "2 Chronicles": "2 Paralipomenon",
    "Ezra": "1 Esdras",
    "Nehemiah": "2 Esdras",
    "Esther": "Esther",
    "Judith": "Judith",
    "Tobit": "Tobias",
    "1 Maccabees": "1 Machabees",
    "2 Maccabees": "2 Machabees",
    "Job": "Job",
    "Psalms": "Psalms",
    "Proverbs": "Proverbs",
    "Ecclesiastes": "Ecclesiastes",
    "Song of Solomon": "Canticle of Canticles",
    "Wisdom": "Wisdom",
    "Sirach": "Ecclesiasticus",
    "Isaiah": "Isaias",
    "Jeremiah": "Jeremias",
    "Lamentations": "Lamentations",
    "Baruch": "Baruch",
    "Ezekiel": "Ezechiel",
    "Daniel": "Daniel",
    "Hosea": "Osee",
    "Joel": "Joel",
    "Amos": "Amos",
    "Obadiah": "Abdias",
    "Jonah": "Jonas",
    "Micah": "Micheas",
    "Nahum": "Nahum",
    "Habakkuk": "Habacuc",
    "Zephaniah": "Sophonias",
    "Haggai": "Aggeus",
    "Zechariah": "Zacharias",
    "Malachi": "Malachias",
    "Matthew": "Matthew",
    "Mark": "Mark",
    "Luke": "Luke",
    "John": "John",
    "The Acts": "Acts",
    "Acts": "Acts",
    "Romans": "Romans",
    "1 Corinthians": "1 Corinthians",
    "2 Corinthians": "2 Corinthians",
    "Galatians": "Galatians",
    "Ephesians": "Ephesians",
    "Philippians": "Philippians",
    "Colossians": "Colossians",
    "1 Thessalonians": "1 Thessalonians",
    "2 Thessalonians": "2 Thessalonians",
    "1 Timothy": "1 Timothy",
    "2 Timothy": "2 Timothy",
    "Titus": "Titus",
    "Philemon": "Philemon",
    "Hebrews": "Hebrews",
    "James": "James",
    "1 Peter": "1 Peter",
    "2 Peter": "2 Peter",
    "1 John": "1 John",
    "2 John": "2 John",
    "3 John": "3 John",
    "Jude": "Jude",
    "Revelation": "Apocalypse",
}

infile = sys.argv[1] if len(sys.argv) > 1 else "vulgate.tsv"
outfile = sys.argv[2] if len(sys.argv) > 2 else "vulgate-normalized.tsv"

skipped = 0
written = 0

with open(infile, encoding="utf-8") as fin, open(outfile, "w", encoding="utf-8") as fout:
    for line in fin:
        line = line.rstrip("\r\n")
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 6:
            skipped += 1
            continue
        book_src, _abbrev, _booknum, chapter, verse, text = parts[0], parts[1], parts[2], parts[3], parts[4], "\t".join(parts[5:])
        drb_book = BOOK_MAP.get(book_src)
        if drb_book is None:
            skipped += 1
            continue
        fout.write(f"{drb_book}\t{chapter}:{verse}\t{text}\n")
        written += 1

print(f"Written: {written}, Skipped: {skipped}", file=sys.stderr)
