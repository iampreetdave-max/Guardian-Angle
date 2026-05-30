# CityShield — Case Management, Auth & Citizen Portal (PLAN)

> Status: **PLAN — not yet implemented.** This is the spec to review before building.
> Goal: turn CityShield from a single-user tool into a multi-user policing platform
> with authentication, role-based access, case lifecycle, evidence governance,
> notifications, and a citizen complaint portal — while keeping VisionScan and
> Arbiter intact as the tools officers use *inside* a case.

---

## 1. Roles & permissions

| Capability | Citizen | Officer | Team Lead | Admin (SHO) |
|---|---|---|---|---|
| Register / track own complaint | ✅ | — | — | ✅ (view all) |
| See all complaints | — | — | own team's | ✅ |
| Triage complaint (severity, priority, response msg) | — | — | ✅ | ✅ |
| Create case / assign team & members | — | — | ✅ (own team) | ✅ |
| Access a case | only if case "citizen-visible" + it's theirs | only if assigned | own team's cases | ✅ all |
| Add evidence / documents (FIR, brief) | — | ✅ (assigned) | ✅ | ✅ |
| Set evidence visibility (team/station/dept/citizen) | — | ✅ | ✅ | ✅ |
| Toggle "citizen can view case" | — | ✅ | ✅ | ✅ |
| Close case + record verdict | — | — | ✅ | ✅ |
| Manage users / teams | — | — | — | ✅ |
| Send case message | 1 message (if visible) | ✅ unlimited | ✅ | ✅ |
| Rate experience (on close) | ✅ | — | — | — |

RBAC is enforced **server-side on every endpoint** (never trust the client). A
per-case access check = `is_admin OR assigned_to_case OR (same team) OR
(citizen owns it AND case.citizen_visible)`.

---

## 2. Data model (new SQLite tables)

```
users(id, name, email UNIQUE, password_hash, role[citizen|officer|lead|admin],
      team_id?, phone, badge_no?, active, created_at)
teams(id, name, station, lead_user_id, created_at)

complaints(id, citizen_id, title, description, category, location,
      status[submitted|under_review|assigned|converted|rejected|closed],
      severity[low|med|high|critical]?, priority[int]?, response_message?,
      assigned_team_id?, created_at, updated_at)

cases(id, title, complaint_id?, created_by, assigned_team_id,
      status[open|active|closed], severity, priority,
      citizen_visible(bool default 0), citizen_id?,
      verdict?, closed_by?, closed_at?, created_at, updated_at)

case_assignments(case_id, user_id, role_on_case)          -- explicit access list
evidence(id, case_id, kind[frame|video|file|report|note], ref, caption,
      visibility[team|station|department|citizen], added_by, created_at)
case_documents(id, case_id, doc_type[FIR|brief|chargesheet|other], title,
      content, created_by, created_at)                    -- Arbiter FIRs land here
case_messages(id, case_id, sender_id, sender_role, body, created_at)
ratings(case_id, citizen_id, stars, comment, created_at)
notifications(id, user_id, type, message, case_id?, complaint_id?, read, created_at)
audit_log(id, actor_id, action, entity, entity_id, detail, created_at)
```

**Evidence governance** — every piece of evidence carries a `visibility`:
`team` (assigned members only) → `station` → `department` → `citizen` (only when
the case is citizen-visible). Existing VisionScan frames/PDF reports attach as
`evidence` rows (kind=frame/report, ref=frame_id/report path); Arbiter FIR drafts
save as `case_documents`. This is what wires Detect → Investigate → Prosecute
into one case record.

---

## 3. Lifecycle (state machines)

**Complaint:** `submitted` → (admin/lead reviews) `under_review` → (triage:
severity+priority+response) `assigned` → (spawns a Case) `converted` → … or
`rejected`. Citizen is emailed/notified the response message at triage.

**Case:** `open` → `active` (investigation: evidence, FIR, brief) → `closed`
(verdict recorded). **Closed cases** get a dedicated archived view (status=closed),
read-only except by admin, with verdict + rating shown.

---

## 4. Authentication

- **Passwords:** hashed with bcrypt (`passlib`). Never stored plain.
- **Tokens:** JWT access token (signed with an env secret), short-lived; sent as
  `Authorization: Bearer`. Optional refresh token.
- **Endpoints** (`/api/auth/*`): `register` (citizen self-serve; officers/admins
  created by admin), `login`, `logout`, `me`, `change-password`,
  `forgot-password`, `reset-password`.
