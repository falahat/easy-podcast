"""
Tests for the PodcastParser class.
"""

import unittest
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import feedparser

from easy_podcast.parser import PodcastParser
from easy_podcast.models import Episode, Podcast

from tests.base import PodcastTestBase


# pylint: disable=too-many-public-methods
class TestPodcastParser(PodcastTestBase):
    """Test suite for the PodcastParser class."""

    def setUp(self) -> None:
        """Set up test data."""
        super().setUp()  # Call parent setUp which creates self.test_dir
        self.parser = PodcastParser()

    def _create_mock_feed_data(
        self,
        title: str = "Test Podcast",
        entries: List[Dict[str, Any]] | None = None,
    ) -> Mock:
        """Create mock feedparser data for testing."""
        feed_data = Mock(spec=feedparser.FeedParserDict)
        feed_data.feed = {"title": title}
        feed_data.entries = entries or []
        feed_data.bozo = 0
        return feed_data

    def _create_mock_entry(
        self,
        episode_id: str = "123",
        title: str = "Test Episode",
        has_audio: bool = True,
        audio_type: str = "audio/mpeg",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create mock feed entry for testing."""
        entry = {
            "supercast_episode_id": episode_id,
            "title": title,
            "published": "2023-01-01",
            "author": "Test Author",
            "itunes_duration": "30:00",
            "image": {"href": "http://example.com/image.jpg"},
            **kwargs,
        }

        if has_audio:
            entry["enclosures"] = [
                {
                    "type": audio_type,
                    "href": "http://example.com/episode.mp3",
                    "length": "1000",
                }
            ]
        else:
            entry["enclosures"] = []

        return entry

    # Test from_rss_url method
    @patch("easy_podcast.parser.download_rss_from_url")
    def test_from_rss_url_success(self, mock_download: Mock) -> None:
        """Test successful RSS download and parsing."""
        mock_download.return_value = b"<rss>test content</rss>"

        with patch.object(self.parser, "from_content") as mock_from_content:
            mock_podcast = Mock(spec=Podcast)
            mock_from_content.return_value = mock_podcast

            result = self.parser.from_rss_url("http://example.com/rss")

            self.assertEqual(result, mock_podcast)
            mock_download.assert_called_once_with("http://example.com/rss")
            mock_from_content.assert_called_once_with(
                "http://example.com/rss", b"<rss>test content</rss>"
            )

    @patch("easy_podcast.parser.download_rss_from_url")
    def test_from_rss_url_download_failure(self, mock_download: Mock) -> None:
        """Test handling of RSS download failure."""
        mock_download.return_value = None

        result = self.parser.from_rss_url("http://example.com/rss")

        self.assertIsNone(result)
        mock_download.assert_called_once_with("http://example.com/rss")

    # Test from_file method
    @patch("easy_podcast.parser.load_rss_from_file")
    def test_from_file_success(self, mock_load: Mock) -> None:
        """Test successful RSS file loading and parsing."""
        mock_load.return_value = b"<rss>test content</rss>"

        with patch.object(self.parser, "from_content") as mock_from_content:
            mock_podcast = Mock(spec=Podcast)
            mock_from_content.return_value = mock_podcast

            result = self.parser.from_file(
                "http://example.com/rss", "/path/to/rss.xml"
            )

            self.assertEqual(result, mock_podcast)
            mock_load.assert_called_once_with("/path/to/rss.xml")
            mock_from_content.assert_called_once_with(
                "http://example.com/rss", b"<rss>test content</rss>"
            )

    @patch("easy_podcast.parser.load_rss_from_file")
    def test_from_file_load_failure(self, mock_load: Mock) -> None:
        """Test handling of RSS file loading failure."""
        mock_load.return_value = None

        result = self.parser.from_file(
            "http://example.com/rss", "/path/to/rss.xml"
        )

        self.assertIsNone(result)
        mock_load.assert_called_once_with("/path/to/rss.xml")

    # Test from_content method
    @patch("feedparser.parse")
    def test_from_content_success(self, mock_parse: Mock) -> None:
        """Test successful RSS content parsing."""
        mock_feed_data = self._create_mock_feed_data("Test Podcast")
        mock_parse.return_value = mock_feed_data

        with patch.object(
            self.parser, "create_podcast_from_feed"
        ) as mock_create:
            mock_podcast = Mock(spec=Podcast)
            mock_podcast.title = "Test Podcast"
            mock_podcast.episodes = []
            mock_create.return_value = mock_podcast

            result = self.parser.from_content(
                "http://example.com/rss", b"<rss>content</rss>"
            )

            self.assertEqual(result, mock_podcast)
            mock_parse.assert_called_once_with(b"<rss>content</rss>")
            mock_create.assert_called_once_with(
                "http://example.com/rss", mock_feed_data
            )

    @patch("feedparser.parse")
    def test_from_content_bozo_with_exception(self, mock_parse: Mock) -> None:
        """Test handling of malformed XML with bozo exception."""
        mock_feed_data = self._create_mock_feed_data()
        mock_feed_data.bozo = 1
        mock_feed_data.bozo_exception = Exception("XML parsing error")
        mock_parse.return_value = mock_feed_data

        with self.assertRaises(ValueError) as cm:
            self.parser.from_content("http://example.com/rss", b"<bad>xml")

        self.assertIn("Malformed XML detected", str(cm.exception))
        self.assertIn("XML parsing error", str(cm.exception))

    @patch("feedparser.parse")
    def test_from_content_bozo_without_exception(
        self, mock_parse: Mock
    ) -> None:
        """Test handling of malformed XML without specific exception."""
        mock_feed_data = self._create_mock_feed_data()
        mock_feed_data.bozo = 1
        mock_feed_data.bozo_exception = None
        mock_parse.return_value = mock_feed_data

        with self.assertRaises(ValueError) as cm:
            self.parser.from_content("http://example.com/rss", b"<bad>xml")

        self.assertEqual(str(cm.exception), "Malformed XML detected")

    @patch("feedparser.parse")
    def test_from_content_parsing_exception(self, mock_parse: Mock) -> None:
        """Test handling of unexpected parsing exceptions."""
        mock_parse.side_effect = Exception("Unexpected error")

        with self.assertRaises(Exception) as cm:
            self.parser.from_content(
                "http://example.com/rss", b"<rss>content</rss>"
            )

        self.assertEqual(str(cm.exception), "Unexpected error")

    @patch("feedparser.parse")
    def test_from_content_create_podcast_returns_none(
        self, mock_parse: Mock
    ) -> None:
        """Test handling when create_podcast_from_feed returns None."""
        mock_feed_data = self._create_mock_feed_data("Test Podcast")
        mock_parse.return_value = mock_feed_data

        with patch.object(
            self.parser, "create_podcast_from_feed"
        ) as mock_create:
            mock_create.return_value = None

            result = self.parser.from_content(
                "http://example.com/rss", b"<rss>content</rss>"
            )

            self.assertIsNone(result)

    # Test _create_podcast_from_feed method
    def test_create_podcast_from_feed_basic(self) -> None:
        """Test basic podcast creation from feed data."""
        entries = [self._create_mock_entry("123", "Episode 1")]
        mock_feed_data = self._create_mock_feed_data("My Podcast", entries)

        with patch.object(
            self.parser, "parse_entry_to_episode"
        ) as mock_parse_episode:
            mock_episode = Mock(spec=Episode)
            mock_parse_episode.return_value = mock_episode

            # pylint: disable=protected-access
            result = self.parser.create_podcast_from_feed(
                "http://example.com/rss", mock_feed_data
            )

            self.assertIsInstance(result, Podcast)
            self.assertEqual(result.title, "My Podcast")
            self.assertEqual(result.rss_url, "http://example.com/rss")
            self.assertEqual(result.safe_title, "My Podcast")
            self.assertEqual(len(result.episodes), 1)
            self.assertEqual(result.episodes[0], mock_episode)

    def test_create_podcast_from_feed_unknown_title(self) -> None:
        """Test podcast creation with missing title."""
        mock_feed_data = self._create_mock_feed_data()
        mock_feed_data.feed = {}  # No title

        # pylint: disable=protected-access
        result = self.parser.create_podcast_from_feed(
            "http://example.com/rss", mock_feed_data
        )
        assert result is not None
        self.assertEqual(result.title, "Unknown Podcast")
        self.assertEqual(result.safe_title, "Unknown Podcast")

    def test_create_podcast_from_feed_no_entries(self) -> None:
        """Test podcast creation with no entries."""
        mock_feed_data = self._create_mock_feed_data("Empty Podcast", [])

        # pylint: disable=protected-access
        result = self.parser.create_podcast_from_feed(
            "http://example.com/rss", mock_feed_data
        )
        assert result is not None
        self.assertEqual(result.title, "Empty Podcast")
        self.assertEqual(len(result.episodes), 0)

    def test_create_podcast_from_feed_filtered_episodes(self) -> None:
        """Test that invalid episodes are filtered out."""
        entries = [
            self._create_mock_entry("123", "Valid Episode"),
            self._create_mock_entry("456", "Invalid Episode"),
        ]
        mock_feed_data = self._create_mock_feed_data("Test Podcast", entries)

        with patch.object(
            self.parser, "parse_entry_to_episode"
        ) as mock_parse_episode:
            # First episode valid, second invalid (returns None)
            mock_episode = Mock(spec=Episode)
            mock_parse_episode.side_effect = [mock_episode, None]

            # pylint: disable=protected-access
            result = self.parser.create_podcast_from_feed(
                "http://example.com/rss", mock_feed_data
            )
            assert result is not None
            self.assertEqual(len(result.episodes), 1)
            self.assertEqual(result.episodes[0], mock_episode)

    # Test _parse_entry_to_episode method
    def test_parse_entry_to_episode_success(self) -> None:
        """Test successful episode parsing."""
        entry = self._create_mock_entry(
            episode_id="123",
            title="Test Episode",
            published="2023-01-01",
            author="Test Author",
            itunes_duration="30:00",
        )

        # pylint: disable=protected-access
        result = self.parser.parse_entry_to_episode(entry)

        self.assertIsNotNone(result)
        assert result is not None  # for type checker
        self.assertEqual(result.id, "123")
        self.assertEqual(result.title, "Test Episode")
        self.assertEqual(result.published, "2023-01-01")
        self.assertEqual(result.author, "Test Author")
        self.assertEqual(result.audio_link, "http://example.com/episode.mp3")
        self.assertEqual(result.size, 1000)

    def test_parse_entry_to_episode_missing_id(self) -> None:
        """Test episode parsing with missing supercast_episode_id."""
        entry = self._create_mock_entry(title="No ID Episode")
        del entry["supercast_episode_id"]

        # pylint: disable=protected-access
        result = self.parser.parse_entry_to_episode(entry)

        self.assertIsNone(result)

    def test_parse_entry_to_episode_no_audio_enclosure(self) -> None:
        """Test episode parsing with no audio enclosures."""
        entry = self._create_mock_entry(has_audio=False)

        # pylint: disable=protected-access
        result = self.parser.parse_entry_to_episode(entry)

        self.assertIsNone(result)

    def test_parse_entry_to_episode_non_audio_enclosure(self) -> None:
        """Test episode parsing with non-audio enclosures."""
        entry = self._create_mock_entry(audio_type="video/mp4")

        # pylint: disable=protected-access
        result = self.parser.parse_entry_to_episode(entry)

        self.assertIsNone(result)

    def test_parse_entry_to_episode_multiple_enclosures(self) -> None:
        """Test episode parsing with multiple enclosures, picks first audio."""
        entry = self._create_mock_entry()
        entry["enclosures"] = [
            {
                "type": "video/mp4",
                "href": "http://example.com/video.mp4",
                "length": "2000",
            },
            {
                "type": "audio/mpeg",
                "href": "http://example.com/audio1.mp3",
                "length": "1000",
            },
            {
                "type": "audio/wav",
                "href": "http://example.com/audio2.wav",
                "length": "1500",
            },
        ]

        # pylint: disable=protected-access
        result = self.parser.parse_entry_to_episode(entry)

        self.assertIsNotNone(result)
        assert result is not None  # for type checker
        self.assertEqual(result.audio_link, "http://example.com/audio1.mp3")
        self.assertEqual(result.size, 1000)

    def test_parse_entry_to_episode_defaults(self) -> None:
        """Test episode parsing with minimal data and defaults."""
        entry = {
            "supercast_episode_id": "123",
            "enclosures": [
                {"type": "audio/mpeg", "href": "http://example.com/test.mp3"}
            ],
        }

        # pylint: disable=protected-access
        result = self.parser.parse_entry_to_episode(entry)

        self.assertIsNotNone(result)
        assert result is not None  # for type checker
        self.assertEqual(result.id, "123")
        self.assertEqual(result.title, "Unknown Title")
        self.assertEqual(result.published, "")
        self.assertEqual(result.author, "")
        self.assertEqual(result.image, "")
        self.assertEqual(result.size, 0)

    def test_parse_entry_to_episode_with_image(self) -> None:
        """Test episode parsing with image data."""
        entry = self._create_mock_entry()
        entry["image"] = {"href": "http://example.com/episode_image.jpg"}

        # pylint: disable=protected-access
        result = self.parser.parse_entry_to_episode(entry)

        self.assertIsNotNone(result)
        assert result is not None  # for type checker
        self.assertEqual(result.image, "http://example.com/episode_image.jpg")

    def test_parse_entry_to_episode_missing_image_href(self) -> None:
        """Test episode parsing with malformed image data."""
        entry = self._create_mock_entry()
        entry["image"] = {}  # Missing href

        # pylint: disable=protected-access
        result = self.parser.parse_entry_to_episode(entry)

        self.assertIsNotNone(result)
        assert result is not None  # for type checker
        self.assertEqual(result.image, "")

    def test_parse_entry_to_episode_enclosure_length_conversion(self) -> None:
        """Test that enclosure length is properly converted to int."""
        entry = self._create_mock_entry()
        entry["enclosures"][0]["length"] = "12345"

        # pylint: disable=protected-access
        result = self.parser.parse_entry_to_episode(entry)

        self.assertIsNotNone(result)
        assert result is not None  # for type checker
        self.assertEqual(result.size, 12345)

    def test_parse_entry_to_episode_invalid_length(self) -> None:
        """Test handling of invalid enclosure length."""
        entry = self._create_mock_entry()
        entry["enclosures"][0]["length"] = "not_a_number"

        # This should raise ValueError when int() is called
        with self.assertRaises(ValueError):
            # pylint: disable=protected-access
            self.parser.parse_entry_to_episode(entry)


if __name__ == "__main__":
    unittest.main()
