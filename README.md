# StackScreener

A thematic, supply-chain-aware stock screener built from scratch on Python 3.14.2.

StackScreener detects geopolitical supply chain disruptions, maps them to affected industries,
runs fundamental screening against that universe, and surfaces the companies best positioned
to fill the gap — before the market catches on.

---

## What It Does

When a supply chain disruption hits (port blockage, sanctions, factory shutdown), capital
rotates toward gap-filler companies. StackScreener automates that process:

```
Disruption detected → Affected sectors identified → Fundamentals screened → Ranked output
```

Signal layers in the composite score:

| Layer | Source | Status |
|---|---|---|
| **EV/Revenue, P/E, EV/EBITDA, Margin, PEG, D/E** | yfinance fundamentals | ✅ Live |
| **Supply chain signal** | Curated event → sector mapping (Tier 2) | ✅ Live |
| **EDGAR geographic revenue** | SEC XBRL — China/US/Europe exposure + 10-K risk flags | ✅ Live |
| **News aggregation** | WSJ/MS/MF podcasts (Whisper) + Yahoo Finance + AP + CNBC + MarketWatch + NewsAPI + GDELT | ✅ Live |
| **Congressional trades** | Senate/House Stock Watcher (free APIs) | ✅ Live |
| **LLM extraction** | Qwen2.5-7B→32B + TurboQuant 4-bit — news/8-K/10-K parsing | ✅ 3/3 validated (7B) |
| **LLM job queue** | SQLite-backed queue — serialises LLM jobs, prevents VRAM deadlock | ✅ Live |
| **Local filing cache** | Raw 10-K/8-K text saved to `src/filings/` for offline validation | ✅ Live |
| **8-K material events** | EDGAR 8-K — fire/flood/recall/cyber keyword scanner | ✅ Live |
| **SEC insider trades** | EDGAR Form 4 — insider buy/sell signals | ✅ Live |
| **SEC Form 13F** | Institutional holdings — 14 major institutions, position change detection | ✅ Live |
| **Options flow** | yfinance unusual call/put volume (>3× open interest) | ✅ Live |
| **USDA crop conditions** | NASS weekly Good+Excellent % → upstream stress signals (free key) | ✅ Live |
| **EIA petroleum inventory** | Weekly crude/gasoline stock surprise vs. 5-week avg (free key) | ✅ Live |
| **AIS chokepoints** | aisstream.io vessel counts at 10 global chokepoints (free key) | ✅ Live |
| **Panama Canal draft** | ACP draft restriction scrape → canal congestion signal | ✅ Live |

---

## Architecture — Four Projects

StackScreener is structured as four independent projects sharing a common core.

| Project | Entry Point | Status |
|---|---|---|
| **P1 — Data Scraper** | `src/scraper_app.py` | ✅ TUI live |
| **P2 — Database & Server** | `src/db_app.py` | ✅ TUI live |
| **P3 — Bloomberg TUI** | `src/app.py` | ✅ Active — main user interface |
| **P4 — Web Server & Site** | `web/` | Planned after P2 REST API is stable |

See [`ROADMAP.md`](ROADMAP.md) for per-project status tables and enhancement backlogs.

---

## TUI Applications

### Bloomberg TUI — `python src/app.py`

Main user interface. Three sidebar sections:

| Section | What's Here |
|---|---|
| **Home** | DB stats + heatmap (tiles by % change, click → quote modal) |
| **Research** | Screener · Calendar · Stock Comparison · Stock Picks · Research Reports · News |
| **Logistics** | Active supply chain events + ASCII world map with event markers |

**Stock Quote Modal** — press Enter on any Screener row or "Open Quote →" in Stock Picks:
- **Overview** — 40+ fundamental fields
- **Signals** — all source signals with scores
- **History** — last 365 days of price history
- **News** — articles tagged to this ticker
- **Filings** — cached 10-K/8-K text files; click a row to preview the first 3,000 characters

Default login: **admin / admin** (forced password change on first launch).

---

### Data Scraper TUI — `python src/scraper_app.py`

P1 pipeline control panel. Left sidebar has one button per data source. Right panel has three tabs:

