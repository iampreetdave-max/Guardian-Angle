"""Regression: a database that already has users must still get the synthetic
incident volume.

seed_demo() short-circuits on a non-empty users table. The synthetic seeder used
to live inside the first-run-only branch, so any carried-over database (an
upgraded Docker volume, a redeployed VM, a judge's laptop that ran an older
build) booted with an empty map, empty analytics and a backtest reporting
"insufficient history". Everything still returned HTTP 200, so nothing caught it.
"""
from __future__ import annotations

import os
import tempfile


def _fresh_db(monkeypatch):
    """Point the app at a throwaway data dir and hand back a live connection."""
    monkeypatch.setenv("VISIONSCAN_DATA_DIR", tempfile.mkdtemp(prefix="visionscan_seedtest_"))
    from app import config, database

    config.get_settings.cache_clear()
    database.init_db()
    return database


def _count(database, table: str) -> int:
    with database.get_conn() as conn:
        return conn.execute(f"SELECT COUNT(*) c FROM {table}").fetchone()["c"]


def test_seed_demo_backfills_synthetic_on_existing_users(monkeypatch):
    database = _fresh_db(monkeypatch)
    from app.platform import seed

    seed.seed_demo()
    users_after_first = _count(database, "users")
    complaints_after_first = _count(database, "complaints")

    assert users_after_first > 0, "first run must create the demo accounts"
    assert complaints_after_first > 100, (
        "first run must lay down the synthetic incident volume, got "
        f"{complaints_after_first}"
    )

    # Simulate the carried-over database: users exist, synthetic volume does not.
    # Clear in foreign-key order — cases.complaint_id references complaints.
    with database.get_conn() as conn:
        conn.execute("DELETE FROM case_assignments")
        conn.execute("DELETE FROM cases")
        conn.execute("DELETE FROM complaints")
        conn.execute("DELETE FROM app_settings WHERE key = 'synthetic_seed_done'")
    assert _count(database, "complaints") == 0

    # Second boot: seed_demo() returns early on the users check, but must still
    # back-fill the incident volume.
    seed.seed_demo()
    assert _count(database, "complaints") > 100, (
        "seed_demo() must back-fill synthetic incidents when users already exist"
    )
    assert _count(database, "users") == users_after_first, "must not duplicate users"


def test_backfill_ignores_force_flag(monkeypatch):
    """VISIONSCAN_SEED_SYNTHETIC must not make every boot re-seed.

    demo_reset.py sets that flag for the whole process, then calls init_db()
    twice and opens a TestClient (a third startup). If the boot-time back-fill
    honoured the flag, each of those stacked another ~2,000 complaints —
    inflating the row count and every metric derived from it.
    """
    database = _fresh_db(monkeypatch)
    monkeypatch.setenv("VISIONSCAN_SEED_SYNTHETIC", "1")
    from app.platform import seed

    seed.seed_demo()
    first = _count(database, "complaints")
    assert first > 100

    # Subsequent boots in the same process, flag still set.
    seed.seed_demo()
    seed.seed_demo()
    assert _count(database, "complaints") == first, (
        "boot-time back-fill must not re-seed when the force flag is set; "
        f"grew from {first} to {_count(database, 'complaints')}"
    )


def test_seed_demo_is_idempotent(monkeypatch):
    database = _fresh_db(monkeypatch)
    from app.platform import seed

    seed.seed_demo()
    first = _count(database, "complaints")
    seed.seed_demo()
    seed.seed_demo()
    assert _count(database, "complaints") == first, "repeat boots must not duplicate rows"


if __name__ == "__main__":  # pragma: no cover - manual run
    import pytest
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
