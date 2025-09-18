"""
Simplified file management for podcast data.

Replaces PathManager and StorageManager.
"""

import hashlib
import json
import os
from dataclasses import asdict
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from .models import Episode, Podcast

from .utils import sanitize_filename


class FileManager:
    """Simplified file manager for all file operations."""

    def __init__(self, data_dir: str = "./data"):
        """Initialize with data directory."""
        self.data_dir = data_dir

    def get_podcast_dir(self, podcast_title: str) -> str:
        """Get podcast directory path using sanitized title."""
        sanitized_title = sanitize_filename(podcast_title)
        return os.path.join(self.data_dir, sanitized_title)

    def get_podcast_dir_from_rss(self, rss_url: str) -> str:
        """Get podcast directory from RSS URL using domain-based naming."""
        # Use URL hash for unique folder names
        url_hash = hashlib.md5(rss_url.encode()).hexdigest()[:8]
        folder_name = f"podcast_{url_hash}"
        return os.path.join(self.data_dir, folder_name)

    def get_episodes_file_path(self, podcast_title: str) -> str:
        """Get path to episodes.jsonl file for a podcast."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        return os.path.join(podcast_dir, "episodes.jsonl")

    def get_podcast_metadata_path(self, podcast_title: str) -> str:
        """Get path to podcast metadata file."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        return os.path.join(podcast_dir, "podcast.json")

    def get_rss_cache_path(self, podcast_title: str) -> str:
        """Get path to RSS cache file."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        return os.path.join(podcast_dir, "rss.xml")

    def get_episode_audio_path(
        self, podcast_title: str, episode: "Episode"
    ) -> str:
        """Get full path to episode audio file."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        return os.path.join(podcast_dir, episode.audio_filename)

    def get_episode_transcript_path(
        self, podcast_title: str, episode: "Episode"
    ) -> str:
        """Get full path to episode transcript file."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        return os.path.join(podcast_dir, episode.transcript_filename)

    def ensure_podcast_dir_exists(self, podcast_title: str) -> str:
        """Ensure podcast directory exists and return its path."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        os.makedirs(podcast_dir, exist_ok=True)
        return podcast_dir

    def save_podcast_metadata(self, podcast: "Podcast") -> None:
        """Save podcast metadata to JSON file."""
        self.ensure_podcast_dir_exists(podcast.title)
        metadata_path = self.get_podcast_metadata_path(podcast.title)

        with open(metadata_path, "w", encoding="utf-8") as f:
            # Save podcast without episodes (episodes saved separately)
            podcast_data = asdict(podcast)
            podcast_data.pop("episodes", None)
            json.dump(podcast_data, f, indent=2, ensure_ascii=False)

    def load_podcast_metadata(self, podcast_title: str) -> Optional["Podcast"]:
        """Load podcast metadata from JSON file."""
        metadata_path = self.get_podcast_metadata_path(podcast_title)

        if not os.path.exists(metadata_path):
            return None

        try:
            from .models import Podcast

            with open(metadata_path, "r", encoding="utf-8") as f:
                podcast_data = json.load(f)
                return Podcast.from_dict(podcast_data)
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            return None

    def save_episodes(
        self, podcast_title: str, episodes: List["Episode"]
    ) -> None:
        """Save all episodes to a single JSONL file."""
        self.ensure_podcast_dir_exists(podcast_title)
        episodes_path = self.get_episodes_file_path(podcast_title)

        with open(episodes_path, "w", encoding="utf-8") as f:
            for episode in episodes:
                episode_data = asdict(episode)
                f.write(json.dumps(episode_data, ensure_ascii=False) + "\n")

    def load_episodes(self, podcast_title: str) -> List["Episode"]:
        """Load all episodes from JSONL file."""
        episodes_path = self.get_episodes_file_path(podcast_title)
        episodes: List["Episode"] = []

        if not os.path.exists(episodes_path):
            return episodes

        try:
            from .models import Episode

            with open(episodes_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        episode_data = json.loads(line)
                        episode = Episode.from_dict(episode_data)
                        episodes.append(episode)
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            pass  # Return empty list on error

        return episodes

    def save_rss_cache(self, podcast_title: str, rss_content: bytes) -> None:
        """Save RSS content to cache file."""
        self.ensure_podcast_dir_exists(podcast_title)
        cache_path = self.get_rss_cache_path(podcast_title)

        with open(cache_path, "wb") as f:
            f.write(rss_content)

    def load_rss_cache(self, podcast_title: str) -> Optional[bytes]:
        """Load RSS content from cache file."""
        cache_path = self.get_rss_cache_path(podcast_title)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, "rb") as f:
                return f.read()
        except (IOError, FileNotFoundError):
            return None

    def list_podcast_directories(self) -> List[str]:
        """List all podcast directories in the data directory."""
        if not os.path.exists(self.data_dir):
            return []

        podcast_dirs = []
        for item in os.listdir(self.data_dir):
            item_path = os.path.join(self.data_dir, item)
            if os.path.isdir(item_path):
                podcast_dirs.append(item)

        return podcast_dirs

    def podcast_exists(self, podcast_title: str) -> bool:
        """Check if a podcast directory exists."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        return os.path.exists(podcast_dir)

    def get_transcript_filename(self, audio_filename: str) -> str:
        """Get transcript filename for an audio file."""
        name_without_ext = os.path.splitext(audio_filename)[0]
        return f"{name_without_ext}_transcript.txt"
