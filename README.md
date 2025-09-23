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

#### 1. Download a Podcast by RSS URL

```python
from easy_podcast.factory import create_manager_from_rss

manager = create_manager_from_rss("https://example.com/podcast/rss.xml")
if manager:
    print(f"Loaded: {manager.get_podcast().title}")
```

#### 2. Basic Podcast Fields

```python
podcast = manager.get_podcast()

print(f"Title: {podcast.title}")
print(f"Episodes: {len(podcast.episodes)}")
print(f"Data dir: {manager.get_podcast_data_dir()}")
```

#### 3. Inspect an Episode

```python
from easy_podcast.models import EpisodeFile

episode = podcast.episodes[0]
print(f"Episode: {episode.title}")
print(f"Duration: {episode.duration_seconds}s")
print(f"Size: {episode.size} bytes")

# Check if files exist
audio_exists = manager.episode_file_exists(episode, EpisodeFile.AUDIO)
audio_path = manager.get_episode_file_path(episode, EpisodeFile.AUDIO)
print(f"Downloaded: {audio_exists} -> {audio_path}")
```

#### 4. Download a Single Episode

```python
new_episodes = manager.get_new_episodes()
if new_episodes:
    result = manager.download_episodes([new_episodes[0]])
    print(f"Downloaded: {result.successful}, Failed: {result.failed}")
```

#### 5. Download Multiple Episodes

```python
new_episodes = manager.get_new_episodes()
print(f"Found {len(new_episodes)} new episodes")

if new_episodes:
    result = manager.download_episodes(new_episodes)
    print(f"Results: {result.successful} downloaded, {result.skipped} skipped, {result.failed} failed")
```

### Working with Existing Podcast Data

```python
from easy_podcast.factory import create_manager_from_storage

# Load existing podcast by title
manager = create_manager_from_storage("My Podcast", "./data")

if manager:
    new_episodes = manager.get_new_episodes()
    if new_episodes:
        result = manager.download_episodes(new_episodes)
        print(f"Downloaded {result.successful} new episodes")
```

## Data Storage Structure

Podcast data is organized in a clear directory structure:

```
data/
└── [Sanitized Podcast Name]/
    ├── podcast.json        # Podcast metadata (title, URL, etc.)
    ├── episodes.jsonl      # Episode metadata (one JSON object per line)
    ├── rss.xml            # Cached RSS feed
    ├── episode1.mp3       # Downloaded audio files (named by episode ID)
    ├── episode2.mp3
    ├── episode1_transcript.json  # Transcript files (when available)
    └── episode2_transcript.json
```

**Important**: Episode objects store filenames only (e.g., `"test123.mp3"`), not full paths. Use `manager.get_episode_file_path(episode, EpisodeFile.AUDIO)` to get complete file paths for audio files, or `manager.get_episode_file_path(episode, EpisodeFile.TRANSCRIPT)` for transcript files.

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
