"""Checksum calculation utilities."""

import hashlib
from pathlib import Path
from typing import BinaryIO


def calculate_sha256(file_path: Path) -> str:
    """
    Calculate SHA-256 checksum of a file using streaming reads.
    
    Args:
        file_path: Path to the file to hash
        
    Returns:
        SHA-256 hash as hexadecimal string
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        PermissionError: If the file cannot be read
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    sha256_hash = hashlib.sha256()
    
    try:
        with open(file_path, "rb") as f:
            _stream_hash(f, sha256_hash)
    except PermissionError:
        raise PermissionError(f"Cannot read file: {file_path}")
    
    return sha256_hash.hexdigest()


def _stream_hash(file_obj: BinaryIO, hash_obj: hashlib._Hash) -> None:
    """
    Stream data from file object into hash object in 1 MiB chunks.
    
    Args:
        file_obj: Binary file object to read from
        hash_obj: Hash object to update with file data
    """
    chunk_size = 1024 * 1024  # 1 MiB
    
    while True:
        chunk = file_obj.read(chunk_size)
        if not chunk:
            break
        hash_obj.update(chunk) 