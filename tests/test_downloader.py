"""
Simplified tests for the podcast downloader functions.
Tests only the core download functions that remain after PathManager removal.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests

from easy_podcast.downloader import (
    download_file_streamed,
    download_rss_from_url,
    load_rss_from_file,
)


class TestDownloader(unittest.TestCase):
    """Test podcast downloader functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.download_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        if os.path.exists(self.download_dir):
            shutil.rmtree(self.download_dir)

    @patch("requests.get")
    def test_rss_download_success(self, mock_get: Mock) -> None:
        """Test successful RSS download."""
        mock_response = Mock()
        mock_response.content = b"<rss>content</rss>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = download_rss_from_url("http://example.com/rss")

        self.assertEqual(result, b"<rss>content</rss>")
        mock_get.assert_called_once_with("http://example.com/rss", timeout=30)

    @patch("requests.get")
    def test_rss_download_network_error(self, mock_get: Mock) -> None:
        """Test RSS download with network error."""
        mock_get.side_effect = requests.exceptions.RequestException(
            "Network error"
        )

        result = download_rss_from_url("http://example.com/rss")

        self.assertIsNone(result)

    @patch("requests.get")
    def test_rss_download_timeout(self, mock_get: Mock) -> None:
        """Test RSS download with timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")

        result = download_rss_from_url("http://example.com/rss")

        self.assertIsNone(result)

    @patch("requests.get")
    def test_rss_download_http_error(self, mock_get: Mock) -> None:
        """Test RSS download with HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = (
            requests.exceptions.HTTPError("404")
        )
        mock_get.return_value = mock_response

        result = download_rss_from_url("http://example.com/rss")

        self.assertIsNone(result)

    def test_load_rss_from_file_success(self) -> None:
        """Test successful RSS file loading."""
        # Create test RSS file
        rss_content = b"<rss>test content</rss>"
        rss_file = os.path.join(self.download_dir, "test.xml")
        with open(rss_file, "wb") as f:
            f.write(rss_content)

        result = load_rss_from_file(rss_file)

        self.assertEqual(result, rss_content)

    def test_load_rss_from_file_not_found(self) -> None:
        """Test RSS file loading with non-existent file."""
        result = load_rss_from_file("nonexistent.xml")

        self.assertIsNone(result)

    @patch("requests.get")
    def test_download_file_streamed_success(self, mock_get: Mock) -> None:
        """Test successful file download using deprecated function."""
        mock_response = Mock()
        mock_response.headers = {"content-length": "1000"}
        mock_response.iter_content.return_value = [b"test content"]
        mock_response.raise_for_status.return_value = None
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_get.return_value = mock_response

        file_path, was_downloaded = download_file_streamed(
            "http://example.com/test.mp3", "test.mp3", self.download_dir
        )

        expected_path = os.path.join(self.download_dir, "test.mp3")
        self.assertEqual(file_path, expected_path)
        self.assertTrue(was_downloaded)
        self.assertTrue(os.path.exists(expected_path))

    @patch("requests.get")
    def test_download_file_streamed_network_error(
        self, mock_get: Mock
    ) -> None:
        """Test file download with network error."""
        mock_get.side_effect = requests.exceptions.RequestException(
            "Network error"
        )

        file_path, was_downloaded = download_file_streamed(
            "http://example.com/test.mp3", "test.mp3", self.download_dir
        )

        self.assertIsNone(file_path)
        self.assertFalse(was_downloaded)


if __name__ == "__main__":
    unittest.main()
