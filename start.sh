#!/usr/bin/env bash
# CityShield / VisionScan — one-command launcher for Linux / macOS.
#   ./start.sh           build + start + open browser
#   ./start.sh --logs    ...then stream logs
#   ./start.sh --rebuild force a no-cache rebuild
set -euo pipefail
cd "$(dirname "$0")"

cyan(){ printf '\n==> %s\n' "$1"; }
warn(){ printf '    %s\n' "$1"; }
die(){ printf '\nERROR: %s\n' "$1" >&2; exit 1; }

# 1. Docker present + running
command -v docker >/dev/null 2>&1 || die "Docker is not installed: https://docs.docker.com/engine/install/"
docker info >/dev/null 2>&1 || die "Docker daemon is not running. Start Docker and re-run."

# 2. .env bootstrap with a random JWT secret
if [ ! -f .env ]; then
  cyan "First run — creating .env from .env.example"
  cp .env.example .env
  secret=$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 48 || true)
  if [ -n "$secret" ]; then
    if sed --version >/dev/null 2>&1; then       # GNU sed (Linux)
      sed -i "s/^VISIONSCAN_JWT_SECRET=.*/VISIONSCAN_JWT_SECRET=$secret/" .env
    else                                          # BSD sed (macOS)
      sed -i '' "s/^VISIONSCAN_JWT_SECRET=.*/VISIONSCAN_JWT_SECRET=$secret/" .env
    fi
    warn "Generated a random JWT secret in .env"
  fi
fi

# Host ports for the URLs we print/open
FRONTEND_PORT=$(grep -E '^\s*FRONTEND_PORT=' .env 2>/dev/null | cut -d= -f2 | tr -d ' ' || true); FRONTEND_PORT=${FRONTEND_PORT:-8080}
BACKEND_PORT=$(grep -E '^\s*BACKEND_PORT=' .env 2>/dev/null | cut -d= -f2 | tr -d ' ' || true);  BACKEND_PORT=${BACKEND_PORT:-8000}

# 3. Build + start
if [ "${1:-}" = "--rebuild" ]; then
  cyan "Rebuilding images from scratch..."
  docker compose build --no-cache
fi
cyan "Starting the stack..."
warn "First run downloads AI models and compiles the face engine — can take 10-15 min."
docker compose up -d --build

# 4. Wait for health
cyan "Waiting for the backend to become healthy..."
health="http://localhost:${BACKEND_PORT}/api/health"
front="http://localhost:${FRONTEND_PORT}"
ready=""
for _ in $(seq 1 90); do
  if curl -fsS "$health" >/dev/null 2>&1; then ready=1; break; fi
  printf '.'; sleep 4
done
printf '\n'

if [ -n "$ready" ]; then
  cyan "CityShield is up and running!"
  echo "    App ......... $front"
  echo "    API docs .... http://localhost:${BACKEND_PORT}/docs"
  echo "    Demo: admin@city.gov/admin123  lead@city.gov/lead123  officer@city.gov/officer123  citizen@example.com/citizen123"
  echo "    Stop with: docker compose down"
  ( command -v xdg-open >/dev/null && xdg-open "$front" ) || ( command -v open >/dev/null && open "$front" ) || true
else
  warn "Backend not healthy yet (models may still be downloading). Watch: docker compose logs -f backend"
fi

[ "${1:-}" = "--logs" ] && docker compose logs -f || true
