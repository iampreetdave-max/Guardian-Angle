#!/usr/bin/env python3
"""
NON-DESTRUCTIVE proof-of-concept + diagnostics for the `users` RLS escalation finding.

It does THREE read-only / rolled-back things, nothing is ever committed:

  PART 1  Policy metadata: shows PERMISSIVE vs RESTRICTIVE for every `users` policy,
          and lists every project-wide policy that grants `USING true` / `WITH CHECK true`
          (these are the loose ones). This answers "is users_no_delete actually restrictive?"

  PART 2  Trigger check: lists triggers on `public.users` so you can see whether a
          BEFORE UPDATE trigger protects the `role` column.

  PART 3  Rollback PoC: assumes the `authenticated` role + your JWT claims (so RLS is
          enforced as if it were YOU), attempts `UPDATE users SET role='super_admin'`,
          observes the result, then ROLLBACKs. Your real role is never changed.

Connection (same as the audit script):
  $env:DB_PASSWORD = "<db password>"          # script sweeps regions + URL-encodes for you
  # or: $env:DB_URL = "postgresql://..."
  $env:SUPABASE_USER_TOKEN = "<your access_token>"   # used only to read your uid/email (optional)
  $env:USER_UID = "9ab40992-39ac-42dd-ad12-caf751c506c9"  # fallback if no token
  python escalation_poc.py
"""
import os
import json
import base64
import uuid
from datetime import datetime, date, timezone

PROJECT_REF = "jpjrhpagjevjkfezgnve"
DB_URL = os.environ.get("DB_URL", "")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
USER_TOKEN = os.environ.get("SUPABASE_USER_TOKEN", "")
USER_UID_ENV = os.environ.get("USER_UID", "")

SUPABASE_REGIONS = [
    "ap-south-1", "ap-southeast-1", "ap-southeast-2", "ap-northeast-1", "ap-northeast-2",
    "us-east-1", "us-east-2", "us-west-1", "us-west-2", "ca-central-1", "sa-east-1",
    "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1", "eu-central-2", "eu-north-1",
]


def decode_jwt_claims(tok):
    try:
        payload = tok.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return {}


def find_connection(psycopg):
    from urllib.parse import quote
    if DB_URL:
        return DB_URL
    if not DB_PASSWORD:
        return None
    pw = quote(DB_PASSWORD, safe="")
    print(f"Sweeping {len(SUPABASE_REGIONS)} regions to find the pooler host...")
    for region in SUPABASE_REGIONS:
        for prefix in ("aws-0", "aws-1"):
            host = f"{prefix}-{region}.pooler.supabase.com"
            url = f"postgresql://postgres.{PROJECT_REF}:{pw}@{host}:6543/postgres"
            try:
                c = psycopg.connect(url, connect_timeout=8)
                c.close()
                print(f"  [OK] {host}\n")
                return url
            except Exception as e:
                m = str(e).lower()
                if "password" in m or "authentication" in m:
                    print(f"  [!] project is in {region} but password rejected.\n")
                    return None
                continue
    print("  Could not locate the project in any region.\n")
    return None


CMD = {"r": "SELECT", "a": "INSERT", "w": "UPDATE", "d": "DELETE", "*": "ALL"}


def part1_policy_metadata(cur):
    print("=" * 90)
    print("PART 1 — `users` policy metadata (PERMISSIVE policies combine with OR)")
    print("=" * 90)
    cur.execute("""
        select policyname, cmd, permissive, roles, qual, with_check
        from pg_policies where schemaname='public' and tablename='users'
        order by cmd, policyname;
    """)
    print(f"{'POLICY':<32} {'CMD':<8} {'TYPE':<12} {'USING / CHECK'}")
    print("-" * 90)
    for name, cmd, perm, roles, qual, check in cur.fetchall():
        expr = f"USING={qual}" if qual is not None else f"CHECK={check}"
        print(f"{name:<32} {cmd:<8} {perm:<12} {expr}")

    print("\nKey question — DELETE on users:")
    cur.execute("""
        select policyname, permissive, qual
        from pg_policies
        where schemaname='public' and tablename='users' and cmd='DELETE';
    """)
    delete_pols = cur.fetchall()
    has_permissive_true = any(p[1] == "PERMISSIVE" and (p[2] in ("true", None)) for p in delete_pols)
    has_restrictive = any(p[1] == "RESTRICTIVE" for p in delete_pols)
    for name, perm, qual in delete_pols:
        print(f"  - {name}: {perm}, USING={qual}")
    if has_permissive_true and not has_restrictive:
        print("  => CONFIRMED: a PERMISSIVE 'USING true' delete policy exists and NO RESTRICTIVE")
        print("     policy counters it. Any authenticated user can DELETE any users row.")
    elif has_restrictive:
        print("  => A RESTRICTIVE delete policy exists — it may block the open one. Read its expr.")

    print("\n" + "=" * 90)
    print("Project-wide loose policies (PERMISSIVE with USING true / WITH CHECK true)")
    print("=" * 90)
    cur.execute("""
        select tablename, policyname, cmd, roles, qual, with_check
        from pg_policies
        where schemaname='public' and permissive='PERMISSIVE'
          and (qual = 'true' or with_check = 'true')
        order by tablename, policyname;
    """)
    rows = cur.fetchall()
    if not rows:
        print("  none")
    for tbl, name, cmd, roles, qual, check in rows:
        who = ",".join(roles) if roles else "?"
        gate = "USING true" if qual == "true" else "WITH CHECK true"
        print(f"  [{tbl}] {name} — {cmd} to {who} ({gate})")


