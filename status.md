# Project Status

## Build Progress

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Data Ingestion (scraper + PII scrubber + SQLite) | ✅ Complete |
| Phase 2 | Theme Grouping (Groq) | ✅ Complete |
| Phase 3 | Note Generation (Gemini) | ✅ Complete |
| Phase 4 | Email Draft (Gmail IMAP) | ✅ Complete |
| Phase 5 | Streamlit UI | ✅ Complete |
| Scheduler | Weekly cron trigger (GitHub Actions) | ✅ Complete |
| Subscribers | Email subscription UI + multi-recipient scheduler | ✅ Complete |
| Unsubscribe | One-click unsubscribe link in email footer | ✅ Complete |
| Phase 6 | React + FastAPI | ⏳ Pending |

---

## Decision Log

### 2026-03-13 (Fix unsubscribe link hidden by Gmail trimming)
- Moved unsubscribe link from `<div class="footer">` into `<div class="body">` — Gmail trims footer-like content into "..." dots
- Removed `---` from plain text unsubscribe line — dashes trigger Gmail's "show quoted text" collapse
- Unsubscribe now always visible without any click to expand

### 2026-03-13 (Unsubscribe link visibility fix)
- Added unsubscribe URL to plain text email body — previously only in HTML, so clients rendering plain text had no unsubscribe option
- Made HTML unsubscribe link colour `#666` (was `#aaa`) so it's visible against the `#f8f9fa` footer background

### 2026-03-13 (Subscribe feedback UX fixes)
- **Success message was invisible**: `st.rerun()` was firing immediately after `st.success()`, wiping the message before the user could read it — fixed by storing message + timestamp in `st.session_state["sub_msg"]` and displaying it outside the form
- **"Already subscribed" warning never dismissed**: warning had no auto-dismiss — fixed with same session state pattern
- Both messages (success + already-subscribed warning + errors) now auto-dismiss after 4 seconds via a 0.5s poll-rerun loop; once expired, `sub_msg` is deleted from session state

### 2026-03-12 (Streamlit Cloud → GitHub subscriber sync)
- Added `_push_to_github()` to `phase5/subscriber_store.py`: after every `_sync_json()`, pushes `subscribers.json` to GitHub via the Contents API if `GITHUB_TOKEN` + `GITHUB_REPO` env vars are set
- Subscribers added/removed on the deployed Streamlit Cloud app now automatically commit `subscribers.json` to the repo — GitHub Actions scheduler reads the latest list without any manual steps
- Requires `GITHUB_TOKEN` (PAT with `contents:write`) and `GITHUB_REPO` secrets added to Streamlit Cloud app settings
- Push failure is silent — subscribe/unsubscribe always succeeds locally

### 2026-03-12 (Unsubscribe link)
- Added `phase5/pages/3_Unsubscribe.py`: handles `/Unsubscribe?email=...` — reads query param, calls `remove_subscriber()`, shows confirmation; handles missing param, already-unsubscribed, DB errors
- Updated `phase4/composer.py`: HTML email footer now includes a per-recipient unsubscribe link pointing to `https://indmoney-appreview-analyser.streamlit.app/Unsubscribe?email={recipient_email}`
- Updated `architecture.md` and `status.md`

### 2026-03-12 (Subscribers + multi-recipient scheduler)
- Added `phase5/subscriber_store.py`: `subscribers` table in `reviews.db`; `add_subscriber`, `list_subscribers`, `remove_subscriber` helpers
- Added **Subscribe card** to `phase5/app.py` (card 6, always visible): email + name form, subscriber list with per-row Remove buttons
- Updated `scheduler/run.py`: resolves recipients — DB subscribers → `SCHEDULER_RECIPIENTS` env var → legacy `SCHEDULER_RECIPIENT_EMAIL`; sends to each in a loop
- Updated `scheduler/config.py`: added `SCHEDULER_RECIPIENTS` env var
- Fixed GitHub Actions cron: `0 9 * * 1` (09:00 UTC) → `30 3 * * 1` (03:30 UTC = 09:00 IST)
- Updated `.github/workflows/weekly_pulse.yml`: new cron + `SCHEDULER_RECIPIENTS` secret
- Updated `architecture.md`: scheduler section, subscriber store docs, file structure

