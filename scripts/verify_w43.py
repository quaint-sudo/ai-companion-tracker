import json
import re
import pandas as pd
from datetime import datetime, timezone

def verify():
    print("Loading data...")
    try:
        with open('data/CharacterAI_raw.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading file: {e}")
        return
    
    df = pd.DataFrame(data)
    df['dt'] = pd.to_datetime(df['created_utc'], unit='s', utc=True)
    df['iso_week'] = df['dt'].dt.strftime('%Y-W%V')
    
    # Filter for 2024-W43
    w43 = df[df['iso_week'] == '2024-W43'].copy()
    
    # 13 patterns from run_pipeline.py
    patterns = [
        r"\baddict", r"\bdependenc", r"\bdependent\b", r"\bobsess", r"\bmanipulat",
        r"\bunhealthy\b", r"\btoxic\b", r"\bself[- ]harm", r"\bsuicid", r"\bdanger",
        r"\bunsafe\b", r"\bharmful\b", r"\bgroom"
    ]
    
    def classify(row):
        title = str(row.get('title', ''))
        selftext = str(row.get('selftext', ''))
        full_text = (title + " " + selftext).lower()
        matches = []
        for p in patterns:
            if re.search(p, full_text, re.I):
                matches.append(p)
        return len(matches) > 0

    w43['is_harm'] = w43.apply(classify, axis=1)
    
    vol = len(w43)
    count = w43['is_harm'].sum()
    rate = count / vol if vol > 0 else 0
    
    print(f"2024-W43 Results:")
    print(f"Volume: {vol}")
    print(f"Harm Count: {count}")
    print(f"Harm Rate: {rate:.4%}")
    
    # Check if this matches the 3.24% target
    # Target was 189 / 5825 = 3.2446%
    if abs(rate - 0.0324) < 0.001:
        print("\nSUCCESS: Matches high-fidelity baseline!")
    else:
        print(f"\nFAILURE: Rate is {rate:.4%}, target was ~3.24%.")
        
        # Try larger list from config.py
        config_terms = [
            "addicted", "addiction", "dependent", "dependency", "obsessed", "obsession",
            "can't stop", "cant stop", "hooked",
            "manipulative", "manipulated", "grooming", "predatory", "exploitation",
            "unsafe", "dangerous", "toxic",
            "self-harm", "self harm", "selfharm", "suicidal", "suicide",
            "harmful", "hurt myself",
            "worried", "concerning", "inappropriate", "creepy",
        ]
        
        def classify_config(row):
            text = (str(row.get('title', '')) + " " + str(row.get('selftext', ''))).lower()
            return any(t.lower() in text for t in config_terms)
            
        w43['is_harm_config'] = w43.apply(classify_config, axis=1)
        config_count = w43['is_harm_config'].sum()
        config_rate = config_count / vol
        print(f"Config List Rate: {config_rate:.4%} ({config_count} matches)")

if __name__ == "__main__":
    verify()
