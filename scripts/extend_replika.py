import requests, json, time, re, os
from datetime import datetime, timezone

HARM = [r'\baddict', r'\bdependenc', r'\bdependent\b', r'\bobsess', r'\bmanipulat', r'\bunhealthy\b', r'\btoxic\b', r'\bself[- ]harm', r'\bsuicid', r'\bdanger', r'\bunsafe\b', r'\bharmful\b', r'\bgroom']
BENEFIT = [r'\bhelp', r'\bsupport', r'\bcomfort', r'\bcope\b', r'\bcoping\b', r'\blonel', r'\banxi', r'\bgrief', r'\bgrieving\b', r'\bheal', r'\bcompanion', r'\bunderstand', r'\btherap']

RAW_FILE = 'data/replika_raw.json'

def fetch_batch(after_ts):
    # PullPush
    pp_url = f"https://api.pullpush.io/reddit/search/submission/?subreddit=replika&size=100&sort=asc&sort_type=created_utc&after={after_ts}"
    try:
        r = requests.get(pp_url, timeout=15)
        if r.status_code == 200:
            data = r.json().get('data', [])
            if data: return data
    except: pass
    
    # Arctic Shift Fallback
    # Note: Arctic usually sorts desc by default, but we can try to use after and hope for the best or handle pagination.
    as_url = f"https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=replika&limit=100&sort=asc&after={after_ts}"
    try:
        r = requests.get(as_url, timeout=15)
        if r.status_code == 200:
            return r.json().get('data', [])
    except: pass
    return []

def run_extension():
    with open(RAW_FILE, 'r', encoding='utf-8') as f:
        master_data = json.load(f)
    
    seen_ids = set([x['id'] for x in master_data])
    current_after = max([x['created_utc'] for x in master_data])
    now_ts = int(time.time())
    
    print(f"Starting extension from {datetime.fromtimestamp(current_after, timezone.utc)}", flush=True)
    
    batch_count = 0
    while current_after < now_ts - 3600: # Stay within 1 hour of now
        batch = fetch_batch(current_after)
        if not batch:
            print("No more data or error.")
            break
        
        new_batch_max = current_after
        added = 0
        for item in batch:
            pid = item.get('id')
            ts = int(item.get('created_utc', 0))
            if ts > new_batch_max: new_batch_max = ts
            
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
                added += 1
        
        print(f"Batch {batch_count}: Added {added} records. Max TS updated to {datetime.fromtimestamp(new_batch_max, timezone.utc)}", flush=True)
        
        if added == 0 and len(batch) > 0:
            # Avoid infinite loop if all in batch are duplicates
            current_after = new_batch_max
        elif len(batch) == 0:
            break
        else:
            current_after = new_batch_max
            
        batch_count += 1
        if batch_count % 5 == 0:
            with open(RAW_FILE, 'w', encoding='utf-8') as f:
                json.dump(master_data, f)
        
        time.sleep(1.0) # Respect rate limits
        
    with open(RAW_FILE, 'w', encoding='utf-8') as f:
        json.dump(master_data, f)
        
    print(f"Extension complete. Total records: {len(master_data)}")

if __name__ == "__main__":
    run_extension()
