#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
mkdir -p logs
BACKEND_LOG="$ROOT/logs/backend.log"
FRONTEND_LOG="$ROOT/logs/frontend.log"

cleanup() {
  echo "Stopping services..."
  kill ${BACK_PID:-} ${FRONT_PID:-} 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM

for port in 8000 3000; do
  if PIDS=$(lsof -t -i :$port 2>/dev/null); then
    echo "Killing processes on port $port: $PIDS"
    kill $PIDS 2>/dev/null || true
  fi
done

if ! docker start familys-mongo >/dev/null 2>&1; then
  docker run --name familys-mongo -p 27017:27017 -v familys-mongo-data:/data/db -d mongo:6
fi

backend/.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload > "$BACKEND_LOG" 2>&1 &
BACK_PID=$!

corepack enable >/dev/null 2>&1 || true
corepack yarn dev --port 3000 > "$FRONTEND_LOG" 2>&1 &
FRONT_PID=$!

echo "Waiting for backend..."
for _ in {1..40}; do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/health || true)
  [ "$code" = "200" ] && break
  sleep 1
done

echo "Waiting for frontend..."
for _ in {1..40}; do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 || true)
  [ "$code" = "200" ] && break
  sleep 1
done

echo "OPEN: http://localhost:3000/parametres"
echo "DEBUG: http://127.0.0.1:8000/api/auth/gmail/debug"
echo "CHECK: curl -I http://127.0.0.1:8000/api/auth/gmail/start"
echo "CHECK: curl http://127.0.0.1:8000/api/accounts"

wait $BACK_PID $FRONT_PID
