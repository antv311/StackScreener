# StackScreener — Development Roadmap

**Last updated:** 2026-04-24

---

## Architecture

StackScreener is structured as four independent projects that share a common core
(`db.py`, `screener_config.py`, `crypto.py`, `screener.py`). Each project has its own
TUI entry point and backlog. Enhancements drop into the relevant project's backlog
without touching the others.

```
┌─────────────────────────┐   ┌─────────────────────────┐
│  P1 — Data Scraper TUI  │   │  P2 — DB & Server TUI   │
│  scraper_app.py         │   │  db_app.py               │
│  ✅ Active              │   │  ✅ Active               │
└────────────┬────────────┘   └────────────┬────────────┘
             │                             │
             ▼                             ▼
        ┌────────────────────────────────────┐
        │         Shared Core                │
        │  db.py · screener_config.py        │
        │  crypto.py · screener.py           │
        │  screener_run.py                   │
        │  SQLite: 20 tables, 10 indexes      │
        └─────────────┬──────────────────────┘
                      │
        ┌─────────────┴──────────────────────┐
        │                                    │
        ▼                                    ▼
┌───────────────────┐              ┌─────────────────────┐
│  P3 — Bloomberg   │              │  P4 — Web Server    │
│  TUI  (app.py)    │              │  web/  (Phase 5+)   │
│  ✅ Active        │              │  🔲 Planned         │
└───────────────────┘              └─────────────────────┘
```

**Guiding principle:** Build and validate locally first. A working TUI is a real product.
A half-finished web app is a liability.

---

## Shared Core — Status ✅ COMPLETE

The foundation all four projects depend on.

- [x] Python 3.14.2 venv, C extensions compiled, all deps installed
- [x] `screener_config.py` — all constants, weights, thresholds, status strings
- [x] `db.py` — SQLite layer: 20 tables, 10 covering indexes, CRUD helpers, batch ops
- [x] `crypto.py` — Fernet encryption (OS keyring) + PBKDF2 password hashing
- [x] `seeder.py` — schema init, admin user, NYSE/NASDAQ universe (~7,010 stocks)
- [x] `enricher.py` — rate-limited fundamentals worker + IPO calendar + 5y price history
- [x] `screener.py` — scoring engine (EV/R, PE, EV/EBITDA, margin, PEG, D/E, SC, flow)
- [x] `screener_run.py` — scan runner (nsr / thematic / watchlist modes + CSV export)

---

---

# Project 1 — Data Scraper

**Entry point:** `src/scraper_app.py`
**Owns:** `enricher.py`, `edgar.py`, `news.py`, `supply_chain.py`, `inst_flow.py`,
          `commodities.py`, `logistics.py`, `llm.py`, `wsj_fetcher.py`
**Purpose:** All data engineering — fetching, transcribing, scraping, LLM extraction,
and enrichment. Operators run this to keep the database current and add new sources.

---

## P1 — Status

