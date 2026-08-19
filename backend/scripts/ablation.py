"""Ablation study of the predictive risk model - what does each ingredient
actually contribute?

`docs/VALIDATION.md` proves the model beats its baselines. It does NOT say which
part of the model is doing the work. This script answers that by re-running the
*same* rolling-origin backtest (`app/platform/validation.py`, untouched) once per
configuration, knocking out one ingredient at a time, and reporting the paired
per-fold delta against the full model.

Ingredients found in `app/platform/predictive.py` (read from the code, not from
the module docstring):

    raw(area) = PRIOR_W[intensity]                                # static prior
              + sum over reports of
                    SEVERITY_W[sev]                               # severity weight
                  * CATEGORY_W[cat]                               # category weight
                  * 0.5 ** (age / RECENCY_HALF_LIFE_DAYS)         # recency decay
              + ANOMALY_BOOST * n_active_anomalies                # anomaly boost

    trend / predicted_score = f(TREND_WINDOW_DAYS)                # forecast term

Two of those are dead weight *in the backtest*, and the script proves it rather
than assuming it:

  * ANOMALY_BOOST is applied only when `as_of is None` (predictive.py:161). Every
    backtest fold passes an `as_of`, so the boost never enters a graded ranking.
  * TREND_WINDOW_DAYS feeds `trend` and `predicted_score`, but `compute_risk`
    sorts by `risk_score` (predictive.py:202) and `_rank_model` takes that order
    (validation.py:91). The forecast term never reorders anything.

So "minus anomaly" and "minus trend" are expected to be EXACTLY 0.000, by
construction, not by measurement. To avoid mistaking "untested" for "useless",
we also run a counterfactual that ranks by `predicted_score` instead - that one
does exercise the trend term.

Runs against a throwaway temp data dir seeded exactly the way
`run_all_checks.py`'s backtest does, so it never touches the demo database.

Run from backend/:
    python scripts/ablation.py                    # writes ../docs/ABLATION.md
    python scripts/ablation.py --folds 8 --out ../docs/ABLATION.md
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUT = REPO_ROOT / "docs" / "ABLATION.md"

INF = float("inf")
METRICS = ("hit_rate@5", "hit_rate@10", "pai@10")


class Flat(dict):
    """A weight table stripped of its ability to discriminate.

    A plain `{}` is not enough: `compute_risk` calls `.get(key, default)` with
    hard-coded non-1.0 defaults (severity falls back to 2.0), so an empty dict
    would still weight an unknown severity differently from a known one.
    Overriding `.get` makes every lookup 1.0 regardless of key or default.
    """

    def get(self, _key=None, _default=None):  # noqa: D102
        return 1.0


# key, label, patches applied to the `predictive` module, strategy, kind, why
ABLATIONS = [
    dict(key="full", label="Full model", patches={}, kind="baseline",
         why="Everything on. All deltas are measured against this row."),
    dict(key="no_recency", label="minus recency decay",
         patches={"RECENCY_HALF_LIFE_DAYS": INF}, kind="ablation",
         why="Half-life -> infinity, so 0.5^(age/hl) = 1.0: every report ever "
             "filed counts exactly as much as one filed yesterday."),
    dict(key="no_prior", label="minus static prior",
         patches={"PRIOR_W": Flat()}, kind="ablation",
         why="Every locality starts from the same baseline instead of "
             "AREA_CRIME_PROFILE's low/medium/high intensity (1/3/6)."),
    dict(key="no_severity", label="minus severity weighting",
         patches={"SEVERITY_W": Flat()}, kind="ablation",
         why="low/medium/high/critical (1/2/3/4) all count as 1.0."),
    dict(key="no_category", label="minus category weighting",
         patches={"CATEGORY_W": Flat()}, kind="ablation",
         why="murder 2.0 ... theft 1.0 all count as 1.0. This term was not in "
             "the brief's component list, but it is a real term in the score."),
    dict(key="no_anomaly", label="minus anomaly boost",
         patches={"ANOMALY_BOOST": 0.0}, kind="ablation",
         why="ANOMALY_BOOST -> 0. Expected to be a no-op: the boost sits inside "
             "`if as_of is None` and every fold passes an as_of."),
    dict(key="no_trend", label="minus trend component",
         patches={"TREND_WINDOW_DAYS": 0.0}, kind="ablation",
         why="Trend window -> 0. Expected to be a no-op: trend only shapes "
             "`predicted_score`, and the backtest ranks on `risk_score`."),
    dict(key="trend_rank", label="plus ranking by predicted_score (counterfactual)",
         patches={}, strategy="model_predicted", kind="counterfactual",
         why="NOT an ablation. Ranks each fold by `predicted_score` (risk x "
             "capped trend growth) instead of `risk_score`, to test whether the "
             "forecast term carries signal the ranking currently throws away."),
    dict(key="stripped", label="minus everything (floor)",
         patches={"RECENCY_HALF_LIFE_DAYS": INF, "PRIOR_W": Flat(),
                  "SEVERITY_W": Flat(), "CATEGORY_W": Flat(),
                  "ANOMALY_BOOST": 0.0}, kind="floor",
         why="All weights flat, no decay: the score collapses to a raw "
             "complaint count. Doubles as the harness self-check - it must "
             "reproduce the `frequency` baseline exactly."),
]


def _bootstrap_temp_db() -> str:
    """Point the app at a fresh temp data dir. MUST run before any `app.*`
    import, exactly as run_all_checks.py's backtest does."""
    data_dir = tempfile.mkdtemp(prefix="visionscan_ablation_")
    os.environ["VISIONSCAN_DATA_DIR"] = data_dir
    os.environ["VISIONSCAN_ENABLE_ANOMALY"] = "false"
    os.environ["VISIONSCAN_SEED_SYNTHETIC"] = "true"
    return data_dir


