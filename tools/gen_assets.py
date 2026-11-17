"""Generate the gold "title sequence" themed profile README and its SVG art.

Usage: python gen_assets.py <cache_dir> <repo_root> <art_dir>

  <cache_dir>  profile.json + avatar.jpg written by fetch_data.py
  <repo_root>  the profile repository: README.md, assets/ (dividers, chess board), data/chess.json
  <art_dir>    data-driven art (hero, lead, galaxy, city, repo cards); published on the "output" branch

Optional: <repo_root>/assets/shots/<repo>.png|jpg replaces the illustrated thumbnail on that repo's card.
"""
import base64
import datetime as dt
import json
import math
import random
import sys
import urllib.parse
from pathlib import Path

import chess

cache, root, art = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
assets = root / "assets"
assets.mkdir(parents=True, exist_ok=True)
art.mkdir(parents=True, exist_ok=True)
P = json.loads((cache / "profile.json").read_text(encoding="utf-8"))
AVATAR = "data:image/jpeg;base64," + base64.b64encode((cache / "avatar.jpg").read_bytes()).decode()

# ------------------------------------------------------------------ personal copy (edit freely)
ABOUT_FALLBACK = "Competitive FOMO: CTF · CP · Hackathon · IoT."  # used only when the GitHub bio is empty
DESCRIPTIONS = {
    "Uang-Papi": "Monthly income & expense tracker for students in a kos.",
    "TubesKursusInAlpro2": "Final project (Tugas Besar) for Algorithms & Programming 2.",
}
CAMPUS = "Telkom University"

# ------------------------------------------------------------------ palette (from the title-sequence look)
INK, INK2, UMBER = "#070503", "#120c04", "#2c1d06"
GOLD_HI, GOLD, GOLD_MID, GOLD_DK, BRONZE = "#fff0c2", "#f2c14e", "#d6a033", "#8f6417", "#5c3f0e"
CREAM, MUTED, LINE = "#f7ecd2", "#b39a60", "#5a4213"
LANG_TINT = ["#ffd766", "#ff9f43", "#fff3d0", "#b9812a", "#e8c27a", "#8f6417"]  # in-palette language colours
LANG_ABBR = {"TypeScript": "TS", "JavaScript": "JS", "Go": "GO", "Python": "PY", "C++": "C+", "HTML": "H5", "CSS": "CS"}

DISPLAY = "'Arial Black', 'Segoe UI Black', 'Helvetica Neue', Impact, Arial, sans-serif"
SANS = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
SERIF = "Georgia, 'Times New Roman', serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"

# ------------------------------------------------------------------ derived data
LOGIN, NAME = P["login"], P["name"]
PROJECTS = sorted((r for r in P["repos"] if r["name"].lower() != LOGIN.lower()), key=lambda r: (-r["stars"], r["name"]))
STARS = sum(r["stars"] for r in P["repos"])
LANG_BYTES = {}
for r in P["repos"]:
    for k, v in r["languages"].items():
        LANG_BYTES[k] = LANG_BYTES.get(k, 0) + v
LANGS = sorted(LANG_BYTES.items(), key=lambda kv: -kv[1])
LANG_TOTAL = sum(LANG_BYTES.values()) or 1
LANG_COLOR = {k: LANG_TINT[min(i, len(LANG_TINT) - 1)] for i, (k, _) in enumerate(LANGS)}
DAYS = {dt.date.fromisoformat(k): v for k, v in P["contributions"].items()}
TOTAL = sum(DAYS.values())
ACTIVE = sum(1 for v in DAYS.values() if v)
BUSIEST = max(DAYS.values()) if DAYS else 0


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wrap(text, width):
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = (cur + " " + word).strip()
    return lines + ([cur] if cur else [])


def save_art(name, svg):
    (art / name).write_text(svg, encoding="utf-8", newline="\n")


def save_static(name, svg):
    (assets / name).write_text(svg, encoding="utf-8", newline="\n")


GOLD_TEXT_GRAD = f'''<linearGradient id="goldText" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#fff5cf"/><stop offset="0.45" stop-color="#f7cb58"/>
  <stop offset="0.56" stop-color="#e2aa30"/><stop offset="1" stop-color="#c0871b"/></linearGradient>'''


