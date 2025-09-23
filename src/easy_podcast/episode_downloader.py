"""
Download service for podcast episodes.

This module provides a clean interface for downloading episodes
with clear results.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

from .downloader import download_file_to_path
from .models import Episode, Podcast, EpisodeFile
from .storage import Storage

if TYPE_CHECKING:
    from .repository import PodcastRepository


@dataclass
class DownloadResult:
    """Result of a download operation."""

    success: bool
    file_path: Optional[str] = None
    error: Optional[str] = None
    was_cached: bool = False


@dataclass
class DownloadSummary:
    """Summary of multiple download operations."""

    successful: int
    skipped: int
    failed: int
    results: list[DownloadResult]

    @classmethod
    def from_results(cls, results: list[DownloadResult]) -> "DownloadSummary":
        """Create summary from list of results."""
        successful = sum(1 for r in results if r.success and not r.was_cached)
        skipped = sum(1 for r in results if r.was_cached)
        failed = sum(1 for r in results if not r.success)

        return cls(
            successful=successful,
            skipped=skipped,
            failed=failed,
            results=results,
        )


class EpisodeDownloader:
    """Service for downloading podcast episodes."""

    def __init__(
        self,
        storage: Storage,
        repository: Optional["PodcastRepository"] = None,
    ):
        """Initialize with storage instance and optional repository."""
        self.storage = storage
        self.repository = repository
        self.logger = logging.getLogger(__name__)

    def download_episode(
        self, episode: Episode, target_path: str
    ) -> DownloadResult:
        """Download single episode to target path."""
        # Check if file already exists
        if self.storage.file_exists(target_path):
            self.logger.debug("Episode already exists: %s", target_path)
            return DownloadResult(
                success=True, file_path=target_path, was_cached=True
            )

        # Download the episode
        try:
            file_path, was_downloaded = download_file_to_path(
                episode.audio_link, target_path
            )

            if file_path:
                return DownloadResult(
                    success=True,
                    file_path=file_path,
                    was_cached=not was_downloaded,
                )
            return DownloadResult(
                success=False, error=f"Failed to download {episode.title}"
            )
        except Exception as e:  # pylint: disable=broad-except
            self.logger.error(
                "Download error for episode %s: %s", episode.id, e
            )
            return DownloadResult(success=False, error=str(e))

    def download_multiple(
        self, downloads: list[tuple[Episode, str]]
    ) -> DownloadSummary:
        """Download multiple episodes with progress tracking."""
        results: list[DownloadResult] = []

        for episode, target_path in downloads:
            result = self.download_episode(episode, target_path)
            results.append(result)

            if result.success:
                if result.was_cached:
                    self.logger.debug("Skipped existing: %s", episode.title)
                else:
                    self.logger.info("Downloaded: %s", episode.title)
            else:
                self.logger.error(
                    "Failed: %s - %s", episode.title, result.error
                )

        return DownloadSummary.from_results(results)

    def download_episodes_for_podcast(
        self, podcast: Podcast, episodes: List[Episode]
    ) -> DownloadSummary:
        """Download multiple episodes for a podcast with full workflow.

        This method handles the complete download workflow including:
        - Preparing download paths
        - Downloading episodes
        - Updating episode tracking in repository
        - Logging results
        """
        if not self.repository:
            raise ValueError(
                "Repository is required for download_episodes_for_podcast"
            )

        downloads = self._prepare_downloads(podcast, episodes)
        summary = self.download_multiple(downloads)

        if summary.successful > 0:
            # Use upsert to automatically handle episode tracking
            successfully_downloaded = (
                self._get_successfully_downloaded_episodes(downloads, summary)
            )
            self.repository.upsert_episodes(
                podcast.guid, successfully_downloaded
            )

        self._log_download_results(summary)
        return summary

    def _prepare_downloads(
        self, podcast: Podcast, episodes: List[Episode]
    ) -> List[tuple[Episode, str]]:
        """Prepare list of episodes and their target paths for download."""
        if not self.repository:
            raise ValueError("Repository is required for _prepare_downloads")

        downloads: List[tuple[Episode, str]] = []
        for episode in episodes:
            target_path = self.repository.get_episode_file_path(
                podcast.guid, episode, EpisodeFile.AUDIO
            )
            downloads.append((episode, target_path))
        return downloads

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

    def _log_download_results(self, summary: DownloadSummary) -> None:
        """Log the download results summary."""
        self.logger.info(
            "Download results: %d successful, %d skipped, %d failed",
            summary.successful,
            summary.skipped,
            summary.failed,
        )
