#!/usr/bin/env python3
"""
Weekly recruiter email scanner.
Scans Gmail for inbound recruiter emails, evaluates each with GPT, and sends a
Telegram summary only if at least one scores 7+. The report includes ALL evaluated
emails (sorted by score) so Jim can see the full landscape.

Criteria for "exceptional" (7+ score):
  - High comp / equity signals
  - Founding or early-team roles
  - Fully remote
  - Interesting company / problem space with real traction
  - Prestigious / rare orgs (academic, research, nonprofit, public interest,
    sports, media) — comp not required for these

Soft avoid (but not hard blockers):
  - Pure crypto / web3
  - Generic "AI for X" wrappers

Always skip:
  - Mass ATS blasts (LinkedIn, Greenhouse, Lever, etc.)
  - No specific role or context

Run: python3 scripts/recruiter-scan.py [--days 7] [--dry-run]

Requires: gog CLI with GOG_ACCOUNT and GOG_KEYRING_PASSWORD env vars set.
"""

import os, sys, json, urllib.request, subprocess, datetime, time, argparse

WORKSPACE  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(WORKSPACE, 'memory', 'recruiter-state.json')
GOG_ACCOUNT = os.environ.get('GOG_ACCOUNT', 'nervestaple@gmail.com')

RECRUITER_KEYWORDS = [
    'opportunity', 'role', 'position', 'hiring', 'join our team',
    'excited to connect', 'reaching out', 'open to', 'exploring',
    'engineer', 'frontend', 'full stack', 'fullstack', 'react', 'typescript',
    'founding', 'staff', 'principal', 'vp of engineering', 'head of',
]

SKIP_SENDERS = [
    'linkedin.com', 'greenhouse.io', 'lever.co', 'ashbyhq.com',
    'workday.com', 'jobvite', 'smartrecruiters',
]


# ── Auth ──────────────────────────────────────────────────────────────────────

def load_openai_key():
    # Prefer env var (set by OpenClaw gateway from .env SecretRefs)
    key = os.environ.get('OPENAI_API_KEY', '')
    if key:
        return key
    # Fallback: read from config (may be a SecretRef like ${OPENAI_API_KEY})
    try:
        with open('/home/claw/.openclaw/openclaw.json') as f:
            cfg = json.load(f)
        val = cfg['skills']['entries']['openai-whisper-api']['apiKey']
        if val and not val.startswith('$'):
            return val
    except Exception:
        pass
    return ''


# ── gog CLI helpers ──────────────────────────────────────────────────────────

def gog_search(query, max_results=50):
    """Search Gmail via gog CLI. Returns list of message dicts."""
    cmd = [
        'gog', 'gmail', 'messages', 'search', query,
        '--max', str(max_results),
        '--json', '--account', GOG_ACCOUNT,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"gog search failed (exit {result.returncode}): {result.stderr.strip()}")
    if not result.stdout.strip():
        return []
    data = json.loads(result.stdout)
    return data.get('messages', []) if isinstance(data, dict) else data


def gog_get(message_id):
    """Get full message via gog CLI. Returns message dict."""
    cmd = [
        'gog', 'gmail', 'get', message_id,
        '--json', '--account', GOG_ACCOUNT,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"gog get failed (exit {result.returncode}): {result.stderr.strip()}")
    return json.loads(result.stdout)


# ── GPT evaluation ────────────────────────────────────────────────────────────

