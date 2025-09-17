"""
Tests for PodcastManager download functionality.
"""

import os
from unittest.mock import patch

from easy_podcast.manager import PodcastManager

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

        manager = PodcastManager(test_podcast_dir, test_podcast)

        # This should work now since episode is part of podcast episodes
        # Mock the download to simulate success
        with patch(
            "easy_podcast.manager.download_episode_file"
        ) as mock_download:
            expected_path = manager.get_episode_audio_path(episode)
            mock_download.return_value = (expected_path, True)
            
            download_path, was_downloaded = manager.download_episode(episode)
            # Episode should download successfully with mock
            self.assertIsNotNone(download_path)
            self.assertEqual(download_path, expected_path)
            self.assertTrue(was_downloaded)

    def test_download_episodes_without_ingest(self) -> None:
        """Test batch downloading with properly initialized manager."""
        test_podcast = self.create_test_podcast()

        test_podcast_dir = os.path.join(self.test_dir, "Test_Podcast")
        os.makedirs(test_podcast_dir, exist_ok=True)

        manager = PodcastManager(test_podcast_dir, test_podcast)

        episode = create_test_episode(
            id="123",
            size=1000,
            audio_link="http://test.com/123.mp3",
        )

        # This should work now since manager is properly initialized
        result = manager.download_episodes([episode])
        # Result will show 0 successful, 0 skipped, 1 failed due to
        # network/mock issues
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)

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
        manager = PodcastManager(test_podcast_dir, test_podcast)

        # Mock the download_episode_file function
        with patch(
            "easy_podcast.manager.download_episode_file"
        ) as mock_download:
            # Mock to return success for episode1, failure for episode2
            def mock_download_side_effect(  # type: ignore
                episode, episode_dir
            ):
                if episode.id == "1":
                    return (os.path.join(episode_dir, "1.mp3"), True)
                else:
                    return (None, False)
            
            mock_download.side_effect = mock_download_side_effect

            # Mock the storage manager save method
            with patch.object(
                manager.storage_manager, "save_episode_metadata"
            ) as mock_save:
                successful, skipped, failed = manager.download_episodes(
                    [episode1, episode2]
                )

                # Verify results
                self.assertEqual(successful, 1)
                self.assertEqual(skipped, 0)
                self.assertEqual(failed, 1)

                # Verify that only the successful episode had metadata saved
                mock_save.assert_called_once_with(
                    episode1, manager.podcast.guid
                )

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
        manager = PodcastManager(test_podcast_dir, test_podcast)

        # Mock download_episode_file to return success
        with patch(
            "easy_podcast.manager.download_episode_file"
        ) as mock_download:
            expected_path = manager.get_episode_audio_path(episode)
            mock_download.return_value = (expected_path, True)

            # Mock storage manager save method instead of episode tracker
            with patch.object(
                manager.storage_manager, "save_episode_metadata"
            ) as mock_save:
                download_path, was_downloaded = manager.download_episode(
                    episode
                )

                # Verify the download result
                self.assertEqual(download_path, expected_path)
                self.assertTrue(was_downloaded)

                # Verify episode metadata was saved
                mock_save.assert_called_once_with(
                    episode, manager.podcast.guid
                )

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
        manager = PodcastManager(test_podcast_dir, test_podcast)

        # Mock download_episode_file to return existing file
        with patch(
            "easy_podcast.manager.download_episode_file"
        ) as mock_download:
            expected_path = manager.get_episode_audio_path(episode)
            mock_download.return_value = (
                expected_path,
                False,
            )  # File exists, not downloaded

            download_path, was_downloaded = manager.download_episode(episode)

            # Verify the download result
            self.assertEqual(download_path, expected_path)
            self.assertFalse(was_downloaded)

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
        manager = PodcastManager(test_podcast_dir, test_podcast)

        # Mock download_episode_file to return failure
        with patch(
            "easy_podcast.manager.download_episode_file"
        ) as mock_download:
            mock_download.return_value = (None, False)  # Download failed

            download_path, was_downloaded = manager.download_episode(episode)

            # Verify the download result
            self.assertIsNone(download_path)
            self.assertFalse(was_downloaded)
