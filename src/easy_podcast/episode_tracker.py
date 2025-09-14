"""
Episode metadata tracking and persistence.
"""

import json
import logging
import os
from typing import Dict, List, Set

from .models import Episode


class EpisodeTracker:
    """Manages episode metadata persistence and loading."""

    def __init__(self, episodes_file_path: str, downloads_dir: str):
        self.episodes_file_path = episodes_file_path
        self.downloads_dir = downloads_dir
        self.episodes_by_id: Dict[str, Episode] = {}
        self.logger = logging.getLogger(__name__)
        self._load_episodes()

    def _load_episodes(self) -> None:
        """Load episodes from JSONL metadata file."""
        if not os.path.exists(self.episodes_file_path):
            self.logger.info(
                "Episodes file not found: %s", self.episodes_file_path
            )
            return

        with open(self.episodes_file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    if line.strip():
                        episode_data = json.loads(line)
                        episode = Episode.from_dict(episode_data)
                        self.episodes_by_id[episode.id] = episode
                except (json.JSONDecodeError, TypeError) as e:
                    self.logger.warning(
                        "Skipping invalid line %d: %s... (%s)",
                        line_num,
                        line.strip()[:50],
                        e,
                    )

    def add_episode(self, episode: Episode) -> None:
        """Add episode and append to the JSONL file."""
        if episode.id in self.episodes_by_id:
            self.logger.warning(
                "Episode %s already exists, skipping", episode.id
            )
            return  # Already exists

        self.episodes_by_id[episode.id] = episode
        with open(self.episodes_file_path, "a", encoding="utf-8") as f:
            f.write(episode.to_json() + "\n")

    def get_existing_episode_ids(self) -> Set[str]:
        """Get set of existing episode IDs."""
        return set(self.episodes_by_id.keys())

    def get_new_episodes(self, episodes: List[Episode]) -> List[Episode]:
        """Get episodes that haven't been tracked yet."""
        existing_ids = self.get_existing_episode_ids()
        new_episodes = [ep for ep in episodes if ep.id not in existing_ids]

        self.logger.info(
            "Found %d new episodes out of %d total episodes",
            len(new_episodes),
            len(episodes),
        )
        self.logger.debug("Existing episode IDs count: %d", len(existing_ids))

        return new_episodes

    def load_episodes(self) -> List[Episode]:
        """Get list of all loaded episodes."""
        return list(self.episodes_by_id.values())

    def save_episodes(self, episodes: List[Episode]) -> None:
        """Save episodes list to JSONL file, overwriting existing content."""
        self.logger.info(
            "Saving %d episodes to %s", len(episodes), self.episodes_file_path
        )

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.episodes_file_path), exist_ok=True)

        # Write all episodes to file, overwriting existing content
        with open(self.episodes_file_path, "w", encoding="utf-8") as f:
            for episode in episodes:
                f.write(episode.to_json() + "\n")

        # Update in-memory dictionary
        self.episodes_by_id = {episode.id: episode for episode in episodes}

        self.logger.info("Successfully saved %d episodes", len(episodes))

    def update_episode(self, episode: Episode) -> None:
        """Update an existing episode in memory and persist changes."""
        if episode.id not in self.episodes_by_id:
            self.logger.warning(
                "Episode %s not found for update, adding instead", episode.id
            )
            self.add_episode(episode)
            return

        # Update in-memory dictionary
        self.episodes_by_id[episode.id] = episode

        # Rewrite the entire file with all current episodes
        episodes_list = list(self.episodes_by_id.values())
        self.save_episodes(episodes_list)

        self.logger.debug("Updated episode %s", episode.id)

    def get_episode_audio_path(self, episode: Episode) -> str:
        """Get full path to episode's audio file."""
        return os.path.join(self.downloads_dir, episode.audio_filename)

    def episode_audio_exists(self, episode: Episode) -> bool:
        """Check if episode's audio file exists."""
        return os.path.exists(self.get_episode_audio_path(episode))

    def get_episode_transcript_path(self, episode: Episode) -> str:
        """Get full path to episode's transcript file."""
        return os.path.join(self.downloads_dir, episode.transcript_filename)

    def episode_transcript_exists(self, episode: Episode) -> bool:
        """Check if episode's transcript file exists."""
        return os.path.exists(self.get_episode_transcript_path(episode))
