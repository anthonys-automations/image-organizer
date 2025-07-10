"""Command-line interface for image organizer."""

import argparse
import sys
from pathlib import Path
from typing import List
import logging

from .database import Database
from .scanner import FileScanner
from .organizer import FileOrganizer
from .deduplicator import FileDeduplicator
from .reverter import FileReverter
from .reporter import ReportGenerator

logger = logging.getLogger(__name__)


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Execute the appropriate command
        if args.command == 'scan':
            cmd_scan(args)
        elif args.command == 'organize':
            cmd_organize(args)
        elif args.command == 'deduplicate':
            cmd_deduplicate(args)
        elif args.command == 'revert':
            cmd_revert(args)
        elif args.command == 'report':
            cmd_report(args)
        else:
            parser.print_help()
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Image Organizer Tool - Manage and deduplicate image/video files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s scan /path/to/photos /path/to/videos
  %(prog)s organize --preferred /path/to/keep --target /path/to/organized
  %(prog)s deduplicate
  %(prog)s revert
  %(prog)s report --format csv --output report.csv
        """
    )
    
    parser.add_argument(
        '--db', 
        type=Path, 
        default=Path('imgtool.db'),
        help='Database file path (default: imgtool.db)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands'
    )
    
    # Scan command
    scan_parser = subparsers.add_parser(
        'scan',
        help='Scan directories and index files'
    )
    scan_parser.add_argument(
        'directories',
        nargs='+',
        type=Path,
        help='Directories to scan'
    )
    
    # Organize command
    organize_parser = subparsers.add_parser(
        'organize',
        help='Organize files into canonical structure'
    )
    organize_parser.add_argument(
        '--preferred',
        nargs='+',
        type=Path,
        required=True,
        help='Preferred directories (in priority order)'
    )
    organize_parser.add_argument(
        '--target',
        type=Path,
        required=True,
        help='Target root directory for organizing'
    )
    
    # Deduplicate command
    dedup_parser = subparsers.add_parser(
        'deduplicate',
        help='Deduplicate files by creating symlinks'
    )
    
    # Revert command
    revert_parser = subparsers.add_parser(
        'revert',
        help='Revert all operations, restoring original structure'
    )
    revert_parser.add_argument(
        '--partial',
        action='store_true',
        help='Revert from partial/interrupted state'
    )
    
    # Report command
    report_parser = subparsers.add_parser(
        'report',
        help='Generate database report'
    )
    report_parser.add_argument(
        '--format',
        choices=['table', 'csv', 'json'],
        default='table',
        help='Output format (default: table)'
    )
    report_parser.add_argument(
        '--output',
        type=Path,
        help='Output file (default: stdout)'
    )
    
    return parser


def cmd_scan(args: argparse.Namespace) -> None:
    """Execute scan command."""
    logger.info(f"Scanning directories: {args.directories}")
    
    with Database(args.db) as db:
        scanner = FileScanner(db)
        scanner.scan_directories(args.directories)
    
    logger.info("Scan completed successfully")


def cmd_organize(args: argparse.Namespace) -> None:
    """Execute organize command."""
    logger.info(f"Organizing files with preferred dirs: {args.preferred}")
    logger.info(f"Target root: {args.target}")
    
    with Database(args.db) as db:
        organizer = FileOrganizer(db)
        organizer.resolve_destinations(args.preferred, args.target)
        organizer.realize()
    
    logger.info("Organization completed successfully")


def cmd_deduplicate(args: argparse.Namespace) -> None:
    """Execute deduplicate command."""
    logger.info("Starting deduplication")
    
    with Database(args.db) as db:
        deduplicator = FileDeduplicator(db)
        deduplicator.deduplicate()
    
    logger.info("Deduplication completed successfully")


def cmd_revert(args: argparse.Namespace) -> None:
    """Execute revert command."""
    if args.partial:
        logger.info("Reverting from partial state")
    else:
        logger.info("Reverting all operations")
    
    with Database(args.db) as db:
        reverter = FileReverter(db)
        if args.partial:
            reverter.revert_from_partial_state()
        else:
            reverter.revert()
    
    logger.info("Revert completed successfully")


def cmd_report(args: argparse.Namespace) -> None:
    """Execute report command."""
    logger.info(f"Generating {args.format} report")
    
    with Database(args.db) as db:
        reporter = ReportGenerator(db)
        reporter.generate(args.format, args.output)
    
    logger.info("Report generated successfully")


if __name__ == '__main__':
    main() 