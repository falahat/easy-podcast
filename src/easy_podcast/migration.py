"""
Migration utilities for converting old flat storage to new nested structure.
"""

import json
import logging
import os
import shutil
from typing import Dict, List, Optional

from .mapping_manager import MappingManager
from .models import Episode, Podcast
from .path_manager import PathManager
from .storage_manager import StorageManager


class StorageMigrator:
    """Migrates old flat storage structure to new nested structure."""

    def __init__(self, base_data_dir: str):
        """Initialize migrator with base data directory."""
        self.base_data_dir = base_data_dir
        self.logger = logging.getLogger(__name__)
        
        # Initialize the new storage system components
        self.mapping_manager = MappingManager(base_data_dir)
        self.path_manager = PathManager(base_data_dir, self.mapping_manager)
        self.storage_manager = StorageManager(self.path_manager)

    def migrate_all_podcasts(self) -> Dict[str, str]:
        """Migrate all podcasts from old to new storage format.
        
        Returns:
            Dict mapping RSS URLs to new podcast GUIDs
        """
        old_podcasts = self._discover_old_podcasts()
        rss_to_guid_mapping = {}
        
        self.logger.info("Found %d old podcasts to migrate", len(old_podcasts))
        
        for old_podcast_dir in old_podcasts:
            try:
                rss_url, podcast_guid = self._migrate_podcast(old_podcast_dir)
                if rss_url and podcast_guid:
                    rss_to_guid_mapping[rss_url] = podcast_guid
                    self.logger.info(
                        "Successfully migrated podcast: %s", old_podcast_dir
                    )
            except Exception as e:  # pylint: disable=broad-except
                self.logger.error(
                    "Failed to migrate podcast %s: %s", old_podcast_dir, e
                )
        
        # Save the RSS URL to GUID mapping
        self.storage_manager.save_rss_to_podcast_mapping(rss_to_guid_mapping)
        
        return rss_to_guid_mapping

    def _discover_old_podcasts(self) -> List[str]:
        """Discover old podcast directories in the data folder."""
        old_podcasts: List[str] = []
        
        if not os.path.exists(self.base_data_dir):
            return old_podcasts
            
        for item in os.listdir(self.base_data_dir):
            item_path = os.path.join(self.base_data_dir, item)
            if os.path.isdir(item_path) and item != "podcasts":
                # Check if this looks like an old podcast directory
                episodes_file = os.path.join(item_path, "episodes.jsonl")
                if os.path.exists(episodes_file):
                    old_podcasts.append(item_path)
                    
        return old_podcasts

    def _migrate_podcast(self, old_podcast_dir: str) -> tuple[str, str]:
        """Migrate a single podcast from old to new format.
        
        Returns:
            Tuple of (rss_url, podcast_guid)
        """
        # Try to extract RSS URL from rss.xml file
        rss_file = os.path.join(old_podcast_dir, "rss.xml")
        rss_url = self._extract_rss_url_from_file(rss_file)
        
        if not rss_url:
            # Use the directory name as fallback
            podcast_name = os.path.basename(old_podcast_dir)
            rss_url = f"file://{podcast_name}"
            
        # Create podcast GUID (using RSS URL for now)
        podcast_guid = rss_url
        
        # Create podcast object
        podcast_name = os.path.basename(old_podcast_dir)
        podcast = Podcast(
            title=podcast_name,
            rss_url=rss_url,
            safe_title=podcast_name,
            guid=podcast_guid,
        )
        
        # Add podcast to mapping manager
        self.mapping_manager.add_podcast(podcast_guid, podcast_name)
        
        # Migrate episodes
        episodes = self._load_old_episodes(old_podcast_dir)
        for episode in episodes:
            # Add GUID field if missing (use the id for now)
            if not episode.guid:
                episode.guid = episode.id
                
            # Add episode to mapping manager
            self.mapping_manager.add_episode(
                podcast_guid, episode.guid, episode.title
            )
            
            # Save episode metadata in new format
            self.storage_manager.save_episode_metadata(episode, podcast_guid)
            
            # Migrate audio file if it exists
            self._migrate_episode_audio_file(
                old_podcast_dir, episode, podcast_guid
            )
        
        # Save podcast metadata
        self.storage_manager.save_podcast_metadata(podcast)
        
        self.logger.info(
            "Migrated podcast '%s' with %d episodes",
            podcast_name, len(episodes)
        )
        
        return rss_url, podcast_guid

    def _extract_rss_url_from_file(self, rss_file_path: str) -> Optional[str]:
        """Try to extract the original RSS URL from RSS file."""
        if not os.path.exists(rss_file_path):
            return None
            
        try:
            # This is a simplified extraction - in practice we might need
            # to parse the XML to find the RSS URL in metadata or comments
            # For now, we'll return None to use fallback logic
            return None
        except Exception:  # pylint: disable=broad-except
            return None

    def _load_old_episodes(self, old_podcast_dir: str) -> List[Episode]:
        """Load episodes from old JSONL format."""
        episodes: List[Episode] = []
        episodes_file = os.path.join(old_podcast_dir, "episodes.jsonl")
        
        if not os.path.exists(episodes_file):
            return episodes
            
        with open(episodes_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    if line.strip():
                        episode_data = json.loads(line)
                        episode = Episode.from_dict(episode_data)
                        episodes.append(episode)
                except (json.JSONDecodeError, TypeError) as e:
                    self.logger.warning(
                        "Skipping invalid episode line %d: %s", line_num, e
                    )
                    
        return episodes

    def _migrate_episode_audio_file(
        self, old_podcast_dir: str, episode: Episode, podcast_guid: str
    ) -> None:
        """Migrate episode audio file from old to new location."""
        old_downloads_dir = os.path.join(old_podcast_dir, "downloads")
        old_audio_file = os.path.join(
            old_downloads_dir, episode.audio_filename
        )
        
        if os.path.exists(old_audio_file):
            # Get new audio file path
            new_audio_path = self.path_manager.get_episode_audio_path(
                episode, podcast_guid
            )
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(new_audio_path), exist_ok=True)
            
            # Copy the file
            shutil.copy2(old_audio_file, new_audio_path)
            self.logger.debug(
                "Migrated audio file: %s -> %s",
                old_audio_file, new_audio_path
            )

    def cleanup_old_storage(self, confirm: bool = False) -> None:
        """Remove old storage directories after successful migration.
        
        Args:
            confirm: If True, actually delete the directories
        """
        if not confirm:
            self.logger.warning(
                "cleanup_old_storage called without confirm=True. "
                "No directories will be deleted."
            )
            return
            
        old_podcasts = self._discover_old_podcasts()
        
        for old_podcast_dir in old_podcasts:
            try:
                shutil.rmtree(old_podcast_dir)
                self.logger.info(
                    "Removed old podcast directory: %s", old_podcast_dir
                )
            except Exception as e:  # pylint: disable=broad-except
                self.logger.error(
                    "Failed to remove old directory %s: %s",
                    old_podcast_dir, e
                )