def part2_triggers(cur):
    print("\n" + "=" * 90)
    print("PART 2 — triggers on public.users (does anything protect the `role` column?)")
    print("=" * 90)
    cur.execute("""
        select pg_get_triggerdef(t.oid)
        from pg_trigger t
        join pg_class c on c.oid = t.tgrelid
        join pg_namespace n on n.oid = c.relnamespace
        where n.nspname='public' and c.relname='users' and not t.tgisinternal;
    """)
    trigs = cur.fetchall()
    if not trigs:
        print("  No user-defined triggers on `users`. Nothing stops a role change at the DB layer.")
    else:
        for (d,) in trigs:
            print(f"  {d}")
        print("\n  Review the above — a BEFORE UPDATE trigger that pins `role` would block escalation.")


def part3_rollback_poc(conn, uid, email):
    print("\n" + "=" * 90)
    print("PART 3 — rollback PoC: attempt self-escalation AS THE AUTHENTICATED USER")
    print("         (RLS enforced; everything is rolled back — your role will NOT change)")
    print("=" * 90)
    if not uid:
        print("  No USER_UID / token available — set USER_UID to run the PoC. Skipping.")
        return

    claims = json.dumps({"sub": uid, "role": "authenticated"})
    conn.autocommit = False
    cur = conn.cursor()
    try:
        # Become the authenticated user so RLS applies exactly as it would for them.
        cur.execute("SELECT set_config('request.jwt.claims', %s, true)", (claims,))
        cur.execute("SET LOCAL ROLE authenticated")
        cur.execute("SELECT auth.uid()")
        seen = cur.fetchone()[0]
        print(f"  Acting as auth.uid() = {seen}  (email: {email or 'n/a'})")

        cur.execute("SELECT role FROM users WHERE id = auth.uid()")
        before = cur.fetchone()
        print(f"  Role BEFORE: {before[0] if before else '(cannot read own row)'}")

        try:
            cur.execute("UPDATE users SET role='super_admin' WHERE id = auth.uid()")
            rc = cur.rowcount
            cur.execute("SELECT role FROM users WHERE id = auth.uid()")
            after = cur.fetchone()
            after_role = after[0] if after else None
            print(f"  UPDATE affected {rc} row(s); role now reads: {after_role}")
            if rc >= 1 and after_role == "super_admin":
                print("\n  >>> EXPLOITABLE: RLS allowed an employee to set their own role to "
                      "super_admin.\n      (Change is being ROLLED BACK — not saved.)")
            elif rc == 0:
                print("\n  Not exploitable via this path: RLS matched 0 rows for the UPDATE.")
        except Exception as e:
            print(f"\n  BLOCKED at the DB layer: {type(e).__name__}: {e}")
            print("  (A trigger or WITH CHECK / RLS rejected the change — good.)")
    finally:
        conn.rollback()  # <-- guarantees nothing is persisted
        print("\n  Transaction ROLLED BACK. No data was changed.")


def _sample_for_type(dtype):
    d = dtype.lower()
    if "char" in d or "text" in d:
        return "poc"
    if "bool" in d:
        return False
    if "int" in d or "numeric" in d or "double" in d or "real" in d:
        return 0
    if "timestamp" in d:
        return datetime.now(timezone.utc)
    if "date" in d:
        return date.today()
    if "json" in d:
        return "{}"
    if "uuid" in d:
        return str(uuid.uuid4())
    return "poc"


