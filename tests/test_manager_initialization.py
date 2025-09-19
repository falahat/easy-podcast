"""
Tests for PodcastManager initialization and factory methods.
"""

import os
from typing import Any, Dict, List
from unittest.mock import Mock, patch

from easy_podcast.factory import (
    create_manager_from_rss,
    create_manager_from_storage,
)
from easy_podcast.models import Podcast
from easy_podcast.manager import PodcastManager
from easy_podcast.repository import PodcastRepository
from easy_podcast.storage import Storage
from easy_podcast.episode_downloader import EpisodeDownloader

from tests.base import PodcastTestBase


class TestPodcastManagerInitialization(PodcastTestBase):
    """Test suite for PodcastManager initialization and factory methods."""

    def test_manager_initialization(self) -> None:
        """Test PodcastManager initialization with dependency injection."""
        # Create a simple podcast object for testing
        test_podcast = Podcast(
            title="Test Podcast",
            rss_url="http://test.com/rss",
            safe_title="Test_Podcast",
            episodes=[],
        )

        # Create dependencies
        storage = Storage(self.test_dir)
        repository = PodcastRepository(storage)
        downloader = EpisodeDownloader(storage)

        # Create manager with dependency injection
        manager = PodcastManager(test_podcast, repository, downloader)

        # Verify manager properties
        self.assertIsNotNone(manager.podcast)
        self.assertIsNotNone(manager.repository)
        self.assertIsNotNone(manager.downloader)
        self.assertEqual(manager.podcast.title, "Test Podcast")

    def test_from_existing_storage_success(self) -> None:
        """Test successful creation from existing storage."""
        # First create a manager using from_rss_url,
        # then load it with from_podcast_folder
        episodes_data: List[Dict[str, Any]] = [
            {
                "supercast_episode_id": "456",
                "title": "Test Episode from Storage",
                "audio_link": "http://test.com/storage_episode.mp3",
                "size": 2000,
            }
        ]
        rss_content = self.create_mock_rss_content(
            episodes_data, title="Test Podcast from Storage"
        )

        # Mock the RSS response
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = rss_content
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            # Create the initial manager to set up storage
            initial_manager = create_manager_from_rss(
                "http://test.com/rss", self.test_dir
            )
            self.assertIsNotNone(initial_manager)
            assert initial_manager is not None  # Type hint for mypy
            podcast_title = initial_manager.podcast.title

        # Now test loading from existing storage
        manager = create_manager_from_storage(podcast_title, self.test_dir)

        # Verify the manager was created successfully
        self.assertIsNotNone(manager, "Manager should be created successfully")
        if manager:
            self.assertEqual(
                manager.podcast.title,
                "Test Podcast from Storage",
                "Podcast title should match",
            )
            self.assertEqual(
                len(manager.podcast.episodes), 1, "Should have one episode"
            )
            self.assertEqual(
                manager.podcast.episodes[0].id,
                "456",
                "Episode ID should match",
            )
            self.assertEqual(
                manager.podcast.episodes[0].title,
                "Test Episode from Storage",
                "Episode title should match",
            )
            # Verify podcast directory structure exists
            podcast_dir = manager.repository.get_podcast_dir(
                manager.podcast.title
            )
            self.assertTrue(
                os.path.exists(podcast_dir),
                "Podcast directory should exist",
            )

    def test_from_podcast_folder_nonexistent_title(self) -> None:
        """Test from_podcast_folder with non-existent title."""
        # Test with a title that doesn't exist
        fake_title = "Nonexistent Podcast"
        manager = create_manager_from_storage(fake_title, self.test_dir)

        # Verify the manager creation failed
        self.assertIsNone(
            manager, "Manager should be None for non-existent title"
        )

    def test_from_podcast_folder_invalid_title(self) -> None:
        """Test from_podcast_folder with invalid title format."""
        # Test with an invalid title format (empty)
        invalid_title = ""
        manager = create_manager_from_storage(invalid_title, self.test_dir)

        # Verify the manager creation failed
        self.assertIsNone(
            manager, "Manager should be None for invalid title format"
        )

    def test_from_podcast_folder_empty_episodes(self) -> None:
        """Test from_podcast_folder with podcast containing no episodes."""
        # Create a manager with no episodes first
        rss_content = self.create_mock_rss_content([], title="Empty Podcast")

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.content = rss_content
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            initial_manager = create_manager_from_rss(
                "http://test.com/empty_rss", self.test_dir
            )
            self.assertIsNotNone(initial_manager)
            assert initial_manager is not None
            podcast_title = initial_manager.podcast.title

        # Now test loading from existing storage
        manager = create_manager_from_storage(podcast_title, self.test_dir)

        # Verify the manager was created successfully even with no episodes
        self.assertIsNotNone(
            manager, "Manager should be created even with empty episodes list"
        )
        if manager:
            self.assertEqual(
                manager.podcast.title,
                "Empty Podcast",
                "Podcast title should match",
            )
            self.assertEqual(
                len(manager.podcast.episodes), 0, "Should have no episodes"
            )

    @patch("requests.get")
    def test_from_rss_url_success(self, mock_get: Mock) -> None:
        """Test successful creation from RSS URL."""
        episodes_data: List[Dict[str, Any]] = [
            {
                "supercast_episode_id": "123",
                "title": "Test Episode RSS",
                "audio_link": "http://test.com/rss_episode.mp3",
                "size": 1500,
            }
        ]
        rss_content = self.create_mock_rss_content(
            episodes_data, title="Test Podcast from RSS"
        )

        mock_response = Mock()
        mock_response.content = rss_content
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        manager = create_manager_from_rss("http://test.com/rss", self.test_dir)

        self.assertIsNotNone(manager)
        if manager:
            self.assertEqual(manager.podcast.title, "Test Podcast from RSS")
            self.assertEqual(len(manager.podcast.episodes), 1)
            self.assertEqual(manager.podcast.episodes[0].id, "123")

    @patch("requests.get")
    def test_from_rss_url_download_failure(self, mock_get: Mock) -> None:
        """Test from_rss_url when RSS download fails."""
        import requests

        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Network error"
        )

        manager = create_manager_from_rss("http://test.com/rss", self.test_dir)

        self.assertIsNone(manager)
