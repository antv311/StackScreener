# CLAUDE.md — Coding Conventions for StackScreener

This file tells Claude Code how to work on this project. Read it before making any changes.
Always read `CONTEXT.md` first for full project context, and `ROADMAP.md` to confirm which
project and backlog item is in scope before writing any code. Also review `tree.md` and
`DATABASE.md` for the full file structure and schema.

The project is structured as four independent projects (P1 Data Scraper, P2 DB & Server,
P3 Bloomberg TUI, P4 Web). Each has its own entry point and backlog in `ROADMAP.md`.
Shared core: `db.py`, `screener_config.py`, `crypto.py`, `screener.py`, `screener_run.py`.

---

## Project Identity

- **Repo:** https://github.com/antv311/StackScreener
- **Built from scratch**
- **Runtime:** Python 3.14.2 only
- **venv:** `venv/` (at repo root — activate with `venv\Scripts\activate`)
- **DB file:** `stackscreener.db`

---

## Language & Runtime Rules

- Python 3.14.2 — do not use any syntax or API not supported in 3.14
- f-strings only — no `.format()` or `%` formatting anywhere
- Type hints on all new functions
- `match-case` preferred over long `if-elif` chains on string/enum values
- No `print()` for debug output — use `if DEBUG_MODE:` from `screener_config.py`

---

## Forbidden Patterns

Never introduce these — they are banned:

| Pattern | Use instead |
|---|---|
| `df.fillna(method='ffill')` | `df.ffill()` |
| `df.fillna(method='bfill')` | `df.bfill()` |
| `frame.insert()` in a loop | `pd.concat()` |
| `forex_python` | `CurrencyConverter` |
| `fpdf` / `HTMLMixin` | `fpdf2` API |
| `numba` (any usage) | Not available on 3.14 — never add |
| `pandas-ta` with numba deps | Always install with `--no-deps` |
| Long `if-elif` on string values | `match-case` |
| Hardcoded constants anywhere | Move to `screener_config.py` |
| `shutil.move()` without guard | Wrap with `os.path.exists()` check |
| Raw `print()` for debug | `if DEBUG_MODE: print(...)` |
| Raw SQL outside `db.py` | All DB access goes through `db.py` only |
| String-formatted SQL | Always use parameterized queries (`?`) |
| Plaintext API keys anywhere | Always encrypted via `db.set_api_key()` |
| `crypto.encrypt/decrypt` outside `db.py` | Only `db.py` calls crypto directly |
| `db.query()` called directly from UI/business code | Add a named helper to `db.py` instead |

---

## File Responsibilities

Each file owns exactly one concern. Do not cross these boundaries.

| File | Project | Owns |
|---|---|---|
| `screener_config.py` | Shared | ALL constants, weights, thresholds, status strings, `DEBUG_MODE` |
| `db.py` | Shared | All SQLite reads/writes — no other file touches the DB |
| `crypto.py` | Shared | Fernet encryption + OS keyring key management + password hashing |
| `seeder.py` | Shared | One-time schema init, default user seed, NYSE/NASDAQ universe fetch |
| `screener.py` | Shared | Core scoring logic only — no hardcoded magic numbers |
| `screener_run.py` | Shared | CLI entry point and scan orchestration only |
| `enricher.py` | P1 | Background fundamentals worker + daily IPO calendar check |
| `supply_chain.py` | P1 | Supply chain signal ingestion and sector mapping only |
| `edgar.py` | P1 | SEC EDGAR pipeline: CIK seeding, XBRL facts, 10-K text extraction |
| `news.py` | P1 | News/media aggregation + ticker tagging |
| `inst_flow.py` | P1 | Congressional trades (Senate + House) + SEC Form 4/13F ingestion |
| `scraper_app.py` | P1 | Data Scraper TUI — logs, manual triggers, source manager, LLM panel |
| `db_app.py` | P2 | Database & Server TUI — SQL shell, table browser, API server controls |
| `app.py` | P3 | Bloomberg TUI (Textual) — UI only, no business logic |
| `pdf_generator.py` | P3 | PDF output only — fpdf2 API |
| `mailer.py` | P4 | Email delivery only |

