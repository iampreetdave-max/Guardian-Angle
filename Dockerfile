# ─────────────────────────────────────────────────────────────────────────
# VisionScan — single-container build for Hugging Face Spaces (Docker SDK).
# Builds the React dashboard and serves it together with the FastAPI backend
# on port 7860 (HF Spaces default). Uses the core stack (CLIP + YOLOv8 + FAISS)
# for fast, reliable cold starts on the free CPU tier; face matching (ArcFace)
# is available in the full local/Docker deployment — see docker-compose.yml.
# ─────────────────────────────────────────────────────────────────────────

# ---- Stage 1: build the frontend ----
FROM node:20-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: backend + static frontend ----
FROM python:3.11-slim

# OpenCV / video decode runtime libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1 libgomp1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces runs containers as UID 1000 — set up a writable home for caches/data
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    TORCH_HOME=/home/user/.cache/torch \
    YOLO_CONFIG_DIR=/home/user/.config/Ultralytics \
    VISIONSCAN_DATA_DIR=/home/user/data \
    VISIONSCAN_DEVICE=cpu \
    VISIONSCAN_STATIC_DIR=/home/user/app/app/static

WORKDIR /home/user/app

COPY --chown=user backend/requirements-core.txt ./requirements-core.txt
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements-core.txt

COPY --chown=user backend/app ./app
COPY --chown=user --from=frontend /fe/dist ./app/static

USER user
EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
