"""Realistic synthetic incident generator — the data foundation for accuracy
metrics, heatmaps, trend detection and backtesting.

This is the *volume* layer that sits underneath the ~20 named, public-sourced
``SEED_INCIDENTS`` (which stay untouched as a small labeled overlay). It emits
~1500-3000 complaints spread over a rolling 180-day window ending now, written
through the EXACT same ``complaints`` columns/path the demo seed uses
(see ``seed._seed_incidents``) so the City Map and analytics read it natively.

IMPORTANT (demo disclaimer):
    Every row produced here is FULLY SYNTHETIC and DETERMINISTIC (fixed random
    seed). It is generated from the editorial, demo-only ``AREA_CRIME_PROFILE``
    intensities and category weights — NOT from any real incident record. No
    real individuals are named. Do not use for operational, legal, or
    real-estate decisions. See docs/AHMEDABAD_CRIME_DATA.md for methodology.

How the realism is built up
---------------------------
* Per-area daily volume scales with AREA_CRIME_PROFILE intensity
  (low/medium/high -> base daily rate).
* Category is sampled from that area's listed categories (front-weighted so the
  area's dominant crime type leads).
* Severity is weighted per category (e.g. murder/assault skew high, theft low).
* Timestamps follow category-specific hour-of-day curves (snatching/theft peak
  in the evening, burglary pre-dawn, cyber-fraud office hours, vehicle theft
  late night) plus a weekend uplift for assault/theft/snatching.

Spatial concentration (the *law of crime concentration*):
    Per-area mean daily volume is set directly from ``AREA_BASE_RATE`` — a
    deliberately steep skew (a handful of genuinely hot areas, ~8 medium, the
    majority low / very-low) rather than three flat buckets. This concentrates
    the heatmap and lifts the oracle PAI ceiling so a good predictor can visibly
    outperform a blind, spread-evenly baseline.

Slow temporal drift (what lets a recency-weighted model HONESTLY beat all-time
frequency and the static prior):
    -- see DRIFT_PATTERNS below for the authoritative, code-driven definition --
    A few areas ramp their intensity slowly across the 180-day window (a low
    area heating to high over months — new-market / gentrification dynamics; a
    formerly-hot area cooling after a sustained crackdown). Because the recent
    distribution then differs from the all-time distribution, recency-weighting
    wins where naive frequency cannot. Crucially, a couple of drift areas end the
    window ranked very differently from their *static* AREA_CRIME_PROFILE label,
    so the model also beats the label-only prior.

Planted, time-boxed surge patterns (so trend/backtest code has sharp signal):
    -- see PLANTED_SURGES below for the authoritative, code-driven definition --
    1. Chain-snatching SPREE in **Maninagar**, roughly **weeks 8-10** of the
       180-day window (~days 56-70 from the window start). ~3x baseline
       chain-snatching volume in that area for that span.
    2. Cyber-fraud RAMP in **SG Highway / Satellite** over the **final 4 weeks**
       of the window (last ~28 days), climbing from baseline to ~2.5-3x.
These are documented again, machine-readable, in ``PLANTED_SURGES``.

Cyber enrichment (per-row, for the Cyber Fraud map layer):
    Every generated ``cyber_fraud`` row also gets a structured NCRP/1930 tag —
    ``cyber_category`` (weighted: UPI/OTP most common, investment scams rarer but
    high-value), a plausible ``fraud_channel``, and an ``amount_lost`` drawn from
    a per-category lognormal (₹ medians calibrated to the published 1930 mix).
    All from the same private RNG, so the stream stays byte-for-byte reproducible.

Gating (in ``maybe_seed_synthetic``):
    Runs only when the complaints table has < ~100 rows OR the env flag
    ``VISIONSCAN_SEED_SYNTHETIC=true`` forces it. A marker row in
    ``app_settings`` (key ``synthetic_seed_done``) plus the row-count check make
    it safe to call on every startup without ever duplicating.
"""
from __future__ import annotations