# ================================================================== 1. title sequence
def hero():
    W, H = 900, 500
    words = NAME.upper().split()
    line1, line2 = (" ".join(words[:-1]), words[-1]) if len(words) > 2 else (NAME.upper(), "")
    size = 86
    y1, y2 = (184, 268) if line2 else (226, 0)

    def title(text, y, clip=False):
        if clip:
            return (f'<text x="450" y="{y}" text-anchor="middle" font-family="{DISPLAY}" font-size="{size}" '
                    f'font-weight="900" letter-spacing="1">{esc(text)}</text>')
        out = []
        for i in range(9, 0, -1):
            shade = "#3d2a08" if i > 6 else "#5d410d" if i > 3 else "#7d5912"
            out.append(f'<text x="{450 + i * 0.9:.1f}" y="{y + i * 0.9:.1f}" text-anchor="middle" font-family="{DISPLAY}" '
                       f'font-size="{size}" font-weight="900" letter-spacing="1" fill="{shade}">{esc(text)}</text>')
        out.append(f'<text x="450" y="{y}" text-anchor="middle" font-family="{DISPLAY}" font-size="{size}" font-weight="900" '
                   f'letter-spacing="1" fill="url(#goldText)" stroke="#fff8dd" stroke-opacity="0.35" stroke-width="0.7">{esc(text)}</text>')
        return "".join(out)

    top2 = " · ".join(k.upper() for k, _ in LANGS[:2])
    credits = []
    for r in PROJECTS[:6]:
        tail = f"★ {r['stars']}" if r["stars"] else (r["language"] or "")
        credits.append(("starring ", r["name"], f" · {tail}" if tail else ""))
    if P["location"]:
        credits.append(("filmed on location in ", P["location"].split(",")[0], ""))
    credits.append(("a ", CAMPUS, " production"))
    step = 30
    roll = "".join(
        f'<text x="450" y="{22 + i * step}" text-anchor="middle" font-family="{SERIF}" font-size="18" fill="{CREAM}">'
        f'<tspan fill-opacity="0.72">{esc(a)}</tspan><tspan font-weight="700">{esc(b)}</tspan>'
        f'<tspan fill-opacity="0.72">{esc(c)}</tspan></text>'
        for i, (a, b, c) in enumerate(credits))
    travel = len(credits) * step + 10
    sub_y = (y2 if line2 else y1) + 50
    roll_y, roll_h = sub_y + 22, 448 - (sub_y + 22) - 6
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub Pictures presents {esc(NAME)}">
<style>
  .cap {{ opacity: 0; animation: fade 1.4s ease-out .2s forwards; }}
  .ttl {{ opacity: 0; animation: rise 1.5s cubic-bezier(.2,.7,.2,1) .8s forwards; }}
  .sub {{ opacity: 0; animation: fade 1.4s ease-out 1.8s forwards; }}
  .roll {{ animation: roll {max(12, len(credits) * 3.4):.0f}s linear -3s infinite; }}
  .credits {{ opacity: 0; animation: fade 1.2s ease-out 2.2s forwards; }}
  .shine {{ animation: shine 7s ease-in-out 3s infinite both; }}
  @keyframes fade {{ to {{ opacity: 1; }} }}
  @keyframes rise {{ from {{ opacity: 0; transform: translateY(16px); }} to {{ opacity: 1; transform: none; }} }}
  @keyframes roll {{ from {{ transform: translateY({roll_h}px); }} to {{ transform: translateY(-{travel}px); }} }}
  @keyframes shine {{ 0% {{ transform: translateX(-200px); }} 35%, 100% {{ transform: translateX(1300px); }} }}
</style>
<defs>
  {GOLD_TEXT_GRAD}
  <clipPath id="frame"><rect width="{W}" height="{H}" rx="16"/></clipPath>
  <clipPath id="tclip">{title(line1, y1, True)}{title(line2, y2, True) if line2 else ""}</clipPath>
  <radialGradient id="warm" cx="50%" cy="46%" r="62%">
    <stop offset="0" stop-color="#3b2707"/><stop offset="0.55" stop-color="#1a1104"/><stop offset="1" stop-color="{INK}"/>
  </radialGradient>
  <radialGradient id="vig" cx="50%" cy="50%" r="72%">
    <stop offset="0.6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.7"/>
  </radialGradient>
  <linearGradient id="rollfade" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.3" stop-color="#fff"/>
    <stop offset="0.75" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>
  <mask id="rollmask" maskUnits="userSpaceOnUse" x="0" y="{roll_y}" width="{W}" height="{roll_h}">
    <rect x="0" y="{roll_y}" width="{W}" height="{roll_h}" fill="url(#rollfade)"/>
  </mask>
</defs>
<g clip-path="url(#frame)">
  <rect width="{W}" height="{H}" fill="url(#warm)"/>
  <rect width="{W}" height="{H}" fill="url(#vig)"/>
  <text class="cap" x="450" y="92" text-anchor="middle" font-family="{MONO}" font-size="12.5" letter-spacing="9" fill="{GOLD_MID}">GITHUB PICTURES PRESENTS</text>
  <g class="ttl">
    {title(line1, y1)}{title(line2, y2) if line2 else ""}
    <g clip-path="url(#tclip)"><g transform="skewX(-22)"><rect class="shine" x="0" y="80" width="70" height="230" fill="#fff" fill-opacity="0.6"/></g></g>
  </g>
  <text class="sub" x="450" y="{sub_y}" text-anchor="middle" font-family="{SANS}" font-size="17" letter-spacing="6" fill="{CREAM}">{esc(top2)} DEVELOPER</text>
  <g class="credits"><g mask="url(#rollmask)"><g transform="translate(0 {roll_y})"><g class="roll">{roll}</g></g></g></g>
  <rect width="{W}" height="40" fill="#000"/>
  <rect y="448" width="{W}" height="52" fill="#000"/>
  <text x="40" y="479" font-family="{MONO}" font-size="11.5" fill="{MUTED}">{TOTAL:,} contributions · {P["followers"]} followers · ★ {STARS}</text>
  <text x="{W - 40}" y="479" text-anchor="end" font-family="{MONO}" font-size="11.5" fill="{MUTED}">github.com/{esc(LOGIN)}</text>
