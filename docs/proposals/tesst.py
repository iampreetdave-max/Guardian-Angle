#!/usr/bin/env python3
"""
Supabase RLS audit for project jpjrhpagjevjkfezgnve (agilitylms.tech).

Compares what each identity can read:
  SERVICE = ground truth (service_role bypasses RLS)
  AUTH    = a logged-in user (your access_token)
  ANON    = the public (anon key)
Plus an optional definitive catalog check (pg_class + policies) if DB_URL is set.

--------------------------------------------------------------------------------
RUN IT (PowerShell) — fill in whichever keys you have, then run:

  $env:SUPABASE_USER_TOKEN  = "<access_token from sb-...-auth-token in localStorage>"
  $env:SUPABASE_SERVICE_KEY = "<service_role key>"      # optional: adds the truth column
  $env:DB_URL = "postgresql://postgres.jpjrhpagjevjkfezgnve:<DB_PW>@aws-0-<region>.pooler.supabase.com:6543/postgres"  # optional: Part B
  pip install requests "psycopg[binary]"
  python C:\\Users\\PREET\\Downloads\\rls_audit.py

The user access_token expires ~1 hour after login — grab a fresh one if AUTH shows "rejected".
--------------------------------------------------------------------------------
"""
import os
import requests

# --- Project config (public values, pre-filled from scan.txt) ---
SUPABASE_URL = "https://jpjrhpagjevjkfezgnve.supabase.co"
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpwanJocGFnamV2amtmZXpnbnZlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg0MzQxMDAsImV4cCI6MjA5NDAxMDEwMH0."
    "hV90FeXDE55DnrfT7tSy4I-8H8cCKXuF66reGqexm30"
)

# --- Secrets (from environment — never hardcode these) ---
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
USER_TOKEN = os.environ.get("SUPABASE_USER_TOKEN", "")
DB_URL = os.environ.get("DB_URL", "")
# If DB_URL isn't set, supply DB_PASSWORD (raw, un-encoded) and the script
# will sweep every Supabase region to find the right pooler host for you.
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
PROJECT_REF = "jpjrhpagjevjkfezgnve"

SUPABASE_REGIONS = [
    "ap-south-1", "ap-southeast-1", "ap-southeast-2",
    "ap-northeast-1", "ap-northeast-2",
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "ca-central-1", "sa-east-1",
    "eu-west-1", "eu-west-2", "eu-west-3",
    "eu-central-1", "eu-central-2", "eu-north-1",
]

REST = f"{SUPABASE_URL}/rest/v1"
ANON_HEADERS = {"apikey": ANON_KEY, "Authorization": f"Bearer {ANON_KEY}"}
SERVICE_HEADERS = {"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}"}
AUTH_HEADERS = {"apikey": ANON_KEY, "Authorization": f"Bearer {USER_TOKEN}"}

CANDIDATE_TABLES = [
    # generic
    "users", "profiles", "accounts", "roles", "role", "permissions",
    # HR / employee portal guesses
    "employees", "employee", "leaves", "leave", "leave_requests", "leave_balance",
    "bonus", "bonuses", "salary", "salaries", "payroll", "attendance",
    "work_from_home", "wfh", "wfh_requests", "departments", "teams",
    "holidays", "timesheets", "documents", "announcements", "notifications",
    # LMS guesses
    "courses", "course", "lessons", "modules", "enrollments", "progress",
    "certificates", "quizzes", "submissions", "grades",
    # original
    "reports", "recent_reports", "bids", "bidding_optimization", "campaigns",
]


# ----------------------------- PART A: REST behavioral ----------------------------
def list_tables_rest():
    """Real table list from the OpenAPI spec (root requires service_role)."""
    if not SERVICE_KEY:
        return []
    r = requests.get(f"{REST}/", headers=SERVICE_HEADERS, timeout=15)
    if r.status_code != 200:
        print(f"  (table discovery failed: HTTP {r.status_code} {r.text[:80]})")
        return []
    spec = r.json()
    return sorted(p.lstrip("/") for p in spec.get("paths", {})
                  if p != "/" and not p.startswith("/rpc/"))


