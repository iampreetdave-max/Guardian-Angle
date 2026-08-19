#!/usr/bin/env bash
# Restore the pre-indexed demo data into the Docker volume.
#
# The 16 test clips are ~300MB and, more importantly, ingesting them takes
# 30-60 minutes of CPU. Shipping the ALREADY-INDEXED volume (videos, FAISS
# indexes, thumbnails, SQLite with detections and tracks) means a fresh
# Codespace is demo-ready in the time it takes to download, not to re-infer.
#
# Published as a GitHub Release asset rather than committed, so cloning the repo
# stays fast and the history does not carry 300MB of video forever.
set -euo pipefail

REPO="${DEMO_DATA_REPO:-iampreetdave-max/Guardian-Angle}"
TAG="${DEMO_DATA_TAG:-demo-data-v1}"
ASSET="visionscan-demo-data.tgz"
VOLUME="${DEMO_DATA_VOLUME:-visionscan_visionscan-data}"
URL="https://github.com/${REPO}/releases/download/${TAG}/${ASSET}"

echo "==> demo data: ${URL}"

# Already populated? Leave it alone — this must be safe to re-run.
if docker run --rm -v "${VOLUME}:/data" alpine test -f /data/visionscan.db 2>/dev/null; then
  n=$(docker run --rm -v "${VOLUME}:/data" alpine sh -c \
      "ls /data/videos 2>/dev/null | wc -l" || echo 0)
  if [ "${n:-0}" -gt 1 ]; then
    echo "==> volume already has ${n} videos; skipping restore"
    exit 0
  fi
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

if ! curl -fL --retry 3 --retry-delay 5 -o "$tmp/$ASSET" "$URL"; then
  echo "!! could not download the demo data."
  echo "!! The app still works — it self-seeds complaints, cases and the map."
  echo "!! Only the VisionScan video search will be empty. Upload a clip to fill it."
  exit 0          # never fail the codespace over optional demo footage
fi

docker volume create "$VOLUME" >/dev/null 2>&1 || true
docker run --rm -v "${VOLUME}:/data" -v "$tmp:/in" alpine \
  sh -c "tar xzf /in/${ASSET} -C /data"

echo "==> restored: $(docker run --rm -v "${VOLUME}:/data" alpine sh -c 'ls /data/videos | wc -l') videos"
