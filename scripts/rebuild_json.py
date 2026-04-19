import json, re, pandas as pd

HARM = [r'\baddict', r'\bdependenc', r'\bdependent\b', r'\bobsess', r'\bmanipulat', r'\bunhealthy\b', r'\btoxic\b', r'\bself[- ]harm', r'\bsuicid', r'\bdanger', r'\bunsafe\b', r'\bharmful\b', r'\bgroom']
BENEFIT = [r'\bhelp', r'\bsupport', r'\bcomfort', r'\bcope\b', r'\bcoping\b', r'\blonel', r'\banxi', r'\bgrief', r'\bgrieving\b', r'\bheal', r'\bcompanion', r'\bunderstand', r'\btherap']

def format_context(text, pattern):
    for m in re.finditer(pattern, text, flags=re.IGNORECASE):
        s, e = m.start(), m.end()
        start_idx = max(0, s - 60)
        end_idx = min(len(text), e + 60)
        prefix = '' if start_idx == 0 else '...'
        suffix = '' if end_idx == len(text) else '...'
        snippet = prefix + text[start_idx:s] + '<mark>' + text[s:e] + '</mark>' + text[e:end_idx] + suffix
        return snippet.strip()
    return ''

# 1. Load Data
with open('data/CharacterAI_raw.json', 'r', encoding='utf-8') as f:
    cai_data = json.load(f)
with open('data/replika_raw.json', 'r', encoding='utf-8') as f:
    rep_data = json.load(f)
with open('docs/data/reddit_weekly.json', 'r', encoding='utf-8') as f:
    out = json.load(f)

df_cai = pd.DataFrame(cai_data)
if not df_cai.empty:
    df_cai['dt'] = pd.to_datetime(df_cai['created_utc'], unit='s', utc=True)
    df_cai['iso_week'] = df_cai['dt'].dt.strftime('%Y-W%V')

df_rep = pd.DataFrame(rep_data)
if not df_rep.empty:
    df_rep['dt'] = pd.to_datetime(df_rep['created_utc'], unit='s', utc=True)
    df_rep['iso_week'] = df_rep['dt'].dt.strftime('%Y-W%V')

def get_top_5(df_local, week, p_list):
    res = []
    wk_df = df_local[df_local['iso_week'] == week].sort_values('created_utc', ascending=True)
    for _, row in wk_df.iterrows():
        if len(res) >= 5: break
        title = str(row.get('title', ''))
        txt = str(row.get('selftext', '')).replace('\n', ' ')
        matched = False
        for pat in p_list:
            if re.search(pat, title, re.IGNORECASE):
                s_title = re.sub(pat, lambda x: f'<mark>{x.group()}</mark>', title, flags=re.IGNORECASE)
                res.append({'title': s_title, 'text': txt[:100] + ('...' if len(txt)>100 else '')})
                matched = True
                break
        if matched: continue
        for pat in p_list:
            if re.search(pat, txt, re.IGNORECASE):
                snippet = format_context(txt, pat)
                res.append({'title': title[:120], 'text': snippet})
                break
    return res

out['metadata']['excerpts']['CharacterAI_harm'] = {'week': '2025-W15', 'posts': get_top_5(df_cai, '2025-W15', HARM)}
out['metadata']['excerpts']['CharacterAI_benefit'] = {'week': '2024-W35', 'posts': get_top_5(df_cai, '2024-W35', BENEFIT)}
out['metadata']['excerpts']['replika_harm'] = {'week': '2024-W46', 'posts': get_top_5(df_rep, '2024-W46', HARM)}
out['metadata']['excerpts']['replika_benefit'] = {'week': '2025-W02', 'posts': get_top_5(df_rep, '2025-W02', BENEFIT)}

all_data_list = []
for d in cai_data:
    d['app'] = 'CharacterAI'
    d['has_harm'] = any(re.search(p, str(d.get('title','')) + ' ' + str(d.get('selftext','')), re.I) for p in HARM)
    d['has_benefit'] = any(re.search(p, str(d.get('title','')) + ' ' + str(d.get('selftext','')), re.I) for p in BENEFIT)
    all_data_list.append(d)
for d in rep_data:
    d['app'] = 'replika'
    d['has_harm'] = any(re.search(p, str(d.get('title','')) + ' ' + str(d.get('selftext','')), re.I) for p in HARM)
    d['has_benefit'] = any(re.search(p, str(d.get('title','')) + ' ' + str(d.get('selftext','')), re.I) for p in BENEFIT)
    all_data_list.append(d)

df = pd.DataFrame(all_data_list)
df['dt'] = pd.to_datetime(df['created_utc'], unit='s', utc=True)
df['iso_week'] = df['dt'].dt.strftime('%Y-W%V')

weekly = df.groupby(['app', 'iso_week']).agg(volume=('id', 'count'), harm_count=('has_harm', 'sum'), benefit_count=('has_benefit', 'sum')).reset_index()
weekly['harm_rate'] = weekly['harm_count'] / weekly['volume']
weekly['benefit_rate'] = weekly['benefit_count'] / weekly['volume']

out['weekly'] = weekly.to_dict(orient='records')

with open('docs/data/reddit_weekly.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
print('JSON Rewrite Successful!')
