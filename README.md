# Reddit Sentiment Scanner (Growth Table + UI)

A Python app that scans Reddit posts/comments for ticker mentions, scores sentiment using bull/bear keywords, stores results in SQLite, and shows a clean UI growth table that tracks price performance since the first recorded run.

## What it does

- **Run Reddit Scan + Update**
  - Scans selected subreddits for ticker mentions
  - Tracks:
    - `mentions`
    - `bull`
    - `bear`
    - `score`
    - `time_of_run`
    - `price` (at the time of scan)
  - Saves first-seen tickers and their first-run values into **SQLite**

- **Refresh Growth Table**
  - Reads tickers from SQLite
  - Pulls current price using `yfinance`
  - Computes **Growth %** from the original run price
  - Displays a scrollable table in the UI

## Screenshots

Add your screenshot here:
- `docs/screenshot.png` (recommended)

Example:
![UI Screenshot](docs/screenshot.png)

---

## Requirements

- Python 3.10+ (recommended: Python 3.11)
- Internet connection (Reddit + yfinance)
- Reddit API credentials (required for scanning)

---

## Setup

### 1) Clone the repo
```bash
git clone <your-repo-url>
cd <your-repo-folder>
