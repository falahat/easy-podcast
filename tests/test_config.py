"""
Tests for the easy_podcast.config module.

This module tests the PodcastConfig class and global configuration functions
that provide centralized configuration management for directories, file paths,
and other settings used throughout the podcast package.
"""

import os
import tempfile
import unittest

import easy_podcast.config
from easy_podcast.config import (
    PodcastConfig,
    config,
    get_config,
    set_base_data_dir,
    get_base_data_dir,
)


# pylint: disable=too-many-public-methods
class TestPodcastConfig(unittest.TestCase):
    """Test the PodcastConfig class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.config = PodcastConfig()

    def test_config_initialization_default(self) -> None:
        """Test that PodcastConfig initializes with default values."""
        config_instance = PodcastConfig()
        self.assertEqual(config_instance.base_data_dir, "data")
        self.assertEqual(config_instance.DOWNLOADS_SUBDIR, "downloads")
        self.assertEqual(config_instance.EPISODES_FILE, "episodes.jsonl")
        self.assertEqual(config_instance.RSS_FILE, "rss.xml")
        self.assertEqual(config_instance.TRANSCRIPT_SUFFIX, "_transcript.txt")

    def test_config_initialization_custom_base_dir(self) -> None:
        """Test PodcastConfig initialization with custom base directory."""
        custom_dir = "/custom/data/dir"
        config_instance = PodcastConfig(base_data_dir=custom_dir)
        self.assertEqual(config_instance.base_data_dir, custom_dir)

    def test_config_initialization_none_base_dir(self) -> None:
        """Test PodcastConfig initialization with None base directory
        falls back to default."""
        config_instance = PodcastConfig(base_data_dir=None)
        self.assertEqual(config_instance.base_data_dir, "data")

    def test_base_data_dir_property_getter(self) -> None:
        """Test the base_data_dir property getter."""
        self.assertEqual(self.config.base_data_dir, "data")

    def test_base_data_dir_property_setter(self) -> None:
        """Test the base_data_dir property setter."""
        new_dir = "/new/data/dir"
        self.config.base_data_dir = new_dir
        self.assertEqual(self.config.base_data_dir, new_dir)

    def test_get_podcast_data_dir(self) -> None:
        """Test getting podcast data directory path."""
        podcast_title = "My Test Podcast"
        expected_path = os.path.join("data", podcast_title)
        self.assertEqual(
            self.config.get_podcast_data_dir(podcast_title), expected_path
        )

    def test_get_podcast_data_dir_custom_base(self) -> None:
        """Test getting podcast data directory with custom base directory."""
        self.config.base_data_dir = "/custom/base"
        podcast_title = "My Test Podcast"
        expected_path = os.path.join("/custom/base", podcast_title)
        self.assertEqual(
            self.config.get_podcast_data_dir(podcast_title), expected_path
        )

    def test_get_podcast_data_dir_from_safe_title(self) -> None:
        """Test getting podcast data directory using safe title."""
        safe_title = "My_Safe_Podcast_Title"
        expected_path = os.path.join("data", safe_title)
        self.assertEqual(
            self.config.get_podcast_data_dir_from_safe_title(safe_title),
            expected_path,
        )

    def test_get_downloads_dir_from_safe_title(self) -> None:
        """Test getting downloads directory using safe title."""
        safe_title = "My_Safe_Podcast_Title"
        expected_path = os.path.join("data", safe_title, "downloads")
        self.assertEqual(
            self.config.get_downloads_dir_from_safe_title(safe_title),
            expected_path,
        )

    def test_get_episodes_file_path_from_safe_title(self) -> None:
        """Test getting episodes file path using safe title."""
        safe_title = "My_Safe_Podcast_Title"
        expected_path = os.path.join("data", safe_title, "episodes.jsonl")
        self.assertEqual(
            self.config.get_episodes_file_path_from_safe_title(safe_title),
            expected_path,
        )

    def test_get_rss_file_path_from_safe_title(self) -> None:
        """Test getting RSS file path using safe title."""
        safe_title = "My_Safe_Podcast_Title"
        expected_path = os.path.join("data", safe_title, "rss.xml")
        self.assertEqual(
            self.config.get_rss_file_path_from_safe_title(safe_title),
            expected_path,
        )

    def test_get_downloads_dir(self) -> None:
        """Test getting downloads directory from podcast data directory."""
        podcast_data_dir = "/path/to/podcast"
        expected_path = os.path.join(podcast_data_dir, "downloads")
        self.assertEqual(
            self.config.get_downloads_dir(podcast_data_dir), expected_path
        )

    def test_get_episodes_file_path(self) -> None:
        """Test getting episodes file path from podcast data directory."""
        podcast_data_dir = "/path/to/podcast"
        expected_path = os.path.join(podcast_data_dir, "episodes.jsonl")
        self.assertEqual(
            self.config.get_episodes_file_path(podcast_data_dir), expected_path
        )

    def test_get_rss_file_path(self) -> None:
        """Test getting RSS file path from podcast data directory."""
        podcast_data_dir = "/path/to/podcast"
        expected_path = os.path.join(podcast_data_dir, "rss.xml")
        self.assertEqual(
            self.config.get_rss_file_path(podcast_data_dir), expected_path
        )

    def test_get_transcript_filename(self) -> None:
        """Test getting transcript filename from audio filename."""
        audio_filename = "episode123.mp3"
        expected_filename = "episode123_transcript.txt"
        self.assertEqual(
            self.config.get_transcript_filename(audio_filename),
            expected_filename,
        )

    def test_get_transcript_filename_different_extensions(self) -> None:
        """Test getting transcript filename with different audio file
        extensions."""
        test_cases = [
            ("episode.mp3", "episode_transcript.txt"),
            ("episode.wav", "episode_transcript.txt"),
            ("episode.m4a", "episode_transcript.txt"),
            ("episode.flac", "episode_transcript.txt"),
            ("episode", "episode_transcript.txt"),  # No extension
        ]

        for audio_filename, expected_filename in test_cases:
            with self.subTest(audio_filename=audio_filename):
                self.assertEqual(
                    self.config.get_transcript_filename(audio_filename),
                    expected_filename,
                )

    def test_get_transcript_filename_with_dots_in_name(self) -> None:
        """Test getting transcript filename when audio filename contains
        dots."""
        audio_filename = "episode.1.2.3.mp3"
        expected_filename = "episode.1.2.3_transcript.txt"
        self.assertEqual(
            self.config.get_transcript_filename(audio_filename),
            expected_filename,
        )

    def test_path_construction_with_windows_paths(self) -> None:
        """Test path construction works correctly on Windows-style paths."""
        if os.name == "nt":  # Only run on Windows
            self.config.base_data_dir = r"C:\Users\Test\Data"
            podcast_title = "Test Podcast"
            expected_path = os.path.join(r"C:\Users\Test\Data", podcast_title)
            self.assertEqual(
                self.config.get_podcast_data_dir(podcast_title), expected_path
            )

    def test_path_construction_with_unix_paths(self) -> None:
        """Test path construction works correctly with Unix-style paths."""
        self.config.base_data_dir = "/home/user/data"
        podcast_title = "Test Podcast"
        expected_path = os.path.join("/home/user/data", podcast_title)
        self.assertEqual(
            self.config.get_podcast_data_dir(podcast_title), expected_path
        )

    def test_class_constants_immutable(self) -> None:
        """Test that class constants are properly defined."""
        # These should be class attributes, not instance attributes
        self.assertEqual(PodcastConfig.DEFAULT_BASE_DATA_DIR, "data")
        self.assertEqual(PodcastConfig.DOWNLOADS_SUBDIR, "downloads")
        self.assertEqual(PodcastConfig.EPISODES_FILE, "episodes.jsonl")
        self.assertEqual(PodcastConfig.RSS_FILE, "rss.xml")
        self.assertEqual(PodcastConfig.TRANSCRIPT_SUFFIX, "_transcript.txt")


class TestGlobalConfigFunctions(unittest.TestCase):
    """Test the global configuration functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Store original config state
        self.original_base_data_dir = config.base_data_dir

    def tearDown(self) -> None:
        """Restore original config state."""
        config.base_data_dir = self.original_base_data_dir

    def test_get_config_returns_global_instance(self) -> None:
        """Test that get_config returns the global config instance."""
        config_instance = get_config()
        self.assertIs(config_instance, config)

    def test_get_config_consistent_instance(self) -> None:
        """Test that get_config always returns the same instance."""
        config1 = get_config()
        config2 = get_config()
        self.assertIs(config1, config2)

    def test_set_base_data_dir_updates_global_config(self) -> None:
        """Test that set_base_data_dir updates the global config."""
        new_dir = "/test/data/dir"
        set_base_data_dir(new_dir)
        self.assertEqual(config.base_data_dir, new_dir)
        self.assertEqual(get_config().base_data_dir, new_dir)

    def test_get_base_data_dir_returns_current_setting(self) -> None:
        """Test that get_base_data_dir returns the current base data
        directory."""
        # Test default value
        original_dir = get_base_data_dir()
        self.assertEqual(original_dir, config.base_data_dir)

        # Test after changing
        new_dir = "/new/test/dir"
        set_base_data_dir(new_dir)
        self.assertEqual(get_base_data_dir(), new_dir)

    def test_global_config_state_persistence(self) -> None:
        """Test that global config state persists across function calls."""
        # Set a custom directory
        custom_dir = "/persistent/test/dir"
        set_base_data_dir(custom_dir)

        # Verify it persists through multiple get_config calls
        config1 = get_config()
        config2 = get_config()

        self.assertEqual(config1.base_data_dir, custom_dir)
        self.assertEqual(config2.base_data_dir, custom_dir)
        self.assertEqual(get_base_data_dir(), custom_dir)

    def test_global_config_module_level_access(self) -> None:
        """Test that the global config is accessible at module level."""
        # The 'config' variable should be available at module level
        self.assertIsInstance(easy_podcast.config.config, PodcastConfig)

    def test_set_base_data_dir_with_empty_string(self) -> None:
        """Test setting base data dir with empty string."""
        set_base_data_dir("")
        self.assertEqual(get_base_data_dir(), "")

    def test_set_base_data_dir_with_relative_path(self) -> None:
        """Test setting base data dir with relative path."""
        relative_path = "relative/data/path"
        set_base_data_dir(relative_path)
        self.assertEqual(get_base_data_dir(), relative_path)

    def test_set_base_data_dir_with_absolute_path(self) -> None:
        """Test setting base data dir with absolute path."""
        if os.name == "nt":
            absolute_path = r"C:\absolute\data\path"
        else:
            absolute_path = "/absolute/data/path"

        set_base_data_dir(absolute_path)
        self.assertEqual(get_base_data_dir(), absolute_path)


