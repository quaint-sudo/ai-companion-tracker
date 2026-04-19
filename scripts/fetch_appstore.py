import requests
from datetime import datetime, timezone

from scripts.config import APP_STORE_IDS, APP_STORE_RSS_TEMPLATE, APP_STORE_MAX_PAGES

def get_week_from_date_str(date_str: str) -> str:
    from dateutil import parser
    try:
        dt = parser.isoparse(date_str).astimezone(timezone.utc)
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    except Exception:
        dt = datetime.now(timezone.utc)
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"

def fetch_appstore() -> list[dict]:
    """
    Fetches raw App Store reviews.
    Returns list of dicts.
    """
    all_reviews = []
    
    for app_name, app_id in APP_STORE_IDS.items():
        print(f"  [App Store] Fetching {app_name} (ID: {app_id})...")
        
        fetched_count = 0
        for page in range(1, APP_STORE_MAX_PAGES + 1):
            url = APP_STORE_RSS_TEMPLATE.format(app_id=app_id, page=page)
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except (requests.RequestException, ValueError) as e:
                print(f"    [WARN] Page {page} failed for {app_name}: {e}")
                break

            entries = data.get("feed", {}).get("entry", [])
            if not entries:
                break

            for entry in entries:
                content = entry.get("content", {})
                updated = entry.get("updated", {}).get("label", "")
                if isinstance(content, dict):
                    label = content.get("label", "")
                    if label:
                        all_reviews.append({
                            "source": "appstore",
                            "app": app_name,
                            "review_date": updated,
                            "review_week": get_week_from_date_str(updated),
                            "text": label
                        })
                        fetched_count += 1
                        
        print(f"    Collected {fetched_count} reviews.")
        
    return all_reviews
