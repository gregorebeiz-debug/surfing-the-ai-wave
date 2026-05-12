"""Collection-only entry point for Claude Routine.

Runs all collectors and saves raw data to data/raw/YYYY-MM-DD/.
The Routine (Claude) then reads and analyzes these files directly.
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

import yaml

from .collectors.blog_collector import BlogCollector
from .collectors.github_collector import GitHubCollector
from .collectors.newsletter_collector import NewsletterCollector
from .collectors.reddit_collector import RedditCollector
from .collectors.youtube_collector import YouTubeCollector
from .state import load_state, prune_state, save_state, update_processed, update_github_seen


def load_config() -> dict:
    from pathlib import Path
    config_path = Path("config/sources.yaml")
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Surfing the AI Wave — Data Collection")
    parser.add_argument("--tier", choices=["tier1", "all"], default="tier1",
                        help="Which tiers to scan (tier1=daily, all=weekly)")
    parser.add_argument("--test", action="store_true",
                        help="Test mode: limit to 2 sources per collector")
    args = parser.parse_args()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tier = args.tier

    print(f"{'='*60}")
    print(f"  Surfing the AI Wave — Collection Phase")
    print(f"  Date: {today} | Tier: {tier}")
    print(f"{'='*60}\n")

    config = load_config()
    state = load_state()
    state = prune_state(state)

    all_items = []

    # YouTube
    print("── YouTube ──")
    yt = YouTubeCollector(state=state)
    yt_sources = config.get("youtube", {}).get("tier1", [])
    if tier == "all":
        yt_sources += config.get("youtube", {}).get("tier2", [])
    if args.test:
        yt_sources = yt_sources[:2]
    yt_items = yt.collect(yt_sources, tier)
    all_items.extend(yt_items)
    update_processed(state, "youtube", [item["id"] for item in yt_items])

    # GitHub
    print("\n── GitHub ──")
    gh = GitHubCollector(state=state, token=os.getenv("GITHUB_TOKEN"))
    gh_sources = config.get("github", {}).get("tier1", {})
    gh_items = gh.collect(gh_sources, tier)
    all_items.extend(gh_items)
    for item in gh_items:
        if item.get("category") == "release" and item.get("repo") and item.get("tag"):
            update_github_seen(state, item["repo"], item["tag"])
        else:
            update_processed(state, "github", [item["id"]])

    # Reddit
    print("\n── Reddit ──")
    reddit = RedditCollector(state=state)
    reddit_sources = config.get("reddit", {}).get("tier1", [])
    if tier == "all":
        reddit_sources += config.get("reddit", {}).get("tier2", [])
    if args.test:
        reddit_sources = reddit_sources[:1]
    reddit_items = reddit.collect(reddit_sources, tier)
    all_items.extend(reddit_items)
    update_processed(state, "reddit", [item["id"] for item in reddit_items])

    # Newsletters
    print("\n── Newsletters ──")
    nl = NewsletterCollector(state=state)
    nl_sources = config.get("newsletters", {}).get("tier1", [])
    if tier == "all":
        nl_sources += config.get("newsletters", {}).get("tier2", [])
    nl_items = nl.collect(nl_sources, tier)
    all_items.extend(nl_items)
    update_processed(state, "newsletter", [item["id"] for item in nl_items])

    # Blogs
    print("\n── Blogs ──")
    blog = BlogCollector(state=state)
    blog_sources = config.get("official_sources", {}).get("tier1", [])
    blog_sources += config.get("technical_voices", {}).get("tier1", [])
    if tier == "all":
        blog_sources += config.get("technical_voices", {}).get("tier2", [])
    blog_sources = [s for s in blog_sources if s.get("blog_url") or s.get("rss_url")]
    blog_items = blog.collect(blog_sources, tier)
    all_items.extend(blog_items)
    update_processed(state, "blog", [item["id"] for item in blog_items])

    # Save state
    save_state(state)

    print(f"\n{'='*60}")
    print(f"  Collection complete: {len(all_items)} items")
    print(f"  Raw data saved to: data/raw/{today}/")
    print(f"{'='*60}\n")

    return all_items


if __name__ == "__main__":
    main()
