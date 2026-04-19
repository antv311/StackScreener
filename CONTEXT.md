# StackScreener — Project Context
> Read this file at the start of every Claude Code session to get fully up to speed.

---

## What Is StackScreener?

StackScreener is a thematic, supply-chain-aware stock and ETF screener built from scratch on
Python 3.14.2. It ingests geopolitical supply chain signals, fundamental scoring data,
congressional trading disclosures, and SEC insider/institutional filings to surface companies
positioned to benefit from supply chain disruptions.

**Owner:** Tony (antv311)
**Repo:** https://github.com/antv311/StackScreener
**Stack:** Python 3.14.2, SQLite, yfinance, yahooquery, pandas-ta, fpdf2, CurrencyConverter, Textual, cryptography, keyring

---

## Core Concept

When a supply chain disruption happens (port blockage, sanctions, factory shutdown, geopolitical
event), capital flows toward companies positioned to fill the gap. StackScreener detects those
disruptions, maps affected industries and sectors, runs fundamental screening against that
universe, and surfaces the best-positioned companies to benefit.

**Signal flow:**
```
Disruption detected → Affected sectors identified → Fundamentals screened → Ranked output
```

---

## UI Design (Decided — April 2026)

The app has three top-level sections in a left sidebar: **Home**, **Research**, **Logistics**.
See UI mockup screenshots in `Mock_up/` for reference. The HTML prototype is at
`Mock_up/Prototype/stackscreener_full_ui_prototype.html`.

### Home
- Full-width market heatmap (tiles color-coded by % change, sized by market cap)
- Index selector at bottom: S&P 500 / DOW / Russell 1000 / Recommended / All

### Research (5 sub-tabs across the top bar)

1. **Screener** — filterable/sortable table. Filter dropdowns: Exchange, Sector, Market Cap,
   P/E, Signal (All / Supply Chain Picks / Congress Buys / Dark Pool Alert).
   Columns: Rank, Ticker, Company, Sector, Market Cap, P/E, Price, Change %, Volume,
   Score (progress bar + number).

2. **Calendar** — weekly calendar view with color-coded event chips
   (green=Earnings, blue=Splits, yellow=IPOs). Filter tabs: All / Earnings / Splits / IPOs /
   Economic. Detail table below the calendar grid.

3. **Stock Comparison** — side-by-side comparison of up to 4 stocks. Sections: Valuation,
   Price Performance, Income Statement. Highs highlighted green ▲, lows red ▼.

4. **Stock Picks** — top picks scored across congressional trades, SEC insider filings,
   Yahoo Finance, and options flow. Each pick is a collapsible card:
   [Logo] [Ticker] [Company Name] [Price] [Composite Score]
   Expanded: per-source breakdown with reason text and sub-score.

5. **Research Reports** — long-form research cards tagged by type
   (Supply Chain / Fundamentals / Inst. Flow). Shows title, summary, and date.

### Logistics
- World map with animated pulsing pins for active supply chain disruptions.
  Pin color = severity (red=CRITICAL, orange=HIGH, yellow=MEDIUM, blue=LOW).
- Clicking a pin filters the table below to that event.
- Table columns: Region/Event | Impacted Companies | Cannot Provide | Will Redirect To | Severity

---

## Architecture

