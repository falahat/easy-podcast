# Easy Storage: GUID-Based Directory Structure Proposal

## Overview

This proposal outlines a simplified storage architecture using GUID-based directory structures to eliminate the complexity of title-based paths and provide better data organization with automatic deduplication.

## Problem Statement

### Current Storage Issues
1. **Complex Path Management**: Title-based directories require sanitization and complex path logic
2. **Split Storage Formats**: Episodes use JSONL, Podcasts use JSON, creating inconsistent APIs
3. **Manual Deduplication**: Complex GUID filtering logic spread across multiple methods
4. **Type Safety Gaps**: Generic operations lack compile-time type checking
5. **Tight Coupling**: Storage logic is tightly coupled to business logic
6. **Directory Structure Fragility**: Renaming podcasts breaks file paths
7. **Scattered Repository Logic**: No clear separation between storage concerns and business logic

### Current Structure
```
data/
└── [Sanitized Podcast Name]/
    ├── episodes.jsonl      # Episode metadata (JSONL format)
    ├── podcast.json        # Podcast metadata (JSON format)
    ├── rss.xml            # Cached RSS feed
    └── downloads/         # Audio files by episode ID
        ├── episode1.mp3
        └── episode2.mp3
```

## Proposed Solution: Option 2 - GUID-Based Directory Structure

### New Storage Architecture

```
data/
├── podcasts/
│   ├── podcast-guid-123.json     # Individual podcast files
│   ├── podcast-guid-456.json     # One file per podcast
│   └── ...
├── episodes/
│   ├── episode-guid-789.json     # Individual episode files
│   ├── episode-guid-abc.json     # One file per episode
│   └── ...
├── downloads/                    # Audio files by episode GUID
│   ├── episode-guid-789.mp3
│   ├── episode-guid-abc.mp3
│   └── ...
└── cache/                        # RSS cache by podcast GUID
    ├── podcast-guid-123.xml
    └── podcast-guid-456.xml
```

### Key Benefits

1. **Elimination of Path Sanitization**: No more `sanitize_filename()` logic
2. **Consistent Storage Format**: All entities use individual JSON files
3. **Natural GUID Integration**: File names ARE the GUIDs
4. **Simplified Repository**: One save/load pattern for all entity types
5. **Immutable Paths**: Renaming podcasts doesn't break file references
6. **Easy Backup/Sync**: Clear entity-based organization

## Implementation Plan

### Phase 1: Create New Repository Architecture

#### Step 1.1: Define New Storage Interface

```python
# First, ensure we have the Storable protocol
from typing import Protocol

class Storable(Protocol):
    """Protocol for entities that can be stored by GUID."""
    guid: str
    
    def to_json(self) -> dict:
        """Convert entity to JSON-serializable dict."""
        ...
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Storable':
        """Create entity from dict."""
        ...

# New simplified storage interface
class GuidStorage:
    """GUID-based storage with consistent JSON format for all entities."""
    
    def __init__(self, base_dir: str = "./data"):
        self.base_dir = base_dir
        self.podcasts_dir = os.path.join(base_dir, "podcasts")
        self.episodes_dir = os.path.join(base_dir, "episodes") 
        self.downloads_dir = os.path.join(base_dir, "downloads")
        self.cache_dir = os.path.join(base_dir, "cache")
        self._ensure_directories()
    
    def save_entity(self, entity: Storable, entity_type: str) -> bool:
        """Save any entity by GUID."""
        file_path = self._get_entity_path(entity.guid, entity_type)
        return self._write_json(file_path, entity.to_json())
    
    def load_entity(self, guid: str, entity_type: str, entity_class: Type[T]) -> Optional[T]:
        """Load entity by GUID."""
        file_path = self._get_entity_path(guid, entity_type)
        data = self._read_json(file_path)
        return entity_class.from_dict(data) if data else None
    
    def list_entities(self, entity_type: str) -> List[str]:
        """List all GUIDs for entity type."""
        dir_path = self._get_entity_dir(entity_type)
        files = os.listdir(dir_path) if os.path.exists(dir_path) else []
        return [f.replace('.json', '') for f in files if f.endswith('.json')]
```

