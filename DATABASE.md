# StackScreener — Database Map

All tables live in `stackscreener.db`. All access goes through `db.py` only.
Schema is created by `db.init_db()`. Migrations (new columns) run automatically on startup.
**20 tables total. 10 covering indexes.**

---

## Relationship Diagram

```
users
 ├── watchlists              (user_uid → users)
 │    └── stocks             (watchlist_uid → watchlists)
 ├── api_keys                (user_uid → users)
 ├── portfolio               (user_uid → users, stock_uid → stocks)
 ├── settings                (user_uid → users)
 ├── newsapi_keywords        (user_uid → users)
 └── llm_jobs                (no FK deps — standalone queue)

stocks
 ├── scan_results            (stock_uid → stocks)
 ├── event_stocks            (stock_uid → stocks)
 ├── calendar_events         (stock_uid → stocks)
 ├── source_signals          (stock_uid → stocks)
 ├── research_reports        (stock_uid → stocks)
 ├── portfolio               (stock_uid → stocks)
 ├── price_history           (stock_uid → stocks)
 ├── edgar_facts             (stock_uid → stocks)
 └── news_articles           (stock_uid → stocks)

scans
 └── scan_results            (scan_uid → scans)

supply_chain_events
 ├── event_stocks            (supply_chain_event_uid → supply_chain_events)
 └── research_reports        (supply_chain_event_uid → supply_chain_events)

newsapi_sources              (no FK deps — catalog table)
scheduled_jobs               (no FK deps — standalone scheduler)
```

**Creation order** (respects FK deps):
`users → watchlists → stocks → api_keys → portfolio → scans → scan_results → supply_chain_events → event_stocks → calendar_events → source_signals → research_reports → price_history → edgar_facts → settings → news_articles → llm_jobs → newsapi_keywords → newsapi_sources → scheduled_jobs`

---

## Tables

### users
Accounts. Passwords are PBKDF2-HMAC-SHA256 hashed (260k iterations, per-user salt).

| Column | Type | Notes |
|---|---|---|
| `user_uid` | INTEGER PK | |
| `username` | TEXT UNIQUE | login handle |
| `password_hash` | TEXT | hex digest |
| `salt` | TEXT | random per-user hex |
| `display_name` | TEXT | |
| `email` | TEXT | |
| `is_admin` | INTEGER | 1 = admin |
| `force_password_change` | INTEGER | 1 = must change on next login |
| `totp_secret` | TEXT | NULL — reserved for future 2FA |
| `created_at`, `updated_at` | TEXT | datetime strings |

---

### watchlists
Named lists of stocks, scoped to a user.

| Column | Type | Notes |
|---|---|---|
| `watchlist_uid` | INTEGER PK | |
| `user_uid` | INTEGER FK → users | |
| `name` | TEXT UNIQUE | |
| `description` | TEXT | |
| `created_at`, `updated_at` | TEXT | |

Stocks are assigned to a watchlist via `watchlist_uid` + `is_watched` columns on the `stocks` table directly.

```sql
-- Get all stocks on a watchlist:
SELECT * FROM stocks WHERE watchlist_uid = ? AND is_watched = 1
```

---

### stocks
Every tracked NYSE/NASDAQ symbol. ~7,001 rows after seeding. Enriched in background by `enricher.py`.

