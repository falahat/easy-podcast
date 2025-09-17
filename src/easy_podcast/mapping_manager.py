"""
Manages GUID to folder name mappings for the new storage system.
"""

import json
import logging
import os
from typing import Dict, Set

from .utils import sanitize_filename


class MappingManager:
    """Manages GUID to folder name mappings."""

    def __init__(self, base_data_dir: str):
        """Initialize with base data directory."""
        self.base_data_dir = base_data_dir
        self.logger = logging.getLogger(__name__)
        
        # Mapping files
        self.rss_mapping_path = os.path.join(
            base_data_dir, "rss_to_podcast_mapping.json"
        )
        self.podcast_mappings_path = os.path.join(
            base_data_dir, "podcasts", "podcast_guid_mappings.json"
        )
        
        # In-memory mappings
        self.rss_to_podcast: Dict[str, str] = {}
        self.podcast_guid_to_folder: Dict[str, str] = {}
        # podcast_guid -> episode mappings
        self.episode_mappings: Dict[str, Dict[str, str]] = {}
        
        self.load_mappings()

    def get_podcast_folder(self, podcast_guid: str) -> str:
        """Get folder name for a podcast GUID."""
        if podcast_guid not in self.podcast_guid_to_folder:
            raise ValueError(f"Podcast GUID not found: {podcast_guid}")
        return self.podcast_guid_to_folder[podcast_guid]

    def get_episode_folder(self, podcast_guid: str, episode_guid: str) -> str:
        """Get folder name for an episode GUID within a podcast."""
        if podcast_guid not in self.episode_mappings:
            raise ValueError(
                f"No episode mappings for podcast: {podcast_guid}"
            )
        
        episode_mappings = self.episode_mappings[podcast_guid]
        if episode_guid not in episode_mappings:
            raise ValueError(f"Episode GUID not found: {episode_guid}")
        
        return episode_mappings[episode_guid]

    def add_podcast(self, podcast_guid: str, title: str) -> str:
        """Add a new podcast mapping and return the folder name."""
        sanitized_title = sanitize_filename(title)
        
        # Get existing podcast folder names to check for collisions
        existing_folders = set(self.podcast_guid_to_folder.values())
        folder_name = self.handle_collision(sanitized_title, existing_folders)
        
        self.podcast_guid_to_folder[podcast_guid] = folder_name
        # RSS URL is the GUID
        self.rss_to_podcast[podcast_guid] = podcast_guid
        
        self.logger.info(
            "Added podcast mapping: %s -> %s", podcast_guid, folder_name
        )
        self.save_mappings()
        
        return folder_name

    def add_episode(
        self, podcast_guid: str, episode_guid: str, title: str
    ) -> str:
        """Add a new episode mapping and return the folder name."""
        sanitized_title = sanitize_filename(title)
        
        # Initialize episode mappings for this podcast if not exists
        if podcast_guid not in self.episode_mappings:
            self.episode_mappings[podcast_guid] = {}
        
        # Get existing episode folder names for this podcast to check
        # for collisions
        existing_folders = set(self.episode_mappings[podcast_guid].values())
        folder_name = self.handle_collision(sanitized_title, existing_folders)
        
        self.episode_mappings[podcast_guid][episode_guid] = folder_name
        
        self.logger.info(
            "Added episode mapping for podcast %s: %s -> %s",
            podcast_guid, episode_guid, folder_name
        )
        self.save_episode_mappings(podcast_guid)
        
        return folder_name

    def load_mappings(self) -> None:
        """Load all mapping files."""
        self._load_rss_mappings()
        self._load_podcast_mappings()

    def _load_rss_mappings(self) -> None:
        """Load RSS to podcast GUID mappings."""
        if os.path.exists(self.rss_mapping_path):
            try:
                with open(self.rss_mapping_path, "r", encoding="utf-8") as f:
                    self.rss_to_podcast = json.load(f)
                self.logger.debug(
                    "Loaded %d RSS mappings", len(self.rss_to_podcast)
                )
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning("Failed to load RSS mappings: %s", e)
                self.rss_to_podcast = {}

    def _load_podcast_mappings(self) -> None:
        """Load podcast GUID to folder mappings."""
        if os.path.exists(self.podcast_mappings_path):
            try:
                with open(
                    self.podcast_mappings_path, "r", encoding="utf-8"
                ) as f:
                    self.podcast_guid_to_folder = json.load(f)
                self.logger.debug(
                    "Loaded %d podcast mappings",
                    len(self.podcast_guid_to_folder)
                )
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning("Failed to load podcast mappings: %s", e)
                self.podcast_guid_to_folder = {}

    def load_episode_mappings(self, podcast_guid: str) -> None:
        """Load episode mappings for a specific podcast."""
        podcast_folder = self.get_podcast_folder(podcast_guid)
        episodes_mapping_path = os.path.join(
            self.base_data_dir, "podcasts", podcast_folder,
            "episodes_guid_mappings.json"
        )
        
        if os.path.exists(episodes_mapping_path):
            try:
                with open(episodes_mapping_path, "r", encoding="utf-8") as f:
                    self.episode_mappings[podcast_guid] = json.load(f)
                self.logger.debug(
                    "Loaded %d episode mappings for podcast %s",
                    len(self.episode_mappings[podcast_guid]), podcast_guid
                )
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(
                    "Failed to load episode mappings for %s: %s",
                    podcast_guid, e
                )
                self.episode_mappings[podcast_guid] = {}
        else:
            self.episode_mappings[podcast_guid] = {}

    def save_mappings(self) -> None:
        """Save all mapping files."""
        self._save_rss_mappings()
        self._save_podcast_mappings()

    def _save_rss_mappings(self) -> None:
        """Save RSS to podcast GUID mappings."""
        os.makedirs(os.path.dirname(self.rss_mapping_path), exist_ok=True)
        try:
            with open(self.rss_mapping_path, "w", encoding="utf-8") as f:
                json.dump(self.rss_to_podcast, f, indent=2)
            self.logger.debug(
                "Saved RSS mappings to %s", self.rss_mapping_path
            )
        except IOError as e:
            self.logger.error("Failed to save RSS mappings: %s", e)

    def _save_podcast_mappings(self) -> None:
        """Save podcast GUID to folder mappings."""
        os.makedirs(os.path.dirname(self.podcast_mappings_path), exist_ok=True)
        try:
            with open(self.podcast_mappings_path, "w", encoding="utf-8") as f:
                json.dump(self.podcast_guid_to_folder, f, indent=2)
            self.logger.debug(
                "Saved podcast mappings to %s", self.podcast_mappings_path
            )
        except IOError as e:
            self.logger.error("Failed to save podcast mappings: %s", e)

    def save_episode_mappings(self, podcast_guid: str) -> None:
        """Save episode mappings for a specific podcast."""
        if podcast_guid not in self.episode_mappings:
            return
        
        podcast_folder = self.get_podcast_folder(podcast_guid)
        episodes_mapping_path = os.path.join(
            self.base_data_dir, "podcasts", podcast_folder,
            "episodes_guid_mappings.json"
        )
        
        os.makedirs(os.path.dirname(episodes_mapping_path), exist_ok=True)
        try:
            with open(episodes_mapping_path, "w", encoding="utf-8") as f:
                json.dump(self.episode_mappings[podcast_guid], f, indent=2)
            self.logger.debug(
                "Saved episode mappings for podcast %s to %s",
                podcast_guid, episodes_mapping_path
            )
        except IOError as e:
            self.logger.error(
                "Failed to save episode mappings for %s: %s",
                podcast_guid, e
            )

    def handle_collision(
        self, base_name: str, existing_names: Set[str]
    ) -> str:
        """Handle folder name collisions by appending numbers."""
        if base_name not in existing_names:
            return base_name
        
        counter = 1
        while f"{base_name}_{counter}" in existing_names:
            counter += 1
        
        return f"{base_name}_{counter}"

    def podcast_exists(self, podcast_guid: str) -> bool:
        """Check if a podcast GUID has a mapping."""
        return podcast_guid in self.podcast_guid_to_folder

    def episode_exists(self, podcast_guid: str, episode_guid: str) -> bool:
        """Check if an episode GUID has a mapping within a podcast."""
        return (podcast_guid in self.episode_mappings and
                episode_guid in self.episode_mappings[podcast_guid])