# Supabase RLS Security Review — agilitylms.tech

**Project:** `jpjrhpagjevjkfezgnve` (Supabase, region ap-northeast-2)
**Scope:** Row Level Security (RLS) posture of the `public` schema (40 tables)
**Method:** Read-only audit — REST probing as anon + authenticated user, Postgres catalog
inspection (`pg_policies`, `pg_trigger`), and **non-destructive** rollback proof-of-concepts
(every write attempt was executed inside a transaction and `ROLLBACK`-ed; nothing was committed).

---

## Executive summary

**Overall: RLS is well-implemented.** All 40 public tables have RLS enabled, and the policy
set is thoughtfully scoped by role (`employee`, `manager`, `people_ops`, `super_admin`,
`contractor`) and by ownership (`auth.uid()`, `reports_to`). Defense-in-depth is present:
where a policy is permissive, a RESTRICTIVE policy, a trigger, or a foreign key backs it up.

**No critical or high-severity issues were confirmed.** An initial concern that an employee
could delete users or self-escalate to `super_admin` was **tested and disproven**. Remaining
items are low-severity hardening / hygiene.

---

## What was tested and cleared (no action strictly required)

| Concern | Result | Why it's safe |
|---|---|---|
| Delete any user (`users_delete USING true`) | **Not exploitable** | `users_no_delete` is **RESTRICTIVE** (`USING false`); restrictive policies AND-combine, so deletes are blocked for all. |
| Self-escalate role via `UPDATE` (`users_update_own`, no column limit) | **Blocked** | `BEFORE UPDATE` trigger `trg_prevent_privilege_escalation` raises *"You do not have permission to modify privileged user fields."* (PoC confirmed.) `trg_guard_classification_update` similarly guards `classification`. |
| Insert a `super_admin` row (`users_insert WITH CHECK true`) | **Blocked** | FK `users_id_fkey` to `auth.users` requires `id` to be a real auth user; arbitrary inserts fail. (PoC confirmed.) |

---

## Findings (low / informational)

### L1 — `system_config` is readable by anonymous users
- **Policy:** `system_config_select_all (SELECT, public) USING true`
- **Confirmed:** anon role read all 10 rows.
- **Impact:** Low. Contents are benign business config (notification toggles, leave-year
  dates, notice-period/probation durations). No secrets or credentials. But there's no reason
  unauthenticated visitors should read internal config.
- **Fix:**
  ```sql
  DROP POLICY system_config_select_all ON public.system_config;
  CREATE POLICY system_config_select_auth ON public.system_config
    FOR SELECT TO authenticated USING (true);
  ```

### L2 — `audit_log` accepts inserts from anyone
- **Policy:** `audit_log_insert_system (INSERT, public) WITH CHECK true`
- **Impact:** Low–medium. Any client (incl. anon) can forge or spam audit-log entries,
  undermining the integrity/trustworthiness of the audit trail. (Not write-tested to avoid
  polluting the log; flagged from policy definition.)
- **Fix:** Write audit entries from a trusted path (service role / `SECURITY DEFINER`
  function) and remove the public INSERT policy, or constrain `WITH CHECK` to the acting user:
  ```sql
  DROP POLICY audit_log_insert_system ON public.audit_log;
  -- inserts should come from a SECURITY DEFINER function or service_role only
  ```

### L3 — `blocked_dates` readable by anonymous users
- **Policy:** `blocked_dates_select_all (SELECT, public) USING true`
- **Impact:** Low. Calendar blackout dates exposed to unauthenticated visitors.
- **Fix:** Restrict the SELECT policy to `authenticated`.

### L4 — Lookup tables enumerable by any authenticated user (by design?)
- **Policies:** `custom_roles.cr_select`, `document_types.document_types_select`,
  `role_permissions.rp_select` — all `SELECT USING true` to `authenticated`.
- **Impact:** Low. Any logged-in employee can read the full role/permission structure.
  Often acceptable for lookup data — flagged so it's a conscious decision, not an oversight.

---

## Hygiene / process recommendations

1. **Tighten the `users` policies anyway.** `users_delete (USING true)` and
   `users_insert (WITH CHECK true)` are currently safe only because a RESTRICTIVE policy and a
   FK happen to catch them. Make the intent explicit — scope INSERT/DELETE to `super_admin`
   (or service role) so the table isn't one dropped-trigger away from a real hole.
2. **Confirm the signup flow** auto-creates the `public.users` row (so a fresh user can't
   insert their own row with `role='super_admin'` before one exists). This is the only
   residual, unverified escalation path.
3. **Never ship the `service_role` key to the frontend** and keep it out of git — it bypasses
   RLS entirely. (Not observed in the reviewed bundle — good.)
4. **Rotate the database password** used during this review (it was exposed in the testing
   session) via Settings → Database → Reset password.
5. **Treat user session tokens (JWT + refresh) as secrets** — don't paste them into logs,
   URLs, screenshots, or chats.

---

## Appendix — how the headline concern was ruled out

The `users` table appeared to grant `DELETE USING true` and `UPDATE` with no column
restriction to logged-in users. Static reading suggested an employee could delete users or
set their own `role` to `super_admin`. Testing showed:
- `users_no_delete` is **RESTRICTIVE** → deletes blocked.
- `trg_prevent_privilege_escalation` (BEFORE UPDATE) → role change rejected at the DB layer.
- `users_id_fkey` → cannot insert a `users` row for a non-existent auth user.

All three confirmed via rolled-back proof-of-concept executed under the `authenticated` role
with the test user's JWT claims, so RLS was enforced exactly as it is for a real employee.
No data was modified.