| Module | Status |
|---|---|
| `enricher.py` — fundamentals + IPO calendar + price history | ✅ Complete |
| `enricher.py` — dividend data fix (`_norm_yield()`) + ex_dividend/dividend/last_dividend_value cols | ✅ Complete |
| `edgar.py` — CIK seed + XBRL geographic revenue + 10-K two-stage pipeline + 8-K material events | ✅ Complete |
| `edgar.py --fetch-filings` — Stage 1: download + cache + keyword-extract + enqueue LLM job | ✅ Complete |
| `edgar.py --check-new-filings` — lightweight accession check, marks stale for re-fetch | ✅ Complete |
| `news.py` — WSJ/MS/MF podcasts (Whisper) + Yahoo + AP + CNBC + MW + NewsAPI + GDELT | ✅ Complete |
| `news.py --classify` — LLM post-ingest hook → supply_chain_events auto-promotion | ✅ Complete |
| `wsj_fetcher.py` — automated WSJ PDF downloader via Gmail IMAP + Chrome profile | ✅ Complete |
| `supply_chain.py` — 27 curated events, 134 company links, Tier 1 matching | ✅ Complete |
| `inst_flow.py` — Senate + House Stock Watcher congressional trades | ✅ Complete |
| `inst_flow.py --form4` — SEC EDGAR Form 4 insider buy/sell trades | ✅ Complete |
| `inst_flow.py --form13f` — SEC EDGAR Form 13F institutional holdings (14 institutions) | ✅ Complete |
| `inst_flow.py --options` — yfinance unusual call/put volume (>3× OI) | ✅ Complete |
| `llm.py` — 3 tasks validated 3/3 on Qwen2.5-7B TurboQuant 4-bit | ✅ Complete |
| `llm.py --worker` — SQLite job queue worker; serialises LLM jobs, prevents VRAM deadlock | ✅ Complete |
| `llm.py --worker --limit N` — process N jobs then exit | ✅ Complete |
| `edgar.py` — local filing cache (`src/filings/10k/` + `src/filings/8k/`) | ✅ Complete |
| `commodities.py` — USDA crop conditions + EIA petroleum inventory signals | ✅ Complete |
| `logistics.py` — AIS chokepoints (10 routes) + Panama Canal draft restriction | ✅ Complete |
| `scraper_app.py` — Data Scraper TUI (21 pipeline buttons incl. WSJ, log tail, queue tab, sources tab, schedule tab) | ✅ Complete |
| LLM job queue controls — pause/resume/cancel/priority in db.py | ✅ Complete |
| `scraper_app.py` — Schedule tab with `scheduled_jobs` table, ScheduleModal, 60s background check | ✅ Complete |
| Tier 1 refactoring — User-Agent centralization, config dict consolidation, SQL helpers, sys.path cleanup | ✅ Complete |

---

## P1 — Completed Work

### Supply Chain Signal Engine

- [x] `supply_chain_events` + `event_stocks` tables — schema, CRUD, role/severity/confidence
- [x] `supply_chain.py --seed-tier2` — 27 curated events, 134 company links: semiconductors (Taiwan Strait, US-China chips, China rare earths), shipping (Red Sea, West Coast ILWU, East Coast ILA, Panama Canal drought), energy (Gulf hurricane, EU natgas cutoff), agriculture (Midwest drought, South Asia fertilizer, Black Sea grain), battery metals (lithium, cobalt, nickel, palladium, graphite), materials (copper, iron ore, titanium, helium, neon/krypton), solar (UFLPA tariffs), chemicals (Rhine drought), REITs (warehouse fire, REIT capacity shock)
- [x] Tier 1 broad sector matching via `db.get_sector_candidates()`
- [x] Thematic scan mode — filters universe to disruption-relevant sectors
- [x] China revenue dampening — high EDGAR China revenue dampens beneficiary scores
- [x] Event context output — event name shown alongside SC score in scan results

### EDGAR XBRL + 10-K Pipeline

- [x] `edgar_facts` table — geographic revenue + customer concentration + risk flags per stock per year
- [x] `stocks.cik` — SEC CIK mapping for every ticker
- [x] `edgar.py --seed-ciks` — maps all 7,000+ tickers to SEC CIKs
- [x] `edgar.py --fetch-facts` — pulls XBRL geographic revenue + customer concentration
- [x] `edgar.py --fetch-filings` — two-stage 10-K pipeline: Stage 1 downloads+caches+keyword-extracts+enqueues LLM job; Stage 2 = LLM worker processes enqueued jobs
- [x] `edgar.py --check-new-filings` — lightweight accession number check; marks stale for re-fetch without downloading
- [x] `db.get_stocks_by_china_exposure()` — query by China revenue threshold
- [x] `db.get_china_revenue_map()` — bulk map for scoring
- [x] `db.get_active_china_events()` — active China/Taiwan events for dampening logic

### LLM Extraction Pipeline

