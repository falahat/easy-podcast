"""
Main orchestration class for podcast management.
"""

import logging
from typing import List

from .episode_downloader import DownloadSummary, EpisodeDownloader
from .models import Episode, Podcast
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

        # Log some statistics about audio files
        existing_episodes = self._get_episodes_with_audio()
        self.logger.info(
            "Found %d episodes with existing audio files",
            len(existing_episodes),
        )

    def get_podcast(self) -> Podcast:
        """Get currently loaded podcast."""
        return self.podcast

    def get_podcast_data_dir(self) -> str:
        """Get the data directory for this podcast."""
        return self.repository.get_podcast_dir(self.podcast.title)

    def episode_audio_exists(self, episode: Episode) -> bool:
        """Check if an episode's audio file exists."""
        return self.repository.episode_audio_exists(
            self.podcast.title, episode
        )

    def episode_transcript_exists(self, episode: Episode) -> bool:
        """Check if an episode's transcript file exists."""
        return self.repository.episode_transcript_exists(
            self.podcast.title, episode
        )

    def get_episode_audio_path(self, episode: Episode) -> str:
        """Get the full path to an episode's audio file."""
        return self.repository.get_episode_audio_path(
            self.podcast.title, episode
        )

    def get_episode_transcript_path(self, episode: Episode) -> str:
        """Get the full path to an episode's transcript file."""
        return self.repository.get_episode_transcript_path(
            self.podcast.title, episode
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
        downloads = self._prepare_downloads(episodes)
        summary = self.downloader.download_multiple(downloads)

        if summary.successful > 0:
            # Use upsert to automatically handle episode tracking
            successfully_downloaded = (
                self._get_successfully_downloaded_episodes(downloads, summary)
            )
            self.repository.upsert_episodes(
                self.podcast.title, successfully_downloaded
            )

        self._log_download_results(summary)
        return summary

    def _get_successfully_downloaded_episodes(
        self,
        downloads: List[tuple[Episode, str]],
        summary: DownloadSummary,
    ) -> List[Episode]:
        """Get episodes that were successfully downloaded."""
        path_to_episode = {path: episode for episode, path in downloads}

        successfully_downloaded: List[Episode] = []
        for result in summary.results:
            if result.success and result.file_path and not result.was_cached:
                episode = path_to_episode.get(result.file_path)
                if episode:
                    successfully_downloaded.append(episode)

        return successfully_downloaded

    def _prepare_downloads(
        self, episodes: List[Episode]
    ) -> List[tuple[Episode, str]]:
        """Prepare list of episodes and their target paths for download."""
        downloads: List[tuple[Episode, str]] = []
        for episode in episodes:
            target_path = self.repository.get_episode_audio_path(
                self.podcast.title, episode
            )
            downloads.append((episode, target_path))
        return downloads

    def _log_download_results(self, summary: DownloadSummary) -> None:
        """Log the download results summary."""
        self.logger.info(
            "Download results: %d successful, %d skipped, %d failed",
            summary.successful,
            summary.skipped,
            summary.failed,
        )

    def _get_episodes_with_audio(self) -> List[Episode]:
        """Get episodes that have existing audio files."""
        return [
            ep for ep in self.podcast.episodes if self.episode_audio_exists(ep)
        ]
