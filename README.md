# Image Organizer Tool

A powerful Python tool for organizing and deduplicating image and video files using SHA-256 checksums and intelligent file management.

## Features

- **Smart File Discovery**: Recursively scans directories for image and video files
- **Deduplication**: Identifies and manages duplicate files using SHA-256 checksums
- **EXIF Support**: Extracts timestamps from image metadata or falls back to filesystem timestamps
- **Flexible Organization**: Organizes files into YYYY/MM structure or preserves preferred directories
- **Symlink Management**: Creates symlinks for duplicates to save disk space
- **Safe Reversion**: Complete rollback capability to restore original file structure
- **Comprehensive Reporting**: Generate reports in table, CSV, or JSON formats

## Supported File Types

- **Images**: JPG, JPEG, PNG, GIF, TIFF, BMP, WebP, CR2, NEF, ARW, DNG
- **Videos**: MOV, MP4, AVI, MKV, WMV, FLV, M4V, 3GP, WebM

## Installation

### Prerequisites

- Python 3.8 or higher
- pip

### Install Dependencies

```bash
# Install runtime dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r dev-requirements.txt
```

### Install Package

```bash
# Install in development mode
pip install -e .

# Or install globally
pip install .
```

## Usage

### Basic Workflow

1. **Scan directories** to index files:
   ```bash
   imgtool scan /path/to/photos /path/to/videos
   ```

2. **Organize files** into canonical structure:
   ```bash
   imgtool organize --preferred /path/to/keep --target /path/to/organized
   ```

3. **Deduplicate** remaining files:
   ```bash
   imgtool deduplicate
   ```

4. **Generate reports**:
   ```bash
   imgtool report --format table
   imgtool report --format csv --output report.csv
   imgtool report --format json --output report.json
   ```

5. **Revert changes** if needed:
   ```bash
   imgtool revert
   ```

### Command Reference

#### Scan Command
```bash
imgtool scan [OPTIONS] DIRECTORIES...
```
Scans directories recursively and indexes files in the database.

#### Organize Command
```bash
imgtool organize [OPTIONS] --preferred DIRECTORIES... --target PATH
```
Organizes files into canonical structure, preserving preferred directories.

#### Deduplicate Command
```bash
imgtool deduplicate [OPTIONS]
```
Converts duplicate files to symlinks, keeping one physical copy.

#### Report Command
```bash
imgtool report [OPTIONS] [--format {table,csv,json}] [--output PATH]
```
Generates database reports in various formats.

#### Revert Command
```bash
imgtool revert [OPTIONS] [--partial]
```
Reverts all operations, restoring original file structure.

### Global Options

- `--db PATH`: Database file path (default: imgtool.db)
- `--verbose, -v`: Enable verbose logging

## Examples

### Organize Family Photos
```bash
# Scan all photo directories
imgtool scan ~/Pictures ~/Downloads/photos ~/Desktop/camera

# Organize with preferred backup location
imgtool organize --preferred ~/Pictures/backup --target ~/Pictures/organized

# Deduplicate to save space
imgtool deduplicate

# Generate report
imgtool report --format table
```

### Revert Changes
```bash
# If something goes wrong, revert everything
imgtool revert
```

### Partial State Recovery
```bash
# If interrupted, recover from partial state
imgtool revert --partial
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone <repository-url>
cd image-organizer

# Install in development mode
pip install -e .

# Install development dependencies
pip install -r dev-requirements.txt
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=imgtool tests/

# Run specific test file
pytest tests/test_scanner.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Run development script (lint, type-check, test)
./scripts/run_dev.sh

# Or run individually:
ruff check .          # Linting
black --check .       # Code formatting
mypy imgtool/         # Type checking
```

### Project Structure

```
image-organizer/
├── imgtool/                 # Main package
│   ├── __init__.py         # Package initialization and API
│   ├── cli.py              # Command-line interface
│   ├── database.py         # SQLite database layer
│   ├── scanner.py          # File scanning and indexing
│   ├── organizer.py        # File organization
│   ├── deduplicator.py     # Deduplication logic
│   ├── reverter.py         # Reversion functionality
│   ├── reporter.py         # Report generation
│   └── utils/              # Utility modules
│       ├── __init__.py
│       ├── hashing.py      # Checksum calculation
│       └── exif.py         # EXIF timestamp extraction
├── tests/                  # Test suite
│   ├── conftest.py         # Shared fixtures
│   ├── test_scanner.py     # Scanner tests
│   ├── test_organizer.py   # Organizer tests
│   ├── test_deduplicator.py # Deduplicator tests
│   ├── test_reverter.py    # Reverter tests
│   ├── test_reporter.py    # Reporter tests
│   └── test_cli.py         # CLI tests
├── scripts/                # Development scripts
│   └── run_dev.sh          # Development workflow
├── docs/                   # Documentation
├── requirements.txt        # Runtime dependencies
├── dev-requirements.txt    # Development dependencies
├── pyproject.toml         # Package configuration
└── README.md              # This file
```

## Database Schema

The tool uses SQLite with two main tables:

### `files` table
- `checksum` (TEXT, PRIMARY KEY): SHA-256 hash of file content
- `timestamp` (TEXT): ISO format timestamp from EXIF or filesystem
- `canonical_path` (TEXT, UNIQUE): Canonical location for the file

### `file_paths` table
- `checksum` (TEXT): Foreign key to files table
- `path` (TEXT): File path
- `is_symlink` (BOOLEAN): Whether this path is a symlink
- Primary key: (checksum, path)

## Performance Notes

- **Hashing**: Uses streaming reads (1 MiB chunks) to keep memory usage constant
- **Database**: Single SQLite connection shared via context manager
- **Future**: Multiprocessing support planned for large directories

## Dependencies

### Runtime
- `pillow`: Image processing and EXIF support
- `piexif`: EXIF metadata extraction
- `click`: Command-line interface (optional, can use argparse)

### Development
- `pytest`: Testing framework
- `pytest-cov`: Coverage reporting
- `black`: Code formatting
- `ruff`: Linting
- `mypy`: Type checking

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the development script: `./scripts/run_dev.sh`
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the documentation in `docs/`
2. Search existing issues
3. Create a new issue with detailed information

## Roadmap

- [ ] Multiprocessing support for large directories
- [ ] Web interface for file management
- [ ] Cloud storage integration
- [ ] Advanced duplicate detection algorithms
- [ ] Batch processing capabilities 