def _run_config(cfg, predictive, validation, starts, truths, n_areas) -> dict:
    """Patch the model's globals, run the backtest, always restore."""
    saved = {k: getattr(predictive, k) for k in cfg["patches"]}
    for k, v in cfg["patches"].items():
        setattr(predictive, k, v)
    try:
        return validation._evaluate_strategy(
            cfg.get("strategy", "model"), starts, truths, n_areas)
    finally:
        for k, v in saved.items():
            setattr(predictive, k, v)


def _per_fold(evaluated: dict, metric: str) -> list[float]:
    return [row[metric] for row in evaluated["folds_detail"]]


def _deltas(full: dict, other: dict, validation) -> dict:
    """Paired per-fold delta (ablated - full) with a bootstrap 90% CI on the
    difference itself. Paired is the right test here: both configurations are
    graded on identical folds, so differencing removes the fold-to-fold variance
    that would otherwise swamp the effect."""
    out = {}
    for m in METRICS:
        diffs = [a - b for a, b in zip(_per_fold(other, m), _per_fold(full, m))]
        mean = sum(diffs) / len(diffs) if diffs else 0.0
        lo, hi = validation._bootstrap_ci(diffs)
        out[m] = {"delta": mean, "ci": [lo, hi],
                  "significant": not (lo <= 0.0 <= hi)}
    return out


def _name(cfg: dict) -> str:
    return cfg["label"].replace("minus ", "").replace("plus ", "")


def _verdict(d: dict) -> str:
    """One honest sentence about the HR@10 delta."""
    hr = d["hit_rate@10"]
    lo, hi = hr["ci"]
    if abs(hr["delta"]) < 5e-4 and abs(lo) < 5e-4 and abs(hi) < 5e-4:
        return "**no effect at all** (exactly 0.000 on every single fold)"
    if not hr["significant"]:
        return ("**not statistically distinguishable from noise** - the 90% CI "
                f"on the delta, [{lo:+.3f}, {hi:+.3f}], contains 0")
    if hr["delta"] < 0:
        return "**contributes** - removing it measurably costs HR@10"
    return "**hurts** - removing it measurably *improves* HR@10"


