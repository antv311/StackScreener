# StackScreener — File Tree

```
StackScreener/
├── src/
│   │
│   │  ── SHARED CORE ──────────────────────────────────────────────────────────
│   ├── screener_config.py                ← ALL constants, weights, thresholds, status strings, DEBUG_MODE
│   ├── db.py                             ← SQLite layer — ALL DB access goes here only (20 tables, 10 indexes)
│   ├── crypto.py                         ← Fernet encryption (OS keyring) + PBKDF2 password hashing
│   ├── seeder.py                         ← one-time schema init + default admin user + NYSE/NASDAQ universe fetch
│   ├── screener.py                       ← core scoring engine (EV/R, PE, EV/EBITDA, PEG, D/E, margin, SC, flow)
│   ├── screener_run.py                   ← scan runner / CLI (nsr / thematic / watchlist + CSV + event context output)
│   │
│   │  ── PROJECT 1: DATA SCRAPER ────────────────────────────────────────────
│   ├── enricher.py                       ← background fundamentals worker + daily IPO calendar check + dividend normalization (_norm_yield)
│   ├── supply_chain.py                   ← Tier 2 curated seed (27 events, 134 links) + Tier 1 sector matching
│   ├── edgar.py                          ← SEC EDGAR: CIK seed + XBRL facts + two-stage 10-K pipeline (fetch+cache / LLM worker) + 8-K material events + --check-new-filings
│   ├── inst_flow.py                      ← congressional trades + Form 4 insider trades + Form 13F + options flow
│   ├── news.py                           ← podcasts (WSJ/MS/MF RSS+Whisper) + WSJ PDF + Yahoo + AP + CNBC + MarketWatch + NewsAPI + GDELT + LLM classifier
│   ├── llm.py                            ← LLM extraction pipeline (TurboQuant Qwen2.5-7B→32B); --worker --limit N
│   ├── commodities.py                    ← upstream commodity signals: USDA crop conditions + EIA petroleum + FRED 16-series (fertilizers/natgas/metals/agri/lumber)
│   ├── logistics.py                      ← midstream vessel signals: AIS chokepoints (aisstream.io) + Panama Canal draft
│   ├── wsj_fetcher.py                    ← automated WSJ PDF downloader: Gmail IMAP check + Chrome profile download → src/News/pdfs/ → news.py ingest
│   ├── scraper_app.py                    ← Data Scraper TUI — 21 pipeline buttons (incl. WSJ), live log tail, Queue tab, Sources tab, Schedule tab
│   │
│   │  ── PROJECT 2: DATABASE & SERVER ─────────────────────────────────────
│   ├── db_app.py                         ← Database & Server TUI — table browser, SQL shell, DB stats
│   │
│   │  ── PROJECT 3: BLOOMBERG TUI ──────────────────────────────────────────
│   ├── app.py                            ← Bloomberg TUI — login, sidebar ticker search, Research tabs + Home heatmap + Logistics world map
│   │
│   ├── Results/                          ← scan output (gitignored)
│   └── News/
│       ├── audio/                        ← temp MP3 downloads (deleted after transcription, gitignored)
│       └── pdfs/                         ← WSJ newspaper PDFs (kept, gitignored)
│
├── src/filings/
│   ├── 10k/                              ← cached 10-K filing text ({ticker}_{cik}_{accession}.txt, gitignored)
│   └── 8k/                               ← cached 8-K filing text (gitignored)
│
├── sql_tables/                           ← canonical SQL table definitions (reference only — schema lives in db.py)
│   ├── users.sql                         ← user accounts, password hash/salt, admin flag, totp_secret (2FA prep)
│   ├── watchlists.sql                    ← named watchlists, scoped to user_uid
│   ├── stocks.sql                        ← all tracked symbols — descriptive, fundamental, technical, dividend cols, cik, delisted
│   ├── api_keys.sql                      ← Fernet-encrypted API credentials per user/provider (+ url, display_name, connector_config, role)
│   ├── portfolio.sql                     ← user holdings (Plaid-ready: quantity, avg_cost, plaid_account_id)
│   ├── scans.sql                         ← scan run metadata (mode, status, counts, timestamps)
│   ├── scan_results.sql                  ← per-symbol scored results per scan run
│   ├── supply_chain_events.sql           ← disruption events with lat/lon, severity, affected/beneficiary sectors
│   ├── event_stocks.sql                  ← junction: stocks impacted by or benefiting from each event
│   ├── calendar_events.sql               ← earnings, splits, IPOs, economic events, ex_dividend, dividend_pay
│   ├── source_signals.sql                ← signals from congressional trades, SEC filings, Yahoo, options flow
│   ├── research_reports.sql              ← long-form research content tagged by type
│   ├── price_history.sql                 ← daily OHLCV bars + dividends + split factors
│   ├── edgar_facts.sql                   ← XBRL geographic revenue + customer concentration + 10-K risk flags + llm_10k_entities
│   ├── news_articles.sql                 ← headlines, transcripts, WSJ PDF text, llm_classified flag
│   ├── llm_jobs.sql                      ← LLM job queue — pending/running/done/failed/paused/cancelled
│   ├── newsapi_keywords.sql              ← per-user NewsAPI keyword list
│   ├── newsapi_sources.sql               ← NewsAPI source catalog (user-scoped)
│   ├── settings.sql                      ← per-user key/value preferences
│   └── scheduled_jobs.sql                ← pipeline scheduler — recurring jobs with interval_hours + last_run_at
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
├── models/                               ← quantized LLM weights (gitignored — generate locally)
│   └── qwen2.5-7b-4bit/                  ← TurboQuant 4-bit output from `python src/llm.py --quantize`
├── READMETQ.md                           ← TurboQuant weight quantization reference (cksac/turboquant-model)
├── CONTEXT.md                            ← full project context (read at start of every session)
├── CLAUDE.md                             ← coding conventions for Claude Code
├── ROADMAP.md                            ← 4-project roadmap with per-project status + backlogs
├── DATABASE.md                           ← full schema map (all 20 tables, FKs, query patterns)
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
17. llm_jobs                    (no FK deps)
18. newsapi_keywords            → users
19. newsapi_sources             (no FK deps)
20. scheduled_jobs              (no FK deps)
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
| `python src/enricher.py --force` | P1 | Re-enrich all active stocks regardless of staleness |
| `python src/enricher.py --ipo-only` | P1 | Run daily IPO calendar check only |
| `python src/enricher.py --history-only` | P1 | Fetch 5y price history for all active stocks |
| `python src/supply_chain.py --seed-tier2` | P1 | Seed curated Tier 2 supply chain relationships |
| `python src/supply_chain.py --list-events` | P1 | List all supply chain events in the database |
| `python src/supply_chain.py --candidates N` | P1 | Print Tier 1 sector candidates for event N |
| `python src/edgar.py --seed-ciks` | P1 | Map all tickers to SEC CIKs (run once) |
| `python src/edgar.py --fetch-facts` | P1 | Pull XBRL geographic revenue + customer concentration |
| `python src/edgar.py --fetch-filings` | P1 | 10-K two-stage: Stage 1 download+cache+keyword-extract+enqueue LLM job |
| `python src/edgar.py --fetch-filings --limit N` | P1 | Stage 1 for N stocks |
| `python src/edgar.py --check-new-filings` | P1 | Lightweight accession check; marks stale for re-fetch |
| `python src/edgar.py --fetch-8k` | P1 | Scan recent 8-K filings for material supply-chain events |
| `python src/edgar.py --fetch-8k --limit N` | P1 | 8-K scan for N stocks |
| `python src/edgar.py --china-exposure 0.15` | P1 | Print stocks with >15% China revenue |
| `python src/news.py --podcasts` | P1 | Fetch + transcribe latest WSJ / Morgan Stanley / Motley Fool |
| `python src/news.py --watchlist` | P1 | Fetch Yahoo Finance news for all watchlist stocks |
| `python src/news.py --ingest-pdfs` | P1 | Ingest all WSJ newspaper PDFs in `src/News/pdfs/` |
| `python src/news.py --classify` | P1 | Run LLM classifier on unclassified articles → supply_chain_events |
| `python src/news.py --all` | P1 | All free news sources |
| `python src/wsj_fetcher.py --setup email "app-password"` | P1 | Configure Gmail credentials for WSJ PDF fetcher |
| `python src/wsj_fetcher.py --fetch` | P1 | Check Gmail, download WSJ PDF, run news.py ingest |
| `python src/wsj_fetcher.py --fetch --no-ingest` | P1 | Download WSJ PDF only, skip ingest |
| `python src/inst_flow.py --congressional` | P1 | Senate + House Stock Watcher trades |
| `python src/inst_flow.py --form4` | P1 | Fetch EDGAR Form 4 insider trades → source_signals |
| `python src/inst_flow.py --form4 --limit 200 --days 90` | P1 | Form 4 with limits |
| `python src/inst_flow.py --form13f` | P1 | Fetch Form 13F holdings for 14 institutions → position diff → source_signals |
| `python src/inst_flow.py --options` | P1 | Scan yfinance options chains for unusual volume (>3× OI) → source_signals |
| `python src/inst_flow.py --options --tickers AAPL MSFT` | P1 | Options scan for specific tickers only |
| `python src/commodities.py --usda-crops` | P1 | USDA NASS weekly crop conditions → crop_stress signals |
| `python src/commodities.py --eia-petroleum` | P1 | EIA weekly petroleum inventory → oil_inventory_surprise signals |
| `python src/commodities.py --all` | P1 | All commodity sources |
| `python src/logistics.py --chokepoints` | P1 | AIS vessel counts at 10 global chokepoints → chokepoint_congestion signals |
| `python src/logistics.py --panama` | P1 | Panama Canal draft restriction scrape → canal_draft_restriction signals |
| `python src/logistics.py --all` | P1 | All logistics sources |
| `python src/llm.py --quantize` | P1 | Download + quantize Qwen2.5-7B-Instruct (run once) |
| `python src/llm.py --test` | P1 | Run 3-task validation suite |
| `python src/llm.py --worker` | P1 | Drain LLM job queue (loops until empty or Ctrl-C) |
| `python src/llm.py --worker --limit N` | P1 | Process N jobs then exit |
| `python src/screener_run.py` | Shared | Run a full NSR scan — scores all active stocks |
| `python src/screener_run.py --mode thematic` | Shared | Supply-chain-aware scan (filtered universe) |
| `python src/screener_run.py --limit N --top 25` | Shared | Limit universe + show top 25 |
| `python src/scraper_app.py` | P1 | Launch the Data Scraper TUI |
| `python src/db_app.py` | P2 | Launch the Database & Server TUI |
| `python src/app.py` | P3 | Launch the Bloomberg TUI |

---

## Data Sources (Free — No Paid API Keys Required Unless Noted)

| Source | Data | Status |
|---|---|---|
| yfinance | Price, fundamentals, options chain, IPO calendar, dividends | ✅ Live |
| yahooquery | Detailed financials supplement | ✅ Live |
| SEC EDGAR XBRL | Geographic revenue, customer concentration | ✅ Live |
| SEC EDGAR 10-K text | Two-stage: risk flags + LLM entity extraction | ✅ Live |
| SEC EDGAR 8-K | Material event keyword scanner | ✅ Live |
| Senate Stock Watcher API | Congressional trades (Senate) | ✅ Live |
| House Stock Watcher API | Congressional trades (House) | ✅ Live |
| SEC EDGAR Form 4 | Insider buy/sell filings | ✅ Live |
| SEC EDGAR Form 13F | Institutional holdings (quarterly) | ✅ Live |
| AP News RSS | Business + finance + technology feeds | ✅ Live |
| CNBC RSS | US business + finance feeds | ✅ Live |
| MarketWatch RSS | Top stories | ✅ Live |
| NewsAPI.org *(requires free key)* | AP, Reuters + 150k sources | ✅ Live |
| GDELT Project | Global event database | ✅ Live |
| USDA NASS *(requires free key)* | Weekly crop condition reports | ✅ Live |
| EIA Open Data *(requires free key)* | Weekly petroleum inventory | ✅ Live |
| FRED / St. Louis Fed *(requires free key)* | 16 commodity price series (fertilizers, natgas, metals, agri, lumber) | ✅ Live |
| aisstream.io *(requires free key)* | AIS vessel tracking — 10 chokepoints | ✅ Live |
| Panama Canal Authority | Draft restriction scrape | ✅ Live |
| WSJ (via wsj_fetcher.py) | PDF newspaper via Gmail IMAP + Chrome | ✅ Live |