- [x] `llm.py` — TurboQuant 4-bit quantization wrapper + three extraction tasks
- [x] Task 1: news disruption classifier → `supply_chain_events` candidate JSON
- [x] Task 2: 10-K supplier/customer extractor → `edgar_facts` entity JSON (`llm_10k_entities`)
- [x] Task 3: 8-K material event parser → `supply_chain_events` candidate JSON
- [x] Validation test suite (`--test`) with ground-truth pass/fail for all three tasks
- [x] `llm.py --worker --limit N` — process N jobs then exit; prevents VRAM deadlock
- [x] Job queue controls: `pause_llm_jobs()`, `resume_llm_jobs()`, `cancel_llm_jobs()`, `set_job_priority()`, `get_distinct_job_types()`, `reset_enrichment_staleness()`
- [x] Job statuses: pending | running | done | failed | paused | cancelled

### News Aggregation

- [x] `news.py` — WSJ podcasts (2 feeds), Morgan Stanley, Motley Fool via RSS + Whisper
- [x] WSJ newspaper PDF ingestion via `wsj_fetcher.py` — Gmail IMAP check → Chrome profile download → `src/News/pdfs/` → `news.py` ingest pipeline
- [x] Yahoo Finance news via `yf.Ticker().news` (per ticker or full watchlist)
- [x] Ticker mention detection — regex against full 7,000-ticker set, common words filtered
- [x] Signals stored in `source_signals` (one row per ticker per article)
- [x] AP News RSS (business + finance + technology feeds)
- [x] CNBC RSS (US business + finance feeds)
- [x] MarketWatch RSS (top stories)
- [x] NewsAPI.org REST (aggregates AP, Reuters + 150k sources; free tier; requires key)
- [x] Reuters via NewsAPI (domains=reuters.com filter)
- [x] GDELT Project REST (global event database; free, no key)

### Institutional Flow

- [x] `inst_flow.py` — Senate Stock Watcher API (free, no key)
- [x] `inst_flow.py` — House Stock Watcher API (free, no key)
- [x] SEC EDGAR Form 4 insider trades → `source_signals`
- [x] SEC EDGAR Form 13F — 14 institutions, position change detection → `source_signals`
- [x] yfinance unusual options volume (>3× OI) → `source_signals`
- [x] All signals wired into composite score via additive overlay

### Commodities & Logistics

- [x] `commodities.py --usda-crops` — USDA NASS weekly crop conditions → `crop_stress` signals
- [x] `commodities.py --eia-petroleum` — EIA crude/gasoline weekly surprise → `oil_inventory_surprise`
- [x] `commodities.py --fred-commodities` — FRED 16-series registry: BLS PPI fertilizers, Henry Hub + EU natgas, copper/aluminum/nickel/zinc/tin/iron ore, palm oil/cocoa/coffee/sugar, lumber → per-category surge signals
- [x] `logistics.py --chokepoints` — AIS vessel counts at 10 global chokepoints → `chokepoint_congestion`
- [x] `logistics.py --panama` — Panama Canal draft restriction scrape → `canal_draft_restriction`

### Data Scraper TUI (`scraper_app.py`)

- [x] 20 pipeline buttons (full list in README and CONTEXT)
- [x] Live log tail (right panel Logs tab)
- [x] Queue tab — pending/running/done/failed/paused/cancelled counts + job list; Pause/Resume/Cancel/Priority controls by job type; auto-refreshes every 5s
- [x] Sources tab — unified EndpointModal for add/edit; api_keys.display_name, url, connector_config, role columns
- [x] LLM Worker Start/Stop toggle — runs `llm.py --worker` as background subprocess
- [x] Fetch Price History button — triggers `enricher.py --history-only`
- [x] Force Re-enrich All button — calls `reset_enrichment_staleness()` then triggers enricher

### Dividend Data

- [x] `_norm_yield()` in `enricher.py` — normalizes yfinance inconsistency (6.95 vs 0.0695)
- [x] Data migration fixes already-stored incorrect values
- [x] New `stocks` columns: `ex_dividend_date`, `dividend_date`, `last_dividend_value`

### API Key Management

- [x] `api_keys` table: `url`, `display_name`, `connector_config`, `role` columns added via migration
- [x] `KNOWN_API_ROLES` list in `screener_config.py` — canonical (role_key, description) pairs
- [x] Sources tab `EndpointModal` uses dropdown of known roles when adding

---

## P1 — Next Up

