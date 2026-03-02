#!/usr/bin/env python3
"""
NYC Movie Events Digest
=======================
Scrapes upcoming special screenings and events from:
  - Metrograph
  - IFC Center
  - Film Forum
  - Anthology Film Archives
  - Nitehawk Cinema (Williamsburg + Prospect Park)
  - BAM
  - Spectacle Theater
  - Syndicated BK
  - Film at Lincoln Center   (best-effort, Cloudflare-protected)
  - Museum of the Moving Image (best-effort, Cloudflare-protected)

Filters out mainstream Hollywood wide releases.
Run weekly for a digest, or with --test to preview without updating state.
"""

import os, sys, json, hashlib, re, requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE  = os.path.dirname(SCRIPT_DIR)
STATE_FILE = os.path.join(WORKSPACE, 'memory', 'events-state.json')
TEST_MODE  = '--test' in sys.argv
PUSH       = '--push' in sys.argv or (not TEST_MODE)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

FLARESOLVERR = 'http://192.168.4.227:8191/v1'

MIN_DAYS, MAX_DAYS = 0, 21

# Mainstream studio titles to skip (case-insensitive substring match)
MAINSTREAM_BLOCKLIST = [
    'avatar', 'marvel', 'avengers', 'spider-man', 'batman', 'superman',
    'star wars', 'fast &', 'fast and furious', 'jurassic', 'transformers',
    'mission: impossible', 'james bond', '007', 'minions', 'despicable me',
    'toy story', 'frozen', 'lion king', 'little mermaid', 'moana',
    'captain america', 'black panther', 'thor', 'doctor strange',
    'guardians of the galaxy', 'ant-man', 'black widow',
]

# Keywords suggesting repertory / special programming (boosts inclusion)
SPECIAL_KEYWORDS = [
    'q&a', 'qa', 'discussion', 'special', 'retrospective', 'series',
    'anniversary', 'tribute', 'in person', 'premiere', 'festival',
    'restoration', 'new print', 'double feature', 'marathon',
    'director', 'actor', 'conversation', 'introduction', 'intro',
    '35mm', '16mm', 'archive', 'rare', 'one night', 'one-night',
    'shorts', 'documentary', 'new wave', 'classic', 'retrospective',
]


# ── helpers ────────────────────────────────────────────────────────────────

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'seen': []}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def event_id(venue, title, date_str=''):
    raw = f"{venue}:{title}:{date_str}".lower()
    return hashlib.md5(raw.encode()).hexdigest()[:12]

def clean_title(title):
    title = re.sub(r'^[,\s]*\d{1,2}:\d{2}\s*(AM|PM)\s*', '', title).strip()
    title = re.sub(r'\s*(Q&A?|More Info|Series Schedule|Watch Trailer|Tickets|Buy Tickets)\s*$',
                   '', title, flags=re.IGNORECASE).strip()
    title = re.sub(r'Q&\s*$', '', title).strip()
    return ' '.join(title.split())

def is_special(title, description=''):
    text = (title + ' ' + description).lower()
    return any(kw in text for kw in SPECIAL_KEYWORDS)

def is_mainstream(title):
    t = title.lower()
    return any(kw in t for kw in MAINSTREAM_BLOCKLIST)

def fetch(url, timeout=12):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"  [fetch error] {url}: {e}", file=sys.stderr)
        return None

def fetch_cf(url, timeout=35):
    """Fetch via FlareSolverr for Cloudflare-protected pages."""
    try:
        r = requests.post(FLARESOLVERR, json={
            'cmd': 'request.get',
            'url': url,
            'maxTimeout': timeout * 1000,
        }, timeout=timeout + 5)
        r.raise_for_status()
        data = r.json()
        if data.get('status') != 'ok':
            print(f"  [flaresolverr error] {url}: {data.get('message')}", file=sys.stderr)
            return None
        # Return a simple object with .text attribute
        class _Resp:
            text = data['solution']['response']
            status_code = data['solution']['status']
        return _Resp()
    except Exception as e:
        print(f"  [flaresolverr error] {url}: {e}", file=sys.stderr)
        return None