def exact_count(table, headers):
    """(state, count): 'ok'+int | 'missing' | 'denied' | 'error'. Reads Content-Range total."""
    if not headers.get("apikey") or "Bearer " == headers.get("Authorization"):
        return "nokey", None
    if headers["Authorization"] == "Bearer ":
        return "nokey", None
    r = requests.get(
        f"{REST}/{table}",
        headers={**headers, "Range": "0-0", "Prefer": "count=exact"},
        params={"select": "*"},
        timeout=15,
    )
    if r.status_code in (200, 206):
        cr = r.headers.get("Content-Range", "")  # "0-0/42" or "*/0"
        total = cr.split("/")[-1] if "/" in cr else "0"
        try:
            return "ok", int(total)
        except ValueError:
            return "ok", 0
    if r.status_code == 404:
        return "missing", None
    if r.status_code in (401, 403):
        return "denied", None
    return "error", r.status_code


def verdict(svc, auth, anon):
    svc_state, svc_n = svc
    auth_state, auth_n = auth
    anon_state, anon_n = anon

    if svc_state == "missing" or (svc_state != "ok" and auth_state == "missing"):
        return "table does not exist"
    if anon_state == "ok" and anon_n > 0:
        denom = f"/{svc_n}" if svc_state == "ok" else ""
        return f"!! PUBLIC LEAK — anon sees {anon_n}{denom} rows"
    if auth_state == "denied":
        return "auth token rejected (expired? grab a fresh one)"
    if auth_state == "ok" and svc_state == "ok":
        if svc_n == 0:
            return "empty table"
        if auth_n >= svc_n and svc_n > 1:
            return f"!! CHECK — authed user sees ALL {svc_n} rows (cross-user leak?)"
        if auth_n == 0:
            return f"SAFE — user sees 0 of {svc_n} rows"
        return f"scoped — user sees {auth_n}/{svc_n} rows (RLS filtering)"
    if auth_state == "ok":
        return f"authed user reads {auth_n} rows (no truth to compare)"
    return "anon/auth see nothing"


def part_a():
    print("=" * 100)
    print("PART A — REST behavioral (SERVICE = truth | AUTH = logged-in user | ANON = public)")
    print("=" * 100)
    print(f"service_role: {'yes' if SERVICE_KEY else 'no'} | "
          f"anon key: {'yes' if ANON_KEY else 'no'} | "
          f"user token: {'yes' if USER_TOKEN else 'no'}\n")

    tables = list_tables_rest()
    if not tables:
        print(f"Falling back to {len(CANDIDATE_TABLES)} guessed table names.\n")
        tables = CANDIDATE_TABLES

    print(f"{'TABLE':<28} {'SERVICE':>8} {'AUTH':>6} {'ANON':>6}   VERDICT")
    print("-" * 100)
    flagged = []
    for t in tables:
        svc = exact_count(t, SERVICE_HEADERS)
        auth = exact_count(t, AUTH_HEADERS) if USER_TOKEN else ("nokey", None)
        anon = exact_count(t, ANON_HEADERS)
        v = verdict(svc, auth, anon)
        disp = lambda r: r[1] if r[0] == "ok" else r[0]
        print(f"{t:<28} {str(disp(svc)):>8} {str(disp(auth)):>6} {str(disp(anon)):>6}   {v}")
        if v.startswith("!!"):
            flagged.append(t)

    print()
    if flagged:
        print(f"=> {len(flagged)} table(s) need review: {flagged}")
    else:
        print("=> No public leaks or obvious cross-user exposure detected via REST.")
    return flagged


