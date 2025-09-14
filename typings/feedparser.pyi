# Type stubs for feedparser
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

# Feed entry class
class FeedParserDict(dict[str, Any]):
    """A dictionary-like object with attribute access."""

    # Core feed attributes
    feed: "FeedParserDict"
    entries: List["FeedParserDict"]

    # HTTP response attributes
    status: int
    href: str
    etag: Optional[str]
    modified: Optional[str]
    headers: Dict[str, str]

    # Feed metadata attributes (when used as feed object)
    title: str
    title_detail: Dict[str, str]
    link: str
    links: List[Dict[str, str]]
    description: str
    description_detail: Dict[str, str]
    updated: str
    updated_parsed: Optional[time.struct_time]
    published: str
    published_parsed: Optional[time.struct_time]
    author: str
    author_detail: Dict[str, str]
    language: str
    image: Dict[str, str]

    # iTunes specific attributes
    itunes_author: str
    itunes_subtitle: str
    itunes_summary: str
    itunes_owner: Dict[str, str]
    itunes_image: Dict[str, str]
    itunes_category: List[Dict[str, str]]
    itunes_explicit: str

    # Entry/episode attributes (when used as entry object)
    id: str
    guidislink: bool
    summary: str
    summary_detail: Dict[str, str]
    content: List[Dict[str, str]]
    enclosures: List[Dict[str, str]]

    # iTunes episode attributes
    itunes_duration: str
    itunes_episode: str
    itunes_season: str
    itunes_episodetype: str

    # Custom attributes (like supercast_episode_id)
    supercast_episode_id: str

    def __init__(self, *_args: Any, **_kwargs: Any) -> None: ...

# Main feedparser functions
def parse(
    _data_or_url: Union[str, bytes],
    _etag: Optional[str] = None,
    _modified: Optional[Union[str, time.struct_time, datetime]] = None,
    _agent: Optional[str] = None,
    _referrer: Optional[str] = None,
    _handlers: Optional[List[Any]] = None,
    _request_headers: Optional[Dict[str, str]] = None,
    _response_headers: Optional[Dict[str, str]] = None,
    _resolve_relative_uris: bool = True,
    _sanitize_html: bool = True,
    **_kwargs: Any,
) -> FeedParserDict: ...

# Exception classes
class CharacterEncodingOverride(UserWarning):
    pass

class NonXMLContentType(UserWarning):
    pass

class UndeclaredNamespace(ValueError):
    pass

# Version info
__version__: str
VERSION: str
