# Architecture: INDMoney App Review Weekly Pulse

## Overview

```
App Store Reviews → Ingestion → Theme Grouping (Groq) → Weekly Note Generation (Gemini) → Email Draft → UI
```

---

## Phase 1 — Data Ingestion (No LLM)

**Goal:** Collect raw reviews from the last 8 weeks (default), scrub PII, store in SQLite.

### Components

#### 1.1 Review Fetcher (`phase1/scraper.py`)
- Source: Google Play Store via `google-play-scraper`
- Fields: `rating`, `title`, `review_text`, `date`, `platform`
- Filter: reviews within configured date window (default 8 weeks)
- Stop condition: date cutoff OR count cap (default 1000), whichever comes first
- Output: list of raw review objects

#### 1.2 PII Scrubber (`phase1/pii_scrubber.py`)
- Runs immediately after fetch, before any storage or LLM call
- Strips: names, emails, phone numbers, usernames, device IDs (regex + spaCy NER)
- Replaces with: `[REDACTED]`
- **Hard gate — no review passes through without scrubbing**

#### 1.3 Review Store (`phase1/review_store.py`)
- SQLite: `data/reviews.db`
- Schema: `id, platform, rating, title, clean_text, date, week_label`
- Deduplicated by review ID to support re-runs
- **Retention policy:** on every run, reviews older than 12 weeks are deleted (`purge_old_reviews`) — DB stays bounded, no manual cleanup needed
- Configurable via `RETENTION_WEEKS` in `phase1/config.py` (default: 12)

**IN:** Google Play package name, date range config
**OUT:** `reviews.db` with clean, PII-free review rows

---

## Phase 2 — Theme Grouping (Groq)

**Goal:** Use Groq LLM to discover themes, then assign each review to a theme.

### Components

#### 2.0 Review Filter (`phase2/review_filter.py`)
- Applied once before any LLM call — reduces token usage and improves theme quality
- Removes:
  - **Too short** — fewer than 5 words
  - **Low signal** — < 40% alphabetic chars (emoji-only, number spam)
  - **All-caps spam** — > 80% uppercase letters
  - **Exact duplicates** — same text (case-insensitive, whitespace-normalised), keep first
- Returns filtered list + stats dict (counts per filter reason)
- Integrated into `classify_reviews` and `discover_themes` — callers get filtered reviews automatically

#### 2.1 Theme Discovery — LLM Call 1 (`phase2/theme_discovery.py`)
- Input: up to `MAX_REVIEWS_FOR_DISCOVERY` (150) reviews, **sampled proportionally across star ratings 1–5** via `_sample_by_rating()` — ensures themes reflect the full rating spectrum, not just whichever rating has the most volume
- Each review text truncated to `REVIEW_TEXT_TRUNCATE` (150) chars to stay under Groq's 12k TPM limit
- Prompt: read sampled reviews → return exactly 3–5 distinct theme labels with short descriptions
- Output: `[{ "theme_id": 1, "label": "...", "description": "..." }, ...]`
- Model: Groq `llama-3.3-70b-versatile` with `response_format={"type":"json_object"}` (JSON mode) to guarantee valid JSON output

#### 2.2 Review Classifier — LLM Call 2 (`phase2/classifier.py`)
- Input: each review + theme list from 2.1
- Prompt: assign this review to exactly one theme
- Batched in groups of 20 reviews per Groq call (reduced from 30 to stay within TPM limits)
- Uses JSON mode (`response_format={"type":"json_object"}`) to guarantee valid JSON
- Output: `review_id → theme_id` mapping stored back into `reviews.db`

#### 2.3 Theme Validator
- Sanity check: each theme must have ≥ 2 reviews
- If < 2 reviews: merge into closest theme
- Final theme count stays within 3–5

**IN:** Clean reviews from `reviews.db`
**OUT:** `themes.json`, `reviews.db` updated with theme assignments

