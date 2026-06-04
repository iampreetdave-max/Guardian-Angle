# VisionScan — Hosting Guide (Public Link for Proposals)

This guide gets the team a **single public URL** to paste into the proposal PDFs
and the README — a fully live, clickable demo of the platform. It documents the
recommended path (updating our existing Hugging Face Space), the production-grade
alternative, and an honest account of the free-tier limits and fallbacks.

> Scope note: a separate, older note (`deploy/HOSTING.md`) covers the
> Cloudflare-tunnel demo-day path. **This file is the canonical guide for the
> proposal/submission link.** Where they overlap, this file wins.

---

## 1. Decision summary — what to host where

| Option | What it gives you | Cost | Verdict |
|---|---|---|---|
| **Hugging Face Space** (`iampreetdave/visionscan`) | The **full live app** — UI + FastAPI backend + CLIP/YOLO search, predictive map, CrimeGPT, GovIntel, Arbiter, anomaly watch — behind one public URL | **Free** (CPU basic, 16 GB RAM / 2 vCPU) | **RECOMMENDED.** This is the link for the proposals. |
| **VPS + Docker Compose + Caddy** (per [`docs/DEPLOYMENT.md`](DEPLOYMENT.md)) | Production-grade: HTTPS on a real domain, persistent storage, face matching (ArcFace), always-on, backups | Paid VM (~$5–10/mo) | Use for a *real* deployment or if the Space can't keep up. Overkill just for a proposal link. |
| **Vercel / Netlify** | Static hosting only — **no Python, no ML runtime** | Free | **NOT viable for the app itself.** These platforms can't run the FastAPI backend or the PyTorch/CLIP/YOLO models. Use only for an optional static *landing page* that links to the Space. |

**Why the Space is the right call:** it is the only free option that runs the
real backend, it is already configured (root `Dockerfile` + HF YAML in
`README.md`), and the remote (`space`) is already wired up. We just need to push
the current code.

---

## 2. Updating the Space — exact steps

### What the Space actually is (verified from the repo)

- **README.md YAML front-matter** declares the Space config:
  ```yaml
  sdk: docker
  app_port: 7860
  license: mit
  ```
  So it's a **Docker SDK Space** (single container), serving on **port 7860**.
- The **root `Dockerfile`** is what HF builds. It is a 2-stage build:
  1. `node:20-alpine` builds the React frontend (`npm install` → `npm run build`).
  2. `python:3.11-slim` installs **`backend/requirements-core.txt`** (the lean
     CPU stack — CLIP + YOLOv8 + FAISS, **no InsightFace/ArcFace**), copies the
     backend, copies the built SPA into `app/static`, and runs
     `uvicorn app.main:app --host 0.0.0.0 --port 7860`.
- The Dockerfile sets the env the Space needs: it runs as UID 1000 with a
  writable `HOME=/home/user`, `VISIONSCAN_DATA_DIR=/home/user/data`,
  `VISIONSCAN_DEVICE=cpu`, model caches under `/home/user/.cache`, and
  `VISIONSCAN_STATIC_DIR=/home/user/app/app/static` so the SPA is served at `/`.
- **One container** serves both the SPA and the API — unlike the local
  `docker-compose.yml`, which runs two containers (backend + nginx frontend) on
  ports 8000/8080. The Space does **not** use docker-compose.
- **The Space builds from the `main` branch.** Confirmed via `git ls-remote space`
  (`HEAD → refs/heads/main`).

### The Space is currently behind — a push is required

Confirmed by comparing commits:

- **Deployed on the Space (`space/main`):** `9350220` — *"Live feed monitoring,
  grouping toggle, model warmup"*.
- **Local `main` / `hf-clean` HEAD:** `1113524` — *"Presentation kit…"*.

The Space is **~18 commits behind** and is missing all of the flagship work:
GIS crime mapping, predictive patrol routing, Phase-3 security, Anomaly Watch,
CrimeGPT, and the GovIntel polish. **You must push the current code** for the
public link to show what the proposals describe.

> Build size / time note: nothing pushed today adds bloat. There is **no
> Playwright dependency** anywhere in the backend (grep-verified), and the Space
> installs `requirements-core.txt`, not the heavier `requirements.txt`. The
> CrimeGPT/GovIntel modules are pure-Python and reuse stack already in
> `requirements-core.txt` (`reportlab`, `chromadb`, `transformers`), so they do
> not materially change build time or image size.

