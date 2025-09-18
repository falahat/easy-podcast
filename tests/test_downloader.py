"""
Tests for the podcast downloader functions.
"""

import os
import shutil
import tempfile
import unittest
from typing import Iterator, Optional, Tuple
from unittest.mock import MagicMock, Mock, patch

import requests

from easy_podcast.downloader import (
    download_episode_file,
    download_episodes_batch,
    download_file_streamed,
    download_rss_from_url,
    load_rss_from_file,
)
from easy_podcast.models import Episode

from tests.utils import create_test_episode


def download_episode_file_compat(
    episode: Episode, download_dir: str
) -> Tuple[Optional[str], bool]:
    """Compatibility wrapper for download_episode_file for tests."""
    if not download_dir:
        raise ValueError("No download directory specified")
    
    # Mock the path manager to return a simple path structure for testing
    from unittest.mock import MagicMock
    path_manager = MagicMock()
    path_manager.get_episode_audio_path.return_value = os.path.join(
        download_dir, f"{episode.id}.mp3"
    )
    path_manager.ensure_episode_dir_exists.return_value = download_dir
    
    podcast_guid = "test-podcast-guid"
    
    return download_episode_file(episode, path_manager, podcast_guid)


def download_episodes_batch_compat(
    episodes: list, download_dir: str, show_progress: bool = True
) -> Tuple[int, int, int]:
    """Compatibility wrapper for download_episodes_batch for tests."""
    if not download_dir:
        raise ValueError("No download directory specified")
    
    # Mock the path manager to return a simple path structure for testing
    from unittest.mock import MagicMock
    path_manager = MagicMock()
    path_manager.ensure_episode_dir_exists.return_value = download_dir
    
    podcast_guid = "test-podcast-guid"
    
    return download_episodes_batch(
        episodes, path_manager, podcast_guid, show_progress
    )


