"""Free, no-key live data layer — government RSS/Atom feed connectors.

The legal/gov data ecosystem has no free keyless JSON API, but several
government bodies publish open RSS/Atom feeds (press releases, notifications)
that need no key and can be polled on a schedule. This module fetches and
normalises them with the Python standard library only (urllib + ElementTree) —
no new pip dependency.

Robustness is the whole point: each feed is fetched in its own try/except with a
browser User-Agent and a short timeout. A 403, a moved URL, a network failure or
a parse error simply yields an empty list for that feed and is logged at debug —
it never raises, so refresh() always succeeds and the bundled corpus is never at
risk. Feeds are best-effort enrichment, not a hard dependency.
"""
from __future__ import annotations

import hashlib
import logging
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from ..config import get_settings
from . import categorize

log = logging.getLogger("visionscan.govintel.sources")

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Registry of free, keyless government feeds. Each carries default metadata used
# when the feed item itself doesn't specify it. URLs are best-effort; if one is
# down or blocks us it is skipped. Toggle the whole layer with VISIONSCAN_GOVINTEL_*.
FEEDS: list[dict] = [
    {
        "key": "pib_all",
        "name": "Press Information Bureau — All releases",
        "url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=0",
        "doc_type": "Notification",
        "department": "Press Information Bureau",
        "ministry": "Government of India",
        "region": "central",
    },
    {
        "key": "pib_gujarat",
        "name": "Press Information Bureau — Gujarat (Ahmedabad)",
        "url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3",
        "doc_type": "Notification",
        "department": "Press Information Bureau, Ahmedabad",
        "ministry": "Government of India",
        "region": "gujarat",
    },
    {
        "key": "rbi_notifications",
        "name": "Reserve Bank of India — Notifications",
        "url": "https://www.rbi.org.in/Scripts/Rss.aspx?cat_id=1",
        "doc_type": "Circular",
        "department": "Reserve Bank of India",
        "ministry": "Reserve Bank of India",
        "region": "central",
    },
    {
        "key": "rbi_press",
        "name": "Reserve Bank of India — Press Releases",
        "url": "https://www.rbi.org.in/Scripts/Rss.aspx?cat_id=2",
        "doc_type": "Notification",
        "department": "Reserve Bank of India",
        "ministry": "Reserve Bank of India",
        "region": "central",
    },
]

# RSS/Atom namespaces we may encounter
_ATOM = "{http://www.w3.org/2005/Atom}"


def _text(el) -> str:
    return (el.text or "").strip() if el is not None else ""


def _clean(html: str) -> str:
    """Strip tags/entities from an RSS description into plain text."""
    import html as _h
    import re

    txt = re.sub(r"<[^>]+>", " ", html or "")
    txt = _h.unescape(txt)
    return re.sub(r"\s+", " ", txt).strip()


def _parse_date(raw: str) -> str:
    """Best-effort RSS/Atom date -> ISO date (YYYY-MM-DD). Falls back to today."""
    raw = (raw or "").strip()
    fmts = (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%d %b %Y",
        "%Y-%m-%d",
    )
    for f in fmts:
        try:
            return datetime.strptime(raw, f).date().isoformat()
        except (ValueError, TypeError):
            continue
    return datetime.now(timezone.utc).date().isoformat()


def _doc_id(feed_key: str, link: str, title: str) -> str:
    h = hashlib.sha1(f"{link}|{title}".encode("utf-8")).hexdigest()[:16]
    return f"live-{feed_key}-{h}"


def _items_from_xml(root) -> list:
    """Return the list of item/entry elements for either RSS or Atom."""
    items = root.findall(".//item")
    if items:
        return items
    return root.findall(f".//{_ATOM}entry")


def _normalise_item(item, feed: dict) -> dict | None:
    is_atom = item.tag.endswith("entry")
    if is_atom:
        title = _text(item.find(f"{_ATOM}title"))
        link_el = item.find(f"{_ATOM}link")
        link = (link_el.get("href") if link_el is not None else "") or ""
        desc = _text(item.find(f"{_ATOM}summary")) or _text(item.find(f"{_ATOM}content"))
        pub = _text(item.find(f"{_ATOM}updated")) or _text(item.find(f"{_ATOM}published"))
    else:
        title = _text(item.find("title"))
        link = _text(item.find("link"))
        desc = _text(item.find("description"))
        pub = _text(item.find("pubDate"))

    title = _clean(title)
    if not title:
        return None
    body = _clean(desc)
    region = categorize.guess_region(title, body, default=feed.get("region", "central"))
    dept = categorize.guess_department(title, body, default=feed.get("department", ""))
    doc_type = feed.get("doc_type") or categorize.classify(title, body)

    return {
        "id": _doc_id(feed["key"], link, title),
        "title": title[:300],
        "doc_type": doc_type,
        "department": dept,
        "ministry": feed.get("ministry", ""),
        "region": region,
        "date": _parse_date(pub),
        "summary": body[:600],
        "body": body,
        "keywords": categorize.extract_keywords(title, body),
        "source_url": link or feed["url"],
        "language": "en",
        "origin": "live",
    }


def fetch_feed(feed: dict, timeout: int) -> list[dict]:
    """Fetch & normalise one feed. Never raises — returns [] on any failure."""
    try:
        req = urllib.request.Request(feed["url"], headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        root = ET.fromstring(raw)
        out = []
        for item in _items_from_xml(root):
            try:
                doc = _normalise_item(item, feed)
                if doc:
                    out.append(doc)
            except Exception:  # pragma: no cover - per-item resilience
                continue
        log.info("GovIntel feed %s: %d items", feed["key"], len(out))
        return out
    except Exception as e:  # pragma: no cover - per-feed resilience
        log.debug("GovIntel feed %s unavailable: %s", feed["key"], e)
        return []


def fetch_all() -> list[dict]:
    """Poll every configured feed. Best-effort; unavailable feeds are skipped."""
    settings = get_settings()
    if not getattr(settings, "govintel_enable", True):
        return []
    timeout = getattr(settings, "govintel_feed_timeout", 6)
    docs: list[dict] = []
    seen: set[str] = set()
    for feed in FEEDS:
        for doc in fetch_feed(feed, timeout):
            if doc["id"] in seen:
                continue
            seen.add(doc["id"])
            docs.append(doc)
    return docs


def feed_catalog() -> list[dict]:
    return [{"key": f["key"], "name": f["name"], "region": f["region"],
             "doc_type": f["doc_type"]} for f in FEEDS]
