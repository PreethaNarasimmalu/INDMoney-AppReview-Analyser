# Project Status

## Build Progress

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Data Ingestion (scraper + PII scrubber + SQLite) | ✅ Complete |
| Phase 2 | Theme Grouping (Groq) | ✅ Complete |
| Phase 3 | Note Generation (Gemini) | ✅ Complete |
| Phase 4 | Email Draft (Gmail IMAP) | ✅ Complete |
| Phase 5 | Streamlit UI | ✅ Complete |
| Scheduler | Weekly cron trigger | ⏳ Pending |
| Phase 6 | React + FastAPI | ⏳ Pending |

---

## Decision Log

### 2026-03-12
- Confirmed data source: Google Play Store only (`in.indwealth`), no credentials needed
- Confirmed LLM split: Groq for Phase 2 (calls 1 & 2), Gemini for Phase 3 (calls 3 & 4)
- Confirmed storage: SQLite (`data/reviews.db`), no external DB
- Confirmed PII scrubbing is a hard gate at ingestion — before storage and before any LLM call
- Confirmed email: Gmail SMTP via App Password, creates Draft (not auto-send), recipient entered in UI
- Confirmed defaults: 8 weeks date window, 1000 max reviews
- Confirmed UI: Streamlit first (Phase 5), React + FastAPI later (Phase 6)
- Confirmed trigger: Manual "Run Now" button now, weekly scheduler added at the end
- Confirmed Phase 1 has NO LLM — pure scraping + PII scrub + storage
- Architecture documented in `architecture.md`
- Existing `phase1/` and `phase2/` code does NOT match architecture — needs to be rebuilt from scratch

### 2026-03-12 (Phase 5 complete)
- Created `phase5/pipeline_runner.py`: orchestrates all 4 phases; accepts `on_progress` callback for live UI updates; returns `PipelineResult` dataclass
- Created `phase5/app.py`: Streamlit dashboard — Run Now button, live progress bar, metrics (reviews, new, themes, purged), pulse note display, download .md, Send Email form
- Created `phase5/pages/1_Reviews.py`: filterable reviews table (date window, rating, theme, keyword search)
- Created `phase5/pages/2_Themes.py`: theme cards with review count, avg rating, expandable review lists
- Added `phase5/tests` to `pytest.ini` testpaths
- Added 31 tests in `test_pipeline_runner.py` — all pass (Phase 1–3 calls, result fields, error cases, progress callback)
- All 341 tests pass (phase1 + phase2 + phase3 + phase4 + phase5)

### 2026-03-12 (DB retention policy added)
- Added `purge_old_reviews(conn, retention_weeks)` to `phase1/review_store.py`
- Deletes reviews older than 12 weeks on every run — DB stays bounded
- `RETENTION_WEEKS = 12` added to `phase1/config.py` (configurable)
- Called once per run after upsert, before analysis
- Added 6 tests in `TestPurgeOldReviews` — all pass
- Updated `architecture.md` with retention policy docs and design decision

### 2026-03-12 (Phase 4 complete)
- Created `phase4/config.py`: IMAP host/port, Drafts folder, email subject prefix
- Created `phase4/composer.py`: `compose()` builds `EmailMessage` with plain-text + HTML parts; `_escape_html()` XSS-safe HTML wrapper using `<pre>` tag
- Created `phase4/sender.py`: `create_draft()` uploads draft via IMAP APPEND to `[Gmail]/Drafts`; `_get_credentials()` loads `GMAIL_ADDRESS` + `GMAIL_APP_PASSWORD` from env
- No SMTP send — creates a Gmail Draft only (safe, reviewable before sending)
- Added `phase4/tests` to `pytest.ini` testpaths
- Added 41 tests across `test_composer.py` and `test_sender.py` — all mocked, no real IMAP calls
- All 304 tests pass (phase1 + phase2 + phase3 + phase4)

