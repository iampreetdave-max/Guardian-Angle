"""Click through every module in a real browser and report what actually renders.

Answers "is everything working?" with evidence rather than HTTP 200s. Several of
the defects found on 2026-08-15 returned 200 from every endpoint while the UI was
empty or stuck on a spinner, so an API-level smoke test would have passed all of
them.

For each role it logs in, visits every nav tab, waits for the tab to settle, and
records: uncaught page errors, console errors, failed network requests, whether a
loading spinner is still on screen, and a screenshot.

Usage (needs the stack running; Playwright + chromium already installed):

    python backend/scripts/ui_smoketest.py
    python backend/scripts/ui_smoketest.py --url http://localhost:8080 --role admin
    python backend/scripts/ui_smoketest.py --headed          # watch it run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Nav keys/labels come from frontend/src/App.jsx. `staff` tabs need officer+;
# Admin needs admin. Citizen sees only the citizen portal.
TABS_BY_ROLE = {
    "admin": ["Dashboard", "VisionScan", "Live Alerts", "City Map", "Arbiter",
              "CrimeGPT", "Legal Feed", "Cases", "Complaints", "Admin"],
    "lead": ["Dashboard", "VisionScan", "Live Alerts", "City Map", "Arbiter",
             "CrimeGPT", "Legal Feed", "Cases", "Complaints"],
    "officer": ["Dashboard", "VisionScan", "Live Alerts", "City Map", "Arbiter",
                "CrimeGPT", "Legal Feed", "Cases", "Complaints"],
    "citizen": ["Legal Feed", "Cases", "Complaints"],
}

CREDS = {
    "admin": ("admin@city.gov", "admin123"),
    "lead": ("lead@city.gov", "lead123"),
    "officer": ("officer@city.gov", "officer123"),
    "citizen": ("citizen@example.com", "citizen123"),
}

# Noise that is not a real defect.
IGNORE_CONSOLE = (
    "favicon",
    "Download the React DevTools",
    "chunks are larger than",
)


def _interesting(text: str) -> bool:
    return not any(n.lower() in text.lower() for n in IGNORE_CONSOLE)


def run_role(pw, base: str, role: str, outdir: Path, headed: bool) -> list[dict]:
    from playwright.sync_api import TimeoutError as PWTimeout

    email, password = CREDS[role]
    browser = pw.chromium.launch(headless=not headed)
    ctx = browser.new_context(viewport={"width": 1600, "height": 1000})
    page = ctx.new_page()

    page_errors: list[str] = []
    console_errors: list[str] = []
    failed_requests: list[str] = []
    page.on("pageerror", lambda e: page_errors.append(str(e)[:300]))
    page.on("console", lambda m: (
        console_errors.append(f"{m.type}: {m.text[:250]}")
        if m.type in ("error",) and _interesting(m.text) else None))
    page.on("requestfailed", lambda r: failed_requests.append(
        f"{r.method} {r.url[:120]} :: {r.failure}"))
    page.on("response", lambda r: failed_requests.append(
        f"HTTP {r.status} {r.request.method} {r.url[:120]}")
        if r.status >= 400 and "/api/" in r.url else None)

    results: list[dict] = []
    try:
        page.goto(base, wait_until="domcontentloaded", timeout=60_000)
        page.fill('input[type="email"]', email)
        page.fill('input[type="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_timeout(4000)

        logged_in = "sign in" not in (page.content()[:4000] or "").lower()
        results.append({"role": role, "tab": "(login)", "ok": logged_in,
                        "page_errors": list(page_errors),
                        "console_errors": list(console_errors),
                        "failed_requests": list(failed_requests)})
        if not logged_in:
            return results

        for tab in TABS_BY_ROLE[role]:
            page_errors.clear(); console_errors.clear(); failed_requests.clear()
            entry: dict = {"role": role, "tab": tab}
            try:
                page.get_by_text(tab, exact=True).first.click(timeout=15_000)
            except PWTimeout:
                entry.update(ok=False, note="nav item not found/clickable")
                results.append(entry)
                continue

            # Let data load. These panels poll, so a fixed settle beats
            # networkidle (which never fires with a 5s poll running).
            page.wait_for_timeout(6000)

            body = page.inner_text("body")[:6000]
            spinning = page.locator(".animate-spin").count()
            shot = outdir / f"{role}_{tab.replace(' ', '_').lower()}.png"
            page.screenshot(path=str(shot), full_page=False)

            entry.update(
                ok=not page_errors,
                still_spinning=spinning,
                chars_rendered=len(body.strip()),
                page_errors=list(page_errors),
                console_errors=list(console_errors),
                failed_requests=list(failed_requests),
                screenshot=str(shot),
            )
            results.append(entry)
    finally:
        ctx.close()
        browser.close()
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--role", action="append",
                    help="repeatable; default = all four demo roles")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--out", default="docs/assets/uiqa")
    a = ap.parse_args()

    roles = a.role or list(CREDS)
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright

    all_results: list[dict] = []
    with sync_playwright() as pw:
        for role in roles:
            print(f"\n=== {role} ===")
            for r in run_role(pw, a.url, role, outdir, a.headed):
                all_results.append(r)
                flag = "OK " if r.get("ok") else "FAIL"
                extra = []
                if r.get("still_spinning"):
                    extra.append(f"spinner x{r['still_spinning']}")
                if r.get("chars_rendered", 1) < 200:
                    extra.append(f"only {r.get('chars_rendered')} chars")
                for k in ("page_errors", "console_errors", "failed_requests"):
                    if r.get(k):
                        extra.append(f"{k}={len(r[k])}")
                print(f"  [{flag}] {r['tab']:<12} {' | '.join(extra)}")
                for k in ("page_errors", "console_errors", "failed_requests"):
                    for item in (r.get(k) or [])[:4]:
                        print(f"        {k[:-1]}: {item}")

    report = outdir / "ui_smoketest.json"
    report.write_text(json.dumps(all_results, indent=2), encoding="utf-8")

    bad = [r for r in all_results
           if not r.get("ok") or r.get("page_errors") or r.get("failed_requests")]
    print(f"\n{'=' * 64}")
    print(f"{len(all_results) - len(bad)}/{len(all_results)} tab loads clean · "
          f"report -> {report}")
    if bad:
        print("Needs attention:")
        for r in bad:
            print(f"  {r['role']}/{r['tab']}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
