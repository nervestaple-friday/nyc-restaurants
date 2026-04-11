#!/usr/bin/env bash
# NYC Film Events — Daily Product Development Cycle
# Spawns Claude Code to: scrape data, develop features, assess, push
set -euo pipefail

PROJECT="/home/claw/.openclaw/workspace/nyc-film-events"
CREDENTIALS="/home/claw/.openclaw/workspace/credentials.json"
FRIDAY_TOKEN=$(python3 -c "import json; print(json.load(open('$CREDENTIALS'))['github']['friday_org'])")
DATE=$(date +%Y-%m-%d)

# Configure git push credentials
cd "$PROJECT"
git remote set-url origin "https://x-access-token:${FRIDAY_TOKEN}@github.com/nervestaple-friday/nyc-film-events.git"

# Tag the current state so we can roll back
PRE_TAG="pre-cycle-${DATE}"
git tag -f "$PRE_TAG" HEAD 2>/dev/null || true

echo "=== NYC Film Events Dev Cycle — $DATE ==="
echo "Pre-cycle tag: $PRE_TAG"
echo "Starting Claude Code..."
