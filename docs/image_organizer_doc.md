# Image Organizer Tool Documentation

## Overview
This tool manages image and video files within specified directories by organizing, deduplicating, and providing restoration capabilities based on SHA‑256 checksums and timestamps (EXIF or, if absent, filesystem timestamps).

---

## Primary Functionalities

### Scan and Index
* Traverse directories recursively.
* Identify files (`jpg`, `jpeg`, `png`, `gif`, `tiff`, `cr2`, `mov`, etc.) **case‑insensitively**.
* Calculate SHA‑256 checksums.
* Extract EXIF timestamps or fall back to file creation/modification time.
* Persist findings to SQLite.

### Organize **+** Deduplicate (single two‑phase workflow)
* **Phase 1 – Assign canonical destinations**  
  Preferred directories (supplied in order on the CLI) become canonical if they already contain the file. For everything else, the canonical path is composed as `<target_root>/<YYYY>/<MM>/filename.ext`.
* **Phase 2 – Realise canonical layout**  
  Move files to canonical paths and leave symlinks behind at every original location.

### Revert
* Walk the database, detect where each copy currently lives (original path _or_ canonical path) and move back so that every *original_path* contains a physical file again, removing any symlinks encountered.
* Works from any partial/interrupted state.

### Report
* Pretty‑print database contents or export to CSV.

---

## Source‑Code Directory Layout

```
image‑organizer/                  ← project root (importable package `imgtool`)
│
├── imgtool/                      ← **package**
│   ├── __init__.py               (exposes high‑level API)
│   ├── cli.py                    (CLI argument parsing & dispatch)
│   ├── database.py               (SQLite layer)
│   ├── scanner.py                (FileScanner class)
│   ├── organizer.py              (FileOrganizer class)
│   ├── deduplicator.py           (FileDeduplicator class)
│   ├── reverter.py               (FileReverter class)
│   ├── reporter.py               (ReportGenerator class)
│   └── utils/
│        ├── __init__.py
│        ├── hashing.py           (checksum helpers)
│        └── exif.py              (timestamp extraction helpers)
│
├── tests/                        ← **pytest** test‑suite
│   ├── conftest.py               (shared fixtures & temp file trees)
│   ├── test_scanner.py           (unit + integration tests for scanning)
│   ├── test_organizer.py         (tests canonical path assignment)
│   ├── test_deduplicator.py      (tests symlink replacement logic)
│   ├── test_reverter.py          (tests full rollback)
│   ├── test_reporter.py          (tests report output)
│   └── test_cli.py               (tests end‑to‑end CLI flows with `CliRunner`)
│
├── scripts/
│   └── run_dev.sh                (lint, type‑check, tests shortcut)
│
├── requirements.txt              (runtime deps)
├── dev‑requirements.txt          (dev extras: pytest, mypy, black, ruff, coverage)
├── setup.cfg / pyproject.toml    (package metadata & tooling configs)
└── README.md
```

---

## Detailed Module & Class Design

### `imgtool.database`
| Function / Method | Purpose |
| ----------------- | ------- |
| `class Database`  | Thin wrapper around SQLite connection; context‑manager aware. |
| `__init__(self, db_path: Path)` | Ensure schema (`files`, `file_paths`) exists. |
| `add_or_update_file(self, checksum, timestamp, canonical_path)` | Upsert into `files`. |
| `record_path(self, checksum, path)` | Insert row into `file_paths` if not present. |
| `iter_all_files()` | Yield joined view of file + paths. |
| `iter_physical_copies(checksum)` | Return list of on‑disk paths for given checksum. |
| `close()` | Explicit close (optional due to context‑manager). |

### `imgtool.scanner`
| Element | Purpose |
| ------- | ------- |
| `class FileScanner` | High‑level façade used by CLI. |
| `scan_directories(self, roots: list[Path])` | Walks, filters by extension, calls helpers. |
| `_calculate_checksum(path)` | Stream SHA‑256 using 1 MiB chunks. |
| `_extract_timestamp(path)` | Uses `utils.exif.get_timestamp` else `path.stat().st_mtime`. |

