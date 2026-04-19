# StackScreener — Database Map

All tables live in `stackscreener.db`. All access goes through `db.py` only.
Schema is created by `db.init_db()`. Migrations (new columns) run automatically on startup.

---

## Relationship Diagram

```
users
 ├── watchlists          (user_uid → users)
 │    └── stocks         (watchlist_uid → watchlists)
 ├── api_keys            (user_uid → users)
 └── portfolio           (user_uid → users, stock_uid → stocks)

stocks
 ├── scan_results        (stock_uid → stocks)
 ├── event_stocks        (stock_uid → stocks)
 ├── calendar_events     (stock_uid → stocks)
 ├── source_signals      (stock_uid → stocks)
 ├── research_reports    (stock_uid → stocks)
 ├── portfolio           (stock_uid → stocks)
 └── price_history       (stock_uid → stocks)

scans
 └── scan_results        (scan_uid → scans)

supply_chain_events
 ├── event_stocks        (supply_chain_event_uid → supply_chain_events)
 └── research_reports    (supply_chain_event_uid → supply_chain_events)
```

**Creation order** (respects FK deps):
`users → watchlists → stocks → api_keys → portfolio → scans → scan_results → supply_chain_events → event_stocks → calendar_events → source_signals → research_reports → price_history`

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
Every tracked NYSE/NASDAQ symbol. ~6,900 rows after seeding. Enriched in background by `enricher.py`.

| Column | Type | Notes |
|---|---|---|
| `stock_uid` | INTEGER PK | |
| `watchlist_uid` | INTEGER FK → watchlists | NULL if not on a watchlist |
| `is_watched` | INTEGER | 1 = on watchlist |
| `ticker` | TEXT | UNIQUE with exchange |
| `exchange` | TEXT | NASDAQ / NYSE / NYSE ARCA |
| `market_index` | TEXT | |
| `sector`, `industry` | TEXT | GICS |
| `country` | TEXT | |
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
| `last_enriched_at` | TEXT | NULL = never enriched; staleness check |
| `macro_signal` | TEXT | reserved for macro overlay |
| `delisted` | INTEGER | 0 = active (default), 1 = delisted — skipped by enricher and scans |

**Indexes:**
- `idx_stocks_delisted_enriched` on `(delisted, last_enriched_at)` — covers enrichment staleness query
- `idx_stocks_delisted_price` on `(delisted, price)` — covers price history pending query

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
Fernet-encrypted API credentials per user. `url` allows storing any REST endpoint generically.

| Column | Type | Notes |
|---|---|---|
| `api_uid` | INTEGER PK | |
| `user_uid` | INTEGER FK → users | |
| `name` | TEXT | provider label — UNIQUE per user |
| `api_key` | TEXT | **Fernet-encrypted** — never plaintext |
| `url` | TEXT | base URL of endpoint (optional) |
| `created_at`, `updated_at` | TEXT | |

```python
# Store:  db.set_api_key(user_uid, 'senate_watcher', 'my-key', url='https://...')
# Fetch:  db.get_api_key(user_uid, 'senate_watcher')  # returns plaintext in memory only
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
`conflict` · `sanctions` · `weather` · `labor` · `accident` · `port_blockage` · `factory_shutdown` · `pandemic`

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
Earnings, splits, IPOs, economic events. IPOs pre-seeded by `enricher.py` daily.

| Column | Type | Notes |
|---|---|---|
| `calendar_event_uid` | INTEGER PK | |
| `stock_uid` | INTEGER FK → stocks | nullable for macro events |
| `event_type` | TEXT | `earnings` / `split` / `ipo` / `economic` |
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

---

### source_signals
Per-stock signals from congressional trades, SEC filings, and options flow.

| Column | Type | Notes |
|---|---|---|
| `source_signal_uid` | INTEGER PK | |
| `stock_uid` | INTEGER FK → stocks | |
| `source` | TEXT | `senate_watcher` · `house_watcher` · `sec_form4` · `sec_13f` · `yahoo_finance` · `options_flow` |
| `sub_score` | REAL | 0–100 score from this source |
| `reason_text` | TEXT | shown in Stock Picks card |
| `signal_type` | TEXT | `congress_buy` · `insider_buy` · `inst_accumulation` · `options_flow` · `analyst_rec` |
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

### price_history
Daily OHLCV bars + corporate actions (dividends, splits) per stock. Enables charting, backtesting, and dividend growth tracking.

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
```
