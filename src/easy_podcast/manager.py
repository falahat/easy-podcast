"""
Main orchestration class for podcast management.
"""

import logging
import os
from typing import List, Optional, Tuple

from .file_manager import FileManager
from .models import Episode, Podcast
from .parser import PodcastParser


class PodcastManager:
    """
    Orchestrates podcast data ingestion, metadata management,
    and episode downloads using simplified file management.
    """

    def __init__(self, podcast: Podcast, data_dir: str = "./data"):
        """Initialize with podcast and optional data directory."""
        self.logger = logging.getLogger(__name__)
        self.podcast: Podcast = podcast
        self.data_dir = data_dir

        # Initialize simplified file manager
        self.file_manager = FileManager(data_dir)

        self.logger.info(
            "Initializing PodcastManager for podcast: '%s'", self.podcast.title
        )
        self.logger.info("Data directory: %s", data_dir)

        # Ensure podcast directory exists
        self.file_manager.ensure_podcast_dir_exists(self.podcast.title)

        # Log some statistics about audio files
        episodes_with_audio = [
            ep for ep in self.podcast.episodes if self.episode_audio_exists(ep)
        ]
        self.logger.info(
            "Found %d episodes with existing audio files",
            len(episodes_with_audio),
        )

    def episode_audio_exists(self, episode: Episode) -> bool:
        """Check if an episode's audio file exists."""
        audio_path = self.file_manager.get_episode_audio_path(
            self.podcast.title, episode
        )
        return os.path.exists(audio_path)

    def get_episode_audio_path(self, episode: Episode) -> str:
        """Get the full path to an episode's audio file."""
        return self.file_manager.get_episode_audio_path(
            self.podcast.title, episode
        )

    def get_episode_transcript_path(self, episode: Episode) -> str:
        """Get the full path to an episode's transcript file."""
        return self.file_manager.get_episode_transcript_path(
            self.podcast.title, episode
        )

    def episode_transcript_exists(self, episode: Episode) -> bool:
        """Check if an episode's transcript file exists."""
        transcript_path = self.get_episode_transcript_path(episode)
        return os.path.exists(transcript_path)

    def get_existing_episode_ids(self) -> set[str]:
        """Get set of episode IDs that have been downloaded."""
        episodes = self.file_manager.load_episodes(self.podcast.title)
        downloaded_ids = set()

        for episode in episodes:
            # Check if the audio file actually exists
            if self.episode_audio_exists(episode):
                downloaded_ids.add(episode.id)

        return downloaded_ids

    def get_podcast(self) -> Podcast:
        """Get currently loaded podcast."""
        return self.podcast

    def get_podcast_data_dir(self) -> str:
        """Get the data directory for this podcast."""
        return self.file_manager.get_podcast_dir(self.podcast.title)

    @staticmethod
    def from_podcast_folder(
        podcast_title: str, data_dir: str = "./data"
    ) -> Optional["PodcastManager"]:
        """Create a manager from an existing podcast folder."""
        logger = logging.getLogger(__name__)
        logger.info("Loading podcast from folder: %s", podcast_title)

        try:
            file_manager = FileManager(data_dir)

            # Load podcast metadata
            podcast = file_manager.load_podcast_metadata(podcast_title)
            if not podcast:
                logger.error("Podcast not found: %s", podcast_title)
                return None

            # Load existing episodes
            episodes = file_manager.load_episodes(podcast_title)
            podcast.episodes = episodes

            logger.info(
                "Loaded podcast '%s' with %d episodes from storage",
                podcast.title,
                len(podcast.episodes),
            )

            # Create PodcastManager instance
            manager = PodcastManager(podcast, data_dir)
            return manager
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Failed to load podcast from storage: %s", e)
            return None

    @staticmethod
    def from_rss_url(
        rss_url: str, data_dir: str = "./data"
    ) -> Optional["PodcastManager"]:
        """Create a manager by downloading and parsing an RSS feed."""
        logger = logging.getLogger(__name__)
        logger.info("Creating PodcastManager from RSS URL: %s", rss_url)

        # Import here to avoid circular dependency
        from .downloader import download_rss_from_url

        # Download RSS content
        rss_content = download_rss_from_url(rss_url)
        if not rss_content:
            logger.error("Failed to download RSS content from %s", rss_url)
            return None

        # Parse RSS content
        parser = PodcastParser()
        podcast = parser.from_content(rss_url, rss_content)

        if not podcast:
            logger.error("Failed to parse RSS from URL")
            return None

        logger.info(
            "Successfully parsed podcast: '%s' (safe_title: '%s')",
            podcast.title,
            podcast.safe_title,
        )

        # Create PodcastManager instance
        try:
            manager = PodcastManager(podcast, data_dir)

            # Save podcast metadata, episodes, and RSS cache
            manager.file_manager.save_podcast_metadata(podcast)
            manager.file_manager.save_episodes(podcast.title, podcast.episodes)
            manager.file_manager.save_rss_cache(podcast.title, rss_content)

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
        existing_ids = self.get_existing_episode_ids()
        new_episodes = [
            ep for ep in self.podcast.episodes if ep.id not in existing_ids
        ]

        self.logger.info(
            "Found %d new episodes out of %d total episodes",
            len(new_episodes),
            len(self.podcast.episodes),
        )

        return new_episodes

    # Download Management
    def download_episodes(
        self, episodes: List[Episode]
    ) -> Tuple[int, int, int]:
        """Download multiple episodes with progress tracking.

        Returns:
            Tuple of (successful_downloads, skipped_files, failed_downloads).
        """
        successful_count = 0
        skipped_count = 0
        failed_count = 0

        for episode in episodes:
            try:
                download_path, was_downloaded = self.download_episode(episode)
                if download_path:
                    if was_downloaded:
                        successful_count += 1
                    else:
                        skipped_count += 1
                else:
                    failed_count += 1
            except Exception as e:  # pylint: disable=broad-except
                self.logger.error(
                    "Failed to download episode %s: %s", episode.id, e
                )
                failed_count += 1

        self.logger.info(
            "Download results: %d successful, %d skipped, %d failed",
            successful_count,
            skipped_count,
            failed_count,
        )

        return successful_count, skipped_count, failed_count

    def download_episode(self, episode: Episode) -> Tuple[Optional[str], bool]:
        """Download single episode file."""
        # Get the target download path
        download_path = self.file_manager.get_episode_audio_path(
            self.podcast.title, episode
        )

        # Check if file already exists
        if os.path.exists(download_path):
            self.logger.info(
                "Audio file already exists for episode %s: %s",
                episode.id,
                download_path,
            )
            return download_path, False

        # Download the episode
        try:
            # Import here to avoid circular dependency
            from .downloader import download_file_to_path

            _, success = download_file_to_path(
                episode.audio_link, download_path
            )
            if success:
                # Save episodes to JSONL (append or update)
                episodes = self.file_manager.load_episodes(self.podcast.title)
                # Remove existing episode if it exists
                episodes = [ep for ep in episodes if ep.id != episode.id]
                episodes.append(episode)
                self.file_manager.save_episodes(self.podcast.title, episodes)

                self.logger.debug("Saved metadata for episode %s", episode.id)
                return download_path, True
            else:
                self.logger.error("Failed to download episode %s", episode.id)
                return None, False
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error(
                "Error downloading episode %s: %s", episode.id, e
            )
            return None, False
