#!/bin/bash
# Interactive Sonarr import helper
# Finds recently downloaded TV shows and lets you approve each import

API_KEY=$(grep -oP 'ApiKey>\K[^<]+' /home/downloader/.config/Sonarr/config.xml 2>/dev/null || docker exec sonarr grep -oP 'ApiKey>\K[^<]+' /config/config.xml 2>/dev/null)
SONARR="http://localhost:8989/api/v3"

if [ -z "$API_KEY" ]; then
  echo "❌ Could not find Sonarr API key"
  exit 1
fi

# Find the download root (check common paths)
DL_ROOT=""
for p in /data/downloads/complete /data/downloads /downloads/complete /downloads; do
  if [ -d "$p" ]; then
    DL_ROOT="$p"
    break
  fi
done

if [ -z "$DL_ROOT" ]; then
  echo "❌ Could not find download directory. Enter path:"
  read -r DL_ROOT
fi

echo "📂 Scanning $DL_ROOT for TV show folders..."
echo ""

# Find directories modified in the last 7 days
find "$DL_ROOT" -maxdepth 2 -type d -mtime -7 2>/dev/null | sort | while read -r dir; do
  # Skip the root itself
  [ "$dir" = "$DL_ROOT" ] && continue
  
  # Check if it has video files
  count=$(find "$dir" -type f \( -name "*.mkv" -o -name "*.mp4" -o -name "*.avi" \) 2>/dev/null | wc -l)
  [ "$count" -eq 0 ] && continue
  
  name=$(basename "$dir")
  size=$(du -sh "$dir" 2>/dev/null | cut -f1)
  
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📺 $name"
  echo "   $count files, $size"
  echo ""
  read -p "   Import this? [y/N/q] " choice
  
  case "$choice" in
    y|Y)
      echo "   ⏳ Triggering import..."
      result=$(curl -s -X POST "$SONARR/command" \
        -H "X-Api-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"DownloadedEpisodesScan\", \"path\": \"$dir\"}")
      
      cmd_id=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id','?'))" 2>/dev/null)
      echo "   ✅ Scan triggered (command id: $cmd_id)"
      echo ""
      ;;
    q|Q)
      echo "Done."
      exit 0
      ;;
    *)
      echo "   ⏭ Skipped"
      echo ""
      ;;
  esac
done

echo ""
echo "Done! Check Sonarr Activity → Queue for import status."
