# CLAUDE.md — Coding Conventions for StackScreener

This file tells Claude Code how to work on this project. Read it before making any changes.
Always read `CONTEXT.md` first for full project context, and `ROADMAP.md` to confirm what
phase is active before writing any code. Also review `tree.md` and `DATABASE.md` for
the full file structure and schema.

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

| File | Owns |
|---|---|
| `screener_config.py` | ALL constants, weights, thresholds, status strings, provider names, `DEBUG_MODE` |
| `db.py` | All SQLite reads/writes — no other file touches the DB |
| `crypto.py` | Fernet encryption + OS keyring key management + password hashing |
| `seeder.py` | One-time schema init, default user seed, NYSE/NASDAQ universe fetch |
| `enricher.py` | Background fundamentals worker + daily IPO calendar check |
| `screener.py` | Core scoring logic only — no hardcoded magic numbers |
| `screener_run.py` | CLI entry point and scan orchestration only |
| `supply_chain.py` | Supply chain signal ingestion and sector mapping only |
| `edgar.py` | SEC EDGAR XBRL pipeline (CIK seeding + facts fetch) only |
| `news.py` | News/media aggregation + ticker tagging only *(Phase 2d)* |
| `inst_flow.py` | Congressional trades + SEC insider/13F ingestion only *(Phase 3)* |
| `app.py` | Desktop TUI (Textual) — UI only, no business logic |
| `pdf_generator.py` | PDF output only — fpdf2 API |
| `mailer.py` | Email delivery only |

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

## UI Conventions (Textual TUI — app.py)

Match the agreed design from `CONTEXT.md` and `Mock_up/`. Three sidebar sections:

1. **Home** — DB stats summary + last scan summary (heatmap in Phase 1b)
2. **Research** — five tabs: Screener · Calendar · Stock Comparison · Stock Picks · Research Reports
3. **Logistics** — active supply chain events table (world map in Phase 1d)

**Research tab conventions:**
- `ScreenerTab` — filter dropdowns (Exchange/Sector/MCap/P/E/Signal) + DataTable; filter in-memory after one DB load; cap display at 200 rows
- `CalendarTab` — DayCell widgets in a 7-column Horizontal; `_week_offset` reactive drives week navigation; filter buttons per event type
- `StockComparisonTab` — 4 ticker inputs → `db.get_stock_by_ticker()` lookups → DataTable with section headers and ▲/▼ highlights; remount DataTable on each compare to reset columns
- `StockPicksTab` — Collapsible cards for top 15 scan results; source signals from `db.get_stock_signals()`
- `ResearchReportsTab` — Static cards from `db.get_research_reports()`; handles empty state with Phase 2 context message

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

1. Check `ROADMAP.md` — confirm it's in scope for the current phase
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
