"""
Tests for PodcastManager initialization and factory methods.
"""

import os
from typing import Any, Dict, List
from unittest.mock import Mock, patch

from easy_podcast.config import get_config
from easy_podcast.manager import PodcastManager
from easy_podcast.models import Podcast

from tests.base import PodcastTestBase
from tests.utils import create_test_episode


class TestPodcastManagerInitialization(PodcastTestBase):
    """Test suite for PodcastManager initialization and factory methods."""

    def test_manager_initialization(self) -> None:
        """Test PodcastManager initialization."""
        # Create a simple podcast object for testing
        test_podcast = Podcast(
            title="Test Podcast",
            rss_url="http://test.com/rss",
            safe_title="Test_Podcast",
            episodes=[],
        )

        # Create a temporary directory for testing
        test_podcast_dir = os.path.join(self.test_dir, "Test_Podcast")
        os.makedirs(test_podcast_dir, exist_ok=True)

        manager = PodcastManager(test_podcast_dir, test_podcast)

        # Config should be set to the test directory
        self.assertEqual(get_config().base_data_dir, self.test_dir)
        self.assertIsNotNone(manager.podcast)
        self.assertIsNotNone(manager.episode_tracker)
        self.assertIsNotNone(manager.downloads_dir)
        self.assertEqual(manager.podcast.title, "Test Podcast")

    def test_from_podcast_folder_success(self) -> None:
        """Test successful creation of PodcastManager from existing folder."""
        # Create test podcast directory and RSS file
        test_podcast_dir = os.path.join(self.test_dir, "Test_Podcast_Folder")
        os.makedirs(test_podcast_dir, exist_ok=True)

        # Create RSS file content
        episodes_data: List[Dict[str, Any]] = [
            {
                "supercast_episode_id": "456",
                "title": "Test Episode from Folder",
                "audio_link": "http://test.com/folder_episode.mp3",
                "size": 2000,
            }
        ]
        rss_content = self.create_mock_rss_content(
            episodes_data, title="Test Podcast from Folder"
        )

        # Write RSS content to file
        rss_file_path = os.path.join(test_podcast_dir, "rss.xml")
        with open(rss_file_path, "wb") as f:
            f.write(rss_content)

        # Test the from_podcast_folder method
        manager = PodcastManager.from_podcast_folder(test_podcast_dir)

        # Verify the manager was created successfully
        self.assertIsNotNone(manager, "Manager should be created successfully")
        if manager:
            self.assertEqual(
                manager.podcast.title,
                "Test Podcast from Folder",
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
                "Test Episode from Folder",
                "Episode title should match",
            )
            # Verify downloads directory exists
            self.assertTrue(
                os.path.exists(manager.downloads_dir),
                "Downloads directory should exist",
            )

    def test_from_podcast_folder_missing_rss_file(self) -> None:
        """Test from_podcast_folder when RSS file is missing."""
        # Create test podcast directory without RSS file
        test_podcast_dir = os.path.join(self.test_dir, "Missing_RSS_Folder")
        os.makedirs(test_podcast_dir, exist_ok=True)

        # Test the from_podcast_folder method
        manager = PodcastManager.from_podcast_folder(test_podcast_dir)

        # Verify the manager creation failed
        self.assertIsNone(
            manager, "Manager should be None when RSS file is missing"
        )

    def test_from_podcast_folder_invalid_rss_file(self) -> None:
        """Test from_podcast_folder with malformed XML content."""
        # Create test podcast directory
        test_podcast_dir = os.path.join(self.test_dir, "Invalid_RSS_Folder")
        os.makedirs(test_podcast_dir, exist_ok=True)

        # Create malformed XML content that triggers feedparser's bozo bit
        # Missing closing tag will cause SAX parser to fail
        malformed_xml = self.get_malformed_xml()

        rss_file_path = os.path.join(test_podcast_dir, "rss.xml")
        with open(rss_file_path, "wb") as f:
            f.write(malformed_xml)

        # Test the from_podcast_folder method
        with self.assertRaises(ValueError) as context:
            PodcastManager.from_podcast_folder(test_podcast_dir)

        # Verify the error message mentions malformed XML
        self.assertIn(
            "Malformed XML detected",
            str(context.exception),
            "Error message should indicate malformed XML",
        )

    @patch("easy_podcast.parser.PodcastParser.from_file")
    def test_from_podcast_folder_file_read_error(
        self, mock_parse_from_file: Mock
    ) -> None:
        """Test from_podcast_folder when RSS file parsing returns None."""
        # Create test podcast directory with RSS file
        test_podcast_dir = os.path.join(
            self.test_dir, "File_Read_Error_Folder"
        )
        os.makedirs(test_podcast_dir, exist_ok=True)

        # Create RSS file
        rss_file_path = os.path.join(test_podcast_dir, "rss.xml")
        with open(rss_file_path, "wb") as f:
            f.write(b"<rss><channel><title>Test</title></channel></rss>")

        # Mock parse_from_file to return None (simulating parse failure)
        # Note: parse_from_file catches all exceptions and returns None
        mock_parse_from_file.return_value = None

        # Test the from_podcast_folder method
        manager = PodcastManager.from_podcast_folder(test_podcast_dir)

        # Verify the manager creation failed due to parse returning None
        self.assertIsNone(
            manager, "Manager should be None when RSS parsing returns None"
        )

        # Verify parse_from_file was called with correct arguments
        mock_parse_from_file.assert_called_once_with("", rss_file_path)

    @patch("builtins.open")
    def test_from_podcast_folder_file_system_error(
        self, mock_open: Mock
    ) -> None:
        """Test from_podcast_folder when file system error occurs."""
        # Create test podcast directory with RSS file
        test_podcast_dir = os.path.join(
            self.test_dir, "File_System_Error_Folder"
        )
        os.makedirs(test_podcast_dir, exist_ok=True)

        # Create RSS file first (so os.path.exists check passes)
        rss_file_path = os.path.join(test_podcast_dir, "rss.xml")
        with open(rss_file_path, "wb") as f:
            f.write(b"<rss><channel><title>Test</title></channel></rss>")

        # Mock open() to raise PermissionError when trying to read RSS file
        mock_open.side_effect = PermissionError("Permission denied")

        # Test the from_podcast_folder method
        manager = PodcastManager.from_podcast_folder(test_podcast_dir)

        # Verify the manager creation failed due to file system error
        # parse_from_file catches the exception and returns None
        self.assertIsNone(
            manager, "Manager should be None when file system error occurs"
        )

    @patch("easy_podcast.parser.PodcastParser.from_file")
    def test_from_podcast_folder_parse_failure(
        self, mock_parse_from_file: Mock
    ) -> None:
        """Test from_podcast_folder when RSS parsing fails."""
        # Create test podcast directory with valid RSS file
        test_podcast_dir = os.path.join(self.test_dir, "Parse_Failure_Folder")
        os.makedirs(test_podcast_dir, exist_ok=True)

        # Create valid RSS file content
        episodes_data: List[Dict[str, Any]] = [
            {
                "supercast_episode_id": "789",
                "title": "Test Episode Parse Failure",
                "audio_link": "http://test.com/parse_failure.mp3",
                "size": 3000,
            }
        ]
        rss_content = self.create_mock_rss_content(episodes_data)
        rss_file_path = os.path.join(test_podcast_dir, "rss.xml")
        with open(rss_file_path, "wb") as f:
            f.write(rss_content)

        # Mock parse_from_file to return None (simulating parse failure)
        mock_parse_from_file.return_value = None

        # Test the from_podcast_folder method
        manager = PodcastManager.from_podcast_folder(test_podcast_dir)

        # Verify the manager creation failed due to parse failure
        self.assertIsNone(
            manager, "Manager should be None when RSS parsing fails"
        )

        # Verify parse_from_file was called with correct arguments
        mock_parse_from_file.assert_called_once_with("", rss_file_path)

    def test_from_podcast_folder_empty_episodes(self) -> None:
        """Test from_podcast_folder with RSS file containing no episodes."""
        # Create test podcast directory
        test_podcast_dir = os.path.join(self.test_dir, "Empty_Episodes_Folder")
        os.makedirs(test_podcast_dir, exist_ok=True)

        # Create RSS file with no episodes
        rss_content = self.create_mock_rss_content([], title="Empty Podcast")
        rss_file_path = os.path.join(test_podcast_dir, "rss.xml")
        with open(rss_file_path, "wb") as f:
            f.write(rss_content)

        # Test the from_podcast_folder method
        manager = PodcastManager.from_podcast_folder(test_podcast_dir)

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

    def test_from_podcast_folder_manager_creation_exception(self) -> None:
        """Test from_podcast_folder when manager creation raises exception."""
        # Create test podcast directory with valid RSS file
        test_podcast_dir = os.path.join(
            self.test_dir, "Manager_Exception_Folder"
        )
        os.makedirs(test_podcast_dir, exist_ok=True)

        # Create valid RSS file content
        episodes_data: List[Dict[str, Any]] = [
            {
                "supercast_episode_id": "999",
                "title": "Test Episode Manager Exception",
                "audio_link": "http://test.com/manager_exception.mp3",
                "size": 4000,
            }
        ]
        rss_content = self.create_mock_rss_content(episodes_data)
        rss_file_path = os.path.join(test_podcast_dir, "rss.xml")
        with open(rss_file_path, "wb") as f:
            f.write(rss_content)

        # Mock PodcastManager.__init__ to raise an exception
        init_patch = "easy_podcast.manager.PodcastManager.__init__"
        with patch(init_patch) as mock_init:
            mock_init.side_effect = Exception(
                "Simulated manager creation failure"
            )

            # Test the from_podcast_folder method
            manager = PodcastManager.from_podcast_folder(test_podcast_dir)

            # Verify the manager creation failed due to exception
            self.assertIsNone(
                manager,
                "Manager should be None when manager creation raises "
                "exception",
            )

    @patch("easy_podcast.parser.PodcastParser.from_rss_url")
    def test_from_rss_url_file_save_error(
        self, mock_parser_from_rss_url: Mock
    ) -> None:
        """Test from_rss_url when PodcastParser fails."""
        # Mock parser to return None (failure)
        mock_parser_from_rss_url.return_value = None

        # Test from_rss_url
        manager = PodcastManager.from_rss_url("http://test.com/rss.xml")

        # Verify manager creation failed
        self.assertIsNone(manager)
        mock_parser_from_rss_url.assert_called_once_with(
            "http://test.com/rss.xml"
        )

    @patch("easy_podcast.parser.PodcastParser.from_rss_url")
    def test_from_rss_url_manager_creation_error(
        self, mock_parser_from_rss_url: Mock
    ) -> None:
        """Test from_rss_url when PodcastManager creation fails."""
        # Create a mock podcast
        mock_podcast = Mock()
        mock_podcast.title = "Test Podcast"
        mock_podcast.safe_title = "Test_Podcast"
        mock_parser_from_rss_url.return_value = mock_podcast

        # Mock PodcastManager.__init__ to raise an exception
        with patch(
            "easy_podcast.manager.PodcastManager.__init__"
        ) as mock_init:
            mock_init.side_effect = Exception("Manager creation failed")

            manager = PodcastManager.from_rss_url("http://test.com/rss")

            # Manager creation should fail
            self.assertIsNone(manager)

    @patch("easy_podcast.parser.PodcastParser.from_rss_url")
    def test_from_rss_url_parse_failure(
        self, mock_parser_from_rss_url: Mock
    ) -> None:
        """Test from_rss_url when RSS parsing fails."""
        # Mock parser to return None (parsing failure)
        mock_parser_from_rss_url.return_value = None

        manager = PodcastManager.from_rss_url("http://test.com/rss")

        # Manager creation should fail due to parse error
        self.assertIsNone(manager)
        mock_parser_from_rss_url.assert_called_once_with("http://test.com/rss")

    @patch("easy_podcast.parser.PodcastParser.from_rss_url")
    def test_podcast_manager_state_reset(
        self, mock_parser_from_rss_url: Mock
    ) -> None:
        """Test that creating a new manager for a new podcast results in a
        clean state."""
        # First podcast
        mock_podcast1 = Podcast(
            title="Podcast 1",
            rss_url="http://test1.com/rss",
            safe_title="Podcast_1",
            episodes=[
                create_test_episode(
                    id="1",
                    title="Ep 1",
                    size=100,
                    audio_link="link1",
                )
            ],
        )
        mock_parser_from_rss_url.return_value = mock_podcast1

        manager1 = PodcastManager.from_rss_url("http://test1.com/rss")
        self.assertIsNotNone(manager1)
        if not manager1:
            return

        self.assertEqual(manager1.get_podcast().title, "Podcast 1")
        self.assertEqual(len(manager1.get_podcast().episodes), 1)

        # Second podcast
        mock_podcast2 = Podcast(
            title="Podcast 2",
            rss_url="http://test2.com/rss",
            safe_title="Podcast_2",
            episodes=[
                create_test_episode(
                    id="2",
                    title="Ep 2",
                    size=200,
                    audio_link="link2",
                )
            ],
        )
        mock_parser_from_rss_url.return_value = mock_podcast2

        manager2 = PodcastManager.from_rss_url("http://test2.com/rss")
        self.assertIsNotNone(manager2)
        if not manager2:
            return

        self.assertEqual(manager2.get_podcast().title, "Podcast 2")
        self.assertEqual(len(manager2.get_podcast().episodes), 1)

        # Verify managers are independent
        self.assertNotEqual(
            manager1.get_podcast().title, manager2.get_podcast().title
        )