| Column | Type | Notes |
|---|---|---|
| `stock_uid` | INTEGER PK | |
| `watchlist_uid` | INTEGER FK → watchlists | NULL if not on a watchlist |
| `is_watched` | INTEGER | 1 = on watchlist |
| `ticker` | TEXT | UNIQUE with exchange |
| `exchange` | TEXT | NASDAQ / NYSE / NYSE ARCA |
| `company_name` | TEXT | yfinance `shortName` — used in UI display |
| `market_index` | TEXT | |
| `sector`, `industry` | TEXT | GICS |
| `country` | TEXT | |
| `business_summary` | TEXT | yfinance `longBusinessSummary` — used for supply chain keyword matching |
| `market_cap` | REAL | |
| `price` | REAL | 0.0 = pre-IPO / not yet listed |
| `ipo_date` | TEXT | YYYY-MM-DD |
| `pe_ratio`, `forward_pe`, `peg_ratio` | REAL | fundamentals |
| `ps_ratio`, `pb_ratio` | REAL | |
| `gross_margin`, `operating_margin`, `net_profit_margin` | REAL | |
| `return_on_assets`, `return_on_equity` | REAL | |
| `current_ratio`, `quick_ratio` | REAL | |
| `total_debt_to_equity`, `lt_debt_to_equity` | REAL | |
| `beta`, `rsi_14`, `atr` | REAL | technical |
| `change_pct`, `perf_week`, `perf_month` ... | REAL | performance |
| `dist_from_sma_20`, `dist_from_sma_50`, `dist_from_sma_200` | REAL | |
| `insider_ownership`, `inst_ownership` | REAL | |
| `shares_outstanding`, `shares_float` | INTEGER | |
| `average_volume`, `current_volume` | INTEGER | |
| `dividend_yield` | REAL | trailing twelve-month yield (normalized: 0.0695 not 6.95) |
| `payout_ratio` | REAL | |
| `ex_dividend_date` | TEXT | YYYY-MM-DD — next ex-dividend date |
| `dividend_date` | TEXT | YYYY-MM-DD — next dividend pay date |
| `last_dividend_value` | REAL | most recent per-share dividend amount |
| `last_enriched_at` | TEXT | NULL = never enriched; staleness check |
| `macro_signal` | TEXT | reserved for macro overlay |
| `cik` | TEXT | SEC Central Index Key — populated by `edgar.py --seed-ciks` |
| `delisted` | INTEGER | 0 = active (default), 1 = delisted — skipped by enricher and scans |

**Indexes:**
- `idx_stocks_delisted_enriched` on `(delisted, last_enriched_at)` — enrichment staleness query
- `idx_stocks_delisted_price` on `(delisted, price)` — price history pending query

```sql
-- Stocks needing enrichment (use db.get_pending_enrichment()):
SELECT stock_uid, ticker, exchange FROM stocks
WHERE (last_enriched_at IS NULL OR last_enriched_at < datetime('now', '-1 days'))
  AND delisted = 0
ORDER BY last_enriched_at ASC NULLS FIRST;

-- Mark a stock delisted (use db.mark_delisted(stock_uid)):
UPDATE stocks SET delisted = 1 WHERE stock_uid = ?;
```

---

### api_keys
Fernet-encrypted API credentials per user. Supports named display labels, base URLs, and
role-based connector mapping.

| Column | Type | Notes |
|---|---|---|
| `api_uid` | INTEGER PK | |
| `user_uid` | INTEGER FK → users | |
| `name` | TEXT | provider role key — UNIQUE per user (e.g. `aisstream`, `newsapi`) |
| `api_key` | TEXT | **Fernet-encrypted** — never plaintext |
| `url` | TEXT | base URL of endpoint (optional) |
| `display_name` | TEXT | cosmetic label shown in Sources tab (e.g. "Bloomberg Shipping") |
| `connector_config` | TEXT | JSON blob for connector-specific settings |
| `role` | TEXT | role key from `KNOWN_API_ROLES` in screener_config.py |
| `created_at`, `updated_at` | TEXT | |

```python
# Store:  db.set_api_key(user_uid, 'aisstream', 'my-key', url='wss://...', display_name='AISstream')
# Fetch:  db.get_api_key(user_uid, 'aisstream')  # returns plaintext in memory only
```

---

### portfolio
User holdings. Plaid-ready (`plaid_account_id` for live sync).

