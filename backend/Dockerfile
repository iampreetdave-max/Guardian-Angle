# VisionScan backend — CPU image (offline-capable field deployment).
# Full stack including face matching (insightface/ArcFace), which compiles from
# source — hence the build toolchain below. This is why face matching "just
# works" in Docker but not on a bare Windows host.
FROM python:3.11-slim

# Runtime libs (OpenCV / ffmpeg) + build toolchain for insightface's C/C++/
# Cython extensions (build-essential, cmake). The toolchain is only needed at
# pip-install time but kept minimal via --no-install-recommends.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1 libgomp1 ffmpeg \
    build-essential cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install torch CPU wheels first (smaller, no CUDA) then the rest.
# numpy + cython up front so insightface's source build finds them.
COPY requirements.txt .
RUN pip install --no-cache-dir numpy==1.26.4 cython && \
    pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

COPY app ./app

# Operator scripts (demo_reset, smoke tests, accuracy eval). Without these in
# the image there is no way to reset or verify the demo against the database the
# container actually uses — the host-side copy points at a different file.
COPY scripts ./scripts

# The test suite ships too: scripts/run_all_checks.py runs pytest as its first
# suite, and its purpose is to prove the build on the machine being demoed from.
COPY tests ./tests
COPY pytest.ini ./pytest.ini

# Bake the YOLO weights in. ultralytics resolves the bare name "yolov8n.pt"
# (config.py) by checking the working directory first, so landing it at
# /app/yolov8n.pt means it is never fetched over the network.
#
# This matters more than it looks: without it ultralytics downloads the file
# into /app, which is the container's *writable layer*, not a volume. Every
# `docker compose down` (stop.ps1) discards it, and the next start re-downloads
# from github.com. Offline, that download fails, detection.py catches the error
# and disables object detection *silently* — object search and weapon alerts go
# dead with nothing but a log line to show for it.
COPY yolov8n.pt ./yolov8n.pt

ENV VISIONSCAN_DATA_DIR=/data
VOLUME ["/data"]
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
