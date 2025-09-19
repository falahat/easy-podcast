"""
Download service for podcast episodes.

This module provides a clean interface for downloading episodes with clear results.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .downloader import download_file_to_path
from .models import Episode
from .storage import Storage


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
    results: List[DownloadResult]

    @classmethod
    def from_results(cls, results: List[DownloadResult]) -> "DownloadSummary":
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

    def __init__(self, storage: Storage):
        """Initialize with storage instance."""
        self.storage = storage
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
            else:
                return DownloadResult(
                    success=False, error=f"Failed to download {episode.title}"
                )

        except Exception as e:
            self.logger.error(
                "Download error for episode %s: %s", episode.id, e
            )
            return DownloadResult(success=False, error=str(e))

    def download_multiple(
        self, downloads: List[Tuple[Episode, str]]
    ) -> DownloadSummary:
        """Download multiple episodes with progress tracking."""
        results = []

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
