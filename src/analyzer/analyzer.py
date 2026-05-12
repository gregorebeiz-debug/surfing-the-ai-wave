"""Main analyzer: sends items to Gemini Flash for extraction/classification/scoring."""
from __future__ import annotations

import json
import os
from pathlib import Path

from google import genai

from .dedup import find_duplicate_groups
from .prompts import ANALYSIS_SYSTEM_PROMPT, ANALYSIS_USER_PROMPT


class Analyzer:
    def __init__(self, gemini_api_key: str | None = None):
        api_key = gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
        self.embed_model = "text-embedding-004"

    def analyze_all(self, raw_items: list[dict], output_dir: str | None = None) -> list[dict]:
        """Analyze all collected items: extract, score, embed, dedup."""
        print(f"[analyzer] Analyzing {len(raw_items)} items...")

        # Step 1: Analyze each item with Gemini Flash
        analyzed = []
        for i, item in enumerate(raw_items):
            print(f"[analyzer] Item {i+1}/{len(raw_items)}: {item.get('title', '')[:60]}...")
            analysis = self._analyze_item(item)
            if analysis:
                merged = {**item, **analysis}
                analyzed.append(merged)

        # Step 2: Generate embeddings for dedup
        print(f"[analyzer] Generating embeddings for {len(analyzed)} items...")
        self._add_embeddings(analyzed)

        # Step 3: Find duplicate groups
        print("[analyzer] Running deduplication...")
        analyzed = find_duplicate_groups(analyzed)

        # Step 4: Filter by minimum relevance
        before_filter = len(analyzed)
        analyzed = [item for item in analyzed if item.get("relevance_score", 0) >= 4.0]
        print(f"[analyzer] Filtered {before_filter - len(analyzed)} low-relevance items")

        # Step 5: Sort by relevance score
        analyzed.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        # Step 6: Save output
        if output_dir:
            out_path = Path(output_dir)
            out_path.mkdir(parents=True, exist_ok=True)
            output_file = out_path / "analysis.json"
            # Remove embeddings from output (they're large and not needed downstream)
            output_items = [{k: v for k, v in item.items() if k != "embedding"} for item in analyzed]
            output_file.write_text(json.dumps(output_items, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[analyzer] Saved {len(output_items)} items to {output_file}")

        return analyzed

    def _analyze_item(self, item: dict) -> dict | None:
        """Send a single item to Gemini Flash for analysis."""
        # Prepare content: use transcript for YouTube, content for others
        content_text = item.get("transcript") or item.get("content") or item.get("description") or ""
        if not content_text.strip():
            content_text = item.get("title", "")

        # Truncate to ~4000 chars to stay within context
        content_text = content_text[:4000]

        prompt = ANALYSIS_USER_PROMPT.format(
            source_type=item.get("source_type", "unknown"),
            source_channel=item.get("source_channel", "unknown"),
            title=item.get("title", ""),
            content=content_text,
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "system_instruction": ANALYSIS_SYSTEM_PROMPT,
                    "temperature": 0.1,
                },
            )

            text = response.text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"[analyzer] JSON parse error for '{item.get('title', '')[:40]}': {e}")
            return None
        except Exception as e:
            print(f"[analyzer] Error analyzing '{item.get('title', '')[:40]}': {e}")
            return None

    def _add_embeddings(self, items: list[dict]) -> None:
        """Generate embeddings for all items using Gemini embedding model."""
        batch_size = 20  # Gemini supports batched embedding requests
        texts = []
        for item in items:
            text = f"{item.get('title', '')} {' '.join(item.get('key_points', []))}"
            texts.append(text[:512])

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                result = self.client.models.embed_content(
                    model=self.embed_model,
                    contents=batch,
                )
                for j, embedding in enumerate(result.embeddings):
                    items[i + j]["embedding"] = embedding.values
            except Exception as e:
                print(f"[analyzer] Embedding error at batch {i}: {e}")
                # Assign empty embeddings for failed items
                for j in range(len(batch)):
                    if i + j < len(items) and "embedding" not in items[i + j]:
                        items[i + j]["embedding"] = []
