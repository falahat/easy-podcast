"""
Common test utilities for the podcast package.

This module contains shared test utilities that are used across
multiple test files to reduce code duplication and maintain consistency.
"""

from typing import Any, Dict, List, Optional
from unittest.mock import Mock

from easy_podcast.models import Episode


def create_test_episode(**kwargs: Any) -> Episode:
    """Helper function to create a test Episode with sensible defaults.

    This utility provides default values for all Episode fields, allowing
    tests to only override the fields that are important for their specific
    test case. This reduces code duplication and makes tests more focused
    on what they're actually testing.

    Args:
        **kwargs: Override any Episode field with custom values

    Returns:
        Episode with default values for all fields unless overridden

    Example:
        # Create episode with just custom ID
        episode = create_test_episode(id="custom_id")

        # Create episode with custom ID and title
        episode = create_test_episode(id="123", title="Custom Title")
    """
    defaults: Dict[str, Any] = {
        "id": "test_episode",
        "published": "2023-01-01",
        "title": "Test Episode",
        "author": "Test Author",
        "duration_seconds": 1800,  # 30 minutes
        "size": 1024,
        "audio_link": "http://example.com/test.mp3",
        "image": "http://example.com/image.jpg",
    }
    defaults.update(kwargs)
    return Episode(**defaults)


def create_test_episodes(count: int, **base_kwargs: Any) -> List[Episode]:
    """Create multiple test episodes with sequential IDs."""
    episodes = []
    for i in range(count):
        episode_kwargs = base_kwargs.copy()
        episode_kwargs.setdefault("id", f"episode_{i+1}")
        episode_kwargs.setdefault("title", f"Episode {i+1}")
        episodes.append(create_test_episode(**episode_kwargs))
    return episodes


class MockTranscriberContext:
    """Context manager for consistent transcriber mocking."""

    def __init__(self, **params: Any):
        self.params = {
            "model_size": "large-v2",
            "device": "cpu",
            "compute_type": "int8",
            "batch_size": 16,
            **params,
        }

    def __enter__(self) -> Mock:
        # Return mock transcriber with expected interface
        return Mock()

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        pass
