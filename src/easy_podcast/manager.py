"""
Main orchestration class for podcast management.
"""

import logging
import os
from typing import List, Optional, Tuple

from .config import get_config
from .downloader import download_episode_file
from .mapping_manager import MappingManager
from .models import Episode, Podcast
from .parser import PodcastParser
from .path_manager import PathManager
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
        """Get set of existing episode IDs by checking for metadata files."""
        existing_ids: set[str] = set()
        podcast_dir = self.path_manager.get_podcast_dir(self.podcast.guid)
        
        if not os.path.exists(podcast_dir):
            return existing_ids
            
        # Check each subdirectory for metadata.json files
        for item in os.listdir(podcast_dir):
            item_path = os.path.join(podcast_dir, item)
            if os.path.isdir(item_path):
                metadata_file = os.path.join(
                    item_path, self.path_manager.EPISODE_METADATA_FILE
                )
                if os.path.exists(metadata_file):
                    try:
                        # Read the metadata file directly to get episode ID
                        import json
                        with open(metadata_file, "r", encoding="utf-8") as f:
                            episode_data = json.load(f)
                            if "id" in episode_data:
                                existing_ids.add(episode_data["id"])
                    except Exception:  # pylint: disable=broad-except
                        # Skip invalid metadata files
                        continue
                        
        return existing_ids

    def get_podcast(self) -> Podcast:
        """Get currently loaded podcast."""
        return self.podcast

    @staticmethod
    def from_podcast_folder(
        podcast_data_dir: str,
    ) -> Optional["PodcastManager"]:
        """
        Create a manager from a folder with RSS and episode data.
        
        This method handles both old flat storage and new nested storage.
        For old storage, it will load from episodes.jsonl and rss.xml.
        For new storage, it will load from the nested structure.
        """
        logger = logging.getLogger(__name__)
        logger.info("Loading podcast data from folder: %s", podcast_data_dir)

        # Convert to absolute path for clearer logging
        abs_podcast_data_dir = os.path.abspath(podcast_data_dir)
        logger.info(
            "Absolute podcast data directory: %s", abs_podcast_data_dir
        )

        # Check if this is old-style storage (has episodes.jsonl)
        episodes_jsonl_path = os.path.join(podcast_data_dir, "episodes.jsonl")
        rss_file_path = os.path.join(podcast_data_dir, "rss.xml")

        if os.path.exists(episodes_jsonl_path):
            logger.info("Detected old-style storage, loading from JSONL")
            return PodcastManager._load_from_old_storage(
                podcast_data_dir, rss_file_path
            )
        else:
            logger.error(
                "New-style storage loading not yet implemented. "
                "Use migration utilities to convert old storage first."
            )
            return None

    @staticmethod
    def _load_from_old_storage(
        podcast_data_dir: str, rss_file_path: str
    ) -> Optional["PodcastManager"]:
        """Load podcast from old JSONL-based storage."""
        logger = logging.getLogger(__name__)
        
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

        # For old storage, we need to determine the base data directory
        # The podcast_data_dir is the old podcast folder
        # We need its parent directory as the base data directory
        base_data_dir = os.path.dirname(podcast_data_dir)

        # Create PodcastManager instance with new storage system
        try:
            manager = PodcastManager(base_data_dir, podcast)
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

        # Set up data directory structure using new storage system
        config = get_config()
        base_data_dir = config.base_data_dir  # Use the base data directory
        
        logger.info("Base data directory: %s", base_data_dir)

        # Create PodcastManager instance with new storage system
        try:
            manager = PodcastManager(base_data_dir, podcast)
            
            # Save podcast metadata in new format
            manager.storage_manager.save_podcast_metadata(podcast)
            
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