</g>
<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="15.5" fill="none" stroke="{LINE}" stroke-opacity="0.9"/>
</svg>'''


# ================================================================== 2. the lead
def lead():
    W, H = 900, 240
    about_lines = wrap(P["bio"] or ABOUT_FALLBACK, 66)[:3]
    meta = " · ".join(x for x in [P["location"], P["company"], f'{P["followers"]} followers',
                                  f'{P["public_repos"]} repositories'] if x)
    about = "".join(f'<text x="44" y="{134 + i * 24}" font-family="{SANS}" font-size="16" fill="{CREAM}" fill-opacity="0.92">{esc(t)}</text>'
                    for i, t in enumerate(about_lines))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="The lead: {esc(NAME)}">
<style>
  .ring {{ transform-box: fill-box; transform-origin: center; animation: spin 40s linear infinite; }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
</style>
<defs>
  <linearGradient id="card" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#33230a"/><stop offset="0.55" stop-color="#1a1205"/><stop offset="1" stop-color="#0b0803"/>
  </linearGradient>
  <radialGradient id="halo" cx="50%" cy="50%" r="50%">
    <stop offset="0.55" stop-color="{GOLD}" stop-opacity="0.35"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/>
  </radialGradient>
  <clipPath id="av"><circle cx="776" cy="120" r="62"/></clipPath>
</defs>
<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="18" fill="url(#card)" stroke="{GOLD_DK}" stroke-opacity="0.7"/>
<text x="44" y="56" font-family="{MONO}" font-size="11.5" letter-spacing="7" fill="{GOLD}">THE LEAD</text>
<text x="44" y="102" font-family="{SANS}" font-size="34" font-weight="800" fill="{CREAM}">{esc(NAME)}</text>
{about}
<text x="44" y="210" font-family="{MONO}" font-size="12" fill="{MUTED}">{esc(meta)}</text>
<circle cx="776" cy="120" r="96" fill="url(#halo)"/>
<circle class="ring" cx="776" cy="120" r="76" fill="none" stroke="{GOLD}" stroke-opacity="0.45" stroke-dasharray="2 9" stroke-linecap="round"/>
<image href="{AVATAR}" x="714" y="58" width="124" height="124" clip-path="url(#av)" preserveAspectRatio="xMidYMid slice"/>
<circle cx="776" cy="120" r="63.5" fill="none" stroke="{GOLD}" stroke-width="4"/>
</svg>'''


