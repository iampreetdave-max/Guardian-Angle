"""End-to-end face-matching self-test (run inside the Docker backend container).

Uses a real face image bundled with insightface, builds a short clip from it,
ingests it through the full pipeline (so ArcFace detects + embeds the face),
then runs a face search with the same image. A high-scoring self-match proves
detection -> embedding -> face FAISS index -> search all work.
"""
from __future__ import annotations

import os
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from pathlib import Path

import cv2
import insightface

from app.config import get_settings
from app.database import get_conn, init_db
from app.services.pipeline import process_video
from app.core import query_router as qr


def main() -> None:
    pkg = Path(insightface.__file__).parent
    candidates = sorted((pkg / "data" / "images").glob("*.jpg")) + \
        sorted((pkg / "data" / "images").glob("*.png"))
    print("bundled sample images:", [c.name for c in candidates])

    # prefer a clear single-face portrait
    chosen = next((c for c in candidates if "Tom" in c.name or c.name == "t1.jpg"),
                  candidates[0])
    face_img = cv2.imread(str(chosen))
    print(f"using reference image: {chosen.name} {face_img.shape}")

    s = get_settings()
    init_db()
    out = Path(s.data_dir) / "face_test.mp4"
    h, w = face_img.shape[:2]
    vw = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"), 10, (w, h))
    for i in range(30):  # slight brightness changes -> trigger keyframes
        vw.write(cv2.convertScaleAbs(face_img, alpha=1.0, beta=(i % 5) * 5))
    vw.release()
    print(f"wrote test clip: {out}")

    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO videos (filename, path, camera_id, status) "
            "VALUES (?, ?, ?, 'pending')",
            ("face_test.mp4", str(out), "CAM-FACE"),
        )
        vid = cur.lastrowid
    process_video(vid)

    with get_conn() as c:
        n_frames = c.execute(
            "SELECT COUNT(*) FROM frames WHERE video_id=?", (vid,)
        ).fetchone()[0]
        n_faces = c.execute("SELECT COUNT(*) FROM faces").fetchone()[0]
    print(f"\nINGEST: frames={n_frames}  faces_detected={n_faces}")

    hits = qr.search_face(face_img, top_k=5, group=False)
    print(f"FACE SEARCH: {len(hits)} hit(s)")
    for hh in hits:
        print(f"  score={hh.score:.3f}  frame={hh.frame_id}  t={hh.timestamp_hms}")

    if n_faces > 0 and hits and hits[0].score > 0.5:
        print("\nRESULT: PASS - ArcFace detected and self-matched the face.")
    else:
        print("\nRESULT: CHECK - see counts above.")


if __name__ == "__main__":
    main()