### 2026-03-12 (Phase 2 filter added)
- Created `phase2/review_filter.py`: filters low-signal reviews before any LLM call
  - Too short (< 5 words)
  - Low signal (< 40% alphabetic chars — catches emoji-only, number spam)
  - All-caps spam (> 80% uppercase letters)
  - Exact duplicates (case-insensitive, whitespace-normalised)
- Returns `(kept_reviews, stats)` with per-filter removal counts
- Updated `phase2/config.py` with `MIN_WORD_COUNT`, `MIN_ALPHA_RATIO`, `MAX_UPPERCASE_RATIO`
- Added 40 new tests in `test_review_filter.py`
- All 263 tests pass

### 2026-03-12 (Phase 3 complete)
- Implemented `llm_client/gemini_client.py`: full Gemini wrapper (chat + retry with exponential backoff + JSON parse), replacing placeholder
- Created `phase3/models.py`: `ThemeSummary` (theme_id, label, summary, representative_quote, quote_rating, quote_platform), `PulseNote` (week_label, theme_summaries, action_ideas)
- Created `phase3/config.py`: `GEMINI_MODEL = "gemini-1.5-flash"`, `TOP_N_THEMES = 3`
- Created `phase3/note_generator.py`: LLM Call 3 (`generate_summaries`) — single Gemini call for top-3 themes, returns summary + verbatim quote each; LLM Call 4 (`generate_action_ideas`) — 3 concrete recommendations; `generate_pulse` orchestrator loads from DB and returns a full `PulseNote`
- Created `phase3/assembler.py`: pure formatting (no LLM) — renders `PulseNote` to fixed Markdown template and writes `output/weekly_pulse.md`
- Added `google-generativeai>=0.7.0` to `requirements.txt`
- Added `phase3/tests` to `pytest.ini` testpaths
- Added 60 new tests across `test_models`, `test_note_generator`, `test_assembler`
- All 223 tests pass (phase1 + phase2 + phase3)

### 2026-03-12 (Phase 2 complete)
- Created `llm_client/`: `groq_client.py` (chat + retry + JSON parse), `gemini_client.py` (placeholder), `router.py`
- Created `phase2/theme_discovery.py`: Groq LLM Call 1 — discovers 3–5 themes from review texts
- Created `phase2/classifier.py`: Groq LLM Call 2 — classifies every review into a theme, batched in groups of 30
- Created `phase2/validator.py`: merges themes with < 2 reviews into largest theme; keeps 3–5 themes; sorts by count
- Created `phase2/store.py`: `themes` table, `theme_id` column write-back to reviews, `themes.json` output
- Rewrote `phase2/models.py`: new `Theme(theme_id, label, description, review_count)`, `ThemeList`, `ClassifiedReview`
- Rewrote `phase2/config.py`: switched from Claude to Groq (`llama3-70b-8192`)
- Removed old `phase2/analyzer.py` (replaced by three focused components above)
- Added `groq>=0.9.0` to `requirements.txt`
- Added 75 new tests across `test_models`, `test_theme_discovery`, `test_classifier`, `test_validator`, `test_store`
- All 163 tests pass (phase1 + phase2)

### 2026-03-12 (Phase 1 complete)
- Implemented `phase1/pii_scrubber.py`: regex hard gate for emails, Indian/intl phones, URLs, UPI IDs, hex tokens; replaces all with `[REDACTED]`
- Implemented `phase1/review_store.py`: SQLite helpers — `create_table`, `upsert_reviews` (INSERT OR IGNORE dedup by SHA-256 hash), `load_reviews` (date-window filter), `count_reviews`
- Updated `phase1/models.py`: added `title` field and `review_hash` property (SHA-256 of date+rating+text) to `Review`
- Added 76 new tests across `test_pii_scrubber.py` and `test_review_store.py`
- All 88 phase1 tests pass (0 failures)
- Note: PII scrubbing is regex-only; spaCy NER not added (not in requirements.txt)

---

## Notes
- Full architecture details in `architecture.md`
- `data/reviews.db` and `output/weekly_pulse.md` are gitignored
