---
title: VisionScan
emoji: 🎥
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# CityShield · VisionScan — Unified AI Policing for Ahmedabad

> **A GIS crime-hotspot mapping and predictive patrol-routing command centre for
> the Cyber Crime Branch, Ahmedabad** — fusing physical and cyber crime on one
> map, forecasting next-week risk, and turning that risk into optimized patrol
> routes. CCTV AI is the differentiator: a live anomaly detected on camera
> auto-opens a case, bumps the risk surface, and dispatches the nearest unit —
> a real closed loop, not five demos stitched for a slide. Runs fully offline on
> a CPU.

[![tests](https://img.shields.io/badge/backend%20tests-77%20passing-2ea44f)](backend/tests)
[![license](https://img.shields.io/badge/license-MIT-blue)](#license)
[![Hugging Face Space](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Space-blue)](https://huggingface.co/spaces/iampreetdave/visionscan)
[![offline](https://img.shields.io/badge/runs-offline%20on%20CPU-0a1124)](#quick-start)

**KANAD S.H.I.E.L.D. 2026 Cybersecurity Hackathon** · Cyber Crime Branch,
Ahmedabad City Police · live pitch at i-Hub Gujarat. One codebase, five official
problem statements — see the [submissions table](#five-submissions-one-platform).

---

## The numbers

The predictive model is backtested with **rolling-origin (walk-forward) temporal
cross-validation** over the synthetic Ahmedabad complaint stream. These figures
come straight from the backtest CLI — reproduce them with:

```bash
cd backend
PYTHONPATH=. python scripts/predictive_backtest.py
```

> **Hit-Rate@10: 0.77 | PAI@10: 2.3x (oracle ceiling 2.5x) | capture 77% of
> next-week crime in 33% of the city (90% CI hit-rate@10 [0.74, 0.80], 8 weekly
> folds) | caught 3/3 planted surge-areas in the live top-10 during their surge
> week**

| Metric (mean over 8 weekly folds, 30 areas) | Model | 90% CI | Oracle ceiling |
|---|---|---|---|
| Hit-Rate@5 | **0.541** | [0.495, 0.585] | — |
| Hit-Rate@10 | **0.771** | [0.738, 0.803] | — |
| PAI@5 (Prediction Accuracy Index) | **3.25×** | [2.97, 3.51] | 3.54× |
| PAI@10 | **2.31×** | [2.22, 2.41] | 2.51× |

**Capture-rate curve** — share of next-week crime that lands inside the model's
top-k localities: top-5 (17% of the city) captures **54.1%**; **top-10 (33% of
the city) captures 77.1%**; top-15 (50%) captures 89.3%.

**Beats every baseline** at Hit-Rate@10 — model **0.771** vs. frequency 0.733,
prior-only 0.629, random 0.370 (a **+40.0 pt** lift over the random floor).
**Surge detection:** the model surfaced all 3 planted, time-boxed hotspots
(Maninagar chain-snatching, SG Highway + Satellite cyber-fraud ramp) into the
live top-10 during the weeks they were active.

> Computed on fully synthetic, deterministic demo data (see
> [docs/AHMEDABAD_CRIME_DATA.md](docs/AHMEDABAD_CRIME_DATA.md)). The numbers
> demonstrate the *methodology*, not real-world operational accuracy. See the
> [data disclaimer](#honest-data-disclaimer).

---

## How we hit every judging criterion

Mapping the flagship problem statement — **Crime Hotspot Mapping & Predictive
Patrol Routing (Cyber-Integrated), `PS-69EEFE1294451`** — to the module and the
file that implements it:

| # | Evaluation criterion | How we meet it | Where in the code |
|---|---|---|---|
| 1 | Accuracy of hotspot detection & prediction | Recency-weighted risk + priors + anomaly boost; backtested HR@10 0.771 / PAI@10 2.31× via rolling-origin CV | `backend/app/platform/predictive.py`, `backend/app/platform/validation.py` |
| 2 | Effectiveness of patrol-route optimization | Nearest-neighbour + 2-opt over live top-risk hotspots, haversine ETAs, balanced unit assignment | `backend/app/platform/patrol.py` |
| 3 | Integration of cyber + physical crime data | NCRP/1930-aligned cyber-fraud taxonomy + victim-location layer on the same GIS as physical crime | `backend/app/constants/cyber.py`, `backend/app/platform/seed_ahmedabad.py` |
| 4 | Performance & scalability | FastAPI + SQLite, CPU-only, additive schema, exact + lazy models; one-command Docker | `backend/app/main.py`, `docker-compose.yml` |
| 5 | Usability of GIS dashboard & visualization | react-leaflet map, 30 real localities, layered heatmaps, drill-down, why-this-hotspot explainability, accuracy panel, CSV export | `frontend/src/components/platform/CityMapView.jsx` |
| 6 | Innovation in predictive policing | Closed loop: live anomaly → auto case → risk bump → nearest-unit dispatch on one shared model | `backend/app/services/incident_loop.py` |
| 7 | Data security & compliance | JWT/RBAC, audit log, lockdown, rate limiting, SSRF + prompt-injection guards; documented testing report | `backend/app/security_mw.py`, `docs/SECURITY_TESTING_REPORT.md` |

---

## Module tour

**GIS Crime Hotspot Map (flagship).** An interactive react-leaflet command centre
over **30 real Ahmedabad localities** with layered views (reports, risk bands,
cyber-fraud), heatmaps, area drill-down, a *why-this-hotspot* explainability panel
that shows the risk score term by term, an accuracy panel quoting the live
backtest, and CSV exports. → `frontend/src/components/platform/CityMapView.jsx`

**Predictive risk model.** A transparent, auditable score —
`risk(area) = prior + Σ severity·category·decay(age) + anomaly_boost` with a
14-day half-life, min-max normalized 0–100, plus a one-window-ahead forecast and
rising/stable/falling trend. Seeded with NCRB/press-derived priors so a fresh
deployment ranks sensibly on day one. Backtested at
`GET /api/predict/validation`. → `backend/app/platform/predictive.py`

**Patrol routing.** Balanced greedy unit assignment → nearest-neighbour → 2-opt
over the live top-risk hotspots, with haversine distances and ETAs from a city
patrol pace — no external routing API, runs on CPU.
→ `backend/app/platform/patrol.py`

**VisionScan CCTV semantic search.** A unified **four-mode query router** over a
single offline vision index: natural-language text and reference-image search
(CLIP ViT-B/32 → FAISS `IndexFlatIP`, exact cosine), suspect-face
re-identification (InsightFace ArcFace), and object search (YOLOv8) all rank the
*same* adaptive keyframes, returning frames with camera ID + timestamp and
exporting a forensic, integrity-hashed PDF. → `backend/app/core/query_router.py`

**Anomaly Watch.** A hybrid CLIP+YOLO detector for fire, smoke, accident, weapon,
and violence, calibrated against a "normal scene" margin with debounce to suppress
false positives. Live events feed the closed loop.
→ `backend/app/core/anomaly.py`

**CityShield platform.** RBAC across citizen → officer → lead → admin; cases,
complaints with an **NCRP cyber-intake + golden-hour 1930 banner**, notifications,
and an analytics dashboard. → `backend/app/platform/`

**CrimeGPT.** From one unified case-data pool, generates **7 statutory
Gujarat-police documents** (Purvani Chargesheet, Medical Treatment Letter, Remand
Request, Seizure Receipt, Court Custody Letter, Accused Panchanama, Face
Identification Form) plus an automated Case Diary, with BNS/BNSS/BSA **section
intelligence over 30 offence patterns** and grounded judgment citations, in
en/hi/gu. → `backend/app/crimegpt/`

**GovIntel legal feed.** A Single Point of Access that searches a bundled offline
corpus plus key-free government RSS, categorizes results (GR/notification/Act/
judgment/scheme), extracts metadata, cross-links related documents, and supports
bookmarks and saved-search alerts. → `backend/app/govintel/`

**Arbiter legal AI.** RAG over a local IPC/IT-Act + BNS/BNSS/BSA corpus
(MiniLM/ChromaDB) with Gemini polish and a deterministic offline fallback, wrapped
in prompt-injection guards and a citation validator so it cites only retrieved
provisions. → `backend/app/arbiter/`

**Phase-3 security.** A four-layer OWASP middleware stack (rate limiting, security
headers, lockdown, metrics), upload + SSRF guards, and prompt-injection defences,
pinned by an automated pytest regression suite.
→ `backend/app/security_mw.py`, `docs/SECURITY_TESTING_REPORT.md`

---

## The closed-loop story

The differentiator is one genuine loop on a single shared data model:

1. **Detect** — Anomaly Watch flags fire/weapon/violence on a live feed
   (`backend/app/core/anomaly.py`).
2. **Open** — the event auto-creates a geo-tagged case with the keyframe attached
   as evidence (`backend/app/services/incident_loop.py`).
3. **Re-rank** — that locality's predictive risk surface is bumped immediately, so
   the map and forecast react in real time.
4. **Dispatch** — the nearest patrol unit (haversine over the units' latest
   check-ins, `backend/app/platform/patrol.py`) is dispatched via a notification.

Every step is fail-soft and wrapped so a failure here can never break ingestion.
The same case can then pull timestamped CCTV evidence frames (VisionScan), draft
its FIR and statutory documents (CrimeGPT/Arbiter), and surface relevant law
(GovIntel) — Detect → Analyse → Investigate → Prosecute → Engage end to end.

---

## Quick start

### Option A — One command (recommended)

Verifies Docker, generates a JWT secret into `.env` on first run, builds and
starts the stack, waits for health, then opens the app.

```powershell
# Windows
.\start.ps1
```
```bash
# Linux / macOS
./start.sh
```

First run pulls base images, downloads AI model weights (CLIP/YOLO/ArcFace) and
compiles the face engine — allow ~10–15 min. Subsequent runs take seconds and are
fully offline (weights are persisted in Docker volumes). Stop with `.\stop.ps1`
(Windows) or `docker compose down`.

Then open **http://localhost:8080** and sign in with a [demo account](#demo-accounts).

### Option B — Plain Docker Compose

```bash
docker compose up -d --build
# open http://localhost:8080  (API on http://localhost:8000/docs)
```

Configuration (ports, JWT secret, optional Gemini key / SMTP) lives in `.env` —
copy `.env.example` to `.env` to customize; the launcher does this for you. Every
value has a safe default, so the stack also runs with no `.env`. The Arbiter and
GovIntel summaries run fully offline without a Gemini key.

### Option C — Local dev

**Backend**
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000          # API docs: /docs
```

**Frontend**
```bash
cd frontend
npm install
npm run dev                                         # http://localhost:5173 (proxies /api)
```

**Run the predictive backtest (safe throwaway DB):**
```bash
cd backend
PYTHONPATH=. python scripts/predictive_backtest.py
```

---

## Demo accounts

Seeded by `backend/app/platform/seed.py` (DEV ONLY — password = role + `123`):

| Role | Email | Password |
|---|---|---|
| Admin / SHO | `admin@city.gov` | `admin123` |
| Team Lead | `lead@city.gov` | `lead123` |
| Officer | `officer@city.gov` | `officer123` |
| Citizen | `citizen@example.com` | `citizen123` |

---

## Five submissions, one platform

All five frame the **same CityShield / VisionScan codebase** against a different
official problem statement — each presents the relevant module as the product and
the rest as integrated companion modules. Branded proposal PDFs are generated by
`backend/scripts/gen_proposal.py` into [`docs/proposals/`](docs/proposals).

| # | Submission | Problem ID | Cat. | Abstract |
|---|---|---|---|---|
| 1 | VisionScan: Smart CCTV Analysis System for Investigation | `PS-69E9C85F9C307` | 1 | [abstract](docs/abstracts/abstract-1-visionscan-cctv.md) |
| 2 | Crime Hotspot Mapping & Predictive Patrol Routing (Cyber-Integrated) — **flagship** | `PS-69EEFE1294451` | 2 | [abstract](docs/abstracts/abstract-2-crime-hotspot.md) |
| 3 | Unified Legal & Government Intelligence Platform | `PS-69EEFDD4DA6E9` | 2 | [abstract](docs/abstracts/abstract-3-unified-legal.md) |
| 4 | CrimeGPT — AI-Powered Crime Documentation & Legal Intelligence | `PS-69EEFDFB90B99` | 2 | [abstract](docs/abstracts/abstract-4-crimegpt.md) |
| 5 | Open-Ended Innovation Platform for Smart Policing | `PS-69EEFE4F8CD1C` | 2 | [abstract](docs/abstracts/abstract-5-open-ended.md) |

Generate the proposal PDFs:

```bash
cd backend
PYTHONPATH=. python scripts/gen_proposal.py     # writes 5 PDFs into docs/proposals/
```

---

## Architecture & validation

- **Architecture:** see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the layered
  design (ingestion → embedding → detection → query → platform → security).
- **Validation:** see [docs/VALIDATION.md](docs/VALIDATION.md) for the full backtest
  methodology, metric definitions (Hit-Rate@k, PAI, capture curve, oracle ceiling),
  and how to reproduce every number. The live endpoint is
  `GET /api/predict/validation`.
- **Security:** [docs/SECURITY_TESTING_REPORT.md](docs/SECURITY_TESTING_REPORT.md)
  documents the OWASP coverage matrix, the 14 findings fixed during the build, and
  the regression suite (**77 backend tests passing**) that pins each control.
- **Demo-day script:** [docs/DEMO_DAY.md](docs/DEMO_DAY.md).
- **Deployment (VPS/Caddy):** [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## Honest data disclaimer

The neighbourhood-level crime intensities and the synthetic incident dataset that
seed the demo are **editorial estimates compiled from public sources (NCRB
reports, Gujarat Police/press coverage, municipal flood reporting) strictly for a
civic-tech demonstration** — *not* official crime ratings of any area. Crime in
India is officially published only at the city/zone level; there is **no official
open dataset that ranks Ahmedabad localities by crime intensity**, so every
locality-level rating is an editorial estimate. No real individuals are named
anywhere in the data or seeds. The backtest figures are computed on this synthetic
data and demonstrate the methodology, not real-world operational accuracy. AI
outputs (ranked CCTV frames, suggested legal sections, drafted documents) are
investigative decision-support and must be verified by an officer before use as
evidence or filing. Full framing in
[docs/AHMEDABAD_CRIME_DATA.md](docs/AHMEDABAD_CRIME_DATA.md).

---

## License

MIT — see the `license: mit` header above (Hugging Face Space metadata).

> Built for the Kanad S.H.I.E.L.D. 2026 hackathon, Cyber Crime Branch, Ahmedabad
> City Police. Submission deadline 20 June 2026.
</content>
</invoke>
