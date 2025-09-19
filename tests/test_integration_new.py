"""
Integration test for the new architecture.
"""

import tempfile
import unittest
from unittest.mock import Mock, patch

from easy_podcast.factory import create_manager_from_rss


class TestNewArchitectureIntegration(unittest.TestCase):
    """Integration test for the refactored architecture."""

    def setUp(self) -> None:
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp(prefix="podcast_integration_test_")

    def test_create_manager_from_rss_integration(self) -> None:
        """Test the complete flow using new factory function."""
        # Mock RSS content
        rss_content = b"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test Integration Podcast</title>
                <item>
                    <title>Test Episode</title>
                    <supercast_episode_id>test123</supercast_episode_id>
                    <enclosure url="http://test.com/test.mp3" 
                               type="audio/mpeg" length="1000"/>
                </item>
            </channel>
        </rss>"""

        # Mock the HTTP request
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = rss_content
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # Create manager using new factory function
            manager = create_manager_from_rss(
                "http://test.com/rss", self.test_dir
            )

            # Verify manager was created successfully
            self.assertIsNotNone(manager)
            if manager:  # Type guard for None check
                self.assertEqual(
                    manager.podcast.title, "Test Integration Podcast"
                )
                self.assertEqual(len(manager.podcast.episodes), 1)

                # Verify episode data
                episode = manager.podcast.episodes[0]
                self.assertEqual(episode.id, "test123")
                self.assertEqual(episode.title, "Test Episode")

                # Verify dependencies are properly injected
                self.assertIsNotNone(manager.repository)
                self.assertIsNotNone(manager.downloader)

                # Test that the repository works
                audio_path = manager.repository.get_episode_audio_path(
                    manager.podcast.title, episode
                )
                self.assertTrue(audio_path.endswith("test123.mp3"))


if __name__ == "__main__":
    unittest.main()
