"""State management: tracks processed items between runs."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path("state.json")
RETENTION_DAYS = 7


def load_state() -> dict:
    """Load state from file, or return empty state."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return _empty_state()


def save_state(state: dict) -> None:
    """Save state to file."""
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[state] Saved state to {STATE_FILE}")


def prune_state(state: dict) -> dict:
    """Remove entries older than RETENTION_DAYS to prevent unbounded growth."""
    # For ID-based lists, we keep only the last N entries
    max_ids = 500  # keep last 500 IDs per type
    processed = state.get("processed", {})

    for key in ["youtube_ids", "reddit_ids", "newsletter_ids", "blog_ids"]:
        if key in processed and len(processed[key]) > max_ids:
            processed[key] = processed[key][-max_ids:]

    state["processed"] = processed
    return state


def update_processed(state: dict, source_type: str, item_ids: list[str]) -> None:
    """Add processed item IDs to state."""
    key = f"{source_type}_ids"
    if "processed" not in state:
        state["processed"] = {}
    existing = state["processed"].get(key, [])
    existing.extend(item_ids)
    state["processed"][key] = existing


def update_github_seen(state: dict, repo: str, tag: str) -> None:
    """Update last-seen version for a monitored GitHub repo."""
    if "processed" not in state:
        state["processed"] = {}
    if "github_repos_seen" not in state["processed"]:
        state["processed"]["github_repos_seen"] = {}
    state["processed"]["github_repos_seen"][repo] = tag


def update_stats(state: dict, stats: dict) -> None:
    """Update run statistics."""
    state["stats"] = stats


def _empty_state() -> dict:
    return {
        "last_run": None,
        "last_weekly_run": None,
        "processed": {
            "youtube_ids": [],
            "reddit_ids": [],
            "github_repos_seen": {},
            "newsletter_ids": [],
            "blog_ids": [],
        },
        "stats": {},
    }
