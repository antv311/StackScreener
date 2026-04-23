# StackScreener — Development Roadmap

**Last updated:** April 2026

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
└────────────┬────────────┘   └────────────┬────────────┘
             │                             │
             ▼                             ▼
        ┌────────────────────────────────────┐
        │         Shared Core                │
        │  db.py · screener_config.py        │
        │  crypto.py · screener.py           │
        │  screener_run.py                   │
        └─────────────┬──────────────────────┘
                      │
        ┌─────────────┴──────────────────────┐
        │                                    │
        ▼                                    ▼
┌───────────────────┐              ┌─────────────────────┐
│  P3 — Bloomberg   │              │  P4 — Web Server    │
│  TUI  (app.py)    │              │  web/  (Phase 5+)   │
└───────────────────┘              └─────────────────────┘
```

**Guiding principle:** Build and validate locally first. A working TUI is a real product.
A half-finished web app is a liability.

---

## Shared Core — Status ✅ COMPLETE

The foundation all four projects depend on.

- [x] Python 3.14.2 venv, C extensions compiled, all deps installed
- [x] `screener_config.py` — all constants, weights, thresholds, status strings
- [x] `db.py` — SQLite layer: 16 tables, 8 covering indexes, CRUD helpers, batch ops
- [x] `crypto.py` — Fernet encryption (OS keyring) + PBKDF2 password hashing
- [x] `seeder.py` — schema init, admin user, NYSE/NASDAQ universe (6,924 stocks)
- [x] `enricher.py` — rate-limited fundamentals worker + IPO calendar + 5y price history
- [x] `screener.py` — scoring engine (EV/R, PE, EV/EBITDA, margin, PEG, D/E, SC, flow)
- [x] `screener_run.py` — scan runner (nsr / thematic / watchlist modes + CSV export)

---

---

# Project 1 — Data Scraper

**Entry point:** `src/scraper_app.py`
**Owns:** `enricher.py`, `edgar.py`, `news.py`, `supply_chain.py`, `inst_flow.py`
**Purpose:** All data engineering — fetching, transcribing, scraping, LLM extraction,
and enrichment. Operators run this to keep the database current and add new sources.

---

## P1 — Status

| Module | Status |
|---|---|
| `enricher.py` — fundamentals + IPO calendar + price history | ✅ Complete |
| `edgar.py` — CIK seed + XBRL geographic revenue + 10-K text flags | ✅ Complete |
| `edgar.py --fetch-8k` — 8-K material event scanner (fire/flood/recall/cyber) | ✅ Complete |
| `news.py` — WSJ/MS/MF podcasts (Whisper) + Yahoo + AP + CNBC + MW + NewsAPI + GDELT | ✅ Complete |
| `news.py` — WSJ newspaper PDF ingestion (pypdf) | 🔲 Blocked — WSJ PDF is scanned images; needs OCR |
| `news.py --classify` — LLM post-ingest hook → supply_chain_events auto-promotion | ✅ Complete |
| `supply_chain.py` — 9 curated events, 51 company links, Tier 1 matching | ✅ Complete |
| `inst_flow.py` — Senate + House Stock Watcher congressional trades | ✅ Complete |
| `inst_flow.py --form4` — SEC EDGAR Form 4 insider buy/sell trades | ✅ Complete |
| `inst_flow.py --form13f` — SEC EDGAR Form 13F institutional holdings (14 institutions) | ✅ Complete |
| `inst_flow.py --options` — yfinance unusual call/put volume (>3× OI) | ✅ Complete |
| `llm.py` — 3 tasks validated 3/3 on Qwen2.5-7B TurboQuant 4-bit | ✅ Complete |
| `llm.py --worker` — SQLite job queue worker; serialises LLM jobs, prevents VRAM deadlock | ✅ Complete |
| `edgar.py` — local filing cache (`src/filings/10k/` + `src/filings/8k/`) | ✅ Complete |
| `commodities.py` — USDA crop conditions + EIA petroleum inventory signals | ✅ Complete |
| `logistics.py` — AIS chokepoints (10 routes) + Panama Canal draft restriction | ✅ Complete |
| `scraper_app.py` — Data Scraper TUI (pipeline buttons, log tail, queue tab, sources tab) | ✅ Complete |

---

## P1 — Completed Work

### Supply Chain Signal Engine

- [x] `supply_chain_events` + `event_stocks` tables — schema, CRUD, role/severity/confidence
- [x] `supply_chain.py --seed-tier2` — 6 curated events (Taiwan Strait, Red Sea, etc.)
- [x] Tier 1 broad sector matching via `db.get_sector_candidates()`
- [x] Thematic scan mode — filters universe to disruption-relevant sectors
- [x] China revenue dampening — high EDGAR China revenue dampens beneficiary scores
- [x] Event context output — event name shown alongside SC score in scan results

### EDGAR XBRL Pipeline

- [x] `edgar_facts` table — geographic revenue + customer concentration per stock per year
- [x] `stocks.cik` — SEC CIK mapping for every ticker
- [x] `edgar.py --seed-ciks` — maps all 6,900 tickers to SEC CIKs
- [x] `edgar.py --fetch-facts` — pulls XBRL geographic revenue + customer concentration
- [x] `edgar.py --fetch-filings` — 10-K text: 8 risk flags + customer % regex extraction
- [x] `db.get_stocks_by_china_exposure()` — query by China revenue threshold
- [x] `db.get_china_revenue_map()` — bulk map for scoring
- [x] `db.get_active_china_events()` — active China/Taiwan events for dampening logic

### LLM Extraction Pipeline

- [x] `llm.py` — TurboQuant 4-bit quantization wrapper + three extraction tasks
- [x] Task 1: news disruption classifier → `supply_chain_events` candidate JSON
- [x] Task 2: 10-K supplier/customer extractor → `edgar_facts` entity JSON
- [x] Task 3: 8-K material event parser → `supply_chain_events` candidate JSON
- [x] Validation test suite (`--test`) with ground-truth pass/fail for all three tasks
- [x] Download + quantize Qwen2.5-7B-Instruct (`python src/llm.py --quantize`) — 4.6 GB
- [x] Run `--test` — all three tasks pass (1066s / 1756s / 3146s; PyTorch fallback on 8GB)
- [x] Wire news classifier into `supply_chain_events` auto-creation (`news.py --classify`)
- [x] Wire 8-K parser into `edgar.py --fetch-8k` pipeline

### News Aggregation

- [x] `news.py` — WSJ podcasts (2 feeds), Morgan Stanley, Motley Fool via RSS + Whisper
- [ ] WSJ newspaper PDF ingestion — blocked: PDF is scanned images, pypdf returns empty text; needs OCR (Tesseract) to complete
- [x] Yahoo Finance news via `yf.Ticker().news` (per ticker or full watchlist)
- [x] Ticker mention detection — regex against full 6,900-ticker set, common words filtered
- [x] Signals stored in `source_signals` (one row per ticker per article)
- [x] AP News RSS (business + finance + technology feeds)
- [x] CNBC RSS (US business + finance feeds)
- [x] MarketWatch RSS (top stories)
- [x] NewsAPI.org REST (aggregates AP, Reuters + 150k sources; free tier; requires key)
- [x] Reuters via NewsAPI (domains=reuters.com filter; Reuters discontinued public RSS 2023)
- [x] GDELT Project REST (global event database; free, no key; strong on physical disruptions)

### Institutional Flow

- [x] `inst_flow.py` — Senate Stock Watcher API (free, no key)
- [x] `inst_flow.py` — House Stock Watcher API (free, no key)
- [x] Signals stored in `source_signals` + wired into composite score

---

## P1 — Next Up

### API Key Provider Name Convention

- [ ] Move all hardcoded provider name strings (`'aisstream'`, `'newsapi'`, `'usda'`, `'eia'`) out of module code into `screener_config.py` constants (e.g. `API_KEY_AISSTREAM`, `API_KEY_NEWSAPI`, etc.)
- [ ] Sources tab in `scraper_app.py` should present a dropdown of known providers rather than a free-text field, so names can never diverge from what each module expects

### Data Scraper TUI — Enhancements

- [ ] Supply chain event editor — add/edit/retire events and company links from TUI
- [ ] Data debugger — pick any ticker, inspect all DB fields, flag anomalies

---

## P1 — Backlog / Enhancements

- **Three-stream coverage gaps** — upstream ✅ (USDA/EIA built), midstream ✅ (AIS/Panama built),
  downstream: REIT entity resolution via 10-K LLM extractor still pending
  — all 5 warehouse-fire smoke-test gaps closed; mining/port-congestion data still open
- Automated supply chain event ingestion (worldmonitor-osint or news scraping)
- Automated refresh on app startup or scheduled trigger
- Earnings call transcript ingestion (via SEC EDGAR or podcast feeds)
- Sentiment scoring on news articles (local model, no API cost)
- Supply chain event confidence scoring using LLM + EDGAR cross-reference
- TASE and European market supply chain mapping
- Backtesting: did past supply chain events generate alpha?

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
| SQLite layer — 18 tables, 9 indexes, all helpers | ✅ Complete |
| LLM job queue helpers (`enqueue`, `dequeue`, `complete`, `fail`, `stats`) | ✅ Complete |
| DB browser helpers (`get_table_names`, `browse_table`, `execute_raw_sql`) | ✅ Complete |
| `db_app.py` — Database TUI (table browser, SQL shell, stats) | ✅ Complete |
| REST API — FastAPI server | 🔲 Phase 5 |
| Multi-user auth — API keys + JWT | 🔲 Phase 5 |

---

## P2 — Completed Work

- [x] 16-table SQLite schema with FK constraints and `tablename_uid` PK convention
- [x] 8 covering indexes across hot query paths
- [x] Fernet-encrypted API key storage via OS keyring
- [x] PBKDF2-HMAC-SHA256 password hashing (260k iterations, per-user salt)
- [x] `_migrate_db()` — safe column/index migrations with `try/except OperationalError`
- [x] `insert_scan_results_batch()` — single-transaction batch insert (6,900 rows)
- [x] `executemany` pattern for all bulk operations

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
- Export any query result to CSV from within the TUI
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
| Research — Screener tab | ✅ Complete |
| Research — Calendar tab | ✅ Complete |
| Research — Stock Comparison tab | ✅ Complete |
| Research — Stock Picks tab | ✅ Complete |
| Research — Research Reports tab | ✅ Complete |
| Research — News tab | ✅ Complete |
| Stock Quote Modal — Overview, Signals, History, News, Filings tabs | ✅ Complete |
| Home — Market heatmap (8-col tile grid, filter buttons, click → StockQuoteModal) | ✅ Complete |
| Logistics — ASCII world map with coloured event markers | ✅ Complete |
| Watchlist management | 🔲 Planned (Phase 1e) |
| Scan results history + diff | 🔲 Planned (Phase 1f) |

---

## P3 — Completed Work

- [x] Textual TUI shell — login, sidebar, panel switching, settings persistence
- [x] Screener tab — filter dropdowns, score bar, 200-row cap, in-memory filter
- [x] Calendar tab — 7-day grid, color-coded chips, week navigation, detail table
- [x] Stock Comparison — 4 tickers, Valuation/Income/Risk sections, ▲/▼ highlights
- [x] Stock Picks — collapsible cards, per-source signal breakdown
- [x] Research Reports — tagged cards from `research_reports` table
- [x] News tab — filterable by source, headline + ticker display
- [x] Stock Quote Modal — 5 tabs: Overview (40+ fields), Signals, History, News, Filings (cached 10-K/8-K preview)
  - Trigger: Enter on Screener row; "Open Quote →" button in Stock Picks cards
  - All data from DB, no network calls on open
- [x] Home heatmap — `HeatmapTile` 8-col CSS grid, bg color by `change_pct`, filter buttons, click → modal
- [x] Logistics world map — `WorldMap(Static)`, 74×18 ASCII equirectangular, coloured markers + legend

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
- Print-to-PDF from within the TUI (fpdf2, dumps current view)
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
- Email morning briefing (`mailer.py`) — daily scan summary + SC event digest
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
| `fpdf2` | PDF report generation | P3 |
| `fastapi` | REST API server | P2, P4 |
| `uvicorn` | ASGI server for FastAPI | P2, P4 |
