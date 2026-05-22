"""Collects latest entries from AI newsletter RSS feeds."""
from __future__ import annotations

import xml.etree.ElementTree as ET
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
        """Parse RSS/Atom feed and return recent entries using xml.etree.ElementTree."""
        try:
            resp = requests.get(rss_url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            })
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception as e:
            print(f"[newsletters] Feed error for {source_name}: {e}")
            return []

        ns_atom = "http://www.w3.org/2005/Atom"
        is_atom = root.tag == f"{{{ns_atom}}}feed" or "feed" in root.tag.lower()

        entries = []
        if is_atom:
            items = root.findall(f"{{{ns_atom}}}entry")
        else:
            channel = root.find("channel")
            items = channel.findall("item") if channel is not None else root.findall(".//item")

        for item in items[:5]:
            if is_atom:
                title_el = item.find(f"{{{ns_atom}}}title")
                link_el = item.find(f"{{{ns_atom}}}link")
                link = link_el.get("href", "") if link_el is not None else ""
                pub_el = item.find(f"{{{ns_atom}}}published") or item.find(f"{{{ns_atom}}}updated")
                id_el = item.find(f"{{{ns_atom}}}id")
                summary_el = item.find(f"{{{ns_atom}}}summary") or item.find(f"{{{ns_atom}}}content")
            else:
                title_el = item.find("title")
                link_el = item.find("link")
                link = (link_el.text or "").strip() if link_el is not None else ""
                pub_el = item.find("pubDate")
                id_el = item.find("guid")
                summary_el = item.find("description")

            title = (title_el.text or "").strip() if title_el is not None else ""
            published = (pub_el.text or "").strip() if pub_el is not None else ""
            item_id = (id_el.text or link or "").strip() if id_el is not None else link
            entry_id = f"nl_{source_name.lower().replace(' ', '_')}_{item_id}"

            content = ""
            if summary_el is not None and summary_el.text:
                content = self._html_to_text(summary_el.text)[:5000]

            if len(content) < 100 and link:
                scraped = self._scrape_page(link, source_name)
                if scraped and len(scraped) > len(content):
                    content = scraped[:5000]

            entries.append({
                "id": entry_id,
                "source_type": "newsletter",
                "source_channel": source_name,
                "source_tier": 1,
                "title": title,
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
