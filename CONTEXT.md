# StackScreener — Project Context
> Read this file at the start of every Claude Code session to get fully up to speed.
> After reading this, read `todonext.md` for the detailed task queue and active diagnostics.

---

## What Is StackScreener?

StackScreener is a thematic, supply-chain-aware stock and ETF screener built from scratch on
Python 3.14.2. It ingests geopolitical supply chain signals, fundamental scoring data,
congressional trading disclosures, and SEC insider/institutional filings to surface companies
positioned to benefit from supply chain disruptions.

**Owner:** Tony (antv311)
**Repo:** https://github.com/antv311/StackScreener
**Stack:** Python 3.14.2, SQLite, yfinance, yahooquery, pandas-ta, CurrencyConverter, Textual, cryptography, keyring

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

### Home ✅ Built
- Stats bar: active stock count, enriched count, SC event count, last scan summary
- Filter buttons: All / Large Cap ($10B+) / Mega Cap ($200B+) / S&P ≈500 (top 500 by mcap) / Watchlist
- 8-column CSS grid of `HeatmapTile` widgets — background color from dark green → dark red by `change_pct`
- Each tile: ticker + % change + market cap; click/Enter → `StockQuoteModal`

### Research (6 sub-tabs across the top bar)

1. **Screener** — filterable/sortable table. Filter dropdowns: Exchange, Sector, Market Cap,
   P/E, Signal (All / Supply Chain Picks / Congress Buys). Press **Enter** on any row to open
   the Stock Quote Modal.

2. **Calendar** — weekly calendar view with color-coded event chips
   (green=Earnings, blue=Splits, yellow=IPOs, teal=Ex-Dividend, purple=Dividend Pay). Filter tabs:
   All / Earnings / Splits / IPOs / Economic / Dividends. Detail table below the calendar grid.
   Dividend events auto-synced from `stocks` on tab mount via `sync_dividend_calendar_events()`.

3. **Stock Comparison** — side-by-side comparison of up to 4 stocks. Sections: Valuation,
   Price Performance, Income Statement. Highs highlighted green ▲, lows red ▼.

4. **Stock Picks** — top picks scored across congressional trades, SEC insider filings,
   Yahoo Finance, and options flow. Each pick is a collapsible card. "Open Quote →" button
   inside each expanded card opens the Stock Quote Modal.

5. **Research Reports** — long-form research cards tagged by type
   (Supply Chain / Fundamentals / Inst. Flow). Shows title, summary, and date.

6. **News** — filterable by source (WSJ Podcast, WSJ PDF, Morgan Stanley, Motley Fool,
   Yahoo Finance). Shows headline, source, date, ticker mention.

### Stock Quote Modal

Triggered from: Screener (Enter on row), Stock Picks ("Open Quote →" button), or the
sidebar ticker search bar (type ticker + Enter).
Press ESC or Q to close. All data from DB — no network calls on open.

- **Overview** — 40+ fields: valuation, margins, growth, risk/technicals, performance,
  ownership, DIVIDENDS section (yield, payout ratio, last dividend value, ex-date, pay date),
  plus EDGAR geographic revenue breakdown if available
- **Signals** — `source_signals` rows + supply chain event links for the stock
- **History** — last 365 days of OHLCV from `price_history`, dividend column
- **News** — recent `news_articles` for this stock
- **Filings** — list of cached 10-K/8-K `.txt` files from `src/filings/`; click to preview first 3,000 chars

### Logistics ✅ Built
- `WorldMap(Static)` widget: 74×18 equirectangular ASCII map, landmass in dim green `~`,
  coloured `●` markers at lat/lon for each active supply chain event, severity legend below
- Left sidebar: scrollable `EventListItem` list (severity badge + region + title); click to select
- Right panel: world map → event detail (title, region, type, severity, affected sectors) → company DataTable
- Company table columns: Role | Ticker | Sector | Cannot Provide | Will Redirect To | Confidence

---

## Architecture — Four Projects, One Core

StackScreener is structured as four independent projects sharing a common core.
See `ROADMAP.md` for full per-project status and backlogs.

```
┌─────────────────────────────┐   ┌─────────────────────────────┐
│  P1 — Data Scraper TUI      │   │  P2 — DB & Server TUI       │
│  scraper_app.py  ✅ Active  │   │  db_app.py  ✅ Active       │
│                             │   │                             │
│  enricher · edgar · news    │   │  db.py internals            │
│  supply_chain · inst_flow   │   │  FastAPI server [FUTURE]    │
│  commodities · logistics    │   │                             │
│  llm · wsj_fetcher          │   │                             │
└─────────────┬───────────────┘   └─────────────┬───────────────┘
              │                                 │
              ▼                                 ▼
     ┌────────────────────────────────────────────┐
     │               Shared Core                  │
     │  db.py · screener_config.py                │
     │  crypto.py · screener.py · screener_run.py │
     │  SQLite: 20 tables, 10 indexes              │
     └───────────────────┬────────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
┌──────────────────────┐     ┌──────────────────────────┐
│  P3 — Bloomberg TUI  │     │  P4 — Web Server & Site  │
│  app.py  ✅ Active   │     │  web/  [PLANNED P4]      │
│                      │     │                          │
│  Login · Screener    │     │  FastAPI · React UI      │
│  Calendar · Picks    │     │  REST API for friends    │
│  Comparison · News   │     │                          │
│  StockQuoteModal     │     │  StackScreenerCD/ has    │
│  Logistics · Settings│     │  the React prototype     │
└──────────────────────┘     └──────────────────────────┘
```

