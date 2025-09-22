"""
Main orchestration class for podcast management.
"""

import logging
from typing import List

from .episode_downloader import DownloadSummary, EpisodeDownloader
from .models import Episode, Podcast, FileSpec
from .repository import PodcastRepository


class PodcastManager:
    """
    Orchestrates podcast data ingestion, metadata management,
    and episode downloads using dependency injection.
    """

    def __init__(
        self,
        podcast: Podcast,
        repository: PodcastRepository,
        downloader: EpisodeDownloader,
    ):
        """Initialize with dependencies."""
        self.logger = logging.getLogger(__name__)
        self.podcast = podcast
        self.repository = repository
        self.downloader = downloader

        self.logger.info(
            "Initializing PodcastManager for podcast: '%s'", self.podcast.title
        )

        # Ensure podcast directory exists
        self.repository.ensure_podcast_dir_exists(self.podcast.title)

    def get_podcast(self) -> Podcast:
        """Get currently loaded podcast."""
        return self.podcast

    def get_podcast_data_dir(self) -> str:
        """Get the data directory for this podcast."""
        return self.repository.get_podcast_dir(self.podcast.title)

    def episode_file_exists(
        self, episode: Episode, file_spec: FileSpec
    ) -> bool:
        """Check if an episode file of the specified type exists."""
        return self.repository.episode_file_exists(
            self.podcast.title, episode, file_spec
        )

    def get_episode_file_path(
        self, episode: Episode, file_spec: FileSpec
    ) -> str:
        """Get the full path to an episode file of the specified type."""
        return self.repository.get_episode_file_path(
            self.podcast.title, episode, file_spec
        )

    def get_new_episodes(self) -> List[Episode]:
        """Get episodes that haven't been downloaded yet."""
        new_episodes = self.repository.filter_new_episodes(
            self.podcast.title, self.podcast.episodes
        )

        self.logger.info(
            "Found %d new episodes out of %d total episodes",
            len(new_episodes),
            len(self.podcast.episodes),
        )

        return new_episodes

    def download_episodes(self, episodes: List[Episode]) -> DownloadSummary:
        """Download multiple episodes with progress tracking."""
        return self.downloader.download_episodes_for_podcast(
            self.podcast, episodes
        )
