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
    EVENT_TYPE_CONFLICT, EVENT_TYPE_SANCTIONS, EVENT_TYPE_WEATHER,
    EVENT_TYPE_LABOR, EVENT_TYPE_FIRE, EVENT_TYPE_PORT_BLOCKAGE,
    EVENT_STATUS_ACTIVE, EVENT_STATUS_MONITORING,
    ROLE_IMPACTED, ROLE_BENEFICIARY,
    SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_CRITICAL,
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

    # ── Gulf Coast Hurricane — Energy Infrastructure ───────────────────────────
    {
        "event": {
            "title":               "Gulf Coast Hurricane Energy Disruption",
            "region":              "Gulf of Mexico",
            "event_type":          EVENT_TYPE_WEATHER,
            "description":         (
                "Major hurricane making landfall on the US Gulf Coast forces shutdown of "
                "offshore oil platforms and coastal refineries. The Gulf Coast hosts ~45% "
                "of US refining capacity and significant LNG export infrastructure. "
                "Recovery typically takes 2-6 weeks depending on storm severity."
            ),
            "severity":            SEVERITY_HIGH,
            "status":              EVENT_STATUS_MONITORING,
            "latitude":            27.0,
            "longitude":           -90.0,
            "country_code":        "US",
            "trade_route":         None,
            "commodity":           "crude oil, natural gas, LNG",
            "affected_sectors":    json.dumps(["Energy"]),
            "affected_industries": json.dumps(["Oil & Gas Refining & Marketing", "Oil & Gas Storage & Transportation"]),
            "beneficiary_sectors": json.dumps(["Energy"]),
            "event_date":          "2024-06-01",
        },
        "links": [
            {
                "ticker":         "VLO",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Gulf Coast refinery output during storm shutdown and recovery",
                "will_redirect":  "Midwest and West Coast refinery capacity absorbs some displaced demand",
                "impact_notes":   "Valero largest US refiner by capacity; heavy Gulf Coast concentration in Port Arthur, Corpus Christi, Texas City",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "MPC",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Galveston Bay and Gulf Coast refinery throughput",
                "will_redirect":  "Midwest PADD 2 refinery network partially offsets",
                "impact_notes":   "Marathon Petroleum Texas City and Garyville (Louisiana) refineries vulnerable to Gulf storms",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "PSX",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Lake Charles and Sweeny refinery output",
                "will_redirect":  "East Coast and West Coast refinery network",
                "impact_notes":   "Phillips 66 significant Gulf Coast refining and NGL fractionation exposure",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "LNG",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Sabine Pass LNG export terminal throughput",
                "will_redirect":  "European buyers divert to spot market; global LNG prices spike",
                "impact_notes":   "Cheniere Energy Sabine Pass (Louisiana) is largest US LNG export facility; direct storm exposure",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "DVN",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Devon upstream crude production benefits from refinery-driven price spike",
                "impact_notes":   "Inland upstream producers benefit when Gulf Coast refinery shutdowns tighten crude spreads",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "COP",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "ConocoPhillips diversified upstream benefits from crude price spike post-storm",
                "impact_notes":   "Large diversified upstream producer; historically benefits from Gulf Coast supply shocks",
                "confidence":     CONFIDENCE_MEDIUM,
            },
        ],
    },

    # ── US Midwest Drought — Agricultural Supply Chain ─────────────────────────
    {
        "event": {
            "title":               "US Midwest Drought Agricultural Disruption",
            "region":              "North America",
            "event_type":          EVENT_TYPE_WEATHER,
            "description":         (
                "Severe drought across the US Corn Belt reduces corn and soybean yields, "
                "driving commodity prices sharply higher. The Midwest produces ~35% of "
                "global corn and ~35% of global soybeans. Drought also lowers Mississippi "
                "River levels, disrupting barge transportation of grain to Gulf export terminals."
            ),
            "severity":            SEVERITY_HIGH,
            "status":              EVENT_STATUS_MONITORING,
            "latitude":            41.5,
            "longitude":           -93.0,
            "country_code":        "US",
            "trade_route":         None,
            "commodity":           "corn, soybeans, grain",
            "affected_sectors":    json.dumps(["Consumer Staples", "Industrials"]),
            "affected_industries": json.dumps(["Agricultural Products & Services", "Packaged Foods & Meats"]),
            "beneficiary_sectors": json.dumps(["Materials"]),
            "event_date":          "2024-06-01",
        },
        "links": [
            {
                "ticker":         "ADM",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "corn and soybean processing volumes at Corn Belt facilities",
                "will_redirect":  "South American sourcing (Brazil, Argentina) at higher cost",
                "impact_notes":   "Archer-Daniels-Midland largest US grain processor; Corn Belt drought directly compresses crush margins",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "BG",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "US grain origination and export volumes through Gulf terminals",
                "will_redirect":  "Brazilian and Argentine origination fills gap at higher logistics cost",
                "impact_notes":   "Bunge Global major US grain exporter; Mississippi River low water levels compound disruption",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "TSN",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "cost-competitive poultry, beef, and pork protein at prior feed costs",
                "will_redirect":  "Pass input cost increases to retail pricing; some production idling",
                "impact_notes":   "Tyson Foods feed costs (corn, soybean meal) are largest input; drought-driven grain price spike compresses margins",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "GIS",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "stable input cost base for grain-dependent packaged food production",
                "will_redirect":  "Hedged positions partially offset; longer-term contract renegotiation",
                "impact_notes":   "General Mills corn and wheat input exposure across cereal, snacks, baking segments",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "MOS",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Drought triggers aggressive replanting next season; fertilizer demand spikes",
                "impact_notes":   "Mosaic (potash, phosphate) historically sees order acceleration after major drought years as farmers maximize next-season yield",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "NTR",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Nutrien retail ag network benefits from post-drought replanting demand surge",
                "impact_notes":   "Nutrien largest global potash producer and largest North American ag retail network; benefits from recovery season",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "DE",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Deere precision ag equipment demand rises as farmers invest in drought-resilient infrastructure",
                "impact_notes":   "John Deere historically sees equipment order strength following drought years as government programs fund farm recovery",
                "confidence":     CONFIDENCE_MEDIUM,
            },
        ],
    },

    # ── Pacific Rim Earthquake — Auto & Electronics Manufacturing ──────────────
    {
        "event": {
            "title":               "Pacific Rim Earthquake Manufacturing Disruption",
            "region":              "East Asia",
            "event_type":          EVENT_TYPE_WEATHER,
            "description":         (
                "Major earthquake in Japan or Taiwan disrupts auto parts and electronics "
                "component manufacturing. Japan supplies ~40% of global auto parts by value "
                "and is the dominant producer of specialty chemicals, bearings, and electronic "
                "components. A magnitude 7+ event can halt production for weeks and trigger "
                "cascading shortages across global auto and consumer electronics supply chains."
            ),
            "severity":            SEVERITY_HIGH,
            "status":              EVENT_STATUS_MONITORING,
            "latitude":            35.7,
            "longitude":           139.7,
            "country_code":        "JP",
            "trade_route":         None,
            "commodity":           "auto parts, electronic components, specialty chemicals",
            "affected_sectors":    json.dumps(["Consumer Discretionary", "Technology", "Industrials"]),
            "affected_industries": json.dumps(["Automobile Manufacturers", "Auto Parts & Equipment", "Electronic Components"]),
            "beneficiary_sectors": json.dumps(["Consumer Discretionary"]),
            "event_date":          "2024-01-01",
        },
        "links": [
            {
                "ticker":         "TM",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "normal vehicle production volumes; domestic and export assembly lines halt",
                "will_redirect":  "North American and European plants operate on existing inventory buffer",
                "impact_notes":   "Toyota Japan domestic production accounts for ~40% of global output; just-in-time supply chain highly vulnerable",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "HMC",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Japan-sourced powertrain components and assembly output",
                "will_redirect":  "Ohio and Alabama US plants continue on stockpiled parts",
                "impact_notes":   "Honda Japan operations supply critical powertrain and electronics components to global assembly network",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "F",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "vehicles requiring Japan-sourced electronic control units and specialty components",
                "will_redirect":  "Domestic US sourcing where available; production resequencing",
                "impact_notes":   "Ford relies on Japanese suppliers for sensors, ECUs, and specialty steel; 2011 Tohoku earthquake precedent",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "GM",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "full vehicle production lines dependent on Japanese electronic components",
                "will_redirect":  "Dual-sourcing contingency plans activated; production prioritized to highest-margin vehicles",
                "impact_notes":   "GM Japan component exposure across EV battery management, infotainment, and transmission systems",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "MU",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Japan-based DRAM and NAND flash production from Hiroshima fab",
                "will_redirect":  "Idaho and Virginia US fabs; Taiwan production absorbs some volume",
                "impact_notes":   "Micron Hiroshima fab is major DRAM production site; earthquake risk is explicit in annual filings",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "STLA",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Jeep and Ram models requiring Japan-sourced specialty components",
                "will_redirect":  "European and North American parts substitution where feasible",
                "impact_notes":   "Stellantis (Jeep, Ram, Dodge, Chrysler) has concentrated Japan supplier relationships for transmissions and electronics",
                "confidence":     CONFIDENCE_MEDIUM,
            },
        ],
    },
    # ── Consumer Staples Warehouse Fire — REIT / Paper Goods Chain ────────────
    {
        "event": {
            "title":               "US Distribution Warehouse Fire — Consumer Staples",
            "region":              "United States",
            "event_type":          EVENT_TYPE_FIRE,
            "description":         (
                "A major fire at an industrial distribution warehouse destroys millions in "
                "consumer staples inventory (paper goods, household products, food/bev). "
                "Industrial REITs own and lease the facilities; consumer staples manufacturers "
                "and retailers absorb the inventory loss. Regional supply shortages of "
                "paper goods typically last 4-8 weeks while alternative distribution routes "
                "are established."
            ),
            "severity":            SEVERITY_HIGH,
            "status":              EVENT_STATUS_MONITORING,
            "latitude":            34.1,
            "longitude":           -117.5,
            "country_code":        "US",
            "trade_route":         None,
            "commodity":           "paper goods, household products, consumer staples",
            "affected_sectors":    json.dumps(["Consumer Staples", "Real Estate"]),
            "affected_industries": json.dumps(["Household Products", "Paper & Packaging", "Industrial REITs"]),
            "beneficiary_sectors": json.dumps(["Consumer Staples", "Real Estate"]),
            "event_date":          "2024-01-01",
        },
        "links": [
            {
                "ticker":         "PLD",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "leased warehouse space at affected facility; tenant operations disrupted",
                "will_redirect":  "Alternative Prologis facilities in adjacent markets absorb displaced tenants",
                "impact_notes":   "Prologis is largest US industrial REIT; warehouse fires create short-term tenant dislocation and insurance claims",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "EXR",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Extra Space Storage benefits as displaced tenants seek overflow storage during facility rebuild",
                "impact_notes":   "Self-storage REITs historically see occupancy and pricing benefits from regional warehouse disruptions",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "KMB",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Kimberly-Clark paper goods inventory in affected region for 4-8 weeks",
                "will_redirect":  "Reroute from alternative distribution centers; accelerate manufacturing output",
                "impact_notes":   "Kimberly-Clark (Kleenex, Scott, Huggies) primary beneficiary of warehouse fire disruption on paper goods inventory",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "PG",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "P&G household product inventory in fire-affected distribution zone",
                "will_redirect":  "Alternative DC network; prioritize highest-velocity SKUs",
                "impact_notes":   "Procter & Gamble broad household product exposure; large distribution warehouse tenant",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "CLX",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Clorox benefits from competitor inventory shortage; shelf space shifts during restock period",
                "impact_notes":   "Household products competitor positioned to capture incremental shelf allocation during KMB/PG restock",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "WMT",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "full household products shelf availability in affected region stores",
                "will_redirect":  "Cross-region inventory transfer; temporary substitution SKUs",
                "impact_notes":   "Walmart as major retailer bears out-of-stock risk; supply constraints from distributor to shelf",
                "confidence":     CONFIDENCE_MEDIUM,
            },
        ],
    },

    # ── West Coast Port Labor Strike — Container Shipping ─────────────────────
    {
        "event": {
            "title":               "West Coast Port Labor Strike (ILWU)",
            "region":              "North America",
            "event_type":          EVENT_TYPE_LABOR,
            "description":         (
                "A strike or work slowdown by the International Longshore and Warehouse Union "
                "(ILWU) at West Coast ports (Los Angeles, Long Beach, Seattle, Oakland) halts "
                "container throughput. The Ports of LA/Long Beach handle ~40% of all US "
                "container imports. A full strike shifts imports to Gulf Coast and East Coast "
                "ports, driving up freight rates across all ocean carriers and straining "
                "intermodal rail capacity."
            ),
            "severity":            SEVERITY_CRITICAL,
            "status":              EVENT_STATUS_MONITORING,
            "latitude":            33.7,
            "longitude":           -118.2,
            "country_code":        "US",
            "trade_route":         "Trans-Pacific",
            "commodity":           "containerized goods, consumer electronics, apparel, auto parts",
            "affected_sectors":    json.dumps(["Industrials", "Consumer Discretionary", "Consumer Staples", "Technology"]),
            "affected_industries": json.dumps(["Marine Shipping", "Air Freight & Logistics", "Trucking"]),
            "beneficiary_sectors": json.dumps(["Industrials", "Energy"]),
            "event_date":          "2024-01-01",
        },
        "links": [
            {
                "ticker":         "MATX",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "normal West Coast port container throughput and on-time vessel schedules",
                "will_redirect":  "Gulf and East Coast vessel rerouting where feasible; premium surcharges",
                "impact_notes":   "Matson Navigation West Coast–Hawaii and transpacific services directly impacted by ILWU strike",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "ZIM",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Trans-Pacific import volumes via West Coast gateway ports",
                "will_redirect":  "East Coast and Gulf port alternatives at higher cost and transit time",
                "impact_notes":   "ZIM significant West Coast trans-Pacific exposure; strike forces cargo diversion and vessel schedule disruption",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "EXPD",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Expeditors captures premium freight forwarding fees as shippers scramble for alternatives",
                "impact_notes":   "Freight forwarders historically benefit from port disruptions; clients pay premium rates for alternate routing and air freight surge",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "CHRW",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "C.H. Robinson benefits from intermodal and trucking demand surge as cargo reroutes inland",
                "impact_notes":   "Third-party logistics provider benefits from rate spike and volume surge through alternative ports and rail",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "UNP",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Union Pacific intermodal network captures diverted cargo flowing through Gulf ports toward Midwest",
                "impact_notes":   "Rail benefits from truck overflow and rerouted import containers; intermodal pricing power increases during port strikes",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "AMZN",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "on-time delivery of West Coast-inbound consumer goods and Prime inventory replenishment",
                "will_redirect":  "Air freight surge for high-priority SKUs; East Coast DC inventory rebalancing",
                "impact_notes":   "Amazon West Coast fulfillment centers heavily dependent on Trans-Pacific import flow; strike creates inventory shortfall",
                "confidence":     CONFIDENCE_MEDIUM,
            },
        ],
    },

    # ── South Asia Fertilizer Import Shortage ────────────────────────────────
    {
        "event": {
            "title":               "South Asia Fertilizer Import Shortage",
            "region":              "South Asia",
            "event_type":          EVENT_TYPE_SANCTIONS,
            "description":         (
                "Russia and Belarus together supply ~40% of global potash exports. "
                "Post-Ukraine invasion sanctions cut off Russian/Belarusian potash "
                "and urea to South Asia (India, Bangladesh, Pakistan, Sri Lanka), "
                "which are heavily import-dependent for nitrogen and potash fertilizers. "
                "Natural gas supply restrictions also constrain domestic nitrogen "
                "(urea/ammonia) production in the region, driving food inflation and "
                "crop yield reductions across staples (wheat, rice, lentils) with "
                "knock-on effects on global food prices."
            ),
            "severity":            SEVERITY_HIGH,
            "status":              EVENT_STATUS_ACTIVE,
            "latitude":            20.0,
            "longitude":           78.0,
            "country_code":        "IN",
            "trade_route":         None,
            "commodity":           "fertilizers, potash, urea, ammonia, DAP",
            "affected_sectors":    json.dumps(["Consumer Staples", "Materials", "Energy"]),
            "affected_industries": json.dumps(["Agricultural Products & Services", "Fertilizers & Agricultural Chemicals", "Packaged Foods & Meats"]),
            "beneficiary_sectors": json.dumps(["Materials", "Energy"]),
            "event_date":          "2022-02-24",
        },
        "links": [
            {
                "ticker":         "MOS",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Mosaic captures South Asian demand diverted from sanctioned Russian/Belarusian suppliers; buyers shift to Canadian and Middle Eastern potash",
                "impact_notes":   "Mosaic is world's largest potash and phosphate producer; Russian/Belarusian sanctions redirect ~40% of global potash trade to non-sanctioned producers",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "NTR",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Nutrien (Canpotex consortium) potash exports surge to fill South Asian supply gap from sanctioned Belarus/Russia",
                "impact_notes":   "Nutrien is world's largest potash producer; Canpotex (Nutrien + Mosaic) handles Canadian potash exports and directly captures displaced South Asian demand",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "CF",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "CF Industries benefits as Russian urea export restrictions and natural gas supply cuts drive global nitrogen prices sharply higher",
                "impact_notes":   "CF Industries is the largest North American nitrogen fertilizer producer (urea, ammonia, UAN); Russian gas restrictions directly boost CF pricing power",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "ICL",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "ICL Group positioned as alternative non-sanctioned potash and phosphate supplier; South Asian buyers shift from Belarusian Belaruskali to ICL and North American producers",
                "impact_notes":   "ICL Israel-based potash and phosphate producer; direct beneficiary as South Asian import tenders specify non-Russian/Belarusian origin",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "ADM",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "stable-cost South Asian grain origination — fertilizer shortage reduces regional crop yields",
                "will_redirect":  "South American and US domestic sourcing substitutes; South Asian food inflation feeds into global commodity prices",
                "impact_notes":   "Archer-Daniels-Midland global grain trading impacted by South Asian yield reductions; downstream food inflation raises procurement costs across wheat, rice, lentils",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "BG",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "normal South Asian agricultural commodity procurement at pre-shortage input costs",
                "will_redirect":  "Bunge reallocates global origination; South Asian wheat/rice supply tightness boosts commodity trading margins but raises cost basis",
                "impact_notes":   "Bunge Global significant South Asia grain trade exposure; fertilizer-driven yield shortfall tightens wheat and rice supply regionally",
                "confidence":     CONFIDENCE_MEDIUM,
            },
        ],
    },

    # ── Industrial REIT Capacity Shock — E-Commerce Logistics ─────────────────
    {
        "event": {
            "title":               "Industrial REIT Capacity Shock — E-Commerce Logistics",
            "region":              "United States",
            "event_type":          EVENT_TYPE_CONFLICT,
            "description":         (
                "A sudden surge in e-commerce demand (pandemic-type event, major retail "
                "consolidation, or infrastructure loss) creates acute shortage of distribution "
                "and last-mile logistics warehouse space. Available Class A industrial REIT "
                "space is absorbed within 90 days, driving vacancy rates to record lows and "
                "lease rates 30-50% above prior market. Alternative: sudden demand collapse "
                "(post-pandemic normalization) drives oversupply and rate compression."
            ),
            "severity":            SEVERITY_MEDIUM,
            "status":              EVENT_STATUS_MONITORING,
            "latitude":            40.7,
            "longitude":           -74.0,
            "country_code":        "US",
            "trade_route":         None,
            "commodity":           "warehouse space, last-mile logistics, 3PL capacity",
            "affected_sectors":    json.dumps(["Real Estate", "Industrials", "Consumer Discretionary"]),
            "affected_industries": json.dumps(["Industrial REITs", "Air Freight & Logistics", "Specialty Retail"]),
            "beneficiary_sectors": json.dumps(["Real Estate", "Industrials"]),
            "event_date":          "2024-01-01",
        },
        "links": [
            {
                "ticker":         "PLD",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Prologis captures demand surge; portfolio vacancy drops; rents reset 30-50% higher at lease renewal",
                "impact_notes":   "Prologis largest global logistics REIT; tightest supply in key infill markets (LA, NJ, Chicago, Seattle)",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "DRE",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Duke Realty (now Prologis post-merger) benefits from same industrial demand surge dynamic",
                "impact_notes":   "Duke Realty legacy portfolio acquired by Prologis 2022; increases Prologis market share in Midwest and Southeast",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "REXR",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Rexford Industrial concentrates in Southern California infill — most supply-constrained market in US logistics",
                "impact_notes":   "Rexford pure-play Southern California industrial REIT; LA/OC/IE markets see largest rent spikes during demand surges",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "FR",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "First Industrial Realty benefits from demand surge across Midwest and Southeast distribution corridors",
                "impact_notes":   "First Industrial diversified across key Midwest and Southeast logistics hubs; benefits from 3PL capacity tightening",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "AMZN",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "cost-competitive expansion of last-mile fulfillment network during capacity shortage",
                "will_redirect":  "Premium lease rates accepted to secure strategic locations; build-to-suit development accelerated",
                "impact_notes":   "Amazon largest single tenant in US industrial real estate; capacity shock directly impacts fulfillment expansion plans",
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
