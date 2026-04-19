"""
supply_chain.py — Supply chain signal ingestion and sector mapping.

Manages two tiers of company-to-event linkage:

  Tier 1 — Automated sector matching
    event.affected_sectors / affected_industries  ↔  stocks.sector / industry
    Broad but fully automated. Use db.get_sector_candidates(event_uid) to query.

  Tier 2 — Curated high-confidence relationships
    Known company-level supply chain links hand-coded in _TIER2_SEEDS.
    These are the relationships that move markets when a disruption hits.
    Stored in event_stocks with role, cannot_provide, will_redirect, confidence.

Usage:
    python supply_chain.py --seed-tier2            # seed curated relationships into DB
    python supply_chain.py --candidates EVENT_UID  # print Tier 1 candidates for an event
    python supply_chain.py --list-events           # list all supply chain events in DB
"""

import argparse
import json

import db
from screener_config import (
    DEBUG_MODE,
    CONFIDENCE_HIGH, CONFIDENCE_MEDIUM,
    EVENT_TYPE_CONFLICT, EVENT_TYPE_SANCTIONS,
    EVENT_STATUS_ACTIVE, EVENT_STATUS_MONITORING,
    ROLE_IMPACTED, ROLE_BENEFICIARY,
    SEVERITY_HIGH,
)


# ── Tier 2 curated seed ────────────────────────────────────────────────────────
#
# Each entry defines one supply chain scenario: the event metadata and the
# specific company-level relationships (impacted vs beneficiary, with context).
#
# Tickers must match what's in the stocks table (NYSE/NASDAQ listed symbols).
# Seed with: python supply_chain.py --seed-tier2

