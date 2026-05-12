"""Collects top posts from configured subreddits via public RSS (no API key needed)."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import requests

from .base import BaseCollector


class RedditCollector(BaseCollector):
    source_type = "reddit"
    request_delay = 1.5

    # RSS namespaces used by Reddit
    NS = {
        "atom": "http://www.w3.org/2005/Atom",
        "media": "http://search.yahoo.com/mrss/",
    }

    def collect(self, sources: list[dict], tier: str = "tier1") -> list[dict]:
        results = []

        for source in sources:
            sub_name = source.get("subreddit", "")
            if not sub_name:
                continue
            print(f"[reddit] Checking r/{sub_name} via RSS...")

            posts = self.retry(self._get_rss_posts, sub_name)
            if not posts:
                print(f"[reddit] No posts from r/{sub_name}")
                continue

            for post in posts:
                post_id = f"reddit_{sub_name}_{post['id']}"
                if self.is_processed(post_id):
                    continue
                results.append(post)
                self.save_item(post, f"{sub_name}_{post['id']}")

            self.throttle()

        self.collected = results
        print(f"[reddit] Collected {len(results)} posts")
        return results

    def _get_rss_posts(self, subreddit_name: str, limit: int = 25) -> list[dict]:
        """Fetch top posts from subreddit public RSS feed."""
        url = f"https://www.reddit.com/r/{subreddit_name}/hot.rss?limit={limit}"
        headers = {"User-Agent": "SurfingTheAIWave/1.0 (newsletter bot)"}

        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        posts = []

        # Reddit RSS is Atom format
        for entry in root.findall("atom:entry", self.NS):
            title_el = entry.find("atom:title", self.NS)
            link_el = entry.find("atom:link", self.NS)
            content_el = entry.find("atom:content", self.NS)
            id_el = entry.find("atom:id", self.NS)
            updated_el = entry.find("atom:updated", self.NS)
            author_el = entry.find("atom:author/atom:name", self.NS)

            if title_el is None or link_el is None:
                continue

            title = (title_el.text or "").strip()
            post_url = link_el.get("href", "")
            raw_content = (content_el.text or "") if content_el is not None else ""
            post_id_full = (id_el.text or "").strip()
            published_date = (updated_el.text or "") if updated_el is not None else ""
            author = (author_el.text or "") if author_el is not None else ""

            # Derive short ID from the Atom id (e.g. t3_abc123)
            short_id = post_id_full.split("_")[-1] if "_" in post_id_full else post_id_full[-8:]

            # Strip HTML from content to get plain text body
            body = self._strip_html(raw_content)[:3000]

            # Extract any external link from content (link posts have it)
            external_link = self._extract_external_link(raw_content)

            posts.append({
                "id": f"reddit_{subreddit_name}_{short_id}",
                "source_type": "reddit",
                "source_channel": f"r/{subreddit_name}",
                "source_tier": 1,
                "title": title,
                "body": body,
                "score": None,   # RSS doesn't expose score
                "num_comments": None,
                "original_url": post_url,
                "published_date": published_date,
                "author": author,
                "link_url": external_link,
            })

        return posts[:15]  # Cap at 15 per subreddit

    def _strip_html(self, html: str) -> str:
        """Remove HTML tags and decode entities to plain text."""
        import html as html_lib
        import re
        text = re.sub(r"<[^>]+>", " ", html)
        text = html_lib.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _extract_external_link(self, content_html: str) -> str | None:
        """Try to find an external link in the post content (link posts)."""
        import re
        # Look for href in content that isn't reddit.com itself
        hrefs = re.findall(r'href="([^"]+)"', content_html)
        for href in hrefs:
            parsed = urlparse(href)
            if parsed.netloc and "reddit.com" not in parsed.netloc:
                return href
        return None