#### Step 1.2: Create Generic Type-Safe Repositories

```python
class Repository(Generic[T]):
    """Generic repository for GUID-based entities with type safety."""
    
    def __init__(self, storage: GuidStorage, entity_type: str, entity_class: Type[T]):
        self.storage = storage
        self.entity_type = entity_type
        self.entity_class = entity_class
    
    def save(self, entity: T) -> bool:
        """Save entity by GUID with automatic deduplication."""
        # T must be Storable, so entity.guid and entity.to_json() are guaranteed
        return self.storage.save_entity(entity, self.entity_type)
    
    def load(self, guid: str) -> Optional[T]:
        """Load entity by GUID."""
        return self.storage.load_entity(guid, self.entity_type, self.entity_class)
    
    def list_all(self) -> List[T]:
        """Load all entities of this type."""
        guids = self.storage.list_entities(self.entity_type)
        entities = []
        for guid in guids:
            entity = self.load(guid)
            if entity:
                entities.append(entity)
        return entities
    
    def exists(self, guid: str) -> bool:
        """Check if entity exists by GUID."""
        return guid in self.storage.list_entities(self.entity_type)
    
    def delete(self, guid: str) -> bool:
        """Delete entity by GUID."""
        file_path = self.storage._get_entity_path(guid, self.entity_type)
        try:
            os.remove(file_path)
            return True
        except OSError:
            return False

class EpisodeRepository(Repository[Episode]):
    """Type-safe repository for Episodes with zero boilerplate."""
    
    def __init__(self, storage: GuidStorage):
        super().__init__(storage, "episodes", Episode)
    
    # All base methods inherited with correct Episode typing!
    # Only add domain-specific methods:
    
    def load_for_podcast(self, podcast_guid: str) -> List[Episode]:
        """Load all episodes for a specific podcast."""
        all_episodes = self.list_all()
        return [ep for ep in all_episodes if ep.podcast_guid == podcast_guid]
    
    def filter_new(self, episodes: List[Episode]) -> List[Episode]:
        """Filter episodes that don't exist in storage."""
        existing_guids = set(self.storage.list_entities(self.entity_type))
        return [ep for ep in episodes if ep.guid not in existing_guids]

class PodcastRepository(Repository[Podcast]):
    """Type-safe repository for Podcasts with zero boilerplate."""
    
    def __init__(self, storage: GuidStorage):
        super().__init__(storage, "podcasts", Podcast)
    
    # All base methods inherited with correct Podcast typing!
    # Add domain-specific methods if needed in the future.

class Persistence:
    """Clean access to type-safe repositories without delegation bloat."""
    
    def __init__(self, storage: GuidStorage):
        self.storage = storage
        self._repositories = {}
    
    def repo(self, entity_class: Type[T]) -> Repository[T]:
        """Get the correct repository for an entity type."""
        if entity_class not in self._repositories:
            if entity_class == Episode:
                self._repositories[entity_class] = EpisodeRepository(self.storage)
            elif entity_class == Podcast:
                self._repositories[entity_class] = PodcastRepository(self.storage)
            else:
                raise ValueError(f"No repository configured for {entity_class}")
        
        return self._repositories[entity_class]

# Usage examples:
# persistence.repo(Episode).save(episode)
# persistence.repo(Episode).load("episode-guid")
# persistence.repo(Episode).filter_new(episodes)
# persistence.repo(Podcast).save(podcast)
# persistence.repo(Podcast).list_all()
```

### Phase 2: Update Models for GUID Relationships

#### Step 2.1: Ensure Models Implement Storable Protocol

```python
@dataclass
class Episode:
    """Episode model implementing Storable protocol."""
    # Existing fields...
    id: str
    published: str
    title: str
    author: str
    duration_seconds: int
    size: int
    audio_link: str
    image: str
    guid: str = ""  # Required by Storable protocol
    
    # NEW: Reference to parent podcast
    podcast_guid: str = ""  # Links episode to its podcast
    
    def to_json(self) -> dict:
        """Convert to JSON dict for storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Episode':
        """Create Episode from dict."""
        return cls(**data)

@dataclass 
class Podcast:
    """Podcast model implementing Storable protocol."""
    # Existing fields...
    title: str
    rss_url: str
    safe_title: str
    guid: str = ""  # Required by Storable protocol (use RSS URL)
    episodes: List[Episode] = field(default_factory=list)
    
    def to_json(self) -> dict:
        """Convert to JSON dict for storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Podcast':
        """Create Podcast from dict."""
        # Convert episode dicts back to Episode objects
        if 'episodes' in data:
            data['episodes'] = [Episode.from_dict(ep) for ep in data['episodes']]
        return cls(**data)
```

