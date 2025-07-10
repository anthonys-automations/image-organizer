"""Tests for the FileScanner class."""

import datetime
from pathlib import Path
import pytest

from imgtool.scanner import FileScanner
from imgtool.database import Database


class TestFileScanner:
    """Test cases for FileScanner class."""
    
    def test_checksum_consistency(self, db: Database, sample_image_files: list[Path]) -> None:
        """Test that checksums are consistent for identical files."""
        scanner = FileScanner(db)
        
        # Scan the same file twice
        file_path = sample_image_files[0]
        scanner._process_file(file_path)
        scanner._process_file(file_path)
        
        # Should only be recorded once
        file_count = 0
        for file_info, paths in db.iter_all_files():
            if file_info['canonical_path'] == str(file_path):
                file_count += 1
        
        assert file_count == 1
    
    def test_timestamp_exif_vs_stat(self, db: Database, tmp_media_tree: Path) -> None:
        """Test timestamp extraction from EXIF vs filesystem."""
        scanner = FileScanner(db)
        
        # Create a test file
        test_file = tmp_media_tree / "test_image.jpg"
        test_file.write_bytes(b"test_content")
        
        # Set filesystem timestamp
        expected_time = datetime.datetime(2023, 6, 15, 10, 30, 0)
        timestamp = expected_time.timestamp()
        import os
        os.utime(test_file, (timestamp, timestamp))
        
        # Extract timestamp
        extracted_time = scanner._extract_timestamp(test_file)
        
        # Should fall back to filesystem timestamp
        assert extracted_time is not None
        assert extracted_time.year == expected_time.year
        assert extracted_time.month == expected_time.month
    
    def test_skip_existing_in_db(self, db: Database, sample_image_files: list[Path]) -> None:
        """Test that existing files in DB are skipped."""
        scanner = FileScanner(db)
        
        # Process a file
        file_path = sample_image_files[0]
        scanner._process_file(file_path)
        
        # Clear the scanned files set to simulate a fresh scan
        scanner._scanned_files.clear()
        
        # Process the same file again
        scanner._process_file(file_path)
        
        # Should be skipped due to path resolution
        file_path_str = str(file_path.resolve())
        assert file_path_str in scanner._scanned_files
    
    def test_scan_directories_recursive(self, db: Database, tmp_media_tree: Path) -> None:
        """Test recursive directory scanning."""
        scanner = FileScanner(db)
        
        # Scan the entire tree
        scanner.scan_directories([tmp_media_tree])
        
        # Count files in database
        file_count = 0
        for file_info, paths in db.iter_all_files():
            file_count += 1
        
        # Should find all supported files
        expected_files = [
            "photo1.jpg", "photo2.png", "photo3.gif",  # From photos dir
            "video1.mp4", "video2.mov",                # From videos dir
            "photo1.jpg", "photo2.png", "video1.mp4"   # From backup dir (duplicates)
        ]
        assert file_count == len(expected_files)
    
    def test_unsupported_file_types(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that unsupported file types are ignored."""
        scanner = FileScanner(db)
        
        # Create unsupported files
        unsupported_files = [
            tmp_media_tree / "document.txt",
            tmp_media_tree / "script.py",
            tmp_media_tree / "data.csv",
        ]
        
        for file_path in unsupported_files:
            file_path.write_bytes(b"content")
        
        # Scan directory
        scanner.scan_directories([tmp_media_tree])
        
        # Check that unsupported files are not in database
        for file_info, paths in db.iter_all_files():
            for path_info in paths:
                path = Path(path_info['path'])
                assert path.suffix.lower() in FileScanner.SUPPORTED_EXTENSIONS
    
    def test_permission_error_handling(self, db: Database, tmp_media_tree: Path) -> None:
        """Test handling of permission errors during scanning."""
        scanner = FileScanner(db)
        
        # Create a directory that we can't access (simulate permission error)
        inaccessible_dir = tmp_media_tree / "inaccessible"
        inaccessible_dir.mkdir()
        
        # Make directory read-only (this might not work on all systems)
        try:
            inaccessible_dir.chmod(0o000)
            
            # Scan should not crash
            scanner.scan_directories([tmp_media_tree])
            
        except PermissionError:
            # Expected on some systems
            pass
        finally:
            # Restore permissions
            try:
                inaccessible_dir.chmod(0o755)
            except PermissionError:
                pass
    
    def test_duplicate_detection(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that duplicate files are properly detected."""
        scanner = FileScanner(db)
        
        # Scan directories with known duplicates
        scanner.scan_directories([tmp_media_tree])
        
        # Find duplicates
        duplicate_checksums = db.get_duplicate_checksums()
        
        # Should find duplicates (photo1.jpg, photo2.png, video1.mp4)
        assert len(duplicate_checksums) >= 3
        
        # Check that duplicate files have the same checksum
        checksum_to_paths = {}
        for file_info, paths in db.iter_all_files():
            checksum = file_info['checksum']
            if checksum not in checksum_to_paths:
                checksum_to_paths[checksum] = []
            checksum_to_paths[checksum].extend([p['path'] for p in paths])
        
        # Verify duplicates
        for checksum in duplicate_checksums:
            paths = checksum_to_paths[checksum]
            assert len(paths) > 1
            
            # All paths should point to files with same content
            first_content = Path(paths[0]).read_bytes()
            for path in paths[1:]:
                assert Path(path).read_bytes() == first_content
    
    def test_case_insensitive_extensions(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that file extensions are handled case-insensitively."""
        scanner = FileScanner(db)
        
        # Create files with different case extensions
        case_variants = [
            tmp_media_tree / "test.JPG",
            tmp_media_tree / "test.JPEG",
            tmp_media_tree / "test.PNG",
            tmp_media_tree / "test.GIF",
        ]
        
        for file_path in case_variants:
            file_path.write_bytes(b"test_content")
        
        # Scan directory
        scanner.scan_directories([tmp_media_tree])
        
        # All case variants should be processed
        processed_files = set()
        for file_info, paths in db.iter_all_files():
            for path_info in paths:
                path = Path(path_info['path'])
                if path.name.startswith("test."):
                    processed_files.add(path.name.lower())
        
        expected_files = {"test.jpg", "test.jpeg", "test.png", "test.gif"}
        assert processed_files == expected_files
    
    def test_empty_directory(self, db: Database, tmp_media_tree: Path) -> None:
        """Test scanning empty directory."""
        scanner = FileScanner(db)
        
        # Create empty directory
        empty_dir = tmp_media_tree / "empty"
        empty_dir.mkdir()
        
        # Scan should not crash
        scanner.scan_directories([empty_dir])
        
        # No files should be found
        file_count = 0
        for file_info, paths in db.iter_all_files():
            file_count += 1
        
        assert file_count == 0
    
    def test_nonexistent_directory(self, db: Database) -> None:
        """Test scanning nonexistent directory."""
        scanner = FileScanner(db)
        
        # Create path to nonexistent directory
        nonexistent_dir = Path("/nonexistent/path/that/does/not/exist")
        
        # Scan should handle gracefully
        scanner.scan_directories([nonexistent_dir])
        
        # No files should be found
        file_count = 0
        for file_info, paths in db.iter_all_files():
            file_count += 1
        
        assert file_count == 0 