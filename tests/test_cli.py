"""
Tests for the CLI module.
"""

import sys
from io import StringIO
from typing import Any
from unittest.mock import Mock, patch

import pytest

from easy_podcast.cli import main
from easy_podcast.models import Episode, Podcast


class TestCLI:
    """Test cases for CLI functionality."""

    def test_cli_help_message(self) -> None:
        """Test that CLI shows help message correctly."""
        with patch.object(sys, "argv", ["podcast-download", "--help"]):
            with pytest.raises(SystemExit) as excinfo:
                main()
            assert excinfo.value.code == 0

    def test_cli_missing_required_argument(self) -> None:
        """Test CLI with missing RSS URL argument."""
        with patch.object(sys, "argv", ["podcast-download"]):
            with pytest.raises(SystemExit) as excinfo:
                main()
            assert excinfo.value.code == 2

    @patch("easy_podcast.cli.PodcastManager")
    def test_cli_successful_download_workflow(
        self, mock_manager_class: Any
    ) -> None:
        """Test complete CLI workflow with successful downloads."""
        # Mock the manager instance
        mock_manager = Mock()
        mock_manager_class.from_rss_url.return_value = mock_manager

        # Create mock podcast and episodes
        mock_podcast = Mock(spec=Podcast)
        mock_podcast.title = "Test Podcast"
        mock_podcast.safe_title = "Test_Podcast"

        mock_episode1 = Mock(spec=Episode)
        mock_episode1.title = "Episode 1"
        mock_episode1.size = 1024 * 1024  # 1MB

        mock_episode2 = Mock(spec=Episode)
        mock_episode2.title = "Episode 2"
        mock_episode2.size = 2 * 1024 * 1024  # 2MB

        mock_episodes = [mock_episode1, mock_episode2]

        # Configure manager mocks
        mock_manager.podcast = mock_podcast
        mock_manager.get_new_episodes.return_value = mock_episodes
        mock_manager.download_episodes.return_value = (
            2,
            0,
            0,
        )  # successful, skipped, failed

        # Capture stdout
        captured_output = StringIO()

        with patch.object(
            sys, "argv", ["podcast-download", "http://example.com/feed.xml"]
        ):
            with patch("sys.stdout", captured_output):
                main()

        output = captured_output.getvalue()

        # Verify manager was initialized correctly
        mock_manager_class.from_rss_url.assert_called_once_with(
            "http://example.com/feed.xml"
        )

        # Verify episode retrieval and download
        mock_manager.get_new_episodes.assert_called_once()
        mock_manager.download_episodes.assert_called_once_with(
            mock_episodes, show_progress=True
        )

        # Verify output content
        assert "Test Podcast" in output
        assert "Found 2 new episodes" in output
        assert "Total download size: 3.00 MiB" in output
        assert "Episode 1 (1.00 MiB)" in output
        assert "Episode 2 (2.00 MiB)" in output
        assert "Successfully downloaded: 2" in output

    @patch("easy_podcast.cli.PodcastManager")
    def test_cli_custom_data_directory(self, mock_manager_class: Any) -> None:
        """Test CLI with custom data directory."""
        mock_manager_class.from_rss_url.return_value = None

        with patch.object(
            sys,
            "argv",
            [
                "podcast-download",
                "--data-dir",
                "/custom/path",
                "http://example.com/feed.xml",
            ],
        ):
            with patch("sys.stderr", StringIO()):
                with pytest.raises(SystemExit) as excinfo:
                    main()
                assert excinfo.value.code == 1

        mock_manager_class.from_rss_url.assert_called_once_with(
            "http://example.com/feed.xml"
        )

    @patch("easy_podcast.cli.PodcastManager")
    def test_cli_list_only_mode(self, mock_manager_class: Any) -> None:
        """Test CLI in list-only mode (no downloads)."""
        mock_manager = Mock()
        mock_manager_class.from_rss_url.return_value = mock_manager

        mock_podcast = Mock(spec=Podcast)
        mock_podcast.title = "Test Podcast"
        mock_podcast.safe_title = "Test_Podcast"

        mock_episode = Mock(spec=Episode)
        mock_episode.title = "Episode 1"
        mock_episode.size = 1024 * 1024

        mock_manager.podcast = mock_podcast
        mock_manager.get_new_episodes.return_value = [mock_episode]

        captured_output = StringIO()

        with patch.object(
            sys,
            "argv",
            ["podcast-download", "--list-only", "http://example.com/feed.xml"],
        ):
            with patch("sys.stdout", captured_output):
                main()

        output = captured_output.getvalue()

        # Verify download wasn't called
        mock_manager.download_episodes.assert_not_called()

        # Verify listing output
        assert "Found 1 new episodes" in output
        assert "Episode 1 (1.00 MiB)" in output

    @patch("easy_podcast.cli.PodcastManager")
    def test_cli_no_progress_mode(self, mock_manager_class: Any) -> None:
        """Test CLI with progress bars disabled."""
        mock_manager = Mock()
        mock_manager_class.from_rss_url.return_value = mock_manager

        mock_podcast = Mock(spec=Podcast)
        mock_podcast.title = "Test Podcast"
        mock_podcast.safe_title = "Test_Podcast"

        mock_episode = Mock(spec=Episode)
        mock_episode.title = "Episode 1"
        mock_episode.size = 1024 * 1024

        mock_manager.podcast = mock_podcast
        mock_manager.get_new_episodes.return_value = [mock_episode]
        mock_manager.download_episodes.return_value = (1, 0, 0)

        with patch.object(
            sys,
            "argv",
            [
                "podcast-download",
                "--no-progress",
                "http://example.com/feed.xml",
            ],
        ):
            with patch("sys.stdout", StringIO()):
                main()

        # Verify progress was disabled
        mock_manager.download_episodes.assert_called_once_with(
            [mock_episode], show_progress=False
        )

    @patch("easy_podcast.cli.PodcastManager")
    def test_cli_rss_feed_parse_failure(self, mock_manager_class: Any) -> None:
        """Test CLI when RSS feed parsing fails."""
        mock_manager_class.from_rss_url.return_value = None

        captured_error = StringIO()

        with patch.object(
            sys,
            "argv",
            ["podcast-download", "http://invalid-feed.com/feed.xml"],
        ):
            with patch("sys.stderr", captured_error):
                with pytest.raises(SystemExit) as excinfo:
                    main()
                assert excinfo.value.code == 1

        error_output = captured_error.getvalue()
        assert (
            "Error: Could not create podcast manager from RSS feed"
            in error_output
        )

    @patch("easy_podcast.cli.PodcastManager")
    def test_cli_no_new_episodes(self, mock_manager_class: Any) -> None:
        """Test CLI when no new episodes are found."""
        mock_manager = Mock()
        mock_manager_class.from_rss_url.return_value = mock_manager

        mock_podcast = Mock(spec=Podcast)
        mock_podcast.title = "Test Podcast"
        mock_podcast.safe_title = "Test_Podcast"

        mock_manager.podcast = mock_podcast
        mock_manager.get_new_episodes.return_value = []

        captured_output = StringIO()

        with patch.object(
            sys, "argv", ["podcast-download", "http://example.com/feed.xml"]
        ):
            with patch("sys.stdout", captured_output):
                main()

        output = captured_output.getvalue()

        # Verify download wasn't called
        mock_manager.download_episodes.assert_not_called()

        # Verify no episodes message
        assert "Found 0 new episodes" in output
        assert "No new episodes to download" in output

    @patch("easy_podcast.cli.PodcastManager")
    def test_cli_partial_download_failure(
        self, mock_manager_class: Any
    ) -> None:
        """Test CLI when some downloads fail."""
        mock_manager = Mock()
        mock_manager_class.from_rss_url.return_value = mock_manager

        mock_podcast = Mock(spec=Podcast)
        mock_podcast.title = "Test Podcast"
        mock_podcast.safe_title = "Test_Podcast"

        mock_episode = Mock(spec=Episode)
        mock_episode.title = "Episode 1"
        mock_episode.size = 1024 * 1024

        mock_manager.podcast = mock_podcast
        mock_manager.get_new_episodes.return_value = [mock_episode]
        mock_manager.download_episodes.return_value = (
            0,
            0,
            1,
        )  # successful, skipped, failed

        captured_output = StringIO()

        with patch.object(
            sys, "argv", ["podcast-download", "http://example.com/feed.xml"]
        ):
            with patch("sys.stdout", captured_output):
                with pytest.raises(SystemExit) as excinfo:
                    main()
                assert excinfo.value.code == 1

        output = captured_output.getvalue()
        assert "Failed downloads: 1" in output

    @patch("easy_podcast.cli.PodcastManager")
    def test_cli_keyboard_interrupt(self, mock_manager_class: Any) -> None:
        """Test CLI handling of keyboard interrupt."""
        mock_manager_class.from_rss_url.side_effect = KeyboardInterrupt()

        captured_error = StringIO()

        with patch.object(
            sys, "argv", ["podcast-download", "http://example.com/feed.xml"]
        ):
            with patch("sys.stderr", captured_error):
                with pytest.raises(SystemExit) as excinfo:
                    main()
                assert excinfo.value.code == 130

        error_output = captured_error.getvalue()
        assert "Download interrupted by user" in error_output

    @patch("easy_podcast.cli.PodcastManager")
    def test_cli_unexpected_exception(self, mock_manager_class: Any) -> None:
        """Test CLI handling of unexpected exceptions."""
        mock_manager_class.from_rss_url.side_effect = Exception(
            "Unexpected error"
        )

        captured_error = StringIO()

        with patch.object(
            sys, "argv", ["podcast-download", "http://example.com/feed.xml"]
        ):
            with patch("sys.stderr", captured_error):
                with pytest.raises(SystemExit) as excinfo:
                    main()
                assert excinfo.value.code == 1

        error_output = captured_error.getvalue()
        assert "Error: Unexpected error" in error_output

    @patch("easy_podcast.cli.PodcastManager")
    def test_cli_mixed_download_results(self, mock_manager_class: Any) -> None:
        """Test CLI with mixed download results (success, skip, fail)."""
        mock_manager = Mock()
        mock_manager_class.from_rss_url.return_value = mock_manager

        mock_podcast = Mock(spec=Podcast)
        mock_podcast.title = "Test Podcast"
        mock_podcast.safe_title = "Test_Podcast"

        mock_episode = Mock(spec=Episode)
        mock_episode.title = "Episode 1"
        mock_episode.size = 1024 * 1024

        mock_manager.podcast = mock_podcast
        mock_manager.get_new_episodes.return_value = [mock_episode]
        mock_manager.download_episodes.return_value = (
            2,
            1,
            0,
        )  # successful, skipped, failed

        captured_output = StringIO()

        with patch.object(
            sys, "argv", ["podcast-download", "http://example.com/feed.xml"]
        ):
            with patch("sys.stdout", captured_output):
                main()

        output = captured_output.getvalue()

        assert "Successfully downloaded: 2" in output
        assert "Already existed (skipped): 1" in output
        assert "Failed downloads: 0" in output