_TIER2_SEEDS: list[dict] = [

    # ── Taiwan Strait — Semiconductor Fabrication ─────────────────────────────
    {
        "event": {
            "title":               "Taiwan Strait Semiconductor Supply Risk",
            "region":              "East Asia",
            "event_type":          EVENT_TYPE_CONFLICT,
            "description":         (
                "Geopolitical tensions across the Taiwan Strait threaten concentration "
                "of advanced semiconductor fabrication. TSMC accounts for ~90% of world "
                "advanced node (sub-7nm) chip production. Any kinetic disruption or "
                "blockade would halt supply to Apple, NVIDIA, AMD, and Qualcomm with no "
                "short-term substitute."
            ),
            "severity":            SEVERITY_HIGH,
            "status":              EVENT_STATUS_MONITORING,
            "latitude":            23.7,
            "longitude":           121.0,
            "country_code":        "TW",
            "trade_route":         "Taiwan Strait",
            "commodity":           "semiconductors",
            "affected_sectors":    json.dumps(["Technology"]),
            "affected_industries": json.dumps(["Semiconductors", "Semiconductor Equipment"]),
            "beneficiary_sectors": json.dumps(["Technology"]),
            "event_date":          "2024-01-01",
        },
        "links": [
            {
                "ticker":         "TSM",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "advanced node semiconductor fabrication (3nm, 5nm, 7nm)",
                "will_redirect":  "Intel Foundry Services (IFS), GlobalFoundries (mature nodes only)",
                "impact_notes":   "TSMC manufactures ~90% of world advanced chips; primary fab for Apple, NVIDIA, AMD, Qualcomm",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "ASML",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "EUV lithography equipment delivery and field service",
                "will_redirect":  "No EUV substitute exists; legacy DUV (Nikon/Canon) limited to mature nodes",
                "impact_notes":   "Sole global supplier of EUV lithography machines; TSMC is largest customer",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "AMAT",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "wafer fab equipment supply and maintenance for Taiwan fabs",
                "will_redirect":  "US/Europe fab buildout (Intel Ohio, TSMC Arizona, Samsung Texas)",
                "impact_notes":   "Applied Materials derives significant revenue from TSMC and other Taiwan fabs",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "LRCX",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "etch and deposition equipment for Taiwan advanced node fabs",
                "will_redirect":  "US domestic fab expansion contracts",
                "impact_notes":   "Lam Research ~30% of revenue from Taiwan customer base",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "KLAC",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "process control and wafer inspection for Taiwan fabs",
                "will_redirect":  "US/Europe fab inspection contracts",
                "impact_notes":   "KLA significant Taiwan concentration in equipment and service revenue",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "INTC",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Intel Foundry Services (IFS) absorbs displaced advanced node demand",
                "impact_notes":   "IFS positioned as primary US-based advanced fab alternative; CHIPS Act funded expansion underway",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "GFS",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "GlobalFoundries captures mature node (12nm+) displaced demand",
                "impact_notes":   "US/EU/Singapore fabs; cannot serve advanced node but benefits from mature node reshoring",
                "confidence":     CONFIDENCE_MEDIUM,
            },
        ],
    },

    # ── Red Sea / Suez Canal ──────────────────────────────────────────────────
    {
        "event": {
            "title":               "Red Sea Shipping Disruption",
            "region":              "Middle East",
            "event_type":          EVENT_TYPE_CONFLICT,
            "description":         (
                "Houthi attacks on commercial shipping in the Red Sea are forcing vessels "
                "to reroute around the Cape of Good Hope, adding 10-14 days and "
                "significant fuel costs to Asia-Europe trade. Suez Canal traffic down "
                "~50% from pre-crisis levels."
            ),
            "severity":            SEVERITY_HIGH,
            "status":              EVENT_STATUS_ACTIVE,
            "latitude":            15.0,
            "longitude":           42.0,
            "country_code":        "YE",
            "trade_route":         "Red Sea",
            "commodity":           "containerized goods",
            "affected_sectors":    json.dumps(["Industrials", "Consumer Discretionary", "Consumer Staples"]),
            "affected_industries": json.dumps(["Marine Shipping", "Air Freight & Logistics"]),
            "beneficiary_sectors": json.dumps(["Energy"]),
            "event_date":          "2023-11-01",
        },
        "links": [
            {
                "ticker":         "ZIM",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "cost-competitive Red Sea / Suez Canal transit",
                "will_redirect":  "Cape of Good Hope routing (+10-14 days, +$1M+ fuel per voyage)",
                "impact_notes":   "ZIM is Israeli carrier; heavily targeted by Houthis, forced full Red Sea rerouting",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "DAC",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "scheduled Suez Canal container transit on Asia-Europe routes",
                "will_redirect":  "Cape routing; some vessels idled pending security clearance",
                "impact_notes":   "Danaos container fleet charter rates affected by rerouting cost increases",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "GSL",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Red Sea corridor container capacity on Asia-Europe lanes",
                "will_redirect":  "Cape of Good Hope alternate routing",
                "impact_notes":   "Global Ship Lease fleet exposed to Asia-Europe route disruption and cost inflation",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "MPC",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Higher bunker fuel demand from longer Cape voyages boosts refinery throughput and margins",
                "impact_notes":   "Marathon Petroleum refinery margins expand when marine fuel demand rises from rerouting",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "VLO",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Valero benefits from increased bunker fuel demand and tighter crude spreads",
                "impact_notes":   "Refining margins historically improve during major shipping disruptions",
                "confidence":     CONFIDENCE_MEDIUM,
            },
        ],
    },

    # ── US-China Semiconductor Export Controls ────────────────────────────────
    {
        "event": {
            "title":               "US-China Advanced Semiconductor Export Controls",
            "region":              "East Asia",
            "event_type":          EVENT_TYPE_SANCTIONS,
            "description":         (
                "US Bureau of Industry and Security (BIS) export controls restrict sale "
                "of advanced AI accelerators (H100, MI300) and semiconductor fabrication "
                "equipment to Chinese entities. Controls are tightening in successive "
                "rounds, cutting off a material revenue source for US chip companies."
            ),
            "severity":            SEVERITY_HIGH,
            "status":              EVENT_STATUS_ACTIVE,
            "latitude":            39.9,
            "longitude":           116.4,
            "country_code":        "CN",
            "trade_route":         None,
            "commodity":           "semiconductors",
            "affected_sectors":    json.dumps(["Technology"]),
            "affected_industries": json.dumps(["Semiconductors", "Semiconductor Equipment"]),
            "beneficiary_sectors": json.dumps([]),
            "event_date":          "2022-10-07",
        },
        "links": [
            {
                "ticker":         "NVDA",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "H100, A100, H800 AI accelerators to Chinese data centers",
                "will_redirect":  "India, Middle East, Southeast Asia data center demand",
                "impact_notes":   "NVIDIA China revenue ~20-25% of data center segment pre-controls; H20 degraded chip approved but under further review",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "AMD",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "MI300 series AI accelerators and Instinct GPUs to China",
                "will_redirect":  "Non-restricted geographies",
                "impact_notes":   "AMD China exposure lower than NVIDIA but MI300 restricted; CPU exports also impacted",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "QCOM",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Advanced mobile and server chips to restricted Chinese OEMs",
                "will_redirect":  "India, emerging market smartphone OEMs",
                "impact_notes":   "Qualcomm ~60% China revenue exposure across smartphone and IoT segments",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "AMAT",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Advanced CVD, ALD, and etch equipment to Chinese advanced node fabs",
                "will_redirect":  "US/Europe/Japan fab customers (Intel, TSMC Arizona, Samsung)",
                "impact_notes":   "Applied Materials China ~26% of total revenue; equipment licensing restrictions tightening",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "LRCX",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Advanced etch and deposition equipment to Chinese advanced node fabs",
                "will_redirect":  "US/Korea/Japan customers",
                "impact_notes":   "Lam Research China ~30% revenue; restricted from supplying SMIC advanced node lines",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "KLAC",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Advanced process control equipment for sub-14nm Chinese fab lines",
                "will_redirect":  "US domestic and allied fab inspection contracts",
                "impact_notes":   "KLA China revenue ~30%; export restrictions on advanced inspection and metrology tools",
                "confidence":     CONFIDENCE_HIGH,
            },
        ],
    },
]


