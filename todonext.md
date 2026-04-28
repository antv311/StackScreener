# StackScreener — Next Up
> Last updated: 2026-04-28 (milestone 12)

This document is the detailed task layer below `ROADMAP.md`. Where ROADMAP tracks project-level
status and backlogs, this file tracks the specific items we are actively thinking about,
diagnosing, or queued to build next. Update the date at the top whenever this file changes.

---

## What Was Completed This Milestone (2026-04-28, milestone 12)

| Item | Files Changed | Notes |
|---|---|---|
| **SD crash recovery** | venv/pyvenv.cfg | SD card failed 2026-04-25; updated pyvenv.cfg `home`/`executable` to new PyManager path (`C:\Users\antv3\AppData\Local\Python\bin\`); Python bumped 3.14.2 → 3.14.4 |
| **PyTorch reinstall** | (pip) | Installed PyTorch 2.11.0+cu128 prebuilt wheel; fixes WinError 126 `aoti_custom_ops.dll` caused by 3.14.2 → 3.14.4 version bump post-crash |
| **asyncio fix — scraper_app.py** | scraper_app.py | Replaced 3× `asyncio.get_event_loop().create_task()` with `asyncio.ensure_future()` — silently dropped tasks in Python 3.14; fixed queue not refreshing after pipeline runs and LLM worker not streaming |
| **Preset schedule buttons** | scraper_app.py | Added Daily/Weekly/Monthly/Quarterly preset buttons to Schedule tab; each upserts a predefined set of jobs at appropriate intervals; `_PRESET_SCHEDULES` dict + `_LABEL_TO_KEY` map added |
| **bat files** | scraper.bat, bloomberg.bat, db.bat | Three launcher bat files at repo root — activate venv + launch respective TUI |
| **Pipeline architecture MD** | memory/pipeline_architecture.md | Full 6-stage pipeline breakdown: Scraper (upstream/midstream/downstream by region: NA, SA, EU, Asia, Pacific), Aggregate, Index (stock_relationships schema), Digestible (local LLM context), LLM Opinion, End User |

---

## What Was Completed Previous Milestone (2026-04-27, milestone 11)

| Item | Files Changed | Notes |
|---|---|---|
| **Tier 2 refactor — SQL centralization** | edgar.py, inst_flow.py, commodities.py, logistics.py, supply_chain.py, scraper_app.py, db.py | 16 raw `db.query()` calls removed across 5 P1 modules; 12+ named helpers added to `db.py` |
| **Tier 3-A — `utils_http.py` shared HTTP client** | src/utils_http.py (NEW), edgar.py, inst_flow.py, commodities.py, logistics.py | `HttpClient` class (header injection only, no rate limiting); `import requests` removed from all 4 modules; news.py skipped (too varied per-call) |
| **Tier 3-B — Unified logging** | enricher.py, edgar.py, inst_flow.py, news.py, commodities.py, logistics.py, supply_chain.py, screener_run.py, wsj_fetcher.py | All `if DEBUG_MODE: print(...)` replaced with `logger.debug(...)` via Python `logging` module |
| **Tier 4-B — `_score_inverse()` helper in screener.py** | screener.py | Added `_score_inverse(val, max_val)` helper; `_score_pe`, `_score_ev_revenue`, `_score_ev_ebitda`, `_score_peg` all reduced to one-liners |
| **Tier 4-A — Split news.py into submodules** | src/news_utils.py (NEW), src/news_podcast.py (NEW), src/news_feeds.py (NEW), news.py | news.py rewritten as ~230-line thin orchestrator; import DAG: `news_utils` ← `news_podcast`/`news_feeds` ← `news`; full `__all__` re-export for backwards compat |
| **Tier 4-C — Split app.py into tui/ subpackage** | src/tui/__init__.py (NEW), src/tui/formatters.py (NEW), src/tui/modals.py (NEW), src/tui/tabs.py (NEW), src/tui/panels.py (NEW), src/tui/screens.py (NEW), app.py | app.py reduced to 12-line entry point; import DAG: `formatters` ← `modals` ← `tabs` ← `panels` ← `screens` ← `__init__`; no circular imports |
| **All refactor.md tasks complete** | refactor.md | All 16 tasks across Tier 1–4 marked done |

---

## What Was Completed Previous Milestone (2026-04-24, milestone 10)

| Item | Files Changed | Notes |
|---|---|---|
| **FRED commodity pipeline** | commodities.py, screener_config.py, scraper_app.py | Expanded from 3 fertilizer series to 16-series registry: BLS PPI fertilizers, Henry Hub + EU natgas (daily aggregated), copper/aluminum/nickel/zinc/tin/iron ore, palm oil/cocoa/coffee/sugar, lumber. Per-category surge thresholds (15–25%). Fixed USDA endpoint `api_GET` + `year__GE` filter. |
| **Supply chain Tier 2 seeds: 9 new** | supply_chain.py | EU natural gas cutoff, helium shortage, lithium supply shock, Indonesia nickel ban, China rare earth controls, Russia palladium sanctions, Congo cobalt disruption, Ukraine neon/krypton shortage, Australia/Brazil iron ore disruption |
| **Supply chain Tier 2 seeds: 8 more** | supply_chain.py | Panama Canal drought, Russia titanium sanctions, China solar/UFLPA, East Coast ILA port strike, Black Sea grain disruption, Copper Chile/Peru, Rhine River low water, China graphite export controls |
| **Total Tier 2: 27 events, 134 links** | supply_chain.py | Up from 9 events / 51 links. 0 unresolved tickers after universe re-seed. |
| **Universe re-seed + delisted shells** | seeder.py (run), db (direct) | Full NYSE/NASDAQ re-seed (~7,010 stocks). X (US Steel, Nippon Steel acquisition) and DRE (Duke Realty, Prologis acquisition) inserted as delisted shells so seed links resolve. |
| **WSJbot .gitignore fix** | C:\Users\tony\WSJbot\.gitignore | Replaced 963-line individual Chrome file listing with `chromeprofile/` wildcard — eliminated 2,294 perpetually untracked files. |

---

## What Was Completed Previous Milestone (2026-04-24, milestone 9)

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

### Gap 4 — Supply Chain Sector Depth (substantially addressed)

**Progress:** Tier 2 expanded from 9 → 27 events, 134 links. Covers: semiconductors, shipping,
energy, agriculture, battery metals, base metals, industrial gases, fab gases, aerospace,
solar, chemicals, REITs. All 134 company links resolved (0 skipped).

**Still open:**
- Port congestion data (LA/Long Beach, Rotterdam, Singapore) — no automated signal today;
  AIS chokepoints cover sea routes but not individual port dwell times
- Automated supply chain event detection — still manual seeding only; worldmonitor-osint or
  news classifier → event promotion still pending (Gap 3 / entity resolution)
- Cross-sector chains (manufacturer → 3PL → warehouse REIT → retail vendor) thin on automation

---

## Next Up — P1 Data Scraper

### Logistics — Midstream (Phase A, items 1–2)
- [ ] **IMF PortWatch** (`logistics.py --ports`) — vessel call counts at 1,000+ ports globally
  (NA/SA/EU/Asia/Pacific); free REST API, no key; same baseline+anomaly pattern as AIS chokepoints
- [ ] **FAA NASSTATUS** (`logistics.py --air`) — free XML; NA air cargo hub ground stops
  (Memphis FedEx, Louisville UPS, Anchorage transpacific)

### Commodities — Upstream + Downstream (Phase A, items 3–7)
- [ ] **Census MTIS** (`commodities.py --inventory`) — NA monthly inventory-to-sales by sector; free
- [ ] **USDA Cold Storage** (`commodities.py --cold-storage`) — NA cold chain utilization; NASS key exists
- [ ] **CONAB** (`commodities.py --conab`) — SA/Brazil monthly crop reports (soy/corn/coffee/sugar); free
- [ ] **Eurostat** (`commodities.py --eurostat`) — EU quarterly warehouse/transport stats; free API
- [ ] **AAR rail traffic** (`commodities.py --rail`) — NA weekly rail carloadings by commodity; free

### Supply Chain Graph (Phase B)
- [ ] **`stock_relationships` table** — add to `db.py` init + `_migrate_db()` + `sql_tables/stock_relationships.sql`;
  PK=`stock_relationship_uid`, FK=`from_stock_uid`→stocks, FK=`to_stock_uid`→stocks;
  types: supplier | customer | 3pl_provider | warehouse_tenant | competitor | subsidiary
- [ ] **Entity resolution** (Gap 3) — `edgar.py` post-extraction step: fuzzy match `llm_10k_entities`
  names → `stocks.company_name` → insert `stock_relationships` rows with confidence=low, source=llm_10k

### Aggregate + Digestible (Phase C)
- [ ] **`context_builder.py`** — `build_context_pack(stock_uid, lookback_days=90)` → structured dict;
  ~2,000 token budget for 8GB VRAM; assembles fundamentals + news + SC events + inst flow + commodities + logistics + edgar

### LLM Synthesis (Phase D)
- [ ] **`llm.py` Task 4** — `generate_investment_thesis(context_pack)` → JSON report stored to
  `research_reports`; job type `synthesize_thesis` in existing queue

### TUI Enhancements (Phase E)
- [ ] **Supply chain event editor** — add/edit/retire events and company links from TUI
- [ ] **Data debugger panel** — pick any ticker, inspect all DB fields, flag anomalies
- [ ] **Research Reports tab populated** — once Task 4 is live, tab shows LLM-generated reports
- [ ] **`data_source_mappings` table** — role-based key swapping from UI (low priority)

### Done
- [x] sql_tables/ missing files (llm_jobs, newsapi_keywords, newsapi_sources, settings) ✅
- [x] Schedule tab — `scheduled_jobs` table, ScheduleModal, 60s background check ✅
- [x] WSJ Newspaper pipeline button (21st button) ✅
- [x] scheduled_jobs.sql canonical entry ✅
- [x] asyncio.ensure_future fix (3 places in scraper_app.py) ✅
- [x] Preset schedule buttons (Daily/Weekly/Monthly/Quarterly) ✅
- [x] bat files (scraper.bat, bloomberg.bat, db.bat) ✅

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

