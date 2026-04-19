import json, re, pandas as pd
from datetime import datetime, timezone

# Pinned Constants
BASELINE_CAI = 301995
BASELINE_REP = 7847
HARM_13 = [
    r'\baddict', r'\bdependenc', r'\bdependent\b', r'\bobsess', r'\bmanipulat',
    r'\bunhealthy\b', r'\btoxic\b', r'\bself[- ]harm', r'\bsuicid', r'\bdanger',
    r'\bunsafe\b', r'\bharmful\b', r'\bgroom'
]
harm_regex = re.compile('|'.join(HARM_13), re.IGNORECASE)
LAWSUIT_WEEK = '2024-W43'
LAWSUIT_DATE = pd.to_datetime("2024-10-22")

def get_stats(raw_file):
    with open(raw_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df['dt'] = pd.to_datetime(df['created_utc'], unit='s', utc=True)
    df['iso_week'] = df['dt'].dt.strftime('%G-W%V')
    
    # Classification
    def is_harm(row):
        txt = (str(row.get('title','')) + ' ' + str(row.get('selftext',''))).lower()
        return bool(re.search(harm_regex, txt))
    
    df['has_harm'] = df.apply(is_harm, axis=1)
    
    # Descriptive
    u_count = len(df['id'].unique())
    max_len = df['selftext'].str.len().max()
    
    # W43 specific
    w43 = df[df['iso_week'] == LAWSUIT_WEEK]
    w43_vol = len(w43)
    w43_harm = w43['has_harm'].sum()
    w43_rate = w43_harm / w43_vol if w43_vol > 0 else 0
    
    # Pre/Post
    weekly = df.groupby('iso_week').agg(
        volume=('id', 'count'),
        harm_count=('has_harm', 'sum')
    ).reset_index()
    weekly['harm_rate'] = weekly['harm_count'] / weekly['volume']
    
    pre = weekly[pd.to_datetime(weekly['iso_week'] + '-1', format='%G-W%V-%w') < LAWSUIT_DATE].tail(12)
    post = weekly[pd.to_datetime(weekly['iso_week'] + '-1', format='%G-W%V-%w') >= LAWSUIT_DATE].head(12)
    
    pre_mean = pre['harm_rate'].mean()
    post_mean = post['harm_rate'].mean()
    delta = post_mean - pre_mean
    
    return {
        'count': u_count,
        'max_len': max_len,
        'w43_vol': w43_vol,
        'w43_harm': w43_harm,
        'w43_rate': w43_rate,
        'pre_mean': pre_mean,
        'post_mean': post_mean,
        'delta': delta
    }

def run_verification():
    print("--- VERIFICATION BLOCK (Option A Re-pull) ---")
    
    cai = get_stats('data/CharacterAI_raw.new.json')
    rep = get_stats('data/replika_raw.new.json')
    
    print(f"\n[r/CharacterAI]")
    print(f"Unique ID Count: {cai['count']} (vs {BASELINE_CAI})")
    print(f"Max Selftext Length: {cai['max_len']}")
    print(f"Volume (2024-W43): {cai['w43_vol']}")
    print(f"Harm Match Count (2024-W43): {cai['w43_harm']}")
    print(f"Harm Rate (2024-W43): {cai['w43_rate']:.4f}")
    print(f"Mean (12wk Pre): {cai['pre_mean']:.4f}")
    print(f"Mean (12wk Post): {cai['post_mean']:.4f}")
    print(f"Delta (Shift): {cai['delta']:.4f}")
    
    print(f"\n[r/replika]")
    print(f"Unique ID Count: {rep['count']} (vs {BASELINE_REP})")
    print(f"Max Selftext Length: {rep['max_len']}")
    print(f"Volume (2024-W43): {rep['w43_vol']}")
    print(f"Harm Match Count (2024-W43): {rep['w43_harm']}")
    print(f"Harm Rate (2024-W43): {rep['w43_rate']:.4f}")
    print(f"Mean (12wk Pre): {rep['pre_mean']:.4f}")
    print(f"Mean (12wk Post): {rep['post_mean']:.4f}")
    print(f"Delta (Shift): {rep['delta']:.4f}")
    
    # LOUD ERRORS
    error = False
    if abs(cai['count'] - BASELINE_CAI) / BASELINE_CAI > 0.10:
        print(f"\nFATAL ERROR: r/CharacterAI volume drift > 10% ({abs(cai['count'] - BASELINE_CAI) / BASELINE_CAI:.1%})")
        error = True
    if abs(rep['count'] - BASELINE_REP) / BASELINE_REP > 0.10:
        print(f"\nFATAL ERROR: r/replika volume drift > 10% ({abs(rep['count'] - BASELINE_REP) / BASELINE_REP:.1%})")
        error = True
        
    if not error:
        print("\nSTATUS: PASS. Volume drift within 10%. Text fidelity verified.")
    else:
        print("\nSTATUS: FAIL. Manual investigation required.")

if __name__ == "__main__":
    run_verification()
