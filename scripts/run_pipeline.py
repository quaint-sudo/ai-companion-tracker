#!/usr/bin/env python3
import os
import json
import time
import re
import requests
import pandas as pd
from datetime import datetime, timezone
from collections import defaultdict

# Constants
PULLPUSH_URL = "https://api.pullpush.io/reddit/search/submission/"
ARCTIC_URL = "https://arctic-shift.photon-reddit.com/api/posts/search"

HARM_PATTERNS = [
    r"\baddict", r"\bdependenc", r"\bdependent\b", r"\bobsess", r"\bmanipulat",
    r"\bunhealthy\b", r"\btoxic\b", r"\bself[- ]harm", r"\bsuicid", r"\bdanger",
    r"\bunsafe\b", r"\bharmful\b", r"\bgroom"
]

BENEFIT_PATTERNS = [
    r"\bhelp", r"\bsupport", r"\bcomfort", r"\bcope\b", r"\bcoping\b",
    r"\blonel", r"\banxi", r"\bgrief", r"\bgrieving\b", r"\bheal",
    r"\bcompanion", r"\bunderstand", r"\btherap"
]

START_TIMESTAMP = int(datetime(2024, 8, 1, tzinfo=timezone.utc).timestamp())
LAW_SUIT_DATE = pd.to_datetime("2024-10-22")

DATA_DIR = "data"
DOCS_DATA_DIR = os.path.join("docs", "data")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DOCS_DATA_DIR, exist_ok=True)

def fetch_batch(subreddit, before_ts):
    url = f"{PULLPUSH_URL}?subreddit={subreddit}&size=100&sort=desc&sort_type=created_utc&before={before_ts}"

    for attempt in range(2):
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                obj = r.json()
                if "data" in obj:
                    return obj["data"]
            print(f"[{subreddit}] PullPush returned {r.status_code}")
        except Exception as e:
            pass
        time.sleep(2.0)

    print(f"[{subreddit}] Falling back to Arctic Shift...")
    fb_url = f"{ARCTIC_URL}?subreddit={subreddit}&limit=100&sort=desc&before={before_ts}"
    try:
        r = requests.get(fb_url, timeout=15)
        if r.status_code == 200:
            obj = r.json()
            if "data" in obj:
                return obj["data"]
    except Exception as e:
        print(f"[{subreddit}] Arctic Shift fallback failed: {e}")
    
    return []

def save_submissions(subreddit, data):
    # Sharded save logic
    if len(data) > 150000:
        split = 150000
        for i, start_idx in enumerate(range(0, len(data), split)):
            part_file = os.path.join(DATA_DIR, f"{subreddit}_raw_part{i+1}.json")
            with open(part_file, "w", encoding="utf-8") as f:
                json.dump(data[start_idx : start_idx + split], f)
        # Clean up old non-sharded file if it exists
        legacy = os.path.join(DATA_DIR, f"{subreddit}_raw.json")
        if os.path.exists(legacy):
            os.remove(legacy)
    else:
        with open(os.path.join(DATA_DIR, f"{subreddit}_raw.json"), "w", encoding="utf-8") as f:
            json.dump(data, f)

def collect_submissions(subreddit):
    # Find all shard files
    # Order: [subreddit]_raw.json first, then [subreddit]_raw_part*.json
    raw_pattern = os.path.join(DATA_DIR, f"{subreddit}_raw")
    shard_files = []
    if os.path.exists(raw_pattern + ".json"):
        shard_files.append(raw_pattern + ".json")
    
    # Check for parts
    import glob
    parts = glob.glob(raw_pattern + "_part*.json")
    parts.sort() # Ensure deterministic order part1, part2...
    shard_files.extend(parts)

    data = []
    for sf in shard_files:
        try:
            with open(sf, "r", encoding="utf-8") as f:
                data.extend(json.load(f))
        except: pass
            
    now_ts = int(time.time())
    seen_ids = set([x.get('id') for x in data if x.get('id')])
    
    min_ts = now_ts
    max_ts = START_TIMESTAMP
    if data:
        min_ts = min([x.get("created_utc", now_ts) for x in data])
        max_ts = max([x.get("created_utc", START_TIMESTAMP) for x in data])

    def fetch_period(target_before, stop_after):
        current_before = target_before
        new_records = []
        batch_count = 0
        
        while current_before > stop_after:
            batch = fetch_batch(subreddit, current_before)
            if not batch: break
            
            added = 0
            new_batch_min = current_before
            
            for item in batch:
                ts = int(item.get("created_utc", 0))
                if ts < new_batch_min: new_batch_min = ts
                
                if ts <= stop_after:
                    continue
                    
                pid = item.get("id")
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    
                    title = str(item.get("title", ""))
                    selftext = item.get("selftext") or ""
                    if selftext in ["[removed]", "[deleted]"]: selftext = ""
                    else: selftext = str(selftext).replace('\n', ' ')
                    
                    new_records.append({
                        "id": pid,
                        "created_utc": ts,
                        "title": title,
                        "selftext": selftext,
                        "permalink": item.get('permalink', '')
                    })
                    added += 1
            
            if added == 0 and new_batch_min >= current_before:
                current_before -= 1
                continue
                
            time.sleep(0.5) 
            current_before = new_batch_min - 1
            
            batch_count += 1
            if batch_count % 10 == 0 and new_records:
                data.extend(new_records)
                new_records = []
                save_submissions(subreddit, data)
        
    # Gap fill execution
    if max_ts < now_ts - 86400:
        print(f"[{subreddit}] Gap fill FORWARD: pulling from {max_ts} to present.")
        fetch_period(now_ts, max_ts)
        
    if min_ts > START_TIMESTAMP:
        print(f"[{subreddit}] Gap fill BACKWARD: pulling from {min_ts} down to {START_TIMESTAMP}.")
        fetch_period(min_ts, START_TIMESTAMP)
        
    # Final save and return
    data.sort(key=lambda x: x.get('created_utc', 0))
    save_submissions(subreddit, data)
    print(f"[{subreddit}] Completed. Total valid records: {len(data)}")
    return data

