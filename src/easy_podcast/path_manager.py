"""
Centralized authority for all file and directory paths in new storage system.
"""

import json
import logging
import os
from typing import TYPE_CHECKING, Dict, Set, Optional

if TYPE_CHECKING:
    from .models import Episode

from .utils import sanitize_filename


class PathManager:
    """Centralized authority for all file and directory paths."""

    # Configuration constants (moved from PodcastConfig)
    DEFAULT_BASE_DATA_DIR = os.getenv("PODCAST_DATA_DIRECTORY", "./data")
    TRANSCRIPT_SUFFIX = "_transcript.txt"

    # Standard file names
    RSS_TO_PODCAST_MAPPING_FILE = "rss_to_podcast_mapping.json"
    PODCAST_GUID_MAPPINGS_FILE = "podcast_guid_mappings.json"
    EPISODES_GUID_MAPPINGS_FILE = "episodes_guid_mappings.json"
    PODCAST_METADATA_FILE = "podcast_metadata.json"
    EPISODE_METADATA_FILE = "metadata.json"
    AUDIO_FILE = "audio.mp3"
    TRANSCRIPT_FILE = "transcript.txt"
    RSS_CACHE_FILE = "rss.xml"

    def __init__(
        self,
        base_data_dir: Optional[str] = None,
    ):
        """Initialize with optional base data directory."""
        self.base_data_dir = base_data_dir or self.DEFAULT_BASE_DATA_DIR
        self.logger = logging.getLogger(__name__)
        
        # In-memory mappings (from MappingManager)
        self.rss_to_podcast: Dict[str, str] = {}
        self.podcast_guid_to_folder: Dict[str, str] = {}
        # podcast_guid -> episode mappings
        self.episode_mappings: Dict[str, Dict[str, str]] = {}
        
        self.load_mappings()

    # Mapping methods (from MappingManager)
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

    def load_mappings(self) -> None:
        """Load all mapping files."""
        self._load_rss_mappings()
        self._load_podcast_mappings()

    def _load_rss_mappings(self) -> None:
        """Load RSS to podcast GUID mappings."""
        rss_mapping_path = self.get_rss_mapping_path()
        try:
            with open(rss_mapping_path, "r", encoding="utf-8") as f:
                self.rss_to_podcast = json.load(f)
            self.logger.debug(
                "Loaded %d RSS mappings", len(self.rss_to_podcast)
            )
        except (json.JSONDecodeError, IOError, FileNotFoundError) as e:
            self.logger.warning("Failed to load RSS mappings: %s", e)
            self.rss_to_podcast = {}

    def _load_podcast_mappings(self) -> None:
        """Load podcast GUID to folder mappings."""
        podcast_mappings_path = self.get_podcast_mappings_path()
        try:
            with open(podcast_mappings_path, "r", encoding="utf-8") as f:
                self.podcast_guid_to_folder = json.load(f)
            self.logger.debug(
                "Loaded %d podcast mappings",
                len(self.podcast_guid_to_folder)
            )
        except (json.JSONDecodeError, IOError, FileNotFoundError) as e:
            self.logger.warning("Failed to load podcast mappings: %s", e)
            self.podcast_guid_to_folder = {}

    def load_episode_mappings(self, podcast_guid: str) -> None:
        """Load episode mappings for a specific podcast."""
        episodes_mapping_path = self.get_episode_mappings_path(
            podcast_guid
        )
        
        try:
            with open(episodes_mapping_path, "r", encoding="utf-8") as f:
                self.episode_mappings[podcast_guid] = json.load(f)
            self.logger.debug(
                "Loaded %d episode mappings for podcast %s",
                len(self.episode_mappings[podcast_guid]), podcast_guid
            )
        except (json.JSONDecodeError, IOError, FileNotFoundError) as e:
            self.logger.warning(
                "Failed to load episode mappings for %s: %s",
                podcast_guid, e
            )
            self.episode_mappings[podcast_guid] = {}

    def save_mappings(self) -> None:
        """Save all mapping files."""
        self._save_rss_mappings()
        self._save_podcast_mappings()

    def _save_rss_mappings(self) -> None:
        """Save RSS to podcast GUID mappings."""
        rss_mapping_path = self.get_rss_mapping_path()
        # Ensure base directories exist using path_manager
        self.ensure_base_dirs_exist()
        try:
            with open(rss_mapping_path, "w", encoding="utf-8") as f:
                json.dump(self.rss_to_podcast, f, indent=2)
            self.logger.debug(
                "Saved RSS mappings to %s", rss_mapping_path
            )
        except IOError as e:
            self.logger.error("Failed to save RSS mappings: %s", e)

    def _save_podcast_mappings(self) -> None:
        """Save podcast GUID to folder mappings."""
        podcast_mappings_path = self.get_podcast_mappings_path()
        # Ensure base directories exist using path_manager
        self.ensure_base_dirs_exist()
        try:
            with open(podcast_mappings_path, "w", encoding="utf-8") as f:
                json.dump(self.podcast_guid_to_folder, f, indent=2)
            self.logger.debug(
                "Saved podcast mappings to %s", podcast_mappings_path
            )
        except IOError as e:
            self.logger.error("Failed to save podcast mappings: %s", e)

    def save_episode_mappings(self, podcast_guid: str) -> None:
        """Save episode mappings for a specific podcast."""
        if podcast_guid not in self.episode_mappings:
            return
        
        episodes_mapping_path = self.get_episode_mappings_path(
            podcast_guid
        )
        
        # Ensure the podcast directory exists
        self.ensure_podcast_dir_exists(podcast_guid)
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

    # Path methods (existing functionality)

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
        episode_folder = self.get_episode_folder(
            podcast_guid, episode_identifier
        )
        return os.path.join(podcast_dir, episode_folder)

    def get_podcast_dir(self, podcast_guid: str) -> str:
        """Get the full path to a podcast's directory."""
        podcasts_dir = os.path.join(self.base_data_dir, "podcasts")
        podcast_folder = self.get_podcast_folder(podcast_guid)
        return os.path.join(podcasts_dir, podcast_folder)

    def get_podcast_metadata_path(self, podcast_guid: str) -> str:
        """Get the full path to a podcast's metadata file."""
        podcast_dir = self.get_podcast_dir(podcast_guid)
        return os.path.join(podcast_dir, self.PODCAST_METADATA_FILE)

    def get_podcast_rss_cache_path(self, podcast_guid: str) -> str:
        """Get the full path to a podcast's RSS cache file."""
        podcast_dir = self.get_podcast_dir(podcast_guid)
        return os.path.join(podcast_dir, self.RSS_CACHE_FILE)

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

    def get_transcript_filename(self, audio_filename: str) -> str:
        """Get transcript filename for an audio file."""
        name_without_ext = os.path.splitext(audio_filename)[0]
        return f"{name_without_ext}{self.TRANSCRIPT_SUFFIX}"


# Global path manager instance (replaces global config)
_global_path_manager = None


def get_path_manager() -> PathManager:
    """Get the global path manager instance.
    
    Note: This function will be deprecated in favor of explicit
    PathManager instances. Only use during transition period.
    """
    # pylint: disable=global-statement
    global _global_path_manager
    if _global_path_manager is None:
        base_data_dir = PathManager.DEFAULT_BASE_DATA_DIR
        _global_path_manager = PathManager(base_data_dir)
    return _global_path_manager


# Compatibility functions for old config system (deprecated)
def set_base_data_dir(base_data_dir: str) -> None:
    """Set the global base data directory (deprecated).
    
    This function is provided for backward compatibility with tests.
    New code should use explicit PathManager instances.
    """
    # pylint: disable=global-statement
    global _global_path_manager
    _global_path_manager = PathManager(base_data_dir)


def get_base_data_dir() -> str:
    """Get the global base data directory (deprecated).
    
    This function is provided for backward compatibility with tests.
    New code should use explicit PathManager instances.
    """
    return get_path_manager().base_data_dir