# ----------------------------- PART B: catalog (definitive) -----------------------
RLS_QUERY = """
select c.relname, c.relrowsecurity, c.relforcerowsecurity, coalesce(p.cnt, 0)
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
left join (select schemaname, tablename, count(*) cnt from pg_policies group by 1, 2) p
  on p.schemaname = n.nspname and p.tablename = c.relname
where c.relkind = 'r' and n.nspname = 'public'
order by c.relname;
"""
POLICY_QUERY = """
select tablename, policyname, cmd, roles, qual, with_check
from pg_policies where schemaname = 'public' order by tablename, policyname;
"""


def find_connection(psycopg):
    """Return a working connection string. Use DB_URL if given; else sweep regions."""
    from urllib.parse import quote
    # 1) explicit DB_URL wins
    if DB_URL:
        return DB_URL
    if not DB_PASSWORD:
        return None

    pw = quote(DB_PASSWORD, safe="")  # URL-encode @, /, etc. for you
    print(f"Sweeping {len(SUPABASE_REGIONS)} regions x 2 pooler prefixes "
          f"to find the right host...\n")
    for region in SUPABASE_REGIONS:
        for prefix in ("aws-0", "aws-1"):
            host = f"{prefix}-{region}.pooler.supabase.com"
            url = f"postgresql://postgres.{PROJECT_REF}:{pw}@{host}:6543/postgres"
            try:
                conn = psycopg.connect(url, connect_timeout=8)
                print(f"  [OK] connected via {host}\n")
                conn.close()
                return url
            except Exception as e:
                msg = str(e).lower()
                if "tenant" in msg or "not found" in msg:
                    continue  # wrong region, keep sweeping
                if "password" in msg or "authentication" in msg:
                    # Right region found, but the password is wrong.
                    print(f"  [!] Found your project in region '{region}' ({host})")
                    print(f"      but the DB password was REJECTED. Fix DB_PASSWORD.\n")
                    return None
                # other transient/network error — try next
                continue
    print("  Could not locate the project in any known region.\n")
    return None


def part_b():
    print("\n" + "=" * 100)
    print("PART B — catalog audit (definitive RLS flags)")
    print("=" * 100)
    if not DB_URL and not DB_PASSWORD:
        print("Set DB_URL, or set DB_PASSWORD to auto-sweep regions for the connection.")
        return
    try:
        import psycopg  # pip install "psycopg[binary]"
    except ImportError:
        print('psycopg not installed — run: pip install "psycopg[binary]"')
        return

    conn_str = find_connection(psycopg)
    if not conn_str:
        return

    with psycopg.connect(conn_str, connect_timeout=15) as conn, conn.cursor() as cur:
        cur.execute(RLS_QUERY)
        rows = cur.fetchall()
        print(f"\n{'TABLE':<28} {'RLS':<7} {'FORCED':<7} {'POLICIES':<9} VERDICT")
        print("-" * 100)
        off = []
        for table, rls, forced, n in rows:
            if not rls:
                v = "!! RLS OFF — public can read/write"
                off.append(table)
            elif n == 0:
                v = "RLS on, 0 policies (denies all anon)"
            else:
                v = "RLS on + policies (review below)"
            print(f"{table:<28} {str(rls):<7} {str(forced):<7} {n:<9} {v}")

        cur.execute(POLICY_QUERY)
        pol = cur.fetchall()
        if pol:
            print("\n--- POLICIES (watch for USING: true granted to anon/public) ---")
            for tablename, policyname, cmd, roles, qual, with_check in pol:
                print(f"  [{tablename}] {policyname} ({cmd}, roles={roles})")
                print(f"      USING: {qual} | WITH CHECK: {with_check}")
        print()
        if off:
            print(f"=> CRITICAL: RLS disabled on {len(off)} table(s): {off}")
        else:
            print("=> Good: every public table has RLS enabled.")


def main():
    print(f"Auditing {SUPABASE_URL}\n")
    part_a()
    part_b()


if __name__ == "__main__":
    main()
