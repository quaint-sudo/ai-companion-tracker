import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime, timezone

# Trustpilot URLs
TRUSTPILOT_TARGETS = {
    "character_ai": "https://www.trustpilot.com/review/character.ai",
    "replika": "https://www.trustpilot.com/review/replika.ai"
}

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

def extract_reviews_from_html(html_content: str) -> list[dict]:
    soup = BeautifulSoup(html_content, 'html.parser')
    reviews = []
    
    # Try getting structured JSON-LD first (robust)
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            data = json.loads(script.string)
            # Trustpilot sometimes nests reviews inside a LocalBusiness or Organization schema
            if isinstance(data, list):
                for item in data:
                    if item.get('@type') == 'LocalBusiness':
                        extracted = item.get('review', [])
                        if extracted:
                            for r in extracted:
                                date = r.get('datePublished', '')
                                text = r.get('reviewBody', '')
                                if date and text:
                                    reviews.append({'date': date, 'text': text})
        except Exception:
            continue
            
    # Fallback to HTML parsing if JSON-LD fails
    if not reviews:
        # Generic heuristic: look for article tags or review containers
        articles = soup.find_all('article')
        for article in articles:
            time_tag = article.find('time')
            if not time_tag:
                continue
            date = time_tag.get('datetime', '')
            # p tags often contain the review
            p_tags = article.find_all('p')
            text = " ".join([p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 20])
            if date and text:
                reviews.append({'date': date, 'text': text})

    return reviews

def fetch_trustpilot(pages=3) -> list[dict]:
    """
    Fetches raw trustpilot reviews using public page parsing.
    Throws Exception if totally failed, handled by pipeline to preserve data.
    """
    all_reviews = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    }
    
    for app, base_url in TRUSTPILOT_TARGETS.items():
        found_any_for_app = False
        print(f"  [Trustpilot] Fetching {app}...")
        
        for page in range(1, pages + 1):
            url = f"{base_url}?page={page}"
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                
                reviews = extract_reviews_from_html(resp.text)
                if not reviews:
                    print(f"    [WARN] Page {page}: No parseable reviews found.")
                    break
                    
                found_any_for_app = True
                
                for r in reviews:
                    all_reviews.append({
                        "source": "trustpilot",
                        "app": app,
                        "review_date": r["date"],
                        "review_week": get_week_from_date_str(r["date"]),
                        "text": r["text"]
                    })
            except requests.RequestException as e:
                print(f"    [ERROR] Page {page} HTTP Request failed: {e}")
                break
                
        if not found_any_for_app:
            raise Exception(f"Failed to extract any Trustpilot data for {app}. Layout may have changed or bot protection triggered.")
            
    return all_reviews
