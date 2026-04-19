import requests, re, json

HARM = [r'\baddict', r'\bdependenc', r'\bdependent\b', r'\bobsess', r'\bmanipulat', r'\bunhealthy\b', r'\btoxic\b', r'\bself[- ]harm', r'\bsuicid', r'\bdanger', r'\bunsafe\b', r'\bharmful\b', r'\bgroom']

def format_context(text, pattern):
    for m in re.finditer(pattern, text, flags=re.IGNORECASE):
        s, e = m.start(), m.end()
        start_idx = max(0, s - 60)
        end_idx = min(len(text), e + 60)
        prefix = '' if start_idx == 0 else '...'
        suffix = '' if end_idx == len(text) else '...'
        # Safely build string
        snippet = prefix + text[start_idx:s] + "<mark>" + text[s:e] + "</mark>" + text[e:end_idx] + suffix
        return snippet.strip()
    return ''

def fetch_authentic(start, end):
    res = []
    url = f'https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=CharacterAI&limit=100&after={start}&before={end}&sort=asc'
    data = requests.get(url, timeout=10).json().get('data', [])
    for p in data:
        if len(res) >= 5: break
        title = str(p.get('title', ''))
        txt = str(p.get('selftext', '')).replace('\n', ' ')
        if txt in ['[removed]', '[deleted]'] or not txt: txt = ''
        
        matched = False
        for pat in HARM:
            if re.search(pat, title, re.IGNORECASE):
                 s_title = re.sub(pat, lambda x: f'<mark>{x.group()}</mark>', title, flags=re.IGNORECASE)
                 res.append({'title': s_title, 'text': (txt[:100] + '...' if len(txt)>100 else txt), 'match': pat})
                 matched = True
                 break
        if matched: continue
        
        for pat in HARM:
            if re.search(pat, txt, re.IGNORECASE):
                 snippet = format_context(txt, pat)
                 res.append({'title': title[:120], 'text': snippet, 'match': pat})
                 break
    return res

print('--- 2024-W43 (Lawsuit Week) ---')
print(json.dumps(fetch_authentic(1729468800, 1730073600), indent=2))
print('\n--- 2025-W15 (Peak Harm Week) ---')
print(json.dumps(fetch_authentic(1744012800, 1744617600), indent=2))
