"""
Main orchestration class for podcast management.
"""

import logging
import os
from typing import List, Optional, Tuple

from .config import get_config
from .downloader import download_episode_file, download_episodes_batch
from .episode_tracker import EpisodeTracker
from .models import Episode, Podcast
from .parser import PodcastParser


class PodcastManager:
    """
    Orchestrates podcast data ingestion, metadata management,
    and episode downloads.
    """

    def __init__(self, podcast_data_dir: str, podcast: Podcast):
        """Initialize with data directory and podcast object."""
        self.logger = logging.getLogger(__name__)
        self.podcast: Podcast = podcast
        self.downloads_dir: str = os.path.join(podcast_data_dir, "downloads")

        # Initialize episode tracker
        episodes_file_path = os.path.join(podcast_data_dir, "episodes.jsonl")
        self.episode_tracker: EpisodeTracker = EpisodeTracker(
            episodes_file_path, self.downloads_dir
        )

        self.logger.info(
            "Initializing PodcastManager for podcast: '%s'", self.podcast.title
        )
        self.logger.info("Podcast data directory: %s", podcast_data_dir)
        self.logger.info("Downloads directory: %s", self.downloads_dir)

        # Ensure downloads directory exists
        os.makedirs(self.downloads_dir, exist_ok=True)
        self.logger.debug(
            "Created/verified downloads directory exists: %s",
            self.downloads_dir,
        )

        # Log some statistics about audio files
        episodes_with_audio = [
            ep
            for ep in self.podcast.episodes
            if self.episode_tracker.episode_audio_exists(ep)
        ]
        self.logger.info(
            "Found %d episodes with existing audio files",
            len(episodes_with_audio),
        )

    def get_podcast(self) -> Podcast:
        """Get currently loaded podcast."""
        return self.podcast

    @staticmethod
    def from_podcast_folder(
        podcast_data_dir: str,
    ) -> Optional["PodcastManager"]:
        """
        Create a manager from a folder with RSS and episode data.

        Note: episode.audio_file contains only filenames (e.g., "727175.mp3").
        Use episode_tracker.get_episode_audio_path() to get full paths.
        """
        logger = logging.getLogger(__name__)
        logger.info("Loading podcast data from folder: %s", podcast_data_dir)

        # Convert to absolute path for clearer logging
        abs_podcast_data_dir = os.path.abspath(podcast_data_dir)
        logger.info(
            "Absolute podcast data directory: %s", abs_podcast_data_dir
        )

        rss_file_path = os.path.join(podcast_data_dir, "rss.xml")

        logger.debug("Looking for RSS file at: %s", rss_file_path)

        if not os.path.exists(rss_file_path):
            logger.error("RSS file not found: %s", rss_file_path)
            return None

        logger.info("Found RSS file: %s", rss_file_path)

        # Parse RSS file
        logger.info("Parsing RSS file...")
        parser = PodcastParser()
        podcast = parser.from_file("", rss_file_path)
        if not podcast:
            logger.error("Failed to parse RSS file: %s", rss_file_path)
            return None

        logger.info(
            "Successfully parsed podcast: '%s' (safe_title: '%s')",
            podcast.title,
            podcast.safe_title,
        )

        # Create PodcastManager instance
        try:
            manager = PodcastManager(podcast_data_dir, podcast)
            logger.info(
                "Successfully created PodcastManager for podcast '%s' from %s",
                podcast.title,
                podcast_data_dir,
            )
            return manager
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Failed to create PodcastManager: %s", e)
            return None

    @staticmethod
    def from_rss_url(rss_url: str) -> Optional["PodcastManager"]:
        """Create a manager by downloading and parsing an RSS feed."""
        logger = logging.getLogger(__name__)
        logger.info("Creating PodcastManager from RSS URL: %s", rss_url)

        # Use PodcastParser to download and parse RSS
        parser = PodcastParser()
        podcast = parser.from_rss_url(rss_url)

        if not podcast:
            logger.error("Failed to download and parse RSS from URL")
            return None

        logger.info(
            "Successfully parsed podcast: '%s' (safe_title: '%s')",
            podcast.title,
            podcast.safe_title,
        )

        # Set up podcast data directory structure
        config = get_config()
        podcast_data_dir = config.get_podcast_data_dir_from_safe_title(
            podcast.safe_title
        )
        rss_file_path = config.get_rss_file_path_from_safe_title(
            podcast.safe_title
        )

        logger.info("Setting up podcast data directory: %s", podcast_data_dir)
        logger.info("RSS file will be saved to: %s", rss_file_path)

        os.makedirs(podcast_data_dir, exist_ok=True)
        logger.debug(
            "Created/verified podcast data directory: %s", podcast_data_dir
        )

        # Create PodcastManager instance
        try:
            manager = PodcastManager(podcast_data_dir, podcast)
            logger.info(
                "Successfully created PodcastManager for '%s' from RSS URL",
                podcast.title,
            )
            return manager
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Failed to create PodcastManager: %s", e)
            return None

    # Episode Discovery
    def get_new_episodes(self) -> List[Episode]:
        """Get episodes that haven't been downloaded yet."""
        return self.episode_tracker.get_new_episodes(self.podcast.episodes)

    # Download Management
    def download_episodes(
        self, episodes: List[Episode], show_progress: bool = True
    ) -> Tuple[int, int, int]:
        """Download multiple episodes with progress tracking.

        Returns:
            Tuple of (successful_downloads, skipped_files, failed_downloads).
        """
        # Use downloader for batch download
        result = download_episodes_batch(
            episodes, self.downloads_dir, show_progress
        )
        successful_count, skipped_count, failed_count = result

        # Add successfully downloaded episodes to tracker
        added_to_tracker = 0
        for episode in episodes:
            if self.episode_tracker.episode_audio_exists(episode):
                self.episode_tracker.add_episode(episode)
                added_to_tracker += 1

        self.logger.info("Added %d episodes to tracker", added_to_tracker)
        return successful_count, skipped_count, failed_count

    def download_episode(self, episode: Episode) -> Tuple[Optional[str], bool]:
        """Download single episode file."""
        download_path, was_downloaded = download_episode_file(
            episode, self.downloads_dir
        )

        if download_path and was_downloaded:
            self.episode_tracker.add_episode(episode)
            self.logger.debug("Added episode %s to tracker", episode.id)

        return download_path, was_downloaded
