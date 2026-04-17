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
| Terminal UI | Textual |
| PDF reports | fpdf2 |
| FX conversion | CurrencyConverter |

---

## Project Status

Currently in **Phase 0** — environment setup and foundation.

See [`ROADMAP.md`](ROADMAP.md) for the full phase breakdown.

---

## Setup

> Requires Python 3.14.2. Some dependencies (numpy, pandas, matplotlib, psutil) must be
> compiled from source on Python 3.14. On Windows, use the
> **x64 Native Tools Command Prompt for VS 2022**.

```bash
# Create venv
python -m venv venv_ss
source venv_ss/bin/activate  # Windows: venv_ss\Scripts\activate

# Install C-extension build tools first (Windows — Chocolatey)
# choco install pkgconfiglite

# Install dependencies
pip install -r requirements.txt
pip install pandas-ta --no-deps
```

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
│   ├── screener.py             ← scoring engine
│   ├── screener_run.py         ← CLI entry point
│   ├── screener_config.py      ← all constants, weights, thresholds
│   ├── db.py                   ← SQLite layer (all DB access here)
│   ├── supply_chain.py         ← disruption ingestion + sector mapping
│   ├── app.py                  ← Textual TUI
│   ├── pdf_generator.py        ← PDF reports (fpdf2)
│   └── mailer.py               ← email delivery
├── Mock_up/                    ← UI mockups + HTML prototype
├── CONTEXT.md                  ← full project context (read first)
├── CLAUDE.md                   ← coding conventions
├── ROADMAP.md                  ← phased development plan
└── requirements.txt
```

---

## License

MIT
