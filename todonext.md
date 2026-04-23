# StackScreener — Next Up
> Last updated: 2026-04-22 (session 4)

This document is the detailed task layer below `ROADMAP.md`. Where ROADMAP tracks project-level
status and backlogs, this file tracks the specific items we are actively thinking about,
diagnosing, or queued to build next. Update the date at the top whenever this file changes.

---

## Diagnostic: Warehouse Fire Smoke Test (2026-04-21)

A warehouse fire in California destroyed millions in toilet paper inventory. The aggregator
missed it entirely. This event exposed five structural gaps in the pipeline:

---

### Gap 1 — No automated event creation from news — ✅ CLOSED

**Built:** `news.py --classify` runs the LLM disruption classifier on unclassified `news_articles`
rows. If `is_supply_chain=True` and `confidence >= 0.7`, creates a `supply_chain_events` candidate
(status=monitoring) and links named tickers via `event_stocks`. Marks each article with
`llm_classified=1` so it is never re-processed. Run after any ingest pass.

---

### Gap 2 — Event type coverage is macro-only — ✅ CLOSED

**Built:** Added to `screener_config.EVENT_TYPES` frozenset: `fire`, `flood`, `natural_disaster`,
`infrastructure_failure`, `product_recall`, `cybersecurity`. 3 new Tier 2 seeds added:
consumer staples warehouse fire (PLD/KMB/PG/CLX/WMT), West Coast port labor strike
(MATX/ZIM/EXPD/CHRW/UNP/AMZN), industrial REIT capacity shock (PLD/REXR/FR/AMZN).
Tier 2 seed total: 9 events.

---

### Gap 3 — Entity resolution is missing

**Problem:** Even if we detected "California warehouse fire," we can't automatically answer:
*which REIT owns it? who are the tenants? who supplied the inventory?* That requires either
LLM extraction from 10-K supplier/customer disclosures or a third-party entity graph.

**What needs to exist:**
- EDGAR 10-K entity extraction: parse supplier/customer name mentions → map to tickers
- `event_stocks` linkage built from extracted relationships, not just manual seeding
- This is the "Phase 2b — EDGAR LLM Extraction" item already in ROADMAP P1

---

### Gap 4 — Consumer staples / REIT sector depth is thin

**Problem:** The Tier 2 seed and sector-matching logic focuses on semiconductors, shipping,
energy. A toilet paper → REIT → consumer staples chain wouldn't match any existing
event → sector link.

**What needs to exist:** Extend `supply_chain.py` Tier 2 seed with:
- Consumer staples supply chain scenarios (paper goods, food/bev, household products)
- Industrial REIT exposure scenarios (warehouse/logistics REIT as both impact target and gap-filler)
- Cross-sector chains: manufacturer → 3PL → warehouse REIT → retail vendor

---

### Gap 5 — No EDGAR 8-K material event signal — ✅ CLOSED

**Built:** `edgar.py --fetch-8k` uses the EDGAR submissions API (`data.sec.gov/submissions/CIK{cik}.json`)
to find 8-Ks filed in the last 30 days per stock, fetches primary document text from archives,
and runs 7-category keyword detection (fire, flood, natural_disaster, infrastructure_failure,
product_recall, cybersecurity, facility_shutdown). Results stored as:
- `edgar_facts` row (type=`8k_material_events`) — weekly check record
- `source_signals` row (`signal_type=material_event`, sub_score=55)
- `supply_chain_events` candidate (status=monitoring) if severity=HIGH

Re-checks weekly per `EDGAR_8K_STALENESS_DAYS=7`. Rate-limited to 10 req/s.

---

---

## Session 4 Work — DONE (2026-04-22)

Five items completed this session:

| Item | Files Changed | Gap Closed |
|---|---|---|
| `edgar.py --fetch-8k` | edgar.py, screener_config.py, db.py | Gap 5 — downstream 8-K material events |
| `inst_flow.py --form4` | inst_flow.py, screener_config.py | P1 — insider trades from EDGAR Form 4 |
| Tier 2 seeds ×3 | supply_chain.py, screener_config.py | Gap 4 — consumer staples + labor + industrial REIT |
| `news.py --classify` | news.py, db.py | Gap 1 — LLM auto-promotes to supply_chain_events |
| New event types | screener_config.py | Gap 2 — fire/flood/recall/infra/cyber coverage |

### New CLI commands

```bash
# 8-K material event scanner (weekly; fires, floods, recalls, cyber, facility shutdowns)
python src/edgar.py --fetch-8k
python src/edgar.py --fetch-8k --limit 100

# Form 4 insider trades (EDGAR EFTS search → XML parse → source_signals)
python src/inst_flow.py --form4
python src/inst_flow.py --form4 --limit 200 --days 90

# LLM news classifier → auto supply_chain_events promotion
python src/news.py --classify
python src/news.py --classify --limit 20

# Seed expanded Tier 2 (9 events now: 6 original + consumer staples + labor strike + industrial REIT)
python src/supply_chain.py --seed-tier2
```

---

## LLM Sub-Project — DONE (2026-04-22)