# ================================================================== section dividers
def divider(text):
    W, H = 900, 44
    half = len(text) * 13.4 / 2 + 26
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(text)}">
<defs><linearGradient id="l" x1="0" x2="1"><stop offset="0" stop-color="{GOLD}" stop-opacity="0"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0.75"/></linearGradient>
<linearGradient id="r" x1="1" x2="0"><stop offset="0" stop-color="{GOLD}" stop-opacity="0"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0.75"/></linearGradient></defs>
<rect x="40" y="21.5" width="{450 - half - 40:.0f}" height="1" fill="url(#l)"/>
<rect x="{450 + half:.0f}" y="21.5" width="{450 - half - 40:.0f}" height="1" fill="url(#r)"/>
<path d="M{450 - half + 8:.0f} 22 l5 -5 l5 5 l-5 5 Z M{450 + half - 18:.0f} 22 l5 -5 l5 5 l-5 5 Z" fill="{GOLD}"/>
<text x="453" y="26.5" text-anchor="middle" font-family="{MONO}" font-size="12.5" letter-spacing="6" fill="{GOLD}">{esc(text)}</text>
</svg>'''


# ================================================================== 3. repo cards (aquarium layout, gold gradient)
def thumb(repo, x, y, w, h):
    for ext, mime in ((".png", "image/png"), (".jpg", "image/jpeg")):
        shot = assets / "shots" / (repo["name"] + ext)
        if shot.exists():
            uri = f"data:{mime};base64," + base64.b64encode(shot.read_bytes()).decode()
            return (f'<clipPath id="tc"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/></clipPath>'
                    f'<image href="{uri}" x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMin slice" clip-path="url(#tc)"/>'
                    f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="none" stroke="{GOLD}" stroke-opacity="0.35"/>')
    rnd = random.Random(repo["name"])
    body = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#0b0803" stroke="{GOLD}" stroke-opacity="0.35"/>',
            f'<rect x="{x}" y="{y}" width="{w}" height="14" rx="8" fill="#241806"/>',
            f'<rect x="{x}" y="{y + 8}" width="{w}" height="6" fill="#241806"/>',
            "".join(f'<circle cx="{x + 9 + i * 8}" cy="{y + 7}" r="2.2" fill="{GOLD}" fill-opacity="{0.9 - i * 0.25}"/>' for i in range(3))]
    if repo["language"] in ("Go", "C", "C++", "Python", "Rust", "Shell"):  # terminal-ish placeholder
        for i in range(5):
            ly = y + 26 + i * 11
            body.append(f'<text x="{x + 9}" y="{ly + 3}" font-family="{MONO}" font-size="8" fill="{GOLD}">$</text>')
            body.append(f'<rect x="{x + 19}" y="{ly - 2}" width="{rnd.randint(34, 104)}" height="4" rx="2" fill="{CREAM}" fill-opacity="{0.25 + 0.12 * (i % 3)}"/>')
    else:  # dashboard-ish placeholder
        body.append(f'<rect x="{x + 9}" y="{y + 22}" width="52" height="5" rx="2.5" fill="{GOLD}"/>')
        body.append(f'<rect x="{x + 9}" y="{y + 32}" width="34" height="4" rx="2" fill="{CREAM}" fill-opacity="0.3"/>')
        for i in range(7):
            bh = rnd.randint(10, 40)
            body.append(f'<rect x="{x + 12 + i * 11}" y="{y + h - 9 - bh}" width="7" height="{bh}" rx="2" fill="{GOLD}" fill-opacity="{0.45 + 0.08 * (i % 4)}"/>')
        body.append(f'<rect x="{x + 96}" y="{y + 24}" width="44" height="22" rx="4" fill="{GOLD}" fill-opacity="0.14" stroke="{GOLD}" stroke-opacity="0.35"/>')
        body.append(f'<rect x="{x + 96}" y="{y + 52}" width="44" height="22" rx="4" fill="{GOLD}" fill-opacity="0.08" stroke="{GOLD}" stroke-opacity="0.25"/>')
    return "".join(body)


def card(idx, repo):
    W, H = 440, 212
    desc = wrap(DESCRIPTIONS.get(repo["name"]) or repo["description"], 31)[:3]
    desc_svg = "".join(f'<text x="28" y="{124 + i * 20}" font-family="{SANS}" font-size="14" fill="{CREAM}" fill-opacity="0.86">{esc(t)}</text>'
                       for i, t in enumerate(desc))
    lang = repo["language"] or "—"
    abbr = LANG_ABBR.get(lang, lang[:2].upper())
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(repo["name"])}: {esc(" ".join(desc))}">
<defs>
  <linearGradient id="aq" x1="0" y1="0" x2="0.9" y2="1">
    <stop offset="0" stop-color="#5a400f"/><stop offset="0.5" stop-color="#33230a"/><stop offset="1" stop-color="#150e04"/>
  </linearGradient>
  <radialGradient id="lamp" cx="82%" cy="12%" r="60%">
    <stop offset="0" stop-color="{GOLD}" stop-opacity="0.28"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/>
  </radialGradient>
</defs>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="24" fill="url(#aq)"/>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="24" fill="url(#lamp)" stroke="{GOLD}" stroke-opacity="0.5" stroke-width="1.5"/>
<path d="M24 17 h128" stroke="{CREAM}" stroke-opacity="0.45" stroke-width="3" stroke-linecap="round"/>
<text x="28" y="56" font-family="{MONO}" font-size="13" letter-spacing="4" fill="{GOLD}">REEL {idx:02d}</text>
<text x="28" y="98" font-family="{MONO}" font-size="19" font-weight="700" fill="{CREAM}">{esc(repo["name"])}</text>
{desc_svg}
{thumb(repo, 268, 88, 148, 84)}
<text x="28" y="190" font-family="{MONO}" font-size="13" fill="{CREAM}">★ {repo["stars"]}</text>
<g transform="translate(86 179)" stroke="{CREAM}" stroke-width="1.4" fill="none" stroke-linecap="round">
  <path d="M2 3 v2.5 q0 3 4 3 q4 0 4 -3 v-2.5 M6 8.5 v3"/><circle cx="2" cy="1.5" r="1.5"/><circle cx="10" cy="1.5" r="1.5"/><circle cx="6" cy="13" r="1.5"/>
</g>
<text x="104" y="190" font-family="{MONO}" font-size="13" fill="{CREAM}">{repo["forks"]}</text>
<rect x="138" y="176" width="20" height="19" rx="4" fill="{GOLD}"/>
<text x="148" y="189.5" text-anchor="middle" font-family="{SANS}" font-size="10" font-weight="800" fill="{INK}">{esc(abbr)}</text>
<text x="166" y="190" font-family="{MONO}" font-size="13" fill="{CREAM}">{esc(lang)}</text>
</svg>'''