| Column | Type | Notes |
|---|---|---|
| `portfolio_uid` | INTEGER PK | |
| `user_uid` | INTEGER FK → users | |
| `stock_uid` | INTEGER FK → stocks | UNIQUE with user_uid |
| `quantity` | REAL | |
| `avg_cost` | REAL | cost basis per share |
| `plaid_account_id` | TEXT | Plaid account reference |
| `added_at`, `updated_at` | TEXT | |

---

### scans
Metadata for each scan run.

| Column | Type | Notes |
|---|---|---|
| `scan_uid` | INTEGER PK | |
| `scan_mode` | TEXT | `nsr`, `thematic`, `watchlist`, `custom` |
| `triggered_by` | TEXT | `manual`, `scheduled`, `alert` |
| `status` | TEXT | `running` → `complete` / `failed` |
| `symbol_count` | INTEGER | total symbols in universe |
| `scored_count` | INTEGER | successfully scored |
| `failed_count` | INTEGER | failed to score |
| `started_at`, `completed_at` | TEXT | |
| `notes` | TEXT | optional notes / error summary |

---

**Indexes:**
- `idx_scan_results_scan_rank` on `(scan_uid, composite_rank)` — result lookup by scan

### scan_results
Per-symbol scored output for each scan run.

| Column | Type | Notes |
|---|---|---|
| `scan_result_uid` | INTEGER PK | |
| `stock_uid` | INTEGER FK → stocks | |
| `scan_uid` | INTEGER FK → scans | |
| `composite_score` | REAL | weighted final score |
| `composite_rank` | INTEGER | rank within this scan |
| `score_ev_revenue` | REAL | EV/Revenue component |
| `score_pe` | REAL | P/E component |
| `score_ev_ebitda` | REAL | EV/EBITDA component |
| `score_profit_margin` | REAL | net margin component |
| `score_peg` | REAL | PEG ratio component |
| `score_debt_equity` | REAL | debt/equity component |
| `score_cfo_ratio` | REAL | CFO/debt component |
| `score_altman_z` | REAL | Altman Z-score component |
| `score_supply_chain` | REAL | additive supply chain layer |
| `score_inst_flow` | REAL | additive institutional flow layer |
| `price_at_scan`, `market_cap_at_scan` | REAL | snapshot values |
| `scored_at` | TEXT | |

---

**Indexes:**
- `idx_sce_status` on `(status)` — active event queries

### supply_chain_events
Active and historical disruption events. Drives the Logistics map.

| Column | Type | Notes |
|---|---|---|
| `supply_chain_event_uid` | INTEGER PK | |
| `title` | TEXT | UNIQUE with region |
| `region` | TEXT | geographic region name |
| `event_type` | TEXT | see `EVENT_TYPE_*` in `screener_config.py` |
| `description` | TEXT | |
| `severity` | TEXT | `CRITICAL` / `HIGH` / `MEDIUM` / `LOW` |
| `status` | TEXT | `active` / `resolved` / `monitoring` |
| `latitude`, `longitude` | REAL | map pin coordinates |
| `country_code` | TEXT | ISO 3166-1 alpha-2 (e.g. `EG`, `CN`) |
| `trade_route` | TEXT | `Red Sea`, `Taiwan Strait`, `Panama Canal` |
| `commodity` | TEXT | `semiconductors`, `crude oil`, `grain` |
| `affected_sectors` | TEXT | JSON array of GICS sectors disrupted |
| `affected_industries` | TEXT | JSON array of specific industries |
| `beneficiary_sectors` | TEXT | JSON array of sectors that fill the gap |
| `source_url` | TEXT | where event was detected |
| `event_date` | TEXT | YYYY-MM-DD |
| `detected_at`, `resolved_at`, `updated_at` | TEXT | |

**Event types** (`screener_config.py`):
`conflict` · `sanctions` · `weather` · `labor` · `accident` · `port_blockage` · `factory_shutdown` · `pandemic` · `fire` · `flood` · `natural_disaster` · `infrastructure_failure` · `product_recall` · `cybersecurity`

---

