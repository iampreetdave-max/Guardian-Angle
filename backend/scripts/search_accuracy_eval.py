"""Graded accuracy evaluation for VisionScan semantic search.

Runs a fixed query set against a running backend and scores the results against
hand-verified ground truth, so "does searching 'red car' actually return a red
car?" has a number instead of an opinion.

The ground truth below was established by downloading each clip, extracting
evenly-spaced frames and visually inspecting them — not from stock-site
descriptions. Presence claims are therefore reliable. Absence claims (used for
the hard negatives) hold for the sampled frames, so a "false positive" on a
sparse clip is worth eyeballing before believing it.

Usage (backend must be running and the clips ingested under these camera ids):

    python backend/scripts/search_accuracy_eval.py
    python backend/scripts/search_accuracy_eval.py --base http://localhost:8000
    python backend/scripts/search_accuracy_eval.py --json out.json

Footage: test_clips/real/ (Pexels License). Re-ingest with one camera id per
clip, in the CAMERAS order below.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

# camera id -> clip filename, fixed by ingest order.
CAMERAS = {
    "CAM-01": "cctv_crosswalk_03.mp4",
    "CAM-02": "cctv_overhead_01.mp4",
    "CAM-03": "cctv_overhead_05.mp4",
    "CAM-04": "cctv_overhead_india_04.mp4",
    "CAM-05": "cctv_streetmonitor_02.mp4",
    "CAM-06": "market_bazaar_lucknow_04.mp4",
    "CAM-07": "market_crowded_01.mp4",
    "CAM-08": "market_crowded_02.mp4",
    "CAM-09": "market_crowded_03.mp4",
    "CAM-10": "pedestrian_crossing_01.mp4",
    "CAM-11": "pedestrian_street_02.mp4",
    "CAM-12": "traffic_bus_kolkata_02.mp4",
    "CAM-13": "traffic_motorbike_05.mp4",
    "CAM-14": "traffic_redcar_06.mp4",
    "CAM-15": "traffic_taxi_kolkata_03.mp4",
    "CAM-16": "traffic_truck_highway_04.mp4",
}

# query -> (endpoint, must-appear cameras, must-NOT-appear cameras)
#   "expect"  : the object is verifiably present; missing it is a false negative.
#   "forbid"  : verifiably absent in every sampled frame; returning it is a
#               false positive. Deliberately small — only clips where the class
#               is clearly not present at all.
QUERIES = [
    # ---- colour+type: the headline claim ----
    ("red car", "region", ["CAM-14", "CAM-11", "CAM-04"], ["CAM-07", "CAM-01"]),
    ("white car", "region", ["CAM-11", "CAM-04", "CAM-12"], ["CAM-07"]),
    ("yellow taxi", "region", ["CAM-15", "CAM-12"], ["CAM-01", "CAM-07"]),
    # ---- vehicle classes ----
    ("bus", "region", ["CAM-12", "CAM-03", "CAM-05"], ["CAM-07", "CAM-14"]),
    ("truck", "region", ["CAM-16", "CAM-03", "CAM-11"], ["CAM-01"]),
    ("motorcycle", "region", ["CAM-13", "CAM-08", "CAM-06"], ["CAM-01"]),
    ("auto rickshaw", "region", ["CAM-09", "CAM-04", "CAM-08"], ["CAM-16"]),
    ("bicycle", "region", ["CAM-01", "CAM-04"], []),
    # ---- people ----
    ("person carrying a bag", "region", ["CAM-08", "CAM-12"], []),
    ("pedestrian crossing the street", "text", ["CAM-10", "CAM-01", "CAM-12"], []),
    # ---- scene-level (whole-frame CLIP) ----
    ("crowded market with many people", "text", ["CAM-07", "CAM-09", "CAM-06"], ["CAM-16"]),
    ("busy highway traffic", "text", ["CAM-16"], ["CAM-07"]),
    ("empty street with no people", "text", ["CAM-05"], ["CAM-07"]),
]

# Matches what the UI actually requests for region search (frontend/src/App.jsx),
# and it matters more than it looks: region search returns individual OBJECT
# INSTANCES, not one row per clip. A single clip can hold 40+ matching crops for
# "red car", so a small top_k lets one clip crowd every other camera out of the
# list and understates recall badly.
TOP_K = 60


def _post(base: str, path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        base.rstrip("/") + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def run(base: str) -> dict:
    rows = []
    for query, kind, expect, forbid in QUERIES:
        path = "/api/search/region" if kind == "region" else "/api/search/text"
        try:
            data = _post(base, path, {"query": query, "top_k": TOP_K})
        except urllib.error.URLError as e:
            print(f"  ! {query!r}: request failed: {e}", file=sys.stderr)
            continue

        hits = data.get("hits", [])
        # rank cameras by their best-scoring hit
        best: dict[str, float] = {}
        for h in hits:
            cam = h.get("camera_id")
            if cam and h.get("score", 0) > best.get(cam, -1):
                best[cam] = h["score"]
        returned = sorted(best, key=lambda c: best[c], reverse=True)

        found = [c for c in expect if c in best]
        missed = [c for c in expect if c not in best]
        false_pos = [c for c in forbid if c in best]
        recall = len(found) / len(expect) if expect else None

        rows.append({
            "query": query,
            "endpoint": kind,
            "n_hits": len(hits),
            "cameras_returned": returned,
            "top_camera": returned[0] if returned else None,
            "top_clip": CAMERAS.get(returned[0]) if returned else None,
            "top_score": round(best[returned[0]], 4) if returned else None,
            "expected": expect,
            "found": found,
            "missed": missed,
            "false_positives": false_pos,
            "recall": recall,
            "top1_correct": bool(returned) and returned[0] in expect,
        })
    return {"base": base, "top_k": TOP_K, "results": rows}


def report(out: dict) -> int:
    rows = out["results"]
    print(f"\n{'QUERY':<34} {'HITS':>5} {'REC':>6} {'TOP1':>5}  TOP RESULT")
    print("-" * 104)
    for r in rows:
        rec = "  n/a" if r["recall"] is None else f"{r['recall']*100:5.0f}%"
        top1 = " OK " if r["top1_correct"] else " -- "
        clip = r["top_clip"] or "(nothing returned)"
        score = f"{r['top_score']:.3f}" if r["top_score"] is not None else "  -  "
        print(f"{r['query']:<34} {r['n_hits']:>5} {rec} {top1}  {clip}  [{score}]")

    graded = [r for r in rows if r["recall"] is not None]
    macro = sum(r["recall"] for r in graded) / len(graded) if graded else 0.0
    top1 = sum(1 for r in rows if r["top1_correct"]) / len(rows) if rows else 0.0
    fp = sum(len(r["false_positives"]) for r in rows)
    empties = [r["query"] for r in rows if r["n_hits"] == 0]

    print("-" * 104)
    print(f"macro recall@{TOP_K}: {macro*100:.1f}%   top-1 accuracy: {top1*100:.1f}%   "
          f"false positives on forbidden clips: {fp}")
    if empties:
        print(f"queries returning NOTHING ({len(empties)}): {', '.join(empties)}")

    print("\nPer-query misses:")
    for r in rows:
        if r["missed"] or r["false_positives"]:
            miss = ", ".join(f"{c}={CAMERAS[c]}" for c in r["missed"])
            fps = ", ".join(f"{c}={CAMERAS[c]}" for c in r["false_positives"])
            print(f"  {r['query']!r}")
            if miss:
                print(f"      MISSED: {miss}")
            if fps:
                print(f"      FALSE+: {fps}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--json", help="also write raw results here")
    a = ap.parse_args()

    out = run(a.base)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"raw results -> {a.json}")
    return report(out)


if __name__ == "__main__":
    raise SystemExit(main())
