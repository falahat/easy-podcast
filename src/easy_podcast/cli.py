"""
Command-line interface for the podcast downloader.
"""

import argparse
import sys

from .manager import PodcastManager
from .path_manager import set_base_data_dir
from .utils import format_bytes


def main() -> None:
    """CLI entry point for podcast downloader."""
    parser = argparse.ArgumentParser(
        description="Download podcast episodes from RSS feeds"
    )
    parser.add_argument("rss_url", help="URL of the podcast RSS feed")
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory to store downloaded episodes and metadata",
    )
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
        # Set global base data directory
        set_base_data_dir(args.data_dir)

        # Initialize manager from RSS URL
        manager = PodcastManager.from_rss_url(args.rss_url)

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
        successful_count, skipped_count, failed_count = result

        print("\nDownload complete:")
        print(f"  Successfully downloaded: {successful_count}")
        print(f"  Already existed (skipped): {skipped_count}")
        print(f"  Failed downloads: {failed_count}")

        if failed_count > 0:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nDownload interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:  # pylint: disable=broad-except
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
