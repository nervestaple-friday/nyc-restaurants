#!/usr/bin/env python3
"""
Film recommendation data tool.

Pure data gatherer for the check-in cron — no LLM calls.
Claude generates recommendations using the structured context this outputs.

Modes:
  python3 scripts/film-of-the-day.py                          # gather context JSON
  python3 scripts/film-of-the-day.py --check '[{"title":..}]' # verify films against library
  python3 scripts/film-of-the-day.py --record 'Title (Year)'  # record titles to state
  python3 scripts/film-of-the-day.py --record ... --dry-run   # preview without saving
"""

import os, sys, json, urllib.request, argparse, datetime

WORKSPACE  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(WORKSPACE, 'memory', 'film-recs-state.json')
PLEX       = 'http://192.168.4.121:32400'
PLEX_TOKEN = 'XRRDNdQVeCjRumgE9mUy'
ARR_URL    = 'http://100.104.61.75:7879'
ARR_KEY    = 'orRkC573vbA4cepg4TV_kdtLoy-AaaM8uuyBloWQzT4'


def plex_req(path):
    sep = '&' if '?' in path else '?'
    url = f"{PLEX}{path}{sep}X-Plex-Token={PLEX_TOKEN}"
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def arr_req(path):
    url = f"{ARR_URL}{path}"
    req = urllib.request.Request(url, headers={'X-Proxy-Key': ARR_KEY, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def get_plex_library_titles():
    """Return set of (title_lower, year) tuples for all movies in Plex."""
    data = plex_req('/library/sections/1/all?type=1')
    titles = set()
    for m in data['MediaContainer'].get('Metadata', []):
        titles.add((m.get('title', '').lower(), m.get('year')))
    return titles


def get_recently_watched(n=20):
    """Get recently watched movies as structured dicts."""
    data = plex_req(f'/library/sections/1/all?type=1&sort=lastViewedAt:desc&limit={n}')
    watched = []
    for m in data['MediaContainer'].get('Metadata', []):
        if m.get('lastViewedAt'):
            watched.append({'title': m.get('title'), 'year': m.get('year')})
    return watched


def get_radarr_titles():
    """Return list of monitored Radarr movie titles. Skips gracefully if unreachable."""
    try:
        movies = arr_req('/movies')
        return [m.get('title', '') for m in movies if m.get('monitored', True)]
    except Exception:
        return []


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {'recommended': [], 'last_run': None}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def check_in_library(title, year, plex_titles, radarr_titles_lower):
    """Check if a film is in Plex or Radarr."""
    t = title.lower()
    in_plex   = any(pt == t or (pt == t and py == year) for pt, py in plex_titles)
    in_radarr = t in radarr_titles_lower
    return in_plex, in_radarr


def cmd_gather():
    """Default mode: output structured context JSON for Claude."""
    state         = load_state()
    recently_watched = get_recently_watched(25)
    plex_titles   = get_plex_library_titles()
    radarr_titles = get_radarr_titles()
    past_recs     = state.get('recommended', [])[-30:]

    output = {
        'recently_watched': recently_watched,
        'past_recommendations': past_recs,
        'plex_library_count': len(plex_titles),
        'radarr_monitored': radarr_titles,
        'last_run': state.get('last_run'),
        'today': datetime.date.today().isoformat(),
    }
    print(json.dumps(output, indent=2))


def cmd_check(check_json):
    """Verify a list of recommendations against Plex/Radarr."""
    try:
        films = json.loads(check_json)
    except json.JSONDecodeError as e:
        print(json.dumps({'error': f'Invalid JSON: {e}'}))
        sys.exit(1)

    plex_titles = get_plex_library_titles()
    radarr_titles_lower = {t.lower() for t in get_radarr_titles()}

    results = []
    for film in films:
        title = film.get('title', '')
        year  = film.get('year')
        in_plex, in_radarr = check_in_library(title, year, plex_titles, radarr_titles_lower)
        results.append({
            'title': title,
            'year': year,
            'in_plex': in_plex,
            'in_radarr': in_radarr,
        })

    print(json.dumps(results, indent=2))


def cmd_record(titles, dry_run=False):
    """Record recommendation titles to state to avoid future repeats."""
    state = load_state()
    past  = state.get('recommended', [])

    for t in titles:
        if t not in past:
            past.append(t)

    state['recommended'] = past
    state['last_run']    = datetime.date.today().isoformat()

    if dry_run:
        print(json.dumps({'dry_run': True, 'would_record': titles, 'total_past': len(past)}))
    else:
        save_state(state)
        print(json.dumps({'recorded': titles, 'total_past': len(past)}))


def main():
    parser = argparse.ArgumentParser(description='Film recommendation data tool')
    parser.add_argument('--check', metavar='JSON',
                        help='JSON array of {title, year} to verify against library')
    parser.add_argument('--record', nargs='+', metavar='TITLE',
                        help='Record recommendation titles to state (e.g. "Title (Year)")')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview --record without saving')
    args = parser.parse_args()

    if args.check:
        cmd_check(args.check)
    elif args.record:
        cmd_record(args.record, dry_run=args.dry_run)
    else:
        cmd_gather()


if __name__ == '__main__':
    main()
