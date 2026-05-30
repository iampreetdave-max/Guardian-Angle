<!-- The YAML block below configures Hugging Face Spaces (Docker SDK). It is
     harmless on GitHub. See deploy/HOSTING.md for deployment steps. -->
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

# VisionScan — Smart CCTV Analysis System for Investigation

> AI-powered CCTV investigation tool. Search hours of surveillance footage in
> seconds using **natural language**, a **reference image**, a **suspect's
> face**, or **object type** — and export a forensic PDF of timestamped
> evidence frames. Built for field investigators with limited hardware and
> connectivity.

**KANAD S.H.I.E.L.D. 2026 Cybersecurity Hackathon** · Problem ID `PS-69E9C85F9C307`
· Cyber Crime Branch, Ahmedabad City Police.

---

## What it does

| Capability | How |
|---|---|
| 🔎 Natural-language search | `"person in red jacket near the gate"` → CLIP semantic match |
| 🖼️ Reference-image search | Upload a still → CLIP visual similarity |
| 🧑 Suspect-face matching | Upload a photo → InsightFace ArcFace identity match |
| 📦 Object search | `car`, `person`, `truck`… → YOLOv8 detections |
| 🎥 Multi-camera sessions | Search all feeds at once or scope to one camera |
| 🌙 Low-light handling | Adaptive CLAHE enhancement for night/IR footage |
| 📄 Forensic reports | Export selected frames as a timestamped PDF |
| 📴 Offline field use | Runs fully offline in Docker once models are cached |

---

## Architecture (5 layers)

```
1. Ingestion   OpenCV adaptive keyframe sampling (scene-change + motion delta)
2. Embedding   CLIP ViT-B/32 → 512-d vectors → FAISS IndexFlatIP (cosine)
3. Detection   YOLOv8 (objects) + InsightFace ArcFace (faces, own FAISS index)
4. Query       Unified router: text | image | face | object  → ranked frames
5. Output      React dashboard · timeline · multi-camera · PDF report (ReportLab)
```

**Stack:** OpenCV · CLIP (HuggingFace transformers) · YOLOv8 (Ultralytics) ·
InsightFace · FAISS · FastAPI · React + TailwindCSS · SQLite · ReportLab · Docker.

```
VisionScan/
├── backend/          FastAPI + the pipeline
│   └── app/
│       ├── core/        ingestion, preprocessing, embedding, index,
│       │                detection, query_router  (layers 1–4)
│       ├── services/    pipeline orchestration, PDF report
│       ├── api/         REST routes
│       ├── config.py · database.py · schemas.py · main.py
├── frontend/         React + Tailwind investigator dashboard (layer 5)
├── data/             videos, thumbnails, FAISS indexes, SQLite (gitignored)
└── docker-compose.yml
```

### Design decisions
- **Lazy + fail-soft models** — CLIP/YOLO/ArcFace load on first use; if a model
  can't load on weak field hardware, that feature disables itself and core
  search keeps working.
- **CPU-first, GPU-auto** — detects CUDA but defaults to CPU.
- **Exact search (IndexFlatIP)** — no approximation; scores are explainable,
  which matters for forensic credibility.
- **Adaptive keyframes** — typically 10–50× fewer frames than full decode while
  keeping every visually distinct moment.
- **Persistent indexes** — process footage once, search repeatedly, survive
  restarts. Critical for offline deployments.

---

## Quick start

### Option A — Docker (recommended, offline-capable)
```bash
docker compose up --build
# open http://localhost:8080
```
First run downloads model weights (CLIP/YOLO/ArcFace) and caches them in named
volumes; subsequent runs are fully offline.

### Option B — Local dev

**Backend**
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
# open http://localhost:5173  (proxies /api to :8000)
```

**Ingest footage from the CLI (demo prep)**
```bash
cd backend
python -m scripts.ingest path/to/footage.mp4 --camera CAM-Gate-1
```

---

## API summary

| Method | Endpoint | Purpose |
|---|---|---|
| `GET`  | `/api/health` | device + which models are online + index size |
| `POST` | `/api/videos` | upload footage (multipart) → background processing |
| `GET`  | `/api/videos` | list feeds + processing status |
| `DELETE`| `/api/videos/{id}` | remove a feed and its vectors |
| `POST` | `/api/search/text` | natural-language query |
| `POST` | `/api/search/object` | YOLO object-class query |
| `POST` | `/api/search/image` | reference-image query (multipart) |
| `POST` | `/api/search/face` | suspect-face query (multipart) |
| `POST` | `/api/report` | generate forensic PDF from selected frames |

---

## Demo-day flow
1. Upload 2–3 short clips tagged as different cameras (`CAM-Gate`, `CAM-Lobby`).
2. Watch them flip to **Ready** as background processing finishes.
3. Run a text query (`"man with a backpack"`), then an object query (`car`).
4. Upload a suspect photo → face match across feeds.
5. Tick the best frames → **Generate Report** → download the timestamped PDF.

> ⚠️ AI-ranked frames are investigative leads and must be verified by an
> investigator before use as evidence.
