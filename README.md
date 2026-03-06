# drb

**Read the Douay-Rheims Bible from your terminal.**

`73 Books · Vulgate Order · 5 Commentaries · Public Domain`

A command-line tool for reading the Douay-Rheims Bible (Challoner revision) — the classic English translation of the Latin Vulgate, with all 73 books of the Catholic canon including the deuterocanonical books.

Includes the **Haydock Catholic Bible Commentary** (full Bible, 35,000+ entries), **Cornelius à Lapide** full Bible commentary (OT + NT, 8,000+ entries), the **1609 Douai Annotations** (original Rheims-Douai marginal notes), **Aquinas' Catena Aurea** with commentary on the Gospels, Pauline epistles, and Job, and **Balthasar Corderius SJ** commentary on Job.

Inspired by [Luke Smith's kjv](https://github.com/LukeSmithxyz/kjv). Built for Catholics who live in the terminal.

---

## Quick Start

```
$ drb John 1:1-5
John
1:1     In the beginning was the Word: and the Word was with God: and the Word
        was God.
1:2     The same was in the beginning with God.
1:3     All things were made by him: and without him was made nothing that was
        made.
1:4     In him was life: and the life was the light of men.
1:5     And the light shineth in darkness: and the darkness did not comprehend
        it.
```

## Installation

### From source

```sh
git clone https://github.com/ecclesia-dev/drb.git
cd drb
make
sudo make install
```

To uninstall:

```sh
sudo make uninstall
```

## Usage

```
drb [flags] [reference...]

  -l      list books
  -r      random verse
  -t      translation version (default: challoner)
          versions: challoner, 1609
  -c      show Haydock commentary alongside verses
  -W      no line wrap
  -h      show help
```

### Translation versions

```
$ drb Genesis 1:1              # default: Challoner revision
$ drb -t 1609 Genesis 1:1     # original 1609 Douay-Rheims
$ drb -t challoner Genesis 1:1 # explicit Challoner
```

The **1609 Douay-Rheims** is the original pre-revision text, more literal, translating directly from the Latin Vulgate. Archaic spelling is preserved ("heauen", "darknes", "diuided", "foule") — this is authentic, not a typo.

The **Challoner revision** (1749–1752) is the standard Catholic English Bible. It modernised spelling, smoothed the prose, and adjusted some renderings. This is the default.

### Reading

```
$ drb Genesis 1:1              # single verse
$ drb Wisdom 7                 # full chapter
$ drb Romans 8:28-31           # verse range
$ drb Romans 8-9               # chapter range
$ drb John 3:16,17             # multiple verses
$ drb John 1:1-2:5             # cross-chapter range
```

### Commentary

Use `-c` to display commentary below each verse. Defaults to Haydock:

```
$ drb -c John 1:1              # Haydock (default)
$ drb -c lapide Matthew 1:2    # Cornelius à Lapide (NT)
$ drb -c lapide Isaiah 7:14    # Cornelius à Lapide (OT)
$ drb -c lapide Genesis 1:1    # Cornelius à Lapide (OT)
$ drb -c douai Genesis 22:1    # 1609 Douai Annotations
$ drb -c 1609 Genesis 22:1     # alias for douai
$ drb -c aquinas Matthew 5:3   # Aquinas (Catena Aurea)
$ drb -c all John 3:16         # all available commentaries
```

**Haydock** covers the entire Bible (35,000+ entries) — Church Fathers, Doctors of the Church, traditional Catholic exegesis.

**Cornelius à Lapide** covers the **full Bible** (OT + NT, 8,000+ entries) — Genesis through Revelation. Dense, scholarly commentary from the 17th century Jesuit exegete.

**1609 Douai Annotations** (`-c douai` or `-c 1609`) — the original marginal notes from the 1609 Douay Old Testament and 1582 Rheims New Testament (3,100+ entries). Text preserves original 1609 spelling: the long-s character ſ is printed as *f*, and archaic orthography is authentic, not a typo.

**Aquinas (Catena Aurea)** (`-c aquinas`) — St. Thomas Aquinas' *Catena Aurea* ("Golden Chain"), a verse-by-verse compilation of patristic commentary on the four Gospels, together with his commentary on the Pauline epistles and Job. Draws on Chrysostom, Augustine, Jerome, Ambrose, and other Fathers. Gospel commentary uses `aquinas-catena.tsv`; Pauline epistle commentary uses `aquinas-epistles.tsv` (sourced by Alcuin); Job commentary uses `aquinas-job.tsv`.

### Random verse

```
$ drb -r
```

### Deuterocanonical books

All seven deuterocanonical books are included:

```
$ drb Wisdom 7:26
$ drb Sirach 1:1-5
$ drb Tobit 1
$ drb 1 Maccabees 1
$ drb Baruch 3
```

### Search with regex

```
$ drb /grace                          # search whole Bible
$ drb John /bread of life             # search one book
$ drb Psalms /mercy                   # search Psalms
```

### Piping

```sh
drb 1 Corinthians /love | grep -c "^"    # count matching verses
drb John 1:1 | cut -f2                    # extract text only
```

### Interactive mode

Launch without arguments for a REPL:

```
$ drb
drb> John 1:1
drb> /love one another
drb> Wisdom 7
```

## Commentary Sources

| Source | Coverage | Entries |
|--------|----------|---------|
| **Haydock** (Rev. George Leo Haydock, 1859) | Full Bible | 35,000+ |
| **Cornelius à Lapide** | Full Bible (OT + NT) | 8,000+ |
| **1609 Douai Annotations** | OT + NT (original Douai/Rheims notes) | 3,100+ |
| **Aquinas (Catena Aurea)** (St. Thomas Aquinas) | Gospels + Pauline Epistles + Job | — |
| **Balthasar Corderius SJ** (Job commentary) | Job | 193 |

Use `-c haydock`, `-c lapide`, `-c douai` (alias: `-c 1609`), `-c aquinas`, or `-c corderius` to select. Use `-c all` to show all five.

All commentary texts are public domain (pre-1928).

## ⚠️ Psalm Numbering

The Douay-Rheims follows **Vulgate/Septuagint numbering**, which differs from the Hebrew numbering in most Protestant Bibles. For example, "The Lord is my shepherd" (Protestant Psalm 23) is:

```
$ drb Psalms 22
```

Run `drb -l` to see all 73 books with their abbreviations.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PAGER` | Pager program | `less` |
| `DRB_NOLINEWRAP` | Disable line wrapping | unset |
| `DRB_MAX_WIDTH` | Maximum line width | terminal width |

## Related Projects

Part of the command-line Bible ecosystem:

| Tool | Translation | Language | Books |
|------|------------|----------|-------|
| **[drb](https://github.com/ecclesia-dev/drb)** | Douay-Rheims (Challoner) | English | 73 (Catholic canon) |
| **[kjv](https://github.com/LukeSmithxyz/kjv)** | King James Version | English | 66 + Apocrypha |
| **[vul](https://github.com/LukeSmithxyz/vul)** | Latin Vulgate | Latin | 73 |
| **[grb](https://github.com/LukeSmithxyz/grb)** | Septuagint / SBL Greek | Greek | 66 + Apocrypha |

All four use the same interface:

```sh
# Compare translations side by side
paste <(drb John 1:1 | cut -f2) <(vul John 1:1 | cut -f2)
```

*Ad Maiorem Dei Gloriam.*

---
_Built by Jerome. Reviewed by Bellarmine (theology) and Pius (content alignment)._