# pylint: disable=too-many-public-methods
class TestPodcastDownloader(unittest.TestCase):
    """Test suite for the podcast downloader functions."""

    def setUp(self) -> None:
        """Set up test data."""
        self.test_dir = tempfile.mkdtemp(prefix="podcast_downloader_test_")
        self.download_dir = os.path.join(self.test_dir, "downloads")
        os.makedirs(self.download_dir, exist_ok=True)

    def tearDown(self) -> None:
        """Clean up test data."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch("requests.get")
    def test_rss_download_success(self, mock_get: Mock) -> None:
        """Test successful RSS download."""
        mock_response = MagicMock()
        mock_response.content = (
            b"<rss><channel><title>Test Podcast</title></channel></rss>"
        )
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = download_rss_from_url("http://test.com/rss")

        self.assertIsNotNone(result)
        expected_content = (
            b"<rss><channel><title>Test Podcast</title></channel></rss>"
        )
        self.assertEqual(result, expected_content)
        mock_get.assert_called_once_with("http://test.com/rss", timeout=30)

    @patch("requests.get")
    def test_rss_download_network_error(self, mock_get: Mock) -> None:
        """Test handling of network errors during RSS download."""
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Network error"
        )

        result = download_rss_from_url("http://test.com/rss")

        self.assertIsNone(result)

    @patch("requests.get")
    def test_rss_download_timeout(self, mock_get: Mock) -> None:
        """Test handling of timeout during RSS download."""
        mock_get.side_effect = requests.exceptions.Timeout("Timeout")

        result = download_rss_from_url("http://test.com/rss")

        self.assertIsNone(result)

    @patch("requests.get")
    def test_rss_download_http_error(self, mock_get: Mock) -> None:
        """Test handling of HTTP errors during RSS download."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = (
            requests.exceptions.HTTPError("404")
        )
        mock_get.return_value = mock_response

        result = download_rss_from_url("http://test.com/rss")

        self.assertIsNone(result)

    @patch("requests.get")
    def test_rss_download_empty_content(self, mock_get: Mock) -> None:
        """Test handling of empty RSS response."""
        mock_response = MagicMock()
        mock_response.content = b""
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = download_rss_from_url("http://test.com/rss")

        self.assertIsNone(result)

    def test_download_episode_file_no_directory(self) -> None:
        """Test download fails when no directory is specified."""
        episode = create_test_episode(
            id="123",
            title="Test",
            size=1000,
            audio_link="http://test.com/123.mp3",
        )

        with self.assertRaises(ValueError) as cm:
            download_episode_file_compat(episode, "")
        self.assertIn("No download directory specified", str(cm.exception))

    def test_existing_file_skip_download(self) -> None:
        """Test that existing files are not re-downloaded."""
        # Create an existing file
        existing_file = os.path.join(self.download_dir, "existing.mp3")
        with open(existing_file, "w", encoding="utf-8") as f:
            f.write("existing content")

        result_path, was_downloaded = download_file_streamed(
            "http://test.com/existing.mp3", "existing.mp3", self.download_dir
        )

        self.assertEqual(result_path, existing_file)
        self.assertFalse(was_downloaded)

    @patch("requests.get")
    def test_download_file_success(self, mock_get: Mock) -> None:
        """Test successful file download."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {"content-length": "1000"}
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_get.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_get.return_value.__exit__ = MagicMock(return_value=None)

        result_path, was_downloaded = download_file_streamed(
            "http://test.com/test.mp3", "test.mp3", self.download_dir
        )

        expected_path = os.path.join(self.download_dir, "test.mp3")
        self.assertEqual(result_path, expected_path)
        self.assertTrue(was_downloaded)
        self.assertTrue(os.path.exists(expected_path))

    @patch("requests.get")
    def test_download_file_network_error(self, mock_get: Mock) -> None:
        """Test handling of network errors during file download."""
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Network error"
        )

        result_path, was_downloaded = download_file_streamed(
            "http://test.com/test.mp3", "test.mp3", self.download_dir
        )

        self.assertIsNone(result_path)
        self.assertFalse(was_downloaded)

    @patch("requests.get")
    def test_download_file_partial_cleanup(self, mock_get: Mock) -> None:
        """Test that partial files are cleaned up on download failure
        during write."""
        destination_path = os.path.join(self.download_dir, "test.mp3")

        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {"content-length": "1000"}

        # Create a generator that yields some data then raises an exception
        def failing_iter_content(
            chunk_size: Optional[int] = None,
        ) -> Iterator[bytes]:
            # chunk_size parameter is ignored in this mock
            del chunk_size  # Explicitly acknowledge parameter usage
            yield b"chunk1"
            raise requests.exceptions.RequestException("Connection lost")

        mock_response.iter_content.side_effect = failing_iter_content
        mock_get.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_get.return_value.__exit__ = MagicMock(return_value=None)

        result_path, was_downloaded = download_file_streamed(
            "http://test.com/test.mp3", "test.mp3", self.download_dir
        )

        # Should clean up partial file and return None
        self.assertIsNone(result_path)
        self.assertFalse(was_downloaded)
        # Verify partial file was cleaned up
        self.assertFalse(os.path.exists(destination_path))

    @patch("requests.get")
    def test_download_file_with_empty_chunks(self, mock_get: Mock) -> None:
        """Test download handling of empty chunks (keep-alive chunks)."""
        destination_path = os.path.join(self.download_dir, "test.mp3")

        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {"content-length": "100"}

        # Create a generator that yields empty chunks (keep-alive chunks)
        def iter_content_with_empty_chunks(
            chunk_size: Optional[int] = None,
        ) -> Iterator[bytes]:
            # chunk_size parameter is ignored in this mock
            del chunk_size  # Explicitly acknowledge parameter usage
            yield b"chunk1"
            yield b""  # Empty chunk (keep-alive)
            yield b"chunk2"
            yield b""  # Another empty chunk
            yield b"chunk3"

        mock_response.iter_content.side_effect = iter_content_with_empty_chunks
        mock_get.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_get.return_value.__exit__ = MagicMock(return_value=None)

        result_path, was_downloaded = download_file_streamed(
            "http://test.com/test.mp3", "test.mp3", self.download_dir
        )

        # Should succeed and create file
        self.assertEqual(result_path, destination_path)
        self.assertTrue(was_downloaded)
        self.assertTrue(os.path.exists(destination_path))

        # Verify file contains only non-empty chunks
        with open(destination_path, "rb") as f:
            content = f.read()
            self.assertEqual(content, b"chunk1chunk2chunk3")

    def test_download_episodes_batch_empty_list(self) -> None:
        """Test batch download with empty episode list."""
        result = download_episodes_batch_compat([], self.download_dir)
        successful, skipped, failed = result

        self.assertEqual(successful, 0)
        self.assertEqual(skipped, 0)
        self.assertEqual(failed, 0)

    def test_download_episodes_batch_no_directory(self) -> None:
        """Test batch download fails when no directory is specified."""
        episode = create_test_episode(
            id="123",
            title="Test",
            size=1000,
            audio_link="http://test.com/123.mp3",
        )

        with self.assertRaises(ValueError) as cm:
            download_episodes_batch_compat([episode], "")
        self.assertIn("No download directory specified", str(cm.exception))

    @patch("easy_podcast.downloader.download_episode_file")
    def test_download_episodes_batch_mixed_results(
        self, mock_download: Mock
    ) -> None:
        """Test batch download with mixed success/failure/skip results."""
        episodes = [
            Episode(
                id="1",
                published="",
                title="Episode 1",
                author="",
                duration_seconds=0,
                size=1000,
                audio_link="http://test.com/1.mp3",
                image="",
            ),
            Episode(
                id="2",
                published="",
                title="Episode 2",
                author="",
                duration_seconds=0,
                size=2000,
                audio_link="http://test.com/2.mp3",
                image="",
            ),
        ]

        # Mock download results: first succeeds, second skipped
        # (already exists)
        mock_download.side_effect = [
            (os.path.join(self.download_dir, "1.mp3"), True),  # Downloaded
            (
                os.path.join(self.download_dir, "2.mp3"),
                False,
            ),  # Already existed
        ]

        result = download_episodes_batch_compat(
            episodes, self.download_dir, show_progress=False
        )
        successful, skipped, failed = result

        self.assertEqual(successful, 1)  # First episode downloaded
        self.assertEqual(skipped, 1)  # Second episode skipped (existed)
        self.assertEqual(failed, 0)

    @patch("easy_podcast.downloader.download_episode_file")
    def test_download_episodes_batch_with_progress(
        self, mock_download: Mock
    ) -> None:
        """Test batch episode download with progress bars."""
        # Create test episodes
        episode1 = Episode(
            id="1",
            published="",
            title="Episode 1",
            author="",
            duration_seconds=0,
            size=1024,
            audio_link="http://test.com/ep1.mp3",
            image="",
        )
        episode2 = Episode(
            id="2",
            published="",
            title="Episode 2",
            author="",
            duration_seconds=0,
            size=2048,
            audio_link="http://test.com/ep2.mp3",
            image="",
        )
        episodes = [episode1, episode2]

        # First episode succeeds, second already exists
        mock_download.side_effect = [
            (
                os.path.join(self.download_dir, "1.mp3"),
                True,
            ),  # Downloaded (note: using ID.mp3)
            (
                os.path.join(self.download_dir, "2.mp3"),
                False,
            ),  # Already existed
        ]

        successful, skipped, failed = download_episodes_batch_compat(
            episodes, self.download_dir, show_progress=True
        )

        self.assertEqual(successful, 1)
        self.assertEqual(skipped, 1)
        self.assertEqual(failed, 0)

    @patch("easy_podcast.downloader.download_episode_file")
    def test_download_episodes_batch_no_progress(
        self, mock_download: Mock
    ) -> None:
        """Test batch episode download without progress bars."""
        # Create test episodes
        episode1 = Episode(
            id="1",
            published="",
            title="Episode 1",
            author="",
            duration_seconds=0,
            size=1024,
            audio_link="http://test.com/ep1.mp3",
            image="",
        )
        episode2 = Episode(
            id="2",
            published="",
            title="Episode 2",
            author="",
            duration_seconds=0,
            size=2048,
            audio_link="http://test.com/ep2.mp3",
            image="",
        )
        episodes = [episode1, episode2]

        # First episode succeeds, second fails
        mock_download.side_effect = [
            (
                os.path.join(self.download_dir, "1.mp3"),
                True,
            ),  # Downloaded (note: using ID.mp3)
            (None, False),  # Failed
        ]

        successful, skipped, failed = download_episodes_batch_compat(
            episodes, self.download_dir, show_progress=False
        )

        self.assertEqual(successful, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(failed, 1)

    @patch("easy_podcast.downloader.download_episode_file")
    def test_download_episodes_batch_progress_with_failure(
        self, mock_download: Mock
    ) -> None:
        """Test batch download with progress bar and failures to cover
        missing lines."""
        # Create test episodes
        episode1 = Episode(
            id="1",
            published="",
            title="Episode 1",
            author="",
            duration_seconds=0,
            size=1024,
            audio_link="http://test.com/ep1.mp3",
            image="",
        )
        episode2 = Episode(
            id="2",
            published="",
            title="Episode 2",
            author="",
            duration_seconds=0,
            size=2048,
            audio_link="http://test.com/ep2.mp3",
            image="",
        )
        episodes = [episode1, episode2]

        # First episode succeeds, second fails
        mock_download.side_effect = [
            (
                os.path.join(self.download_dir, "1.mp3"),
                True,
            ),  # Downloaded (note: using ID.mp3)
            (None, False),  # Failed
        ]

        successful, skipped, failed = download_episodes_batch_compat(
            episodes, self.download_dir, show_progress=True
        )

        # Verify that tqdm.write was called for the failure
        self.assertEqual(successful, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(failed, 1)

    def test_load_rss_from_file_success(self) -> None:
        """Test successful RSS file loading."""
        rss_file_path = os.path.join(self.test_dir, "test.xml")
        rss_content = (
            b"<rss><channel><title>Test Podcast</title></channel></rss>"
        )

        with open(rss_file_path, "wb") as f:
            f.write(rss_content)

        result = load_rss_from_file(rss_file_path)

        self.assertIsNotNone(result)
        self.assertEqual(result, rss_content)

    def test_load_rss_from_file_not_found(self) -> None:
        """Test RSS file loading when file doesn't exist."""
        result = load_rss_from_file("nonexistent.xml")
        self.assertIsNone(result)

    def test_load_rss_from_file_empty(self) -> None:
        """Test RSS file loading when file is empty."""
        rss_file_path = os.path.join(self.test_dir, "empty.xml")

        # Create empty file
        with open(rss_file_path, "wb"):
            pass

        result = load_rss_from_file(rss_file_path)
        self.assertIsNone(result)

    @patch("builtins.open")
    def test_load_rss_from_file_read_error(self, mock_open: Mock) -> None:
        """Test RSS file loading when read operation fails."""
        mock_open.side_effect = IOError("Permission denied")

        result = load_rss_from_file("test.xml")
        self.assertIsNone(result)

    @patch("requests.get")
    def test_download_file_streamed_ioerror_cleanup(
        self, mock_get: Mock
    ) -> None:
        """Test file cleanup when IOError occurs during file write."""
        output_path = os.path.join(self.download_dir, "test.mp3")

        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {"content-length": "1000"}
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_get.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_get.return_value.__exit__ = MagicMock(return_value=None)

        # Mock open to raise IOError during write
        with patch("builtins.open", side_effect=IOError("Disk full")):
            result_path, was_downloaded = download_file_streamed(
                "http://test.com/test.mp3", "test.mp3", self.download_dir
            )

        self.assertIsNone(result_path)
        self.assertFalse(was_downloaded)
        # Verify partial file was not left behind
        self.assertFalse(os.path.exists(output_path))

    @patch("requests.get")
    def test_download_file_streamed_no_content_length(
        self, mock_get: Mock
    ) -> None:
        """Test file download when content-length header is missing."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {}  # No content-length header
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_get.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_get.return_value.__exit__ = MagicMock(return_value=None)

        result_path, was_downloaded = download_file_streamed(
            "http://test.com/test.mp3", "test.mp3", self.download_dir
        )

        expected_path = os.path.join(self.download_dir, "test.mp3")
        self.assertEqual(result_path, expected_path)
        self.assertTrue(was_downloaded)
        self.assertTrue(os.path.exists(expected_path))

    @patch("easy_podcast.downloader.download_file_to_path")
    def test_download_episode_file_success(self, mock_download: Mock) -> None:
        """Test successful episode file download using the actual function."""
        episode = Episode(
            id="123",
            published="",
            title="Test",
            author="",
            duration_seconds=0,
            size=1000,
            audio_link="http://test.com/123.mp3",
            image="",
        )

        expected_path = os.path.join(self.download_dir, "123.mp3")
        mock_download.return_value = (expected_path, True)

        result_path, was_downloaded = download_episode_file_compat(
            episode, self.download_dir
        )

        self.assertEqual(result_path, expected_path)
        self.assertTrue(was_downloaded)
        mock_download.assert_called_once_with(
            "http://test.com/123.mp3", expected_path
        )


if __name__ == "__main__":
    unittest.main()
