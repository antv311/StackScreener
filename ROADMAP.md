# StackScreener — Development Roadmap

**Current Status:** Phase 0 complete. Phase 1a (app shell) and 1c (Research tabs) complete. Phase 2d (news aggregator) partial — news.py built, feed URLs need verification before first run.
**Last updated:** April 2026

---

## Guiding Principle

Build the desktop app first. Validate the scoring engine and supply chain logic locally before
adding the complexity of a web server, authentication, and deployment. A working CLI/TUI app
is a real product. A half-finished web app is a liability.

---

## Phase 0 — Environment & Foundation ✅ COMPLETE

- [x] Python 3.14.2 venv at `venv/`, C extensions compiled, all deps installed
- [x] `screener_config.py` — all constants, weights, thresholds, status strings, provider names
- [x] `db.py` — full SQLite layer: 16 tables, 2 covering indexes, CRUD helpers, upsert builders, batch ops
- [x] `crypto.py` — Fernet encryption via OS keyring + PBKDF2 password hashing
- [x] `seeder.py` — schema init, default admin user, NYSE/NASDAQ universe fetch (6,924 stocks)
- [x] `enricher.py` — rate-limited fundamentals worker + daily IPO calendar check + 5y price history
- [x] Full database seeded and enriched — 6,910 stocks with fundamentals + price history
- [x] `screener.py` — scoring engine (EV/R, PE, EV/EBITDA, margin, PEG, D/E, supply chain, inst flow)
- [x] `screener_run.py` — scan runner + CLI entry point (nsr / thematic / watchlist modes + CSV export)

**Exit criteria met:** `python screener_run.py` completes a full scan, saves to DB, outputs CSV. ✅

---

## Phase 1 — Desktop App (Textual TUI)

Turn the screener into a usable standalone desktop application matching the agreed UI mockup.

### 1a — Core App Shell ✅ COMPLETE

- [x] Create `app.py` as the Textual TUI entry point
- [x] Three-section sidebar: Home / Research / Logistics
- [x] Login screen — enforce password change for admin on first run
- [x] Config management: load/save user settings via `settings` table
- [x] Graceful error handling and user-friendly error messages

### 1b — Home Screen

- [ ] Full-width market heatmap (tiles color-coded by % change, sized by market cap)
- [ ] Index selector at bottom: S&P 500 / DOW / Russell 1000 / Recommended / All

### 1c — Research Screen (5 sub-tabs) ✅ COMPLETE

- [x] **Screener** — filter dropdowns (Exchange/Sector/MCap/P/E/Signal); score bar; in-memory filtering; 200-row cap
- [x] **Calendar** — 7-day weekly grid (DayCell per day); color-coded event chips; week navigation; filter buttons; detail table
- [x] **Stock Comparison** — 4 ticker inputs; DB lookup; Valuation/Income/Risk sections; green ▲ best / red ▼ worst per row
- [x] **Stock Picks** — collapsible Textual cards for top 15 scan results; source signal breakdown (populated in Phase 3)
- [x] **Research Reports** — scrollable tagged cards from `research_reports` table; empty-state with Phase 2 context

### 1d — Logistics Screen

- [ ] World map with pulsing pins for active supply chain disruptions (color = severity)
- [ ] Click pin → filter table to that event
- [ ] Table: Region/Event | Impacted Companies | Cannot Provide | Will Redirect To | Severity

### 1e — Watchlist Management

- [ ] Add / remove symbols from watchlist via app
- [ ] View watchlist with latest scores and prices
- [ ] Import watchlist from CSV
- [ ] Persist watchlist to `db.py` (user-scoped via `user_uid`)

### 1f — Results & History

- [ ] View past scan results from DB
- [ ] Side-by-side diff of two scan runs
- [ ] Export results to CSV from within the app

**Exit criteria:** A non-technical user can run a scan, browse results, and manage a watchlist
entirely from the TUI without touching any Python files.

---

## Phase 2 — Supply Chain Signal Engine

Add the core intelligence layer that makes StackScreener different from any other screener.

### 2a — Disruption Events (partial ✅)

- [x] `supply_chain_events` table — schema, CRUD helpers, sector/region/severity fields
- [x] `event_stocks` junction table — role (impacted/beneficiary), cannot_provide, will_redirect
- [x] `supply_chain.py --seed-tier2` — 6 curated events, 31 company links seeded
- [x] `db.get_sector_candidates()` — Tier 1 broad sector matching
- [ ] Automated ingestion of new disruption events (worldmonitor-osint or equivalent)
- [ ] Automated refresh on app startup (or on demand)

### 2b — EDGAR XBRL Data Pipeline (partial ✅)

- [x] `edgar_facts` table — geographic revenue + customer concentration per stock per year
- [x] `stocks.cik` — SEC CIK mapping for every ticker
- [x] `edgar.py --seed-ciks` — map all 6,900 tickers to SEC CIKs
- [x] `edgar.py --fetch-facts` — pull XBRL geographic revenue + customer concentration
- [x] `db.get_stocks_by_china_exposure()` — query stocks by China revenue threshold
- [ ] Wire geographic exposure into supply chain scoring (high China revenue = higher impact score)

### 2c — EDGAR LLM Extraction (pending P40 GPU)

