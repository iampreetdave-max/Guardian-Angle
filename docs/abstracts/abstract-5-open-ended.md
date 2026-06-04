# Open-Ended Innovation Platform for Smart Policing (Cyber Crime Branch, Ahmedabad City)

**Problem ID:** PS-69EEFE4F8CD1C · **Category:** 2
**Hackathon:** Kanad S.H.I.E.L.D. 2026 — Cyber Crime Branch, Ahmedabad City
**Team:** _[team name placeholder]_ · **Members:** _[member placeholder]_

---

## Problem

Modern policing faces digital-first crime, exploding data volumes, and rising
demand for transparent, citizen-centric service — yet investigation tools,
analytics, evidence handling, and citizen interaction usually live in disconnected
systems. The Cyber Crime Branch needs one platform that ties AI-driven case
management, predictive analytics, cybercrime support, digital evidence, and
citizen engagement into a single, secure, deployable workflow.

## Proposed Solution

CityShield is the integrated platform the other four submissions are modules of —
one codebase that runs **Detect → Analyse → Investigate → Prosecute → Engage** end
to end. Its differentiator is a **genuine closed loop on one shared data model**:
Anomaly Watch (hybrid CLIP+YOLO fire/smoke/accident/weapon/violence detection)
raises a live alert, which auto-creates a case, boosts the predictive risk score
for that locality, and feeds patrol-route dispatch — while VisionScan CCTV search
supplies timestamped evidence frames, Arbiter/CrimeGPT drafts the FIR and grounded
BNS/BNSS/BSA documents, GovIntel surfaces relevant law, and a citizen portal
(NCRP/1930-style cyber-fraud intake with a golden-hour banner, complaint tracking,
ratings) bridges the public and the branch. Everything is JWT/RBAC-governed,
audit-logged, offline-capable on CPU, and security-hardened with a documented
testing report.

## Methodology

- **Data:** One SQLite model spanning complaints, cases, evidence, case documents,
  anomaly events, notifications, audit log, and patrol logs; a realistic synthetic
  Ahmedabad dataset (public-source-grounded) seeds the demo; live data ingests
  additively.
- **Models / intelligence:** CLIP + YOLOv8 (search + anomaly detection),
  ArcFace (faces), explainable recency-weighted predictive risk + NN/2-opt patrol
  routing, ChromaDB/MiniLM RAG legal AI with Gemini-or-offline generation, react-
  leaflet GIS over 30 real localities. AI calls are sanitized and prompt-injection
  guarded.
- **Validation:** Predictive backtesting with hit-rate@k and PAI; anomaly detector
  calibrated against a "normal scene" margin to suppress false positives; an
  automated pytest regression suite pins the security controls; closed-loop
  anomaly→case→dispatch demonstrated end to end.
- **Deployment:** FastAPI + React/Vite, four-layer OWASP security middleware (rate
  limiting, headers, lockdown, metrics), RBAC (citizen→officer→lead→admin), audit
  logging, one-command Docker, public Hugging Face Space; runs offline on CPU.

## Tools & Technologies

Python · FastAPI · SQLite · React + Vite + Tailwind · react-leaflet + OpenStreetMap ·
OpenCLIP · YOLOv8 · InsightFace ArcFace · FAISS · ChromaDB + MiniLM ·
Gemini-with-offline-fallback · ReportLab · JWT/RBAC + OWASP middleware + prompt-
injection guards · Docker.

## Key Differentiators

- **One real closed loop:** anomaly detection → auto case → risk boost → patrol
  dispatch on a shared model — not five demos stitched for a slide.
- **Cyber-integrated & citizen-centric:** NCRP/1930-aligned fraud intake with a
  golden-hour freeze nudge, complaint tracking, and ratings inside the same system
  officers investigate in.
- **Measurable impact:** predictive accuracy reported via hit-rate@k/PAI; documented
  security testing; explainable, auditable AI throughout.
- **Offline, secure, interoperable:** CPU-only Docker deployment, RBAC + audit +
  lockdown, additive SQLite schema with a clear CCTNS/FIR-integration path and an
  API-based architecture.
- **Working prototype + HF deployment:** the full platform runs today, multilingual
  (en/hi/gu), with seeded demo accounts.

## Expected Impact

CityShield demonstrates a single platform that takes a detected incident all the
way to a documented, prosecutable case with optimized patrol response and a
citizen kept in the loop — measurably reducing manual workload across detection,
analytics, and documentation while improving transparency through end-to-end audit
trails. Because it runs offline on commodity CPU hardware and exposes an API-based,
additive schema, the prototype is positioned for real-world piloting and future
integration with existing police systems (FIR/CCTNS) within the Cyber Crime Branch
ecosystem.