### Custom Data Source Mapping

Enable users to register new data sources and map them to existing pipeline roles without
changing module code. A "Bloomberg Shipping" key tagged to role `aisstream` already works
today.

- [ ] `data_source_mappings` table — `(role, display_name, priority, enabled)` per user;
  allows swapping Bloomberg for AISstream by reassigning the role mapping from the UI
- [ ] Sources tab UI — "Map Role" button on each key row; drag-to-reorder priority;
  enable/disable toggle so you can stage a new provider before cutting over
- [ ] `db.get_api_key_for_role()` — returns the highest-priority enabled key for a given role

### Data Scraper TUI — Enhancements

- [ ] Supply chain event editor — add/edit/retire events and company links from TUI
- [ ] Data debugger — pick any ticker, inspect all DB fields, flag anomalies

---

## P1 — Backlog / Enhancements

- **Entity resolution** — wire LLM-extracted supplier names from `llm_10k_entities` facts
  into `event_stocks` auto-linkage (Gap 3 from warehouse fire smoke test)
- **Three-stream coverage gaps** — upstream ✅ (USDA/EIA built), midstream ✅ (AIS/Panama built),
  downstream: REIT entity resolution via 10-K LLM extractor still pending;
  mining/port-congestion data still open
- Automated supply chain event ingestion (worldmonitor-osint or news scraping)
- Earnings call transcript ingestion (via SEC EDGAR or podcast feeds)
- Sentiment scoring on news articles (local model, no API cost)
- TASE and European market supply chain mapping
- Backtesting: did past supply chain events generate alpha?
- Dividend history dedicated table (currently in `price_history.dividend` column)

---

---

# Project 2 — Database & Server

**Entry point:** `src/db_app.py`
**Owns:** `db.py` internals, future FastAPI server, API key management
**Purpose:** Direct database access, query debugging, migration management, and
(eventually) the REST API server that exposes StackScreener data to external clients.

---

## P2 — Status

| Component | Status |
|---|---|
| SQLite layer — 20 tables, 10 indexes, all helpers | ✅ Complete |
| LLM job queue helpers (`enqueue`, `dequeue`, `complete`, `fail`, `pause`, `cancel`, `stats`) | ✅ Complete |
| Job controls (`pause_llm_jobs`, `resume_llm_jobs`, `cancel_llm_jobs`, `set_job_priority`) | ✅ Complete |
| DB browser helpers (`get_table_names`, `browse_table`, `execute_raw_sql`) | ✅ Complete |
| `db_app.py` — Database TUI (table browser, SQL shell, stats) | ✅ Complete |
| REST API — FastAPI server | 🔲 Phase 5 |
| Multi-user auth — API keys + JWT | 🔲 Phase 5 |

---

## P2 — Completed Work

- [x] 19-table SQLite schema with FK constraints and `tablename_uid` PK convention
- [x] 9 covering indexes across hot query paths
- [x] Fernet-encrypted API key storage via OS keyring
- [x] PBKDF2-HMAC-SHA256 password hashing (260k iterations, per-user salt)
- [x] `_migrate_db()` — safe column/index migrations with `try/except OperationalError`
- [x] `insert_scan_results_batch()` — single-transaction batch insert (7,000 rows)
- [x] `executemany` pattern for all bulk operations
- [x] `sync_dividend_calendar_events()` — syncs stock dividend dates → calendar_events automatically

---

## P2 — Next Up

### Database TUI — Enhancements

- [ ] Schema viewer — show CREATE TABLE + indexes for any table from within TUI
- [ ] Migration runner — show pending migrations, run with confirmation
- [ ] Export query result to CSV from SQL shell

### REST API Server (Phase 5)

- [ ] FastAPI application in `web/api/`
- [ ] Endpoints: `/scan/run`, `/scan/results`, `/stocks/{ticker}`, `/events`, `/watchlist`
- [ ] JWT authentication wrapping existing `crypto.py` + `users` table
- [ ] Rate limiting per API key
- [ ] OpenAPI docs auto-generated
- [ ] Deploy to Ubuntu (VPS or home server)