| Tab | What's Here |
|---|---|
| **Logs** | Live stdout/stderr stream from the last triggered command |
| **Queue** | LLM job queue — pending/running/done/failed counts + job list, auto-refreshes every 5s |
| **Sources** | API key manager — press Enter on any row to update a key |

**LLM Worker toggle** — Start/Stop button that runs `llm.py --worker` as a background subprocess, draining the job queue one job at a time (prevents VRAM deadlock from parallel LLM calls).

Pipeline buttons (each triggers the corresponding CLI command):

| Button | Command |
|---|---|
| Enrich Fundamentals | `enricher.py` |
| EDGAR CIKs | `edgar.py --seed-ciks` |
| EDGAR XBRL Facts | `edgar.py --fetch-facts --limit 100` |
| EDGAR 10-K Text | `edgar.py --fetch-filings --limit 50` |
| EDGAR 8-K Events | `edgar.py --fetch-8k --limit 100` |
| Form 4 Insider Trades | `inst_flow.py --form4` |
| Form 13F Holdings | `inst_flow.py --form13f` |
| Options Flow | `inst_flow.py --options` |
| News — All Sources | `news.py --all` |
| News — Classify | `news.py --classify` (enqueues LLM jobs) |
| USDA Crop Conditions | `commodities.py --usda-crops` |
| EIA Petroleum | `commodities.py --eia-petroleum` |
| AIS Chokepoints | `logistics.py --chokepoints` |
| Panama Canal | `logistics.py --panama` |
| Supply Chain Seed | `supply_chain.py --seed-tier2` |

**Setting API keys via Sources tab:** run `scraper_app.py`, click Sources tab, press Enter on the row for the provider, paste the key.

Or set from CLI:
```bash
python -c "import sys; sys.path.insert(0,'src'); import db; db.init_db(); db.set_api_key(1, 'PROVIDER', 'YOUR_KEY')"
```

Providers: `newsapi`, `aisstream`, `usda`, `eia`

---

### Database TUI — `python src/db_app.py`

P2 database browser. Three tabs:

| Tab | What's Here |
|---|---|
| **Browser** | Table list (left) + row viewer (right); PgUp/PgDn to page through rows |
| **SQL Shell** | Type any SELECT query, press Enter; ↑/↓ for history |
| **Stats** | Row counts per table, DB file size, full index list |

---

## Setup

> Requires Python 3.14.2. Some dependencies (numpy, pandas) must be compiled from source
> on Python 3.14. On Windows, use the **x64 Native Tools Command Prompt for VS 2022**.

```bash
# Create and activate venv
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt
pip install pandas-ta --no-deps   # must be --no-deps (no numba on 3.14)
```

---

## Quick Start

```bash
# 1 — Initialize DB schema + default admin user
python src/seeder.py --schema-only

# 2 — Seed full NYSE/NASDAQ universe (~6,900 tickers)
python src/seeder.py

# 3 — Enrich fundamentals
python src/enricher.py
python src/enricher.py --limit 50   # test run — 50 stocks only

# 4 — Run a scan
python src/screener_run.py                            # full NSR scan
python src/screener_run.py --mode thematic            # supply-chain filtered
python src/screener_run.py --limit 500 --top 25       # quick test run

# 5 — Launch the Bloomberg TUI
python src/app.py
```

---

## Data Pipeline — CLI Reference

### EDGAR

```bash
python src/edgar.py --seed-ciks                  # map tickers → CIKs (run once)
python src/edgar.py --fetch-facts                # XBRL geographic revenue + customer concentration
python src/edgar.py --fetch-facts --limit 100
python src/edgar.py --fetch-filings --limit 100  # 10-K risk flags + customer mentions
python src/edgar.py --fetch-8k                   # 8-K material event scanner
python src/edgar.py --fetch-8k --limit 100
python src/edgar.py --china-exposure 0.15        # list stocks with >15% China revenue
```

10-K and 8-K filing text is cached to `src/filings/10k/` and `src/filings/8k/` on first fetch.
Re-runs read from cache. Files are named `{ticker}_{cik}_{accession}.txt` and can be used
for offline validation (e.g. Gemini batch review against the same source documents).

### News

