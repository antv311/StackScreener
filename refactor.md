# Codebase Refactoring — Full Detailed Plan

## Context

Full audit of all 7 MDs and all 18 Python source files. The project is well-architected and
well-documented, but the code has grown faster than its own rules. This plan lists every
specific change, file by file, organized by risk tier.

---

## TIER 1 — Quick Wins (~90 min, near-zero risk)

These are small, isolated fixes that address the most egregious rule violations.
None of them change any function signatures or DB schema.

---

### T1-A: Fix personal email in User-Agent headers (15 min)

**Files:** `edgar.py`, `inst_flow.py`

`screener_config.py` already has `EDGAR_IDENTITY = "StackScreener antv311@gmail.com"`.
Both files should reference that constant instead of hardcoding the email.

- `edgar.py` line ~51: `_EDGAR_HEADERS = {"User-Agent": screener_config.EDGAR_IDENTITY, ...}`
- `inst_flow.py` line ~65: same pattern — replace the hardcoded string with `EDGAR_IDENTITY`

Also review `commodities.py` L43 and `logistics.py` L47 which have `*@stackscreener.local`
strings — move these to screener_config.py as `COMMODITIES_USER_AGENT` and `LOGISTICS_USER_AGENT`.

---

### T1-B: Move `_CONFIDENCE_MULT` to screener_config.py (10 min)

**Files:** `screener_run.py`, `screener_config.py`

`screener_run.py` lines 38-42 defines:
```python
_CONFIDENCE_MULT: dict[str, float] = {"high": 1.5, "medium": 1.0, "low": 0.6}
```
This is scoring-related config. Move to `screener_config.py` as `SC_CONFIDENCE_MULT`.
Update `screener_run.py` to import it from config.

---

### T1-C: Remove legacy podcast constants from screener_config.py (20 min)

**Files:** `screener_config.py`, `app.py`

`screener_config.py` lines 317-322 has deprecated individual constants:
```python
WSJ_PODCAST_FEEDS = [...]           # legacy
MORGAN_STANLEY_PODCAST_FEED = ...   # legacy
MOTLEY_FOOL_PODCAST_FEED = ...      # legacy
```
These were superseded by `PODCAST_FEEDS` (lines 306-314).
`app.py` lines 39-41 still imports the legacy names.

Fix: Update `app.py` to use `PODCAST_FEEDS` directly; delete the 3 legacy constants.

---

### T1-D: Move UI filter config dicts from app.py to screener_config.py (45 min)

**Files:** `app.py`, `screener_config.py`

These dicts live in `app.py` but are configuration, not UI logic:

| Variable in app.py | Lines | Move to screener_config.py as |
|---|---|---|
| `_MCAP_BUCKETS` | 659-664 | `SCREENER_MCAP_BUCKETS` |
| `_PE_BUCKETS` | 666-673 | `SCREENER_PE_BUCKETS` |
| `_HEATMAP_FILTERS` | 1514-1520 | `HEATMAP_FILTERS` |
| `_HEAT_COLORS` | 1335-1342 | `HEATMAP_COLORS` |
| `_SOURCE_LABELS` | 1086-1093 | `SIGNAL_SOURCE_LABELS` |
| `_EVENT_STYLE` | 796-813 | `CALENDAR_EVENT_STYLES` |

`_SIGNAL_FILTERS` (lines 674-676) is a dict of lambdas — this cannot move to config (lambdas in config are bad). Leave it in app.py.

After moving each dict, update `app.py` to import the new constant names.

---

### T1-E: Fix sys.path hacks in commodities.py and logistics.py (10 min)

**Files:** `commodities.py` L28, `logistics.py` L31

Both files do:
```python
sys.path.insert(0, __file__.replace("commodities.py", ""))
import db
```
Other modules just `import db` with PYTHONPATH=src in the environment.
The scraper_app already sets `env["PYTHONPATH"] = _SRC` for all subprocesses.

Fix: Remove the `sys.path.insert()` lines. The modules will import correctly when
called via scraper_app (which sets PYTHONPATH) or via `python src/commodities.py` from
the project root (which needs `PYTHONPATH=src` or `python -m` invocation).
Add a note in README that all scripts must be run from project root with `PYTHONPATH=src`.

---

### T1-F: Fix raw SQL in HomePanel._load_stats() in app.py (20 min)

**Files:** `app.py` lines 1567-1570, `db.py`

`HomePanel._load_stats()` has 3 raw SQL queries:
```python
db.query("SELECT COUNT(*) AS n FROM stocks WHERE delisted = 0")
db.query("SELECT COUNT(*) AS n FROM stocks WHERE last_enriched_at IS NOT NULL AND delisted = 0")
db.query("SELECT COUNT(*) AS n FROM scans ORDER BY scan_uid DESC LIMIT 1")
```
Add three named helpers to `db.py`:
- `db.get_active_stock_count() -> int`
- `db.get_enriched_stock_count() -> int`
- `db.get_last_scan() -> dict | None` (already exists as `get_recent_scans(1)` — just use that)