---

## Database Conventions

- All PKs: `tablename_uid` (e.g. `stock_uid`, `scan_uid`, `watchlist_uid`)
- All DB access through `db.py` — never raw SQL in other modules
- Always use parameterized queries — never f-string or format SQL
- Staleness tracked via `last_enriched_at` on `stocks` — enricher checks this
- All status/type string values come from constants in `screener_config.py`
- Always scope stock queries to active stocks with `AND delisted = 0` unless explicitly including delisted
- Use `db.get_pending_enrichment()` / `db.get_pending_history()` rather than rebuilding those filters inline
- Use `db.get_watched_tickers()` for watchlist ticker lists; `db.get_stocks_by_tickers(list)` for batch stock lookups; `db.get_news_article_urls(source)` for PDF deduplication
- Use `db.insert_scan_results_batch(rows)` — not per-row `insert_scan_result()` — when persisting full scan output
- Use `if param is not None:` not `if param:` when conditionally appending to a query — `0` and empty string are valid parameter values
- New query helpers that filter or paginate data belong in `db.py`, not in the calling module
- Migrations go in `_migrate_db()` in `db.py` — one `ALTER TABLE` per new column, wrapped in `try/except OperationalError`
- Covering indexes also go in `_migrate_db()` using `CREATE INDEX IF NOT EXISTS` — **not** in `executescript`, because they may reference columns added by migrations that run after `executescript`

Watchlist query pattern (canonical):
```python
db.get_watchlist_stocks(watchlist_uid)
# → SELECT * FROM stocks WHERE watchlist_uid = ? AND is_watched = 1
```

Pending enrichment pattern (canonical):
```python
db.get_pending_enrichment(limit, skip_delisted=True)
db.get_pending_history(limit, skip_delisted=True)
```

Settings pattern (user-scoped):
```python
db.get_setting(user_uid, "theme", default="dark")
db.set_setting(user_uid, "theme", "light")
```

---

## Security Conventions

- API keys are stored encrypted in the `api_keys` table via `db.set_api_key()`
- Retrieve with `db.get_api_key(user_uid, provider_name)` — returns plaintext only in memory
- Fernet master key lives in the OS keyring, never on disk or in code
- Passwords hashed with PBKDF2-HMAC-SHA256, 260k iterations, random per-user salt
- Default admin account (`admin/admin`) must force password change on first login
- `totp_secret` column on `users` is reserved for future 2FA — do not populate yet

---

## Scoring & Config

- All weights, thresholds, and scoring constants live in `screener_config.py`
- Score components: EV/R, P/E, EV/EBITDA, profit margin, PEG, debt/equity, CFO ratio, Altman Z (0–100 each; `None` → 50 neutral)
- `score_cfo_ratio` and `score_altman_z` return 50 until balance sheet data is seeded — do not remove these placeholders
- Supply chain and inst flow are **additive overlays** on top of the fundamental base (max +20 pts each at default weights of 1.5)
- Scan modes: `nsr` (all active stocks), `thematic` (event-sector filtered), `watchlist` (named list) — constants in `SCAN_MODE_*`
- Institutional flow sources (all free, no paid keys): Senate/House Stock Watcher (congressional trades), SEC EDGAR Form 4 (insider trades), SEC EDGAR Form 13F (institutional holdings), yfinance options chain

---

## UI Conventions (P3 Bloomberg TUI — app.py)

Match the agreed design from `CONTEXT.md` and `Mock_up/`. Three sidebar sections:

1. **Home** — DB stats summary + last scan summary (heatmap in P3 next)
2. **Research** — six tabs: Screener · Calendar · Stock Comparison · Stock Picks · Research Reports · News
3. **Logistics** — active supply chain events table (world map in P3 next)