def part4_insert_poc(conn, uid):
    print("\n" + "=" * 90)
    print("PART 4 — rollback PoC: can an authenticated user INSERT a super_admin `users` row?")
    print("         (the UPDATE trigger does NOT fire on INSERT — this tests that gap)")
    print("=" * 90)
    if not uid:
        print("  No USER_UID — skipping.")
        return

    # Read columns first (read-only, as the privileged conn) to satisfy NOT NULLs.
    conn.autocommit = True
    with conn.cursor() as c0:
        c0.execute("""
            select column_name, is_nullable, column_default, data_type
            from information_schema.columns
            where table_schema='public' and table_name='users'
            order by ordinal_position;
        """)
        cols = c0.fetchall()

    test_id = str(uuid.uuid4())
    vals = {}
    for name, nullable, default, dtype in cols:
        if name == "id":
            vals["id"] = test_id
        elif name == "role":
            vals["role"] = "super_admin"
        elif name == "email":
            vals["email"] = f"poc-{test_id}@example.invalid"
        elif nullable == "NO" and default is None:
            vals[name] = _sample_for_type(dtype)

    claims = json.dumps({"sub": uid, "role": "authenticated"})
    conn.autocommit = False
    cur = conn.cursor()
    try:
        cur.execute("SELECT set_config('request.jwt.claims', %s, true)", (claims,))
        cur.execute("SET LOCAL ROLE authenticated")
        colnames = ", ".join(f'"{k}"' for k in vals)
        placeholders = ", ".join(["%s"] * len(vals))
        print(f"  Attempting INSERT with role='super_admin', id={test_id}")
        try:
            cur.execute(f"INSERT INTO users ({colnames}) VALUES ({placeholders})", list(vals.values()))
            print(f"\n  >>> EXPLOITABLE: insert succeeded ({cur.rowcount} row) — an authenticated")
            print("      user could create a super_admin row. (ROLLED BACK — not saved.)")
        except Exception as e:
            msg = str(e).lower()
            if "foreign key" in msg:
                reason = "FK to auth.users blocks arbitrary inserts (must match a real auth user)"
            elif "row-level security" in msg:
                reason = "RLS WITH CHECK rejected it"
            elif "duplicate" in msg or "unique" in msg:
                reason = "PK/unique conflict"
            elif "permission" in msg or "denied" in msg:
                reason = "trigger/privilege rejected it"
            elif "not-null" in msg or "not null" in msg or "violates check" in msg:
                reason = "blocked by a column constraint (NOTE: RLS itself permitted the insert)"
            else:
                reason = "other"
            print(f"\n  BLOCKED: {type(e).__name__} — {reason}")
            print(f"    {str(e).splitlines()[0]}")
    finally:
        conn.rollback()
        print("\n  Transaction ROLLED BACK. No data was changed.")
    print("\n  Caveat: this used an EXISTING user's identity. The residual risk is a *fresh*")
    print("  signup inserting its own row with role='super_admin' before any row exists —")
    print("  verify whether signup auto-creates the users row (PK then blocks re-insert).")


SECRET_HINT = ("key", "secret", "token", "password", "passwd", "api", "credential",
               "private", "service_role", "smtp", "webhook")


def part5_read_system_config(conn):
    print("\n" + "=" * 90)
    print("PART 5 — what can an ANONYMOUS visitor read from system_config? (USING true to public)")
    print("=" * 90)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        cur.execute("SET LOCAL ROLE anon")
        cur.execute("SELECT * FROM system_config LIMIT 100")
        colnames = [d.name for d in cur.description]
        rows = cur.fetchall()
        print(f"  anon CAN read system_config: {len(rows)} row(s). Columns: {colnames}")
        flagged = False
        for r in rows:
            cells = {c: (str(v)[:100] if v is not None else None) for c, v in zip(colnames, r)}
            line = " | ".join(f"{c}={v}" for c, v in cells.items())
            hit = any(h in line.lower() for h in SECRET_HINT)
            mark = "  <-- looks sensitive" if hit else ""
            flagged = flagged or hit
            print(f"    {line[:200]}{mark}")
        print()
        if flagged:
            print("  => Rows above look like they may contain secrets/config — anon can read them.")
        else:
            print("  => Visible to anon, but nothing obviously secret. Confirm by eye.")
    except Exception as e:
        print(f"  anon could NOT read system_config: {str(e).splitlines()[0]}")
        print("  (Table GRANT may block anon even though the policy says USING true.)")
    finally:
        conn.rollback()


def main():
    try:
        import psycopg
    except ImportError:
        print('psycopg not installed — run: pip install "psycopg[binary]"')
        return

    if not DB_URL and not DB_PASSWORD:
        print("Set DB_PASSWORD (or DB_URL) first.")
        return

    claims = decode_jwt_claims(USER_TOKEN) if USER_TOKEN else {}
    uid = USER_UID_ENV or claims.get("sub", "")
    email = claims.get("email", "")

    conn_str = find_connection(psycopg)
    if not conn_str:
        return

    conn = psycopg.connect(conn_str, connect_timeout=15)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            part1_policy_metadata(cur)
            part2_triggers(cur)
        part3_rollback_poc(conn, uid, email)
        part4_insert_poc(conn, uid)
        part5_read_system_config(conn)
    finally:
        conn.close()
    print("\nDone. This script committed NOTHING.")


if __name__ == "__main__":
    main()
