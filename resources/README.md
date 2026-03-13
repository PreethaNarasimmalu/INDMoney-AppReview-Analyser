# Submission Resources — INDMoney App Review Pulse

| File | What it is |
|------|-----------|
| `weekly_note.md` | Sample one-page weekly pulse note (Week of 2026-03-09) |
| `email_draft.md` | Text/markdown representation of the styled HTML email sent to subscribers |
| `sample_reviews.csv` | 20-row sample of the scraped & classified Google Play reviews used as input |
| `README.md` | This file — re-run guide + theme legend |

---

## How to re-run for a new week

### Prerequisites
```bash
pip install -r requirements.txt
cp .env.example .env          # add GROQ_API_KEY, GEMINI_API_KEY, GMAIL_ADDRESS, GMAIL_APP_PASSWORD
```

### Option A — Streamlit dashboard (recommended)
```bash
streamlit run app.py
```
1. Enter app ID (`com.indmoney`) and date window (default: 8 weeks)
2. Click **Fetch Reviews** → **Analyse** → **Generate Pulse**
3. The weekly note renders in the browser and is saved to `output/weekly_pulse.md`
4. Use the **Send** tab to email it to subscribers

### Option B — Automated weekly via GitHub Actions
The workflow at `.github/workflows/weekly_pulse.yml` runs every Monday at 07:00 UTC.

Required GitHub Secrets (set in repo → Settings → Secrets):
| Secret | Value |
|--------|-------|
| `GROQ_API_KEY` | Groq API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `GMAIL_ADDRESS` | Sender Gmail address |
| `GMAIL_APP_PASSWORD` | Gmail App Password (not account password) |

To trigger manually: **Actions → Weekly Pulse → Run workflow**

### Option C — CLI (headless)
```bash
python -m scheduler.run
```
Runs the full pipeline (scrape → classify → generate → email) once and exits.

---

## Pipeline Stages

```
Phase 1  Scrape        google-play-scraper  →  SQLite (reviews)
Phase 2  Classify      Groq LLM             →  SQLite (themes + classified reviews)
Phase 3  Summarise     Gemini LLM           →  output/weekly_pulse.md
Phase 4  Email         SMTP / Gmail         →  inbox
Phase 5  Dashboard     Streamlit            →  browser
```

---

## Theme Legend

Themes are **discovered dynamically each week** by the LLM from the current
batch of reviews — they are not hardcoded. The table below shows the typical
recurring categories seen in INDMoney reviews.

| Theme (example label) | What it covers | Colour in email |
|-----------------------|---------------|-----------------|
| **Login & OTP Issues** | Sign-in failures, OTP not arriving, biometric auth breaking after updates | Blue card |
| **Portfolio Sync Delays** | Stale NAV / holdings, slow refresh, incorrect balances | Blue card |
| **US Stocks Experience** | International order failures, currency conversion, real-time pricing | Blue card |
| **Smart Save / Goals** | Automated savings, round-ups, goal tracking — usually positive | Blue card |
| **App Performance** | Crashes, slow load, UI glitches | Blue card |

> **Note:** The number of themes per week is 3–5, controlled by `phase2/config.py`
> (`MIN_THEMES = 3`, `MAX_THEMES = 5`). Themes with fewer than 2 reviews are
> merged into the nearest related theme by the validator.

### Email card colour coding

| Section | Border colour | Background |
|---------|--------------|------------|
| Top Themes | Navy `#0f3460` | `#f8f9ff` |
| User Voices (quotes) | Amber `#f5a623` | `#fffaf3` |
| What's Working | Purple `#a855f7` | `#fdf4ff` |
| Action Ideas | Green `#22c55e` | `#f0fdf4` |

---

## Key configuration files

| File | Controls |
|------|---------|
| `phase1/config.py` | App ID, date window, max reviews |
| `phase2/config.py` | Theme count, classifier batch size, review filters |
| `phase3/config.py` | LLM model, top-N themes to summarise |
| `phase4/config.py` | Email subject prefix |
| `scheduler/config.py` | Cron schedule, pipeline flags |
