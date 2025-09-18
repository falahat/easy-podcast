"""
Tests for data models (Episode and Podcast classes).
"""

import json
import unittest

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
        self.assertEqual(
            episode.audio_filename, "123.mp3"
        )  # Test the computed property
        self.assertEqual(
            episode.transcript_filename, "123_transcript.json"
        )  # Test the computed property

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

        json_str = episode.to_json()
        parsed = json.loads(json_str)

        self.assertEqual(parsed["id"], "123")
        self.assertEqual(parsed["title"], "Test Episode")
        self.assertEqual(parsed["size"], 1000)
        self.assertEqual(parsed["author"], "Test Author")


class TestPodcast(unittest.TestCase):
    """Test suite for the Podcast class."""

    def test_podcast_creation(self) -> None:
        """Test creating a Podcast instance."""
        podcast = Podcast(
            title="Test Podcast",
            rss_url="http://test.com/rss",
            safe_title="Test_Podcast",
        )

        self.assertEqual(podcast.title, "Test Podcast")
        self.assertEqual(podcast.rss_url, "http://test.com/rss")
        self.assertEqual(podcast.safe_title, "Test_Podcast")
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
            safe_title="Test_Podcast",
            episodes=[episode],
        )

        self.assertEqual(len(podcast.episodes), 1)
        self.assertEqual(podcast.episodes[0].id, "123")

    def test_episode_from_dict_with_old_format(self) -> None:
        """Test Episode.from_dict handles conversion from old format."""
        old_format_data = {
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
        new_format_data = {
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
            safe_title="Test_Podcast",
            guid="test-podcast-guid",
        )

        # Test to_json
        json_str = podcast.to_json()
        self.assertIsInstance(json_str, str)
        self.assertIn("Test Podcast", json_str)
        self.assertIn("test-podcast-guid", json_str)

        # Test from_dict
        podcast_dict = json.loads(json_str)
        restored_podcast = Podcast.from_dict(podcast_dict)

        self.assertEqual(restored_podcast.title, "Test Podcast")
        self.assertEqual(restored_podcast.rss_url, "http://test.com/rss")
        self.assertEqual(restored_podcast.safe_title, "Test_Podcast")
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
            safe_title="Test_Podcast",
            episodes=[episode],
            guid="test-podcast-guid",
        )

        # Test serialization round-trip
        podcast_dict = json.loads(podcast.to_json())
        restored_podcast = Podcast.from_dict(podcast_dict)

        self.assertEqual(len(restored_podcast.episodes), 1)
        self.assertEqual(restored_podcast.episodes[0].id, "123")
        self.assertEqual(restored_podcast.episodes[0].size, 1000)


if __name__ == "__main__":
    unittest.main()
