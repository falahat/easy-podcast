"""
Command-line interface for the podcast downloader.
"""

import argparse
import os
import sys

from .factory import create_manager_from_rss
from .utils import format_bytes


def main() -> None:
    """CLI entry point for podcast downloader."""
    parser = argparse.ArgumentParser(
        description="Download podcast episodes from RSS feeds"
    )
    parser.add_argument("rss_url", help="URL of the podcast RSS feed")
    parser.add_argument(
        "--no-progress", action="store_true", help="Disable progress bars"
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="List new episodes without downloading",
    )

    args = parser.parse_args()

    try:
        # Check if PODCAST_DATA_DIRECTORY environment variable is set
        data_dir = os.getenv("PODCAST_DATA_DIRECTORY")
        if not data_dir:
            print(
                "Error: PODCAST_DATA_DIRECTORY environment variable "
                "must be set.",
                file=sys.stderr,
            )
            print(
                "Example: export PODCAST_DATA_DIRECTORY=/path/to/podcast/data",
                file=sys.stderr,
            )
            sys.exit(1)

        print(f"Using data directory: {data_dir}")

        # Initialize manager from RSS URL
        manager = create_manager_from_rss(args.rss_url, data_dir)

        if not manager:
            print(
                "Error: Could not create podcast manager from RSS feed",
                file=sys.stderr,
            )
            sys.exit(1)

        podcast = manager.podcast
        podcast_data_dir = manager.get_podcast_data_dir()

        print(f"Podcast: {podcast.title}")
        print(f"Data directory: {podcast_data_dir}")

        # Find new episodes
        new_episodes = manager.get_new_episodes()
        print(f"Found {len(new_episodes)} new episodes")

        if not new_episodes:
            print("No new episodes to download")
            return

        # Calculate total size
        total_download_size = sum(ep.size for ep in new_episodes)
        print(f"Total download size: {format_bytes(total_download_size)}")

        # List episodes
        for i, episode in enumerate(new_episodes, 1):
            print(f"  {i}. {episode.title} ({format_bytes(episode.size)})")

        if args.list_only:
            return

        # Download episodes
        print("\nDownloading episodes...")
        result = manager.download_episodes(new_episodes)

        print("\nDownload complete:")
        print(f"  Successfully downloaded: {result.successful}")
        print(f"  Already existed (skipped): {result.skipped}")
        print(f"  Failed downloads: {result.failed}")

        if result.failed > 0:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nDownload interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:  # pylint: disable=broad-except
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
