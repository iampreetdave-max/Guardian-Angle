# Crime Hotspot Mapping & Predictive Patrol Routing System (Cyber-Integrated)

**Problem ID:** PS-69EEFE1294451 · **Category:** 2
**Hackathon:** Kanad S.H.I.E.L.D. 2026 — Cyber Crime Branch, Ahmedabad City
**Team:** _[team name placeholder]_ · **Members:** _[member placeholder]_

---

## Problem

Ahmedabad's FIRs, complaints, cyber-fraud reports, and patrol logs hold enormous
preventive value, but they sit in silos with no shared map, no temporal model,
and no link between cyber and physical crime — so policing stays reactive. The
Cyber Crime Branch needs a GIS platform that fuses these sources, finds and
forecasts hotspots, and converts that intelligence into concrete patrol routes
and deployment decisions, securely and in real time.

## Proposed Solution

This is the flagship: a GIS command-centre that ingests physical and cyber crime
into one spatial-temporal model over **30 real Ahmedabad localities** and turns
risk into action. Its differentiator is an **explainable, fully-offline
risk-to-route pipeline** — a transparent recency-weighted risk score (auditable
term by term, seeded with NCRB/press-derived priors so a fresh deployment ranks
sensibly on day one), a one-window-ahead forecast with rising/stable/falling
trend, and patrol routes computed by nearest-neighbour + 2-opt over the live
top-risk hotspots — no external routing API, runs on CPU. A dedicated
**cyber-intelligence layer** maps NCRP/1930-style fraud categories and victim
locations alongside physical crime, and live Anomaly Watch events feed a real-time
risk boost, closing the loop from detection to dispatch.

## Methodology

- **Data integration:** Complaints/FIRs, an NCRP-aligned cyber-fraud taxonomy
  (UPI/OTP, digital-arrest, investment, sextortion, loan-app, etc. with golden-hour
  flags), and patrol-log check-ins, normalized to a shared category + locality
  schema. A realistic synthetic Ahmedabad incident dataset (grounded in public
  NCRB/press reporting, every neighbourhood rating flagged as an editorial
  estimate) seeds the demo; live data ingests additively.
- **Models:** `risk(area) = prior + Σ severity·category·decay(age) +
  anomaly_boost` with a 14-day half-life; min-max normalized 0–100; trend from a
  recent-vs-previous window ratio. Temporal analytics by hour-of-day and
  day-of-week. Patrol routing: balanced greedy unit assignment → nearest-neighbour
  → 2-opt, haversine distances, ETA from city patrol pace.
- **Validation:** Backtesting on the synthetic dataset with **hit-rate@k** (did
  the top-k predicted hotspots contain tomorrow's incidents) and a **PAI**
  (Prediction Accuracy Index) metric — measured numbers, not adjectives.
- **Deployment:** FastAPI + SQLite + react-leaflet over OSM tiles; role-based
  access, audit logging, lockdown; one-command Docker; runs offline on CPU.

## Tools & Technologies

Python · FastAPI · SQLite · React + Vite · react-leaflet + OpenStreetMap tiles ·
NumPy · custom recency-decay risk model · NN + 2-opt TSP routing · OpenCLIP +
YOLOv8 (Anomaly Watch feed) · JWT/RBAC + OWASP security middleware · ReportLab ·
Docker.

## Key Differentiators

- **Cyber + physical fusion:** an NCRP/1930-style fraud taxonomy and victim-location
  map layer sit on the same GIS as physical crime — directly hitting the
  "integration of cyber and physical crime data" criterion.
- **Measured accuracy, not claims:** backtested with hit-rate@k and PAI on a
  documented synthetic dataset; the risk model is auditable term by term.
- **Risk-to-route in one loop:** prediction drives NN+2-opt patrol routes and
  deployment counts; live anomaly events re-rank risk in real time.
- **Offline & secure:** no external routing/cloud API; RBAC, audit logs, lockdown,
  rate limiting, and a documented security-testing report cover the data-security
  criterion.
- **Working prototype + HF Space:** interactive map, heatmap layers, drill-down,
  predictive bands, and patrol routes already render live.

## Expected Impact

By ranking and forecasting risk across 30 localities and pushing optimized routes
to patrol units, the platform shifts deployment from reactive to preventive and
gives command staff a single situational picture spanning cyber and street crime.
The prototype demonstrates end-to-end hotspot→forecast→route generation in
seconds, fully offline, with accuracy reported through hit-rate@k and PAI rather
than assertion.

> Neighbourhood-level intensities are editorial estimates compiled from public
> sources for demonstration, not official crime ratings of any area.
