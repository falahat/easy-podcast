"""
Main orchestration class for podcast management.
"""

import logging
import os
from typing import List, Optional, Tuple

from .path_manager import PathManager, get_base_data_dir
from .downloader import download_episode_file
from .mapping_manager import MappingManager
from .models import Episode, Podcast
from .parser import PodcastParser
from .storage_manager import StorageManager


class PodcastManager:
    """
    Orchestrates podcast data ingestion, metadata management,
    and episode downloads using the new nested storage system.
    """

    def __init__(self, base_data_dir: str, podcast: Podcast):
        """Initialize with base data directory and podcast object."""
        self.logger = logging.getLogger(__name__)
        self.podcast: Podcast = podcast
        self.base_data_dir = base_data_dir

        # Initialize new storage system components
        self.mapping_manager = MappingManager(base_data_dir)
        self.path_manager = PathManager(base_data_dir, self.mapping_manager)
        self.storage_manager = StorageManager(self.path_manager)

        # Ensure the podcast has a valid GUID
        if not getattr(self.podcast, 'guid', None):
            self.podcast.guid = self.podcast.rss_url

        # Add podcast to mapping manager
        self.mapping_manager.add_podcast(self.podcast.guid, self.podcast.title)

        # Add all episodes to mapping manager
        for episode in self.podcast.episodes:
            if not getattr(episode, 'guid', None):
                episode.guid = episode.id  # Fallback for compatibility
            self.mapping_manager.add_episode(
                self.podcast.guid, episode.guid, episode.title
            )

        self.logger.info(
            "Initializing PodcastManager for podcast: '%s'", self.podcast.title
        )
        self.logger.info("Base data directory: %s", base_data_dir)

        # Ensure base directories exist
        self.path_manager.ensure_base_dirs_exist()
        self.path_manager.ensure_podcast_dir_exists(self.podcast.guid)

        # Log some statistics about audio files
        episodes_with_audio = [
            ep
            for ep in self.podcast.episodes
            if self.episode_audio_exists(ep)
        ]
        self.logger.info(
            "Found %d episodes with existing audio files",
            len(episodes_with_audio),
        )

    def episode_audio_exists(self, episode: Episode) -> bool:
        """Check if an episode's audio file exists."""
        audio_path = self.path_manager.get_episode_audio_path(
            episode, self.podcast.guid
        )
        return os.path.exists(audio_path)

    def get_episode_audio_path(self, episode: Episode) -> str:
        """Get the full path to an episode's audio file."""
        return self.path_manager.get_episode_audio_path(
            episode, self.podcast.guid
        )

    def get_episode_transcript_path(self, episode: Episode) -> str:
        """Get the full path to an episode's transcript file."""
        return self.path_manager.get_episode_transcript_path(
            episode, self.podcast.guid
        )

    def episode_transcript_exists(self, episode: Episode) -> bool:
        """Check if an episode's transcript file exists."""
        transcript_path = self.get_episode_transcript_path(episode)
        return os.path.exists(transcript_path)

    def get_existing_episode_ids(self) -> set[str]:
        """Get set of existing episode IDs using StorageManager."""
        episodes = self.storage_manager.list_podcast_episodes(
            self.podcast.guid
        )
        return {episode.id for episode in episodes}

    def get_podcast(self) -> Podcast:
        """Get currently loaded podcast."""
        return self.podcast

    def get_podcast_data_dir(self) -> str:
        """Get the data directory for this podcast."""
        return self.path_manager.get_podcast_dir(self.podcast.guid)

    @staticmethod
    def from_existing_storage(podcast_guid: str) -> Optional["PodcastManager"]:
        """Load podcast from existing new storage format."""
        logger = logging.getLogger(__name__)
        logger.info("Loading podcast from storage: %s", podcast_guid)

        try:
            # Get base data directory and set up storage components
            base_data_dir = get_base_data_dir()
            mapping_manager = MappingManager(base_data_dir)
            path_manager = PathManager(base_data_dir, mapping_manager)
            storage_manager = StorageManager(path_manager)

            # Load podcast metadata
            podcast = storage_manager.load_podcast_metadata(podcast_guid)
            if not podcast:
                logger.error("Podcast not found in storage: %s", podcast_guid)
                return None

            # Load existing episodes from storage (individual episode files)
            episodes = storage_manager.list_podcast_episodes(podcast_guid)
            
            # If no individual episode files found, use episodes from metadata
            if episodes:
                podcast.episodes = episodes
            else:
                logger.info(
                    "No individual episode files found, "
                    "using episodes from podcast metadata"
                )

            logger.info(
                "Loaded podcast '%s' with %d episodes from storage",
                podcast.title,
                len(podcast.episodes),
            )

            # Create PodcastManager instance
            manager = PodcastManager(base_data_dir, podcast)
            return manager
        except ValueError as e:
            logger.error("Invalid GUID or missing podcast: %s", e)
            return None
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Failed to load podcast from storage: %s", e)
            return None

    @staticmethod
    def from_rss_url(rss_url: str) -> Optional["PodcastManager"]:
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

        # Set up data directory structure using new storage system
        base_data_dir = get_base_data_dir()
        logger.info("Base data directory: %s", base_data_dir)

        # Create PodcastManager instance with new storage system
        try:
            manager = PodcastManager(base_data_dir, podcast)
            
            # Save podcast metadata and RSS cache in new format
            manager.storage_manager.save_podcast_metadata(podcast)
            manager.storage_manager.save_rss_cache(podcast.guid, rss_content)
            
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
            ep for ep in self.podcast.episodes
            if ep.id not in existing_ids
        ]
        
        self.logger.info(
            "Found %d new episodes out of %d total episodes",
            len(new_episodes),
            len(self.podcast.episodes),
        )
        
        return new_episodes

    def get_downloads_dir_for_episode(self, episode: Episode) -> str:
        """Get the downloads directory for a specific episode."""
        audio_path = self.path_manager.get_episode_audio_path(
            episode, self.podcast.guid
        )
        return os.path.dirname(audio_path)

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
            successful_count, skipped_count, failed_count
        )
        
        return successful_count, skipped_count, failed_count

    def download_episode(self, episode: Episode) -> Tuple[Optional[str], bool]:
        """Download single episode file."""
        # Ensure episode directory exists
        episode_dir = self.path_manager.ensure_episode_dir_exists(
            episode, self.podcast.guid
        )
        
        # Download to the episode's specific directory
        download_path, was_downloaded = download_episode_file(
            episode, episode_dir
        )

        if download_path and was_downloaded:
            # Save episode metadata
            self.storage_manager.save_episode_metadata(
                episode, self.podcast.guid
            )
            self.logger.debug("Saved metadata for episode %s", episode.id)

        return download_path, was_downloaded
