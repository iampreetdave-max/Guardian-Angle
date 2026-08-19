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

# Git Bash / MSYS on Windows rewrites arguments that look like absolute paths, so
# a container path such as -C /data arrives as C:/Program Files/Git/data. Disable
# that for docker only — exporting it globally instead breaks curl, which is a
# native Windows binary and does need the conversion for its output path. Inert
# on Linux, where a Codespace actually runs.
dockerx() { MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' docker "$@"; }


REPO="${DEMO_DATA_REPO:-iampreetdave-max/Guardian-Angle}"
TAG="${DEMO_DATA_TAG:-demo-data-v1}"
ASSET="visionscan-demo-data.tgz"
VOLUME="${DEMO_DATA_VOLUME:-visionscan_visionscan-data}"
URL="https://github.com/${REPO}/releases/download/${TAG}/${ASSET}"
# Published digest of the release asset; overridable for a new bundle.
EXPECT_SHA256="${DEMO_DATA_SHA256:-cd8471a31b016e61b55855e81c2248c6b13645e49495ab1e6d226d75762a64e6}"

echo "==> demo data: ${URL}"

# Already populated? Leave it alone — this must be safe to re-run.
if dockerx run --rm -v "${VOLUME}:/data" alpine test -f /data/visionscan.db 2>/dev/null; then
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

# Integrity check. A truncated download would otherwise surface much later as a
# corrupt SQLite file or a half-written FAISS index, which is far harder to
# diagnose than a failed checksum here.
if command -v sha256sum >/dev/null 2>&1; then
  got=$(sha256sum "$tmp/$ASSET" | cut -d' ' -f1)
  if [ -n "$EXPECT_SHA256" ] && [ "$got" != "$EXPECT_SHA256" ]; then
    echo "!! checksum mismatch — download looks corrupt, not restoring."
    echo "!!   expected $EXPECT_SHA256"
    echo "!!   got      $got"
    exit 0
  fi
  echo "==> checksum ok"
fi

dockerx volume create "$VOLUME" >/dev/null 2>&1 || true

# Piped through stdin rather than bind-mounting the temp directory: a host path
# from mktemp is not necessarily visible to the Docker daemon (notably on Windows
# with Git Bash, where /tmp/... is a shell-only construct), and stdin works
# identically everywhere.
if ! dockerx run --rm -i -v "${VOLUME}:/data" alpine tar xzf - -C /data < "$tmp/$ASSET"; then
  echo "!! extraction failed; leaving the volume as it was."
  exit 0
fi

n=$(dockerx run --rm -v "${VOLUME}:/data" alpine sh -c 'ls /data/videos 2>/dev/null | wc -l')
echo "==> restored: ${n} videos"
