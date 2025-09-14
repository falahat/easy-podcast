"""
File downloading functionality for RSS feeds and episode audio files.
"""

import logging
import os
from typing import List, Optional, Tuple

import requests
from tqdm import tqdm

from .models import Episode


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
    episode: Episode, target_download_dir: str
) -> Tuple[Optional[str], bool]:
    """Download single episode audio file.

    Returns:
        Tuple of (file_path, was_downloaded).
    """
    logger = logging.getLogger(__name__)

    if not target_download_dir:
        logger.error("No download directory specified")
        raise ValueError("No download directory specified")

    logger.debug(
        "Downloading episode %s (%s) to %s",
        episode.id,
        episode.title,
        target_download_dir,
    )

    return download_file_streamed(
        episode.audio_link, episode.audio_filename, target_download_dir
    )


def download_episodes_batch(
    episodes: List[Episode],
    target_download_dir: str,
    show_progress: bool = True,
) -> Tuple[int, int, int]:
    """Download multiple episodes with progress tracking.

    Returns:
        Tuple of (successful_downloads, skipped_files, failed_downloads).
    """
    logger = logging.getLogger(__name__)

    if not episodes:
        logger.info("No episodes to download")
        return 0, 0, 0

    if not target_download_dir:
        logger.error("No download directory specified")
        raise ValueError("No download directory specified")

    logger.info(
        "Starting batch download of %d episodes to %s",
        len(episodes),
        target_download_dir,
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
                    episode, target_download_dir
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
                episode, target_download_dir
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
def download_file_streamed(
    file_url: str, output_filename: str, output_directory: str
) -> Tuple[Optional[str], bool]:
    """Download file from URL with progress tracking."""
    logger = logging.getLogger(__name__)
    output_path = os.path.join(output_directory, output_filename)

    if os.path.exists(output_path):
        logger.debug("File already exists: %s. Skipping.", output_path)
        return output_path, False

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
