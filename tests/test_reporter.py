"""Tests for the ReportGenerator class."""

import csv
import json
from pathlib import Path
import pytest

from imgtool.reporter import ReportGenerator
from imgtool.database import Database
from imgtool.scanner import FileScanner
from imgtool.organizer import FileOrganizer
from imgtool.deduplicator import FileDeduplicator


class TestReportGenerator:
    """Test cases for ReportGenerator class."""
    
    def test_table_output_matches_db(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that table output accurately reflects database contents."""
        # Set up: scan, organize, and deduplicate
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        organizer.resolve_destinations([], tmp_media_tree / "organized")
        organizer.realize()
        
        deduplicator = FileDeduplicator(db)
        deduplicator.deduplicate()
        
        # Generate table report
        reporter = ReportGenerator(db)
        output_file = tmp_media_tree / "report.txt"
        reporter.generate("table", output_file)
        
        # Read the report
        report_content = output_file.read_text()
        
        # Check that all files are mentioned
        for file_info, paths in db.iter_all_files():
            checksum = file_info['checksum']
            assert checksum in report_content
            
            canonical_path = file_info['canonical_path']
            assert canonical_path in report_content
        
        # Check summary statistics
        assert "Total files:" in report_content
        assert "Files with duplicates:" in report_content
        assert "Total symlinks:" in report_content
    
    def test_csv_export(self, db: Database, tmp_media_tree: Path) -> None:
        """Test CSV export functionality."""
        # Set up: scan, organize, and deduplicate
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        organizer.resolve_destinations([], tmp_media_tree / "organized")
        organizer.realize()
        
        deduplicator = FileDeduplicator(db)
        deduplicator.deduplicate()
        
        # Generate CSV report
        reporter = ReportGenerator(db)
        output_file = tmp_media_tree / "report.csv"
        reporter.generate("csv", output_file)
        
        # Read and parse CSV
        rows = []
        with open(output_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Check header
        expected_headers = [
            'checksum', 'timestamp', 'canonical_path', 
            'path', 'is_symlink', 'is_duplicate'
        ]
        assert list(rows[0].keys()) == expected_headers
        
        # Check that all database entries are in CSV
        db_entries = []
        for file_info, paths in db.iter_all_files():
            for path_info in paths:
                db_entries.append({
                    'checksum': file_info['checksum'],
                    'canonical_path': file_info['canonical_path'],
                    'path': path_info['path'],
                    'is_symlink': str(path_info['is_symlink']).lower(),
                    'is_duplicate': str(len(paths) > 1).lower()
                })
        
        assert len(rows) == len(db_entries)
    
    def test_json_export(self, db: Database, tmp_media_tree: Path) -> None:
        """Test JSON export functionality."""
        # Set up: scan, organize, and deduplicate
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        organizer.resolve_destinations([], tmp_media_tree / "organized")
        organizer.realize()
        
        deduplicator = FileDeduplicator(db)
        deduplicator.deduplicate()
        
        # Generate JSON report
        reporter = ReportGenerator(db)
        output_file = tmp_media_tree / "report.json"
        reporter.generate("json", output_file)
        
        # Read and parse JSON
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check structure
        assert 'summary' in data
        assert 'files' in data
        
        # Check summary fields
        summary = data['summary']
        assert 'total_files' in summary
        assert 'files_with_duplicates' in summary
        assert 'total_symlinks' in summary
        
        # Check files structure
        files = data['files']
        assert len(files) > 0
        
        for file_data in files:
            assert 'checksum' in file_data
            assert 'canonical_path' in file_data
            assert 'paths' in file_data
            assert 'is_duplicate' in file_data
    
    def test_statistics_accuracy(self, db: Database, tmp_media_tree: Path) -> None:
        """Test that statistics are accurately calculated."""
        # Set up: scan, organize, and deduplicate
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        organizer = FileOrganizer(db)
        organizer.resolve_destinations([], tmp_media_tree / "organized")
        organizer.realize()
        
        deduplicator = FileDeduplicator(db)
        deduplicator.deduplicate()
        
        # Get statistics
        reporter = ReportGenerator(db)
        stats = reporter.get_statistics()
        
        # Calculate expected statistics
        total_files = 0
        files_with_duplicates = 0
        total_symlinks = 0
        
        for file_info, paths in db.iter_all_files():
            total_files += 1
            if len(paths) > 1:
                files_with_duplicates += 1
            total_symlinks += sum(1 for p in paths if p['is_symlink'])
        
        # Check statistics
        assert stats['total_files'] == total_files
        assert stats['files_with_duplicates'] == files_with_duplicates
        assert stats['total_symlinks'] == total_symlinks
        assert stats['total_size_bytes'] > 0
        assert stats['total_size_mb'] > 0
    
    def test_stdout_output(self, db: Database, tmp_media_tree: Path, capsys) -> None:
        """Test that output goes to stdout when no file specified."""
        # Set up: scan files
        scanner = FileScanner(db)
        scanner.scan_directories([tmp_media_tree])
        
        # Generate table report to stdout
        reporter = ReportGenerator(db)
        reporter.generate("table")
        
        # Check that output was printed
        captured = capsys.readouterr()
        assert "IMAGE ORGANIZER DATABASE REPORT" in captured.out
        assert "SUMMARY" in captured.out
    
    def test_invalid_format_handling(self, db: Database) -> None:
        """Test that invalid format raises appropriate error."""
        reporter = ReportGenerator(db)
        
        with pytest.raises(ValueError, match="Unsupported format"):
            reporter.generate("invalid_format")
    
    def test_empty_database_report(self, db: Database, tmp_media_tree: Path) -> None:
        """Test reporting on empty database."""
        reporter = ReportGenerator(db)
        
        # Generate report on empty database
        output_file = tmp_media_tree / "empty_report.txt"
        reporter.generate("table", output_file)
        
        # Read the report
        report_content = output_file.read_text()
        
        # Should have summary with zeros
        assert "Total files: 0" in report_content
        assert "Files with duplicates: 0" in report_content
        assert "Total symlinks: 0" in report_content 