**Research tab conventions:**
- `ScreenerTab` — filter dropdowns (Exchange/Sector/MCap/P/E/Signal) + DataTable; filter in-memory after one DB load; cap display at 200 rows; Enter on row → `StockQuoteModal`
- `CalendarTab` — DayCell widgets in a 7-column Horizontal; `_week_offset` reactive drives week navigation; filter buttons per event type
- `StockComparisonTab` — 4 ticker inputs → `db.get_stock_by_ticker()` lookups → DataTable with section headers and ▲/▼ highlights; remount DataTable on each compare to reset columns
- `StockPicksTab` — Collapsible cards for top 15 scan results; source signals from `db.get_stock_signals()`; "Open Quote →" button per card → `StockQuoteModal`
- `ResearchReportsTab` — Static cards from `db.get_research_reports()`; handles empty state
- `NewsTab` — filter buttons per source; `db.get_news_articles()` with LEFT JOIN for ticker

**`StockQuoteModal` conventions:**
- `ModalScreen[None]` — triggered by Enter (Screener) or button click (Picks); ESC/Q to dismiss
- All data loaded from DB on mount — no network calls; 4 tabs: Overview, Signals, History, News
- Overview renders a single `Static` with markup via `"\n".join(parts)` — do not mount per-row widgets
- History uses `db.get_price_history(stock_uid, start_date=...)` — last 365 days, most recent first

Do not invent new screens or reorganize navigation without confirming first.

---

## Style Rules

- Functional programming — avoid sprawling class hierarchies
- Small, focused functions with a single responsibility
- `frozenset` for constant set membership checks
- `dataclasses.fields()` for iterating model fields — not hand-rolled field lists
- Imports: stdlib → third-party → local, one blank line between groups
- Utility/formatting helpers in `app.py` (`_fmt_mcap`, `_fmt_pct`, `_fmt_ratio`, `_score_bar`) — keep them at module level, not inside classes

---

## yahooquery

- Timestamp dict keys must be converted to strings before use
- Always filter annual data with `periodType == '12M'`
- JSON save block must come after yahooquery assignments, not before

---

## Output & Results

- All scan output goes to `src/Results/<scan_mode>/<datetime>/`
- `Results/` is gitignored — never commit scan output
- PDF generation uses fpdf2 — see `pdf_generator.py`

---

## Git / .gitignore

Must include:
```
venv/
builds/
__pycache__/
*.pyc
Results/
src/News/audio/
src/News/pdfs/
stackscreener.db
*.db
```

---

## When Adding a New Feature

1. Check `ROADMAP.md` — confirm which project (P1/P2/P3/P4) owns it and that it's in the backlog
2. Config/constants → `screener_config.py`
3. DB changes → `db.py`:
   - Add column to `init_db()` CREATE TABLE
   - Add migration to `_migrate_db()` (ALTER TABLE, catches OperationalError)
   - Add covering indexes to `_migrate_db()` index_migrations list (never in executescript)
   - Update matching file in `sql_tables/`
   - Update `DATABASE.md`
4. Encryption/auth changes → `crypto.py` only
5. Business logic → appropriate module (`screener.py`, `supply_chain.py`, `edgar.py`, etc.)
6. UI changes → `app.py` only
7. Update `CONTEXT.md`, `tree.md`, and `ROADMAP.md` to reflect the new state

---

## Never Do These

- Don't refactor code that isn't broken unless it's explicitly in scope
- Don't add dependencies without verifying Python 3.14 compatibility first
- Don't write to the DB from anywhere except `db.py`
- Don't call `crypto.py` functions from anywhere except `db.py`
- Don't hardcode tickers, weights, thresholds, or status strings outside `screener_config.py`
- Don't commit `.db` files or scan results
- Don't reorganize the UI navigation without confirming the change first
- Don't store API keys or secrets in flat files, env vars, or source code
- Don't put `CREATE INDEX` statements inside `executescript` — they must go in `_migrate_db()` so they run after column migrations
