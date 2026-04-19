import requests, json, time, sys, os
from datetime import datetime, timezone

# Constants
START_TS = 1722470400 # Aug 1, 2024 00:00:00 UTC
NOW_TS = int(time.time())
BATCH_SIZE = 100
PULLPUSH_URL = "https://api.pullpush.io/reddit/search/submission/"
ARCTIC_URL = "https://arctic-shift.photon-reddit.com/api/posts/search"

def fetch_batch(subreddit, after_ts):
    """Fetch 100 records from PullPush or Arctic Shift."""
    params = {
        "subreddit": subreddit,
        "size": BATCH_SIZE,
        "sort": "asc",
        "sort_type": "created_utc",
        "after": after_ts
    }
    
    # Try PullPush first
    try:
        r = requests.get(PULLPUSH_URL, params=params, timeout=20)
        if r.status_code == 200:
            data = r.json().get('data', [])
            if data: return data, "PullPush", 200
        elif r.status_code == 429:
            print("PullPush Rate Limited (429). Trying Arctic Shift fallback...", flush=True)
        else:
            print(f"PullPush Error {r.status_code}. Trying Arctic Shift fallback...", flush=True)
    except Exception as e:
        print(f"PullPush Exception: {e}. Trying Arctic Shift fallback...", flush=True)
    
    # Try Arctic Shift Fallback
    params_as = {
        "subreddit": subreddit,
        "limit": BATCH_SIZE,
        "sort": "asc",
        "after": after_ts
    }
    try:
        r = requests.get(ARCTIC_URL, params=params_as, timeout=20)
        if r.status_code == 200:
            data = r.json().get('data', [])
            if data: return data, "ArcticShift", 200
            else: return [], "ArcticShift", 200 # Both empty
        elif r.status_code == 429:
            return [], "ArcticShift", 429
        else:
            return [], "ArcticShift", r.status_code
    except Exception as e:
        return [], "ArcticShift", -1
    
    return [], None, 0

def run_pull(subreddit):
    target_file = f"data/{subreddit}_raw.new.json"
    print(f"\n--- Starting/Resuming re-pull for r/{subreddit} ---", flush=True)
    
    master_data = []
    seen_ids = set()
    current_after = START_TS
    
    if os.path.exists(target_file):
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                master_data = json.load(f)
            if master_data:
                current_after = max(x['created_utc'] for x in master_data)
                seen_ids = set(x['id'] for x in master_data)
                print(f"Resuming from {datetime.fromtimestamp(current_after, timezone.utc)} ({len(master_data)} records found).", flush=True)
        except Exception as e:
            print(f"Error loading existing data: {e}. Starting fresh.", flush=True)

    last_save_ts = current_after
    failed_attempts = 0
    
    print(f"Targeting window: {datetime.fromtimestamp(current_after, timezone.utc)} to now.", flush=True)
    
    while current_after < NOW_TS - 3600:
        batch, provider, status = fetch_batch(subreddit, current_after)
        
        if not batch:
            if status == 429:
                print(f"Both archives rate-limited. Sleeping 60s...", flush=True)
                time.sleep(60)
                continue
            elif status == 200:
                print(f"No records found after {datetime.fromtimestamp(current_after, timezone.utc)}. Jumping 1 hour...", flush=True)
                current_after += 3600
                failed_attempts = 0
                if current_after > NOW_TS: break
                continue
            else:
                failed_attempts += 1
                print(f"ERROR: No batch from archives. Attempt {failed_attempts}/5", flush=True)
                time.sleep(10)
                if failed_attempts >= 5:
                    print("FATAL: Failed to fetch data after 5 attempts. Aborting.", flush=True)
                    sys.exit(1)
                continue
        
        failed_attempts = 0
        new_max_ts = current_after
        added = 0
        
        for item in batch:
            pid = item.get('id')
            ts = int(float(item.get('created_utc', 0)))
            if ts > new_max_ts: new_max_ts = ts
            
            if pid not in seen_ids:
                seen_ids.add(pid)
                master_data.append({
                    'id': pid,
                    'created_utc': ts,
                    'title': item.get('title', '')[:200],
                    'selftext': item.get('selftext', ''), # FULL TEXT
                    'permalink': item.get('permalink', '')
                })
                added += 1
        
        print(f"[{subreddit}] Added {added} records. Max TS: {datetime.fromtimestamp(new_max_ts, timezone.utc)} ({provider})", flush=True)
        
        if new_max_ts <= current_after:
            current_after += 1
        else:
            current_after = new_max_ts
            
        # Periodic save every day of data
        if current_after - last_save_ts >= 3600 * 24:
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(master_data, f)
            last_save_ts = current_after
            
        time.sleep(0.5)
        
    with open(target_file, 'w', encoding='utf-8') as f:
        json.dump(master_data, f)
    print(f"SUCCESS: r/{subreddit} re-pull complete. Total: {len(master_data)}", flush=True)

if __name__ == "__main__":
    for sub in ["CharacterAI", "replika"]:
        run_pull(sub)
