"""Ahmedabad demo seed data for the CityShield / VisionScan crime heatmap.

Plain, importable data structures only -- no DB code, no external dependencies.

IMPORTANT (demo disclaimer):
    All values here are APPROXIMATIONS compiled from public sources (NCRB "Crime in
    India" city tables, Gujarat Police / mainstream-press coverage, and AMC monsoon
    reporting) for DEMONSTRATION PURPOSES ONLY. India's crime data is officially
    published at city/police-zone granularity, NOT per neighbourhood, so every
    locality-level "intensity" and "categories" assignment below is an EDITORIAL
    ESTIMATE for demo realism -- not an official crime rating of any neighbourhood.
    No real individuals are named. Do not use for operational, legal, or real-estate
    decisions. See docs/AHMEDABAD_CRIME_DATA.md for sources and methodology.

Exports:
    AREA_CRIME_PROFILE : dict[str, dict]   area -> {"intensity": str, "categories": list[str]}
    SEED_INCIDENTS     : list[dict]        generic public-reported incident seeds
    FLOOD_PRONE_AREAS  : list[str]         waterlogging / flood-prone localities
    INTENSITY_LEVELS   : tuple[str, ...]   allowed intensity values
    CRIME_CATEGORIES   : tuple[str, ...]   canonical category vocabulary
"""

# --- controlled vocabularies -------------------------------------------------

INTENSITY_LEVELS = ("low", "medium", "high")

# Canonical category slugs used across AREA_CRIME_PROFILE and SEED_INCIDENTS.
CRIME_CATEGORIES = (
    "cyber_fraud",
    "vehicle_theft",
    "chain_snatching",
    "burglary",
    "theft",
    "assault",
    "body_offences",
    "murder",
    "narcotics",
    "prohibition",
    "disaster_flood",
)

# --- area-wise crime profile -------------------------------------------------
# Intensity is "low" | "medium" | "high". We use the same three buckets the doc
# describes; "medium-high" in the doc is represented here as "high" or "medium"
# (rounded toward the dominant character) to keep the heatmap legend simple.

AREA_CRIME_PROFILE = {
    # West / west-central (planned suburbs -> cyber fraud, vehicle theft, snatching)
    "Navrangpura": {"intensity": "medium", "categories": ["chain_snatching", "cyber_fraud", "theft"]},
    "Ellisbridge": {"intensity": "medium", "categories": ["chain_snatching", "theft", "cyber_fraud"]},
    "Paldi": {"intensity": "medium", "categories": ["chain_snatching", "burglary", "theft"]},
    "Vasna": {"intensity": "medium", "categories": ["theft", "vehicle_theft", "burglary"]},
    "Vejalpur": {"intensity": "medium", "categories": ["vehicle_theft", "cyber_fraud", "theft"]},
    "Satellite": {"intensity": "high", "categories": ["cyber_fraud", "chain_snatching", "vehicle_theft"]},
    "Vastrapur": {"intensity": "high", "categories": ["cyber_fraud", "chain_snatching", "theft"]},
    "Bodakdev": {"intensity": "high", "categories": ["cyber_fraud", "burglary", "vehicle_theft"]},
    "Thaltej": {"intensity": "high", "categories": ["cyber_fraud", "vehicle_theft", "burglary"]},
    "Bopal": {"intensity": "medium", "categories": ["cyber_fraud", "vehicle_theft", "burglary"]},
    "SG Highway": {"intensity": "high", "categories": ["cyber_fraud", "vehicle_theft", "theft"]},
    "Gota": {"intensity": "medium", "categories": ["vehicle_theft", "burglary", "cyber_fraud"]},
    "Ghatlodia": {"intensity": "high", "categories": ["chain_snatching", "vehicle_theft", "theft"]},
    "Memnagar": {"intensity": "medium", "categories": ["chain_snatching", "theft", "cyber_fraud"]},
    "Ranip": {"intensity": "medium", "categories": ["vehicle_theft", "theft", "assault"]},

    # North / north-west (growth belts -> vehicle theft, burglary)
    "Chandkheda": {"intensity": "high", "categories": ["vehicle_theft", "burglary", "theft"]},
    "Sabarmati": {"intensity": "medium", "categories": ["theft", "vehicle_theft", "assault"]},

    # Central-east / old city (mixed; markets, transit -> theft, assault)
    "Shahibaug": {"intensity": "medium", "categories": ["theft", "cyber_fraud", "assault"]},
    "Asarwa": {"intensity": "high", "categories": ["assault", "theft", "body_offences"]},
    "Jamalpur": {"intensity": "high", "categories": ["theft", "assault", "chain_snatching"]},

    # Eastern industrial / working-class belt (Zone 5/6 -> violent / body offences)
    "Bapunagar": {"intensity": "high", "categories": ["assault", "body_offences", "theft"]},
    "Naroda": {"intensity": "high", "categories": ["assault", "vehicle_theft", "body_offences", "cyber_fraud"]},
    "Nikol": {"intensity": "high", "categories": ["vehicle_theft", "theft", "assault"]},
    "Odhav": {"intensity": "high", "categories": ["assault", "body_offences", "vehicle_theft"]},
    "Gomtipur": {"intensity": "high", "categories": ["murder", "assault", "body_offences"]},
    "Vatva": {"intensity": "high", "categories": ["assault", "body_offences", "narcotics", "theft"]},

    # South / south-east (mixed residential-industrial)
    "Maninagar": {"intensity": "high", "categories": ["chain_snatching", "theft", "vehicle_theft"]},
    "Kankaria": {"intensity": "medium", "categories": ["theft", "chain_snatching", "assault"]},
    "Isanpur": {"intensity": "medium", "categories": ["vehicle_theft", "theft", "assault"]},
    "Behrampura": {"intensity": "high", "categories": ["theft", "assault", "body_offences"]},
}

