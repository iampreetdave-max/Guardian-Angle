"""Demo polish: carry the complaint window up to today and fill the dead KPI tiles.

Two visible dashboard defects, both fixed here, both idempotently.

1. "Complaints, last 14 days" fell off a cliff.
   ``seed_synthetic`` lays down a rolling 180-day window, but its LAST generated
   day is ``seed_day - 1``: ``for day in range(WINDOW_DAYS)`` means the highest
   index is 179 and ``window_start + 179 days == now - 1 day``. So the chart's
   final bar is empty the moment the seed finishes, and one more bar dies for
   every day that passes afterwards (measured: data ended 2026-08-15 with today
   at 2026-08-19, four dead bars).
   ``scripts/demo_reset.py`` re-anchors the window to ``datetime.now()``, which
   does fix bars 2..14 (verified). It cannot fix today's bar, because of the
   off-by-one above. So we top up the thin tail days with the SAME generator
   (``seed_synthetic.generate_incidents``), re-anchored so window index 179 is
   TODAY, and keep only rows at or before the current clock time. Category mix,
   severity weighting, hour-of-day curve, area weighting, slow drift and the
   planted surges are therefore identical to the rest of the stream, and today
   reads as a partial day in progress rather than a future-dated spike.

2. Four KPI tiles read CLOSED 0 / AVG RESOLVE 0h / AVG RATING (blank) / EVIDENCE 0.
   Every seeded case is ``active`` and stamped with the seed timestamp, so there
   is nothing to close and nothing to average. We backdate each case to its own
   complaint's intake time, close the middle-aged subset with a verdict, closer
   and ``closed_at``, and add evidence (referencing REAL ingested frames and
   clips), citizen ratings, case messages, audit entries and notifications.

Everything written here is synthetic and deterministic: no real individuals, no
real case numbers, no real press-reported incidents. See
docs/AHMEDABAD_CRIME_DATA.md.

Run AFTER scripts/demo_reset.py: a reset wipes cases/evidence/ratings/messages,
so the order is always reset first, polish second. Inside the backend container,
from /app:
    PYTHONPATH=. python scripts/demo_polish.py
    PYTHONPATH=. python scripts/demo_polish.py --kpis   # read-only, changes nothing

Safe to re-run any number of times: the complaint top-up only fires on days that
are still thin, and every child-row insert is guarded by ``_once``.
"""
from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("VISIONSCAN_ENABLE_ANOMALY", "false")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import get_conn  # noqa: E402
from app.platform.seed_synthetic import (  # noqa: E402
    RANDOM_SEED,
    WINDOW_DAYS,
    _resolve_citizen_id,
    generate_incidents,
)

TS = "%Y-%m-%d %H:%M:%S"

# Local seed for the case/evidence/rating choices. Separate from the stream's
# RANDOM_SEED so topping up complaints and polishing cases stay independent.
POLISH_SEED = 8801

# A day whose count is below this share of the recent daily mean counts as
# "thin" and gets topped up. Also the idempotency guard: once a day is filled it
# is no longer thin, so a second run inserts nothing.
_THIN_SHARE = 0.55

# Plausible investigative span per category, in days (min, max). A money-trail
# cyber case takes weeks; a waterlogging response closes in days.
_DURATION_DAYS = {
    "cyber_fraud": (12, 20), "narcotics": (9, 14), "assault": (5, 10),
    "theft": (4, 9), "snatching": (5, 9), "vehicle_theft": (6, 11),
    "burglary": (7, 13), "disaster_flood": (3, 6), "disaster_fire": (3, 7),
}
_DEFAULT_DURATION = (6, 12)

# Closing verdicts: generic station language, deliberately name-free and
# number-free (no FIR/CR numbers) so nothing here can read as a real record.
_VERDICTS = {
    "cyber_fraud": "Chargesheet filed. Money trail traced via the bank nodal "
                   "officer, mule accounts frozen, and the recovered amount "
                   "ordered released to the complainant.",
    "narcotics": "Chargesheet filed. Consignment sent for chemical analysis; "
                 "accused remanded to judicial custody.",
    "assault": "Chargesheet filed. Injury report and CCTV keyframes annexed; "
               "accused released on bail pending trial.",
    "disaster_flood": "Closed after relief action. Low-lying zone pumped out, "
                      "drainage desilted, ward engineer compliance report on "
                      "record.",
    "disaster_fire": "Closed after relief action. Fire cause report received; "
                     "premises cleared for re-occupation.",
}
_DEFAULT_VERDICT = ("Investigation completed. Final report filed with the "
                    "supervising officer; nothing further pending at station "
                    "level.")

