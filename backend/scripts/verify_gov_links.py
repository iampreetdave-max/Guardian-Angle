"""Check every source_url in the bundled GovIntel corpus still resolves.

Link rot in the Legal Feed is a credibility hit: a judge clicks "Right to
Information Act" and gets a 404. Run this before any demo (or from CI):

    python backend/scripts/verify_gov_links.py            # host
    docker compose exec -T backend sh -c "cd /app && PYTHONPATH=. python scripts/verify_gov_links.py"

Exit code is 1 if any URL 404s (or is otherwise dead), 0 otherwise. 403 is
reported but tolerated: several government sites (incometaxindia.gov.in,
rbidocs) bot-block non-browser clients while working fine in a browser.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[1] / "app" / "govintel" / "corpus" / "gov_corpus.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
TIMEOUT = 25
# Dead: hard 404/410, or no answer at all (000 = DNS/TLS/timeout).
FAIL = {0, 404, 410}


def check(url: str) -> tuple[int, str]:
    """(status, note). GET, not HEAD, because several gov sites 405 on HEAD."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.reason or ""
    except Exception as e:  # URLError, socket timeout, bad TLS, ...
        return 0, type(e).__name__


def main() -> int:
    docs = json.loads(CORPUS.read_text(encoding="utf-8"))
    rows = [(d["id"], d.get("source_url") or "") for d in docs]

    # ponytail: 8 threads is plenty for ~35 links; no retry/backoff until a
    # flaky site actually makes this noisy.
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda r: check(r[1]) if r[1] else (0, "no url"), rows))

    width = max(len(i) for i, _ in rows)
    dead = []
    for (doc_id, url), (status, note) in zip(rows, results):
        flag = "DEAD" if status in FAIL else ("warn" if status >= 400 else "ok")
        if status in FAIL:
            dead.append((doc_id, url, status, note))
        print(f"{status or '000':>3}  {flag:<4}  {doc_id:<{width}}  {url}"
              + (f"   [{note}]" if note else ""))

    print(f"\n{len(rows)} links checked, {len(dead)} dead")
    for doc_id, url, status, note in dead:
        print(f"  DEAD {status or '000'} {doc_id}: {url} {note}")
    return 1 if dead else 0


if __name__ == "__main__":
    sys.exit(main())
