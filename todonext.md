# StackScreener — Next Up
> Last updated: 2026-04-24 (milestone 9)

This document is the detailed task layer below `ROADMAP.md`. Where ROADMAP tracks project-level
status and backlogs, this file tracks the specific items we are actively thinking about,
diagnosing, or queued to build next. Update the date at the top whenever this file changes.

---

## What Was Completed This Milestone (2026-04-24)

| Item | Files Changed | Notes |
|---|---|---|
| **Memory & efficiency fixes** | scraper_app.py, app.py, db_app.py, news.py | Orphaned Collapsible cleanup, N+1 batch query, 2000-row load cap, 15s poll interval, TTL-cached ticker frozenset, column-width 100-row cap |
| **Tier 1 refactoring — all 6 tasks** | screener_config.py, app.py, news.py, screener_run.py, edgar.py, inst_flow.py, commodities.py, logistics.py, db.py | User-Agent centralization; SC_CONFIDENCE_MULT to config; legacy podcast constants removed; 6 UI config dicts moved to screener_config; sys.path hacks removed; HomePanel raw SQL → db helpers |
| **`scraper_app.py` — Schedule tab** | scraper_app.py, db.py | New `scheduled_jobs` table (20th); ScheduleModal; 60s background check fires due jobs; Add/Toggle/Delete controls |
| **`scraper_app.py` — WSJ Newspaper button** | scraper_app.py | 21st pipeline button — runs wsj_fetcher.py from the TUI |
| **`refactor.md`** | refactor.md | Full 4-tier refactoring roadmap (Tier 2-4 still pending) |
| `scraper_app.py` — full scheduler, 21 pipeline buttons | scraper_app.py | Was [PLANNED]; now ✅ Live. Seed Stock Universe, Force Re-enrich All, Fetch Price History, all 21 P1 pipeline buttons |
| `scraper_app.py` — Queue tab with Pause/Resume/Cancel/Priority | scraper_app.py, db.py | Job controls: pause_llm_jobs, resume_llm_jobs, cancel_llm_jobs, set_job_priority, get_distinct_job_types |
| `scraper_app.py` — Sources tab with unified EndpointModal | scraper_app.py | Single modal for add/edit; api_keys.display_name, url, connector_config, role columns |
| `db_app.py` — table browser, SQL shell, DB stats | db_app.py | Was [PLANNED]; now ✅ Live |
| `wsj_fetcher.py` — NEW file | wsj_fetcher.py, news.py | Automated WSJ PDF downloader: Gmail IMAP check, Chrome profile download, moves to src/News/pdfs/, calls news.py ingest |
| `edgar.py` two-stage 10-K split | edgar.py, screener_config.py | `--fetch-filings` = Stage 1 (download+cache+keyword-extract+enqueue LLM job); `--check-new-filings` = lightweight accession check, marks stale |
| `llm.py --worker --limit N` | llm.py | Accept --limit N: process N jobs then exit cleanly |
| Job queue controls in db.py | db.py | pause_llm_jobs(), resume_llm_jobs(), cancel_llm_jobs(), set_job_priority(), get_distinct_job_types(), reset_enrichment_staleness() |
| Job statuses expanded | db.py, screener_config.py | pending \| running \| done \| failed \| paused \| cancelled |
| Dividend data fix — `_norm_yield()` | enricher.py, db.py | Normalizes yfinance 6.95 vs 0.0695 inconsistency; data migration fixes stored values |
| New stocks columns: ex_dividend_date, dividend_date, last_dividend_value | db.py | Added via migration; enricher populates |
| Bloomberg TUI — ticker search bar | app.py | Sidebar search: type ticker + Enter → StockQuoteModal |
| Bloomberg TUI — DIVIDENDS section in Overview | app.py | Yield, payout ratio, last dividend value, ex-date, pay date |
| Bloomberg TUI — Calendar dividend events | app.py, db.py | ex_dividend and dividend_pay event types; Dividends filter button in CalendarTab |
| `sync_dividend_calendar_events()` in db.py | db.py | Auto-syncs stock dividend dates → calendar_events on CalendarTab.on_mount() |
| api_keys table: url, display_name, connector_config, role columns | db.py | Migration-added; Sources tab uses all four |
| `FACT_LLM_10K_ENTITIES` constant | screener_config.py | `"llm_10k_entities"` — fact type for LLM-extracted supplier/customer entities |
| `FILINGS_CACHE_DIR`, `STALENESS_DAYS`, `HISTORY_STALENESS_DAYS` | screener_config.py | `"src/filings"`, 1, 3 |
| calendar_events: ex_dividend, dividend_pay event types | db.py, screener_config.py | New event types added to EVENT_TYPE_* constants |

---

## Active Gaps & Issues

### Gap 3 — Entity Resolution (still open)

**Problem:** LLM 10-K extraction exists and is validated (`FACT_LLM_10K_ENTITIES` stored in
`edgar_facts`). What is missing is the downstream wiring: extracted supplier/customer names
(e.g. "TSMC", "Foxconn") need to be resolved to stock tickers and automatically inserted into
`event_stocks` so the Logistics panel and scoring engine can use them without manual seeding.

