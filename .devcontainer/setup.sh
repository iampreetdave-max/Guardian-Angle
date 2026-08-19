#!/usr/bin/env bash
# Codespace first-boot: build the stack, then restore the pre-indexed demo data.
#
# Order matters. The restore has to run AFTER the stack exists, because the volume
# name is derived from the compose project (the directory basename), so it can
# only be discovered from a real container. And the backend must be stopped while
# the database is replaced — extracting over a SQLite file that a live process
# holds open in WAL mode is how you get a corrupt database.
set -euo pipefail
cd "$(dirname "$0")/.."

cp -n .env.example .env 2>/dev/null || true

echo "==> building and starting the stack (first run: 10-15 min)"
docker compose up -d --build

echo "==> stopping backend so the database can be replaced safely"
docker compose stop backend || true

echo "==> restoring the pre-indexed demo data"
bash deploy/fetch-demo-data.sh || echo "!! demo data restore skipped; the app still self-seeds"

echo "==> starting backend on the restored data"
docker compose start backend || docker compose up -d backend

echo
echo "==> done. Open the Ports tab, set port 8080 to Public, then open it."
echo "==> sign in as admin@city.gov / admin123"
