"""
Centralized authority for all file and directory paths in new storage system.
"""

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .mapping_manager import MappingManager
    from .models import Episode


class PathManager:
    """Centralized authority for all file and directory paths."""

    # Standard file names
    RSS_TO_PODCAST_MAPPING_FILE = "rss_to_podcast_mapping.json"
    PODCAST_GUID_MAPPINGS_FILE = "podcast_guid_mappings.json"
    EPISODES_GUID_MAPPINGS_FILE = "episodes_guid_mappings.json"
    PODCAST_METADATA_FILE = "podcast_metadata.json"
    EPISODE_METADATA_FILE = "metadata.json"
    AUDIO_FILE = "audio.mp3"
    TRANSCRIPT_FILE = "transcript.txt"

    def __init__(self, base_data_dir: str, mapping_manager: "MappingManager"):
        """Initialize with base data directory and mapping manager."""
        self.base_data_dir = base_data_dir
        self.mapping_manager = mapping_manager

    def get_episode_audio_path(
        self, episode: "Episode", podcast_guid: str
    ) -> str:
        """Get the full path to an episode's audio file."""
        episode_dir = self.get_episode_dir(episode, podcast_guid)
        return os.path.join(episode_dir, self.AUDIO_FILE)

    def get_episode_transcript_path(
        self, episode: "Episode", podcast_guid: str
    ) -> str:
        """Get the full path to an episode's transcript file."""
        episode_dir = self.get_episode_dir(episode, podcast_guid)
        return os.path.join(episode_dir, self.TRANSCRIPT_FILE)

    def get_episode_metadata_path(
        self, episode: "Episode", podcast_guid: str
    ) -> str:
        """Get the full path to an episode's metadata file."""
        episode_dir = self.get_episode_dir(episode, podcast_guid)
        return os.path.join(episode_dir, self.EPISODE_METADATA_FILE)

    def get_episode_dir(self, episode: "Episode", podcast_guid: str) -> str:
        """Get the full path to an episode's directory."""
        podcast_dir = self.get_podcast_dir(podcast_guid)
        # Use GUID if available, fallback to ID for backward compatibility
        episode_identifier = episode.guid if episode.guid else episode.id
        episode_folder = self.mapping_manager.get_episode_folder(
            podcast_guid, episode_identifier
        )
        return os.path.join(podcast_dir, episode_folder)

    def get_podcast_dir(self, podcast_guid: str) -> str:
        """Get the full path to a podcast's directory."""
        podcasts_dir = os.path.join(self.base_data_dir, "podcasts")
        podcast_folder = self.mapping_manager.get_podcast_folder(podcast_guid)
        return os.path.join(podcasts_dir, podcast_folder)

    def get_podcast_metadata_path(self, podcast_guid: str) -> str:
        """Get the full path to a podcast's metadata file."""
        podcast_dir = self.get_podcast_dir(podcast_guid)
        return os.path.join(podcast_dir, self.PODCAST_METADATA_FILE)

    def get_rss_mapping_path(self) -> str:
        """Get the full path to the RSS mapping file."""
        return os.path.join(
            self.base_data_dir, self.RSS_TO_PODCAST_MAPPING_FILE
        )

    def get_podcast_mappings_path(self) -> str:
        """Get the full path to the podcast mappings file."""
        podcasts_dir = os.path.join(self.base_data_dir, "podcasts")
        return os.path.join(podcasts_dir, self.PODCAST_GUID_MAPPINGS_FILE)

    def get_episode_mappings_path(self, podcast_guid: str) -> str:
        """Get the full path to a podcast's episode mappings file."""
        podcast_dir = self.get_podcast_dir(podcast_guid)
        return os.path.join(podcast_dir, self.EPISODES_GUID_MAPPINGS_FILE)

    def ensure_episode_dir_exists(
        self, episode: "Episode", podcast_guid: str
    ) -> str:
        """Ensure an episode's directory exists and return its path."""
        episode_dir = self.get_episode_dir(episode, podcast_guid)
        os.makedirs(episode_dir, exist_ok=True)
        return episode_dir

    def ensure_podcast_dir_exists(self, podcast_guid: str) -> str:
        """Ensure a podcast's directory exists and return its path."""
        podcast_dir = self.get_podcast_dir(podcast_guid)
        os.makedirs(podcast_dir, exist_ok=True)
        return podcast_dir

    def ensure_base_dirs_exist(self) -> None:
        """Ensure all base directories exist."""
        os.makedirs(self.base_data_dir, exist_ok=True)
        podcasts_dir = os.path.join(self.base_data_dir, "podcasts")
        os.makedirs(podcasts_dir, exist_ok=True)