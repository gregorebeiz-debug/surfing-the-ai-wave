"""Main orchestrator for Surfing the AI Wave newsletter pipeline.

In Routine mode (default): only runs collection + delivery.
Analysis and synthesis are handled by the Claude Routine directly.

Usage:
    python -m src.main --test          # Test collection with limited sources
    python -m src.main --tier tier1    # Full daily collection
    python -m src.main --tier all      # Full weekly collection (includes Tier 2)
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone

from .collect import main as collect_main


def main():
    parser = argparse.ArgumentParser(description="Surfing the AI Wave — Newsletter Pipeline")
    parser.add_argument("--tier", choices=["tier1", "all"], default="tier1",
                        help="Which tiers to scan (tier1=daily, all=weekly)")
    parser.add_argument("--test", action="store_true",
                        help="Run in test mode (limited sources)")
    args = parser.parse_args()

    start_time = time.time()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    newsletter_type = "weekly" if args.tier == "all" else "daily"

    print(f"{'='*60}")
    print(f"  Surfing the AI Wave — {newsletter_type.upper()} Pipeline")
    print(f"  Date: {today} | Tier: {args.tier}")
    print(f"  Mode: Routine (collect only — Claude handles analysis/synthesis)")
    print(f"{'='*60}\n")

    # Run collection
    collect_main()

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"  Collection complete in {elapsed / 60:.1f} minutes")
    print(f"  Raw data at: data/raw/{today}/")
    print(f"  Next: Claude Routine reads data and writes newsletter")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
