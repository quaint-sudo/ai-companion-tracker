import requests, json, time, re

HARM = [r'\baddict', r'\bdependenc', r'\bdependent\b', r'\bobsess', r'\bmanipulat', r'\bunhealthy\b', r'\btoxic\b', r'\bself[- ]harm', r'\bsuicid', r'\bdanger', r'\bunsafe\b', r'\bharmful\b', r'\bgroom']
BENEFIT = [r'\bhelp', r'\bsupport', r'\bcomfort', r'\bcope\b', r'\bcoping\b', r'\blonel', r'\banxi', r'\bgrief', r'\bgrieving\b', r'\bheal', r'\bcompanion', r'\bunderstand', r'\btherap']

url = 'https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=CharacterAI&limit=100&sort=desc'
data = []
for i in range(10):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            batch = r.json().get('data', [])
            for item in batch:
                ts = int(item.get('created_utc', 0))
                title = str(item.get('title', ''))
                text = str(item.get('selftext') or '').replace('\n', ' ')
                if text in ['[removed]', '[deleted]']: text = ''
                t_full = title + ' ' + text
                h = [p for p in HARM if re.search(p, t_full, re.IGNORECASE)]
                b = [p for p in BENEFIT if re.search(p, t_full, re.IGNORECASE)]
                data.append({'id': item['id'], 'created_utc': ts, 'title': title[:120], 'selftext': text[:100], 'harm_matches': h, 'benefit_matches': b, 'permalink': item.get('permalink', '')})
            if batch:
                m_ts = min([int(x["created_utc"]) for x in batch])
                url = f'https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=CharacterAI&limit=100&sort=desc&before={m_ts}'
    except: pass

with open('data/CharacterAI_raw.json', 'r', encoding='utf-8') as f:
    existing = json.load(f)

existing.extend(data)

with open('data/CharacterAI_raw.json', 'w', encoding='utf-8') as f:
    json.dump(existing, f)
print('Latest 1000 records fetched successfully.')
