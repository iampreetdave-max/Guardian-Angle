"""One-command reset to a known-good demo state — against the REAL dev DB.

The presenter runs this once before going on stage. It:

  1. BACKS UP the current dev database to a timestamped ``.bak`` beside it (so a
     reset is always reversible);
  2. WIPES the demo-relevant tables and recreates the schema via ``init_db``,
     then FORCE-seeds the deterministic synthetic stream (demo accounts + ~20
     labeled Ahmedabad incidents + the ~1.5-3k synthetic complaint volume that
     drives the City Map, analytics, and the predictive backtest);
  3. SELF-VERIFIES the result end-to-end with an in-process FastAPI TestClient
     (no server needed): complaint volume in band, risk endpoint returns all 30
     localities with a known-hot top hotspot, the patrol plan covers the top-5,
     the validation/backtest endpoint is healthy, and the anomaly / cyber /
     CrimeGPT / GovIntel health endpoints all answer.

On success it prints a green ``DEMO READY`` banner with the live app URLs and the
demo accounts (read straight from ``platform/seed.py`` so they never drift). On
any failed check it prints a red banner naming the failing check and exits 1.

Idempotent and re-runnable: every run re-backs-up, re-wipes, and re-seeds, so the
demo state is deterministic no matter how many times you run it.

Run from backend/:
    python scripts/demo_reset.py
    python scripts/demo_reset.py --no-backup     # skip the .bak (CI / throwaway)
    python scripts/demo_reset.py --dry-run        # verify only, never touch data
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from datetime import datetime

# Anomaly stays off for the reset so no model has to load — the self-checks use
# TestClient against the seeded DB only. Force the synthetic stream so the demo
# volume is present regardless of any pre-existing rows.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("VISIONSCAN_ENABLE_ANOMALY", "false")
os.environ["VISIONSCAN_SEED_SYNTHETIC"] = "true"

# Windows consoles default to cp1252 and choke on box-drawing / em-dash glyphs.
# Reconfigure to UTF-8 where supported so the banner always prints cleanly.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# ---- ANSI colour (auto-disabled when not a TTY or NO_COLOR is set) ----------
_USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
def _c(code: str, s: str) -> str:
    return f"\033[{code}m{s}\033[0m" if _USE_COLOR else s
GREEN = lambda s: _c("32", s)
RED = lambda s: _c("1;31", s)
BOLD = lambda s: _c("1", s)
DIM = lambda s: _c("2", s)

# Known genuinely-hot localities — the top forecast hotspot must be one of these.
# The eastern industrial belt + SG-Highway spine run hot in AREA_BASE_RATE; Bopal
# and Gota heat into the top tier via the planted drift patterns (see
# platform/seed_synthetic.py). Any of them topping the ranking is "correct".
_KNOWN_HOT = {"Vatva", "Naroda", "Gomtipur", "Bapunagar", "Maninagar",
              "SG Highway", "Bopal", "Gota"}

# Expected synthetic complaint volume band (the generator targets ~1.5-3k over a
# rolling 180-day window; the exact count drifts day to day with the weekend
# uplift, so we assert the band, not a fixed number).
_MIN_COMPLAINTS = 1200
_MAX_COMPLAINTS = 4000

_FAILURES: list[str] = []
_PASSED = 0


def check(name: str, ok: bool, detail: str = "") -> bool:
    global _PASSED
    mark = GREEN("[PASS]") if ok else RED("[FAIL]")
    line = f"  {mark} {name}"
    if detail:
        line += DIM(f"  — {detail}")
    print(line)
    if ok:
        _PASSED += 1
    else:
        _FAILURES.append(name)
    return ok


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

def _backup_db(db_path) -> "str | None":
    """Copy the current DB (and its WAL/SHM sidecars) to a timestamped .bak."""
    if not db_path.exists():
        print(DIM(f"  (no existing DB at {db_path} — nothing to back up)"))
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = db_path.with_suffix(db_path.suffix + f".{ts}.bak")
    shutil.copy2(db_path, bak)
    # WAL-mode sidecars, if present, so the backup is a faithful snapshot.
    for ext in ("-wal", "-shm"):
        side = db_path.parent / (db_path.name + ext)
        if side.exists():
            shutil.copy2(side, str(bak) + ext)
    print(GREEN(f"  backed up DB -> {bak.name}"))
    return str(bak)


def _wipe_demo_tables() -> None:
    """Drop the demo-relevant rows so init_db + seed rebuild a clean state.

    We clear the platform data tables (users/teams/complaints/cases/…) and the
    synthetic-seed marker, then let init_db()'s seed flow repopulate. Reference
    tables created by schema scripts are left to be recreated idempotently.
    """
    from app.database import get_conn

    # Order respects FKs (children first). Unknown/absent tables are ignored so
    # this stays robust as the schema grows. Reference/cache tables that are
    # rebuilt or re-fetched (gov_documents corpus, login_attempts, audit_log) are
    # cleared too so the demo starts from a pristine, deterministic state.
    tables = [
        # case-scoped children
        "case_assignments", "case_diary", "case_documents", "case_messages",
        "case_meetings", "case_parties", "case_seizures", "case_statements",
        "crimegpt_documents", "evidence", "ratings",
        # platform activity
        "notifications", "anomaly_events", "patrol_logs", "broadcasts",
        "email_outbox", "login_attempts", "audit_log",
        # core entities
        "cases", "complaints", "teams", "users",
        # gov intel cache + per-user state
        "gov_bookmarks", "gov_saved_searches", "gov_subscriptions",
        "gov_search_log", "gov_feed_status",
        # seed marker so the synthetic stream re-seeds deterministically
        "app_settings",
    ]
    with get_conn() as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        for t in tables:
            try:
                conn.execute(f"DELETE FROM {t}")
            except Exception:
                pass  # table may not exist in this build — fine
        conn.execute("PRAGMA foreign_keys = ON")


def reset_demo_state(do_backup: bool) -> "str | None":
    """Back up (optional), wipe, recreate + force-seed. Returns the backup path."""
    from app.config import get_settings
    from app.database import init_db
    from app.platform.seed_synthetic import seed_synthetic

    from app.database import get_conn

    settings = get_settings()
    print(BOLD("Resetting demo state (real dev DB)…"))
    bak = _backup_db(settings.db_path) if do_backup else None
    if not do_backup:
        print(DIM("  (--no-backup: skipping DB backup)"))

    # init_db is idempotent: creates the schema if missing. Wipe AFTER ensuring
    # the schema exists so DELETEs always target real tables.
    init_db()
    _wipe_demo_tables()
    # Re-run the full seed flow against the now-empty DB. With users==0 it seeds
    # the demo accounts + labeled incidents, then (via maybe_seed_synthetic, with
    # the marker wiped + VISIONSCAN_SEED_SYNTHETIC set) lays down the synthetic
    # stream. We DON'T force a second seed_synthetic here — that would double the
    # volume — but we guard against a skipped seed below.
    init_db()
    with get_conn() as conn:
        n = conn.execute("SELECT COUNT(*) c FROM complaints").fetchone()["c"]
    if n < _MIN_COMPLAINTS:
        # The seed flow didn't lay the stream down (unexpected) — force it once.
        n = seed_synthetic(force=True)
    print(GREEN(f"  re-seeded demo state ({n} synthetic complaints)"))
    return bak


# ---------------------------------------------------------------------------
# Self-verification (in-process TestClient — no server needed)
# ---------------------------------------------------------------------------

def self_verify() -> None:
    from fastapi.testclient import TestClient

    from app.main import app
    from app.platform.seed import _DEMO

    # Resolve an officer login from the seed list so the gated endpoints work.
    officer = next((d for d in _DEMO if d[3] == "officer"), None)
    assert officer, "no officer in seed._DEMO"

    print(BOLD("\nSelf-verifying demo state…"))
    with TestClient(app) as client:
        r = client.post("/api/auth/login",
                        json={"email": officer[1], "password": officer[2]})
        check("officer demo account logs in", r.status_code == 200, r.text[:60])
        if r.status_code != 200:
            return
        hdr = {"Authorization": f"Bearer {r.json()['token']}"}

        # 1) Complaint volume in the expected demo band.
        m = client.get("/api/analytics/map", headers=hdr)
        ok = m.status_code == 200
        total = 0
        if ok:
            total = sum(a["complaints"] for a in m.json()["areas"])
        check("complaints volume in demo band",
              ok and _MIN_COMPLAINTS <= total <= _MAX_COMPLAINTS,
              f"{total} complaints (expect {_MIN_COMPLAINTS}-{_MAX_COMPLAINTS})")

        # 2) Risk endpoint returns all 30 localities with a known-hot top hotspot.
        rk = client.get("/api/predict/risk", headers=hdr)
        check("risk endpoint healthy", rk.status_code == 200, rk.text[:60])
        areas = rk.json().get("areas", []) if rk.status_code == 200 else []
        check("risk scores cover 30 localities", len(areas) == 30,
              f"got {len(areas)}")
        top = areas[0] if areas else {}
        check("top hotspot is a known-hot area",
              top.get("area") in _KNOWN_HOT,
              f"top={top.get('area')} ({top.get('risk_score')})")
        check("scores normalized 0..100",
              bool(areas) and all(0 <= a["risk_score"] <= 100 for a in areas))

        # 3) Patrol plan covers the top-5 forecast hotspots.
        top5 = {a["area"] for a in areas[:5]}
        pr = client.get("/api/predict/patrol-routes?units=2", headers=hdr)
        check("patrol planner healthy", pr.status_code == 200, pr.text[:60])
        routed = set()
        if pr.status_code == 200:
            routed = {w["area"] for rt in pr.json()["routes"]
                      for w in rt["waypoints"]}
        check("patrol plan covers the top-5 hotspots",
              len(top5 & routed) >= 5 if len(top5) >= 5 else bool(top5 & routed),
              f"covered {sorted(top5 & routed)} of top5={sorted(top5)}")

        # 4) Validation / backtest endpoint healthy with real folds + surges.
        v = client.get("/api/predict/validation?compare=true&folds=8", headers=hdr)
        check("validation endpoint healthy", v.status_code == 200, v.text[:60])
        vj = v.json() if v.status_code == 200 else {}
        check("backtest evaluated folds", vj.get("folds", 0) >= 4,
              f"folds={vj.get('folds')}")
        surges = vj.get("surge_detection", [])
        check("planted surges all caught in top-10",
              bool(surges) and all(s["in_top10_during"] for s in surges),
              f"{sum(s['in_top10_during'] for s in surges)}/{len(surges)} caught")

        # 5) Module health endpoints answer (200) — offline-friendly probes.
        for label, path in (
            ("anomaly watch", "/api/anomalies?status_filter=all&limit=1"),
            ("cyber map layer", "/api/analytics/map/cyber?days=90"),
            ("CrimeGPT", "/api/crimegpt/health"),
            ("GovIntel", "/api/gov/health"),
        ):
            hr = client.get(path, headers=hdr)
            check(f"{label} health endpoint 200", hr.status_code == 200,
                  f"{path} -> {hr.status_code}")


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

def _print_demo_ready(n_checks: int) -> None:
    from app.platform.seed import _DEMO

    bar = "═" * 64
    print()
    print(GREEN(bar))
    print(GREEN(BOLD(f"  DEMO READY — all {n_checks} checks passed")))
    print(GREEN(bar))
    print(BOLD("\n  App URLs"))
    print("    Dashboard (one-command launch) .. http://localhost:8080")
    print("    API + Swagger docs .............. http://localhost:8000/docs")
    print("    Frontend dev (vite) ............. http://localhost:5173")
    print("    Public try-it (Hugging Face) .... "
          "https://huggingface.co/spaces/iampreetdave/visionscan")
    print(BOLD("\n  Demo accounts  (DEV ONLY)"))
    for name, email, pw, role, badge in _DEMO:
        print(f"    {role:<8s} {email:<22s} {pw:<12s} {DIM(name)}")
    print(DIM("\n  Note: synthetic, deterministic demo data — see "
              "docs/AHMEDABAD_CRIME_DATA.md"))
    print()


def _print_failure() -> None:
    bar = "═" * 64
    print()
    print(RED(bar))
    print(RED(BOLD(f"  DEMO NOT READY — {len(_FAILURES)} check(s) failed")))
    for f in _FAILURES:
        print(RED(f"    ✗ {f}"))
    print(RED(bar))
    print(DIM("  Re-run after fixing, or restore the .bak printed above.\n"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reset + self-verify the VisionScan demo state.")
    parser.add_argument("--no-backup", action="store_true",
                        help="skip the timestamped DB backup")
    parser.add_argument("--dry-run", action="store_true",
                        help="run the self-checks only; never touch the DB")
    args = parser.parse_args()

    print(BOLD("VisionScan — demo reset & self-verify"))
    print("=" * 64)

    if args.dry_run:
        print(DIM("--dry-run: verifying the CURRENT demo state, no reset.\n"))
    else:
        try:
            reset_demo_state(do_backup=not args.no_backup)
        except Exception as exc:  # pragma: no cover - surfaced to the presenter
            print(RED(f"  reset failed: {exc}"))
            _FAILURES.append(f"reset: {exc}")

    if not _FAILURES:
        try:
            self_verify()
        except Exception as exc:  # pragma: no cover
            print(RED(f"  self-verify crashed: {exc}"))
            _FAILURES.append(f"self-verify: {exc}")

    if _FAILURES:
        _print_failure()
        return 1
    _print_demo_ready(_PASSED)
    return 0


if __name__ == "__main__":
    sys.exit(main())
