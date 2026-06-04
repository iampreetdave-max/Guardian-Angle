"""Predictive-model backtest CLI — the quotable accuracy harness.

Runs rolling-origin temporal cross-validation over the complaints table and
prints a judge-ready headline plus the baseline comparison table:

    Hit-Rate@10: 0.71 | PAI@10: 3.8x | capture 68% of crime in 33% of city ...

By default it works on a THROWAWAY temp database seeded with the deterministic
synthetic stream, so it never touches (or pollutes) your dev DB. If your dev DB
is already synthetic-seeded you can point it there with --use-dev-db.

Run from backend/:
    python scripts/predictive_backtest.py                 # temp DB (safe)
    python scripts/predictive_backtest.py --folds 8 --no-compare
    python scripts/predictive_backtest.py --use-dev-db    # only if already seeded
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")


def _bootstrap_temp_db() -> str:
    """Point the app at a fresh temp data dir and return it. MUST run before any
    `app.*` import so the throwaway DB is the one that gets created/seeded."""
    data_dir = tempfile.mkdtemp(prefix="visionscan_backtest_")
    os.environ["VISIONSCAN_DATA_DIR"] = data_dir
    os.environ["VISIONSCAN_ENABLE_ANOMALY"] = "false"
    # Force the synthetic seed even though the demo seed flag would also run it;
    # being explicit keeps the harness self-contained.
    os.environ["VISIONSCAN_SEED_SYNTHETIC"] = "true"
    return data_dir


def _print_table(rows: list[dict]) -> None:
    """Pretty-print the baseline comparison summaries as an aligned table."""
    if not rows:
        print("  (no comparison rows)")
        return
    cols = ["strategy", "hit_rate@5", "hit_rate@10", "pai@5", "pai@10"]
    headers = ["strategy", "HR@5", "HR@10", "PAI@5", "PAI@10"]
    widths = [max(len(h), 9) for h in headers]
    line = "  " + "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(line)
    print("  " + "  ".join("-" * w for w in widths))
    for r in rows:
        cells = []
        for c in cols:
            v = r.get(c, "")
            if isinstance(v, float):
                v = f"{v:.3f}" if c.startswith("hit") else f"{v:.2f}x"
            cells.append(str(v))
        print("  " + "  ".join(c.ljust(w) for c, w in zip(cells, widths)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Backtest the predictive risk model.")
    parser.add_argument("--folds", type=int, default=8,
                        help="weekly walk-forward folds (default 8)")
    parser.add_argument("--no-compare", action="store_true",
                        help="skip the baseline comparison table")
    parser.add_argument("--use-dev-db", action="store_true",
                        help="run against the existing dev DB instead of a temp "
                             "copy (only if it is already synthetic-seeded)")
    args = parser.parse_args()

    if not args.use_dev_db:
        data_dir = _bootstrap_temp_db()
        print(f"[backtest] using throwaway DB at {data_dir}")
    else:
        print("[backtest] using the existing dev database (no temp copy)")

    # Imports happen AFTER the env is set so the temp DB is the active one.
    from app.database import init_db
    from app.platform.seed_synthetic import seed_synthetic
    from app.database import get_conn
    from app.platform.validation import run_validation

    init_db()  # creates schema + demo users (+ auto synthetic seed when forced)

    # Make sure there is data to backtest. On a temp DB the forced env flag
    # already seeded it via the demo-seed flow; seed_synthetic(force=...) is
    # idempotent enough that a second guarded call is cheap and safe.
    with get_conn() as conn:
        n = conn.execute("SELECT COUNT(*) c FROM complaints").fetchone()["c"]
    if n < 100:
        if args.use_dev_db:
            print("[backtest] dev DB has too few complaints to backtest "
                  f"({n}). Re-run without --use-dev-db for a seeded temp DB.")
            return 2
        inserted = seed_synthetic(force=True)
        print(f"[backtest] seeded {inserted} synthetic complaints")
        with get_conn() as conn:
            n = conn.execute("SELECT COUNT(*) c FROM complaints").fetchone()["c"]
    print(f"[backtest] complaints available: {n}")

    result = run_validation(folds=args.folds, compare=not args.no_compare)

    print("\n" + "=" * 72)
    print("PREDICTIVE MODEL — BACKTEST (rolling-origin temporal CV)")
    print("=" * 72)
    if not result.get("folds"):
        print(result.get("headline", "No folds could be evaluated."))
        return 1

    win = result["window"]
    print(f"folds: {result['folds']}  horizon: {result['horizon_days']}d  "
          f"areas: {result['n_areas']}")
    print(f"window: {win['first_fold_start']}  ->  {win['last_fold_start']}")
    print("\nHEADLINE:")
    print("  " + result["headline"])

    ms = result["model"]["summary"]
    oracle = result.get("oracle_pai", {})
    print("\nMODEL METRICS (mean over folds, 90% bootstrap CI):")
    for k in (5, 10):
        hr = ms.get(f"hit_rate@{k}")
        hr_ci = ms.get(f"hit_rate@{k}_ci90")
        pai = ms.get(f"pai@{k}")
        pai_ci = ms.get(f"pai@{k}_ci90")
        oc = oracle.get(k) or oracle.get(str(k))
        oc_txt = f"  (oracle ceiling {oc:.2f}x)" if oc else ""
        print(f"  Hit-Rate@{k}: {hr:.3f}  CI90 {hr_ci}    "
              f"PAI@{k}: {pai:.2f}x  CI90 {pai_ci}{oc_txt}")

    cap = result["model"]["capture_curve"]
    if cap:
        marks = [1, 3, 5, 10, 15]
        print("\nCAPTURE-RATE CURVE (share of next-week crime in top-k areas):")
        for k in marks:
            if k <= len(cap):
                city = round(100.0 * k / result["n_areas"])
                print(f"  top-{k:<2d} ({city:>2d}% of city): "
                      f"{cap[k - 1] * 100:.1f}% of crime")

    surges = result.get("surge_detection") or []
    if surges:
        print("\nSURGE DETECTION (did the model surface planted, time-boxed "
              "hotspots while they happened?):")
        for s in surges:
            rb, rd = s.get("rank_before_surge"), s.get("rank_during_surge")
            flag = "TOP-10" if s.get("in_top10_during") else "      "
            print(f"  [{flag}] {s['area']:<12s} {s['category']:<16s} "
                  f"rank {rb}->{rd}  (+{s.get('rank_improvement')})  "
                  f"| {s['surge']}")

    if result.get("comparison"):
        print("\nBASELINE COMPARISON:")
        _print_table(result["comparison"])
        # Quick verdict line: model uplift over the random floor.
        by_name = {r["strategy"]: r for r in result["comparison"]}
        m, rnd = by_name.get("model"), by_name.get("random")
        if m and rnd:
            uplift = m["hit_rate@10"] - rnd["hit_rate@10"]
            print(f"\n  Model beats the random floor at HR@10 by "
                  f"{uplift * 100:.1f} pts "
                  f"({m['hit_rate@10']:.3f} vs {rnd['hit_rate@10']:.3f}).")

    print("\n" + result.get("disclaimer", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
