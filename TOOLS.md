# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## jim-wtf Dev Workflow
- Repo: `workspace/jim-wtf/` (nervestaple/jim-wtf)
- Start dev server: `bash scripts/start-jimwtf.sh` → http://localhost:3421
- Screenshot: `node scripts/screenshot-site.js` → saves to `workspace/jim-wtf-preview.png`
- Logs: `/tmp/jim-wtf-dev.log`, PID: `/tmp/jim-wtf-dev.pid`
- Kill server: `kill $(cat /tmp/jim-wtf-dev.pid)`
- Note: uses `LD_LIBRARY_PATH=/home/linuxbrew/.linuxbrew/lib` for Playwright headless Chromium

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

### Hue Bridge
- IP: 192.168.4.39
- Rooms: HJP Office, Living Room, Dining Room, Kitchen, Porch, Bedroom

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.
