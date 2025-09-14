"""
Configuration settings for the podcast package.

This module provides centralized configuration management for directories,
file paths, and other settings used throughout the podcast package.
"""

import os
from typing import Optional


class PodcastConfig:
    """Centralized configuration for the podcast package."""

    # Default base directory for all podcast data
    DEFAULT_BASE_DATA_DIR = "data"

    # Default downloads subdirectory name
    DOWNLOADS_SUBDIR = "downloads"

    # Default episodes metadata file name
    EPISODES_FILE = "episodes.jsonl"

    # Default RSS file name
    RSS_FILE = "rss.xml"

    # Default transcript file suffix
    TRANSCRIPT_SUFFIX = "_transcript.txt"

    def __init__(self, base_data_dir: Optional[str] = None):
        """Initialize configuration with optional base data directory."""
        self._base_data_dir = base_data_dir or self.DEFAULT_BASE_DATA_DIR

    @property
    def base_data_dir(self) -> str:
        """Get the base data directory path."""
        return self._base_data_dir

    @base_data_dir.setter
    def base_data_dir(self, value: str) -> None:
        """Set the base data directory path."""
        self._base_data_dir = value

    def get_podcast_data_dir(self, podcast_title: str) -> str:
        """
        Get the data directory path for a specific podcast.

        Args:
            podcast_title: The sanitized title of the podcast

        Returns:
            The full path to the podcast's data directory
        """
        return os.path.join(self.base_data_dir, podcast_title)

    def get_podcast_data_dir_from_safe_title(self, safe_title: str) -> str:
        """Get podcast data directory path using safe title."""
        return os.path.join(self.base_data_dir, safe_title)

    def get_downloads_dir_from_safe_title(self, safe_title: str) -> str:
        """Get downloads directory path using safe title."""
        podcast_data_dir = self.get_podcast_data_dir_from_safe_title(
            safe_title
        )
        return os.path.join(podcast_data_dir, self.DOWNLOADS_SUBDIR)

    def get_episodes_file_path_from_safe_title(self, safe_title: str) -> str:
        """
        Get the episodes metadata file path for a podcast using its safe title.

        Args:
            safe_title: The sanitized title of the podcast

        Returns:
            The full path to the episodes.jsonl file
        """
        podcast_data_dir = self.get_podcast_data_dir_from_safe_title(
            safe_title
        )
        return os.path.join(podcast_data_dir, self.EPISODES_FILE)

    def get_rss_file_path_from_safe_title(self, safe_title: str) -> str:
        """
        Get the RSS file path for a podcast using its safe title.

        Args:
            safe_title: The sanitized title of the podcast

        Returns:
            The full path to the rss.xml file
        """
        podcast_data_dir = self.get_podcast_data_dir_from_safe_title(
            safe_title
        )
        return os.path.join(podcast_data_dir, self.RSS_FILE)

    def get_downloads_dir(self, podcast_data_dir: str) -> str:
        """
        Get the downloads directory path for a podcast.

        Args:
            podcast_data_dir: The podcast's data directory

        Returns:
            The full path to the podcast's downloads directory
        """
        return os.path.join(podcast_data_dir, self.DOWNLOADS_SUBDIR)

    def get_episodes_file_path(self, podcast_data_dir: str) -> str:
        """
        Get the episodes metadata file path for a podcast.

        Args:
            podcast_data_dir: The podcast's data directory

        Returns:
            The full path to the episodes.jsonl file
        """
        return os.path.join(podcast_data_dir, self.EPISODES_FILE)

    def get_rss_file_path(self, podcast_data_dir: str) -> str:
        """
        Get the RSS file path for a podcast.

        Args:
            podcast_data_dir: The podcast's data directory

        Returns:
            The full path to the rss.xml file
        """
        return os.path.join(podcast_data_dir, self.RSS_FILE)

    def get_transcript_filename(self, audio_filename: str) -> str:
        """
        Get the transcript filename for an audio file.

        Args:
            audio_filename: The audio file name (e.g., "episode.mp3")

        Returns:
            The transcript filename (e.g., "episode_transcript.txt")
        """
        name_without_ext = os.path.splitext(audio_filename)[0]
        return f"{name_without_ext}{self.TRANSCRIPT_SUFFIX}"


# Global configuration instance
config = PodcastConfig()


def get_config() -> PodcastConfig:
    """Get the global configuration instance."""
    return config


def set_base_data_dir(base_data_dir: str) -> None:
    """Set the global base data directory."""
    config.base_data_dir = base_data_dir


def get_base_data_dir() -> str:
    """Get the global base data directory."""
    return config.base_data_dir