### event_stocks
Junction: which stocks are impacted by or benefit from each supply chain event.

| Column | Type | Notes |
|---|---|---|
| `event_stock_uid` | INTEGER PK | |
| `supply_chain_event_uid` | INTEGER FK → supply_chain_events | |
| `stock_uid` | INTEGER FK → stocks | |
| `role` | TEXT | `impacted` or `beneficiary` |
| `cannot_provide` | TEXT | what the impacted company can't supply |
| `will_redirect` | TEXT | where demand shifts (gap filler) |
| `impact_notes` | TEXT | why this stock is included |
| `confidence` | TEXT | `high` / `medium` / `low` |
| `linked_at` | TEXT | |

```sql
-- Logistics table query (all impacted + beneficiary companies for an event):
SELECT es.role, es.cannot_provide, es.will_redirect,
       s.ticker, s.sector, s.industry
FROM event_stocks es
JOIN stocks s USING (stock_uid)
WHERE es.supply_chain_event_uid = ?
ORDER BY es.role, s.ticker
```

---

### calendar_events
Earnings, splits, IPOs, economic events, and dividend dates. IPOs pre-seeded by `enricher.py`
daily. Dividend events auto-synced from `stocks` by `db.sync_dividend_calendar_events()`.

| Column | Type | Notes |
|---|---|---|
| `calendar_event_uid` | INTEGER PK | |
| `stock_uid` | INTEGER FK → stocks | nullable for macro events |
| `event_type` | TEXT | `earnings` / `split` / `ipo` / `economic` / `ex_dividend` / `dividend_pay` |
| `event_date` | TEXT | YYYY-MM-DD |
| `title` | TEXT | |
| `eps_estimate`, `eps_actual` | REAL | earnings-specific |
| `revenue_estimate`, `revenue_actual` | REAL | |
| `surprise_pct` | REAL | |
| `split_ratio` | TEXT | e.g. `4:1` |
| `ipo_price_low`, `ipo_price_high` | REAL | IPO range |
| `detail` | TEXT | free text for macro events |
| `status` | TEXT | `upcoming` / `confirmed` / `reported` |
| `fetched_at`, `updated_at` | TEXT | |

**Event types** (`screener_config.py`):
`earnings` · `split` · `ipo` · `economic` · `ex_dividend` · `dividend_pay`

---

**Indexes:**
- `idx_source_signals_stock` on `(stock_uid)` — signal score and stock picks queries

### source_signals
Per-stock signals from congressional trades, SEC filings, and options flow.

| Column | Type | Notes |
|---|---|---|
| `source_signal_uid` | INTEGER PK | |
| `stock_uid` | INTEGER FK → stocks | |
| `source` | TEXT | `senate_watcher` · `house_watcher` · `sec_form4` · `sec_13f` · `yahoo_finance` · `options_flow` |
| `sub_score` | REAL | 0–100 score from this source |
| `reason_text` | TEXT | shown in Stock Picks card |
| `signal_type` | TEXT | `congress_buy` · `insider_buy` · `inst_accumulation` · `options_flow` · `analyst_rec` · `material_event` |
| `signal_url` | TEXT | link to original filing/source |
| `raw_data` | TEXT | JSON blob for reprocessing |
| `fetched_at` | TEXT | UNIQUE with stock_uid + source |

---

### research_reports
Long-form research cards shown in the Research → Research Reports tab.

| Column | Type | Notes |
|---|---|---|
| `research_report_uid` | INTEGER PK | |
| `title` | TEXT | |
| `summary` | TEXT | shown in card preview |
| `body` | TEXT | full markdown content |
| `tag` | TEXT | `supply_chain` / `fundamentals` / `inst_flow` |
| `supply_chain_event_uid` | INTEGER FK → supply_chain_events | optional link |
| `stock_uid` | INTEGER FK → stocks | optional link |
| `author` | TEXT | default `StackScreener` |
| `source_url` | TEXT | |
| `published_at`, `updated_at` | TEXT | |

