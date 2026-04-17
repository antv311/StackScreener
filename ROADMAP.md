# StackScreener — Development Roadmap

**Current Status:** Starting over. Environment needs to be rebuilt from scratch.
**Last updated:** April 2026

---

## Guiding Principle

Build the desktop app first. Validate the scoring engine and supply chain logic locally before
adding the complexity of a web server, authentication, and deployment. A working CLI/TUI app
is a real product. A half-finished web app is a liability.

---

## Phase 0 — Environment & Foundation 🔄 REDO

Get a clean, working Python 3.14 environment with all dependencies resolved.

- [ ] Create `venv_ss` on Python 3.14.2
- [ ] Compile C extensions from source (numpy, pandas, matplotlib, psutil)
- [ ] Install pure-Python deps via `requirements.txt`
- [ ] Verify `pandas-ta` installed with `--no-deps` (no numba)
- [ ] Confirm `CurrencyConverter` in place of `forex-python`
- [ ] Confirm `fpdf2` migration complete in `pdf_generator.py`
- [ ] Apply all pandas 2.x compatibility fixes (`.ffill()`, `.bfill()`)
- [ ] Apply all yahooquery Timestamp / `periodType` fixes
- [ ] Move all constants to `screener_config.py`
- [ ] Add `DEBUG_MODE = False` to `screener_config.py`
- [ ] Wire `db.py` SQLite layer into scan flow
- [ ] Confirm a full scan runs end-to-end without errors
- [ ] Initialize git repo and push to GitHub

**Exit criteria:** `python screener_run.py` completes a full scan, saves to DB, outputs CSV + PDF.

---

## Phase 1 — Desktop App (Textual TUI)

Turn the screener into a usable standalone desktop application matching the agreed UI mockup.

### 1a — Core App Shell

- [ ] Create `app.py` as the Textual TUI entry point
- [ ] Three-section sidebar: Home / Research / Logistics
- [ ] Config management: load/save user settings (scan mode, market, thresholds)
- [ ] Graceful error handling and user-friendly error messages

### 1b — Home Screen

- [ ] Full-width market heatmap (tiles color-coded by % change, sized by market cap)
- [ ] Index selector at bottom: S&P 500 / DOW / Russell 1000 / Recommended / All

### 1c — Research Screen (5 sub-tabs)

- [ ] **Screener** — filterable/sortable table; filters: Exchange, Sector, Market Cap, P/E, Signal
- [ ] **Calendar** — weekly grid with color-coded event chips (Earnings / Splits / IPOs / Economic)
- [ ] **Stock Comparison** — side-by-side up to 4 stocks; Valuation, Price Performance, Income
- [ ] **Stock Picks** — collapsible cards scored across Unusual Whales, Quiver Quant, Yahoo, Motley Fool
- [ ] **Research Reports** — long-form cards tagged by type (Supply Chain / Fundamentals / Inst. Flow)

### 1d — Logistics Screen

- [ ] World map with pulsing pins for active supply chain disruptions (color = severity)
- [ ] Click pin → filter table to that event
- [ ] Table: Region/Event | Impacted Companies | Cannot Provide | Will Redirect To | Severity

### 1e — Watchlist Management

- [ ] Add / remove symbols from watchlist via app
- [ ] View watchlist with latest scores and prices
- [ ] Import watchlist from CSV
- [ ] Persist watchlist to `db.py`

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

Layer in smart money signals to validate or strengthen supply chain picks.

- [ ] Integrate **Quiver Quant API** (congressional trades, lobbying, gov contracts)
- [ ] Integrate **Unusual Whales API** (dark pool prints, options flow, institutional activity)
- [ ] Add flow signal scores to `stock_financials` in DB
- [ ] Incorporate flow signals into final ranking (configurable weight in `screener_config.py`)
- [ ] Confluence view: supply chain signal + institutional flow + fundamentals all aligned

**Exit criteria:** A scan result shows which supply chain picks also have institutional money
flowing in, with a combined score.

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
- [ ] User authentication
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
- Quiver Quant and Unusual Whales require API keys — budget/access TBD
- Ubuntu deployment environment TBD (VPS, home server, cloud?)

---

## Dependencies Reference

| Package | Purpose | Notes |
|---|---|---|
| `yfinance` | Price + fundamentals | Primary data source |
| `yahooquery` | Detailed financials | Supplement to yfinance |
| `pandas-ta` | Technical indicators | Install with `--no-deps` |
| `fpdf2` | PDF report generation | Replaced old fpdf |
| `CurrencyConverter` | FX conversion | Replaced forex-python |
| `textual` | Terminal UI | Phases 1–4 |
| `requests` | HTTP fetches | Web data, news |
| `sqlite3` | DB (stdlib) | No ORM needed |
| `numpy` | Numerics | Compile from source |
| `pandas` | DataFrames | Compile from source |
| `matplotlib` | Charts | Compile from source |
| `psutil` | System info | Compile from source |