**3/3 validation tasks passed** on Qwen2.5-7B-Instruct TurboQuant 4-bit (8GB RTX 3080).

| Task | Result | Time | Key output |
|---|---|---|---|
| News disruption classifier | PASS | 1066s | `event_type: fire`, `PLD` ticker, `Fontana CA`, confidence 0.9 |
| 10-K entity extractor | PASS | 1756s | `china_exposure: 0.19`, `single_source_risk: true`, TSMC supplier |
| 8-K material event parser | PASS | 3146s | `event_type: fire`, `$45M loss`, `tissue paper`, `supply_chain_relevant: true` |

Slow on 8GB (PyTorch fallback, no CuTile kernel). P40 + 32B will be faster.
Prompt library transfers 1:1 to 32B — same Qwen2ForCausalLM architecture.

### VRAM Constraints — READ BEFORE RUNNING

- **Only one LLM process at a time.** Two simultaneous processes fill VRAM (7.7/8GB),
  deadlock each other, and produce no output.
- `load_quantized()` with `device='cuda'` allocates 14GB bf16 scaffold first — OOM on 8GB.
  Fixed in `load_model()`: CPU load → patch index caching → move quantized weights to CUDA.
- `_cached_indices` accumulates unpacked indices for all 196 layers (~20GB total).
  Fixed via `_prepare_for_inference()` no-cache monkey-patch in `llm.py`.

### Model Reference

**Winner:** Qwen2.5 family (Qwen2ForCausalLM). TurboQuant 4-bit g=128 + Hadamard rotation.
NOT Ollama/GGUF compatible — native PyTorch only. vLLM PR #38171 open, not merged.

| Hardware | Model | VRAM | Status |
|---|---|---|---|
| 8GB RTX 3080 | Qwen2.5-7B-Instruct 4-bit | ~4.6GB | ✅ validated |
| P40 (24GB) | Qwen2.5-32B-Instruct 4-bit | ~20GB | pending P40 arrival |

### Next: Wire LLM into pipeline

```
fetch_articles() → news_articles → classify_news()
    → if is_supply_chain=True and confidence>0.7 → create supply_chain_events candidate
```

---

---

## News Source Expansion — DONE (2026-04-22)

**Built:** AP News RSS, CNBC RSS, MarketWatch RSS, NewsAPI.org, Reuters (via NewsAPI), GDELT.
All constants in `screener_config.py`. All fetchers in `news.py`.

**CLI usage:**
```bash
python src/news.py --ap                         # AP RSS (business, finance, tech)
python src/news.py --cnbc                       # CNBC RSS
python src/news.py --marketwatch                # MarketWatch RSS
python src/news.py --reuters                    # Reuters via NewsAPI (requires key)
python src/news.py --newsapi "supply chain"     # NewsAPI keyword query
python src/news.py --gdelt supply chain fire    # GDELT event search
python src/news.py --all                        # all free sources (AP + CNBC + MW + podcasts + watchlist + PDFs)
```

**NewsAPI key setup (one-time):**
```bash
python -c "import sys; sys.path.insert(0,'src'); import db; db.init_db(); db.set_api_key(1,'newsapi','YOUR_KEY')"
```

**Next step:** Run `python src/llm.py --quantize` to download and quantize Qwen2.5-7B-Instruct,
then `--test` to validate all three extraction tasks against the warehouse fire gaps.

### LLM Integration Note (pending)

Once model is validated, add a post-ingest step to `news.py`:
```
fetch_articles() → insert into news_articles → run classify_news() on new rows
    → if is_supply_chain=True and confidence>0.7 → create supply_chain_events candidate
```
This closes Gap 1 from the warehouse fire smoke test end-to-end.

---

## Other Items Queued

### P1 — Form 4 Insider Trades — ✅ BUILT (2026-04-22)
- `python src/inst_flow.py --form4` — EDGAR EFTS search + XML parse → source_signals
- Scores: insider_buy=70, insider_sell=20 (in screener_config.py)
### P1 — Form 13F Institutional Holdings — ✅ BUILT (2026-04-22)
- `python src/inst_flow.py --form13f` — 14 configured institutions, position diff → source_signals
- `INSTITUTION_CIKS` list in `screener_config.py` — extend as needed

### P1 — Options Flow Detection — ✅ BUILT (2026-04-22)
- `python src/inst_flow.py --options` — yfinance options chain, flags volume > 3× open interest
- `--tickers AAPL MSFT` for targeted scan; `--limit N` to cap universe

### P3 — Home Heatmap — ✅ BUILT (2026-04-23)
- `HeatmapTile` widget: ticker + % change + market cap, background color by pct
- Filter buttons: All / Large Cap / Mega Cap / S&P ≈500 / Watchlist
- 8-column CSS grid layout in `HomePanel`, click/Enter → `StockQuoteModal`
- DB helper: `db.get_heatmap_stocks(limit, min_mcap, watchlist_only)`

### P3 — Logistics World Map — ✅ BUILT (2026-04-23)
- `WorldMap(Static)` widget: 74×18 equirectangular ASCII map + coloured `●` event markers
- `_build_base_map()` programmatically fills landmass regions at module load
- Severity colour legend rendered below map
- Mounted inside `LogisticsPanel` above event detail; updated on `_load_events()`

