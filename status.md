# Project Status & Decision Log

## Project: INDMoney App Review Analyser

---

## Architecture

| Phase | Responsibility | Status |
|-------|---------------|--------|
| Phase 1 | Data Ingestion — scrape Google Play reviews | Done |
| Phase 2 | AI Analysis — sentiment, themes, insights | Done (needs LLM swap) |

---

## Decisions

### [2026-03-12] App ID
- **Decision:** Use `in.indwealth` as the default app ID (not `com.indmoney`)
- **Reason:** Correct Google Play ID for INDMoney app

### [2026-03-12] Phase 1 — Data Ingestion Config
- **App ID:** `in.indwealth`
- **Max reviews:** 1000
- **Date window:** 8 weeks
- **Language:** `en`, Country: `in`
- **Batch size:** 200 (Google Play scraper max per request)
- **Review text truncate:** 300 chars

### [2026-03-12] Phase 2 — AI Analysis Config
- **Max reviews in prompt:** 500
- **Review text truncate:** 300 chars
- **Top themes:** 5
- **LLM provider:** ⚠️ Currently Anthropic (Claude) — **PENDING DECISION: switch to Groq or Gemini**

---

## Pending Decisions

- [ ] **Phase 2 LLM provider** — confirm Groq or Gemini for Phase 2 analysis
- [ ] If there is a Phase 3, confirm its LLM provider

---

## Notes

- All tests mocked — no real API calls in test suite
- 81 tests passing as of last commit