# ================================================================== 4. repo galaxy
def galaxy():
    W, H = 900, 400
    rnd = random.Random(11)
    cx, cy, tilt, squash = 628, 204, -16, 0.52
    names = [k for k, _ in LANGS] or ["—"]
    weights = [v for _, v in LANGS] or [1]

    def colour():
        return LANG_COLOR.get(rnd.choices(names, weights)[0], GOLD) if rnd.random() < 0.8 else GOLD_HI

    dust = []
    for arm in range(2):
        for _ in range(330):
            t = rnd.random() ** 0.8
            th = t * 3.3 * math.pi + arm * math.pi + rnd.gauss(0, 0.11)
            r = 20 + t * 190 + rnd.gauss(0, 6)
            tw = ' class="tw" style="animation-delay:-%.1fs"' % rnd.uniform(0, 6) if rnd.random() < 0.12 else ""
            dust.append(f'<circle cx="{r * math.cos(th):.1f}" cy="{r * math.sin(th):.1f}" r="{rnd.uniform(0.9, 2.6):.1f}" '
                        f'fill="{colour()}" fill-opacity="{rnd.uniform(0.4, 1):.2f}"{tw}/>')
    for _ in range(150):  # halo
        r, th = 230 * math.sqrt(rnd.random()), rnd.uniform(0, 2 * math.pi)
        dust.append(f'<circle cx="{r * math.cos(th):.1f}" cy="{r * math.sin(th):.1f}" r="{rnd.uniform(0.5, 1.3):.1f}" '
                    f'fill="{GOLD_HI}" fill-opacity="{rnd.uniform(0.1, 0.4):.2f}"/>')
    for _ in range(60):  # core
        dust.append(f'<circle cx="{rnd.gauss(0, 15):.1f}" cy="{rnd.gauss(0, 15):.1f}" r="{rnd.uniform(0.8, 2):.1f}" fill="#fff6d8" fill-opacity="{rnd.uniform(0.4, 0.9):.2f}"/>')

    def project(r, th):
        x, y = r * math.cos(th), r * math.sin(th) * squash
        a = math.radians(tilt)
        return cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)

    repos = sorted(P["repos"], key=lambda r: (-r["stars"], r["name"]))[:8]
    stars = []
    for i, r in enumerate(repos):
        t = [0.5, 0.62, 0.86, 0.4, 0.74, 0.95, 0.56, 0.68][i]
        arm = i % 2
        sx, sy = project(20 + t * 190, t * 3.3 * math.pi + arm * math.pi)
        rad = 5 + 3.5 * math.log2(1 + r["stars"])
        col = LANG_COLOR.get(r["language"], GOLD_HI)
        label_w = len(r["name"]) * 7.4 + 44
        left = sx < cx and sx - rad - 9 - label_w > 300  # label points away from the core when there is room
        tx, anchor = (sx - rad - 9, "end") if left else (sx + rad + 9, "start")
        stars.append(
            f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{rad * 3.2:.1f}" fill="{col}" fill-opacity="0.1"/>'
            f'<circle class="pulse" style="animation-delay:-{i * 0.9:.1f}s" cx="{sx:.1f}" cy="{sy:.1f}" r="{rad * 1.9:.1f}" fill="{col}" fill-opacity="0.22"/>'
            f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{rad:.1f}" fill="{col}"/><circle cx="{sx:.1f}" cy="{sy:.1f}" r="{rad * 0.38:.1f}" fill="#fffdf2"/>'
            f'<text x="{tx:.1f}" y="{sy + 4:.1f}" text-anchor="{anchor}" font-family="{SANS}" font-size="12.5" font-weight="700" fill="{CREAM}" '
            f'stroke="{INK}" stroke-width="3" paint-order="stroke">{esc(r["name"])} <tspan fill="{GOLD}">★ {r["stars"]}</tspan></text>')
    legend = "".join(
        f'<circle cx="46" cy="{271 + i * 23}" r="5" fill="{LANG_COLOR[k]}"/>'
        f'<text x="62" y="{275.5 + i * 23}" font-family="{SANS}" font-size="13" font-weight="700" fill="{CREAM}">{esc(k)}</text>'
        f'<text x="206" y="{275.5 + i * 23}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{MUTED}">{v * 100 / LANG_TOTAL:.0f}%</text>'
        for i, (k, v) in enumerate(LANGS[:4]))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Repo galaxy of {esc(LOGIN)}: {STARS} stars, {P["public_repos"]} repositories">
<style>
  .rot {{ animation: rot 260s linear infinite; }}
  @keyframes rot {{ to {{ transform: rotate(360deg); }} }}
  .tw {{ animation: tw 3.5s ease-in-out infinite; }}
  @keyframes tw {{ 50% {{ fill-opacity: 0.1; }} }}
  .pulse {{ transform-box: fill-box; transform-origin: center; animation: pulse 3.6s ease-in-out infinite; }}
  @keyframes pulse {{ 50% {{ transform: scale(1.35); fill-opacity: 0.08; }} }}
</style>
<defs>
  <linearGradient id="space" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1c1305"/><stop offset="0.6" stop-color="#0c0803"/><stop offset="1" stop-color="{INK}"/></linearGradient>
  <radialGradient id="core" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#ffe9a8" stop-opacity="0.55"/><stop offset="0.4" stop-color="{GOLD}" stop-opacity="0.16"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>
  <clipPath id="gframe"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="17"/></clipPath>
</defs>
<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="18" fill="url(#space)" stroke="{GOLD_DK}" stroke-opacity="0.7"/>
<g clip-path="url(#gframe)">
  <g transform="translate({cx} {cy}) rotate({tilt}) scale(1 {squash})">
    <circle r="120" fill="url(#core)"/>
    <g class="rot">{''.join(dust)}</g>
  </g>
  {''.join(stars)}