- [ ] Run Llama 3.1 70B (4-bit quant) locally via Ollama on NVIDIA P40 (24GB VRAM)
- [ ] `edgar.py --extract-relationships` — feed 10-K Item 1A to LLM, extract supplier/customer links
- [ ] Auto-populate `event_stocks` with medium-confidence relationships from filings
- [ ] Zero API cost; runs entirely local

### 2d — News Aggregation (partial ✅)

Module: `src/news.py` — built
Table: `news_articles` (16th table) — built
Directories: `src/News/audio/` (temp MP3), `src/News/pdfs/` (WSJ PDFs kept)
Dependencies: `torch` (custom cp314 wheel), `openai-whisper`, `pypdf` (already present)

- [x] **WSJ podcasts** — RSS → MP3 → Whisper transcription; uses embedded transcript tag if present
- [x] **Morgan Stanley "Thoughts on the Market"** — same RSS + Whisper pipeline
- [x] **Motley Fool Money** — same RSS + Whisper pipeline
- [x] **Yahoo Finance** — `yf.Ticker(ticker).news` per ticker or full watchlist
- [x] **WSJ newspaper PDF** — `pypdf` text extraction; drop PDF in `src/News/pdfs/`
- [x] Ticker mention detection — regex against full 6,900-ticker DB set; common words filtered
- [x] Signals stored in `source_signals` (one row per ticker per article)
- [ ] Verify RSS feed URLs in `screener_config.py` before first run
- [ ] Add news section to Research screen in app (Phase 1c follow-on)

### 2e — Financial Podcast Transcripts ✅ (merged into 2d)

Covered by `news.py` podcast pipeline above — all three shows use the same RSS + Whisper path.

### 2f — Thematic Scan Mode

- [ ] New scan mode: `run_thematic` — filters universe to disruption-relevant sectors
- [ ] Supply chain signal score layered on top of fundamental score
  (Tier 1 sector match + Tier 2 curated links + EDGAR geographic exposure)
- [ ] Output: ranked list of gap-filler candidates with disruption context

**Exit criteria:** Given a real supply chain event, StackScreener surfaces a ranked list of
companies positioned to benefit, with geographic exposure data and news signals attached.

---

## Phase 3 — Institutional Flow Integration

Layer in free public smart-money signals to validate or strengthen supply chain picks.
Quiver Quant and Unusual Whales were dropped — too expensive. Replaced with free public sources.

- [ ] Integrate **Senate Stock Watcher API** (congressional trades — Senate, free)
- [ ] Integrate **House Stock Watcher API** (congressional trades — House, free)
- [ ] Integrate **SEC EDGAR Form 4** (insider buy/sell filings, free public API)
- [ ] Integrate **SEC EDGAR Form 13F** (institutional holdings, free public API)
- [ ] Integrate **yfinance options chain** (basic options flow, free)
- [ ] Store all signals in `source_signals` table via `db.py`
- [ ] Incorporate flow signals into final ranking (configurable weight in `screener_config.py`)
- [ ] Confluence view: supply chain signal + institutional flow + fundamentals all aligned

**Exit criteria:** A scan result shows which supply chain picks also have congressional or
insider buying, with a combined score. No paid API keys required.

---

## Phase 4 — Alerts & Automation

Make StackScreener run continuously and notify on significant events.

- [ ] Scheduled scans (daily pre-market, configurable)
- [ ] Alert on: new supply chain event, score threshold crossed, new congressional trade
- [ ] Email delivery via `mailer.py`
- [ ] Optional: SMS / webhook alerts
- [ ] Watchlist price alerts

**Exit criteria:** StackScreener runs unattended overnight and emails a morning briefing.

---

## Phase 5 — Web App

Migrate the desktop app to a web interface. By this point the core logic is fully validated.

- [ ] FastAPI backend
- [ ] REST API wrapping scan engine and DB queries
- [ ] Web dashboard: scan runner, results table, supply chain event feed, watchlist
- [ ] User authentication (multi-user, 2FA via stored `totp_secret`)
- [ ] Plaid integration for live portfolio sync
- [ ] Deploy to Ubuntu server

**Exit criteria:** Full feature parity with the desktop app, accessible from a browser.

---

## Backlog / Nice to Have

- Portfolio performance tracking against benchmark
- Backtesting: would past supply chain events have generated alpha?
- Sector rotation signals
- TASE and European market supply chain mapping
- Integration with news APIs for event detection
- ML-based sector impact prediction

---

## Current Blockers / Open Questions

- Supply chain data source TBD: worldmonitor-osint vs paid API vs news scraping
- Ubuntu deployment environment TBD (VPS, home server, cloud?)

---

## Dependencies Reference

| Package | Purpose | Notes |
|---|---|---|
| `yfinance` | Price, fundamentals, IPO calendar, options chain | Primary data source |
| `yahooquery` | Detailed financials | Supplement to yfinance |
| `pandas-ta` | Technical indicators | Install with `--no-deps` (no numba) |
| `fpdf2` | PDF report generation | |
| `CurrencyConverter` | FX conversion | |
| `textual` | Terminal UI | Phase 1 |
| `requests` | HTTP fetches | SEC EDGAR, congressional trade APIs |
| `cryptography` | Fernet encryption | API key storage |
| `keyring` | OS keyring access | Fernet master key storage |
| `sqlite3` | DB (stdlib) | No ORM needed |
| `numpy` | Numerics | Compile from source on Windows |
| `pandas` | DataFrames | Compile from source on Windows |
