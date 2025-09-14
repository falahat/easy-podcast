"""
Utility functions for the podcast package.
"""

from typing import Optional


def parse_duration_to_seconds(duration_str: str) -> int:
    """Convert duration string to seconds, return -1 if parsing fails.

    Supports formats:
    - "30:45" (MM:SS) -> 1845 seconds
    - "1:30:45" (HH:MM:SS) -> 5445 seconds
    - "3600" (raw seconds) -> 3600 seconds

    Returns:
        Duration in seconds, or -1 if parsing fails.
    """
    if not duration_str or not duration_str.strip():
        return -1

    duration_str = duration_str.strip()

    try:
        # Try to parse as colon-separated time format
        if ":" in duration_str:
            parts = duration_str.split(":")
            if len(parts) == 2:  # MM:SS
                minutes, seconds = int(parts[0]), int(parts[1])
                return minutes * 60 + seconds
            if len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = (
                    int(parts[0]),
                    int(parts[1]),
                    int(parts[2]),
                )
                return hours * 3600 + minutes * 60 + seconds
            return -1
        # Try to parse as raw seconds (integer or float)
        return int(float(duration_str))
    except (ValueError, OverflowError):
        return -1


def format_bytes(byte_count: Optional[int]) -> str:
    """Convert bytes to human-readable format (B, KiB, MiB, GiB, TiB)."""
    if byte_count == 0 or byte_count is None:
        return "0 B"

    size_units = {0: "B", 1: "KiB", 2: "MiB", 3: "GiB", 4: "TiB"}
    current_size = float(byte_count)
    unit_index = 0

    while current_size >= 1024 and unit_index < len(size_units) - 1:
        current_size /= 1024
        unit_index += 1

    return f"{current_size:.2f} {size_units[unit_index]}"


def sanitize_filename(filename: str) -> str:
    """Remove invalid filename characters and ensure valid output."""
    # Replace Windows forbidden characters
    invalid_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
    clean_filename = filename
    for char in invalid_chars:
        clean_filename = clean_filename.replace(char, "_")

    # Remove leading/trailing whitespace and dots
    clean_filename = clean_filename.strip(". ")

    return clean_filename if clean_filename else "unnamed"