# --- generic public-reported seed incidents ----------------------------------
# Descriptions are intentionally generic (no real individuals, indicative amounts).

SEED_INCIDENTS = [
    {
        "title": "Digital-arrest cyber-fraud ring busted",
        "description": "A gang posing as law-enforcement officials over video calls extorted a large sum from a resident before arrests were made.",
        "category": "cyber_fraud",
        "area": "Satellite",
        "severity": "high",
        "year": 2024,
    },
    {
        "title": "Overseas-linked loan-scam call-centre raided",
        "description": "An illegal call-centre abetting overseas fraudsters with fake loan and credit offers was raided and shut down.",
        "category": "cyber_fraud",
        "area": "Bodakdev",
        "severity": "high",
        "year": 2024,
    },
    {
        "title": "Chain-snatching gang traced across west Ahmedabad",
        "description": "Two suspects were linked to a series of gold-chain snatchings targeting lone pedestrians during evening hours.",
        "category": "chain_snatching",
        "area": "Navrangpura",
        "severity": "medium",
        "year": 2024,
    },
    {
        "title": "Evening chain-snatching spree on lone pedestrians",
        "description": "Multiple snatching incidents were reported between 8 and 10 pm before the pattern was traced to a single gang.",
        "category": "chain_snatching",
        "area": "Ellisbridge",
        "severity": "medium",
        "year": 2024,
    },
    {
        "title": "Two-wheeler theft cluster flagged on weeknights",
        "description": "Predictive-policing alerts highlighted a recurring pattern of late-night two-wheeler thefts in the area.",
        "category": "vehicle_theft",
        "area": "Chandkheda",
        "severity": "medium",
        "year": 2024,
    },
    {
        "title": "Two-wheeler theft alert raised by predictive policing",
        "description": "Police teams were directed to increase night patrols after an AI model flagged the locality as a vehicle-theft hotspot.",
        "category": "vehicle_theft",
        "area": "Maninagar",
        "severity": "medium",
        "year": 2024,
    },
    {
        "title": "ATM card-swap fraud against a senior citizen",
        "description": "A victim was tricked into handing over a debit card and PIN, with funds withdrawn over several days.",
        "category": "cyber_fraud",
        "area": "Maninagar",
        "severity": "medium",
        "year": 2024,
    },
    {
        "title": "Burglary targeting an elderly resident's home",
        "description": "An unoccupied home of a senior citizen was broken into and valuables were stolen.",
        "category": "burglary",
        "area": "Paldi",
        "severity": "medium",
        "year": 2023,
    },
    {
        "title": "Night-time house break-in in a residential society",
        "description": "Intruders entered a locked flat overnight and made off with cash and jewellery.",
        "category": "burglary",
        "area": "Thaltej",
        "severity": "medium",
        "year": 2024,
    },
    {
        "title": "Illegal liquor-manufacturing unit busted",
        "description": "Police raided a clandestine unit and seized raw material in a prohibition-enforcement drive.",
        "category": "prohibition",
        "area": "Vatva",
        "severity": "medium",
        "year": 2024,
    },
    {
        "title": "Narcotics consignment seized in enforcement drive",
        "description": "A significant quantity of narcotics was intercepted as part of an ongoing anti-drug operation.",
        "category": "narcotics",
        "area": "Odhav",
        "severity": "high",
        "year": 2024,
    },
    {
        "title": "Violent brawl in eastern industrial belt",
        "description": "A dispute escalated into a violent altercation requiring police intervention in a working-class neighbourhood.",
        "category": "assault",
        "area": "Bapunagar",
        "severity": "high",
        "year": 2023,
    },
    {
        "title": "Violent altercation reported in dense locality",
        "description": "A clash between groups led to injuries and multiple detentions in a historically tense area.",
        "category": "assault",
        "area": "Gomtipur",
        "severity": "high",
        "year": 2023,
    },
    {
        "title": "Pickpocketing and theft surge at lakefront crowds",
        "description": "Heavy footfall at the lakefront drew a spike in petty theft and pickpocketing complaints.",
        "category": "theft",
        "area": "Kankaria",
        "severity": "low",
        "year": 2024,
    },
    {
        "title": "Market-area snatching during festival rush",
        "description": "Crowded festival shopping created conditions for snatching and theft in the old-city market.",
        "category": "theft",
        "area": "Jamalpur",
        "severity": "medium",
        "year": 2024,
    },
    {
        "title": "Fake investment-app scam defrauds residents",
        "description": "Residents were lured by a fraudulent investment application promising high returns before funds disappeared.",
        "category": "cyber_fraud",
        "area": "SG Highway",
        "severity": "high",
        "year": 2024,
    },
    {
        "title": "Parked-vehicle theft reported near commercial hub",
        "description": "Several parked two-wheelers went missing from a busy commercial stretch over a short period.",
        "category": "vehicle_theft",
        "area": "Ghatlodia",
        "severity": "medium",
        "year": 2024,
    },
    {
        "title": "Loan-app extortion network exposed",
        "description": "A network using harassment tactics to extort borrowers via fake loan apps was uncovered.",
        "category": "cyber_fraud",
        "area": "Vastrapur",
        "severity": "high",
        "year": 2024,
    },
    {
        "title": "Monsoon waterlogging stranded residents",
        "description": "Heavy rainfall overwhelmed local drainage, leaving low-lying lanes and societies waterlogged for days.",
        "category": "disaster_flood",
        "area": "Bopal",
        "severity": "high",
        "year": 2024,
    },
    {
        "title": "Riverfront low-zone flooding after dam release",
        "description": "Water released upstream raised river levels and submerged low-lying riverfront zones, prompting evacuations.",
        "category": "disaster_flood",
        "area": "Vasna",
        "severity": "high",
        "year": 2017,
    },
]

# --- flood / disaster-prone areas --------------------------------------------
# Source-named: Bopal (Ghuma-Bopal), Sabarmati riverfront / Vasna Barrage zone.
# Remaining entries are low-lying / old-city inferences for demo use.

FLOOD_PRONE_AREAS = [
    "Bopal",
    "Vasna",
    "Behrampura",
    "Jamalpur",
    "Sabarmati",
    "Paldi",
    "Vatva",
    "Isanpur",
    "Maninagar",
    "Naroda",
    "Odhav",
    "Ranip",
    "Chandkheda",
]


__all__ = [
    "AREA_CRIME_PROFILE",
    "SEED_INCIDENTS",
    "FLOOD_PRONE_AREAS",
    "INTENSITY_LEVELS",
    "CRIME_CATEGORIES",
]