**Exit criteria:** Friends can point their own frontend or scripts at the API and get
live scan results, stock quotes, and supply chain events without running the TUI.

---

## P2 — Backlog / Enhancements

- Query history — save and replay previous SQL queries
- DB health checks — detect missing indexes, bloated tables, orphaned FKs
- WebSocket endpoint for live scan progress streaming
- Plaid integration for live portfolio sync
- Multi-tenant user management (invite users, assign roles)
- 2FA enforcement via `totp_secret` column on `users`
- Webhook alerts — push scan results or SC events to Slack / Discord / custom URL

---

---

# Project 3 — Bloomberg TUI

**Entry point:** `src/app.py`
**Owns:** All user-facing terminal UI
**Purpose:** The main product. Navigate scan results, research stocks, monitor supply
chain events, and manage watchlists from a polished terminal interface.

---

## P3 — Status

| Screen / Tab | Status |
|---|---|
| Login screen + forced password change | ✅ Complete |
| Sidebar navigation (Home / Research / Logistics / Settings) | ✅ Complete |
| Sidebar ticker search bar — type ticker + Enter → StockQuoteModal | ✅ Complete |
| Research — Screener tab | ✅ Complete |
| Research — Calendar tab | ✅ Complete |
| Research — Calendar — ex_dividend / dividend_pay event types + Dividends filter button | ✅ Complete |
| Research — Stock Comparison tab | ✅ Complete |
| Research — Stock Picks tab | ✅ Complete |
| Research — Research Reports tab | ✅ Complete |
| Research — News tab | ✅ Complete |
| Stock Quote Modal — Overview, Signals, History, News, Filings tabs | ✅ Complete |
| Stock Quote Modal — DIVIDENDS section in Overview (yield, payout, last div, ex-date, pay date) | ✅ Complete |
| Home — Market heatmap (8-col tile grid, filter buttons, click → StockQuoteModal) | ✅ Complete |
| Logistics — ASCII world map with coloured event markers | ✅ Complete |
| Watchlist management | 🔲 Planned (Phase 1e) |
| Scan results history + diff | 🔲 Planned (Phase 1f) |

---

## P3 — Completed Work

- [x] Textual TUI shell — login, sidebar, panel switching, settings persistence
- [x] Screener tab — filter dropdowns, score bar, 200-row cap, in-memory filter
- [x] Calendar tab — 7-day grid, color-coded chips, week navigation, detail table; ex_dividend and dividend_pay event chips; Dividends filter button; auto-syncs dividend dates from stocks on mount
- [x] Stock Comparison — 4 tickers, Valuation/Income/Risk sections, ▲/▼ highlights
- [x] Stock Picks — collapsible cards, per-source signal breakdown
- [x] Research Reports — tagged cards from `research_reports` table
- [x] News tab — filterable by source, headline + ticker display
- [x] Stock Quote Modal — 5 tabs: Overview (40+ fields + DIVIDENDS section), Signals, History, News, Filings (cached 10-K/8-K preview)
  - Trigger: Enter on Screener row; "Open Quote →" button in Stock Picks cards; ticker search bar in sidebar
  - All data from DB, no network calls on open
- [x] Home heatmap — `HeatmapTile` 8-col CSS grid, bg color by `change_pct`, filter buttons, click → modal
- [x] Logistics world map — `WorldMap(Static)`, 74×18 ASCII equirectangular, coloured markers + legend
- [x] Ticker search bar — sidebar input; type any ticker + Enter → StockQuoteModal directly

---

## P3 — Next Up

### Watchlist Management

- [ ] Add / remove symbols from watchlist via the TUI (no CLI needed)
- [ ] Watchlist tab showing latest scores, prices, and signals
- [ ] Import watchlist from CSV drag-and-drop or file path input
- [ ] Watchlist scoped to logged-in user via `user_uid`

### Results & History

- [ ] Browse all past scan runs — filter by mode, date, score count
- [ ] Side-by-side diff: two scan runs, highlight movers (rank up/down > 10)
- [ ] Export current view to CSV from within the app

