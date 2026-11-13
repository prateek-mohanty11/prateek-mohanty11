#!/usr/bin/env python3
"""Build GitHub README SVG cards from data/contributions.json.

Run: python scripts/render_cards.py
Screenshot mode: STATIC=1 python scripts/render_cards.py
Optional font embedding: FONT_FILE=assets/ProfileSans.ttf (requires fonttools and brotli).
"""
from __future__ import annotations
import base64
import html
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv('CONTRIBUTION_JSON', ROOT / 'data' / 'contributions.json'))
OUT = ROOT / 'cards'
STATIC = os.getenv('STATIC', '0').lower() in {'1', 'true', 'yes'}
BG = os.getenv('CARD_BG', '#090914')
PANEL = os.getenv('CARD_PANEL', '#11111f')
PANEL2 = os.getenv('CARD_PANEL_2', '#17152a')
TEXT = os.getenv('CARD_TEXT', '#f5f3ff')
MUTED = os.getenv('CARD_MUTED', '#a6a0bd')
BRAND = os.getenv('CARD_BRAND', '#a855f7')
BRAND2 = os.getenv('CARD_BRAND_2', '#7c3aed')
ACCENT = os.getenv('CARD_ACCENT', '#c4b5fd')
BORDER = os.getenv('CARD_BORDER', '#30264a')
FONT = 'ProfileSans, Inter, ui-sans-serif, system-ui, sans-serif'
W = 960


def e(v):
    return html.escape(str(v or ''), quote=True)


def slug(v):
    return re.sub(r'[^a-z0-9]+', '-', str(v).lower()).strip('-')[:32] or 'project'


