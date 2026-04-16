"""
Reddit public JSON scraper (NO API key required).
Fetches recent posts from target subreddits using Reddit's public .json endpoints,
classifies them, and appends weekly aggregates to data/reddit_weekly.csv.

Run as: python -m ingestion.reddit_api

This uses Reddit's public JSON interface which requires no authentication.
Rate limit: ~60 requests/minute for unauthenticated access.
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime, timezone

from ingestion.config import (
    TARGET_SUBREDDITS,
    REDDIT_JSON_TEMPLATE,
    REDDIT_USER_AGENT,
    REDDIT_POST_LIMIT,
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


def fetch_subreddit_texts(subreddit_name: str) -> dict:
    """
    Fetch recent posts from a subreddit using the public JSON API.
    No authentication needed.

    Returns:
        dict with:
            - post_texts (list[str]): Post titles + selftext
            - post_count (int)
            - comment_count (int): Estimated from num_comments field
    """
    headers = {
        "User-Agent": REDDIT_USER_AGENT,
    }

    post_texts = []
    total_comments = 0
    after = None  # Pagination cursor

    # Fetch in batches (max 100 per request)
    remaining = REDDIT_POST_LIMIT
    while remaining > 0:
        batch_size = min(remaining, 100)
        url = REDDIT_JSON_TEMPLATE.format(subreddit=subreddit_name, limit=batch_size)
        if after:
            url += f"&after={after}"

        try:
            resp = requests.get(url, headers=headers, timeout=30)

            # Handle rate limiting
            if resp.status_code == 429:
                print(f"  [RATE LIMIT] Waiting 10 seconds...")
                time.sleep(10)
                continue

            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as e:
            print(f"  [WARN] Error fetching r/{subreddit_name}: {e}")
            break

        posts = data.get("data", {}).get("children", [])
        if not posts:
            break

        for post in posts:
            post_data = post.get("data", {})
            title = post_data.get("title", "")
            selftext = post_data.get("selftext", "")
            text = f"{title} {selftext}".strip()
            if text and not post_data.get("stickied", False):
                post_texts.append(text)
            total_comments += post_data.get("num_comments", 0)

        # Get pagination cursor
        after = data.get("data", {}).get("after")
        if not after:
            break

        remaining -= batch_size
        # Respect rate limits: 1 second between requests
        time.sleep(1.5)

    return {
        "post_texts": post_texts,
        "post_count": len(post_texts),
        "comment_count": total_comments,
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
    print(f"=== Reddit Ingestion (Public JSON) — Week {week} ===")
    print(f"    No API key required.\n")

    new_rows = []

    for sub_name in TARGET_SUBREDDITS:
        print(f"[r/{sub_name}] Fetching posts...")

        if week_sub_exists(week, sub_name):
            print(f"  [SKIP] Data for r/{sub_name} week {week} already exists.")
            continue

        data = fetch_subreddit_texts(sub_name)
        total_items = len(data["post_texts"])

        print(f"  Collected {data['post_count']} posts ({data['comment_count']} comments referenced).")

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

        stats = classify_batch(data["post_texts"])
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

        # Respect rate limits between subreddits
        time.sleep(2)

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
