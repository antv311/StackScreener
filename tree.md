# StackScreener — File Tree

```
StackScreener/
├── src/
│   │
│   │  ── SHARED CORE ──────────────────────────────────────────────────────────
│   ├── screener_config.py                ← ALL constants, weights, thresholds, status strings, DEBUG_MODE
│   ├── db.py                             ← SQLite layer — ALL DB access goes here only (16 tables, 8 indexes)
│   ├── crypto.py                         ← Fernet encryption (OS keyring) + PBKDF2 password hashing
│   ├── seeder.py                         ← one-time schema init + default admin user + NYSE/NASDAQ universe fetch
│   ├── screener.py                       ← core scoring engine (EV/R, PE, EV/EBITDA, PEG, D/E, margin, SC, flow)
│   ├── screener_run.py                   ← scan runner / CLI (nsr / thematic / watchlist + CSV + event context output)
│   │
│   │  ── PROJECT 1: DATA SCRAPER ────────────────────────────────────────────
│   ├── enricher.py                       ← background fundamentals worker + daily IPO calendar check
│   ├── supply_chain.py                   ← Tier 2 curated seed (6 events, 37 links) + Tier 1 sector matching
│   ├── edgar.py                          ← SEC EDGAR: CIK seed + XBRL facts + 10-K text (risk flags + customer %)
│   ├── inst_flow.py                      ← congressional trades (Senate + House) + Form 4/13F  [PARTIAL — P1 next]
│   ├── news.py                           ← podcasts (WSJ/MS/MF RSS+Whisper) + WSJ PDF + Yahoo Finance news
│   ├── llm.py                            ← LLM extraction pipeline (TurboQuant Qwen2.5-7B→32B)
│   ├── scraper_app.py                    ← Data Scraper TUI entry point                        [PLANNED — P1]
│   │
│   │  ── PROJECT 2: DATABASE & SERVER ─────────────────────────────────────
│   ├── db_app.py                         ← Database & Server TUI entry point                   [PLANNED — P2]
│   │
│   │  ── PROJECT 3: BLOOMBERG TUI ──────────────────────────────────────────
│   ├── app.py                            ← Bloomberg TUI — login, sidebar, all Research tabs + StockQuoteModal
│   ├── pdf_generator.py                  ← PDF reports (fpdf2)                                 [PLANNED — P3]
│   ├── mailer.py                         ← email delivery                                      [PLANNED — P4]
│   │
│   ├── screener_post_processing.py       ← normalized scoring output                           [PLANNED]
│   ├── Results/                          ← scan output (gitignored)
│   └── News/
│       ├── audio/                        ← temp MP3 downloads (deleted after transcription, gitignored)
│       └── pdfs/                         ← WSJ newspaper PDFs (kept, gitignored)
│
├── sql_tables/                           ← canonical SQL table definitions (reference only — schema lives in db.py)
│   ├── users.sql                         ← user accounts, password hash/salt, admin flag, totp_secret (2FA prep)
│   ├── watchlists.sql                    ← named watchlists, scoped to user_uid
│   ├── stocks.sql                        ← all tracked symbols — descriptive, fundamental, technical, cik, delisted
│   ├── api_keys.sql                      ← Fernet-encrypted API credentials per user/provider
│   ├── portfolio.sql                     ← user holdings (Plaid-ready: quantity, avg_cost, plaid_account_id)
│   ├── scans.sql                         ← scan run metadata (mode, status, counts, timestamps)
│   ├── scan_results.sql                  ← per-symbol scored results per scan run
│   ├── supply_chain_events.sql           ← disruption events with lat/lon, severity, affected/beneficiary sectors
│   ├── event_stocks.sql                  ← junction: stocks impacted by or benefiting from each event
│   ├── calendar_events.sql               ← earnings, splits, IPOs, economic events
│   ├── source_signals.sql                ← signals from congressional trades, SEC filings, Yahoo, options flow
│   ├── research_reports.sql              ← long-form research content tagged by type
│   ├── price_history.sql                 ← daily OHLCV bars + dividends + split factors
│   ├── edgar_facts.sql                   ← XBRL geographic revenue + customer concentration + 10-K risk flags
│   ├── settings.sql                      ← per-user key/value preferences
│   └── news_articles.sql                 ← headlines, transcripts, WSJ PDF text
│
│  ── PROJECT 4: WEB SERVER & SITE ──────────────────────────────────────────
├── StackScreenerCD/                      ← React/JSX web prototype (reference UI for P4)
│   ├── StackScreener Web UI.html         ← single-file prototype entry point
│   ├── atoms.jsx                         ← shared components, icons, design tokens
│   ├── shell.jsx                         ← sidebar, topbar, router
│   ├── home.jsx                          ← home / heatmap page
│   ├── research.jsx                      ← Research tabs (Screener, Calendar, Comparison, Picks, Reports)
│   ├── logistics.jsx                     ← Logistics / supply chain map
│   ├── settings.jsx                      ← Settings pages
│   └── styles.css                        ← design system CSS
│
├── man/
│   └── enricher.1                        ← man page for enricher CLI
├── Mock_up/                              ← original TUI mockup screenshots + HTML prototype
│   ├── HomePage_.jpg
│   ├── Logisitc_.jpg
│   ├── Research_Screener.jpg
│   ├── Research_Calendar.jpg
│   ├── Research_Comparison.jpg
│   ├── Research Stock picks.jpg
│   ├── Research Reasearch reports_.jpg
│   └── Prototype/
│       └── stackscreener_full_ui_prototype.html
├── READMETQ.md                           ← TurboQuant weight quantization reference (cksac/turboquant-model)
├── CONTEXT.md                            ← full project context (read at start of every session)
├── CLAUDE.md                             ← coding conventions for Claude Code
├── ROADMAP.md                            ← 4-project roadmap with per-project status + backlogs
├── DATABASE.md                           ← full schema map (all 16 tables, FKs, query patterns)
├── README.md                             ← GitHub landing page
├── tree.md                               ← this file
├── requirements.txt                      ← Python dependencies
└── LICENSE
```

