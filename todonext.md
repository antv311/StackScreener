# StackScreener — Next Up
> Last updated: 2026-04-22 (session 3)

This document is the detailed task layer below `ROADMAP.md`. Where ROADMAP tracks project-level
status and backlogs, this file tracks the specific items we are actively thinking about,
diagnosing, or queued to build next. Update the date at the top whenever this file changes.

---

## Diagnostic: Warehouse Fire Smoke Test (2026-04-21)

A warehouse fire in California destroyed millions in toilet paper inventory. The aggregator
missed it entirely. This event exposed five structural gaps in the pipeline:

---

### Gap 1 — No automated event creation from news

**Problem:** `news.py` collects articles into `news_articles` but nothing promotes them to
`supply_chain_events`. A fire story sits inert — it never becomes a scored signal. The upstream
chain (REIT → supplier → vendor) never fires.

**What needs to exist:** A classifier that reads `news_articles` rows and, when a disruption
pattern is detected (fire, flood, strike, sanctions, port closure, etc.), creates a
`supply_chain_events` row and links affected tickers via `event_stocks`.

**Candidate approach:** LLM pass over new articles (local Ollama / P40) or a lightweight
keyword+regex classifier as a first pass before LLM confirmation.

---

### Gap 2 — Event type coverage is macro-only

**Problem:** The 6 Tier 2 seeds are all geopolitical (Taiwan Strait, Red Sea, sanctions).
Domestic physical events — fires, floods, strikes, infrastructure failures — have no
representation. Different signal class entirely.

**What needs to exist:** Expand `supply_chain_events.event_type` to include:
- `fire` / `flood` / `natural_disaster`
- `labor_strike`
- `infrastructure_failure`
- `product_recall`
- `facility_shutdown`

Also expand Tier 2 seed scenarios to cover consumer staples + REIT chains.

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

### Gap 5 — No EDGAR 8-K material event signal

**Problem:** SEC Form 8-K filings cover material events — fires, facility losses, and major
disruptions qualify. We pull 10-K text and XBRL facts but not 8-Ks. The warehouse fire REIT
would have filed an 8-K within 4 business days.

**What needs to exist:**
- `edgar.py --fetch-8k` — poll EDGAR full-text search for recent 8-K filings per ticker
- Parse Item 1.05 (Material Cybersecurity Incidents) and Item 8.01 (Other Events)
- Flag fire/flood/facility keywords → create `source_signals` row + candidate `supply_chain_events`
- New CLI flag: `python src/edgar.py --fetch-8k --limit 100`

---

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

### P1 — Form 4 Insider Trades
- `inst_flow.py --form4`
- Fetch recent Form 4 filings from EDGAR full-text search API
- Parse: filer name, issuer ticker, transaction type (buy/sell), shares, price, date
- Store in `source_signals` with `signal_type = 'insider_buy'` / `'insider_sell'`
- Wire into composite score

### P1 — Form 13F Institutional Holdings
- `inst_flow.py --form13f`
- Quarterly 13F filings → institutional position changes per ticker
- Store in `source_signals` with `signal_type = 'inst_buy'` / `'inst_sell'`

### P1 — Options Flow Detection
- `inst_flow.py --options`
- yfinance options chain: flag unusual put/call volume vs. 20-day avg
- Store in `source_signals` with `signal_type = 'options_unusual'`

### P3 — Home Heatmap
- Full-width market heatmap (tiles color-coded by % change, sized by market cap)
- Index selector: S&P 500 / DOW / Russell 1000 / Recommended / All
- Click tile → `StockQuoteModal`

### P3 — Logistics World Map
- ASCII/Unicode region markers for active supply chain events
- Click marker → filter Logistics table to that event

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