# ── Seed function ──────────────────────────────────────────────────────────────

def seed_tier2_relationships() -> None:
    """Upsert all Tier 2 curated supply chain events and company links into the DB.

    Idempotent — safe to run multiple times. Events are keyed on (title, region);
    links are keyed on (supply_chain_event_uid, stock_uid, role).
    """
    total_events = 0
    total_links = 0
    total_skipped = 0

    for seed in _TIER2_SEEDS:
        event_uid = db.upsert_supply_chain_event(seed["event"])
        total_events += 1

        for link in seed["links"]:
            stock = db.get_stock_by_ticker(link["ticker"])
            if not stock:
                print(f"  SKIP {link['ticker']}: not found in stocks table")
                total_skipped += 1
                continue

            db.link_event_stock(
                supply_chain_event_uid=event_uid,
                stock_uid=stock["stock_uid"],
                role=link["role"],
                cannot_provide=link.get("cannot_provide"),
                will_redirect=link.get("will_redirect"),
                impact_notes=link.get("impact_notes"),
                confidence=link["confidence"],
            )
            total_links += 1
            if DEBUG_MODE:
                print(f"  [supply_chain] linked {link['ticker']} ({link['role']}) → event {event_uid}")

    print(f"Tier 2 seed complete: {total_events} events, {total_links} links, {total_skipped} tickers skipped.")


# ── CLI ────────────────────────────────────────────────────────────────────────

def _print_candidates(event_uid: int) -> None:
    candidates = db.get_sector_candidates(event_uid)
    event = db.get_event(event_uid)
    if not event:
        print(f"Event {event_uid} not found.")
        return
    print(f"\nTier 1 candidates for: {event['title']} ({event['region']})")
    print(f"  {len(candidates)} stocks match affected sectors/industries\n")
    for s in candidates[:50]:
        cap = f"${s['market_cap'] / 1e9:.1f}B" if s.get("market_cap") else "n/a"
        print(f"  {s['ticker']:<8} {cap:<10} {s['sector'] or ''} / {s['industry'] or ''}")
    if len(candidates) > 50:
        print(f"  ... and {len(candidates) - 50} more")


def _list_events() -> None:
    events = db.get_active_events()
    if not events:
        print("No supply chain events in database. Run --seed-tier2 first.")
        return
    print(f"\n{'UID':<5} {'Severity':<10} {'Status':<12} {'Region':<15} Title")
    print("-" * 70)
    for e in events:
        print(f"  {e['supply_chain_event_uid']:<3} {e['severity']:<10} {e['status']:<12} {e['region']:<15} {e['title']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="StackScreener supply chain manager")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--seed-tier2",   action="store_true",  help="Seed curated Tier 2 supply chain relationships into the database")
    group.add_argument("--candidates",   type=int, metavar="EVENT_UID", help="Print Tier 1 sector-matched stock candidates for an event")
    group.add_argument("--list-events",  action="store_true",  help="List all supply chain events currently in the database")
    args = parser.parse_args()

    if args.seed_tier2:
        seed_tier2_relationships()
    elif args.candidates is not None:
        _print_candidates(args.candidates)
    elif args.list_events:
        _list_events()


if __name__ == "__main__":
    main()
