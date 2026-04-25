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
    EVENT_TYPE_NATURAL_DISASTER,
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

    # ── European Natural Gas Disruption — Russia Pipeline Cutoff ─────────────
    {
        "event": {
            "title":               "European Natural Gas Supply Cutoff — Russia",
            "region":              "Europe",
            "event_type":          EVENT_TYPE_CONFLICT,
            "description":         (
                "Russia halted natural gas flows to Europe via Nord Stream 1, Yamal-Europe, "
                "and TurkStream following the Ukraine invasion and subsequent sanctions. "
                "Europe imported ~40% of its natural gas from Russia pre-war. The cutoff "
                "triggered a global LNG demand surge, record European gas prices, and a "
                "structural shift toward US LNG exports as Europe rapidly built import "
                "terminals to replace pipeline gas."
            ),
            "severity":            SEVERITY_CRITICAL,
            "status":              EVENT_STATUS_ACTIVE,
            "latitude":            51.2,
            "longitude":           10.5,
            "country_code":        "DE",
            "trade_route":         None,
            "commodity":           "natural gas, LNG",
            "affected_sectors":    json.dumps(["Energy", "Industrials", "Materials"]),
            "affected_industries": json.dumps(["Oil & Gas Storage & Transportation", "Specialty Chemicals", "Electric Utilities"]),
            "beneficiary_sectors": json.dumps(["Energy"]),
            "event_date":          "2022-02-24",
        },
        "links": [
            {
                "ticker":         "LNG",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Sabine Pass and Corpus Christi LNG exports surge to fill European pipeline gas gap",
                "impact_notes":   "Cheniere Energy largest US LNG exporter; European buyers signed long-term US LNG contracts to replace Russian pipeline gas",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "AR",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Antero Resources Appalachian natural gas production captures European LNG export premium",
                "impact_notes":   "Antero one of largest US natural gas producers; European LNG demand drove Henry Hub and Appalachian gas pricing higher in 2022-2023",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "EQT",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "EQT largest US natural gas producer by volume; LNG export demand drives sustained pricing uplift",
                "impact_notes":   "EQT Appalachian basin production feeds LNG export terminals; European structural shift to US LNG is multi-year tailwind",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "CTRA",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Coterra Energy Marcellus natural gas production benefits from LNG export-driven demand",
                "impact_notes":   "Coterra (Cabot + Cimarex merger) significant Marcellus gas exposure; LNG export boom is primary pricing catalyst",
                "confidence":     CONFIDENCE_MEDIUM,
            },
        ],
    },

    # ── Helium Shortage — Federal Reserve Depletion + Geopolitical Supply Risk ─
    {
        "event": {
            "title":               "Global Helium Shortage — Reserve Depletion and Supply Concentration",
            "region":              "Global",
            "event_type":          EVENT_TYPE_SANCTIONS,
            "description":         (
                "The US Bureau of Land Management Federal Helium Reserve — historically the "
                "world's largest helium stockpile — has been privatized and drawn down. Russia "
                "(Amur Gas Processing Plant) and Qatar together supply ~50% of global helium. "
                "Russia's Amur plant fire in 2021 and subsequent geopolitical risk created "
                "recurring global helium shortages. Helium is critical for semiconductor fab "
                "cooling, MRI magnet cryogenics, fiber optic production, and space programs. "
                "No practical substitute exists at scale."
            ),
            "severity":            SEVERITY_HIGH,
            "status":              EVENT_STATUS_MONITORING,
            "latitude":            31.8,
            "longitude":           34.8,
            "country_code":        "US",
            "trade_route":         None,
            "commodity":           "helium",
            "affected_sectors":    json.dumps(["Technology", "Healthcare", "Industrials"]),
            "affected_industries": json.dumps(["Semiconductors", "Semiconductor Equipment", "Health Care Equipment", "Industrial Gases"]),
            "beneficiary_sectors": json.dumps(["Materials"]),
            "event_date":          "2021-08-05",
        },
        "links": [
            {
                "ticker":         "APD",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Air Products captures pricing power as one of four global helium distributors; supply constraints expand margins",
                "impact_notes":   "Air Products is one of four major global helium distributors; shortage-driven pricing passes through directly to margins",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "LIN",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Linde is second-largest global helium supplier; shortage tightens contract pricing and spot premiums",
                "impact_notes":   "Linde (Praxair + Linde merger) one of two dominant global industrial gas companies; helium scarcity is direct margin tailwind",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "AMAT",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "fab equipment installation and testing requiring uninterrupted helium supply for cooling and leak detection",
                "will_redirect":  "Helium conservation protocols; equipment qualification with higher-purity recycled helium",
                "impact_notes":   "Applied Materials semiconductor manufacturing equipment requires helium for chamber cooling and process gas; shortage disrupts fab tool installation timelines",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "SYK",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "MRI system installation and magnet re-energization on normal timelines during shortage",
                "will_redirect":  "Zero-boil-off magnet technology in newer systems reduces ongoing helium consumption",
                "impact_notes":   "Stryker MRI and imaging businesses require liquid helium to cool superconducting MRI magnets; shortage creates installation backlogs",
                "confidence":     CONFIDENCE_MEDIUM,
            },
        ],
    },

    # ── Lithium Supply Shock — Battery Supply Chain ───────────────────────────
    {
        "event": {
            "title":               "Lithium Supply Shock — EV Battery Supply Chain",
            "region":              "South America",
            "event_type":          EVENT_TYPE_CONFLICT,
            "description":         (
                "The Lithium Triangle (Chile, Argentina, Bolivia) holds ~55% of global "
                "lithium reserves. Chile nationalization moves (2022-2023), Argentina's "
                "political instability, and Bolivia's state-monopoly structure constrain "
                "new project development. China controls ~65% of global lithium processing "
                "capacity. Combined with a structural EV demand surge, lithium carbonate "
                "prices spiked 10x from 2020 to 2022 peak. A supply disruption (political, "
                "weather, or Chinese processing curbs) would directly compress EV battery "
                "margins and delay OEM production targets."
            ),
            "severity":            SEVERITY_HIGH,
            "status":              EVENT_STATUS_MONITORING,
            "latitude":            -22.9,
            "longitude":           -68.2,
            "country_code":        "CL",
            "trade_route":         None,
            "commodity":           "lithium carbonate, lithium hydroxide",
            "affected_sectors":    json.dumps(["Materials", "Consumer Discretionary", "Industrials"]),
            "affected_industries": json.dumps(["Specialty Chemicals", "Automobile Manufacturers", "Auto Parts & Equipment", "Electrical Components & Equipment"]),
            "beneficiary_sectors": json.dumps(["Materials"]),
            "event_date":          "2022-01-01",
        },
        "links": [
            {
                "ticker":         "ALB",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Albemarle largest US lithium producer; supply disruption narrows available non-China supply, expanding ALB pricing power",
                "impact_notes":   "Albemarle (Greenbushes Australia + Chile Atacama brine) is largest Western lithium producer; supply shocks drive contract repricing",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "SQM",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Sociedad Quimica y Minera controls Atacama Salar brine; Chile disruptions constrain SQM production but pricing power offsets volume loss",
                "impact_notes":   "SQM is world's second-largest lithium producer from Atacama brine; near-term supply shock is mixed — pricing up but volume risk rises",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "TSLA",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "EV production at target volumes if lithium carbonate pricing spikes above $80K/tonne",
                "will_redirect":  "Tesla has direct long-term lithium supply agreements with ALB and SQM; CATL NMC cells partially buffered",
                "impact_notes":   "Tesla battery cost is largest COGS component; lithium price spike directly compresses gross margin and delays price reductions",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "GM",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Ultium EV battery platform cell production at cost targets if lithium spikes",
                "will_redirect":  "GM-LG Energy Solution Ultium Cells JVs have some contracted lithium supply; spot exposure on incremental volume",
                "impact_notes":   "GM Ultium EV platform is entirely dependent on lithium NMC chemistry; battery cost is primary EV profitability constraint",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "F",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "F-150 Lightning and Mustang Mach-E production at target volumes if lithium costs surge",
                "will_redirect":  "Ford BlueOval SK battery JV (Ford + SK Innovation) has Korean battery supply; lithium sourcing partially via ALB contracts",
                "impact_notes":   "Ford EV losses ($4-5B annually) are directly amplified by lithium price spikes; battery cost improvement is critical path to EV profitability",
                "confidence":     CONFIDENCE_MEDIUM,
            },
        ],
    },

    # ── Indonesia Nickel Export Ban — EV Battery Supply Chain ─────────────────
    {
        "event": {
            "title":               "Indonesia Nickel Export Ban — EV Battery Precursor Supply",
            "region":              "Southeast Asia",
            "event_type":          EVENT_TYPE_SANCTIONS,
            "description":         (
                "Indonesia banned unprocessed nickel ore exports in January 2020 to force "
                "domestic value-add processing. Indonesia holds ~22% of global nickel "
                "reserves and has become the world's largest nickel producer. The ban, "
                "combined with Indonesia's goal to become the dominant EV battery supply "
                "chain hub (HPAL nickel processing → MHP → NMC battery precursors), "
                "disrupted supply to Japanese and South Korean battery manufacturers. "
                "Chinese smelters (backed by CATL/BYD) built processing capacity inside "
                "Indonesia to comply, reshaping global nickel trade flows."
            ),
            "severity":            SEVERITY_HIGH,
            "status":              EVENT_STATUS_ACTIVE,
            "latitude":            -0.8,
            "longitude":           120.0,
            "country_code":        "ID",
            "trade_route":         None,
            "commodity":           "nickel ore, nickel sulfate, NMC battery precursors",
            "affected_sectors":    json.dumps(["Materials", "Consumer Discretionary", "Industrials"]),
            "affected_industries": json.dumps(["Diversified Metals & Mining", "Steel", "Automobile Manufacturers", "Electrical Components & Equipment"]),
            "beneficiary_sectors": json.dumps(["Materials"]),
            "event_date":          "2020-01-01",
        },
        "links": [
            {
                "ticker":         "VALE",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Vale Indonesia (PT Vale Indonesia) operates integrated nickel mining and smelting inside Indonesia — compliant with export ban; benefits from competitor exit",
                "impact_notes":   "Vale largest nickel producer in Indonesia with integrated matte smelting; peers without local processing lost market access, improving Vale's relative position",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "FCX",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Freeport-McMoRan Grasberg mine copper-cobalt byproducts benefit from tighter nickel/base metal supply",
                "impact_notes":   "FCX benefits indirectly via base metal price strength; Grasberg copper byproducts appreciate when nickel supply tightens battery metals broadly",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "TSLA",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "battery cell production at target cost if Indonesian HPAL nickel supply is disrupted",
                "will_redirect":  "Tesla is shifting toward LFP chemistry (no nickel) for standard range; NCA/NMC for longer range still requires nickel",
                "impact_notes":   "Tesla NMC and NCA battery chemistries require high-purity nickel sulfate; Indonesia supply disruption directly impacts CATL and Panasonic cell pricing",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "GM",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Ultium NMC cell production at target costs if Indonesian nickel sulfate supply is disrupted",
                "will_redirect":  "LG Energy Solution Ultium JV sources from multiple suppliers; some spot exposure on incremental volume",
                "impact_notes":   "GM Ultium platform uses NMC chemistry requiring high-purity nickel; Indonesia is the dominant global source for battery-grade nickel sulfate",
                "confidence":     CONFIDENCE_MEDIUM,
            },
        ],
    },

    # ── China Rare Earth Export Controls ─────────────────────────────────────
    {
        "event": {
            "title":               "China Rare Earth Export Controls",
            "region":              "East Asia",
            "event_type":          EVENT_TYPE_SANCTIONS,
            "description":         (
                "China controls ~85% of global rare earth processing and ~60% of global "
                "mining. Export controls on gallium (July 2023), germanium (August 2023), "
                "and graphite (October 2023) demonstrated China's willingness to weaponize "
                "critical mineral supply chains. NdFeB permanent magnets (neodymium, "
                "dysprosium) are essential for F-35 actuators, guided missile systems, and "
                "EV traction motors. A full rare earth export embargo would ground US "
                "defense production within 12-18 months."
            ),
            "severity":            SEVERITY_CRITICAL,
            "status":              EVENT_STATUS_ACTIVE,
            "latitude":            39.9,
            "longitude":           116.4,
            "country_code":        "CN",
            "trade_route":         None,
            "commodity":           "rare earth elements, neodymium, dysprosium, gallium, germanium, graphite",
            "affected_sectors":    json.dumps(["Industrials", "Technology", "Consumer Discretionary"]),
            "affected_industries": json.dumps(["Aerospace & Defense", "Semiconductors", "Semiconductor Equipment", "Automobile Manufacturers", "Electrical Components & Equipment"]),
            "beneficiary_sectors": json.dumps(["Materials"]),
            "event_date":          "2023-07-03",
        },
        "links": [
            {
                "ticker":         "MP",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "MP Materials Mountain Pass mine is only active US rare earth mining and processing site; export controls redirect Western buyers to MP",
                "impact_notes":   "MP Materials produces ~15% of global rare earth concentrate; Mountain Pass is the only operating US rare earth mine; Chinese export controls are direct pricing catalyst",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "LMT",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "F-35, PAC-3, and THAAD production at full rate if NdFeB magnet supply is disrupted",
                "will_redirect":  "DoD NDAA Section 881 rare earth supply chain diversification programs; domestic sourcing from MP Materials being developed",
                "impact_notes":   "Lockheed Martin uses rare earth permanent magnets in F-35 actuators, guided missiles, radar systems; Chinese embargo would directly halt production",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "RTX",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Patriot missile, Javelin, and Stinger production at target rates without Chinese rare earth magnets",
                "will_redirect":  "Raytheon Technologies DoD-funded rare earth magnet qualification from non-Chinese sources underway",
                "impact_notes":   "RTX guided munitions and radar systems require NdFeB magnets; Ukrainian war demand for Patriot and Stinger amplifies supply chain urgency",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "NOC",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "B-21 Raider, GBSD ICBM, and E-2D Advanced Hawkeye production without Chinese rare earth components",
                "will_redirect":  "Northrop Grumman DoD supply chain hardening programs; domestic and allied nation alternative sourcing",
                "impact_notes":   "Northrop Grumman advanced defense systems depend on rare earth elements for motors, actuators, and electronics; GBSD nuclear modernization adds urgency",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "AMAT",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "semiconductor fab equipment production at full rate if gallium and germanium supply is restricted",
                "will_redirect":  "Applied Materials qualifying alternative gallium nitride and germanium suppliers in Canada, Australia, EU",
                "impact_notes":   "China's gallium/germanium export controls directly impact compound semiconductor and wafer fab equipment supply chains",
                "confidence":     CONFIDENCE_MEDIUM,
            },
        ],
    },

    # ── Russia Palladium Sanctions ────────────────────────────────────────────
    {
        "event": {
            "title":               "Russia Palladium Supply Disruption — Auto Catalytic Converters",
            "region":              "Eastern Europe",
            "event_type":          EVENT_TYPE_SANCTIONS,
            "description":         (
                "Russia (Norilsk Nickel) supplies ~40-45% of global palladium, the dominant "
                "precious group metal in gasoline catalytic converters. Post-Ukraine invasion "
                "Western sanctions and insurance/shipping restrictions create supply "
                "uncertainty. Palladium prices spiked to $3,400/oz in March 2022. "
                "Automotive manufacturers use ~2.5-3g palladium per vehicle catalytic "
                "converter; disruption raises per-vehicle production costs and creates "
                "assembly-line shortages if hedges expire."
            ),
            "severity":            SEVERITY_HIGH,
            "status":              EVENT_STATUS_ACTIVE,
            "latitude":            69.3,
            "longitude":           88.2,
            "country_code":        "RU",
            "trade_route":         None,
            "commodity":           "palladium, platinum group metals",
            "affected_sectors":    json.dumps(["Consumer Discretionary", "Materials", "Industrials"]),
            "affected_industries": json.dumps(["Automobile Manufacturers", "Auto Parts & Equipment", "Precious Metals & Minerals"]),
            "beneficiary_sectors": json.dumps(["Materials"]),
            "event_date":          "2022-02-24",
        },
        "links": [
            {
                "ticker":         "SBSW",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Sibanye-Stillwater is world's second-largest palladium producer (Montana, US + South Africa); captures demand diverted from Russian supply",
                "impact_notes":   "SBSW Stillwater Mine (Montana) is largest US PGM producer; Russian sanctions redirect Western automotive buyers to SBSW, driving ASP higher",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "F",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "catalytic converter production at normal cost if palladium spot exceeds $3,000/oz",
                "will_redirect":  "Ford hedging program limits near-term exposure; platinum substitution in gasoline cats being tested",
                "impact_notes":   "Ford produces ~4M gasoline vehicles annually; at 2.5g/vehicle, 10t palladium annual exposure — Russian supply disruption is direct cost headwind",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "GM",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "catalytic converter supply at normal PGM costs across ICE and hybrid vehicle lines",
                "will_redirect":  "GM hedging and strategic stockpile partially offsets; accelerated shift to EVs (zero catalytic converter requirement) is structural mitigation",
                "impact_notes":   "GM largest US automaker by ICE volume; palladium exposure across Chevrolet, Buick, Cadillac, GMC gasoline and hybrid powertrains",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "STLA",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Jeep, Ram, and Dodge ICE catalytic converter supply at pre-disruption PGM costs",
                "will_redirect":  "Stellantis European operations partially hedged via South African PGM suppliers; Ram truck lineup has high palladium loading per unit",
                "impact_notes":   "Stellantis (Jeep RAM Dodge Chrysler) heavy ICE/truck lineup has highest per-unit palladium loading among US-market OEMs",
                "confidence":     CONFIDENCE_MEDIUM,
            },
        ],
    },

    # ── Congo Cobalt Disruption — EV Battery Supply Chain ────────────────────
    {
        "event": {
            "title":               "Congo Cobalt Disruption — EV Battery Supply Chain",
            "region":              "Sub-Saharan Africa",
            "event_type":          EVENT_TYPE_CONFLICT,
            "description":         (
                "The Democratic Republic of Congo supplies ~70% of global cobalt, primarily "
                "from the Katanga province. Armed conflict, political instability, state "
                "royalty disputes, and artisanal mining violence periodically disrupt output "
                "from Glencore, CMOC (formerly Freeport Cobalt), and smaller operators. "
                "Cobalt is an essential cathode component in NMC and NCA lithium-ion battery "
                "chemistries used in EVs, consumer electronics, and grid storage. A major "
                "disruption could delay EV production and spike battery cell costs."
            ),
            "severity":            SEVERITY_HIGH,
            "status":              EVENT_STATUS_MONITORING,
            "latitude":            -10.7,
            "longitude":           26.5,
            "country_code":        "CD",
            "trade_route":         None,
            "commodity":           "cobalt, cobalt hydroxide, NMC battery cathode",
            "affected_sectors":    json.dumps(["Materials", "Consumer Discretionary", "Technology"]),
            "affected_industries": json.dumps(["Diversified Metals & Mining", "Automobile Manufacturers", "Electronic Components", "Electrical Components & Equipment"]),
            "beneficiary_sectors": json.dumps(["Materials"]),
            "event_date":          "2024-01-01",
        },
        "links": [
            {
                "ticker":         "TSLA",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "NCA (Panasonic) and NMC battery cell production at target costs if cobalt spikes",
                "will_redirect":  "Tesla shifting toward cobalt-free LFP chemistry for standard range globally; NCA cells for long-range/Cybertruck still cobalt-dependent",
                "impact_notes":   "Tesla uses cobalt-containing NCA chemistry in Panasonic 4680 and 2170 cells; DRC disruption directly impacts cell cost and availability",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "GM",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "Ultium NMC battery cells at target cost if cobalt hydroxide supply is disrupted",
                "will_redirect":  "LG Energy Solution Ultium JV has some hedged cobalt supply; reducing cobalt content in higher Ni NMC formulations",
                "impact_notes":   "GM Ultium NMC cells use cobalt; LG Energy Solution sources significant cobalt from DRC via Glencore; disruption flows through JV cost structure",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "VALE",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Vale produces cobalt as byproduct from Sudbury (Canada) and Onca Puma (Brazil) nickel operations; DRC disruption tightens non-DRC supply and lifts cobalt pricing",
                "impact_notes":   "Vale non-DRC cobalt byproduct production benefits from supply concentration risk premium when DRC instability flares",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "ALB",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Cobalt disruption accelerates shift to high-Ni, low-Co NMC and LFP formulations where ALB lithium is essential regardless of cobalt chemistry",
                "impact_notes":   "Albemarle lithium demand is chemistry-agnostic for the LFP substitution shift; DRC cobalt risk accelerates ALB's addressable market as LFP adoption grows",
                "confidence":     CONFIDENCE_MEDIUM,
            },
        ],
    },

    # ── Ukraine Neon / Krypton Shortage — Semiconductor Fab Gases ─────────────
    {
        "event": {
            "title":               "Ukraine Neon and Krypton Shortage — Semiconductor Fab Laser Gases",
            "region":              "Eastern Europe",
            "event_type":          EVENT_TYPE_CONFLICT,
            "description":         (
                "Ukraine supplies ~50% of global neon and ~30% of global krypton, both "
                "purified as byproducts of Ukrainian steel production. Neon is the primary "
                "gas in excimer lasers used for ArF immersion lithography (the dominant "
                "patterning technology for chips 28nm and below). Russia's February 2022 "
                "invasion halted Ukrainian neon and krypton production from Mariupol and "
                "Odessa. Chipmakers and equipment suppliers scrambled to qualify "
                "alternative suppliers in South Korea, China, and the EU."
            ),
            "severity":            SEVERITY_HIGH,
            "status":              EVENT_STATUS_ACTIVE,
            "latitude":            47.9,
            "longitude":           33.4,
            "country_code":        "UA",
            "trade_route":         None,
            "commodity":           "neon, krypton, xenon, industrial gases",
            "affected_sectors":    json.dumps(["Technology", "Industrials"]),
            "affected_industries": json.dumps(["Semiconductors", "Semiconductor Equipment"]),
            "beneficiary_sectors": json.dumps(["Materials"]),
            "event_date":          "2022-02-24",
        },
        "links": [
            {
                "ticker":         "AMAT",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "excimer laser-based lithography tool installation and calibration on normal schedule",
                "will_redirect":  "Applied Materials qualified South Korean and EU neon suppliers; internal gas recycling systems added to fab toolsets",
                "impact_notes":   "AMAT CVD and etch tools use neon; ArF excimer laser sources in litho tools require ultra-high-purity neon — shortage delays tool qualification and installation",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "LRCX",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "etch tool process qualification at affected fabs during neon shortage",
                "will_redirect":  "Lam Research adjusted process recipes and qualified alternative gas suppliers; gas recycling reduces neon consumption per wafer",
                "impact_notes":   "Lam Research plasma etch tools use neon as process gas; DUV litho scanner neon dependency propagates across entire fab patterning flow",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "ASML",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "ArF immersion and KrF excimer laser scanner production and shipment without neon/krypton",
                "will_redirect":  "ASML qualified Korean (SK, Neon Gas) and US (Matheson) alternative suppliers; gas recycling systems shipped with tools",
                "impact_notes":   "ASML ArF immersion scanners (most of 7nm-28nm installed base) use neon in excimer laser sources; krypton for KrF scanners; shortage was cited in 2022 earnings as supply chain risk",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "APD",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Air Products accelerated non-Ukraine neon and krypton production to fill supply gap",
                "impact_notes":   "Air Products industrial gas portfolio includes rare gases; Ukrainian supply disruption created pricing and volume opportunity for non-Ukraine rare gas producers",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "LIN",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Linde expanded rare gas (neon, krypton) supply from non-Ukrainian air separation plants globally",
                "impact_notes":   "Linde rare gas air separation operations in South Korea, Germany, US ramped production; semiconductor customers locked in long-term non-Ukrainian contracts",
                "confidence":     CONFIDENCE_MEDIUM,
            },
        ],
    },

    # ── Australia / Brazil Iron Ore Disruption ────────────────────────────────
    {
        "event": {
            "title":               "Australia and Brazil Iron Ore Supply Disruption",
            "region":              "Global",
            "event_type":          EVENT_TYPE_NATURAL_DISASTER,
            "description":         (
                "Australia (Pilbara — BHP, Rio Tinto, Fortescue) and Brazil (Vale Carajás) "
                "together supply ~80% of global seaborne iron ore. Disruption scenarios "
                "include: Pilbara cyclone season (Category 5 events close ports 2-4 weeks), "
                "Brazilian dam failures (Brumadinho January 2019 halted Vale output for "
                "months), or port infrastructure outages. Iron ore price spikes drive "
                "global hot-rolled coil and cold-rolled sheet prices higher, benefiting "
                "US-domestic integrated steelmakers who are net iron ore producers."
            ),
            "severity":            SEVERITY_HIGH,
            "status":              EVENT_STATUS_MONITORING,
            "latitude":            -23.5,
            "longitude":           -46.6,
            "country_code":        "BR",
            "trade_route":         None,
            "commodity":           "iron ore, hot-rolled coil, steel",
            "affected_sectors":    json.dumps(["Materials", "Industrials"]),
            "affected_industries": json.dumps(["Steel", "Diversified Metals & Mining", "Automobile Manufacturers", "Construction & Engineering"]),
            "beneficiary_sectors": json.dumps(["Materials"]),
            "event_date":          "2024-01-01",
        },
        "links": [
            {
                "ticker":         "X",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "US Steel owns Minnesota iron ore mines (Minntac, Keetac); Australian/Brazilian disruption tightens seaborne supply and lifts global steel prices",
                "impact_notes":   "US Steel is vertically integrated with Midwest iron ore mining; seaborne iron ore price spike improves domestic steel pricing power and widens spread vs. imports",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "CLF",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Cleveland-Cliffs is largest US iron ore pellet producer (Minorca, HBI plants); seaborne disruption is direct pricing tailwind",
                "impact_notes":   "CLF produces 28Mt iron ore pellets annually from Great Lakes region; fully integrated into blast furnace steel; Australian/Brazilian disruption lifts domestic iron ore and HRC pricing",
                "confidence":     CONFIDENCE_HIGH,
            },
            {
                "ticker":         "NUE",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Nucor EAF steel production uses scrap, not iron ore; benefits from elevated HRC pricing when seaborne iron ore tightens global steel supply",
                "impact_notes":   "Nucor largest US steel producer; EAF model insulated from iron ore cost directly, but benefits from steel price strength when integrated mills lose supply advantage",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "STLD",
                "role":           ROLE_BENEFICIARY,
                "cannot_provide": None,
                "will_redirect":  "Steel Dynamics EAF flat-roll mills benefit from steel price uplift driven by seaborne iron ore disruption",
                "impact_notes":   "Steel Dynamics Columbus mill and Sinton Texas flat-roll capacity benefits from HRC price strength; insulated from iron ore cost while capturing pricing upside",
                "confidence":     CONFIDENCE_MEDIUM,
            },
            {
                "ticker":         "F",
                "role":           ROLE_IMPACTED,
                "cannot_provide": "vehicle production at target cost if hot-rolled coil prices spike >30% on iron ore disruption",
                "will_redirect":  "Ford has steel purchase agreements but spot exposure on incremental volume; F-150 aluminum body partially offsets steel dependency",
                "impact_notes":   "Ford uses ~1,000 lbs steel per vehicle; HRC price spike of 30%+ adds ~$200/vehicle direct cost; F-Series truck steel content is highest-exposure product",
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
