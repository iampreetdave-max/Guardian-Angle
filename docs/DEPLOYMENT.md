# CityShield / VisionScan — Going Live (Production Deployment Plan)

> Status: **plan, ready to implement.** This document is the roadmap for taking
> the platform from "runs on my laptop / HF demo" to a real, multi-user,
> internet-facing deployment. Nothing here is wired in yet — it's the recipe.
>
> For the *demo-grade* hosting that already exists (Hugging Face Spaces public
> link + Cloudflare quick tunnel), see [`deploy/HOSTING.md`](../deploy/HOSTING.md).
> This file is about the **production** story.

---

## 1. Where we are today

| Surface | What it is | Good for | Not good for |
|---|---|---|---|
| `start.ps1` / `docker compose` | Full 2-container stack on one host | Local + field/offline use | Public multi-user access |
| HF Spaces (`iampreetdave/visionscan`) | Single core-only container, :7860 | A public try-it link for judges | Real data (ephemeral storage), face matching, auth persistence, always-on |

**Gaps to close before "live":**
1. **HTTPS + a domain** — login tokens and case data must never travel over plain HTTP.
2. **Persistent storage** — SQLite DB, uploaded footage, FAISS indexes and model cache must survive restarts/redeploys.
3. **Security hardening** — real JWT secret, demo accounts off, CORS locked down, **API-level auth gating** (see §6 — currently the UI gates, the VisionScan/Arbiter API routes do not).
4. **Backups** — the SQLite DB holds users, cases, evidence, audit log. It needs scheduled backups.
5. **Always-on host** — no idle-sleep; enough RAM for the models (ArcFace + CLIP + YOLO ≈ 3–4 GB resident).

---

## 2. Recommended path: single VPS + Docker Compose + Caddy (auto-HTTPS)

The fastest credible production setup. One Linux VM runs the existing compose
stack plus a **Caddy** reverse proxy that terminates TLS and auto-renews
Let's Encrypt certificates. This reuses everything we already built.

```
                 Internet
                    │  https://cityshield.example.com
            ┌───────▼────────┐
            │     Caddy      │  TLS termination + auto-cert + reverse proxy
            └───┬────────┬───┘
                │        │
        /api,/thumbnails │ everything else (SPA)
                │        │
        ┌───────▼──┐  ┌──▼────────┐
        │ backend  │  │ frontend  │   (the existing two containers)
        │ :8000    │  │ nginx :80 │
        └────┬─────┘  └───────────┘
             │ named volumes: visionscan-data, model-cache, insightface-cache
```

