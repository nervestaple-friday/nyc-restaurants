# HEARTBEAT.md

## Background pulse. Default: silent (HEARTBEAT_OK).
## Schedule is defined in openclaw.json (single source of truth).
## Daily check-ins are handled by cron.

---

## Break silence ONLY for genuinely URGENT items:
- Time-sensitive email (flight change, security alert, package issue)
- Calendar event starting within 2 hours not yet mentioned
- System error needing attention (disk full, service down)

## NOT urgent (save for scheduled check-ins):
- Normal emails, newsletters, Venmo, package updates
- Film/show recommendations
- 4K upgrade results
- Recruiter emails (Monday cron handles these)
- Disk space (unless critical)

---

## If urgent: send message to Jim (main thread, not check-in topic)
## If nothing urgent: HEARTBEAT_OK

---

## Silent background tasks (do these WITHOUT breaking silence):
### Memory maintenance (once per day, track in heartbeat-state.json → lastMemoryMaintenance)
- Scan today's `memory/YYYY-MM-DD.md` for unstored preferences, decisions, lessons
- `memory_recall` broad query → check for stale/outdated entries
- Store new, update stale, forget obsolete — silently
