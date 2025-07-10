"""Image Organizer Tool - Manage and deduplicate image/video files."""

import logging
import logging.handlers
from pathlib import Path
from typing import List

from .database import Database
from .scanner import FileScanner
from .organizer import FileOrganizer
from .deduplicator import FileDeduplicator
from .reverter import FileReverter
from .reporter import ReportGenerator

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create rotating file handler
log_file = Path("imgtool.log")
handler = logging.handlers.RotatingFileHandler(
    log_file, maxBytes=1024 * 1024, backupCount=5
)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

__version__ = "1.0.0"

__all__ = [
    "Database",
    "FileScanner",
    "FileOrganizer",
    "FileDeduplicator",
    "FileReverter",
    "ReportGenerator",
    "scan_directories",
    "organize_files",
    "deduplicate_files",
    "revert_operations",
    "generate_report",
]


def scan_directories(
    roots: List[Path], db_path: Path = Path("imgtool.db")
) -> None:
    """Scan directories and index files in the database."""
    with Database(db_path) as db:
        scanner = FileScanner(db)
        scanner.scan_directories(roots)


def organize_files(
    preferred_dirs: List[Path],
    target_root: Path,
    db_path: Path = Path("imgtool.db"),
) -> None:
    """Organize files into canonical structure."""
    with Database(db_path) as db:
        organizer = FileOrganizer(db)
        organizer.resolve_destinations(preferred_dirs, target_root)
        organizer.realize()


def deduplicate_files(db_path: Path = Path("imgtool.db")) -> None:
    """Deduplicate files by creating symlinks."""
    with Database(db_path) as db:
        deduplicator = FileDeduplicator(db)
        deduplicator.deduplicate()


def revert_operations(db_path: Path = Path("imgtool.db")) -> None:
    """Revert all operations, restoring original file structure."""
    with Database(db_path) as db:
        reverter = FileReverter(db)
        reverter.revert()


def generate_report(
    db_path: Path = Path("imgtool.db"),
    format: str = "table",
    output_file: Path | None = None,
) -> None:
    """Generate a report of the database contents."""
    with Database(db_path) as db:
        reporter = ReportGenerator(db)
        reporter.generate(format, output_file) 