"""
Reddit API ingestion via PRAW.
Fetches recent posts and comments from target subreddits, classifies them,
and appends weekly aggregates to data/reddit_weekly.csv.

Run as: python -m ingestion.reddit_api

Requires environment variables:
    REDDIT_CLIENT_ID
    REDDIT_CLIENT_SECRET
    REDDIT_USER_AGENT  (optional, defaults to a generic agent string)
"""

import os
import sys
import praw
import pandas as pd
from datetime import datetime, timezone

from ingestion.config import (
    TARGET_SUBREDDITS,
    REDDIT_POST_LIMIT,
    REDDIT_COMMENT_LIMIT,
    REDDIT_CSV,
    REDDIT_COLUMNS,
    DATA_DIR,
)
from ingestion.classifier import classify_batch


def get_current_week() -> str:
    """Return current ISO week as 'YYYY-WNN' string."""
    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def get_reddit_client() -> praw.Reddit:
    """
    Create an authenticated Reddit client from environment variables.
    Uses read-only mode (no user login needed).
    """
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = os.environ.get("REDDIT_USER_AGENT", "AI-Companion-Tracker/1.0")

    if not client_id or not client_secret:
        print("[ERROR] REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET must be set.")
        print("        Set them as environment variables or GitHub Secrets.")
        sys.exit(1)

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


def fetch_subreddit_texts(reddit: praw.Reddit, subreddit_name: str) -> dict:
    """
    Fetch recent posts and comments from a subreddit.

    Returns:
        dict with:
            - post_texts (list[str]): Post titles + selftext
            - comment_texts (list[str]): Comment bodies
            - post_count (int)
            - comment_count (int)
    """
    subreddit = reddit.subreddit(subreddit_name)
    post_texts = []
    comment_texts = []

    try:
        for post in subreddit.new(limit=REDDIT_POST_LIMIT):
            # Combine title and body for classification
            text = f"{post.title} {post.selftext or ''}".strip()
            if text:
                post_texts.append(text)

            # Fetch top-level comments
            post.comments.replace_more(limit=0)  # Skip "load more" to stay fast
            for comment in post.comments[:REDDIT_COMMENT_LIMIT]:
                if hasattr(comment, "body") and comment.body:
                    comment_texts.append(comment.body)

    except Exception as e:
        print(f"  [WARN] Error fetching r/{subreddit_name}: {e}")

    return {
        "post_texts": post_texts,
        "comment_texts": comment_texts,
        "post_count": len(post_texts),
        "comment_count": len(comment_texts),
    }


def ensure_csv_exists():
    """Create the CSV file with headers if it doesn't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(REDDIT_CSV):
        df = pd.DataFrame(columns=REDDIT_COLUMNS)
        df.to_csv(REDDIT_CSV, index=False)
        print(f"[INIT] Created {REDDIT_CSV}")


def week_sub_exists(week: str, subreddit: str) -> bool:
    """Check if data for this week+subreddit already exists (idempotency)."""
    if not os.path.exists(REDDIT_CSV):
        return False
    df = pd.read_csv(REDDIT_CSV)
    return ((df["week"] == week) & (df["subreddit"] == subreddit)).any()


def get_previous_sentiment(subreddit: str) -> float | None:
    """Get the most recent net_sentiment for a subreddit to compute velocity."""
    if not os.path.exists(REDDIT_CSV):
        return None
    df = pd.read_csv(REDDIT_CSV)
    sub_df = df[df["subreddit"] == subreddit].sort_values("week", ascending=False)
    if len(sub_df) == 0:
        return None
    return sub_df.iloc[0]["net_sentiment"]


def run():
    """Main entry point: fetch, classify, and append data for all target subreddits."""
    ensure_csv_exists()
    week = get_current_week()
    print(f"=== Reddit Ingestion — Week {week} ===")

    reddit = get_reddit_client()
    new_rows = []

    for sub_name in TARGET_SUBREDDITS:
        print(f"\n[r/{sub_name}] Fetching posts and comments...")

        if week_sub_exists(week, sub_name):
            print(f"  [SKIP] Data for r/{sub_name} week {week} already exists.")
            continue

        data = fetch_subreddit_texts(reddit, sub_name)
        all_texts = data["post_texts"] + data["comment_texts"]
        total_items = len(all_texts)

        print(f"  Collected {data['post_count']} posts, {data['comment_count']} comments.")

        if total_items == 0:
            print(f"  [WARN] No texts found, writing zero row.")
            new_rows.append({
                "week": week,
                "subreddit": sub_name,
                "post_count": 0,
                "comment_count": 0,
                "benefit_count": 0,
                "harm_count": 0,
                "benefit_rate": 0.0,
                "harm_rate": 0.0,
                "net_sentiment": 0.0,
                "sentiment_velocity": 0.0,
            })
            continue

        stats = classify_batch(all_texts)
        prev_sentiment = get_previous_sentiment(sub_name)
        velocity = round(stats["net_sentiment"] - prev_sentiment, 4) if prev_sentiment is not None else 0.0

        row = {
            "week": week,
            "subreddit": sub_name,
            "post_count": data["post_count"],
            "comment_count": data["comment_count"],
            "benefit_count": stats["benefit_count"],
            "harm_count": stats["harm_count"],
            "benefit_rate": stats["benefit_rate"],
            "harm_rate": stats["harm_rate"],
            "net_sentiment": stats["net_sentiment"],
            "sentiment_velocity": velocity,
        }
        new_rows.append(row)
        print(f"  benefit_rate={row['benefit_rate']}, harm_rate={row['harm_rate']}, "
              f"net={row['net_sentiment']}, velocity={row['sentiment_velocity']}")

    if new_rows:
        df_existing = pd.read_csv(REDDIT_CSV)
        df_new = pd.DataFrame(new_rows, columns=REDDIT_COLUMNS)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined.to_csv(REDDIT_CSV, index=False)
        print(f"\n[DONE] Appended {len(new_rows)} rows to {REDDIT_CSV}")
    else:
        print("\n[DONE] No new data to append.")


if __name__ == "__main__":
    run()
