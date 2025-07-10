"""Shared fixtures and test configuration."""

import datetime
import tempfile
import shutil
from pathlib import Path
from typing import Generator
import pytest

from imgtool.database import Database


@pytest.fixture
def tmp_media_tree() -> Generator[Path, None, None]:
    """
    Builds a temporary directory tree with duplicates & EXIF metadata.
    
    Creates a test directory structure with:
    - Multiple directories containing image files
    - Some duplicate files across directories
    - Files with different timestamps
    - A mix of file types
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create directory structure
        photos_dir = temp_path / "photos"
        videos_dir = temp_path / "videos"
        backup_dir = temp_path / "backup"
        
        photos_dir.mkdir()
        videos_dir.mkdir()
        backup_dir.mkdir()
        
        # Create subdirectories
        (photos_dir / "2023").mkdir()
        (photos_dir / "2024").mkdir()
        (videos_dir / "vacation").mkdir()
        
        # Create test files with different content
        test_files = [
            # Photos
            (photos_dir / "2023" / "photo1.jpg", b"photo1_content_2023"),
            (photos_dir / "2023" / "photo2.png", b"photo2_content_2023"),
            (photos_dir / "2024" / "photo1.jpg", b"photo1_content_2024"),  # Different content
            (photos_dir / "2024" / "photo3.gif", b"photo3_content_2024"),
            
            # Videos
            (videos_dir / "vacation" / "video1.mp4", b"video1_content"),
            (videos_dir / "video2.mov", b"video2_content"),
            
            # Backup (duplicates of some files)
            (backup_dir / "photo1.jpg", b"photo1_content_2023"),  # Duplicate of 2023 photo1
            (backup_dir / "photo2.png", b"photo2_content_2023"),  # Duplicate of 2023 photo2
            (backup_dir / "video1.mp4", b"video1_content"),       # Duplicate of video1
        ]
        
        # Create the files
        for file_path, content in test_files:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)
            
            # Set modification time to simulate different timestamps
            if "2023" in str(file_path):
                timestamp = datetime.datetime(2023, 6, 15, 10, 30, 0).timestamp()
            elif "2024" in str(file_path):
                timestamp = datetime.datetime(2024, 3, 20, 14, 45, 0).timestamp()
            else:
                timestamp = datetime.datetime(2024, 1, 10, 9, 15, 0).timestamp()
            
            os.utime(file_path, (timestamp, timestamp))
        
        yield temp_path


@pytest.fixture
def db(tmp_media_tree: Path) -> Generator[Database, None, None]:
    """Yields a temporary Database instance bound to the fixture tree."""
    db_path = tmp_media_tree / "test.db"
    with Database(db_path) as database:
        yield database


@pytest.fixture
def sample_image_files(tmp_media_tree: Path) -> list[Path]:
    """Create sample image files with known content for testing."""
    files = []
    
    # Create files with different content
    test_contents = [
        (b"image1_content", "image1.jpg"),
        (b"image2_content", "image2.png"),
        (b"image1_content", "image1_copy.jpg"),  # Duplicate of image1
        (b"image3_content", "image3.gif"),
    ]
    
    for content, filename in test_contents:
        file_path = tmp_media_tree / filename
        file_path.write_bytes(content)
        files.append(file_path)
    
    return files


@pytest.fixture
def organized_structure(tmp_media_tree: Path) -> Path:
    """Create an organized directory structure for testing."""
    organized_dir = tmp_media_tree / "organized"
    organized_dir.mkdir()
    
    # Create year/month structure
    (organized_dir / "2023" / "06").mkdir(parents=True)
    (organized_dir / "2024" / "03").mkdir(parents=True)
    (organized_dir / "2024" / "01").mkdir(parents=True)
    
    return organized_dir


# Import os for timestamp manipulation
import os 