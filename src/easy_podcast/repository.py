"""
Domain-specific repository for podcast data persistence.

This module handles podcast and episode storage using the Storage layer.
"""

import json
from dataclasses import asdict
from typing import List, Optional, TypeVar, Generic, Set, Type

from .models import (
    Episode,
    Podcast,
    Storable,
    FileSpec,
    EpisodeFile,
    PodcastFiles,
)
from .storage import Storage
from .utils import sanitize_filename

T = TypeVar("T", bound=Storable)


class Repository(Generic[T]):
    """Generic repository for GUID-based entities."""

    def __init__(self, storage: Storage):
        """Initialize with storage instance."""
        self.storage = storage

    def save(self, entities: List[T], file_path: str) -> bool:
        """Save entities to JSONL file."""
        lines = [entity.to_json() for entity in entities]
        return self.storage.write_text_lines(file_path, lines)

    def load(self, file_path: str, entity_class: Type[T]) -> List[T]:
        """Load entities from JSONL file."""
        lines = self.storage.read_text_lines(file_path)
        if not lines:
            return []

        entities: List[T] = []
        for line in lines:
            if not line.strip():
                continue

            try:
                entity_data = json.loads(line)
                entity = entity_class.from_dict(entity_data)
                # Type ignore needed for protocol type issues
                entities.append(entity)  # type: ignore[arg-type]
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

        return entities

    def get_existing_guids(self, entities: List[T]) -> Set[str]:
        """Extract non-empty GUIDs from entities."""
        return {entity.guid for entity in entities if entity.guid}

    def filter_new_entities(
        self, all_entities: List[T], existing_entities: List[T]
    ) -> List[T]:
        """Filter entities that don't exist yet based on GUID."""
        existing_guids = self.get_existing_guids(existing_entities)

        # For entities without GUID, fall back to ID-based comparison
        existing_ids = {
            getattr(entity, "id", "")
            for entity in existing_entities
            if not entity.guid and hasattr(entity, "id")
        }

        new_entities: List[T] = []
        for entity in all_entities:
            if entity.guid:
                # Use GUID-based filtering for entities with GUID
                if entity.guid not in existing_guids:
                    new_entities.append(entity)
            else:
                # Fall back to ID-based filtering for entities without GUID
                entity_id = getattr(entity, "id", "")
                if entity_id and entity_id not in existing_ids:
                    new_entities.append(entity)

        return new_entities

    def upsert(
        self, existing: List[T], incoming: List[T]
    ) -> tuple[List[T], List[T]]:
        """Merge entities, returning (updated_list, newly_added)."""
        existing_by_guid = {e.guid: e for e in existing}
        new_entities: List[T] = []

        for entity in incoming:
            if entity.guid not in existing_by_guid:
                new_entities.append(entity)
                existing_by_guid[entity.guid] = entity
            # Could add update logic here if entities can change

        return list(existing_by_guid.values()), new_entities


