"""
File downloading functionality for RSS feeds and episode audio files.
"""

import logging
import os
from typing import List, Optional, Tuple, TYPE_CHECKING

import requests
from tqdm import tqdm

from .models import Episode

if TYPE_CHECKING:
    from .path_manager import PathManager


# RSS Download Functions
def download_rss_from_url(rss_url: str) -> Optional[bytes]:
    """Download RSS content from URL."""
    logger = logging.getLogger(__name__)
    logger.info("Downloading RSS from %s", rss_url)
    try:
        response = requests.get(rss_url, timeout=30)
        response.raise_for_status()
        if not response.content:
            logger.error("Failed to download RSS content - response was empty")
            return None
        logger.info(
            "Successfully downloaded RSS content (%d bytes)",
            len(response.content),
        )
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error("RSS download error: %s", e)
        return None


def load_rss_from_file(rss_file_path: str) -> Optional[bytes]:
    """Load RSS content from local file."""
    logger = logging.getLogger(__name__)
    logger.info("Loading RSS from %s", rss_file_path)
    try:
        with open(rss_file_path, "rb") as f:
            rss_content = f.read()
        if not rss_content:
            logger.error("RSS file is empty")
            return None
        logger.info(
            "Successfully loaded RSS content (%d bytes)", len(rss_content)
        )
        return rss_content
    except FileNotFoundError:
        logger.error("RSS file not found: %s", rss_file_path)
        return None
    except Exception as e:  # pylint: disable=broad-except
        logger.error("RSS file read error: %s", e)
        return None


# Episode Download Functions
def download_episode_file(
    episode: Episode, path_manager: "PathManager", podcast_guid: str
) -> Tuple[Optional[str], bool]:
    """Download single episode audio file.

    Args:
        episode: Episode object to download
        path_manager: PathManager instance for file operations
        podcast_guid: GUID of the podcast this episode belongs to

    Returns:
        Tuple of (file_path, was_downloaded).
    """
    logger = logging.getLogger(__name__)

    logger.debug(
        "Downloading episode %s (%s)",
        episode.id,
        episode.title,
    )

    # Get the target path from path_manager
    target_path = path_manager.get_episode_audio_path(episode, podcast_guid)
    
    # Ensure the episode directory exists
    path_manager.ensure_episode_dir_exists(episode, podcast_guid)

    return download_file_to_path(episode.audio_link, target_path)


def download_episodes_batch(
    episodes: List[Episode],
    path_manager: "PathManager",  # Type hint with quotes for forward reference
    podcast_guid: str,
    show_progress: bool = True,
) -> Tuple[int, int, int]:
    """Download multiple episodes with progress tracking.

    Args:
        episodes: List of Episode objects to download
        path_manager: PathManager instance for file operations
        podcast_guid: GUID of the podcast these episodes belong to
        show_progress: Whether to show progress bars

    Returns:
        Tuple of (successful_downloads, skipped_files, failed_downloads).
    """
    logger = logging.getLogger(__name__)

    if not episodes:
        logger.info("No episodes to download")
        return 0, 0, 0

    logger.info(
        "Starting batch download of %d episodes",
        len(episodes),
    )

    successful_count = 0
    skipped_count = 0
    failed_count = 0

    total_download_bytes = sum(ep.size for ep in episodes)
    logger.info("Total download size: %d bytes", total_download_bytes)

    if show_progress:
        with tqdm(
            total=total_download_bytes,
            unit="B",
            unit_scale=True,
            desc="Downloading Episodes",
        ) as progress_bar:
            for i, episode in enumerate(episodes, 1):
                title_short = episode.title[:30]
                desc = f"Episode {i}/{len(episodes)}: {title_short}..."
                progress_bar.set_description(desc)

                download_path, was_downloaded = download_episode_file(
                    episode, path_manager, podcast_guid
                )

                if download_path and was_downloaded:
                    successful_count += 1
                    progress_bar.update(episode.size)
                    logger.debug("Successfully downloaded: %s", episode.title)
                elif download_path:  # File existed
                    skipped_count += 1
                    progress_bar.update(episode.size)
                    logger.debug("Skipped existing file: %s", episode.title)
                else:  # Download failed
                    failed_count += 1
                    logger.warning("Failed to download: %s", episode.title)

            progress_bar.set_description("Download Complete!")
    else:
        for i, episode in enumerate(episodes, 1):
            logger.info(
                "Downloading episode %d/%d: %s",
                i,
                len(episodes),
                episode.title,
            )

            download_path, was_downloaded = download_episode_file(
                episode, path_manager, podcast_guid
            )
            if download_path and was_downloaded:
                successful_count += 1
                logger.debug("Successfully downloaded: %s", episode.title)
            elif download_path:
                skipped_count += 1
                logger.debug("Skipped existing file: %s", episode.title)
            else:
                failed_count += 1
                logger.warning("Failed to download: %s", episode.title)

    logger.info(
        "Batch download completed: %d successful, %d skipped, %d failed",
        successful_count,
        skipped_count,
        failed_count,
    )

    return successful_count, skipped_count, failed_count


# Helper Functions
def download_file_to_path(
    file_url: str, output_path: str
) -> Tuple[Optional[str], bool]:
    """Download file from URL to specific path."""
    logger = logging.getLogger(__name__)

    if os.path.exists(output_path):
        logger.debug("File already exists: %s. Skipping.", output_path)
        return output_path, False

    output_filename = os.path.basename(output_path)
    logger.info("Downloading %s from %s", output_filename, file_url)
    try:
        with requests.get(file_url, stream=True, timeout=30) as response:
            response.raise_for_status()

            # Get file size for progress bar
            content_length = int(response.headers.get("content-length", 0))
            logger.debug("Content length: %d bytes", content_length)

            with open(output_path, "wb") as output_file:
                # Show download progress
                with tqdm(
                    total=content_length,
                    unit="B",
                    unit_scale=True,
                    desc=output_filename,
                    leave=False,
                ) as progress_bar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:  # Filter out keep-alive chunks
                            output_file.write(chunk)
                            progress_bar.update(len(chunk))

        logger.info("Download complete: %s", output_filename)
        return output_path, True
    except (requests.exceptions.RequestException, IOError) as e:
        logger.error("Download failed for %s: %s", output_filename, e)
        if os.path.exists(output_path):
            os.remove(output_path)  # Clean up partial file
            logger.debug("Cleaned up partial file: %s", output_path)
        return None, False


def download_file_streamed(
    file_url: str, output_filename: str, output_directory: str
) -> Tuple[Optional[str], bool]:
    """Download file from URL with progress tracking.
    
    DEPRECATED: Use download_file_to_path instead.
    """
    output_path = os.path.join(output_directory, output_filename)
    return download_file_to_path(file_url, output_path)
