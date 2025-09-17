"""
Handles all metadata persistence using the new nested directory structure.
"""

import json
import os
from dataclasses import asdict
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from .models import Episode, Podcast
    from .path_manager import PathManager


class StorageManager:
    """Handles all metadata persistence using new nested structure."""

    def __init__(self, path_manager: "PathManager"):
        """Initialize with path manager for file operations."""
        self.path_manager = path_manager

    def save_episode_metadata(
        self, episode: "Episode", podcast_guid: str
    ) -> None:
        """Save episode metadata to individual JSON file."""
        # Ensure the episode directory exists
        self.path_manager.ensure_episode_dir_exists(episode, podcast_guid)
        
        # Get metadata file path and save
        metadata_path = self.path_manager.get_episode_metadata_path(
            episode, podcast_guid
        )
        
        # Use dataclass built-in method instead of manual dict creation
        episode_data = asdict(episode)
        
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(episode_data, f, indent=2, ensure_ascii=False)

    def load_episode_metadata(
        self, episode_id: str, podcast_guid: str
    ) -> Optional["Episode"]:
        """Load episode metadata from individual JSON file."""
        # We need to find the episode by ID, but we need the Episode object
        # to get the path. This is a chicken-and-egg problem.
        # For now, we'll need to iterate through the episode mappings
        # to find the right folder name.
        
        from .models import Episode  # Import here to avoid circular imports
        
        # Create a temporary Episode object just to get the path
        temp_episode = Episode(
            id=episode_id,
            published="",
            title="",
            author="",
            duration_seconds=0,
            size=0,
            audio_link="",
            image="",
        )
        
        metadata_path = self.path_manager.get_episode_metadata_path(
            temp_episode, podcast_guid
        )
        
        if not os.path.exists(metadata_path):
            return None
            
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                episode_data = json.load(f)
                return Episode.from_dict(episode_data)
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            return None

    def save_podcast_metadata(self, podcast: "Podcast") -> None:
        """Save podcast metadata to JSON file."""
        # Use the GUID field from the podcast model
        podcast_guid = podcast.guid
        if not podcast_guid:
            raise ValueError("Podcast must have a non-empty guid field")
        
        # Ensure the podcast directory exists
        self.path_manager.ensure_podcast_dir_exists(podcast_guid)
        
        # Get metadata file path and save
        metadata_path = self.path_manager.get_podcast_metadata_path(
            podcast_guid
        )
        
        # Convert podcast to dict for JSON serialization using dataclass method
        podcast_data = asdict(podcast)
        
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(podcast_data, f, indent=2, ensure_ascii=False)

    def load_podcast_metadata(self, podcast_guid: str) -> Optional["Podcast"]:
        """Load podcast metadata from JSON file."""
        metadata_path = self.path_manager.get_podcast_metadata_path(
            podcast_guid
        )
        
        if not os.path.exists(metadata_path):
            return None
            
        try:
            from .models import Podcast  # Import here to avoid circular
            
            with open(metadata_path, "r", encoding="utf-8") as f:
                podcast_data = json.load(f)
                return Podcast(
                    title=podcast_data["title"],
                    rss_url=podcast_data["rss_url"],
                    safe_title=podcast_data["safe_title"],
                )
        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            return None

    def list_podcast_episodes(self, podcast_guid: str) -> List["Episode"]:
        """List all episodes for a podcast by loading their metadata files."""
        episodes: List["Episode"] = []
        podcast_dir = self.path_manager.get_podcast_dir(podcast_guid)
        
        if not os.path.exists(podcast_dir):
            return episodes
            
        # Iterate through subdirectories looking for metadata.json files
        for item in os.listdir(podcast_dir):
            item_path = os.path.join(podcast_dir, item)
            if os.path.isdir(item_path):
                metadata_file = os.path.join(
                    item_path, self.path_manager.EPISODE_METADATA_FILE
                )
                if os.path.exists(metadata_file):
                    try:
                        with open(metadata_file, "r", encoding="utf-8") as f:
                            episode_data = json.load(f)
                            from .models import Episode
                            episode = Episode.from_dict(episode_data)
                            episodes.append(episode)
                    except (json.JSONDecodeError, KeyError):
                        # Skip malformed metadata files
                        continue
                        
        return episodes

    def save_rss_to_podcast_mapping(self, mappings: Dict[str, str]) -> None:
        """Save RSS URL to podcast GUID mappings."""
        self.path_manager.ensure_base_dirs_exist()
        mapping_path = self.path_manager.get_rss_mapping_path()
        
        with open(mapping_path, "w", encoding="utf-8") as f:
            json.dump(mappings, f, indent=2, ensure_ascii=False)

    def load_rss_to_podcast_mapping(self) -> Dict[str, str]:
        """Load RSS URL to podcast GUID mappings."""
        mapping_path = self.path_manager.get_rss_mapping_path()
        
        if not os.path.exists(mapping_path):
            return {}
            
        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, FileNotFoundError):
            return {}