class TestConfigIntegration(unittest.TestCase):
    """Test config integration scenarios that might occur in real usage."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = PodcastConfig()
        self.test_podcast_title = "Test Podcast Title"
        self.test_safe_title = "Test_Podcast_Title"

    def test_complete_file_path_construction_workflow(self) -> None:
        """Test a complete workflow of constructing all file paths for a
        podcast."""
        # Set custom base directory
        base_dir = "/custom/podcast/data"
        self.config.base_data_dir = base_dir

        # Get all paths
        podcast_data_dir = self.config.get_podcast_data_dir_from_safe_title(
            self.test_safe_title
        )
        downloads_dir = self.config.get_downloads_dir_from_safe_title(
            self.test_safe_title
        )
        episodes_file = self.config.get_episodes_file_path_from_safe_title(
            self.test_safe_title
        )
        rss_file = self.config.get_rss_file_path_from_safe_title(
            self.test_safe_title
        )

        # Verify all paths are correctly constructed
        expected_base = os.path.join(base_dir, self.test_safe_title)
        self.assertEqual(podcast_data_dir, expected_base)
        self.assertEqual(
            downloads_dir, os.path.join(expected_base, "downloads")
        )
        self.assertEqual(
            episodes_file, os.path.join(expected_base, "episodes.jsonl")
        )
        self.assertEqual(rss_file, os.path.join(expected_base, "rss.xml"))

    def test_alternate_path_construction_methods(self) -> None:
        """Test that both path construction methods yield the same results."""
        # Use os.path.join for cross-platform compatibility
        base_dir = os.path.join("explicit", "podcast", "data")
        podcast_subdir = "test_podcast"
        podcast_data_dir = os.path.join(base_dir, podcast_subdir)

        # Method 1: Using podcast data dir directly
        downloads_dir_1 = self.config.get_downloads_dir(podcast_data_dir)
        episodes_file_1 = self.config.get_episodes_file_path(podcast_data_dir)
        rss_file_1 = self.config.get_rss_file_path(podcast_data_dir)

        # Method 2: Using safe title (with matching base dir setup)
        self.config.base_data_dir = base_dir
        safe_title = podcast_subdir  # To match the podcast_data_dir
        downloads_dir_2 = self.config.get_downloads_dir_from_safe_title(
            safe_title
        )
        episodes_file_2 = self.config.get_episodes_file_path_from_safe_title(
            safe_title
        )
        rss_file_2 = self.config.get_rss_file_path_from_safe_title(safe_title)

        # Both methods should yield the same results
        self.assertEqual(downloads_dir_1, downloads_dir_2)
        self.assertEqual(episodes_file_1, episodes_file_2)
        self.assertEqual(rss_file_1, rss_file_2)

    def test_transcript_filename_with_real_episode_ids(self) -> None:
        """Test transcript filename generation with realistic episode IDs."""
        test_cases = [
            ("727175.mp3", "727175_transcript.txt"),
            ("ep_001.mp3", "ep_001_transcript.txt"),
            (
                "2023-12-25-special-episode.mp3",
                "2023-12-25-special-episode_transcript.txt",
            ),
            ("podcast.episode.123.mp3", "podcast.episode.123_transcript.txt"),
        ]

        for audio_file, expected_transcript in test_cases:
            with self.subTest(audio_file=audio_file):
                result = self.config.get_transcript_filename(audio_file)
                self.assertEqual(result, expected_transcript)

    def test_config_immutability_of_constants(self) -> None:
        """Test that config constants cannot be accidentally modified."""
        # Verify constants exist and have expected values
        original_downloads_subdir = self.config.DOWNLOADS_SUBDIR
        original_episodes_file = self.config.EPISODES_FILE
        original_rss_file = self.config.RSS_FILE
        original_transcript_suffix = self.config.TRANSCRIPT_SUFFIX

        # Verify they are strings (not mutable)
        self.assertIsInstance(original_downloads_subdir, str)
        self.assertIsInstance(original_episodes_file, str)
        self.assertIsInstance(original_rss_file, str)
        self.assertIsInstance(original_transcript_suffix, str)

        # If someone tries to modify them directly (shouldn't work as
        # they're class attributes)
        # The instance attributes shouldn't affect class behavior
        # pylint: disable=attribute-defined-outside-init
        setattr(self.config, "DOWNLOADS_SUBDIR", "modified")

        # Creating a new instance should still have original values
        new_config = PodcastConfig()
        self.assertEqual(
            new_config.DOWNLOADS_SUBDIR, original_downloads_subdir
        )

    def test_cross_platform_path_consistency(self) -> None:
        """Test that path construction works consistently across platforms."""
        # Use forward slashes in base dir (should work on both Windows
        # and Unix)
        self.config.base_data_dir = "test/data/base"
        safe_title = "cross_platform_test"

        podcast_dir = self.config.get_podcast_data_dir_from_safe_title(
            safe_title
        )
        downloads_dir = self.config.get_downloads_dir_from_safe_title(
            safe_title
        )

        # Results should use the platform's path separator
        expected_podcast_dir = os.path.join("test/data/base", safe_title)
        expected_downloads_dir = os.path.join(
            "test/data/base", safe_title, "downloads"
        )

        self.assertEqual(podcast_dir, expected_podcast_dir)
        self.assertEqual(downloads_dir, expected_downloads_dir)

        # Verify paths use correct separator for the current platform
        if os.name == "nt":  # Windows
            self.assertIn("\\", downloads_dir)
        else:  # Unix-like
            self.assertIn("/", downloads_dir)


if __name__ == "__main__":
    unittest.main()
