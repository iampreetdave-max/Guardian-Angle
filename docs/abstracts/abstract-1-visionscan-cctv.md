# VisionScan: Smart CCTV Analysis System for Investigation

**Problem ID:** PS-69E9C85F9C307 · **Category:** 1
**Hackathon:** Kanad S.H.I.E.L.D. 2026 — Cyber Crime Branch, Ahmedabad City
**Team:** _[team name placeholder]_ · **Members:** _[member placeholder]_

---

## Problem

Investigators reviewing CCTV in theft, missing-person, accident, and terrorism
cases must scrub through hours of footage from many cameras by hand to find one
person, vehicle, or object. This is slow, error-prone, and demands technical
skill that field teams rarely have on hand. There is no simple, offline-capable
tool that lets an officer search long footage by plain-language description or a
reference photo and pull out timestamped, exportable evidence frames.

## Proposed Solution

VisionScan is a working web tool that turns hours of CCTV into a searchable index
an officer queries the way they think — *"person in a red jacket near the gate"*,
a suspect's photo, or an object class like `white van`. Its differentiator is a
**unified four-mode query router over a single offline vision index**: CLIP
semantic text + reference-image search, ArcFace suspect-face re-identification,
and YOLOv8 object search all rank the *same* adaptive keyframes, returning frames
with timestamp and camera ID and exporting a forensic PDF. It runs fully offline
on CPU once models are cached, so it works in field conditions with no cloud and
weak hardware. CityShield case management, Arbiter legal AI, and Anomaly Watch
ship as integrated companion modules, so a found frame attaches straight to a
case as evidence.

## Methodology

- **Data / ingestion:** Ingest `.mp4/.avi/.mov` from multiple cameras (batch
  upload); OpenCV adaptive keyframe sampling (scene-change + motion delta) keeps
  every distinct moment while cutting 10–50× of redundant frames; CLAHE
  enhancement for night/IR footage.
- **Models:** CLIP ViT-B/32 → 512-d embeddings in a FAISS `IndexFlatIP` (exact
  cosine, explainable scores — no approximation); YOLOv8 objects; InsightFace
  ArcFace faces. Models load lazily and fail-soft — if one can't load on weak
  hardware, that mode disables itself and search keeps working.
- **Validation:** Multi-camera demo over sample footage; ranked frames carry the
  raw similarity score; export integrity hash for chain-of-custody.
- **Deployment:** One-command Docker; CPU-first with automatic GPU use; persistent
  indexes survive restarts; deployed as a public Hugging Face Space prototype.

## Tools & Technologies

Python · FastAPI · OpenCV · OpenCLIP/HuggingFace transformers · YOLOv8
(Ultralytics) · InsightFace ArcFace · FAISS · SQLite · React + Vite + Tailwind ·
ReportLab (forensic PDF) · Docker. Optional Gemini (with offline fallback) for
companion modules; multilingual keyword input (English/Hindi/Gujarati).

## Key Differentiators

- **Innovation in vision + NLP:** one router fuses semantic text, image, face,
  and object search over a single index — not four disconnected tools.
- **Offline & field-ready:** runs CPU-only in Docker with cached models; lazy
  fail-soft loading degrades gracefully on weak hardware.
- **Forensically sound:** exact FAISS search gives explainable scores; timestamped
  frames + camera ID + integrity-hashed PDF exports.
- **Robust footage handling:** adaptive keyframing and CLAHE cope with varied
  angles, resolution, and low/IR light.
- **Working prototype, not slideware:** live dashboard with timeline view,
  multi-camera scoping, search history, and a public Hugging Face deployment.

## Expected Impact

By replacing manual scrubbing with second-scale semantic and visual search,
VisionScan can collapse the footage-review phase of an investigation from hours
to minutes per query, letting a non-technical officer find a suspect across
multiple feeds and hand a court-ready, timestamped PDF straight into the case
file. The same offline, CPU-friendly design means it deploys at a thana or a
field post without cloud access or specialist hardware.

> AI-ranked frames are investigative leads and must be verified by an
> investigator before being treated as evidence.