def aggregate_data(cai_data, replika_data):
    all_data = []
    
    # Pre-compile regexes for speed
    h_re = [re.compile(p, re.I) for p in HARM_PATTERNS]
    b_re = [re.compile(p, re.I) for p in BENEFIT_PATTERNS]

    def classify(item):
        full_text = (str(item.get('title', '')) + " " + str(item.get('selftext', ''))).lower()
        h_matches = [p for p, r in zip(HARM_PATTERNS, h_re) if r.search(full_text)]
        b_matches = [p for p, r in zip(BENEFIT_PATTERNS, b_re) if r.search(full_text)]
        return h_matches, b_matches

    print("Classifying CharacterAI...")
    for d in cai_data:
        d['app'] = 'CharacterAI'
        h, b = classify(d)
        d['harm_matches'] = h
        d['benefit_matches'] = b
        d['has_harm'] = len(h) > 0
        d['has_benefit'] = len(b) > 0
        all_data.append(d)
        
    print("Classifying replika...")
    for d in replika_data:
        d['app'] = 'replika'
        h, b = classify(d)
        d['harm_matches'] = h
        d['benefit_matches'] = b
        d['has_harm'] = len(h) > 0
        d['has_benefit'] = len(b) > 0
        all_data.append(d)
        
    if not all_data: return
        
    print("Processing DataFrame...")
    df = pd.DataFrame(all_data)
    df["dt"] = pd.to_datetime(df["created_utc"], unit="s", utc=True)
    df["iso_week"] = df["dt"].dt.strftime("%Y-W%V")
    
    # 1. Weekly Rates
    weekly = df.groupby(["app", "iso_week"]).agg(
        volume=("id", "count"),
        harm_count=("has_harm", "sum"),
        benefit_count=("has_benefit", "sum")
    ).reset_index()
    weekly["harm_rate"] = weekly["harm_count"] / weekly["volume"]
    weekly["benefit_rate"] = weekly["benefit_count"] / weekly["volume"]
    
    # 2. Pre/post Means
    pre_start = LAW_SUIT_DATE - pd.Timedelta(weeks=12)
    post_end = LAW_SUIT_DATE + pd.Timedelta(weeks=12)
    
    averages = {}
    pattern_counts = {"CharacterAI": {"harm": defaultdict(int), "benefit": defaultdict(int)},
                      "replika": {"harm": defaultdict(int), "benefit": defaultdict(int)}}
                      
    for app in ["CharacterAI", "replika"]:
        app_df = df[df["app"] == app].copy()
        
        # Means
        if not app_df.empty:
            app_df["dt_tz_naive"] = app_df["dt"].dt.tz_localize(None)
            pre_mask = (app_df["dt_tz_naive"] >= pre_start) & (app_df["dt_tz_naive"] < LAW_SUIT_DATE)
            post_mask = (app_df["dt_tz_naive"] >= LAW_SUIT_DATE) & (app_df["dt_tz_naive"] < post_end)
            
            pre_vol = pre_mask.sum()
            post_vol = post_mask.sum()
            pre_harm_rate_mean = app_df.loc[pre_mask, "has_harm"].mean() if pre_vol > 0 else 0
            post_harm_rate_mean = app_df.loc[post_mask, "has_harm"].mean() if post_vol > 0 else 0
        else:
            pre_harm_rate_mean, post_harm_rate_mean = 0, 0
            
        delta = post_harm_rate_mean - pre_harm_rate_mean
        averages[app] = {
            "pre_harm_rate_mean": float(pre_harm_rate_mean),
            "post_harm_rate_mean": float(post_harm_rate_mean),
            "delta": float(delta)
        }
        
        # Pattern counts
        for _, row in app_df.iterrows():
            for p in row['harm_matches']: pattern_counts[app]["harm"][p] += 1
            for p in row['benefit_matches']: pattern_counts[app]["benefit"][p] += 1
            
    # 3. Peak Excerpts Selection
    excerpts = {}
    def extract_peak(target_app, rate_col, matches_col):
        app_wks = weekly[weekly['app'] == target_app]
        if app_wks.empty: return {"week": "", "posts": []}
        peak_wkRow = app_wks.sort_values(rate_col, ascending=False).iloc[0]
        peak_wk = peak_wkRow['iso_week']
        
        app_df = df[(df['app'] == target_app) & (df['iso_week'] == peak_wk) & (df[matches_col].str.len() > 0)]
        app_df = app_df.sort_values('created_utc', ascending=True).head(5)
        
        posts = []
        for _, r in app_df.iterrows():
            dt_str = r['dt'].strftime('%Y-%m-%d')
            posts.append({
                "title": r["title"][:120] + ("..." if len(str(r["title"])) > 120 else ""),
                "selftext": r["selftext"][:200] + ("..." if len(str(r["selftext"])) > 200 else ""),
                "patterns_matched": r[matches_col],
                "date": dt_str,
                "permalink": r["permalink"]
            })
        return {"week": peak_wk, "posts": posts}

    excerpts["CharacterAI_harm"] = extract_peak("CharacterAI", "harm_rate", "harm_matches")
    excerpts["CharacterAI_benefit"] = extract_peak("CharacterAI", "benefit_rate", "benefit_matches")
    excerpts["replika_harm"] = extract_peak("replika", "harm_rate", "harm_matches")
    excerpts["replika_benefit"] = extract_peak("replika", "benefit_rate", "benefit_matches")

    # 4. Worked Example (Peak CAI Harm)
    worked_example = {}
    cai_wks = weekly[weekly['app'] == 'CharacterAI']
    if not cai_wks.empty:
        pwk = cai_wks.sort_values("harm_rate", ascending=False).iloc[0]
        worked_example = {
            "week": pwk['iso_week'],
            "volume": int(pwk['volume']),
            "harm_count": int(pwk['harm_count']),
            "benefit_count": int(pwk['benefit_count']),
            "harm_rate": float(pwk['harm_rate']),
            "benefit_rate": float(pwk['benefit_rate'])
        }

    # 5. Spike Analysis (2024-W43)
    spike_analysis = {}
    for app in ["CharacterAI", "replika"]:
        app_df = weekly[weekly['app'] == app]
        row_w43 = app_df[app_df['iso_week'] == "2024-W43"]
        spike_analysis[app] = {
            "rate_w43": float(row_w43['harm_rate'].iloc[0]) if not row_w43.empty else 0.0,
            "count_w43": int(row_w43['harm_count'].iloc[0]) if not row_w43.empty else 0,
            "vol_w43": int(row_w43['volume'].iloc[0]) if not row_w43.empty else 0
        }

    # 6. Event Markers
    events_raw = []
    if os.path.exists("data/events.json"):
        with open("data/events.json", "r", encoding="utf-8") as f:
            events_raw = json.load(f)
    
    events_processed = []
    for ev in events_raw:
        ev_dt = pd.to_datetime(ev["date"])
        ev["iso_week"] = ev_dt.strftime("%Y-W%V")
        events_processed.append(ev)

    # Output JSON
    output = {
        "metadata": {
            "lawsuit_date": "2024-10-22",
            "worked_example": worked_example,
            "pattern_counts": pattern_counts,
            "excerpts": excerpts,
            "spike_analysis": spike_analysis,
            "events": events_processed
        },
        "averages": averages,
        "weekly": []
    }
    for _, row in weekly.iterrows(): output["weekly"].append(row.to_dict())
    
    out_path = os.path.join(DOCS_DATA_DIR, "reddit_weekly.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

def main():
    print("=== Pulling CharacterAI ===")
    cai_data = collect_submissions("CharacterAI")
    
    print("\n=== Pulling replika ===")
    replika_data = collect_submissions("replika")
    
    print("\n=== Aggregating Weekly Outcomes ===")
    aggregate_data(cai_data, replika_data)

if __name__ == "__main__":
    main()
