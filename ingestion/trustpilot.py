"""
Trustpilot review scraper.
Fetches recent reviews for each target app from Trustpilot's public pages,
classifies them, and appends weekly aggregates to data/trustpilot_weekly.csv.

Run as: python -m ingestion.trustpilot

No API key needed — Trustpilot pages are publicly accessible.
"""

import os
import re
import json
import requests
import pandas as pd
from datetime import datetime, timezone

from ingestion.config import (
    TRUSTPILOT_SLUGS,
    TRUSTPILOT_BASE_URL,
    TRUSTPILOT_MAX_PAGES,
    TRUSTPILOT_CSV,
    TRUSTPILOT_COLUMNS,
    DATA_DIR,
)
from ingestion.classifier import classify_batch


def get_current_week() -> str:
    """Return current ISO week as 'YYYY-WNN' string."""
    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def fetch_reviews(slug: str, max_pages: int = TRUSTPILOT_MAX_PAGES) -> list[str]:
    """
    Fetch review texts from Trustpilot public pages.

    Trustpilot embeds review data in a __NEXT_DATA__ JSON blob in the HTML.
    We extract review bodies from that structured data.

    Args:
        slug: Trustpilot business page slug (e.g., 'character.ai').
        max_pages: Number of pages to fetch.

    Returns:
        List of review body strings.
    """
    reviews = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for page in range(1, max_pages + 1):
        url = TRUSTPILOT_BASE_URL.format(slug=slug)
        if page > 1:
            url += f"?page={page}"

        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            html = resp.text
        except requests.RequestException as e:
            print(f"  [WARN] Page {page} failed for {slug}: {e}")
            break

        # Extract __NEXT_DATA__ JSON from the page
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
        if not match:
            # Fallback: extract review text from JSON-LD
            reviews.extend(_extract_from_jsonld(html))
            continue

        try:
            next_data = json.loads(match.group(1))
            # Navigate the nested structure to find reviews
            page_props = next_data.get("props", {}).get("pageProps", {})
            review_list = page_props.get("reviews", [])

            for review in review_list:
                text = review.get("text", "")
                title = review.get("title", "")
                combined = f"{title} {text}".strip()
                if combined:
                    reviews.append(combined)

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"  [WARN] Failed to parse __NEXT_DATA__ on page {page}: {e}")
            # Try fallback extraction
            reviews.extend(_extract_from_jsonld(html))

    return reviews


def _extract_from_jsonld(html: str) -> list[str]:
    """Fallback: extract reviews from JSON-LD structured data in the HTML."""
    reviews = []
    # Look for JSON-LD review data
    ld_matches = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    for ld_text in ld_matches:
        try:
            ld_data = json.loads(ld_text)
            # JSON-LD can be a single object or array
            items = ld_data if isinstance(ld_data, list) else [ld_data]
            for item in items:
                if item.get("@type") == "Review":
                    body = item.get("reviewBody", "")
                    name = item.get("name", "")
                    combined = f"{name} {body}".strip()
                    if combined:
                        reviews.append(combined)
                # Also check for nested reviews
                for review in item.get("review", []):
                    body = review.get("reviewBody", "")
                    name = review.get("name", "")
                    combined = f"{name} {body}".strip()
                    if combined:
                        reviews.append(combined)
        except (json.JSONDecodeError, TypeError):
            continue
    return reviews


def ensure_csv_exists():
    """Create the CSV file with headers if it doesn't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(TRUSTPILOT_CSV):
        df = pd.DataFrame(columns=TRUSTPILOT_COLUMNS)
        df.to_csv(TRUSTPILOT_CSV, index=False)
        print(f"[INIT] Created {TRUSTPILOT_CSV}")


def week_app_exists(week: str, app: str) -> bool:
    """Check if data for this week+app combo already exists (idempotency)."""
    if not os.path.exists(TRUSTPILOT_CSV):
        return False
    df = pd.read_csv(TRUSTPILOT_CSV)
    return ((df["week"] == week) & (df["app"] == app)).any()


def run():
    """Main entry point: fetch, classify, and append data for all target apps."""
    ensure_csv_exists()
    week = get_current_week()
    print(f"=== Trustpilot Ingestion — Week {week} ===")

    new_rows = []

    for app_name, slug in TRUSTPILOT_SLUGS.items():
        print(f"\n[{app_name}] Fetching Trustpilot reviews ({slug})...")

        if week_app_exists(week, app_name):
            print(f"  [SKIP] Data for {app_name} week {week} already exists.")
            continue

        reviews = fetch_reviews(slug)
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
        df_existing = pd.read_csv(TRUSTPILOT_CSV)
        df_new = pd.DataFrame(new_rows, columns=TRUSTPILOT_COLUMNS)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined.to_csv(TRUSTPILOT_CSV, index=False)
        print(f"\n[DONE] Appended {len(new_rows)} rows to {TRUSTPILOT_CSV}")
    else:
        print("\n[DONE] No new data to append.")


if __name__ == "__main__":
    run()