### P1 — USDA Crop Conditions + EIA Petroleum — ✅ BUILT (2026-04-23)
- `commodities.py --usda-crops` — USDA NASS weekly G+E % per crop → `crop_stress` signals
- `commodities.py --eia-petroleum` — EIA crude/gasoline weekly surprise → `oil_inventory_surprise`
- Both require free API keys stored in `api_keys` table
- Sub-scores: crop_stress=45 (±10 by severity), oil_surprise=50 (draw) / 30 (build)

### P1 — AIS Chokepoints + Panama Canal Draft — ✅ BUILT (2026-04-23)
- `logistics.py --chokepoints` — aisstream.io WebSocket, 60s sample, 10 chokepoints
- Baseline rolling avg from stored signals; alert at < 60% → `chokepoint_congestion`
- `logistics.py --panama` — scrapes ACP restrictions page, flags draft < 12 m
- Both promote HIGH/CRITICAL events to `supply_chain_events` (status=monitoring)
- `CHOKEPOINTS` dict in `screener_config.py` shared with TUI world map markers

---

## Supply Chain Coverage Gaps — All Three Streams (2026-04-22)

StackScreener is designed to detect disruptions across the full supply chain, not just
maritime/geopolitical. Current Tier 2 seeds are macro-only (6 geopolitical events).
These gaps represent the coverage holes across upstream, midstream, and downstream.

---

### Upstream Gaps (raw materials, energy, agriculture, suppliers)

**What we're missing:**
- Agricultural weather signals — USDA weekly crop condition reports (drought/frost/flooding
  affecting corn, soy, wheat) feed directly into food/bev and consumer staples chains
- Energy production disruptions — EIA weekly petroleum inventory surprises; LNG facility
  outages; refinery fires (these are 8-K filings waiting to be parsed)
- Mining/metals disruptions — copper mine strikes, lithium facility shutdowns affect
  semiconductors, EVs, defense; no automated detection today
- Single-source supplier shutdown — 10-K extractor identifies dependencies; next step is
  wiring extracted supplier names into `event_stocks` auto-linkage

**Candidate data sources (all free):**
- USDA NASS crop reports: `https://api.nass.usda.gov/api/get`
- EIA weekly petroleum: `https://api.eia.gov/v2/petroleum/sum/snd/w/` (free key)
- LLM classifier on AP/GDELT news already catches many of these once wired

---

### Midstream Gaps (transportation, processing, chokepoints)

**What we're missing:**
- Live vessel traffic at chokepoints — 10 critical routes identified; no real-time counts
- Port congestion data — Port of LA/Long Beach, Rotterdam, Singapore are the three that move
  US equity prices; no automated signal today
- Panama Canal daily draft restrictions — Canal Authority publishes free; 2023 drought cut
  max draft and was a direct, clean supply constraint signal with almost no noise

**Candidate data sources:**
- **AISHub** (best free option) — requires cheap AIS antenna to share data; gives full
  global API access in return. 10 chokepoints to monitor:
  Strait of Hormuz · Strait of Malacca · Suez Canal · Bab el-Mandeb · Taiwan Strait ·
  English Channel · Strait of Gibraltar · Turkish Straits · Danish Straits · Panama Canal
- **MarineTraffic API** — pay-per-call; no hardware needed
- **Panama Canal Authority** — free daily vessel/draft data at `https://www.pancanal.com`
- Port congestion: MarineTraffic or individual port authority feeds

**Implementation sketch:**
```python
# logistics.py (new module)
def fetch_chokepoint_vessel_counts() -> dict:
    # poll AISHub for vessel count in each chokepoint bounding box
    # compare to 30-day rolling baseline
    # if count < baseline * 0.6 → HIGH severity event candidate

def fetch_panama_draft_restriction() -> dict:
    # poll Canal Authority daily
    # if max_draft < historical_avg - 1ft → MEDIUM severity
```

---

### Downstream Gaps (warehousing, distribution, retail)

**What we're missing:**
- 8-K material event pipeline — fires, floods, facility losses that REITs must file within
  4 business days; this is Gap 5 from the warehouse fire smoke test (see above)
- REIT entity resolution — "warehouse in Fontana" → PLD owner → tenants → product categories;
  requires either LLM extraction from 10-K or a third-party facility database
- Consumer staples Tier 2 seeds — toilet paper → warehouse REIT → retail vendor chain has
  zero representation in current 6-event seed (Gap 4 from smoke test)
- Retail disruption signals — store closure announcements, inventory shortage disclosures

**Next actionable steps:**
1. `edgar.py --fetch-8k` — poll EDGAR full-text search for recent 8-K filings per ticker;
   parse Item 1.05 (cybersecurity) and Item 8.01 (other events); keyword-flag fire/flood/facility
2. Extend `supply_chain.py --seed-tier2` with consumer staples + industrial REIT chains
3. LLM 10-K extractor already built — wire supplier names into `event_stocks` auto-creation

---
