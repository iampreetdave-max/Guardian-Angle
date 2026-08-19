"""Zone-occupancy and line-crossing endpoints. Owned by the zones pass.

Both routes read only what the ingest pipeline already stored, so they are
cheap and cannot disturb detection. All coordinates in and out are 0..1
fractions of the frame, matching the `match_bbox` convention.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..core.zones import line_crossings, zone_analytics
from ..platform.security import auth_gate

router = APIRouter(tags=["analytics"])


class ZoneRequest(BaseModel):
    polygon: list[list[float]]
    labels: list[str] | None = None


class LineRequest(BaseModel):
    line: list[list[float]]
    labels: list[str] | None = None


def _bad(msg: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, msg)


def _points(raw: list[list[float]], what: str) -> list[tuple[float, float]]:
    """Validate a list of normalised points; raises 400 with a clear message."""
    pts = []
    for p in raw:
        if len(p) != 2:
            raise _bad(f"{what}: each point must be [x, y]")
        if not all(0.0 <= c <= 1.0 for c in p):
            raise _bad(
                f"{what}: coordinates must be 0..1 fractions of the frame, "
                f"got {p}"
            )
        pts.append((float(p[0]), float(p[1])))
    return pts


@router.post("/videos/{video_id}/zone-analytics")
def post_zone_analytics(video_id: int, body: ZoneRequest,
                        _user: dict | None = Depends(auth_gate)) -> dict:
    """Occupancy of a polygon over time (bottom-centre of each box counts)."""
    pts = _points(body.polygon, "polygon")
    if len(pts) < 3:
        raise _bad("polygon needs at least 3 points")
    # Shoelace: a zero-area polygon (all points collinear or duplicated) can
    # never contain anything, so say so instead of returning a silent zero.
    area = abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2)
                   in zip(pts, pts[1:] + pts[:1]))) / 2.0
    if area < 1e-9:
        raise _bad("polygon is degenerate (zero area)")
    return zone_analytics(video_id, body.polygon, body.labels)


@router.post("/videos/{video_id}/line-crossings")
def post_line_crossings(video_id: int, body: LineRequest,
                        _user: dict | None = Depends(auth_gate)) -> dict:
    """Directional crossing counts for a line segment. Needs track ids."""
    pts = _points(body.line, "line")
    if len(pts) != 2:
        raise _bad("line needs exactly 2 points")
    if pts[0] == pts[1]:
        raise _bad("line needs 2 distinct points")
    return line_crossings(video_id, body.line, body.labels)