def parse_date_loose(text):
    try:
        from dateutil import parser as dp
        return dp.parse(text, fuzzy=True)
    except Exception:
        return None

def make_event(venue, title, link='', date=None, date_str='', special=None):
    title = clean_title(title)
    if not title or len(title) < 3 or is_mainstream(title):
        return None
    return {
        'venue': venue,
        'title': title,
        'link': link,
        'date': date,
        'date_str': date_str,
        'special': special if special is not None else is_special(title),
    }


# ── scrapers ───────────────────────────────────────────────────────────────

def scrape_metrograph():
    events = []
    r = fetch('https://metrograph.com/feed/')
    if not r:
        return events
    try:
        root = ET.fromstring(r.text)
        for item in root.findall('.//item'):
            title = item.findtext('title', '').strip()
            link  = item.findtext('link', '').strip()
            e = make_event('Metrograph', title, link, special=True)
            if e:
                events.append(e)
    except Exception as ex:
        print(f"  [Metrograph] {ex}", file=sys.stderr)
    return events


def scrape_spectacle():
    """Spectacle Theater has a working RSS feed."""
    events = []
    r = fetch('https://www.spectacletheater.com/feed/')
    if not r:
        return events
    try:
        root = ET.fromstring(r.text)
        for item in root.findall('.//item'):
            title = item.findtext('title', '').strip()
            link  = item.findtext('link', '').strip()
            e = make_event('Spectacle Theater', title, link, special=True)
            if e:
                events.append(e)
    except Exception as ex:
        print(f"  [Spectacle] {ex}", file=sys.stderr)
    return events