#### Step 2.2: Ensure Podcast GUID Population

```python
# In parser.py - ensure podcast GUID is set
def from_content(self, rss_url: str, content: bytes) -> Optional[Podcast]:
    # ... existing parsing logic ...
    
    podcast = Podcast(
        title=title,
        rss_url=rss_url,
        safe_title=safe_title,
        guid=rss_url,  # Use RSS URL as podcast GUID
        episodes=episodes
    )
    
    # Set podcast_guid on all episodes
    for episode in episodes:
        episode.podcast_guid = podcast.guid
    
    return podcast
```

### Phase 3: Update Path Management

#### Step 3.1: Implement GUID-Based Path Methods

```python
class Persistence:
    def get_episode_audio_path(self, episode: Episode) -> str:
        """Get path to episode audio file using GUID."""
        return os.path.join(self.storage.downloads_dir, f"{episode.guid}.mp3")
    
    def get_episode_transcript_path(self, episode: Episode) -> str:
        """Get path to episode transcript file using GUID."""
        return os.path.join(self.storage.downloads_dir, f"{episode.guid}_transcript.json")
    
    def get_rss_cache_path(self, podcast: Podcast) -> str:
        """Get path to RSS cache using podcast GUID."""
        return os.path.join(self.storage.cache_dir, f"{podcast.guid}.xml")
    
    def episode_audio_exists(self, episode: Episode) -> bool:
        """Check if episode audio file exists."""
        return os.path.exists(self.get_episode_audio_path(episode))
```

### Phase 4: Update Manager Integration

#### Step 4.1: Update PodcastManager Constructor

```python
class PodcastManager:
    def __init__(
        self,
        podcast: Podcast,
        persistence: Persistence,
        downloader: EpisodeDownloader,
    ):
        self.podcast = podcast
        self.persistence = persistence
        self.downloader = downloader
        
        # Ensure podcast is saved with episodes linked
        self.persistence.repo(Podcast).save(podcast)
        for episode in podcast.episodes:
            episode.podcast_guid = podcast.guid
            self.persistence.repo(Episode).save(episode)
```

#### Step 4.2: Simplify Manager Methods

```python
class PodcastManager:
    def get_new_episodes(self) -> List[Episode]:
        """Get episodes that haven't been downloaded yet."""
        return self.persistence.repo(Episode).filter_new(self.podcast.episodes)
    
    def download_episodes(self, episodes: List[Episode]) -> DownloadSummary:
        """Download episodes with automatic storage updates."""
        downloads = self._prepare_downloads(episodes)
        summary = self.downloader.download_multiple(downloads)
        
        if summary.successful > 0:
            # Save successfully downloaded episodes
            for episode in episodes:
                if self.episode_audio_exists(episode):
                    self.persistence.repo(Episode).save(episode)
        
        return summary
    
    def episode_audio_exists(self, episode: Episode) -> bool:
        return self.persistence.episode_audio_exists(episode)
```

### Phase 5: Update Factory Functions

#### Step 5.1: Update Dependency Creation

```python
def _create_dependencies(data_dir: str) -> tuple[GuidStorage, Persistence, EpisodeDownloader]:
    """Create new GUID-based dependencies."""
    storage = GuidStorage(data_dir)
    persistence = Persistence(storage)
    downloader = EpisodeDownloader(storage)
    return storage, persistence, downloader

def create_manager_from_rss(rss_url: str, data_dir: str = "./data") -> Optional[PodcastManager]:
    """Create manager from RSS with new storage."""
    # ... RSS parsing logic ...
    
    # Create dependencies
    storage, persistence, downloader = _create_dependencies(data_dir)
    
    # Save podcast and episodes
    persistence.repo(Podcast).save(podcast)
    for episode in podcast.episodes:
        episode.podcast_guid = podcast.guid
        persistence.repo(Episode).save(episode)
    
    # Save RSS cache
    cache_path = persistence.get_rss_cache_path(podcast)
    storage._write_bytes(cache_path, rss_content)
    
    return PodcastManager(podcast, persistence, downloader)
```