import logging
import math
import os
import random
from datetime import datetime, timedelta

from ..constants.ahmedabad import AREAS, area_centroid
from ..constants.cyber import CYBER_CATEGORIES, FRAUD_CHANNELS
from ..database import get_conn
from .seed_ahmedabad import AREA_CRIME_PROFILE

log = logging.getLogger("visionscan.platform.seed_synthetic")

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

# Fixed seed => byte-for-byte reproducible heatmaps/metrics across runs.
RANDOM_SEED = 20240601
# Rolling window the synthetic stream covers (days, ending "now").
WINDOW_DAYS = 180
# Marker key in app_settings so we never double-seed on restart.
MARKER_KEY = "synthetic_seed_done"
# Below this many complaints we treat the DB as "empty enough" to auto-seed.
AUTO_SEED_BELOW = 100

# Fallback mean complaints/day per intensity bucket. Only used when an area is
# missing from AREA_BASE_RATE below (it never is, but the lookup stays safe).
BASE_DAILY_RATE = {"low": 0.14, "medium": 0.40, "high": 0.85}

# --- Spatial concentration (law of crime concentration) ---------------------
# Per-area mean complaints/day across ALL of that area's categories. This is the
# steep, deliberately skewed distribution that drives both the heatmap density
# and the predictive oracle ceiling: a small set of genuinely hot areas, a
# medium tier, and a long low/very-low tail. Summed over 30 areas * 180 days
# (with the +rare-cluster sampler and surges) this lands the synthetic stream in
# the ~1500-3000 target band. Values are editorial demo intensities, NOT real
# per-neighbourhood rates (see the module disclaimer).
#
# A few of these areas are STARTING points — DRIFT_PATTERNS (below) ramps them
# up or down over the window, so an area's effective rate on any given day is
# AREA_BASE_RATE[area] * drift_multiplier(area, day).
AREA_BASE_RATE = {
    # -- genuinely hot (eastern industrial belt + the SG-Highway transit spine) --
    "Vatva": 1.15,
    "Naroda": 1.08,
    "Gomtipur": 0.98,
    "Bapunagar": 1.02,
    "Maninagar": 0.94,
    "SG Highway": 0.86,
    # -- medium tier --
    "Odhav": 0.34,
    "Nikol": 0.26,
    "Asarwa": 0.38,
    "Jamalpur": 0.24,
    "Behrampura": 0.22,
    "Ghatlodia": 0.20,
    "Satellite": 0.26,
    "Vastrapur": 0.18,
    # -- low / very-low residential tail --
    "Navrangpura": 0.09,
    "Chandkheda": 0.10,
    "Ellisbridge": 0.05,
    "Paldi": 0.04,
    "Vasna": 0.04,
    "Vejalpur": 0.04,
    "Bodakdev": 0.04,
    "Thaltej": 0.04,
    "Bopal": 0.07,
    "Gota": 0.07,
    "Memnagar": 0.05,
    "Ranip": 0.04,
    "Sabarmati": 0.04,
    "Shahibaug": 0.05,
    "Kankaria": 0.06,
    "Isanpur": 0.05,
}

# Severity weights per category (low | medium | high | critical). Sampled with
# random.choices; absolute magnitudes don't matter, only the ratios.
SEVERITY_WEIGHTS = {
    "cyber_fraud":     {"low": 1, "medium": 5, "high": 3, "critical": 1},
    "vehicle_theft":   {"low": 3, "medium": 5, "high": 1, "critical": 0},
    "chain_snatching": {"low": 1, "medium": 5, "high": 3, "critical": 0},
    "burglary":        {"low": 2, "medium": 5, "high": 2, "critical": 0},
    "theft":           {"low": 5, "medium": 4, "high": 1, "critical": 0},
    "assault":         {"low": 1, "medium": 4, "high": 4, "critical": 1},
    "body_offences":   {"low": 0, "medium": 3, "high": 4, "critical": 2},
    "murder":          {"low": 0, "medium": 0, "high": 2, "critical": 5},
    "narcotics":       {"low": 1, "medium": 4, "high": 3, "critical": 0},
    "prohibition":     {"low": 3, "medium": 4, "high": 1, "critical": 0},
    "disaster_flood":  {"low": 1, "medium": 3, "high": 4, "critical": 1},
}
_DEFAULT_SEVERITY = {"low": 2, "medium": 4, "high": 2, "critical": 0}

