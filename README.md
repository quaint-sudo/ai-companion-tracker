# AI Companion Narrative Shift Tracker

An automated data pipeline and public dashboard that monitors how users and online communities talk about AI companion apps over time — specifically testing whether narrative shifts around **harm**, **dependency**, and **benefit** appear before or after major public incidents.

## 🎯 Target Apps

| App | App Store | Reddit |
|-----|-----------|--------|
| **Character.AI** | ✅ iOS Reviews | r/CharacterAI |
| **Replika** | ✅ iOS Reviews | r/replika |
| **Pi** | ✅ iOS Reviews | — |
| **Woebot** | ✅ iOS Reviews | — |
| **General AI** | — | r/artificial |

## 📊 What We Track

### App Store (iOS)
- Weekly review volume per app
- Benefit language rate (% of reviews with benefit terms)
- Harm language rate (% of reviews with harm terms)
- Net sentiment score (benefit rate − harm rate)

### Reddit
- Weekly post and comment volume per subreddit
- Benefit/harm language rates
- Week-over-week sentiment velocity (rate of narrative change)

## 🏷️ Classification Dictionaries

**Benefit terms:** support, helpful, anxiety, loneliness, comfort, grief, supportive, helped, helps, comforting, comforted, therapeutic, therapy, coping, safe space, mental health, emotional support, calming, reassuring, well-being

**Harm terms:** addicted, manipulative, dependent, obsessed, unsafe, self-harm, addiction, manipulated, dependency, obsession, dangerous, toxic, predatory, exploitation, grooming, suicidal, self harm, selfharm, harmful

## ⚙️ How It Works

1. **GitHub Actions** runs every Monday at 06:00 UTC
2. Python scripts fetch iOS App Store reviews (via RSS) and Reddit posts/comments (via PRAW)
3. Each text is classified using dictionary-based keyword matching
4. Weekly aggregates are appended to CSV files in `data/`
5. Updated CSVs are auto-committed back to the repo
6. The **GitHub Pages** dashboard reads the CSVs and renders live charts

**Zero manual intervention** after initial setup.

## 🚀 Setup

### 1. Clone & Install
```bash
git clone https://github.com/YOUR_USERNAME/ai-companion-tracker.git
cd ai-companion-tracker
pip install -r requirements.txt
```

### 2. Reddit API Credentials
1. Go to https://www.reddit.com/prefs/apps
2. Create a "script" type application
3. Add these as **GitHub Repository Secrets**:
   - `REDDIT_CLIENT_ID`
   - `REDDIT_CLIENT_SECRET`

### 3. Enable GitHub Pages
1. Go to **Settings → Pages**
2. Set source to **Deploy from a branch**
3. Select `main` branch and `/dashboard` folder
4. Your dashboard will be live at `https://YOUR_USERNAME.github.io/ai-companion-tracker/`

### 4. First Run
Trigger the workflow manually:
1. Go to **Actions → Weekly Data Update → Run workflow**
2. Wait ~2 minutes for data collection
3. Check `data/` for the first CSV entries

## 🧪 Running Tests
```bash
pytest tests/ -v
```

## 📁 Project Structure
```
ai-companion-tracker/
├── .github/workflows/weekly_update.yml   # Automated weekly pipeline
├── ingestion/
│   ├── appstore_rss.py                   # App Store review scraper
│   ├── reddit_api.py                     # Reddit post/comment scraper
│   ├── classifier.py                     # Benefit/harm keyword classifier
│   └── config.py                         # All configuration & dictionaries
├── data/
│   ├── appstore_weekly.csv               # Auto-generated App Store data
│   └── reddit_weekly.csv                 # Auto-generated Reddit data
├── dashboard/
│   ├── index.html                        # Public dashboard
│   ├── style.css                         # Dashboard styling
│   └── app.js                            # Chart rendering logic
├── tests/                                # Unit & smoke tests
└── requirements.txt
```

## 📜 License

MIT
