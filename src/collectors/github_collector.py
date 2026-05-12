"""Collects trending AI repos and release info from GitHub."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from .base import BaseCollector

GITHUB_API = "https://api.github.com"


class GitHubCollector(BaseCollector):
    source_type = "github"
    request_delay = 0.5

    def __init__(self, state: dict | None = None, token: str | None = None):
        super().__init__(state)
        self.headers = {"Accept": "application/vnd.github+json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def collect(self, sources: dict, tier: str = "tier1") -> list[dict]:
        results = []

        # 1. Trending repos by topic
        if tier == "tier1":
            topics = sources.get("trending_topics", [])
            for topic in topics:
                trending = self.retry(self._get_trending, topic)
                if trending:
                    results.extend(trending)
                self.throttle()

        # 2. Releases from monitored repos
        monitored = sources.get("monitored_repos", [])
        for repo in monitored:
            release = self.retry(self._get_latest_release, repo)
            if release and not self.is_processed(release["id"]):
                results.append(release)
            self.throttle()

        self.collected = results
        print(f"[github] Collected {len(results)} items")
        return results

    def _get_trending(self, topic: str) -> list[dict]:
        """Find repos created/updated in last 24h with significant stars."""
        since = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        query = f"topic:{topic} pushed:>{since} stars:>10"
        url = f"{GITHUB_API}/search/repositories"
        params = {"q": query, "sort": "stars", "order": "desc", "per_page": 10}

        resp = requests.get(url, headers=self.headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for repo in data.get("items", []):
            repo_id = f"gh_trending_{repo['full_name']}"
            if self.is_processed(repo_id):
                continue
            results.append({
                "id": repo_id,
                "source_type": "github",
                "category": "trending_repo",
                "source_tier": 1,
                "title": repo["full_name"],
                "description": repo.get("description", ""),
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "language": repo.get("language", ""),
                "topics": repo.get("topics", []),
                "original_url": repo["html_url"],
                "created_at": repo["created_at"],
                "updated_at": repo["updated_at"],
            })
        return results

    def _get_latest_release(self, repo: str) -> dict | None:
        """Check for new releases on a monitored repo."""
        url = f"{GITHUB_API}/repos/{repo}/releases/latest"
        try:
            resp = requests.get(url, headers=self.headers, timeout=15)
            if resp.status_code == 404:
                # Try tags instead
                return self._get_latest_tag(repo)
            resp.raise_for_status()
            release = resp.json()

            release_id = f"gh_release_{repo}_{release['tag_name']}"
            state_key = "github_repos_seen"
            seen = self.state.get("processed", {}).get(state_key, {})
            if seen.get(repo) == release["tag_name"]:
                return None

            return {
                "id": release_id,
                "source_type": "github",
                "category": "release",
                "source_tier": 1,
                "title": f"{repo} {release['tag_name']}",
                "description": release.get("body", "")[:2000],
                "tag": release["tag_name"],
                "repo": repo,
                "original_url": release["html_url"],
                "published_date": release.get("published_at", ""),
            }
        except Exception as e:
            print(f"[github] Error checking {repo}: {e}")
            return None

    def _get_latest_tag(self, repo: str) -> dict | None:
        """Fallback: check tags if no releases exist."""
        url = f"{GITHUB_API}/repos/{repo}/tags"
        try:
            resp = requests.get(url, headers=self.headers, params={"per_page": 1}, timeout=15)
            resp.raise_for_status()
            tags = resp.json()
            if not tags:
                return None
            tag = tags[0]
            tag_id = f"gh_tag_{repo}_{tag['name']}"
            seen = self.state.get("processed", {}).get("github_repos_seen", {})
            if seen.get(repo) == tag["name"]:
                return None
            return {
                "id": tag_id,
                "source_type": "github",
                "category": "release",
                "source_tier": 1,
                "title": f"{repo} {tag['name']}",
                "description": "",
                "tag": tag["name"],
                "repo": repo,
                "original_url": f"https://github.com/{repo}/releases/tag/{tag['name']}",
                "published_date": "",
            }
        except Exception:
            return None