**Data sources (all free — no paid API keys required unless noted):**
```
yfinance / yahooquery         → price, fundamentals, IPO calendar, options chain
Senate + House Stock Watcher  → congressional trades (inst_flow.py — built)
SEC EDGAR XBRL                → geographic revenue, customer concentration (edgar.py — built)
SEC EDGAR 10-K text           → risk flags, customer % mentions (edgar.py — two-stage pipeline)
SEC EDGAR Form 4              → insider buy/sell filings (inst_flow.py — built)
SEC EDGAR Form 13F            → institutional holdings, 14 institutions (inst_flow.py — built)
SEC EDGAR 8-K                 → material events: fire/flood/recall/cyber (edgar.py — built)
yfinance options chain        → unusual call/put volume >3× OI (inst_flow.py — built)
WSJ/MS/MF podcasts (Whisper)  → transcript news signals (news.py — built)
WSJ PDF (wsj_fetcher.py)      → Gmail IMAP check → Chrome download → news.py ingest
AP News / CNBC / MarketWatch  → RSS article feeds (news.py — built)
NewsAPI.org (AP+Reuters+150k) → REST API, free tier (news.py — built; requires key)
GDELT Project                 → global event database, free (news.py — built)
USDA NASS crop conditions     → weekly G+E% per crop → crop_stress signals (commodities.py; requires free key)
EIA petroleum inventory       → weekly crude/gasoline surprise (commodities.py; requires free key)
FRED (St. Louis Fed)          → 16 commodity price series: BLS PPI fertilizers, Henry Hub natgas, EU natgas, copper/aluminum/nickel/zinc/tin/iron ore, palm oil/cocoa/coffee/sugar, lumber (commodities.py; requires free key)
AIS maritime chokepoints      → aisstream.io WebSocket, 10 chokepoints (logistics.py; requires free key)
Panama Canal Authority        → ACP draft restrictions scrape (logistics.py; public)
Qwen2.5-7B validated 3/3 / 32B (prod) + TurboQuant 4-bit → LLM extraction (llm.py — built)
```

**LLM stack decision (April 2026):** Qwen2.5 family selected unanimously. TurboQuant 4-bit
g=128 + Hadamard rotation. `src/llm.py` built and **validated 3/3** on Qwen2.5-7B-Instruct
(8GB RTX 3080). Model at `models/qwen2.5-7b-4bit/` (4.6GB). P40 + 32B is production target.
**VRAM rule: only one LLM process at a time** — two processes fill 8GB VRAM and deadlock.
Use `llm.py --worker --limit N` to bound a batch run. See `todonext.md` LLM section and
`READMETQ.md` for full details.

**Available cp314 wheels (pre-built, Windows amd64):**
- `torch-2.12.0a0+gitfafc7d6` — installed
- `xformers-0.0.35+6e9337ce` — memory-efficient attention, install before running LLM
- `tvdcn-1.1.0` — torchvision deformable convolutions
- `opencv_python-4.13.0.92` — computer vision (future use)

---

## Project File Structure