**What needs to exist:**
- `edgar.py` post-extraction step: match entity names from `llm_10k_entities` facts against
  `stocks.company_name` and `stocks.business_summary` using fuzzy match or another LLM call
- Insert matched rows into `event_stocks` with `confidence='low'` and `role='impacted'` or
  `'beneficiary'` based on entity context
- This is tracked in ROADMAP P1 Backlog as "EDGAR entity resolution"

---

### Gap 4 — Consumer Staples / REIT Sector Depth (partially addressed)

**Progress:** 3 new Tier 2 seeds added (consumer staples warehouse fire, West Coast port labor
strike, industrial REIT capacity shock). Tier 2 total: 9 events.

**Still open:**
- Mining/metals disruptions (copper, lithium) affecting semiconductors, EVs, defense — no
  Tier 2 seeds, no automated detection
- Port congestion data (LA/Long Beach, Rotterdam, Singapore) — no automated signal today;
  AIS chokepoints cover routes but not individual port dwell times
- Cross-sector chains (manufacturer → 3PL → warehouse REIT → retail vendor) are thin

---

## Next Up — P1 Data Scraper

- [ ] **Supply chain event editor** — add/edit/retire events and company links from the
  Scraper TUI without touching the CLI or DB directly
- [ ] **Data debugger panel** — pick any ticker, inspect all DB fields (stocks, enrichment,
  edgar_facts, source_signals, price_history summary), flag obvious anomalies
- [ ] **`data_source_mappings` table** — `(role, display_name, priority, enabled)` per user;
  lets a user swap Bloomberg Shipping for AISstream by reassigning the role in the TUI without
  editing module code; `db.get_api_key_for_role()` returns highest-priority enabled key
- [ ] **Entity resolution** — wire LLM-extracted supplier names from `llm_10k_entities` facts
  into `event_stocks` auto-linkage (see Gap 3 above)
- [x] **sql_tables/ missing files** — `llm_jobs.sql`, `newsapi_keywords.sql`, `newsapi_sources.sql`, `settings.sql` created ✅
- [x] **Schedule tab in Scraper TUI** — `scheduled_jobs` table, ScheduleModal, 60s background check, Add/Toggle/Delete ✅
- [x] **WSJ Newspaper pipeline button** — 21st button in Scraper TUI sidebar ✅
- [x] **`scheduled_jobs.sql`** — canonical sql_tables entry created ✅

---

## Next Up — P2 Database & Server

- [ ] Schema viewer — show CREATE TABLE + indexes for any table from within db_app TUI
- [ ] Migration runner — show pending migrations, run with confirmation from TUI
- [ ] Export query result to CSV from SQL shell
- [ ] REST API server (FastAPI) — Phase 5; see ROADMAP P2

---

## Next Up — P3 Bloomberg TUI

- [ ] **Watchlist management** — add/remove symbols from watchlist in the TUI (no CLI);
  watchlist tab showing latest scores, prices, and signals; import from CSV; scoped to user_uid
- [ ] **Scan results history + diff view** — browse all past scan runs, filter by mode/date;
  side-by-side diff between two runs highlighting movers (rank change > 10)
- [ ] Sector rotation view — which sectors are gaining/losing composite score week-over-week

---

## LLM Runtime Notes (keep — still relevant)

**3/3 validation tasks passed** on Qwen2.5-7B-Instruct TurboQuant 4-bit (8GB RTX 3080).

| Task | Result | Time | Key output |
|---|---|---|---|
| News disruption classifier | PASS | 1066s | `event_type: fire`, `PLD` ticker, `Fontana CA`, confidence 0.9 |
| 10-K entity extractor | PASS | 1756s | `china_exposure: 0.19`, `single_source_risk: true`, TSMC supplier |
| 8-K material event parser | PASS | 3146s | `event_type: fire`, `$45M loss`, `tissue paper`, `supply_chain_relevant: true` |

Slow on 8GB (PyTorch fallback, no CuTile kernel). P40 + 32B will be faster.

### VRAM Constraints — READ BEFORE RUNNING

- **Only one LLM process at a time.** Two simultaneous processes fill VRAM (7.7/8GB),
  deadlock each other, and produce no output.
- `load_quantized()` with `device='cuda'` allocates 14GB bf16 scaffold first — OOM on 8GB.
  Fixed in `load_model()`: CPU load → patch index caching → move quantized weights to CUDA.
- `_cached_indices` accumulates unpacked indices for all 196 layers (~20GB total).
  Fixed via `_prepare_for_inference()` no-cache monkey-patch in `llm.py`.
- Use `llm.py --worker --limit N` to process a bounded batch and release VRAM cleanly.

### Model Reference

**Winner:** Qwen2.5 family (Qwen2ForCausalLM). TurboQuant 4-bit g=128 + Hadamard rotation.
NOT Ollama/GGUF compatible — native PyTorch only.

| Hardware | Model | VRAM | Status |
|---|---|---|---|
| 8GB RTX 3080 | Qwen2.5-7B-Instruct 4-bit | ~4.6GB | ✅ validated |
| P40 (24GB) | Qwen2.5-32B-Instruct 4-bit | ~20GB | pending P40 arrival |

---