Update `HomePanel._load_stats()` to call these helpers.

---

## TIER 2 — SQL Centralization ✅ DONE (2026-04-25)

> All Tier 3 and Tier 4 tasks completed 2026-04-27.

**Core rule:** "All DB access goes through db.py only — never raw SQL in other modules."

16 raw `db.query()` calls removed across 5 P1 modules. 12 named helpers added to db.py.

---

### T2-A: edgar.py inline SQL (10 queries → db.py helpers)

**File:** `edgar.py` (5+ raw query sites), `db.py`

Queries to extract:

| Current inline query | New db.py function |
|---|---|
| SELECT stocks WHERE cik IS NULL | `db.get_stocks_missing_cik(limit) -> list[dict]` |
| SELECT stocks JOIN edgar_facts WHERE 10-K not fetched | `db.get_stocks_pending_10k(limit) -> list[dict]` |
| SELECT stocks WHERE cik IS NOT NULL for 8-K scan | `db.get_stocks_with_cik(limit) -> list[dict]` |
| SELECT edgar_facts WHERE fact_type = 'geographic_revenue' AND stock_uid | `db.get_edgar_facts_by_type(stock_uid, fact_type) -> list[dict]` (may already exist) |
| Multi-join query for filing staleness | `db.get_stale_10k_stocks(limit) -> list[dict]` |

---

### T2-B: inst_flow.py inline SQL (5 queries → db.py helpers)

**File:** `inst_flow.py`, `db.py`

| Current inline query | New db.py function |
|---|---|
| SELECT stocks WHERE cik IS NOT NULL | `db.get_stocks_with_cik(limit)` (shared with edgar) |
| DELETE FROM source_signals WHERE stock_uid+source | `db.delete_signals_for_stock(stock_uid, source)` |
| Complex 13F position diff loop query | `db.get_source_signals_for_stock(stock_uid, source) -> list[dict]` |
| SELECT for congressional trade dedup | Use existing `db.signal_exists_by_url()` (some callers already do this) |

---

### T2-C: commodities.py + logistics.py inline SQL (6 queries → db.py helpers)

**Files:** `commodities.py`, `logistics.py`, `db.py`

| File | Current inline query | New db.py function |
|---|---|---|
| commodities.py | SELECT stocks WHERE sector IN (dynamic list) | `db.get_stocks_by_sectors(sectors: list[str]) -> list[dict]` |
| logistics.py | SELECT source_signals for baseline vessel counts | `db.get_baseline_vessel_counts(chokepoint) -> dict` |
| logistics.py | SELECT stocks WHERE ticker IN chokepoint tickers | `db.get_stocks_by_tickers()` — already exists |
| logistics.py | SELECT supply_chain_events for active route events | `db.get_active_events_by_route(trade_route)` |

---

### T2-D: scraper_app.py inline SQL (2 queries → db.py helpers)

**File:** `scraper_app.py`, `db.py`

| Current inline query | New db.py function |
|---|---|
| SELECT api_keys WHERE user_uid + role (L590) | `db.get_api_keys_by_user(user_uid) -> list[dict]` (may exist) |
| SELECT connector_config WHERE provider (L837-841) | `db.get_api_key_config(user_uid, provider) -> dict | None` |

---

### T2-E: supply_chain.py inline SQL (1 query → db.py helper)

**File:** `supply_chain.py`, `db.py`

| Current inline query | New db.py function |
|---|---|
| SELECT stocks WHERE sector matches event sectors | `db.get_stocks_by_sectors(sectors)` (shared with T2-C) |

---

## TIER 3 — Shared HTTP Client + Unified Logging ✅ DONE (2026-04-27)

These two changes improve maintainability and debuggability significantly,
but require touching many call sites across all P1 modules.

---

### T3-A: Create `src/utils_http.py` — shared HTTP client ✅ DONE

**New file:** `src/utils_http.py` — `HttpClient` class injects default headers, no automatic rate limiting (modules manage their own `time.sleep()` calls to avoid double-sleeping).

**Updated:** `edgar.py`, `inst_flow.py`, `commodities.py`, `logistics.py` — replaced per-module `_HEADERS` dicts + raw `requests.get()` with `_client = HttpClient(...)` + `_client.get(...)`. Removed `import requests` from all four modules. `news.py` skipped (headers vary too much per call).

---

### T3-B: Replace `if DEBUG_MODE: print()` with `logging` module ✅ DONE

All `if DEBUG_MODE: print(...)` blocks replaced with `logger.debug(...)` across: `enricher.py`, `edgar.py`, `inst_flow.py`, `news.py`, `commodities.py`, `logistics.py`, `supply_chain.py`, `screener_run.py`, `wsj_fetcher.py`. Each module now has `import logging` + `logger = logging.getLogger(__name__)` + `logging.basicConfig(level=logging.DEBUG if DEBUG_MODE else logging.INFO, ...)` in `main()`.

