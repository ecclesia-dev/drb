# Contributing to drb

Thank you for your interest in contributing! This project serves the Catholic community by making the Douay-Rheims Bible accessible from the command line.

## How to Contribute

### Reporting Bugs

- Open an issue with a clear description of the problem
- Include the output of `drb -h` and your OS/shell version
- Provide the exact command that produced the bug

### Suggesting Features

- Open an issue describing the feature and its use case
- Keep suggestions aligned with the project's scope: a simple, fast CLI Bible reader

### Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b fix/psalm-numbering`)
3. Make your changes
4. Test locally: `make clean && make && ./drb John 1:1`
5. Run shellcheck: `shellcheck -s sh drb.sh`
6. Submit a pull request with a clear description

### Text Corrections

If you find an error in the Bible text (`drb.tsv`), please open an issue with:

- The book, chapter, and verse
- The current (incorrect) text
- The corrected text with a citation (e.g., 1899 Challoner edition, [DRBO](https://www.drbo.org/))

We take textual accuracy seriously. All corrections must be verifiable against a published edition.

## Code Style

- Shell scripts target POSIX `sh` — no bashisms
- All scripts must pass `shellcheck -s sh`
- Keep it simple. This is a ~100-line shell script, not a framework.

## Scope

This project intentionally stays small. We aim to:

- ✅ Read and search the Douay-Rheims Bible text
- ✅ Support standard reference notation
- ✅ Work on any POSIX system
- ✅ Provide commentary via `-c` flag (Haydock, Lapide, Douai 1609)
- ❌ Not support other translations (use [kjv](https://github.com/LukeSmithxyz/kjv) for King James)

## Community

This is a Catholic open source project. We welcome contributors of all backgrounds. Be charitable, be patient, be kind.

*Deo gratias.*
