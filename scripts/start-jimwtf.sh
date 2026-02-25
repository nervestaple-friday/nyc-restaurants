#!/bin/bash
# Start the jim-wtf dev server in the background.
# Usage: bash scripts/start-jimwtf.sh [--port 3421]

PORT=${1:-3421}
REPO="$(cd "$(dirname "$0")/../jim-wtf" && pwd)"

if lsof -ti tcp:$PORT >/dev/null 2>&1; then
  echo "Port $PORT already in use — server may already be running."
  exit 0
fi

echo "Starting jim-wtf dev server on port $PORT..."
cd "$REPO"
nohup npm run dev -- --port $PORT --hostname 0.0.0.0 > /tmp/jim-wtf-dev.log 2>&1 &
echo $! > /tmp/jim-wtf-dev.pid

# Wait for ready
for i in $(seq 1 20); do
  sleep 1
  if grep -q "Ready" /tmp/jim-wtf-dev.log 2>/dev/null; then
    echo "Ready at http://localhost:$PORT"
    exit 0
  fi
done
echo "Timed out waiting for server. Check /tmp/jim-wtf-dev.log"
exit 1
