"""Tests for the FileDeduplicator class."""

from pathlib import Path
import pytest

from imgtool.deduplicator import FileDeduplicator
from imgtool.database import Database
from imgtool.scanner import FileScanner
from imgtool.organizer import FileOrganizer


class TestFileDeduplicator:
    """Test cases for FileDeduplicator class."""
    
    def test_symlink_replacement(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that duplicate files are replaced with symlinks."""
        # Set up: scan and organize files
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        organizer.resolve_destinations([], tmp_media_tree / "organized")
        organizer.realize()
        
        # Run deduplication
        deduplicator = FileDeduplicator(db)
        deduplicator.deduplicate()
        
        # Check that duplicates are now symlinks
        for file_info, paths in db.iter_all_files():
            if len(paths) > 1:  # Has duplicates
                physical_count = 0
                symlink_count = 0
                
                for path_info in paths:
                    path = Path(path_info['path'])
                    if path.is_symlink():
                        symlink_count += 1
                    else:
                        physical_count += 1
                
                # Should have exactly one physical copy
                assert physical_count == 1
                # Rest should be symlinks
                assert symlink_count == len(paths) - 1
    
    def test_idempotent_on_symlinks(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that deduplication is idempotent when run multiple times."""
        # Set up: scan and organize files
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        organizer.resolve_destinations([], tmp_media_tree / "organized")
        organizer.realize()
        
        deduplicator = FileDeduplicator(db)
        
        # Run deduplication twice
        deduplicator.deduplicate()
        first_symlink_count = sum(
            1 for file_info, paths in db.iter_all_files()
            for path_info in paths if path_info['is_symlink']
        )
        
        deduplicator.deduplicate()
        second_symlink_count = sum(
            1 for file_info, paths in db.iter_all_files()
            for path_info in paths if path_info['is_symlink']
        )
        
        # Should have same number of symlinks
        assert first_symlink_count == second_symlink_count
    
    def test_canonical_file_preservation(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that canonical files are preserved during deduplication."""
        # Set up: scan and organize files
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        organizer.resolve_destinations([], tmp_media_tree / "organized")
        organizer.realize()
        
        # Record canonical paths before deduplication
        canonical_paths_before = {}
        for file_info, paths in db.iter_all_files():
            canonical_paths_before[file_info['checksum']] = file_info['canonical_path']
        
        # Run deduplication
        deduplicator = FileDeduplicator(db)
        deduplicator.deduplicate()
        
        # Check that canonical paths are preserved
        for file_info, paths in db.iter_all_files():
            checksum = file_info['checksum']
            canonical_path = file_info['canonical_path']
            assert canonical_path == canonical_paths_before[checksum]
            
            # Canonical file should still exist and be physical
            canonical_path_obj = Path(canonical_path)
            assert canonical_path_obj.exists()
            assert not canonical_path_obj.is_symlink()
    
    def test_no_duplicates_handling(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that deduplication handles files without duplicates gracefully."""
        # Create files without duplicates
        unique_files = [
            (tmp_media_tree / "unique1.jpg", b"unique_content_1"),
            (tmp_media_tree / "unique2.png", b"unique_content_2"),
            (tmp_media_tree / "unique3.gif", b"unique_content_3"),
        ]
        
        for file_path, content in unique_files:
            file_path.write_bytes(content)
        
        # Scan and organize
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        organizer.resolve_destinations([], tmp_media_tree / "organized")
        organizer.realize()
        
        # Run deduplication
        deduplicator = FileDeduplicator(db)
        deduplicator.deduplicate()
        
        # Check that unique files are unchanged
        for file_info, paths in db.iter_all_files():
            if "unique" in file_info['canonical_path']:
                # Should have only one path
                assert len(paths) == 1
                # Should not be a symlink
                assert not paths[0]['is_symlink']
    
    def test_symlink_target_consistency(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that all symlinks point to the correct canonical file."""
        # Set up: scan and organize files
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        organizer.resolve_destinations([], tmp_media_tree / "organized")
        organizer.realize()
        
        # Run deduplication
        deduplicator = FileDeduplicator(db)
        deduplicator.deduplicate()
        
        # Check that all symlinks point to canonical files
        for file_info, paths in db.iter_all_files():
            canonical_path = Path(file_info['canonical_path'])
            
            for path_info in paths:
                if path_info['is_symlink']:
                    symlink_path = Path(path_info['path'])
                    
                    # Should be a symlink
                    assert symlink_path.is_symlink()
                    
                    # Should point to canonical path
                    assert symlink_path.resolve() == canonical_path.resolve()
    
    def test_deduplication_statistics(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that deduplication statistics are accurate."""
        # Set up: scan and organize files
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        organizer.resolve_destinations([], tmp_media_tree / "organized")
        organizer.realize()
        
        # Count duplicates before deduplication
        duplicates_before = db.get_duplicate_checksums()
        
        # Run deduplication
        deduplicator = FileDeduplicator(db)
        deduplicator.deduplicate()
        
        # Count duplicates after deduplication
        duplicates_after = db.get_duplicate_checksums()
        
        # Should have no duplicates after deduplication
        assert len(duplicates_after) == 0
        
        # Check idempotency
        assert deduplicator.is_idempotent() 