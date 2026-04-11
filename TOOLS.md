# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## jim-wtf Dev Workflow
- Repo: `workspace/jim-wtf/` (nervestaple/jim-wtf)
- Start dev server: `bash scripts/start-jimwtf.sh` → http://localhost:3421
- Screenshot: `node scripts/screenshot-site.js` → saves to `workspace/jim-wtf-preview.png`
- Logs: `/tmp/jim-wtf-dev.log`, PID: `/tmp/jim-wtf-dev.pid`
- Kill server: `kill $(cat /tmp/jim-wtf-dev.pid)`
- Note: uses `LD_LIBRARY_PATH=/home/linuxbrew/.linuxbrew/lib` for Playwright headless Chromium

### Todoist (Task Tracking — Single Source of Truth)
- API: v1 (`https://api.todoist.com/api/v1/`)
- Token: `credentials.json` → `todoist.api_token`
- Project: "Friday" (id: `6g6H9HrFM5FRwW3J`)
- NYC Film Events section: `6g7rCj3PF2rQ7GMJ`
- CLI (`todoist` v0.4.0) installed but broken on v1 API — use curl for now
- **Todoist only** — no task files, no dual tracking

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

### arr-proxy (Radarr + Sonarr Gateway)
- URL: `http://100.104.61.75:7879` (Tailscale hostname — stable, unlike DHCP IPs)
- Auth: `X-Proxy-Key` header → `credentials.json` → `arr_proxy.key`
- Proxies Radarr (movies) and Sonarr (series) — API keys stay server-side

**Endpoints (movies):**
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/movies` | List full library |
| GET | `/movies/search?term=X` | Search by title (metadata lookup) |
| GET | `/movies/quality-profiles` | List quality profiles |
| GET | `/root-folders` | List root folders |
| POST | `/movies` | **Add a movie** (body: `tmdbId`, `qualityProfileId`, `rootFolderPath`) |
| PATCH | `/movies/{id}/monitored?monitored=bool` | Toggle monitored |
| PATCH | `/movies/{id}/quality-profile?qualityProfileId=N` | Change quality profile |
| POST | `/movies/{id}/search` | Trigger search for better copy |
| GET | `/movies/files` | Batch file quality info |
| GET | `/movies/{id}/file` | Single movie file info |

**Endpoints (series):**
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/series` | List full library |
| GET | `/series/search?term=X` | Search by title |
| GET | `/series/quality-profiles` | List quality profiles |
| GET | `/series/root-folders` | List root folders |
| POST | `/series` | **Add a series** (body: `tvdbId`, `qualityProfileId`, `rootFolderPath`) |
| PATCH | `/series/{id}/monitored?monitored=bool` | Toggle monitored |

**Blocked:** All DELETE operations, any unlisted path → 403

**Quality Profiles (Radarr):**
| ID | Name |
|----|------|
| 1 | Any |
| 4 | HD-1080p |
| 5 | Ultra-HD |
| 6 | HD - 720p/1080p |

**Root folder:** `/data/media/movies` (id: 1)

**Quick add movie example:**
```bash
PROXY_KEY=$(python3 -c "import json; print(json.load(open('credentials.json'))['arr_proxy']['key'])")
curl -s -X POST "http://100.104.61.75:7879/movies" \
  -H "X-Proxy-Key: $PROXY_KEY" -H "Content-Type: application/json" \
  -d '{"tmdbId": 13554, "qualityProfileId": 1, "rootFolderPath": "/data/media/movies"}'
```

**⚠️ Common mistake:** Don't use `/movies/add` or `/movies/list` — those are wrong paths and return 403. Use POST `/movies` and GET `/movies`.

### Hue Bridge
- IP: 192.168.4.39
- Rooms: HJP Office, Living Room, Dining Room, Kitchen, Porch, Bedroom

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.
