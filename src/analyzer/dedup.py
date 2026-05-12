"""Semantic deduplication using embeddings and cosine similarity."""
from __future__ import annotations

import hashlib

import numpy as np


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a)
    b_arr = np.array(b)
    dot = np.dot(a_arr, b_arr)
    norm = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def title_hash(title: str) -> str:
    normalized = title.lower().strip()
    return hashlib.md5(normalized.encode()).hexdigest()


def find_duplicate_groups(
    items: list[dict],
    similarity_threshold: float = 0.90,
) -> list[dict]:
    """Group items by semantic similarity. Mutates items in-place with group info.

    Each item must have an 'embedding' field (list of floats).
    Returns the same list with 'duplicate_group_id' and 'is_best_in_group' fields added.
    """
    # Step 1: Exact title dedup
    title_hashes: dict[str, list[int]] = {}
    for i, item in enumerate(items):
        h = title_hash(item.get("title", ""))
        title_hashes.setdefault(h, []).append(i)

    # Step 2: Semantic dedup via embeddings
    n = len(items)
    assigned_group: dict[int, str] = {}
    group_counter = 0

    for i in range(n):
        if i in assigned_group:
            continue
        emb_i = items[i].get("embedding")
        if not emb_i:
            continue

        group_members = [i]
        for j in range(i + 1, n):
            if j in assigned_group:
                continue
            emb_j = items[j].get("embedding")
            if not emb_j:
                continue

            sim = cosine_similarity(emb_i, emb_j)
            if sim >= similarity_threshold:
                group_members.append(j)

        if len(group_members) > 1:
            group_id = f"group_{group_counter}"
            group_counter += 1
            for idx in group_members:
                assigned_group[idx] = group_id

    # Also group exact title matches
    for h, indices in title_hashes.items():
        if len(indices) > 1:
            # Check if already in a semantic group
            existing_group = None
            for idx in indices:
                if idx in assigned_group:
                    existing_group = assigned_group[idx]
                    break
            group_id = existing_group or f"group_{group_counter}"
            if not existing_group:
                group_counter += 1
            for idx in indices:
                assigned_group[idx] = group_id

    # Step 3: For each group, pick the best item
    groups: dict[str, list[int]] = {}
    for idx, gid in assigned_group.items():
        groups.setdefault(gid, []).append(idx)

    for i, item in enumerate(items):
        item["duplicate_group_id"] = assigned_group.get(i)
        item["is_best_in_group"] = True  # default

    for gid, members in groups.items():
        best_idx = _pick_best(items, members)
        for idx in members:
            items[idx]["is_best_in_group"] = (idx == best_idx)

    return items


def _pick_best(items: list[dict], indices: list[int]) -> int:
    """Pick the best item in a duplicate group based on:
    (a) source tier (lower = better), (b) has practical demo, (c) relevance score.
    """
    def score(idx: int) -> tuple:
        item = items[idx]
        tier = item.get("source_tier", 2)
        has_demo = 1 if item.get("has_practical_demo") else 0
        relevance = item.get("relevance_score", 0)
        return (-tier, has_demo, relevance)  # negative tier so tier 1 > tier 2

    return max(indices, key=score)
