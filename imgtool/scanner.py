"""File scanning and indexing functionality."""

import datetime
from pathlib import Path
from typing import List, Set
import logging

from .database import Database
from .utils.hashing import calculate_sha256
from .utils.exif import get_timestamp

logger = logging.getLogger(__name__)


class FileScanner:
    """High-level façade for scanning and indexing files."""
    
    # Supported file extensions (case-insensitive)
    SUPPORTED_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.tiff', '.tif', 
        '.bmp', '.webp', '.cr2', '.nef', '.arw', '.dng',
        '.mov', '.mp4', '.avi', '.mkv', '.wmv', '.flv',
        '.m4v', '.3gp', '.webm'
    }
    
    def __init__(self, database: Database) -> None:
        """
        Initialize scanner with database connection.
        
        Args:
            database: Database instance for storing file information
        """
        self.database = database
        self._scanned_files: Set[str] = set()
    
    def scan_directories(self, roots: List[Path]) -> None:
        """
        Scan directories recursively and index files.
        
        Args:
            roots: List of directory paths to scan
        """
        logger.info(f"Starting scan of {len(roots)} directories")
        
        for root in roots:
            if not root.exists():
                logger.warning(f"Directory does not exist: {root}")
                continue
            
            if not root.is_dir():
                logger.warning(f"Path is not a directory: {root}")
                continue
            
            logger.info(f"Scanning directory: {root}")
            self._scan_directory(root)
        
        logger.info(f"Scan completed. Indexed {len(self._scanned_files)} files")
    
    def _scan_directory(self, directory: Path) -> None:
        """
        Recursively scan a directory for supported files.
        
        Args:
            directory: Directory path to scan
        """
        try:
            for item in directory.iterdir():
                if item.is_file():
                    self._process_file(item)
                elif item.is_dir():
                    self._scan_directory(item)
        except PermissionError:
            logger.warning(f"Permission denied accessing directory: {directory}")
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
    
    def _process_file(self, file_path: Path) -> None:
        """
        Process a single file: check if supported, calculate checksum, extract timestamp.
        
        Args:
            file_path: Path to the file to process
        """
        # Check if file extension is supported
        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return
        
        # Skip if already processed
        file_path_str = str(file_path.resolve())
        if file_path_str in self._scanned_files:
            return
        
        try:
            # Calculate checksum
            checksum = self._calculate_checksum(file_path)
            
            # Extract timestamp
            timestamp = self._extract_timestamp(file_path)
            timestamp_str = timestamp.isoformat() if timestamp else None
            
            # Determine canonical path (will be updated by organizer)
            canonical_path = str(file_path)
            
            # Store in database
            self.database.add_or_update_file(checksum, timestamp_str, canonical_path)
            self.database.record_path(checksum, file_path_str)
            
            self._scanned_files.add(file_path_str)
            logger.debug(f"Indexed: {file_path}")
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """
        Calculate SHA-256 checksum of file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA-256 checksum as hexadecimal string
        """
        return calculate_sha256(file_path)
    
    def _extract_timestamp(self, file_path: Path) -> datetime.datetime | None:
        """
        Extract timestamp from file using EXIF or filesystem.
        
        Args:
            file_path: Path to the file
            
        Returns:
            datetime object if timestamp found, None otherwise
        """
        try:
            return get_timestamp(file_path)
        except ImportError:
            # Fallback to filesystem timestamp if EXIF libraries not available
            try:
                stat = file_path.stat()
                return datetime.datetime.fromtimestamp(stat.st_mtime)
            except (OSError, ValueError):
                return None 