# Relative hour-of-day weight (0..23) per category. Values are unnormalised; the
# sampler treats them as weights. Curves encode the spec:
#   chain_snatching / theft  -> evening peak 19:00-23:00
#   burglary                 -> pre-dawn 01:00-05:00
#   cyber_fraud              -> office hours 10:00-18:00
#   vehicle_theft            -> late night 22:00-03:00
#   assault                  -> evening/night
def _curve(peaks: dict[int, float], base: float = 0.2) -> list[float]:
    return [peaks.get(h, base) for h in range(24)]


HOUR_CURVES = {
    "chain_snatching": _curve({
        18: 1.5, 19: 3.0, 20: 4.0, 21: 4.0, 22: 3.0, 23: 1.5, 17: 0.8,
    }),
    "theft": _curve({
        11: 0.8, 12: 1.0, 17: 1.2, 18: 1.6, 19: 2.4, 20: 3.0, 21: 2.8,
        22: 2.0, 23: 1.0,
    }, 0.5),
    "burglary": _curve({
        0: 1.5, 1: 3.0, 2: 4.0, 3: 4.0, 4: 3.0, 5: 1.5, 23: 0.8,
    }, 0.1),
    "cyber_fraud": _curve({
        10: 2.5, 11: 3.5, 12: 3.5, 13: 2.5, 14: 3.0, 15: 3.5, 16: 3.5,
        17: 3.0, 18: 2.0, 9: 1.2,
    }, 0.2),
    "vehicle_theft": _curve({
        22: 3.0, 23: 4.0, 0: 4.0, 1: 3.5, 2: 3.0, 3: 2.0, 21: 1.5,
    }, 0.2),
    "assault": _curve({
        18: 1.5, 19: 2.5, 20: 3.0, 21: 3.5, 22: 3.5, 23: 3.0, 0: 2.0,
        1: 1.2,
    }, 0.3),
    "body_offences": _curve({
        19: 2.0, 20: 2.5, 21: 3.0, 22: 3.0, 23: 2.5, 0: 2.0, 1: 1.5,
    }, 0.4),
    "murder": _curve({
        20: 2.0, 21: 2.5, 22: 2.5, 23: 2.0, 0: 1.8, 1: 1.5, 2: 1.2,
    }, 0.5),
    "narcotics": _curve({
        20: 1.8, 21: 2.2, 22: 2.5, 23: 2.5, 0: 2.0, 1: 1.5, 2: 1.2,
    }, 0.5),
    "prohibition": _curve({
        20: 1.8, 21: 2.2, 22: 2.5, 23: 2.5, 0: 2.0, 1: 1.5,
    }, 0.5),
    "disaster_flood": _curve({}, 1.0),  # ~uniform across the day
}
_DEFAULT_HOURS = _curve({}, 1.0)

# Categories that get a weekend (Sat/Sun) volume uplift.
_WEEKEND_UPLIFT = {"assault": 1.6, "theft": 1.4, "chain_snatching": 1.5,
                   "body_offences": 1.4, "murder": 1.3}

