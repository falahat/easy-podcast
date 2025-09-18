"""
Factory functions for creating PodcastManager instances.

This module provides simple factory functions that wire up dependencies clearly.
"""

import logging
from typing import Optional

from .downloader import download_rss_from_url
from .episode_downloader import EpisodeDownloader
from .manager import PodcastManager
from .parser import PodcastParser
from .repository import PodcastRepository
from .storage import Storage


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
    storage = Storage(data_dir)
    repository = PodcastRepository(storage)
    downloader = EpisodeDownloader(storage)

    # Save podcast metadata
    repository.save_podcast_metadata(podcast)

    # Save RSS cache
    repository.save_rss_cache(podcast.title, rss_content)

    # Create and return manager
    manager = PodcastManager(podcast, repository, downloader)
    logger.info(
        "Successfully created PodcastManager for '%s' with %d episodes",
        podcast.title,
        len(podcast.episodes),
    )

    return manager


def create_manager_from_storage(
    podcast_title: str, data_dir: str = "./data"
) -> Optional[PodcastManager]:
    """Create PodcastManager from existing storage."""
    logger = logging.getLogger(__name__)
    logger.info("Loading PodcastManager from storage: %s", podcast_title)

    # Create dependencies
    storage = Storage(data_dir)
    repository = PodcastRepository(storage)

    # Load podcast metadata
    podcast = repository.load_podcast_metadata(podcast_title)
    if not podcast:
        logger.error("Could not load podcast metadata for %s", podcast_title)
        return None

    # Load episodes
    episodes = repository.load_episodes(podcast_title)
    podcast.episodes = episodes

    # Create downloader
    downloader = EpisodeDownloader(storage)

    # Create and return manager
    manager = PodcastManager(podcast, repository, downloader)
    logger.info(
        "Successfully loaded PodcastManager for '%s' with %d episodes",
        podcast.title,
        len(podcast.episodes),
    )

    return manager


def list_available_podcasts(data_dir: str = "./data") -> list[str]:
    """List available podcast directories."""
    storage = Storage(data_dir)
    return storage.list_directories(data_dir)