# INDMoney App Review Pulse

A tool that scrapes Google Play reviews for any app, groups them into themes using AI, and delivers a one-page weekly pulse report by email — with a Streamlit dashboard to run it on demand.

---

## What it does

1. **Scrapes** recent Google Play reviews (configurable window: 1–16 weeks)
2. **Removes PII** automatically before any data is stored or sent to an LLM
3. **Discovers themes** from the reviews using Groq (e.g. "Login Issues", "Slow Performance")
4. **Classifies** every review into a theme
5. **Generates a report** — summaries, user quotes, what's working, action ideas — using Gemini
6. **Emails the report** as a formatted HTML email via Gmail
7. **Runs automatically** every Monday at 9 AM IST via GitHub Actions

---

## Prerequisites

- Python 3.11+
- A [Groq API key](https://console.groq.com) (free tier works)
- A [Gemini API key](https://aistudio.google.com) (free tier works)
- A Gmail account with an [App Password](https://myaccount.google.com/apppasswords) set up

---

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd INDMoney-AppReview-Analyser
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your keys:

```env
# Theme grouping (Phase 2)
GROQ_API_KEY=your_groq_api_key_here

# Report generation (Phase 3)
GEMINI_API_KEY=your_gemini_api_key_here

# Email sending (Phase 4)
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
EMAIL_RECIPIENT=team@yourcompany.com
```

> **Gmail App Password:** Go to Google Account → Security → 2-Step Verification → App passwords. Generate one for "Mail". Use that 16-character password here — not your regular Gmail password.

### 3. Run the dashboard

```bash
streamlit run phase5/app.py
```

The app opens at `http://localhost:8501`.

---

## Using the Dashboard

### Run pipeline

1. Select how many **weeks of reviews** to analyse (1–16)
2. Enter **max reviews** to fetch (100–5000; 500 is a good starting point)
3. Click **Run full pipeline**

The status bar shows live progress through five stages: Reviews → Themes → Grouped → Report → Draft email. This typically takes 2–5 minutes depending on review count.

### View the report

After the pipeline finishes, click **Load latest report** to read the pulse note inline.

### Download the report

Click **Download .md** to save the pulse note as a Markdown file.

### Send an email

Enter a recipient email (and optional name) and click **Send email**. The formatted HTML email is sent immediately via your configured Gmail account.

### Subscribe to the weekly pulse

Enter an email and name in the **Subscribe** card. Subscribers automatically receive the pulse every Monday at 9 AM IST when the GitHub Actions scheduler runs. An unsubscribe link is included in every automated email.

---

## Pages

| Page | URL path | What it shows |
|------|----------|---------------|
| Dashboard | `/` | Pipeline runner, report viewer, email sender, subscriptions |
| Reviews | `/Reviews` | Full reviews table — filter by date, rating, theme, or keyword |
| Themes | `/Themes` | Theme cards with descriptions and review counts |
| Unsubscribe | `/Unsubscribe?email=you@example.com` | One-click unsubscribe (linked from email footer) |

---

## Automated weekly email (GitHub Actions)

The workflow at `.github/workflows/weekly_pulse.yml` runs every Monday at 09:00 IST and emails the pulse to all subscribers.

### Setting it up

Add these secrets to your GitHub repository (Settings → Secrets → Actions):

| Secret | Value |
|--------|-------|
| `GROQ_API_KEY` | Your Groq API key |
| `GEMINI_API_KEY` | Your Gemini API key |
| `GMAIL_ADDRESS` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | Your Gmail App Password |
| `SCHEDULER_RECIPIENT_EMAIL` | Fallback recipient email (if no subscribers in DB) |
| `SCHEDULER_RECIPIENT_NAME` | Fallback recipient name |

The scheduler reads recipients in this priority order:
1. `subscribers.json` in the repo (managed via the Subscribe card)
2. SQLite subscriber table
3. `SCHEDULER_RECIPIENTS` secret (comma-separated `Name:email` pairs)
4. Legacy `SCHEDULER_RECIPIENT_EMAIL` secret

### Trigger manually

Go to **Actions → Weekly App Review Pulse → Run workflow** in GitHub to trigger a run outside the Monday schedule.

---

## Running tests

```bash
pytest
```

All 365+ tests should pass. To run tests for a specific phase:

```bash
pytest phase1/tests/
pytest phase2/tests/
pytest phase3/tests/
pytest phase4/tests/
pytest phase5/tests/
pytest scheduler/tests/
```

---

## Configuration defaults

| Setting | Default | Where to change |
|---------|---------|-----------------|
| App ID | `com.indmoney` | `phase1/config.py` |
| Lookback window | 8 weeks | Dashboard UI or `phase1/config.py` |
| Max reviews | 1 000 | Dashboard UI or `phase1/config.py` |
| Scheduler lookback | 3 weeks | `SCHEDULER_WEEKS` env var |
| Scheduler max reviews | 200 | `SCHEDULER_MAX_REVIEWS` env var |
| Email schedule | Monday 09:00 IST | `.github/workflows/weekly_pulse.yml` |

To analyse a different app, change `app_id` in `phase1/config.py` to any Google Play app ID (the `id=` parameter from the Play Store URL).

---

## Project structure

```
phase1/       Review scraping & PII removal
phase2/       Theme discovery & classification (Groq)
phase3/       Report generation (Gemini)
phase4/       Email composition & sending (Gmail)
phase5/       Streamlit dashboard
scheduler/    GitHub Actions entry point
llm_client/   Shared LLM wrappers (Groq, Gemini)
.github/      CI/CD workflows
```