### `imgtool.organizer`
| Element | Purpose |
| ------- | ------- |
| `class FileOrganizer` | Determines canonical destinations & moves files. |
| `resolve_destinations(self, preferred: list[Path], target_root: Path)` | Fills `canonical_path` in DB. |
| `realize(self)` | Physically moves files and drops symlinks. | 

### `imgtool.deduplicator`
| Element | Purpose |
| ------- | ------- |
| `class FileDeduplicator` | Second pass that converts remaining duplicate copies to symlinks targeting canonical file. |
| `deduplicate(self)` | For every *checksum* with >1 physical copy: leave canonical untouched; others → replace with symlink. |

### `imgtool.reverter`
| Element | Purpose |
| ------- | ------- |
| `class FileReverter` | Undo all operations regardless of current partial state. |
| `revert(self)` | Walk DB, for each *original_path*: if symlink, remove and copy back; if canonical file missing, move physical file back. |

### `imgtool.reporter`
| Element | Purpose |
| ------- | ------- |
| `class ReportGenerator` | Human‑readable & CSV/JSON reporting. |
| `generate(self, format='table')` | Pretty‑table to stdout or writes CSV/JSON to file. |

### `imgtool.cli`
* Uses **argparse**.
* Sub‑commands: `scan`, `organize`, `deduplicate`, `revert`, `report`.
* Dispatches to corresponding classes.

---

## Unit‑Test Map

| Test file | Units covered | Key test‑case names |
| --------- | ------------- | ------------------- |
| `test_scanner.py` | `FileScanner` | `test_checksum_consistency`, `test_timestamp_exif_vs_stat`, `test_skip_existing_in_db` |
| `test_organizer.py` | `FileOrganizer` | `test_preferred_priority_order`, `test_target_dir_yyyy_mm`, `test_symlink_creation` |
| `test_deduplicator.py` | `FileDeduplicator` | `test_symlink_replacement`, `test_idempotent_on_symlinks` |
| `test_reverter.py` | `FileReverter` | `test_full_revert_cycle`, `test_revert_from_partial_state` |
| `test_reporter.py` | `ReportGenerator` | `test_table_output_matches_db`, `test_csv_export` |
| `test_cli.py` | `cli.py` (end‑to‑end) | `test_scan_and_organize_flow`, `test_revert_flow`, `test_interrupt_and_resume` |

Fixtures in **`conftest.py`**
* `tmp_media_tree` – Builds a temporary directory tree with duplicates & EXIF metadata.
* `db` – Yields a temporary Database instance bound to the fixture tree.

Run tests with:
```bash
pytest -q --cov=imgtool tests/
```

---

## Testing Strategy (expanded)

1. **Unit tests** focus on pure functions & class methods (`_calculate_checksum`, `_extract_timestamp`).
2. **Integration tests** build a `tmp_media_tree`, execute CLI sub‑commands via `CliRunner`, and verify both filesystem and DB states.
3. **Concurrency / interruption** simulated with `KeyboardInterrupt` injection and subsequent resume run.
4. **Edge cases** cover read‑only files, EXIF‑less images, MOV files without metadata, broken symlinks.

---

## Logging
* Standard `logging` configured in `imgtool.__init__.py` (rotating file handler → `imgtool.log`, level INFO; `‑‑verbose` CLI flag raises level to DEBUG).

---

## Performance Notes
* Hashing is the hot path – streamed reads (1 MiB) keep memory constant.
* SQLite single‑connection shared via `Database` context to avoid file‑locking overhead.
* Future optimisation hooks: multiprocessing pool in `FileScanner.scan_directories` guarded by `if os.cpu_count() > 1`.

---

## Dependencies
* Runtime: `pillow`, `piexif` (EXIF helper), `sqlite3` (stdlib), `click` (CLI).
* Dev: `pytest`, `pytest‑cov`, `black`, `ruff`, `mypy`.

---

## Development Notes
* 100 % type‑annotated (`mypy --strict` passes).
* `black` & `ruff` ensure consistent style.
* CI pipeline (GH Actions) runs lint → type‑check → tests.

---

_End of developer‑oriented specification._

