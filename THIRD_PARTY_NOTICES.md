# Third-Party Notices & Open-Source Compliance

Per the Kanad S.H.I.E.L.D. 2026 rules ("open-source libraries or frameworks
… must be properly documented and used in compliance with their respective
licenses"), this file documents the third-party components CityShield /
VisionScan depends on. **Our own source code is MIT-licensed (see `LICENSE`).**
All dependencies below are obtained at build/run time via `pip` and `npm` —
their code is **not** vendored into this repository — and each retains its own
license. Licenses are as published by each project; this list is maintained on
a best-effort basis.

## ⚠️ Notable: AGPL-3.0 dependency

- **Ultralytics YOLOv8** (`ultralytics==8.3.55`) — **AGPL-3.0**. Used unmodified,
  via pip, as one optional signal in the Anomaly Watch detector (the primary
  detector is CLIP zero-shot; YOLO adds object labels). It is not modified or
  redistributed by us. AGPL-3.0 carries a network-use copyleft clause; for a
  production deployment a team should either comply with AGPL (offer the
  corresponding source) or swap YOLO for a permissively-licensed detector. For
  this prototype it is documented here and used as published.

## Python backend (pip — see `backend/requirements.txt`)

| Package | Purpose | License |
|---|---|---|
| fastapi | Web API framework | MIT |
| uvicorn | ASGI server | BSD-3-Clause |
| python-multipart | Form/upload parsing | Apache-2.0 |
| pydantic, pydantic-settings | Validation / config | MIT |
| opencv-python-headless | Video / image I/O | Apache-2.0 |
| numpy | Numerics | BSD-3-Clause |
| Pillow | Image handling | HPND (permissive) |
| torch, torchvision | ML runtime (CPU) | BSD-3-Clause |
| transformers, tokenizers | CLIP model loading | Apache-2.0 |
| faiss-cpu | Vector similarity search | MIT |
| **ultralytics** | YOLOv8 detection | **AGPL-3.0** (see above) |
| insightface | ArcFace face matching (optional) | MIT |
| onnxruntime | ONNX inference | MIT |
| reportlab | Branded PDF generation | BSD-3-Clause |
| yt-dlp | Public live-stream URL resolve | Unlicense (public domain) |
| chromadb | RAG vector store (optional) | Apache-2.0 |
| google-generativeai | Optional Gemini generation | Apache-2.0 |
| PyJWT | JWT auth | MIT |
| bcrypt | Password hashing | Apache-2.0 |
| email-validator | Email validation | permissive (CC0/Unlicense) |
| psutil | Server monitoring | BSD-3-Clause |
| pytest, httpx | Testing | MIT / BSD-3-Clause |
| tqdm | Progress bars | MPL-2.0 / MIT |

## Frontend (npm — see `frontend/package.json`)

| Package | License |
|---|---|
| react, react-dom | MIT |
| vite | MIT |
| leaflet, react-leaflet | BSD-2-Clause / Hippocratic-MIT |
| lucide-react (icons) | ISC |
| axios | MIT |
| tailwindcss, autoprefixer, postcss | MIT |
| recharts / charting (if present) | MIT |

## Data, models & assets

- **CLIP (ViT-B/32)** and **YOLOv8** model weights are downloaded from their
  official sources at first run and cached; weights are not redistributed here.
- **Map tiles**: OpenStreetMap — map data © OpenStreetMap contributors, licensed
  under the Open Database License (ODbL). Tiles are fetched at runtime, not bundled.
- **Test clips** (`test_clips/`): Creative-Commons / public-domain footage from
  Wikimedia Commons — per-file source and license in `test_clips/MANIFEST.md`.
- **Legal & government corpus** (`backend/app/arbiter/corpus`,
  `backend/app/govintel/corpus`): excerpts/metadata of public Indian legal and
  government documents (statutes, GRs, notifications, judgments) with source
  links; public-record material used for retrieval/reference.
- **Crime statistics** (`docs/AHMEDABAD_CRIME_DATA.md`): editorial estimates
  grounded in public NCRB / press reporting; the live demo runs on **synthetic**
  data and contains no real personal or police records.
- **Logo / emblem** (`frontend/public/logo.*`): used to theme this submission
  for the Cyber Crime Branch context; it does not imply official endorsement.

## Originality

All application source code in this repository is the team's original work,
developed for Kanad S.H.I.E.L.D. 2026 (with AI-assisted development tooling). No
proprietary third-party source code or copyrighted concepts have been copied.
