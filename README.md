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
| **News aggregation** | WSJ/MS/MF podcasts (Whisper) + WSJ PDF + Yahoo Finance | ✅ Live |
| **Congressional trades** | Senate/House Stock Watcher (free APIs) | ✅ Live |
| **LLM extraction** | Qwen2.5-7B→32B + TurboQuant 4-bit — news/8-K/10-K parsing | ✅ 3/3 validated (7B) |
| **8-K material events** | EDGAR 8-K — fire/flood/recall/cyber keyword scanner | ✅ Live |
| **SEC insider trades** | EDGAR Form 4 — insider buy/sell signals | ✅ Live |
| **SEC Form 13F** | Institutional holdings — 14 major institutions, position change detection | ✅ Live |
| **Options flow** | yfinance unusual call/put volume (>3× open interest) | ✅ Live |

---

## Architecture — Four Projects

StackScreener is structured as four independent projects sharing a common core.

| Project | Entry Point | Status |
|---|---|---|
| **P1 — Data Scraper** | `src/scraper_app.py` | Core modules complete; TUI planned |
| **P2 — Database & Server** | `src/db_app.py` | DB layer complete; TUI + API planned |
| **P3 — Bloomberg TUI** | `src/app.py` | ✅ Active — main user interface |
| **P4 — Web Server & Site** | `web/` | Planned after P2 REST API is stable |

See [`ROADMAP.md`](ROADMAP.md) for per-project status tables and enhancement backlogs.

---

## Bloomberg TUI (Project 3)

Three-section desktop TUI built with [Textual](https://github.com/Textualize/textual):

| Section | What's Here |
|---|---|
| **Home** | DB stats + last scan summary (heatmap coming in P3 next) |
| **Research** | Screener · Calendar · Stock Comparison · Stock Picks · Research Reports · News |
| **Logistics** | Active supply chain events (world map coming in P3 next) |

**Stock Quote Modal** — press Enter on any Screener row or click "Open Quote →" in Stock Picks to open a full quote view: Overview (40+ fields), Signals, Price History, News. All data from the local DB — no network calls.

Mockup screenshots and an interactive HTML prototype are in [`Mock_up/`](Mock_up/).
Web prototype (React/JSX) is in [`StackScreenerCD/`](StackScreenerCD/).

---

## Tech Stack

| Layer | Tools |
|---|---|
| Language | Python 3.14.2 |
| Data | yfinance, yahooquery, openai-whisper, pypdf |
| Database | SQLite — 16 tables, 8 indexes, all access via `db.py` |
| Encryption | cryptography (Fernet) + keyring (OS keyring) |
| Terminal UI | Textual 8.x |
| PDF reports | fpdf2 *(P3 planned)* |
| SEC EDGAR | requests (XBRL JSON API, no key required) |
| FX conversion | CurrencyConverter |
| LLM | Qwen2.5-7B/32B-Instruct + TurboQuant 4-bit (cksac/turboquant-model) |
| Web prototype | React 18 + D3 (JSX, no build step) |

---

## Project Status

| Component | Status |
|---|---|
| Shared core — DB, scoring engine, scan runner | ✅ Complete |
| P1 — Enricher, EDGAR, news, supply chain, congressional trades | ✅ Core complete |
| P1 — LLM extraction pipeline — 3/3 tasks validated on Qwen2.5-7B TurboQuant 4-bit | ✅ Complete |
| P1 — EDGAR 8-K material event scanner (fire/flood/recall/cyber) | ✅ Complete |
| P1 — LLM news classifier → auto supply_chain_events promotion | ✅ Complete |
| P1 — Tier 2 seeds expanded (9 events: +consumer staples + labor strike + industrial REIT) | ✅ Complete |
| P1 — SEC EDGAR Form 4 insider trades | ✅ Complete |
| P1 — Form 13F institutional holdings (14 institutions, position diff) | ✅ Complete |
| P1 — Options flow (yfinance unusual call/put volume) | ✅ Complete |
| P1 — Data Scraper TUI (`scraper_app.py`) | 🔲 Planned |
| P2 — Database & Server TUI (`db_app.py`) | 🔲 Planned |
| P3 — Screener, Calendar, Comparison, Picks, Reports, News tabs | ✅ Complete |
| P3 — Stock Quote Modal (Enter on Screener / Picks) | ✅ Complete |
| P3 — Home heatmap | 🔲 Next |
| P3 — Logistics world map | 🔲 Planned |
| P4 — Web server + React frontend | 🔲 Planned |

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

Default login after seeding: **admin / admin** — you will be forced to change this on first launch.

---

## EDGAR Supply Chain Data

```bash
# Map all tickers to SEC CIKs (run once after seeding)
python src/edgar.py --seed-ciks

# Pull geographic revenue breakdown (China/US/Europe) for all stocks
python src/edgar.py --fetch-facts
python src/edgar.py --fetch-facts --limit 100   # test run

# Pull 10-K text: risk flags + customer % mentions
python src/edgar.py --fetch-filings --limit 100

# Find stocks with >15% China revenue exposure
python src/edgar.py --china-exposure 0.15
```

---

## Supply Chain Seeding

```bash
# Seed 6 curated supply chain scenarios (Taiwan Strait, Red Sea, etc.)
python src/supply_chain.py --seed-tier2

# List all active events
python src/supply_chain.py --list-events

# Show sector-match candidates for an event
python src/supply_chain.py --candidates 1
```

---

## Repo Structure

```
StackScreener/
├── src/
│   ├── — Shared Core —
│   ├── screener_config.py      ← all constants, weights, thresholds
│   ├── db.py                   ← SQLite layer (16 tables, 8 indexes)
│   ├── crypto.py               ← Fernet encryption + password hashing
│   ├── seeder.py               ← DB init + NYSE/NASDAQ universe fetch
│   ├── screener.py             ← scoring engine
│   ├── screener_run.py         ← CLI scan runner
│   ├── — P1: Data Scraper —
│   ├── enricher.py             ← fundamentals worker + IPO calendar
│   ├── supply_chain.py         ← Tier 2 events + Tier 1 sector matching
│   ├── edgar.py                ← SEC EDGAR XBRL + 10-K pipeline
│   ├── inst_flow.py            ← congressional trades + Form 4/13F
│   ├── news.py                 ← podcasts + WSJ PDF + Yahoo Finance
│   ├── llm.py                  ← LLM extraction pipeline (TurboQuant Qwen2.5)
│   ├── scraper_app.py          ← Data Scraper TUI [planned]
│   ├── — P2: DB & Server —
│   ├── db_app.py               ← Database & Server TUI [planned]
│   ├── — P3: Bloomberg TUI —
│   └── app.py                  ← Bloomberg TUI (login, Research, Logistics)
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

## License

MIT