def font_uri():
    source = os.getenv('FONT_FILE')
    if not source:
        return ''
    source_path = Path(source)
    if not source_path.is_absolute():
        source_path = ROOT / source_path
    if not source_path.exists():
        raise SystemExit(f'FONT_FILE not found: {source}')

    target = OUT / 'profile-subset.woff'
    OUT.mkdir(parents=True, exist_ok=True)
    # Complete character set including arrows, stars, bullets and box-drawing/symbols
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,;:!?@#&()[]{}+-=*/_—–\'’“”%₹→←·★⑂↗•'
    unicodes = ','.join(f'U+{ord(c):04X}' for c in sorted(set(chars)))

    # Try Python module invocation first (works when pip installed without script on PATH)
    cmd = [
        sys.executable, '-m', 'fontTools.subset', str(source_path),
        f'--output-file={target}', '--flavor=woff',
        f'--unicodes={unicodes}', '--layout-features=*', '--name-IDs=0,1,2,4,6'
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        if shutil.which('pyftsubset'):
            subprocess.run([
                'pyftsubset', str(source_path), f'--output-file={target}', '--flavor=woff',
                f'--unicodes={unicodes}', '--layout-features=*', '--name-IDs=0,1,2,4,6'
            ], check=True)
        else:
            raise SystemExit('FONT_FILE requires fonttools and brotli (pip install fonttools brotli).')

    return 'data:font/woff;base64,' + base64.b64encode(target.read_bytes()).decode()


def start_svg(height, title, font='', width=W, extra_defs=''):
    face = f"@font-face{{font-family:ProfileSans;src:url('{font}') format('woff');font-weight:100 900}}" if font else ''
    if not STATIC:
        motion = '''
      .enter{opacity:0;transform:translateY(16px);animation:rise .8s cubic-bezier(.2,.75,.2,1) both}
      .pulse{animation:pulse 4s ease-in-out infinite}
      .draw{stroke-dasharray:1100;stroke-dashoffset:1100;animation:draw 1.8s ease-out forwards}
      .float{animation:float 5s ease-in-out infinite}
      @keyframes rise{to{opacity:1;transform:translateY(0)}}
      @keyframes pulse{0%,100%{opacity:.5}50%{opacity:1}}
      @keyframes draw{to{stroke-dashoffset:0}}
      @keyframes float{50%{transform:translateY(-5px)}}
      @media(prefers-reduced-motion:reduce){
        *,*::before,*::after{animation:none!important;transition:none!important}
        .enter{opacity:1!important;transform:none!important}
        .pulse,.float{animation:none!important;transform:none!important}
        animate,animateTransform,animateMotion{display:none!important}
        .shine-anim{display:none!important}
      }'''
    else:
        motion = '''
      .enter{opacity:1;transform:none}
      .pulse,.draw,.float{animation:none!important}
      @media(prefers-reduced-motion:reduce){
        *,*::before,*::after{animation:none!important;transition:none!important}
        .enter{opacity:1!important;transform:none!important}
        animate,animateTransform,animateMotion{display:none!important}
        .shine-anim{display:none!important}
      }'''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{e(title)}">
    <title>{e(title)}</title><defs><linearGradient id="brand" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{BRAND}"/><stop offset="1" stop-color="{BRAND2}"/></linearGradient>
    <linearGradient id="shine"><stop stop-color="{BRAND}" stop-opacity="0"/><stop offset=".5" stop-color="{ACCENT}"/><stop offset="1" stop-color="{BRAND}" stop-opacity="0"/></linearGradient>
    <filter id="blur"><feGaussianBlur stdDeviation="26"/></filter>{extra_defs}<style>{face}
    text{{font-family:{FONT}}}.title{{fill:{TEXT};font-size:31px;font-weight:750;letter-spacing:-.8px}}.sub{{fill:{MUTED};font-size:15px}}
    .label{{fill:{MUTED};font-size:12px;font-weight:650;letter-spacing:1.5px}}.metric{{fill:{TEXT};font-size:29px;font-weight:800}}
    .small{{fill:{MUTED};font-size:13px}}.panel{{fill:{PANEL};stroke:{BORDER};stroke-width:1.2}}{motion}</style></defs>
    <rect width="{width}" height="{height}" rx="26" fill="{BG}"/><circle cx="{int(width*.86)}" cy="38" r="125" fill="{BRAND}" opacity=".12" filter="url(#blur)"/>
    <rect x="1" y="1" width="{width-2}" height="{height-2}" rx="25" fill="none" stroke="{BORDER}"/>'''


def save(name, body):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(body + '</svg>\n', encoding='utf-8')


def days_from(data):
    result = []
    for x in data.get('contributions', []):
        try:
            result.append((date.fromisoformat(x['date']), int(x.get('count', 0))))
        except (KeyError, TypeError, ValueError):
            pass
    return sorted(result)


def calc_streaks(days):
    active = {d for d, n in days if n > 0}
    today = datetime.now(timezone.utc).date()
    cursor = today if today in active else today - timedelta(days=1)
    current = 0
    while cursor in active:
        current += 1
        cursor -= timedelta(days=1)
    longest = run = 0
    prev = None
    for d, n in days:
        if n:
            run = run + 1 if prev and d == prev + timedelta(days=1) else 1
            longest = max(longest, run)
            prev = d
        else:
            run = 0
            prev = None
    return current, longest


def vectorize_avatar(image_path_or_bytes, size=126, num_colors=72):
    try:
        from PIL import Image
        import io
        if isinstance(image_path_or_bytes, (bytes, bytearray)):
            im = Image.open(io.BytesIO(image_path_or_bytes))
        else:
            im = Image.open(image_path_or_bytes)

        # Center crop to square
        w, h = im.size
        dim = min(w, h)
        left = (w - dim) // 2
        top = (h - dim) // 2
        im = im.crop((left, top, left + dim, top + dim))

        im_resized = im.resize((size, size), Image.Resampling.LANCZOS)
        im_q = im_resized.quantize(colors=num_colors).convert('RGB')

        paths_by_color = defaultdict(list)
        r = size / 2
        cx, cy = r, r

        for y in range(size):
            run_start = None
            last_color = None
            for x in range(size):
                dist_sq = (x + 0.5 - cx)**2 + (y + 0.5 - cy)**2
                if dist_sq > r**2:
                    if run_start is not None:
                        paths_by_color[last_color].append(f'M{run_start} {y}h{x - run_start}v1h{run_start - x}z')
                        run_start = None
                    continue

                c = im_q.getpixel((x, y))
                hex_color = f'#{c[0]:02x}{c[1]:02x}{c[2]:02x}'

                if run_start is None:
                    run_start = x
                    last_color = hex_color
                elif hex_color != last_color:
                    paths_by_color[last_color].append(f'M{run_start} {y}h{x - run_start}v1h{run_start - x}z')
                    run_start = x
                    last_color = hex_color

            if run_start is not None:
                paths_by_color[last_color].append(f'M{run_start} {y}h{size - run_start}v1h{run_start - size}z')

        svg_paths = ''.join(f'<path fill="{c}" d="{"".join(d)}"/>' for c, d in paths_by_color.items())
        return f'<g transform="translate(761, 74)">{svg_paths}</g>'
    except Exception as exc:
        print(f"Warning: avatar vectorization failed: {exc}")
        return ''


def render_hero(data, font):
    name = data.get('name') or 'Prateek Mohanty'
    bio = data.get('bio') or 'Engineering student • Developer • AI/ML enthusiast'
    profile = data.get('profile_url') or 'https://github.com/prateek-mohanty11'
    website = data.get('website_url') or 'https://prateek-mohanty.vercel.app'
    avatar = data.get('avatar_url')
    avatar_vector = ''

    # Prioritize local profile photo in assets if present
    local_avatar = ROOT / 'assets' / 'my_photo.jpeg'
    if local_avatar.exists():
        avatar_vector = vectorize_avatar(local_avatar)
    elif avatar:
        try:
            req = urllib.request.Request(avatar, headers={'User-Agent': 'profile-svg-card-builder'})
            with urllib.request.urlopen(req, timeout=12) as response:
                avatar_vector = vectorize_avatar(response.read())
        except Exception:
            avatar_vector = ''  # Fall back to the PM monogram.

    s = start_svg(280, f'{name} profile introduction', font)
    s += f'''<rect x="24" y="24" width="912" height="232" rx="22" class="panel"/><rect x="24" y="24" width="5" height="232" rx="2" fill="url(#brand)"/>
    <g class="enter" style="animation-delay:0s"><text x="64" y="72" class="label">HELLO, I'M</text><text x="64" y="128" class="title" font-size="48">{e(name)}</text>
    <text x="64" y="164" class="sub">{e(bio[:100])}</text><rect x="64" y="193" width="150" height="38" rx="19" fill="url(#brand)"/>
    <text x="139" y="217" fill="#fff" font-size="13" font-weight="700" text-anchor="middle">GITHUB PROFILE ↗</text>
    <a href="{e(profile)}" xlink:href="{e(profile)}" target="_blank"><rect x="64" y="193" width="150" height="38" rx="19" fill="transparent"/></a>
    <a href="{e(website)}" xlink:href="{e(website)}" target="_blank"><text x="235" y="217" fill="{ACCENT}" font-size="13" font-weight="700">PORTFOLIO ↗</text></a></g>
    <circle cx="824" cy="137" r="82" fill="{BRAND}" opacity=".13" class="pulse"/>'''
    if avatar_vector:
        s += f'''<g class="enter float" style="animation-delay:.15s"><circle cx="824" cy="137" r="69" fill="url(#brand)"/>
        {avatar_vector}</g>'''
    else:
        s += '<g class="enter float" style="animation-delay:.15s"><circle cx="824" cy="137" r="69" fill="url(#brand)"/><text x="824" y="154" text-anchor="middle" fill="#fff" font-size="46" font-weight="800">PM</text></g>'
    save('01-hero.svg', s)


def render_link_tile(filename, label, url, delay, font):
    # Each standalone SVG is 312px wide so three README img tags at 32.5% fit in a row.
    s = start_svg(116, label + ' link', font, width=312)
    s += f'''<a href="{e(url)}" xlink:href="{e(url)}" target="_blank"><g class="enter" style="animation-delay:{delay}s">
    <rect x="8" y="8" width="296" height="100" rx="18" fill="{PANEL2}" stroke="{BORDER}"/><rect x="9" y="9" width="294" height="3" rx="2" fill="url(#brand)"/>
    <text x="28" y="53" fill="{TEXT}" font-size="23" font-weight="750">{e(label)}</text><text x="28" y="80" class="small">OPEN ↗</text>
    <circle cx="270" cy="58" r="23" fill="url(#brand)"/><text x="270" y="65" text-anchor="middle" fill="#fff" font-size="21" font-weight="800">↗</text></g></a>'''
    save(filename, s)


def render_activity(data, font):
    days = days_from(data)
    monthly = defaultdict(int)
    weekdays = Counter()
    for d, n in days:
        monthly[d.strftime('%b')] += n
        weekdays[d.strftime('%A')] += n
    # Retain the final 12 month buckets in chronological order.
    month_map = {}
    for d, n in days:
        month_map[(d.year, d.month)] = month_map.get((d.year, d.month), 0) + n
    last12 = sorted(month_map.items())[-12:]
    vals = [v for _, v in last12]
    maximum = max(vals, default=1) or 1
    current, longest = calc_streaks(days)
    active = sum(n > 0 for _, n in days)
    peak = max(days, key=lambda x: x[1], default=(date.today(), 0))
    busiest = max(weekdays, key=weekdays.get) if weekdays else '—'
    s = start_svg(360, 'GitHub contribution activity', font)
    s += '<rect x="24" y="24" width="912" height="312" rx="22" class="panel"/><g class="enter" style="animation-delay:.9s"><text x="52" y="65" class="label">CONTRIBUTION PULSE</text><text x="52" y="101" class="title">Consistency compounds.</text></g>'
    for i, (lab, val) in enumerate([('CURRENT STREAK', f'{current} days'), ('ACTIVE DAYS', str(active)), ('LONGEST STREAK', f'{longest} days')]):
        x = 52 + i * 190
        s += f'<g class="enter" style="animation-delay:{1.05+i*.12}s"><text x="{x}" y="142" class="label">{lab}</text><text x="{x}" y="180" class="metric">{e(val)}</text></g>'
    s += '<text x="52" y="224" class="label">MONTHLY CONTRIBUTIONS · LAST 12 MONTHS</text>'
    for i, ((yr, mo), v) in enumerate(zip([k for k, _ in last12], vals)):
        h = max(3, int(v / maximum * 55))
        x = 54 + i * 69
        label = date(yr, mo, 1).strftime('%b')
        s += f'<g class="enter" style="animation-delay:{1.45+i*.055}s"><rect x="{x}" y="{300-h}" width="45" height="{h}" rx="7" fill="url(#brand)"/><text x="{x+22}" y="320" text-anchor="middle" class="small">{label}</text></g>'
    s += f'<g class="enter" style="animation-delay:2.2s"><text x="745" y="142" class="label">BUSIEST WEEKDAY</text><text x="745" y="180" fill="{ACCENT}" font-size="24" font-weight="800">{e(busiest)}</text><text x="745" y="204" class="small">Peak date: {peak[0].strftime("%d %b %Y")}</text><text x="745" y="226" class="small">{peak[1]} contributions</text></g>'
    if not STATIC:
        s += '<rect class="shine-anim" x="24" y="24" width="912" height="2" fill="url(#shine)"><animate attributeName="x" values="-920;960" dur="5s" repeatCount="indefinite"/></rect>'
    save('03-activity.svg', s)


def render_repo(repo, index, font):
    name = repo.get('name') or f'Featured project {index}'
    desc = repo.get('description') or 'A project built to solve a practical problem.'
    url = repo.get('url') or '#'
    lang = repo.get('language') or 'Project'
    s = start_svg(190, 'Featured repository ' + name, font)
    s += f'''<a href="{e(url)}" xlink:href="{e(url)}" target="_blank"><g class="enter" style="animation-delay:{2.4+(index-1)*.9}s">
    <rect x="24" y="24" width="912" height="142" rx="22" class="panel"/><rect x="24" y="24" width="5" height="142" rx="2" fill="url(#brand)"/>
    <text x="54" y="61" class="label">FEATURED REPOSITORY · {index:02d}</text><text x="54" y="99" class="title">{e(name[:42])}</text>
    <text x="54" y="128" class="sub">{e(desc[:105])}</text><rect x="730" y="52" width="170" height="34" rx="17" fill="{PANEL2}" stroke="{BORDER}"/>
    <text x="815" y="74" text-anchor="middle" fill="{ACCENT}" font-size="12" font-weight="700">{e(lang)}</text>
    <text x="730" y="122" class="small">★ {e(repo.get('stars', 0))}　⑂ {e(repo.get('forks', 0))}　 VIEW ↗</text></g></a>'''
    save(f'repo-{index:02d}-{slug(name)}.svg', s)


def render_graph(days, font):
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=363)
    start -= timedelta(days=(start.weekday() + 1) % 7)
    counts = {d: n for d, n in days}
    maxn = max(counts.values(), default=1) or 1
    colors = ['#211a32', '#4b2872', '#7040a5', BRAND, ACCENT]
    s = start_svg(230, 'GitHub contribution graph', font)
    s += '<rect x="24" y="24" width="912" height="182" rx="22" class="panel"/><text x="52" y="61" class="label">ONE YEAR OF SHOWING UP</text><text x="52" y="88" class="small">Contribution activity · brand-colour intensity</text>'
    for week in range(53):
        for dow in range(7):
            d = start + timedelta(days=week * 7 + dow)
            if d > today:
                continue
            n = counts.get(d, 0)
            level = 0 if n == 0 else min(4, max(1, int(n / maxn * 4) + 1))
            x = 54 + week * 14
            y = 111 + dow * 14
            s += f'<rect x="{x}" y="{y}" width="10" height="10" rx="2" fill="{colors[level]}"><title>{d.isoformat()}: {n} contributions</title></rect>'
    for i, (label, color) in enumerate(zip(['0', '1+', '25%', '50%', '75%+'], colors)):
        x = 690 + i * 43
        s += f'<rect x="{x}" y="{178}" width="10" height="10" rx="2" fill="{color}"/><text x="{x+14}" y="188" class="small">{label}</text>'
    save('99-contributions.svg', s)


def update_readme(repo_md):
    readme_path = ROOT / 'README.md'
    if not readme_path.exists():
        return
    text = readme_path.read_text(encoding='utf-8')
    start = '<!-- FEATURED_REPOS_START -->'
    end = '<!-- FEATURED_REPOS_END -->'
    if start not in text or end not in text:
        return
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    new_content = before + start + '\n' + (repo_md + '\n' if repo_md else '') + end + after
    readme_path.write_text(new_content, encoding='utf-8')


def main():
    if not DATA.exists():
        raise SystemExit(f'Missing {DATA}. Run the contribution data generation step first.')
    data = json.loads(DATA.read_text(encoding='utf-8'))
    OUT.mkdir(parents=True, exist_ok=True)
    font = font_uri()
    for old in OUT.glob('repo-*.svg'):
        old.unlink()
    render_hero(data, font)
    render_link_tile('02-github.svg', 'GitHub', data.get('profile_url', 'https://github.com/prateek-mohanty11'), 0.9, font)
    render_link_tile('02-linkedin.svg', 'LinkedIn', data.get('linkedin_url', 'https://www.linkedin.com/in/prateek-mohanty-134806331'), 1.05, font)
    render_link_tile('02-portfolio.svg', 'Portfolio', data.get('website_url', 'https://prateek-mohanty.vercel.app'), 1.2, font)
    render_activity(data, font)
    repos = data.get('featured_repos', [])
    for i, repo in enumerate(repos, 1):
        render_repo(repo, i, font)

    repo_md_lines = []
    for i, repo in enumerate(repos, 1):
        r_name = repo.get('name') or f'Featured project {i}'
        r_url = repo.get('url') or '#'
        r_slug = slug(r_name)
        repo_md_lines.append(
            f'<a href="{e(r_url)}"><img src="cards/repo-{i:02d}-{r_slug}.svg" alt="{e(r_name)}" width="100%"></a>'
        )
    repo_md = '\n'.join(repo_md_lines)
    (OUT / 'featured-repos.md').write_text(repo_md + ('\n' if repo_md else ''), encoding='utf-8')
    update_readme(repo_md)

    render_graph(days_from(data), font)
    print(f'Rendered {len(list(OUT.glob("*.svg")))} SVG cards in {OUT}; STATIC={int(STATIC)}')


if __name__ == '__main__':
    main()

