# StackScreener — File Tree

```
StackScreener/
├── src/
│   ├── screener_config.py                ← ALL constants, weights, thresholds, status strings, provider names, DEBUG_MODE
│   ├── db.py                             ← SQLite layer — ALL DB access goes here only (13 tables, 2 indexes)
│   ├── crypto.py                         ← Fernet encryption (OS keyring) + PBKDF2 password hashing
│   ├── seeder.py                         ← one-time schema init + default admin user + NYSE/NASDAQ universe fetch
│   ├── enricher.py                       ← background fundamentals worker + daily IPO calendar check
│   ├── screener.py                       ← core scoring engine                                [NEXT]
│   ├── screener_run.py                   ← scan runner / CLI entry point                      [NEXT]
│   ├── screener_post_processing.py       ← normalized scoring output                          [PLANNED]
│   ├── supply_chain.py                   ← Tier 2 curated seed + Tier 1 sector matching       [PARTIAL]
│   ├── inst_flow.py                      ← congressional trades + SEC insider/13F ingestion   [PLANNED]
│   ├── app.py                            ← desktop TUI entry point (Textual)                  [PLANNED]
│   ├── pdf_generator.py                  ← PDF reports (fpdf2)                                [PLANNED]
│   ├── mailer.py                         ← email delivery                                     [PLANNED]
│   └── Results/                          ← scan output (gitignored)
├── sql_tables/                           ← canonical SQL table definitions (reference only — schema lives in db.py)
│   ├── users.sql                         ← user accounts, password hash/salt, admin flag, totp_secret (2FA prep)
│   ├── watchlists.sql                    ← named watchlists, scoped to user_uid
│   ├── stocks.sql                        ← all tracked symbols — descriptive, fundamental, technical, last_enriched_at, delisted
│   ├── api_keys.sql                      ← Fernet-encrypted API credentials per user/provider
│   ├── portfolio.sql                     ← user holdings (Plaid-ready: quantity, avg_cost, plaid_account_id)
│   ├── scans.sql                         ← scan run metadata (mode, status, counts, timestamps)
│   ├── scan_results.sql                  ← per-symbol scored results per scan run
│   ├── supply_chain_events.sql           ← disruption events with lat/lon, severity, affected/beneficiary sectors
│   ├── event_stocks.sql                  ← junction: stocks impacted by or benefiting from each event
│   ├── calendar_events.sql               ← earnings, splits, IPOs, economic events
│   ├── source_signals.sql                ← signals from congressional trades, SEC filings, Yahoo, options flow
│   ├── research_reports.sql             ← long-form research content tagged by type
│   └── price_history.sql               ← daily OHLCV bars + dividends + split factors
├── man/
│   └── enricher.1                        ← man page for enricher CLI (install to /usr/share/man/man1/)
├── Mock_up/
│   ├── HomePage_.jpg
│   ├── Logisitc_.jpg
│   ├── Research_Screener.jpg
│   ├── Research_Calendar.jpg
│   ├── Research_Comparison.jpg
│   ├── Research Stock picks.jpg
│   ├── Research Reasearch reports_.jpg
│   └── Prototype/
│       └── stackscreener_full_ui_prototype.html
├── CONTEXT.md                            ← full project context (read at start of every session)
├── CLAUDE.md                             ← coding conventions for Claude Code
├── ROADMAP.md                            ← phased development plan with progress tracking
├── DATABASE.md                           ← full database schema map (all 13 tables, FKs, query patterns)
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
```

---

## Key Entry Points

| Command | What it does |
|---|---|
| `python src/seeder.py --schema-only` | Initialize DB schema + seed admin user |
| `python src/seeder.py` | Full seed: schema + admin + NYSE/NASDAQ universe |
| `python src/seeder.py --limit N` | Seed with at most N tickers (for testing) |
| `python src/enricher.py` | Enrich all active stocks with full yfinance fundamentals |
| `python src/enricher.py --limit N` | Enrich N stocks then stop |
| `python src/enricher.py --ipo-only` | Run daily IPO calendar check only |
| `python src/enricher.py --history-only` | Fetch 5y price history for all active stocks |
| `python src/enricher.py --include-delisted` | Include delisted stocks in enrichment run |
| `python src/supply_chain.py --seed-tier2` | Seed curated Tier 2 supply chain relationships |
| `python src/supply_chain.py --list-events` | List all supply chain events in the database |
| `python src/supply_chain.py --candidates N` | Print Tier 1 sector candidates for event N |
| `python src/screener_run.py` | Run a full scan (once scoring engine is built) |

## Data Sources (Free — No Paid API Keys Required)

| Source | Data | Provider |
|---|---|---|
| yfinance | Price, fundamentals, options chain, IPO calendar | Yahoo Finance |
| yahooquery | Detailed financials supplement | Yahoo Finance |
| Senate Stock Watcher API | Congressional trades (Senate) | senatestockwatcher.com |
| House Stock Watcher API | Congressional trades (House) | housestockwatcher.com |
| SEC EDGAR Form 4 | Insider buy/sell filings | SEC (public) |
| SEC EDGAR Form 13F | Institutional holdings (quarterly) | SEC (public) |
