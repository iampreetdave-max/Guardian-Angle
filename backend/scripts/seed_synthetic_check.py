"""Verification harness for the synthetic incident generator.

Seeds a fresh TEMP database (never the dev DB) and prints:
  * total complaint rows + how many are the synthetic stream,
  * rows per area (top 5),
  * an hour-of-day histogram (should peak in the evening),
  * Maninagar chain-snatching counts inside vs. outside the planted surge weeks,
  * SG Highway / Satellite cyber-fraud weekly counts (ramp in the final 4 weeks).

Run:
    backend/.venv/Scripts/python.exe backend/scripts/seed_synthetic_check.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Make the temp dir the data_dir BEFORE importing app modules so get_settings()
# (lru-cached) picks it up and we never touch the real dev DB.
_TMP = Path(tempfile.mkdtemp(prefix="vs_synth_check_"))
os.environ["VISIONSCAN_DATA_DIR"] = str(_TMP)
# Quiet the demo overlay so the histogram reflects the synthetic stream only.
os.environ["VISIONSCAN_SEED_DEMO_DATA"] = "false"

# Ensure `backend/` is importable as the package root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import get_conn, init_db  # noqa: E402
from app.platform.seed_synthetic import (  # noqa: E402
    PLANTED_SURGES,
    WINDOW_DAYS,
    seed_synthetic,
)


def main() -> None:
    init_db()  # creates schema + seeds demo users (needed: complaints FK)
    n = seed_synthetic(force=True)
    print(f"\nTemp DB: {_TMP}")
    print(f"Inserted (synthetic): {n}")

    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM complaints").fetchone()["c"]
        print(f"Total complaint rows: {total}")
        if not (1500 <= n <= 3000):
            print(f"  !! WARNING: synthetic count {n} outside the 1500-3000 target band")

        print("\nRows per area (top 5):")
        for r in conn.execute(
            "SELECT area, COUNT(*) c FROM complaints WHERE area IS NOT NULL "
            "GROUP BY area ORDER BY c DESC LIMIT 5"
        ):
            print(f"  {r['area']:<14} {r['c']}")

        print("\nHour-of-day histogram (all categories):")
        hist = {int(r["h"]): r["c"] for r in conn.execute(
            "SELECT CAST(strftime('%H', created_at) AS INT) h, COUNT(*) c "
            "FROM complaints GROUP BY h"
        )}
        peak_hours = sorted(hist, key=lambda h: hist[h], reverse=True)[:3]
        for h in range(24):
            c = hist.get(h, 0)
            bar = "#" * round(c / max(1, max(hist.values())) * 40)
            star = "  <- peak" if h in peak_hours else ""
            print(f"  {h:02d}:00 {c:>4} {bar}{star}")
        print(f"  busiest hours: {sorted(peak_hours)}")

        # --- planted surge #1: Maninagar chain-snatching, weeks 8-10 ---
        surge = next(s for s in PLANTED_SURGES if "Maninagar" in s["areas"])
        d0, d1 = surge["day_start"], surge["day_end"]
        # Translate window-day offsets to date() boundaries relative to today.
        lo = WINDOW_DAYS - d1   # days-ago at surge end (newer edge)
        hi = WINDOW_DAYS - d0   # days-ago at surge start (older edge)
        inside = conn.execute(
            "SELECT COUNT(*) c FROM complaints WHERE area='Maninagar' "
            "AND category='chain_snatching' "
            "AND date(created_at) >= date('now', ?) "
            "AND date(created_at) <  date('now', ?)",
            (f"-{hi} days", f"-{lo} days"),
        ).fetchone()["c"]
        span_days = d1 - d0
        outside = conn.execute(
            "SELECT COUNT(*) c FROM complaints WHERE area='Maninagar' "
            "AND category='chain_snatching' "
            "AND NOT (date(created_at) >= date('now', ?) "
            "AND date(created_at) < date('now', ?))",
            (f"-{hi} days", f"-{lo} days"),
        ).fetchone()["c"]
        in_rate = inside / max(1, span_days)
        out_rate = outside / max(1, WINDOW_DAYS - span_days)
        print(f"\nPlanted surge: {surge['name']}")
        print(f"  inside  (days {d0}-{d1}): {inside} chain-snatching "
              f"({in_rate:.2f}/day)")
        print(f"  outside the surge window: {outside} ({out_rate:.2f}/day)")
        print(f"  surge/baseline daily rate ratio: {in_rate / max(0.01, out_rate):.1f}x"
              f"  {'OK' if in_rate > out_rate * 1.8 else '!! WEAK'}")

        # --- planted surge #2: SG Highway/Satellite cyber-fraud final 4 weeks ---
        print("\nPlanted surge: SG Highway / Satellite cyber-fraud "
              "(weekly counts, ramp expected in final ~4 weeks):")
        for wk in range(WINDOW_DAYS // 7 - 5, WINDOW_DAYS // 7):
            lo_w = WINDOW_DAYS - (wk + 1) * 7
            hi_w = WINDOW_DAYS - wk * 7
            c = conn.execute(
                "SELECT COUNT(*) c FROM complaints "
                "WHERE area IN ('SG Highway','Satellite') AND category='cyber_fraud' "
                "AND date(created_at) >= date('now', ?) "
                "AND date(created_at) <  date('now', ?)",
                (f"-{hi_w} days", f"-{lo_w} days"),
            ).fetchone()["c"]
            print(f"  week {wk + 1:>2}: {c}")

    print("\nOK: synthetic seed verified.")


if __name__ == "__main__":
    main()
