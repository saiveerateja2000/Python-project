#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi

echo "Starting users service on port ${USERS_SERVICE_PORT:-5001}"
python "$ROOT_DIR/services/users_service/app.py" &
USERS_PID=$!

echo "Starting orders service on port ${ORDERS_SERVICE_PORT:-5002}"
python "$ROOT_DIR/services/orders_service/app.py" &
ORDERS_PID=$!

cleanup() {
  echo "Stopping services"
  kill "$USERS_PID" "$ORDERS_PID" >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM
wait