---

## Phase 3 — Weekly Note Generation (Gemini)

**Goal:** Produce a structured one-page weekly pulse document.

### Components

#### 3.1 Theme Summariser + Quote Picker — LLM Call 3 (`phase3/note_generator.py`)
- For each of the top 3 themes (ranked by review count):
  - Summarise in 2–3 sentences
  - Select the single most representative user quote (verbatim, already PII-free)
- Output: `{ theme_label, summary, representative_quote } × 3`

#### 3.2 Action Idea Generator + What's Working — LLM Call 4 (`phase3/note_generator.py`)
- Input: 3 theme summaries
- Prompt: given these themes, propose 3 concrete actionable product/support recommendations **and** identify 3 things users are praising that should be preserved or amplified
- Output: `(["Action 1: ...", ...], ["Working 1: ...", ...])` — both lists returned from a single Gemini call

#### 3.3 Note Assembler (`phase3/assembler.py`)
- Pure formatting — **no LLM call**
- Combines 3.1 + 3.2 into fixed Markdown template → `output/weekly_pulse.md`

```
Weekly App Review Pulse — Week of [DATE]
─────────────────────────────────────────
TOP THEMES
  1. [Theme Label] — [Summary]
  2. ...
  3. ...

USER VOICES
  "[Quote 1]"  — [Platform], [Star Rating]★
  "[Quote 2]"  — ...
  "[Quote 3]"  — ...

WHAT'S WORKING
  1. [Working 1]
  2. [Working 2]
  3. [Working 3]

ACTION IDEAS
  1. [Action]
  2. [Action]
  3. [Action]
```

**IN:** `themes.json`, classified reviews from `reviews.db`
**OUT:** `output/weekly_pulse.md`

---

## Phase 4 — Email Draft & Delivery

**Goal:** Send the weekly pulse as a draft email.

### Components

#### 4.1 Email Composer (`phase4/composer.py`)
- Wraps `weekly_pulse.md` into HTML email body (plain text fallback)
- Subject: `INDMoney App Review Pulse — Week of [DATE]`
- Recipient: entered inline in UI at send time — never hardcoded
- Footer includes a per-recipient **unsubscribe link**: `https://indmoney-appreview-analyser.streamlit.app/Unsubscribe?email={recipient_email}` — clicking it opens the Unsubscribe page and removes that address automatically

#### 4.2 Email Sender (`phase4/sender.py`)
- Transport: Gmail SMTP via App Password
- Credentials: loaded from `.env` — never in source code
- Creates draft in Gmail Drafts folder for human review before sending

**IN:** `weekly_pulse.md`, Gmail credentials from env
**OUT:** Draft email in Gmail Drafts

---

## Phase 5 — Streamlit UI

**Goal:** Manage the full pipeline from a browser.

### Layout & Branding
- INDMoney brand colors: `#2DB34A` green, `#1A1A1A` near-black, `#F7F8FA` background
- Sidebar hidden entirely; all controls inline in main content area
- `sys.path` fix at top of every page file so Streamlit can resolve package imports regardless of working directory

### Dashboard (`phase5/app.py`) — vertical section-card layout
1. **Status card** — five pipeline stage badges (Reviews → Themes → Grouped → Report → Draft email); rendered via `st.empty()` placeholder so badges turn green **live during execution** as each stage completes (Reviews@20%, Themes@50%, Grouped@60%, Report@90%, Draft email@100%); all green + report date shown after full run
2. **Run pipeline card** — description text, weeks dropdown (1–16), max reviews input, **Run full pipeline** button; live `st.progress` bar + `_on_progress` callback updates both progress bar and status badges; `st.rerun()` on success
3. **View report card** *(post-run only)* — "Load latest report" toggle button; shows pulse markdown in a code block when expanded
4. **Download report card** *(post-run only)* — Download `.md` button
5. **Send email card** *(post-run only)* — recipient email + optional name fields, Send button; sends via `phase4.sender`
6. **Subscribe card** *(always visible)* — email + optional name form; Subscribe button adds to `subscribers` table in `reviews.db`; shows current subscriber list with per-row Remove buttons; `st.rerun()` on add/remove

