# VisionScan — Demo-Day Playbook

For: **KANAD S.H.I.E.L.D. 2026** · Cyber Crime Branch, Ahmedabad City Police.
Audience: senior police officers + technical evaluators. They reward **practical
field value, data security, and credibility** over flashy ML.

---

## 1. The 60-second pitch (memorize this)

> "When a crime happens, investigators get hours of CCTV from dozens of cameras
> — and today they watch it frame by frame, for days. **VisionScan lets them
> just ask.** Type *'person in a red jacket near the gate'*, or upload a
> suspect's photo, and in seconds it returns the exact timestamped frames across
> every camera — ranked, grouped into events, and exportable as a forensic PDF.
> It runs **fully offline on a field laptop**, so it works at a crime scene with
> no internet, and the footage never leaves the investigator's machine. We built
> it on proven open models — CLIP, YOLOv8, and ArcFace — so there's no black box
> and no per-query cloud cost."

**The one line they'll remember:** *"Ctrl-F for CCTV — offline, in the field."*

---

## 2. Live demo runbook (5–6 minutes)

> Pre-stage before you present (see §4). Have 2–3 short clips already processed
> so you never wait on stage. Keep one camera unprocessed to show ingestion live.

| # | Action | What you say |
|---|--------|--------------|
| 1 | Open dashboard. Point at the **status bar** (device, CLIP/YOLO/ArcFace online, indexed-frame count). | "Everything's running locally on this laptop — no cloud." |
| 2 | **Live Feed tab → click a public feed** (or upload a clip). Show it flip Queued → Processing → Ready. | "It ingests any footage — a file, or a live public camera feed — and analyses it automatically." |
| 3 | **Text search:** `two people standing near a car`. | "Plain English. No tags, no metadata — it understands the *scene*." |
| 4 | Point out an **event badge** (e.g. "×9, 00:12–00:21"). | "It collapses 50 near-identical frames into one event, so you review moments, not duplicates." |
| 5 | **Object search:** `car` (click a chip). | "Need every vehicle? One click — that's YOLO object detection." |
| 6 | **Suspect Face tab:** upload a face photo → matches. | "Got a suspect's photo? ArcFace finds them across every camera." |
| 7 | Tick 3–4 best frames → **Generate Report** → open the PDF. | "And here's a court-ready evidence sheet — timestamps, cameras, confidence scores — in one click." |
| 8 | (Optional) Toggle a camera scope / multi-camera. | "Scope to one camera or search them all at once." |

**Closing line:** "From hours of manual scrubbing to seconds of search — offline,
in the field, with an audit trail."

---

## 3. Anticipated Q&A (drill these)

**Q: How accurate is it? Can we trust it as evidence?**
A: It returns **ranked candidate frames with confidence scores** — an
investigative aid that points you to the right minutes, not an automated verdict.
A human always verifies. The PDF footer states exactly this. It shrinks days of
review to minutes; the officer still makes the call.

**Q: Does footage leave the device? Is it secure?**
A: No. It runs **100% offline** — models and data stay on the local machine or
on-prem server. No internet, no third-party cloud, no API calls. Critical for
chain-of-custody and sensitive cases. (The hosted demo link is only for your
convenience in evaluating it.)

**Q: What hardware does it need in the field?**
A: A standard laptop — it's **CPU-first**; a GPU just makes it faster. We ship it
as a single Docker container, so deployment is one command, even on an air-gapped
machine.

**Q: How does it scale to a city's worth of cameras / long footage?**
A: Two things. **Adaptive keyframe sampling** keeps only visually distinct frames
(typically 10–50× fewer than full decode), and **FAISS** does exact vector search
over millions of frames in milliseconds. You process once, then search instantly,
repeatedly.

**Q: Natural-language and face recognition — what about bias / false matches?**
A: Confidence scores are surfaced on every result, search is exact (no
approximation that could silently mislead), and a human reviews every hit. Face
matching is a **lead generator**, used within an authorized investigation — never
an automated identification.

**Q: How is this different from existing CCTV/VMS software?**
A: Existing tools play back and bookmark footage; you still watch it. Ours is the
only one that unifies **semantic text search + reference-image + face + object**
in one offline tool, with **forensic report export** — built for field
investigation, not a control-room wall.

**Q: What about cameras you don't have legal access to?**
A: We deliberately don't touch unsecured/private cameras. The live-feed feature
is for **footage you're authorized to use** — your own CCTV exports or
intentionally-public government feeds. We built that guardrail into the product.

**Q: What's the tech, and is any of it a paid black box?**
A: All open, inspectable models — **CLIP** (semantic), **YOLOv8** (objects),
**InsightFace/ArcFace** (faces), **FAISS** (search), **FastAPI + React**. No paid
API, no per-query cost, no vendor lock-in.

**Q: What's next if you win / for production?**
A: Person re-identification across cameras (track one person's path through a
city), license-plate OCR, a proper case-management layer with user roles and an
audit log, and hardware-accelerated ingestion for real-time multi-camera feeds.

---

## 4. Pre-demo checklist

- [ ] Laptop charged + charger; **don't rely on venue Wi-Fi** (offline is the point).
- [ ] `docker compose up -d` run earlier; models already downloaded & cached.
- [ ] 2–3 short clips **already processed** (different `camera_id`s, e.g. CAM-Gate, CAM-Lobby).
- [ ] One suspect face photo on the desktop, ready to drag in (a person who appears in a processed clip).
- [ ] One clip left **unprocessed** to show live ingestion.
- [ ] Dashboard open at `http://localhost:8080`; status bar shows CLIP/YOLO/ArcFace online.
- [ ] A generated **sample PDF** already on disk as backup if export is slow live.
- [ ] Public **HF Spaces link** open in a phone/second tab as the "try it yourself" handoff.
- [ ] Rehearse the 8-step runbook end-to-end **twice**; time it under 6 minutes.

## 5. Slide outline (≤8 slides)

1. **Title** — VisionScan + one-line tagline + your name/team + PS-69E9C85F9C307.
2. **The problem** — a photo of an investigator buried in CCTV monitors; "days of manual review."
3. **The solution** — one screenshot of the dashboard with a search result; the "Ctrl-F for CCTV" line.
4. **How it works** — the 5-layer pipeline diagram (Ingestion → CLIP → Detection → Query → Report).
5. **Live demo** — (switch to the app; this is the slide you spend the most time *off*).
6. **Why it fits field investigation** — offline, CPU, forensic PDF, data never leaves device.
7. **Tech & credibility** — open models, exact search, human-in-the-loop; no black box.
8. **Impact & roadmap** — "hours → seconds"; re-ID, plate OCR, case management next.

---

## 6. Failure-recovery (if something breaks on stage)
- Search returns nothing → you queried an unprocessed camera; switch scope to "all feeds" or a ready camera.
- A model shows offline in the status bar → it's lazy-loaded; run one search to warm it, or note "it loads on first use."
- Live ingestion slow → switch to a pre-processed clip; "I pre-loaded these to respect your time."
- Whole app down → open the **HF Spaces link** as instant backup.
