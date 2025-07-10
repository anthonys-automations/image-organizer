"""Report generation functionality."""

import csv
import json
from pathlib import Path
from typing import Optional
import logging

from .database import Database

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Human-readable & CSV/JSON reporting."""
    
    def __init__(self, database: Database) -> None:
        """
        Initialize reporter with database connection.
        
        Args:
            database: Database instance
        """
        self.database = database
    
    def generate(
        self, 
        format: str = "table", 
        output_file: Optional[Path] = None
    ) -> None:
        """
        Generate report in specified format.
        
        Args:
            format: Output format ('table', 'csv', 'json')
            output_file: Output file path (optional)
        """
        if format == "table":
            self._generate_table(output_file)
        elif format == "csv":
            self._generate_csv(output_file)
        elif format == "json":
            self._generate_json(output_file)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_table(self, output_file: Optional[Path] = None) -> None:
        """
        Generate pretty-printed table output.
        
        Args:
            output_file: Output file path (optional, defaults to stdout)
        """
        lines = []
        lines.append("=" * 80)
        lines.append("IMAGE ORGANIZER DATABASE REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        total_files = 0
        total_duplicates = 0
        total_symlinks = 0
        
        for file_info, paths in self.database.iter_all_files():
            checksum = file_info['checksum']
            timestamp = file_info['timestamp']
            canonical_path = file_info['canonical_path']
            
            lines.append(f"File: {checksum}")
            lines.append(f"  Timestamp: {timestamp or 'Unknown'}")
            lines.append(f"  Canonical: {canonical_path}")
            lines.append(f"  Copies: {len(paths)}")
            
            symlink_count = sum(1 for p in paths if p['is_symlink'])
            physical_count = len(paths) - symlink_count
            
            lines.append(f"    Physical: {physical_count}")
            lines.append(f"    Symlinks: {symlink_count}")
            
            if len(paths) > 1:
                total_duplicates += 1
                lines.append("    *** DUPLICATE ***")
            
            total_symlinks += symlink_count
            total_files += 1
            
            for path_info in paths:
                path = path_info['path']
                is_symlink = path_info['is_symlink']
                symlink_indicator = " -> " if is_symlink else ""
                lines.append(f"    {path}{symlink_indicator}")
            
            lines.append("")
        
        # Summary
        lines.append("=" * 80)
        lines.append("SUMMARY")
        lines.append("=" * 80)
        lines.append(f"Total files: {total_files}")
        lines.append(f"Files with duplicates: {total_duplicates}")
        lines.append(f"Total symlinks: {total_symlinks}")
        lines.append("=" * 80)
        
        output = "\n".join(lines)
        
        if output_file:
            output_file.write_text(output, encoding='utf-8')
            logger.info(f"Table report written to: {output_file}")
        else:
            print(output)
    
    def _generate_csv(self, output_file: Optional[Path] = None) -> None:
        """
        Generate CSV report.
        
        Args:
            output_file: Output file path (optional, defaults to stdout)
        """
        if output_file:
            file_obj = open(output_file, 'w', newline='', encoding='utf-8')
        else:
            import sys
            file_obj = sys.stdout
        
        try:
            writer = csv.writer(file_obj)
            
            # Header
            writer.writerow([
                'checksum', 'timestamp', 'canonical_path', 
                'path', 'is_symlink', 'is_duplicate'
            ])
            
            # Data
            for file_info, paths in self.database.iter_all_files():
                checksum = file_info['checksum']
                timestamp = file_info['timestamp']
                canonical_path = file_info['canonical_path']
                is_duplicate = len(paths) > 1
                
                for path_info in paths:
                    writer.writerow([
                        checksum,
                        timestamp or '',
                        canonical_path,
                        path_info['path'],
                        path_info['is_symlink'],
                        is_duplicate
                    ])
        
        finally:
            if output_file:
                file_obj.close()
                logger.info(f"CSV report written to: {output_file}")
    
    def _generate_json(self, output_file: Optional[Path] = None) -> None:
        """
        Generate JSON report.
        
        Args:
            output_file: Output file path (optional, defaults to stdout)
        """
        data = {
            'summary': {
                'total_files': 0,
                'files_with_duplicates': 0,
                'total_symlinks': 0
            },
            'files': []
        }
        
        total_files = 0
        total_duplicates = 0
        total_symlinks = 0
        
        for file_info, paths in self.database.iter_all_files():
            checksum = file_info['checksum']
            timestamp = file_info['timestamp']
            canonical_path = file_info['canonical_path']
            
            symlink_count = sum(1 for p in paths if p['is_symlink'])
            physical_count = len(paths) - symlink_count
            is_duplicate = len(paths) > 1
            
            file_data = {
                'checksum': checksum,
                'timestamp': timestamp,
                'canonical_path': canonical_path,
                'is_duplicate': is_duplicate,
                'copy_count': len(paths),
                'physical_count': physical_count,
                'symlink_count': symlink_count,
                'paths': [
                    {
                        'path': path_info['path'],
                        'is_symlink': path_info['is_symlink']
                    }
                    for path_info in paths
                ]
            }
            
            data['files'].append(file_data)
            
            total_files += 1
            if is_duplicate:
                total_duplicates += 1
            total_symlinks += symlink_count
        
        data['summary']['total_files'] = total_files
        data['summary']['files_with_duplicates'] = total_duplicates
        data['summary']['total_symlinks'] = total_symlinks
        
        output = json.dumps(data, indent=2, ensure_ascii=False)
        
        if output_file:
            output_file.write_text(output, encoding='utf-8')
            logger.info(f"JSON report written to: {output_file}")
        else:
            print(output)
    
    def get_statistics(self) -> dict:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        total_files = 0
        total_duplicates = 0
        total_symlinks = 0
        total_size = 0
        
        for file_info, paths in self.database.iter_all_files():
            checksum = file_info['checksum']
            canonical_path = Path(file_info['canonical_path'])
            
            symlink_count = sum(1 for p in paths if p['is_symlink'])
            physical_count = len(paths) - symlink_count
            is_duplicate = len(paths) > 1
            
            total_files += 1
            if is_duplicate:
                total_duplicates += 1
            total_symlinks += symlink_count
            
            # Calculate size (only count physical files once)
            if canonical_path.exists():
                try:
                    total_size += canonical_path.stat().st_size
                except OSError:
                    pass
        
        return {
            'total_files': total_files,
            'files_with_duplicates': total_duplicates,
            'total_symlinks': total_symlinks,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        } 