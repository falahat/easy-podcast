"""
Tests for PodcastManager episode management functionality.
"""

import os
from typing import Any, Dict, List
from unittest.mock import Mock, patch

from easy_podcast.manager import PodcastManager
from easy_podcast.models import Podcast  # Keep for remaining instances

from tests.base import PodcastTestBase
from tests.utils import create_test_episode


class TestPodcastManagerEpisodes(PodcastTestBase):
    """Test suite for PodcastManager episode management functionality."""

    def test_get_new_episodes_without_podcast(self) -> None:
        """Test get_new_episodes with an empty podcast."""
        test_podcast = self.create_test_podcast(
            title="Empty Podcast",
            safe_title="Empty_Podcast",
            episodes=[],  # Empty episodes list
        )

        test_podcast_dir = os.path.join(self.test_dir, "Empty_Podcast")
        os.makedirs(test_podcast_dir, exist_ok=True)

        manager = PodcastManager(test_podcast_dir, test_podcast)
        new_episodes = manager.get_new_episodes()
        self.assertEqual(len(new_episodes), 0)

    def test_get_episode_audio_path(self) -> None:
        """Test get_episode_audio_path method."""
        episode = create_test_episode(
            id="test123",
            title="Test Episode",
            size=1000,
            audio_link="http://test.com/test.mp3",
        )

        test_podcast = self.create_test_podcast(
            episodes=[episode],
        )

        test_podcast_dir = os.path.join(self.test_dir, "Test_Podcast")
        os.makedirs(test_podcast_dir, exist_ok=True)
        manager = PodcastManager(test_podcast_dir, test_podcast)

        expected_path = os.path.join(
            manager.downloads_dir, episode.audio_filename
        )
        actual_path = manager.episode_tracker.get_episode_audio_path(episode)

        self.assertEqual(actual_path, expected_path)

    def test_episode_audio_exists(self) -> None:
        """Test episode_audio_exists method."""
        episode = create_test_episode(
            id="test456",
            title="Test Episode",
            size=1000,
            audio_link="http://test.com/test.mp3",
        )

        test_podcast = self.create_test_podcast(
            episodes=[episode],
        )

        test_podcast_dir = os.path.join(self.test_dir, "Test_Podcast")
        os.makedirs(test_podcast_dir, exist_ok=True)
        manager = PodcastManager(test_podcast_dir, test_podcast)

        # File doesn't exist initially
        self.assertFalse(manager.episode_tracker.episode_audio_exists(episode))

        # Create the file
        episode_path = manager.episode_tracker.get_episode_audio_path(episode)
        with open(episode_path, "w", encoding="utf-8") as f:
            f.write("test content")

        # File should exist now
        self.assertTrue(manager.episode_tracker.episode_audio_exists(episode))

    def test_get_episode_transcript_path(self) -> None:
        """Test get_episode_transcript_path method."""
        episode = create_test_episode(
            id="test789",
            title="Test Episode",
            size=1000,
            audio_link="http://test.com/test.mp3",
        )

        test_podcast = self.create_test_podcast(
            episodes=[episode],
        )

        test_podcast_dir = os.path.join(self.test_dir, "Test_Podcast")
        os.makedirs(test_podcast_dir, exist_ok=True)
        manager = PodcastManager(test_podcast_dir, test_podcast)

        expected_path = os.path.join(
            manager.downloads_dir, episode.transcript_filename
        )
        actual_path = manager.episode_tracker.get_episode_transcript_path(
            episode
        )

        self.assertEqual(actual_path, expected_path)

    def test_episode_transcript_exists(self) -> None:
        """Test episode_transcript_exists method."""
        episode = create_test_episode(
            id="test101",
            title="Test Episode",
            size=1000,
            audio_link="http://test.com/test.mp3",
        )

        test_podcast = Podcast(
            title="Test Podcast",
            rss_url="http://test.com/rss",
            safe_title="Test_Podcast",
            episodes=[episode],
        )

        test_podcast_dir = os.path.join(self.test_dir, "Test_Podcast")
        os.makedirs(test_podcast_dir, exist_ok=True)
        manager = PodcastManager(test_podcast_dir, test_podcast)

        # File doesn't exist initially
        self.assertFalse(
            manager.episode_tracker.episode_transcript_exists(episode)
        )

        # Create the file
        transcript_path = manager.episode_tracker.get_episode_transcript_path(
            episode
        )
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write('{"test": "transcript content"}')

        # File should exist now
        self.assertTrue(
            manager.episode_tracker.episode_transcript_exists(episode)
        )

    @patch("easy_podcast.parser.PodcastParser.from_content")
    @patch("easy_podcast.manager.download_episodes_batch")
    @patch("easy_podcast.parser.download_rss_from_url")
    def test_duplicate_episode_handling(  # pylint: disable=too-many-locals
        self,
        mock_download_rss: Mock,
        mock_download_batch: Mock,
        mock_parse_content: Mock,
    ) -> None:
        """Test existing episodes are not re-downloaded and new ones are."""
        # First ingestion: 2 episodes
        initial_episodes: List[Dict[str, Any]] = [
            {
                "supercast_episode_id": "101",
                "title": "Episode 1",
                "audio_link": "http://test.com/ep1.mp3",
                "size": 1000,
            },
            {
                "supercast_episode_id": "102",
                "title": "Episode 2",
                "audio_link": "http://test.com/ep2.mp3",
                "size": 2000,
            },
        ]
        mock_rss_content = self.create_mock_rss_content(
            initial_episodes, "Test Podcast"
        )
        mock_download_rss.return_value = mock_rss_content

        # Create mock podcast from episodes
        mock_episodes = [
            create_test_episode(
                id="101",
                published="2023-01-01",
                title="Episode 1",
                author="Test",
                duration_seconds=1800,
                size=1000,
                audio_link="http://test.com/ep1.mp3",
            ),
            create_test_episode(
                id="102",
                published="2023-01-02",
                title="Episode 2",
                author="Test",
                duration_seconds=1800,
                size=2000,
                audio_link="http://test.com/ep2.mp3",
            ),
        ]
        mock_podcast = Podcast(
            title="Test Podcast",
            rss_url="http://test.com/rss",
            safe_title="Test_Podcast",
            episodes=mock_episodes,
        )
        mock_parse_content.return_value = mock_podcast
        mock_download_batch.return_value = (
            2,
            0,
            0,
        )  # 2 successful, 0 skipped, 0 failed

        # Ingest and download
        manager = PodcastManager.from_rss_url("http://test.com/rss")
        self.assertIsNotNone(manager)
        if not manager:
            return

        new_episodes = manager.get_new_episodes()
        self.assertEqual(len(new_episodes), 2)

        # Simulate successful download
        for ep in new_episodes:
            # Create dummy files to simulate download
            episode_path = os.path.join(
                manager.downloads_dir, ep.audio_filename
            )
            with open(episode_path, "w", encoding="utf-8") as f:
                f.write("dummy content")
            manager.episode_tracker.add_episode(ep)

        # Second ingestion: one new episode, one old
        updated_episodes: List[Dict[str, Any]] = [
            {
                "supercast_episode_id": "102",
                "title": "Episode 2",
                "audio_link": "http://test.com/ep2.mp3",
                "size": 2000,
            },
            {
                "supercast_episode_id": "103",
                "title": "Episode 3",
                "audio_link": "http://test.com/ep3.mp3",
                "size": 3000,
            },
        ]
        mock_rss_content = self.create_mock_rss_content(
            updated_episodes, "Test Podcast"
        )
        mock_download_rss.return_value = mock_rss_content

        mock_episodes_updated = [
            mock_episodes[1],  # Episode 102
            create_test_episode(
                id="103",
                published="2023-01-03",
                title="Episode 3",
                author="Test",
                duration_seconds=1800,
                size=3000,
                audio_link="http://test.com/ep3.mp3",
            ),
        ]
        mock_podcast_updated = Podcast(
            title="Test Podcast",
            rss_url="http://test.com/rss",
            safe_title="Test_Podcast",
            episodes=mock_episodes_updated,
        )
        mock_parse_content.return_value = mock_podcast_updated

        # Re-create manager to simulate a new run
        manager_new = PodcastManager.from_rss_url("http://test.com/rss")
        self.assertIsNotNone(manager_new)
        if not manager_new:
            return

        # Should only find one new episode
        new_episodes_after_update = manager_new.get_new_episodes()
        self.assertEqual(len(new_episodes_after_update), 1)
        self.assertEqual(new_episodes_after_update[0].id, "103")

        # After adding episodes to the tracker, the original manager should
        # show no new episodes
        new_episodes = manager.get_new_episodes()
        self.assertEqual(len(new_episodes), 0)

        # Simulate downloading episodes
        for episode in new_episodes:
            if manager.episode_tracker:
                manager.episode_tracker.add_episode(episode)

        # After adding episodes to tracker, there should be no new episodes
        new_episodes_after_tracking = manager.get_new_episodes()
        self.assertEqual(len(new_episodes_after_tracking), 0)

        # Second ingestion: 2 old + 2 new episodes
        final_episodes: List[Dict[str, Any]] = initial_episodes + [
            {
                "supercast_episode_id": "103",
                "title": "Episode 3",
                "audio_link": "http://test.com/ep3.mp3",
                "size": 3000,
            },
            {
                "supercast_episode_id": "104",
                "title": "Episode 4",
                "audio_link": "http://test.com/ep4.mp3",
                "size": 4000,
            },
        ]
        mock_rss_content2 = self.create_mock_rss_content(
            final_episodes, "Test Podcast"
        )
        mock_download_rss.return_value = mock_rss_content2

        # Create mock podcast with all 4 episodes
        mock_episodes_updated = mock_episodes + [
            create_test_episode(
                id="103",
                published="2023-01-03",
                title="Episode 3",
                author="Test",
                duration_seconds=1800,
                size=3000,
                audio_link="http://test.com/ep3.mp3",
            ),
            create_test_episode(
                id="104",
                published="2023-01-04",
                title="Episode 4",
                author="Test",
                duration_seconds=1800,
                size=4000,
                audio_link="http://test.com/ep4.mp3",
            ),
        ]
        mock_podcast_updated = Podcast(
            title="Test Podcast",
            rss_url="http://test.com/rss",
            safe_title="Test_Podcast",
            episodes=mock_episodes_updated,
        )
        mock_parse_content.return_value = mock_podcast_updated

        # Re-ingest: Create a new manager from the updated RSS feed
        # Since it's the same RSS URL, it will use the same data directory
        # and episode tracker
        manager_updated = PodcastManager.from_rss_url("http://test.com/rss")
        self.assertIsNotNone(manager_updated)
        assert manager_updated is not None  # For type checker

        new_episodes_second_run = manager_updated.get_new_episodes()

        # Verification: should only find 2 new episodes (103, 104)
        # Episodes 101, 102 were already tracked so they shouldn't appear
        # as new
        self.assertEqual(len(new_episodes_second_run), 2)
        episode_ids = {ep.id for ep in new_episodes_second_run}
        self.assertEqual(episode_ids, {"103", "104"})