# Generic, no-PII complaint phrasing per category (a title/description pool the
# sampler draws from so the synthetic rows read like real filings).
_PHRASES = {
    "cyber_fraud": (
        "Online fraud reported",
        "Resident reports money lost to an online scam call / fake offer.",
    ),
    "vehicle_theft": (
        "Two-wheeler / vehicle theft reported",
        "A parked vehicle was reported stolen from the locality.",
    ),
    "chain_snatching": (
        "Chain-snatching reported",
        "A pedestrian reports a gold chain snatched by a passing motorcyclist.",
    ),
    "burglary": (
        "House break-in reported",
        "An entry into a locked premises with valuables reported missing.",
    ),
    "theft": (
        "Theft reported",
        "Petty theft / pickpocketing reported in a public area.",
    ),
    "assault": (
        "Assault reported",
        "A physical altercation requiring police intervention was reported.",
    ),
    "body_offences": (
        "Body-offence complaint reported",
        "A complaint involving injury / bodily harm was registered.",
    ),
    "murder": (
        "Serious violent crime reported",
        "A serious violent offence was reported and is under investigation.",
    ),
    "narcotics": (
        "Narcotics-related complaint reported",
        "Suspected narcotics activity was reported in the locality.",
    ),
    "prohibition": (
        "Prohibition-offence complaint reported",
        "Suspected illegal-liquor activity was reported for enforcement.",
    ),
    "disaster_flood": (
        "Waterlogging / flooding reported",
        "Heavy-rain waterlogging affecting the locality was reported.",
    ),
}
_DEFAULT_PHRASE = ("Incident reported", "An incident was reported in the locality.")

# Statuses the synthetic rows take. ALL of these are counted by the analytics
# /map query (which filters only on a non-empty area, never on status) and by
# the analytics /summary KPIs. We deliberately avoid 'converted' so the small
# labeled SEED_INCIDENTS overlay stays the distinguishable "cases" layer.
_STATUS_WEIGHTS = {"submitted": 4, "under_review": 4, "assigned": 2}

# Lat/lng jitter around an area centroid (degrees) — ~±0.9km, keeps the dot
# inside the locality while spreading the heatmap.
_JITTER_DEG = 0.008

# ---------------------------------------------------------------------------
# Cyber-fraud enrichment (per-row NCRP/1930 structured tags).
# Keys here are validated against constants/cyber.CYBER_CATEGORIES at import.
# ---------------------------------------------------------------------------
# How often each cyber_category appears among generated cyber_fraud rows. UPI/OTP
# fraud dominates the real 1930 mix; investment scams are rarer but high-value.
_CYBER_CATEGORY_WEIGHTS = {
    "upi_otp_fraud": 32,
    "phishing_smishing": 13,
    "fake_shopping": 11,
    "job_task_fraud": 9,
    "loan_app_extortion": 8,
    "digital_arrest_scam": 8,
    "investment_trading_scam": 8,
    "sextortion": 4,
    "identity_theft": 4,
    "social_media_impersonation": 3,
}

# Plausible fraud-channel mix per cyber_category (weights, sampled per row). Every
# value is a member of constants/cyber.FRAUD_CHANNELS.
_CYBER_CHANNEL_WEIGHTS = {
    "upi_otp_fraud":              {"UPI": 6, "phone_call": 3, "SMS": 2},
    "phishing_smishing":         {"SMS": 4, "WhatsApp": 3, "website": 2, "card": 1},
    "fake_shopping":             {"website": 5, "social_media": 3, "UPI": 2},
    "job_task_fraud":            {"WhatsApp": 4, "fake_app": 3, "UPI": 2},
    "loan_app_extortion":        {"fake_app": 5, "phone_call": 3, "WhatsApp": 2},
    "digital_arrest_scam":       {"phone_call": 5, "WhatsApp": 3, "UPI": 1},
    "investment_trading_scam":   {"fake_app": 4, "WhatsApp": 3, "website": 2, "UPI": 1},
    "sextortion":                {"WhatsApp": 4, "social_media": 3, "phone_call": 1},
    "identity_theft":            {"website": 3, "card": 2, "SMS": 1},
    "social_media_impersonation":{"social_media": 6, "WhatsApp": 2},
}