def scrape_syndicated():
    """Syndicated BK — uses Veezi ticketing, scrape the sessions page."""
    events = []
    url = 'https://ticketing.useast.veezi.com/sessions/?siteToken=dxdq5wzbef6bz2sjqt83ytzn1c'
    r = fetch(url)
    if not r:
        return events
    soup = BeautifulSoup(r.text, 'html.parser')
    current_date_str = None
    current_date     = None
    now = datetime.now()
    seen_titles = set()
    for el in soup.find_all(['h3', 'h4', 'div', 'span', 'li', 'a']):
        text = el.get_text(strip=True)
        if re.match(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', text):
            current_date_str = text
            try:
                from dateutil import parser as dp
                current_date = dp.parse(text + f" {now.year}", fuzzy=True)
            except Exception:
                current_date = None
        elif (text and 5 < len(text) < 80 and current_date and
              el.name in ['a', 'h3', 'h4'] and not re.match(r'^\d+:\d+', text)):
            if text not in seen_titles:
                delta = (current_date - now).days
                if MIN_DAYS <= delta <= MAX_DAYS:
                    if text.lower() in ('show future dates', 'showtimes', 'buy tickets'):
                        continue
                    e = make_event('Syndicated BK', text, url,
                                   date=current_date, date_str=current_date_str)
                    if e:
                        seen_titles.add(text)
                        events.append(e)
    return events


def scrape_ifc():
    """IFC Center — apitap read extracts clean markdown from the homepage.
    Parse title/link pairs from rendered markdown instead of raw HTML soup."""
    import subprocess as _sp
    events = []
    try:
        result = _sp.run(
            ['apitap', 'read', 'https://www.ifccenter.com/'],
            capture_output=True, text=True, timeout=30,
        )
        md = result.stdout
    except Exception as ex:
        print(f"  [IFC/apitap] fallback to requests: {ex}", file=sys.stderr)
        r = fetch('https://www.ifccenter.com/')
        if not r:
            return events
        md = r.text  # raw HTML fallback — regex still works on href/h1 patterns

    seen = set()
    # Match markdown links: [TITLE](https://www.ifccenter.com/films/...) or /series/
    for m in re.finditer(
        r'#\s+([^\n\r]+)\n[^\[]*\[?[^\]]*\]?\(?(?:https://www\.ifccenter\.com)?((?:/films/|/series/)[\w\-/]+)\)?',
        md,
    ):
        title = m.group(1).strip()
        path  = m.group(2).strip().rstrip(')')
        link  = f"https://www.ifccenter.com{path}"
        # Strip markdown formatting and trailing context
        title = re.sub(r'[#\*\[\]]', '', title).strip()
        title = re.split(r'Q&A|Filmmaker|Director|Screening on|Opens|Academy Award', title)[0].strip()
        if not title or len(title) < 3 or link in seen:
            continue
        seen.add(link)
        note = re.search(r'\n([^\n#]{10,120})', md[m.end():m.end()+300])
        special = is_special(title) or bool(note and is_special(note.group(1)))
        e = make_event('IFC Center', title, link, special=special)
        if e:
            events.append(e)

    return events[:15]


def scrape_film_forum():
    events = []
    r = fetch('https://filmforum.org/films')
    if not r:
        return events
    soup = BeautifulSoup(r.text, 'html.parser')
    seen_titles = set()
    for a in soup.find_all('a', href=True):
        href = a.get('href', '')
        if '/film/' in href or '/films/' in href:
            title = a.get_text(strip=True)
            if title and 3 < len(title) < 100 and title not in seen_titles:
                seen_titles.add(title)
                link = f"https://filmforum.org{href}" if href.startswith('/') else href
                e = make_event('Film Forum', title, link)
                if e:
                    events.append(e)
    return events[:20]


def scrape_anthology():
    events = []
    now = datetime.now()
    for month_offset in [0, 1]:
        month = (now.month + month_offset - 1) % 12 + 1
        year  = now.year + (1 if now.month + month_offset > 12 else 0)
        url   = (f"https://anthologyfilmarchives.org/film_screenings/calendar"
                 f"?view=list&month={month:02d}&year={year}")
        r = fetch(url)
        if not r:
            continue
        soup = BeautifulSoup(r.text, 'html.parser')
        current_date = None
        for h3 in soup.find_all('h3'):
            date_text = h3.get_text(strip=True)
            try:
                from dateutil import parser as dp
                current_date = dp.parse(date_text + f" {year}", fuzzy=True)
            except Exception:
                pass
            for sib in h3.next_siblings:
                if hasattr(sib, 'name') and sib.name == 'h3':
                    break
                text = sib.get_text(strip=True) if hasattr(sib, 'get_text') else ''
                if not text or len(text) < 5:
                    continue
                clean = re.sub(r'^[,\s]*\d{1,2}:\d{2}\s*(AM|PM)\s*', '', text).strip()
                title = re.split(r'\s+by\s+|\s+Share\s+|In \w+ with|\d{4},\s*\d+\s*min|Share \+', clean)[0].strip()
                title = re.sub(r'^EC:\s*', '', title).strip()  # keep but clean EC: prefix
                if title and 5 < len(title) < 100 and current_date:
                    delta = (current_date - now).days
                    if MIN_DAYS <= delta <= MAX_DAYS:
                        e = make_event('Anthology Film Archives', title, url,
                                       date=current_date,
                                       date_str=current_date.strftime('%b %d'),
                                       special=True)
                        if e:
                            events.append(e)
    seen = set()
    return [e for e in events if e['title'] not in seen and not seen.add(e['title'])][:20]


def scrape_nitehawk():
    """Nitehawk — apitap-style: regex series index -> movie slug -> /nj/v1/show API.
    No BeautifulSoup, no h1 guessing. Two lightweight HTML fetches per location
    (index page + series page), one API call per film for structured data."""
    import urllib.request as _ur, urllib.error as _ue

    SKIP_SLUGS = {
        'adults-with-infants', 'adults-with-infants-2',
        'brunch', 'brunch-screenings', 'brunch-screenings-2',
        'family-friendly', 'family-friendly-screenings', 'family-friendly-screenings-2',
        'spoons-toons', 'all-ages-2',
    }
    LOCATIONS = [
        ('Williamsburg',  'https://nitehawkcinema.com/williamsburg/film-series/'),
        ('Prospect Park', 'https://nitehawkcinema.com/prospectpark/film-series-2/'),
    ]
    NJ_API = 'https://nitehawkcinema.com/wp-json/nj/v1/show'

    def nj_fetch(slug):
        """Fetch structured show data from Nitehawk's WP REST API by movie slug."""
        try:
            req = _ur.Request(
                f'{NJ_API}?slug={slug}&_fields=id,title,link,excerpt,director',
                headers={'Accept': 'application/json'},
            )
            with _ur.urlopen(req, timeout=8) as resp:
                data = json.load(resp)
                return data[0] if data else None
        except Exception:
            return None

    events = []
    seen_slugs = set()

    for location, index_url in LOCATIONS:
        r = fetch(index_url)
        if not r:
            continue

        # Extract series hrefs with regex — no BS4 needed
        series_hrefs = re.findall(
            r'href="(https://nitehawkcinema\.com/(?:williamsburg|prospectpark)/film-series[^"]*)"',
            r.text,
        )
        series_hrefs = list(dict.fromkeys(series_hrefs))  # dedupe, preserve order

        for series_href in series_hrefs[:25]:
            slug = series_href.rstrip('/').split('/')[-1]
            if slug in SKIP_SLUGS or slug in ('film-series', 'film-series-2'):
                continue

            # Fetch series page, extract ALL /movies/<slug> links
            r2 = fetch(series_href)
            if not r2:
                continue
            movie_slugs = list(dict.fromkeys(re.findall(r'/movies/([\w\-]+)', r2.text)))
            if not movie_slugs:
                continue

            for movie_slug in movie_slugs:
                if movie_slug in seen_slugs:
                    continue
                seen_slugs.add(movie_slug)

                # Get structured data from API
                show = nj_fetch(movie_slug)
                if show:
                    title   = show['title']['rendered']
                    link    = show.get('link', series_href)
                    excerpt = re.sub(r'<[^>]+>', '', show.get('excerpt', {}).get('rendered', '')).strip()
                    dirs    = [d['name'] for d in show.get('director', [])]
                    special_note = excerpt or (f"Dir. {', '.join(dirs)}" if dirs else None)
                else:
                    title = movie_slug.replace('-', ' ').title()
                    link  = f'https://nitehawkcinema.com/movies/{movie_slug}/'
                    special_note = None

                e = make_event(f'Nitehawk ({location})', title, link, special=True)
                if e:
                    if special_note:
                        e['special_note'] = special_note
                    events.append(e)

    return events[:40]


def scrape_flc():
    """Film at Lincoln Center — apitap-captured REST API at api.filmlinc.org/showtimes.
    Returns structured film objects with title, slug, dates, and ticket URLs.
    No FlareSolverr needed."""
    import urllib.request as _ur
    events = []
    try:
        req = _ur.Request(
            'https://api.filmlinc.org/showtimes',
            headers={'Accept': 'application/json', 'Origin': 'https://www.filmlinc.org'},
        )
        with _ur.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
    except Exception as ex:
        print(f"  [FLC/api] {ex}", file=sys.stderr)
        return events

    now = datetime.now()
    seen = set()
    for film in data.get('films', []):
        title = film.get('title', '').strip()
        slug  = film.get('slug', '')
        link  = f"https://www.filmlinc.org/films/{slug}/" if slug else 'https://www.filmlinc.org/calendar/'
        if not title or title in seen or len(title) < 4:
            continue
        # Filter to upcoming showtimes within window
        showtimes = film.get('showtimes', [])
        def _flc_date(s):
            """Parse FLC dateTimeET to naive date for comparison."""
            raw = s.get('dateTimeET', '')
            if not raw:
                return None
            try:
                # Strip tz suffix → naive datetime for delta calc
                return datetime.fromisoformat(raw.split('T')[0])
            except Exception:
                return None

        upcoming = [
            s for s in showtimes
            if _flc_date(s) and MIN_DAYS <= (_flc_date(s) - now).days <= MAX_DAYS
        ] if showtimes else []
        # Include if it has upcoming showtimes or no dates at all (always show current programming)
        if showtimes and not upcoming:
            continue
        seen.add(title)
        date = None
        date_str = ''
        if upcoming:
            try:
                dt_str = upcoming[0]['dateTimeET'].split('T')[0]
                date   = datetime.fromisoformat(dt_str)
                date_str = upcoming[0].get('date', '')
            except Exception:
                pass
        e = make_event('Film at Lincoln Center', title, link, date=date, date_str=date_str)
        if e:
            events.append(e)

    return events[:20]


def scrape_momi():
    """Museum of the Moving Image — apitap read for clean markdown extraction.
    MoMI blocks headless browsers and FlareSolverr; readability works server-side."""
    import subprocess as _sp
    events = []
    try:
        result = _sp.run(
            ['apitap', 'read', 'https://movingimage.org/whats-on/screenings-and-series/'],
            capture_output=True, text=True, timeout=30,
        )
        md = result.stdout
    except Exception as ex:
        print(f"  [MoMI/apitap] {ex}", file=sys.stderr)
        return events

    SKIP = {'screenings and series', 'screenings', 'events', 'calendar',
            'see all', 'rentals', 'museum of the moving image', 'whats on'}
    seen = set()
    # MoMI renders titles as ## or ### headings and bold links
    for m in re.finditer(
        r'(?:#{1,3}\s+|\*\*)\[?([^\n\]\*]{4,80})\]?\(?(?:https://movingimage\.org)?(/[^\s\)\"]{5,100})?\)?',
        md,
    ):
        title = m.group(1).strip().strip('*').strip()
        path  = (m.group(2) or '').strip()
        link  = f"https://movingimage.org{path}" if path else 'https://movingimage.org/whats-on/screenings-and-series/'
        if not title or title.lower() in SKIP or title in seen:
            continue
        seen.add(title)
        e = make_event('Museum of the Moving Image', title, link, special=True)
        if e:
            events.append(e)

    return events[:20]


def scrape_moma():
    """MoMA Film — apitap read for clean markdown extraction.
    MoMA blocks headless Playwright; readability bypasses CF and gives structured output."""
    import subprocess as _sp
    events = []
    try:
        result = _sp.run(
            ['apitap', 'read', 'https://www.moma.org/calendar/film'],
            capture_output=True, text=True, timeout=30,
        )
        md = result.stdout
    except Exception as ex:
        print(f"  [MoMA/apitap] {ex}", file=sys.stderr)
        return events

    SKIP = {'upcoming showtimes', 'upcoming exhibitions', 'view all showtimes',
            'film series', 'moma film', 'moma'}
    seen = set()
    # MoMA renders as ### Film Title\ndate-range\ndescription
    for m in re.finditer(
        r'###\s+\[?([^\n\]\#]{4,100})\]?\(?(https://www\.moma\.org/calendar/film/[^\s\)\"]+)?\)?',
        md,
    ):
        title = m.group(1).strip()
        link  = m.group(2) or 'https://www.moma.org/calendar/film'
        # Strip trailing date ranges: "Mar 5–26, 2026" etc.
        title = re.sub(r'\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d.*$', '', title).strip()
        title = re.sub(r'\s*(Ongoing|Now Playing|Coming Soon)\s*$', '', title, flags=re.IGNORECASE).strip()
        if not title or title.lower() in SKIP or title in seen or len(title) < 4:
            continue
        seen.add(title)
        e = make_event('MoMA', title, link, special=True)
        if e:
            events.append(e)

    return events[:20]


def scrape_paris():
    """Paris Theater NYC — extract all current films from the double-escaped JSON
    embedded in the Next.js page bundle. No API auth needed, no FlareSolverr.
    Paris typically shows 2-4 films at a time, all listed in the page source."""
    import urllib.request as _ur
    events = []

    try:
        req = _ur.Request(
            'https://www.paristheaternyc.com',
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36'},
        )
        with _ur.urlopen(req, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='replace')
    except Exception as ex:
        print(f"  [Paris/html] {ex}", file=sys.stderr)
        return events

    # Extract DisplayTitle from escaped JSON in Next.js bundle.
    # Raw bytes: DisplayTitle\\":\\"Title - \\u003cParis\\u003e\\"
    seen = set()
    SKIP_TITLES = {'fall preview', 'coming soon', 'paris theater', 'special event'}
    for m in re.finditer(
        r'DisplayTitle[^:]*?:.*?"([^"\\]{3,80})',
        html,
    ):
        title = m.group(1).strip().rstrip(' -').strip()
        if not title or len(title) < 3:
            continue
        if title.lower() in SKIP_TITLES or title in seen:
            continue
        seen.add(title)
        slug  = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        link  = f"https://www.paristheaternyc.com/films/{slug}"
        e = make_event('Paris Theater', title, link)
        if e:
            events.append(e)

    return events[:10]


def scrape_bam():
    """BAM — apitap read gives clean markdown with h3 titles.
    BAM's rendered HTML concatenates text into noise; the readability
    extraction is significantly cleaner. Links still need a slug lookup
    since apitap read strips JS-rendered hrefs, so we derive from title."""
    import subprocess as _sp
    events = []
    try:
        result = _sp.run(
            ['apitap', 'read', 'https://www.bam.org/film'],
            capture_output=True, text=True, timeout=30,
        )
        md = result.stdout
    except Exception as ex:
        print(f"  [BAM/apitap] fallback: {ex}", file=sys.stderr)
        r = fetch('https://www.bam.org/film')
        if not r:
            return events
        md = r.text

    seen = set()
    # apitap read renders BAM titles cleanly as ### Title
    for m in re.finditer(r'###\s+([^\n#]{3,80})', md):
        title = m.group(1).strip().strip('"').strip()
        # Skip header noise
        if title in ('BAM Film 2026', 'BAM Film', 'Film') or len(title) < 4:
            continue
        if title in seen:
            continue
        seen.add(title)
        # Derive link slug from title
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        link = f"https://www.bam.org/film/{slug}"
        e = make_event('BAM', title, link)
        if e:
            events.append(e)

    return events[:15]


# ── filtering + formatting ─────────────────────────────────────────────────

def filter_by_date(events):
    now = datetime.now()
    result = []
    for e in events:
        if e['date']:
            delta = (e['date'] - now).days
            if MIN_DAYS <= delta <= MAX_DAYS:
                result.append(e)
        else:
            result.append(e)  # undated venue listings always included
    return result


def format_digest(events_by_venue):
    now   = datetime.now()
    lines = [f"🎬 *NYC Movie Events — Week of {now.strftime('%B %d')}*\n"]
    total = 0
    for venue, events in events_by_venue.items():
        if not events:
            continue
        lines.append(f"*{venue}*")
        for e in events:
            date_part = f" — {e['date'].strftime('%b %d')}" if e['date'] else ""
            lines.append(f"• {e['title']}{date_part}")
            if e.get('link'):
                lines.append(f"  {e['link']}")
            total += 1
        lines.append('')
    if total == 0:
        return None
    return '\n'.join(lines).strip()




def push_to_github(events_by_venue):
    """Push events.json to nervestaple-friday/nyc-film-events for GitHub Pages."""
    import base64
    try:
        creds_path = os.path.join(WORKSPACE, 'credentials.json')
        with open(creds_path) as f:
            token = json.load(f)['github']['friday_org']
    except Exception as e:
        print(f"  [github] could not load token: {e}", file=sys.stderr)
        return False

    payload = {
        'updated': datetime.now().isoformat(),
        'venues': {
            venue: {
                'url': VENUE_URLS.get(venue, ''),
                'events': [
                    {'title': e['title'], 'link': e.get('link',''), 'date_str': e.get('date_str','')}
                    for e in events
                ]
            }
            for venue, events in events_by_venue.items()
            if events
        }
    }
    content = json.dumps(payload, indent=2, ensure_ascii=False)
    encoded = base64.b64encode(content.encode()).decode()

    api = 'https://api.github.com/repos/nervestaple-friday/nyc-film-events/contents/events.json'
    headers = {'Authorization': f'token {token}', 'Content-Type': 'application/json'}

    # Get current SHA if file exists
    sha = None
    r = requests.get(api, headers=headers)
    if r.status_code == 200:
        sha = r.json().get('sha')

    body = {'message': f'Update events {datetime.now().strftime("%Y-%m-%d")}',
            'content': encoded}
    if sha:
        body['sha'] = sha

    r = requests.put(api, headers=headers, json=body)
    if r.status_code in (200, 201):
        print(f"  [github] pushed events.json ✓", file=sys.stderr)
        return True
    else:
        print(f"  [github] push failed: {r.status_code} {r.text[:200]}", file=sys.stderr)
        return False


# ── main ───────────────────────────────────────────────────────────────────

VENUES_ORDER = [
    'Metrograph', 'Film Forum', 'IFC Center', 'Film at Lincoln Center',
    'Anthology Film Archives', 'Museum of the Moving Image', 'MoMA',
    'Nitehawk (Williamsburg)', 'Nitehawk (Prospect Park)',
    'Spectacle Theater', 'Syndicated BK', 'Paris Theater', 'BAM',
]

VENUE_URLS = {
    'Metrograph':                  'https://metrograph.com/calendar/',
    'Film Forum':                  'https://filmforum.org/films',
    'IFC Center':                  'https://www.ifccenter.com/',
    'Film at Lincoln Center':      'https://www.filmlinc.org/calendar/',
    'Anthology Film Archives':     'https://anthologyfilmarchives.org/film_screenings/calendar',
    'Museum of the Moving Image':  'https://movingimage.org/whats-on/screenings-and-series/',
    'MoMA':                        'https://www.moma.org/calendar/film',
    'Nitehawk (Williamsburg)':     'https://nitehawkcinema.com/williamsburg/',
    'Nitehawk (Prospect Park)':    'https://nitehawkcinema.com/prospectpark/',
    'Spectacle Theater':           'https://www.spectacletheater.com/',
    'Syndicated BK':               'https://syndicatedbk.com/',
    'Paris Theater':               'https://paristheaternyc.com',
    'BAM':                         'https://www.bam.org/film',
}

SCRAPERS = [
    scrape_metrograph,
    scrape_spectacle,
    scrape_syndicated,
    scrape_ifc,
    scrape_film_forum,
    scrape_anthology,
    scrape_nitehawk,
    scrape_flc,
    scrape_momi,
    scrape_moma,
    scrape_paris,
    scrape_bam,
]


def main():
    print("Scraping NYC movie events...", file=sys.stderr)
    state    = load_state()
    seen_ids = set(state.get('seen', []))
    all_events = []
    for scraper in SCRAPERS:
        name = scraper.__name__.replace('scrape_', '').replace('_', ' ').title()
        print(f"  Fetching {name}...", file=sys.stderr)
        try:
            events = scraper()
            print(f"    {len(events)} items", file=sys.stderr)
            all_events.extend(events)
        except Exception as ex:
            print(f"    Error: {ex}", file=sys.stderr)

    filtered  = filter_by_date(all_events)
    new_events, new_ids = [], []
    for e in filtered:
        eid = event_id(e['venue'], e['title'], e.get('date_str', ''))
        if eid not in seen_ids:
            new_events.append(e)
            new_ids.append(eid)

    events_by_venue = {v: [] for v in VENUES_ORDER}
    for e in new_events:
        if e['venue'] in events_by_venue:
            events_by_venue[e['venue']].append(e)
        else:
            events_by_venue[e['venue']] = events_by_venue.get(e['venue'], []) + [e]

    digest = format_digest(events_by_venue)
    print(digest if digest else "No new events found.")

    if not TEST_MODE and new_ids:
        state['seen']    = list(seen_ids | set(new_ids))[-300:]
        state['lastRun'] = datetime.now().isoformat()
        save_state(state)
        print(f"\n[State updated: {len(new_ids)} new events]", file=sys.stderr)

    if PUSH:
        push_to_github(events_by_venue)


if __name__ == '__main__':
    try:
        from dateutil import parser as _
    except ImportError:
        import subprocess
        subprocess.run(['pip3', 'install', 'python-dateutil', '--break-system-packages', '-q'])
    main()
