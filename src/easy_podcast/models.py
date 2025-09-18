"""
Data models for podcast episodes and podcasts.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from .utils import parse_duration_to_seconds


@dataclass
class Episode:  # pylint: disable=too-many-instance-attributes
    """Represents a single podcast episode.

    Pure data class without file system dependencies.
    File paths are handled by the repository layer.
    
    The 'id' field contains the current supercast_episode_id for backward
    compatibility. The 'guid' field will contain the RSS standard GUID.
    During transition, 'guid' may be None for existing episodes.
    """

    id: str
    published: str
    title: str
    author: str
    duration_seconds: int
    size: int
    audio_link: str
    image: str
    guid: str = ""  # RSS standard GUID field

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Episode":
        """Create Episode from dictionary, handling old format conversion."""

        # Remove fields that are no longer used
        data = data.copy()
        data.pop("audio_file", None)
        data.pop("transcript_file", None)

        # Handle conversion from old itunes_duration to new duration_seconds
        if "itunes_duration" in data and "duration_seconds" not in data:
            duration_str = data.pop("itunes_duration")
            data["duration_seconds"] = parse_duration_to_seconds(duration_str)

        return cls(**data)

    def to_json(self) -> str:
        """Convert episode to JSON string."""
        return json.dumps(asdict(self))
@dataclass
class Podcast:
    """Represents a podcast, containing its metadata and episodes.

    The 'guid' field contains the RSS standard GUID for the podcast.
    During transition, this may be derived from the RSS URL or feed data.
    """

    title: str
    rss_url: str
    safe_title: str  # Sanitized title used for folder names
    episodes: List[Episode] = field(default_factory=list)
    guid: str = ""  # RSS standard GUID field

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Podcast":
        """Create Podcast from dictionary."""
        # Make a copy to avoid modifying the original
        data = data.copy()

        # Handle episodes list if present
        episodes_data = data.pop("episodes", [])
        episodes = [Episode.from_dict(ep_data) for ep_data in episodes_data]

        return cls(episodes=episodes, **data)

    def to_json(self) -> str:
        """Convert podcast to JSON string."""
        return json.dumps(asdict(self))
