"""Object-tracking endpoints. Implementation owned by the tracking pass."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..core.tracking import assign_tracks, track_summary
from ..database import get_conn
from ..platform.security import auth_gate

router = APIRouter(tags=["analytics"])


@router.get("/videos/{video_id}/tracks")
def video_tracks(video_id: int, _user: dict | None = Depends(auth_gate)) -> dict:
    """Distinct objects and their paths for one video.

    Tracks are computed on first request and persisted, so the second call is a
    plain read. Re-running is safe (`assign_tracks` is idempotent) but pointless.
    """
    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM videos WHERE id = ?", (video_id,)).fetchone() is None:
            raise HTTPException(404, "Video not found")
        tracked = conn.execute(
            "SELECT COUNT(*) n FROM detections d JOIN frames f ON f.id = d.frame_id "
            "WHERE f.video_id = ? AND d.track_id IS NOT NULL", (video_id,)
        ).fetchone()["n"]
    if not tracked:
        # ponytail: a video with zero detections re-runs this on every request.
        # It is two indexed COUNTs against nothing; add a "tracked_at" stamp only
        # if that ever shows up in a profile.
        assign_tracks(video_id)
    return track_summary(video_id)
