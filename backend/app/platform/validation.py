"""Backtesting / temporal validation harness for the predictive risk model.

The single hardest question a judging panel asks a predictive-policing system is
**"how do you know it works?"** This module answers it with a defensible,
standard methodology — rolling-origin (a.k.a. walk-forward) temporal
cross-validation — and reports the metrics the crime-forecasting literature uses
to grade hotspot maps:

  * **Hit-Rate@k**   share of next-week incidents that fall inside the predicted
                     top-k localities. (Operationally: "if I patrol the top k
                     areas, what fraction of next week's crime do I sit on?")
  * **PAI@k**        Predictive Accuracy Index — the field-standard metric
                     (Chainey et al., 2008):

                         PAI@k = (hits_in_top_k / total_incidents)
                                 ----------------------------------
                                       (k / total_areas)

                     i.e. how many times better than a blind "spread evenly"
                     baseline the model concentrates crime. PAI = 1 is no better
                     than chance; PAI = 3 means 3x the crime per unit area.
  * **capture-rate** the curve of captured-crime share as k grows 1..15 — the
                     "X% of crime in Y% of the city" headline.

Everything is **rolling-origin**: for each weekly fold we predict using ONLY the
complaints that existed strictly before the fold start (``compute_risk`` with an
``as_of`` cutoff), then grade against the incidents that actually occurred in the
following 7 days. No future data ever leaks into a prediction — this is genuine
out-of-sample forecasting, not curve-fitting.

We also run four ranking strategies side by side so the headline number has a
floor to beat:

    a) ``random``    uniform random ordering (fixed seed) — pure chance.
    b) ``prior``     static AREA_CRIME_PROFILE intensity ranking — "just patrol
                     the historically-bad areas", no live data.
    c) ``frequency`` raw all-time complaint counts before the fold, no decay —
                     a naive analyst's hotspot map.
    d) ``model``     the full recency-weighted predictive model.

Pure Python standard library only (``random``/``math``) — no numpy/sklearn — so
it runs anywhere the backend does, offline.
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

from ..constants.ahmedabad import AREAS
from ..database import get_conn
from .predictive import compute_risk
from .seed_ahmedabad import AREA_CRIME_PROFILE

# ---------------------------------------------------------------------------
# Tunables (kept conservative + documented so the numbers are reproducible).
# ---------------------------------------------------------------------------
DEFAULT_FOLDS = 8           # ~8 weekly walk-forward folds
FOLD_DAYS = 7               # one week per fold (the forecast horizon)
TOP_KS = (5, 10)            # report Hit-Rate / PAI at these k
CAPTURE_MAX_K = 15          # capture-rate curve runs top-1..top-15
BOOTSTRAP_ITERS = 1000      # resamples for the 90% CI over folds
BOOTSTRAP_SEED = 20240601   # fixed => reproducible CI
CI_LOW, CI_HIGH = 0.05, 0.95  # 90% interval

# Map the model's intensity buckets to a numeric rank for the prior baseline.
_PRIOR_INTENSITY_RANK = {"low": 1.0, "medium": 3.0, "high": 6.0}

_DT_FMT = "%Y-%m-%d %H:%M:%S"


def _parse_dt(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _fmt(dt: datetime) -> str:
    return dt.strftime(_DT_FMT)


# ---------------------------------------------------------------------------
# Ranking strategies. Each returns an ordered list of area names (most-risky
# first) given the cutoff ``as_of``. They must only look at data < as_of.
# ---------------------------------------------------------------------------

def _rank_model(as_of: datetime, _rng: random.Random) -> list[str]:
    """Full recency-weighted model (the system under test)."""
    return [a["area"] for a in compute_risk(as_of=as_of)]


def _rank_frequency(as_of: datetime, _rng: random.Random) -> list[str]:
    """Raw historical complaint frequency before the fold — no decay."""
    cutoff = _fmt(as_of)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT area, COUNT(*) n FROM complaints "
            "WHERE area IS NOT NULL AND area != '' AND created_at < ? "
            "GROUP BY area", (cutoff,)).fetchall()
    counts = {r["area"]: r["n"] for r in rows}
    # Stable order: by count desc, then by the canonical AREAS order so ties are
    # deterministic across runs.
    return sorted(AREAS, key=lambda a: (-counts.get(a, 0), list(AREAS).index(a)))


def _rank_prior(_as_of: datetime, _rng: random.Random) -> list[str]:
    """Static prior: AREA_CRIME_PROFILE intensity, no live data at all."""
    def score(a: str) -> float:
        prof = AREA_CRIME_PROFILE.get(a, {})
        return _PRIOR_INTENSITY_RANK.get(prof.get("intensity", ""), 1.0)
    return sorted(AREAS, key=lambda a: (-score(a), list(AREAS).index(a)))


def _rank_random(_as_of: datetime, rng: random.Random) -> list[str]:
    """Uniform random ordering (fixed seed) — the chance floor."""
    order = list(AREAS)
    rng.shuffle(order)
    return order


_STRATEGIES = {
    "model": _rank_model,
    "frequency": _rank_frequency,
    "prior": _rank_prior,
    "random": _rank_random,
}


# ---------------------------------------------------------------------------
# Fold construction + per-fold incident truth.
# ---------------------------------------------------------------------------

def _data_bounds(conn) -> tuple[datetime | None, datetime | None]:
    row = conn.execute(
        "SELECT MIN(created_at) lo, MAX(created_at) hi FROM complaints "
        "WHERE area IS NOT NULL AND area != ''").fetchone()
    if not row or not row["lo"] or not row["hi"]:
        return None, None
    return _parse_dt(row["lo"]), _parse_dt(row["hi"])


def _fold_starts(folds: int) -> list[datetime]:
    """The last ``folds`` weekly fold-start instants.

    Each fold predicts at ``fold_start`` and is graded on ``[fold_start,
    fold_start + 7d)``. We anchor the most recent gradable week so its 7-day
    horizon ends at the last incident, then step back one week per fold. Folds
    that would start before the data begins are dropped.
    """
    with get_conn() as conn:
        lo, hi = _data_bounds(conn)
    if lo is None or hi is None:
        return []
    # Most recent fully-gradable fold ends at hi; back up one horizon for its
    # start, then walk backwards a week at a time.
    latest_start = hi - timedelta(days=FOLD_DAYS)
    starts = []
    for i in range(folds):
        s = latest_start - timedelta(days=FOLD_DAYS * i)
        # Need at least one horizon of history before the fold to predict from.
        if s - timedelta(days=FOLD_DAYS) < lo:
            break
        starts.append(s)
    starts.reverse()  # chronological
    return starts


def _fold_incidents(fold_start: datetime) -> dict[str, int]:
    """Count incidents per area in the graded horizon [start, start+7d)."""
    lo, hi = _fmt(fold_start), _fmt(fold_start + timedelta(days=FOLD_DAYS))
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT area, COUNT(*) n FROM complaints "
            "WHERE area IS NOT NULL AND area != '' "
            "AND created_at >= ? AND created_at < ? GROUP BY area",
            (lo, hi)).fetchall()
    return {r["area"]: r["n"] for r in rows}


# ---------------------------------------------------------------------------
# Metrics.
# ---------------------------------------------------------------------------

def _hit_rate(ranking: list[str], truth: dict[str, int], k: int) -> float:
    total = sum(truth.values())
    if total == 0:
        return 0.0
    hits = sum(truth.get(a, 0) for a in ranking[:k])
    return hits / total


def _pai(ranking: list[str], truth: dict[str, int], k: int,
         n_areas: int) -> float:
    """Predictive Accuracy Index: hit-rate divided by the area-share k/N."""
    hr = _hit_rate(ranking, truth, k)
    area_share = k / n_areas if n_areas else 0.0
    if area_share <= 0:
        return 0.0
    return hr / area_share


def _capture_curve(ranking: list[str], truth: dict[str, int],
                   max_k: int) -> list[float]:
    """Cumulative captured-crime share for k = 1..max_k."""
    total = sum(truth.values())
    if total == 0:
        return [0.0] * max_k
    out, run = [], 0
    for i in range(max_k):
        if i < len(ranking):
            run += truth.get(ranking[i], 0)
        out.append(run / total)
    return out


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


# ---------------------------------------------------------------------------
# Bootstrap CI over folds (resample folds with replacement).
# ---------------------------------------------------------------------------

def _bootstrap_ci(per_fold: list[float], iters: int = BOOTSTRAP_ITERS,
                  seed: int = BOOTSTRAP_SEED) -> tuple[float, float]:
    """90% CI for the mean of a per-fold metric by resampling folds with
    replacement. Pure stdlib; fixed seed for reproducibility."""
    n = len(per_fold)
    if n == 0:
        return (0.0, 0.0)
    if n == 1:
        return (per_fold[0], per_fold[0])
    rng = random.Random(seed)
    means = []
    for _ in range(iters):
        sample = [per_fold[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[max(0, int(CI_LOW * iters) - 1)]
    hi = means[min(iters - 1, int(CI_HIGH * iters))]
    return (lo, hi)


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------

def _evaluate_strategy(name: str, starts: list[datetime],
                       truths: list[dict[str, int]],
                       n_areas: int) -> dict:
    """Run one ranking strategy across every fold and aggregate its metrics."""
    rank_fn = _STRATEGIES[name]
    # One RNG per strategy, seeded deterministically, so the random baseline is
    # reproducible run-to-run yet still differs fold-to-fold. Python's built-in
    # str hash is PYTHONHASHSEED-salted (not stable across processes), so derive
    # a stable per-strategy salt from the name bytes instead.
    salt = int.from_bytes(name.encode(), "little") & 0xFFFFFFFF
    rng = random.Random(BOOTSTRAP_SEED ^ salt)
    hr_by_k = {k: [] for k in TOP_KS}
    pai_by_k = {k: [] for k in TOP_KS}
    capture_folds: list[list[float]] = []
    fold_rows = []

    for start, truth in zip(starts, truths):
        ranking = rank_fn(start, rng)
        row = {"fold_start": _fmt(start),
               "incidents": sum(truth.values()),
               "top_areas": ranking[:max(TOP_KS)]}
        for k in TOP_KS:
            hr = _hit_rate(ranking, truth, k)
            pai = _pai(ranking, truth, k, n_areas)
            hr_by_k[k].append(hr)
            pai_by_k[k].append(pai)
            row[f"hit_rate@{k}"] = round(hr, 4)
            row[f"pai@{k}"] = round(pai, 3)
        capture_folds.append(_capture_curve(ranking, truth, CAPTURE_MAX_K))
        fold_rows.append(row)

    # Average the capture curve position-wise across folds.
    capture_avg = [
        round(_mean([c[i] for c in capture_folds]), 4)
        for i in range(CAPTURE_MAX_K)
    ] if capture_folds else []

    summary = {"strategy": name, "folds": len(starts)}
    for k in TOP_KS:
        hr_mean = _mean(hr_by_k[k])
        pai_mean = _mean(pai_by_k[k])
        hr_lo, hr_hi = _bootstrap_ci(hr_by_k[k])
        pai_lo, pai_hi = _bootstrap_ci(pai_by_k[k])
        summary[f"hit_rate@{k}"] = round(hr_mean, 4)
        summary[f"hit_rate@{k}_ci90"] = [round(hr_lo, 4), round(hr_hi, 4)]
        summary[f"pai@{k}"] = round(pai_mean, 3)
        summary[f"pai@{k}_ci90"] = [round(pai_lo, 3), round(pai_hi, 3)]
    return {"summary": summary, "capture_curve": capture_avg, "folds_detail": fold_rows}


def _surge_detection() -> list[dict]:
    """Did the model surface the planted, time-boxed surges *while they were
    happening*? This is the cleanest evidence the model reacts to emerging
    hotspots rather than just parroting the static prior.

    For each planted surge we score the model at the surge's END (so it has seen
    the surge build) and report the surge area's rank, against its rank scored
    just BEFORE the surge began (the counterfactual "no surge yet"). A big jump
    up the ranking = the model caught it. Fully data-driven from the
    ``PLANTED_SURGES`` ground truth, so it stays in sync with the seed.
    """
    # Imported here (not at module top) so a trimmed deployment without the
    # synthetic seed module still imports validation.py cleanly.
    try:
        from .seed_synthetic import PLANTED_SURGES, WINDOW_DAYS
    except Exception:  # pragma: no cover - synthetic seed optional
        return []

    with get_conn() as conn:
        _lo, hi = _data_bounds(conn)
    if hi is None:
        return []
    # The synthetic window starts WINDOW_DAYS before "today midnight". The data's
    # max timestamp is the window end, so back-compute the window start to align
    # surge day-offsets to real datetimes.
    window_start = (hi.replace(hour=0, minute=0, second=0, microsecond=0)
                    - timedelta(days=WINDOW_DAYS))

    out = []
    for s in PLANTED_SURGES:
        end_day = s["day_end"]
        start_day = s["day_start"]
        as_of_during = window_start + timedelta(days=end_day)
        as_of_before = window_start + timedelta(days=max(0, start_day - 1))
        rank_during = {a["area"]: i + 1 for i, a in
                       enumerate(compute_risk(as_of=as_of_during))}
        rank_before = {a["area"]: i + 1 for i, a in
                       enumerate(compute_risk(as_of=as_of_before))}
        for area in s["areas"]:
            rd = rank_during.get(area)
            rb = rank_before.get(area)
            out.append({
                "surge": s["name"],
                "area": area,
                "category": s["category"],
                "rank_before_surge": rb,
                "rank_during_surge": rd,
                "rank_improvement": (rb - rd) if (rb and rd) else None,
                "in_top10_during": bool(rd and rd <= 10),
            })
    return out


def run_validation(folds: int = DEFAULT_FOLDS, compare: bool = False) -> dict:
    """Rolling-origin temporal cross-validation of the risk model.

    Returns a JSON-serialisable dict:
      {
        "method": "...", "folds": N, "n_areas": M,
        "window": {"first_fold_start": ..., "last_fold_start": ...},
        "model": {summary..., capture_curve, folds_detail},
        "comparison": [ {summary per strategy} ]   # only when compare=True
        "headline": "...quotable one-liner..."
      }

    ``compare=False`` evaluates only the full model (fast). ``compare=True`` also
    runs the random / prior / frequency baselines for a side-by-side table.
    """
    folds = max(1, min(int(folds), 26))
    n_areas = len(AREAS)
    starts = _fold_starts(folds)

    if not starts:
        return {
            "method": "rolling-origin temporal cross-validation",
            "folds": 0, "n_areas": n_areas,
            "window": None, "model": None, "comparison": [],
            "headline": "Insufficient history to backtest "
                        "(need at least two weekly folds of complaints).",
            "note": "Seed the synthetic complaint stream to enable backtesting.",
        }

    # Precompute the ground-truth incident maps once; every strategy grades
    # against the same folds.
    truths = [_fold_incidents(s) for s in starts]

    model_eval = _evaluate_strategy("model", starts, truths, n_areas)

    # Oracle ceiling: rank each fold by its OWN realised counts (perfect
    # hindsight). This is the maximum PAI any predictor could score on this data
    # — it makes the model's PAI interpretable (a stationary, lightly-contrasted
    # synthetic stream has a low ceiling; the honest claim is the % of that
    # ceiling the model reaches, not an inflated absolute).
    oracle = {k: [] for k in TOP_KS}
    for truth in truths:
        oracle_rank = sorted(truth, key=lambda a: -truth.get(a, 0))
        for k in TOP_KS:
            oracle[k].append(_pai(oracle_rank, truth, k, n_areas))
    oracle_pai = {k: round(_mean(oracle[k]), 3) for k in TOP_KS}

    comparison = []
    if compare:
        for name in ("model", "frequency", "prior", "random"):
            comparison.append(_evaluate_strategy(
                name, starts, truths, n_areas)["summary"])

    surges = _surge_detection()

    # Headline numbers pulled from the model summary.
    ms = model_eval["summary"]
    cap10 = model_eval["capture_curve"][9] if len(
        model_eval["capture_curve"]) >= 10 else 0.0
    hr10 = ms.get("hit_rate@10", 0.0)
    pai10 = ms.get("pai@10", 0.0)
    ci = ms.get("hit_rate@10_ci90", [0.0, 0.0])
    city_share = round(100.0 * 10 / n_areas)
    # Surge-detection one-liner — the genuinely strong, judge-friendly result.
    caught = [s for s in surges if s.get("in_top10_during")]
    surge_line = ""
    if surges:
        surge_line = (f" | caught {len(caught)}/{len(surges)} planted "
                      f"surge-areas in the live top-10 during their surge week")
    headline = (
        f"Hit-Rate@10: {hr10:.2f} | PAI@10: {pai10:.1f}x "
        f"(oracle ceiling {oracle_pai.get(10, 0.0):.1f}x) | "
        f"capture {round(cap10 * 100)}% of next-week crime in "
        f"{city_share}% of the city "
        f"(90% CI hit-rate@10 [{ci[0]:.2f}, {ci[1]:.2f}], "
        f"{ms['folds']} weekly folds){surge_line}"
    )

    return {
        "method": "rolling-origin temporal cross-validation",
        "horizon_days": FOLD_DAYS,
        "folds": len(starts),
        "n_areas": n_areas,
        "top_ks": list(TOP_KS),
        "capture_max_k": CAPTURE_MAX_K,
        "window": {
            "first_fold_start": _fmt(starts[0]),
            "last_fold_start": _fmt(starts[-1]),
        },
        "model": model_eval,
        "oracle_pai": oracle_pai,
        "comparison": comparison,
        "surge_detection": surges,
        "headline": headline,
        "disclaimer": "Computed on fully synthetic, deterministic demo data "
                      "(see docs/AHMEDABAD_CRIME_DATA.md). Numbers demonstrate "
                      "methodology, not real-world operational accuracy.",
    }
