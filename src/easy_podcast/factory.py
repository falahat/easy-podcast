"""
Factory functions for creating PodcastManager instances.

This module provides simple factory functions that wire up dependencies
clearly.
"""

import logging
from typing import Optional

from .downloader import download_rss_from_url
from .episode_downloader import EpisodeDownloader
from .manager import PodcastManager
from .models import Podcast
from .parser import PodcastParser
from .repository import PodcastRepository
from .storage import Storage


def _create_dependencies(
    data_dir: str,
) -> tuple[Storage, PodcastRepository, EpisodeDownloader]:
    """Create shared dependencies for PodcastManager."""
    storage = Storage(data_dir)
    repository = PodcastRepository(storage)
    downloader = EpisodeDownloader(storage, repository)
    return storage, repository, downloader


def _create_manager(
    podcast: Podcast,
    repository: PodcastRepository,
    downloader: EpisodeDownloader,
) -> PodcastManager:
    """Create PodcastManager with given dependencies."""
    manager = PodcastManager(podcast, repository, downloader)
    logger = logging.getLogger(__name__)
    logger.info(
        "Successfully created PodcastManager for '%s' with %d episodes",
        podcast.title,
        len(podcast.episodes),
    )
    return manager


def create_manager_from_rss(
    rss_url: str, data_dir: str = "./data"
) -> Optional[PodcastManager]:
    """Create PodcastManager by downloading and parsing RSS feed."""
    logger = logging.getLogger(__name__)
    logger.info("Creating PodcastManager from RSS URL: %s", rss_url)

    # Download RSS content
    rss_content = download_rss_from_url(rss_url)
    if not rss_content:
        logger.error("Failed to download RSS content from %s", rss_url)
        return None

    # Parse RSS content
    parser = PodcastParser()
    podcast = parser.from_content(rss_url, rss_content)
    if not podcast:
        logger.error("Failed to parse RSS content from %s", rss_url)
        return None

    # Create dependencies
    _storage, repository, downloader = _create_dependencies(data_dir)

    # Save podcast metadata
    repository.save_podcast_metadata(podcast)

    # Save episodes
    repository.save_episodes(podcast.guid, podcast.episodes)

    # Save RSS cache
    repository.save_rss_cache(podcast.guid, rss_content)

    # Create and return manager
    return _create_manager(podcast, repository, downloader)


def create_manager_from_storage(
    podcast_guid: str, data_dir: str = "./data"
) -> Optional[PodcastManager]:
    """Create PodcastManager from existing storage."""
    logger = logging.getLogger(__name__)
    logger.info("Loading PodcastManager from storage: %s", podcast_guid)

    # Create dependencies
    _storage, repository, downloader = _create_dependencies(data_dir)

    # Load podcast metadata
    podcast = repository.load_podcast_metadata(podcast_guid)
    if not podcast:
        logger.error("Could not load podcast metadata for %s", podcast_guid)
        return None

    # Load episodes
    episodes = repository.load_episodes(podcast_guid)
    podcast.episodes = episodes

    # Create and return manager
    return _create_manager(podcast, repository, downloader)


def list_available_podcasts(data_dir: str = "./data") -> list[str]:
    """List available podcast directories."""
    storage = Storage(data_dir)
    return storage.list_directories(data_dir)
