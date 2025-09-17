"""
RSS feed parsing functionality.
"""

import logging
from typing import Any, Dict, Optional

import feedparser

from .downloader import download_rss_from_url, load_rss_from_file
from .models import Episode, Podcast
from .utils import parse_duration_to_seconds, sanitize_filename


class PodcastParser:
    """Handles RSS parsing and podcast creation from various sources."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    def from_rss_url(self, rss_url: str) -> Optional[Podcast]:
        """Create podcast from RSS URL by downloading and parsing."""
        self.logger.info("Parsing podcast from RSS URL: %s", rss_url)

        rss_content = download_rss_from_url(rss_url)
        if not rss_content:
            self.logger.error(
                "Failed to download RSS content from %s", rss_url
            )
            return None

        return self.from_content(rss_url, rss_content)

    def from_file(self, rss_url: str, rss_file_path: str) -> Optional[Podcast]:
        """Create podcast from RSS file."""
        self.logger.info(
            "Parsing podcast from file: %s (URL: %s)", rss_file_path, rss_url
        )

        rss_content = load_rss_from_file(rss_file_path)
        if not rss_content:
            self.logger.error(
                "Failed to load RSS content from %s", rss_file_path
            )
            return None

        return self.from_content(rss_url, rss_content)

    def from_content(
        self, rss_url: str, rss_content: bytes
    ) -> Optional[Podcast]:
        """Parse RSS content into a Podcast object."""
        self.logger.debug(
            "Parsing RSS content (%d bytes) for URL: %s",
            len(rss_content),
            rss_url,
        )

        feed_data = feedparser.parse(rss_content)

        # Check if the feed is malformed using feedparser's bozo bit
        if getattr(feed_data, "bozo", 0):
            bozo_exception = getattr(feed_data, "bozo_exception", None)
            if bozo_exception:
                self.logger.error("Malformed XML detected: %s", bozo_exception)
                error_msg = f"Malformed XML detected: {bozo_exception}"
                raise ValueError(error_msg)
            self.logger.error("Malformed XML detected")
            raise ValueError("Malformed XML detected")

        podcast = self._create_podcast_from_feed(rss_url, feed_data)

        if podcast:
            self.logger.info(
                "Successfully parsed podcast '%s' with %d episodes",
                podcast.title,
                len(podcast.episodes),
            )

        return podcast

    def _create_podcast_from_feed(
        self, rss_url: str, feed_data: feedparser.FeedParserDict
    ) -> Podcast:
        """Create Podcast object from parsed feed data."""
        feed_info = getattr(feed_data, "feed", {})
        podcast_title = feed_info.get("title", "Unknown Podcast")
        safe_title = sanitize_filename(podcast_title)

        # Create a GUID for the podcast - use RSS URL as a unique identifier
        # In the future, this could be extracted from feed metadata
        podcast_guid = rss_url

        self.logger.debug(
            "Creating podcast: '%s' (safe: '%s')", podcast_title, safe_title
        )

        podcast = Podcast(
            title=podcast_title,
            rss_url=rss_url,
            safe_title=safe_title,
            guid=podcast_guid,
        )

        feed_entries = getattr(feed_data, "entries", [])
        self.logger.debug("Processing %d feed entries", len(feed_entries))

        for entry in feed_entries:
            episode = self._parse_entry_to_episode(entry)
            if episode:
                podcast.episodes.append(episode)

        self.logger.debug(
            "Created %d valid episodes from %d entries",
            len(podcast.episodes),
            len(feed_entries),
        )

        return podcast

    def _parse_entry_to_episode(
        self, entry: Dict[str, Any]
    ) -> Optional[Episode]:
        """Convert feed entry to Episode object."""
        # Extract both the supercast ID (for backward compatibility)
        # and the RSS standard GUID
        episode_id = entry.get("supercast_episode_id")
        episode_guid = entry.get("guid", "")
        
        # If we don't have a supercast ID, try to use the GUID as ID
        if not episode_id:
            episode_id = episode_guid
            
        if not episode_id:
            self.logger.debug(
                "Skipping entry without episode ID or GUID: %s",
                entry.get("title", "Unknown"),
            )
            return None

        # Find audio enclosure
        audio_url, audio_size = None, 0
        for enclosure in entry.get("enclosures", []):
            if enclosure.get("type", "").startswith("audio"):
                audio_url = enclosure.get("href")
                audio_size = int(enclosure.get("length", 0))
                break

        if not audio_url:
            self.logger.debug(
                "Skipping entry without audio enclosure: %s",
                entry.get("title", "Unknown"),
            )
            return None

        episode_title = entry.get("title", "Unknown Title")
        self.logger.debug("Parsed episode: %s (%s)", episode_id, episode_title)

        return Episode(
            id=episode_id,
            published=entry.get("published", ""),
            title=episode_title,
            author=entry.get("author", ""),
            image=entry.get("image", {}).get("href", ""),
            duration_seconds=parse_duration_to_seconds(
                entry.get("itunes_duration", "")
            ),
            audio_link=audio_url,
            size=audio_size,
            guid=episode_guid,  # Add the GUID field
        )
