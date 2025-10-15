# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),  
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.2.1] - 2025-09-19

### changed

- reinforced the html text cleaning

## [0.2.0] - 2025-09-17

### Added

- New parsing package: `textnormx.parser`
  - `types.py`: `Element` & `Chunk` dataclasses.
  - `markdown.py`: `parse_markdown_elements(md: str)`.
  - `html.py`: `parse_html_elements(html: str)` (optional extra `textnormx[html]` via `beautifulsoup4`).
  - `chunk.py`: `chunk_by_title(...)` (by-title aggregation, soft split).
- Test suite (pytest) and optional Poetry group:
  - `[tool.poetry.group.test]` with `pytest>=7.4,<8` and optional `pytest-cov>=4.1,<7`.
- Logging-friendly pytest configuration examples for live logging.

### Changed

- `textnormx.__init__` now re-exports cleaner & parser APIs for a simpler import surface.
- `clean_chunks(...)` supports both **dict** chunks and **dataclass** chunks; new args:
  - `preserve_markdown_tables=True`
  - `in_place=True`
- `clean_text(...)` adds `preserve_markdown_tables` to avoid mangling Markdown tables when collapsing whitespace.

### Fixed

- `chunk_by_title(...)` no longer mixes Markdown tables into text; tables are emitted as dedicated `Table` chunks (no stray `|` fragments).
- Tiny tail fragments are merged into the previous chunk when `< min_chunk_chars`, reducing low-signal micro-chunks.
- Normalization preserves table spacing while replacing PUA bullets and NBSP appropriately.

### Deprecated

- Importing cleaner functions from legacy root module paths is discouraged.  
  Prefer: `from textnormx.cleaner import clean_text, clean_lines, clean_chunks`.

### Removed

- N/A

### Security

- N/A

## [0.1.0] - 2025-09-15

### Added

- Initial release: core normalization (`textnormx.cleaner`) with mappings & basic CLI.
