# StackScreener

A thematic, supply-chain-aware stock and ETF screener built on Python 3.14.2.

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

Signal sources layered into the composite score:
- **Fundamentals** — EV/Revenue, P/E, EV/EBITDA, profit margin, PEG, debt/equity, CFO ratio, Altman Z
- **Supply chain signals** — active disruption events mapped to GICS sectors
- **Institutional flow** — congressional trades (Quiver Quant), dark pool / options flow (Unusual Whales) *(planned)*

---

## UI

Three-section desktop TUI built with [Textual](https://github.com/Textualize/textual):

| Section | What's Here |
|---|---|
| **Home** | Market heatmap color-coded by % change, sized by market cap. Index selector. |
| **Research** | Screener · Calendar · Stock Comparison · Stock Picks · Research Reports |
| **Logistics** | World map with live disruption pins. Click a pin to filter the impact table. |

Mockup screenshots and an interactive HTML prototype are in [`Mock_up/`](Mock_up/).

---

## Tech Stack

| Layer | Tools |
|---|---|
| Language | Python 3.14.2 |
| Data | yfinance, yahooquery |
| Technical analysis | pandas-ta (installed `--no-deps`) |
| Database | SQLite via `db.py` |
| Encryption | cryptography (Fernet) + keyring (OS keyring) |
| Terminal UI | Textual *(planned)* |
| PDF reports | fpdf2 *(planned)* |
| FX conversion | CurrencyConverter |

---

## Project Status

**Phase 0 — backend foundation complete.**

- Database layer (`db.py`) — 12 tables, full CRUD, encrypted API key storage
- Encryption (`crypto.py`) — Fernet via OS keyring, PBKDF2 password hashing
- Data pipeline — `seeder.py` seeds the full NYSE/NASDAQ universe; `enricher.py` fills in fundamentals in the background

**Up next:** scoring engine (`screener.py` + `screener_run.py`)

See [`ROADMAP.md`](ROADMAP.md) for the full phase breakdown.

---

## Setup

> Requires Python 3.14.2. Some dependencies (numpy, pandas, matplotlib, psutil) must be
> compiled from source on Python 3.14. On Windows, use the
> **x64 Native Tools Command Prompt for VS 2022**.

```bash
# Create venv
python -m venv venv_ss
source venv_ss/bin/activate   # Windows: venv_ss\Scripts\activate

# Install C-extension build tools (Windows — Chocolatey)
# choco install pkgconfiglite

# Install dependencies
pip install -r requirements.txt
pip install pandas-ta --no-deps
```

---

## Database Initialization

```bash
# Initialize schema and seed default admin user only (safe to run first to verify)
python src/seeder.py --schema-only

# Fetch full NYSE + NASDAQ universe (~8,000+ tickers)
python src/seeder.py

# Test with a small batch first
python src/seeder.py --limit 50
```

Default login after seeding: **admin / admin** — you will be prompted to change this on first launch.

---

## Data Enrichment

The seeder populates ticker symbols and prices. Full fundamentals are filled in by the enricher:

```bash
# Run enrichment (processes all unenriched stocks, 0.5s between requests)
python src/enricher.py

# Test run — enrich 20 stocks then stop
python src/enricher.py --limit 20

# Check for upcoming IPOs only (also runs automatically at the start of each enricher run)
python src/enricher.py --ipo-only
```

The enricher is safe to kill and restart — progress is committed per stock.

---

## Running a Scan

```bash
python src/screener_run.py
```

Scan output is written to `Results/<scan_mode>/<datetime>/` (gitignored).

---

## Repo Structure

```
StackScreener/
├── src/
│   ├── screener_config.py      ← all constants, weights, thresholds, status strings
│   ├── db.py                   ← SQLite layer (all DB access here)
│   ├── crypto.py               ← encryption + password hashing
│   ├── seeder.py               ← one-time DB init + universe fetch
│   ├── enricher.py             ← background fundamentals worker
│   ├── screener.py             ← scoring engine           [next]
│   ├── screener_run.py         ← CLI entry point          [next]
│   ├── supply_chain.py         ← disruption ingestion     [planned]
│   ├── app.py                  ← Textual TUI              [planned]
│   ├── pdf_generator.py        ← PDF reports              [planned]
│   └── mailer.py               ← email delivery           [planned]
├── sql_tables/                 ← canonical SQL table definitions
├── Mock_up/                    ← UI mockups + HTML prototype
├── CONTEXT.md                  ← full project context (read first)
├── CLAUDE.md                   ← coding conventions
├── ROADMAP.md                  ← phased development plan
└── requirements.txt
```

---

## License

MIT