```
StackScreener/
├── src/
│   ├── — SHARED CORE —
│   ├── screener_config.py          ← ALL constants, weights, thresholds, status values, DEBUG_MODE
│   ├── db.py                       ← SQLite layer — ALL DB access goes here only (20 tables, 10 indexes)
│   ├── crypto.py                   ← Fernet encryption (OS keyring) + password hashing
│   ├── seeder.py                   ← one-time schema init + NYSE/NASDAQ universe fetch
│   ├── screener.py                 ← core scoring engine (8 components + SC/flow overlays)
│   ├── screener_run.py             ← scan runner / CLI (nsr/thematic/watchlist + CSV)
│   ├── — P1: DATA SCRAPER —
│   ├── enricher.py                 ← background fundamentals worker + daily IPO calendar check + dividend normalization
│   ├── supply_chain.py             ← Tier 2 curated seed (27 events, 134 links) + Tier 1 sector matching
│   ├── edgar.py                    ← SEC EDGAR: CIK seed + XBRL facts + two-stage 10-K pipeline + 8-K material events
│   ├── inst_flow.py                ← congressional trades + Form 4 insider trades + Form 13F + options flow
│   ├── news.py                     ← podcasts (WSJ/MS/MF RSS+Whisper) + WSJ PDF + Yahoo + AP + CNBC + MW + NewsAPI + GDELT + LLM classifier
│   ├── llm.py                      ← LLM extraction pipeline (TurboQuant Qwen2.5-7B→32B); --worker --limit N
│   ├── commodities.py              ← USDA crop conditions + EIA petroleum + FRED (16-series: fertilizers/natgas/metals/agri/lumber) → upstream commodity signals
│   ├── logistics.py                ← AIS chokepoints (aisstream.io) + Panama Canal draft → midstream signals
│   ├── wsj_fetcher.py              ← automated WSJ PDF downloader: Gmail IMAP + Chrome profile → src/News/pdfs/
│   ├── scraper_app.py              ← Data Scraper TUI — 21 pipeline buttons (incl. WSJ), log tail, Queue tab, Sources tab, Schedule tab
│   ├── — P2: DATABASE & SERVER —
│   ├── db_app.py                   ← Database & Server TUI — table browser, SQL shell, DB stats
│   ├── — P3: BLOOMBERG TUI —
│   ├── app.py                      ← Bloomberg TUI — login, sidebar ticker search, Research tabs, Home heatmap, Logistics world map
│   └── Results/                    ← scan output (gitignored)
├── src/filings/
│   ├── 10k/                        ← cached 10-K filing text ({ticker}_{cik}_{accession}.txt)
│   └── 8k/                         ← cached 8-K filing text
├── sql_tables/                     ← canonical SQL table definitions (reference only — schema lives in db.py)
│   ├── *.sql                       ← all 19 table definitions present
├── src/News/
│   ├── audio/                      ← temp MP3 storage (deleted after transcription, gitignored)
│   └── pdfs/                       ← WSJ newspaper PDFs (kept, gitignored)
├── StackScreenerCD/                ← P4 web prototype (React/JSX, Claude-designed reference UI)
│   ├── StackScreener Web UI.html
│   ├── atoms.jsx · shell.jsx · home.jsx
│   ├── research.jsx · logistics.jsx · settings.jsx
│   └── styles.css
├── Mock_up/                        ← TUI mockup screenshots + original HTML prototype
├── CONTEXT.md                      ← this file
├── CLAUDE.md                       ← coding conventions for Claude Code
├── ROADMAP.md                      ← 4-project roadmap with per-project backlogs
├── DATABASE.md                     ← full schema map (all 20 tables, FKs, query patterns)
├── tree.md                         ← annotated file tree with entry points
├── requirements.txt
└── README.md
```

---

## Database Schema

All primary keys follow the `tablename_uid` convention. All tables live in `stackscreener.db`
and are created by `db.init_db()`. All access goes through `db.py` only.
**20 tables total. 10 covering indexes.**

| Table | Purpose |
|---|---|
| `users` | User accounts — password hash + salt, admin flag, force-change flag, totp_secret (2FA prep) |
| `watchlists` | Named watchlists, attached to a user via `user_uid` |
| `stocks` | All tracked symbols — descriptive, fundamental, technical fields + dividend columns + `last_enriched_at` |
| `api_keys` | Fernet-encrypted API credentials per user/provider — includes url, display_name, connector_config, role |
| `portfolio` | User holdings (Plaid-ready: quantity, avg_cost, plaid_account_id) |
| `scans` | Scan run metadata (mode, status, counts, timestamps) |
| `scan_results` | Per-symbol scored results for each scan run |
| `supply_chain_events` | Active disruption events with lat/lon, severity, affected/beneficiary sectors |
| `event_stocks` | Junction: which stocks are impacted or benefit from each event |
| `calendar_events` | Earnings, splits, IPOs, economic events, ex_dividend, dividend_pay — upcoming IPOs pre-seeded |
| `source_signals` | Per-stock signals from congressional trades, SEC filings, Yahoo, options flow |
| `research_reports` | Long-form research content tagged by type |
| `price_history` | Daily OHLCV bars + dividends + split factors per stock |
| `edgar_facts` | XBRL geographic revenue + customer concentration + 10-K risk flags + llm_10k_entities per stock |
| `settings` | Per-user key/value preferences (theme, scan defaults, etc.) |
| `news_articles` | Headlines, full transcripts, WSJ PDF text — one row per article/episode |
| `llm_jobs` | Job queue for LLM work (classify_news / extract_10k / parse_8k); statuses: pending/running/done/failed/paused/cancelled |
| `newsapi_keywords` | Per-user keyword list for NewsAPI searches |
| `newsapi_sources` | NewsAPI source catalog (cached from API) |

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
- USDA NASS Quick Stats API: https://quickstats.nass.usda.gov/api (free key)
- EIA Open Data API: https://www.eia.gov/opendata/ (free key)
- aisstream.io WebSocket API: https://aisstream.io (free key — requires signup)
- Panama Canal Authority restrictions: https://www.pancanal.com/eng/op/aqRestricciones.html (public)
