"""EXIF timestamp extraction utilities."""

import datetime
from pathlib import Path
from typing import Optional

try:
    import piexif
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


def get_timestamp(file_path: Path) -> Optional[datetime.datetime]:
    """
    Extract timestamp from image file using EXIF data or fallback to filesystem.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        datetime object if timestamp found, None otherwise
        
    Raises:
        ImportError: If pillow/piexif not available
    """
    if not PILLOW_AVAILABLE:
        raise ImportError("pillow and piexif required for EXIF extraction")
    
    if not file_path.exists():
        return None
    
    # Try EXIF first
    exif_timestamp = _extract_exif_timestamp(file_path)
    if exif_timestamp:
        return exif_timestamp
    
    # Fallback to filesystem timestamp
    return _get_filesystem_timestamp(file_path)


def _extract_exif_timestamp(file_path: Path) -> Optional[datetime.datetime]:
    """
    Extract timestamp from EXIF data in image file.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        datetime object if EXIF timestamp found, None otherwise
    """
    try:
        # Try piexif first (more reliable for EXIF)
        exif_dict = piexif.load(str(file_path))
        
        # Check for DateTimeOriginal (most reliable)
        if "0th" in exif_dict and piexif.ImageIFD.DateTimeOriginal in exif_dict["0th"]:
            date_str = exif_dict["0th"][piexif.ImageIFD.DateTimeOriginal].decode("utf-8")
            return _parse_exif_datetime(date_str)
        
        # Check for DateTime
        if "0th" in exif_dict and piexif.ImageIFD.DateTime in exif_dict["0th"]:
            date_str = exif_dict["0th"][piexif.ImageIFD.DateTime].decode("utf-8")
            return _parse_exif_datetime(date_str)
            
    except (piexif.InvalidImageDataError, KeyError, UnicodeDecodeError):
        pass
    
    try:
        # Fallback to PIL for other image formats
        with Image.open(file_path) as img:
            if hasattr(img, "_getexif") and img._getexif():
                exif = img._getexif()
                
                # EXIF tags for DateTimeOriginal and DateTime
                datetime_original = 36867
                datetime_tag = 306
                
                if datetime_original in exif:
                    return _parse_exif_datetime(exif[datetime_original])
                elif datetime_tag in exif:
                    return _parse_exif_datetime(exif[datetime_tag])
                    
    except (OSError, KeyError, ValueError):
        pass
    
    return None


def _parse_exif_datetime(date_str: str) -> Optional[datetime.datetime]:
    """
    Parse EXIF datetime string format.
    
    Args:
        date_str: EXIF datetime string (format: "YYYY:MM:DD HH:MM:SS")
        
    Returns:
        datetime object if parsing successful, None otherwise
    """
    try:
        # EXIF format: "YYYY:MM:DD HH:MM:SS"
        return datetime.datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None


def _get_filesystem_timestamp(file_path: Path) -> Optional[datetime.datetime]:
    """
    Get file creation/modification time from filesystem.
    
    Args:
        file_path: Path to the file
        
    Returns:
        datetime object from filesystem timestamp
    """
    try:
        stat = file_path.stat()
        # Use modification time as fallback
        return datetime.datetime.fromtimestamp(stat.st_mtime)
    except (OSError, ValueError):
        return None 