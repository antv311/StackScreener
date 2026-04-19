# StackScreener — Development Roadmap

**Current Status:** Phase 0 complete. Database fully seeded and enriched. Next: scoring engine.
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
- [x] `db.py` — full SQLite layer: 13 tables, 2 covering indexes, CRUD helpers, upsert builders, batch ops
- [x] `crypto.py` — Fernet encryption via OS keyring + PBKDF2 password hashing
- [x] `seeder.py` — schema init, default admin user, NYSE/NASDAQ universe fetch (6,924 stocks)
- [x] `enricher.py` — rate-limited fundamentals worker + daily IPO calendar check + 5y price history
- [x] Full database seeded and enriched — 6,910 stocks with fundamentals + price history
- [ ] `screener.py` + `screener_run.py` — scoring engine + CLI entry point  ← **NEXT**

**Exit criteria:** `python screener_run.py` completes a full scan, saves to DB, outputs CSV.

---

## Phase 1 — Desktop App (Textual TUI)

Turn the screener into a usable standalone desktop application matching the agreed UI mockup.

### 1a — Core App Shell

- [ ] Create `app.py` as the Textual TUI entry point
- [ ] Three-section sidebar: Home / Research / Logistics
- [ ] Login screen — enforce password change for admin on first run
- [ ] Config management: load/save user settings via `settings` table
- [ ] Graceful error handling and user-friendly error messages

### 1b — Home Screen

- [ ] Full-width market heatmap (tiles color-coded by % change, sized by market cap)
- [ ] Index selector at bottom: S&P 500 / DOW / Russell 1000 / Recommended / All

### 1c — Research Screen (5 sub-tabs)

- [ ] **Screener** — filterable/sortable table; filters: Exchange, Sector, Market Cap, P/E, Signal
- [ ] **Calendar** — weekly grid with color-coded event chips (Earnings / Splits / IPOs / Economic)
- [ ] **Stock Comparison** — side-by-side up to 4 stocks; Valuation, Price Performance, Income
- [ ] **Stock Picks** — collapsible cards scored across Senate/House Stock Watcher, SEC EDGAR (Form 4/13F), Yahoo Finance, options flow
- [ ] **Research Reports** — long-form cards tagged by type (Supply Chain / Fundamentals / Inst. Flow)

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

### 2a — Disruption Ingestion

- [ ] Integrate supply chain data source (worldmonitor-osint or equivalent)
- [ ] Define disruption event schema (type, region, affected sectors, severity, date)
- [ ] Store events in `supply_chain_events` table via `db.py`
- [ ] Automated refresh on app startup (or on demand)

### 2b — Sector Mapping

- [ ] Map disruption events → affected GICS sectors and industries
- [ ] Map disruption events → potential beneficiary sectors (the "gap fillers")
- [ ] Configurable mapping table in `screener_config.py`

### 2c — Thematic Scan Mode

- [ ] New scan mode: `run_thematic` — filters universe to disruption-relevant sectors
- [ ] Supply chain signal score layered on top of fundamental score
- [ ] Output: ranked list of gap-filler candidates with disruption context

### 2d — App Integration

- [ ] Supply Chain Events view populated from `supply_chain_events` table
- [ ] Thematic scan wired through app
- [ ] Results annotated with which disruption event triggered inclusion

**Exit criteria:** Given a real supply chain event (e.g. port closure, sanctions), StackScreener
automatically surfaces a ranked list of companies positioned to benefit.

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
