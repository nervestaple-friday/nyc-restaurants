# Recurring System Behavior — Complete Specification

Everything Friday does on a schedule lives here. If it's not in this file, it doesn't run.

---

## Delivery

All scheduled messages go to:
- **Channel:** Telegram
- **Target:** 573228387 (Jim's DM)
- **Thread:** 2771 (check-in topic), unless noted otherwise
- **Format:** One consolidated message per job. Concise.
- **Failures:** Must be visible — no silent drops.

---

## Heartbeat (schedule in openclaw.json — single source of truth)

The heartbeat is NOT a check-in. It's a background pulse. Default behavior: **silent** (`HEARTBEAT_OK`).

Break silence ONLY for genuinely urgent items:
- Time-sensitive email (flight change, security alert, package issue)
- Calendar event starting within 2 hours not yet mentioned
- System error needing attention (disk full, service down)
- SeedPool or similar open-registration windows

**Not urgent** (save for scheduled check-ins):
- Normal emails, newsletters, Venmo, package updates
- Film/show recommendations
- 4K upgrade results
- Recruiter emails (Monday cron handles these)
- Disk space (unless critical)

---

## Daily Check-Ins

### 🌅 Morning — 9:00 AM ET (daily)
- **Email** (last 12h) — filter noise: skip Nextdoor, routine financial statements, newsletters
- **Calendar** events in next 24–48h
- **System alerts** — disk, services, anything broken

### 🌤️ Afternoon — 1:00 PM ET (daily)
- **Email** since morning
- **Film recs** — 2 films not already in Plex/Radarr, via `scripts/film-of-the-day.py`
- **Stalled shows** — Wednesdays only: any show unwatched 14+ days, via `scripts/plex-watch-status.py`
- **Monthly show rec** — 1st of month only: 1 new show recommendation

### 🌙 Evening — 8:00 PM ET (daily)
- **Email** since afternoon
- **Weather** — tomorrow's forecast (Brooklyn, Open-Meteo lat 40.6501 lon -73.9496)
  - Only mention if notable: rain/snow (precip >50% or weathercode ≥61), extreme cold (<25°F), extreme heat (>90°F)
  - Skip if unremarkable
- **Loose ends** — any reminders or unfinished items from the day

---

## Weekly Jobs

### 📧 Recruiter Scan — Mondays 9:00 AM ET
- Runs `scripts/recruiter-scan.py --days 7`
- Only messages Jim if score ≥7 (exceptional opportunities)
- Silent otherwise
- State tracked in `memory/recruiter-state.json`
- Criteria: high comp/equity, founding/early roles, all-remote; soft-avoid crypto + "AI for X"
- Also exceptional: academic, research labs, nonprofits, public interest, sports, major media

### 🎬 Movie Events Digest — Sundays 6:00 PM ET
- Upcoming movie events/screenings
- Delivered to Telegram

---

## Background Maintenance (every 2h, silent)

Runs as isolated cron with lightweight model (Haiku). **Never messages Jim** unless disk is critical.

- **4K upgrade scan** — `scripts/4k-upgrade-scan.py`
- **Config backup** — backs up openclaw config
- **Disk check** — alerts only if critically low

---

## Open Questions for Jim

1. **Isolated vs main session?** Isolated sessions have been unreliable for delivery. Should check-ins run in main session (reliable but adds to conversation history) or isolated (cleaner but delivery issues)?
2. **Delivery mechanism?** Options: (a) `announce` mode — agent replies, OpenClaw delivers; (b) agent uses `message` tool directly; (c) something else?
3. **Thread 2771** — is that still the right topic for check-ins, or should they go to the main DM?
4. **Retry on failure?** Should failed check-ins retry, or just alert that they failed?
5. **Anything missing?** Any recurring task not captured above?