---

## TIER 4 — Structural Cleanup ✅ DONE (2026-04-27)

---

### T4-A: Split news.py into submodules ✅ DONE

**New files:** `src/news_utils.py` (shared utilities), `src/news_podcast.py` (podcast + PDF pipeline), `src/news_feeds.py` (article RSS + NewsAPI + GDELT). `src/news.py` rewritten as ~230-line thin orchestrator — imports all functions from submodules, re-exports via `__all__` for backwards compat. Import DAG: `news_utils` ← `news_podcast` / `news_feeds` ← `news`.

---

### T4-B: Extract `_score_inverse()` in screener.py ✅ DONE

Added `_score_inverse(val, max_val)` helper after `_clamp()`. Replaced `_score_pe`, `_score_ev_revenue`, `_score_ev_ebitda`, `_score_peg` with one-liner calls. `_score_profit_margin` and `_score_debt_equity` kept unchanged (different patterns).

---

### T4-C: Split app.py into tui/ subpackage ✅ DONE

**New structure:**
```
src/tui/
    __init__.py      — StackScreenerApp
    formatters.py    — _fmt_mcap, _fmt_pct, _fmt_pct_abs, _fmt_ratio, _score_bar, _week_dates
    modals.py        — StockQuoteModal
    tabs.py          — ScreenerTab, DayCell, CalendarTab, StockComparisonTab, StockPicksTab, NewsTab, ResearchReportsTab
    panels.py        — NavItem, Sidebar, HeatmapTile, WorldMap, HomePanel, ResearchPanel, EventListItem, LogisticsPanel, SettingsPanel, MainScreen
    screens.py       — LoginScreen, ChangePasswordScreen
src/app.py           — 12-line entry point: from tui import StackScreenerApp
```

Import DAG (no circular imports): `formatters` ← `modals` ← `tabs` ← `panels` ← `screens` ← `__init__`.

---

## What Not To Touch

- `db.py` internal helpers — solid as-is
- `screener.py` scoring logic (other than T4-B)
- `seeder.py`, `crypto.py` — both small and clean
- `llm.py` VRAM handling — well-reasoned
- TUI navigation structure (sidebar sections, tab names, modal flows)
- DB schema (no table or column changes needed)

---

## Execution Order

| Order | Tier | Task | Status |
|---|---|---|---|
| 1 | T1-A | Email in User-Agents | ✅ Done (milestone 9) |
| 2 | T1-B | _CONFIDENCE_MULT to config | ✅ Done (milestone 9) |
| 3 | T1-C | Remove legacy podcast constants | ✅ Done (milestone 9) |
| 4 | T1-D | UI config dicts to screener_config | ✅ Done (milestone 9) |
| 5 | T1-E | Fix sys.path hacks | ✅ Done (milestone 9) |
| 6 | T1-F | HomePanel raw SQL → db.py | ✅ Done (milestone 9) |
| 7 | T2-A | edgar.py SQL → db.py helpers | ✅ Done (2026-04-25) |
| 8 | T2-B | inst_flow.py SQL → db.py helpers | ✅ Done (2026-04-25) |
| 9 | T2-C | commodities + logistics SQL | ✅ Done (2026-04-25) |
| 10 | T2-D | scraper_app SQL | ✅ Done (2026-04-25) |
| 11 | T2-E | supply_chain SQL | ✅ Done (2026-04-25) |
| 12 | T3-A | utils_http.py shared client | ✅ Done (2026-04-27) |
| 13 | T3-B | Unified logging | ✅ Done (2026-04-27) |
| 14 | T4-A | Split news.py | ✅ Done (2026-04-27) |
| 15 | T4-B | _score_inverse abstraction | ✅ Done (2026-04-27) |
| 16 | T4-C | Split app.py into tui/ | ✅ Done (2026-04-27) |

**All refactor tasks complete. No remaining items.**

---

## Verification After Each Tier

```bash
# After Tier 1
python -m py_compile src/screener_config.py src/app.py src/screener_run.py
grep -n "antv311@gmail" src/edgar.py src/inst_flow.py   # expect 0 hits

# After Tier 2
python -c "
import sys; sys.path.insert(0,'src')
import db; db.init_db()
# Verify all new helpers exist and return expected types
print(type(db.get_active_stock_count()))  # expect int
print(type(db.get_stocks_with_cik(5)))    # expect list
"
grep -rn "db.query(" src/edgar.py src/inst_flow.py src/commodities.py src/logistics.py
# expect 0 hits

# After Tier 3
grep -rn "if DEBUG_MODE.*print" src/edgar.py src/news.py src/enricher.py
# expect 0 hits — replaced with logger calls
python src/enricher.py --limit 1   # confirm no output regression

# Full smoke test (all TUIs up for 3s)
python src/app.py &; sleep 3; kill %1
python src/scraper_app.py &; sleep 3; kill %1
python src/db_app.py &; sleep 3; kill %1
```
