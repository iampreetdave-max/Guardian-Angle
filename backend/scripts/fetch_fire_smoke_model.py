"""Download a pretrained fire/smoke YOLO model so the anomaly watch can draw
localized boxes (red = fire, amber = smoke) instead of only CLIP whole-frame
scores.

CLIP tells us a frame *contains* fire; it cannot say *where*. A YOLO model
trained on fire/smoke outputs the box coordinates the Live Alerts overlay
renders. The anomaly layer (core/anomaly.py) loads whatever .pt you point
VISIONSCAN_ANOMALY_SPECIALIZED_WEIGHTS at and reads its class names directly,
so any fire/smoke YOLOv8+/YOLOv10 model works.

Usage:
    python -m backend.scripts.fetch_fire_smoke_model
    python -m backend.scripts.fetch_fire_smoke_model --url <hf-resolve-url>

After it finishes, set the env var it prints (add to backend/.env) and restart:
    VISIONSCAN_ANOMALY_SPECIALIZED_WEIGHTS=backend/models/fire_smoke_yolo.pt
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

# Confirmed-present pretrained fire/smoke weights (Ultralytics-loadable .pt,
# classes: fire, smoke). Override with --url for your own model.
DEFAULT_URL = (
    "https://huggingface.co/TommyNgx/YOLOv10-Fire-and-Smoke-Detection"
    "/resolve/main/best.pt"
)

DEST = Path(__file__).resolve().parents[2] / "backend" / "models" / "fire_smoke_yolo.pt"


def _progress(done: int, total: int) -> None:
    if total <= 0:
        return
    pct = min(100, int(done * 100 / total))
    mb = done / 1_048_576
    sys.stdout.write(f"\r  downloading… {pct:3d}%  ({mb:6.1f} MB)")
    sys.stdout.flush()


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch a fire/smoke YOLO model.")
    ap.add_argument("--url", default=DEFAULT_URL, help="direct .pt download URL")
    ap.add_argument("--dest", default=str(DEST), help="where to save the weights")
    ap.add_argument("--force", action="store_true", help="re-download if present")
    args = ap.parse_args()

    dest = Path(args.dest)
    if dest.exists() and not args.force:
        print(f"Already present: {dest}  (use --force to re-download)")
        _print_next_steps(dest)
        return 0

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Fetching {args.url}")
    try:
        with urllib.request.urlopen(args.url) as resp:  # noqa: S310 (trusted URL)
            total = int(resp.headers.get("Content-Length", 0))
            done = 0
            tmp = dest.with_suffix(".part")
            with open(tmp, "wb") as f:
                while chunk := resp.read(1 << 16):
                    f.write(chunk)
                    done += len(chunk)
                    _progress(done, total)
            tmp.replace(dest)
        print(f"\nSaved {dest}  ({dest.stat().st_size / 1_048_576:.1f} MB)")
    except Exception as e:  # noqa: BLE001
        print(f"\nDownload failed: {e}", file=sys.stderr)
        print("Pass your own model with --url <direct .pt link>.", file=sys.stderr)
        return 1

    _print_next_steps(dest)
    return 0


def _print_next_steps(dest: Path) -> None:
    rel = dest.as_posix()
    print("\nNext steps:")
    print("  1. Ensure ultralytics is installed:  pip install ultralytics")
    print(f"  2. Add to backend/.env:  VISIONSCAN_ANOMALY_SPECIALIZED_WEIGHTS={rel}")
    print("  3. Restart the backend. Fire/smoke alerts will now carry a box.")


if __name__ == "__main__":
    raise SystemExit(main())
