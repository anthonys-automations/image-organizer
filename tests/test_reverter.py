"""Tests for the FileReverter class."""

from pathlib import Path
import pytest

from imgtool.reverter import FileReverter
from imgtool.database import Database
from imgtool.scanner import FileScanner
from imgtool.organizer import FileOrganizer
from imgtool.deduplicator import FileDeduplicator


class TestFileReverter:
    """Test cases for FileReverter class."""
    
    def test_full_revert_cycle(self, db: Database, tmp_media_tree: Path) -> None:
        """Test complete organization and reversion cycle."""
        # Set up: scan, organize, and deduplicate
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        organizer.resolve_destinations([], tmp_media_tree / "organized")
        organizer.realize()
        
        deduplicator = FileDeduplicator(db)
        deduplicator.deduplicate()
        
        # Record original file locations
        original_locations = {}
        for file_info, paths in db.iter_all_files():
            checksum = file_info['checksum']
            original_locations[checksum] = [
                path['path'] for path in paths
            ]
        
        # Run reversion
        reverter = FileReverter(db)
        reverter.revert()
        
        # Check that all original locations have physical files
        for file_info, paths in db.iter_all_files():
            checksum = file_info['checksum']
            
            for path_info in paths:
                path = Path(path_info['path'])
                
                # Should exist
                assert path.exists()
                
                # Should be a physical file, not a symlink
                assert not path.is_symlink()
                assert path.is_file()
                
                # Should be in original location
                assert path['path'] in original_locations[checksum]
    
    def test_revert_from_partial_state(self, db: Database, tmp_media_tree: Path) -> None:
        """Test reversion from partial/interrupted state."""
        # Set up: scan and organize
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        organizer.resolve_destinations([], tmp_media_tree / "organized")
        organizer.realize()
        
        # Create some broken symlinks to simulate partial state
        for file_info, paths in db.iter_all_files():
            for path_info in paths:
                if path_info['is_symlink']:
                    path = Path(path_info['path'])
                    if path.exists():
                        # Break the symlink by removing target
                        target = path.resolve()
                        if target.exists():
                            target.unlink()
                    break
        
        # Run reversion from partial state
        reverter = FileReverter(db)
        reverter.revert_from_partial_state()
        
        # Check that all files are restored
        for file_info, paths in db.iter_all_files():
            for path_info in paths:
                path = Path(path_info['path'])
                
                # Should exist
                assert path.exists()
                
                # Should be a physical file
                assert not path.is_symlink()
                assert path.is_file()
    
    def test_symlink_restoration(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that symlinks are properly replaced with physical files."""
        # Set up: scan, organize, and deduplicate
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        organizer.resolve_destinations([], tmp_media_tree / "organized")
        organizer.realize()
        
        deduplicator = FileDeduplicator(db)
        deduplicator.deduplicate()
        
        # Count symlinks before reversion
        symlinks_before = sum(
            1 for file_info, paths in db.iter_all_files()
            for path_info in paths if path_info['is_symlink']
        )
        
        # Run reversion
        reverter = FileReverter(db)
        reverter.revert()
        
        # Count symlinks after reversion
        symlinks_after = sum(
            1 for file_info, paths in db.iter_all_files()
            for path_info in paths if path_info['is_symlink']
        )
        
        # Should have no symlinks after reversion
        assert symlinks_after == 0
        
        # All files should be physical
        for file_info, paths in db.iter_all_files():
            for path_info in paths:
                path = Path(path_info['path'])
                assert path.exists()
                assert not path.is_symlink()
                assert path.is_file()
    
    def test_canonical_file_recovery(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that canonical files are properly recovered if missing."""
        # Set up: scan, organize, and deduplicate
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        organizer.resolve_destinations([], tmp_media_tree / "organized")
        organizer.realize()
        
        deduplicator = FileDeduplicator(db)
        deduplicator.deduplicate()
        
        # Remove some canonical files to simulate corruption
        removed_canonicals = []
        for file_info, paths in db.iter_all_files():
            canonical_path = Path(file_info['canonical_path'])
            if canonical_path.exists():
                canonical_path.unlink()
                removed_canonicals.append(canonical_path)
                break
        
        # Run reversion
        reverter = FileReverter(db)
        reverter.revert()
        
        # Check that canonical files are restored
        for canonical_path in removed_canonicals:
            assert canonical_path.exists()
            assert canonical_path.is_file()
    
    def test_broken_symlink_fixing(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that broken symlinks are properly fixed during reversion."""
        # Set up: scan, organize, and deduplicate
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        organizer.resolve_destinations([], tmp_media_tree / "organized")
        organizer.realize()
        
        deduplicator = FileDeduplicator(db)
        deduplicator.deduplicate()
        
        # Create some broken symlinks
        broken_symlinks = []
        for file_info, paths in db.iter_all_files():
            for path_info in paths:
                if path_info['is_symlink']:
                    path = Path(path_info['path'])
                    if path.exists():
                        # Break the symlink
                        path.unlink()
                        path.symlink_to("/nonexistent/target")
                        broken_symlinks.append(path)
                        break
        
        # Run reversion from partial state
        reverter = FileReverter(db)
        reverter.revert_from_partial_state()
        
        # Check that broken symlinks are fixed
        for symlink_path in broken_symlinks:
            assert symlink_path.exists()
            assert not symlink_path.is_symlink()
            assert symlink_path.is_file()
    
    def test_file_content_preservation(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that file content is preserved during reversion."""
        # Set up: scan, organize, and deduplicate
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        # Record original content
        original_content = {}
        for file_info, paths in db.iter_all_files():
            checksum = file_info['checksum']
            for path_info in paths:
                path = Path(path_info['path'])
                if path.exists():
                    original_content[checksum] = path.read_bytes()
                    break
        
        organizer = FileOrganizer(db)
        organizer.resolve_destinations([], tmp_media_tree / "organized")
        organizer.realize()
        
        deduplicator = FileDeduplicator(db)
        deduplicator.deduplicate()
        
        # Run reversion
        reverter = FileReverter(db)
        reverter.revert()
        
        # Check that content is preserved
        for file_info, paths in db.iter_all_files():
            checksum = file_info['checksum']
            if checksum in original_content:
                # Find a physical copy
                for path_info in paths:
                    path = Path(path_info['path'])
                    if path.exists() and not path.is_symlink():
                        current_content = path.read_bytes()
                        assert current_content == original_content[checksum]
                        break 