### Phase 6: Testing Strategy

#### Step 6.1: Unit Tests for New Storage

```python
class TestGuidStorage(unittest.TestCase):
    def test_save_and_load_podcast(self):
        storage = GuidStorage(self.test_dir)
        persistence = Persistence(storage)
        
        podcast = Podcast(
            title="Test Podcast",
            rss_url="http://test.com/rss",
            safe_title="Test_Podcast", 
            guid="test-podcast-guid"
        )
        
        # Save and reload
        self.assertTrue(persistence.repo(Podcast).save(podcast))
        loaded = persistence.repo(Podcast).load("test-podcast-guid")
        
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.title, "Test Podcast")
    
    def test_episode_relationships(self):
        # Test episode-podcast relationships work correctly
        pass
```

#### Step 6.2: Integration Tests

```python
class TestGuidIntegration(unittest.TestCase):
    def test_end_to_end_workflow(self):
        # Test complete workflow from RSS parsing to episode download
        # Verify all GUID relationships work correctly
        pass
```

## Benefits Analysis

### Code Reduction
- **Repository**: 230 lines → 80 lines (65% reduction)
- **Path Management**: Eliminated `sanitize_filename()`, complex directory logic
- **Storage Interface**: Unified save/load for all entity types

### Performance Improvements
- **Faster Queries**: Direct GUID-based file access
- **No Directory Scanning**: List operations use directory listings
- **Atomic Operations**: Individual file operations are naturally atomic

### Maintenance Benefits
- **Immutable Paths**: GUIDs never change, eliminating path breakage
- **Clear Organization**: Entity type directories provide clear structure
- **Easy Debugging**: File names directly correspond to entity GUIDs

### Simplicity Benefits
- **No Migration Needed**: Clean implementation since no existing data to migrate
- **Consistent API**: Same save/load pattern for all entity types
- **Type Safety**: Compile-time guarantees with minimal boilerplate

## Implementation Timeline

**Note: No migration or backward compatibility needed since this is a fresh implementation.**

1. **Week 1**: Implement `GuidStorage` and type-safe repository classes
2. **Week 2**: Update models, add `podcast_guid` relationships, and update `PodcastManager`  
3. **Week 3**: Update factory functions, comprehensive testing, and documentation

## Conclusion

This GUID-based directory structure provides **massive simplification** while maintaining all existing functionality. Key advantages:

### Architecture Benefits
- **Zero Boilerplate**: Type-safe repositories inherit all functionality from `Repository[T]`
- **Storable Protocol**: Both Episode and Podcast implement common interface with `guid`, `to_json()`, `from_dict()`
- **Clean Access Pattern**: `persistence.repo(Episode).save(episode)` - no delegation bloat
- **Type Safety**: Compile-time guarantees with `EpisodeRepository` and `PodcastRepository`
- **No Migration Complexity**: Fresh implementation means no backward compatibility needed

### Code Quality Improvements  
- **65% Code Reduction**: From 230+ lines to ~80 lines in repository layer
- **Elimination of Delegation**: No more useless wrapper methods in UnifiedRepository
- **Unified Storage Format**: Consistent JSON files for all entity types via Storable protocol
- **Natural GUID Integration**: File names ARE the GUIDs - no indirection

### Developer Experience
- **Intuitive API**: `persistence.repo(EntityType).method()` pattern is self-documenting
- **Easy Testing**: Direct file operations, no complex setup needed  
- **Clear Organization**: Entity types in separate directories
- **Immutable Paths**: GUIDs never change, eliminating path breakage

The combination of **GUID-based storage** + **generic type-safe repositories** + **Storable protocol** + **clean Persistence access** creates an elegant, maintainable architecture that's significantly simpler than the current title-based approach. The Persistence class provides unified access to repositories without any delegation bloat, while maintaining full type safety throughout the system.