---

### edgar_facts
Structured XBRL and 10-K/8-K text data pulled from SEC EDGAR for each stock.
Refreshed quarterly (XBRL) or via the two-stage 10-K pipeline.

| Column | Type | Notes |
|---|---|---|
| `edgar_fact_uid` | INTEGER PK | |
| `stock_uid` | INTEGER FK → stocks | |
| `fact_type` | TEXT | see fact types below |
| `period` | TEXT | Fiscal year, e.g. `2023` |
| `value_json` | TEXT | JSON blob — shape varies by fact_type (see below) |
| `fetched_at` | TEXT | |

**Fact types** (`screener_config.py`):
- `geographic_revenue` — `{"US": 0.42, "China": 0.19, "Europe": 0.27, "Other": 0.12}`
- `customer_concentration` — `[{"name": "Apple Inc.", "pct": 0.18, "segment": "Products"}]`
- `risk_flags` — `{"china_dependency": true, "tariff_risk": false, ...}` — 8 boolean supply-chain risk flags from 10-K text
- `filing_customers` — `[{"name": "Walmart", "pct": 0.22}]` — customer % mentions extracted from 10-K narrative
- `llm_10k_entities` — `[{"name": "TSMC", "type": "supplier", "ticker": "TSM", "context": "..."}]` — LLM-extracted supplier/customer entities from 10-K text

**Indexes:**
- `idx_edgar_facts_stock_type` on `(stock_uid, fact_type)` — per-stock fact lookup
- `idx_edgar_facts_type_fetched` on `(fact_type, fetched_at)` — pending pipeline queries

```python
# Stocks with >15% China revenue exposure:
db.get_stocks_by_china_exposure(0.15)

# All geographic facts for a stock:
db.get_edgar_facts(stock_uid, 'geographic_revenue')

# Scoring: China revenue map used to dampen beneficiary SC scores when China events are active
db.get_china_revenue_map()        # {stock_uid: china_pct}
db.get_active_china_events()      # active events where country_code='CN' or region contains China/Taiwan
```

---

### price_history
Daily OHLCV bars + corporate actions (dividends, splits) per stock. Enables charting,
backtesting, and dividend growth tracking. 6,808,808 rows after full history fetch.

| Column | Type | Notes |
|---|---|---|
| `price_history_uid` | INTEGER PK | |
| `stock_uid` | INTEGER FK → stocks | |
| `date` | TEXT | YYYY-MM-DD — UNIQUE with stock_uid |
| `open`, `high`, `low` | REAL | |
| `close` | REAL | adjusted close |
| `volume` | INTEGER | |
| `dividend` | REAL | per-share dividend paid on this date; 0.0 otherwise |
| `split_factor` | REAL | e.g. `4.0` for a 4:1 split; `1.0` = no split |

```python
# Fetch via yfinance:
df = yf.Ticker('AAPL').history(period='5y')
# df columns: Open, High, Low, Close, Volume, Dividends, Stock Splits
```

---

### settings
Per-user key/value preferences. Persisted across sessions. All settings are user-scoped.

| Column | Type | Notes |
|---|---|---|
| `setting_uid` | INTEGER PK | |
| `user_uid` | INTEGER FK → users | NOT NULL — all settings belong to a user |
| `key` | TEXT | setting name, UNIQUE with user_uid |
| `value` | TEXT | stored as string; parse in caller |
| `updated_at` | TEXT | |

```python
# Read a setting (with default):
db.get_setting(user_uid, "theme", default="dark")

# Write/update a setting:
db.set_setting(user_uid, "scan_top_n", "25")

# Read all settings for a user:
db.get_all_settings(user_uid)  # → {"theme": "dark", "scan_top_n": "25", ...}
```


---

**Indexes:**
- `idx_news_articles_source_pub` on `(source, published_at DESC)` — News tab filter queries