**Exit criteria:** A non-technical user can run a scan, research any stock, monitor
supply chain events, and manage a watchlist entirely from the TUI.

---

## P3 — Backlog / Enhancements

- Alerts panel — view triggered alerts (score threshold, SC event, congressional trade)
- Portfolio tracker — enter holdings, show P&L vs last scan benchmark
- Sector rotation view — which sectors are gaining/losing score week-over-week
- Keyboard command palette (`:` to open, type any action)
- Dark/light theme toggle persisted in `settings` table
- Confluence view — stocks where SC signal + inst flow + fundamentals all align
- Backtesting view — replay historical SC events, show what the screener would have surfaced

---

---

# Project 4 — Web Server & Site

**Entry point:** `web/` directory
**Owns:** FastAPI backend, REST API, and browser-based frontend
**Status:** 🔲 Planned — begins after Project 2 REST API is stable
**Prerequisite:** Projects 1–3 fully validated; REST API live from Project 2

---

## P4 — Planned Work

- [ ] FastAPI app in `web/api/` wrapping scan engine and DB helpers
- [ ] React frontend (based on `StackScreenerCD/` prototype) consuming the REST API
- [ ] Pages: Home heatmap, Screener, Calendar, Stock Comparison, Stock Picks, Quote
- [ ] Logistics map (Leaflet.js with D3 overlays)
- [ ] User auth — login, JWT, 2FA via `totp_secret`
- [ ] Watchlist sync between TUI and web
- [ ] Plaid integration for live portfolio sync
- [ ] Deploy to Ubuntu server

**Exit criteria:** Full feature parity with the Bloomberg TUI, accessible from a browser.
Friends can create accounts and run their own scans.

---

## P4 — Backlog / Enhancements

- Mobile-responsive layout
- PWA / home screen install
- Shareable scan result links (public permalink per scan run)
- Embeddable supply chain event widget for external sites
- Email morning briefing — daily scan summary + SC event digest
- SMS / webhook alerts on score threshold or new SC event
- Public API tier with rate limiting (friends build their own tools on top)

---

---

## Open Questions / Blockers

| Item | Status |
|---|---|
| Supply chain event auto-ingestion source | TBD — worldmonitor-osint vs news scraping |
| NVIDIA P40 GPU arrival | Pending — gates Qwen2.5-32B production inference; 7B validated 3/3 on 8GB laptop |
| Ubuntu deployment environment | TBD — VPS, home server, or cloud |
| REST API authentication design | Deferred to Project 2 |
| EDGAR entity resolution | Gap 3 — LLM extraction done; wiring to event_stocks auto-linkage still pending |

---

## Dependencies Reference

| Package | Purpose | Project |
|---|---|---|
| `yfinance` | Price, fundamentals, IPO calendar, options chain | P1 |
| `yahooquery` | Detailed financials supplement | P1 |
| `pandas-ta` | Technical indicators (install `--no-deps`) | P1 |
| `openai-whisper` | Podcast transcription | P1 |
| `pypdf` | WSJ PDF text extraction | P1 |
| `torch` | Whisper backend (custom cp314 wheel) | P1 |
| `transformers` | Model loading for LLM pipeline | P1 |
| `accelerate` | GPU device_map for transformers | P1 |
| `turboquant-model` | TurboQuant 4-bit weight quantization (cksac/turboquant-model) | P1 |
| `xformers` | Memory-efficient attention (cp314 wheel available) | P1 |
| `requests` | HTTP — SEC EDGAR, congressional trade APIs | P1 |
| `textual` | Terminal UI framework | P1, P2, P3 |
| `cryptography` | Fernet encryption | Shared core |
| `keyring` | OS keyring — Fernet master key | Shared core |
| `sqlite3` | Database (stdlib, no ORM) | Shared core |
| `numpy` | Numerics (compile from source on Windows) | Shared core |
| `pandas` | DataFrames (compile from source on Windows) | Shared core |
| `CurrencyConverter` | FX conversion | Shared core |
| `fastapi` | REST API server | P2, P4 |
| `uvicorn` | ASGI server for FastAPI | P2, P4 |