</g>
<text x="40" y="58" font-family="{MONO}" font-size="11.5" letter-spacing="6" fill="{GOLD}">REPO GALAXY</text>
<text x="40" y="100" font-family="{SANS}" font-size="31" font-weight="800" fill="{CREAM}">@{esc(LOGIN)}</text>
<text x="40" y="128" font-family="{SANS}" font-size="15" font-weight="600" fill="{GOLD}">{STARS} star{"" if STARS == 1 else "s"} · {P["public_repos"]} repositories</text>
<text x="40" y="151" font-family="{SANS}" font-size="13" fill="{MUTED}">Each star is a repository, sized by its stars.</text>
<text x="40" y="246" font-family="{MONO}" font-size="10.5" letter-spacing="5" fill="{GOLD}">ARMS</text>
{legend}
</svg>'''


# ================================================================== 5. contribution city
def city():
    W, H = 900, 410
    a, b, ox, oy, inset = 9.2, 4.6, 352, 88, 0.86
    ai, bi = a * inset, b * inset
    first = min(DAYS)
    sunday = first - dt.timedelta(days=(first.weekday() + 1) % 7)
    top_c = ["#241a09", "#a87a22", "#d6a033", "#f2c14e", "#fff0c2"]
    left_c = ["#181105", "#7a5716", "#a67a22", "#c99632", "#e9cd84"]
    right_c = ["#0f0b04", "#4f370c", "#6f4f12", "#8f6a1c", "#b89345"]
    cells = []
    for day, count in DAYS.items():
        off = (day - sunday).days
        w, d = off // 7, off % 7
        lvl = 0 if not count else min(4, 1 + int(3.999 * count / BUSIEST))
        h = 2 if not count else 9 + 62 * math.sqrt(count / BUSIEST)
        x, y = ox + (w - d) * a, oy + (w + d) * b + b

        def pts(*p):
            return " ".join(f"{px:.1f},{py:.1f}" for px, py in p)

        g = (f'<polygon points="{pts((x - ai, y - h), (x, y + bi - h), (x, y + bi), (x - ai, y))}" fill="{left_c[lvl]}"/>'
             f'<polygon points="{pts((x, y + bi - h), (x + ai, y - h), (x + ai, y), (x, y + bi))}" fill="{right_c[lvl]}"/>'
             f'<polygon points="{pts((x, y - bi - h), (x + ai, y - h), (x, y + bi - h), (x - ai, y - h))}" fill="{top_c[lvl]}"/>')
        if count:
            g = f'<g class="grow" style="animation-delay:{0.4 + w * 0.03:.2f}s">{g}</g>'
        cells.append((w + d, g))
    cells.sort(key=lambda c: c[0])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Contribution city: {TOTAL} contributions in the last year, {ACTIVE} active days, busiest day {BUSIEST}">
<style>
  .grow {{ transform-box: fill-box; transform-origin: 50% 100%; animation: grow 1.1s cubic-bezier(.2,.8,.2,1) both; }}
  @keyframes grow {{ from {{ transform: scaleY(0.04); }} to {{ transform: scaleY(1); }} }}
</style>
<defs>
  <linearGradient id="dusk" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3a290b"/><stop offset="0.5" stop-color="#1c1305"/><stop offset="1" stop-color="#0a0703"/></linearGradient>
  <radialGradient id="sun" cx="78%" cy="8%" r="65%"><stop offset="0" stop-color="{GOLD}" stop-opacity="0.22"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>
  {GOLD_TEXT_GRAD}
</defs>
<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="18" fill="url(#dusk)"/>
<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="18" fill="url(#sun)" stroke="{GOLD_DK}" stroke-opacity="0.7"/>
{''.join(g for _, g in cells)}
<text x="40" y="58" font-family="{MONO}" font-size="11.5" letter-spacing="5" fill="{GOLD}">CONTRIBUTION CITY</text>
<text x="38" y="112" font-family="{DISPLAY}" font-size="50" font-weight="900" fill="url(#goldText)">{TOTAL:,}</text>
<text x="40" y="138" font-family="{SANS}" font-size="15" font-weight="600" fill="{CREAM}">contributions in the last year</text>
<text x="40" y="176" font-family="{SANS}" font-size="14" fill="{GOLD}">{ACTIVE} active days</text>
<text x="40" y="198" font-family="{SANS}" font-size="14" fill="{GOLD}">Busiest day: {BUSIEST}</text>
<text x="40" y="{H - 30}" font-family="{MONO}" font-size="11" fill="{MUTED}">@{esc(LOGIN)}</text>
</svg>'''


