"""Base test classes and utilities for podcast package tests."""

# pylint: disable=duplicate-code

import os
import shutil
import tempfile
import unittest
from typing import Any, Dict, List
from unittest.mock import Mock

from easy_podcast.models import Podcast


class PodcastTestBase(unittest.TestCase):
    """Base test class providing common setup/teardown and utilities."""

    def setUp(self) -> None:
        """Set up temporary test directory and configure environment."""
        # Use tempfile for better isolation and automatic cleanup
        self.test_dir = tempfile.mkdtemp(prefix="podcast_test_")

        # Set environment variable for centralized path management
        os.environ["PODCAST_DATA_DIRECTORY"] = self.test_dir

    def tearDown(self) -> None:
        """Clean up test directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def create_mock_rss_content(
        self, episodes_data: List[Dict[str, Any]], title: str = "Test Podcast"
    ) -> bytes:
        """Generate mock RSS content for testing."""
        items = ""
        for episode in episodes_data:
            items += f"""
            <item>
                <title>{episode.get("title", "Test Episode")}</title>
                <supercast_episode_id>
                    {episode.get("supercast_episode_id", "123")}
                </supercast_episode_id>
                <enclosure
                    url="{episode.get("audio_link",
                                      "http://test.com/test.mp3")}"
                    type="audio/mpeg"
                    length="{episode.get("size", 1000)}"/>
            </item>"""

        rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>{title}</title>
                {items}
            </channel>
        </rss>"""
        return rss_content.encode("utf-8")

    def create_test_podcast(self, **kwargs: Any) -> Podcast:
        """Create a test Podcast object with sensible defaults."""
        defaults: Dict[str, Any] = {
            "title": "Test Podcast",
            "rss_url": "http://test.com/rss",
            "safe_title": "Test_Podcast",
            "episodes": [],
        }
        defaults.update(kwargs)
        return Podcast(**defaults)

    def create_mock_feed_data(
        self,
        title: str = "Test Podcast",
        entries: List[Dict[str, Any]] | None = None,
    ) -> Mock:
        """Create mock feedparser data for testing."""
        if entries is None:
            entries = [{"title": "Default Episode", "id": "default_123"}]

        mock_feed = Mock()
        mock_feed.feed.title = title
        mock_feed.entries = []

        for entry_data in entries:
            entry = Mock()
            for key, value in entry_data.items():
                setattr(entry, key, value)
            mock_feed.entries.append(entry)

        return mock_feed

    @staticmethod
    def get_malformed_xml() -> bytes:
        """Get standard malformed XML for testing parser error handling."""
        return b"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test Podcast</title>
                <item>
                    <title>Test Episode</title>
                    <description>Unclosed description tag
                </item>
            </channel>
        </rss>"""

    @staticmethod
    def get_wellformed_xml() -> bytes:
        """Get standard well-formed XML for testing successful parsing."""
        return b"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test Podcast</title>
                <description>A test podcast</description>
                <item>
                    <title>Test Episode</title>
                    <description>Test description</description>
                    <supercast_episode_id>123</supercast_episode_id>
                    <enclosure
                        url="http://test.com/audio.mp3"
                        type="audio/mpeg"
                        length="1000"/>
                </item>
            </channel>
        </rss>"""

    @staticmethod
    def get_xml_fragment() -> bytes:
        """Get XML fragment for testing."""
        return b"<title>Test Episode</title>"


class IntegrationTestBase(PodcastTestBase):
    """Base class for integration tests with enhanced mocking utilities."""

    def create_mock_http_responses(
        self, rss_content: bytes, audio_content: bytes = b"audio_content"
    ) -> Dict[str, Mock]:
        """Create standard HTTP response mocks for RSS and audio."""
        rss_response = Mock()
        rss_response.content = rss_content
        rss_response.raise_for_status.return_value = None

        audio_response = Mock()
        audio_response.iter_content.return_value = [audio_content]
        audio_response.raise_for_status.return_value = None
        audio_response.__enter__ = Mock(return_value=audio_response)
        audio_response.__exit__ = Mock(return_value=None)

        return {"rss": rss_response, "audio": audio_response}
