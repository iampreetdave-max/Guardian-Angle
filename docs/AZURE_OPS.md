# Azure Deployment — Ops Status & Runway Plan

*Snapshot: 2026-07-11. All facts below verified live that day unless marked estimate.*

## Live deployment

| Item | Value |
|---|---|
| URL | https://visionscan.centralindia.cloudapp.azure.com (HTTPS via Caddy) |
| Old IP URL | http://20.235.242.219 → 301 redirects to the HTTPS URL |
| VM | "Visionscan" in `Visionscan_group`, Central India Zone 1, B2as_v2 (2vCPU/8GB), Ubuntu 24.04, 64GB Standard SSD, 4GB swap |
| SSH | `ssh -i ~/.ssh/visionscan_do azureuser@20.235.242.219` |
| Deploy flow | `git push ssh://azureuser@20.235.242.219/home/azureuser/visionscan.git hf-clean:main` → on VM: `cd ~/app && git pull && sudo docker compose up -d --build` |
| Deployed commit | `10bdd10` — **one behind** local `40f5975` (Anomaly Watch fire/smoke). Fire/smoke `.pt` (546MB) is gitignored → must be copied to VM separately if deploying that commit |
| TLS cert | Valid to **Sep 2, 2026**; Caddy auto-renews — no action needed |
| Subscription | Azure for Students (no card), credit expires 06/04/2027 |

## Health check results (2026-07-11) — everything working: YES

- Frontend loads (index.html + 1MB JS bundle, HTTP 200)
- `/api/health` ok; `/api/feeds`, `/api/videos`, `/api/legal/health` all 200
- Auth verified end-to-end: login as `officer@city.gov` returned JWT; authed `/api/notifications` 200; unauthed 401
- VM: up 37 days, load ~0, disk 28% used (45GB free), 5.5GB RAM available, swap untouched
- Containers `app-backend-1` (healthy) + `app-frontend-1`, both `restart: unless-stopped`; docker + caddy systemd-enabled → **VM start = site back with zero manual steps, ~2–4 min**

## Credit runway (the only clock that matters)

- Balance 2026-07-11: **₹4,240 of ₹9,439** (portal → Education blade)
- Burn: ₹1,601.68 in first 10.5 days of July ≈ **₹152/day** (VM ≈ ₹127/day, disk+IP ≈ ₹25/day fixed)
- **Do nothing → credit dies ~Aug 8–9, 2026**
- At ₹0: subscription disabled, VM deallocated, **disk kept** — resume by upgrading to pay-as-you-go, nothing deleted

## Options to extend (decided 2026-07-11, NOT yet implemented)

### Plan A — nightly scheduled stop/start (~30–45 min setup, no code)
- Stop 10pm IST: VM blade → Operations → **Auto-shutdown** (built-in)
- Start 6:30am IST: one Logic App (consumption) or Automation runbook on a schedule (both ~free)
- Saves ~₹48/day → burn ~₹104/day → **alive to ~Aug 21**. Site fully down 10pm–6:30am.

### Plan B — Plan A + wake-on-visit (~4–6 hrs, 5 moving parts)
- Requires **own domain** (₹99–500/yr) + free Cloudflare in front. Can't be done on the `cloudapp.azure.com` hostname — when the VM is off nothing catches the request.
- Cloudflare Worker: origin up → pass through; origin down → serve "waking up, ~3 min, auto-refresh" page + call small Azure Function (managed identity) that starts the VM.
- Wake latency for visitor: ~3–5 min. Plus one-line Caddy change + DNS A record.

### Endgame — migrate to teammate's Azure for Students (fresh ₹9,439), ~1–2 hrs
- Same compose setup; copy SQLite DB + docker volumes (rsync).
- **URL can be kept** if: (1) new VM is also in **Central India**, (2) release the DNS label first (old portal → Public IP → Configuration → clear label, or delete the IP), (3) friend immediately sets label `visionscan` on their new public IP. Small minutes-long race window — do steps back-to-back.
- Raw IP will change → update SSH command + git push remote. Caddy fetches a fresh cert for the same hostname automatically.

### Two-month math
Fixed disk+IP ≈ ₹25/day means a full 2 months (to ~Sep 11) needs the VM off ~16h/day. Realistic path: **Plan A now, teammate migration when credit nears zero.**

## Recommendation
Do Plan A (30 min, zero risk). Add Plan B only if judges actually browse at night. Keep the teammate migration as the backstop.
