# INDMoney App Review Pulse — Project Overview

> A quick-reference guide for understanding the project at a glance.
> Useful for interviews, onboarding, and demos.

---

## What Is This Project?

**INDMoney App Review Pulse** is an automated AI pipeline that:
1. Scrapes user reviews from the Google Play Store for the INDMoney fintech app
2. Uses AI to discover themes, classify reviews, and generate a weekly digest
3. Emails a one-page pulse report to subscribers every Monday — automatically

**The core problem it solves:** Product and growth teams waste hours manually reading hundreds of app reviews to figure out what users love or hate. This system does it in minutes, every week, without manual effort.

---

## Tech Stack — At a Glance

| Layer | Tool / Tech | Why |
|---|---|---|
| **Data Source** | Google Play Scraper | Fetch up to 1,000 reviews per run |
| **AI — Analysis** | Groq (llama-3.3-70b) | Fast, cheap bulk theme discovery & classification |
| **AI — Writing** | Gemini 1.5 Flash | Higher quality summaries, quotes, recommendations |
| **Database** | SQLite | Zero-infra local storage; sufficient for weekly batch |
| **UI** | Streamlit | Rapid dashboard — run pipeline, view report, manage subscribers |
| **Email** | Gmail SMTP (TLS) | Deliver HTML pulse emails; drafts created for human review |
| **Automation** | GitHub Actions | Cron job every Monday 9 AM IST — fully hands-free |
| **Language** | Python 3.11+ | Core implementation across all phases |

---

## How It Works — 5-Phase Pipeline

```
Google Play Store
      ↓
  Phase 1 — Scrape & Scrub
      Fetch reviews → Remove PII → Store in SQLite
      ↓
  Phase 2 — Theme Discovery (Groq AI)
      Sample reviews → Discover 3–5 themes → Classify every review
      ↓
  Phase 3 — Report Generation (Gemini AI)
      Summarize top themes → Pick user quotes → Generate action ideas
      ↓
  Phase 4 — Email Draft
      Format as HTML email → Create Gmail Draft → Ready for review
      ↓
  Phase 5 — Dashboard + Scheduler
      Streamlit UI (manual) or GitHub Actions (automated weekly)
```

---

## The Weekly Output — What Gets Delivered

A one-page Markdown/HTML report containing:

- **Top 3 Themes** — What users are actually talking about (AI-discovered, not hardcoded)
- **User Voices** — Verbatim quotes from real reviews, one per theme
- **What's Working** — 3 things users appreciate about the app
- **Action Ideas** — 3 specific, AI-generated product recommendations

**Delivery:** Every Monday at 9 AM IST via email to all subscribers.

---

## Key Product & Design Decisions

### 1. AI discovers themes — not humans
Themes are not predefined categories. The LLM reads real reviews and emerges themes from the data. This means the report reflects what users *actually* care about, not what the team assumes they care about.

### 2. Two different AI models for two different jobs
- **Groq** handles bulk classification (fast + cost-efficient for repetitive tasks)
- **Gemini** handles report writing (higher quality for nuanced language)

This split reduces cost while maintaining output quality.

### 3. PII scrubbing is a hard gate — not optional
Every review is sanitized (emails, phones, UPI IDs, URLs removed) *before* being stored or sent to any AI model. No personal user data ever reaches the LLM. This is a non-negotiable privacy boundary.

### 4. Email is created as a Draft — not auto-sent
Phase 4 puts the email in Gmail Drafts for human review before delivery. This is intentional — it prevents incorrect reports from going out without oversight.

### 5. Proportional sampling for fair theme discovery
Instead of randomly sampling 150 reviews, the system samples proportionally across 1–5 star ratings. This prevents the theme engine from being dominated by one sentiment (e.g., only 1-star complaints or only 5-star praise).

### 6. 4 focused LLM calls — not one mega-prompt
Breaking the analysis into 4 targeted calls (discover themes → classify → summarize → recommend) makes each step debuggable, retryable, and independently testable.

---

## Why This Matters — PM Interview Framing

### Problem Statement
App review analysis is a critical but time-consuming task for product teams. Reading hundreds of reviews weekly to spot trends, user pain points, and feature gaps is manual, inconsistent, and often skipped under deadline pressure.