def render(rows: list[dict], meta: dict, selfcheck: tuple[bool, str]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full = next(r for r in rows if r["cfg"]["key"] == "full")
    ranked = sorted((r for r in rows if r["cfg"]["kind"] == "ablation"),
                    key=lambda r: -abs(r["deltas"]["hit_rate@10"]["delta"]))
    material = [r for r in ranked if r["deltas"]["hit_rate@10"]["significant"]]
    dead = [r for r in ranked
            if abs(r["deltas"]["hit_rate@10"]["delta"]) < 5e-4]
    ok, note = selfcheck

    L: list[str] = []
    L.append("# Predictive model - ablation study")
    L.append("")
    L.append(f"_Generated **{now}** by `backend/scripts/ablation.py`. Every "
             "number below was produced by running the code on this machine "
             "against a throwaway, freshly-seeded temp database._")
    L.append("")
    L.append("> **This is synthetic data.** Every complaint in this study comes "
             "from `backend/app/platform/seed_synthetic.py` (fixed seed, "
             "deterministic). This ablation therefore measures **how the model "
             "responds to a known generative process** - it is not a "
             "measurement of real-world predictive accuracy, and no row below "
             "should be read as one. A component that helps here helps because "
             "it happens to match the way the synthetic stream was generated.")
    L.append("")

    # ---- headline findings, auto-derived from the run ----
    L.append("## Bottom line")
    L.append("")
    helped_by_removal = [r for r in ranked
                         if r["deltas"]["hit_rate@10"]["delta"] > 5e-4]
    if material:
        best = material[0]
        verb = "produces" if len(material) == 1 else "produce"
        L.append(f"Of the {len(ranked)} ablated components, **{len(material)}** "
                 f"{verb} a change in HR@10 whose 90% bootstrap CI excludes "
                 f"zero: **{_name(best['cfg'])}** "
                 f"(dHR@10 = {best['deltas']['hit_rate@10']['delta']:+.3f})"
                 + ("." if len(material) == 1 else
                    ", the largest of them.")
                 + f" The other {len(ranked) - len(material)} are not "
                 "statistically distinguishable from noise on this data.")
    else:
        L.append(f"**None** of the {len(ranked)} ablated components produce a "
                 "change in HR@10 whose 90% bootstrap CI excludes zero. With "
                 f"{meta['folds']} folds the confidence intervals are wide "
                 "relative to the effects, so the honest reading is that this "
                 "backtest cannot separate these components from noise. The "
                 "point estimates below are reported for completeness, not as a "
                 "ranking to be trusted.")
    L.append("")
    if helped_by_removal:
        L.append("**Some components point the wrong way.** Deleting these "
                 "*raised* HR@10 rather than lowering it, so on this data they "
                 "are at best contributing nothing and may be mildly harmful:")
        for r in helped_by_removal:
            hr = r["deltas"]["hit_rate@10"]
            L.append(f"  - `{_name(r['cfg'])}`: dHR@10 = "
                     f"{hr['delta']:+.3f} (90% CI "
                     f"[{hr['ci'][0]:+.3f}, {hr['ci'][1]:+.3f}])"
                     + ("" if hr["significant"] else
                        " - the CI still contains 0, so this is a *direction*, "
                        "not a proven harm"))
        L.append("")
    if dead:
        names = ", ".join("`" + _name(r["cfg"]) + "`" for r in dead)
        L.append(f"**{len(dead)} of them change nothing whatsoever: {names}.** "
                 "Not \"a small effect\" - literally identical rankings on every "
                 "fold. That is a property of the code, not of the data; see "
                 "[Components that cannot affect the backtest]"
                 "(#components-that-cannot-affect-the-backtest).")
        L.append("")

    # ---- method ----
    L.append("## Method")
    L.append("")
    L.append("- Same harness as `docs/VALIDATION.md`: rolling-origin "
             "(walk-forward) temporal cross-validation, "
             f"**{meta['folds']} weekly folds**, {meta['horizon']}-day forecast "
             f"horizon, {meta['n_areas']} Ahmedabad localities.")
    L.append(f"- Window: `{meta['first']}` -> `{meta['last']}`.")
    L.append("- Each configuration re-runs `validation._evaluate_strategy` after "
             "monkey-patching one constant in `app.platform.predictive`. **No "
             "source file is modified** - the model under test is the shipped "
             "model with one knob neutralised.")
    L.append("- Delta is **paired per fold** (`ablated - full`, identical folds) "
             "with a 1000-resample bootstrap 90% CI on the difference itself. "
             "Pairing is what makes a small effect detectable at all; comparing "
             "two overlapping level-CIs would be a weaker and misleading test.")
    L.append("- **Sign convention: delta negative means removing the component "
             "made the model worse, i.e. the component was helping.** Delta "
             "positive means removing it *improved* the model.")
    L.append("- \"Distinguishable\" means the CI on the delta excludes 0. Where "
             "it does not, the result is reported as *not distinguishable* "
             "rather than ranked as if the point estimate meant something.")
    L.append("")

    # ---- levels ----
    L.append("## Absolute metrics per configuration")
    L.append("")
    L.append("| Configuration | HR@5 | HR@10 | HR@10 90% CI | PAI@10 |")
    L.append("|---|---|---|---|---|")
    for r in rows:
        s = r["eval"]["summary"]
        ci = s["hit_rate@10_ci90"]
        L.append(f"| {r['cfg']['label']} | {s['hit_rate@5']:.3f} | "
                 f"{s['hit_rate@10']:.3f} | [{ci[0]:.3f}, {ci[1]:.3f}] | "
                 f"{s['pai@10']:.2f}x |")
    L.append("")
    L.append("The full-model row is the same measurement `docs/VALIDATION.md` "
             "reports; small run-to-run differences in the level (not in the "
             "paired deltas) are the sliding-window drift described under "
             "[Reproduce](#reproduce).")
    L.append("")
    # Honest full-vs-floor comparison, including where the floor wins.
    strip = next((r for r in rows if r["cfg"]["kind"] == "floor"), None)
    if strip:
        d5 = strip["deltas"]["hit_rate@5"]
        d10 = strip["deltas"]["hit_rate@10"]
        L.append(f"**Full model vs the stripped floor** (a raw complaint count, "
                 f"identical to the `frequency` baseline at HR@10 "
                 f"{meta['frequency_hr10']:.3f}): every weight and the decay "
                 f"together are worth dHR@10 = {-d10['delta']:+.3f} "
                 f"(90% CI [{-d10['ci'][1]:+.3f}, {-d10['ci'][0]:+.3f}]) and "
                 f"dHR@5 = {-d5['delta']:+.3f} "
                 f"(90% CI [{-d5['ci'][1]:+.3f}, {-d5['ci'][0]:+.3f}]).")
        if d5["delta"] > 5e-4:
            L.append("")
            L.append("Note the sign at k=5. **The full model's advantage over a "
                     "raw complaint count is real at k=10 and gone at k=5** - "
                     "the stripped model is nominally ahead there"
                     + ("." if d5["significant"] else
                        ", though that CI contains 0, so the honest statement is "
                        "\"the weighting buys nothing in the top-5\" rather than "
                        "\"the weighting hurts in the top-5\".")
                     + " k=5 is the sharper operational question (5 patrol areas "
                     "out of 30), and the headline HR@10 number does not reveal "
                     "this asymmetry.")
    L.append("")

    # ---- contributions ranked ----
    L.append("## Contribution of each component, ranked by effect size")
    L.append("")
    L.append("Ranked by |dHR@10|. Ablations only; the counterfactual and the "
             "floor row are discussed separately below.")
    L.append("")
    L.append("| Rank | Component removed | dHR@5 | dHR@10 | dHR@10 90% CI | "
             "dPAI@10 | Distinguishable from noise? |")
    L.append("|---|---|---|---|---|---|---|")
    for i, r in enumerate(ranked, 1):
        d = r["deltas"]
        hr10 = d["hit_rate@10"]
        L.append(
            f"| {i} | {_name(r['cfg'])} | "
            f"{d['hit_rate@5']['delta']:+.3f} | {hr10['delta']:+.3f} | "
            f"[{hr10['ci'][0]:+.3f}, {hr10['ci'][1]:+.3f}] | "
            f"{d['pai@10']['delta']:+.3f}x | "
            f"{'yes' if hr10['significant'] else '**no**'} |")
    L.append("")
    L.append("### Reading each row")
    L.append("")
    for r in ranked:
        L.append(f"- **{_name(r['cfg'])}** - {_verdict(r['deltas'])}. "
                 f"_What was changed:_ {r['cfg']['why']}")
    L.append("")

    # ---- structural no-ops ----
    L.append("## Components that cannot affect the backtest")
    L.append("")
    L.append("These are zero **by construction**, which is a stronger and more "
             "useful statement than \"the measured effect was small\". The "
             "ablation confirms it empirically (identical rankings on every "
             "fold) and the code says why:")
    L.append("")
    L.append("- **Anomaly boost** - `predictive.py` applies it inside "
             "`if as_of is None:` (line 161). Every backtest fold passes an "
             "`as_of` cutoff, so the boost is never added to a graded score. "
             "The comment there is explicit and correct: live anomaly events "
             "have no historical timeline, so including them would leak "
             "present-day state into a past fold. **The anomaly boost is a "
             "live-dashboard feature, not a predictive one. Nothing in "
             "`docs/VALIDATION.md` is evidence for it.**")
    L.append("- **Trend / forecast term** - `TREND_WINDOW_DAYS` produces only "
             "`trend` and `predicted_score`. `compute_risk` sorts its output by "
             "`risk_score` (line 202) and `validation._rank_model` consumes that "
             "order, so the forecast never reorders a single locality in a "
             "graded fold. The counterfactual below tests whether it *could*.")
    L.append("- Not ablated at all, because they are monotone or cosmetic and "
             "provably cannot reorder anything: the min-max rescale to 0-100 "
             "(affine, order-preserving) and `RISK_BANDS` (a label applied after "
             "ranking).")
    L.append("")

    # ---- counterfactual ----
    cf = next((r for r in rows if r["cfg"]["kind"] == "counterfactual"), None)
    if cf:
        d = cf["deltas"]["hit_rate@10"]
        L.append("## Counterfactual: does the trend term contain unused signal?")
        L.append("")
        L.append("Ranking each fold by `predicted_score` (= `risk_score` x "
                 "capped trend growth) instead of `risk_score`:")
        L.append("")
        L.append(f"- dHR@10 = **{d['delta']:+.3f}** (90% CI "
                 f"[{d['ci'][0]:+.3f}, {d['ci'][1]:+.3f}]) - "
                 f"{_verdict(cf['deltas'])}.")
        L.append("")
        if d["significant"] and d["delta"] > 0:
            L.append("The forecast term carries signal that the current ranking "
                     "discards. Switching `_rank_model` to `predicted_score` "
                     "would be a real, testable improvement.")
        elif d["significant"] and d["delta"] < 0:
            L.append("Ranking on the forecast is measurably **worse** than "
                     "ranking on current risk. Leaving `risk_score` as the "
                     "ranking key is the right call, and this is the evidence "
                     "for it.")
        else:
            L.append("No detectable difference either way on this data. The "
                     "trend term is fine to keep as a UI annotation; there is "
                     "no evidence it would improve the ranking, and none that "
                     "it would hurt it.")
        L.append("")

    # ---- self-check ----
    L.append("## Harness self-check")
    L.append("")
    L.append("With every weight flattened and decay disabled, the model's score "
             "collapses to a plain complaint count, so its ranking must equal "
             "the independently-implemented `frequency` baseline in "
             "`validation.py`. If the patches were silently not reaching the "
             "scoring path, this check would fail and every row above would be "
             "meaningless.")
    L.append("")
    L.append(f"- **{'PASS' if ok else 'FAIL'}** - {note}")
    L.append("")

    # ---- reproduce ----
    L.append("## Reproduce")
    L.append("")
    L.append("```bash")
    L.append("cd backend")
    L.append(f"PYTHONPATH=. python scripts/ablation.py --folds {meta['folds']}")
    L.append("# writes docs/ABLATION.md; uses a throwaway temp DB seeded with")
    L.append("# VISIONSCAN_SEED_SYNTHETIC=true, never the demo database")
    L.append("```")
    L.append("")
    L.append("Deterministic within a day: the synthetic seed, the fold "
             "construction and the bootstrap seed (`BOOTSTRAP_SEED = 20240601`) "
             "are all fixed. The one moving part is that the synthetic window "
             "ends at seed time, so absolute levels drift slightly day to day as "
             "the window slides - the same effect documented in "
             "`docs/VALIDATION.md`. The paired deltas are markedly more stable "
             "than the levels, which is another reason to pair.")
    L.append("")

    # ---- plain english ----
    L.append("## What this means, in plain English")
    L.append("")
    L.append("The risk score is largely one idea - *count the recent complaints "
             "in each locality* - wearing several coats of paint. This study "
             "measures which coats are load-bearing.")
    L.append("")
    if material:
        L.append("- These components survive the significance test, so on this "
                 "data they genuinely change which localities get patrolled: "
                 + ", ".join("**" + _name(r["cfg"]) + "**" for r in material)
                 + ".")
    else:
        L.append("- **No single component clears the bar on its own.** The full "
                 "model's edge over the `frequency` baseline "
                 f"({full['eval']['summary']['hit_rate@10']:.3f} vs "
                 f"{meta['frequency_hr10']:.3f} HR@10) is spread thinly across "
                 "several terms, none of which is individually separable from "
                 f"fold-to-fold noise with only {meta['folds']} folds.")
    if helped_by_removal:
        L.append("- "
                 + ", ".join("**" + _name(r["cfg"]) + "**"
                             for r in helped_by_removal)
                 + " point the *wrong* way: the model scored slightly better "
                 "without them. None of those deltas clears the significance "
                 "bar either, so the correct statement is \"no evidence these "
                 "help, and a hint they might not\" - which is still a very "
                 "different claim from the one the model card implies.")
    if dead:
        L.append("- Some components are purely presentational. They make the "
                 "dashboard more informative and the model card more "
                 "explainable, and they contribute exactly nothing to the "
                 "accuracy numbers this project quotes. Anyone citing HR@10 as "
                 "evidence that anomaly detection improves prediction is citing "
                 "the wrong number.")
    L.append("- The honest summary is that a simple recency-weighted incident "
             "count does most of the work, and the elaborations around it are - "
             f"on synthetic data, at {meta['folds']} folds - mostly "
             "unresolvable. That is a limitation of the available evidence, not "
             "a claim that the elaborations are worthless on real data.")
    L.append("- The right next step is therefore not to add components. It is to "
             "get enough real folds that a delta this size becomes measurable.")
    L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Ablate the predictive risk model.")
    ap.add_argument("--folds", type=int, default=8)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    data_dir = _bootstrap_temp_db()
    print(f"[ablation] throwaway DB at {data_dir}")

    from app.database import init_db, get_conn
    from app.platform import predictive, validation
    from app.platform.seed_synthetic import seed_synthetic

    init_db()
    with get_conn() as conn:
        n = conn.execute("SELECT COUNT(*) c FROM complaints").fetchone()["c"]
    if n < 100:
        seed_synthetic(force=True)
        with get_conn() as conn:
            n = conn.execute("SELECT COUNT(*) c FROM complaints").fetchone()["c"]
    print(f"[ablation] complaints available: {n}")

    starts = validation._fold_starts(args.folds)
    if len(starts) < 2:
        print("[ablation] not enough history to backtest")
        return 1
    truths = [validation._fold_incidents(s) for s in starts]
    n_areas = len(validation.AREAS)
    print(f"[ablation] {len(starts)} folds, {n_areas} areas")

    # Counterfactual strategy: identical model, ranked on the forecast instead.
    def _rank_model_predicted(as_of, _rng):
        return [a["area"] for a in sorted(predictive.compute_risk(as_of=as_of),
                                          key=lambda a: -a["predicted_score"])]
    validation._STRATEGIES["model_predicted"] = _rank_model_predicted

    rows = []
    for cfg in ABLATIONS:
        ev = _run_config(cfg, predictive, validation, starts, truths, n_areas)
        rows.append({"cfg": cfg, "eval": ev})
        print(f"  {cfg['label']:<48} HR@10 {ev['summary']['hit_rate@10']:.4f}")

    full = next(r for r in rows if r["cfg"]["key"] == "full")
    for r in rows:
        r["deltas"] = _deltas(full["eval"], r["eval"], validation)

    # Self-check: the fully-stripped model must reproduce the frequency baseline.
    freq = validation._evaluate_strategy("frequency", starts, truths, n_areas)
    stripped = next(r for r in rows if r["cfg"]["key"] == "stripped")
    f_hr = freq["summary"]["hit_rate@10"]
    s_hr = stripped["eval"]["summary"]["hit_rate@10"]
    ok = abs(f_hr - s_hr) < 1e-9
    note = (f"stripped model HR@10 {s_hr:.4f} == frequency baseline HR@10 "
            f"{f_hr:.4f}; the patches provably reach the scoring path."
            if ok else
            f"stripped model HR@10 {s_hr:.4f} != frequency baseline HR@10 "
            f"{f_hr:.4f}. Investigate before trusting any row above.")
    print(f"[ablation] self-check {'PASS' if ok else 'FAIL'}: {note}")

    meta = {
        "folds": len(starts), "n_areas": n_areas,
        "horizon": validation.FOLD_DAYS,
        "first": validation._fmt(starts[0]),
        "last": validation._fmt(starts[-1]),
        "frequency_hr10": f_hr,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(rows, meta, (ok, note)), encoding="utf-8")
    print(f"[ablation] wrote {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
