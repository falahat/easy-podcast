"""
Tests for PodcastManager download functionality.
"""

import os
from unittest.mock import patch

from tests.base import PodcastTestBase
from tests.utils import create_test_episode


class TestPodcastManagerDownloads(PodcastTestBase):
    """Test suite for PodcastManager download functionality."""

    def test_download_episode_without_ingest(self) -> None:
        """Test downloading episode with properly initialized manager."""
        episode = create_test_episode(
            id="123",
            size=1000,
            audio_link="http://test.com/123.mp3",
        )

        test_podcast = self.create_test_podcast(episodes=[episode])

        test_podcast_dir = self.test_dir  # Use base test dir, not subdirectory

        manager = self.create_manager(test_podcast, test_podcast_dir)

        # Mock the download function to simulate success
        with patch(
            "easy_podcast.episode_downloader.download_file_to_path"
        ) as mock_download:
            expected_path = manager.get_episode_audio_path(episode)
            mock_download.return_value = (expected_path, True)

            # Use the new download_episodes method
            summary = manager.download_episodes([episode])

            # Episode should download successfully with mock
            self.assertEqual(summary.successful, 1)
            self.assertEqual(summary.skipped, 0)
            self.assertEqual(summary.failed, 0)

            # Verify the download function was called with correct arguments
            mock_download.assert_called_once_with(
                "http://test.com/123.mp3", expected_path
            )

    def test_download_episodes_without_ingest(self) -> None:
        """Test batch downloading with properly initialized manager."""
        test_podcast = self.create_test_podcast()

        test_podcast_dir = os.path.join(self.test_dir, "Test_Podcast")
        os.makedirs(test_podcast_dir, exist_ok=True)

        manager = self.create_manager(test_podcast, test_podcast_dir)

        episode = create_test_episode(
            id="123",
            size=1000,
            audio_link="http://test.com/123.mp3",
        )

        # This should work now since manager is properly initialized
        result = manager.download_episodes([episode])
        # Result will show 0 successful, 0 skipped, 1 failed due to
        # network/mock issues
        from easy_podcast.episode_downloader import DownloadSummary

        self.assertIsInstance(result, DownloadSummary)
        self.assertEqual(result.successful, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.failed, 1)

    def test_download_episodes_with_episode_tracking(self) -> None:
        """Test download_episodes with episode tracking after download."""
        # Create a mock podcast and manager
        episode1 = create_test_episode(
            id="1",
            title="Episode 1",
            size=1000,
            audio_link="http://test.com/ep1.mp3",
        )
        episode2 = create_test_episode(
            id="2",
            title="Episode 2",
            size=2000,
            audio_link="http://test.com/ep2.mp3",
        )
        test_podcast = self.create_test_podcast(episodes=[episode1, episode2])
        test_podcast_dir = os.path.join(self.test_dir, "Test_Podcast")
        os.makedirs(test_podcast_dir, exist_ok=True)
        manager = self.create_manager(test_podcast, test_podcast_dir)

        # Mock the download function to avoid actual downloads
        with patch(
            "easy_podcast.episode_downloader.download_file_to_path"
        ) as mock_download:
            # Mock to return success for episode1, failure for episode2
            def mock_download_side_effect(url, path):  # type: ignore
                if "ep1.mp3" in url:
                    # Successful download
                    return (path, True)
                else:
                    # Failed download
                    return (None, False)

            mock_download.side_effect = mock_download_side_effect

            download_summary = manager.download_episodes([episode1, episode2])

            # Verify results
            self.assertEqual(download_summary.successful, 1)
            self.assertEqual(download_summary.failed, 1)
            self.assertEqual(download_summary.skipped, 0)

    def test_download_episode_success_with_tracking(self) -> None:
        """Test download_episode with successful download and tracking."""
        episode = create_test_episode(
            id="download_test",
            title="Download Test Episode",
            size=1000,
            audio_link="http://test.com/download_test.mp3",
        )

        test_podcast = self.create_test_podcast(episodes=[episode])

        test_podcast_dir = os.path.join(self.test_dir, "Test_Podcast")
        os.makedirs(test_podcast_dir, exist_ok=True)
        manager = self.create_manager(test_podcast, test_podcast_dir)

        # Mock the download function to simulate success
        with patch(
            "easy_podcast.episode_downloader.download_file_to_path"
        ) as mock_download:
            expected_path = manager.get_episode_audio_path(episode)
            mock_download.return_value = (expected_path, True)

            download_summary = manager.download_episodes([episode])

            # Verify the download result
            self.assertEqual(download_summary.successful, 1)
            self.assertEqual(download_summary.failed, 0)
            self.assertEqual(len(download_summary.results), 1)

            result = download_summary.results[0]
            self.assertTrue(result.success)
            self.assertEqual(result.file_path, expected_path)

    def test_download_episode_already_exists(self) -> None:
        """Test download_episode when episode already exists."""
        episode = create_test_episode(
            id="existing_test",
            title="Existing Test Episode",
            size=1000,
            audio_link="http://test.com/existing_test.mp3",
        )

        test_podcast = self.create_test_podcast(episodes=[episode])

        test_podcast_dir = os.path.join(self.test_dir, "Test_Podcast")
        os.makedirs(test_podcast_dir, exist_ok=True)
        manager = self.create_manager(test_podcast, test_podcast_dir)

        # Mock download_episode_file to return existing file
        # Create the episode file to simulate it already exists
        episode_path = manager.get_episode_audio_path(episode)
        os.makedirs(os.path.dirname(episode_path), exist_ok=True)
        with open(episode_path, "w", encoding="utf-8") as f:
            f.write("existing content")

        download_summary = manager.download_episodes([episode])

        # Verify the download result
        self.assertEqual(
            download_summary.successful, 0
        )  # File already exists, so skipped
        self.assertEqual(download_summary.skipped, 1)
        self.assertEqual(len(download_summary.results), 1)

        result = download_summary.results[0]
        self.assertTrue(
            result.was_cached
        )  # Should indicate it was cached/existing

    def test_download_episode_failure(self) -> None:
        """Test download_episode when download fails."""
        episode = create_test_episode(
            id="failed_test",
            title="Failed Test Episode",
            size=1000,
            audio_link="http://test.com/failed_test.mp3",
        )

        test_podcast = self.create_test_podcast(episodes=[episode])

        test_podcast_dir = os.path.join(self.test_dir, "Test_Podcast")
        os.makedirs(test_podcast_dir, exist_ok=True)
        manager = self.create_manager(test_podcast, test_podcast_dir)

        # Mock the download function to return failure
        with patch(
            "easy_podcast.episode_downloader.download_file_to_path"
        ) as mock_download:
            mock_download.return_value = (None, False)  # Download failed

            download_summary = manager.download_episodes([episode])

            # Verify the download result
            self.assertEqual(download_summary.successful, 0)
            self.assertEqual(download_summary.failed, 1)
            self.assertEqual(len(download_summary.results), 1)

            result = download_summary.results[0]
            self.assertFalse(result.success)
            self.assertIsNone(result.file_path)
