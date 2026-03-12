# Project Status & Decision Log

## Project: INDMoney App Review Weekly Pulse

---

## Confirmed Architecture (All Decisions Locked)

### Data Source
- **Google Play Store only** — public scraping via `google-play-scraper`, no credentials needed
- **App package:** `in.indwealth`

### LLM Split
| LLM Call | Phase | Provider | Purpose |
|----------|-------|----------|---------|
| Call 1 — Theme Discovery | Phase 2 | **Groq** | Analytical — find patterns across raw review data |
| Call 2 — Review Classifier | Phase 2 | **Groq** | Analytical + bulk batching, needs speed |
| Call 3 — Summariser + Quote Picker | Phase 3 | **Gemini** | Writing — nuance and quality output |
| Call 4 — Action Idea Generator | Phase 3 | **Gemini** | Writing — reasoning and creative recommendations |

### Storage
- **SQLite** (`data/reviews.db`) — zero infrastructure, sufficient for weekly batch
- Schema: `reviews (id, platform, rating, title, clean_text, date, week_label)`, `themes`, `runs`, `pulse_notes`, `settings`

### PII
- Stripped at ingestion, **before** any storage or LLM call
- Method: regex + spaCy NER
- Hard gate — no review passes through without scrubbing

### Email
- Gmail SMTP via App Password (stored in `.env` / Streamlit secrets)
- Recipient name + email entered inline in UI at send time
- Created as **draft**, not auto-sent
- Subject: `INDMoney App Review Pulse — Week of [DATE]`

### Defaults
- **Max reviews:** 1000 (if user leaves blank)
- **Date window:** 8 weeks (if user leaves blank)
- Boundary is date window first, count cap second

### Trigger
- Manual "Run Now" button (Streamlit)
- Weekly scheduler added at the end

### UI
- **Phase 5:** Streamlit (Python, free Streamlit Cloud deploy)
- **Phase 6 (later):** React + FastAPI — built after everything works, shares same pipeline core

---

## Confirmed Phase Breakdown

### Phase 1 — Data Ingestion (NO LLM)
- `pipeline/ingestion/scraper.py` — google-play-scraper calls
- `pipeline/ingestion/pii_scrubber.py` — PII removal before storage
- `pipeline/storage/review_store.py` — SQLite read/write

### Phase 2 — Theme Grouping (Groq)
- `pipeline/analysis/theme_discovery.py` — Groq LLM Call 1: generate 3–5 theme labels
- `pipeline/analysis/classifier.py` — Groq LLM Call 2 (batched): assign each review to a theme
- Validate: merge themes with < 2 reviews into closest theme

### Phase 3 — Weekly Pulse Generation (Gemini)
- `pipeline/generation/note_generator.py` — Gemini LLM Calls 3 & 4: summaries + action ideas
- `pipeline/generation/assembler.py` — pure formatting, no LLM → `weekly_pulse.md`

### Phase 4 — Email
- `pipeline/email/composer.py` — build HTML email
- `pipeline/email/sender.py` — Gmail SMTP send

### Phase 5 — Streamlit UI
- `streamlit_app/app.py` — Dashboard (main page)
- `streamlit_app/pages/1_Reviews.py` — filterable reviews table
- `streamlit_app/pages/2_Themes.py` — theme cards + drill-down

### Phase 6 — React + FastAPI (later)
- `api/` — FastAPI wrapping same pipeline
- `frontend/` — React UI

---

## Confirmed File Structure

```
INDMoney-AppReview-Analyser/
├── pipeline/
│   ├── ingestion/
│   │   ├── scraper.py
│   │   └── pii_scrubber.py
│   ├── storage/
│   │   └── review_store.py
│   ├── analysis/
│   │   ├── theme_discovery.py    # Groq LLM Call 1
│   │   └── classifier.py         # Groq LLM Call 2
│   ├── generation/
│   │   ├── note_generator.py     # Gemini LLM Calls 3 & 4
│   │   └── assembler.py
│   └── email/
│       ├── composer.py
│       └── sender.py
├── llm_client/
│   ├── groq_client.py
│   ├── gemini_client.py
│   └── router.py                 # routes each call to correct LLM
├── streamlit_app/
│   ├── app.py
│   └── pages/
│       ├── 1_Reviews.py
│       └── 2_Themes.py
├── api/                          # Phase 6 (later)
├── frontend/                     # Phase 6 (later)
├── data/
│   └── reviews.db                # gitignored
├── output/
│   └── weekly_pulse.md           # gitignored
├── .env.example
├── requirements.txt
└── main.py                       # headless CLI runner
```

---

## LLM Routing Config
```python
LLM_ROUTING = {
    "theme_discovery": "groq",
    "classifier":      "groq",
    "summariser":      "gemini",
    "action_ideas":    "gemini",
}
```

---

## Environment Variables Required
```
GROQ_API_KEY=
GEMINI_API_KEY=
PLAY_STORE_PACKAGE=in.indwealth
GMAIL_SENDER=your@gmail.com
GMAIL_APP_PASSWORD=
EMAIL_RECIPIENT=your@gmail.com
DATE_WINDOW_WEEKS=8
MAX_REVIEWS=1000
MAX_THEMES=4
```

---

## Current Code State vs Architecture

| What exists | What architecture requires |
|-------------|---------------------------|
| `phase1/` (scraper, models, config) | `pipeline/ingestion/` (scraper + PII scrubber) |
| `phase2/` (analyzer using **Anthropic**) | `pipeline/analysis/` using **Groq** |
| No SQLite | SQLite `reviews.db` required |
| No PII scrubber | Hard gate PII scrubber required |
| No llm_client/ | `llm_client/` with groq + gemini + router |

**⚠️ Current code does NOT match architecture. Needs to be rebuilt.**

---

## Build Order
1. Phase 1 — pipeline/ingestion/ + pipeline/storage/ (no LLM)
2. Phase 2 — pipeline/analysis/ (Groq)
3. Phase 3 — pipeline/generation/ (Gemini)
4. Phase 4 — pipeline/email/
5. Phase 5 — Streamlit UI
6. Scheduler
7. Phase 6 — React + FastAPI

---

## Status

- [x] Architecture confirmed and locked
- [x] All decisions recorded in status.md
- [ ] Phase 1 implementation
- [ ] Phase 2 implementation
- [ ] Phase 3 implementation
- [ ] Phase 4 implementation
- [ ] Phase 5 Streamlit UI
- [ ] Scheduler
- [ ] Phase 6 React + FastAPI
