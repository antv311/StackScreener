# CLAUDE.md — Coding Conventions for StackScreener

This file tells Claude Code how to work on this project. Read it before making any changes.
Always read `CONTEXT.md` first for full project context, and `ROADMAP.md` to confirm what
phase is active before writing any code.

---

## Project Identity

- **Repo:** https://github.com/antv311/StackScreener
- **Built from scratch**
- **Runtime:** Python 3.14.2 only
- **venv name:** `venv_ss`
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

Watchlist query pattern (canonical):
```python
db.get_watchlist_stocks(watchlist_uid)
# → SELECT * FROM stocks WHERE watchlist_uid = ? AND is_watched = 1
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

- All weights, thresholds, scoring constants live in `screener_config.py`
- Score components: EV/R, P/E, EV/EBITDA, profit margin, PEG, debt/equity, CFO ratio, Altman Z
- Supply chain signal score is additive on top of fundamental score (configurable weight)
- Composite score across Quiver Quant + Unusual Whales + Yahoo Finance + Motley Fool sources

---

## UI Screens (Textual TUI — app.py)

Match the agreed design. Three sidebar sections, each with its own screen:

1. **Home** — heatmap display + index selector
2. **Research** — tabbed: Screener / Calendar / Stock Comparison / Stock Picks / Research Reports
3. **Logistics** — world map with disruption pins + company redirect table

Do not invent new screens or reorganize navigation without confirming first.

---

## Style Rules

- Functional programming — avoid sprawling class hierarchies
- Small, focused functions with a single responsibility
- `frozenset` for constant set membership checks
- `dataclasses.fields()` for iterating model fields — not hand-rolled field lists
- Imports: stdlib → third-party → local, one blank line between groups

---

## yahooquery

- Timestamp dict keys must be converted to strings before use
- Always filter annual data with `periodType == '12M'`
- JSON save block must come after yahooquery assignments, not before

---

## Output & Results

- All scan output goes to `Results/<scan_mode>/<datetime>/`
- `Results/` is gitignored — never commit scan output
- PDF generation uses fpdf2 — see `pdf_generator.py`

---

## Git / .gitignore

Must include:
```
venv_ss/
builds/
__pycache__/
*.pyc
Results/
stackscreener.db
*.db
```

---

## When Adding a New Feature

1. Check `ROADMAP.md` — confirm it's in scope for the current phase
2. Config/constants → `screener_config.py`
3. DB changes → `db.py` (update `init_db()` + add helpers; update `sql_tables/` to match)
4. Encryption/auth changes → `crypto.py` only
5. Business logic → appropriate module (`screener.py`, `supply_chain.py`, etc.)
6. UI changes → `app.py` only
7. Update `CONTEXT.md` if the architecture or file structure changes

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
