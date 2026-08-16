# CityShield / VisionScan — Demo-Day Stage Runbook

For: **KANAD S.H.I.E.L.D. 2026** · Cyber Crime Branch, Ahmedabad City Police ·
live pitch at i-Hub Gujarat. Audience: senior police officers + technical
evaluators. They reward **practical field value, data security, and credibility**
over flashy ML. Time budget on stage: **6 minutes** of clicking + Q&A.

> This is the operational runbook. For the architecture/feature inventory see the
> README; for the honest accuracy evidence see `docs/VALIDATION.md`.

---

## 0. The 30-second framing (say this first)

> "CityShield is one offline platform that takes a city from **sensing** to
> **action**. A camera flags an anomaly, it becomes a geo-tagged case, the map
> shows where crime is concentrating and where to patrol next, and CrimeGPT drafts
> the paperwork — all on a field laptop, no cloud, no footage leaving the machine."

**The one line they'll remember:** *"From the camera to the chargesheet — offline."*

---

## 1. Pre-stage checklist (do this BEFORE you walk up)

Run these in order; the whole thing takes ~3 minutes.

- [ ] **Launch the app first**: `.\start.ps1`. It reuses the already-built images
      and does **not** touch the network. Open **http://localhost:8080** and sign
      in as `admin@city.gov / admin123`.
      > Stop your other Docker projects first — `docker stop $(docker ps -q)`.
      > Several stacks running alongside this one will starve the daemon on 16 GB.
- [ ] **Reset to a known-good state** (backs up the DB, re-seeds, self-verifies).
      Run it **inside the container** — the Docker stack reads the
      `visionscan-data` volume at `/data`, *not* the host `data/visionscan.db`, so
      running this on the host resets a database the demo never opens:
      ```powershell
      docker compose exec backend sh -c "cd /app && PYTHONPATH=. python scripts/demo_reset.py"
      ```
      Wait for the green **`DEMO READY — all 15 checks passed`** banner. If it
      prints a red banner, fix the named check before presenting (or restore the
      `.bak` it just made).
      > Only run this on the host (`cd backend; PYTHONPATH=. python scripts/demo_reset.py`)
      > if you are demoing from the local venv rather than Docker.
- [ ] **Warm the map once while you still have internet** — open the **City Map**
      tab and pan/zoom around Ahmedabad so Leaflet caches the OSM basemap tiles in
      the browser. If venue Wi-Fi dies later, the cached tiles (and all data
      layers) still render; if tiles do fail you'll get a styled offline chip, not
      broken-image gray.
- [ ] **Export one PDF in advance as a backup** — open any case in CrimeGPT and
      generate a chargesheet PDF; keep it on the desktop. If live export is slow on
      stage, open this instead. (Every report PDF now carries an
      `Integrity SHA-256` footer + `X-Integrity-SHA256` header — point at it if
      asked about chain-of-custody.)
- [ ] Have the **staged anomaly clip** ready and know which camera you'll attach
      it to. Note `test_clips/` subfolders are gitignored and ship **empty** —
      restore them with `python test_clips\fetch_all.py fire` *before* the day.
      The 16 real street/market/CCTV clips in `test_clips/real/` are already
      ingested as CAM-01..CAM-16 and are the better material for the search demo.
- [ ] **Public URL, if you want one**: `.\deploy\share.ps1` prints a
      `https://<random>.trycloudflare.com` address for the locally-running stack.
      Generate it on the day — the URL changes every run.
      > The **HF Space is not a fallback any more.** Docker Spaces went paid-only
      > (~8 Jul 2026) and free-account Docker Spaces are reported to stay stuck in
      > "Paused". Do not put that link on a slide without testing it first.
- [ ] Laptop charged + charger. **Do not rely on venue Wi-Fi** — offline is the point.
- [ ] Rehearse §2 end-to-end **twice**; time it under 6 minutes.

**Demo accounts** (also printed by `demo_reset.py`, sourced from `seed.py`):

| Role | Email | Password |
|---|---|---|
| Admin / SHO | `admin@city.gov` | `admin123` |
| Team Lead | `lead@city.gov` | `lead123` |
| Officer | `officer@city.gov` | `officer123` |
| Citizen | `citizen@example.com` | `citizen123` |

---

## 2. The 6-minute click-path (with timestamps)

> Stay logged in as **admin** (sees everything). Speak the *value*, not the UI.