### news_articles
Headlines, transcripts, and article text from all news sources. One row per article/episode.
Ticker mentions from each article create rows in `source_signals`.

| Column | Type | Notes |
|---|---|---|
| `article_uid` | INTEGER PK | |
| `stock_uid` | INTEGER FK → stocks | Primary ticker — nullable |
| `source` | TEXT | `wsj_podcast` · `wsj_pdf` · `morgan_stanley_podcast` · `motley_fool_podcast` · `yahoo_finance_news` · `ap_news` · `cnbc` · `marketwatch` · `newsapi` · `gdelt` |
| `headline` | TEXT | Article headline or podcast episode title |
| `summary` | TEXT | Short description or RSS teaser |
| `body` | TEXT | Full transcript or article text |
| `url` | TEXT | Audio URL, article URL, or absolute PDF path — UNIQUE with source |
| `published_at` | TEXT | |
| `sentiment` | REAL | NULL until sentiment scoring added |
| `llm_classified` | INTEGER | 1 = already processed by classify_news LLM job; 0 = pending |
| `fetched_at` | TEXT | |

```python
# Store an article:
db.upsert_news_article({"source": "wsj_podcast", "headline": "...", "url": "...", ...})

# Fetch recent articles:
db.get_news_articles(source="wsj_pdf", limit=10)
db.get_news_articles_for_stock(stock_uid, limit=20)
```

---

### llm_jobs
Job queue for LLM extraction work. Serialises all LLM calls through a single worker process
to prevent VRAM deadlock on 8GB GPUs. Processed by `llm.py --worker`.

| Column | Type | Notes |
|---|---|---|
| `job_uid` | INTEGER PK | |
| `job_type` | TEXT | `classify_news` · `extract_10k` · `parse_8k` |
| `status` | TEXT | `pending` · `running` · `done` · `failed` · `paused` · `cancelled` |
| `priority` | INTEGER | 1 (highest) – 9 (lowest); default 5 |
| `input_json` | TEXT | JSON input payload for the job |
| `result_json` | TEXT | JSON result, populated on completion |
| `error_text` | TEXT | error message if status = `failed` |
| `retries` | INTEGER | retry count; max 3 before `failed` |
| `source_ref` | TEXT | freeform back-reference (e.g. `article_uid:42` or `cik:0001234`) |
| `created_at` | TEXT | |
| `started_at` | TEXT | |
| `completed_at` | TEXT | |

```python
# Enqueue a job:
db.enqueue_llm_job(job_type='classify_news', input_json='{"article_uid": 42, ...}', priority=5)

# Worker loop pattern (used by llm.py --worker):
job = db.dequeue_next_llm_job()     # returns highest-priority pending job, marks running
db.complete_llm_job(job_uid, result_json)
db.fail_llm_job(job_uid, error_text)

# Queue controls from scraper_app Queue tab:
db.pause_llm_jobs(job_type)         # set status=paused for all pending of given type
db.resume_llm_jobs(job_type)        # set status=pending for all paused of given type
db.cancel_llm_jobs(job_type)        # set status=cancelled for all pending/paused
db.set_job_priority(job_type, priority)   # update priority for all pending/paused
db.get_distinct_job_types()         # list of job types with pending counts
```


---

### newsapi_keywords
Per-user keyword list for NewsAPI searches. Used by `news.py --newsapi` to drive keyword
queries without hardcoding terms.

| Column | Type | Notes |
|---|---|---|
| `keyword_uid` | INTEGER PK | |
| `user_uid` | INTEGER FK → users | |
| `keyword` | TEXT | search term, UNIQUE with user_uid |
| `enabled` | INTEGER | 1 = active (default); 0 = disabled |
| `created_at` | TEXT | |


---

### newsapi_sources
NewsAPI source catalog, cached from the NewsAPI `/sources` endpoint. Used to populate
the Sources tab dropdown and allow per-source filtering in `news.py`.

