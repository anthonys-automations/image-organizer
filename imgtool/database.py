"""SQLite database layer for image organizer."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class Database:
    """Thin wrapper around SQLite connection with context manager support."""
    
    def __init__(self, db_path: Path) -> None:
        """
        Initialize database connection and ensure schema exists.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self._ensure_schema()
    
    def _ensure_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS files (
                    checksum TEXT PRIMARY KEY,
                    timestamp TEXT,
                    canonical_path TEXT UNIQUE NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS file_paths (
                    checksum TEXT NOT NULL,
                    path TEXT NOT NULL,
                    is_symlink BOOLEAN DEFAULT FALSE,
                    PRIMARY KEY (checksum, path),
                    FOREIGN KEY (checksum) REFERENCES files (checksum)
                );
                
                CREATE INDEX IF NOT EXISTS idx_file_paths_checksum 
                ON file_paths (checksum);
                
                CREATE INDEX IF NOT EXISTS idx_file_paths_path 
                ON file_paths (path);
            """)
    
    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get database connection with proper setup."""
        if self.connection is None:
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.row_factory = sqlite3.Row
        
        try:
            yield self.connection
        except Exception as e:
            logger.error(f"Database error: {e}")
            raise
    
    def add_or_update_file(
        self, 
        checksum: str, 
        timestamp: Optional[str], 
        canonical_path: str
    ) -> None:
        """
        Upsert file record into files table.
        
        Args:
            checksum: SHA-256 checksum of the file
            timestamp: ISO format timestamp string
            canonical_path: Canonical path for the file
        """
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO files (checksum, timestamp, canonical_path)
                VALUES (?, ?, ?)
            """, (checksum, timestamp, canonical_path))
            conn.commit()
    
    def record_path(self, checksum: str, path: str, is_symlink: bool = False) -> None:
        """
        Insert row into file_paths if not present.
        
        Args:
            checksum: SHA-256 checksum of the file
            path: File path to record
            is_symlink: Whether this path is a symlink
        """
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO file_paths (checksum, path, is_symlink)
                VALUES (?, ?, ?)
            """, (checksum, str(path), is_symlink))
            conn.commit()
    
    def update_path_symlink_status(self, path: str, is_symlink: bool) -> None:
        """
        Update symlink status for a path.
        
        Args:
            path: File path to update
            is_symlink: New symlink status
        """
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE file_paths SET is_symlink = ? WHERE path = ?
            """, (is_symlink, str(path)))
            conn.commit()
    
    def get_file_info(self, checksum: str) -> Optional[sqlite3.Row]:
        """
        Get file information by checksum.
        
        Args:
            checksum: SHA-256 checksum
            
        Returns:
            Row with file info or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM files WHERE checksum = ?
            """, (checksum,))
            return cursor.fetchone()
    
    def get_paths_for_checksum(self, checksum: str) -> List[sqlite3.Row]:
        """
        Get all paths for a given checksum.
        
        Args:
            checksum: SHA-256 checksum
            
        Returns:
            List of rows with path information
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM file_paths WHERE checksum = ?
            """, (checksum,))
            return cursor.fetchall()
    
    def iter_all_files(self) -> Iterator[Tuple[sqlite3.Row, List[sqlite3.Row]]]:
        """
        Yield joined view of file + paths.
        
        Yields:
            Tuple of (file_info, list_of_paths)
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT f.*, fp.path, fp.is_symlink
                FROM files f
                LEFT JOIN file_paths fp ON f.checksum = fp.checksum
                ORDER BY f.checksum, fp.path
            """)
            
            current_file = None
            current_paths = []
            
            for row in cursor:
                if current_file is None or row['checksum'] != current_file['checksum']:
                    if current_file is not None:
                        yield current_file, current_paths
                    
                    current_file = {
                        'checksum': row['checksum'],
                        'timestamp': row['timestamp'],
                        'canonical_path': row['canonical_path']
                    }
                    current_paths = []
                
                if row['path'] is not None:
                    current_paths.append({
                        'path': row['path'],
                        'is_symlink': bool(row['is_symlink'])
                    })
            
            if current_file is not None:
                yield current_file, current_paths
    
    def iter_physical_copies(self, checksum: str) -> List[str]:
        """
        Return list of on-disk paths for given checksum.
        
        Args:
            checksum: SHA-256 checksum
            
        Returns:
            List of physical file paths (excluding symlinks)
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT path FROM file_paths 
                WHERE checksum = ? AND is_symlink = FALSE
            """, (checksum,))
            return [row['path'] for row in cursor.fetchall()]
    
    def get_duplicate_checksums(self) -> List[str]:
        """
        Get checksums that have multiple physical copies.
        
        Returns:
            List of checksums with duplicates
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT checksum FROM file_paths 
                WHERE is_symlink = FALSE
                GROUP BY checksum 
                HAVING COUNT(*) > 1
            """)
            return [row['checksum'] for row in cursor.fetchall()]
    
    def close(self) -> None:
        """Explicit close (optional due to context-manager)."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def __enter__(self) -> 'Database':
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close() 