| t | Action | What you say | If it fails → do this |
|---|---|---|---|
| **0:00** | **City Map → Reports** layer. Point at the dense circles over the eastern belt (Vatva, Bapunagar, Naroda). | "Every complaint and case, mapped to 30 Ahmedabad localities. Crime concentrates — and the map shows it instantly." | Map blank → you skipped the reset; the side panels (hotspots, accuracy) still tell the story. Tiles gray → the offline chip appears; carry on, data layers are live. |
| **0:40** | Switch to **Risk forecast** layer → click the top hotspot → open **"Why this hotspot?"**. | "This isn't a heatmap of the past — it's a *forecast*. And it explains itself: this score is *prior + recent snatching + a live anomaly boost*, decayed by recency. No black box." | Popover empty → expand the same area in the right-hand **Top predicted hotspots** list instead. |
| **1:30** | Open the **Model accuracy (backtested)** panel → read the **surge** line and the **79% capture** line. | "We backtested it honestly — rolling-origin, no future data leaks. The top-10 zones hold **79% of next-week crime**, and it caught **3 of 3 planted crime waves** the week they happened. It beats frequency, prior and random baselines." | Panel still loading → quote from `docs/VALIDATION.md` on screen/print: HR@10 0.79, PAI@10 2.37× (oracle 2.53×). |
| **2:30** | Toggle the **Cyber fraud** layer. Point at the ₹ headline chip. | "Switch to the cyber lens — victim-location density, with the rupees actually lost. This is the 1930 / NCRP picture for the city." | Headline reads ₹0 → switch the window selector to **90 days**; the chip recomputes. |
| **3:10** | Back to **Risk forecast** → set **2 units** → **Plan patrol routes**. | "Now act on it: the planner routes patrol units through the top hotspots — nearest-neighbour plus 2-opt — with distance and ETA per unit." | Routes don't draw → re-click Plan; if still nothing, show the **Patrol plan** card text in the side panel. |
| **3:50** | **Closed loop**: ingest the staged **fire clip** on a camera (Live Feed / upload). Wait for the **anomaly alert** to pin. | "Here's the loop that matters. A camera sees fire — Anomaly Watch flags it…" | Ingest slow → use a feed you pre-processed; "I pre-loaded this to respect your time." |
| **4:30** | Show the **auto-created case** + the **dispatch notification** to the nearest unit. | "…and the platform *acts*: it spawns a geo-tagged case with the keyframe as evidence, bumps that area's risk, and dispatches the nearest unit. Sensing to action, automatically." | Auto-case missing → open Cases; the anomaly card links to its case once created. |
| **5:00** | **CrimeGPT** → open a case → show the **unified pool** → **Suggest BNS sections**. | "One data pool per case. CrimeGPT suggests the right **BNS / BNSS** sections from the facts — snatching → BNS 304; OTP fraud → BNS 318 + IT Act 66C/66D." | Suggestions empty → use a case with a fuller description (the seeded snatching case works). |
| **5:30** | **Generate chargesheet PDF** → open it. Point at the **Integrity SHA-256** footer. | "And it drafts the statutory document — branded, in English/Hindi/Gujarati — with a tamper-evident **SHA-256 integrity stamp** in the footer for chain-of-custody. The officer verifies and signs." | Export slow → open the **backup PDF** from the desktop. |
| **5:50** | **GovIntel → Legal Feed**: show a **saved-search alert** landing in notifications. | "And officers stay current — saved searches over GRs, notifications and judgments push alerts into the same inbox." | Feed offline → the bundled corpus still searches; say "live RSS is opt-in, the corpus works offline." |

**Closing line (6:00):** "Sensing, prediction, action, and paperwork — one offline
platform, with an audit trail and honest, backtested numbers."

---

## 3. Judge Q&A bank (drill these)

**Q: Where does the data come from? Is this real Ahmedabad crime data?**
A: The map and all accuracy numbers run on a **fully synthetic, deterministic**
incident stream we generate (`seed_synthetic.py`, fixed seed) from editorial,
public-sourced area intensities — **not** real per-neighbourhood records (India
publishes crime at city/zone level only). It's clearly labelled in the UI and in
`docs/AHMEDABAD_CRIME_DATA.md`. The point is to demonstrate the **methodology and
pipeline**; drop in a station's real CSV and the same engine runs on it.

**Q: How do you know the prediction actually works? What's the methodology?**
A: **Rolling-origin (walk-forward) temporal cross-validation** — the field-standard
way to grade hotspot maps. For each weekly fold we predict using only complaints
that existed *before* the fold, then grade against the next 7 days; no future data
ever leaks. We report **Hit-Rate@k** and **PAI@k** (Chainey 2008) with **90%
bootstrap CIs**, against random/prior/frequency baselines and a perfect-hindsight
**oracle ceiling**. Live numbers: **HR@10 0.79, PAI@10 2.37× of a 2.53× ceiling,
79% capture in the top-10, 3/3 planted surges caught.** Re-run it yourself:
`python scripts/predictive_backtest.py`. Full report: `docs/VALIDATION.md`.

