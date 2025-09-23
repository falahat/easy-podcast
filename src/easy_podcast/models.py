"""
Data models for podcast episodes and podcasts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Protocol, Union

from .utils import parse_duration_to_seconds


@dataclass(frozen=True)
class CustomFile:
    """Custom episode file specification for extensibility."""

    name: str
    suffix: str

    def __post_init__(self) -> None:
        if not self.name or not self.suffix:
            raise ValueError("name and suffix are required")


class EpisodeFile(Enum):
    """Standard episode file types."""
    AUDIO = "audio"
    TRANSCRIPT = "transcript"

    @property
    def suffix(self) -> str:
        """Get file suffix for this type."""
        return {
            EpisodeFile.AUDIO: ".mp3",
            EpisodeFile.TRANSCRIPT: "_transcript.json",
        }[self]


# Type alias for flexible file specifications
FileSpec = Union[EpisodeFile, CustomFile]


# Constants for podcast-level files
class PodcastFiles:
    """Standard podcast directory file names."""

    METADATA = "podcast.json"
    EPISODES = "episodes.jsonl"
    RSS_CACHE = "rss.xml"


class Storable(Protocol):
    """Protocol for entities that can be stored with GUID-based operations."""

    guid: str

    def to_json(self) -> dict[str, Any]:
        """Convert entity to JSON-serializable dictionary."""
        ...  # pylint: disable=unnecessary-ellipsis

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Storable":
        """Create entity from dictionary."""
        ...  # pylint: disable=unnecessary-ellipsis


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
    podcast_guid: str = ""  # Reference to parent podcast GUID

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Episode":
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

    def to_json(self) -> dict[str, Any]:
        """Convert episode to JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class Podcast:
    """Represents a podcast, containing its metadata and episodes.

    The 'guid' field contains the RSS standard GUID for the podcast.
    During transition, this may be derived from the RSS URL or feed data.
    """

    title: str
    rss_url: str
    episodes: list["Episode"] = field(default_factory=list)
    guid: str = ""  # RSS standard GUID field

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Podcast":
        """Create Podcast from dictionary."""
        # Make a copy to avoid modifying the original
        data = data.copy()

        # Handle episodes list if present
        episodes_data = data.pop("episodes", [])
        episodes = [Episode.from_dict(ep_data) for ep_data in episodes_data]

        return cls(episodes=episodes, **data)

    def to_json(self) -> dict[str, Any]:
        """Convert podcast to JSON-serializable dictionary."""
        return asdict(self)