_CASE_NOTES = {
    "cyber_fraud": "Bank nodal-officer reply received; transaction trail and "
                   "beneficiary account details annexed to the case file.",
    "narcotics": "Seizure panchnama drawn in the presence of two independent "
                 "witnesses; samples sealed for analysis.",
    "assault": "Medical injury certificate obtained; two eyewitness statements "
               "recorded under the relevant procedure.",
    "disaster_flood": "Ward-level water-level log and pump deployment record "
                      "attached.",
}
_DEFAULT_NOTE = ("Preliminary enquiry note: locality canvassed, nearest "
                 "municipal camera footage requisitioned.")

# Citizen feedback for closed cases. Deliberately a mixed bag (one 3) so the
# average lands at 4.x; a wall of 5s reads as fabricated.
_FEEDBACK = [
    (5, "Officer visited the same day and kept me updated until it closed."),
    (4, "Good follow-up. Would have liked faster updates in the first week."),
    (5, "Very satisfied, the recovered amount actually came back to me."),
    (4, "Handled properly. Had to call the station twice for a status update."),
    (3, "Case was resolved, but I had to follow up myself for most of it."),
]


# --------------------------------------------------------------------------- #
# KPI reads: the exact queries platform/analytics.py:summary() runs
# --------------------------------------------------------------------------- #

def read_kpis(conn) -> dict:
    def q(sql):
        return conn.execute(sql).fetchone()[0]

    avg_h = q("SELECT AVG((julianday(closed_at) - julianday(created_at)) * 24.0) "
              "FROM cases WHERE status = 'closed' AND closed_at IS NOT NULL")
    rating = q("SELECT AVG(stars) FROM ratings")
    return {
        "closed_cases": q("SELECT COUNT(*) FROM cases WHERE status = 'closed'"),
        "open_cases": q("SELECT COUNT(*) FROM cases "
                        "WHERE status IN ('open','active')"),
        "avg_resolution_hours": round(avg_h, 1) if avg_h else 0,
        "avg_rating": round(rating, 2) if rating else 0,
        "n_ratings": q("SELECT COUNT(*) FROM ratings"),
        "total_evidence": q("SELECT COUNT(*) FROM evidence"),
        "case_messages": q("SELECT COUNT(*) FROM case_messages"),
        "notifications": q("SELECT COUNT(*) FROM notifications"),
    }


def day_series(conn, days: int = 14) -> list[tuple[str, int]]:
    """Dense complaints-per-day tail, same shape analytics.py builds."""
    raw = {r[0]: r[1] for r in conn.execute(
        "SELECT date(created_at) d, COUNT(*) FROM complaints "
        "WHERE created_at >= date('now', ?) GROUP BY d", (f"-{days - 1} days",))}
    out = []
    for off in range(days - 1, -1, -1):
        day = conn.execute("SELECT date('now', ?)", (f"-{off} days",)).fetchone()[0]
        out.append((day, raw.get(day, 0)))
    return out


# --------------------------------------------------------------------------- #
# Defect 1: top up the thin tail days with the real generator
# --------------------------------------------------------------------------- #

