"""Collects latest entries from AI newsletter RSS feeds."""
from __future__ import annotations

from datetime import datetime, timezone

import feedparser

from .base import BaseCollector


class NewsletterCollector(BaseCollector):
    source_type = "newsletters"
    request_delay = 1.0

    def collect(self, sources: list[dict], tier: str = "tier1") -> list[dict]:
        results = []

        for source in sources:
            name = source.get("name", "")
            rss_url = source.get("rss_url")
            if not rss_url:
                print(f"[newsletters] No RSS URL for {name}, skipping")
                continue

            print(f"[newsletters] Checking {name}...")
            entries = self.retry(self._parse_feed, rss_url, name)
            if entries:
                for entry in entries:
                    if not self.is_processed(entry["id"]):
                        results.append(entry)
                        self.save_item(entry, entry["id"].replace("/", "_").replace(":", "_")[:80])

            self.throttle()

        self.collected = results
        print(f"[newsletters] Collected {len(results)} entries")
        return results

    def _parse_feed(self, rss_url: str, source_name: str) -> list[dict]:
        """Parse RSS feed and return recent entries."""
        feed = feedparser.parse(rss_url)

        if feed.bozo and not feed.entries:
            print(f"[newsletters] Feed error for {source_name}: {feed.bozo_exception}")
            return []

        entries = []
        for entry in feed.entries[:5]:  # last 5 entries
            entry_id = f"nl_{source_name.lower().replace(' ', '_')}_{entry.get('id', entry.get('link', ''))}"

            published = ""
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()

            # Get content — try content first, then summary
            content = ""
            if hasattr(entry, "content") and entry.content:
                content = entry.content[0].get("value", "")[:5000]
            elif hasattr(entry, "summary"):
                content = (entry.summary or "")[:5000]

            entries.append({
                "id": entry_id,
                "source_type": "newsletter",
                "source_channel": source_name,
                "source_tier": 1,
                "title": entry.get("title", ""),
                "content": content,
                "original_url": entry.get("link", ""),
                "published_date": published,
            })

        return entries
