#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "Killing ports 8000 and 3000 if busy..."
for port in 8000 3000; do
  if PIDS=$(lsof -t -i :$port 2>/dev/null); then
    kill $PIDS 2>/dev/null || true
  fi
done

echo "Starting Mongo (Docker)..."
if ! docker start familys-mongo >/dev/null 2>&1; then
  docker run --name familys-mongo -p 27017:27017 -v familys-mongo-data:/data/db -d mongo:6
fi

echo "Starting backend..."
mkdir -p logs
backend/.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload > logs/backend.log 2>&1 &
BACK_PID=$!

echo "Waiting for backend health..."
for _ in {1..40}; do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/health || true)
  [ "$code" = "200" ] && break
  sleep 1
done

echo "Starting frontend..."
corepack enable >/dev/null 2>&1 || true
corepack yarn dev -p 3000 > logs/frontend.log 2>&1 &
FRONT_PID=$!

echo "OPEN http://localhost:3000/parametres"
echo "CHECK LOGS: tail -f logs/backend.log"
wait $BACK_PID $FRONT_PID
