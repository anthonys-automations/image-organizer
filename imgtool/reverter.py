"""File reversion functionality."""

import shutil
from pathlib import Path
import logging

from .database import Database

logger = logging.getLogger(__name__)


class FileReverter:
    """Undo all operations regardless of current partial state."""
    
    def __init__(self, database: Database) -> None:
        """
        Initialize reverter with database connection.
        
        Args:
            database: Database instance
        """
        self.database = database
    
    def revert(self) -> None:
        """
        Walk DB, for each original_path: if symlink, remove and copy back; 
        if canonical file missing, move physical file back.
        """
        logger.info("Starting reversion process")
        
        # Get all files and their paths
        for file_info, paths in self.database.iter_all_files():
            checksum = file_info['checksum']
            canonical_path = Path(file_info['canonical_path'])
            
            logger.debug(f"Reverting file: {checksum}")
            
            # Find the physical copy (canonical or other)
            physical_copy = self._find_physical_copy(canonical_path, paths)
            
            if not physical_copy:
                logger.warning(f"No physical copy found for checksum: {checksum}")
                continue
            
            # Process each path for this file
            for path_info in paths:
                path = Path(path_info['path'])
                is_symlink = path_info['is_symlink']
                
                if is_symlink:
                    # Remove symlink and copy physical file back
                    self._restore_from_symlink(path, physical_copy)
                else:
                    # Ensure physical file exists at this location
                    self._ensure_physical_file(path, physical_copy)
        
        logger.info("Reversion completed")
    
    def _find_physical_copy(
        self, 
        canonical_path: Path, 
        paths: list
    ) -> Path | None:
        """
        Find a physical copy of the file (not a symlink).
        
        Args:
            canonical_path: Canonical path for the file
            paths: List of path information dictionaries
            
        Returns:
            Path to physical file, or None if not found
        """
        # First check canonical path
        if canonical_path.exists() and not canonical_path.is_symlink():
            return canonical_path
        
        # Check other paths
        for path_info in paths:
            path = Path(path_info['path'])
            is_symlink = path_info['is_symlink']
            
            if not is_symlink and path.exists():
                return path
        
        return None
    
    def _restore_from_symlink(self, symlink_path: Path, source_path: Path) -> None:
        """
        Remove symlink and copy physical file back to original location.
        
        Args:
            symlink_path: Path where symlink currently exists
            source_path: Path to physical file to copy from
        """
        try:
            if symlink_path.exists():
                if symlink_path.is_symlink():
                    # Remove symlink
                    symlink_path.unlink()
                    logger.debug(f"Removed symlink: {symlink_path}")
                else:
                    # Remove regular file
                    symlink_path.unlink()
                    logger.debug(f"Removed file: {symlink_path}")
            
            # Copy physical file back
            shutil.copy2(source_path, symlink_path)
            
            # Update database
            self.database.update_path_symlink_status(str(symlink_path), False)
            
            logger.debug(f"Restored physical file: {symlink_path}")
            
        except Exception as e:
            logger.error(f"Failed to restore {symlink_path}: {e}")
    
    def _ensure_physical_file(self, target_path: Path, source_path: Path) -> None:
        """
        Ensure physical file exists at target location.
        
        Args:
            target_path: Path where file should exist
            source_path: Path to physical file to copy from
        """
        try:
            if not target_path.exists():
                # Copy file to target location
                shutil.copy2(source_path, target_path)
                logger.debug(f"Copied file to: {target_path}")
            elif target_path.is_symlink():
                # Remove symlink and copy physical file
                target_path.unlink()
                shutil.copy2(source_path, target_path)
                
                # Update database
                self.database.update_path_symlink_status(str(target_path), False)
                
                logger.debug(f"Replaced symlink with physical file: {target_path}")
                
        except Exception as e:
            logger.error(f"Failed to ensure physical file at {target_path}: {e}")
    
    def revert_from_partial_state(self) -> None:
        """
        Revert from any partial/interrupted state.
        
        This method handles cases where the organization process was interrupted
        and some files may be in an inconsistent state.
        """
        logger.info("Reverting from partial state")
        
        # First, identify any broken symlinks and fix them
        self._fix_broken_symlinks()
        
        # Then perform normal reversion
        self.revert()
    
    def _fix_broken_symlinks(self) -> None:
        """Fix any broken symlinks by finding their targets."""
        logger.info("Fixing broken symlinks")
        
        for file_info, paths in self.database.iter_all_files():
            checksum = file_info['checksum']
            
            # Find all symlinks for this file
            symlinks = []
            physical_copies = []
            
            for path_info in paths:
                path = Path(path_info['path'])
                is_symlink = path_info['is_symlink']
                
                if is_symlink:
                    symlinks.append(path)
                else:
                    physical_copies.append(path)
            
            # Fix broken symlinks
            for symlink_path in symlinks:
                if symlink_path.exists() and symlink_path.is_symlink():
                    try:
                        # Check if symlink is broken
                        symlink_path.resolve()
                    except (OSError, RuntimeError):
                        # Symlink is broken, fix it
                        if physical_copies:
                            target = physical_copies[0]
                            symlink_path.unlink()
                            symlink_path.symlink_to(target)
                            logger.debug(f"Fixed broken symlink: {symlink_path} -> {target}")
                elif not symlink_path.exists():
                    # Symlink doesn't exist, recreate it
                    if physical_copies:
                        target = physical_copies[0]
                        symlink_path.symlink_to(target)
                        logger.debug(f"Recreated missing symlink: {symlink_path} -> {target}") 