"""
Pure storage layer for file operations.

This module provides low-level file operations without any business logic.
"""

import json
import os
from typing import Any, Dict, Optional


class Storage:
    """Pure file operations without business logic."""

    def __init__(self, base_dir: str = "./data"):
        """Initialize with base directory."""
        self.base_dir = base_dir

    def ensure_directory(self, path: str) -> None:
        """Create directory if it doesn't exist."""
        os.makedirs(path, exist_ok=True)

    def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        return os.path.exists(path)

    def read_json(self, path: str) -> Optional[Dict[str, Any]]:
        """Read JSON file, return None if file doesn't exist or invalid JSON."""
        if not os.path.exists(path):
            return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, FileNotFoundError, IOError):
            return None

    def write_json(self, path: str, data: Dict[str, Any]) -> bool:
        """Write data to JSON file, return success status."""
        try:
            # Ensure directory exists
            directory = os.path.dirname(path)
            if directory:
                self.ensure_directory(directory)
            
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except (IOError, TypeError):
            return False

    def read_bytes(self, path: str) -> Optional[bytes]:
        """Read file as bytes, return None if error."""
        try:
            with open(path, "rb") as f:
                return f.read()
        except (FileNotFoundError, IOError):
            return None

    def write_bytes(self, path: str, data: bytes) -> bool:
        """Write bytes to file, return success status."""
        try:
            # Ensure directory exists
            directory = os.path.dirname(path)
            if directory:
                self.ensure_directory(directory)
            
            with open(path, "wb") as f:
                f.write(data)
            return True
        except IOError:
            return False

    def write_text_lines(self, path: str, lines: list) -> bool:
        """Write lines to text file (for JSONL), return success status."""
        try:
            # Ensure directory exists
            directory = os.path.dirname(path)
            if directory:
                self.ensure_directory(directory)
            
            with open(path, "w", encoding="utf-8") as f:
                for line in lines:
                    f.write(line + "\n")
            return True
        except IOError:
            return False

    def read_text_lines(self, path: str) -> Optional[list]:
        """Read lines from text file, return None if error."""
        if not os.path.exists(path):
            return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                return [line.strip() for line in f.readlines()]
        except (FileNotFoundError, IOError):
            return None

    def list_directories(self, path: str) -> list:
        """List subdirectories in given path."""
        if not os.path.exists(path):
            return []
        
        try:
            return [item for item in os.listdir(path)
                    if os.path.isdir(os.path.join(path, item))]
        except OSError:
            return []

    def join_path(self, *parts: str) -> str:
        """Join path parts."""
        return os.path.join(*parts)