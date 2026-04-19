# AI Companion Narrative Shift Tracker

An indicator of harm-language discourse in Reddit communities for Character.AI and Replika. 

## Live dashboard

https://quaint-sudo.github.io/ai-companion-tracker/

## What this tracks

Weekly rate of submissions in r/CharacterAI and r/replika that match at least one of 13 pre-registered harm-language regex patterns. See the live dashboard's methodology section for detail.

## Repository structure

- docs/: Static dashboard site (served by GitHub Pages)
- data/: Raw submission corpus from PullPush and Arctic Shift
- scripts/: Python pipeline for data aggregation and classification
- .github/workflows/: Manual-trigger update workflow

## Updating the dashboard

The tracker supports both manual and scheduled updates.

To update manually:
  1. Clone the repo
  2. pip install -r requirements.txt
  3. python scripts/run_pipeline.py
  4. Commit and push the updated docs/data/reddit_weekly.json

A GitHub Actions workflow at .github/workflows/manual_update.yml runs the same pipeline on demand via the Actions tab. Scheduled updates are not enabled in this version. A cron schedule can be enabled by uncommenting the schedule block in that workflow file.

## Reproducibility

All harm and benefit term lists are committed in `scripts/run_pipeline.py`. Raw submission data is preserved untruncated in `data/`. Weekly aggregates in `docs/data/reddit_weekly.json` are regenerated from the raw corpus. Any researcher can clone this repo and reproduce the numbers.

## Accompanying paper

[Paper title to be added post-submission] — Spring 2026.