class PodcastRepository:
    """Repository for podcast-specific data operations."""

    def __init__(self, storage: Storage):
        """Initialize with storage instance."""
        self.storage = storage
        self.episode_repository = Repository[Episode](storage)
        self.podcast_repository = Repository[Podcast](storage)

    def get_podcast_dir(self, podcast_title: str) -> str:
        """Get podcast directory path using sanitized title."""
        sanitized_title = sanitize_filename(podcast_title)
        return self.storage.join_path(self.storage.base_dir, sanitized_title)

    def get_episode_file_path(
        self, podcast_title: str, episode: Episode, file_spec: FileSpec
    ) -> str:
        """Get full path to an episode file of the specified type."""
        podcast_dir = self.get_podcast_dir(podcast_title)

        if hasattr(file_spec, "suffix"):  # EpisodeFile enum
            suffix = file_spec.suffix
        else:  # CustomFile
            suffix = file_spec.suffix

        filename = f"{episode.id}{suffix}"
        return self.storage.join_path(podcast_dir, filename)

    def ensure_podcast_dir_exists(self, podcast_title: str) -> str:
        """Ensure podcast directory exists and return its path."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        self.storage.ensure_directory(podcast_dir)
        return podcast_dir

    def save_podcast_metadata(self, podcast: Podcast) -> bool:
        """Save podcast metadata to JSON file."""
        self.ensure_podcast_dir_exists(podcast.title)
        metadata_path = self._get_podcast_metadata_path(podcast.title)

        # Save podcast without episodes (episodes saved separately)
        podcast_data = asdict(podcast)
        podcast_data.pop("episodes", None)

        return self.storage.write_json(metadata_path, podcast_data)

    def load_podcast_metadata(self, podcast_title: str) -> Optional[Podcast]:
        """Load podcast metadata from JSON file."""
        metadata_path = self._get_podcast_metadata_path(podcast_title)

        data = self.storage.read_json(metadata_path)
        if not data:
            return None

        try:
            return Podcast.from_dict(data)
        except (KeyError, TypeError):
            return None

    def save_episodes(
        self, podcast_title: str, episodes: List[Episode]
    ) -> bool:
        """Save all episodes to a single JSONL file."""
        self.ensure_podcast_dir_exists(podcast_title)
        episodes_path = self._get_episodes_file_path(podcast_title)
        return self.episode_repository.save(episodes, episodes_path)

    def load_episodes(self, podcast_title: str) -> List[Episode]:
        """Load all episodes from JSONL file."""
        episodes_path = self._get_episodes_file_path(podcast_title)
        return self.episode_repository.load(episodes_path, Episode)

    def upsert_episodes(
        self, podcast_title: str, new_episodes: List[Episode]
    ) -> tuple[List[Episode], List[Episode]]:
        """Merge new episodes with existing ones, return (all, newly_added)."""
        existing_episodes = self.load_episodes(podcast_title)
        updated_episodes, newly_added = self.episode_repository.upsert(
            existing_episodes, new_episodes
        )
        self.save_episodes(podcast_title, updated_episodes)
        return updated_episodes, newly_added

    def filter_new_episodes(
        self, podcast_title: str, episodes: List[Episode]
    ) -> List[Episode]:
        """Filter episodes that don't have audio files downloaded yet."""
        return [
            episode
            for episode in episodes
            if not self.episode_file_exists(
                podcast_title, episode, EpisodeFile.AUDIO
            )
        ]

    def save_rss_cache(self, podcast_title: str, rss_content: bytes) -> bool:
        """Save RSS content to cache file."""
        self.ensure_podcast_dir_exists(podcast_title)
        cache_path = self._get_rss_cache_path(podcast_title)
        return self.storage.write_bytes(cache_path, rss_content)

    def load_rss_cache(self, podcast_title: str) -> Optional[bytes]:
        """Load RSS content from cache file."""
        cache_path = self._get_rss_cache_path(podcast_title)
        return self.storage.read_bytes(cache_path)

    def list_podcast_directories(self) -> List[str]:
        """List all podcast directories in the data directory."""
        return self.storage.list_directories(self.storage.base_dir)

    def podcast_exists(self, podcast_title: str) -> bool:
        """Check if a podcast directory exists."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        return self.storage.file_exists(podcast_dir)

    def episode_file_exists(
        self, podcast_title: str, episode: Episode, file_spec: FileSpec
    ) -> bool:
        """Check if an episode file of the specified type exists."""
        file_path = self.get_episode_file_path(
            podcast_title, episode, file_spec
        )
        return self.storage.file_exists(file_path)

    def _get_podcast_metadata_path(self, podcast_title: str) -> str:
        """Get path to podcast metadata file."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        return self.storage.join_path(podcast_dir, PodcastFiles.METADATA)

    def _get_episodes_file_path(self, podcast_title: str) -> str:
        """Get path to episodes.jsonl file for a podcast."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        return self.storage.join_path(podcast_dir, PodcastFiles.EPISODES)

    def _get_rss_cache_path(self, podcast_title: str) -> str:
        """Get path to RSS cache file."""
        podcast_dir = self.get_podcast_dir(podcast_title)
        return self.storage.join_path(podcast_dir, PodcastFiles.RSS_CACHE)
