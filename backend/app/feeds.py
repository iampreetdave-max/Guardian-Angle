"""Catalog of public, click-to-load live feeds.

VisionScan ships with a small set of *intentionally public* streams so the tool
demonstrates itself out of the box — an investigator can load a feed in one
click instead of hunting for a URL. The catalog is editable: drop a
`public_feeds.json` (a JSON list with the same fields) into the data directory
to override/extend it without touching code — e.g. paste a pre-tested local
Gujarat traffic-camera URL before demo day.

ETHICS: only list feeds that are deliberately published for public viewing
(govt/traffic cameras, public test streams, public webcams). Never list
unsecured/private cameras — accessing those without authorization is illegal.

The bundled defaults are verified-public HLS streams. The two "Demo" entries
contain real people/objects (good for exercising object & semantic search); the
"Live" entry is a continuous 24/7 stream that shows true live-capture behaviour.
Swap in local CCTV/traffic feeds for an investigation-realistic demo.
"""
from __future__ import annotations

import json
import logging

from .config import get_settings

log = logging.getLogger("visionscan.feeds")

DEFAULT_FEEDS: list[dict] = [
    {
        "id": "demo-bipbop",
        "name": "Public Demo Stream",
        "location": "HLS test feed - people & street scenes",
        "category": "Demo",
        "url": "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
        "note": "Reliable public HLS - good for testing natural-language search.",
        "verified": True,
    },
    {
        "id": "demo-tears",
        "name": "Public Demo Stream (objects)",
        "location": "HLS test feed - people, vehicles, objects",
        "category": "Demo",
        "url": "https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8",
        "note": "Rich scenes - good for exercising YOLO object detection.",
        "verified": True,
    },
    {
        "id": "live-akamai",
        "name": "Continuous Live Feed",
        "location": "24/7 live HLS stream",
        "category": "Live",
        "url": "https://moctobpltc-i.akamaihd.net/hls/live/571329/eight/playlist.m3u8",
        "note": "Always-on live stream - demonstrates real-time capture.",
        "verified": True,
    },
]


def load_feeds() -> list[dict]:
    """Return the feed catalog: bundled defaults plus any user override file."""
    settings = get_settings()
    override = settings.data_dir / "public_feeds.json"
    if override.exists():
        try:
            data = json.loads(override.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                log.info("Loaded %d feeds from %s", len(data), override)
                return data
        except Exception as e:  # pragma: no cover
            log.warning("Could not parse %s, using defaults: %s", override, e)
    return DEFAULT_FEEDS
