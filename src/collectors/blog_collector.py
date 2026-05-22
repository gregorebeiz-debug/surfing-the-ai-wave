"""Collects latest posts from AI blogs and technical voices."""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urljoin

import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup

from .base import BaseCollector


class BlogCollector(BaseCollector):
    source_type = "blogs"
    request_delay = 1.5

    def collect(self, sources: list[dict], tier: str = "tier1") -> list[dict]:  # noqa: ARG002
        results = []

        for source in sources:
            name = source.get("name", "")
            rss_url = source.get("rss_url")
            blog_url = source.get("blog_url")

            print(f"[blogs] Checking {name}...")

            if rss_url:
                entries = self.retry(self._parse_rss, rss_url, name)
            elif blog_url:
                entries = self.retry(self._scrape_blog, blog_url, name)
            else:
                print(f"[blogs] No URL for {name}, skipping")
                continue

            if entries:
                for entry in entries:
                    if not self.is_processed(entry["id"]):
                        results.append(entry)
                        safe_name = entry["id"].replace("/", "_").replace(":", "_")[:80]
                        self.save_item(entry, safe_name)

            self.throttle()

        self.collected = results
        print(f"[blogs] Collected {len(results)} posts")
        return results

    def _parse_rss(self, rss_url: str, source_name: str) -> list[dict]:
        """Parse RSS/Atom feed for blog posts using xml.etree.ElementTree."""
        try:
            resp = requests.get(rss_url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            })
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception as e:
            print(f"[blogs] Feed error for {source_name}: {e}")
            return []

        # Detect format: RSS 2.0 vs Atom
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
            entry_id = f"blog_{source_name.lower().replace(' ', '_')}_{item_id}"

            content = ""
            if summary_el is not None and summary_el.text:
                soup = BeautifulSoup(summary_el.text, "html.parser")
                content = soup.get_text(separator=" ", strip=True)[:5000]

            if len(content) < 200 and link:
                full_content = self._fetch_article(link, source_name)
                if full_content and len(full_content) > len(content):
                    content = full_content

            entries.append({
                "id": entry_id,
                "source_type": "blog",
                "source_channel": source_name,
                "source_tier": 1,
                "title": title,
                "content": content,
                "original_url": link,
                "published_date": published,
            })

        return entries

    def _scrape_blog(self, blog_url: str, source_name: str) -> list[dict]:
        """Fallback: scrape blog page for recent posts when no RSS is available."""
        try:
            resp = requests.get(blog_url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            })
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            entries = []
            # Look for article-like elements
            articles = soup.find_all("article")[:5]
            if not articles:
                articles = soup.find_all("div", class_=lambda c: c and ("post" in c or "article" in c or "entry" in c))[:5]

            for i, article in enumerate(articles):
                title_tag = article.find(["h1", "h2", "h3", "a"])
                title = title_tag.get_text(strip=True) if title_tag else f"Post {i+1}"

                link = ""
                if title_tag and title_tag.name == "a":
                    link = title_tag.get("href", "")
                else:
                    a_tag = article.find("a")
                    link = a_tag.get("href", "") if a_tag else ""

                if link and not link.startswith("http"):
                    link = urljoin(blog_url, link)
                if not link or not link.startswith("http"):
                    continue

                # Get initial content from the listing page
                content = article.get_text(separator=" ", strip=True)[:500]

                # Fetch full article content if we have a link
                if link:
                    full_content = self._fetch_article(link, source_name)
                    if full_content and len(full_content) > len(content):
                        content = full_content

                entry_id = f"blog_{source_name.lower().replace(' ', '_')}_{link or i}"
                entries.append({
                    "id": entry_id,
                    "source_type": "blog",
                    "source_channel": source_name,
                    "source_tier": 1,
                    "title": title,
                    "content": content,
                    "original_url": link,
                    "published_date": "",
                })

            return entries
        except Exception as e:
            print(f"[blogs] Error scraping {blog_url}: {e}")
            return []

    def _fetch_article(self, url: str, source_name: str) -> str:
        """Fetch full article content from a URL."""
        try:
            resp = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            })
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove noise
            for tag in soup.find_all(["nav", "header", "footer", "script", "style", "aside"]):
                tag.decompose()

            # Try article containers in priority order
            article = (
                soup.find("article")
                or soup.find("main")
                or soup.find("div", class_=lambda c: c and any(
                    k in c for k in ["content", "article", "post", "entry", "blog"]
                ))
            )

            if article:
                text = article.get_text(separator="\n", strip=True)
            else:
                text = soup.find("body").get_text(separator="\n", strip=True) if soup.find("body") else ""

            # Clean up
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            text = "\n".join(lines)
            return text[:4000] if len(text) > 200 else ""
        except Exception as e:
            print(f"[blogs] Could not fetch article from {source_name}: {e}")
            return ""