```bash
python src/news.py --ap                          # AP News RSS
python src/news.py --cnbc                        # CNBC RSS
python src/news.py --marketwatch                 # MarketWatch RSS
python src/news.py --reuters                     # Reuters via NewsAPI
python src/news.py --newsapi "supply chain"      # NewsAPI keyword search
python src/news.py --gdelt supply chain fire     # GDELT event search
python src/news.py --podcasts                    # WSJ / Morgan Stanley / Motley Fool podcasts
python src/news.py --watchlist                   # Yahoo Finance for all watchlist tickers
python src/news.py --all                         # all free sources
python src/news.py --classify                    # enqueue LLM classify jobs for unprocessed articles
```

### Institutional Flow

```bash
python src/inst_flow.py --congressional          # Senate + House trades
python src/inst_flow.py --form4                  # EDGAR Form 4 insider trades
python src/inst_flow.py --form4 --limit 200 --days 90
python src/inst_flow.py --form13f                # EDGAR Form 13F institutional holdings
python src/inst_flow.py --options                # yfinance unusual options volume
python src/inst_flow.py --options --tickers AAPL MSFT
```

### Commodities & Logistics

```bash
python src/commodities.py --usda-crops           # USDA NASS crop condition signals (requires key)
python src/commodities.py --eia-petroleum        # EIA weekly petroleum inventory (requires key)

python src/logistics.py --chokepoints            # AIS vessel counts at 10 global chokepoints (requires key)
python src/logistics.py --panama                 # Panama Canal draft restriction scrape
```

### LLM Pipeline

```bash
python src/llm.py --quantize                     # download + quantize Qwen2.5-7B (run once)
python src/llm.py --test                         # run 3-task validation suite
python src/llm.py --worker                       # drain job queue (loops until empty or Ctrl-C)
python src/llm.py --worker-once                  # process one pending job then exit
```

The worker processes one job at a time to prevent VRAM deadlock on 8GB GPUs.
Jobs are enqueued automatically by `news.py --classify` and `edgar.py --fetch-8k`
(on HIGH/CRITICAL severity hits).

### Supply Chain

```bash
python src/supply_chain.py --seed-tier2          # seed 9 curated supply chain scenarios
python src/supply_chain.py --list-events         # list all active events
python src/supply_chain.py --candidates 1        # sector-match candidates for event ID 1
```

---

## API Keys

All keys stored encrypted in the DB (never in files or env vars).

| Provider | Required For | Get Key |
|---|---|---|
| `newsapi` | Reuters + keyword news search | newsapi.org (free tier) |
| `aisstream` | AIS vessel tracking at chokepoints | aisstream.io (free) |
| `usda` | USDA NASS crop condition reports | quickstats.nass.usda.gov/api (free) |
| `eia` | EIA petroleum inventory reports | eia.gov/opendata (free) |

Set any key:
```bash
python -c "import sys; sys.path.insert(0,'src'); import db; db.init_db(); db.set_api_key(1, 'PROVIDER', 'YOUR_KEY')"
```

Or use the **Sources tab** in `scraper_app.py`.

---

## Project Status

