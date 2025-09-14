"""
Tests for the podcast parser functions.
"""

# pylint: disable=duplicate-code

import os
import shutil
import unittest
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import feedparser

from easy_podcast.parser import PodcastParser

from tests.base import PodcastTestBase


# pylint: disable=too-many-public-methods
class TestPodcastParserFunctions(PodcastTestBase):
    """Test suite for the podcast parser functions."""

    def setUp(self) -> None:
        """Set up test data."""
        super().setUp()  # Call parent setUp for test_dir
        self.parser = PodcastParser()
        self.base_dir = "test_parser_data"
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def tearDown(self) -> None:
        """Clean up test data."""
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)
        super().tearDown()  # Call parent tearDown

    def _create_mock_feed(
        self, title: str, entries_data: List[Dict[str, Any]]
    ) -> feedparser.FeedParserDict:
        """Creates a mock feedparser dictionary."""
        feed = feedparser.FeedParserDict()
        feed["feed"] = {"title": title}
        feed["entries"] = []
        for ep_data in entries_data:
            # Use a regular dict instead of FeedParserDict for entries
            entry = {}
            # Copy all fields from ep_data to entry
            for key, value in ep_data.items():
                if key not in ["audio_link", "size"]:
                    entry[key] = value

            # Create enclosures structure that the parser expects
            if "audio_link" in ep_data:
                entry["enclosures"] = [
                    {
                        "href": ep_data["audio_link"],
                        "type": "audio/mpeg",
                        "length": str(ep_data.get("size", 0)),
                    }
                ]
            else:
                entry["enclosures"] = []

            feed["entries"].append(entry)
        return feed

    def test_parse_basic_podcast(self) -> None:
        """Test parsing a basic RSS feed into a Podcast object."""
        entries_data = [
            {
                "supercast_episode_id": "1",
                "title": "Episode 1",
                "audio_link": "http://example.com/ep1.mp3",
                "size": 1000,
            }
        ]
        mock_feed = self._create_mock_feed("My Test Podcast", entries_data)

        # pylint: disable=protected-access
        podcast = self.parser._create_podcast_from_feed(
            "http://example.com/rss", mock_feed
        )

        self.assertEqual(podcast.title, "My Test Podcast")
        self.assertEqual(len(podcast.episodes), 1)
        self.assertEqual(podcast.episodes[0].id, "1")
        self.assertEqual(podcast.episodes[0].title, "Episode 1")

    def test_parse_with_sanitized_title(self) -> None:
        """Test that the podcast safe title is correctly sanitized."""
        mock_feed = self._create_mock_feed("Podcast/With\\Slashes", [])

        # pylint: disable=protected-access
        podcast = self.parser._create_podcast_from_feed(
            "http://example.com/rss", mock_feed
        )

        expected_safe_title = "Podcast_With_Slashes"
        self.assertEqual(podcast.safe_title, expected_safe_title)

    def test_parse_podcast_with_mixed_valid_invalid_entries(self) -> None:
        """Test parsing a podcast with both valid and invalid entries."""
        # Create entries with mixed valid and invalid data
        entries_data: List[Dict[str, Any]] = [
            # Valid entry
            {
                "supercast_episode_id": "1",
                "published": "Tue, 01 Jan 2020 12:00:00 +0000",
                "title": "Valid Episode",
                "author": "Author",
                "itunes_duration": "10:00",
                "image": {"href": "http://example.com/image.jpg"},
                "audio_link": "http://example.com/ep1.mp3",
                "size": 1000,
            },
            # Invalid entry (will have no audio enclosures)
            {
                "supercast_episode_id": "2",
                "title": "Invalid Episode",
                # No audio_link, so no enclosures will be created
            },
            # Another valid entry
            {
                "supercast_episode_id": "3",
                "published": "Wed, 02 Jan 2020 12:00:00 +0000",
                "title": "Another Valid Episode",
                "author": "Author",
                "itunes_duration": "15:30",
                "audio_link": "http://example.com/ep3.mp3",
                "size": 2000,
            },
        ]

        mock_feed = self._create_mock_feed("Mixed Test Podcast", entries_data)

        # pylint: disable=protected-access
        podcast = self.parser._create_podcast_from_feed(
            "http://example.com/rss", mock_feed
        )

        # Only valid entries should be included
        self.assertEqual(podcast.title, "Mixed Test Podcast")
        self.assertEqual(len(podcast.episodes), 2)  # Only valid episodes
        self.assertEqual(podcast.episodes[0].id, "1")
        self.assertEqual(podcast.episodes[0].title, "Valid Episode")
        self.assertEqual(podcast.episodes[1].id, "3")
        self.assertEqual(podcast.episodes[1].title, "Another Valid Episode")

    def test_parse_entry_to_episode(self) -> None:
        """Test the internal method for parsing a single entry."""
        entry_data = {
            "supercast_episode_id": "ep123",
            "published": "Tue, 01 Jan 2020 12:00:00 +0000",
            "title": "The Best Episode",
            "author": "The Author",
            "itunes_duration": "01:23:45",  # feedparser returns string
            "image": {"href": "http://example.com/image.jpg"},
            "enclosures": [
                {
                    "href": "http://example.com/ep123.mp3?key=val",
                    "type": "audio/mpeg",
                    "length": "12345",
                }
            ],
        }

        # pylint: disable=protected-access
        episode = self.parser._parse_entry_to_episode(entry_data)

        self.assertIsNotNone(episode)
        if episode:
            self.assertEqual(episode.id, "ep123")
            self.assertEqual(episode.title, "The Best Episode")
            self.assertEqual(episode.audio_filename, "ep123.mp3")
            self.assertEqual(episode.size, 12345)
            # Verify duration was correctly parsed: 1h 23m 45s = 5025 seconds
            self.assertEqual(episode.duration_seconds, 5025)

    def test_parse_entry_missing_id(self) -> None:
        """Test that entries without a supercast ID are skipped."""
        entry_data = {"title": "No ID Episode"}
        # pylint: disable=protected-access
        episode = self.parser._parse_entry_to_episode(entry_data)
        self.assertIsNone(episode)

    def test_parse_entry_missing_audio(self) -> None:
        """Test that entries without an audio enclosure are skipped."""
        entry_data = {"supercast_episode_id": "no-audio-123"}
        # pylint: disable=protected-access
        episode = self.parser._parse_entry_to_episode(entry_data)
        self.assertIsNone(episode)

    def test_parse_entry_missing_episode_id(self) -> None:
        """Test parsing entry without supercast_episode_id returns None."""
        entry: Dict[str, Any] = {
            "title": "Test Episode",
            "enclosures": [
                {"href": "http://test.com/audio.mp3", "type": "audio/mpeg"}
            ],
        }
        # pylint: disable=protected-access
        result = self.parser._parse_entry_to_episode(entry)
        self.assertIsNone(result)

    def test_parse_entry_missing_audio_enclosure(self) -> None:
        """Test parsing entry without audio enclosure returns None."""
        entry: Dict[str, Any] = {
            "supercast_episode_id": "123",
            "title": "Test Episode",
            "enclosures": [
                {"href": "http://test.com/video.mp4", "type": "video/mp4"}
            ],
        }
        # pylint: disable=protected-access
        result = self.parser._parse_entry_to_episode(entry)
        self.assertIsNone(result)

    def test_parse_entry_with_different_audio_formats(self) -> None:
        """Test parsing entries with various audio formats."""
        test_cases = [
            ("audio/mpeg", ".mp3"),
            ("audio/wav", ".wav"),
            ("audio/ogg", ".ogg"),
            ("audio/mp4", ".mp4"),
        ]

        for audio_type, original_ext in test_cases:
            entry: Dict[str, Any] = {
                "supercast_episode_id": "123",
                "title": "Test Episode",
                "enclosures": [
                    {
                        "href": f"http://test.com/audio{original_ext}",
                        "type": audio_type,
                    }
                ],
            }
            # pylint: disable=protected-access
            result = self.parser._parse_entry_to_episode(entry)
            self.assertIsNotNone(result)
            if result:
                # Audio file is always {id}.mp3 regardless of original format
                self.assertEqual(result.audio_filename, "123.mp3")

    def test_parse_entry_url_with_query_params(self) -> None:
        """Test parsing audio URL with query parameters."""
        entry: Dict[str, Any] = {
            "supercast_episode_id": "123",
            "title": "Test Episode",
            "enclosures": [
                {
                    "href": "http://test.com/audio.mp3?token=abc123",
                    "type": "audio/mpeg",
                }
            ],
        }
        # pylint: disable=protected-access
        result = self.parser._parse_entry_to_episode(entry)
        self.assertIsNotNone(result)
        if result:
            self.assertEqual(
                result.audio_filename, "123.mp3"
            )  # Should strip query params for filename

    def test_parse_entry_with_empty_fields(self) -> None:
        """Test parsing entry with missing optional fields."""
        entry: Dict[str, Any] = {
            "supercast_episode_id": "123",
            # Missing title, author, etc.
            "enclosures": [
                {
                    "href": "http://test.com/audio.mp3",
                    "type": "audio/mpeg",
                    "length": "1000",
                }
            ],
        }

        # pylint: disable=protected-access
        result = self.parser._parse_entry_to_episode(entry)
        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result.id, "123")
            self.assertEqual(result.title, "Unknown Title")  # Default value
            self.assertEqual(result.author, "")  # Default empty
            self.assertEqual(result.size, 1000)

    def test_parse_entry_with_multiple_enclosures(self) -> None:
        """Test parsing entry with multiple enclosures picks first audio."""
        entry: Dict[str, Any] = {
            "supercast_episode_id": "123",
            "title": "Test Episode",
            "enclosures": [
                {"href": "http://test.com/video.mp4", "type": "video/mp4"},
                {
                    "href": "http://test.com/audio1.mp3",
                    "type": "audio/mpeg",
                    "length": "1000",
                },
                {
                    "href": "http://test.com/audio2.mp3",
                    "type": "audio/wav",
                    "length": "2000",
                },
            ],
        }

        # pylint: disable=protected-access
        result = self.parser._parse_entry_to_episode(entry)
        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result.audio_link, "http://test.com/audio1.mp3")
            self.assertEqual(result.size, 1000)

    def test_parse_unknown_podcast_title(self) -> None:
        """Test parsing feed with missing title."""
        feed = feedparser.FeedParserDict()
        feed["feed"] = {}  # No title
        feed["entries"] = []

        # pylint: disable=protected-access
        podcast = self.parser._create_podcast_from_feed(
            "http://example.com/rss", feed
        )
        self.assertEqual(podcast.title, "Unknown Podcast")

    def test_parse_feed_without_entries(self) -> None:
        """Test parsing feed with no entries attribute."""
        feed = feedparser.FeedParserDict()
        feed["feed"] = {"title": "Test Podcast"}
        # No entries attribute at all

        # pylint: disable=protected-access
        podcast = self.parser._create_podcast_from_feed(
            "http://example.com/rss", feed
        )
        self.assertEqual(podcast.title, "Test Podcast")
        self.assertEqual(len(podcast.episodes), 0)

    def test_parse_from_content_success(self) -> None:
        """Test successful parsing from RSS content bytes."""
        rss_content = (
            b"<rss><channel><title>Test Podcast</title><item>"
            b"<supercast_episode_id>123</supercast_episode_id>"
            + self.get_xml_fragment()
            + b'<enclosure url="http://test.com/audio.mp3" type="audio/mpeg"/>'
            b"</item></channel></rss>"
        )

        result = self.parser.from_content("http://test.com/rss", rss_content)

        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result.title, "Test Podcast")
            self.assertEqual(len(result.episodes), 1)
            self.assertEqual(result.episodes[0].id, "123")

    @patch("feedparser.parse")
    def test_parse_from_content_exception(self, mock_parse: Mock) -> None:
        """Test parse_from_content propagates exceptions."""
        mock_parse.side_effect = Exception("Parse error")

        # Should raise the exception instead of returning None
        with self.assertRaises(Exception) as context:
            self.parser.from_content("http://test.com/rss", b"invalid content")

        self.assertEqual(str(context.exception), "Parse error")

    def test_parse_from_file_success(self) -> None:
        """Test successful parsing from RSS file."""
        rss_file_path = os.path.join(self.base_dir, "test.xml")
        rss_content = (
            b"<rss><channel><title>File Podcast</title><item>"
            b"<supercast_episode_id>456</supercast_episode_id>"
            b"<title>File Episode</title>"
            b'<enclosure url="http://test.com/file.mp3" type="audio/mpeg"/>'
            b"</item></channel></rss>"
        )

        with open(rss_file_path, "wb") as f:
            f.write(rss_content)

        result = self.parser.from_file("http://test.com/rss", rss_file_path)

        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result.title, "File Podcast")
            self.assertEqual(len(result.episodes), 1)
            self.assertEqual(result.episodes[0].id, "456")

    def test_parse_from_file_not_found(self) -> None:
        """Test parse_from_file when file doesn't exist."""
        result = self.parser.from_file(
            "http://test.com/rss", "nonexistent.xml"
        )

        self.assertIsNone(result)

    @patch("builtins.open")
    def test_parse_from_file_read_error(self, mock_open: Mock) -> None:
        """Test parse_from_file when file read fails."""
        mock_open.side_effect = IOError("Read error")

        result = self.parser.from_file("http://test.com/rss", "test.xml")

        self.assertIsNone(result)

    def test_parse_entry_duration_mm_ss_format(self) -> None:
        """Test parsing entry with MM:SS duration format."""
        entry: Dict[str, Any] = {
            "supercast_episode_id": "123",
            "title": "Test Episode",
            "itunes_duration": "30:45",  # 30 minutes 45 seconds
            "enclosures": [
                {
                    "href": "http://test.com/audio.mp3",
                    "type": "audio/mpeg",
                }
            ],
        }

        # pylint: disable=protected-access
        result = self.parser._parse_entry_to_episode(entry)
        self.assertIsNotNone(result)
        if result:
            # 30:45 = 30*60 + 45 = 1845 seconds
            self.assertEqual(result.duration_seconds, 1845)

    def test_parse_entry_duration_hh_mm_ss_format(self) -> None:
        """Test parsing entry with HH:MM:SS duration format."""
        entry: Dict[str, Any] = {
            "supercast_episode_id": "123",
            "title": "Test Episode",
            "itunes_duration": "2:15:30",  # 2 hours 15 minutes 30 seconds
            "enclosures": [
                {
                    "href": "http://test.com/audio.mp3",
                    "type": "audio/mpeg",
                }
            ],
        }

        # pylint: disable=protected-access
        result = self.parser._parse_entry_to_episode(entry)
        self.assertIsNotNone(result)
        if result:
            # 2:15:30 = 2*3600 + 15*60 + 30 = 8130 seconds
            self.assertEqual(result.duration_seconds, 8130)

    def test_parse_entry_duration_invalid_format(self) -> None:
        """Test parsing entry with invalid duration format returns -1."""
        entry: Dict[str, Any] = {
            "supercast_episode_id": "123",
            "title": "Test Episode",
            "itunes_duration": "invalid",
            "enclosures": [
                {
                    "href": "http://test.com/audio.mp3",
                    "type": "audio/mpeg",
                }
            ],
        }

        # pylint: disable=protected-access
        result = self.parser._parse_entry_to_episode(entry)
        self.assertIsNotNone(result)
        if result:
            # Invalid duration should return -1
            self.assertEqual(result.duration_seconds, -1)

    def test_parse_entry_duration_empty(self) -> None:
        """Test parsing entry with empty duration returns -1."""
        entry: Dict[str, Any] = {
            "supercast_episode_id": "123",
            "title": "Test Episode",
            "itunes_duration": "",
            "enclosures": [
                {
                    "href": "http://test.com/audio.mp3",
                    "type": "audio/mpeg",
                }
            ],
        }

        # pylint: disable=protected-access
        result = self.parser._parse_entry_to_episode(entry)
        self.assertIsNotNone(result)
        if result:
            # Empty duration should return -1
            self.assertEqual(result.duration_seconds, -1)

    def test_parse_entry_duration_missing(self) -> None:
        """Test parsing entry without itunes_duration field returns -1."""
        entry: Dict[str, Any] = {
            "supercast_episode_id": "123",
            "title": "Test Episode",
            # No itunes_duration field
            "enclosures": [
                {
                    "href": "http://test.com/audio.mp3",
                    "type": "audio/mpeg",
                }
            ],
        }

        # pylint: disable=protected-access
        result = self.parser._parse_entry_to_episode(entry)
        self.assertIsNotNone(result)
        if result:
            # Missing duration should return -1
            self.assertEqual(result.duration_seconds, -1)

    def test_parse_from_content_malformed_xml(self) -> None:
        """Test parse_from_content with malformed XML (triggers bozo bit)."""
        # Create malformed XML with unclosed tag that will trigger SAX error
        malformed_xml = self.get_malformed_xml()

        # This should raise an exception due to malformed XML
        with self.assertRaises(Exception) as context:
            self.parser.from_content("http://test.com/rss", malformed_xml)

        self.assertIn("Malformed XML detected", str(context.exception))

    def test_parse_from_content_wellformed_xml(self) -> None:
        """Test parse_from_content with well-formed XML."""
        # Create well-formed XML
        wellformed_xml = self.get_wellformed_xml()

        # This should succeed
        result = self.parser.from_content(
            "http://test.com/rss", wellformed_xml
        )
        self.assertIsNotNone(
            result, "Parser should succeed with well-formed XML"
        )
        if result:
            self.assertEqual(result.title, "Test Podcast")
            self.assertEqual(len(result.episodes), 1)
            self.assertEqual(result.episodes[0].id, "123")

    def test_parse_from_content_non_xml_content(self) -> None:
        """Test parse_from_content with non-XML content."""
        # Non-XML content that will trigger bozo bit
        non_xml = b"This is not XML content at all"

        # This should raise an exception due to malformed XML
        with self.assertRaises(Exception) as context:
            self.parser.from_content("http://test.com/rss", non_xml)

        self.assertIn("Malformed XML detected", str(context.exception))

    def test_parse_from_file_malformed_xml(self) -> None:
        """Test parse_from_file with malformed XML file."""
        # Create a file with malformed XML
        malformed_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test Podcast</title>
                <item>
                    <title>Test Episode</title>
                    <description>Unclosed description
                </item>
            </channel>
        </rss>"""

        test_file = os.path.join(self.base_dir, "malformed.xml")
        with open(test_file, "wb") as f:
            f.write(malformed_xml)

        # This should raise an exception due to malformed XML
        with self.assertRaises(ValueError) as context:
            self.parser.from_file("http://test.com/rss", test_file)

        self.assertIn("Malformed XML detected", str(context.exception))

    @patch("feedparser.parse")
    def test_parse_from_content_bozo_bit_detection(
        self, mock_parse: Mock
    ) -> None:
        """Test that bozo bit detection works correctly."""
        # Create a mock object with bozo attributes
        mock_feed = Mock()
        mock_feed.bozo = 1
        mock_feed.bozo_exception = Exception("Test SAX exception")
        mock_parse.return_value = mock_feed

        # Should raise an exception due to bozo bit being set
        with self.assertRaises(Exception) as context:
            self.parser.from_content("http://test.com/rss", b"<xml>test</xml>")

        self.assertIn("Malformed XML detected", str(context.exception))
        self.assertIn("Test SAX exception", str(context.exception))

    @patch("feedparser.parse")
    def test_parse_from_content_bozo_bit_no_exception(
        self, mock_parse: Mock
    ) -> None:
        """Test bozo bit detection when no specific exception provided."""
        # Create a mock object with bozo bit set but no specific exception
        mock_feed = Mock()
        mock_feed.bozo = 1
        mock_feed.bozo_exception = None
        mock_parse.return_value = mock_feed

        # Should raise an exception due to bozo bit being set
        with self.assertRaises(Exception) as context:
            self.parser.from_content("http://test.com/rss", b"<xml>test</xml>")

        self.assertEqual(str(context.exception), "Malformed XML detected")


if __name__ == "__main__":
    unittest.main()
