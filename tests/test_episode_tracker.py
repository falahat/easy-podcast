"""
Tests for the EpisodeTracker class.
"""

import os
import shutil
import tempfile
import unittest

from easy_podcast.episode_tracker import EpisodeTracker

from tests.utils import create_test_episode


# pylint: disable=too-many-public-methods
class TestEpisodeTracker(unittest.TestCase):
    """Test suite for the EpisodeTracker class."""

    def setUp(self) -> None:
        """Set up a temporary directory for test data."""
        self.test_dir = tempfile.mkdtemp(
            prefix="podcast_episode_tracker_test_"
        )
        self.episodes_file = os.path.join(self.test_dir, "episodes.jsonl")
        self.downloads_dir = os.path.join(self.test_dir, "downloads")
        os.makedirs(self.downloads_dir, exist_ok=True)

    def _create_test_episode_json(self, episode_id: str) -> str:
        """Create a test episode JSON string with the given ID."""
        return (
            f'{{"id": "{episode_id}", "published": "d", "title": "t", '
            f'"author": "a", "duration_seconds": -1, "audio_file": "af", '
            f'"size": 1, "audio_link": "al", "image": "im"}}\n'
        )

    def tearDown(self) -> None:
        """Remove the temporary directory after tests."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_load_episodes_from_file(self) -> None:
        """Test loading episodes from a .jsonl file."""
        with open(self.episodes_file, "w", encoding="utf-8") as f:
            f.write(self._create_test_episode_json("1"))
            f.write(self._create_test_episode_json("2"))

        tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)
        self.assertEqual(len(tracker.episodes_by_id), 2)
        self.assertIn("1", tracker.episodes_by_id)
        self.assertIn("2", tracker.episodes_by_id)
        self.assertEqual(tracker.episodes_by_id["1"].title, "t")

    def test_load_episodes_malformed_json(self) -> None:
        """Test that malformed lines in the episodes file are skipped."""
        with open(self.episodes_file, "w", encoding="utf-8") as f:
            f.write(self._create_test_episode_json("1"))
            f.write("this is not json\n")
            f.write(self._create_test_episode_json("3"))

        tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)
        self.assertEqual(len(tracker.episodes_by_id), 2)
        self.assertIn("1", tracker.episodes_by_id)
        self.assertNotIn("2", tracker.episodes_by_id)
        self.assertIn("3", tracker.episodes_by_id)

    def test_load_episodes_empty_file(self) -> None:
        """Test loading from empty episodes file."""
        # Create empty file
        with open(self.episodes_file, "w", encoding="utf-8"):
            pass

        tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)
        self.assertEqual(len(tracker.episodes_by_id), 0)

    def test_load_episodes_nonexistent_file(self) -> None:
        """Test loading when episodes file doesn't exist."""
        nonexistent_file = os.path.join(self.test_dir, "nonexistent.jsonl")
        nonexistent_downloads = os.path.join(
            self.test_dir, "nonexistent_downloads"
        )
        tracker = EpisodeTracker(nonexistent_file, nonexistent_downloads)
        self.assertEqual(len(tracker.episodes_by_id), 0)

    def test_add_episode(self) -> None:
        """Test adding a new episode."""
        tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)
        episode = create_test_episode(id="1")
        tracker.add_episode(episode)

        self.assertIn("1", tracker.episodes_by_id)
        with open(self.episodes_file, "r", encoding="utf-8") as f:
            line = f.readline()
            self.assertIn('"id": "1"', line)

    def test_add_duplicate_episode(self) -> None:
        """Test that adding a duplicate episode is ignored."""
        episode = create_test_episode(id="1")
        with open(self.episodes_file, "w", encoding="utf-8") as f:
            f.write(episode.to_json() + "\n")

        tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)
        self.assertEqual(len(tracker.episodes_by_id), 1)

        tracker.add_episode(episode)  # Add again
        self.assertEqual(len(tracker.episodes_by_id), 1)

        with open(self.episodes_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1)

    def test_get_existing_episode_ids(self) -> None:
        """Test retrieving the set of existing episode IDs."""
        with open(self.episodes_file, "w", encoding="utf-8") as f:
            f.write(self._create_test_episode_json("10"))
            f.write(self._create_test_episode_json("20"))

        tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)
        ids = tracker.get_existing_episode_ids()
        self.assertEqual(ids, {"10", "20"})

    def test_episode_persistence_across_instances(self) -> None:
        """Test that episodes persist across EpisodeTracker instances."""
        # First instance - add episodes
        tracker1 = EpisodeTracker(self.episodes_file, self.downloads_dir)
        episode1 = create_test_episode(
            id="1",
            title="Episode 1",
            size=1000,
        )
        episode2 = create_test_episode(
            id="2",
            title="Episode 2",
            size=2000,
        )
        tracker1.add_episode(episode1)
        tracker1.add_episode(episode2)

        # Second instance - should load existing episodes
        tracker2 = EpisodeTracker(self.episodes_file, self.downloads_dir)
        self.assertEqual(len(tracker2.episodes_by_id), 2)
        self.assertIn("1", tracker2.episodes_by_id)
        self.assertIn("2", tracker2.episodes_by_id)
        self.assertEqual(tracker2.episodes_by_id["1"].title, "Episode 1")
        self.assertEqual(tracker2.episodes_by_id["2"].title, "Episode 2")

    def test_load_episodes(self) -> None:
        """Test load_episodes method returns list of all episodes."""
        tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)

        # Initially empty
        episodes = tracker.load_episodes()
        self.assertEqual(len(episodes), 0)
        self.assertIsInstance(episodes, list)

        # Add some episodes
        episode1 = create_test_episode(
            id="1",
            title="Episode 1",
            size=1000,
        )
        episode2 = create_test_episode(
            id="2",
            title="Episode 2",
            size=2000,
        )
        tracker.add_episode(episode1)
        tracker.add_episode(episode2)

        # Load episodes should return both
        episodes = tracker.load_episodes()
        self.assertEqual(len(episodes), 2)
        episode_ids = {ep.id for ep in episodes}
        self.assertEqual(episode_ids, {"1", "2"})

    def test_save_episodes(self) -> None:
        """Test save_episodes method overwrites file with new episode list."""
        tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)

        # Create episodes list
        episodes = [
            create_test_episode(
                id="100",
                title="Episode 100",
                size=1000,
            ),
            create_test_episode(
                id="200",
                title="Episode 200",
                size=2000,
            ),
        ]

        # Save episodes
        tracker.save_episodes(episodes)

        # Verify in-memory state
        self.assertEqual(len(tracker.episodes_by_id), 2)
        self.assertIn("100", tracker.episodes_by_id)
        self.assertIn("200", tracker.episodes_by_id)

        # Verify file contents
        with open(self.episodes_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)
            self.assertIn('"id": "100"', lines[0])
            self.assertIn('"id": "200"', lines[1])

    def test_save_episodes_creates_directory(self) -> None:
        """Test save_episodes creates parent directory if it doesn't exist."""
        # Use a nested directory that doesn't exist
        nested_dir = os.path.join(self.test_dir, "nested", "deeper")
        nested_episodes_file = os.path.join(nested_dir, "episodes.jsonl")

        tracker = EpisodeTracker(nested_episodes_file, self.downloads_dir)

        episodes = [
            create_test_episode(
                id="1",
                title="Episode 1",
                size=1000,
            )
        ]

        # Directory shouldn't exist yet
        self.assertFalse(os.path.exists(nested_dir))

        # Save episodes should create directory
        tracker.save_episodes(episodes)

        # Verify directory was created and file exists
        self.assertTrue(os.path.exists(nested_dir))
        self.assertTrue(os.path.exists(nested_episodes_file))

        # Verify content
        with open(nested_episodes_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn('"id": "1"', content)

    def test_save_episodes_overwrites_existing(self) -> None:
        """Test save_episodes overwrites existing file content."""
        tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)

        # Add initial episode via normal add_episode
        initial_episode = create_test_episode(
            id="initial",
            title="Initial Episode",
            size=1000,
        )
        tracker.add_episode(initial_episode)

        # Verify initial state
        self.assertEqual(len(tracker.episodes_by_id), 1)
        self.assertIn("initial", tracker.episodes_by_id)

        # Save completely different episodes
        new_episodes = [
            create_test_episode(
                id="new1",
                title="New Episode 1",
                size=1000,
            ),
            create_test_episode(
                id="new2",
                title="New Episode 2",
                size=2000,
            ),
        ]
        tracker.save_episodes(new_episodes)

        # Verify old episode is gone, new episodes are present
        self.assertEqual(len(tracker.episodes_by_id), 2)
        self.assertNotIn("initial", tracker.episodes_by_id)
        self.assertIn("new1", tracker.episodes_by_id)
        self.assertIn("new2", tracker.episodes_by_id)

        # Verify file only contains new episodes
        with open(self.episodes_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertNotIn("initial", content)
            self.assertIn("new1", content)
            self.assertIn("new2", content)

    def test_update_episode_existing(self) -> None:
        """Test update_episode modifies an existing episode."""
        tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)

        # Add initial episode
        original_episode = create_test_episode(
            id="update_test",
            title="Original Title",
            author="Original Author",
            size=1000,
        )
        tracker.add_episode(original_episode)

        # Verify initial state
        self.assertEqual(
            tracker.episodes_by_id["update_test"].title, "Original Title"
        )
        self.assertEqual(
            tracker.episodes_by_id["update_test"].author, "Original Author"
        )

        # Update episode
        updated_episode = create_test_episode(
            id="update_test",
            title="Updated Title",
            author="Updated Author",
            size=2000,
        )
        tracker.update_episode(updated_episode)

        # Verify update in memory
        self.assertEqual(
            tracker.episodes_by_id["update_test"].title, "Updated Title"
        )
        self.assertEqual(
            tracker.episodes_by_id["update_test"].author, "Updated Author"
        )
        self.assertEqual(tracker.episodes_by_id["update_test"].size, 2000)

        # Verify persistence by loading new tracker instance
        new_tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)
        self.assertEqual(
            new_tracker.episodes_by_id["update_test"].title, "Updated Title"
        )
        self.assertEqual(
            new_tracker.episodes_by_id["update_test"].author, "Updated Author"
        )

    def test_update_episode_nonexistent(self) -> None:
        """Test update_episode adds episode if it doesn't exist."""
        tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)

        # Verify initially empty
        self.assertEqual(len(tracker.episodes_by_id), 0)

        # Try to update non-existent episode
        new_episode = create_test_episode(
            id="nonexistent",
            title="New Episode",
            size=1000,
        )
        tracker.update_episode(new_episode)

        # Verify episode was added
        self.assertEqual(len(tracker.episodes_by_id), 1)
        self.assertIn("nonexistent", tracker.episodes_by_id)
        self.assertEqual(
            tracker.episodes_by_id["nonexistent"].title, "New Episode"
        )

        # Verify persistence
        with open(self.episodes_file, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn('"id": "nonexistent"', content)

    def test_load_episodes_with_blank_lines(self) -> None:
        """Test loading episodes file with blank lines and whitespace."""
        with open(self.episodes_file, "w", encoding="utf-8") as f:
            f.write(self._create_test_episode_json("1"))
            f.write("\n")  # Blank line
            f.write("   \n")  # Whitespace only line
            f.write(self._create_test_episode_json("2"))
            f.write("\n")  # Trailing blank line

        tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)
        self.assertEqual(len(tracker.episodes_by_id), 2)
        self.assertIn("1", tracker.episodes_by_id)
        self.assertIn("2", tracker.episodes_by_id)

    def test_load_episodes_with_type_error(self) -> None:
        """Test handling of TypeError during episode deserialization."""
        with open(self.episodes_file, "w", encoding="utf-8") as f:
            # Valid episode JSON
            f.write(
                '{"id": "1", "published": "d", "title": "t", "author": "a", '
                '"duration_seconds": -1, "audio_file": "af", "size": 1, '
                '"audio_link": "al", "image": "im"}\n'
            )
            # This will cause a TypeError in Episode.from_dict due to missing
            # required fields
            f.write('{"id": "incomplete"}\n')
            # Another valid episode JSON
            f.write(
                '{"id": "3", "published": "d", "title": "t", "author": "a", '
                '"duration_seconds": -1, "audio_file": "af", "size": 1, '
                '"audio_link": "al", "image": "im"}\n'
            )

        tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)
        # Should load valid episodes and skip the invalid one
        self.assertEqual(len(tracker.episodes_by_id), 2)
        self.assertIn("1", tracker.episodes_by_id)
        self.assertNotIn("incomplete", tracker.episodes_by_id)
        self.assertIn("3", tracker.episodes_by_id)

    def test_get_episode_audio_path(self) -> None:
        """Test get_episode_audio_path method."""
        tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)
        episode = create_test_episode(id="test123")

        expected_path = os.path.join(
            self.downloads_dir, episode.audio_filename
        )
        actual_path = tracker.get_episode_audio_path(episode)

        self.assertEqual(actual_path, expected_path)

    def test_episode_audio_exists(self) -> None:
        """Test episode_audio_exists method."""
        tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)
        episode = create_test_episode(id="test123")

        # File doesn't exist initially
        self.assertFalse(tracker.episode_audio_exists(episode))

        # Create the file
        audio_path = tracker.get_episode_audio_path(episode)
        with open(audio_path, "w", encoding="utf-8") as f:
            f.write("test audio content")

        # File should exist now
        self.assertTrue(tracker.episode_audio_exists(episode))

    def test_get_episode_transcript_path(self) -> None:
        """Test get_episode_transcript_path method."""
        tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)
        episode = create_test_episode(id="test123")

        expected_path = os.path.join(
            self.downloads_dir, episode.transcript_filename
        )
        actual_path = tracker.get_episode_transcript_path(episode)

        self.assertEqual(actual_path, expected_path)

    def test_episode_transcript_exists(self) -> None:
        """Test episode_transcript_exists method."""
        tracker = EpisodeTracker(self.episodes_file, self.downloads_dir)
        episode = create_test_episode(id="test123")

        # File doesn't exist initially
        self.assertFalse(tracker.episode_transcript_exists(episode))

        # Create the file
        transcript_path = tracker.get_episode_transcript_path(episode)
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write('{"test": "transcript content"}')

        # File should exist now
        self.assertTrue(tracker.episode_transcript_exists(episode))


if __name__ == "__main__":
    unittest.main()