| Component | Status |
|---|---|
| Shared core — DB, scoring engine, scan runner | ✅ Complete |
| P1 — Enricher, EDGAR, news, supply chain, congressional trades | ✅ Complete |
| P1 — LLM extraction pipeline — 3/3 tasks validated on Qwen2.5-7B TurboQuant 4-bit | ✅ Complete |
| P1 — LLM job queue (SQLite-backed, serialised worker, enqueue from news + 8-K) | ✅ Complete |
| P1 — Local filing cache (`src/filings/10k/` + `src/filings/8k/`) | ✅ Complete |
| P1 — EDGAR 8-K material event scanner (fire/flood/recall/cyber) | ✅ Complete |
| P1 — LLM news classifier → job queue → supply_chain_events promotion | ✅ Complete |
| P1 — Tier 2 seeds expanded (9 events: +consumer staples + labor strike + industrial REIT) | ✅ Complete |
| P1 — SEC EDGAR Form 4 insider trades | ✅ Complete |
| P1 — Form 13F institutional holdings (14 institutions, position diff) | ✅ Complete |
| P1 — Options flow (yfinance unusual call/put volume) | ✅ Complete |
| P1 — USDA crop conditions + EIA petroleum (upstream commodity signals) | ✅ Complete |
| P1 — AIS chokepoint monitoring + Panama Canal draft (midstream logistics) | ✅ Complete |
| P1 — Data Scraper TUI (`scraper_app.py`) — pipeline buttons, log tail, queue, sources | ✅ Complete |
| P2 — Database TUI (`db_app.py`) — table browser, SQL shell, DB stats | ✅ Complete |
| P3 — Screener, Calendar, Comparison, Picks, Reports, News tabs | ✅ Complete |
| P3 — Stock Quote Modal — Overview, Signals, History, News, Filings tabs | ✅ Complete |
| P3 — Home heatmap (tiles by % change, sized by market cap, click → quote modal) | ✅ Complete |
| P3 — Logistics world map (ASCII equirectangular + coloured event markers) | ✅ Complete |
| P1 — WSJ newspaper PDF ingestion | 🔲 Blocked — PDF is scanned images; needs OCR |
| P2 — REST API server | 🔲 Planned |
| P4 — Web server + React frontend | 🔲 Planned |

---

## Repo Structure

```
StackScreener/
├── src/
│   ├── — Shared Core —
│   ├── screener_config.py      ← all constants, weights, thresholds
│   ├── db.py                   ← SQLite layer (18 tables, 9 indexes)
│   ├── crypto.py               ← Fernet encryption + password hashing
│   ├── seeder.py               ← DB init + NYSE/NASDAQ universe fetch
│   ├── screener.py             ← scoring engine
│   ├── screener_run.py         ← CLI scan runner
│   ├── — P1: Data Scraper —
│   ├── enricher.py             ← fundamentals worker + IPO calendar
│   ├── supply_chain.py         ← Tier 2 events + Tier 1 sector matching
│   ├── edgar.py                ← SEC EDGAR XBRL + 10-K/8-K pipeline + filing cache
│   ├── inst_flow.py            ← congressional trades + Form 4/13F + options flow
│   ├── news.py                 ← podcasts + Yahoo Finance + AP/CNBC/MW/NewsAPI/GDELT
│   ├── llm.py                  ← LLM pipeline — TurboQuant Qwen2.5 + job queue worker
│   ├── commodities.py          ← USDA crop conditions + EIA petroleum inventory
│   ├── logistics.py            ← AIS chokepoints + Panama Canal draft
│   ├── scraper_app.py          ← P1 Data Scraper TUI
│   ├── — P2: DB & Server —
│   ├── db_app.py               ← P2 Database TUI
│   ├── — P3: Bloomberg TUI —
│   └── app.py                  ← Bloomberg TUI (login, Research, Logistics)
├── src/filings/
│   ├── 10k/                    ← cached 10-K filing text ({ticker}_{cik}_{accession}.txt)
│   └── 8k/                     ← cached 8-K filing text
├── StackScreenerCD/            ← P4 web prototype (React/JSX reference)
├── sql_tables/                 ← canonical SQL table definitions
├── Mock_up/                    ← UI mockups + original HTML prototype
├── CONTEXT.md                  ← full project context
├── CLAUDE.md                   ← coding conventions
├── ROADMAP.md                  ← 4-project roadmap with backlogs
├── DATABASE.md                 ← full schema map
└── requirements.txt
```

---

## Tech Stack

| Layer | Tools |
|---|---|
| Language | Python 3.14.2 |
| Data | yfinance, yahooquery, openai-whisper, pypdf |
| Database | SQLite — 18 tables, 9 indexes, all access via `db.py` |
| Encryption | cryptography (Fernet) + keyring (OS keyring) |
| Terminal UI | Textual 8.x |
| PDF reports | fpdf2 *(P3 planned)* |
| SEC EDGAR | requests (XBRL JSON API + archives, no key required) |
| FX conversion | CurrencyConverter |
| LLM | Qwen2.5-7B/32B-Instruct + TurboQuant 4-bit (cksac/turboquant-model) |
| Web prototype | React 18 + D3 (JSX, no build step) |

---

## License

MIT