```
Layer 1 — Data Sources
  yfinance                       → price, fundamentals (primary)
  yahooquery                     → detailed financials (supplement)
  Yahoo Finance Screener API     → full NYSE/NASDAQ universe enumeration
  Yahoo Finance Calendar API     → upcoming IPOs (daily check)
  Senate Stock Watcher API       → congressional trades (Senate) — free, no key   [PLANNED]
  House Stock Watcher API        → congressional trades (House) — free, no key     [PLANNED]
  SEC EDGAR (Form 4)             → insider trades — free, public                   [PLANNED]
  SEC EDGAR (Form 13F)           → institutional holdings — free, public           [PLANNED]
  yfinance options chain         → basic options flow — free                       [PLANNED]
  worldmonitor-osint / other     → geopolitical / supply chain disruption signals  [PLANNED]

Layer 2 — Database
  SQLite via stackscreener.db    → 13 tables + 2 covering indexes (see schema below)
  API keys encrypted via Fernet, master key stored in OS keyring
  db.py helpers: get_pending_enrichment, get_pending_history, ipo_checked_today,
                 mark_delisted, get_active_stocks (all SQL lives in db.py only)

Layer 3 — Data Pipeline
  seeder.py                      → one-time schema init + NYSE/NASDAQ universe seed
                                   6,924 stocks seeded (NMS/NGM/NCM/NYQ)
  enricher.py                    → rate-limited background worker; fills fundamentals,
                                   daily IPO calendar check via Yahoo Finance;
                                   5y price history for all listed stocks complete

Layer 4 — Scoring Engine
  screener.py                    → EV/R, PE, EV/EBITDA, profit margin, PEG,
                                   debt/equity, CFO ratio, Altman Z-score        [NEXT]
  screener_run.py                → scan orchestration + CLI entry point          [NEXT]

Layer 5 — Output (Phase 1: Desktop App)
  app.py (Textual TUI)           → interactive terminal app matching the UI design above  [PLANNED]
  pdf_generator.py               → CSV + PDF reports to Results/ directory                [PLANNED]

Layer 6 — Output (Phase 5: Web App)
  FastAPI backend                → [FUTURE]
  REST API                       → [FUTURE]
```

---

## Project File Structure

```
StackScreener/
├── src/
│   ├── screener_config.py          ← ALL constants, weights, thresholds, status values, DEBUG_MODE
│   ├── db.py                       ← SQLite layer — ALL DB access goes here only
│   ├── crypto.py                   ← Fernet encryption (OS keyring) + password hashing
│   ├── seeder.py                   ← one-time schema init + NYSE/NASDAQ universe fetch
│   ├── enricher.py                 ← background fundamentals worker + daily IPO calendar check
│   ├── screener.py                 ← core scoring engine                        [NEXT]
│   ├── screener_run.py             ← scan runner / CLI entry point              [NEXT]
│   ├── screener_post_processing.py ← normalized scoring output                  [PLANNED]
│   ├── supply_chain.py             ← supply chain signal ingestion + sector mapping [PLANNED]
│   ├── app.py                      ← desktop TUI entry point (Textual)          [PLANNED]
│   ├── pdf_generator.py            ← PDF reports (fpdf2)                        [PLANNED]
│   ├── mailer.py                   ← email delivery                             [PLANNED]
│   └── Results/                    ← scan output (gitignored)
├── sql_tables/                     ← canonical SQL table definitions (reference)
│   ├── users.sql
│   ├── watchlists.sql
│   ├── stocks.sql
│   ├── api_keys.sql
│   ├── portfolio.sql
│   ├── scans.sql
│   ├── scan_results.sql
│   ├── supply_chain_events.sql
│   ├── event_stocks.sql
│   ├── calendar_events.sql
│   ├── source_signals.sql
│   └── research_reports.sql
├── Mock_up/
│   ├── *.jpg                       ← UI mockup screenshots
│   └── Prototype/
│       └── stackscreener_full_ui_prototype.html
├── CONTEXT.md                      ← this file
├── CLAUDE.md                       ← coding conventions for Claude Code
├── ROADMAP.md                      ← phased development plan
├── DATABASE.md                     ← full schema map (all 12 tables, FKs, query patterns)
├── requirements.txt
└── README.md
```

---

## Database Schema

All primary keys follow the `tablename_uid` convention. All tables live in `stackscreener.db`
and are created by `db.init_db()`. All access goes through `db.py` only.

