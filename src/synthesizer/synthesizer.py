"""Newsletter synthesis using Claude Sonnet API."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from .prompts import SYNTHESIS_SYSTEM_PROMPT, SYNTHESIS_USER_PROMPT


class Synthesizer:
    def __init__(self, api_key: str | None = None):
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-6"

    def synthesize(
        self,
        analyzed_items: list[dict],
        newsletter_type: str = "daily",
        output_dir: str | None = None,
    ) -> str:
        """Generate newsletter from analyzed items."""
        print(f"[synthesizer] Generating {newsletter_type} newsletter from {len(analyzed_items)} items...")

        # Prepare items for the prompt — remove unnecessary fields
        clean_items = []
        for item in analyzed_items:
            clean = {
                "title": item.get("title", ""),
                "source_type": item.get("source_type", ""),
                "source_channel": item.get("source_channel", ""),
                "source_tier": item.get("source_tier", 2),
                "category": item.get("category", ""),
                "relevance_score": item.get("relevance_score", 0),
                "key_points": item.get("key_points", []),
                "action_type": item.get("action_type", "info_only"),
                "why_relevant": item.get("why_relevant", ""),
                "has_practical_demo": item.get("has_practical_demo", False),
                "is_original_content": item.get("is_original_content", True),
                "original_url": item.get("original_url", ""),
                "duplicate_group_id": item.get("duplicate_group_id"),
                "is_best_in_group": item.get("is_best_in_group", True),
                "video_duration_minutes": item.get("video_duration_minutes"),
                "stars": item.get("stars"),
                "forks": item.get("forks"),
                "dedup_group": item.get("dedup_group"),
            }
            # Remove None values
            clean = {k: v for k, v in clean.items() if v is not None}
            clean_items.append(clean)

        # Count unique sources
        sources = set(item.get("source_channel", "") for item in clean_items)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        user_prompt = SYNTHESIS_USER_PROMPT.format(
            item_count=len(clean_items),
            source_count=len(sources),
            date=date_str,
            newsletter_type=newsletter_type,
            items_json=json.dumps(clean_items, ensure_ascii=False, indent=2),
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYNTHESIS_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            newsletter_md = response.content[0].text
            print(f"[synthesizer] Newsletter generated ({len(newsletter_md)} chars)")

            # Save output
            if output_dir:
                out_path = Path(output_dir)
                out_path.mkdir(parents=True, exist_ok=True)
                output_file = out_path / "newsletter.md"
                output_file.write_text(newsletter_md, encoding="utf-8")
                print(f"[synthesizer] Saved to {output_file}")

            return newsletter_md
        except Exception as e:
            print(f"[synthesizer] Error: {e}")
            raise