### Reviews Page (`phase5/pages/1_Reviews.py`)
- All filters inline (no sidebar): date window, rating multiselect, theme, keyword search — 4-column row
- Filterable dataframe of PII-scrubbed reviews

### Themes Page (`phase5/pages/2_Themes.py`)
- Theme cards: label, description, green review-count badge, star rating (filled stars in `#2DB34A`)
- Expandable to show all reviews under that theme

### Unsubscribe Page (`phase5/pages/3_Unsubscribe.py`)
- URL: `/Unsubscribe?email=user@example.com`
- Reads `email` from query params, calls `remove_subscriber()`, shows confirmation
- Handles edge cases: missing param, already unsubscribed, DB errors
- Link to re-subscribe on main dashboard

### Bug fixes & resilience
- Fixed `'NoneType' object has no attribute 'parent'`: `pipeline_runner.py` was passing `db_path=None` to `get_connection()`, overriding its default
- Fixed Groq token limit (413): reduced `MAX_REVIEWS_FOR_DISCOVERY` 500→150, `REVIEW_TEXT_TRUNCATE` 200→150, `CLASSIFIER_BATCH_SIZE` 30→20
- Fixed unterminated-string JSON parse errors on Groq calls: enabled JSON mode via `response_format={"type":"json_object"}` in `groq_client.py`
- Fixed same unterminated-string error on Gemini calls (Phase 3): enabled JSON mode via `response_mime_type="application/json"` in `gemini_client.py` — root cause was verbatim user quotes in `representative_quote` field containing unescaped `"` characters
- Fixed widgets rendering outside card boundary: replaced HTML `<div>` wrapping with `st.container(border=True)` + CSS override on `stVerticalBlockBorderWrapper`

---

## Scheduler — GitHub Actions Weekly Trigger

**Goal:** Run the full pipeline automatically every Monday and send the pulse email directly to a fixed recipient — no human needed.

### Trigger
- **Automatic:** GitHub Actions cron `30 3 * * 1` (Monday 09:00 IST / 03:30 UTC)
- **Manual:** `workflow_dispatch` button in the GitHub Actions UI for ad-hoc runs

### Components

#### scheduler/config.py
| Variable | Default | Description |
|----------|---------|-------------|
| `SCHEDULER_WEEKS` | 3 | Lookback window — tight enough for weekly cadence |
| `SCHEDULER_MAX_REVIEWS` | 200 | Review cap — keeps LLM token costs low for unattended runs |
| `SCHEDULER_RECIPIENTS` | "" | Multi-recipient list — comma-separated `email` or `Name:email` entries (GitHub Actions) |
| `SCHEDULER_RECIPIENT_EMAIL` | "" | Legacy single-recipient fallback |
| `SCHEDULER_RECIPIENT_NAME` | "" | Display name for legacy single-recipient |

#### scheduler/run.py
1. Resolves recipients in priority order: DB subscribers → `SCHEDULER_RECIPIENTS` env var → legacy `SCHEDULER_RECIPIENT_EMAIL`
2. Exits with code 1 if no recipients found from any source
3. Calls `run_pipeline(weeks, max_reviews, on_progress)` — Phases 1–3
4. Calls `phase4.composer.compose()` + `phase4.sender.send_email()` for **each recipient** in a loop
5. Reports sent/failed counts; exits with code 1 only if all sends failed

#### .github/workflows/weekly_pulse.yml
- Checks out repo, installs `requirements.txt`, runs `python -m scheduler.run`
- All secrets injected from GitHub repo settings: `GROQ_API_KEY`, `GEMINI_API_KEY`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `SCHEDULER_RECIPIENTS`, `SCHEDULER_RECIPIENT_EMAIL`, `SCHEDULER_RECIPIENT_NAME`

