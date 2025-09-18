"""
Podcast package - Handles downloading RSS data, parsing into episodes,
downloading episodes, and managing metadata.

This package provides a modular approach to podcast management with
separate components for data models, parsing, downloading, and tracking.
"""

from .factory import create_manager_from_rss, create_manager_from_storage
from .manager import PodcastManager
from .models import Episode, Podcast

__all__ = [
    "create_manager_from_rss",
    "create_manager_from_storage", 
    "PodcastManager",
    "Episode",
    "Podcast",
]
