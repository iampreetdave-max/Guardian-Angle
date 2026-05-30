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

# Pre-bundling weights into the image keeps the container fully offline.
# (Optional) uncomment to bake YOLO weights at build time:
# RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

ENV VISIONSCAN_DATA_DIR=/data
VOLUME ["/data"]
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