### Key difference from the UI email
The Streamlit UI's "Send Email" card is a **one-off manual send** to whoever the user types in.
The scheduler is an **automated send** to all subscribers — runs entirely without human interaction.

**IN:** GitHub secrets (API keys, Gmail credentials, recipients)
**OUT:** Weekly pulse email delivered to every subscriber every Monday at 9 AM IST

---

## Phase 6 — React + FastAPI (Built Later)

**Goal:** Production-grade UI on top of the same pipeline core.

- FastAPI wraps `pipeline/` as REST endpoints
- React mirrors all Streamlit pages with richer UX
- Independently deployable via Docker
- Zero pipeline logic duplication — both UIs call the same engine

### API Endpoints
```
POST /api/run           — trigger full pipeline
GET  /api/reviews       — list reviews (filters, pagination)
GET  /api/themes        — list themes + review counts
GET  /api/pulse/latest  — fetch latest weekly note
POST /api/email/send    — trigger email draft send
GET  /api/runs          — run history
GET  /api/run/status    — live pipeline progress (SSE)
GET|PUT /api/settings   — read/write config
```

---

## LLM Call Summary

| # | Call | Provider | Input | Output |
|---|------|----------|-------|--------|
| 1 | Theme Discovery | Groq | All review texts | 3–5 theme labels + descriptions |
| 2 | Review Classifier | Groq | Each review + theme list (batched) | review_id → theme_id |
| 3 | Summariser + Quote Picker | Gemini | Reviews grouped by theme | summary + quote × 3 |
| 4 | Action Idea Generator + What's Working | Gemini | 3 theme summaries | 3 action recommendations + 3 positive highlights |

**Total API requests per run:** `3 + ceil(review_count / batch_size)`
Example: 200 reviews, batch_size=20 → 13 Groq API requests

---

## LLM Routing

```python
# llm_client/router.py
LLM_ROUTING = {
    "theme_discovery":            "groq",
    "classifier":                 "groq",
    "summariser":                 "gemini",
    "action_ideas_whats_working": "gemini",
}
```

Swapping any call to a different LLM = one-line config change.

---

## Full Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        CONFIGURATION                            │
│  date_window, groq_api_key, gemini_api_key, smtp_creds          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1 — INGESTION (No LLM)                                   │
│  Play Store Scraper → PII Scrubber → reviews.db                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2 — THEME GROUPING (Groq)                                │
│  Theme Discovery (LLM Call 1) → themes.json                     │
│  Review Classifier (LLM Call 2, batched) → reviews.db + theme_id│
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3 — NOTE GENERATION (Gemini)                             │
│  Summariser + Quote Picker (LLM Call 3)                         │
│  Action Idea Generator (LLM Call 4)                             │
│  Note Assembler (no LLM) → weekly_pulse.md                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 4 — EMAIL DRAFT                                          │
│  Composer → Gmail SMTP → Draft in Drafts folder                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 5 — STREAMLIT UI                                         │
│  Dashboard | Reviews | Themes                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

### Subscriber Store (`phase5/subscriber_store.py`)
- `subscribers` table in `data/reviews.db` (same DB as reviews) — columns: `email` (PK), `name`, `subscribed_at`
- `add_subscriber(conn, email, name)` — `INSERT OR IGNORE`, returns bool
- `list_subscribers(conn)` — returns `[Subscriber]` ordered by sign-up date
- `remove_subscriber(conn, email)` — returns bool
- Used by both the Streamlit UI (add/remove via browser) and `scheduler/run.py` (load for automated sends)
- Also used by the Unsubscribe page (`3_Unsubscribe.py`) to process one-click removal from email links

---

## File Structure