- **Forgot/reset:** issues a one-time reset token. Delivery via the email layer
  (below) — or, offline, surfaced to the user/admin so the flow still works.
- **Seeded demo accounts** so judges log in instantly: `admin@city`,
  `officer@city`, `citizen@city` (passwords shown in the demo doc).

---

## 5. Notifications & email

- **In-app:** `notifications` table + `GET /api/notifications` (unread count
  badge in the header; we already poll every 3s). Marked read on view.
- **Email (optional, hybrid like Arbiter):** if SMTP env vars are set, real
  emails go out; otherwise messages are written to an **"outbox"** (stored +
  shown to admin / logged) so the flow is demonstrable fully offline.
- **Triggers:** complaint created → admins; complaint triaged/assigned → team +
  citizen (response msg); case created/assigned → assigned officers; evidence
  added → case members; case closed → members + citizen (if visible); citizen
  message → team.

---

## 6. API surface (new, all additive — VisionScan/Arbiter routes untouched)

```
/api/auth/*              register, login, logout, me, change/forgot/reset password
/api/users, /api/teams   admin user & team management
/api/complaints          citizen create + list-own; admin/lead list-all, triage
/api/cases               create, list (role-scoped), get, update, close
/api/cases/{id}/assign   assign members/team
/api/cases/{id}/evidence add/list (visibility-filtered)
/api/cases/{id}/documents FIR/brief (Arbiter output saved here)
/api/cases/{id}/messages thread (citizen capped at 1)
/api/cases/{id}/citizen-visibility  toggle
/api/cases/{id}/rate     citizen rating on closed case
/api/notifications       list/mark-read
```

Every route runs an auth dependency (`get_current_user`) + a role/case-access
check. All mutations write an `audit_log` entry.

---

## 7. Frontend

- Add **react-router-dom** (today it's a single page; multi-role dashboards need
  routing).
- **Auth pages:** `/login`, `/register`, `/forgot-password`, `/reset-password`,
  `/account` (change password).
- **Role-aware shell** (nav adapts to role) with a notifications bell:
  - **Admin:** Dashboard (stats), Complaints inbox, Cases, Users & Teams.
  - **Officer/Lead:** My Cases → **Case workspace** (Overview · Evidence ·
    Documents/FIR · Messages · Timeline/Audit · Close+Verdict), with VisionScan
    search and Arbiter embedded as in-case tools ("attach result to case").
  - **Citizen:** Register/Track complaint, case progress (if enabled), one
    message, rating on closure.
- VisionScan & Arbiter remain usable standalone, but also appear inside a case.

---

## 8. Security & compliance (judge-scoring)

Server-side RBAC on every endpoint · bcrypt password hashing · JWT · full
audit log of every action · evidence visibility scoping · citizen data
minimization · role separation. Documented production hardening path: HTTPS,
rate limiting, 2FA, encryption-at-rest, refresh-token rotation.

---

## 9. Suggested phasing (build order)

- **Phase 1 — Identity & access:** auth (login/logout/JWT/change+forgot pwd),
  users/roles, seeded accounts, route-gating. *Everything else depends on this.*
- **Phase 2 — Cases & evidence:** cases, assignment, per-case access control,
  evidence + documents with visibility, attach VisionScan frames/reports & Arbiter
  FIRs, close + verdict, closed-case archive.
- **Phase 3 — Citizen portal & complaints:** complaint registration, admin
  triage (severity/priority/response), citizen visibility toggle, one message,
  rating.
- **Phase 4 — Notifications & email:** in-app notifications + bell, hybrid email
  (SMTP or offline outbox), all triggers, audit-log timeline UI.

Each phase is independently demoable and doesn't break the previous one.

---

## 10. Open decisions (need your input before Phase 1)

1. **Does login gate the whole platform?** (Recommended yes, with seeded demo
   accounts so judges get in instantly.) This changes the current open demo.
2. **Email:** real SMTP (needs creds) vs **hybrid** (SMTP if configured, else
   offline outbox — recommended, keeps offline story).
3. **Scope now:** all 4 phases, or start with Phase 1 (+2) and iterate?
4. **Teams:** full team model (teams + lead + members) or simpler per-officer
   case assignment to start?
5. **DB:** stay on SQLite for the demo (recommended) — note Postgres as the
   scale path — or move to Postgres now?
