# StackScreener — Next Up
> Last updated: 2026-04-21

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

## LLM Sub-Project — Model Decision & Test Plan (2026-04-21)

All three independent evaluations (Claude, Grok, Gemini) converged on the same answer.
Decision is locked. Document the approach here before the sub-project opens formally.

---

### Model Selection

**Winner: Qwen2.5 family (Qwen2ForCausalLM architecture)**

Rationale: best-in-class structured JSON output, strong instruction adherence, 128K context
window, financial/SEC domain knowledge, and local deployment viability. The only alternative
worth benchmarking later is **DeepSeek-R1-Distill-Qwen-32B** (same architecture, R1 reasoning
chain distilled in — better on ambiguous classification edge cases, same VRAM profile).

---

### Quantization: TurboQuant (cksac/turboquant-model)

Adaptation of Zandieh et al. (2025) from KV-cache compression to model weight compression.
Drop-in `nn.Linear` replacement. Post-training quantization — no calibration dataset needed.
Reference: `READMETQ.md` in repo root.

Key benchmarks at scale (Qwen2.5-32B):
- 4+4 residual (8-bit): PPL 14.28 vs 14.29 baseline — near-lossless. ~36GB VRAM.
- **4-bit g=128 + CuTile: PPL +2.3. ~20GB VRAM. Target config for P40.**

Fused kernel priority: CuTile > Triton > PyTorch fallback. Use Hadamard rotation
(`--rotation hadamard`) — same quality as QR, O(d) storage vs O(d²).

**Deployment constraint:** NOT compatible with Ollama or standard GGUF.
Requires native PyTorch + CuTile/Triton environment.
vLLM integration: PR #38171 open, not yet merged. Custom inference wrapper needed.

---

### VRAM Targets

| Hardware | Model | Config | VRAM | KV Headroom | Verdict |
|---|---|---|---|---|---|
| 8GB laptop | Qwen2.5-7B-Instruct | 4-bit g=128 CuTile | ~4.4GB | ~3.5GB | ✓ test bed |
| P40 (24GB) | Qwen2.5-32B-Instruct | 4-bit g=128 CuTile | ~20GB | ~4GB | ✓ production |
| P40 (24GB) | Qwen2.5-32B-Instruct | 4+4 residual | ~36GB | none | ✗ too big |

---

### Test Bed — "1995 Corolla" (8GB Laptop)

**Model:** Qwen2.5-7B-Instruct, TurboQuant 4-bit g=128, CuTile kernel
**Purpose:** Validate the full pipeline before committing P40 cycles to 32B inference.
Same Qwen2ForCausalLM architecture — all prompt code transfers 1:1 to production.

Install:
```bash
uv pip install -e ".[transformers]"
turboquant quantize --model Qwen/Qwen2.5-7B-Instruct --output ./quantized \
    --bit-width 4 --rotation hadamard
```

**Three validation tasks (warehouse fire gaps → extraction tests):**

1. **News disruption classifier** — feed headline + body → expect structured JSON:
   `{"is_supply_chain": true, "event_type": "fire", "severity": "HIGH", "sectors": [...]}`
   Ground truth: known disruption articles from `news_articles` table.

2. **10-K supplier/customer extractor** — feed short 10-K risk paragraph → expect:
   `{"suppliers": [...], "customers": [...], "china_exposure": 0.19}`
   Ground truth: verify against XBRL edgar_facts for the same ticker.

3. **8-K material event parser** — feed mock 8-K Item 8.01 fire filing → expect:
   `{"event_type": "facility_fire", "location": "California", "ticker_hint": "...", "severity": "HIGH"}`

Pass criteria: all three return valid JSON matching the target schema with no hallucinated
company names or tickers. If 7B passes, 32B inherits the prompt library unchanged.

---

---

## News Source Expansion — Widen the Net (2026-04-22)

**Problem:** WSJ still hasn't covered the California warehouse fire. The LLM classifier
(`llm.py` Task 1) can only process articles that are already in `news_articles`. If the
ingestion layer misses the event, the classifier never sees it — so the supply chain event
never gets created regardless of how good the model is. This is a data coverage gap, not a
model gap.

**Why this blocks the LLM test:** The warehouse fire smoke test revealed the aggregator
missed the event entirely. Until we have broader source coverage, the LLM validation test
suite is running against a biased sample (only WSJ/MS/MF content). We need AP and Reuters
in the pipeline before the LLM results mean anything at scale.

---

### Sources to Add (all free tiers available)

| Source | Method | Why |
|---|---|---|
| **AP News** | RSS feeds (free, no key) | Breaks physical events (fires, floods, strikes) faster than WSJ |
| **Reuters** | RSS feeds (free, no key) | Global commodity + logistics coverage; strong on port/shipping |
| **NewsAPI.org** | REST API (free tier: 100 req/day) | Aggregates AP, Reuters + 150k sources; single integration point |
| **GDELT Project** | REST API (free, no key) | Global event database; specifically strong on geopolitical/disaster signals |
| **CNBC** | RSS feeds (free, no key) | Fast on market-moving supply chain stories |
| **MarketWatch** | RSS feeds (free, no key) | Strong on commodity + sector rotation coverage |

**Recommended integration order:**
1. **NewsAPI.org** first — one integration covers AP + Reuters + most others; free tier is enough to validate
2. **GDELT** second — purpose-built for event detection, perfect feed for `supply_chain_events` auto-creation
3. Individual RSS (AP, Reuters, CNBC, MarketWatch) — add after NewsAPI proves value

---

### What needs to change in code

- `news.py` — add `fetch_newsapi(query, api_key)` and `fetch_gdelt(keywords)` functions
- `db.py` — no schema changes; `news_articles` already has `source` column for new sources
- `screener_config.py` — add `NEWS_SOURCE_AP`, `NEWS_SOURCE_REUTERS`, `NEWS_SOURCE_NEWSAPI`,
  `NEWS_SOURCE_GDELT` constants; add GDELT base URL constant
- `api_keys` table — store NewsAPI key via `db.set_api_key()` (free key, still encrypted)
- After ingestion: new articles flow through `llm.py classify_news()` automatically

---

### LLM Integration Note

Once broader sources are ingested, add a post-ingest step to `news.py`:
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