# ================================================================== 6. chess
PIECES = {
    "p": '<rect x="24" y="80" width="52" height="11" rx="4"/><path d="M33 80 C40 66 43 58 43 48 L57 48 C57 58 60 66 67 80 Z"/>'
         '<rect x="35" y="43" width="30" height="7" rx="3.5"/><circle cx="50" cy="30" r="14"/>',
    "r": '<rect x="24" y="80" width="52" height="11" rx="4"/><path d="M33 80 L36 40 L64 40 L67 80 Z"/>'
         '<path d="M27 16 h11 v7 h7 v-7 h10 v7 h7 v-7 h11 v20 q0 4 -4 4 h-38 q-4 0 -4 -4 Z"/>',
    "b": '<rect x="24" y="80" width="52" height="11" rx="4"/><path d="M34 80 C40 68 44 60 44 52 L56 52 C56 60 60 68 66 80 Z"/>'
         '<rect x="35" y="46" width="30" height="7" rx="3.5"/><circle cx="50" cy="10" r="4.5"/>'
         '<path d="M50 13 C61 23 65 33 60 46 L40 46 C35 33 39 23 50 13 Z"/><path d="M56 24 L48 35" fill="none" stroke-width="4" stroke-linecap="round"/>',
    "n": '<rect x="24" y="80" width="52" height="11" rx="4"/>'
         '<path d="M34 80 C34 64 40 56 47 48 L38 52 L28 46 L30 38 L44 22 L46 11 L55 20 C69 26 75 46 70 80 Z"/>'
         '<circle cx="44" cy="31" r="1.6"/><path d="M58 27 C65 37 67 52 65 70" fill="none"/>',
    "q": '<rect x="24" y="80" width="52" height="11" rx="4"/><path d="M30 80 L33 66 L67 66 L70 80 Z"/>'
         '<path d="M31 66 L21 32 L34 50 L37 26 L45 48 L50 22 L55 48 L63 26 L66 50 L79 32 L69 66 Z"/>'
         '<circle cx="21" cy="29" r="4.5"/><circle cx="37" cy="22" r="4.5"/><circle cx="50" cy="18" r="4.5"/><circle cx="63" cy="22" r="4.5"/><circle cx="79" cy="29" r="4.5"/>',
    "k": '<rect x="24" y="80" width="52" height="11" rx="4"/><path d="M46 6 h8 v8 h8 v8 h-8 v14 h-8 v-14 h-8 v-8 h8 Z"/>'
         '<path d="M33 80 C35 68 28 58 28 48 C28 36 42 32 50 42 C58 32 72 36 72 48 C72 58 65 68 67 80 Z"/>',
}


def chess_board(board):
    sq, bx, by = 52, 54, 34
    W, H = bx * 2 + sq * 8, by + sq * 8 + 50
    last = board.peek() if board.move_stack else None
    out = []
    for rank in range(8):
        for file in range(8):
            x, y = bx + file * sq, by + (7 - rank) * sq
            light = (rank + file) % 2 == 1
            out.append(f'<rect x="{x}" y="{y}" width="{sq}" height="{sq}" fill="{"#d9b560" if light else "#6f4d15"}"/>')
            s = chess.square(file, rank)
            if last and s in (last.from_square, last.to_square):
                out.append(f'<rect x="{x}" y="{y}" width="{sq}" height="{sq}" fill="#fff3a6" fill-opacity="0.42"/>')
            if board.is_check() and board.king(board.turn) == s:
                out.append(f'<rect x="{x}" y="{y}" width="{sq}" height="{sq}" fill="#ff5a3c" fill-opacity="0.5"/>')
            piece = board.piece_at(s)
            if piece:
                fill, stroke = ("#fff8e2", "#2a1c05") if piece.color else ("#1d1406", "#f2c14e")
                out.append(f'<use href="#pc-{piece.symbol().lower()}" transform="translate({x + 3} {y + 2.5}) scale(0.46)" '
                           f'fill="{fill}" stroke="{stroke}" stroke-width="3" stroke-linejoin="round"/>')
    coords = "".join(f'<text x="{bx + i * sq + sq / 2}" y="{by + sq * 8 + 24}" text-anchor="middle">{c}</text>' for i, c in enumerate("abcdefgh"))
    coords += "".join(f'<text x="{bx - 22}" y="{by + (7 - i) * sq + sq / 2 + 4}" text-anchor="middle">{i + 1}</text>' for i in range(8))
    defs = "".join(f'<g id="pc-{k}">{v}</g>' for k, v in PIECES.items())
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Chess board, {"white" if board.turn else "black"} to move">
<defs>{defs}
  <linearGradient id="felt" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3a290b"/><stop offset="1" stop-color="#0d0903"/></linearGradient>
  <radialGradient id="glint" cx="85%" cy="88%" r="50%"><stop offset="0" stop-color="{GOLD}" stop-opacity="0.3"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>