def topup_recent_days(conn) -> int:
    now = datetime.now().replace(microsecond=0)
    today = now.replace(hour=0, minute=0, second=0)

    # Reference level: mean daily count over days -34..-15, i.e. well inside the
    # fully-seeded part of the window and clear of the tail we are repairing.
    ref = conn.execute(
        "SELECT COUNT(*) / 20.0 FROM complaints "
        "WHERE created_at >= date('now','-34 days') "
        "AND created_at < date('now','-14 days')").fetchone()[0]
    if ref <= 0:                      # empty DB, nothing to reason from
        return 0

    counts = dict(day_series(conn, 14))
    # Today is legitimately partial: expect only the elapsed share of a day.
    elapsed = (now - today).total_seconds() / 86400.0
    thin = set()
    for off in range(13, -1, -1):
        day = (today - timedelta(days=off)).strftime("%Y-%m-%d")
        want = ref * _THIN_SHARE * (elapsed if off == 0 else 1.0)
        if counts.get(day, 0) < want:
            thin.add(day)
    if not thin:
        return 0

    # Re-anchor the generator so window index WINDOW_DAYS-1 == TODAY. That keeps
    # the drift and planted-surge treatment these days are meant to get (the
    # surges are defined relative to the END of the window).
    rows = [r for r in generate_incidents(random.Random(RANDOM_SEED),
                                          today - timedelta(days=WINDOW_DAYS - 1))
            if r["created_at"][:10] in thin
            and r["created_at"] <= now.strftime(TS)]  # never future-dated
    if not rows:
        return 0

    citizen_id = _resolve_citizen_id(conn)
    if not citizen_id:
        return 0
    conn.executemany(
        "INSERT INTO complaints (citizen_id, title, description, category, "
        "location, area, lat, lng, severity, status, created_at, "
        "cyber_category, fraud_channel, amount_lost, hours_since_incident) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(citizen_id, r["title"], r["description"], r["category"], r["location"],
          r["area"], r["lat"], r["lng"], r["severity"], r["status"],
          r["created_at"], r["cyber_category"], r["fraud_channel"],
          r["amount_lost"], r["hours_since_incident"]) for r in rows])
    print(f"  topped up {len(rows)} complaints across {len(thin)} thin day(s): "
          f"{', '.join(sorted(thin))}")
    return len(rows)


# --------------------------------------------------------------------------- #
# Defect 2: close cases, attach evidence, ratings, messages, audit, notifs
# --------------------------------------------------------------------------- #

def _once(conn, table: str, keys: dict, extra: dict) -> bool:
    """INSERT unless a row already matches every key column. This is what makes
    the whole script re-runnable. Table/column names are literals from this
    module, never user input."""
    where = " AND ".join(f"{k} IS ?" for k in keys)
    if conn.execute(f"SELECT 1 FROM {table} WHERE {where} LIMIT 1",
                    tuple(keys.values())).fetchone():
        return False
    cols = list(keys) + list(extra)
    conn.execute(
        f"INSERT INTO {table} ({', '.join(cols)}) "
        f"VALUES ({', '.join('?' * len(cols))})",
        tuple(keys.values()) + tuple(extra.values()))
    return True


