# Have a nice, easy interface

Common Tasks (User Stories):

1. I have an RSS link, download my podcast
2. I want to see my podcasts downloaded
3. I want to download new episodes of my podcast

```python

rss_link = "https://example.com/podcast/rss.xml"
from easy_podcast import download_podcast, get_all_podcasts

podcast: Podcast = download_podcast(rss_link)

podcasts: List[Podcast] = get_all_podcasts()

for episode in podcast.episodes:
    episode.download() # downloads audio, skips if already downloaded (by default)

# Or, we can configure
with downloader.Downloader(max_concurrent_downloads=2, delay_seconds=10, show_progress=True, max_downloads=50) as downloader:
    downloader.download_episodes(podcast.episodes)
```