</defs>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="30" fill="url(#felt)"/>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="30" fill="url(#glint)" stroke="{GOLD}" stroke-opacity="0.55" stroke-width="1.5"/>
<rect x="{bx - 34}" y="{by - 14}" width="{sq * 8 + 68}" height="{sq * 8 + 54}" rx="20" fill="none" stroke="{GOLD}" stroke-opacity="0.3"/>
<rect x="{bx - 6}" y="{by - 6}" width="{sq * 8 + 12}" height="{sq * 8 + 12}" rx="8" fill="#241806" stroke="{GOLD}" stroke-opacity="0.6"/>
{''.join(out)}
<g font-family="{MONO}" font-size="12" font-weight="700" fill="{GOLD}">{coords}</g>
</svg>'''


def load_game():
    path = root / "data" / "chess.json"
    state = {"game": 1, "moves": [], "players": [], "score": {"visitors": 0, "bot": 0, "draws": 0}, "last_result": ""}
    if path.exists():
        state.update(json.loads(path.read_text(encoding="utf-8")))
    return state


def chess_section():
    """Board image + one issue link per legal move. Visitors play White, the bot (tools/chess_game.py) answers as Black."""
    state = load_game()
    board, sans = chess.Board(), []
    for uci in state["moves"]:
        sans.append(board.san(chess.Move.from_uci(uci)))
        board.push_uci(uci)
    ply = len(state["moves"])
    board_file = f'chess-board-g{state["game"]}-p{ply}.svg'  # new name every move, so no stale cached image
    for old in assets.glob("chess-board-*.svg"):
        if old.name != board_file:
            old.unlink()
    save_static(board_file, chess_board(board))

    # One row per piece that can move: "♙ Pawn e2 →" followed by a button for each square it can go to.
    piece_name = {chess.PAWN: "♙ Pawn", chess.KNIGHT: "♘ Knight", chess.BISHOP: "♗ Bishop", chess.ROOK: "♖ Rook",
                  chess.QUEEN: "♕ Queen", chess.KING: "♔ King"}
    order = [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN, chess.KING]
    promo = {chess.QUEEN: "♕", chess.ROOK: "♖", chess.BISHOP: "♗", chess.KNIGHT: "♘"}
    by_from = {}
    for mv in board.legal_moves:
        by_from.setdefault(mv.from_square, []).append(mv)
    froms = sorted(by_from, key=lambda s: (order.index(board.piece_type_at(s)), chess.square_file(s), chess.square_rank(s)))

    def label(mv):
        san = board.san(mv)
        if board.is_castling(mv):
            text = f"{chess.square_name(mv.to_square)} castle"
        else:
            text = ("×" if board.is_capture(mv) else "") + chess.square_name(mv.to_square)
        if mv.promotion:
            text += " " + promo[mv.promotion]
        return text + (" #" if san.endswith("#") else " +" if san.endswith("+") else "")

    body = urllib.parse.quote('Just press "Create" below. The board redraws itself in about a minute.')
    cells = []
    for sq in froms:
        moves = sorted(by_from[sq], key=lambda m: (chess.square_file(m.to_square), chess.square_rank(m.to_square),
                                                   -(m.promotion or 0)))
        links = []
        for mv in moves:
            title = urllib.parse.quote(f'chess|move|{mv.uci()}|{state["game"]}.{ply}')
            links.append(f'<a href="https://github.com/{LOGIN}/{LOGIN}/issues/new?title={title}&body={body}"><kbd>{label(mv)}</kbd></a>')
        cells.append(f'<td align="right">{piece_name[board.piece_type_at(sq)]} on <b>{chess.square_name(sq)}</b> →</td>'
                     f'<td>{" ".join(links)}</td>')
    if len(cells) % 2:
        cells.append("<td></td><td></td>")
    head = '<tr><th align="right">Piece</th><th align="left">Move to</th><th align="right">Piece</th><th align="left">Move to</th></tr>'
    rows = [head] + ["<tr>" + cells[i] + cells[i + 1] + "</tr>" for i in range(0, len(cells), 2)]
    table = '<table align="center">\n  ' + "\n  ".join(rows) + "\n</table>"

    status = f"<b>Your move, White</b> · game {state['game']} · move {board.fullmove_number}"
    if ply >= 2:
        who = state["players"][-1] if state["players"] else "a visitor"
        status += f" · last: <code>{sans[-2]}</code> by @{esc(who)}, bot replied <code>{sans[-1]}</code>"
    elif state["last_result"]:
        status += f" · previous game: {esc(state['last_result'])}"
    sc = state["score"]
    score = f'Visitors {sc["visitors"]} · Bot {sc["bot"]} · Draws {sc["draws"]}'
    reset_body = urllib.parse.quote("Starts a fresh board. Only works when opened by the profile owner.")
    reset = f"https://github.com/{LOGIN}/{LOGIN}/issues/new?title={urllib.parse.quote('chess|newgame')}&body={reset_body}"
    return board_file, status, table, score, reset


# ================================================================== write everything
ART_URL = f"https://raw.githubusercontent.com/{LOGIN}/{LOGIN}/output"
save_art("hero.svg", hero())
save_art("lead.svg", lead())
save_art("galaxy.svg", galaxy())
save_art("city.svg", city())
DIVIDERS = {"cast": "THE CAST", "showing": "NOW SHOWING", "universe": "THE UNIVERSE", "city": "THE CITY",
            "boxoffice": "BOX OFFICE", "intermission": "INTERMISSION · PLAY CHESS", "credits": "END CREDITS"}
for key, text in DIVIDERS.items():
    save_static(f"div-{key}.svg", divider(text))
card_tags = []
for i, repo in enumerate(PROJECTS[:4], 1):
    fname = f"reel-{i:02d}.svg"
    save_art(fname, card(i, repo))
    card_tags.append(f'<a href="{repo["url"]}"><img src="{ART_URL}/{fname}" width="49%" alt="{esc(repo["name"])}" /></a>')
board_file, status, moves, score, reset_link = chess_section()

template = (Path(__file__).parent / "README.template.md").read_text(encoding="utf-8")
readme = (template.replace("{{LOGIN}}", LOGIN).replace("{{NAME}}", esc(NAME)).replace("{{ART}}", ART_URL)
          .replace("{{CARDS}}", "\n  ".join(card_tags)).replace("{{CHESS_BOARD}}", board_file)
          .replace("{{CHESS_STATUS}}", status).replace("{{CHESS_MOVES}}", moves).replace("{{CHESS_SCORE}}", score)
          .replace("{{CHESS_RESET}}", reset_link))
(root / "README.md").write_text(readme, encoding="utf-8", newline="\n")
print(f"ok: {TOTAL} contributions, {len(PROJECTS)} project cards, board {board_file}")