# Lognormal ₹-loss parameters per cyber_category as (median_rupees, sigma). The
# draw is median * exp(sigma * gauss); median is the geometric centre and sigma
# the spread. Calibrated so UPI/OTP medians ~₹25k, investment scams ~₹4L with a
# fat tail to tens of lakhs, etc. (see SPEC). A small share of rows carry no loss.
_CYBER_AMOUNT_PARAMS = {
    "upi_otp_fraud":             (25_000, 0.9),
    "phishing_smishing":         (18_000, 0.95),
    "fake_shopping":             (6_000, 0.85),
    "job_task_fraud":            (60_000, 1.0),
    "loan_app_extortion":        (35_000, 0.9),
    "digital_arrest_scam":       (220_000, 1.0),
    "investment_trading_scam":   (500_000, 1.05),
    "sextortion":                (15_000, 0.95),
    "identity_theft":            (40_000, 1.0),
    "social_media_impersonation":(12_000, 0.9),
}
# Fraction of cyber rows with NO money loss (harassment / attempted-only).
_CYBER_NO_LOSS_PROB = 0.12

# ---------------------------------------------------------------------------
# Planted surges (machine-readable mirror of the module docstring).
# Weeks are 1-indexed from the START of the WINDOW_DAYS window. A surge entry
# multiplies the daily rate for (area, category) inside [day_start, day_end].
# ---------------------------------------------------------------------------
PLANTED_SURGES = [
    {
        "name": "Maninagar chain-snatching spree (weeks 8-10)",
        "areas": ["Maninagar"],
        "category": "chain_snatching",
        "day_start": 7 * 8 - 1,   # start of week 8  -> day 55
        "day_end": 7 * 10,        # end of week 10   -> day 70
        "multiplier": 3.0,
    },
    {
        "name": "SG Highway / Satellite cyber-fraud ramp (final 4 weeks)",
        "areas": ["SG Highway", "Satellite"],
        "category": "cyber_fraud",
        "day_start": WINDOW_DAYS - 28,  # last 28 days
        "day_end": WINDOW_DAYS,
        "multiplier_start": 1.0,        # ramps linearly from baseline ...
        "multiplier_end": 3.0,          # ... up to ~3x at the window end
    },
]


# ---------------------------------------------------------------------------
# Slow temporal drift (machine-readable, mirrors the module docstring).
#
# Each pattern multiplies an ENTIRE area's daily rate (all categories) by a slow
# ramp between ``mult_start`` and ``mult_end`` across [day_start, day_end], held
# flat at the endpoints outside that span. Two shapes:
#   "linear"  — constant-slope ramp (steady gentrification / steady decline)
#   "sigmoid" — slow-then-fast-then-slow S-curve (a tipping-point change)
#
# This is the signal that makes RECENCY-WEIGHTING honestly beat all-time
# frequency: the recent month's spatial distribution genuinely differs from the
# 180-day average. Two of these areas (Bopal heating, Gomtipur cooling) also end
# the window ranked very differently from their STATIC AREA_CRIME_PROFILE label,
# so the model beats the label-only prior too — not just the frequency baseline.
# ---------------------------------------------------------------------------
DRIFT_PATTERNS = [
    {
        # Heats from a quiet residential rate into the TOP tier by the window's
        # end. Because its all-time count stays low (it was quiet for months),
        # the naive frequency baseline keeps under-ranking it while the
        # recency-weighted model promotes it — the cleanest "recency wins" case.
        "name": "Bopal new-market boom (very-low -> hottest over ~5 months)",
        "area": "Bopal",
        "shape": "sigmoid",
        "day_start": 25,
        "day_end": 165,
        "mult_start": 1.0,
        "mult_end": 15.0,  # 0.07/day base -> ~1.05/day recently (top-tier)
    },
    {
        # Second heater crossing low -> hot in the back half of the window.
        "name": "Gota growth-belt heating (low -> hot over ~4 months)",
        "area": "Gota",
        "shape": "sigmoid",
        "day_start": 50,
        "day_end": 168,
        "mult_start": 1.0,
        "mult_end": 11.0,  # 0.07/day base -> ~0.77/day recently
    },
    {
        # A formerly-hot area cooled hard after a sustained crackdown. Its big
        # early count keeps the all-time frequency baseline ranking it high, but
        # recent activity is minimal — the model correctly de-ranks it. Cools
        # early (by ~day 150) so the back-half folds see it quiet while its
        # all-time tally stays large.
        "name": "Gomtipur post-crackdown collapse (hottest -> quiet)",
        "area": "Gomtipur",
        "shape": "sigmoid",
        "day_start": 25,
        "day_end": 150,
        "mult_start": 1.0,
        "mult_end": 0.12,  # 0.98/day base -> ~0.12/day recently
    },
    {
        # A medium area cooling to low over the back half of the window.
        "name": "Asarwa enforcement cooling (medium -> low over ~4 months)",
        "area": "Asarwa",
        "shape": "linear",
        "day_start": 40,
        "day_end": 160,
        "mult_start": 1.0,
        "mult_end": 0.30,  # 0.38/day base -> ~0.11/day recently
    },
]


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def _category_weights(categories: list[str]) -> list[float]:
    """Front-weight an area's category list so its dominant crime leads."""
    n = len(categories)
    # e.g. 3 cats -> [3,2,1]; mild decay keeps the tail present.
    return [float(n - i) for i in range(n)]