### 2026-03-12 (Scheduler — GitHub Actions weekly trigger)
- Created `scheduler/` folder as a standalone module (not Phase 6, which is reserved for React+FastAPI)
- `scheduler/config.py`: reads `SCHEDULER_WEEKS` (default 3), `SCHEDULER_MAX_REVIEWS` (default 200), `SCHEDULER_RECIPIENT_EMAIL`, `SCHEDULER_RECIPIENT_NAME` from env
- `scheduler/run.py`: entry point — calls `run_pipeline()`, composes email via `phase4.composer`, sends directly via `phase4.sender.send_email()` (SMTP, not draft); exits with code 1 if `SCHEDULER_RECIPIENT_EMAIL` is not set
- `.github/workflows/weekly_pulse.yml`: cron `0 9 * * 1` (Monday 09:00 UTC) + `workflow_dispatch` for manual runs; all secrets injected from GitHub repo secrets
- `.env.example`: added `SCHEDULER_*` vars documentation
- `pytest.ini`: added `scheduler/tests` to testpaths
- 18 new tests in `scheduler/tests/test_run.py` — all pass
- All 365 tests pass

### 2026-03-12 (Phase 3 — "What's Working" section added)
- Extended LLM Call 4 prompt to return both `action_ideas` and `whats_working` in a single Gemini call — no extra API request
- `generate_action_ideas()` now returns `tuple[list[str], list[str]]`; `generate_pulse()` unpacks and passes `whats_working` to `PulseNote`
- Added `whats_working: list[str]` field to `PulseNote` (default empty list for backwards compatibility)
- Assembler template gains `WHAT'S WORKING` section between `USER VOICES` and `ACTION IDEAS`
- Updated `architecture.md`: Phase 3 template diagram and LLM call table reflect new section
- All 347 tests pass (7 new tests added across test_models, test_note_generator, test_assembler)

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

### 2026-03-12 (Fix Gemini unterminated-string JSON error)
- Enabled JSON mode on Gemini calls (`response_mime_type="application/json"` in `gemini_client.py`) — same root cause as the earlier Groq fix; verbatim user quotes in `representative_quote` contained unescaped `"` characters breaking `json.loads()`
- Phase 3 (Report) was failing after Groq Phase 2 completed successfully

### 2026-03-12 (Phase 5 — live status badges + proportional sampling)
- Status card now uses `st.empty()` placeholder; `_on_progress` callback updates it live — badges turn green one-by-one as each stage completes (Reviews@20%, Themes@50%, Grouped@60%, Report@90%, Draft email@100%)
- Added `_sample_by_rating()` in `phase2/theme_discovery.py`: distributes the 150-review cap proportionally across star-rating buckets (1★–5★) so theme discovery sees balanced signal; prevents all reviews being 1-star complaints
- Enabled Groq JSON mode (`response_format={"type":"json_object"}`) by default in `llm_client/groq_client.py` — forces valid JSON output, eliminates unterminated-string parse errors
- Reduced Groq token usage: `MAX_REVIEWS_FOR_DISCOVERY` 500→150, `REVIEW_TEXT_TRUNCATE` 200→150, `CLASSIFIER_BATCH_SIZE` 30→20 (stays under 12k TPM free-tier limit)
- Fixed widgets rendering outside card boundary: replaced HTML `<div>` wrapping with `st.container(border=True)` + CSS override

### 2026-03-12 (Phase 5 UI redesign + bug fixes)
- Fixed `'NoneType' object has no attribute 'parent'` crash on Run Now: `pipeline_runner.py` was passing `db_path=None` explicitly to `get_connection()`, overriding its default; guarded with `if db_path is not None`
- Redesigned `phase5/app.py` with INDMoney brand colors (`#2DB34A`, `#1A1A1A`, `#F7F8FA`) and vertical section-card layout matching reference UI structure:
  - **Status card** — pipeline stage badges (greyed → green after run, with report date)
  - **Run pipeline card** — description, weeks dropdown, max reviews input, "Run full pipeline" button; `st.rerun()` on success
  - **View report card** — "Load latest report" toggle; post-run only
  - **Download report card** — Download `.md`; post-run only
  - **Send email card** — recipient email + name fields; post-run only
- Removed sidebar entirely from all three pages (CSS `display: none` + `initial_sidebar_state="collapsed"`)
- Added `sys.path` fix at top of `app.py`, `1_Reviews.py`, `2_Themes.py` so all phase imports resolve correctly when Streamlit runs from a subdirectory
- Redesigned `phase5/pages/1_Reviews.py`: filters moved inline as 4-column row (no sidebar)
- Redesigned `phase5/pages/2_Themes.py`: theme cards with green review-count badges and coloured star ratings

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
