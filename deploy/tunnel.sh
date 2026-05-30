#!/usr/bin/env bash
# VisionScan — expose the locally-running app via a free Cloudflare Quick Tunnel.
# See tunnel.ps1 for the Windows equivalent and full notes.
#
#   1. docker compose up --build        # serves UI on :8080
#   2. ./deploy/tunnel.sh                # prints a public https URL
#
# No Cloudflare account or domain required.
set -euo pipefail
PORT="${1:-8080}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared not found. Install it:"
  echo "  macOS:  brew install cloudflared"
  echo "  Linux:  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
  exit 1
fi

echo "Exposing http://localhost:${PORT} via Cloudflare Quick Tunnel…"
echo "Share the https://<...>.trycloudflare.com URL printed below."
cloudflared tunnel --url "http://localhost:${PORT}"