def _surge_multiplier(area: str, category: str, day: int) -> float:
    """Combined multiplier from any planted surge active for (area, category, day)."""
    mult = 1.0
    for s in PLANTED_SURGES:
        if category != s["category"] or area not in s["areas"]:
            continue
        if not (s["day_start"] <= day < s["day_end"]):
            continue
        if "multiplier" in s:
            mult *= s["multiplier"]
        else:  # linear ramp
            span = max(1, s["day_end"] - s["day_start"])
            frac = (day - s["day_start"]) / span
            mult *= s["multiplier_start"] + frac * (
                s["multiplier_end"] - s["multiplier_start"])
    return mult


def _drift_multiplier(area: str, day: int) -> float:
    """Slow whole-area intensity drift for ``day`` (0..WINDOW_DAYS-1).

    Applies to EVERY category in the area (unlike a planted surge, which targets
    one category). Held flat at ``mult_start`` before ``day_start`` and at
    ``mult_end`` after ``day_end``; ramps in between by the pattern's shape.
    """
    mult = 1.0
    for d in DRIFT_PATTERNS:
        if area != d["area"]:
            continue
        d0, d1 = d["day_start"], d["day_end"]
        m0, m1 = d["mult_start"], d["mult_end"]
        if day <= d0:
            frac = 0.0
        elif day >= d1:
            frac = 1.0
        else:
            frac = (day - d0) / max(1, d1 - d0)
            if d.get("shape") == "sigmoid":
                # Logistic S-curve centred on the span midpoint; k controls
                # steepness. Rescaled to hit 0 at frac=0 and 1 at frac=1 so the
                # endpoints meet mult_start/mult_end exactly.
                k = 9.0
                s = lambda x: 1.0 / (1.0 + math.exp(-k * (x - 0.5)))
                lo, hi = s(0.0), s(1.0)
                frac = (s(frac) - lo) / (hi - lo)
        mult *= m0 + frac * (m1 - m0)
    return mult


