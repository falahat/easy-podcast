# Easy Podcast

A modular Python package for downloading podcast episodes from RSS feeds. Features progress tracking, metadata management, and duplicate detection.

## Python Version Requirements

**This package requires Python 3.10, 3.11, or 3.12.** Python 3.13+ is not supported due to dependency limitations with the WhisperX library.

## Features

- **RSS Feed Parsing**: Download and parse podcast RSS feeds
- **Episode Management**: Track downloaded episodes with JSONL metadata
- **Progress Tracking**: Visual progress bars for downloads
- **Duplicate Detection**: Automatically skip already downloaded episodes
- **Type Safety**: Comprehensive type hints throughout

## Installation

### Standard Installation

```bash
git clone https://github.com/falahat/easy-podcast.git
cd easy-podcast
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/falahat/easy-podcast.git
cd easy-podcast
pip install -e .[dev,notebook]
```

## Quick Start

### Command Line Interface

```bash
# Download episodes from an RSS feed
easy_podcast "https://example.com/podcast/rss.xml"

# Specify custom data directory  
easy_podcast "https://example.com/podcast/rss.xml" --data-dir ./my_podcasts

# List episodes without downloading
easy_podcast "https://example.com/podcast/rss.xml" --list-only

# Disable progress bars
easy_podcast "https://example.com/podcast/rss.xml" --no-progress
```

### Python API

```python
from easy_podcast.manager import PodcastManager

# Create manager from RSS URL (downloads and parses automatically)
manager = PodcastManager.from_rss_url("https://example.com/podcast/rss.xml")

if manager:
    podcast = manager.get_podcast()
    print(f"Podcast: {podcast.title}")
    
    # Get new episodes to download
    new_episodes = manager.get_new_episodes()
    print(f"Found {len(new_episodes)} new episodes")
    
    # Download episodes with progress tracking
    successful, skipped, failed = manager.download_episodes(new_episodes)
    print(f"Downloaded: {successful}, Skipped: {skipped}, Failed: {failed}")
```

### Working with Existing Podcast Data

```python
# Load manager from existing podcast folder
manager = PodcastManager.from_podcast_folder("data/My Podcast/")

if manager:
    # Continue downloading new episodes
    new_episodes = manager.get_new_episodes()
    manager.download_episodes(new_episodes)
```

## Data Storage Structure

Podcast data is organized in a clear directory structure:

```
data/
└── [Sanitized Podcast Name]/
    ├── episodes.jsonl      # Episode metadata (one JSON object per line)
    ├── rss.xml            # Cached RSS feed
    └── downloads/         # Downloaded audio files
        ├── episode1.mp3
        ├── episode2.mp3
        └── ...
```

**Important**: Episode objects store filenames only (e.g., `"727175.mp3"`), not full paths. Use `manager.get_episode_audio_path(episode)` to get complete file paths.

## Development

### Setting up Development Environment

```bash
git clone https://github.com/falahat/easy-podcast.git
cd easy-podcast

# Create virtual environment (note the .venv name)
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install in development mode
pip install -e .[dev,notebook]
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=easy_podcast --cov-report=html

# Run specific test file
pytest tests/test_manager.py -v
```

### Code Quality Tools

The project uses:

- **Black** for code formatting
- **mypy** for type checking  
- **flake8** for linting
- **pytest** for testing

```bash
# Format code
black src/ tests/

# Type checking
mypy src/easy_podcast/

# Linting
flake8 src/easy_podcast/
```

## Core Components

The package is built with a modular architecture:

- **`PodcastManager`** - Main orchestrator for the complete workflow
- **`Episode`/`Podcast`** - Data models with computed properties
- **`EpisodeTracker`** - JSONL-based metadata persistence
- **`PodcastParser`** - RSS feed parsing with custom episode ID extraction
- **`PodcastDownloader`** - HTTP downloads with progress tracking

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Ensure all tests pass (`pytest`)
5. Check code quality (`black src/ tests/` and `mypy src/`)
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
