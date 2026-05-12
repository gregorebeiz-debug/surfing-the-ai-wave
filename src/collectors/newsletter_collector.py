"""Collects latest entries from AI newsletter RSS feeds."""
from __future__ import annotations

from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

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

            # Get content — try content first, then summary, then scrape page
            content = ""
            if hasattr(entry, "content") and entry.content:
                raw = entry.content[0].get("value", "")
                content = self._html_to_text(raw)[:5000]
            elif hasattr(entry, "summary") and entry.summary:
                content = self._html_to_text(entry.summary)[:5000]

            # If content is too short, scrape the page directly
            link = entry.get("link", "")
            if len(content) < 100 and link:
                scraped = self._scrape_page(link, source_name)
                if scraped and len(scraped) > len(content):
                    content = scraped[:5000]

            entries.append({
                "id": entry_id,
                "source_type": "newsletter",
                "source_channel": source_name,
                "source_tier": 1,
                "title": entry.get("title", ""),
                "content": content,
                "original_url": link,
                "published_date": published,
            })

        return entries

    def _scrape_page(self, url: str, source_name: str) -> str:
        """Scrape newsletter page content when RSS doesn't provide it."""
        try:
            resp = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            })
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove navigation, headers, footers, scripts
            for tag in soup.find_all(["nav", "header", "footer", "script", "style", "aside"]):
                tag.decompose()

            # Try common article containers
            article = (
                soup.find("article")
                or soup.find("main")
                or soup.find("div", class_=lambda c: c and ("content" in c or "article" in c or "post" in c))
                or soup.find("div", id=lambda i: i and ("content" in i or "article" in i))
            )

            if article:
                text = article.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)

            # Clean up: remove excessive whitespace
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            text = "\n".join(lines)

            if len(text) > 100:
                return text
        except Exception as e:
            print(f"[newsletters] Could not scrape {source_name} at {url}: {e}")
        return ""

    def _html_to_text(self, html: str) -> str:
        """Convert HTML content to plain text."""
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(separator="\n", strip=True)
