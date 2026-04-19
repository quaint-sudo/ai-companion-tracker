#!/usr/bin/env python3
"""
AI Companion Narrative Shift Tracker — Manual Refresh

Run this script to collect the latest data and update the dashboard:

    python refresh.py

This will:
  1. Fetch exact historical timestamps for up to 500 App Store reviews per app
  2. Classify text using seeded benefit/harm term lists
  3. Group reviews by their exact week (YYYY-WNN)
  4. Output the time-series trends to appstore_weekly.csv

After running, commit and push to update the GitHub Pages dashboard:

    git add docs/data/
    git commit -m "data: weekly update YYYY-WNN"
    git push
"""

from scripts.fetch_appstore import run as run_appstore


def main():
    print("============================================================")
    print("  AI Companion Narrative Shift Tracker - Manual Refresh")
    print("  Character.AI + Replika")
    print("============================================================")

    run_appstore()

    print("\n" + "=" * 60)
    print("  ✓ Refresh complete.")
    print()
    print("  Next steps:")
    print("    1. Review the output above for any warnings")
    print("    2. Spot-check the sample matches for accuracy")
    print("    3. Commit and push to update the live dashboard:")
    print()
    print('       git add docs/data/')
    print('       git commit -m "data: weekly update"')
    print('       git push')
    print("=" * 60)


if __name__ == "__main__":
    main()
