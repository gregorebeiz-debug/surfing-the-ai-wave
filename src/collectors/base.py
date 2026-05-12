"""Base collector with retry logic, rate limiting, and standard output format."""
from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

BOGOTA_OFFSET = -5  # UTC-5


def today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def raw_data_dir(source_type: str) -> Path:
    base = Path(os.getenv("DATA_DIR", "data"))
    d = base / "raw" / today_str() / source_type
    d.mkdir(parents=True, exist_ok=True)
    return d


class BaseCollector(ABC):
    """Base class for all data collectors."""

    source_type: str = "unknown"
    max_retries: int = 3
    retry_delay: float = 2.0
    request_delay: float = 1.0  # seconds between requests

    def __init__(self, state: dict | None = None):
        self.state = state or {}
        self.collected: list[dict] = []

    @abstractmethod
    def collect(self, sources: list[dict], tier: str = "tier1") -> list[dict]:
        """Collect data from configured sources. Returns list of raw items."""
        ...

    def is_processed(self, item_id: str) -> bool:
        key = f"{self.source_type}_ids"
        processed = self.state.get("processed", {}).get(key, [])
        return item_id in processed

    def save_item(self, item: dict, filename: str) -> Path:
        out_dir = raw_data_dir(self.source_type)
        path = out_dir / f"{filename}.json"
        path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def retry(self, fn, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    print(f"[{self.source_type}] Failed after {self.max_retries} retries: {e}")
                    return None
                wait = self.retry_delay * (2 ** attempt)
                print(f"[{self.source_type}] Retry {attempt + 1}/{self.max_retries} in {wait}s: {e}")
                time.sleep(wait)

    def throttle(self):
        time.sleep(self.request_delay)