def _frames_for(conn, video_id: int, n: int) -> list[tuple[int, float]]:
    """n keyframes spread across a real ingested video (frames table)."""
    rows = conn.execute("SELECT id, timestamp_sec FROM frames WHERE video_id = ? "
                        "ORDER BY frame_number", (video_id,)).fetchall()
    if not rows:
        return []
    picks = [rows[min(len(rows) - 1, (i + 1) * len(rows) // (n + 1))]
             for i in range(n)]
    return [(r["id"], r["timestamp_sec"] or 0.0) for r in picks]


def polish_cases(conn) -> dict:
    now = datetime.now().replace(microsecond=0)
    staff = {r["role"]: r["id"] for r in
             conn.execute("SELECT role, id FROM users ORDER BY id")}
    lead = staff.get("lead") or staff.get("admin")
    officer = staff.get("officer") or lead
    stats = {"closed": 0, "evidence": 0, "ratings": 0, "messages": 0,
             "notifs": 0, "audit": 0}
    if not lead:
        return stats

    cases = conn.execute(
        "SELECT c.id, c.title, c.citizen_id, cp.category, cp.area, "
        "cp.created_at AS intake FROM cases c "
        "JOIN complaints cp ON cp.id = c.complaint_id "
        "ORDER BY cp.created_at, c.id").fetchall()
    if not cases:
        return stats

    videos = conn.execute("SELECT id, filename FROM videos ORDER BY id").fetchall()

    # Close the middle-aged band: the oldest case keeps running (a long-tail
    # cyber investigation is normal) and the newest ones stay open, so the
    # station never looks like it has zero live work.
    closing = {r["id"] for r in cases[1:1 + max(1, round(len(cases) * 0.55))]}

    for rank, c in enumerate(cases):
        # Deterministic per case rank: re-running writes identical values.
        rng = random.Random(POLISH_SEED + rank)
        intake = datetime.strptime(c["intake"], TS)
        opened = intake + timedelta(hours=rng.randint(2, 9),
                                    minutes=rng.randrange(0, 60, 5))
        lo, hi = _DURATION_DAYS.get(c["category"], _DEFAULT_DURATION)
        span = timedelta(days=rng.randint(lo, hi), hours=rng.randint(0, 9))
        closed_at = min(opened + span, now - timedelta(hours=13))
        will_close = c["id"] in closing and closed_at > opened + timedelta(days=1)

        if will_close:
            verdict = _VERDICTS.get(c["category"], _DEFAULT_VERDICT)
            conn.execute(
                "UPDATE cases SET status='closed', verdict=?, closed_by=?, "
                "closed_at=?, citizen_visible=1, created_at=?, updated_at=? "
                "WHERE id=?",
                (verdict, lead, closed_at.strftime(TS), opened.strftime(TS),
                 closed_at.strftime(TS), c["id"]))
            stats["closed"] += 1
        else:
            last = min(now, opened + timedelta(days=rng.randint(1, 4)))
            conn.execute("UPDATE cases SET created_at=?, updated_at=? WHERE id=?",
                         (opened.strftime(TS), last.strftime(TS), c["id"]))

        if _once(conn, "audit_log",
                 {"actor_id": lead, "action": "create_case", "entity": "case",
                  "entity_id": c["id"]},
                 {"detail": c["title"][:120], "created_at": opened.strftime(TS)}):
            stats["audit"] += 1

        # ---- evidence: real ingested keyframes/clips, not invented paths ----
        if videos:
            vid = videos[rank % len(videos)]
            ev_at = opened + timedelta(hours=rng.randint(4, 30))
            for fid, tsec in _frames_for(conn, vid["id"], 2 if will_close else 1):
                if _once(conn, "evidence",
                         {"case_id": c["id"], "kind": "frame", "ref": str(fid)},
                         {"caption": "CCTV keyframe from the ingested clip corpus"
                                     f": {vid['filename']} @ {tsec:.1f}s",
                          "visibility": "team", "added_by": officer,
                          "created_at": ev_at.strftime(TS)}):
                    stats["evidence"] += 1
            if _once(conn, "evidence",
                     {"case_id": c["id"], "kind": "video", "ref": str(vid["id"])},
                     {"caption": "Source clip retained with the case file: "
                                 f"{vid['filename']}",
                      "visibility": "station", "added_by": officer,
                      "created_at": ev_at.strftime(TS)}):
                stats["evidence"] += 1
        if will_close and _once(
                conn, "evidence",
                {"case_id": c["id"], "kind": "note", "ref": None},
                {"caption": _CASE_NOTES.get(c["category"], _DEFAULT_NOTE),
                 "visibility": "citizen", "added_by": officer,
                 "created_at": (opened + timedelta(days=1)).strftime(TS)}):
            stats["evidence"] += 1

        # ---- messages so the case thread is never empty ----
        thread = [
            (officer, "officer", "Statement recorded and footage from the "
                                 "nearest municipal camera requisitioned.",
             opened + timedelta(hours=6)),
            (c["citizen_id"], "citizen", "Thank you. Let me know if you need "
                                         "anything more from my side.",
             opened + timedelta(hours=20)),
        ]
        if will_close:
            thread.append((lead, "lead", "Final report reviewed. Closing the "
                                         "case at station level.", closed_at))
        for sender, role, body, at in thread:
            if sender and _once(conn, "case_messages",
                                {"case_id": c["id"], "body": body},
                                {"sender_id": sender, "sender_role": role,
                                 "created_at": at.strftime(TS)}):
                stats["messages"] += 1

        # ---- citizen rating + the notifications that go with a closure ----
        if will_close and c["citizen_id"]:
            stars, comment = _FEEDBACK[(stats["closed"] - 1) % len(_FEEDBACK)]
            if _once(conn, "ratings", {"case_id": c["id"]},
                     {"citizen_id": c["citizen_id"], "stars": stars,
                      "comment": comment,
                      "created_at": (closed_at + timedelta(hours=5)).strftime(TS)}):
                stats["ratings"] += 1
            if _once(conn, "audit_log",
                     {"actor_id": lead, "action": "close_case", "entity": "case",
                      "entity_id": c["id"]},
                     {"detail": _VERDICTS.get(c["category"],
                                              _DEFAULT_VERDICT)[:120],
                      "created_at": closed_at.strftime(TS)}):
                stats["audit"] += 1
            for uid, ntype, msg in (
                (c["citizen_id"], "case_closed",
                 "Your case has been closed. You may now rate your experience."),
                (officer, "case_closed", f"Case #{c['id']} has been closed."),
            ):
                if uid and _once(conn, "notifications",
                                 {"user_id": uid, "type": ntype,
                                  "case_id": c["id"]},
                                 {"message": msg, "read": 0,
                                  "created_at": closed_at.strftime(TS)}):
                    stats["notifs"] += 1
        elif officer:
            if _once(conn, "notifications",
                     {"user_id": officer, "type": "case_assigned",
                      "case_id": c["id"]},
                     {"message": f"Case #{c['id']} is assigned to you: "
                                 f"{c['title'][:60]}",
                      "read": 0, "created_at": opened.strftime(TS)}):
                stats["notifs"] += 1
    return stats


# --------------------------------------------------------------------------- #
# Self-check: the one runnable assertion set for the logic above
# --------------------------------------------------------------------------- #

def verify(conn) -> None:
    k = read_kpis(conn)
    series = day_series(conn, 14)
    assert k["closed_cases"] >= 1, "no closed cases, CLOSED tile still dead"
    assert k["open_cases"] >= 3, f"only {k['open_cases']} open cases left"
    assert 24 <= k["avg_resolution_hours"] <= 1200, \
        f"avg resolution {k['avg_resolution_hours']}h is not days-scale"
    assert 3.0 <= k["avg_rating"] < 5.0, f"avg rating {k['avg_rating']} implausible"
    assert k["total_evidence"] >= 8, "too little evidence"
    assert k["case_messages"] >= 4, "case threads still thin"
    assert all(n > 0 for _, n in series), \
        f"empty bar(s) in the 14-day chart: {[d for d, n in series if not n]}"
    assert conn.execute("SELECT COUNT(*) FROM complaints "
                        "WHERE created_at > datetime('now')").fetchone()[0] == 0, \
        "future-dated complaints"
    assert conn.execute(
        "SELECT COUNT(*) FROM cases WHERE status='closed' "
        "AND (closed_at <= created_at OR closed_at > datetime('now'))"
    ).fetchone()[0] == 0, "closed_at outside (created_at, now)"
    print("  self-check: all assertions passed")


def _show(label: str, k: dict, series: list[tuple[str, int]]) -> None:
    print(f"\n{label}")
    print(f"  CLOSED {k['closed_cases']}   OPEN {k['open_cases']}   "
          f"AVG RESOLVE {k['avg_resolution_hours']}h   "
          f"AVG RATING {k['avg_rating'] or '-'} ({k['n_ratings']})   "
          f"EVIDENCE {k['total_evidence']}")
    print(f"  messages {k['case_messages']}  notifications {k['notifications']}")
    print("  last 14 days: " + " ".join(f"{d[5:]}:{n}" for d, n in series))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Top up the complaint window to today and fill the dead "
                    "dashboard KPI tiles (idempotent).")
    ap.add_argument("--kpis", action="store_true",
                    help="print the KPIs and the 14-day series, change nothing")
    args = ap.parse_args()

    with get_conn() as conn:
        _show("BEFORE", read_kpis(conn), day_series(conn, 14))
        if args.kpis:
            return 0
        print("\nPolishing...")
        topup_recent_days(conn)
        stats = polish_cases(conn)
        # NB: "closed set" is the whole subset this script owns, not new writes:
        # the case UPDATEs are deterministic, so a re-run rewrites the same rows.
        print(f"  closed set {stats['closed']}, evidence +{stats['evidence']}, "
              f"ratings +{stats['ratings']}, messages +{stats['messages']}, "
              f"notifs +{stats['notifs']}, audit +{stats['audit']}")
        _show("AFTER", read_kpis(conn), day_series(conn, 14))
        verify(conn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
