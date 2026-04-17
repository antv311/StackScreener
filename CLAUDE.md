# CLAUDE.md — Coding Conventions for StackScreener

This file tells Claude Code how to work on this project. Read it before making any changes.
Always read `CONTEXT.md` first for full project context, and `ROADMAP.md` to confirm what
phase is active before writing any code.

---

## Project Identity

- **Repo:** https://github.com/antv311/StackScreener
- **Built from scratch** — this is NOT a fork of asafravid/sss
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

---

## File Responsibilities

Each file owns exactly one concern. Do not cross these boundaries.

| File | Owns |
|---|---|
| `screener_config.py` | ALL constants, weights, thresholds, scoring config, `DEBUG_MODE` |
| `screener.py` | Core scoring logic only — no hardcoded magic numbers |
| `screener_run.py` | CLI entry point and scan orchestration only |
| `db.py` | All SQLite reads/writes — no other file touches the DB |
| `supply_chain.py` | Supply chain signal ingestion and sector mapping only |
| `app.py` | Desktop TUI (Textual) — UI only, no business logic |
| `pdf_generator.py` | PDF output only — fpdf2 API |
| `mailer.py` | Email delivery only |

---

## Database Conventions

- All PKs: `tablename_uid` (e.g. `stock_uid`, `scan_uid`, `watchlist_uid`, `event_uid`)
- All DB access through `db.py` — never raw SQL in other modules
- Always use parameterized queries — never f-string or format SQL
- Staleness tracking on `stock_financials` — check before fetching fresh data
- `supply_chain_events` table tracks active disruptions with affected/beneficiary sectors

Watchlist query pattern (canonical):
```python
db.query("SELECT * FROM stocks WHERE watchlist_uid = ? AND is_watched = 1", (wl_id,))
```

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
3. DB changes → `db.py` (add a migration function if schema changes)
4. Business logic → appropriate module (`screener.py`, `supply_chain.py`, etc.)
5. UI changes → `app.py` only
6. Update `CONTEXT.md` if the architecture or file structure changes

---

## Never Do These

- Don't refactor code that isn't broken unless it's explicitly in scope
- Don't add dependencies without verifying Python 3.14 compatibility first
- Don't write to the DB from anywhere except `db.py`
- Don't hardcode tickers, weights, or thresholds outside `screener_config.py`
- Don't commit `.db` files or scan results
- Don't reorganize the UI navigation without confirming the change first
