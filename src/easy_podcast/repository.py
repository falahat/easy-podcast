"""
Domain-specific repository for podcast data persistence.

This module handles podcast and episode storage using the Storage layer.
"""

import json
from dataclasses import asdict
from typing import List, Optional

from .models import Episode, Podcast
from .storage import Storage
from .utils import sanitize_filename


class PodcastRepository:
    """Repository for podcast-specific data operations."""

    def __init__(self, storage: Storage):
        """Initialize with storage instance."""
        self.storage = storage

    def get_podcast_dir(self, podcast_title: str) -> str:
        """Get podcast directory path using sanitized title."""
        sanitized_title = sanitize_filename(podcast_title)
        return self.storage.join_path(self.storage.base_dir, sanitized_title)

    def get_episode_audio_path(
        self, podcast_title: str, episode: Episode
    ) -> str:
        """Get full path to episode audio file."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        return self.storage.join_path(podcast_dir, f"{episode.id}.mp3")

    def get_episode_transcript_path(
        self, podcast_title: str, episode: Episode
    ) -> str:
        """Get full path to episode transcript file."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        filename = f"{episode.id}_transcript.json"
        return self.storage.join_path(podcast_dir, filename)

    def ensure_podcast_dir_exists(self, podcast_title: str) -> str:
        """Ensure podcast directory exists and return its path."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        self.storage.ensure_directory(podcast_dir)
        return podcast_dir

    def save_podcast_metadata(self, podcast: Podcast) -> bool:
        """Save podcast metadata to JSON file."""
        self.ensure_podcast_dir_exists(podcast.title)
        metadata_path = self._get_podcast_metadata_path(podcast.title)
        
        # Save podcast without episodes (episodes saved separately)
        podcast_data = asdict(podcast)
        podcast_data.pop("episodes", None)
        
        return self.storage.write_json(metadata_path, podcast_data)

    def load_podcast_metadata(self, podcast_title: str) -> Optional[Podcast]:
        """Load podcast metadata from JSON file."""
        metadata_path = self._get_podcast_metadata_path(podcast_title)
        
        data = self.storage.read_json(metadata_path)
        if not data:
            return None
        
        try:
            return Podcast.from_dict(data)
        except (KeyError, TypeError):
            return None

    def save_episodes(
        self, podcast_title: str, episodes: List[Episode]
    ) -> bool:
        """Save all episodes to a single JSONL file."""
        self.ensure_podcast_dir_exists(podcast_title)
        episodes_path = self._get_episodes_file_path(podcast_title)
        
        lines = []
        for episode in episodes:
            episode_json = json.dumps(asdict(episode))
            lines.append(episode_json)
        
        return self.storage.write_text_lines(episodes_path, lines)

    def load_episodes(self, podcast_title: str) -> List[Episode]:
        """Load all episodes from JSONL file."""
        episodes_path = self._get_episodes_file_path(podcast_title)
        lines = self.storage.read_text_lines(episodes_path)
        
        if not lines:
            return []
        
        episodes: List[Episode] = []
        for line in lines:
            if not line.strip():
                continue
            
            try:
                episode_data = json.loads(line)
                episode = Episode.from_dict(episode_data)
                episodes.append(episode)
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        
        return episodes

    def save_rss_cache(self, podcast_title: str, rss_content: bytes) -> bool:
        """Save RSS content to cache file."""
        self.ensure_podcast_dir_exists(podcast_title)
        cache_path = self._get_rss_cache_path(podcast_title)
        return self.storage.write_bytes(cache_path, rss_content)

    def load_rss_cache(self, podcast_title: str) -> Optional[bytes]:
        """Load RSS content from cache file."""
        cache_path = self._get_rss_cache_path(podcast_title)
        return self.storage.read_bytes(cache_path)

    def list_podcast_directories(self) -> List[str]:
        """List all podcast directories in the data directory."""
        return self.storage.list_directories(self.storage.base_dir)

    def podcast_exists(self, podcast_title: str) -> bool:
        """Check if a podcast directory exists."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        return self.storage.file_exists(podcast_dir)

    def episode_audio_exists(
        self, podcast_title: str, episode: Episode
    ) -> bool:
        """Check if episode audio file exists."""
        audio_path = self.get_episode_audio_path(podcast_title, episode)
        return self.storage.file_exists(audio_path)

    def episode_transcript_exists(
        self, podcast_title: str, episode: Episode
    ) -> bool:
        """Check if episode transcript file exists."""
        transcript_path = self.get_episode_transcript_path(
            podcast_title, episode
        )
        return self.storage.file_exists(transcript_path)

    def _get_podcast_metadata_path(self, podcast_title: str) -> str:
        """Get path to podcast metadata file."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        return self.storage.join_path(podcast_dir, "podcast.json")

    def _get_episodes_file_path(self, podcast_title: str) -> str:
        """Get path to episodes.jsonl file for a podcast."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        return self.storage.join_path(podcast_dir, "episodes.jsonl")

    def _get_rss_cache_path(self, podcast_title: str) -> str:
        """Get path to RSS cache file."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        return self.storage.join_path(podcast_dir, "rss.xml")