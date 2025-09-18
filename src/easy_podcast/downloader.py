"""
File downloading functionality for RSS feeds and episode audio files.
"""

import logging
import os
from typing import Optional, Tuple

import requests
from tqdm import tqdm


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
