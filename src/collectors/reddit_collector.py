"""Collects top posts from configured subreddits."""
from __future__ import annotations

import os

import praw

from .base import BaseCollector


class RedditCollector(BaseCollector):
    source_type = "reddit"
    request_delay = 1.0

    def __init__(self, state: dict | None = None):
        super().__init__(state)
        self.reddit = None

    def _init_reddit(self):
        if self.reddit is None:
            self.reddit = praw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID", ""),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
                user_agent="SurfingTheAIWave/1.0",
            )

    def collect(self, sources: list[dict], tier: str = "tier1") -> list[dict]:
        self._init_reddit()
        results = []

        for source in sources:
            sub_name = source["subreddit"]
            print(f"[reddit] Checking r/{sub_name}...")

            posts = self.retry(self._get_top_posts, sub_name)
            if not posts:
                continue

            for post in posts:
                post_id = f"reddit_{sub_name}_{post['id']}"
                if self.is_processed(post_id):
                    continue
                results.append(post)
                self.save_item(post, f"{sub_name}_{post['id']}")

            self.throttle()

        self.collected = results
        print(f"[reddit] Collected {len(results)} posts")
        return results

    def _get_top_posts(self, subreddit_name: str, limit: int = 15) -> list[dict]:
        """Get top posts from last 24 hours."""
        sub = self.reddit.subreddit(subreddit_name)
        posts = []

        for post in sub.hot(limit=limit):
            if post.stickied:
                continue

            # Get top comments for context
            post.comment_sort = "best"
            post.comments.replace_more(limit=0)
            top_comments = []
            for comment in post.comments[:5]:
                top_comments.append({
                    "body": comment.body[:500],
                    "score": comment.score,
                })

            posts.append({
                "id": f"reddit_{subreddit_name}_{post.id}",
                "source_type": "reddit",
                "source_channel": f"r/{subreddit_name}",
                "source_tier": 1,
                "title": post.title,
                "body": (post.selftext or "")[:3000],
                "score": post.score,
                "num_comments": post.num_comments,
                "original_url": f"https://reddit.com{post.permalink}",
                "published_date": str(post.created_utc),
                "top_comments": top_comments,
                "link_url": post.url if not post.is_self else None,
            })

        return posts
