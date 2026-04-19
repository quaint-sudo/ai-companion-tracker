import requests, json, time, re, sys
from datetime import datetime, timezone

HARM = [r'\baddict', r'\bdependenc', r'\bdependent\b', r'\bobsess', r'\bmanipulat', r'\bunhealthy\b', r'\btoxic\b', r'\bself[- ]harm', r'\bsuicid', r'\bdanger', r'\bunsafe\b', r'\bharmful\b', r'\bgroom']
BENEFIT = [r'\bhelp', r'\bsupport', r'\bcomfort', r'\bcope\b', r'\bcoping\b', r'\blonel', r'\banxi', r'\bgrief', r'\bgrieving\b', r'\bheal', r'\bcompanion', r'\bunderstand', r'\btherap']

RAW_FILE = 'data/CharacterAI_raw.json'
START_TS = 1746783597 # 2025-05-09
TEN_WEEKS_SEC = 3600 * 24 * 7 * 10
NOW_TS = int(time.time())

def fetch_batch(after_ts):
    # Try PullPush first
    url = f"https://api.pullpush.io/reddit/search/submission/?subreddit=CharacterAI&size=100&sort=asc&sort_type=created_utc&after={after_ts}"
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            data = r.json().get('data', [])
            if data:
                return data, "PullPush", 200
        elif r.status_code == 429:
            return [], "PullPush", 429
    except Exception as e:
        pass
    
    # Try Arctic Shift Fallback
    url = f"https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=CharacterAI&limit=100&sort=asc&after={after_ts}"
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            data = r.json().get('data', [])
            if data:
                return data, "ArcticShift", 200
            else:
                return [], "ArcticShift", 200 # Both empty
        else:
            return [], "ArcticShift", r.status_code
    except Exception as e:
        return [], "ArcticShift", -1
        
    return [], None, 0

def run_repair():
    print(f"Loading {RAW_FILE}...", flush=True)
    with open(RAW_FILE, 'r', encoding='utf-8') as f:
        master_data = json.load(f)
    
    seen_ids = set([x['id'] for x in master_data])
    initial_count = len(master_data)
    current_after = START_TS
    last_save_ts = START_TS
    failed_batches = 0
    added_total = 0
    
    print(f"Repair starting from {datetime.fromtimestamp(START_TS, timezone.utc)}", flush=True)
    
    batch_idx = 0
    while current_after < NOW_TS - 7200:
        batch, provider, status = fetch_batch(current_after)
        
        if not batch:
            if status == 429:
                print(f"Rate limited by {provider}. Sleeping 30s...", flush=True)
                time.sleep(30)
                continue
            elif status == 200:
                # Both PullPush and ArcticShift returned []
                # This is a REAL volume gap or end of data.
                # In CharacterAI, a real gap of > 1 hour is extremely unlikely.
                # But we might need to jump if it persists.
                print(f"No records found after {datetime.fromtimestamp(current_after, timezone.utc)}. Force incrementing...", flush=True)
                current_after += 3600 # Jump 1 hour to see if we find something
                failed_batches = 0 # reset since status was 200
                continue
            else:
                failed_batches += 1
                print(f"Batch {batch_idx} ERROR ({provider} status {status}). Attempt {failed_batches}/5", flush=True)
                time.sleep(10)
                if failed_batches >= 5:
                    print("FATAL ERROR: Both APIs failed 5 times in a row. Aborting.")
                    sys.exit(1)
                continue
        
        failed_batches = 0
        added_in_batch = 0
        new_max_ts = current_after
        
        for item in batch:
            pid = item.get('id')
            ts = int(float(item.get('created_utc', 0))) 
            if ts > new_max_ts: new_max_ts = ts
            
            if pid not in seen_ids:
                seen_ids.add(pid)
                title = str(item.get('title', ''))
                text = str(item.get('selftext') or '').replace('\n', ' ')
                if text in ['[removed]', '[deleted]']: text = ''
                
                full = (title + ' ' + text).lower()
                h = [p for p in HARM if re.search(p, full, re.I)]
                b = [p for p in BENEFIT if re.search(p, full, re.I)]
                
                master_data.append({
                    'id': pid,
                    'created_utc': ts,
                    'title': title[:120],
                    'selftext': text[:100],
                    'harm_matches': h,
                    'benefit_matches': b,
                    'permalink': item.get('permalink', '')
                })
                added_in_batch += 1
                added_total += 1

        print(f"Batch {batch_idx} ({provider}): Added {added_in_batch}/{len(batch)}. Max TS: {datetime.fromtimestamp(new_max_ts, timezone.utc)}", flush=True)
        
        if new_max_ts <= current_after:
            current_after += 1
        else:
            current_after = new_max_ts
            
        batch_idx += 1
        
        if current_after - last_save_ts >= TEN_WEEKS_SEC:
            print(f"PROGRESS SAVE: Reached {datetime.fromtimestamp(current_after, timezone.utc)}", flush=True)
            with open(RAW_FILE, 'w', encoding='utf-8') as f:
                json.dump(master_data, f)
            last_save_ts = current_after
            
        time.sleep(1.0) 
        
    print("\n--- FINAL CHECKS ---", flush=True)
    if added_total < 50000:
        print(f"FATAL ERROR: Only {added_total} records added (expected >50,000). Data may be truncated.")
        sys.exit(1)
        
    last_ts = max([x['created_utc'] for x in master_data])
    if NOW_TS - last_ts > 3600 * 48:
        print(f"FATAL ERROR: Last record is from {datetime.fromtimestamp(last_ts, timezone.utc)}, which is >48h old.")
        sys.exit(1)
        
    with open(RAW_FILE, 'w', encoding='utf-8') as f:
        json.dump(master_data, f)
    
    print(f"SUCCESS: Gap filled. New total count: {len(master_data)} (Added {added_total})", flush=True)

if __name__ == "__main__":
    run_repair()