### Solution
An automated AI pipeline that converts raw reviews into structured, actionable weekly insights — delivered to inboxes without any manual effort.

### Impact / Value Delivered
- **Time saved:** Hours of manual review reading reduced to ~5 minutes of pipeline runtime
- **Consistency:** Same analysis framework applied every week, no human bias or fatigue
- **Actionability:** Not just "what users say" but "what to do about it" (action ideas)
- **Scalability:** Can be pointed at any Play Store app by changing one config variable

### Trade-offs Made
| Trade-off | Decision | Reason |
|---|---|---|
| SQLite vs. cloud DB | SQLite | Zero infra cost; weekly batch doesn't need real-time scale |
| Streamlit vs. React | Streamlit | Ship fast, validate use case before investing in full frontend |
| Draft vs. auto-send | Draft | Safety — human review before delivery in production |
| 150 review sample vs. all | Sample | Cost control; LLM token limits; proportional sampling keeps fairness |

### Metrics to Track (if this were a real product)
- Open rate and click-through of weekly pulse emails
- Subscriber growth over time
- Time from report delivery to PM action taken
- Accuracy of AI-discovered themes (user validation surveys)
- Cost per report (LLM API spend per run)

---

## Architecture — Folder Map

```
INDMoney-AppReview-Analyser/
├── phase1/           # Data ingestion: scrape, scrub PII, store
├── phase2/           # Theme discovery & review classification (Groq)
├── phase3/           # Report generation: summaries, quotes, recommendations (Gemini)
├── phase4/           # Email composition & Gmail Draft creation
├── phase5/           # Streamlit dashboard + pipeline orchestration
│   └── pages/        # Reviews, Themes, Unsubscribe pages
├── llm_client/       # Shared Groq & Gemini API wrappers
├── scheduler/        # GitHub Actions entry point (headless runner)
├── .github/
│   └── workflows/    # weekly_pulse.yml — cron: every Monday 9 AM IST
├── resources/        # Sample output: weekly note, email draft, reviews CSV
├── data/             # SQLite DB (gitignored)
├── output/           # Generated report .md file (gitignored)
├── README.md         # Setup & usage guide
├── architecture.md   # Detailed architecture deep-dive
└── OVERVIEW.md       # This file
```

---

## LLM Calls — Summary Table

| Call | Phase | Model | Input | Output |
|---|---|---|---|---|
| 1 — Theme Discovery | 2 | Groq | 150 sampled reviews | 3–5 themes with labels & descriptions |
| 2 — Review Classifier | 2 | Groq | All reviews + themes (batched 20/call) | Each review → assigned theme |
| 3 — Summarizer + Quote Picker | 3 | Gemini | Top-3 themes + their reviews | 2–3 sentence summary + 1 verbatim quote per theme |
| 4 — Action Ideas + What's Working | 3 | Gemini | 3 summaries | 3 action recommendations + 3 positive highlights |

**Total API calls per run:** ~13 for 200 reviews (3 Groq single-calls + 10 Groq batch-calls + 2 Gemini calls)

---

## Security & Privacy Highlights

| Concern | How It's Handled |
|---|---|
| User PII in reviews | Regex scrubber removes emails, phones, UPI IDs, URLs before any storage or LLM use |
| API keys & credentials | `.env` file only — never committed to source code |
| Email safety | Draft-only send; humans review before delivery |
| Unsubscribe | One-click link per email; instant removal from subscriber list |
| Data retention | Reviews auto-purged after 12 weeks; DB stays bounded |

---

## Running the Project

```bash
# 1. Clone & install
pip install -r requirements.txt

# 2. Set up credentials
cp .env.example .env
# Fill in: GROQ_API_KEY, GEMINI_API_KEY, GMAIL_ADDRESS, GMAIL_APP_PASSWORD

# 3. Launch dashboard
streamlit run phase5/app.py

# 4. Or run headless (for automation / testing)
python -m scheduler.run
```

**Tests (365+ total):**
```bash
pytest                  # Run all tests
pytest phase1/tests/    # Phase-specific
```

---

## One-Line Summary (for elevator pitch)

> "INDMoney App Review Pulse is an end-to-end AI pipeline that turns raw Google Play reviews into a structured weekly product insights report — automatically discovering themes, surfacing user quotes, and recommending actions — delivered to PMs every Monday morning."
