"""Main orchestrator for Surfing the AI Wave newsletter pipeline."""
from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .analyzer.analyzer import Analyzer
from .collectors.blog_collector import BlogCollector
from .collectors.github_collector import GitHubCollector
from .collectors.newsletter_collector import NewsletterCollector
from .collectors.reddit_collector import RedditCollector
from .collectors.youtube_collector import YouTubeCollector
from .delivery.email_sender import send_newsletter_email
from .delivery.pdf_generator import markdown_to_pdf
from .state import load_state, prune_state, save_state, update_processed, update_github_seen, update_stats
from .synthesizer.synthesizer import Synthesizer


def load_config() -> dict:
    config_path = Path("config/sources.yaml")
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Surfing the AI Wave — Newsletter Pipeline")
    parser.add_argument("--tier", choices=["tier1", "all"], default="tier1",
                        help="Which tiers to scan (tier1=daily, all=weekly)")
    parser.add_argument("--test", action="store_true",
                        help="Run in test mode (limited sources, no email)")
    parser.add_argument("--skip-collect", action="store_true",
                        help="Skip collection, use existing raw data")
    parser.add_argument("--skip-email", action="store_true",
                        help="Skip email delivery")
    args = parser.parse_args()

    start_time = time.time()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tier = args.tier
    newsletter_type = "weekly" if tier == "all" else "daily"

    print(f"{'='*60}")
    print(f"  Surfing the AI Wave — {newsletter_type.upper()} Pipeline")
    print(f"  Date: {today} | Tier: {tier}")
    print(f"{'='*60}\n")

    # Load config and state
    config = load_config()
    state = load_state()
    state = prune_state(state)

    all_items = []
    stats = {
        "date": today,
        "tier": tier,
        "total_items_collected": 0,
        "items_after_analysis": 0,
        "items_in_newsletter": 0,
        "gemini_api_calls": 0,
        "sonnet_api_calls": 0,
    }

    # ── PHASE 1: COLLECTION ──────────────────────────────────
    if not args.skip_collect:
        print("\n📡 PHASE 1: Collection\n")

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
        # Combine official sources and technical voices
        blog_sources = config.get("official_sources", {}).get("tier1", [])
        blog_sources += config.get("technical_voices", {}).get("tier1", [])
        if tier == "all":
            blog_sources += config.get("technical_voices", {}).get("tier2", [])
        # Filter to sources with blog_url or rss_url
        blog_sources = [s for s in blog_sources if s.get("blog_url") or s.get("rss_url")]
        blog_items = blog.collect(blog_sources, tier)
        all_items.extend(blog_items)
        update_processed(state, "blog", [item["id"] for item in blog_items])

        stats["total_items_collected"] = len(all_items)
        print(f"\n✅ Collection complete: {len(all_items)} items total\n")

    # ── PHASE 2: ANALYSIS ────────────────────────────────────
    print("\n🔬 PHASE 2: Analysis\n")
    data_dir = os.getenv("DATA_DIR", "data")
    analysis_output = f"{data_dir}/analyzed/{today}"

    analyzer = Analyzer()
    analyzed_items = analyzer.analyze_all(all_items, output_dir=analysis_output)
    stats["items_after_analysis"] = len(analyzed_items)
    stats["gemini_api_calls"] = len(all_items) + (len(all_items) // 20 + 1)  # analysis + embedding batches

    print(f"\n✅ Analysis complete: {len(analyzed_items)} items after filtering\n")

    # ── PHASE 3: SYNTHESIS ───────────────────────────────────
    print("\n✍️ PHASE 3: Synthesis\n")
    newsletter_output = f"{data_dir}/output/{today}"

    synthesizer = Synthesizer()
    newsletter_md = synthesizer.synthesize(
        analyzed_items,
        newsletter_type=newsletter_type,
        output_dir=newsletter_output,
    )
    stats["sonnet_api_calls"] = 1
    stats["items_in_newsletter"] = len(analyzed_items)

    print(f"\n✅ Synthesis complete\n")

    # ── PHASE 4: DELIVERY ────────────────────────────────────
    print("\n📬 PHASE 4: Delivery\n")
    pdf_path = f"{newsletter_output}/surfing-ai-wave-{today}.pdf"
    markdown_to_pdf(newsletter_md, pdf_path)

    # Archive newsletter
    archive_dir = Path(f"newsletters/{today[:4]}/{today[5:7]}")
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / f"{today}.md").write_text(newsletter_md, encoding="utf-8")

    if not args.skip_email and not args.test:
        send_newsletter_email(
            newsletter_md=newsletter_md,
            pdf_path=pdf_path,
            date_str=today,
            newsletter_type=newsletter_type,
        )
    else:
        print("[email] Skipped (test mode or --skip-email)")

    # ── FINALIZE ─────────────────────────────────────────────
    elapsed = time.time() - start_time
    stats["execution_time_minutes"] = round(elapsed / 60, 1)
    update_stats(state, stats)

    if tier == "all":
        state["last_weekly_run"] = datetime.now(timezone.utc).isoformat()

    save_state(state)

    print(f"\n{'='*60}")
    print(f"  Pipeline complete in {stats['execution_time_minutes']} minutes")
    print(f"  Collected: {stats['total_items_collected']} | Analyzed: {stats['items_after_analysis']} | In newsletter: {stats['items_in_newsletter']}")
    print(f"  Gemini calls: {stats['gemini_api_calls']} | Sonnet calls: {stats['sonnet_api_calls']}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
