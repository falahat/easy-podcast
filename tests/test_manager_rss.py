"""
Tests for PodcastManager RSS handling functionality.
"""

import os
from unittest.mock import Mock, patch

from easy_podcast.manager import PodcastManager
from easy_podcast.models import Podcast

from tests.base import PodcastTestBase
from tests.utils import create_test_episode


class TestPodcastManagerRSS(PodcastTestBase):
    """Test suite for PodcastManager RSS handling functionality."""

    @patch("easy_podcast.parser.PodcastParser.from_rss_url")
    def test_ingest_rss_data_success(
        self, mock_parser_from_rss_url: Mock
    ) -> None:
        """Test successful RSS ingestion using static method."""
        mock_episode = create_test_episode(
            id="123",
            title="Test Episode",
            size=1000,
            audio_link="http://test.com/test.mp3",
        )
        mock_podcast = Podcast(
            title="Test Podcast",
            rss_url="http://test.com/rss",
            safe_title="Test_Podcast",
            episodes=[mock_episode],
        )
        mock_parser_from_rss_url.return_value = mock_podcast

        manager = PodcastManager.from_rss_url("http://test.com/rss")

        self.assertIsNotNone(manager)
        if manager:
            podcast = manager.get_podcast()
            self.assertEqual(podcast.title, "Test Podcast")
            self.assertEqual(len(podcast.episodes), 1)

            self.assertIsNotNone(manager.downloads_dir)
            self.assertIsNotNone(manager.episode_tracker)
            self.assertTrue(os.path.exists(manager.downloads_dir))

    @patch("easy_podcast.parser.PodcastParser.from_rss_url")
    def test_ingest_rss_data_failure(
        self, mock_parser_from_rss_url: Mock
    ) -> None:
        """Test RSS ingestion failure using static method."""
        mock_parser_from_rss_url.return_value = None

        manager = PodcastManager.from_rss_url("http://test.com/rss")

        self.assertIsNone(manager)

    @patch("easy_podcast.parser.PodcastParser.from_rss_url")
    def test_empty_rss_feed(self, mock_parser_from_rss_url: Mock) -> None:
        """Test handling of empty RSS feed using static method."""
        mock_podcast = Podcast(
            title="Empty Podcast",
            rss_url="http://test.com/rss",
            safe_title="Empty_Podcast",
            episodes=[],
        )
        mock_parser_from_rss_url.return_value = mock_podcast

        manager = PodcastManager.from_rss_url("http://test.com/rss")

        self.assertIsNotNone(manager)
        if manager:
            podcast = manager.get_podcast()
            self.assertEqual(len(podcast.episodes), 0)
            self.assertEqual(len(manager.get_new_episodes()), 0)

    @patch("easy_podcast.parser.PodcastParser.from_rss_url")
    def test_rss_feed_missing_title(
        self, mock_parser_from_rss_url: Mock
    ) -> None:
        """Test handling of RSS feed without title using static method."""
        # Create a podcast with default title
        mock_podcast = Podcast(
            title="Unknown Podcast",
            rss_url="http://test.com/rss",
            safe_title="Unknown_Podcast",
            episodes=[],
        )
        mock_parser_from_rss_url.return_value = mock_podcast

        manager = PodcastManager.from_rss_url("http://test.com/rss")

        self.assertIsNotNone(manager)
        if manager:
            podcast = manager.get_podcast()
            self.assertEqual(podcast.title, "Unknown Podcast")

        mock_parser_from_rss_url.assert_called_once_with("http://test.com/rss")

    @patch("easy_podcast.parser.PodcastParser.from_rss_url")
    def test_sanitized_podcast_title(
        self, mock_parser_from_rss_url: Mock
    ) -> None:
        """Test that podcast titles with special characters are sanitized."""
        # Create a podcast with the special characters title
        mock_podcast = Podcast(
            title="Test/Podcast\\With:Special*Chars",
            rss_url="http://test.com/rss",
            safe_title="Test_Podcast_With_Special_Chars",
            episodes=[],
        )
        mock_parser_from_rss_url.return_value = mock_podcast

        manager = PodcastManager.from_rss_url("http://test.com/rss")

        self.assertIsNotNone(manager)
        # Check that the directory path was created successfully
        if manager:
            self.assertIsNotNone(manager.downloads_dir)
            self.assertTrue(os.path.exists(manager.downloads_dir))

    @patch("easy_podcast.parser.PodcastParser.from_rss_url")
    def test_rss_content_saved_to_file(
        self, mock_parser_from_rss_url: Mock
    ) -> None:
        """Test that manager is created correctly from RSS URL."""
        mock_episode = create_test_episode(
            id="123",
            published="2023-01-01",
            title="Test Episode",
            author="Test",
            duration_seconds=1800,
            size=1000,
            audio_link="http://test.com/test.mp3",
        )
        mock_podcast = Podcast(
            title="Test Podcast",
            rss_url="http://test.com/rss",
            safe_title="Test_Podcast",
            episodes=[mock_episode],
        )
        mock_parser_from_rss_url.return_value = mock_podcast

        manager = PodcastManager.from_rss_url("http://test.com/rss")

        # Verify manager was created
        self.assertIsNotNone(manager)
        if manager:
            podcast = manager.get_podcast()
            self.assertEqual(podcast.title, "Test Podcast")
            self.assertEqual(len(podcast.episodes), 1)