### Step 1 — Mint a fresh write token

The old token was stripped from the remote URL (treat it as compromised). Create
a new one:

1. Go to <https://huggingface.co/settings/tokens>.
2. **New token** → name it e.g. `visionscan-space-deploy` → role **Write**.
3. Copy it (shown once). **Do not commit it or bake it into the remote URL.**

### Step 2 — Push current `main` to the Space

The `space` remote already exists with a **token-free** URL
(`https://huggingface.co/spaces/iampreetdave/visionscan`), which is correct — we
pass the token at push time so it never lands in git config.

```bash
# from the project root: C:/Users/PREET/OneDrive/Desktop/VisionScan
# (optional) confirm the remote and target branch:
git remote -v                       # 'space' -> huggingface.co/.../visionscan
git ls-remote space                 # HEAD -> refs/heads/main

# push your up-to-date main to the Space's main branch.
# When prompted for a password, paste the WRITE TOKEN (username can be anything,
# e.g. your HF username 'iampreetdave').
git push space main

# If you're on the hf-clean branch and it equals main (it does today), you can
# push the current branch onto the Space's main explicitly:
git push space hf-clean:main
```

> One-liner without an interactive prompt (token inline, **not stored** because
> we don't change the saved remote URL):
> ```bash
> git push https://USER:HF_WRITE_TOKEN@huggingface.co/spaces/iampreetdave/visionscan main
> ```
> Replace `USER` with your HF username and `HF_WRITE_TOKEN` with the token from
> Step 1. Prefer the prompt form above so the token doesn't land in shell history.

### Step 3 — Set Space Secrets (recommended, not required to boot)

In the Space → **Settings → Variables and secrets → New secret**:

| Secret | Why | Required? |
|---|---|---|
| `VISIONSCAN_JWT_SECRET` | A strong random string to sign login tokens instead of the dev default | Recommended. **Not** required to boot: `require_auth` defaults to `false`, so `Settings.assert_secure()` does **not** block startup on the dev secret. |
| `VISIONSCAN_GEMINI_API_KEY` | Enables polished Arbiter/GovIntel LLM output | Optional. Without it the app runs **fully offline** with citation-grounded templates (`gemini_api_key` defaults to empty). |

Do **not** set `VISIONSCAN_REQUIRE_AUTH=true` on the free Space — the demo is
intentionally login-gated only at the UI so judges can click in. (If you ever do
set it, you **must** also set `VISIONSCAN_JWT_SECRET`, or boot will fail by
design.) Leave `VISIONSCAN_SEED_DEMO_USERS` at its default `true` so the demo
accounts exist on every boot.

### Step 4 — Wait for the build

- After the push, the Space rebuilds automatically. Watch **Space → Logs** (build
  log, then container log).
- **Expected build time: ~8–15 min on first/changed build** — it compiles the
  frontend, installs Torch (CPU wheel via the PyTorch index) + the CV stack, and
  may compile `chroma-hnswlib` from source (the Dockerfile installs
  `build-essential` for exactly this). Subsequent pushes that don't change
  `requirements-core.txt` rebuild faster (Docker layer cache).
- **First boot after build** downloads model weights (CLIP ViT-B/32, YOLOv8n)
  into the cache and warms them in a background thread (`app/main.py` `_startup`).
  Allow an extra ~1–2 min after the container starts before search/anomaly is hot.

### Step 5 — Verify it's live

1. Open <https://huggingface.co/spaces/iampreetdave/visionscan>. The SPA should
   render (the Space embeds the app at port 7860, served at `/`).
2. API health: the backend answers `GET /api/health`. From the embedded app this
   is internal; you can also hit the Space's direct URL
   (`https://iampreetdave-visionscan.hf.space/api/health`) and expect HTTP 200.
3. **Log in** with a demo account (password = role + `123`):
   - `admin@city.gov` / `admin123`, `lead@city.gov` / `lead123`,
     `officer@city.gov` / `officer123`, `citizen@example.com` / `citizen123`.
   - These are seeded automatically on boot — see "ephemeral storage" below.
4. Spot-check the flagship views (City Map / predictive hotspots) and a CCTV
   text search to confirm models warmed up.

> **Demo data is reseeded on every boot — verified in code.** `app/main.py`
> `_startup()` calls `init_db()` (`app/database.py`), which creates all tables and
> then calls `seed_demo()` when `seed_demo_users` is true. `seed_demo()` is
> idempotent — it only seeds when the `users` table is empty — and also seeds ~20
> Ahmedabad demo incidents (`seed_demo_data` default true, via
> `seed_ahmedabad.SEED_INCIDENTS`). On the Space's **ephemeral** disk the SQLite
> DB at `/home/user/data/visionscan.db` is wiped on every restart, so a fresh DB
> is created and **reseeded every cold start**. That's exactly what we want for a
> judge-facing demo: it always comes up clean and populated.

---

## 3. Free CPU-tier limitations (honest)

These are real and fine for a proposal/demo link — call them out so nobody is
surprised on stage:

- **Cold starts / sleep.** Free Spaces sleep after inactivity and wake on the
  next visit. The first hit after sleep takes ~10–30 s to wake the container, and
  then models warm in the background. Open the link a couple minutes before any
  live demo.
- **Ephemeral SQLite.** Storage resets on restart/redeploy. Uploaded footage,
  FAISS indexes, and any cases created during a session are **not** persisted.
  Demo accounts and the seed data **reseed automatically** on each boot (see
  above), so the baseline demo is always intact — but don't expect anything a
  visitor uploads to survive a restart.
- **Model download on first boot.** CLIP + YOLO weights download on the first run
  after a build (cached for the life of that container). This is why the first
  load is slower than later ones.
- **No GPU — CPU only.** This is by design: `VISIONSCAN_DEVICE=cpu`, and the whole
  stack (CLIP / YOLO / anomaly watch) is built to run on CPU. Expect inference to
  be a few seconds per query, not instant. Keep demo clips short (~10–60 s).
- **No face matching on the Space.** The Space builds `requirements-core.txt`,
  which omits InsightFace/ArcFace. Text, reference-image, and object search +
  anomaly watch all work; **suspect-face re-ID is a local/Docker-only feature**.

---

## 4. Link block for proposals / README

Paste this into the proposal PDFs and the README:

```
Live demo (Hugging Face Space):
  https://huggingface.co/spaces/iampreetdave/visionscan

Source code (GitHub):
  https://github.com/iampreetdave-max/Guardian-Angle

Note: the GitHub repository is PRIVATE until submission and will be made
available to the evaluation committee on request / at submission. The live
Space runs the core CPU stack (CLIP + YOLOv8 + FAISS) with demo data that
reseeds on each boot; sign in with a demo account (e.g. admin@city.gov /
admin123).
```

> The GitHub URL above is the project's `origin` remote
> (`iampreetdave-max/Guardian-Angle`). Confirm its visibility before sharing —
> keep it **private until submission** as noted.

---

## 5. Fallback — if the Space breaks near the deadline

If a build fails or the free Space is too slow/unstable close to the **20 June
2026** deadline, you have two documented backups:

1. **VPS path (production-grade).** Follow [`docs/DEPLOYMENT.md`](DEPLOYMENT.md):
   single Linux VM running the existing `docker compose` stack behind **Caddy**
   for automatic HTTPS on a real domain, with persistent named volumes
   (`visionscan-data`, `model-cache`, `insightface-cache`) so data and weights
   survive restarts, plus face matching and always-on uptime. This is the
   recommended *real* deployment and the strongest fallback for a stable link.
2. **Local demo (the offline story).** Run the full two-container stack on a
   laptop with `./start.ps1` (Windows) / `./start.sh` and open
   `http://localhost:8080`. For a temporary public URL with **no account or
   domain needed**, expose it via the Cloudflare quick tunnel documented in
   `deploy/HOSTING.md` (`./deploy/tunnel.ps1`). This is also the best on-stage
   demo: full hardware, face matching enabled, no cold start, and it doubles as
   the "runs fully offline in the field" narrative if the venue has no internet.

> Triage order near the deadline: (1) re-push to the Space and watch the build
> log; (2) if it won't build, stand up the VPS path; (3) if all else fails,
> demo locally + Cloudflare tunnel and submit the GitHub link.
