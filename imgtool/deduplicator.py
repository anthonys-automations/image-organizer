"""File deduplication functionality."""

import shutil
from pathlib import Path
import logging

from .database import Database

logger = logging.getLogger(__name__)


class FileDeduplicator:
    """Second pass that converts remaining duplicate copies to symlinks."""
    
    def __init__(self, database: Database) -> None:
        """
        Initialize deduplicator with database connection.
        
        Args:
            database: Database instance
        """
        self.database = database
    
    def deduplicate(self) -> None:
        """
        For every checksum with >1 physical copy: leave canonical untouched; 
        others → replace with symlink.
        """
        logger.info("Starting deduplication process")
        
        # Get all checksums with multiple physical copies
        duplicate_checksums = self.database.get_duplicate_checksums()
        
        if not duplicate_checksums:
            logger.info("No duplicates found")
            return
        
        logger.info(f"Found {len(duplicate_checksums)} checksums with duplicates")
        
        for checksum in duplicate_checksums:
            self._deduplicate_checksum(checksum)
        
        logger.info("Deduplication completed")
    
    def _deduplicate_checksum(self, checksum: str) -> None:
        """
        Deduplicate all copies of a specific checksum.
        
        Args:
            checksum: SHA-256 checksum to deduplicate
        """
        # Get file info
        file_info = self.database.get_file_info(checksum)
        if not file_info:
            logger.warning(f"No file info found for checksum: {checksum}")
            return
        
        canonical_path = Path(file_info['canonical_path'])
        
        # Get all physical copies
        physical_copies = self.database.iter_physical_copies(checksum)
        
        if len(physical_copies) <= 1:
            return  # No duplicates
        
        logger.debug(f"Deduplicating {len(physical_copies)} copies of {checksum}")
        
        # Find the canonical copy (prefer one that's already at canonical path)
        canonical_copy = None
        other_copies = []
        
        for copy_path in physical_copies:
            copy_path_obj = Path(copy_path)
            if copy_path_obj == canonical_path:
                canonical_copy = copy_path
            else:
                other_copies.append(copy_path)
        
        # If no copy is at canonical path, move one there
        if not canonical_copy:
            if other_copies:
                canonical_copy = other_copies[0]
                other_copies = other_copies[1:]
                
                # Ensure canonical directory exists
                canonical_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Move file to canonical location
                try:
                    shutil.move(canonical_copy, canonical_path)
                    canonical_copy = str(canonical_path)
                    logger.debug(f"Moved {canonical_copy} to canonical location")
                except Exception as e:
                    logger.error(f"Failed to move {canonical_copy} to canonical location: {e}")
                    return
        
        # Replace other copies with symlinks
        for copy_path in other_copies:
            try:
                copy_path_obj = Path(copy_path)
                
                if copy_path_obj.exists():
                    # Check if it's already a symlink
                    if copy_path_obj.is_symlink():
                        # Remove existing symlink and create new one
                        copy_path_obj.unlink()
                        copy_path_obj.symlink_to(canonical_path)
                        logger.debug(f"Updated symlink: {copy_path} -> {canonical_path}")
                    else:
                        # Remove file and create symlink
                        copy_path_obj.unlink()
                        copy_path_obj.symlink_to(canonical_path)
                        
                        # Update database
                        self.database.update_path_symlink_status(copy_path, True)
                        logger.debug(f"Created symlink: {copy_path} -> {canonical_path}")
                        
            except Exception as e:
                logger.error(f"Failed to create symlink for {copy_path}: {e}")
    
    def is_idempotent(self) -> bool:
        """
        Check if deduplication is idempotent (safe to run multiple times).
        
        Returns:
            True if safe to run again, False otherwise
        """
        duplicate_checksums = self.database.get_duplicate_checksums()
        return len(duplicate_checksums) == 0 