| Table | Purpose |
|---|---|
| `users` | User accounts — password hash + salt, admin flag, force-change flag, totp_secret (2FA prep) |
| `watchlists` | Named watchlists, attached to a user via `user_uid` |
| `stocks` | All tracked symbols — descriptive, fundamental, technical fields + `last_enriched_at` |
| `api_keys` | Fernet-encrypted API credentials per user/provider |
| `portfolio` | User holdings (Plaid-ready: quantity, avg_cost, plaid_account_id) |
| `scans` | Scan run metadata (mode, status, counts, timestamps) |
| `scan_results` | Per-symbol scored results for each scan run |
| `supply_chain_events` | Active disruption events with lat/lon, severity, affected/beneficiary sectors |
| `event_stocks` | Junction: which stocks are impacted or benefit from each event |
| `calendar_events` | Earnings, splits, IPOs, economic events — upcoming IPOs pre-seeded here |
| `source_signals` | Per-stock signals from congressional trades, SEC filings, Yahoo, options flow |
| `research_reports` | Long-form research content tagged by type |
| `price_history` | Daily OHLCV bars + dividends + split factors per stock |

Watchlist query pattern:
```sql
SELECT * FROM stocks WHERE watchlist_uid = ? AND is_watched = 1
```

Enrichment staleness check:
```sql
SELECT * FROM stocks WHERE last_enriched_at IS NULL
   OR last_enriched_at < datetime('now', '-1 days')
```

---

## Security — API Keys & Passwords

**API keys** are stored encrypted in the `api_keys` table. Encryption uses Fernet symmetric
encryption (`cryptography` library). The master key is stored in the OS keyring:
- Windows → Windows Credential Manager
- macOS → macOS Keychain
- Linux → SecretService (GNOME Keyring / KWallet)

`db.set_api_key()` / `db.get_api_key()` handle encrypt/decrypt transparently.
Never call `crypto.encrypt()` / `crypto.decrypt()` directly from outside `db.py`.

**Passwords** are hashed with PBKDF2-HMAC-SHA256 (260,000 iterations, random per-user salt).
Default admin account: `admin / admin` — forced to change on first login.

---

## Python 3.14 Compatibility Notes

| Package | Issue | Resolution |
|---|---|---|
| `numba` | Hard-capped at Python <3.14 | Cannot use — install `pandas-ta` with `--no-deps` |
| `forex-python` | Unmaintained, broken | Replaced with `CurrencyConverter` |
| `fpdf` / `HTMLMixin` | HTMLMixin removed in fpdf2 | Use fpdf2 API only |
| `pyPdf` | Dead since 2010 | Replaced with `pypdf` |
| `talib` | C extension, fights 3.14 | Replaced with `pandas-ta` |
| `pandas` `.fillna(method=)` | Deprecated in pandas 2.x | Use `.ffill()` / `.bfill()` |

`pandas-ta` must be installed with `--no-deps` — no exceptions.

---

## Build Environment (Windows)

- Python 3.14.2 in a venv called `venv` (located at `StackScreener/venv/`)
- C extensions compiled from source via **x64 Native Tools Command Prompt for VS 2022**
- Build prerequisites: `meson-python`, `meson`, `ninja`, `cython`, `pybind11`,
  `versioneer`, `setuptools_scm`, `pkgconfiglite` (via Chocolatey)
- Deployment target: Ubuntu

---

## Coding Style & Patterns

- Functional programming preferred — avoid sprawling class hierarchies
- All constants in `screener_config.py` — never hardcoded in logic files
- `DEBUG_MODE = False` in `screener_config.py` gates all debug output
- `frozenset` for constant set membership checks (e.g. `INT_FIELDS`)
- `match-case` over long `if-elif` chains
- `pd.concat()` over repeated `DataFrame.insert()` — avoids PerformanceWarning
- `dataclasses.fields()` for iterating model fields
- SQLite PK convention: `tablename_uid`
- All `shutil.move()` calls guarded with `os.path.exists()`
- yahooquery: Timestamp dict keys → strings; filter `periodType == '12M'` for annual data

---

## Key External Resources

- Senate Stock Watcher API: https://senatestockwatcher.com/api (free, no key)
- House Stock Watcher API: https://housestockwatcher.com/api (free, no key)
- SEC EDGAR full-text search: https://efts.sec.gov/LATEST/search-index (free)
- SEC EDGAR filings API: https://data.sec.gov/submissions/ (free)
- Supply chain signals: https://github.com/worldmonitor/worldmonitor-osint (planned)
