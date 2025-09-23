"""
Tests for data models (Episode and Podcast classes).
"""

import unittest
from typing import Any, Dict

from easy_podcast.models import Episode, Podcast

from tests.utils import create_test_episode


class TestEpisode(unittest.TestCase):
    """Test suite for the Episode class."""

    def test_episode_creation(self) -> None:
        """Test creating an Episode instance."""
        episode = create_test_episode(
            id="123",
            published="2023-01-01",
            title="Test Episode",
            author="Test Author",
            duration_seconds=1800,  # 30 minutes = 1800 seconds
            size=1000,
            audio_link="http://test.com/123.mp3",
            image="http://test.com/image.jpg",
        )

        self.assertEqual(episode.id, "123")
        self.assertEqual(episode.title, "Test Episode")
        self.assertEqual(episode.size, 1000)
        self.assertEqual(episode.duration_seconds, 1800)

    def test_episode_to_json_serialization(self) -> None:
        """Test that Episode objects serialize correctly to JSON."""
        episode = create_test_episode(
            id="123",
            published="2023-01-01",
            title="Test Episode",
            author="Test Author",
            duration_seconds=1800,  # 30 minutes
            size=1000,
            audio_link="http://test.com/123.mp3",
            image="http://test.com/image.jpg",
        )

        data_dict = episode.to_json()

        self.assertEqual(data_dict["id"], "123")
        self.assertEqual(data_dict["title"], "Test Episode")
        self.assertEqual(data_dict["size"], 1000)
        self.assertEqual(data_dict["author"], "Test Author")


class TestPodcast(unittest.TestCase):
    """Test suite for the Podcast class."""

    def test_podcast_creation(self) -> None:
        """Test creating a Podcast instance."""
        podcast = Podcast(
            title="Test Podcast",
            rss_url="http://test.com/rss",
        )

        self.assertEqual(podcast.title, "Test Podcast")
        self.assertEqual(podcast.rss_url, "http://test.com/rss")
        # safe_title field no longer exists - using GUID-based storage
        self.assertEqual(len(podcast.episodes), 0)

    def test_podcast_with_episodes(self) -> None:
        """Test Podcast with episodes."""
        episode = create_test_episode(
            id="123",
            size=1000,
            audio_link="http://test.com/123.mp3",
        )

        podcast = Podcast(
            title="Test Podcast",
            rss_url="http://test.com/rss",
            episodes=[episode],
        )

        self.assertEqual(len(podcast.episodes), 1)
        self.assertEqual(podcast.episodes[0].id, "123")

    def test_episode_from_dict_with_old_format(self) -> None:
        """Test Episode.from_dict handles conversion from old format."""
        old_format_data: Dict[str, Any] = {
            "id": "123",
            "published": "2023-01-01",
            "title": "Test Episode",
            "author": "Test Author",
            "itunes_duration": "30:00",  # Old format
            "size": 1000,
            "audio_link": "http://test.com/123.mp3",
            "image": "http://test.com/image.jpg",
        }

        episode = Episode.from_dict(old_format_data)

        self.assertEqual(episode.id, "123")
        # 30:00 = 1800 seconds
        self.assertEqual(episode.duration_seconds, 1800)

    def test_episode_from_dict_with_new_format(self) -> None:
        """Test Episode.from_dict works with new duration_seconds format."""
        new_format_data: Dict[str, Any] = {
            "id": "456",
            "published": "2023-01-01",
            "title": "Test Episode",
            "author": "Test Author",
            "duration_seconds": 3600,  # New format
            "size": 1000,
            "audio_link": "http://test.com/456.mp3",
            "image": "http://test.com/image.jpg",
        }

        episode = Episode.from_dict(new_format_data)

        self.assertEqual(episode.id, "456")
        self.assertEqual(episode.duration_seconds, 3600)

    def test_podcast_serialization(self) -> None:
        """Test Podcast to_json and from_dict methods."""
        podcast = Podcast(
            title="Test Podcast",
            rss_url="http://test.com/rss",
            guid="test-podcast-guid",
        )

        # Test to_json
        data_dict = podcast.to_json()
        self.assertIsInstance(data_dict, dict)
        self.assertEqual(data_dict["title"], "Test Podcast")
        self.assertEqual(data_dict["guid"], "test-podcast-guid")

        # Test from_dict
        restored_podcast = Podcast.from_dict(data_dict)

        self.assertEqual(restored_podcast.title, "Test Podcast")
        self.assertEqual(restored_podcast.rss_url, "http://test.com/rss")
        # safe_title field no longer exists - using GUID-based storage
        self.assertEqual(restored_podcast.guid, "test-podcast-guid")
        self.assertEqual(len(restored_podcast.episodes), 0)

    def test_podcast_serialization_with_episodes(self) -> None:
        """Test Podcast serialization with episodes."""
        episode = create_test_episode(
            id="123",
            size=1000,
            audio_link="http://test.com/123.mp3",
        )

        podcast = Podcast(
            title="Test Podcast",
            rss_url="http://test.com/rss",
            episodes=[episode],
            guid="test-podcast-guid",
        )

        # Test serialization round-trip
        podcast_dict = podcast.to_json()
        restored_podcast = Podcast.from_dict(podcast_dict)

        self.assertEqual(len(restored_podcast.episodes), 1)
        self.assertEqual(restored_podcast.episodes[0].id, "123")
        self.assertEqual(restored_podcast.episodes[0].size, 1000)


if __name__ == "__main__":
    unittest.main()
