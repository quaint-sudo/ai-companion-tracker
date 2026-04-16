"""
iOS App Store RSS feed scraper.
Fetches recent reviews for each target app, classifies them, and appends
weekly aggregates to data/appstore_weekly.csv.

Run as: python -m ingestion.appstore_rss
"""

import os
import sys
import requests
import pandas as pd
from datetime import datetime, timezone

from ingestion.config import (
    APP_STORE_IDS,
    APP_STORE_RSS_TEMPLATE,
    APP_STORE_MAX_PAGES,
    APPSTORE_CSV,
    APPSTORE_COLUMNS,
    DATA_DIR,
)
from ingestion.classifier import classify_batch


def get_current_week() -> str:
    """Return current ISO week as 'YYYY-WNN' string."""
    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def fetch_reviews(app_id: str, max_pages: int = APP_STORE_MAX_PAGES) -> list[str]:
    """
    Fetch review texts from the App Store RSS JSON feed.

    Args:
        app_id: Numeric Apple App Store ID.
        max_pages: Number of pages to fetch (each ~50 reviews).

    Returns:
        List of review body strings.
    """
    reviews = []
    for page in range(1, max_pages + 1):
        url = APP_STORE_RSS_TEMPLATE.format(app_id=app_id, page=page)
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as e:
            print(f"  [WARN] Page {page} failed for app {app_id}: {e}")
            break

        entries = data.get("feed", {}).get("entry", [])
        if not entries:
            break

        for entry in entries:
            # Skip the first entry if it's the app metadata (no review content)
            content = entry.get("content", {})
            if isinstance(content, dict):
                label = content.get("label", "")
                if label:
                    reviews.append(label)

    return reviews


def ensure_csv_exists():
    """Create the CSV file with headers if it doesn't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(APPSTORE_CSV):
        df = pd.DataFrame(columns=APPSTORE_COLUMNS)
        df.to_csv(APPSTORE_CSV, index=False)
        print(f"[INIT] Created {APPSTORE_CSV}")


def week_app_exists(week: str, app: str) -> bool:
    """Check if data for this week+app combo already exists (idempotency)."""
    if not os.path.exists(APPSTORE_CSV):
        return False
    df = pd.read_csv(APPSTORE_CSV)
    return ((df["week"] == week) & (df["app"] == app)).any()


def run():
    """Main entry point: fetch, classify, and append data for all target apps."""
    ensure_csv_exists()
    week = get_current_week()
    print(f"=== App Store Ingestion — Week {week} ===")

    new_rows = []

    for app_name, app_id in APP_STORE_IDS.items():
        print(f"\n[{app_name}] Fetching reviews (ID: {app_id})...")

        if week_app_exists(week, app_name):
            print(f"  [SKIP] Data for {app_name} week {week} already exists.")
            continue

        reviews = fetch_reviews(app_id)
        print(f"  Collected {len(reviews)} reviews.")

        if len(reviews) == 0:
            print(f"  [WARN] No reviews found, writing zero row.")
            new_rows.append({
                "week": week,
                "app": app_name,
                "review_count": 0,
                "benefit_count": 0,
                "harm_count": 0,
                "benefit_rate": 0.0,
                "harm_rate": 0.0,
                "net_sentiment": 0.0,
            })
            continue

        stats = classify_batch(reviews)
        row = {
            "week": week,
            "app": app_name,
            "review_count": stats["total"],
            "benefit_count": stats["benefit_count"],
            "harm_count": stats["harm_count"],
            "benefit_rate": stats["benefit_rate"],
            "harm_rate": stats["harm_rate"],
            "net_sentiment": stats["net_sentiment"],
        }
        new_rows.append(row)
        print(f"  benefit_rate={row['benefit_rate']}, harm_rate={row['harm_rate']}, net={row['net_sentiment']}")

    if new_rows:
        df_existing = pd.read_csv(APPSTORE_CSV)
        df_new = pd.DataFrame(new_rows, columns=APPSTORE_COLUMNS)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined.to_csv(APPSTORE_CSV, index=False)
        print(f"\n[DONE] Appended {len(new_rows)} rows to {APPSTORE_CSV}")
    else:
        print("\n[DONE] No new data to append.")


if __name__ == "__main__":
    run()
