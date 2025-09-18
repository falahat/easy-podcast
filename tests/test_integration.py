"""
Integration tests for the easy_podcast.
"""

# pylint: disable=duplicate-code

import os
import unittest
from typing import Any
from unittest.mock import MagicMock, Mock, patch

from easy_podcast.path_manager import set_base_data_dir
from easy_podcast.manager import PodcastManager
from easy_podcast.models import Episode, Podcast
from easy_podcast.utils import format_bytes

from tests.base import PodcastTestBase
from tests.utils import create_test_episode


class TestIntegration(PodcastTestBase):
    """Integration tests for the complete podcast workflow."""

    @patch("requests.get")
    def test_complete_workflow(self, mock_get: Mock) -> None:
        """Test the complete podcast download workflow."""
        # Mock RSS download
        rss_response = MagicMock()
        rss_response.content = b"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test Podcast</title>
                <item>
                    <title>Episode 1</title>
                    <supercast_episode_id>ep1</supercast_episode_id>
                    <enclosure url="http://test.com/ep1.mp3"
                              type="audio/mpeg"
                              length="1000"/>
                </item>
            </channel>
        </rss>"""
        rss_response.raise_for_status.return_value = None

        # Mock episode file download
        episode_response = MagicMock()
        episode_response.headers = {"content-length": "1000"}
        episode_response.iter_content.return_value = [b"audio_content"]
        episode_response.raise_for_status.return_value = None
        episode_response.__enter__ = MagicMock(return_value=episode_response)
        episode_response.__exit__ = MagicMock(return_value=None)

        def mock_get_side_effect(url: str, **_kwargs: Any) -> MagicMock:
            if url.endswith(".xml") or "rss" in url:
                return rss_response
            return episode_response

        mock_get.side_effect = mock_get_side_effect

        # Run the complete workflow
        set_base_data_dir(self.test_dir)

        # Use the static factory method to create manager from RSS
        manager = PodcastManager.from_rss_url("http://test.com/rss")
        self.assertIsNotNone(manager)
        assert manager is not None  # Help mypy understand this

        # Get the podcast info
        podcast = manager.get_podcast()
        self.assertEqual(podcast.title, "Test Podcast")

        # Get new episodes
        new_episodes = manager.get_new_episodes()
        self.assertEqual(len(new_episodes), 1)
        self.assertEqual(new_episodes[0].id, "ep1")

        # Download episodes
        file_path, was_downloaded = manager.download_episode(new_episodes[0])
        self.assertIsNotNone(file_path)
        assert file_path is not None  # Help mypy understand this
        self.assertTrue(was_downloaded)
        self.assertTrue(os.path.exists(file_path))

        # 4. Verify no new episodes after download
        new_episodes_after = manager.get_new_episodes()
        self.assertEqual(len(new_episodes_after), 0)

    def test_package_imports(self) -> None:
        """Test that all package imports work correctly."""
        # Test that classes can be instantiated
        episode = create_test_episode(
            id="test",
            title="Test",
            size=1000,
            audio_link="http://test.com/test.mp3",
        )
        self.assertEqual(episode.id, "test")

        podcast = Podcast(
            title="Test", rss_url="http://test.com", safe_title="Test"
        )
        self.assertEqual(podcast.title, "Test")

        # Test manager creation with required parameters
        manager = PodcastManager(self.test_dir, podcast)
        self.assertIsNotNone(manager)

        result = format_bytes(1024)
        self.assertEqual(result, "1.00 KiB")

    def test_backward_compatibility(self) -> None:
        """Test that direct module imports work."""
        # Test that the main package imports work correctly
        try:
            # Create a test podcast for manager creation
            test_podcast = Podcast(
                title="Test", rss_url="http://test.com", safe_title="Test"
            )
            manager = PodcastManager(self.test_dir, test_podcast)
            self.assertIsNotNone(manager)
            # Use imports to satisfy type checker
            self.assertIsNotNone(Episode)
            self.assertIsNotNone(format_bytes)
        except ImportError:
            self.fail("Package imports should work")


if __name__ == "__main__":
    unittest.main()
