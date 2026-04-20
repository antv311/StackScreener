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
| **Congressional trades** | Senate/House Stock Watcher (free APIs) | ✅ Built — Phase 3 wiring |
| **SEC insider filings** | EDGAR Form 4 + 13F (free) | Planned Phase 3 |

---

## UI

Three-section desktop TUI built with [Textual](https://github.com/Textualize/textual):

| Section | What's Here |
|---|---|
| **Home** | Live database stats + last scan summary (heatmap in Phase 1b) |
| **Research** | Screener · Calendar · Stock Comparison · Stock Picks · Research Reports · News |
| **Logistics** | Active supply chain events table (interactive world map in Phase 1d) |

Mockup screenshots and an interactive HTML prototype are in [`Mock_up/`](Mock_up/).

---

## Tech Stack

| Layer | Tools |
|---|---|
| Language | Python 3.14.2 |
| Data | yfinance, yahooquery |
| Database | SQLite — 16 tables, all access via `db.py` |
| Encryption | cryptography (Fernet) + keyring (OS keyring) |
| Terminal UI | Textual 8.x |
| PDF reports | fpdf2 *(Phase 1f)* |
| SEC EDGAR | requests (XBRL JSON API, no key required) |
| FX conversion | CurrencyConverter |

---

## Project Status

**Phase 0, 1a, 1c, and most of Phase 2 complete.**

| Phase | Status | What it covers |
|---|---|---|
| Phase 0 — Foundation | ✅ Complete | DB (16 tables, 8 indexes), enricher, seeder, scoring engine, scan runner |
| Phase 1a — App Shell | ✅ Complete | Textual TUI, login, sidebar navigation, settings table |
| Phase 1c — Research Tabs | ✅ Complete | Screener, Calendar, Comparison, Stock Picks, Research Reports, News |
| Phase 2b — EDGAR Pipeline | ✅ Complete | CIK seed, XBRL facts, 10-K risk flags; China exposure wired into scoring |
| Phase 2d — News Aggregation | ✅ Complete | WSJ/MS/MF podcasts (Whisper) + WSJ PDF + Yahoo Finance; News tab in app |
| Phase 2f — Thematic Scan | ✅ Complete | Disruption-filtered universe + SC scoring + event context output |
| Phase 1b — Home Screen | 🔲 Next | Market heatmap, index selector |
| Phase 1d — Logistics | 🔲 Planned | Interactive world map with disruption pins |
| Phase 3 — Institutional Flow | 🔲 Planned | Form 4 insider trades, 13F holdings, options flow |

See [`ROADMAP.md`](ROADMAP.md) for the full phase breakdown.

---

## Setup

> Requires Python 3.14.2. Some dependencies (numpy, pandas) must be compiled from source
> on Python 3.14. On Windows, use the **x64 Native Tools Command Prompt for VS 2022**.

```bash
# Create and activate venv
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install C-extension build tools (Windows — Chocolatey, one-time)
# choco install pkgconfiglite

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

# 3 — Enrich fundamentals (runs until all stocks are up to date)
python src/enricher.py
python src/enricher.py --limit 50   # test run — 50 stocks only

# 4 — Run a scan
python src/screener_run.py                            # full NSR scan
python src/screener_run.py --mode thematic            # supply-chain filtered
python src/screener_run.py --limit 500 --top 25       # quick test run

# 5 — Launch the TUI
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
│   ├── screener_config.py      ← all constants, weights, thresholds, status strings
│   ├── db.py                   ← SQLite layer (16 tables, all DB access here)
│   ├── crypto.py               ← Fernet encryption + PBKDF2 password hashing
│   ├── seeder.py               ← one-time DB init + NYSE/NASDAQ universe fetch
│   ├── enricher.py             ← background fundamentals worker + IPO calendar
│   ├── screener.py             ← scoring engine (8 components + SC/flow overlays)
│   ├── screener_run.py         ← CLI scan runner (nsr/thematic/watchlist + CSV)
│   ├── supply_chain.py         ← Tier 2 curated seed + Tier 1 sector matching
│   ├── edgar.py                ← SEC EDGAR XBRL pipeline
│   ├── news.py                 ← podcasts (WSJ/MS/MF) + WSJ PDF + Yahoo Finance news
│   ├── app.py                  ← Textual TUI (login, sidebar, all Research tabs + Settings)
│   ├── pdf_generator.py        ← PDF reports [planned]
│   └── mailer.py               ← email delivery [planned]
├── sql_tables/                 ← canonical SQL table definitions (reference)
├── Mock_up/                    ← UI mockups + HTML prototype
├── man/                        ← man pages (enricher.1)
├── CONTEXT.md                  ← full project context (read at session start)
├── CLAUDE.md                   ← coding conventions for Claude Code
├── ROADMAP.md                  ← phased development plan with progress tracking
├── DATABASE.md                 ← full schema map (all 16 tables, FKs, query patterns)
└── requirements.txt
```

---

## License

MIT