def generate_incidents(rng: random.Random,
                       window_start: datetime) -> list[dict]:
    """Build the deterministic synthetic incident list (no DB I/O).

    Returns a list of dicts with the exact fields the complaints INSERT needs:
    title, description, category, location, area, lat, lng, severity, status,
    created_at (ISO string).
    """
    rows: list[dict] = []
    # Iterate areas in a fixed order for determinism.
    for area in AREAS:
        profile = AREA_CRIME_PROFILE.get(area)
        if not profile:
            continue
        intensity = profile.get("intensity", "medium")
        categories = profile.get("categories") or []
        if not categories:
            continue
        # Per-area absolute daily rate (steep spatial skew) with a safe fallback
        # to the intensity bucket if an area is ever missing from the map.
        base_rate = AREA_BASE_RATE.get(
            area, BASE_DAILY_RATE.get(intensity, BASE_DAILY_RATE["medium"]))
        cat_weights = _category_weights(categories)
        cat_weight_sum = sum(cat_weights)
        centroid = area_centroid(area)

        for day in range(WINDOW_DAYS):
            date = window_start + timedelta(days=day)
            is_weekend = date.weekday() >= 5  # 5=Sat, 6=Sun
            drift = _drift_multiplier(area, day)

            # Sample the day's count from a Poisson-ish process: one draw per
            # category lets a surge lift just that category.
            for cat, cw in zip(categories, cat_weights):
                # Per-category share of the area's base rate.
                share = cw / cat_weight_sum
                rate = base_rate * share * drift
                rate *= _surge_multiplier(area, cat, day)
                if is_weekend:
                    rate *= _WEEKEND_UPLIFT.get(cat, 1.0)
                # Expected count for this (area, cat, day). Use a small-count
                # sampler: floor + Bernoulli on the fractional part, then a rare
                # extra to give occasional clusters.
                count = int(rate)
                if rng.random() < (rate - count):
                    count += 1
                if count and rng.random() < 0.08:
                    count += 1
                for _ in range(count):
                    hour = _sample_hour(rng, cat)
                    minute = rng.randint(0, 59)
                    second = rng.randint(0, 59)
                    ts = date.replace(hour=hour, minute=minute, second=second)
                    severity = _sample_severity(rng, cat)
                    status = rng.choices(
                        list(_STATUS_WEIGHTS), weights=list(_STATUS_WEIGHTS.values())
                    )[0]
                    lat = lng = None
                    if centroid:
                        lat = round(centroid[0] + rng.uniform(-_JITTER_DEG, _JITTER_DEG), 6)
                        lng = round(centroid[1] + rng.uniform(-_JITTER_DEG, _JITTER_DEG), 6)
                    title, desc = _PHRASES.get(cat, _DEFAULT_PHRASE)
                    # Structured NCRP/1930 enrichment for cyber-fraud rows only;
                    # all other categories leave these columns NULL.
                    cyber_category = fraud_channel = amount_lost = None
                    if cat == "cyber_fraud":
                        cyber_category, fraud_channel, amount_lost = \
                            _sample_cyber(rng)
                    rows.append({
                        "title": title,
                        "description": desc,
                        "category": cat,
                        "location": f"{area}, Ahmedabad",
                        "area": area,
                        "lat": lat,
                        "lng": lng,
                        "severity": severity,
                        "status": status,
                        "created_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
                        "cyber_category": cyber_category,
                        "fraud_channel": fraud_channel,
                        "amount_lost": amount_lost,
                        # hours_since_incident stays NULL for synthetic rows — it
                        # is a live golden-hour intake signal, not a history field.
                        "hours_since_incident": None,
                    })
    return rows


def _sample_hour(rng: random.Random, category: str) -> int:
    weights = HOUR_CURVES.get(category, _DEFAULT_HOURS)
    return rng.choices(range(24), weights=weights)[0]


def _sample_severity(rng: random.Random, category: str) -> str:
    w = SEVERITY_WEIGHTS.get(category, _DEFAULT_SEVERITY)
    levels = list(w)
    return rng.choices(levels, weights=[w[l] for l in levels])[0]


def _sample_cyber(rng: random.Random) -> tuple[str, str, float | None]:
    """Draw a structured NCRP/1930 cyber tag for one cyber_fraud row.

    Returns ``(cyber_category, fraud_channel, amount_lost)`` where amount_lost is
    a per-category lognormal ₹ value (rounded to ₹100) or ``None`` for the small
    share of harassment / attempted-only rows. Uses ONLY the passed-in private
    RNG so the whole stream stays deterministic.
    """
    cats = list(_CYBER_CATEGORY_WEIGHTS)
    cyber_category = rng.choices(
        cats, weights=[_CYBER_CATEGORY_WEIGHTS[c] for c in cats])[0]

    ch_w = _CYBER_CHANNEL_WEIGHTS.get(cyber_category) or {"UPI": 1}
    channels = list(ch_w)
    fraud_channel = rng.choices(
        channels, weights=[ch_w[c] for c in channels])[0]

    amount_lost: float | None = None
    if rng.random() >= _CYBER_NO_LOSS_PROB:
        median, sigma = _CYBER_AMOUNT_PARAMS.get(cyber_category, (20_000, 1.0))
        amt = median * math.exp(sigma * rng.gauss(0.0, 1.0))
        # Clamp to a sane floor and round to the nearest ₹100 so the figures read
        # like real reported losses.
        amount_lost = float(round(max(amt, 500.0) / 100.0) * 100)
    return cyber_category, fraud_channel, amount_lost


