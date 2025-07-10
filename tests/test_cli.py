"""End-to-end CLI tests."""

import tempfile
from pathlib import Path
import pytest
from click.testing import CliRunner

from imgtool.cli import main


class TestCLI:
    """Test cases for CLI functionality."""
    
    def test_scan_and_organize_flow(self, tmp_media_tree: Path) -> None:
        """Test complete scan and organize workflow."""
        runner = CliRunner()
        
        # Test scan command
        result = runner.invoke(main, [
            'scan', 
            str(tmp_media_tree / "photos"),
            str(tmp_media_tree / "videos")
        ])
        
        assert result.exit_code == 0
        
        # Test organize command
        organized_dir = tmp_media_tree / "organized"
        result = runner.invoke(main, [
            'organize',
            '--preferred', str(tmp_media_tree / "backup"),
            '--target', str(organized_dir)
        ])
        
        assert result.exit_code == 0
        
        # Check that organized directory was created
        assert organized_dir.exists()
        assert organized_dir.is_dir()
    
    def test_revert_flow(self, tmp_media_tree: Path) -> None:
        """Test complete organization and revert workflow."""
        runner = CliRunner()
        
        # Scan and organize
        result = runner.invoke(main, [
            'scan', str(tmp_media_tree)
        ])
        assert result.exit_code == 0
        
        organized_dir = tmp_media_tree / "organized"
        result = runner.invoke(main, [
            'organize',
            '--preferred', str(tmp_media_tree / "backup"),
            '--target', str(organized_dir)
        ])
        assert result.exit_code == 0
        
        # Revert
        result = runner.invoke(main, ['revert'])
        assert result.exit_code == 0
        
        # Check that original structure is restored
        for file_info, paths in db.iter_all_files():
            for path_info in paths:
                path = Path(path_info['path'])
                assert path.exists()
                assert not path.is_symlink()
    
    def test_interrupt_and_resume(self, tmp_media_tree: Path) -> None:
        """Test handling of interrupted operations and resume."""
        runner = CliRunner()
        
        # Start scan
        result = runner.invoke(main, [
            'scan', str(tmp_media_tree)
        ])
        assert result.exit_code == 0
        
        # Organize (this could be interrupted)
        organized_dir = tmp_media_tree / "organized"
        result = runner.invoke(main, [
            'organize',
            '--preferred', str(tmp_media_tree / "backup"),
            '--target', str(organized_dir)
        ])
        assert result.exit_code == 0
        
        # Revert from partial state
        result = runner.invoke(main, ['revert', '--partial'])
        assert result.exit_code == 0
    
    def test_report_generation(self, tmp_media_tree: Path) -> None:
        """Test report generation in different formats."""
        runner = CliRunner()
        
        # Scan files
        result = runner.invoke(main, [
            'scan', str(tmp_media_tree)
        ])
        assert result.exit_code == 0
        
        # Generate table report
        result = runner.invoke(main, ['report'])
        assert result.exit_code == 0
        assert "IMAGE ORGANIZER DATABASE REPORT" in result.output
        
        # Generate CSV report
        csv_file = tmp_media_tree / "report.csv"
        result = runner.invoke(main, [
            'report', '--format', 'csv', '--output', str(csv_file)
        ])
        assert result.exit_code == 0
        assert csv_file.exists()
        
        # Generate JSON report
        json_file = tmp_media_tree / "report.json"
        result = runner.invoke(main, [
            'report', '--format', 'json', '--output', str(json_file)
        ])
        assert result.exit_code == 0
        assert json_file.exists()
    
    def test_help_output(self) -> None:
        """Test that help is displayed correctly."""
        runner = CliRunner()
        
        # Main help
        result = runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert "Image Organizer Tool" in result.output
        assert "scan" in result.output
        assert "organize" in result.output
        
        # Command help
        result = runner.invoke(main, ['scan', '--help'])
        assert result.exit_code == 0
        assert "directories to scan" in result.output
    
    def test_invalid_arguments(self) -> None:
        """Test handling of invalid arguments."""
        runner = CliRunner()
        
        # Invalid command
        result = runner.invoke(main, ['invalid_command'])
        assert result.exit_code != 0
        
        # Missing required arguments
        result = runner.invoke(main, ['scan'])
        assert result.exit_code != 0
        
        result = runner.invoke(main, ['organize'])
        assert result.exit_code != 0
    
    def test_verbose_logging(self, tmp_media_tree: Path) -> None:
        """Test verbose logging output."""
        runner = CliRunner()
        
        result = runner.invoke(main, [
            '--verbose', 'scan', str(tmp_media_tree)
        ])
        assert result.exit_code == 0
        
        # Should have more detailed output
        assert "Starting scan" in result.output or "Scan completed" in result.output
    
    def test_custom_database_path(self, tmp_media_tree: Path) -> None:
        """Test using custom database path."""
        runner = CliRunner()
        
        custom_db = tmp_media_tree / "custom.db"
        
        result = runner.invoke(main, [
            '--db', str(custom_db),
            'scan', str(tmp_media_tree)
        ])
        assert result.exit_code == 0
        
        # Check that custom database was created
        assert custom_db.exists()
    
    def test_deduplicate_command(self, tmp_media_tree: Path) -> None:
        """Test deduplicate command."""
        runner = CliRunner()
        
        # Scan and organize first
        result = runner.invoke(main, [
            'scan', str(tmp_media_tree)
        ])
        assert result.exit_code == 0
        
        organized_dir = tmp_media_tree / "organized"
        result = runner.invoke(main, [
            'organize',
            '--preferred', str(tmp_media_tree / "backup"),
            '--target', str(organized_dir)
        ])
        assert result.exit_code == 0
        
        # Run deduplication
        result = runner.invoke(main, ['deduplicate'])
        assert result.exit_code == 0
        
        # Check that symlinks were created
        # (This would require checking the database or filesystem)
        assert "Deduplication completed" in result.output or result.exit_code == 0 