# Project Status

## Build Progress

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Data Ingestion (scraper + PII scrubber + SQLite) | ✅ Complete |
| Phase 2 | Theme Grouping (Groq) | ✅ Complete |
| Phase 3 | Note Generation (Gemini) | ⏳ Pending |
| Phase 4 | Email Draft (Gmail SMTP) | ⏳ Pending |
| Phase 5 | Streamlit UI | ⏳ Pending |
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