**Q: Privacy / DPDP — what about citizens' data and footage?**
A: It runs **100% offline** — models and data stay on the local machine or on-prem
server; no cloud, no third-party API, no footage leaving the device. Role-based
access (admin/officer/citizen) gates every screen; anomaly alerts and risk maps
are staff-only, never citizen-facing. Report PDFs carry a **SHA-256 integrity
stamp** (footer + response header) so a printed copy is tamper-evident — chain of
custody. Face matching is a **lead generator** inside an authorized investigation,
never an automated identification.

**Q: Does it scale to a city's worth of cameras and history?**
A: Yes. CCTV search uses **adaptive keyframe sampling** (10–50× fewer frames than
full decode) + **FAISS** exact vector search over millions of frames in
milliseconds — process once, search instantly. The predictive model is pure
standard-library Python (no numpy/sklearn), recomputed cheaply and cached. It's
**CPU-first** and ships as a single container — one command on an air-gapped
machine.

**Q: False positives — both in anomaly detection and in the risk map?**
A: Anomaly Watch is **hybrid** (CLIP zero-shot scene scoring calibrated against
"normal scene" prompts + YOLO object signals) with a **margin threshold and event
debounce**, so a single noisy frame doesn't ping anyone; only sustained,
above-margin events on live feeds alert. The risk map is **decision support, not
evidence** — every score shows its decomposition and the model card; officers
verify. We surface confidence everywhere and a human is always in the loop.

**Q: How is this different from existing CCTV/VMS or analytics software?**
A: Existing tools play back footage or show a dashboard; you still watch and you
still act manually. CityShield **closes the loop** — a live anomaly becomes a
case becomes a dispatch — and unifies semantic CCTV search, a self-explaining
predictive map, patrol routing, and BNS-aware document drafting in **one offline
tool** with an audit trail. Built for field investigation, not a control-room wall.

**Q: What's the tech, and is any of it a paid black box?**
A: All open, inspectable models — **CLIP** (semantic), **YOLOv8** (objects),
**InsightFace/ArcFace** (faces), **FAISS** (search), **FastAPI + React + SQLite**.
The legal AI (Arbiter/CrimeGPT) uses Gemini when a key is present but has a full
**offline, citation-grounded fallback**, so nothing is gated on a paid API.

**Q: What's next for production?**
A: Person re-identification across cameras, license-plate OCR, hardware-accelerated
multi-camera ingestion, and integrating a station's real records behind the same
RBAC + audit layer.

---

## 4. Failure-recovery quick reference

- **Venue Wi-Fi dies / map tiles gray** → the City Map shows a styled
  *"Map tiles unavailable — running offline; data layers still live"* chip; all
  circles, routes and panels keep working. Pre-warming tiles (§1) avoids it
  entirely. Everything else is offline by design.
- **A model shows offline / first action is slow** → models are lazy-loaded; the
  first search/ingest warms them. Say "it loads on first use" and continue.
- **Live ingestion slow** → switch to a pre-processed feed; "I pre-loaded these."
- **PDF export slow** → open the backup PDF you exported in §1.
- **Demo state looks wrong (empty map, no cases)** → you skipped the reset; re-run
  `python scripts/demo_reset.py` (it's idempotent and self-verifies).
- **Whole app down** → open the **HF Space** link as an instant backup.

---

## 5. Wi-Fi-death plan (the venue has none / it dies mid-demo)

1. **You don't need it.** The backend, models, DB, predictive backtest, anomaly
   detection, CrimeGPT (offline fallback) and report export all run locally.
2. The **only** thing that wants the network is the **OSM basemap**. You warmed
   the tiles in §1, so they're cached; if not, the offline chip appears and the
   data layers still render over the navy background.
3. **GovIntel live RSS** is the other network feature — it's **opt-in**; the
   bundled corpus searches offline, so just say so.
4. If you want to *prove* offline on stage: turn Wi-Fi **off** before you start.
   The reset, the map data, the backtest, the closed loop and the chargesheet all
   work — which is exactly the field-deployment story.

---

## 6. Slide outline (≤8 slides, spend most time *off* them)

1. **Title** — CityShield / VisionScan + "from the camera to the chargesheet" + team + submission IDs.
2. **The problem** — fragmented tools: footage you scrub by hand, no forecast, manual paperwork.
3. **The platform** — one diagram: Sense → Predict → Act → Document, all offline.
4. **Live demo** — (switch to the app; this is the slide you spend the most time off).
5. **Honest accuracy** — the `docs/VALIDATION.md` numbers + methodology (rolling-origin, baselines, CI).
6. **Security & privacy** — offline, RBAC, integrity-stamped PDFs, human-in-the-loop.
7. **Tech & credibility** — open models, no paid black box, single-container deploy.
8. **Impact & roadmap** — closed-loop policing today; re-ID, plate OCR, real records next.