# ---------------------------------------------------------------------------
# DB entry points
# ---------------------------------------------------------------------------

def _resolve_citizen_id(conn) -> int | None:
    """Find a citizen user to own the synthetic complaints (FK is NOT NULL).
    Prefer the demo citizen; fall back to any user so seeding still works."""
    row = conn.execute(
        "SELECT id FROM users WHERE role = 'citizen' ORDER BY id LIMIT 1"
    ).fetchone()
    if row:
        return row["id"]
    row = conn.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
    return row["id"] if row else None


def _already_seeded(conn) -> bool:
    row = conn.execute(
        "SELECT value FROM app_settings WHERE key = ?", (MARKER_KEY,)
    ).fetchone()
    return bool(row and str(row["value"]) == "1")


def seed_synthetic(force: bool = False) -> int:
    """Insert the deterministic synthetic complaint stream. Idempotent: a marker
    row in app_settings prevents a second run unless ``force`` is set (which also
    skips the marker check, e.g. when seeding a fresh temp DB in a test).

    Returns the number of rows inserted (0 if skipped)."""
    rng = random.Random(RANDOM_SEED)
    # Anchor the window to midnight today so timestamps are stable within a day.
    now = datetime.now().replace(microsecond=0)
    window_start = (now - timedelta(days=WINDOW_DAYS)).replace(
        hour=0, minute=0, second=0)

    with get_conn() as conn:
        if not force and _already_seeded(conn):
            return 0
        citizen_id = _resolve_citizen_id(conn)
        if not citizen_id:
            log.warning("synthetic seed skipped: no user to own complaints")
            return 0
        rows = generate_incidents(rng, window_start)
        conn.executemany(
            "INSERT INTO complaints (citizen_id, title, description, category, "
            "location, area, lat, lng, severity, status, created_at, "
            "cyber_category, fraud_channel, amount_lost, hours_since_incident) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (citizen_id, r["title"], r["description"], r["category"],
                 r["location"], r["area"], r["lat"], r["lng"], r["severity"],
                 r["status"], r["created_at"], r["cyber_category"],
                 r["fraud_channel"], r["amount_lost"], r["hours_since_incident"])
                for r in rows
            ],
        )
        conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, '1')",
            (MARKER_KEY,),
        )
    log.info("Seeded %d synthetic complaints over a %d-day window", len(rows),
             WINDOW_DAYS)
    return len(rows)


def maybe_seed_synthetic() -> int:
    """Gating wrapper called from the demo seed flow. Runs the synthetic seed
    only when the complaints table is near-empty (< ~100 rows) OR the env flag
    VISIONSCAN_SEED_SYNTHETIC forces it. Fully fail-soft — never blocks startup.

    Returns the number of rows inserted (0 if skipped)."""
    forced = os.getenv("VISIONSCAN_SEED_SYNTHETIC", "").strip().lower() in (
        "1", "true", "yes", "on")
    try:
        with get_conn() as conn:
            if _already_seeded(conn) and not forced:
                return 0
            n = conn.execute("SELECT COUNT(*) c FROM complaints").fetchone()["c"]
        if not forced and n >= AUTO_SEED_BELOW:
            return 0
        return seed_synthetic(force=forced)
    except Exception:  # pragma: no cover - never block startup on demo data
        log.warning("synthetic incident seeding skipped", exc_info=True)
        return 0