### Why this first
- Reuses the current `docker-compose.yml` almost verbatim (add one Caddy service).
- Auto-HTTPS with zero cert hassle.
- A single $12–24/mo VM comfortably runs the whole thing for a pilot.
- Trivial to back up (it's all in named volumes on one box).

### Sizing
| Tier | Spec | Notes |
|---|---|---|
| Minimum | 2 vCPU / 4 GB RAM / 40 GB SSD | core search only; face matching may OOM |
| **Recommended** | 4 vCPU / 8 GB RAM / 80 GB SSD | full stack incl. ArcFace, a few concurrent users |
| Heavy / GPU | + NVIDIA T4/L4 | only if you ingest many long videos; set `VISIONSCAN_DEVICE=cuda` |

Providers: Hetzner (cheapest, ~€8–16/mo), DigitalOcean, Linode, AWS Lightsail,
Azure VM, or an on-prem police server for data-sovereignty (this app is built to
run fully offline, which is a strong fit for a govt deployment).

### Step-by-step
1. **Provision** an Ubuntu 22.04+ VM. Open ports 80 + 443 only (SSH restricted to your IP).
2. **Install Docker** (`curl -fsSL https://get.docker.com | sh`) + the compose plugin.
3. **DNS**: point an A record (`cityshield.example.com`) at the VM's IP.
4. **Clone** the repo, create `.env` from `.env.example` and set, at minimum:
   - `VISIONSCAN_JWT_SECRET=<48+ random chars>`
   - `VISIONSCAN_SEED_DEMO_USERS=false`  (after you've created a real admin)
   - optional `VISIONSCAN_GEMINI_API_KEY`, SMTP for real email.
5. **Add the Caddy overlay** (Appendix A) and launch:
   `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
6. **Create the real admin** (temporarily seed demo, log in as admin, create your
   admin user via the Admin panel, then set `SEED_DEMO_USERS=false` and redeploy),
   or add a one-off `scripts/create_admin.py`.
7. **Verify**: `https://cityshield.example.com` loads over TLS, login works, file
   upload + search work, `/docs` reachable.
8. **Set up backups** (§5) and a restart policy (already `unless-stopped`).

---

## 3. Alternative architectures (for later scale)

| Option | Shape | When to choose | Trade-offs |
|---|---|---|---|
| **A. Single VPS + Caddy** (recommended) | one box, compose | pilot → first real users | manual scaling; one host |
| **B. Split: static FE + API service** | FE on Netlify/Vercel/CF Pages, API container on Fly.io / Cloud Run / Render | want CDN-fast UI, managed API | API cold starts; must externalize storage |
| **C. Managed containers** (AWS ECS/Fargate, GCP Cloud Run, Azure Container Apps) | backend image + managed DB + object store | org already on a cloud; want autoscale | most rework: move SQLite→Postgres, files→S3/GCS, FAISS→shared volume or a vector DB |
| **D. On-prem / air-gapped** | the compose stack on a police server | data sovereignty, offline mandate | you own ops + backups |

**Note for B/C:** the app currently uses **SQLite + local-disk FAISS + local
thumbnails**, which assume a single host with a persistent disk. Going
multi-instance/serverless requires: SQLite → **Postgres**, thumbnails/footage →
**S3/GCS**, and FAISS → a shared volume or a managed vector DB (e.g. Qdrant /
pgvector). That's a meaningful refactor — fine to defer until you outgrow A.

---

## 4. Production hardening checklist

- [ ] `VISIONSCAN_JWT_SECRET` set to a long random value (not the default).
- [ ] `VISIONSCAN_SEED_DEMO_USERS=false` and demo accounts deleted/rotated.
- [ ] HTTPS enforced (Caddy redirects HTTP→HTTPS automatically).
- [ ] CORS locked to the real origin: set `cors_origins` in `config.py` (or an env
      list) to `https://cityshield.example.com` instead of the localhost defaults.
- [ ] **API-level auth gating** turned on: set `VISIONSCAN_REQUIRE_AUTH=true` (see §6).
- [ ] Upload limits sane (`client_max_body_size` is 2 GB in nginx — tune to need).
- [ ] SSH key-only, firewall to 80/443, automatic security updates on the host.
- [ ] Secrets in `.env` only (already gitignored); never commit real keys.
- [ ] Rate-limiting on `/api/auth/login` (Caddy or a slowapi middleware) to blunt brute force.
- [ ] Log retention + the existing `audit_log` table reviewed for compliance.

---

## 5. Persistence & backups

All durable state lives in three named Docker volumes:
- `visionscan-data` → **SQLite DB (`visionscan.db`), uploaded videos, thumbnails, FAISS indexes, Chroma corpus.** This is the irreplaceable one.
- `model-cache`, `insightface-cache` → downloaded model weights (re-downloadable; back up only to speed recovery).

**Daily backup (cron on the host):**
```bash
# dump just the DB consistently, plus the data volume
docker compose exec -T backend sh -c 'sqlite3 /data/visionscan.db ".backup /data/backup.db"'
docker run --rm -v visionscan_visionscan-data:/data -v /opt/backups:/out alpine \
  tar czf /out/cityshield-$(date +%F).tar.gz -C /data .
# rotate: keep 14 days, ship offsite (S3/rsync) for real DR
```
Test a restore at least once before you trust it.

---

## 6. API-level auth gating (built in — flip the flag)

The **frontend** gates the UI behind login. By default the VisionScan and Arbiter
**API routes stay open** so the public HF demo (which has no users) keeps working.
For a real deployment, set **`VISIONSCAN_REQUIRE_AUTH=true`** — every
VisionScan/Arbiter route then requires a valid login token (the `auth_gate`
dependency in `app/platform/security.py`), while `/api/health`, `/api/feeds` and
`/api/legal/health` stay public so the Docker healthcheck still works. The React
client auto-bounces to the login screen on a 401. **Set this before exposing real
footage/cases.** For finer control you can additionally swap `auth_gate` for
`require_role(...)` on specific routes.

---

## 7. Suggested phasing

1. **Phase 1 — Pilot (1–2 days):** Option A on a single 8 GB VPS, Caddy TLS, real
   admin, demo users off, daily DB backup. Good enough for a controlled pilot
   with a handful of officers.
2. **Phase 2 — Harden (this sprint):** API auth gating (§6), login rate-limiting,
   CORS lockdown, offsite backups, uptime monitoring (UptimeRobot/Healthchecks.io
   hitting `/api/health`).
3. **Phase 3 — Scale (only if needed):** migrate SQLite→Postgres and
   files→object storage, then move to Option C (managed containers) for
   autoscaling and HA. Optionally add a GPU node for heavy ingestion.

---

## Appendix A — `docker-compose.prod.yml` (Caddy overlay, ready to drop in)

```yaml
# Use:  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
services:
  # Don't publish backend/frontend ports publicly; only Caddy is exposed.
  backend:
    ports: []
  frontend:
    ports: []

  caddy:
    image: caddy:2-alpine
    depends_on:
      - frontend
      - backend
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
      - caddy-config:/config
    restart: unless-stopped

volumes:
  caddy-data:
  caddy-config:
```

## Appendix B — `deploy/Caddyfile`

```
cityshield.example.com {
    encode gzip

    # API + thumbnails go to the backend
    @api path /api/* /thumbnails/* /docs /openapi.json
    handle @api {
        reverse_proxy backend:8000
    }

    # Everything else is the React SPA served by the frontend nginx
    handle {
        reverse_proxy frontend:80
    }
}
```

That's the whole production delta: two small files + a `.env` + a domain. Caddy
fetches and renews the TLS cert automatically on first request.