```
INDMoney-AppReview-Analyser/
├── phase1/                       # Data Ingestion (No LLM)
│   ├── scraper.py                # google-play-scraper
│   ├── pii_scrubber.py           # PII removal (hard gate before storage)
│   ├── review_store.py           # SQLite helpers
│   ├── config.py                 # defaults: app_id, weeks, max_reviews
│   ├── models.py                 # Review, FetchResult dataclasses
│   └── tests/
├── phase2/                       # Theme Grouping (Groq)
│   ├── theme_discovery.py        # Groq LLM Call 1
│   ├── classifier.py             # Groq LLM Call 2 (batched)
│   ├── validator.py              # merge themes with < 2 reviews
│   ├── config.py
│   ├── models.py                 # Theme, ThemeList dataclasses
│   └── tests/
├── phase3/                       # Note Generation (Gemini)
│   ├── note_generator.py         # Gemini LLM Calls 3 & 4
│   ├── assembler.py              # pure formatting, no LLM → weekly_pulse.md
│   ├── config.py
│   ├── models.py
│   └── tests/
├── phase4/                       # Email Draft
│   ├── composer.py               # HTML email builder
│   ├── sender.py                 # Gmail SMTP send
│   ├── config.py
│   └── tests/
├── phase5/                       # Streamlit UI
│   ├── app.py                    # Dashboard (main page)
│   ├── subscriber_store.py       # SQLite subscriber CRUD
│   └── pages/
│       ├── 1_Reviews.py
│       ├── 2_Themes.py
│       └── 3_Unsubscribe.py
├── phase6/                       # React + FastAPI (later)
│   ├── api/
│   │   └── main.py
│   └── frontend/
│       └── src/
├── llm_client/                   # Shared LLM wrapper
│   ├── groq_client.py            # Groq API wrapper (retries, rate limits)
│   ├── gemini_client.py          # Gemini API wrapper (retries, rate limits)
│   └── router.py                 # routes each call to correct LLM
├── data/
│   └── reviews.db                # gitignored
├── output/
│   └── weekly_pulse.md           # gitignored
├── .env.example
├── requirements.txt
├── main.py                       # headless CLI runner (orchestrates all phases)
├── architecture.md               # this file
└── status.md                     # decision log and build status
```

---

## Environment Variables

```
GROQ_API_KEY=
GEMINI_API_KEY=
PLAY_STORE_PACKAGE=in.indwealth
GMAIL_SENDER=your@gmail.com
GMAIL_APP_PASSWORD=              # 16-char Google App Password
DATE_WINDOW_WEEKS=8
MAX_REVIEWS=1000
MAX_THEMES=4
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| PII scrubbing at ingestion boundary | No personal data ever reaches LLM or storage |
| LLM generates themes first, then classifies | Avoids hardcoded categories; themes emerge from data |
| Groq for analytical calls (1 & 2) | Speed + cost for bulk classification |
| Gemini for writing calls (3 & 4) | Quality and nuance for summaries and recommendations |
| 4 focused LLM calls, not one mega-prompt | Easier to debug, retry, and iterate each step |
| Email created as Draft, not auto-sent | Human review before delivery |
| Credentials only in `.env` | No secrets in source; safe to open-source |
| SQLite for local storage | Zero infrastructure, sufficient for weekly batch |
| 12-week retention policy | DB stays bounded; anything older than the analysis window has no value |
| Streamlit first, React+FastAPI later | Ship fast, upgrade UI when core is proven |

---

## Build Order

1. Phase 1 — `pipeline/ingestion/` + `pipeline/storage/` (no LLM)
2. Phase 2 — `pipeline/analysis/` (Groq)
3. Phase 3 — `pipeline/generation/` (Gemini)
4. Phase 4 — `pipeline/email/`
5. Phase 5 — Streamlit UI
6. Scheduler — `scheduler/` + `.github/workflows/weekly_pulse.yml` ✅
7. Phase 6 — React + FastAPI
