#!/usr/bin/env python3
"""
DEFINITIVE Supabase RLS audit — connects directly to Postgres and reads the
system catalog. Reports, per table in `public`:
  - whether RLS is ENABLED
  - how many policies it has
  - the policies themselves (so you can spot `using (true)` = wide open)

Requires the DB connection string (NOT the service key — Postgres needs a real
login). Get it from the Supabase dashboard:
  Project Settings -> Database -> Connection string -> "URI"
It looks like:
  postgresql://postgres.<ref>:<PASSWORD>@aws-0-<region>.pooler.supabase.com:6543/postgres

Install the driver first:
  pip install "psycopg[binary]"
"""
import os
import sys
import psycopg  # pip install "psycopg[binary]"

# Read from env var DB_URL, or paste your connection string here:
DB_URL = os.environ.get("DB_URL") or "PASTE_YOUR_CONNECTION_STRING_HERE"

RLS_QUERY = """
select
    c.relname                          as table_name,
    c.relrowsecurity                   as rls_enabled,
    c.relforcerowsecurity              as rls_forced,
    coalesce(p.cnt, 0)                 as policy_count
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
left join (
    select schemaname, tablename, count(*) as cnt
    from pg_policies
    group by schemaname, tablename
) p on p.schemaname = n.nspname and p.tablename = c.relname
where c.relkind = 'r'
  and n.nspname = 'public'
order by c.relname;
"""

POLICY_QUERY = """
select tablename, policyname, cmd, roles, qual, with_check
from pg_policies
where schemaname = 'public'
order by tablename, policyname;
"""


def main():
    if "PASTE_YOUR_CONNECTION_STRING" in DB_URL:
        print("ERROR: set DB_URL env var or edit DB_URL in this file.")
        print('  PowerShell:  $env:DB_URL = "postgresql://postgres.<ref>:<pw>@...:6543/postgres"')
        sys.exit(1)

    with psycopg.connect(DB_URL, connect_timeout=15) as conn:
        with conn.cursor() as cur:
            cur.execute(RLS_QUERY)
            rows = cur.fetchall()

            print(f"\n{'TABLE':<32} {'RLS':<10} {'FORCED':<8} {'POLICIES':<9} VERDICT")
            print("-" * 80)
            exposed = []
            locked_no_policy = []
            for table, rls, forced, n_policies in rows:
                if not rls:
                    verdict = "!! RLS OFF — anyone with anon key can read/write"
                    exposed.append(table)
                elif n_policies == 0:
                    verdict = "RLS on, 0 policies (denies all anon access)"
                    locked_no_policy.append(table)
                else:
                    verdict = "RLS on + policies (review the rules)"
                print(f"{table:<32} {str(rls):<10} {str(forced):<8} {n_policies:<9} {verdict}")

            # Show the actual policy rules so you can spot `using (true)`
            cur.execute(POLICY_QUERY)
            policies = cur.fetchall()
            if policies:
                print("\n--- POLICY DETAILS (watch for qual = 'true' granted to anon/public) ---")
                for tablename, policyname, cmd, roles, qual, with_check in policies:
                    print(f"\n  [{tablename}] {policyname}  ({cmd}, roles={roles})")
                    print(f"      USING:      {qual}")
                    print(f"      WITH CHECK: {with_check}")

            print("\n" + "=" * 80)
            if exposed:
                print(f"CRITICAL: {len(exposed)} table(s) with RLS DISABLED -> {exposed}")
            else:
                print("Good: every public table has RLS enabled.")
            if locked_no_policy:
                print(f"Note: {len(locked_no_policy)} table(s) have RLS but no policies "
                      f"(fully locked for anon) -> {locked_no_policy}")


if __name__ == "__main__":
    main()
