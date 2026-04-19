import json
import pandas as pd
import re
from datetime import datetime, timezone

def run_audit():
    with open('data/CharacterAI_raw.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    df['dt'] = pd.to_datetime(df['created_utc'], unit='s', utc=True)
    df['iso_week'] = df['dt'].dt.strftime('%Y-W%V')
    
    # 1. 2024-W43 Slice
    w43 = df[df['iso_week'] == '2024-W43']
    vol = len(w43)
    
    # 2. Count using JSON Field (Matches stored during crawl)
    field_matches = w43['harm_matches'].apply(lambda x: len(x) > 0 if isinstance(x, list) else False).sum()
    
    # 3. Count using CURRENT 13 regexes in run_pipeline.py
    HARM_REGEX_13 = [
        r'\baddict', r'\bdependenc', r'\bdependent\b', r'\bobsess', r'\bmanipulat',
        r'\bunhealthy\b', r'\btoxic\b', r'\bself[- ]harm', r'\bsuicid', r'\bdanger',
        r'\bunsafe\b', r'\bharmful\b', r'\bgroom'
    ]
    regex_13 = re.compile('|'.join(HARM_REGEX_13), re.IGNORECASE)
    recalc_13 = w43.apply(lambda r: bool(re.search(regex_13, str(r['title']) + ' ' + str(r['selftext']))), axis=1).sum()
    
    # 4. Count using 27 HARM_TERMS in config.py
    HARM_TERMS_27 = [
        'addicted', 'addiction', 'dependent', 'dependency', 'obsessed', 'obsession',
        "can't stop", 'cant stop', 'hooked', 'manipulative', 'manipulated', 'grooming',
        'predatory', 'exploitation', 'unsafe', 'dangerous', 'toxic', 'self-harm',
        'self harm', 'selfharm', 'suicidal', 'suicide', 'harmful', 'hurt myself',
        'worried', 'concerning', 'inappropriate', 'creepy'
    ]
    recalc_27 = w43.apply(lambda r: any(term in (str(r['title']) + ' ' + str(r['selftext'])).lower() for term in HARM_TERMS_27), axis=1).sum()
    
    print(f'--- AUDIT: 2024-W43 CharacterAI ---')
    print(f'Total Volume: {vol}')
    print(f'Field Matches (stored): {field_matches} (Rate: {field_matches/vol:.4f})')
    print(f'Regex-13 Matches (current): {recalc_13} (Rate: {recalc_13/vol:.4f})')
    print(f'Terms-27 Matches (config): {recalc_27} (Rate: {recalc_27/vol:.4f})')
    
    # 5. Check if crawl touched pre-2025-05-09 data
    # Min timestamp in original data before crawl was ~Aug 2024.
    # Start timestamp of my crawl was May 9, 2025.
    # If anything was added/changed before that, we'll see if backup differs.
    
    with open('data/CharacterAI_raw.backup.json', 'r', encoding='utf-8') as b:
        b_data = json.load(b)
    
    b_df = pd.DataFrame(b_data)
    b_df['dt'] = pd.to_datetime(b_df['created_utc'], unit='s', utc=True)
    b_df['iso_week'] = b_df['dt'].dt.strftime('%Y-W%V')
    
    bw43 = b_df[b_df['iso_week'] == '2024-W43']
    print(f'\n--- BACKUP CHECK: 2024-W43 ---')
    print(f'Backup Volume: {len(bw43)}')
    
    # Check if any new records were added PRE-May 9, 2025
    crawl_start_ts = 1746748800 # May 9, 2025 00:00:00 UTC
    new_records = df[~df['id'].isin(b_df['id'])]
    early_new = new_records[new_records['created_utc'] < crawl_start_ts]
    print(f'New records added predating May 9, 2025: {len(early_new)}')

if __name__ == '__main__':
    run_audit()