| Column | Type | Notes |
|---|---|---|
| `source_uid` | INTEGER PK | |
| `user_uid` | INTEGER FK → users | scoped per user |
| `source_id` | TEXT | NewsAPI source ID (e.g. `reuters`) — UNIQUE with user_uid |
| `name` | TEXT | human-readable source name |
| `category` | TEXT | `business` · `general` · `technology` etc. |
| `country` | TEXT | ISO 3166-1 alpha-2 |
| `language` | TEXT | ISO 639-1 code |
| `enabled` | INTEGER | 1 = active; 0 = disabled (default 0) |

---

### scheduled_jobs
Persistent pipeline scheduler. Each row is a recurring job that fires automatically
when `interval_hours` have elapsed since `last_run_at`. Managed from the Schedule tab
in `scraper_app.py`.

| Column | Type | Notes |
|---|---|---|
| `schedule_uid` | INTEGER PK | |
| `label` | TEXT | human label matching `_COMMANDS` button label |
| `command_key` | TEXT | argv[1] fragment used as stable lookup key |
| `interval_hours` | REAL | fire again after this many hours (default 24) |
| `enabled` | INTEGER | 1 = active; 0 = paused |
| `last_run_at` | TEXT | ISO datetime of last execution; NULL = never run |
| `created_at` | TEXT | DEFAULT datetime('now') |

---

## Key Query Patterns

```sql
-- Enrichment staleness check
SELECT ticker FROM stocks
WHERE last_enriched_at IS NULL
   OR last_enriched_at < datetime('now', '-1 days')
ORDER BY last_enriched_at ASC NULLS FIRST;

-- Watchlist stocks
SELECT * FROM stocks WHERE watchlist_uid = ? AND is_watched = 1;

-- Top scan results with stock info
SELECT sr.composite_rank, s.ticker, s.sector, sr.composite_score
FROM scan_results sr
JOIN stocks s USING (stock_uid)
WHERE sr.scan_uid = ?
ORDER BY sr.composite_rank ASC;

-- Active supply chain events (for map)
SELECT * FROM supply_chain_events
WHERE status = 'active'
ORDER BY severity DESC, detected_at DESC;

-- Congressional trades for a stock
SELECT reason_text, signal_type, fetched_at
FROM source_signals
WHERE stock_uid = ? AND source IN ('senate_watcher', 'house_watcher')
ORDER BY fetched_at DESC;

-- Upcoming IPOs (next 30 days)
SELECT title, event_date, ipo_price_low, ipo_price_high
FROM calendar_events
WHERE event_type = 'ipo'
  AND event_date BETWEEN date('now') AND date('now', '+30 days')
ORDER BY event_date;

-- Upcoming dividend events (next 30 days)
SELECT ce.event_type, ce.event_date, ce.title, s.ticker
FROM calendar_events ce
JOIN stocks s USING (stock_uid)
WHERE ce.event_type IN ('ex_dividend', 'dividend_pay')
  AND ce.event_date BETWEEN date('now') AND date('now', '+30 days')
ORDER BY ce.event_date;

-- Dividend history for a stock (growth tracking)
SELECT date, dividend
FROM price_history
WHERE stock_uid = ? AND dividend > 0
ORDER BY date ASC;

-- Last 1 year of daily closes
SELECT date, close, volume
FROM price_history
WHERE stock_uid = ? AND date >= date('now', '-1 year')
ORDER BY date ASC;

-- Recent news for a stock
SELECT headline, source, published_at FROM news_articles
WHERE stock_uid = ? ORDER BY published_at DESC LIMIT 20;

-- Pending LLM jobs (ordered by priority then enqueue time)
SELECT * FROM llm_jobs
WHERE status = 'pending'
ORDER BY priority ASC, enqueued_at ASC;

-- LLM job queue stats by type
SELECT job_type, status, COUNT(*) as cnt
FROM llm_jobs
GROUP BY job_type, status
ORDER BY job_type, status;
```
