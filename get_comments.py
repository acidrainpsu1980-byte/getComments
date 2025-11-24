"""
CLI tool for exporting Facebook group post comments to CSV using the Graph API.

Usage example:
    export FB_ACCESS_TOKEN="<YOUR_TOKEN>"
    python get_comments.py --group-id 123456789 --output comments.csv

You need a Facebook user access token with permissions to read the target group's posts and comments.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, List, Optional

import requests

GRAPH_API_VERSION = "v19.0"
BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class FacebookAPIError(RuntimeError):
    """Raised when the Facebook Graph API returns a non-success response."""


@dataclass
class CommentRow:
    post_id: str
    post_message: str
    post_created_time: str
    comment_id: str
    comment_message: str
    comment_created_time: str
    comment_author_id: str
    comment_author_name: str
    comment_like_count: int
    comment_reply_count: int

    def to_list(self) -> List[str]:
        return [
            self.post_id,
            self.post_message,
            self.post_created_time,
            self.comment_id,
            self.comment_message,
            self.comment_created_time,
            self.comment_author_id,
            self.comment_author_name,
            str(self.comment_like_count),
            str(self.comment_reply_count),
        ]


@dataclass
class FacebookClient:
    access_token: str

    def _get(self, path: str, params: Optional[Dict[str, str]] = None) -> Dict:
        params = params or {}
        params.setdefault("access_token", self.access_token)
        url = f"{BASE_URL}/{path}"
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            try:
                payload = response.json()
                message = payload.get("error", {}).get("message", response.text)
            except ValueError:
                message = response.text
            raise FacebookAPIError(f"Graph API request failed ({response.status_code}): {message}")
        try:
            return response.json()
        except ValueError as exc:
            raise FacebookAPIError(f"Invalid JSON from Graph API: {response.text}") from exc

    def iter_group_posts(
        self,
        group_id: str,
        *,
        limit: int = 100,
        since: Optional[str] = None,
        until: Optional[str] = None,
        max_posts: Optional[int] = None,
    ) -> Iterator[Dict]:
        """
        Iterate through posts in the group feed.

        Args:
            group_id: Numeric group ID.
            limit: Max number of posts to fetch per page (Graph API limit parameter).
            since: ISO8601 or Unix timestamp string for earliest post.
            until: ISO8601 or Unix timestamp string for latest post.
            max_posts: Optional cap on number of posts retrieved overall.
        """

        params: Dict[str, str] = {
            "limit": str(limit),
            "fields": "id,message,created_time",
        }
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        fetched = 0
        next_url = None
        while True:
            payload = (
                self._get(f"{group_id}/feed", params=params)
                if next_url is None
                else self._get(next_url.replace(f"{BASE_URL}/", ""))
            )

            data = payload.get("data", [])
            for post in data:
                yield post
                fetched += 1
                if max_posts is not None and fetched >= max_posts:
                    return

            paging = payload.get("paging", {})
            cursors = paging.get("cursors", {})
            after = cursors.get("after")
            next_url = paging.get("next") if after else None
            if not next_url:
                return

    def iter_comments(
        self,
        post_id: str,
        *,
        limit: int = 100,
        order: str = "chronological",
    ) -> Iterator[Dict]:
        """Iterate through comments on a post with pagination."""
        params: Dict[str, str] = {
            "limit": str(limit),
            "order": order,
            "fields": "id,message,created_time,from,like_count,comment_count",
        }

        next_url = None
        while True:
            payload = (
                self._get(f"{post_id}/comments", params=params)
                if next_url is None
                else self._get(next_url.replace(f"{BASE_URL}/", ""))
            )
            for comment in payload.get("data", []):
                yield comment

            paging = payload.get("paging", {})
            cursors = paging.get("cursors", {})
            after = cursors.get("after")
            next_url = paging.get("next") if after else None
            if not next_url:
                return


def collect_comments(
    client: FacebookClient,
    group_id: str,
    *,
    since: Optional[str],
    until: Optional[str],
    max_posts: Optional[int],
) -> Iterable[CommentRow]:
    """Yield ``CommentRow`` objects for all comments on group posts."""
    for post in client.iter_group_posts(group_id, since=since, until=until, max_posts=max_posts):
        post_id = post.get("id", "")
        post_message = post.get("message", "")
        post_created_time = post.get("created_time", "")
        for comment in client.iter_comments(post_id):
            author = comment.get("from", {}) or {}
            yield CommentRow(
                post_id=post_id,
                post_message=post_message,
                post_created_time=post_created_time,
                comment_id=comment.get("id", ""),
                comment_message=comment.get("message", ""),
                comment_created_time=comment.get("created_time", ""),
                comment_author_id=author.get("id", ""),
                comment_author_name=author.get("name", ""),
                comment_like_count=int(comment.get("like_count", 0) or 0),
                comment_reply_count=int(comment.get("comment_count", 0) or 0),
            )


def write_comments_to_csv(rows: Iterable[CommentRow], output_path: str) -> None:
    headers = [
        "post_id",
        "post_message",
        "post_created_time",
        "comment_id",
        "comment_message",
        "comment_created_time",
        "comment_author_id",
        "comment_author_name",
        "comment_like_count",
        "comment_reply_count",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row.to_list())


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Facebook group comments to CSV")
    parser.add_argument("--group-id", required=True, help="Target Facebook group numeric ID")
    parser.add_argument(
        "--access-token",
        help="Facebook access token (falls back to FB_ACCESS_TOKEN environment variable)",
    )
    parser.add_argument(
        "--output",
        default="comments.csv",
        help="Destination CSV file path (default: comments.csv)",
    )
    parser.add_argument("--since", help="Earliest post timestamp (ISO8601 or Unix epoch)")
    parser.add_argument("--until", help="Latest post timestamp (ISO8601 or Unix epoch)")
    parser.add_argument(
        "--max-posts",
        type=int,
        help="Optional cap on number of posts to fetch from the group feed",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    access_token = args.access_token or os.getenv("FB_ACCESS_TOKEN")
    if not access_token:
        print("Error: Provide an access token via --access-token or FB_ACCESS_TOKEN", file=sys.stderr)
        return 1

    client = FacebookClient(access_token=access_token)
    rows = collect_comments(
        client,
        args.group_id,
        since=args.since,
        until=args.until,
        max_posts=args.max_posts,
    )
    write_comments_to_csv(rows, args.output)
    print(f"Comments exported to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