def evaluate_opportunity(subject, sender, body_preview, openai_key):
    prompt = f"""You are evaluating a recruiter email for Jim, a senior frontend/fullstack engineer in Brooklyn, NY.

Jim's hiring preferences:
- HIGH INTEREST: high comp/equity, founding or early-team roles, fully remote, companies with genuine traction and interesting problem spaces
- ALSO HIGH INTEREST (comp not required): prestigious or rare orgs — academic institutions, research labs, nonprofits, public interest orgs, sports teams/leagues, major media companies — score 7+ on prestige alone if the org is notable
- SOFT AVOID: pure crypto/web3, generic "AI for X" wrapper companies — but not a hard block if genuinely compelling
- SKIP: mass blasts with no specifics, no named role, no company context

Email details:
From: {sender}
Subject: {subject}
Body: {body_preview[:1000]}

Return JSON only — no commentary outside the JSON:
{{
  "is_recruiter": true/false,
  "score": 0-10,
  "role": "job title or null",
  "company": "company name or null",
  "comp_signal": "any salary or equity mention, or null",
  "remote": "remote/hybrid/onsite/unknown",
  "red_flags": ["concern1", "concern2"],
  "summary": "one punchy sentence on why this is or isn't worth Jim's time"
}}"""

    data = json.dumps({
        'model': 'gpt-4o-mini',
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.2,
        'response_format': {'type': 'json_object'},
    }).encode()

    req = urllib.request.Request(
        'https://api.openai.com/v1/chat/completions', data=data,
        headers={'Authorization': f'Bearer {openai_key}',
                 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r:
        result = json.loads(r.read())

    return json.loads(result['choices'][0]['message']['content'])


# ── State ─────────────────────────────────────────────────────────────────────

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {'seen': []}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


# ── Report formatting ─────────────────────────────────────────────────────────

def format_entry(e):
    role    = e.get('role') or 'Unknown role'
    company = e.get('company') or 'Unknown company'
    score   = e.get('score', 0)
    remote  = {'remote': '🌐', 'hybrid': '🏢', 'onsite': '📍'}.get(e.get('remote', ''), '❓')
    comp    = e.get('comp_signal') or ''
    comp    = '' if comp.lower() in ('null', 'none', 'n/a', 'unknown', '') else comp
    flags   = [f for f in (e.get('red_flags') or [])
               if f and f.lower() not in ('null', 'none', 'n/a')]
    star    = ' ⭐' if score >= 7 else ''

    lines = [f"• {role} @ {company} [{score}/10]{star} {remote}",
             f"  {e.get('summary', '')}"]
    if comp:
        lines.append(f"  💰 {comp}")
    if flags:
        lines.append(f"  ⚠️ {', '.join(flags)}")
    return '\n'.join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    openai_key = load_openai_key()
    if not openai_key:
        print("No OpenAI key found.", file=sys.stderr)
        sys.exit(1)

    state = load_state()
    after = int((datetime.datetime.now() - datetime.timedelta(days=args.days)).timestamp())

    query = (f'in:inbox after:{after} '
             f'(opportunity OR "reaching out" OR "open to" OR hiring OR role OR position)')
    msgs = gog_search(query, max_results=50)
    print(f"Found {len(msgs)} candidate emails in last {args.days} days", flush=True)

    all_evaluated = []  # all recruiter emails with GPT scores

    for m in msgs:
        msg_id = m['id']
        if msg_id in state['seen']:
            continue

        sender  = m.get('from', '')
        subject = m.get('subject', '')

        if any(s in sender.lower() for s in SKIP_SENDERS):
            state['seen'].append(msg_id)
            continue

        combined = subject.lower()
        if not any(kw in combined for kw in RECRUITER_KEYWORDS):
            state['seen'].append(msg_id)
            continue

        # Fetch full body for promising candidates
        try:
            detail = gog_get(msg_id)
            body = detail.get('body', '') or subject
        except Exception as e:
            print(f"  gog get error for {msg_id}: {e}", flush=True)
            body = subject

        try:
            result = evaluate_opportunity(subject, sender, body, openai_key)
        except Exception as e:
            print(f"  GPT error: {subject[:40]}: {e}", flush=True)
            state['seen'].append(msg_id)
            continue

        state['seen'].append(msg_id)

        if not result.get('is_recruiter'):
            continue

        all_evaluated.append({**result, 'subject': subject, 'sender': sender})
        score = result.get('score', 0)
        print(f"  [{score}/10] {result.get('company','?')} — {result.get('role','?')}", flush=True)
        time.sleep(0.3)

    save_state(state)

    exceptional = [e for e in all_evaluated if e.get('score', 0) >= 7]
    print(f"\nEvaluated {len(all_evaluated)} recruiter emails. "
          f"{len(exceptional)} scored 7+.", flush=True)

    if not exceptional:
        print("Nothing worth reporting this week.")
        return

    # Report: all evaluated sorted by score, stars on 7+
    sorted_all = sorted(all_evaluated, key=lambda x: -x.get('score', 0))
    lines = [f"📋 Weekly recruiter scan ({len(all_evaluated)} evaluated, "
             f"{len(exceptional)} ⭐):\n"]
    lines += [format_entry(e) for e in sorted_all]
    report = '\n\n'.join(lines).strip()

    if args.dry_run:
        print('\n' + report)
    else:
        print('\n' + report)
        # In production this runs via cron → main session → message tool
        # The cron system-event handler sends the Telegram message


if __name__ == '__main__':
    main()
