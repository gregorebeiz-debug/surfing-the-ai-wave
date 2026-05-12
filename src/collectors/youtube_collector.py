"""Collects YouTube video transcripts and descriptions from configured channels."""
from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET

import requests
from youtube_transcript_api import YouTubeTranscriptApi

from .base import BaseCollector


class YouTubeCollector(BaseCollector):
    source_type = "youtube"
    request_delay = 1.5  # be gentle with YouTube

    def __init__(self, state: dict | None = None):
        super().__init__(state=state)
        # Support cookie-based auth to bypass IP blocks
        cookie_path = os.getenv("YOUTUBE_COOKIE_FILE", "config/youtube_cookies.txt")
        http_client = None
        if os.path.exists(cookie_path):
            import http.cookiejar
            session = requests.Session()
            cj = http.cookiejar.MozillaCookieJar(cookie_path)
            cj.load(ignore_discard=True, ignore_expires=True)
            session.cookies = cj
            http_client = session
            print(f"[youtube] Using cookies from {cookie_path}")
        self.ytt_api = YouTubeTranscriptApi(http_client=http_client)

    def collect(self, sources: list[dict], tier: str = "tier1") -> list[dict]:
        results = []
        for source in sources:
            handle = source.get("handle", "")
            channel_id = source.get("channel_id")
            name = source.get("name", handle)
            print(f"[youtube] Checking {name} ({handle})...")

            videos = self.retry(self._get_recent_videos, handle, channel_id)
            if not videos:
                print(f"[youtube] No videos found for {name}")
                continue

            for video in videos:
                vid = video["id"]
                if self.is_processed(vid):
                    continue

                # Try transcript first, fall back to RSS description
                transcript = self.retry(self._get_transcript, vid)
                content = transcript or video.get("description", "")

                item = {
                    "id": f"yt_{vid}",
                    "source_type": "youtube",
                    "source_channel": name,
                    "source_tier": 1 if tier == "tier1" else 2,
                    "title": video["title"],
                    "video_id": vid,
                    "published_date": video.get("published", ""),
                    "original_url": f"https://www.youtube.com/watch?v={vid}",
                    "transcript": transcript or "",
                    "description": video.get("description", ""),
                    "content": content,
                    "has_transcript": transcript is not None,
                    "dedup_group": source.get("dedup_group"),
                }
                self.save_item(item, f"{handle.strip('@')}_{vid}")
                results.append(item)
                self.throttle()

        self.collected = results
        transcript_count = sum(1 for r in results if r["has_transcript"])
        print(f"[youtube] Collected {len(results)} new videos ({transcript_count} with transcripts, {len(results) - transcript_count} with descriptions only)")
        return results

    def _get_recent_videos(self, handle: str, channel_id: str | None = None) -> list[dict]:
        """Fetch recent videos from a channel via its RSS feed, including descriptions."""
        if not channel_id:
            channel_id = self._resolve_channel_id(handle)
        if not channel_id:
            return []

        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        resp = requests.get(feed_url, timeout=15)
        resp.raise_for_status()

        root = ET.fromstring(resp.text)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
            "media": "http://search.yahoo.com/mrss/",
        }

        videos = []
        for entry in root.findall("atom:entry", ns)[:5]:  # last 5 videos
            vid = entry.find("yt:videoId", ns)
            title = entry.find("atom:title", ns)
            published = entry.find("atom:published", ns)

            # Extract description from media:group > media:description
            description = ""
            media_group = entry.find("media:group", ns)
            if media_group is not None:
                desc_elem = media_group.find("media:description", ns)
                if desc_elem is not None and desc_elem.text:
                    description = desc_elem.text.strip()

            if vid is not None and title is not None:
                videos.append({
                    "id": vid.text,
                    "title": title.text,
                    "published": published.text if published is not None else "",
                    "description": description,
                })
        return videos

    def _resolve_channel_id(self, handle: str) -> str | None:
        """Resolve a @handle to a channel ID by scraping the channel page."""
        url = f"https://www.youtube.com/{handle}"
        try:
            resp = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            })
            resp.raise_for_status()
            match = re.search(r'"externalId":"(UC[^"]+)"', resp.text)
            if match:
                return match.group(1)
            match = re.search(r'<meta itemprop="channelId" content="(UC[^"]+)"', resp.text)
            if match:
                return match.group(1)
        except Exception as e:
            print(f"[youtube] Could not resolve {handle}: {e}")
        return None

    def _get_transcript(self, video_id: str) -> str | None:
        """Get transcript for a video. Falls back through multiple strategies."""
        # Strategy 1: Try specific languages
        for langs in [["en", "es"], ["en-US", "en-GB", "es-419"], None]:
            try:
                if langs:
                    transcript = self.ytt_api.fetch(video_id, languages=langs)
                else:
                    # Strategy 2: Try without language filter (any available)
                    transcript = self.ytt_api.fetch(video_id)
                text = " ".join(snippet.text for snippet in transcript.snippets)
                if text.strip():
                    return text
            except Exception:
                continue

        # All strategies failed
        print(f"[youtube] No transcript for {video_id} (IP may be blocked)")
        return None