---

## Database Table Dependency Order

Tables must be created in this order (FK dependencies):

```
1.  users
2.  watchlists                  → users
3.  stocks                      → watchlists
4.  api_keys                    → users
5.  portfolio                   → users, stocks
6.  scans                       (no FK deps)
7.  scan_results                → stocks, scans
8.  supply_chain_events         (no FK deps)
9.  event_stocks                → supply_chain_events, stocks
10. calendar_events             → stocks
11. source_signals              → stocks
12. research_reports            → supply_chain_events, stocks
13. price_history               → stocks
14. edgar_facts                 → stocks
15. settings                    → users
16. news_articles               → stocks
```

---

## Key Entry Points

| Command | Project | What it does |
|---|---|---|
| `python src/seeder.py --schema-only` | Shared | Initialize DB schema + seed admin user |
| `python src/seeder.py` | Shared | Full seed: schema + admin + NYSE/NASDAQ universe |
| `python src/seeder.py --limit N` | Shared | Seed with at most N tickers (for testing) |
| `python src/enricher.py` | P1 | Enrich all active stocks with full yfinance fundamentals |
| `python src/enricher.py --limit N` | P1 | Enrich N stocks then stop |
| `python src/enricher.py --ipo-only` | P1 | Run daily IPO calendar check only |
| `python src/enricher.py --history-only` | P1 | Fetch 5y price history for all active stocks |
| `python src/supply_chain.py --seed-tier2` | P1 | Seed curated Tier 2 supply chain relationships |
| `python src/supply_chain.py --list-events` | P1 | List all supply chain events in the database |
| `python src/supply_chain.py --candidates N` | P1 | Print Tier 1 sector candidates for event N |
| `python src/edgar.py --seed-ciks` | P1 | Map all tickers to SEC CIKs (run once) |
| `python src/edgar.py --fetch-facts` | P1 | Pull XBRL geographic revenue + customer concentration |
| `python src/edgar.py --fetch-filings` | P1 | Pull 10-K text: risk flags + customer % mentions |
| `python src/edgar.py --china-exposure 0.15` | P1 | Print stocks with >15% China revenue |
| `python src/news.py --podcasts` | P1 | Fetch + transcribe latest WSJ / Morgan Stanley / Motley Fool |
| `python src/news.py --watchlist` | P1 | Fetch Yahoo Finance news for all watchlist stocks |
| `python src/news.py --ingest-pdfs` | P1 | Ingest all WSJ newspaper PDFs in `src/News/pdfs/` |
| `python src/screener_run.py` | Shared | Run a full NSR scan — scores all active stocks |
| `python src/screener_run.py --mode thematic` | Shared | Supply-chain-aware scan (filtered universe) |
| `python src/screener_run.py --limit N --top 25` | Shared | Limit universe + show top 25 |
| `python src/app.py` | P3 | Launch the Bloomberg TUI |

---

## Data Sources (Free — No Paid API Keys Required)

| Source | Data | Status |
|---|---|---|
| yfinance | Price, fundamentals, options chain, IPO calendar | ✅ Live |
| yahooquery | Detailed financials supplement | ✅ Live |
| SEC EDGAR XBRL | Geographic revenue, customer concentration | ✅ Live |
| SEC EDGAR 10-K text | Risk flags, customer % mentions | ✅ Live |
| Senate Stock Watcher API | Congressional trades (Senate) | ✅ Built |
| House Stock Watcher API | Congressional trades (House) | ✅ Built |
| SEC EDGAR Form 4 | Insider buy/sell filings | 🔲 P1 next |
| SEC EDGAR Form 13F | Institutional holdings (quarterly) | 🔲 P1 planned |
| worldmonitor-osint | Supply chain disruption events | 🔲 P1 planned |
