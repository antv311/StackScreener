"""
LLM extraction pipeline for StackScreener.

Model: Qwen2.5-7B-Instruct (test bed) → Qwen2.5-32B-Instruct (P40 production)
Quantization: TurboQuant 4-bit g=128 + Hadamard rotation

Three extraction tasks:
  1. News disruption classifier   → supply_chain_events candidate
  2. 10-K entity extractor        → edgar_facts supplier/customer JSON
  3. 8-K material event parser    → supply_chain_events candidate

CLI:
  python src/llm.py --quantize                  # download + quantize model (run once)
  python src/llm.py --test                      # run all three validation tasks
  python src/llm.py --classify-news "headline"  # quick single-article test
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from turboquant_model import TurboQuantConfig, load_quantized, quantize_model, save_quantized

import screener_config as cfg

# ---------------------------------------------------------------------------
# Constants (all values live in screener_config.py — these are just aliases)
# ---------------------------------------------------------------------------
MODEL_ID       = cfg.LLM_MODEL_ID
QUANTIZED_DIR  = cfg.LLM_QUANTIZED_DIR
BIT_WIDTH      = cfg.LLM_BIT_WIDTH
GROUP_SIZE     = cfg.LLM_GROUP_SIZE
MAX_NEW_TOKENS = cfg.LLM_MAX_NEW_TOKENS

# ---------------------------------------------------------------------------
# Model lifecycle
# ---------------------------------------------------------------------------

def _get_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def quantize_and_save(model_id: str = MODEL_ID, output_dir: str = QUANTIZED_DIR) -> None:
    """Download model, apply TurboQuant 4-bit Hadamard, save to disk.

    Loads in bf16 on CPU so all weights are accessible (avoids meta-tensor
    offload when bf16 model exceeds GPU VRAM). Quantized output fits in GPU.
    """
    print(f"Loading {model_id} in bf16 on CPU (full weights needed for quantization)...")
    model = AutoModelForCausalLM.from_pretrained(
        model_id, dtype=torch.bfloat16, device_map="cpu"
    )
    tokenizer = AutoTokenizer.from_pretrained(model_id)

    print(f"Quantizing: {BIT_WIDTH}-bit, group={GROUP_SIZE}, rotation=hadamard...")
    config = TurboQuantConfig(bit_width=BIT_WIDTH, group_size=GROUP_SIZE,
                               rotation="hadamard", seed=42)
    model = quantize_model(model, config)

    print(f"Saving to {output_dir}...")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    save_quantized(model, config, output_dir)
    tokenizer.save_pretrained(output_dir)
    print("Done.")


def _prepare_for_inference(model) -> None:
    """Patch each TurboQuantLinear layer for memory-safe inference on ≤8 GB VRAM.

    The default `_get_indices()` caches unpacked indices for every layer the
    first time they are called, accumulating ~20 GB for a 7B model — well
    beyond 8 GB VRAM.  Replacing the method with a no-cache version means
    only the current layer's indices (~68–272 MB) are resident during its
    forward call; they are freed before the next layer runs.

    Also disables cuTile/Triton fused kernels (not present on this build) so
    the PyTorch fallback path is used instead.
    """
    import types
    from turboquant_model.module import TurboQuantLinear
    from turboquant_model.quantize import unpack_4bit

    def _nocache_get_indices(self) -> torch.Tensor:
        return unpack_4bit(self.indices_packed, self.in_features)

    for m in model.modules():
        if isinstance(m, TurboQuantLinear):
            m.use_cutile = False
            m.use_triton = False
            m._get_indices = types.MethodType(_nocache_get_indices, m)


def load_model(quantized_dir: str = QUANTIZED_DIR) -> tuple:
    """Load quantized model + tokenizer from disk.

    load_quantized() with device='cuda' allocates a full bf16 model (~14 GB)
    to GPU before swapping in quantized weights, causing OOM on 8 GB cards.
    Work-around: load on CPU, patch away index caching (see _prepare_for_inference),
    then move only the compact quantized weights (~4.6 GB) to CUDA.
    """
    if not Path(quantized_dir).exists():
        raise FileNotFoundError(
            f"Quantized model not found at {quantized_dir}. "
            "Run: python src/llm.py --quantize"
        )
    print("Loading quantized model on CPU...")
    model = load_quantized(MODEL_ID, quantized_dir, device="cpu")
    _prepare_for_inference(model)

    device = _get_device()
    if device == "cuda":
        print("Moving quantized model to CUDA (~4.6 GB)...")
        model = model.to(device)

    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(quantized_dir)
    return model, tokenizer


# ---------------------------------------------------------------------------
# Core inference helper
# ---------------------------------------------------------------------------

def _infer(model, tokenizer, system_prompt: str, user_content: str) -> str:
    """Single inference call. Returns raw model output string."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_content},
    ]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(text, return_tensors="pt").to(_get_device())
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    # strip the prompt tokens from the output
    new_ids = output_ids[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(new_ids, skip_special_tokens=True).strip()


def _parse_json(raw: str) -> Optional[dict | list]:
    """Extract the first JSON object or array from a model response."""
    raw = raw.strip()
    # find first { or [
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = raw.find(start_char)
        if start == -1:
            continue
        # walk backwards from end to find matching close
        depth = 0
        for i, ch in enumerate(raw[start:], start=start):
            if ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(raw[start:i + 1])
                    except json.JSONDecodeError:
                        break
    return None


# ---------------------------------------------------------------------------
# Task 1 — News disruption classifier
# ---------------------------------------------------------------------------

_NEWS_SYSTEM = """You are a supply chain disruption analyst. Given a news article,
determine whether it describes a supply chain disruption event.

Respond ONLY with a JSON object — no explanation, no markdown:
{
  "is_supply_chain": true/false,
  "event_type": "fire|flood|strike|sanctions|port_closure|facility_shutdown|recall|geopolitical|other|none",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW|NONE",
  "sectors": ["list", "of", "GICS", "sector", "names"],
  "affected_tickers": ["list of stock tickers if explicitly named, else empty"],
  "location": "city, state or country if mentioned, else null",
  "confidence": 0.0-1.0
}"""


def classify_news(model, tokenizer, headline: str, body: str = "") -> Optional[dict]:
    """
    Task 1: classify a news article as a supply chain disruption.
    Returns structured dict or None if model output is unparseable.
    """
    content = headline if not body else f"Headline: {headline}\n\nBody: {body[:2000]}"
    raw = _infer(model, tokenizer, _NEWS_SYSTEM, content)
    result = _parse_json(raw)
    if cfg.DEBUG_MODE:
        print(f"[classify_news] raw: {raw[:200]}")
    return result


# ---------------------------------------------------------------------------
# Task 2 — 10-K supplier / customer extractor
# ---------------------------------------------------------------------------

_EDGAR_SYSTEM = """You are a financial document analyst. Given a passage from a 10-K SEC filing,
extract supplier and customer relationships.

Respond ONLY with a JSON object — no explanation, no markdown:
{
  "suppliers": [
    {"name": "Company Name", "ticker": "TICK or null", "pct_of_revenue": 0.0-1.0 or null, "geography": "country or null"}
  ],
  "customers": [
    {"name": "Company Name or 'unnamed'", "ticker": "TICK or null", "pct_of_revenue": 0.0-1.0 or null}
  ],
  "china_exposure": 0.0-1.0 or null,
  "single_source_risk": true/false
}
If no suppliers or customers are mentioned, return empty arrays."""


def extract_10k_entities(model, tokenizer, passage: str) -> Optional[dict]:
    """
    Task 2: extract supplier/customer relationships from a 10-K text passage.
    Returns structured dict or None if unparseable.
    """
    raw = _infer(model, tokenizer, _EDGAR_SYSTEM, passage[:3000])
    result = _parse_json(raw)
    if cfg.DEBUG_MODE:
        print(f"[extract_10k_entities] raw: {raw[:200]}")
    return result


# ---------------------------------------------------------------------------
# Task 3 — 8-K material event parser
# ---------------------------------------------------------------------------

_8K_SYSTEM = """You are an SEC filing analyst. Given text from an 8-K filing,
extract details about any material event described.

Respond ONLY with a JSON object — no explanation, no markdown:
{
  "event_type": "fire|flood|facility_loss|cybersecurity|leadership_change|litigation|other",
  "location": "city, state or country or null",
  "estimated_loss_usd": integer or null,
  "operational_impact": "brief one-sentence description or null",
  "supply_chain_relevant": true/false,
  "affected_product": "product or commodity name or null",
  "ticker_hint": "ticker if mentioned in the text, else null"
}"""


def parse_8k_event(model, tokenizer, filing_text: str) -> Optional[dict]:
    """
    Task 3: parse material event details from an 8-K filing passage.
    Returns structured dict or None if unparseable.
    """
    raw = _infer(model, tokenizer, _8K_SYSTEM, filing_text[:3000])
    result = _parse_json(raw)
    if cfg.DEBUG_MODE:
        print(f"[parse_8k_event] raw: {raw[:200]}")
    return result


# ---------------------------------------------------------------------------
# Validation test suite
# ---------------------------------------------------------------------------

_TEST_CASES = [
    {
        "task": "classify_news",
        "label": "Warehouse fire — California toilet paper",
        "input": {
            "headline": "Fire destroys major distribution warehouse in Fontana, CA",
            "body": (
                "A five-alarm fire destroyed a 400,000 square foot distribution warehouse "
                "in Fontana, California late Tuesday, incinerating an estimated $80 million "
                "in consumer goods inventory including toilet paper, paper towels, and "
                "household cleaning products. The warehouse is owned by Prologis Inc (PLD) "
                "and was leased to a major consumer goods distributor. Investigators believe "
                "an electrical fault caused the blaze. The loss is expected to disrupt "
                "regional supply chains for paper goods for 4-6 weeks."
            ),
        },
        "expect": {"is_supply_chain": True, "event_type": "fire"},
    },
    {
        "task": "extract_10k_entities",
        "label": "Apple 10-K China supplier passage",
        "input": {
            "passage": (
                "The Company relies on single-source suppliers for certain components "
                "including application processors manufactured by TSMC in Taiwan, which "
                "accounted for substantially all of the Company's chip supply. "
                "Our operations in Greater China represented 19% of net sales in fiscal 2023. "
                "Foxconn Technology Group assembles the majority of our iPhone products "
                "at facilities in China. Disruption to these suppliers could materially "
                "adversely affect our business."
            )
        },
        "expect": {"china_exposure": 0.19, "single_source_risk": True},
    },
    {
        "task": "parse_8k_event",
        "label": "8-K fire filing — facility loss",
        "input": {
            "filing_text": (
                "Item 8.01 Other Events. On April 18, 2026, a fire occurred at the "
                "Company's primary manufacturing facility located in Memphis, Tennessee. "
                "The fire caused significant damage to production equipment and inventory. "
                "The Company estimates the loss at approximately $45 million. "
                "Production of tissue paper products at this facility has been suspended "
                "pending assessment. The Company carries property insurance and is working "
                "with its insurer. Alternative sourcing arrangements are being evaluated."
            )
        },
        "expect": {"event_type": "fire", "supply_chain_relevant": True},
    },
]


def run_tests(model, tokenizer) -> None:
    """Run the three validation tasks and print pass/fail results."""
    print("\n" + "=" * 60)
    print("LLM EXTRACTION VALIDATION — Qwen2.5-7B TurboQuant 4-bit")
    print("=" * 60)

    passed = 0
    for tc in _TEST_CASES:
        print(f"\n[{tc['task']}] {tc['label']}")
        t0 = time.time()

        match tc["task"]:
            case "classify_news":
                result = classify_news(model, tokenizer, **tc["input"])
            case "extract_10k_entities":
                result = extract_10k_entities(model, tokenizer, **tc["input"])
            case "parse_8k_event":
                result = parse_8k_event(model, tokenizer, **tc["input"])
            case _:
                result = None

        elapsed = time.time() - t0

        if result is None:
            print(f"  FAIL — output unparseable ({elapsed:.1f}s)")
            continue

        # check expected keys match
        ok = all(
            str(result.get(k)).lower() == str(v).lower()
            or (isinstance(v, float) and abs(float(result.get(k, 0)) - v) < 0.05)
            for k, v in tc["expect"].items()
        )

        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"  {status} ({elapsed:.1f}s)")
        print(f"  output: {json.dumps(result, indent=2)[:300]}")

    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{len(_TEST_CASES)} passed")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="StackScreener LLM extraction pipeline")
    p.add_argument("--quantize",      action="store_true", help="Download + quantize model (run once)")
    p.add_argument("--test",          action="store_true", help="Run validation test suite")
    p.add_argument("--classify-news", metavar="HEADLINE",  help="Classify a news headline")
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    if args.quantize:
        quantize_and_save()
        return

    model, tokenizer = load_model()

    if args.test:
        run_tests(model, tokenizer)
        return

    if args.classify_news:
        result = classify_news(model, tokenizer, headline=args.classify_news)
        print(json.dumps(result, indent=2) if result else "Could not parse output")
        return

    print("No action specified. Use --quantize, --test, or --classify-news.")


if __name__ == "__main__":
    main()
