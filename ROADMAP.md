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
| `news.py` — WSJ/MS/MF podcasts (Whisper) + WSJ PDF + Yahoo Finance | ✅ Complete |
| `supply_chain.py` — 6 curated events, 37 company links, Tier 1 matching | ✅ Complete |
| `inst_flow.py` — Senate + House Stock Watcher congressional trades | ✅ Built (Phase 3 wiring) |
| SEC EDGAR Form 4 — insider buy/sell filings | 🔲 Next |
| SEC EDGAR Form 13F — institutional holdings | 🔲 Planned |
| yfinance options chain — basic options flow | 🔲 Planned |
| EDGAR LLM extraction — Llama 3.1 70B via Ollama (P40 GPU) | 🔲 Pending GPU |
| Automated supply chain event ingestion | 🔲 Planned |
| `scraper_app.py` — Data Scraper TUI | 🔲 Planned |

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

### News Aggregation

- [x] `news.py` — WSJ podcasts (2 feeds), Morgan Stanley, Motley Fool via RSS + Whisper
- [x] WSJ newspaper PDF ingestion via `pypdf`
- [x] Yahoo Finance news via `yf.Ticker().news` (per ticker or full watchlist)
- [x] Ticker mention detection — regex against full 6,900-ticker set, common words filtered
- [x] Signals stored in `source_signals` (one row per ticker per article)
- [x] All 7 RSS feed URLs verified live (April 2026)

### Institutional Flow

- [x] `inst_flow.py` — Senate Stock Watcher API (free, no key)
- [x] `inst_flow.py` — House Stock Watcher API (free, no key)
- [x] Signals stored in `source_signals` + wired into composite score

---

## P1 — Next Up

### SEC EDGAR Form 4 — Insider Trades

- [ ] `inst_flow.py --form4` — fetch recent Form 4 filings from EDGAR full-text search API
- [ ] Parse: filer name, issuer ticker, transaction type (buy/sell), shares, price, date
- [ ] Store in `source_signals` with `signal_type = 'insider_buy'` / `'insider_sell'`
- [ ] Wire into composite score (configurable weight in `screener_config.py`)

### SEC EDGAR Form 13F — Institutional Holdings

- [ ] `inst_flow.py --form13f` — fetch quarterly 13F filings for top institutions
- [ ] Track position changes (new position, increased, decreased, exited)
- [ ] Store in `source_signals` with `signal_type = 'inst_holding_change'`

### yfinance Options Flow

- [ ] `inst_flow.py --options` — pull options chain via `yf.Ticker().options`
- [ ] Flag unusual call/put volume (>2x 30-day average)
- [ ] Store in `source_signals` with `signal_type = 'unusual_options'`

### Data Scraper TUI (`scraper_app.py`)

- [ ] Live log tail — enricher, EDGAR, news, inst_flow output streamed in real time
- [ ] Manual trigger panel — run any pipeline step on demand with configurable args
- [ ] Source manager — enable/disable sources, edit RSS feed URLs, set rate limits
- [ ] LLM panel — Ollama model status, GPU memory, trigger `--extract-relationships`
- [ ] Data debugger — pick any ticker, inspect all DB fields, flag anomalies
- [ ] Supply chain event editor — add/edit/retire events and company links

**Exit criteria:** An operator can run any enrichment step, inspect the results, and
debug bad data entirely from the TUI without touching the CLI.

---

## P1 — Backlog / Enhancements

- Automated supply chain event ingestion (worldmonitor-osint or news scraping)
- Automated refresh on app startup or scheduled trigger
- Reuters RSS feed ingestion
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
| SQLite layer — 16 tables, 8 indexes, all helpers | ✅ Complete |
| `db_app.py` — Database TUI | 🔲 Planned |
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

### Database TUI (`db_app.py`)

- [ ] Interactive SQL shell — type a query, paginated results rendered as DataTable
- [ ] Table browser — pick any of the 16 tables, page through rows, column filter
- [ ] Schema viewer — show CREATE TABLE + indexes for any table
- [ ] Migration runner — show pending migrations, run with confirmation
- [ ] API key manager — add/rotate/revoke encrypted API keys per user/provider
- [ ] DB stats dashboard — row counts, DB file size, index usage, last enriched
- [ ] Log viewer — tail enricher, EDGAR, news logs from within the TUI

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
| Stock Quote Modal (Enter on any row) | ✅ Complete |
| Home — Market heatmap | 🔲 Next (Phase 1b) |
| Logistics — Interactive world map | 🔲 Planned (Phase 1d) |
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
- [x] Stock Quote Modal — 4 tabs: Overview (40+ fields), Signals, History, News
  - Trigger: Enter on Screener row; "Open Quote →" button in Stock Picks cards
  - All data from DB, no network calls on open

---

## P3 — Next Up

### Phase 1b — Home Screen

- [ ] Full-width market heatmap — tiles color-coded by % change, sized by market cap
- [ ] Click tile → open Stock Quote Modal for that ticker
- [ ] Index selector: S&P 500 / DOW / Russell 1000 / Watchlist / All
- [ ] Summary row: gainers count, losers count, flat count, avg score

### Phase 1d — Logistics Screen (world map)

- [ ] ASCII/Unicode world map with region markers for active SC events
- [ ] Marker color = severity (red=CRITICAL, orange=HIGH, yellow=MEDIUM, blue=LOW)
- [ ] Click/select region → filter the company table below
- [ ] Table: Region/Event | Impacted Companies | Cannot Provide | Will Redirect To | Severity

### Phase 1e — Watchlist Management

- [ ] Add / remove symbols from watchlist via the TUI (no CLI needed)
- [ ] Watchlist tab showing latest scores, prices, and signals
- [ ] Import watchlist from CSV drag-and-drop or file path input
- [ ] Watchlist scoped to logged-in user via `user_uid`

### Phase 1f — Results & History

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
| NVIDIA P40 GPU arrival | Pending — gates EDGAR LLM extraction (P1) |
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
