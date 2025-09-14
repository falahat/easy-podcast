"""
Tests for utility functions.
"""

import unittest
from typing import List, Optional, Tuple

from easy_podcast.utils import (
    format_bytes,
    parse_duration_to_seconds,
    sanitize_filename,
)


class TestUtils(unittest.TestCase):
    """Test suite for utility functions."""

    def test_format_bytes_various_sizes(self) -> None:
        """Test format_bytes function with various byte counts."""
        test_cases: List[Tuple[Optional[int], str]] = [
            (0, "0 B"),
            (512, "512.00 B"),
            (1024, "1.00 KiB"),
            (1536, "1.50 KiB"),
            (1048576, "1.00 MiB"),
            (2097152, "2.00 MiB"),
            (1073741824, "1.00 GiB"),
            (1099511627776, "1.00 TiB"),
            (None, "0 B"),
        ]

        for byte_count, expected in test_cases:
            with self.subTest(byte_count=byte_count):
                result = format_bytes(byte_count)
                self.assertEqual(result, expected)

    def test_format_bytes_edge_cases(self) -> None:
        """Test format_bytes with edge cases."""
        # Very large number
        very_large = 1024**5  # Larger than TiB
        result = format_bytes(very_large)
        self.assertTrue(result.endswith("TiB"))

        # Fractional values that should round properly
        result = format_bytes(1536)  # 1.5 KiB
        self.assertEqual(result, "1.50 KiB")

        # Just under the next threshold
        result = format_bytes(1023)  # Just under 1 KiB
        self.assertEqual(result, "1023.00 B")

    def test_format_bytes_precision(self) -> None:
        """Test that format_bytes maintains proper precision."""
        # Test that we get 2 decimal places
        result = format_bytes(1234567)  # Should be ~1.18 MiB
        self.assertTrue(result.endswith("MiB"))
        parts = result.split(" ")
        self.assertEqual(len(parts), 2)
        # Check that we have decimal places
        self.assertIn(".", parts[0])

    def test_sanitize_filename_edge_cases(self) -> None:
        """Test sanitize_filename with edge cases to improve coverage."""
        # Test empty string
        result = sanitize_filename("")
        self.assertEqual(result, "unnamed")

        # Test string with only spaces and dots
        result = sanitize_filename("  . . .  ")
        self.assertEqual(result, "unnamed")

        # Test string with only spaces
        result = sanitize_filename("   ")
        self.assertEqual(result, "unnamed")

        # Test string with only dots
        result = sanitize_filename("...")
        self.assertEqual(result, "unnamed")

    def test_parse_duration_to_seconds_mm_ss(self) -> None:
        """Test parsing MM:SS format."""
        self.assertEqual(parse_duration_to_seconds("30:45"), 1845)
        self.assertEqual(parse_duration_to_seconds("05:00"), 300)
        self.assertEqual(parse_duration_to_seconds("00:30"), 30)

    def test_parse_duration_to_seconds_hh_mm_ss(self) -> None:
        """Test parsing HH:MM:SS format."""
        self.assertEqual(parse_duration_to_seconds("1:30:45"), 5445)
        self.assertEqual(parse_duration_to_seconds("2:00:00"), 7200)
        self.assertEqual(parse_duration_to_seconds("0:05:30"), 330)

    def test_parse_duration_to_seconds_raw_seconds(self) -> None:
        """Test parsing raw seconds format."""
        self.assertEqual(parse_duration_to_seconds("3600"), 3600)
        self.assertEqual(parse_duration_to_seconds("300.5"), 300)
        self.assertEqual(parse_duration_to_seconds("0"), 0)

    def test_parse_duration_to_seconds_invalid(self) -> None:
        """Test parsing invalid formats returns -1."""
        self.assertEqual(parse_duration_to_seconds(""), -1)
        self.assertEqual(parse_duration_to_seconds("   "), -1)
        self.assertEqual(parse_duration_to_seconds("invalid"), -1)
        self.assertEqual(parse_duration_to_seconds("1:2:3:4"), -1)
        self.assertEqual(parse_duration_to_seconds("not:a:number"), -1)


if __name__ == "__main__":
    unittest.main()
