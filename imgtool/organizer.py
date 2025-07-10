"""File organization and canonical path management."""

import datetime
import shutil
from pathlib import Path
from typing import List
import logging

from .database import Database

logger = logging.getLogger(__name__)


class FileOrganizer:
    """Determines canonical destinations and moves files."""
    
    def __init__(self, database: Database) -> None:
        """
        Initialize organizer with database connection.
        
        Args:
            database: Database instance
        """
        self.database = database
    
    def resolve_destinations(
        self, 
        preferred_dirs: List[Path], 
        target_root: Path
    ) -> None:
        """
        Phase 1: Assign canonical destinations for all files.
        
        Preferred directories (supplied in order on the CLI) become canonical 
        if they already contain the file. For everything else, the canonical 
        path is composed as <target_root>/<YYYY>/<MM>/filename.ext.
        
        Args:
            preferred_dirs: List of preferred directories in priority order
            target_root: Root directory for organizing files
        """
        logger.info("Phase 1: Resolving canonical destinations")
        
        # Get all files from database
        for file_info, paths in self.database.iter_all_files():
            checksum = file_info['checksum']
            current_canonical = file_info['canonical_path']
            timestamp_str = file_info['timestamp']
            
            # Check if any preferred directory contains this file
            preferred_canonical = self._find_preferred_canonical(
                checksum, preferred_dirs
            )
            
            if preferred_canonical:
                # Use preferred directory as canonical
                new_canonical = str(preferred_canonical)
                logger.debug(f"Using preferred canonical for {checksum}: {new_canonical}")
            else:
                # Generate canonical path based on timestamp and target root
                new_canonical = self._generate_canonical_path(
                    current_canonical, timestamp_str, target_root
                )
                logger.debug(f"Generated canonical for {checksum}: {new_canonical}")
            
            # Update canonical path in database
            self.database.add_or_update_file(
                checksum, timestamp_str, new_canonical
            )
        
        logger.info("Phase 1 completed: Canonical destinations assigned")
    
    def realize(self) -> None:
        """
        Phase 2: Realize canonical layout.
        
        Move files to canonical paths and leave symlinks behind at every 
        original location.
        """
        logger.info("Phase 2: Realizing canonical layout")
        
        for file_info, paths in self.database.iter_all_files():
            checksum = file_info['checksum']
            canonical_path = Path(file_info['canonical_path'])
            
            # Get all physical copies of this file
            physical_copies = self.database.iter_physical_copies(checksum)
            
            if not physical_copies:
                logger.warning(f"No physical copies found for checksum: {checksum}")
                continue
            
            # Find the best source file (prefer one that's already at canonical path)
            source_path = self._find_best_source(canonical_path, physical_copies)
            
            if not source_path:
                logger.warning(f"No suitable source found for checksum: {checksum}")
                continue
            
            # Ensure canonical directory exists
            canonical_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move source to canonical location if not already there
            if Path(source_path) != canonical_path:
                try:
                    shutil.move(source_path, canonical_path)
                    logger.debug(f"Moved {source_path} to {canonical_path}")
                except Exception as e:
                    logger.error(f"Failed to move {source_path} to {canonical_path}: {e}")
                    continue
            
            # Create symlinks for all other copies
            for copy_path in physical_copies:
                if copy_path != str(canonical_path):
                    try:
                        copy_path_obj = Path(copy_path)
                        if copy_path_obj.exists():
                            # Remove existing file and create symlink
                            copy_path_obj.unlink()
                            copy_path_obj.symlink_to(canonical_path)
                            
                            # Update database
                            self.database.update_path_symlink_status(copy_path, True)
                            logger.debug(f"Created symlink: {copy_path} -> {canonical_path}")
                    except Exception as e:
                        logger.error(f"Failed to create symlink {copy_path}: {e}")
        
        logger.info("Phase 2 completed: Canonical layout realized")
    
    def _find_preferred_canonical(
        self, 
        checksum: str, 
        preferred_dirs: List[Path]
    ) -> Path | None:
        """
        Find if any preferred directory contains a file with this checksum.
        
        Args:
            checksum: SHA-256 checksum to search for
            preferred_dirs: List of preferred directories in priority order
            
        Returns:
            Path to file in preferred directory, or None if not found
        """
        for preferred_dir in preferred_dirs:
            if not preferred_dir.exists() or not preferred_dir.is_dir():
                continue
            
            # Check if any file in this directory matches the checksum
            for file_path in preferred_dir.rglob("*"):
                if file_path.is_file():
                    try:
                        from .utils.hashing import calculate_sha256
                        file_checksum = calculate_sha256(file_path)
                        if file_checksum == checksum:
                            return file_path
                    except Exception:
                        continue
        
        return None
    
    def _generate_canonical_path(
        self, 
        current_path: str, 
        timestamp_str: str | None, 
        target_root: Path
    ) -> str:
        """
        Generate canonical path based on timestamp and target root.
        
        Args:
            current_path: Current file path
            timestamp_str: ISO format timestamp string
            target_root: Root directory for organizing
            
        Returns:
            Canonical path string
        """
        current_path_obj = Path(current_path)
        filename = current_path_obj.name
        
        if timestamp_str:
            try:
                timestamp = datetime.datetime.fromisoformat(timestamp_str)
                year = str(timestamp.year)
                month = f"{timestamp.month:02d}"
            except ValueError:
                # Fallback to current date if timestamp parsing fails
                now = datetime.datetime.now()
                year = str(now.year)
                month = f"{now.month:02d}"
        else:
            # Fallback to current date if no timestamp
            now = datetime.datetime.now()
            year = str(now.year)
            month = f"{now.month:02d}"
        
        canonical_path = target_root / year / month / filename
        return str(canonical_path)
    
    def _find_best_source(
        self, 
        canonical_path: Path, 
        physical_copies: List[str]
    ) -> str | None:
        """
        Find the best source file from physical copies.
        
        Prefers files that are already at the canonical path.
        
        Args:
            canonical_path: Target canonical path
            physical_copies: List of physical file paths
            
        Returns:
            Best source path, or None if no suitable source found
        """
        # First, check if any copy is already at canonical path
        canonical_str = str(canonical_path)
        for copy_path in physical_copies:
            if copy_path == canonical_str:
                return copy_path
        
        # Otherwise, use the first available copy
        for copy_path in physical_copies:
            if Path(copy_path).exists():
                return copy_path
        
        return None 