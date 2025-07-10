"""Tests for the FileOrganizer class."""

import datetime
from pathlib import Path
import pytest

from imgtool.organizer import FileOrganizer
from imgtool.database import Database
from imgtool.scanner import FileScanner


class TestFileOrganizer:
    """Test cases for FileOrganizer class."""
    
    def test_preferred_priority_order(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that preferred directories are used in priority order."""
        # Scan files first
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        
        # Set up preferred directories in specific order
        preferred_dirs = [
            tmp_media_tree / "backup",  # Should be preferred
            tmp_media_tree / "photos",  # Should be second choice
        ]
        target_root = tmp_media_tree / "organized"
        
        # Resolve destinations
        organizer.resolve_destinations(preferred_dirs, target_root)
        
        # Check that files in preferred directories keep their paths
        for file_info, paths in db.iter_all_files():
            checksum = file_info['checksum']
            canonical_path = file_info['canonical_path']
            
            # Find if any path is in preferred directory
            in_preferred = any(
                str(preferred_dirs[0]) in path['path'] 
                for path in paths
            )
            
            if in_preferred:
                # Should use preferred path as canonical
                assert str(preferred_dirs[0]) in canonical_path
    
    def test_target_dir_yyyy_mm(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that files are organized into YYYY/MM structure."""
        # Scan files first
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        
        # No preferred directories, so should use target structure
        preferred_dirs = []
        target_root = tmp_media_tree / "organized"
        
        # Resolve destinations
        organizer.resolve_destinations(preferred_dirs, target_root)
        
        # Check that canonical paths follow YYYY/MM structure
        for file_info, paths in db.iter_all_files():
            canonical_path = Path(file_info['canonical_path'])
            
            # Should be under target root
            assert target_root in canonical_path.parents
            
            # Should have YYYY/MM structure
            relative_path = canonical_path.relative_to(target_root)
            path_parts = relative_path.parts
            
            if len(path_parts) >= 3:  # YYYY/MM/filename
                year = path_parts[0]
                month = path_parts[1]
                
                # Check format
                assert len(year) == 4 and year.isdigit()
                assert len(month) == 2 and month.isdigit()
                assert 1 <= int(month) <= 12
    
    def test_symlink_creation(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that symlinks are created for duplicate files."""
        # Scan files first
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        
        # Organize files
        preferred_dirs = []
        target_root = tmp_media_tree / "organized"
        
        organizer.resolve_destinations(preferred_dirs, target_root)
        organizer.realize()
        
        # Check that symlinks were created
        symlink_count = 0
        for file_info, paths in db.iter_all_files():
            for path_info in paths:
                if path_info['is_symlink']:
                    symlink_count += 1
                    path = Path(path_info['path'])
                    
                    # Should be a symlink
                    assert path.is_symlink()
                    
                    # Should point to canonical path
                    canonical_path = Path(file_info['canonical_path'])
                    assert path.resolve() == canonical_path.resolve()
        
        # Should have created some symlinks for duplicates
        assert symlink_count > 0
    
    def test_canonical_path_generation(self, db: Database, tmp_media_tree: Path) -> None:
        """Test canonical path generation with timestamps."""
        # Create a file with known timestamp
        test_file = tmp_media_tree / "test_photo.jpg"
        test_file.write_bytes(b"test_content")
        
        # Set specific timestamp
        expected_time = datetime.datetime(2023, 6, 15, 10, 30, 0)
        timestamp = expected_time.timestamp()
        import os
        os.utime(test_file, (timestamp, timestamp))
        
        # Scan the file
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        
        # Organize
        preferred_dirs = []
        target_root = tmp_media_tree / "organized"
        
        organizer.resolve_destinations(preferred_dirs, target_root)
        
        # Check canonical path
        for file_info, paths in db.iter_all_files():
            if "test_photo.jpg" in file_info['canonical_path']:
                canonical_path = Path(file_info['canonical_path'])
                expected_path = target_root / "2023" / "06" / "test_photo.jpg"
                assert canonical_path == expected_path
                break
    
    def test_preferred_directory_scanning(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that preferred directories are properly scanned for existing files."""
        # Create a file in a preferred directory
        preferred_dir = tmp_media_tree / "preferred"
        preferred_dir.mkdir()
        preferred_file = preferred_dir / "special_photo.jpg"
        preferred_file.write_bytes(b"special_content")
        
        # Create same content in another location
        other_file = tmp_media_tree / "other_photo.jpg"
        other_file.write_bytes(b"special_content")
        
        # Scan all directories
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        
        # Set preferred directory
        preferred_dirs = [preferred_dir]
        target_root = tmp_media_tree / "organized"
        
        organizer.resolve_destinations(preferred_dirs, target_root)
        
        # Check that preferred file location is used as canonical
        for file_info, paths in db.iter_all_files():
            if "special_content" in str(file_info['canonical_path']):
                canonical_path = file_info['canonical_path']
                assert str(preferred_dir) in canonical_path
                break
    
    def test_file_movement(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that files are moved to canonical locations."""
        # Scan files first
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        
        # Organize files
        preferred_dirs = []
        target_root = tmp_media_tree / "organized"
        
        organizer.resolve_destinations(preferred_dirs, target_root)
        organizer.realize()
        
        # Check that files exist at canonical locations
        for file_info, paths in db.iter_all_files():
            canonical_path = Path(file_info['canonical_path'])
            
            # Canonical file should exist
            assert canonical_path.exists()
            assert not canonical_path.is_symlink()
            
            # Should be a physical file
            assert canonical_path.is_file()
    
    def test_directory_creation(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that target directories are created as needed."""
        # Scan files first
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        
        # Use a target root that doesn't exist
        target_root = tmp_media_tree / "new_organized"
        preferred_dirs = []
        
        # This should create the directory structure
        organizer.resolve_destinations(preferred_dirs, target_root)
        organizer.realize()
        
        # Target root should exist
        assert target_root.exists()
        assert target_root.is_dir()
        
        # Should have created year/month directories
        year_dirs = list(target_root.iterdir())
        assert len(year_dirs) > 0
        
        for year_dir in year_dirs:
            assert year_dir.is_dir()
            month_dirs = list(year_dir.iterdir())
            assert len(month_dirs) > 0
    
    def test_duplicate_handling(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that duplicates are handled correctly during organization."""
        # Scan files first
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        
        # Organize files
        preferred_dirs = []
        target_root = tmp_media_tree / "organized"
        
        organizer.resolve_destinations(preferred_dirs, target_root)
        organizer.realize()
        
        # Check that duplicates are properly handled
        checksum_to_paths = {}
        for file_info, paths in db.iter_all_files():
            checksum = file_info['checksum']
            if checksum not in checksum_to_paths:
                checksum_to_paths[checksum] = []
            checksum_to_paths[checksum].extend([p['path'] for p in paths])
        
        # For each duplicate, should have one physical copy and rest as symlinks
        for checksum, paths in checksum_to_paths.items():
            if len(paths) > 1:
                physical_count = 0
                symlink_count = 0
                
                for path in paths:
                    path_obj = Path(path)
                    if path_obj.is_symlink():
                        symlink_count += 1
                    else:
                        physical_count += 1
                
                # Should have exactly one physical copy
                assert physical_count == 1
                # Should have symlinks for the rest
                assert symlink_count == len(paths) - 1 