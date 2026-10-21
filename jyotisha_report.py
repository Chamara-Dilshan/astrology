#!/usr/bin/env python3
"""jyotisha_report.py — Sinhala PDF report generator on top of jyotisha_calc.py

Report types (product scope): A1 Kendra Sara (basic natal)  [A2/A3/B/C/D modules to follow]

Usage:
  python3 jyotisha_report.py --report A1 --name "නම" --date 1999-10-28 --time 08:11 --lat 7.9403 --lon 81.0188 \
      --tz Asia/Colombo --place Polonnaruwa --out report_A1.pdf [--notes notes.json] [--time-exact yes|approx]
  notes.json (optional, astrologer's Sinhala text):
      {"summary": "...", "lagna": "...", "yogas": "...", "dasha": "...", "gochara": "...", "upcoming": "...", "remedies": "..."}

Requires: weasyprint, pymupdf (for --qa), fonts/ next to this script: NotoSansSinhala(.ttf,-Bold.ttf) v3.0+, NotoSans(.ttf,-Bold.ttf), NotoSansSymbols2.ttf, NotoSansMath.ttf — all from notofonts.github.io; jyotisha_calc.py in the same dir.
All calculations come from jyotisha_calc.py (Lahiri, whole-sign, mean nodes, Swiss Ephemeris).
"""
import argparse
import collections
import html
import json
import os
import re
import struct
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BRAND = "Jyothisha Insight"
BRAND_SI = "ජ්‍යොතිෂ ඉන්සයිට්"
BRAND_TAGLINE = "පාරම්පරික ජ්‍යොතිෂය · නවීන නිරවද්‍යතාව"
BRAND_CONTACT = ""   # e.g. "facebook.com/jyothishainsight · 07X XXX XXXX"

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jyotisha_calc as jc  # noqa: E402

# ---------------------------------------------------------------- Sinhala vocabulary
SIGN_SI = ["මේෂ", "වෘෂභ", "මිථුන", "කටක", "සිංහ", "කන්‍යා", "තුලා", "වෘශ්චික", "ධනු", "මකර", "කුම්භ", "මීන"]
PLANET_SI = {"Su": "රවි", "Mo": "චන්ද්‍ර", "Ma": "කුජ", "Me": "බුධ", "Ju": "ගුරු", "Ve": "ශුක්‍ර", "Sa": "ශනි", "Ra": "රාහු", "Ke": "කේතු"}
NAK_SI = ["අස්විද", "බෙරණ", "කැති", "රෙහෙණ", "මුවසිරස", "අද", "පුනාවස", "පුෂ", "අස්ලිස", "මා", "පුවපල්", "උත්‍රපල්", "හත", "සිත",
          "සා", "විසා", "අනුර", "දෙට", "මුල", "පුවසල", "උත්‍රසල", "සුවණ", "දෙනට", "සියාවස", "පුවපුටුප", "උත්‍රපුටුප", "රේවතී"]
HOUSE_SI = {1: "ශරීරය, පෞරුෂය, ආත්ම විශ්වාසය", 2: "ධනය, කථනය, පවුල, ආහාර", 3: "සහෝදරයන්, ධෛර්යය, කෙටි ගමන්, සන්නිවේදනය",
            4: "මව, නිවස, වාහන, අධ්‍යාපනය, මානසික සතුට", 5: "දරුවන්, බුද්ධිය, පූර්ව පුණ්‍ය, නිර්මාණශීලීත්වය",
            6: "රෝග, ණය, සතුරන්, සේවය, තරඟ", 7: "විවාහය, සහකරු, හවුල් ව්‍යාපාර", 8: "ආයුෂ, හදිසි වෙනස්කම්, ගුප්ත විද්‍යා, උරුම",
            9: "පියා, ධර්මය, වාසනාව, උසස් අධ්‍යාපනය, දුර ගමන්", 10: "රැකියාව, කර්මය, කීර්තිය, සමාජ තත්ත්වය",
            11: "ලාභ, ආදායම, මිතුරන්, බලාපොරොත්තු", 12: "වියදම්, විදේශ, නින්ද, ඉවත්වීම, මෝක්ෂය"}
LAGNA_NATURE_SI = [
    "ක්‍රියාශීලී, ඉක්මන් තීරණ ගන්නා, නායකත්ව ගුණ ඇති; ඉවසීම වර්ධනය කරගත යුතු",
    "ස්ථාවර, ඉවසිලිවන්ත, සුඛෝපභෝගී දේ අගය කරන; වෙනස් වීමට ප්‍රතිරෝධී විය හැකි",
    "බුද්ධිමත්, කථනයට දක්ෂ, කුතුහලය ඇති; අවධානය බෙදී යාමට ප්‍රවණතාව",
    "සංවේදී, පවුලට ළැදි, ආරක්ෂාව සොයන; හැඟීම් මත තීරණ ගැනීම ගැන අවධානය",
    "ආත්ම විශ්වාසී, ගෞරවය අගය කරන, උදාර; අභිමානය තුලනය කරගත යුතු",
    "විශ්ලේෂණාත්මක, විස්තර වලට සැලකිලිමත්, සේවා මනස ඇති; අධික විවේචනශීලීත්වය",
    "සමබර, සම්බන්ධතා අගය කරන, රසිකත්වය ඇති; තීරණ ගැනීමේ පසුබෑම",
    "ගැඹුරු, තීව්‍ර, රහස්‍ය ගවේෂණ ස්වභාවය, ඉමහත් කැපවීම; අවිශ්වාසය සහ අනම්‍ය බව ගැන අවධානය",
    "දාර්ශනික, අවංක, ධර්මයට ළැදි, දුර දැක්ම ඇති; අධික නිර්භීත බව",
    "විනයගරුක, ප්‍රායෝගික, කැපවීමෙන් ඉහළට යන; සීතල ලෙස පෙනීමට ඉඩ",
    "නව්‍ය චින්තන, මානුෂීය, ස්වාධීන; හුදකලා වීමට ප්‍රවණතාව",
    "අනුකම්පාව, කලාත්මක, ආධ්‍යාත්මික ප්‍රවණතාව; ප්‍රායෝගික සීමා තබාගත යුතු",
]
PLANET_NATURE_SI = {"Su": "ආත්මය, පියා, අධිකාරිය, රජය, ආත්ම විශ්වාසය", "Mo": "මනස, මව, හැඟීම්, ජනතාව, සුවපහසුව",
                    "Ma": "ශක්තිය, ධෛර්යය, සහෝදරයන්, ඉඩම්, ඉංජිනේරු/තාක්ෂණික කටයුතු", "Me": "බුද්ධිය, කථනය, ව්‍යාපාර, අධ්‍යාපනය, ලේඛන",
                    "Ju": "ප්‍රඥාව, ගුරුවරයා, දරුවන්, ධනය, ධර්මය, වාසනාව", "Ve": "ප්‍රේමය, විවාහය, කලා, සුඛෝපභෝගී, වාහන",
                    "Sa": "කර්මය, ශ්‍රමය, විනය, ප්‍රමාදය, දිගු කාලීන ප්‍රතිඵල", "Ra": "අභිලාශ, විදේශ, තාක්ෂණය, අනපේක්ෂිත, මායා",
                    "Ke": "ඉවත්වීම, ආධ්‍යාත්මිකත්වය, පර්යේෂණ, අතීත කර්ම"}
SATURN_FROM_MOON_SI = {1: "සඩේ සති මධ්‍ය අවධිය: වගකීම් බර, සෞඛ්‍යය සහ මානසික සමබරතාවය ගැන අවධානය",
                       2: "සඩේ සති අවසන් අවධිය: ධන කටයුතු, පවුල් වගකීම්; ක්‍රමයෙන් සැහැල්ලු වීම", 3: "හිතකර — ධෛර්යය, ශ්‍රමයට ප්‍රතිඵල",
                       4: "අර්ධාෂ්ටම ශනි (ධයියා): නිවස/මව/මානසික සතුට ගැන අවධානය", 5: "දරුවන්/අධ්‍යාපනය සම්බන්ධ ප්‍රමාද; ඉවසීම",
                       6: "හිතකර — සතුරන්/ණය/රෝග ජය ගැනීමට ශක්තිය", 7: "විවාහ/හවුල් සම්බන්ධතා වල පරිණතභාවය අවශ්‍ය",
                       8: "අෂ්ටම ශනි (ධයියා): හදිසි බාධක, සෞඛ්‍යය, වියදම් — ප්‍රවේශම්", 9: "වාසනාව/පියා/දුර ගමන් වල ප්‍රමාද; ධර්මයට නැඹුරුව",
                       10: "රැකියාවේ බර වගකීම්, ශ්‍රමයෙන් තත්ත්වය ගොඩනැගීම", 11: "හිතකර — ශ්‍රමයට ලාභ, ස්ථාවර ආදායම්",
                       12: "සඩේ සති ආරම්භය: වියදම්, නින්ද/විවේකය, විදේශ සම්බන්ධ වෙනස්කම්"}
JUPITER_FROM_MOON_SI = {1: "මිශ්‍ර — ආත්ම වර්ධනය, ඒත් අධික විශ්වාසය", 2: "හිතකර — ධනය, පවුල් සතුට, කථනය",
                        3: "අඩු හිතකර — වෙහෙස, සහෝදර කටයුතු", 4: "අඩු හිතකර — නිවස/මව සම්බන්ධ වෙනස්",
                        5: "හිතකර — දරුවන්, අධ්‍යාපනය, බුද්ධිය", 6: "අඩු හිතකර — සතුරන්, සෞඛ්‍යය ගැන අවධානය",
                        7: "හිතකර — විවාහය, සම්බන්ධතා, ගමන්", 8: "අඩු හිතකර — වියදම්, බාධක", 9: "හිතකර — වාසනාව, ධර්මය, උසස් අධ්‍යාපනය",
                        10: "මිශ්‍ර — රැකියා වෙනස්කම්, ප්‍රයත්නය", 11: "හිතකර — ලාභ, මිතුරන්, බලාපොරොත්තු ඉටුවීම", 12: "අඩු හිතකර — වියදම්, විදේශ ගමන්"}
DIGNITY_SI = [("Uchcha", "උච්ච"), ("Neecha", "නීච"), ("Moolatrikona", "මූලත්‍රිකෝණ"), ("Swakshetra", "ස්වක්ෂේත්‍ර"), ("Own", "ස්වක්ෂේත්‍ර"),
              ("exalted", "උච්ච"), ("debilitated", "නීච"), ("friend", "මිත්‍ර ක්ෂේත්‍ර"), ("enemy", "සතුරු ක්ෂේත්‍ර"), ("neutral", "සම ක්ෂේත්‍ර")]
YOGA_SI = {"Gaja-Kesari": "ගජකේසරී යෝගය — කීර්තිය, බුද්ධිය, ගුරු–චන්ද්‍ර සම්බන්ධය",
           "Mangal dosha": "කුජ දෝෂ ඇඟවීම — විවාහ ගැලපීමේදී cancellations පරීක්ෂා කළ යුතුයි",
           "Kemadruma": "කේමද්‍රුම යෝගය — චන්ද්‍රට සහාය ග්‍රහ නැති බව; ශ්‍රමයෙන් ජය",
           "Raja": "රාජ යෝගය — කේන්ද්‍ර–ත්‍රිකෝණ අධිපති සම්බන්ධය", "Dhana": "ධන යෝගය", "Budha-Aditya": "බුධාදිත්‍ය යෝගය — බුද්ධිය, දක්ෂතාව",
           "Chandra-Mangala": "චන්ද්‍ර–මංගල යෝගය — ලෞකික සාර්ථකත්වය", "Kala Sarpa": "කාල සර්ප යෝග ඇඟවීම — රාහු–කේතු අක්ෂය",
           "Neecha Bhanga": "නීච භංග රාජ යෝගය", "Vipareeta": "විපරීත රාජ යෝගය — බාධක වලින්ම ජය"}
WEEKDAY_SI = ["සඳුදා", "අඟහරුවාදා", "බදාදා", "බ්‍රහස්පතින්දා", "සිකුරාදා", "සෙනසුරාදා", "ඉරිදා"]


def si_dignity(d):
    if not d:
        return "—"
    out = []
    for en, si in DIGNITY_SI:
        if en.lower() in d.lower() and si not in out:
            out.append(si)
    if "NB:" in d:
        out.append("(නීච භංග)")
    return " ".join(out) if out else "—"


def dms(x):
    d = int(x)
    m = int((x - d) * 60)
    return f"{d:02d}°{m:02d}′"


def fmt_date(iso, tz):
    try:
        return datetime.fromisoformat(iso).astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d")
    except Exception:
        return iso[:10]


# ---------------------------------------------------------------- Sinhala South Indian chart (HTML grid — SVG <text> gets no Sinhala shaping in WeasyPrint)
CHART_CSS = """
.sic { position: relative; border: 2px solid #3b2f2f; background: #fffdf7; box-sizing: border-box; }
.sic .c { position: absolute; text-align: left; width: 25%; height: 25%; border: 1px solid #3b2f2f; box-sizing: border-box; padding: 2px 4px; overflow: hidden; }
.sic .c .sn { font-size: 7.5pt; color: #8a7f7f; line-height: 1.1; }
.sic .c .pl { font-size: 9.2pt; line-height: 1.25; color: #1c1c1c; }
.sic .c .pl b { color: #8b1a1a; }
.sic .mid { position: absolute; left: 25%; top: 25%; width: 50%; height: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
.sic .mid .t { font-size: 11pt; font-weight: 700; color: #3b2f2f; }
.sic .mid .s { font-size: 7.5pt; color: #8a7f7f; margin-top: 3px; }
"""
_GRID = {11: (0, 0), 0: (1, 0), 1: (2, 0), 2: (3, 0), 10: (0, 1), 3: (3, 1), 9: (0, 2), 4: (3, 2),
         8: (0, 3), 7: (1, 3), 6: (2, 3), 5: (3, 3)}


def south_indian_html_si(sign_labels, title, size_mm=120):
    """sign_labels: {sign_idx: [Sinhala labels]} — South Indian fixed layout as an HTML grid (proper text shaping)."""
    cells = []
    for si, (cx, cy) in _GRID.items():
        labs = sign_labels.get(si, [])
        pl = "<br>".join(f"<b>{html.escape(l)}</b>" if l.startswith("ලග්න") else html.escape(l) for l in labs[:6])
        cells.append(f'<div class="c" style="left:{cx * 25}%;top:{cy * 25}%"><div class="sn">{SIGN_SI[si]}</div><div class="pl">{pl}</div></div>')
    mid = f'<div class="mid"><div class="t">{html.escape(title)}</div><div class="s">දකුණු ඉන්දීය ක්‍රමය · ලාහිරි අයනාංශය</div></div>'
    return f'<div class="sic" style="width:{size_mm}mm;height:{size_mm}mm">' + "".join(cells) + mid + "</div>"


# ---------------------------------------------------------------- compute
def run_calc(a, dasha_from, dasha_to, workdir, extra=()):
    jpath = os.path.join(workdir, "calc.json")
    cmd = [sys.executable, os.path.join(HERE, "jyotisha_calc.py"), "--name", a.name, "--date", a.date, "--time", a.time,
           "--lat", str(a.lat), "--lon", str(a.lon), "--tz", a.tz, "--place", a.place or "", "--vargas", "D9,D10",
           "--dasha-depth", "3", "--dasha-from", str(dasha_from), "--dasha-to", str(dasha_to), "--json", jpath] + list(extra)
    if getattr(a, "report", "") == "A3":
        cmd[cmd.index("--vargas") + 1] = "D2,D4,D7,D9,D10,D12,D24,D60"
    elif getattr(a, "report", "").startswith("B"):
        need = B_SPECS[a.report]["varga"]
        cmd[cmd.index("--vargas") + 1] = f"D9,D10,{need}" if need not in ("D9", "D10") else "D9,D10"
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=CHILD_ENV)
    if r.returncode != 0:
        sys.exit("jyotisha_calc.py failed:\n" + r.stderr[-2000:])
    with open(jpath, encoding="utf-8") as f:
        d = json.load(f)
    # matter analysis lines (printed by the engine, not in JSON)
    if "--matter" in cmd:
        keep, lines = False, []
        for ln in r.stdout.split("\n"):
            if "MATTER ANALYSIS" in ln:
                keep = True
                continue
            if keep:
                if not ln.strip() or ln[:1] not in " \t":
                    break
                lines.append(ln.strip())
        d["matter_lines"] = lines
    return d


def transit_snapshot(when_utc, natal, lat, lon):
    jd, _ = jc.to_jd_ut(when_utc.replace(tzinfo=None), "UTC")
    pos, _ = jc.compute_positions(jd)
    ms = natal["planets"]["Mo"]["sign_idx"]
    ls = natal["lagna"]["sign_idx"]
    out = {}
    for c in ["Sa", "Ju", "Ra", "Ke"]:
        s = jc.sign_of(pos[c]["lon"])
        out[c] = {"sign": s, "from_moon": jc.house_from(ms, s), "from_lagna": jc.house_from(ls, s), "retro": pos[c]["retro"]}
    hm = out["Sa"]["from_moon"]
    out["sade_sati"] = "සඩේ සති" if hm in (12, 1, 2) else ("ධයියා (අර්ධාෂ්ටම)" if hm == 4 else "ධයියා (අෂ්ටම)" if hm == 8 else "නැත")
    return out


def sign_changes(start_utc, years, planets=("Sa", "Ju", "Ra"), min_stay_days=150):
    """Sign ingresses of slow planets over `years`. Retrograde loops shorter than min_stay_days are absorbed;
    each settled ingress carries the date of the FIRST entry into that sign (first_entry) and the settled date."""
    jd0, _ = jc.to_jd_ut(start_utc.replace(tzinfo=None), "UTC")
    out = []
    ndays = int(years * 365.25) + 400
    for p in planets:
        # raw ingress list
        raw = []
        prev = jc.sign_of(jc.compute_positions(jd0)[0][p]["lon"])
        for d in range(1, ndays, 5):
            sgn = jc.sign_of(jc.compute_positions(jd0 + d)[0][p]["lon"])
            if sgn != prev:
                lo, hi = jd0 + d - 5, jd0 + d
                for _ in range(18):
                    mid = (lo + hi) / 2
                    if jc.sign_of(jc.compute_positions(mid)[0][p]["lon"]) == prev:
                        lo = mid
                    else:
                        hi = mid
                raw.append((hi, prev, sgn))
                prev = sgn
        # runs -> drop short runs
        runs = []  # (start_jd, sign)
        cur_sign = jc.sign_of(jc.compute_positions(jd0)[0][p]["lon"])
        runs.append([jd0, cur_sign])
        for t, a, b in raw:
            runs.append([t, b])
        runs.append([jd0 + ndays, None])
        settled = [runs[0]]
        for i in range(1, len(runs) - 1):
            stay = runs[i + 1][0] - runs[i][0]
            if stay >= min_stay_days and runs[i][1] != settled[-1][1]:
                settled.append(runs[i])
        for t, sgn in settled[1:]:
            if t > jd0 + years * 365.25:
                continue
            first = min([r[0] for r in raw if r[2] == sgn and r[0] <= t and t - r[0] < 400] + [t])
            out.append((jc.jd_to_datetime(first), p, sgn, jc.jd_to_datetime(t)))
    return sorted(out)


# ---------------------------------------------------------------- notes / chart consistency check
_HOUSE_RE = re.compile(r"(\d{1,2})\s*(?:වන|වැනි|වැන්න|වැන්නේ|වැන්නට)")
# a claim is skipped when the planet word is possessive/ablative (ගුරුගේ රාශිය = "Jupiter's sign")
_POSS = ("ගේ", "ගෙන්", "ගෙ", "ට ", "ටත්")
# ... or when the sentence is clearly about transits / relative counting, not the natal position
_TRANSIT_WORDS = ("ගෝචර", "සංචාර", "රාශියෙන්", "රාශියට", "යාම", "පැමිණ", "මාරු", "ගෙන්", "ලග්නයෙන්", "ගොස්",
                  # lordship / dignity — "ගුරු 12 වැනි අධිපති" is not a placement claim
                  "අධිපති", "උච්ච", "නීච", "මූලත්‍රිකෝණ", "කාරක",
                  # dasha & period sentences name rasis and houses that are not natal positions
                  "දශා", "අන්තර්", "ප්‍රත්‍යන්තර", "නාරායණ", "විම්ශෝත්තරී", "මුද්දා", "වර්ෂ", "මුන්ථා",
                  # explicit "now / moving / until" framing
                  "දැනට", "දැන්", "ගමන් කර", "වක්‍රව", "දක්වා", "සිට ")
# words that, right after a rasi name, mark it as a lordship/dignity/transit mention
_SIGN_CTX = ("අධිපති", "උච්ච", "නීච", "ලග්න", "යට", "යෙන්", "දශා", "ගෝචර", "මාරු")


def check_notes(notes, d):
    """Warn when a natal planet/sign/house claim in the astrologer's notes contradicts the computed chart.
    Transit sentences and possessive forms are ignored; this is a helper, not a censor."""
    P, warn = d["planets"], []
    si2idx = {SIGN_SI[i]: i for i in range(12)}
    others = sorted(PLANET_SI.values(), key=lambda x: -len(x))
    for key, text in (notes or {}).items():
        if not isinstance(text, str):
            continue
        for code, psi in PLANET_SI.items():
            # lookahead: a graha named again inside a previous window must still be checked
            for m in re.finditer(re.escape(psi) + r"(?=(.{0,55}))", text, re.S):
                tail = re.split(r"[.;\n]", m.group(1))[0]   # one sentence only
                if tail.startswith(_POSS):
                    continue
                # a claim ends where the next graha is named — otherwise a neighbour's
                # sign/house leaks into this graha's window (the old false-positive source)
                cut = min([tail.find(o) for o in others if o != psi and tail.find(o) >= 0] or [len(tail)])
                tail = tail[:cut]
                seg = psi + tail
                lead = text[max(0, m.start() - 24):m.start()]   # "ගෝචර ගුරු" — the cue sits before the graha
                lead = re.split(r"[.;\n]", lead)[-1]            # ...but only within the same sentence
                if any(w in seg or w in lead for w in _TRANSIT_WORDS):
                    continue
                for ssi, si in si2idx.items():
                    j = seg.find(ssi)
                    if j < 0 or P[code]["sign_idx"] == si:
                        continue
                    # "මකරයේ උච්ච", "කුම්භ අධිපති", "මේෂයට" = lordship/dignity/transit, not a natal claim
                    if any(w in seg[j + len(ssi): j + len(ssi) + 16] for w in _SIGN_CTX):
                        continue
                    warn.append(f'[{key}] "{psi} … {ssi}" — ගණනයේ {psi} {SIGN_SI[P[code]["sign_idx"]]} රාශියේ')
                hm = _HOUSE_RE.search(seg)
                if hm and 1 <= int(hm.group(1)) <= 12 and int(hm.group(1)) != P[code]["house"]:
                    warn.append(f'[{key}] "{psi} … {hm.group(1)} වැන්නේ" — ගණනයේ {psi} {P[code]["house"]} වැන්නේ')
    return sorted(set(warn))


# ---------------------------------------------------------------- HTML building
CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm;
  @bottom-left { content: "BRANDNAME"; font-family: "Noto Sans"; font-size: 8pt; color: #a08c6a; letter-spacing: .5px; }
  @bottom-right { content: "පිටුව " counter(page) " / " counter(pages); font-family: "Noto Sans Sinhala"; font-size: 8.5pt; color: #7a6f6f; }
}
@font-face { font-family: "Noto Sans Sinhala"; src: url("FONTDIR/NotoSansSinhala.ttf"); }
@font-face { font-family: "Noto Sans Sinhala"; src: url("FONTDIR/NotoSansSinhala-Bold.ttf"); font-weight: 700; }
@font-face { font-family: "Noto Sans"; src: url("FONTDIR/NotoSans.ttf"); }
@font-face { font-family: "Noto Sans"; src: url("FONTDIR/NotoSans-Bold.ttf"); font-weight: 700; }
@font-face { font-family: "Noto Sans Symbols 2"; src: url("FONTDIR/NotoSansSymbols2.ttf"); }
@font-face { font-family: "Noto Sans Math"; src: url("FONTDIR/NotoSansMath.ttf"); }
body { font-family: "Noto Sans Sinhala", "Noto Sans", "Noto Sans Symbols 2", "Noto Sans Math", sans-serif; font-size: 10.5pt; color: #1e1a1a; line-height: 1.55; }
h1 { font-size: 22pt; color: #6b1010; margin: 0 0 4pt 0; font-weight: 700; }
h2 { font-size: 14pt; color: #6b1010; border-bottom: 1.5px solid #c9a24d; padding-bottom: 3pt; margin: 18pt 0 8pt 0; page-break-after: avoid; }
h3 { font-size: 11.5pt; color: #3b2f2f; margin: 12pt 0 4pt 0; page-break-after: avoid; }
.cover { text-align: center; padding-top: 14mm; page-break-inside: avoid; }
.cover h1 { margin: 0; }
.cover .sub { font-size: 12.5pt; color: #3b2f2f; margin-bottom: 0; }
.cover .name { margin: 12pt 0 2pt 0; }
.cover .name { font-size: 18pt; font-weight: 700; margin: 14pt 0; }
.box { border: 1px solid #d9cfa8; background: #fbf7ea; padding: 8pt 10pt; border-radius: 4pt; margin: 8pt 0; }
.note { border-left: 4px solid #c9a24d; background: #fbf7ea; padding: 6pt 10pt; margin: 8pt 0; font-size: 10pt; }
.note .lbl { font-weight: 700; color: #6b1010; font-size: 9.5pt; }
.muted { color: #7a6f6f; font-size: 9pt; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt 0; font-size: 9.6pt; }
thead { display: table-header-group; }
tr { page-break-inside: avoid; }
.note, .box { page-break-inside: avoid; }
h2, h3 { page-break-after: avoid; }
th { background: #6b1010; color: #fff; padding: 4pt 5pt; text-align: left; font-weight: 600; }
td { padding: 3.5pt 5pt; border-bottom: 1px solid #e4dccb; vertical-align: top; }
tr:nth-child(even) td { background: #faf6ee; }
.cur td { background: #f3e6c2 !important; font-weight: 600; }
.two { display: flex; gap: 14pt; }
.two > div { flex: 1; }
.chart { text-align: center; margin: 6pt 0; }
.small { font-size: 9pt; }
.pb { page-break-before: always; }
/* section heads flow instead of forcing a new page; the block after them stays whole */
.sec { margin-top: 20pt; }
.vblock { page-break-inside: avoid; }
ul { margin: 4pt 0 6pt 16pt; padding: 0; }
li { margin: 2pt 0; }
.disc { font-size: 8.8pt; color: #4a4040; }
.brandmark { font-family: "Noto Sans", sans-serif; font-size: 15pt; letter-spacing: 2.5px; color: #6b1010; font-weight: 700; text-transform: uppercase; }
.brandline { width: 46mm; height: 2px; background: #c9a24d; margin: 7pt auto 5pt auto; }
.brandtag { font-size: 9.5pt; color: #8a7f7f; letter-spacing: .5px; }
.brandfoot { text-align: center; margin-top: 14pt; padding-top: 8pt; border-top: 1px solid #e4dccb; }
"""


def esc(x):
    return html.escape(str(x))


def note_block(notes, key, label="ජ්‍යොතිෂවේදියාගේ සටහන"):
    t = (notes or {}).get(key)
    if not t:
        return ""
    paras = "".join(f"<p>{esc(p)}</p>" for p in str(t).split("\n\n") if p.strip())
    return f'<div class="note"><div class="lbl">{label}</div>{paras}</div>'


def build_a1(d, a, tr, changes, notes, now_local):
    P = d["planets"]
    ls = d["lagna"]["sign_idx"]
    tz = a.tz
    lord = jc.SIGN_LORD[ls]
    lord_house = P[lord]["house"]
    moon = P["Mo"]
    approx = a.time_exact != "yes"
    # --- chart labels
    labels = {ls: ["ලග්න"]}
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        lab = PLANET_SI[c] + (" (ව)" if P[c]["retro"] and c not in ("Ra", "Ke") else "")
        labels.setdefault(P[c]["sign_idx"], []).append(lab)
    svg_d1 = south_indian_html_si(labels, "D1 · රාශි චක්‍රය", 116)
    d9 = d["vargas"].get("D9", {})
    lab9 = {}
    if d9:
        inv = {v: k for k, v in enumerate(jc.SIGNS)}
        lab9 = {inv[d9["La"]]: ["ලග්න"]}
        for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
            lab9.setdefault(inv[d9[c]], []).append(PLANET_SI[c])
    svg_d9 = south_indian_html_si(lab9, "D9 · නවාංශකය", 90) if lab9 else ""

    # --- dasha
    vim = d["vimshottari"]
    now_utc = now_local.astimezone(timezone.utc)
    def cur(lst):
        for x in lst:
            if datetime.fromisoformat(x["start"]) <= now_utc < datetime.fromisoformat(x["end"]):
                return x
        return None
    md = cur(vim["mahadashas"])
    ad = cur(md["sub"]) if md and md.get("sub") else None
    pd_ = cur(ad["sub"]) if ad and ad.get("sub") else None
    horizon = now_utc + timedelta(days=int(3 * 365.25))
    upcoming = []
    for m in vim["mahadashas"]:
        for s in m.get("sub", []):
            st, en = datetime.fromisoformat(s["start"]), datetime.fromisoformat(s["end"])
            if en > now_utc and st < horizon:
                upcoming.append((m["lord"], s["lord"], st, en, s.get("sub", [])))

    # --- text pieces
    lagna_txt = (f"ඔබේ ලග්නය <b>{SIGN_SI[ls]}</b> ({dms(d['lagna']['deg_in_sign'])}) — {LAGNA_NATURE_SI[ls]}. "
                 f"ලග්නාධිපති <b>{PLANET_SI[lord]}</b> {SIGN_SI[P[lord]['sign_idx']]} රාශියේ, <b>{lord_house} වැන්නේ</b> ({HOUSE_SI[lord_house]}) සිටීම "
                 f"ජීවිතයේ එම ක්ෂේත්‍රය කේන්ද්‍රීය වන ප්‍රවණතාවක් පෙන්වයි"
                 + (f"; තත්ත්වය: {si_dignity(P[lord]['dignity'])}" if si_dignity(P[lord]['dignity']) != "—" else "") + ".")
    moon_txt = (f"චන්ද්‍ර <b>{SIGN_SI[moon['sign_idx']]}</b> රාශියේ, <b>{NAK_SI[jc.NAKSHATRAS.index(moon['nakshatra'])]}</b> නැකතේ {moon['pada']} වන පාදයේ, "
                f"{moon['house']} වැන්නේ ({HOUSE_SI[moon['house']]}). මනසේ ස්වභාවය සහ මානසික සුවය මේ ස්ථානයෙන් කියවේ"
                + (f"; {si_dignity(moon['dignity'])}" if si_dignity(moon['dignity']) != "—" else "") + ".")

    # yogas
    yl = []
    for y in d.get("yoga_indications", []):
        key = next((k for k in YOGA_SI if k.lower() in y.lower()), None)
        yl.append(f"<li><b>{esc(YOGA_SI[key].split(' — ')[0]) if key else esc(y)}</b>" + (f" — {esc(YOGA_SI[key].split(' — ', 1)[1])}" if key and ' — ' in YOGA_SI[key] else "") +
                  f' <span class="muted">({esc(y)})</span></li>')
    vt = d.get("vargottama", [])
    if vt:
        yl.append(f"<li><b>වර්ගෝත්තම</b>: {esc(', '.join(PLANET_SI.get(v, v) if v in PLANET_SI else v for v in vt))} — D1 සහ D9 දෙකේම එකම රාශියේ; ශක්තිමත්</li>")
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]:
        dg = si_dignity(P[c]["dignity"])
        if "උච්ච" in dg or "නීච" in dg:
            yl.append(f"<li>{PLANET_SI[c]} {dg} ({SIGN_SI[P[c]['sign_idx']]}, {P[c]['house']} වැන්න) — {PLANET_NATURE_SI[c]} සම්බන්ධ කාරණා {'ශක්තිමත්' if 'උච්ච' in dg else 'අභියෝගාත්මක, ඒත් නීච භංග තිබේද බලන්න'}</li>")
    if not yl:
        yl.append("<li>ප්‍රධාන යෝග/දෝෂ ඇඟවීම් නැත (මූලික පරීක්ෂාව)</li>")

    def dasha_row(m, s=None, p=None):
        node = p or s or m
        return f"<tr><td>{PLANET_SI[m['lord']]}</td><td>{PLANET_SI[s['lord']] if s else '—'}</td><td>{PLANET_SI[p['lord']] if p else '—'}</td><td>{fmt_date(node['start'], tz)}</td><td>{fmt_date(node['end'], tz)}</td></tr>"

    md_txt = ""
    if md:
        L = md["lord"]
        md_txt = (f"දැනට ක්‍රියාත්මක මහා දශාව <b>{PLANET_SI[L]}</b> ({fmt_date(md['start'], tz)} – {fmt_date(md['end'], tz)}). "
                  f"{PLANET_SI[L]} — {PLANET_NATURE_SI[L]}; ජන්ම කේන්දරයේ {SIGN_SI[P[L]['sign_idx']]} රාශියේ {P[L]['house']} වැන්නේ ({HOUSE_SI[P[L]['house']]})"
                  + (f", {si_dignity(P[L]['dignity'])}" if si_dignity(P[L]['dignity']) != "—" else "")
                  + ". මේ දශාව පුරා එම භාවයේ කාරණා ප්‍රමුඛ වන ප්‍රවණතාවක් ඇත.")
        if ad:
            A = ad["lord"]
            md_txt += (f" වත්මන් අන්තර් දශාව <b>{PLANET_SI[A]}</b> ({fmt_date(ad['start'], tz)} – {fmt_date(ad['end'], tz)}): {PLANET_SI[A]} {P[A]['house']} වැන්නේ — "
                       f"{HOUSE_SI[P[A]['house']]} සම්බන්ධ සිදුවීම් මතුවීමට ඉඩ.")

    up_rows = []
    for m, s, st, en, subs in upcoming:
        up_rows.append(f"<tr{' class=cur' if st <= now_utc < en else ''}><td>{PLANET_SI[m]} / {PLANET_SI[s]}</td><td>{st.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</td>"
                       f"<td>{en.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</td><td>{PLANET_SI[s]} {P[s]['house']} වැන්නේ ({SIGN_SI[P[s]['sign_idx']]}) — {HOUSE_SI[P[s]['house']].split(',')[0]}, {HOUSE_SI[P[s]['house']].split(',')[1].strip() if ',' in HOUSE_SI[P[s]['house']] else ''}</td></tr>")

    # transits
    sa, ju, ra = tr["Sa"], tr["Ju"], tr["Ra"]
    goch = [
        f"<li><b>ශනි</b> {SIGN_SI[sa['sign']]} රාශියේ{' (වක්‍ර)' if sa['retro'] else ''} — චන්ද්‍රගෙන් {sa['from_moon']} වැන්න, ලග්නයෙන් {sa['from_lagna']} වැන්න: {SATURN_FROM_MOON_SI[sa['from_moon']]}</li>",
        f"<li><b>ගුරු</b> {SIGN_SI[ju['sign']]} රාශියේ{' (වක්‍ර)' if ju['retro'] else ''} — චන්ද්‍රගෙන් {ju['from_moon']} වැන්න, ලග්නයෙන් {ju['from_lagna']} වැන්න: {JUPITER_FROM_MOON_SI[ju['from_moon']]}</li>",
        f"<li><b>රාහු–කේතු</b> {SIGN_SI[ra['sign']]}–{SIGN_SI[(ra['sign'] + 6) % 12]} අක්ෂය — ලග්නයෙන් {ra['from_lagna']}/{(ra['from_lagna'] + 5) % 12 + 1} වැනි භාව: {HOUSE_SI[ra['from_lagna']].split(',')[0]} සහ {HOUSE_SI[(ra['from_lagna'] + 5) % 12 + 1].split(',')[0]} ක්ෂේත්‍ර වල අනපේක්ෂිත වෙනස්කම්/අභිලාශ</li>",
        f"<li><b>සඩේ සති / ධයියා තත්ත්වය</b>: {tr['sade_sati']}</li>",
    ]
    ch_rows = "".join(f"<tr><td>{dt.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}{'<br><span class=muted>ස්ථිර ' + st.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d') + '</span>' if (st - dt).days > 20 else ''}</td><td>{PLANET_SI[p]}</td><td>{SIGN_SI[s]}</td>"
                      f"<td>චන්ද්‍රගෙන් {jc.house_from(moon['sign_idx'], s)}, ලග්නයෙන් {jc.house_from(ls, s)}</td>"
                      f"<td>{(SATURN_FROM_MOON_SI[jc.house_from(moon['sign_idx'], s)] if p == 'Sa' else JUPITER_FROM_MOON_SI[jc.house_from(moon['sign_idx'], s)] if p == 'Ju' else HOUSE_SI[jc.house_from(ls, s)].split(',')[0] + ' ක්ෂේත්‍රයට රාහු')}</td></tr>"
                      for dt, p, s, st in changes)

    # planet table
    prow = []
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        p = P[c]
        prow.append(f"<tr><td>{PLANET_SI[c]}</td><td>{SIGN_SI[p['sign_idx']]}</td><td>{dms(p['deg_in_sign'])}</td><td>{p['house']}</td>"
                    f"<td>{NAK_SI[jc.NAKSHATRAS.index(p['nakshatra'])]} {p['pada']}</td>"
                    f"<td>{'වක්‍ර ' if p['retro'] and c not in ('Ra', 'Ke') else ''}{'අස්තංගත ' if p.get('combust') else ''}{si_dignity(p['dignity']) if si_dignity(p['dignity']) != '—' else ''}</td></tr>")

    kk = d["chara_karakas"]
    ar = d["arudhas"]
    inv = {v: k for k, v in enumerate(jc.SIGNS)}

    summary_auto = (f"{SIGN_SI[ls]} ලග්නය; ලග්නාධිපති {PLANET_SI[lord]} {lord_house} වැන්නේ. චන්ද්‍ර {SIGN_SI[moon['sign_idx']]} ({NAK_SI[jc.NAKSHATRAS.index(moon['nakshatra'])]}). "
                    + (f"වත්මන් දශාව {PLANET_SI[md['lord']]}" + (f"/{PLANET_SI[ad['lord']]}" if ad else "") + ". " if md else "")
                    + f"ශනි ගෝචරය: {tr['sade_sati'] if tr['sade_sati'] != 'නැත' else 'සඩේ සති/ධයියා නැත'}; ගුරු චන්ද්‍රගෙන් {ju['from_moon']} වැන්නේ.")

    birth_rows = [("නම", a.name), ("උපන් දිනය", a.date), ("උපන් වේලාව", f"{a.time} ({'නිශ්චිත' if not approx else 'ආසන්න'})"),
                  ("ස්ථානය", a.place or "—"), ("අක්ෂාංශ / දේශාංශ", f"{a.lat:.4f}° N, {a.lon:.4f}° E"),
                  ("කාල කලාපය", f"{a.tz} (UTC{'+' if not str(d['birth']['utc_offset']).startswith('-') else ''}{str(d['birth']['utc_offset'])[:-3]})"),
                  ("අයනාංශය", f"ලාහිරි {dms(d['ayanamsa'])}"), ("පංචාංගය", f"{esc(pch_si(d['panchanga'])['vara'])} · {esc(pch_si(d['panchanga'])['tithi'])} තිථි · {esc(pch_si(d['panchanga'])['yoga'])} යෝග · {esc(pch_si(d['panchanga'])['karana'])} කරණ · හිරු උදාව {d['panchanga']['sunrise']}"),
                  ("වාර්තා දිනය", now_local.strftime("%Y-%m-%d"))]

    H = []
    H.append(f"""<div class="cover"><div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:20pt">ජන්ම කේන්දර වාර්තාව</h1><div class="sub">කේන්දර සාර — මූලික විග්‍රහය (A1)</div>
      <div class="name">{esc(a.name)}</div>
      <div>{esc(a.date)} · {esc(a.time)} · {esc(a.place or '')}</div>
      <div style="margin:16pt auto 0 auto; width:116mm">{svg_d1}</div>
      <p class="muted" style="margin-top:12pt; font-size:8.5pt">පරාශර සහ ජෛමිනි සම්ප්‍රදාය · ලාහිරි අයනාංශය · සම්පූර්ණ රාශි භාව ක්‍රමය · මධ්‍යම රාහු-කේතු · Swiss Ephemeris</p></div>""")
    H.append('<div class="pb"></div><h2>1. සාරාංශය</h2>')
    H.append(f'<div class="box">{esc(summary_auto)}</div>')
    H.append(note_block(notes, "summary"))
    if approx:
        H.append('<div class="note"><div class="lbl">උපන් වේලාව ගැන</div><p>උපන් වේලාව ආසන්න වශයෙන් දී ඇති නිසා මේ වාර්තාවේ D1 කේන්දරය, දශා සහ ගෝචරය ප්‍රමුඛ කර ඇත; සියුම් වර්ග (D9, D10) කේන්දර වල ලග්නය මිනිත්තු කිහිපයකින් වෙනස් විය හැක.</p></div>')
    H.append("<h2>2. උපන් දත්ත</h2><table>" + "".join(f"<tr><td style='width:34%'><b>{k}</b></td><td>{v}</td></tr>" for k, v in birth_rows) + "</table>")
    H.append('<p class="small muted">දත්ත වැරදි නම් වහාම දන්වන්න — වේලාව මිනිත්තු 10ක් වෙනස් වුවත් සමහර ප්‍රතිඵල වෙනස් විය හැක.</p>')

    H.append("<h2>3. ලග්නය සහ ග්‍රහ ස්ථාන (D1)</h2>")
    H.append(f"<p>{lagna_txt}</p><p>{moon_txt}</p>")
    H.append("<table><tr><th>ග්‍රහයා</th><th>රාශිය</th><th>අංශක</th><th>භාවය</th><th>නැකත / පාදය</th><th>තත්ත්වය</th></tr>" + "".join(prow) + "</table>")
    H.append(note_block(notes, "lagna"))
    H.append('<h3>ජෛමිනි කාරක සහ ආරූඪ (සංක්ෂිප්ත)</h3>')
    H.append("<table><tr><th>ආත්මකාරක (AK)</th><th>අමාත්‍යකාරක (AmK)</th><th>දාරාකාරක (DK)</th><th>ආරූඪ ලග්නය (AL)</th><th>උපපද (UL)</th></tr>"
             f"<tr><td>{PLANET_SI[kk['AK']['planet']]}</td><td>{PLANET_SI[kk['AmK']['planet']]}</td><td>{PLANET_SI[kk['DK']['planet']]}</td>"
             f"<td>{SIGN_SI[inv[ar['AL']]]}</td><td>{SIGN_SI[inv[ar['UL']]]}</td></tr></table>")
    H.append('<p class="small muted">AK = ආත්මයේ ගමන් මග; AL = සමාජය ඔබ දකින ආකාරය; UL = විවාහ/සහකරු සම්බන්ධ ආරූඪය. විස්තර විග්‍රහය A2/A3 වාර්තා වල.</p>')

    H.append('<div class="pb"></div><h2>4. නවාංශකය (D9) සහ යෝග</h2>')
    if svg_d9:
        H.append(f'<div class="two"><div class="chart" style="width:90mm; flex: 0 0 90mm">{svg_d9}</div><div><p class="small">D9 — විවාහය, අභ්‍යන්තර ශක්තිය සහ ග්‍රහ බලය පෙන්වන වර්ග කේන්දරය. '
                 f'D9 ලග්නය <b>{SIGN_SI[inv[d9["La"]]]}</b>.' + (' උපන් වේලාව ආසන්න නිසා D9 ලග්නය වෙනස් විය හැක.' if approx else '') + '</p></div></div>')
    H.append("<h3>ප්‍රධාන යෝග / දෝෂ සහ තත්ත්ව</h3><ul>" + "".join(yl) + "</ul>")
    H.append(note_block(notes, "yogas"))

    H.append("<h2>5. විම්ශෝත්තරී දශා</h2>")
    H.append(f"<p>{md_txt}</p>")
    H.append("<table><tr><th>මහා දශාව</th><th>අන්තර්</th><th>ප්‍රත්‍යන්තර</th><th>ආරම්භය</th><th>අවසානය</th></tr>")
    if md:
        H.append(dasha_row(md))
        if ad:
            H.append(dasha_row(md, ad))
        if pd_:
            H.append(dasha_row(md, ad, pd_))
    H.append("</table>")
    H.append("<h3>ඉදිරි වසර 3 — අන්තර් දශා</h3><table><tr><th>දශාව</th><th>ආරම්භය</th><th>අවසානය</th><th>ප්‍රවණතාව (ජන්ම කේන්දරය අනුව)</th></tr>" + "".join(up_rows) + "</table>")
    H.append("<h3>මහා දශා අනුපිළිවෙල</h3><table><tr><th>දශාව</th><th>ආරම්භය</th><th>අවසානය</th></tr>" +
             "".join(f"<tr{' class=cur' if md and m['lord'] == md['lord'] else ''}><td>{PLANET_SI[m['lord']]}</td><td>{fmt_date(m['start'], tz)}</td><td>{fmt_date(m['end'], tz)}</td></tr>" for m in vim["mahadashas"]) + "</table>")
    H.append(note_block(notes, "dasha"))

    H.append('<div class="pb"></div><h2>6. ගෝචරය (වත්මන් ග්‍රහ සංචාරය)</h2>')
    H.append(f'<p class="small muted">{now_local.strftime("%Y-%m-%d")} දිනට</p><ul>' + "".join(goch) + "</ul>")
    if ch_rows:
        H.append("<h3>ඉදිරි වසර 3 තුළ ශනි / ගුරු / රාහු රාශි මාරු</h3><table><tr><th>දිනය</th><th>ග්‍රහයා</th><th>නව රාශිය</th><th>භාවය</th><th>ප්‍රවණතාව</th></tr>" + ch_rows + "</table>")
    H.append(note_block(notes, "gochara"))

    H.append("<h2>7. ඉදිරි කාලය — සාරාංශ කවුළු</h2>")
    win = []
    for m, s, st, en, subs in upcoming:
        if en <= now_utc:
            continue
        tone = "හිතකර" if P[s]["house"] in (1, 2, 4, 5, 7, 9, 10, 11) and "නීච" not in si_dignity(P[s]["dignity"]) else "අවධානය යොමු කළ යුතු"
        win.append(f"<li><b>{max(st, now_utc).astimezone(ZoneInfo(tz)).strftime('%Y-%m')} → {en.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</b> — {PLANET_SI[m]}/{PLANET_SI[s]}: "
                   f"{HOUSE_SI[P[s]['house']].split(',')[0]} ක්ෂේත්‍රය ({tone} ප්‍රවණතාව)</li>")
    for dt, p, s, st in changes:
        win.append(f"<li><b>{dt.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</b> — {PLANET_SI[p]} {SIGN_SI[s]} රාශියට"
                   + (f" (වක්‍ර චලනයෙන් පසු ස්ථිර {st.astimezone(ZoneInfo(tz)).strftime('%Y-%m')})" if (st - dt).days > 20 else "") + ": ගෝචර වෙනස</li>")
    H.append("<ul>" + "".join(sorted(win)) + "</ul>")
    H.append('<p class="small muted">වක්‍ර චලනය නිසා ග්‍රහයෙක් රාශියකට ඇතුළු වී ආපසු ගොස් නැවත ඇතුළු වන විට පළමු ඇතුළුවීමේ දිනයත්, ස්ථිර වන දිනයත් දෙකම දක්වා ඇත.</p>')
    H.append('<p class="small">දශාව, ගෝචරය සහ වාර්ෂික චක්‍රය එකට ගැලපෙන කාල කවුළු වඩාත් වැදගත්; තනි ඇඟවීමක් මත පමණක් තීරණ නොගන්න. විස්තර timing සහ Varsha Kundali A2/C1 වාර්තා වල.</p>')
    H.append(note_block(notes, "upcoming"))
    if (notes or {}).get("remedies"):
        H.append("<h2>8. යෝජනා</h2>" + note_block(notes, "remedies", "ප්‍රතිකර්ම / ආකල්ප යෝජනා"))

    H.append('<div class="pb"></div><h2>ක්‍රමවේදය සහ වගකීම් ප්‍රකාශය</h2>')
    H.append('<div class="disc"><p><b>ක්‍රමවේදය:</b> පරාශර හෝරා ශාස්ත්‍රය සහ ජෛමිනි සම්ප්‍රදාය; P.V.R. Narasimha Rao ගේ <i>Vedic Astrology: An Integrated Approach</i> ප්‍රධාන යොමුව. '
             'ලාහිරි අයනාංශය, සම්පූර්ණ රාශි භාව ක්‍රමය, මධ්‍යම රාහු–කේතු, Swiss Ephemeris ගණනය. විම්ශෝත්තරී දශා සෞර වර්ෂ අනුව.</p>'
             '<p><b>වගකීම් ප්‍රකාශය:</b> මේ වාර්තාව ජ්‍යොතිෂ ශාස්ත්‍රය අනුව ප්‍රවණතා සහ කාල රටා ගැන ප්‍රතිබිම්බනාත්මක මගපෙන්වීමකි — ස්ථිර අනාවැකි නොවේ. '
             'මෙහි වෛද්‍ය රෝග විනිශ්චය, ආයුෂ/මරණ අනාවැකි, නීතිමය හෝ මූල්‍ය ආයෝජන උපදෙස් අන්තර්ගත නොවේ; ඒ කාරණා සඳහා සුදුසුකම් ලත් වෘත්තිකයෙකු හමුවන්න. '
             'ජීවිතයේ තීරණ ඔබේ විචාරය, උත්සාහය සහ වගකීම මතයි. උපන් වේලාවේ නිරවද්‍යතාව ප්‍රතිඵල වලට සෘජුව බලපායි.</p>'
             '<p><b>පෞද්ගලිකත්වය:</b> ඔබේ උපන් දත්ත මේ වාර්තාව සැකසීමට පමණක් භාවිත කර ඇත; තෙවන පාර්ශ්වයකට ලබා නොදේ.</p></div>')
    H.append(f'<div class="brandfoot"><div class="brandmark" style="font-size:12pt">{esc(BRAND)}</div>'
             f'<div class="brandtag" style="font-size:8.5pt">{esc(BRAND_TAGLINE)}</div>'
             + (f'<div class="muted" style="margin-top:4pt">{esc(BRAND_CONTACT)}</div>' if BRAND_CONTACT else '') + '</div>')
    return "\n".join(H)


# ================================================================ Sinhala rendering of engine strings
SIGN_EN2SI = {"Mesha": "මේෂ", "Vrishabha": "වෘෂභ", "Mithuna": "මිථුන", "Karka": "කටක", "Simha": "සිංහ", "Kanya": "කන්‍යා",
              "Tula": "තුලා", "Vrischika": "වෘශ්චික", "Dhanu": "ධනු", "Makara": "මකර", "Kumbha": "කුම්භ", "Meena": "මීන"}
PL_EN2SI = {"Surya": "රවි", "Chandra": "චන්ද්‍ර", "Chand": "චන්ද්‍ර", "Kuja": "කුජ", "Budha": "බුධ", "Guru": "ගුරු",
            "Shukra": "ශුක්‍ර", "Shukr": "ශුක්‍ර", "Shani": "ශනි", "Rahu": "රාහු", "Ketu": "කේතු"}
PHRASE_SI = [
    # ch.11 yoga conditions (the detector's English reason strings)
    ("combust, weakened", "අස්තංගත, දුර්වල"), ("combust", "අස්තංගත"), ("weakened", "දුර්වල වී ඇත"),
    ("conditions partly unmet", "කොන්දේසි අර්ධ වශයෙන් පමණක් සපුරයි"),
    ("no benefic association", "ශුභ ග්‍රහ සම්බන්ධයක් නැත"), ("benefic association", "ශුභ ග්‍රහ සම්බන්ධය"),
    ("mutual graha drishti", "අන්‍යෝන්‍ය ග්‍රහ දෘෂ්ටිය"), ("graha drishti", "ග්‍රහ දෘෂ්ටිය"),
    ("dusthana lords", "දුස්ථානාධිපතීන්"), ("dusthanas", "දුස්ථානවල"), ("dusthana", "දුස්ථාන"),
    ("kendra lord", "කේන්ද්‍රාධිපති"), ("trikona lord", "ත්‍රිකෝණාධිපති"),
    ("apoklima (much)", "අපොක්ලිම ස්ථානවල (බොහෝ දුරට)"), ("apoklima", "අපොක්ලිම"), ("panapara", "පණපර"),
    ("wealth/intelligence guideline", "ධනය/බුද්ධිය පිළිබඳ මාර්ගෝපදේශය"),
    ("all grahas in", "සියලු ග්‍රහයෝ"), ("houses from house", "භාව ඇතුළත, ආරම්භය භාවය"),
    ("benefic in Lagna or", "ලග්නයේ ශුභ ග්‍රහයෙක් හෝ"), ("subha-kartari", "ශුභ කර්තරී"),
    ("in/with", "තුළ / සමඟ"), ("5L-9L", "5ප-9ප"), ("apart", "දුරින්"), ("weak", "දුර්වල"),
    ("association", "සම්බන්ධය"),
    # plurals before singulars, or "kendras" leaves a stray "s"
    ("kendras", "කේන්ද්‍රස්ථාන"), ("trikonas", "ත්‍රිකෝණස්ථාන"), ("apoklimas", "අපොක්ලිම ස්ථාන"),
    ("panapharas", "පණපර ස්ථාන"), ("panaphara", "පණපර"), ("lords", "අධිපතීන්"),
    ("th lords", " වන භාවාධිපතීන්"), ("st lords", " වන භාවාධිපතීන්"),
    ("nd lords", " වන භාවාධිපතීන්"), ("rd lords", " වන භාවාධිපතීන්"), ("also", "ද"),
    ("in a kendra", "කේන්ද්‍රස්ථානයක"), ("kendra", "කේන්ද්‍ර"), ("trikona", "ත්‍රිකෝණ"),
    ("deeply exalted", "ගැඹුරින් උච්ච"), ("own/exalted", "ස්වක්ෂේත්‍ර/උච්ච"),
    ("exalted", "උච්ච"), ("debilitated", "නීච"), ("mutual", "අන්‍යෝන්‍ය"),
    ("strong", "ශක්තිමත්"), ("together", "එකට"), ("benefic", "ශුභ ග්‍රහ"), ("malefic", "පාප ග්‍රහ"),
    (" & ", " සහ "), (" or ", " හෝ "),
    # Tajaka aspects / yogas
    ("conjunction", "සංයෝගය"), ("opposition", "ප්‍රතියෝගය"), ("trine", "ත්‍රිකෝණ දෘෂ්ටිය"), ("square", "චතුරස්‍ර දෘෂ්ටිය"),
    ("sextile", "ෂඩාෂ්ටක දෘෂ්ටිය"), ("vartamana", "වර්තමාන"), ("poorna", "පූර්ණ"), ("bhavishya", "භවිෂ්‍ය"),
    ("Kamboola", "කම්බූල"), ("gap", "පරතරය"), ("Ithasala", "ඉථසාල"), ("Eesarpha", "ඊසර්ඵ"),
    # Shatpanchasika verdicts
    ("SUCCESS indicated", "සාර්ථක වීමේ ප්‍රවණතාව"), ("FAILURE indicated", "අසාර්ථක වීමේ ප්‍රවණතාව"),
    ("MIXED — success only with great effort", "මිශ්‍ර — විශාල උත්සාහයකින් පමණක් සාර්ථකත්වය"),
    ("querent gains ALL desired in full", "අපේක්ෂිත දේ සම්පූර්ණයෙන් ලැබීමේ ප්‍රවණතාව"),
    ("complete failure of the desire; caution", "අපේක්ෂාව ඉටු නොවීමේ ප්‍රවණතාව; ප්‍රවේශම්"),
    ("partial — obstacles", "අර්ධ ප්‍රතිඵල — බාධක"),
    ("gains & success", "ලාභ සහ සාර්ථකත්වය"), ("losses", "අලාභ"), ("gains and losses both", "ලාභ සහ අලාභ දෙකම"),
    ("success foretold", "සාර්ථකත්වය"), ("gain of land/position", "ඉඩම්/තනතුරු ලාභය"),
    ("wealth & honour from authorities", "අධිකාරි මගින් ධනය සහ ගෞරවය"), ("no success in the matter", "කාරණයේ සාර්ථකත්වයක් නැත"),
    ("not favourable for the matter", "කාරණයට හිතකර නැත"), ("prosperity", "සමෘද්ධිය"),
    ("success through a woman's help", "කාන්තාවකගේ සහාය මගින් සාර්ථකත්වය"),
    ("loss of the object in mind, monetary loss, fear", "අපේක්ෂිත දේ අහිමි වීම, මුදල් අලාභ, බිය"),
    ("good in all these respects", "මේ සියලු අතින් හිතකර"),
    ("SPEEDY recovery", "ඉක්මනින් නැවත ලැබීම"), ("recovery indicated", "නැවත ලැබීමේ ප්‍රවණතාව"),
    ("stolen article recovered soon", "සොරකම් කළ දේ ඉක්මනින් ලැබීම"),
    ("recovery not promised by this prashna", "මේ ප්‍රශ්න කේන්දරයෙන් නැවත ලැබීමක් පෙන්නුම් නොකරයි"),
    ("article is still in the same place; taken by a close relation / insider",
     "දේ තවම එම ස්ථානයේම; ළඟ කෙනෙකු/ඇතුළාන්තයේ කෙනෙකු විසින් ගෙන ඇත"),
    ("article has been moved away", "දේ වෙනත් තැනකට ගෙන ගොස් ඇත"),
    ("front part of the house", "ගෙදර ඉදිරි කොටසේ"), ("middle of the house", "ගෙදර මැද කොටසේ"),
    ("back of the house or beyond", "ගෙදර පිටුපස හෝ ඉන් ඔබ්බේ"),
    ("direction:", "දිශාව:"), ("article shape:", "දෙයේ හැඩය:"), ("long", "දිගු"), ("broad", "පළල්"), ("small", "කුඩා"),
    ("VICTORY to the querent", "ප්‍රශ්නකරුට ජය"), ("victory to the OPPONENT", "ප්‍රතිවාදියාට ජය"),
    ("defeat to the opponent", "ප්‍රතිවාදියාට පරාජය"), ("defeat to the querent's side", "ප්‍රශ්නකරුගේ පැත්තට පරාජය"),
    ("favours querent", "ප්‍රශ්නකරුට වාසි"), ("favours opponent", "ප්‍රතිවාදියාට වාසි"), ("balanced", "සමබර"),
    ("settlement / accommodation between the parties", "පාර්ශ්ව අතර සමථයක්"),
    ("fighting & enmity continue", "ගැටුම සහ වෛරය දිගටම"), ("peace between the parties", "පාර්ශ්ව අතර සාමය"),
    ("they will fight", "ගැටුම දිගටම"),
    ("opponent does not come forward", "ප්‍රතිවාදියා ඉදිරිපත් නොවේ"), ("opponent comes in strength and presses", "ප්‍රතිවාදියා ශක්තියෙන් ඉදිරිපත් වේ"),
    ("opponent turns back after advancing far", "ප්‍රතිවාදියා දුර ඇවිත් ආපසු හැරේ"),
    ("opponent returns after coming half-way", "ප්‍රතිවාදියා අඩක් ඇවිත් ආපසු යයි"),
    ("opponent withdraws", "ප්‍රතිවාදියා පසුබසී"), ("opponent does not come", "ප්‍රතිවාදියා නොපැමිණේ"),
    ("opponent comes well prepared", "ප්‍රතිවාදියා හොඳින් සූදානම්ව පැමිණේ"),
    ("opponent turns back part-way", "ප්‍රතිවාදියා අතරමගදී ආපසු හැරේ"),
    ("opponent retires disappointed after close approach", "ප්‍රතිවාදියා ළං වී කලකිරී ආපසු යයි"),
    ("opponent retreats in disgrace", "ප්‍රතිවාදියා අපහසුතාවෙන් පසුබසී"),
    ("opponent cannot stand; early retreat", "ප්‍රතිවාදියාට නොනැගී සිටිය නොහැක; ඉක්මන් පසුබැසීම"),
    ("hostile party will not arrive", "විරුද්ධ පාර්ශ්වය නොපැමිණේ"), ("hostile party arrives quickly", "විරුද්ධ පාර්ශ්වය ඉක්මනින් පැමිණේ"),
    ("party gone out returns immediately", "පිටව ගිය පාර්ශ්වය වහාම ආපසු එයි"),
    ("safe recovery indicated", "සුවය ලැබීමේ ප්‍රවණතාව"),
    ("recovery combination incomplete — no strong promise (astrology is not medical advice)",
     "සුවය පිළිබඳ සංයෝගය සම්පූර්ණ නැත — ශක්තිමත් ඇඟවීමක් නැත (ජ්‍යොතිෂය වෛද්‍ය උපදෙස් නොවේ)"),
    ("marriage indicated", "විවාහයේ ප්‍රවණතාව"), ("marriage will be celebrated", "විවාහය සිදුවීමේ ප්‍රවණතාව"),
    ("marriage celebrated speedily", "විවාහය ඉක්මනින් සිදුවීමේ ප්‍රවණතාව"),
    ("no promise from this stanza alone", "මේ ශ්ලෝකයෙන් පමණක් ඇඟවීමක් නැත"),
    ("query concerns:", "ප්‍රශ්නය සම්බන්ධ වන්නේ:"), ("query is about the querent himself", "ප්‍රශ්නය ප්‍රශ්නකරු ගැනමයි"),
    ("traveller", "ගමන් කරන්නා"), ("return within", "ආපසු පැමිණීම"), ("days", "දින"), ("months", "මාස"),
    ("safe return", "ආරක්ෂිතව ආපසු පැමිණීම"), ("with wealth & honour", "ධනය සහ ගෞරවය සමඟ"),
    ("plentiful rain", "බහුල වර්ෂාව"), ("early rain in the season", "කන්නයේ මුල් වර්ෂාව"), ("no rain combination", "වර්ෂා සංයෝගයක් නැත"),
    ("combination absent", "සංයෝගය නැත"), ("rain", "වර්ෂාව"),
    # matter analysis (29.2)
    ("saham at", "සහමය"), ("lord", "අධිපති"), ("Lagna lord", "ලග්නාධිපති"),
    ("matter slipping away / delayed", "කාරණය ලිස්සා යාම / ප්‍රමාද වීම"),
    ("favours fulfilment", "කාරණය ඉටුවීමට හිතකර"), ("empty", "හිස්"),
    ("Kamboola support", "කම්බූල සහාය"), ("karaka", "කාරකයා"),
    ("No ithasala among the significators — no strong Tajaka promise for this matter in this chart",
     "කාරක ග්‍රහයන් අතර ඉථසාල යෝගයක් නැත — මේ කේන්දරයෙන් මේ කාරණයට ශක්තිමත් ඇඟවීමක් නැත"),
    ("th lord", " වන භාවාධිපති"), ("st lord", " වන භාවාධිපති"), ("nd lord", " වන භාවාධිපති"), ("rd lord", " වන භාවාධිපති"),
    ("in house", "—"), ("House", "භාවය"),
    # residual English fragments in rule strings
    ("object of the query:", "ප්‍රශ්නයේ විෂය:"), ("Jeeva (living being)", "ජීව (ප්‍රාණීන්)"),
    ("Moola (vegetable/root)", "මූල (ශාක/මුල්)"), ("Dhatu (mineral/inanimate)", "ධාතු (ලෝහ/අජීවී)"),
    ("no malefics in kendras/8th", "කේන්ද්‍ර/8 වැන්නේ පාප ග්‍රහයන් නැත"),
    ("in kendras/8th", "කේන්ද්‍ර/8 වැන්නේ"), ("in kendra/trikona", "කේන්ද්‍ර/ත්‍රිකෝණයේ"),
    ("in kendras", "කේන්ද්‍රවල"), ("in 7th/10th", "7/10 වැන්නේ"), ("in 1/2/5", "1/2/5 වැන්නේ"),
    ("in 11th/12th", "11/12 වැන්නේ"), ("in 3/5/7/11", "3/5/7/11 වැන්නේ"), ("in 1/3/5/8/9", "1/3/5/8/9 වැන්නේ"),
    ("in 6/7/8 from", "6/7/8 වැන්නේ — "), ("from Lagna lord", "ලග්නාධිපතිගෙන්"),
    ("article shape: long", "දෙයේ හැඩය: දිගු"), ("article shape: broad", "දෙයේ හැඩය: පළල්"), ("article shape: small", "දෙයේ හැඩය: කුඩා"), ("from", "සිට"),
    ("(Ge/Vi/Li/Aq)", "(මිථුන/කන්‍යා/තුලා/කුම්භ)"),
    # generic
    ("benefics", "ශුභ ග්‍රහයන්"), ("benefic", "ශුභ"), ("malefics", "පාප ග්‍රහයන්"), ("malefic", "පාප"),
    ("Lagna", "ලග්නය"), ("lagna", "ලග්නය"), ("kendra/trikona", "කේන්ද්‍ර/ත්‍රිකෝණ"), ("kendras", "කේන්ද්‍ර"),
    ("house", "භාවය"), ("houses", "භාව"), ("navamsa", "නවාංශකය"), ("odd sign", "ඔජ රාශිය"), ("even sign", "යුග්ම රාශිය"),
    ("tara Parama Mitra", "තාරා පරම මිත්‍ර"), ("tara Parama", "තාරා පරම මිත්‍ර"), ("tara Mitra", "තාරා මිත්‍ර"),
    ("tara Sampat", "තාරා සම්පත්"), ("tara Kshema", "තාරා ක්ෂේම"), ("tara Sadhana", "තාරා සාධන"), ("tara Janma", "තාරා ජන්ම"),
    ("janma tara (mixed)", "ජන්ම තාරා (මිශ්‍ර)"), ("hora lord favorable w.r.t. natal", "හෝරාධිපති ජන්ම කේන්දරයට හිතකර විය යුතුයි"),
    ("should be clean", "පිරිසිදු විය යුතුයි"), ("check D-", "බලන්න D-"),
    ("Sirshodaya", "ශීර්ෂෝදය"), ("Prishtodaya", "පෘෂ්ඨෝදය"), ("Ubhayodaya", "උභයෝදය"),
    ("shadvarga lords", "ෂඩ්වර්ග අධිපතියන්"), ("benefic-owned", "ශුභ ග්‍රහයෙකුට අයත්"), ("malefic-owned", "පාප ග්‍රහයෙකුට අයත්"),
    ("drekkana", "ද්‍රේෂ්කාණය"), ("rising", "උදා වීම"), ("strongest planet", "ශක්තිමත්ම ග්‍රහයා"),
    ("East", "නැගෙනහිර"), ("West", "බටහිර"), ("North", "උතුර"), ("South", "දකුණ"),
    ("South-East", "අග්නිදිග"), ("South-West", "නිරිත දිග"), ("North-West", "වයඹ දිග"), ("North-East", "ඊසාන දිග"),
]


SAHAM_SI = {"Punya (fortune)": "පුණ්‍ය (වාසනාව)", "Vidya (education)": "විද්‍යා (අධ්‍යාපනය)", "Yasas (fame)": "යශස් (කීර්තිය)",
            "Karma (work)": "කර්ම (රැකියාව)", "Vivaha (marriage)": "විවාහ", "Putra (children)": "පුත්‍ර (දරුවන්)",
            "Artha (money)": "අර්ථ (ධනය)", "Labha (gains)": "ලාභ", "Roga (illness)": "රෝග", "Bhratri (siblings)": "භ්‍රාතෘ (සහෝදර)",
            "Rajya (position)": "රාජ්‍ය (තනතුර)", "Paradesa (foreign)": "පරදේශ (විදේශ)", "Vyapara (business)": "ව්‍යාපාර",
            "Matri (mother)": "මාතෘ (මව)", "Pitri (father)": "පිතෘ (පියා)", "Mrityu": "මෘත්‍යු", "Sastra": "ශාස්ත්‍ර"}

_WORD_SI = {"wide": "පුළුල්", "grahas": "ග්‍රහයන්", "distinct": "වෙනස්", "rasis": "රාශි",
            "upachayas": "උපචය ස්ථාන", "there": "එහි", "variant": "ප්‍රභේදය", "little": "සුළු",
            "partial": "අර්ධ", "but": "නමුත්", "occupied": "ග්‍රහයන් සිටී", "cancellation": "අවලංගු වීම",
            "per": "අනුව", "average": "සාමාන්‍ය", "opposite": "ප්‍රතිවිරුද්ධ", "all": "සියලු",
            "exaltation": "උච්ච ස්ථානය",
            "with": "සමඟ", "and": "සහ", "in": "—", "no": "නැති", "aspect": "දෘෂ්ටිය", "aspected": "දෘෂ්ටි වන",
            "planets": "ග්‍රහයන්", "planet": "ග්‍රහයා", "sign": "රාශිය", "signs": "රාශි", "day": "දිවා", "night": "රාත්‍රී",
            "empty": "හිස්", "conjunct": "සංයුක්ත", "retrograde": "වක්‍ර", "secondary": "ද්විතීයික"}


YOGA_NAME_SI = {"Dharma-Karmadhipati Raja yoga": "ධර්ම-කර්මාධිපති රාජ යෝගය",
                "Vipareeta Raja yoga": "විපරීත රාජ යෝගය", "Raja yoga": "රාජ යෝගය",
                "Chandra from Surya": "සූර්යයාගෙන් චන්ද්‍රයා", "Ardha Chandra": "අර්ධ චන්ද්‍ර",
                "Gaja-Kesari": "ගජකේසරී", "Budha-Aditya": "බුධාදිත්‍ය", "Ubhayachari": "උභයචරී",
                "Anapha": "අනඵා", "Sunapha": "සුනඵා", "Durudhara": "දුරුධරා", "Kemadruma": "කේමද්‍රැම",
                "Subha": "ශුභ", "Asubha": "අශුභ", "Nipuna": "නිපුණ",
                "Daridra yoga": "දරිද්‍ර යෝගය", "Dhana yoga": "ධන යෝගය", "association": "සම්බන්ධය"}


def si_yoga_name(s):
    """Yoga names keep their Sanskrit form; the English qualifiers around them do not."""
    out = str(s)
    for en, si in sorted(YOGA_NAME_SI.items(), key=lambda kv: -len(kv[0])):
        out = out.replace(en, si)
    out = re.sub(r"(\d{1,2})L\b", r"\1ප", out)
    for en, si in sorted(PHRASE_SI, key=lambda kv: -len(kv[0])):
        out = out.replace(en, si)
    out = re.sub(r"\b(" + "|".join(_WORD_SI) + r")\b", lambda m: _WORD_SI[m.group(1)], out)
    return re.sub(r"\s{2,}", " ", out).strip()


def si_text(s):
    """Best-effort Sinhala rendering of an engine-generated English line.
    Order matters: proper names first (so 'Chand' is not eaten by the word 'and'), then phrases, then single words."""
    out = str(s)
    for en, si in sorted(PL_EN2SI.items(), key=lambda kv: -len(kv[0])):
        out = out.replace(en, si)
    for en, si in sorted(SIGN_EN2SI.items(), key=lambda kv: -len(kv[0])):
        out = out.replace(en, si)
    for en, si in sorted(SAHAM_SI.items(), key=lambda kv: -len(kv[0])):
        out = out.replace(en, si)
    for tbl in (NAK_EN2SI, TITHI_SI):
        for en, si in sorted(tbl.items(), key=lambda kv: -len(kv[0])):
            out = re.sub(r"\b" + re.escape(en) + r"\b", si, out)
    # English puts the reference last ("Kuja in 12th from Chandra"); Sinhala puts it first.
    # Must run before PHRASE_SI, which turns "from" into "සිට".
    _W = r"[^\s;,.()\[\]—]+"   # a word, ZWJ included (Sinhala needs it), punctuation excluded
    out = re.sub(rf"({_W}) in (\d{{1,2}})(?:st|nd|rd|th) from ({_W})", r"\3ගෙන් \2 වැන්නේ \1", out)
    out = re.sub(rf"({_W}) in an? kendra from ({_W})|({_W}) in kendra from ({_W})",
                 lambda m: f"{m.group(2) or m.group(4)}ගෙන් කේන්ද්‍රයක {m.group(1) or m.group(3)}", out)
    for en, si in sorted(PHRASE_SI, key=lambda kv: -len(kv[0])):
        out = out.replace(en, si)
    out = re.sub(r"\b(" + "|".join(_WORD_SI) + r")\b", lambda m: _WORD_SI[m.group(1)], out)
    out = re.sub(r"\b(\d{1,2})(st|nd|rd|th)\b", r"\1 වැනි", out)
    out = out.replace("ලග්නයගෙන්", "ලග්නයෙන්").replace("චන්ද්‍රගෙන්", "චන්ද්‍රයාගෙන්")
    return re.sub(r"\s{2,}", " ", out).strip()


VARNA_SI = {"Brahmin": "බ්‍රාහ්මණ", "Kshatriya": "ක්ෂත්‍රිය", "Vaishya": "වෛශ්‍ය", "Shudra": "ශූද්‍ර"}
VASHYA_SI = {"Chatushpada": "චතුෂ්පද", "Manava": "මානව", "Jalachara": "ජලචර", "Vanachara": "වනචර", "Keeta": "කීට"}
YONI_SI = {"Horse": "අශ්ව", "Elephant": "ගජ", "Sheep": "මේෂ", "Serpent": "සර්ප", "Dog": "ශ්වාන", "Cat": "මාර්ජාර",
           "Rat": "මූෂික", "Cow": "ගෝ", "Buffalo": "මහිෂ", "Tiger": "ව්‍යාඝ්‍ර", "Deer": "මෘග", "Monkey": "වානර",
           "Mongoose": "නකුල", "Lion": "සිංහ"}
GANA_SI = {"Deva": "දේව", "Manushya": "මනුෂ්‍ය", "Rakshasa": "රාක්ෂස"}
NADI_SI = {"Aadi": "ආදි", "Madhya": "මධ්‍ය", "Antya": "අන්ත්‍ය"}
NAK_EN2SI = {jc.NAKSHATRAS[i]: NAK_SI[i] for i in range(27)}
TITHI_SI = {"Shukla": "පුර", "Krishna": "අව", "Prathama": "පළවක", "Dwitiya": "දෙවක", "Tritiya": "තෙවක", "Chaturthi": "සතරවක",
            "Panchami": "පස්වක", "Shashthi": "සයවක", "Saptami": "සත්වක", "Ashtami": "අටවක", "Navami": "නවවක",
            "Dashami": "දසවක", "Ekadashi": "එකොළොස්වක", "Dwadashi": "දොළොස්වක", "Trayodashi": "දහතුන්වක",
            "Chaturdashi": "දහහතරවක", "Purnima": "පසළොස්වක පෝය", "Amavasya": "අමාවක",
            "Pratipada": "පළවක"}
VARA_SI2 = {"Ravi": "ඉරිදා", "Soma": "සඳුදා", "Mangala": "අඟහරුවාදා", "Budha": "බදාදා", "Guru": "බ්‍රහස්පතින්දා",
            "Shukra": "සිකුරාදා", "Shani": "සෙනසුරාදා"}

# Panchanga name tables (engine emits English; these render the report side in Sinhala)
NITYA_YOGA_SI = {"Vishkambha": "විෂ්කම්භ", "Priti": "ප්‍රීති", "Ayushman": "ආයුෂ්මාන්", "Saubhagya": "සෞභාග්‍ය",
                 "Shobhana": "ශෝභන", "Atiganda": "අතිගණ්ඩ", "Sukarma": "සුකර්ම", "Dhriti": "ධෘති",
                 "Shula": "ශූල", "Ganda": "ගණ්ඩ", "Vriddhi": "වෘද්ධි", "Dhruva": "ධ්‍රැව",
                 "Vyaghata": "ව්‍යාඝාත", "Harshana": "හර්ෂණ", "Vajra": "වජ්‍ර", "Siddhi": "සිද්ධි",
                 "Vyatipata": "ව්‍යතීපාත", "Variyan": "වරියාන්", "Parigha": "පරිඝ", "Shiva": "ශිව",
                 "Siddha": "සිද්ධ", "Sadhya": "සාධ්‍ය", "Shubha": "ශුභ", "Shukla": "ශුක්ල",
                 "Brahma": "බ්‍රහ්ම", "Indra": "ඉන්ද්‍ර", "Vaidhriti": "වෛධෘති"}
KARANA_SI = {"Bava": "බව", "Balava": "බාලව", "Kaulava": "කෞලව", "Taitila": "තෛතිල", "Garaja": "ගරජ",
             "Vanija": "වණිජ", "Vishti (Bhadra)": "විෂ්ටි (භද්‍රා)", "Shakuni": "ශකුනි",
             "Chatushpada": "චතුෂ්පාද", "Naga": "නාග", "Kimstughna": "කිංස්තුඝ්න"}
_VARA_NOTE_SI = "සූර්යෝදයට පෙර උපත — පෙර දිනයේ වාරය"


def pch_si(p):
    """Sinhala rendering of the engine's panchanga dict (vara/tithi/yoga/karana)."""
    vara = str(p.get("vara", ""))
    note = _VARA_NOTE_SI if "before sunrise" in vara else ""
    base = re.sub(r"\s*\(.*?\)\s*$", "", vara)
    base = re.sub(r"vara$", "", base, flags=re.I).strip()
    vs = VARA_SI2.get(base, base)
    if note:
        vs = f"{vs} ({note})"
    tithi = str(p.get("tithi", ""))
    for en, si in sorted(TITHI_SI.items(), key=lambda kv: -len(kv[0])):
        tithi = re.sub(r"\b" + re.escape(en) + r"\b", si, tithi)
    return {"vara": vs, "tithi": tithi.strip(),
            "yoga": NITYA_YOGA_SI.get(p.get("yoga", ""), p.get("yoga", "")),
            "karana": KARANA_SI.get(p.get("karana", ""), p.get("karana", "")),
            "sunrise": p.get("sunrise", "")}

KOOTA_SI = {"Varna": ("වර්ණ", "මානසික/ආධ්‍යාත්මික ගැලපීම"), "Vashya": ("වශ්‍ය", "අන්‍යෝන්‍ය ආකර්ෂණය සහ බලපෑම"),
            "Tara": ("තාරා", "සෞභාග්‍යය සහ සෞඛ්‍යය"), "Yoni": ("යෝනි", "ශාරීරික/ලිංගික ගැලපීම"),
            "Graha Maitri": ("ග්‍රහ මෛත්‍රී", "මනස්, මිත්‍රත්වය"), "Gana": ("ගණ", "ස්වභාවය සහ හැසිරීම"),
            "Bhakoot": ("භකූට", "පවුල් සමෘද්ධිය, දරුවන්"), "Nadi": ("නාඩි", "සෞඛ්‍යය සහ පරම්පරාව")}
MUDDA_HINT = {"Su": "අධිකාරිය, පිය, තත්ත්වය", "Mo": "මනස, මව, ජනතාව", "Ma": "ශක්තිය, තරඟ, ඉඩම්", "Me": "කථනය, ව්‍යාපාර, ලේඛන",
              "Ju": "ප්‍රඥාව, ගුරු, දරුවන්, ධනය", "Ve": "සම්බන්ධතා, කලා, සුවපහසුව", "Sa": "ශ්‍රමය, විනය, ප්‍රමාද",
              "Ra": "අනපේක්ෂිත, විදේශ, අභිලාශ", "Ke": "ඉවත්වීම, පර්යේෂණ, ආධ්‍යාත්මික"}
PRASHNA_TOPIC_SI = {"general": "සාමාන්‍ය ප්‍රශ්නය", "travel": "ගමන / ආපසු පැමිණීම", "abroad": "විදේශගත පුද්ගලයා",
                    "lost": "නැතිවූ / සොරකම් කළ දේ", "dispute": "ආරවුල / තරඟය", "health": "සුවතාව",
                    "marriage": "විවාහය", "subject": "ප්‍රශ්නයේ විෂය", "rain": "වර්ෂාව"}


# ================================================================ G — free one-page
def build_g(d, a, now_local):
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    moon = P["Mo"]
    lord = jc.SIGN_LORD[ls]
    labels = {ls: ["ලග්න"]}
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        labels.setdefault(P[c]["sign_idx"], []).append(PLANET_SI[c])
    now_utc = now_local.astimezone(timezone.utc)
    md = ad = None
    for m in d["vimshottari"]["mahadashas"]:
        if datetime.fromisoformat(m["start"]) <= now_utc < datetime.fromisoformat(m["end"]):
            md = m
            for s in m.get("sub", []):
                if datetime.fromisoformat(s["start"]) <= now_utc < datetime.fromisoformat(s["end"]):
                    ad = s
    nak_si = NAK_SI[jc.NAKSHATRAS.index(moon["nakshatra"])]
    H = [f'''<div style="text-align:center"><div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:14pt; font-size:17pt">ඔබේ කේන්දරයේ මූලික තොරතුරු</h1>
      <div class="muted">{esc(a.name)} · {esc(a.date)} · {esc(a.time)} · {esc(a.place or "")}</div></div>''']
    H.append(f'<div class="two" style="margin-top:10pt"><div style="flex:0 0 84mm">{south_indian_html_si(labels, "රාශි චක්‍රය", 84)}</div><div>')
    H.append("<table>"
             f"<tr><td><b>ලග්නය</b></td><td>{SIGN_SI[ls]} ({dms(d['lagna']['deg_in_sign'])})</td></tr>"
             f"<tr><td><b>ලග්නාධිපති</b></td><td>{PLANET_SI[lord]} — {P[lord]['house']} වැන්නේ</td></tr>"
             f"<tr><td><b>චන්ද්‍ර රාශිය</b></td><td>{SIGN_SI[moon['sign_idx']]}</td></tr>"
             f"<tr><td><b>ජන්ම නැකත</b></td><td>{nak_si} — {moon['pada']} වන පාදය</td></tr>"
             f"<tr><td><b>නාම අකුර</b></td><td>{esc(jc.nama_nakshatra(moon['lon'])['sinhala'])}</td></tr>"
             f"<tr><td><b>වත්මන් මහා දශාව</b></td><td>{PLANET_SI[md['lord']] if md else '—'}"
             + (f" ({fmt_date(md['start'], a.tz)} – {fmt_date(md['end'], a.tz)})" if md else "") + "</td></tr>"
             + (f"<tr><td><b>අන්තර් දශාව</b></td><td>{PLANET_SI[ad['lord']]} ({fmt_date(ad['start'], a.tz)} – {fmt_date(ad['end'], a.tz)})</td></tr>" if ad else "")
             + f"<tr><td><b>පංචාංගය</b></td><td>{esc(pch_si(d['panchanga'])['vara'])} · {esc(pch_si(d['panchanga'])['tithi'])}</td></tr>"
             "</table></div></div>")
    H.append(f'<div class="box"><b>{SIGN_SI[ls]} ලග්නය:</b> {LAGNA_NATURE_SI[ls]}.<br>'
             f'<b>{PLANET_SI[md["lord"]] if md else "—"} මහා දශාව:</b> {PLANET_NATURE_SI[md["lord"]] if md else ""} — '
             f'ජන්ම කේන්දරයේ {P[md["lord"]]["house"]} වැන්නේ ({HOUSE_SI[P[md["lord"]]["house"]]}) සිටී.</div>' if md else "")
    H.append('<div class="note"><div class="lbl">මේක නොමිලේ ලැබෙන මූලික තොරතුරු පත්‍රිකාවක්</div>'
             '<p>සම්පූර්ණ විග්‍රහයකට — යෝග/දෝෂ, නවාංශකය, දශා කාල සීමා, ගෝචරය සහ ඉදිරි වසර කිහිපයේ ප්‍රවණතා — '
             'අපගේ <b>කේන්දර සාර (A1)</b> වාර්තාව බලන්න.</p></div>')
    H.append('<p class="disc">ජ්‍යොතිෂය ප්‍රවණතා ගැන ප්‍රතිබිම්බනාත්මක මගපෙන්වීමකි; ස්ථිර අනාවැකි නොවේ. වෛද්‍ය, නීතිමය හෝ මූල්‍ය උපදෙස් නොවේ. '
             'උපන් වේලාවේ නිරවද්‍යතාව ප්‍රතිඵල වලට බලපායි. ගණනය: ලාහිරි අයනාංශය · සම්පූර්ණ රාශි භාව ක්‍රමය · Swiss Ephemeris.</p>')
    H.append(f'<div class="brandfoot"><div class="brandmark" style="font-size:11pt">{esc(BRAND)}</div>'
             + (f'<div class="muted">{esc(BRAND_CONTACT)}</div>' if BRAND_CONTACT else "") + "</div>")
    return "\n".join(H)


# ================================================================ C1 — Varsha Phala
def build_c1(d, a, notes, now_local, year):
    v = d["varsha_kundali"]
    inv = {s: i for i, s in enumerate(jc.SIGNS)}
    vls = inv[v["lagna"]]
    labels = {vls: ["ලග්න"]}
    for c, p in v["planets"].items():
        labels.setdefault(inv[p["sign"]], []).append(PLANET_SI[c] + (" (ව)" if p["retro"] and c not in ("Ra", "Ke") else ""))
    labels.setdefault(inv[v["muntha"]], []).append("මුන්ථා")
    natal = d["planets"]
    nls = d["lagna"]["sign_idx"]
    vsh = v["varshesha"]
    H = [f'''<div class="cover" style="padding-top:12mm"><div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">වාර්ෂික ඵල වාර්තාව</h1><div class="sub">වර්ෂ ඵල — තාජක ක්‍රමය (C1) · {year}–{year + 1}</div>
      <div class="name">{esc(a.name)}</div>
      <div class="muted">ජන්ම: {esc(a.date)} · {esc(a.time)} · {esc(a.place or "")}</div>
      <div style="margin:14pt auto 0 auto; width:112mm">{south_indian_html_si(labels, f"වර්ෂ කුණ්ඩලිය {year}", 112)}</div>
      <p class="muted" style="margin-top:10pt; font-size:8.5pt">වර්ෂ ප්‍රවේශය {esc(v["varsha_pravesha_local"])} ({esc(a.tz)}) · තාජක ක්‍රමය · ලාහිරි අයනාංශය</p></div>''']
    H.append('<div class="pb"></div><h2>1. වර්ෂයේ මූලික ව්‍යුහය</h2>')
    H.append("<table>"
             f"<tr><td style='width:34%'><b>වර්ෂ ප්‍රවේශය</b></td><td>{esc(v['varsha_pravesha_local'])} ({esc(a.tz)}) — රවි ජන්ම ස්ථානයට පැමිණෙන මොහොත</td></tr>"
             f"<tr><td><b>වර්ෂ ලග්නය</b></td><td>{SIGN_SI[vls]} ({dms(v['lagna_deg'])})</td></tr>"
             f"<tr><td><b>මුන්ථා</b></td><td>{SIGN_SI[inv[v['muntha']]]} — වර්ෂ ලග්නයෙන් {jc.house_from(vls, inv[v['muntha']])} වැන්නේ, "
             f"ජන්ම ලග්නයෙන් {jc.house_from(nls, inv[v['muntha']])} වැන්නේ ({HOUSE_SI[jc.house_from(nls, inv[v['muntha']])]})</td></tr>"
             f"<tr><td><b>වර්ෂේශ (වර්ෂාධිපති)</b></td><td>{PLANET_SI[vsh]} — {PLANET_NATURE_SI[vsh]}</td></tr>"
             f"<tr><td><b>දින/රාත්‍රී කේන්දරය</b></td><td>{'දිවා' if v['day_chart'] else 'රාත්‍රී'}</td></tr>"
             "</table>")
    H.append(f'<div class="box">මුන්ථා ජන්ම කේන්දරයේ {jc.house_from(nls, inv[v["muntha"]])} වැන්නට පැමිණීම මේ වර්ෂයේ '
             f'{HOUSE_SI[jc.house_from(nls, inv[v["muntha"]])]} සම්බන්ධ කාරණා ඉදිරියට එන ප්‍රවණතාවක් පෙන්වයි. '
             f'වර්ෂේශ {PLANET_SI[vsh]} වර්ෂය පුරා ප්‍රධාන ග්‍රහයා ලෙස ක්‍රියා කරයි.</div>')
    H.append(note_block(notes, "summary"))
    H.append("<h3>වර්ෂ කුණ්ඩලියේ ග්‍රහ ස්ථාන සහ බල</h3>")
    rows = []
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        p = v["planets"][c]
        s = inv[p["sign"]]
        hb = v["harsha_bala"].get(c)
        pv = v["pancha_vargeeya"].get(c)
        rows.append(f"<tr><td>{PLANET_SI[c]}</td><td>{SIGN_SI[s]}</td><td>{dms(p['lon'] % 30)}</td>"
                    f"<td>{jc.house_from(vls, s)}</td><td>{'වක්‍ර' if p['retro'] and c not in ('Ra', 'Ke') else ''}</td>"
                    f"<td>{hb if hb is not None else '—'}</td><td>{pv if pv is not None else '—'}</td></tr>")
    H.append("<table><tr><th>ග්‍රහයා</th><th>රාශිය</th><th>අංශක</th><th>වර්ෂ භාවය</th><th></th><th>හර්ෂ බල</th><th>පංච වර්ගීය බල</th></tr>"
             + "".join(rows) + "</table>")
    H.append('<p class="small muted">හර්ෂ බල (0–20) සහ පංච වර්ගීය බල (0–20) තාජක ක්‍රමයේ ග්‍රහ ශක්තිය මනින ක්‍රම දෙකකි; ඉහළ අගය = ශක්තිමත්.</p>')

    H.append('<div class="pb"></div><h2>2. තාජක යෝග</h2>')
    ty = v["tajaka_yogas"]
    items = [("ඉථසාල (කාරණය ඉටුවීමට නැඹුරු)", ty.get("ithasala", [])), ("ඊසර්ඵ (කාරණය ලිස්සා යාමට නැඹුරු)", ty.get("eesarpha", [])),
             ("වෙනත් යෝග", ty.get("general", [])), ("නක්ත / යමයා", ty.get("nakta_yamaya", []))]
    any_y = False
    for title, lst in items:
        if lst:
            any_y = True
            H.append(f"<h3>{title}</h3><ul>" + "".join(f"<li>{esc(si_text(x))}</li>" for x in lst) + "</ul>")
    if not any_y:
        H.append("<p>මේ වර්ෂ කුණ්ඩලියේ දෘෂ්ටි කක්ෂ තුළ ප්‍රධාන තාජක යෝග නොමැත.</p>")
    H.append(note_block(notes, "yogas"))

    H.append("<h2>3. සහම් (Sahams) — කාරණා අනුව සංවේදී ලක්ෂ්‍ය</h2>")
    srow = []
    for k, sv in list(v["sahams"].items())[:14]:
        lon = sv["lon"] if isinstance(sv, dict) else sv
        s = jc.sign_of(lon)
        srow.append(f"<tr><td>{esc(SAHAM_SI.get(k, k))}</td><td>{SIGN_SI[s]} {dms(lon % 30)}</td>"
                    f"<td>{jc.house_from(vls, s)}</td><td>{PLANET_SI[jc.SIGN_LORD[s]]}</td></tr>")
    H.append("<table><tr><th>සහමය</th><th>ස්ථානය</th><th>වර්ෂ භාවය</th><th>අධිපති</th></tr>" + "".join(srow) + "</table>")
    H.append('<p class="small muted">සහමයක් ශක්තිමත් ග්‍රහයෙකු සමඟ සම්බන්ධ වන කාලවලදී එම කාරණය ඉදිරියට එන ප්‍රවණතාවක් ඇත.</p>')

    H.append('<div class="pb"></div><h2>4. මුද්දා දශා — වර්ෂයේ කාල බෙදීම</h2>')
    mrow = []
    nowl = now_local.strftime("%Y-%m-%d %H:%M")
    for m in v["mudda"]:
        curr = m["start"][:16] <= nowl < m["end"][:16]
        mrow.append(f"<tr{' class=cur' if curr else ''}><td>{PLANET_SI[m['lord']]}</td><td>{esc(m['start'])}</td><td>{esc(m['end'])}</td>"
                    f"<td>{MUDDA_HINT[m['lord']]}</td></tr>")
    H.append("<table><tr><th>දශාධිපති</th><th>ආරම්භය</th><th>අවසානය</th><th>ප්‍රවණතාව</th></tr>" + "".join(mrow) + "</table>")
    H.append(note_block(notes, "dasha"))

    H.append("<h2>5. ඉදිරි කාලය — වර්ෂයේ ප්‍රධාන කවුළු</h2>")
    strong = sorted(v["pancha_vargeeya"].items(), key=lambda kv: -kv[1])[:3]
    weak = sorted(v["pancha_vargeeya"].items(), key=lambda kv: kv[1])[:2]
    H.append("<ul>"
             + f"<li>වර්ෂය පුරා ප්‍රධාන ග්‍රහයා: <b>{PLANET_SI[vsh]}</b> — {PLANET_NATURE_SI[vsh]}</li>"
             + f"<li>ශක්තිමත්ම ග්‍රහයන්: {', '.join(PLANET_SI[k] for k, _ in strong)} — මේවාගේ මුද්දා දශා කාල වඩාත් ඵලදායී</li>"
             + f"<li>දුර්වල ග්‍රහයන්: {', '.join(PLANET_SI[k] for k, _ in weak)} — ඒ කාලවලදී ඉවසීම සහ සැලසුම්</li>"
             + "".join(f"<li><b>{m['start'][:7]} → {m['end'][:7]}</b> — {PLANET_SI[m['lord']]} මුද්දා දශාව: {MUDDA_HINT[m['lord']]}</li>"
                       for m in v["mudda"] if m["end"][:10] >= now_local.strftime("%Y-%m-%d"))
             + "</ul>")
    H.append(note_block(notes, "upcoming"))
    if (notes or {}).get("remedies"):
        H.append("<h2>6. යෝජනා</h2>" + note_block(notes, "remedies", "ප්‍රතිකර්ම / ආකල්ප යෝජනා"))
    H.append(disclaimer_block("වර්ෂ ඵල (තාජක) ක්‍රමය — P.V.R. Narasimha Rao, ch. 27–31. වර්ෂ කුණ්ඩලිය සෑදෙන්නේ රවි නැවත ජන්ම ස්ථානයට පැමිණෙන මොහොතටයි. "
                              "මේ වාර්තාව ජන්ම කේන්දරයට අතිරේකයකි; ජන්ම කේන්දරය සමඟ එකට කියවිය යුතුයි."))
    return "\n".join(H)


# ================================================================ D1 — Porondam (compatibility)
def build_d1(d, a, notes, now_local):
    comp = d["compatibility"]
    if not comp:
        sys.exit("compatibility data missing — check --match-* arguments")
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    pt = comp["partner"]
    inv = {s: i for i, s in enumerate(jc.SIGNS)}
    total = comp["ashtakoota_total"]
    verdict = ("හොඳ ගැලපීමක්" if total >= 24 else "මධ්‍යම ගැලපීමක්" if total >= 18 else "අඩු ලකුණු ගැලපීමක්")
    labels = {ls: ["ලග්න"]}
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        labels.setdefault(P[c]["sign_idx"], []).append(PLANET_SI[c])
    H = [f'''<div class="cover" style="padding-top:12mm"><div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">පොරොන්දම් වාර්තාව</h1><div class="sub">අෂ්ටකූට ගැලපීම (D1)</div>
      <div class="name">{esc(a.name)} &nbsp;·&nbsp; {esc(a.match_name or "සහකරු")}</div>
      <div style="margin:16pt auto; font-size:15pt"><b>{total} / 36</b> — {verdict}</div>
      <div style="width:104mm; margin:0 auto">{south_indian_html_si(labels, "රාශි චක්‍රය (පළමු කේන්දරය)", 104)}</div></div>''']
    H.append('<div class="pb"></div><h2>1. උපන් දත්ත</h2><table><tr><th></th><th>පළමු අය</th><th>දෙවන අය</th></tr>'
             f'<tr><td><b>නම</b></td><td>{esc(a.name)}</td><td>{esc(a.match_name or "—")}</td></tr>'
             f'<tr><td><b>උපන් දිනය</b></td><td>{esc(a.date)}</td><td>{esc(pt["date"])}</td></tr>'
             f'<tr><td><b>වේලාව</b></td><td>{esc(a.time)}</td><td>{esc(pt["time"])}</td></tr>'
             f'<tr><td><b>ලග්නය</b></td><td>{SIGN_SI[ls]}</td><td>{SIGN_SI[inv[pt["lagna"]]]}</td></tr>'
             f'<tr><td><b>චන්ද්‍ර රාශිය</b></td><td>{SIGN_SI[P["Mo"]["sign_idx"]]}</td><td>{SIGN_SI[inv[pt["moon"]]]}</td></tr>'
             "</table>")
    H.append("<h2>2. අෂ්ටකූට ලකුණු</h2>")
    krow = []
    for k in comp["kootas"]:
        si, meaning = KOOTA_SI.get(k["name"], (k["name"], ""))
        det = k["detail"]
        for tbl in (VARNA_SI, VASHYA_SI, YONI_SI, GANA_SI, NADI_SI, NAK_EN2SI):
            for en, sisi in sorted(tbl.items(), key=lambda kv: -len(kv[0])):
                det = re.sub(r"\b" + re.escape(en) + r"\b", sisi, det)
        det = (si_text(det).replace("Bhakoot dosha", "භකූට දෝෂය").replace("Nadi dosha", "නාඩි දෝෂය")
               .replace("cancelled", "නිෂ්ප්‍රභ වී ඇත").replace("same/friendly අධිපතිs", "අධිපතියන් සම/මිත්‍ර")
               .replace("same/friendly lords", "අධිපතියන් සම/මිත්‍ර")
               .replace("(same)", "(සම)").replace("(6/8)", "(6/8 තත්ත්වය)"))
        krow.append(f"<tr><td>{si}</td><td>{meaning}</td><td><b>{k['points']}</b> / {k['max']}</td><td>{esc(det)}</td></tr>")
    H.append("<table><tr><th>කූටය</th><th>මනින දේ</th><th>ලකුණු</th><th>විස්තර</th></tr>" + "".join(krow)
             + f"<tr class='cur'><td colspan='2'><b>එකතුව</b></td><td><b>{total} / 36</b></td><td>{verdict}</td></tr></table>")
    H.append('<div class="note"><div class="lbl">ලකුණු කියවන ආකාරය</div>'
             '<p>අෂ්ටකූට යනු ගැලපීම මනින එක් ක්‍රමයක් පමණි — අවසන් තීරණය නොවේ. 18ට අඩු නම් සාමාන්‍යයෙන් වැඩිදුර පරීක්ෂාව අවශ්‍යයි; '
             '18–24 මධ්‍යම; 24ට වැඩි නම් හොඳ ලෙස සලකනු ලැබේ. නමුත් දෝෂ නිෂ්ප්‍රභ වීම්, දෙදෙනාගේම 7 වැන්න, D9 කේන්දර සහ දශා ගැලපීම '
             'ලකුණු එකතුවට වඩා වැදගත් විය හැක. පහත කොටස් බලන්න.</p></div>')
    dosha = []
    for k in comp["kootas"]:
        if "dosha" in k["detail"].lower():
            nm = "භකූට දෝෂය" if k["name"] == "Bhakoot" else "නාඩි දෝෂය"
            canc = "cancel" in k["detail"].lower()
            dosha.append(f"<li><b>{nm}</b> — {esc(si_text(k['detail']))}. "
                         + ("<b>නිෂ්ප්‍රභ වී ඇත</b> (සම්භාව්‍ය ග්‍රන්ථවල දක්වා ඇති නිෂ්ප්‍රභ වීමේ නියමයක් අනුව)." if canc
                            else "නිෂ්ප්‍රභ වීමේ නියමයක් මෙහි ක්‍රියාත්මක නොවේ — වැඩිදුර පරීක්ෂාව අවශ්‍යයි.") + "</li>")
    mangal = [y for y in d.get("yoga_indications", []) if "Mangal" in y]
    if mangal:
        dosha.append("<li><b>කුජ දෝෂ ඇඟවීම</b> (පළමු කේන්දරයේ) — දෙදෙනාගේම කේන්දර දෙකේම කුජ ස්ථානය සහ නිෂ්ප්‍රභ වීම් එකට පරීක්ෂා කළ යුතුයි.</li>")
    H.append("<h2>3. දෝෂ සහ නිෂ්ප්‍රභ වීම්</h2><ul>" + ("".join(dosha) if dosha else "<li>ප්‍රධාන දෝෂ ඇඟවීම් නොමැත.</li>") + "</ul>")
    H.append(note_block(notes, "dosha") or note_block(notes, "yogas"))
    H.append('<div class="pb"></div><h2>4. ජ්‍යොතිෂවේදියාගේ විග්‍රහය</h2>')
    H.append(note_block(notes, "summary") or '<p class="muted">(සවිස්තර විග්‍රහය සඳහා සම්පූර්ණ පොරොන්දම් වාර්තාව — D2 — බලන්න.)</p>')
    H.append(note_block(notes, "upcoming", "විවාහ කාලය සහ ඉදිරි කාලය"))
    H.append(disclaimer_block("අෂ්ටකූට ගුණ මිලන ක්‍රමය සහ දෝෂ නිෂ්ප්‍රභ වීමේ නියම — P.V.R. Narasimha Rao, ch. 26. "
                              "මේ වාර්තාව ගැලපීම පිළිබඳ එක් දෘෂ්ටි කෝණයක් පමණි. විවාහය පිළිබඳ තීරණය දෙදෙනාගේ අවබෝධය, "
                              "සන්නිවේදනය සහ පවුල්වල එකඟතාව මත පදනම් විය යුතුයි — ලකුණු එකතුවක් මත නොවේ."))
    return "\n".join(H)


# ================================================================ P1 — Prashna
def build_p1(d, a, notes, now_local, shat_topic, matter):
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    labels = {ls: ["ලග්න"]}
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        labels.setdefault(P[c]["sign_idx"], []).append(PLANET_SI[c] + (" (ව)" if P[c]["retro"] and c not in ("Ra", "Ke") else ""))
    H = [f'''<div class="cover" style="padding-top:12mm"><div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">ප්‍රශ්න වාර්තාව</h1><div class="sub">ප්‍රශ්න ජ්‍යොතිෂය (P1) — තාජක සහ ෂට්පංචාශිකා</div>
      <div class="name" style="font-size:14pt">{esc(a.question or a.name)}</div>
      <div class="muted">ප්‍රශ්න මොහොත: {esc(a.date)} · {esc(a.time)} · {esc(a.place or "")}</div>
      <div style="margin:14pt auto 0 auto; width:112mm">{south_indian_html_si(labels, "ප්‍රශ්න කේන්දරය", 112)}</div></div>''']
    H.append('<div class="pb"></div><h2>1. ප්‍රශ්න කේන්දරයේ මූලික තොරතුරු</h2>')
    lord = jc.SIGN_LORD[ls]
    H.append("<table>"
             f"<tr><td style='width:34%'><b>ප්‍රශ්න ලග්නය</b></td><td>{SIGN_SI[ls]} ({dms(d['lagna']['deg_in_sign'])}) — අධිපති {PLANET_SI[lord]}, {P[lord]['house']} වැන්නේ</td></tr>"
             f"<tr><td><b>චන්ද්‍ර</b></td><td>{SIGN_SI[P['Mo']['sign_idx']]} — {P['Mo']['house']} වැන්නේ, {NAK_SI[jc.NAKSHATRAS.index(P['Mo']['nakshatra'])]} නැකත</td></tr>"
             f"<tr><td><b>හෝරාධිපති</b></td><td>{esc(si_text(d.get('hora', '')))}</td></tr>"
             f"<tr><td><b>පංචාංගය</b></td><td>{esc(pch_si(d['panchanga'])['vara'])} · {esc(pch_si(d['panchanga'])['tithi'])} · {esc(pch_si(d['panchanga'])['karana'])} කරණ</td></tr>"
             "</table>")
    ps = d.get("prashna_strengths", {})
    if ps:
        H.append("<h3>ග්‍රහ බල (තාජක)</h3><table><tr><th>ග්‍රහයා</th>"
                 + "".join(f"<th>{PLANET_SI[c]}</th>" for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]) + "</tr>"
                 + "<tr><td>හර්ෂ බල</td>" + "".join(f"<td>{ps['harsha'][c]}</td>" for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]) + "</tr>"
                 + "<tr><td>පංච වර්ගීය</td>" + "".join(f"<td>{ps['pvb'][c]}</td>" for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]) + "</tr></table>")
    ty = d.get("tajaka_yogas", {})
    lines = [("ඉථසාල", ty.get("ithasala", [])), ("ඊසර්ඵ", ty.get("eesarpha", [])), ("වෙනත්", ty.get("general", []) + ty.get("nakta_yamaya", []))]
    H.append("<h2>2. තාජක යෝග</h2>")
    if any(l for _, l in lines):
        for t, l in lines:
            if l:
                H.append(f"<h3>{t}</h3><ul>" + "".join(f"<li>{esc(si_text(x))}</li>" for x in l) + "</ul>")
    else:
        H.append("<p>දෘෂ්ටි කක්ෂ තුළ ප්‍රධාන තාජක යෝග නොමැත.</p>")
    if matter:
        H.append(f"<h2>3. කාරණය — {matter} වන භාවය ({HOUSE_SI[matter]})</h2><ul>"
                 + "".join(f"<li>{esc(si_text(x.strip()))}</li>" for x in d.get("matter_lines", [])) + "</ul>")
        H.append('<p class="small muted">ලග්නාධිපති, කාරණයේ භාවාධිපති, අදාළ සහමයේ අධිපති සහ ස්වාභාවික කාරකයා අතර ඉථසාල යෝගයක් '
                 'කාරණය ඉටුවීමට නැඹුරුව පෙන්වයි; ඊසර්ඵ ලිස්සා යාම පෙන්වයි (තාජක 29.2).</p>')
    if d.get("shatpanchasika"):
        H.append(f'<div class="pb"></div><h2>4. ෂට්පංචාශිකා — {PRASHNA_TOPIC_SI.get(shat_topic, shat_topic)}</h2>')
        H.append("<table><tr><th style='width:8%'>ශ්ලෝකය</th><th>නියමය</th><th>ඇඟවීම</th></tr>"
                 + "".join(f"<tr><td>{r['stanza']}</td><td>{esc(si_text(r['rule']))}</td><td>{esc(si_text(r['verdict']))}</td></tr>"
                           for r in d["shatpanchasika"]) + "</table>")
        H.append('<p class="small muted">මූලාශ්‍රය: ප්‍රිථුයශස් ගේ ෂට්පංචාශිකා (චප්පන්න), B. Suryanarain Rao ගේ 1946 ඉංග්‍රීසි පරිවර්තනය. '
                 'නූපන් දරුවාගේ ලිංගය, ලිංගික හැසිරීම සහ මරණය පිළිබඳ ශ්ලෝක මෙහි ඉදිරිපත් නොකෙරේ.</p>')
    H.append("<h2>5. විග්‍රහය</h2>")
    H.append(f'<div class="box">{p1_auto_summary(d, matter, shat_topic)}</div>')
    H.append(note_block(notes, "summary"))
    H.append(note_block(notes, "upcoming", "කාල සීමා"))
    H.append(disclaimer_block("ප්‍රශ්න ජ්‍යොතිෂය — තාජක ක්‍රමය (P.V.R. Narasimha Rao ch. 27–29) සහ ෂට්පංචාශිකා. "
                              "ප්‍රශ්න කේන්දරය සෑදෙන්නේ ප්‍රශ්නය අසන මොහොතටයි; එම මොහොත වැරදි නම් ප්‍රතිඵලයද වෙනස් වේ. "
                              "මේ ඇඟවීම් ප්‍රවණතා පෙන්වන අතර, ඔබේ තීරණය ඔබේ විචාරය මතයි."))
    return "\n".join(H)


POS_MARKS = ("සාර්ථක", "ලැබීම", "ලාභ", "ජය", "සමෘද්ධි", "හිතකර", "ඉටුවීම", "සාමය", "සුවය", "විවාහය සිදුවීම", "ගෞරව")
NEG_MARKS = ("අසාර්ථක", "අලාභ", "පරාජය", "නොවේ", "නැත", "ලිස්සා", "බිය", "බාධක", "ප්‍රවේශම්", "අහිමි")


def p1_auto_summary(d, matter, shat_topic):
    """Objective synthesis so this section is never empty; the astrologer's note is added below it."""
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    lord = jc.SIGN_LORD[ls]
    ty = d.get("tajaka_yogas", {})
    ith, ees = len(ty.get("ithasala", [])), len(ty.get("eesarpha", []))
    bits = []
    bits.append(f"ප්‍රශ්න ලග්නය <b>{SIGN_SI[ls]}</b>; අධිපති {PLANET_SI[lord]} {P[lord]['house']} වැන්නේ. "
                f"චන්ද්‍ර {SIGN_SI[P['Mo']['sign_idx']]} — {P['Mo']['house']} වැන්නේ."
                + (" ලග්නාධිපති කේන්ද්‍ර/ත්‍රිකෝණයක සිටීම ප්‍රශ්නකරුට ශක්තියක්." if P[lord]["house"] in (1, 4, 5, 7, 9, 10)
                   else " ලග්නාධිපති දුස්ථානයක සිටීම ශ්‍රමය අවශ්‍ය බව පෙන්වයි." if P[lord]["house"] in (6, 8, 12) else ""))
    if matter:
        ml = " ".join(d.get("matter_lines", []))
        if "ITHASALA" in ml:
            bits.append(f"<b>{matter} වන භාවය</b> ({HOUSE_SI[matter]}) සම්බන්ධ කාරක ග්‍රහයන් අතර <b>ඉථසාල</b> යෝගයක් ඇත — "
                        "කාරණය ඉටුවීමට නැඹුරු ප්‍රවණතාවක්.")
        elif "EESARPHA" in ml:
            bits.append(f"<b>{matter} වන භාවය</b> ({HOUSE_SI[matter]}) සම්බන්ධ කාරක ග්‍රහයන් අතර <b>ඊසර්ඵ</b> යෝගයක් ඇත — "
                        "කාරණය ලිස්සා යාමට හෝ ප්‍රමාද වීමට නැඹුරු ප්‍රවණතාවක්; අමතර උත්සාහයක් අවශ්‍ය විය හැක.")
        else:
            bits.append(f"<b>{matter} වන භාවය</b> සම්බන්ධ කාරක ග්‍රහයන් අතර ඉථසාල/ඊසර්ඵ යෝගයක් නැත — "
                        "තාජක ක්‍රමයෙන් මේ කාරණයට ශක්තිමත් ඇඟවීමක් නොලැබේ.")
    bits.append(f"තාජක යෝග: ඉථසාල {ith}ක්, ඊසර්ඵ {ees}ක් — "
                + ("ඉටුවීමේ ඇඟවීම් වැඩියි." if ith > ees else "ප්‍රමාද/බාධක ඇඟවීම් වැඩියි." if ees > ith else "දෙපැත්තම සමානයි."))
    sh = d.get("shatpanchasika") or []
    if sh:
        pos = sum(1 for r in sh if any(w in si_text(r["verdict"]) for w in POS_MARKS) and not any(w in si_text(r["verdict"]) for w in NEG_MARKS))
        neg = sum(1 for r in sh if any(w in si_text(r["verdict"]) for w in NEG_MARKS))
        bits.append(f"ෂට්පංචාශිකා ({PRASHNA_TOPIC_SI.get(shat_topic, shat_topic)}): හිතකර ඇඟවීම් {pos}ක්, අවධානය යොමු කළ යුතු ඇඟවීම් {neg}ක්"
                    + (" — සමස්තයක් ලෙස හිතකර පැත්තට බර වැඩියි." if pos > neg
                       else " — සමස්තයක් ලෙස අවධානය යොමු කළ යුතු පැත්තට බර වැඩියි." if neg > pos else " — මිශ්‍රයි."))
    bits.append("<span class=\"muted\">මේ ඇඟවීම් ප්‍රවණතා පෙන්වන අතර පරස්පර ඇඟවීම් ද තිබිය හැක; අවසන් තීරණය ඔබේ විචාරය මතයි.</span>")
    return "<br>".join(bits)


def disclaimer_block(method_line):
    return ('<div class="pb"></div><h2>ක්‍රමවේදය සහ වගකීම් ප්‍රකාශය</h2>'
            f'<div class="disc"><p><b>ක්‍රමවේදය:</b> {method_line} ලාහිරි අයනාංශය, සම්පූර්ණ රාශි භාව ක්‍රමය, මධ්‍යම රාහු–කේතු, Swiss Ephemeris ගණනය.</p>'
            '<p><b>වගකීම් ප්‍රකාශය:</b> මේ වාර්තාව ප්‍රවණතා සහ කාල රටා ගැන ප්‍රතිබිම්බනාත්මක මගපෙන්වීමකි — ස්ථිර අනාවැකි නොවේ. '
            'වෛද්‍ය රෝග විනිශ්චය, ආයුෂ/මරණ අනාවැකි, නීතිමය හෝ මූල්‍ය ආයෝජන උපදෙස් මෙහි අන්තර්ගත නොවේ; ඒ සඳහා සුදුසුකම් ලත් වෘත්තිකයෙකු හමුවන්න.</p>'
            '<p><b>පෞද්ගලිකත්වය:</b> ඔබේ දත්ත මේ වාර්තාව සැකසීමට පමණක් භාවිත කර ඇත; තෙවන පාර්ශ්වයකට ලබා නොදේ.</p></div>'
            f'<div class="brandfoot"><div class="brandmark" style="font-size:12pt">{esc(BRAND)}</div>'
            f'<div class="brandtag" style="font-size:8.5pt">{esc(BRAND_TAGLINE)}</div>'
            + (f'<div class="muted" style="margin-top:4pt">{esc(BRAND_CONTACT)}</div>' if BRAND_CONTACT else "") + "</div>")


# ================================================================ A2 / A3 — standard & deep natal
VARGA_SI = {"D1": ("රාශි", "සමස්ත ජීවිතය"), "D2": ("හෝරා", "ධනය"), "D3": ("ද්‍රේෂ්කාණ", "සහෝදරයන්, ධෛර්යය"),
            "D4": ("චතුර්ථාංශ", "දේපල, නිවස, වාසනාව"), "D7": ("සප්තාංශ", "දරුවන්, පරම්පරාව"),
            "D9": ("නවාංශක", "විවාහය, අභ්‍යන්තර ශක්තිය, ග්‍රහ බලය"), "D10": ("දශාංශ", "රැකියාව, කර්මය"),
            "D12": ("ද්වාදශාංශ", "දෙමව්පියන්"), "D16": ("ෂෝඩශාංශ", "වාහන, සුවපහසුව"), "D20": ("විංශාංශ", "ආධ්‍යාත්මික සාධනය"),
            "D24": ("චතුර්විංශාංශ", "අධ්‍යාපනය, ඉගෙනුම"), "D27": ("භාංශ", "ශක්තිය සහ දුර්වලතා"),
            "D30": ("ත්‍රිංශාංශ", "අභියෝග, දුෂ්කරතා"), "D40": ("ඛවේදාංශ", "මාතෘ පාර්ශ්ව උරුමය"),
            "D45": ("අක්ෂවේදාංශ", "පිතෘ පාර්ශ්ව උරුමය"), "D60": ("ෂෂ්ටිඅංශ", "පූර්ව කර්මය")}
YOGA_CAT_SI = {"Ravi": "රවි යෝග", "Chandra": "චන්ද්‍ර යෝග", "Mahapurusha": "පංච මහාපුරුෂ යෝග",
               "Nabhasa-Asraya": "නාභස (ආශ්‍රය) යෝග", "Nabhasa-Dala": "නාභස (දල) යෝග", "Nabhasa-Akriti": "නාභස (ආකෘති) යෝග",
               "Nabhasa-Sankhya": "නාභස (සංඛ්‍යා) යෝග", "Popular": "ප්‍රසිද්ධ යෝග", "Vipareeta": "විපරීත රාජ යෝග",
               "Raja": "රාජ යෝග", "Dhana": "ධන යෝග", "Daridra": "දාරිද්‍ර යෝග (අවධානය)"}
UPAGRAHA_SI = {"Dhuma": "ධූම", "Vyatipata": "ව්‍යතීපාත", "Parivesha": "පරිවේෂ", "Indrachapa": "ඉන්ද්‍රචාප", "Upaketu": "උපකේතු",
               "Kaala": "කාල", "Mrityu": "මෘත්‍යු", "Arthaprahara": "අර්ථප්‍රහාර", "Yamaghantaka": "යමඝණ්ටක",
               "Gulika": "ගුලික", "Maandi": "මාන්දි"}
AREA_DEF = {
    "career": ("රැකියාව සහ කර්මය", 10, "D10", ["AmK"], (1, 2, 6, 7, 10, 11)),
    "marriage": ("විවාහය සහ සම්බන්ධතා", 7, "D9", ["DK"], (2, 7, 8, 12)),
    "wealth": ("ධනය සහ ආදායම", 2, "D2", [], (2, 5, 9, 11)),
    "education": ("අධ්‍යාපනය", 4, "D24", [], (2, 4, 5, 9)),
    "family": ("පවුල සහ නිවස", 4, "D12", ["MK"], (2, 4, 9, 12)),
}


def area_paragraph(d, key):
    """Objective Sinhala paragraph for one life area: house, lord, occupants, karaka, varga lagna."""
    title, house, varga, karakas, support = AREA_DEF[key]
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    hs = (ls + house - 1) % 12
    lord = jc.SIGN_LORD[hs]
    occ = [c for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"] if P[c]["sign_idx"] == hs]
    kar = {"career": "Sa", "marriage": "Ve", "wealth": "Ju", "education": "Me", "family": "Mo"}[key]
    bits = [f"<b>{house} වන භාවය</b> ({SIGN_SI[hs]}) — {HOUSE_SI[house]}."]
    bits.append(f"අධිපති {PLANET_SI[lord]} {SIGN_SI[P[lord]['sign_idx']]} රාශියේ, {P[lord]['house']} වැන්නේ"
                + (f" ({si_dignity(P[lord]['dignity'])})" if si_dignity(P[lord]["dignity"]) != "—" else "")
                + (", වක්‍ර" if P[lord]["retro"] and lord not in ("Ra", "Ke") else "") + ".")
    bits.append("භාවයේ ග්‍රහයන්: " + (", ".join(PLANET_SI[c] for c in occ) if occ else "නැත") + ".")
    bits.append(f"කාරකයා {PLANET_SI[kar]} {P[kar]['house']} වැන්නේ"
                + (f" ({si_dignity(P[kar]['dignity'])})" if si_dignity(P[kar]["dignity"]) != "—" else "") + ".")
    v = d["vargas"].get(varga)
    if v:
        inv = {s: i for i, s in enumerate(jc.SIGNS)}
        vl = inv[v["La"]]
        vlord = jc.SIGN_LORD[vl]
        bits.append(f"{varga} ({VARGA_SI[varga][0]}) ලග්නය {SIGN_SI[vl]}; අධිපති {PLANET_SI[vlord]} "
                    f"එම කේන්දරයේ {jc.house_from(vl, inv[v[vlord]])} වැන්නේ.")
    kk = d["chara_karakas"]
    for k in karakas:
        if k in kk:
            kp = kk[k]["planet"]
            bits.append(f"{k} ({PLANET_SI[kp]}) ජන්ම කේන්දරයේ {P[kp]['house']} වැන්නේ.")
    strong = P[lord]["house"] in (1, 4, 5, 7, 9, 10, 11) and "නීච" not in si_dignity(P[lord]["dignity"])
    bits.append("<b>ප්‍රවණතාව:</b> " + ("භාවාධිපති හිතකර ස්ථානයක සිටීම මේ ක්ෂේත්‍රයට සහායකයි."
                                        if strong else "භාවාධිපතිගේ ස්ථානය අනුව මේ ක්ෂේත්‍රයේ ප්‍රතිඵල ශ්‍රමයෙන් ලැබෙන ප්‍රවණතාවක් ඇත.")
                + " දශා සහ ගෝචර කොටස් සමඟ එකට කියවන්න.")
    return title, " ".join(bits)


def sade_sati_timeline(natal_moon_sign, start_utc, years=15):
    """Saturn's transits through 12th/1st/2nd (Sade Sati) and 4th/8th (Dhaiya) from the natal Moon."""
    rows = []
    jd0, _ = jc.to_jd_ut(start_utc.replace(tzinfo=None), "UTC")
    prev = None
    for dd in range(0, int(years * 365.25), 10):
        s = jc.sign_of(jc.compute_positions(jd0 + dd)[0]["Sa"]["lon"])
        h = jc.house_from(natal_moon_sign, s)
        tag = "සඩේ සති" if h in (12, 1, 2) else ("ධයියා" if h in (4, 8) else None)
        key = (tag, h) if tag else None
        if key != prev:
            if rows and rows[-1][1] is None:
                rows[-1][1] = jc.jd_to_datetime(jd0 + dd)
            if tag:
                rows.append([jc.jd_to_datetime(jd0 + dd), None, tag, h])
            prev = key
    if rows and rows[-1][1] is None:
        rows[-1][1] = jc.jd_to_datetime(jd0 + int(years * 365.25))
    # merge only retrograde re-entries into the SAME house
    merged = []
    for r in rows:
        if merged and r[2] == merged[-1][2] and r[3] == merged[-1][3] and (r[0] - merged[-1][1]).days < 400:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))
    return merged


def dedupe_phases(rows, gap_days=1100):
    """Saturn's retrograde causes 12->1->12->1 flip-flops. Collapse each phase of each spell into one
    row from its first entry to its last exit, then clip overlaps so phases read in order."""
    groups = []  # each: [start, end, tag, house]
    for s0, s1, tag, h in rows:
        hit = None
        for g in reversed(groups):
            if g[2] == tag and g[3] == h and (s0 - g[1]).days < gap_days:
                hit = g
                break
        if hit:
            hit[1] = max(hit[1], s1)
        else:
            groups.append([s0, s1, tag, h])
    groups.sort(key=lambda r: r[0])
    for i in range(len(groups) - 1):
        if groups[i][1] > groups[i + 1][0]:
            groups[i][1] = groups[i + 1][0]
    return [g for g in groups if (g[1] - g[0]).days > 60]


def merge_spells(rows):
    """Collapse consecutive phases of the same spell (12->1->2) into one row, for summary tables."""
    out = []
    for s0, s1, tag, h in rows:
        if out and out[-1][2] == tag and (s0 - out[-1][1]).days < 400:
            out[-1][1] = s1
        else:
            out.append([s0, s1, tag, h])
    return out


def time_sensitivity(a, span_min=20, step_min=2):
    """Which parts of the chart survive a wobble in the recorded birth time.
    Mirrors the engine's --time-scan, but returns the verdict instead of a wall of rows."""
    base = datetime.strptime(f"{a.date} {a.time}", "%Y-%m-%d %H:%M")
    keys = ["La", "D9", "D10", "D60", "D24", "nak"]
    seen = {k: set() for k in keys}
    for off in range(-span_min, span_min + 1, step_min):
        jd, _ = jc.to_jd_ut(base + timedelta(minutes=off), a.tz)
        pos, _ = jc.compute_positions(jd)
        lag = jc.compute_lagna(jd, a.lat, a.lon)
        seen["La"].add(jc.sign_of(lag))
        for dv in (9, 10, 60, 24):
            seen[f"D{dv}"].add(jc.varga_sign(lag, dv))
        n, pd_, _ = jc.nakshatra_of(pos["Mo"]["lon"])
        seen["nak"].add((n, pd_))
    label = {"La": "ලග්නය (D1)", "D9": "නවාංශක ලග්නය (D9)", "D10": "දශාංශක ලග්නය (D10)",
             "D24": "චතුර්විංශාංශ ලග්නය (D24)", "D60": "ෂෂ්ටියාංශ ලග්නය (D60)",
             "nak": "චන්ද්‍ර නැකත සහ පාදය"}
    stable = [label[k] for k in keys if len(seen[k]) == 1]
    shifts = [(label[k], len(seen[k])) for k in keys if len(seen[k]) > 1]
    return span_min, stable, shifts


def time_sensitivity_html(a):
    span, stable, shifts = time_sensitivity(a)
    rows = "".join(f"<tr><td>{esc(n)}</td><td>✓ ස්ථිරයි</td></tr>" for n in stable)
    rows += "".join(f"<tr><td>{esc(n)}</td><td>⚠ මේ පරාසය තුළ විකල්ප {c}ක්</td></tr>" for n, c in shifts)
    return ('<h3>උපන් වේලාවේ සංවේදීතාව</h3>'
            f'<p class="small">වාර්තා කළ වේලාවෙන් ±මිනිත්තු {span}ක් ඇතුළත කේන්දරය නැවත ගණනය කර, '
            'කුමන කොටස් වෙනස් නොවී පවතීද යන්න පරීක්ෂා කර ඇත. ස්ථිර අංග දෘඪ ලෙස කියවිය හැක; '
            'වෙනස් වන අංග උපන් වේලාව හරියටම දන්නේ නම් මිස සැහැල්ලුවෙන් කියවිය යුතුය.</p>'
            f'<table><tr><th style="width:52%">අංගය</th><th>තත්ත්වය</th></tr>{rows}</table>')


def mangal_dosha_html(d):
    """Kuja from Lagna / Chandra / Shukra — the three references the tradition uses."""
    P = d["planets"]
    ls, ma = d["lagna"]["sign_idx"], P["Ma"]["sign_idx"]
    refs = [("ලග්නය", ls), ("චන්ද්‍රයා", P["Mo"]["sign_idx"]), ("ශුක්‍ර", P["Ve"]["sign_idx"])]
    hot = (1, 2, 4, 7, 8, 12)
    rows, flagged = "", []
    for nm, ref in refs:
        h = jc.house_from(ref, ma)
        bad = h in hot
        if bad:
            flagged.append(nm)
        rows += (f"<tr><td>{esc(nm)}</td><td>{h} වැන්නේ</td>"
                 f"<td>{'⚠ දෝෂ ලකුණක්' if bad else '— නැත'}</td></tr>")
    if not flagged:
        verdict = "කුජ දෝෂයක් පෙන්නුම් නොකරයි."
    elif "ලග්නය" in flagged:
        verdict = ("ලග්නයෙන් දෝෂ ලකුණක් ඇති බැවින් පොරොන්දම් බලන විට "
                   "අවලංගු වීමේ (cancellation) නීති පරීක්ෂා කළ යුතුය.")
    else:
        verdict = (f"ලග්නයෙන් දෝෂයක් නැත; {', '.join(flagged)} අනුව පමණක් ලකුණක් ඇත — "
                   "එබැවින් මෘදු ලෙස සලකනු ලැබේ. පොරොන්දම් අවස්ථාවකදී තහවුරු කර ගන්න.")
    return ('<h3>කුජ (මංගල) දෝෂය</h3>'
            '<p class="small">කුජ ලග්නය, චන්ද්‍රයා සහ ශුක්‍ර යන තිදෙනාගෙන් 1, 2, 4, 7, 8, 12 '
            'භාවවල පිහිටීම සලකා බලයි.</p>'
            f'<table><tr><th style="width:34%">ගණන් ගන්නේ</th><th>කුජ</th><th>තත්ත්වය</th></tr>{rows}</table>'
            f'<p class="small">{esc(verdict)}</p>')


def build_a2(d, a, tr, changes, notes, now_local, deep=False):
    """A2 (standard) and A3 (deep, deep=True). Extends the A1 structure."""
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    tz = a.tz
    lord = jc.SIGN_LORD[ls]
    moon = P["Mo"]
    inv = {s: i for i, s in enumerate(jc.SIGNS)}
    approx = a.time_exact != "yes"
    code = "A3" if deep else "A2"
    title = "සම්පූර්ණ කේන්දර විග්‍රහය (A2)" if not deep else "ගැඹුරු කේන්දර විග්‍රහය (A3)"
    labels = {ls: ["ලග්න"]}
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        labels.setdefault(P[c]["sign_idx"], []).append(PLANET_SI[c] + (" (ව)" if P[c]["retro"] and c not in ("Ra", "Ke") else ""))
    H = [f'''<div class="cover" style="padding-top:12mm"><div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">ජන්ම කේන්දර වාර්තාව</h1><div class="sub">{title}</div>
      <div class="name">{esc(a.name)}</div>
      <div class="muted">{esc(a.date)} · {esc(a.time)} · {esc(a.place or "")}</div>
      <div style="margin:14pt auto 0 auto; width:112mm">{south_indian_html_si(labels, "D1 · රාශි චක්‍රය", 112)}</div>
      <p class="muted" style="margin-top:10pt; font-size:8.5pt">පරාශර සහ ජෛමිනි සම්ප්‍රදාය · ලාහිරි අයනාංශය · සම්පූර්ණ රාශි භාව ක්‍රමය · Swiss Ephemeris</p></div>''']

    # ---- 1 summary
    now_utc = now_local.astimezone(timezone.utc)
    def cur(lst):
        for x in lst:
            if datetime.fromisoformat(x["start"]) <= now_utc < datetime.fromisoformat(x["end"]):
                return x
        return None
    vim = d["vimshottari"]
    md = cur(vim["mahadashas"])
    ad = cur(md["sub"]) if md and md.get("sub") else None
    pd_ = cur(ad["sub"]) if ad and ad.get("sub") else None
    H.append('<div class="pb"></div><h2>1. සාරාංශය</h2>')
    H.append(f'<div class="box">{SIGN_SI[ls]} ලග්නය; ලග්නාධිපති {PLANET_SI[lord]} {P[lord]["house"]} වැන්නේ. '
             f'චන්ද්‍ර {SIGN_SI[moon["sign_idx"]]} ({NAK_SI[jc.NAKSHATRAS.index(moon["nakshatra"])]}), {moon["house"]} වැන්නේ. '
             + (f'වත්මන් දශාව {PLANET_SI[md["lord"]]}' + (f"/{PLANET_SI[ad['lord']]}" if ad else "") + ". " if md else "")
             + f'ශනි ගෝචරය: {tr["sade_sati"]}.</div>')
    H.append(note_block(notes, "summary"))
    if approx:
        H.append('<div class="note"><div class="lbl">උපන් වේලාව ගැන</div><p>උපන් වේලාව ආසන්න බැවින් D1, දශා සහ ගෝචරය ප්‍රමුඛ කර ඇත; '
                 'සියුම් වර්ග (D9, D10, D24, D60) ලග්න මිනිත්තු කිහිපයකින් වෙනස් විය හැක. නිශ්චිත වේලාවක් සොයා ගැනීමට E1 (ජන්ම කාල ශුද්ධි) වාර්තාව උපකාරී වේ.</p></div>')
    birth_rows = [("නම", a.name), ("උපන් දිනය", a.date), ("උපන් වේලාව", f"{a.time} ({'නිශ්චිත' if not approx else 'ආසන්න'})"),
                  ("ස්ථානය", a.place or "—"), ("අක්ෂාංශ / දේශාංශ", f"{a.lat:.4f}° N, {a.lon:.4f}° E"),
                  ("කාල කලාපය", f"{a.tz} (UTC{d['birth']['utc_offset']})"), ("අයනාංශය", f"ලාහිරි {dms(d['ayanamsa'])}"),
                  ("පංචාංගය", f"{pch_si(d['panchanga'])['vara']} · {pch_si(d['panchanga'])['tithi']} · {pch_si(d['panchanga'])['yoga']} යෝග · {pch_si(d['panchanga'])['karana']} කරණ · හිරු උදාව {d['panchanga']['sunrise']}"),
                  ("වාර්තා දිනය", now_local.strftime("%Y-%m-%d"))]
    H.append("<h2>2. උපන් දත්ත</h2><table>" + "".join(f"<tr><td style='width:34%'><b>{k}</b></td><td>{esc(v)}</td></tr>" for k, v in birth_rows) + "</table>")

    # ---- 3 planets
    H.append(time_sensitivity_html(a))
    H.append("<h2>3. ග්‍රහ ස්ථාන (D1)</h2>")
    prow = []
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        p = P[c]
        prow.append(f"<tr><td>{PLANET_SI[c]}</td><td>{SIGN_SI[p['sign_idx']]}</td><td>{dms(p['deg_in_sign'])}</td><td>{p['house']}</td>"
                    f"<td>{NAK_SI[jc.NAKSHATRAS.index(p['nakshatra'])]} {p['pada']}</td>"
                    f"<td>{'වක්‍ර ' if p['retro'] and c not in ('Ra', 'Ke') else ''}{'අස්තංගත ' if p.get('combust') else ''}{si_dignity(p['dignity']) if si_dignity(p['dignity']) != '—' else ''}</td>"
                    f"<td>{PLANET_NATURE_SI[c].split(',')[0] if c in PLANET_NATURE_SI else ''}</td></tr>")
    H.append("<table><tr><th>ග්‍රහයා</th><th>රාශිය</th><th>අංශක</th><th>භාවය</th><th>නැකත</th><th>තත්ත්වය</th><th>කාරකත්වය</th></tr>" + "".join(prow) + "</table>")
    sl = d.get("special_lagnas", {})
    if sl:
        H.append("<p class='small'><b>විශේෂ ලග්න:</b> " + " · ".join(
            f"{k} {SIGN_SI[inv[v['sign']]]}" for k, v in sl.items() if isinstance(v, dict)) + "</p>")
    H.append(note_block(notes, "lagna"))

    # ---- 4 Jaimini
    kk, ar = d["chara_karakas"], d["arudhas"]
    H.append("<h2>4. ජෛමිනි ස්තරය</h2><table><tr><th>කාරකය</th><th>ග්‍රහයා</th><th>භාවය</th><th>අර්ථය</th></tr>")
    KAR_SI = {"AK": ("ආත්මකාරක", "ආත්මයේ ගමන් මග"), "AmK": ("අමාත්‍යකාරක", "වෘත්තිය, උපදේශක"), "BK": ("භ්‍රාතෘකාරක", "සහෝදරයන්, ගුරු"),
              "MK": ("මාතෘකාරක", "මව, රැකවරණය"), "PiK": ("පිතෘකාරක", "පියා"), "PK": ("පුත්‍රකාරක", "දරුවන්, බුද්ධිය"),
              "GK": ("ඥාතිකාරක", "ඥාතීන්, අභියෝග"), "DK": ("දාරාකාරක", "සහකරු")}
    for k, v in kk.items():
        si = KAR_SI.get(k, (k, ""))
        H.append(f"<tr><td>{si[0]} ({k})</td><td>{PLANET_SI[v['planet']]}</td><td>{P[v['planet']]['house']}</td><td>{si[1]}</td></tr>")
    H.append("</table>")
    H.append("<table><tr><th>ආරූඪය</th><th>රාශිය</th><th>ලග්නයෙන් භාවය</th></tr>"
             + "".join(f"<tr><td>{k}</td><td>{SIGN_SI[inv[v]]}</td><td>{jc.house_from(ls, inv[v])}</td></tr>"
                       for k, v in ar.items() if (deep or k in ("AL", "UL", "A7", "A10"))) + "</table>")
    H.append('<p class="small muted">AL = සමාජය ඔබ දකින ආකාරය · UL = සහකරු/විවාහ ආරූඪය · A10 = රැකියාව පිළිබඳ ආරූඪය.</p>')

    # ---- 5 vargas
    H.append('<h2 class="sec">5. වර්ග කේන්දර</h2>')
    show_v = ["D9", "D10"] if not deep else [v for v in ["D9", "D10", "D2", "D4", "D7", "D12", "D24", "D60"] if v in d["vargas"]]
    for i, vname in enumerate(show_v):
        v = d["vargas"].get(vname)
        if not v:
            continue
        vl = inv[v["La"]]
        vlab = {vl: ["ලග්න"]}
        for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
            vlab.setdefault(inv[v[c]], []).append(PLANET_SI[c])
        nm, purpose = VARGA_SI.get(vname, (vname, ""))
        H.append(f'<div class="two vblock" style="margin-bottom:8pt"><div style="flex:0 0 76mm">{south_indian_html_si(vlab, f"{vname} · {nm}", 76)}</div>'
                 f'<div><p class="small"><b>{vname} — {nm}</b>: {purpose}. ලග්නය {SIGN_SI[vl]}; අධිපති {PLANET_SI[jc.SIGN_LORD[vl]]} '
                 f'එම කේන්දරයේ {jc.house_from(vl, inv[v[jc.SIGN_LORD[vl]]])} වැන්නේ.'
                 + (f' වර්ගෝත්තම: {", ".join(PLANET_SI.get(x, x) for x in d.get("vargottama", []))}.' if vname == "D9" and d.get("vargottama") else "")
                 + "</p></div></div>")

    # ---- 6 yogas
    H.append('<h2 class="sec">6. යෝග සහ දෝෂ</h2>')
    yf = d.get("yogas_full")
    if yf and deep:
        cat = None
        H.append("<table><tr><th style='width:22%'>වර්ගය</th><th style='width:26%'>යෝගය</th><th>විස්තරය</th></tr>")
        for y in yf:
            csi = YOGA_CAT_SI.get(y["category"], y["category"])
            H.append(f"<tr><td>{csi if csi != cat else ''}</td><td>{esc(si_yoga_name(y['name']))}</td><td>{esc(si_text(y['detail']))}</td></tr>")
            cat = csi
        H.append("</table>")
    else:
        yl = []
        for y in d.get("yoga_indications", []):
            key = next((k for k in YOGA_SI if k.lower() in y.lower()), None)
            yl.append(f"<li><b>{esc(YOGA_SI[key].split(' — ')[0]) if key else esc(y)}</b>"
                      + (f" — {esc(YOGA_SI[key].split(' — ', 1)[1])}" if key and " — " in YOGA_SI[key] else "")
                      + f' <span class="muted">({esc(y)})</span></li>')
        for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]:
            dg = si_dignity(P[c]["dignity"])
            if "උච්ච" in dg or "නීච" in dg:
                yl.append(f"<li>{PLANET_SI[c]} {dg} ({SIGN_SI[P[c]['sign_idx']]}, {P[c]['house']} වැන්න) — {PLANET_NATURE_SI[c]}</li>")
        H.append("<ul>" + ("".join(yl) or "<li>ප්‍රධාන යෝග/දෝෂ ඇඟවීම් නැත.</li>") + "</ul>")
    H.append(mangal_dosha_html(d))
    H.append(note_block(notes, "yogas"))

    # ---- 7 Ashtakavarga
    av = d.get("ashtakavarga")
    if av:
        H.append("<h2>7. අෂ්ටකවර්ග</h2>")
        sav = av["sav"]
        H.append("<table><tr><th>රාශිය</th>" + "".join(f"<th>{SIGN_SI[i][:3]}</th>" for i in range(12)) + "</tr>")
        if deep:
            for p, row in av["bav"].items():
                H.append(f"<tr><td>{PLANET_SI[p]}</td>" + "".join(f"<td>{x}</td>" for x in row) + "</tr>")
        H.append("<tr class='cur'><td><b>SAV</b></td>" + "".join(f"<td><b>{x}</b></td>" for x in sav) + "</tr></table>")
        best = sorted(range(12), key=lambda i: -sav[i])[:3]
        worst = sorted(range(12), key=lambda i: sav[i])[:3]
        H.append(f"<p class='small'>ශක්තිමත්ම රාශි: {', '.join(f'{SIGN_SI[i]} ({sav[i]}, {jc.house_from(ls, i)} වැන්න)' for i in best)}. "
                 f"අඩුම: {', '.join(f'{SIGN_SI[i]} ({sav[i]})' for i in worst)}. "
                 "ග්‍රහයෙක් බින්දු වැඩි රාශියක් ගෝචරයෙන් යන විට ප්‍රතිඵල හිතකර වීමේ ප්‍රවණතාවක් ඇත (28 ට වැඩි = හොඳ).</p>")

    # ---- 8 argala / upagrahas (A3)
    if deep:
        H.append('<h2>8. අර්ගල සහ උපග්‍රහ</h2>')
        arg = d.get("argala", {})
        rows = []
        for h in range(1, 13):
            g = arg.get(str(h)) or arg.get(h)
            if not g:
                continue
            sub = ", ".join(PLANET_SI[p] for p, _ in g["subha"]) or "—"
            pap = ", ".join(PLANET_SI[p] for p, _ in g["papa"]) or "—"
            vir = ", ".join(PLANET_SI[p] for p, _, _b in g["virodha"]) or "—"
            rows.append(f"<tr><td>{h}</td><td>{HOUSE_SI[h].split(',')[0]}</td><td>{sub}</td><td>{pap}</td><td>{vir}</td></tr>")
        H.append("<table><tr><th>භාවය</th><th>කාරණය</th><th>ශුභ අර්ගල</th><th>පාප අර්ගල</th><th>විරෝධාර්ගල</th></tr>" + "".join(rows) + "</table>")
        H.append('<p class="small muted">අර්ගල = භාවයකට බාහිරින් එන ආධාරය/බාධාව (2, 4, 11 වැනි ස්ථානවලින්); විරෝධාර්ගල ඒවා අවහිර කරයි.</p>')
        up = d.get("upagrahas", {})
        if up:
            H.append("<h3>උපග්‍රහ</h3><table><tr><th>උපග්‍රහයා</th><th>රාශිය</th><th>අංශක</th><th>භාවය</th></tr>"
                     + "".join(f"<tr><td>{UPAGRAHA_SI.get(k, k)}</td><td>{SIGN_SI[jc.sign_of(v)]}</td><td>{dms(v % 30)}</td>"
                               f"<td>{jc.house_from(ls, jc.sign_of(v))}</td></tr>" for k, v in up.items()) + "</table>")
            H.append('<p class="small muted">උපග්‍රහ පාප ලක්ෂ්‍ය ලෙස සැලකේ; ගුලික/මාන්දි ශනි හා සමාන ස්වභාවයක් දරයි.</p>')

    # ---- 9 life areas
    H.append('<h2 style="page-break-before:auto">' + ("9" if deep else "8") + '. ජීවන ක්ෂේත්‍ර</h2>')
    for k in ["career", "marriage", "wealth", "education", "family"]:
        t, para = area_paragraph(d, k)
        H.append(f"<h3>{t}</h3><p>{para}</p>")
    H.append(note_block(notes, "areas") or note_block(notes, "lagna2"))

    # ---- 10 dashas
    n = "10" if deep else "9"
    H.append(f'<h2 class="sec">{n}. දශා</h2>')
    if md:
        L = md["lord"]
        H.append(f'<p>වත්මන් මහා දශාව <b>{PLANET_SI[L]}</b> ({fmt_date(md["start"], tz)} – {fmt_date(md["end"], tz)}): {PLANET_NATURE_SI[L]}; '
                 f'ජන්ම කේන්දරයේ {SIGN_SI[P[L]["sign_idx"]]} රාශියේ {P[L]["house"]} වැන්නේ ({HOUSE_SI[P[L]["house"]]}).'
                 + (f' වත්මන් අන්තර් දශාව <b>{PLANET_SI[ad["lord"]]}</b> ({fmt_date(ad["start"], tz)} – {fmt_date(ad["end"], tz)})'
                    f' — {P[ad["lord"]]["house"]} වැන්න.' if ad else "")
                 + (f' ප්‍රත්‍යන්තර {PLANET_SI[pd_["lord"]]} ({fmt_date(pd_["start"], tz)} – {fmt_date(pd_["end"], tz)}).' if pd_ else "") + "</p>")
    horizon = now_utc + timedelta(days=int((10 if deep else 5) * 365.25))
    rows = []
    for m in vim["mahadashas"]:
        for s_ in m.get("sub", []):
            st, en = datetime.fromisoformat(s_["start"]), datetime.fromisoformat(s_["end"])
            if en > now_utc and st < horizon:
                tone = "හිතකර" if P[s_["lord"]]["house"] in (1, 2, 4, 5, 7, 9, 10, 11) and "නීච" not in si_dignity(P[s_["lord"]]["dignity"]) else "අවධානය"
                rows.append(f"<tr{' class=cur' if st <= now_utc < en else ''}><td>{PLANET_SI[m['lord']]}/{PLANET_SI[s_['lord']]}</td>"
                            f"<td>{st.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</td><td>{en.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</td>"
                            f"<td>{PLANET_SI[s_['lord']]} {P[s_['lord']]['house']} වැන්නේ — {HOUSE_SI[P[s_['lord']]['house']].split(',')[0]} ({tone})</td></tr>")
    H.append(f"<h3>ඉදිරි වසර {10 if deep else 5} — අන්තර් දශා</h3><table><tr><th>දශාව</th><th>ආරම්භය</th><th>අවසානය</th><th>ප්‍රවණතාව</th></tr>" + "".join(rows) + "</table>")
    H.append("<h3>මහා දශා අනුපිළිවෙල</h3><table><tr><th>දශාව</th><th>ආරම්භය</th><th>අවසානය</th></tr>"
             + "".join(f"<tr{' class=cur' if md and m['lord'] == md['lord'] else ''}><td>{PLANET_SI[m['lord']]}</td>"
                       f"<td>{fmt_date(m['start'], tz)}</td><td>{fmt_date(m['end'], tz)}</td></tr>" for m in vim["mahadashas"]) + "</table>")
    nd = d.get("narayana_dasa")
    if nd:
        cur_nd = next((x for x in nd if datetime.fromisoformat(x["start"]) <= now_utc < datetime.fromisoformat(x["end"])), None)
        H.append("<h3>නාරායණ දශා (රාශි දශා — තහවුරු කිරීමේ මෙවලම)</h3><table><tr><th>රාශිය</th><th>ආරම්භය</th><th>අවසානය</th><th>ලග්නයෙන් භාවය</th></tr>"
                 + "".join(f"<tr{' class=cur' if cur_nd and x is cur_nd else ''}><td>{SIGN_SI[inv[x['sign']]]}</td>"
                           f"<td>{fmt_date(x['start'], tz)}</td><td>{fmt_date(x['end'], tz)}</td><td>{jc.house_from(ls, inv[x['sign']])}</td></tr>"
                           for x in [y for y in nd if datetime.fromisoformat(y["end"]) > now_utc - timedelta(days=1825)][:14]) + "</table>")
    if deep and d.get("kalachakra"):
        kc = d["kalachakra"]
        H.append(f"<h3>කාලචක්‍ර දශා</h3><p class='small'>චන්ද්‍ර {NAK_SI[jc.NAKSHATRAS.index(kc['nakshatra'])]} නැකතේ {kc['pada']} වන පාදයේ; "
                 f"දේහ රාශිය {SIGN_SI[inv[kc['deha']]]}, ජීව රාශිය {SIGN_SI[inv[kc['jeeva']]]}.</p>"
                 "<table><tr><th>රාශිය</th><th>ආරම්භය</th><th>අවසානය</th></tr>"
                 + "".join(f"<tr{' class=cur' if datetime.fromisoformat(x['start']) <= now_utc < datetime.fromisoformat(x['end']) else ''}>"
                           f"<td>{SIGN_SI[inv[x['sign']]]}</td><td>{fmt_date(x['start'], tz)}</td><td>{fmt_date(x['end'], tz)}</td></tr>"
                           for x in kc["dasas"][:8]) + "</table>")
    H.append(note_block(notes, "dasha"))

    # ---- 11 gochara
    n2 = "11" if deep else "10"
    H.append(f'<h2>{n2}. ගෝචරය</h2>')
    sa, ju, ra = tr["Sa"], tr["Ju"], tr["Ra"]
    H.append(f'<p class="small muted">{now_local.strftime("%Y-%m-%d")} දිනට</p><ul>'
             f'<li><b>ශනි</b> {SIGN_SI[sa["sign"]]}{" (වක්‍ර)" if sa["retro"] else ""} — චන්ද්‍රගෙන් {sa["from_moon"]}, ලග්නයෙන් {sa["from_lagna"]}: {SATURN_FROM_MOON_SI[sa["from_moon"]]}</li>'
             f'<li><b>ගුරු</b> {SIGN_SI[ju["sign"]]}{" (වක්‍ර)" if ju["retro"] else ""} — චන්ද්‍රගෙන් {ju["from_moon"]}, ලග්නයෙන් {ju["from_lagna"]}: {JUPITER_FROM_MOON_SI[ju["from_moon"]]}</li>'
             f'<li><b>රාහු–කේතු</b> {SIGN_SI[ra["sign"]]}–{SIGN_SI[(ra["sign"] + 6) % 12]} — ලග්නයෙන් {ra["from_lagna"]}/{(ra["from_lagna"] + 5) % 12 + 1} වැනි භාව</li>'
             f'<li><b>සඩේ සති / ධයියා</b>: {tr["sade_sati"]}</li></ul>')
    if av:
        sav = av["sav"]
        H.append("<p class='small'><b>අෂ්ටකවර්ග බින්දු ගෝචර ග්‍රහයන්ට:</b> "
                 + " · ".join(f"{PLANET_SI[c]} {SIGN_SI[tr[c]['sign']]} = {sav[tr[c]['sign']]}" for c in ["Sa", "Ju"]) + " (SAV)</p>")
    if changes:
        H.append(f"<h3>ඉදිරි වසර {3 if not deep else 5} — රාශි මාරු</h3><table><tr><th>දිනය</th><th>ග්‍රහයා</th><th>නව රාශිය</th><th>භාවය</th><th>ප්‍රවණතාව</th></tr>"
                 + "".join(f"<tr><td>{dt.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}"
                           + (f"<br><span class=muted>ස්ථිර {st.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</span>" if (st - dt).days > 20 else "")
                           + f"</td><td>{PLANET_SI[p]}</td><td>{SIGN_SI[s_]}</td>"
                           f"<td>චන්ද්‍රගෙන් {jc.house_from(moon['sign_idx'], s_)}, ලග්නයෙන් {jc.house_from(ls, s_)}</td>"
                           f"<td>{SATURN_FROM_MOON_SI[jc.house_from(moon['sign_idx'], s_)] if p == 'Sa' else JUPITER_FROM_MOON_SI[jc.house_from(moon['sign_idx'], s_)] if p == 'Ju' else HOUSE_SI[jc.house_from(ls, s_)].split(',')[0] + ' ක්ෂේත්‍රයට රාහු'}</td></tr>"
                           for dt, p, s_, st in changes) + "</table>")
    ss = merge_spells(sade_sati_timeline(moon["sign_idx"], now_utc - timedelta(days=365 * 3), 18 if deep else 12))
    if ss:
        H.append("<h3>සඩේ සති / ධයියා කාල රේඛාව</h3><table><tr><th>වර්ගය</th><th>ආරම්භය</th><th>අවසානය</th><th>භාවය (චන්ද්‍රගෙන්)</th></tr>"
                 + "".join(f"<tr{' class=cur' if s0 <= now_utc <= s1 else ''}><td>{tag}</td>"
                           f"<td>{s0.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</td><td>{s1.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</td><td>{h}</td></tr>"
                           for s0, s1, tag, h in ss) + "</table>")
        H.append('<p class="small muted">සඩේ සති = ශනි චන්ද්‍රගෙන් 12, 1, 2 වැනි රාශිවලින් යන කාලය (වසර ~7½); ධයියා = 4 හෝ 8 වැන්නෙන් යන කාලය (~2½). '
                 'මේවා බියවිය යුතු කාල නොව, වගකීම් සහ පරිණතභාවය වැඩෙන කාල ලෙස සලකනු ලැබේ.</p>')
    H.append(note_block(notes, "gochara"))

    # ---- 12 convergence
    n3 = "12" if deep else "11"
    H.append(f'<h2>{n3}. ඉදිරි කාලය — සම්මුඛ වන කවුළු</h2>')
    win = []
    for m in vim["mahadashas"]:
        for s_ in m.get("sub", []):
            st, en = datetime.fromisoformat(s_["start"]), datetime.fromisoformat(s_["end"])
            if en > now_utc and st < horizon:
                h = P[s_["lord"]]["house"]
                tone = "හිතකර" if h in (1, 2, 4, 5, 7, 9, 10, 11) else "අවධානය යොමු කළ යුතු"
                win.append((max(st, now_utc), f"<li><b>{max(st, now_utc).astimezone(ZoneInfo(tz)).strftime('%Y-%m')} → {en.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</b> — "
                                              f"{PLANET_SI[m['lord']]}/{PLANET_SI[s_['lord']]}: {HOUSE_SI[h].split(',')[0]} ({tone})</li>"))
    for dt, p, s_, st in changes:
        win.append((dt, f"<li><b>{dt.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</b> — {PLANET_SI[p]} {SIGN_SI[s_]} රාශියට: ගෝචර වෙනස</li>"))
    for s0, s1, tag, h in ss:
        if s1 > now_utc:
            win.append((s0, f"<li><b>{s0.astimezone(ZoneInfo(tz)).strftime('%Y-%m')} → {s1.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</b> — {tag}</li>"))
    H.append("<ul>" + "".join(x for _, x in sorted(win, key=lambda t: t[0])) + "</ul>")
    H.append('<p class="small">දශාව, ගෝචරය සහ වාර්ෂික චක්‍රය එකට ගැලපෙන කවුළු වඩාත් වැදගත්; තනි ඇඟවීමක් මත තීරණ නොගන්න.</p>')
    H.append(note_block(notes, "upcoming"))
    if (notes or {}).get("remedies"):
        H.append("<h2>යෝජනා</h2>" + note_block(notes, "remedies", "ප්‍රතිකර්ම / ආකල්ප යෝජනා"))
    H.append(disclaimer_block(f"පරාශර හෝරා ශාස්ත්‍රය සහ ජෛමිනි සම්ප්‍රදාය; P.V.R. Narasimha Rao ගේ Vedic Astrology: An Integrated Approach ප්‍රධාන යොමුව. "
                              f"වාර්තා වර්ගය {code}. විම්ශෝත්තරී දශා සෞර වර්ෂ අනුව."))
    return "\n".join(H)


# ================================================================ B series — life-area reports
# spec: (code, Sinhala title, subtitle, main house, support houses, main varga, extra vargas,
#        karaka planet, chara karakas, arudha, matter house for Tajaka, notes key set)
B_SPECS = {
    "B1": dict(title="විවාහ විග්‍රහය", sub="විවාහය සහ සහකරු (B1)", house=7, support=[2, 8, 12, 4],
               varga="D9", extra=["D9"], karaka="Ve", ck=["DK"], arudha="UL", matter=7,
               intro="විවාහය, සහකරු සහ දිගු කාලීන සම්බන්ධතා පිළිබඳ ප්‍රවණතා. 7 වන භාවය, එහි අධිපති, ශුක්‍ර, උපපද ලග්නය (UL), "
                     "දාරාකාරක (DK) සහ නවාංශකය (D9) එකට කියවීමෙන් මේ ක්ෂේත්‍රයේ රටාව පෙනේ.",
               timing="විවාහ කාලය සාමාන්‍යයෙන් 7 වන භාවය/අධිපති, UL, DK හෝ ශුක්‍ර සම්බන්ධ දශා කාලවලදී, "
                      "ගුරු ගෝචරයෙන් 7 වැන්නට හෝ චන්ද්‍රගෙන් හිතකර ස්ථානයකට පැමිණෙන විට කැපී පෙනේ."),
    "B2": dict(title="වෘත්තීය විග්‍රහය", sub="රැකියාව සහ ව්‍යාපාරය (B2)", house=10, support=[1, 2, 6, 11, 7],
               varga="D10", extra=["D10"], karaka="Sa", ck=["AmK"], arudha="A10", matter=10,
               intro="රැකියාව, ව්‍යාපාරය සහ සමාජ තත්ත්වය පිළිබඳ ප්‍රවණතා. 10 වන භාවය, එහි අධිපති, ශනි (කර්ම කාරකයා), "
                     "අමාත්‍යකාරක (AmK), A10 ආරූඪය සහ දශාංශකය (D10) ප්‍රධාන මෙවලම්.",
               timing="රැකියා වෙනස්කම් 10, 6, 11 භාවාධිපතීන්ගේ දශා කාලවලදී සහ ශනි/ගුරු ගෝචරයෙන් 10 වැන්නට හෝ "
                      "ලග්නයට පැමිණෙන කාලවලදී කැපී පෙනේ."),
    "B3": dict(title="අධ්‍යාපන විග්‍රහය", sub="ඉගෙනීම සහ විභාග (B3)", house=4, support=[2, 5, 9, 11],
               varga="D24", extra=["D24"], karaka="Me", ck=["AK"], arudha="A4", matter=4,
               intro="අධ්‍යාපනය, විෂය ප්‍රවණතාව සහ උසස් අධ්‍යාපනය. 4 වන (මූලික අධ්‍යාපනය), 5 වන (බුද්ධිය), "
                     "9 වන (උසස් අධ්‍යාපනය) භාව, බුධ, ගුරු සහ චතුර්විංශාංශකය (D24).",
               timing="විභාග සහ අධ්‍යාපන පියවර 4, 5, 9 භාවාධිපතීන්ගේ සහ බුධ/ගුරු දශා කාලවලදී කැපී පෙනේ."),
    "B4": dict(title="ධන විග්‍රහය", sub="ධනය සහ ආදායම (B4)", house=2, support=[5, 9, 11, 6, 12],
               varga="D2", extra=["D2"], karaka="Ju", ck=["AmK"], arudha="A2", matter=2,
               intro="ආදායම් මාර්ග, ඉතිරි කිරීම සහ මූල්‍ය රටාව. 2 වන (ධනය), 11 වන (ලාභ), 5/9 (පූර්ව පුණ්‍ය) භාව, "
                     "ගුරු, හෝරා කේන්දරය (D2) සහ ධන යෝග.",
               timing="ධන යෝගවලට සම්බන්ධ ග්‍රහයන්ගේ දශා කාල මූල්‍ය වශයෙන් කැපී පෙනේ. "
                      "මෙය ආයෝජන උපදෙස් නොවේ — මූල්‍ය තීරණවලට සුදුසුකම් ලත් උපදේශකයෙකු හමුවන්න."),
    "B5": dict(title="සන්තාන විග්‍රහය", sub="දරුවන් (B5)", house=5, support=[2, 9, 11, 7],
               varga="D7", extra=["D7"], karaka="Ju", ck=["PK"], arudha="A5", matter=5,
               intro="දරුවන් පිළිබඳ ප්‍රවණතා. 5 වන භාවය, එහි අධිපති, ගුරු, පුත්‍රකාරක (PK) සහ සප්තාංශකය (D7). "
                     "මෙය වෛද්‍ය තොරතුරු නොවේ; සෞඛ්‍ය කාරණා සඳහා වෛද්‍යවරයෙකු හමුවන්න.",
               timing="5 වන භාවය, එහි අධිපති හෝ ගුරු සම්බන්ධ දශා කාල සහ ගුරු ගෝචරයෙන් 5 වැන්නට පැමිණෙන කාල."),
    "B6": dict(title="විදේශ විග්‍රහය", sub="විදේශ ගමන් සහ පදිංචිය (B6)", house=12, support=[3, 7, 9, 4],
               varga="D4", extra=["D4"], karaka="Ra", ck=["AK"], arudha="A12", matter=12,
               intro="විදේශ ගමන්, අධ්‍යාපනය හෝ පදිංචිය පිළිබඳ ප්‍රවණතා. 12 වන (විදේශ), 9 වන (දුර ගමන්), "
                     "3 වන (කෙටි ගමන්) භාව, රාහු සහ චතුර්ථාංශකය (D4).",
               timing="12, 9, 3 භාවාධිපතීන්ගේ සහ රාහු දශා කාල; ශනි/ගුරු ගෝචරයෙන් එම භාවවලට පැමිණෙන කාල."),
    "B7": dict(title="දේපල විග්‍රහය", sub="නිවස, ඉඩම් සහ වාහන (B7)", house=4, support=[2, 11, 12, 8],
               varga="D4", extra=["D4"], karaka="Ma", ck=["MK"], arudha="A4", matter=4,
               intro="නිවස, ඉඩම් සහ වාහන පිළිබඳ ප්‍රවණතා. 4 වන භාවය, එහි අධිපති, කුජ (ඉඩම් කාරකයා), "
                     "ශුක්‍ර (වාහන) සහ චතුර්ථාංශකය (D4).",
               timing="4 වන භාවාධිපති, කුජ හෝ ශුක්‍ර සම්බන්ධ දශා කාල; ගුරු ගෝචරයෙන් 4 වැන්නට පැමිණෙන කාල."),
    "B8": dict(title="මාතෘ–පිතෘ විග්‍රහය", sub="දෙමව්පියන් සමඟ සම්බන්ධතාව (B8)", house=4, support=[9, 10, 2, 12],
               varga="D12", extra=["D12"], karaka="Mo", ck=["MK", "PiK"], arudha="A4", matter=4,
               intro="දෙමව්පියන් සමඟ සම්බන්ධතාව සහ ඔවුන්ගෙන් ලැබෙන සහාය පිළිබඳ පොදු ප්‍රවණතා. "
                     "4 වන (මව), 9 වන (පියා) භාව, චන්ද්‍ර, රවි සහ ද්වාදශාංශකය (D12). "
                     "දෙමව්පියන්ගේ ආයුෂ හෝ සෞඛ්‍යය පිළිබඳ අනාවැකි මෙහි ඇතුළත් නොවේ.",
               timing="4, 9 භාවාධිපතීන්ගේ දශා කාල සහ ශනි/ගුරු ගෝචරය එම භාවවලට පැමිණෙන කාල."),
}
KAR_SI_B = {"AK": "ආත්මකාරක", "AmK": "අමාත්‍යකාරක", "BK": "භ්‍රාතෘකාරක", "MK": "මාතෘකාරක", "PiK": "පිතෘකාරක",
            "PK": "පුත්‍රකාරක", "GK": "ඥාතිකාරක", "DK": "දාරාකාරක"}


def build_b(d, a, code, tr, changes, notes, now_local):
    spec = B_SPECS[code]
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    inv = {s: i for i, s in enumerate(jc.SIGNS)}
    tz = a.tz
    h = spec["house"]
    hs = (ls + h - 1) % 12
    hlord = jc.SIGN_LORD[hs]
    kar = spec["karaka"]
    approx = a.time_exact != "yes"
    labels = {ls: ["ලග්න"]}
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        labels.setdefault(P[c]["sign_idx"], []).append(PLANET_SI[c] + (" (ව)" if P[c]["retro"] and c not in ("Ra", "Ke") else ""))
    H = [f'''<div class="cover" style="padding-top:12mm"><div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">{spec["title"]}</h1><div class="sub">{spec["sub"]}</div>
      <div class="name">{esc(a.name)}</div>
      <div class="muted">{esc(a.date)} · {esc(a.time)} · {esc(a.place or "")}</div>
      <div style="margin:14pt auto 0 auto; width:110mm">{south_indian_html_si(labels, "D1 · රාශි චක්‍රය", 110)}</div></div>''']

    H.append('<div class="pb"></div><h2>1. මේ වාර්තාව ගැන</h2>')
    H.append(f'<div class="box">{spec["intro"]}</div>')
    if approx:
        H.append(f'<div class="note"><div class="lbl">උපන් වේලාව</div><p>වේලාව ආසන්න බැවින් {spec["varga"]} වර්ග කේන්දරයේ ලග්නය '
                 'මිනිත්තු කිහිපයකින් වෙනස් විය හැක; D1, දශා සහ ගෝචරය ප්‍රමුඛ කර කියවන්න.</p></div>')
    H.append("<table>"
             f"<tr><td style='width:34%'><b>ලග්නය</b></td><td>{SIGN_SI[ls]} — අධිපති {PLANET_SI[jc.SIGN_LORD[ls]]}, {P[jc.SIGN_LORD[ls]]['house']} වැන්නේ</td></tr>"
             f"<tr><td><b>චන්ද්‍ර</b></td><td>{SIGN_SI[P['Mo']['sign_idx']]} — {P['Mo']['house']} වැන්නේ, {NAK_SI[jc.NAKSHATRAS.index(P['Mo']['nakshatra'])]} නැකත</td></tr>"
             f"<tr><td><b>ප්‍රධාන භාවය</b></td><td>{h} වැන්න ({SIGN_SI[hs]}) — {HOUSE_SI[h]}</td></tr>"
             f"<tr><td><b>වාර්තා දිනය</b></td><td>{now_local.strftime('%Y-%m-%d')}</td></tr></table>")

    # --- 2 core analysis
    H.append(f"<h2>2. {h} වන භාවය සහ එහි අධිපති</h2>")
    occ = [c for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"] if P[c]["sign_idx"] == hs]
    rows = [("භාවය", f"{h} වැන්න — {SIGN_SI[hs]}"),
            ("භාවාධිපති", f"{PLANET_SI[hlord]} — {SIGN_SI[P[hlord]['sign_idx']]} රාශියේ, {P[hlord]['house']} වැන්නේ"
                          + (f", {si_dignity(P[hlord]['dignity'])}" if si_dignity(P[hlord]["dignity"]) != "—" else "")
                          + (", වක්‍ර" if P[hlord]["retro"] and hlord not in ("Ra", "Ke") else "")),
            ("භාවයේ ග්‍රහයන්", ", ".join(f"{PLANET_SI[c]} ({dms(P[c]['deg_in_sign'])})" for c in occ) or "නැත"),
            ("කාරකයා", f"{PLANET_SI[kar]} — {SIGN_SI[P[kar]['sign_idx']]}, {P[kar]['house']} වැන්නේ"
                       + (f", {si_dignity(P[kar]['dignity'])}" if si_dignity(P[kar]["dignity"]) != "—" else ""))]
    for k in spec["ck"]:
        if k in d["chara_karakas"]:
            kp = d["chara_karakas"][k]["planet"]
            rows.append((f"{KAR_SI_B.get(k, k)} ({k})", f"{PLANET_SI[kp]} — {SIGN_SI[P[kp]['sign_idx']]}, {P[kp]['house']} වැන්නේ"))
    ar = d["arudhas"].get(spec["arudha"])
    if ar:
        rows.append((f"ආරූඪය ({spec['arudha']})", f"{SIGN_SI[inv[ar]]} — ලග්නයෙන් {jc.house_from(ls, inv[ar])} වැන්න"))
    H.append("<table>" + "".join(f"<tr><td style='width:30%'><b>{k}</b></td><td>{v}</td></tr>" for k, v in rows) + "</table>")
    good = P[hlord]["house"] in (1, 4, 5, 7, 9, 10, 11) and "නීච" not in si_dignity(P[hlord]["dignity"])
    H.append(f'<div class="box"><b>ප්‍රවණතාව:</b> භාවාධිපති {PLANET_SI[hlord]} {P[hlord]["house"]} වැන්නේ '
             f'({HOUSE_SI[P[hlord]["house"]]}) සිටීම මේ ක්ෂේත්‍රය එම කාරණා සමඟ බැඳෙන බව පෙන්වයි. '
             + ("භාවාධිපති හිතකර ස්ථානයක සිටීම සහායකයි." if good else "ප්‍රතිඵල ශ්‍රමයෙන් සහ ඉවසීමෙන් ලැබෙන ප්‍රවණතාවක් ඇත.")
             + (f' භාවයේ {", ".join(PLANET_SI[c] for c in occ)} සිටීම එම ග්‍රහයන්ගේ ස්වභාවය මේ ක්ෂේත්‍රයට එකතු කරයි.' if occ else "")
             + "</div>")
    sup = []
    for sh in spec["support"]:
        shs = (ls + sh - 1) % 12
        sl = jc.SIGN_LORD[shs]
        sup.append(f"<tr><td>{sh}</td><td>{HOUSE_SI[sh].split(',')[0]}</td><td>{SIGN_SI[shs]}</td><td>{PLANET_SI[sl]} — {P[sl]['house']} වැන්නේ</td>"
                   f"<td>{', '.join(PLANET_SI[c] for c in ['Su', 'Mo', 'Ma', 'Me', 'Ju', 'Ve', 'Sa', 'Ra', 'Ke'] if P[c]['sign_idx'] == shs) or '—'}</td></tr>")
    H.append("<h3>සහායක භාව</h3><table><tr><th>භාවය</th><th>කාරණය</th><th>රාශිය</th><th>අධිපති</th><th>ග්‍රහයන්</th></tr>" + "".join(sup) + "</table>")
    H.append(note_block(notes, "lagna"))

    # --- 3 varga
    v = d["vargas"].get(spec["varga"])
    if v:
        vl = inv[v["La"]]
        vlab = {vl: ["ලග්න"]}
        for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
            vlab.setdefault(inv[v[c]], []).append(PLANET_SI[c])
        nm, purpose = VARGA_SI.get(spec["varga"], (spec["varga"], ""))
        vh = jc.house_from(vl, inv[v[hlord]])
        H.append(f'<div class="pb"></div><h2>3. {spec["varga"]} — {nm} කේන්දරය</h2>')
        H.append(f'<div class="two"><div style="flex:0 0 86mm">{south_indian_html_si(vlab, f'{spec["varga"]} · {nm}' , 86)}</div>'
                 f'<div><p class="small">{purpose}. ලග්නය <b>{SIGN_SI[vl]}</b>; අධිපති {PLANET_SI[jc.SIGN_LORD[vl]]} '
                 f'එම කේන්දරයේ {jc.house_from(vl, inv[v[jc.SIGN_LORD[vl]]])} වැන්නේ. '
                 f'D1 හි {h} වන භාවාධිපති {PLANET_SI[hlord]} මෙහි {vh} වැන්නේ. '
                 + (f'වර්ගෝත්තම ග්‍රහයන්: {", ".join(PLANET_SI.get(x, x) for x in d.get("vargottama", []))}.' if spec["varga"] == "D9" and d.get("vargottama") else "")
                 + "</p></div></div>")
        vrow = []
        for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
            vs = inv[v[c]]
            vrow.append(f"<tr><td>{PLANET_SI[c]}</td><td>{SIGN_SI[vs]}</td><td>{jc.house_from(vl, vs)}</td>"
                        f"<td>{SIGN_SI[P[c]['sign_idx']]} ({P[c]['house']})</td></tr>")
        H.append(f"<table><tr><th>ග්‍රහයා</th><th>{spec['varga']} රාශිය</th><th>{spec['varga']} භාවය</th><th>D1 රාශිය (භාවය)</th></tr>" + "".join(vrow) + "</table>")

    # --- 4 yogas relevant
    H.append("<h2>4. අදාළ යෝග සහ තත්ත්ව</h2><ul>")
    ylist = []
    for y in d.get("yoga_indications", []):
        key = next((k for k in YOGA_SI if k.lower() in y.lower()), None)
        ylist.append(f"<li><b>{YOGA_SI[key].split(' — ')[0] if key else esc(y)}</b>"
                     + (f" — {YOGA_SI[key].split(' — ', 1)[1]}" if key and " — " in YOGA_SI[key] else "") + "</li>")
    for c in [hlord, kar]:
        dg = si_dignity(P[c]["dignity"])
        if dg != "—":
            ylist.append(f"<li>{PLANET_SI[c]} {dg} — මේ ක්ෂේත්‍රයට {'ශක්තියක්' if 'උච්ච' in dg or 'ස්වක්ෂේත්‍ර' in dg or 'මූලත්‍රිකෝණ' in dg else 'අභියෝගයක්'}</li>")
        if P[c].get("combust"):
            ylist.append(f"<li>{PLANET_SI[c]} අස්තංගත — එහි ඵල ප්‍රකාශ වීම දුර්වල විය හැක</li>")
    av = d.get("ashtakavarga")
    if av:
        ylist.append(f"<li>අෂ්ටකවර්ග: {h} වන භාවයේ SAV බින්දු <b>{av['sav'][hs]}</b> "
                     + ("(28ට වැඩි — හිතකර)" if av["sav"][hs] >= 28 else "(28ට අඩු — වැඩි ශ්‍රමයක් අවශ්‍ය විය හැක)") + "</li>")
    H.append("".join(ylist) or "<li>විශේෂ ඇඟවීම් නැත.</li>")
    H.append("</ul>")
    H.append(note_block(notes, "yogas"))

    # --- 5 dasha timing
    now_utc = now_local.astimezone(timezone.utc)
    vim = d["vimshottari"]
    key_planets = {hlord, kar} | {d["chara_karakas"][k]["planet"] for k in spec["ck"] if k in d["chara_karakas"]}
    key_planets |= {jc.SIGN_LORD[(ls + x - 1) % 12] for x in spec["support"][:2]}
    H.append('<div class="pb"></div><h2>5. දශා අනුව කාල ප්‍රවණතා</h2>')
    H.append(f'<p class="small">මේ ක්ෂේත්‍රයට ප්‍රධාන ග්‍රහයන්: {", ".join(PLANET_SI[p] for p in sorted(key_planets))}. '
             f'{spec["timing"]}</p>')
    horizon = now_utc + timedelta(days=int(7 * 365.25))
    rows = []
    for m in vim["mahadashas"]:
        for s_ in m.get("sub", []):
            st, en = datetime.fromisoformat(s_["start"]), datetime.fromisoformat(s_["end"])
            if en <= now_utc or st >= horizon:
                continue
            rel = [p for p in (m["lord"], s_["lord"]) if p in key_planets]
            if not rel:
                continue
            why = " / ".join(f"{PLANET_SI[p]}: " + (f"{h} වන භාවාධිපති" if p == hlord else "කාරකයා" if p == kar else "සම්බන්ධ ග්‍රහයා") for p in rel)
            rows.append(f"<tr{' class=cur' if st <= now_utc < en else ''}><td>{PLANET_SI[m['lord']]}/{PLANET_SI[s_['lord']]}</td>"
                        f"<td>{st.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</td><td>{en.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</td><td>{why}</td></tr>")
    H.append("<h3>ඉදිරි වසර 7 — මේ ක්ෂේත්‍රයට සම්බන්ධ දශා කවුළු</h3>"
             + ("<table><tr><th>දශාව</th><th>ආරම්භය</th><th>අවසානය</th><th>ඇයි</th></tr>" + "".join(rows) + "</table>"
                if rows else "<p>ඉදිරි වසර 7 තුළ මේ ක්ෂේත්‍රයට කෙලින්ම සම්බන්ධ දශා කවුළුවක් නැත; ගෝචර කොටස බලන්න.</p>"))
    nd = d.get("narayana_dasa")
    if nd:
        rel_nd = [x for x in nd if datetime.fromisoformat(x["end"]) > now_utc and datetime.fromisoformat(x["start"]) < horizon]
        if rel_nd:
            H.append("<h3>නාරායණ දශා (තහවුරු කිරීම)</h3><table><tr><th>රාශිය</th><th>ආරම්භය</th><th>අවසානය</th><th>ලග්නයෙන්</th><th>අදාළද</th></tr>"
                     + "".join(f"<tr><td>{SIGN_SI[inv[x['sign']]]}</td><td>{fmt_date(x['start'], tz)}</td><td>{fmt_date(x['end'], tz)}</td>"
                               f"<td>{jc.house_from(ls, inv[x['sign']])} වැන්න</td>"
                               f"<td>{'✔ මේ ක්ෂේත්‍රයට' if jc.house_from(ls, inv[x['sign']]) in [h] + spec['support'] else '—'}</td></tr>"
                               for x in rel_nd[:8]) + "</table>")
    H.append(note_block(notes, "dasha"))

    # --- 6 gochara
    H.append("<h2>6. ගෝචරය</h2>")
    sa, ju = tr["Sa"], tr["Ju"]
    hs_house_from_lagna = h
    H.append("<ul>"
             f"<li><b>ශනි</b> {SIGN_SI[sa['sign']]} — ලග්නයෙන් {sa['from_lagna']} වැන්න"
             + (f" (මේ ක්ෂේත්‍රයේ ප්‍රධාන භාවය — වගකීම් සහ ප්‍රමාද, ඒත් ස්ථාවර පදනමක්)" if sa["from_lagna"] == hs_house_from_lagna else "")
             + f"; චන්ද්‍රගෙන් {sa['from_moon']}: {SATURN_FROM_MOON_SI[sa['from_moon']]}</li>"
             f"<li><b>ගුරු</b> {SIGN_SI[ju['sign']]} — ලග්නයෙන් {ju['from_lagna']} වැන්න"
             + (" (මේ ක්ෂේත්‍රයට හිතකර ගෝචරයක්)" if ju["from_lagna"] in [h] + spec["support"] else "")
             + f"; චන්ද්‍රගෙන් {ju['from_moon']}: {JUPITER_FROM_MOON_SI[ju['from_moon']]}</li>"
             f"<li><b>සඩේ සති / ධයියා</b>: {tr['sade_sati']}</li></ul>")
    rel_ch = [(dt, p, s_, st) for dt, p, s_, st in changes if jc.house_from(ls, s_) in [h] + spec["support"]]
    if rel_ch:
        H.append("<h3>මේ ක්ෂේත්‍රයට වැදගත් ගෝචර මාරු</h3><table><tr><th>දිනය</th><th>ග්‍රහයා</th><th>රාශිය</th><th>භාවය</th></tr>"
                 + "".join(f"<tr><td>{dt.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</td><td>{PLANET_SI[p]}</td><td>{SIGN_SI[s_]}</td>"
                           f"<td>ලග්නයෙන් {jc.house_from(ls, s_)} වැන්න</td></tr>" for dt, p, s_, st in rel_ch) + "</table>")
    H.append(note_block(notes, "gochara"))

    # --- 7 convergence + notes
    H.append("<h2>7. ඉදිරි කාලය</h2>")
    win = []
    for m in vim["mahadashas"]:
        for s_ in m.get("sub", []):
            st, en = datetime.fromisoformat(s_["start"]), datetime.fromisoformat(s_["end"])
            if en > now_utc and st < horizon and (m["lord"] in key_planets or s_["lord"] in key_planets):
                win.append((max(st, now_utc), f"<li><b>{max(st, now_utc).astimezone(ZoneInfo(tz)).strftime('%Y-%m')} → "
                                              f"{en.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</b> — {PLANET_SI[m['lord']]}/{PLANET_SI[s_['lord']]} දශාව</li>"))
    for dt, p, s_, st in rel_ch:
        win.append((dt, f"<li><b>{dt.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</b> — {PLANET_SI[p]} {SIGN_SI[s_]} රාශියට "
                        f"(ලග්නයෙන් {jc.house_from(ls, s_)} වැන්න)</li>"))
    H.append("<ul>" + ("".join(x for _, x in sorted(win, key=lambda t: t[0])) or "<li>ඉදිරි වසර 7 තුළ කැපී පෙනෙන සම්මුඛ කවුළුවක් නැත.</li>") + "</ul>")
    H.append('<p class="small">දශාව සහ ගෝචරය එකට ගැලපෙන කාල වඩාත් වැදගත්; තනි ඇඟවීමක් මත තීරණ නොගන්න.</p>')
    H.append(note_block(notes, "summary", "ජ්‍යොතිෂවේදියාගේ විග්‍රහය"))
    H.append(note_block(notes, "upcoming"))
    if (notes or {}).get("remedies"):
        H.append("<h2>යෝජනා</h2>" + note_block(notes, "remedies", "ප්‍රතිකර්ම / ආකල්ප යෝජනා"))
    extra_disc = ""
    if code == "B4":
        extra_disc = " මෙහි ආයෝජන, මූල්‍ය හෝ නීතිමය උපදෙස් අන්තර්ගත නොවේ."
    if code in ("B5", "B8"):
        extra_disc = " මෙහි වෛද්‍ය තොරතුරු, රෝග විනිශ්චය හෝ ආයුෂ පිළිබඳ අනාවැකි අන්තර්ගත නොවේ."
    H.append(disclaimer_block(f"පරාශර හෝරා ශාස්ත්‍රය සහ ජෛමිනි සම්ප්‍රදාය; P.V.R. Narasimha Rao ගේ Vedic Astrology: An Integrated Approach. "
                              f"වාර්තා වර්ගය {code} — {spec['sub']}.{extra_disc}"))
    return "\n".join(H)


# ================================================================ C series — annual / time-based reports
SS_PHASE_SI = {12: ("පළමු අවධිය (ආරෝහණ)", "වියදම්, නින්ද/විවේකය, විදේශ හෝ ස්ථාන වෙනස්කම්; අභ්‍යන්තර සූදානම"),
               1: ("මධ්‍ය අවධිය (ශිඛර)", "වගකීම් බර, ශරීර/මානසික ශක්තිය, පෞද්ගලික අනන්‍යතාවය පිළිබඳ ප්‍රශ්න"),
               2: ("තෙවන අවධිය (අවරෝහණ)", "ධන කටයුතු, පවුල, කථනය; ක්‍රමයෙන් සැහැල්ලු වීම"),
               4: ("ධයියා (අර්ධාෂ්ටම)", "නිවස, මව, මානසික සතුට සහ දේපල සම්බන්ධ වගකීම්"),
               8: ("ධයියා (අෂ්ටම)", "හදිසි වෙනස්කම්, වියදම්, සෞඛ්‍ය පුරුදු ගැන අවධානය")}
SS_ADVICE = ["නියමිත වේලාවට වැඩ කිරීම සහ පොරොන්දු ඉටු කිරීම — ශනි විනය අගය කරයි",
             "නින්ද, ආහාර සහ ව්‍යායාම නිතිපතා තබා ගැනීම",
             "වැඩිහිටියන්, සේවකයන් සහ අඩු පහසුකම් ඇති අය සමඟ ඉවසීමෙන් සහ ගෞරවයෙන් කටයුතු කිරීම",
             "මූල්‍ය සැලසුම් සහ අනවශ්‍ය ණය වළක්වා ගැනීම",
             "ලොකු තීරණ කලබලයෙන් නොගෙන, කරුණු ලියා තබා ගෙන ගැනීම"]


def build_c2(d, a, notes, now_local, year, tr, changes):
    """C2 = C1 (Varsha) + that year's transits + Vimshottari AD/PD overlay -> convergence calendar."""
    base = build_c1(d, a, notes, now_local, year)
    # cut C1's disclaimer; we add our own at the end
    base = base.split('<div class="pb"></div><h2>ක්‍රමවේදය සහ වගකීම් ප්‍රකාශය</h2>')[0]
    base = base.replace("වර්ෂ ඵල — තාජක ක්‍රමය (C1)", "වර්ෂ ඵල + ගෝචර දින දර්ශනය (C2)")
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    moon = P["Mo"]
    tz = a.tz
    v = d["varsha_kundali"]
    inv = {s: i for i, s in enumerate(jc.SIGNS)}
    H = [base]
    y0 = datetime.strptime(v["varsha_pravesha_local"], "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(a.tz)).astimezone(timezone.utc)
    y1 = y0 + timedelta(days=366)
    H.append('<div class="pb"></div><h2>6. වර්ෂය තුළ ගෝචරය</h2>')
    sa, ju, ra = tr["Sa"], tr["Ju"], tr["Ra"]
    H.append("<ul>"
             f"<li><b>ශනි</b> {SIGN_SI[sa['sign']]} — චන්ද්‍රගෙන් {sa['from_moon']}, ලග්නයෙන් {sa['from_lagna']}: {SATURN_FROM_MOON_SI[sa['from_moon']]}</li>"
             f"<li><b>ගුරු</b> {SIGN_SI[ju['sign']]} — චන්ද්‍රගෙන් {ju['from_moon']}, ලග්නයෙන් {ju['from_lagna']}: {JUPITER_FROM_MOON_SI[ju['from_moon']]}</li>"
             f"<li><b>රාහු–කේතු</b> {SIGN_SI[ra['sign']]}–{SIGN_SI[(ra['sign'] + 6) % 12]} — ලග්නයෙන් {ra['from_lagna']}/{(ra['from_lagna'] + 5) % 12 + 1} වැනි භාව</li>"
             f"<li><b>සඩේ සති / ධයියා</b>: {tr['sade_sati']}</li></ul>")
    yr_ch = [c for c in changes if y0 <= c[0].astimezone(timezone.utc) <= y1]
    if yr_ch:
        H.append("<h3>වර්ෂය තුළ රාශි මාරු</h3><table><tr><th>දිනය</th><th>ග්‍රහයා</th><th>නව රාශිය</th><th>භාවය</th><th>ප්‍රවණතාව</th></tr>"
                 + "".join(f"<tr><td>{dt.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</td><td>{PLANET_SI[p]}</td><td>{SIGN_SI[s_]}</td>"
                           f"<td>චන්ද්‍රගෙන් {jc.house_from(moon['sign_idx'], s_)}, ලග්නයෙන් {jc.house_from(ls, s_)}</td>"
                           f"<td>{SATURN_FROM_MOON_SI[jc.house_from(moon['sign_idx'], s_)] if p == 'Sa' else JUPITER_FROM_MOON_SI[jc.house_from(moon['sign_idx'], s_)] if p == 'Ju' else HOUSE_SI[jc.house_from(ls, s_)].split(',')[0] + ' ක්ෂේත්‍රයට රාහු'}</td></tr>"
                           for dt, p, s_, st in yr_ch) + "</table>")
    # --- convergence calendar: month by month
    H.append('<div class="pb"></div><h2>7. මාසික සම්මුඛ දින දර්ශනය</h2>')
    H.append('<p class="small">එක් මාසයකට: විම්ශෝත්තරී අන්තර්/ප්‍රත්‍යන්තර දශාව, මුද්දා දශාව සහ ගෝචර සිදුවීම් එකට. '
             'තුනම එකම දිශාවට යොමු වන මාස වඩාත් කැපී පෙනේ.</p>')
    vim = d["vimshottari"]
    def at(dtv, lst):
        for x in lst:
            if datetime.fromisoformat(x["start"]) <= dtv < datetime.fromisoformat(x["end"]):
                return x
        return None
    rows = []
    cur = y0
    while cur < y1:
        mid = cur + timedelta(days=15)
        md = at(mid, vim["mahadashas"])
        ad = at(mid, md["sub"]) if md and md.get("sub") else None
        pd_ = at(mid, ad["sub"]) if ad and ad.get("sub") else None
        mud = next((m for m in v["mudda"] if m["start"][:16] <= mid.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d %H:%M") < m["end"][:16]), None)
        ev = [f"{PLANET_SI[p]} → {SIGN_SI[s_]}" for dt, p, s_, st in yr_ch
              if cur <= dt.astimezone(timezone.utc) < cur + timedelta(days=31)]
        dash = (f"{PLANET_SI[md['lord']]}/{PLANET_SI[ad['lord']]}" if ad else (PLANET_SI[md["lord"]] if md else "—"))
        if pd_:
            dash += f"/{PLANET_SI[pd_['lord']]}"
        score = 0
        for pl in [x["lord"] for x in (ad, pd_, mud) if x]:
            hh = P[pl]["house"]
            if hh in (1, 2, 4, 5, 7, 9, 10, 11):
                score += 1
            if hh in (6, 8, 12):
                score -= 1
            if "නීච" in si_dignity(P[pl]["dignity"]):
                score -= 1
            if any(x in si_dignity(P[pl]["dignity"]) for x in ("උච්ච", "ස්වක්ෂේත්‍ර", "මූලත්‍රිකෝණ")):
                score += 1
        if ev:
            score += 0
        tone = "හිතකර" if score >= 2 else ("අවධානය" if score <= -2 else "මිශ්‍ර")
        focus = HOUSE_SI[P[pd_["lord"]]["house"]].split(",")[0] if pd_ else (HOUSE_SI[P[ad["lord"]]["house"]].split(",")[0] if ad else "—")
        rows.append(f"<tr><td>{cur.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</td><td>{dash}</td>"
                    f"<td>{PLANET_SI[mud['lord']] if mud else '—'}</td><td>{focus}</td><td>{', '.join(ev) or '—'}</td><td>{tone}</td></tr>")
        cur += timedelta(days=30.44)
    H.append("<table><tr><th>මාසය</th><th>විම්ශෝත්තරී (MD/AD/PD)</th><th>මුද්දා</th><th>අවධානය යොමු වන ක්ෂේත්‍රය</th><th>ගෝචර සිදුවීම්</th><th>ප්‍රවණතාව</th></tr>"
             + "".join(rows) + "</table>")
    H.append(note_block(notes, "calendar") or note_block(notes, "gochara"))
    H.append(disclaimer_block("වර්ෂ ඵල (තාජක) සහ ගෝචර ක්‍රම — P.V.R. Narasimha Rao, ch. 25–31. වාර්තා වර්ගය C2. "
                              "වර්ෂ කුණ්ඩලිය ජන්ම කේන්දරයට අතිරේකයකි; දෙකම එකට කියවිය යුතුයි."))
    return "\n".join(H)


def build_c3(d, a, notes, now_local, tr):
    """C3 — Sade Sati / Dhaiya report."""
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    moon = P["Mo"]
    ms = moon["sign_idx"]
    tz = a.tz
    now_utc = now_local.astimezone(timezone.utc)
    spells = dedupe_phases(sade_sati_timeline(ms, now_utc - timedelta(days=365 * 12), 36))
    cur_sp = next((x for x in spells if x[0] <= now_utc <= x[1]), None)
    nxt = next((x for x in spells if x[0] > now_utc), None)
    av = d.get("ashtakavarga")
    sat_bav = av["bav"]["Sa"] if av and "Sa" in av.get("bav", {}) else None
    labels = {ls: ["ලග්න"]}
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        labels.setdefault(P[c]["sign_idx"], []).append(PLANET_SI[c] + (" (ව)" if P[c]["retro"] and c not in ("Ra", "Ke") else ""))
    status = (f"දැනට <b>{cur_sp[2]}</b> කාලය තුළ ({cur_sp[0].astimezone(ZoneInfo(tz)).strftime('%Y-%m')} – {cur_sp[1].astimezone(ZoneInfo(tz)).strftime('%Y-%m')})"
              if cur_sp else (f"දැනට සඩේ සති හෝ ධයියා නැත. ඊළඟ කාලය <b>{nxt[2]}</b> — {nxt[0].astimezone(ZoneInfo(tz)).strftime('%Y-%m')} සිට" if nxt else "දැනට සඩේ සති හෝ ධයියා නැත."))
    H = [f'''<div class="cover" style="padding-top:12mm"><div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">සඩේ සති වාර්තාව</h1><div class="sub">ශනි ගෝචරය සහ ධයියා කාල (C3)</div>
      <div class="name">{esc(a.name)}</div>
      <div class="muted">{esc(a.date)} · {esc(a.time)} · {esc(a.place or "")}</div>
      <div style="margin:12pt auto 0 auto; width:100mm">{south_indian_html_si(labels, "D1 · රාශි චක්‍රය", 100)}</div>
      <p style="margin-top:10pt">{status}</p></div>''']
    H.append('<div class="pb"></div><h2>1. සඩේ සති යනු මොකක්ද?</h2>')
    H.append('<div class="box">ශනි ඔබේ ජන්ම චන්ද්‍ර රාශියෙන් 12, 1, 2 යන රාශි තුන හරහා ගමන් කරන කාලය <b>සඩේ සති</b> ලෙස හැඳින්වේ — '
             'රාශියකට වසර 2½ බැගින්, මුළු කාලය වසර 7½ක් පමණ. ශනි 4 හෝ 8 වැනි රාශියේ සිටින වසර 2½ <b>ධයියා</b> ලෙස හැඳින්වේ.<br><br>'
             'මේ කාල "අසුබ" ලෙස පොදුවේ කථා කළත්, සම්භාව්‍ය ග්‍රන්ථවල දැක්වෙන්නේ මේවා <b>වගකීම්, විනය සහ පරිණතභාවය</b> වැඩෙන කාල ලෙසයි. '
             'ශනි ශ්‍රමයට ප්‍රතිඵල දෙන ග්‍රහයා; කලින් නොසලකා හැරි කාරණා මතු වී, ඒවා විසඳා ගැනීමට බල කරන ප්‍රවණතාවක් ඇති කරයි. '
             'ජන්ම කේන්දරයේ ශනිගේ තත්ත්වය අනුව මේ කාලයේ බර වැඩි හෝ අඩු විය හැක.</div>')
    H.append("<h2>2. ඔබේ කේන්දරයේ ශනි</h2>")
    sa_n = P["Sa"]
    own = [h for h in range(1, 13) if jc.SIGN_LORD[(ls + h - 1) % 12] == "Sa"]
    H.append("<table>"
             f"<tr><td style='width:34%'><b>ජන්ම චන්ද්‍ර රාශිය</b></td><td>{SIGN_SI[ms]} — {NAK_SI[jc.NAKSHATRAS.index(moon['nakshatra'])]} නැකත</td></tr>"
             f"<tr><td><b>ජන්ම ශනි</b></td><td>{SIGN_SI[sa_n['sign_idx']]} {dms(sa_n['deg_in_sign'])}, {sa_n['house']} වැන්නේ"
             + (f", {si_dignity(sa_n['dignity'])}" if si_dignity(sa_n["dignity"]) != "—" else "")
             + (", වක්‍ර" if sa_n["retro"] else "") + "</td></tr>"
             f"<tr><td><b>ශනි අධිපති භාව</b></td><td>{', '.join(str(x) + ' වැන්න' for x in own)} — {'; '.join(HOUSE_SI[x].split(',')[0] for x in own)}</td></tr>"
             f"<tr><td><b>චන්ද්‍රගෙන් ශනි</b></td><td>{jc.house_from(ms, sa_n['sign_idx'])} වැන්නේ</td></tr>"
             + (f"<tr><td><b>ශනිගේ අෂ්ටකවර්ග බින්දු</b></td><td>{sum(sat_bav)} (සියලු රාශිවල එකතුව)</td></tr>" if sat_bav else "")
             + "</table>")
    good_sa = sa_n["house"] in (3, 6, 10, 11) or si_dignity(sa_n["dignity"]) in ("උච්ච", "ස්වක්ෂේත්‍ර", "මූලත්‍රිකෝණ")
    H.append(f'<div class="box"><b>ප්‍රවණතාව:</b> ' + ("ජන්ම කේන්දරයේ ශනි ශක්තිමත් ස්ථානයක සිටීම මේ කාලවල බර සාපේක්ෂව අඩු කරන සාධකයකි."
                                                       if good_sa else "ජන්ම ශනිගේ ස්ථානය අනුව මේ කාලවලදී ඉවසීම සහ ක්‍රමවත් බව වැඩිපුර අවශ්‍ය විය හැක.")
             + " ශනි අධිපති භාවවල කාරණා මේ කාලවලදී ප්‍රමුඛ වේ.</div>")
    H.append('<div class="pb"></div><h2>3. ඔබේ සඩේ සති / ධයියා කාල රේඛාව</h2>')
    rows = []
    for s0, s1, tag, h in spells:
        ph = SS_PHASE_SI.get(h, ("", ""))
        mark = " class=cur" if s0 <= now_utc <= s1 else ""
        past = "අවසන්" if s1 < now_utc else ("ක්‍රියාත්මක" if s0 <= now_utc <= s1 else "ඉදිරියේ")
        rows.append(f"<tr{mark}><td>{tag}</td><td>{ph[0]}</td><td>{s0.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</td>"
                    f"<td>{s1.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</td><td>{past}</td><td>{ph[1]}</td></tr>")
    H.append("<table><tr><th>වර්ගය</th><th>අවධිය</th><th>ආරම්භය</th><th>අවසානය</th><th>තත්ත්වය</th><th>ප්‍රමුඛ කාරණා</th></tr>" + "".join(rows) + "</table>")
    H.append('<p class="small muted">ශනිගේ වක්‍ර චලනය නිසා රාශි මාරු දෙවරක් සිදුවිය හැක; මෙහි කාල එකතු කර දක්වා ඇත. '
             'දිනවලට දින කිහිපයක නිරවද්‍යතාවක් ඇත.</p>')
    if sat_bav:
        H.append("<h2>4. අෂ්ටකවර්ග අනුව ශනි ගෝචරයේ බර</h2>")
        H.append("<table><tr><th>රාශිය</th>" + "".join(f"<th>{SIGN_SI[i][:3]}</th>" for i in range(12)) + "</tr>"
                 + "<tr><td>ශනි BAV</td>" + "".join(f"<td>{sat_bav[i]}</td>" for i in range(12)) + "</tr>"
                 + "<tr><td>SAV</td>" + "".join(f"<td>{av['sav'][i]}</td>" for i in range(12)) + "</tr></table>")
        H.append('<p class="small">ශනි ගමන් කරන රාශියේ ශනිගේ බින්දු 4 හෝ ඊට වැඩි නම් එම කාලයේ ප්‍රතිඵල සාපේක්ෂව පහසු වන ප්‍රවණතාවක් ඇත; '
                 '2ට අඩු නම් වැඩි ඉවසීමක් අවශ්‍ය විය හැක.</p>')
        for s0, s1, tag, h in spells:
            if s1 < now_utc:
                continue
            sgn = (ms + h - 1) % 12
            H.append(f'<p class="small">• {tag} — {ph_label(h)} — {SIGN_SI[sgn]} රාශියේ ({s0.astimezone(ZoneInfo(tz)).strftime("%Y-%m")}–'
                     f'{s1.astimezone(ZoneInfo(tz)).strftime("%Y-%m")}): ශනි බින්දු <b>{sat_bav[sgn]}</b>, SAV {av["sav"][sgn]}</p>')
    H.append('<div class="pb"></div><h2>5. ප්‍රායෝගික ආකල්ප</h2><ul>' + "".join(f"<li>{x}</li>" for x in SS_ADVICE) + "</ul>")
    H.append('<div class="note"><div class="lbl">වැදගත්</div><p>සඩේ සති කාලයක් සෞඛ්‍ය ප්‍රශ්නයක් හෝ අර්බුදයක් ලෙස නොසලකන්න. '
             'සෞඛ්‍ය, මූල්‍ය හෝ නීතිමය කාරණා සඳහා අදාළ වෘත්තිකයන් හමුවන්න. ජ්‍යොතිෂය එම උපදෙස් වෙනුවට නොවේ.</p></div>')
    H.append(note_block(notes, "summary", "ජ්‍යොතිෂවේදියාගේ විග්‍රහය"))
    H.append(note_block(notes, "remedies", "ප්‍රතිකර්ම / ආකල්ප යෝජනා"))
    H.append(disclaimer_block("ශනි ගෝචරය සහ අෂ්ටකවර්ග — P.V.R. Narasimha Rao, ch. 12, 25. වාර්තා වර්ගය C3."))
    return "\n".join(H)


def ph_label(h):
    return SS_PHASE_SI.get(h, ("", ""))[0]


def build_c4(d, a, notes, now_local, tr):
    """C4 — Dasha Sandhi: the change of Mahadasha, one year either side."""
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    tz = a.tz
    now_utc = now_local.astimezone(timezone.utc)
    vim = d["vimshottari"]
    mds = vim["mahadashas"]
    cur_i = next((i for i, m in enumerate(mds) if datetime.fromisoformat(m["start"]) <= now_utc < datetime.fromisoformat(m["end"])), 0)
    cur_md, nxt_md = mds[cur_i], mds[cur_i + 1] if cur_i + 1 < len(mds) else None
    if not nxt_md:
        sys.exit("no following Mahadasha in range")
    change = datetime.fromisoformat(cur_md["end"])
    A, B = cur_md["lord"], nxt_md["lord"]
    labels = {ls: ["ලග්න"]}
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        labels.setdefault(P[c]["sign_idx"], []).append(PLANET_SI[c])
    H = [f'''<div class="cover" style="padding-top:12mm"><div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">දශා සන්ධි වාර්තාව</h1><div class="sub">මහා දශා මාරුව (C4)</div>
      <div class="name">{esc(a.name)}</div>
      <div style="margin:10pt 0; font-size:14pt"><b>{PLANET_SI[A]} → {PLANET_SI[B]}</b> · {change.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d")}</div>
      <div style="width:96mm; margin:8pt auto 0 auto">{south_indian_html_si(labels, "D1 · රාශි චක්‍රය", 96)}</div></div>''']
    H.append('<div class="pb"></div><h2>1. දශා සන්ධිය යනු</h2>')
    H.append('<div class="box">මහා දශාවක් අවසන් වී අලුත් එකක් පටන් ගන්නා කාලය <b>දශා සන්ධිය</b> ලෙස හැඳින්වේ. '
             'ජීවිතයේ කේන්ද්‍රීය තේමාව එක් ග්‍රහයෙකුගේ ස්වභාවයෙන් තවත් ග්‍රහයෙකුගේ ස්වභාවයට මාරු වන නිසා, '
             'මේ කාලයේ ප්‍රමුඛතා, පරිසරය සහ සම්බන්ධතා වෙනස් වන ප්‍රවණතාවක් ඇත. '
             'මාරුව එක් දිනකින් සිදු නොවේ — කලින් මාස 6–12 සිට පසුව මාස 6–12 දක්වා ක්‍රමයෙන් සිදු වේ.</div>')
    rows = []
    for L, lbl in ((A, "අවසන් වන දශාව"), (B, "පටන් ගන්නා දශාව")):
        own = [h for h in range(1, 13) if jc.SIGN_LORD[(ls + h - 1) % 12] == L]
        rows.append(f"<tr><td><b>{lbl}</b></td><td>{PLANET_SI[L]}</td><td>{SIGN_SI[P[L]['sign_idx']]}, {P[L]['house']} වැන්නේ</td>"
                    f"<td>{si_dignity(P[L]['dignity'])}</td><td>{', '.join(str(x) for x in own) or '—'}</td>"
                    f"<td>{PLANET_NATURE_SI[L]}</td></tr>")
    H.append("<h2>2. ග්‍රහයන් දෙදෙනා</h2><table><tr><th></th><th>ග්‍රහයා</th><th>ස්ථානය</th><th>තත්ත්වය</th><th>අධිපති භාව</th><th>කාරකත්වය</th></tr>"
             + "".join(rows) + "</table>")
    ha, hb = P[A]["house"], P[B]["house"]
    H.append(f'<div class="box"><b>වෙනස:</b> {PLANET_SI[A]} දශාවේදී {HOUSE_SI[ha]} සම්බන්ධ කාරණා ප්‍රමුඛ වූ බව පෙනේ. '
             f'{PLANET_SI[B]} දශාවේදී අවධානය {HOUSE_SI[hb]} දෙසට හැරෙන ප්‍රවණතාවක් ඇත. '
             + ("නව දශාධිපති හිතකර ස්ථානයක සිටීම මාරුව සාපේක්ෂව පහසු කරයි."
                if hb in (1, 2, 4, 5, 7, 9, 10, 11) and "නීච" not in si_dignity(P[B]["dignity"])
                else "නව දශාධිපතිගේ ස්ථානය අනුව මුල් කාලයේ ගැලපීමට කාලයක් ගත විය හැක.") + "</div>")
    H.append('<div class="pb"></div><h2>3. සන්ධි කාලය — අන්තර් දශා</h2>')
    win0, win1 = change - timedelta(days=400), change + timedelta(days=400)
    rows = []
    for m in (cur_md, nxt_md):
        for s_ in m.get("sub", []):
            st, en = datetime.fromisoformat(s_["start"]), datetime.fromisoformat(s_["end"])
            if en < win0 or st > win1:
                continue
            hh = P[s_["lord"]]["house"]
            rows.append(f"<tr{' class=cur' if st <= now_utc < en else ''}><td>{PLANET_SI[m['lord']]}/{PLANET_SI[s_['lord']]}</td>"
                        f"<td>{st.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</td><td>{en.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</td>"
                        f"<td>{PLANET_SI[s_['lord']]} {hh} වැන්නේ — {HOUSE_SI[hh].split(',')[0]}</td></tr>")
    H.append("<table><tr><th>දශාව</th><th>ආරම්භය</th><th>අවසානය</th><th>ප්‍රවණතාව</th></tr>" + "".join(rows) + "</table>")
    H.append(f'<p class="small">මාරු දිනය <b>{change.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d")}</b>. '
             f'ඊට කලින් අවසන් අන්තර් දශාව සහ පසුව පළමු අන්තර් දශාව මාරුවේ ස්වභාවය තීරණය කරයි.</p>')
    H.append("<h2>4. ගෝචරය මාරු කාලයේ</h2>")
    sa, ju = tr["Sa"], tr["Ju"]
    H.append("<ul>"
             f"<li><b>ශනි</b> {SIGN_SI[sa['sign']]} — චන්ද්‍රගෙන් {sa['from_moon']}: {SATURN_FROM_MOON_SI[sa['from_moon']]}</li>"
             f"<li><b>ගුරු</b> {SIGN_SI[ju['sign']]} — චන්ද්‍රගෙන් {ju['from_moon']}: {JUPITER_FROM_MOON_SI[ju['from_moon']]}</li>"
             f"<li><b>සඩේ සති / ධයියා</b>: {tr['sade_sati']}</li></ul>")
    H.append("<h2>5. ප්‍රායෝගිකව</h2><ul>"
             f"<li>නව දශාධිපති {PLANET_SI[B]} නියෝජනය කරන කාරණා ({PLANET_NATURE_SI[B]}) ක්‍රමයෙන් ඉදිරියට එනවා — ඒවාට කලින් සූදානම් වීම ප්‍රයෝජනවත්.</li>"
             f"<li>{HOUSE_SI[hb]} සම්බන්ධ දේවල් නව අවධියේ තේමාව වීමට ඉඩ ඇත.</li>"
             "<li>මාරු කාලයේ ලොකු, ආපසු හැරවිය නොහැකි තීරණ ගැනීමට කලින් කරුණු ලියා තබා ගෙන සලකා බලන්න.</li>"
             "<li>පැරණි දශාවේ ඉතිරි වී ඇති කටයුතු (ණය, පොරොන්දු, අවසන් නොකළ වැඩ) මාරුවට කලින් අවසන් කර ගැනීම ප්‍රයෝජනවත්.</li></ul>")
    H.append(note_block(notes, "summary", "ජ්‍යොතිෂවේදියාගේ විග්‍රහය"))
    H.append(note_block(notes, "upcoming"))
    H.append(disclaimer_block("විම්ශෝත්තරී දශා — P.V.R. Narasimha Rao, ch. 16. වාර්තා වර්ගය C4. දශා දින සෞර වර්ෂ අනුව."))
    return "\n".join(H)


def build_c6(d, a, notes, now_local, year, month):
    """C6 — Masa Phala: one Tajaka month of the year."""
    v = d["varsha_kundali"]
    m = v.get("masa")
    if not m:
        sys.exit("monthly chart missing — pass --month 1..12 with --year")
    inv = {s: i for i, s in enumerate(jc.SIGNS)}
    mls = inv[m["lagna"]]
    labels = {mls: ["ලග්න"]}
    for c, sgn in m["planets"].items():
        labels.setdefault(inv[sgn], []).append(PLANET_SI[c])
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    H = [f'''<div class="cover" style="padding-top:12mm"><div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">මාස ඵල වාර්තාව</h1><div class="sub">තාජක මාසික කේන්දරය (C6) · {year} වර්ෂයේ {month} වන මාසය</div>
      <div class="name">{esc(a.name)}</div>
      <div class="muted">මාස ප්‍රවේශය {esc(m["pravesha_local"])} ({esc(a.tz)})</div>
      <div style="margin:12pt auto 0 auto; width:104mm">{south_indian_html_si(labels, "මාස කුණ්ඩලිය", 104)}</div></div>''']
    H.append('<div class="pb"></div><h2>1. මාසයේ ව්‍යුහය</h2>')
    H.append("<table>"
             f"<tr><td style='width:34%'><b>මාස ප්‍රවේශය</b></td><td>{esc(m['pravesha_local'])} — රවි වර්ෂ ලග්නයෙන් 30°ක් ගමන් කරන මොහොත</td></tr>"
             f"<tr><td><b>මාස ලග්නය</b></td><td>{SIGN_SI[mls]}</td></tr>"
             f"<tr><td><b>මාසේශ (මාසාධිපති)</b></td><td>{PLANET_SI[m['masesha']]} — {PLANET_NATURE_SI[m['masesha']]}</td></tr>"
             f"<tr><td><b>වර්ෂේශ</b></td><td>{PLANET_SI[v['varshesha']]}</td></tr>"
             f"<tr><td><b>වර්ෂ මුන්ථා</b></td><td>{SIGN_SI[inv[v['muntha']]]}</td></tr>"
             f"<tr><td><b>සුදර්ශන චක්‍ර අන්තර් රාශිය</b></td><td>{SIGN_SI[inv[m['sc_antar_sign']]]} — මේ මාසයේ ග්‍රහයන් මේ රාශියෙන් බලන්න</td></tr>"
             "</table>")
    H.append(f'<div class="box">මාසේශ <b>{PLANET_SI[m["masesha"]]}</b> මේ මාසයේ ප්‍රධාන ග්‍රහයා. '
             f'ජන්ම කේන්දරයේ එය {P[m["masesha"]]["house"]} වැන්නේ ({HOUSE_SI[P[m["masesha"]]["house"]]}) සිටී — '
             f'මාසය පුරා එම කාරණා ඉදිරියට එන ප්‍රවණතාවක් ඇත.</div>')
    rows = []
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        sgn = inv[m["planets"][c]]
        rows.append(f"<tr><td>{PLANET_SI[c]}</td><td>{SIGN_SI[sgn]}</td><td>{jc.house_from(mls, sgn)}</td>"
                    f"<td>{SIGN_SI[P[c]['sign_idx']]} ({P[c]['house']})</td></tr>")
    H.append("<h3>මාස කුණ්ඩලියේ ග්‍රහ ස්ථාන</h3><table><tr><th>ග්‍රහයා</th><th>රාශිය</th><th>මාස භාවය</th><th>ජන්ම රාශිය (භාවය)</th></tr>"
             + "".join(rows) + "</table>")
    H.append('<p class="small muted">මාස කුණ්ඩලිය වර්ෂ කුණ්ඩලියට යටත් වේ; වර්ෂ ඵල වාර්තාව (C1/C2) සමඟ එකට කියවන්න.</p>')
    H.append(note_block(notes, "summary", "ජ්‍යොතිෂවේදියාගේ විග්‍රහය"))
    H.append(note_block(notes, "upcoming", "මාසය තුළ අවධානය"))
    H.append(disclaimer_block("තාජක මාසික කේන්දරය — P.V.R. Narasimha Rao, ch. 27.3, 28.7, 31. වාර්තා වර්ගය C6."))
    return "\n".join(H)


# ================================================================ D2 — Sampurna Porondam (full compatibility)
MANGAL_HOUSES = (1, 2, 4, 7, 8, 12)


def mangal_check(P, ls):
    """Kuja dosha from Lagna, Moon and Venus, with the common cancellation checks."""
    ks = P["Ma"]["sign_idx"]
    refs = {"ලග්නය": ls, "චන්ද්‍ර": P["Mo"]["sign_idx"], "ශුක්‍ර": P["Ve"]["sign_idx"]}
    hits = {k: jc.house_from(v, ks) for k, v in refs.items() if jc.house_from(v, ks) in MANGAL_HOUSES}
    canc = []
    if ks in jc.OWN["Ma"] or ks == jc.EXALT["Ma"]:
        canc.append("කුජ ස්වක්ෂේත්‍ර/උච්ච රාශියක")
    for b in ("Ju", "Ve"):
        if jc.sign_of(P[b]["lon"]) == ks:
            canc.append(f"{PLANET_SI[b]} කුජ සමඟ")
    if jc.sign_of(P["Sa"]["lon"]) == ks:
        canc.append("ශනි කුජ සමඟ")
    return hits, canc


def build_d2(dA, dB, a, notes, now_local):
    """dA = querent's full chart JSON (with compatibility block), dB = partner's full chart JSON."""
    comp = dA["compatibility"]
    if not comp:
        sys.exit("compatibility data missing — check --match-* arguments")
    tz = a.tz
    inv = {s: i for i, s in enumerate(jc.SIGNS)}
    PA, PB = dA["planets"], dB["planets"]
    lsA, lsB = dA["lagna"]["sign_idx"], dB["lagna"]["sign_idx"]
    nameA, nameB = a.name, (a.match_name or "සහකරු")
    total = comp["ashtakoota_total"]
    total = int(total) if float(total).is_integer() else total
    verdict = "හොඳ ගැලපීමක්" if total >= 24 else "මධ්‍යම ගැලපීමක්" if total >= 18 else "අඩු ලකුණු ගැලපීමක්"

    def chart(P, ls, title, size=86):
        lab = {ls: ["ලග්න"]}
        for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
            lab.setdefault(P[c]["sign_idx"], []).append(PLANET_SI[c] + (" (ව)" if P[c]["retro"] and c not in ("Ra", "Ke") else ""))
        return south_indian_html_si(lab, title, size)

    def varga_chart(d_, vname, title, size=86):
        v = d_["vargas"].get(vname)
        if not v:
            return ""
        vl = inv[v["La"]]
        lab = {vl: ["ලග්න"]}
        for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
            lab.setdefault(inv[v[c]], []).append(PLANET_SI[c])
        return south_indian_html_si(lab, title, size)

    H = [f'''<div class="cover" style="padding-top:12mm"><div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">සම්පූර්ණ පොරොන්දම් වාර්තාව</h1><div class="sub">අෂ්ටකූට + කේන්දර දෙකේ සංයෝජන විග්‍රහය (D2)</div>
      <div class="name">{esc(nameA)} &nbsp;·&nbsp; {esc(nameB)}</div>
      <div style="margin:12pt 0; font-size:15pt"><b>{total} / 36</b> — {verdict}</div>
      <div class="two" style="margin-top:6pt"><div style="flex:1">{chart(PA, lsA, nameA, 80)}</div><div style="flex:1">{chart(PB, lsB, nameB, 80)}</div></div></div>''']

    # --- 1 birth data
    H.append('<div class="pb"></div><h2>1. උපන් දත්ත</h2><table><tr><th></th><th>' + esc(nameA) + "</th><th>" + esc(nameB) + "</th></tr>"
             f'<tr><td><b>උපන් දිනය</b></td><td>{esc(a.date)}</td><td>{esc(a.match_date)}</td></tr>'
             f'<tr><td><b>වේලාව</b></td><td>{esc(a.time)}</td><td>{esc(a.match_time)}</td></tr>'
             f'<tr><td><b>ලග්නය</b></td><td>{SIGN_SI[lsA]} ({dms(dA["lagna"]["deg_in_sign"])})</td><td>{SIGN_SI[lsB]} ({dms(dB["lagna"]["deg_in_sign"])})</td></tr>'
             f'<tr><td><b>චන්ද්‍ර රාශිය</b></td><td>{SIGN_SI[PA["Mo"]["sign_idx"]]}</td><td>{SIGN_SI[PB["Mo"]["sign_idx"]]}</td></tr>'
             f'<tr><td><b>ජන්ම නැකත</b></td><td>{NAK_SI[jc.NAKSHATRAS.index(PA["Mo"]["nakshatra"])]} {PA["Mo"]["pada"]}</td>'
             f'<td>{NAK_SI[jc.NAKSHATRAS.index(PB["Mo"]["nakshatra"])]} {PB["Mo"]["pada"]}</td></tr>'
             f'<tr><td><b>ලග්නාධිපති</b></td><td>{PLANET_SI[jc.SIGN_LORD[lsA]]} — {PA[jc.SIGN_LORD[lsA]]["house"]} වැන්නේ</td>'
             f'<td>{PLANET_SI[jc.SIGN_LORD[lsB]]} — {PB[jc.SIGN_LORD[lsB]]["house"]} වැන්නේ</td></tr></table>')

    # --- 2 ashtakoota
    H.append("<h2>2. අෂ්ටකූට ලකුණු</h2>")
    krow = []
    for k in comp["kootas"]:
        si, meaning = KOOTA_SI.get(k["name"], (k["name"], ""))
        det = k["detail"]
        for tbl in (VARNA_SI, VASHYA_SI, YONI_SI, GANA_SI, NADI_SI, NAK_EN2SI):
            for en, sisi in sorted(tbl.items(), key=lambda kv: -len(kv[0])):
                det = re.sub(r"\b" + re.escape(en) + r"\b", sisi, det)
        det = (si_text(det).replace("Bhakoot dosha", "භකූට දෝෂය").replace("Nadi dosha", "නාඩි දෝෂය")
               .replace("cancelled", "නිෂ්ප්‍රභ වී ඇත").replace("same/friendly අධිපතිs", "අධිපතියන් සම/මිත්‍ර")
               .replace("same/friendly lords", "අධිපතියන් සම/මිත්‍ර").replace("(same)", "(සම)").replace("(6/8)", "(6/8 තත්ත්වය)"))
        krow.append(f"<tr><td>{si}</td><td>{meaning}</td><td><b>{k['points']}</b> / {k['max']}</td><td>{esc(det)}</td></tr>")
    H.append("<table><tr><th>කූටය</th><th>මනින දේ</th><th>ලකුණු</th><th>විස්තර</th></tr>" + "".join(krow)
             + f"<tr class='cur'><td colspan='2'><b>එකතුව</b></td><td><b>{total} / 36</b></td><td>{verdict}</td></tr></table>")
    H.append('<div class="note"><div class="lbl">ලකුණු කියවන ආකාරය</div>'
             '<p>අෂ්ටකූට ලකුණු ගැලපීමේ එක් ස්තරයක් පමණි. පහත කේන්දර දෙකේ සංයෝජනය (synastry), 7 වන භාවය, උපපද ලග්නය සහ දශා ගැලපීම '
             'ලකුණු එකතුවට වඩා ප්‍රායෝගික තොරතුරු දෙයි.</p></div>')

    # --- 3 doshas
    H.append('<h2>3. දෝෂ සහ නිෂ්ප්‍රභ වීම්</h2>')
    dl = []
    for k in comp["kootas"]:
        if "dosha" in k["detail"].lower():
            nm = "භකූට දෝෂය" if k["name"] == "Bhakoot" else "නාඩි දෝෂය"
            canc = "cancel" in k["detail"].lower()
            dl.append(f"<li><b>{nm}</b> — {'නිෂ්ප්‍රභ වී ඇත' if canc else 'නිෂ්ප්‍රභ වීමේ නියමයක් මෙහි ක්‍රියාත්මක නොවේ'}. "
                      + ("භකූට දෝෂය පවුල් සමෘද්ධියට, නාඩි දෝෂය සෞඛ්‍යයට සම්බන්ධ ලෙස සම්භාව්‍ය ග්‍රන්ථවල දැක්වේ; "
                         "නිෂ්ප්‍රභ වීමේ නියම කිහිපයක් ද ඇත." if not canc else "") + "</li>")
    for nm_, P_, ls_ in ((nameA, PA, lsA), (nameB, PB, lsB)):
        hits, canc = mangal_check(P_, ls_)
        if hits:
            dl.append(f"<li><b>කුජ දෝෂ ඇඟවීම — {esc(nm_)}</b>: කුජ {', '.join(f'{k}ගෙන් {v} වැන්නේ' for k, v in hits.items())}. "
                      + (f"නිෂ්ප්‍රභ වීමේ සාධක: {', '.join(canc)}." if canc else "පැහැදිලි නිෂ්ප්‍රභ වීමේ සාධකයක් නැත.") + "</li>")
        else:
            dl.append(f"<li>කුජ දෝෂ ඇඟවීමක් නැත — {esc(nm_)}</li>")
    H.append("<ul>" + "".join(dl) + "</ul>")
    H.append('<p class="small muted">දෝෂ පිළිබඳ සම්ප්‍රදායන් අතර වෙනස්කම් ඇත; මෙහි දක්වා ඇත්තේ P.V.R. Narasimha Rao ගේ ග්‍රන්ථයේ ක්‍රමයයි. '
             'දෝෂයක් තිබීම විවාහය නොකළ යුතු බවක් නොවේ — නිෂ්ප්‍රභ වීම්, කේන්දර දෙකේ සමස්ත ගැලපීම සහ දෙදෙනාගේ අවබෝධය වැදගත්.</p>')

    # --- 4 synastry overlay
    H.append('<h2>4. කේන්දර දෙකේ සංයෝජනය (Synastry)</h2>')
    H.append('<p class="small">එක් අයෙකුගේ ග්‍රහයන් අනෙකාගේ කේන්දරයේ කුමන භාවවලට වැටෙනවාද යන්න සම්බන්ධතාවයේ ස්වභාවය පෙන්වයි. '
             '1, 4, 5, 7, 9, 11 භාවවලට වැටීම හිතකර; 6, 8, 12 වලට වැටීම ඝර්ෂණයක් හෝ වගකීමක් පෙන්විය හැක.</p>')
    rows = []
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        hA = jc.house_from(lsB, PA[c]["sign_idx"])   # A's planet in B's chart
        hB = jc.house_from(lsA, PB[c]["sign_idx"])   # B's planet in A's chart
        def tone(h):
            return "හිතකර" if h in (1, 4, 5, 7, 9, 11) else ("අවධානය" if h in (6, 8, 12) else "මධ්‍යම")
        rows.append(f"<tr><td>{PLANET_SI[c]}</td><td>{SIGN_SI[PA[c]['sign_idx']]}</td><td>{hA} — {tone(hA)}</td>"
                    f"<td>{SIGN_SI[PB[c]['sign_idx']]}</td><td>{hB} — {tone(hB)}</td></tr>")
    H.append(f"<table><tr><th>ග්‍රහයා</th><th>{esc(nameA)} රාශිය</th><th>→ {esc(nameB)} භාවය</th>"
             f"<th>{esc(nameB)} රාශිය</th><th>→ {esc(nameA)} භාවය</th></tr>" + "".join(rows) + "</table>")
    good = sum(1 for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]
               if jc.house_from(lsB, PA[c]["sign_idx"]) in (1, 4, 5, 7, 9, 11)) \
        + sum(1 for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]
              if jc.house_from(lsA, PB[c]["sign_idx"]) in (1, 4, 5, 7, 9, 11))
    bad = sum(1 for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]
              if jc.house_from(lsB, PA[c]["sign_idx"]) in (6, 8, 12)) \
        + sum(1 for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]
              if jc.house_from(lsA, PB[c]["sign_idx"]) in (6, 8, 12))
    H.append(f'<div class="box">සංයෝජන සාරාංශය: හිතකර ස්ථාන {good}ක්, අවධානය යොමු කළ යුතු ස්ථාන {bad}ක් (ග්‍රහ 7 × දෙපැත්ත = 14). '
             + ("සමස්තයක් ලෙස සංයෝජනය සහායක පැත්තට බර වැඩියි." if good > bad + 2
                else "සමස්තයක් ලෙස ඝර්ෂණ ස්ථාන වැඩියි — සන්නිවේදනය සහ ඉවසීම වැදගත්." if bad > good
                else "සංයෝජනය මිශ්‍රයි — ශක්තිමත් පැති සහ ඝර්ෂණ පැති දෙකම ඇත.") + "</div>")
    mo_h = jc.house_from(lsB, PA["Mo"]["sign_idx"])
    ve_h = jc.house_from(lsB, PA["Ve"]["sign_idx"])
    H.append(f"<p class='small'><b>විශේෂ ලක්ෂ්‍ය:</b> {esc(nameA)} ගේ චන්ද්‍ර {esc(nameB)} ගේ {mo_h} වැන්නේ "
             f"(මානසික ගැලපීම), ශුක්‍ර {ve_h} වැන්නේ (ආකර්ෂණය). "
             f"{esc(nameB)} ගේ චන්ද්‍ර {esc(nameA)} ගේ {jc.house_from(lsA, PB['Mo']['sign_idx'])} වැන්නේ, "
             f"ශුක්‍ර {jc.house_from(lsA, PB['Ve']['sign_idx'])} වැන්නේ.</p>")

    # --- 5 seventh house / UL / DK
    H.append('<div class="pb"></div><h2>5. විවාහ භාවය, උපපදය සහ දාරාකාරක</h2>')
    rows = []
    for nm_, d_, P_, ls_ in ((nameA, dA, PA, lsA), (nameB, dB, PB, lsB)):
        h7 = (ls_ + 6) % 12
        l7 = jc.SIGN_LORD[h7]
        ul = d_["arudhas"].get("UL")
        dk = d_["chara_karakas"].get("DK", {}).get("planet")
        occ = [c for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"] if P_[c]["sign_idx"] == h7]
        rows.append(f"<tr><td><b>{esc(nm_)}</b></td><td>{SIGN_SI[h7]}</td><td>{', '.join(PLANET_SI[c] for c in occ) or '—'}</td>"
                    f"<td>{PLANET_SI[l7]} — {P_[l7]['house']} වැන්නේ{', ' + si_dignity(P_[l7]['dignity']) if si_dignity(P_[l7]['dignity']) != '—' else ''}</td>"
                    f"<td>{SIGN_SI[inv[ul]] if ul else '—'}</td><td>{PLANET_SI[dk] if dk else '—'} ({P_[dk]['house'] if dk else '—'})</td>"
                    f"<td>{PLANET_SI['Ve']} {P_['Ve']['house']} වැන්නේ{', ' + si_dignity(P_['Ve']['dignity']) if si_dignity(P_['Ve']['dignity']) != '—' else ''}</td></tr>")
    H.append("<table><tr><th></th><th>7 වන රාශිය</th><th>7 වන ග්‍රහයන්</th><th>7 වන අධිපති</th><th>උපපදය (UL)</th><th>දාරාකාරක</th><th>ශුක්‍ර</th></tr>"
             + "".join(rows) + "</table>")
    H.append('<p class="small muted">7 වන භාවය සහකරු සහ විවාහ ජීවිතය; උපපද ලග්නය (UL) විවාහයේ පිටතට පෙනෙන ස්වරූපය; '
             'දාරාකාරක (DK) සහකරු පිළිබඳ ජෛමිනි කාරකයා; ශුක්‍ර ආකර්ෂණය සහ රසිකත්වය.</p>')
    H.append('<h3>නවාංශක (D9) කේන්දර</h3>')
    H.append(f'<div class="two"><div style="flex:1">{varga_chart(dA, "D9", f"D9 · {nameA}", 80)}</div>'
             f'<div style="flex:1">{varga_chart(dB, "D9", f"D9 · {nameB}", 80)}</div></div>')
    v9A, v9B = dA["vargas"].get("D9"), dB["vargas"].get("D9")
    if v9A and v9B:
        H.append(f'<p class="small">D9 ලග්න: {esc(nameA)} — {SIGN_SI[inv[v9A["La"]]]}; {esc(nameB)} — {SIGN_SI[inv[v9B["La"]]]}. '
                 f'{esc(nameA)} ගේ D9 චන්ද්‍ර {SIGN_SI[inv[v9A["Mo"]]]}, {esc(nameB)} ගේ {SIGN_SI[inv[v9B["Mo"]]]}. '
                 'නවාංශකයේ ලග්න හෝ චන්ද්‍ර රාශි එකිනෙකට කේන්ද්‍ර/ත්‍රිකෝණ වීම දිගු කාලීන ගැලපීමට හිතකර ලෙස සලකනු ලැබේ — '
                 f'මෙහි D9 ලග්න අතර දුර {(inv[v9B["La"]] - inv[v9A["La"]]) % 12 + 1} වැන්න.</p>')

    # --- 6 timing overlap
    H.append('<h2>6. විවාහ කාල ගැලපීම</h2>')
    now_utc = now_local.astimezone(timezone.utc)
    horizon = now_utc + timedelta(days=int(6 * 365.25))
    def key_planets(d_, P_, ls_):
        s = {jc.SIGN_LORD[(ls_ + 6) % 12], "Ve"}
        dk = d_["chara_karakas"].get("DK", {}).get("planet")
        if dk:
            s.add(dk)
        ul = d_["arudhas"].get("UL")
        if ul:
            s.add(jc.SIGN_LORD[inv[ul]])
        return s
    kA, kB = key_planets(dA, PA, lsA), key_planets(dB, PB, lsB)
    def windows(d_, keys):
        out = []
        for m in d_["vimshottari"]["mahadashas"]:
            for s_ in m.get("sub", []):
                st, en = datetime.fromisoformat(s_["start"]), datetime.fromisoformat(s_["end"])
                if en > now_utc and st < horizon and (m["lord"] in keys or s_["lord"] in keys):
                    out.append((max(st, now_utc), min(en, horizon), f"{PLANET_SI[m['lord']]}/{PLANET_SI[s_['lord']]}"))
        return out
    wA, wB = windows(dA, kA), windows(dB, kB)
    H.append(f'<p class="small">විවාහ කාරක ග්‍රහයන් — {esc(nameA)}: {", ".join(PLANET_SI[p] for p in sorted(kA))}; '
             f'{esc(nameB)}: {", ".join(PLANET_SI[p] for p in sorted(kB))}.</p>')
    overlap = []
    for s1, e1, l1 in wA:
        for s2, e2, l2 in wB:
            s, e = max(s1, s2), min(e1, e2)
            if (e - s).days > 45:
                overlap.append((s, e, l1, l2))
    overlap.sort()
    if overlap:
        H.append("<table><tr><th>කවුළුව</th><th>" + esc(nameA) + " දශාව</th><th>" + esc(nameB) + " දශාව</th><th>දින</th></tr>"
                 + "".join(f"<tr><td>{s.astimezone(ZoneInfo(tz)).strftime('%Y-%m')} → {e.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</td>"
                           f"<td>{l1}</td><td>{l2}</td><td>{(e - s).days}</td></tr>" for s, e, l1, l2 in overlap[:12]) + "</table>")
        H.append('<p class="small">දෙදෙනාගේම විවාහ කාරක දශා එකවර ක්‍රියාත්මක වන කාල ඉහත දැක්වේ. ගුරු ගෝචරය එම කාලවලට ගැලපේද යන්නත් බලන්න.</p>')
    else:
        H.append("<p>ඉදිරි වසර 6 තුළ දෙදෙනාගේම විවාහ කාරක දශා එකවර ක්‍රියාත්මක වන පැහැදිලි කවුළුවක් නැත; "
                 "එක් අයෙකුගේ දශාව සහ ගුරු ගෝචරය එකට ගැලපෙන කාල බලන්න.</p>")
    if wA or wB:
        H.append("<h3>එක් එක් අයගේ කවුළු</h3><table><tr><th>අය</th><th>දශාව</th><th>ආරම්භය</th><th>අවසානය</th></tr>"
                 + "".join(f"<tr><td>{esc(nameA)}</td><td>{l}</td><td>{s.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</td>"
                           f"<td>{e.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</td></tr>" for s, e, l in wA[:8])
                 + "".join(f"<tr><td>{esc(nameB)}</td><td>{l}</td><td>{s.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</td>"
                           f"<td>{e.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</td></tr>" for s, e, l in wB[:8]) + "</table>")

    # --- 7 summary
    H.append("<h2>7. සමස්ත විග්‍රහය</h2>")
    pts = []
    pts.append(f"අෂ්ටකූට {total}/36 — {verdict}.")
    pts.append(f"සංයෝජනය: හිතකර ස්ථාන {good}, ඝර්ෂණ ස්ථාන {bad}.")
    dosha_open = [k["name"] for k in comp["kootas"] if "dosha" in k["detail"].lower() and "cancel" not in k["detail"].lower()]
    pts.append("නිෂ්ප්‍රභ නොවූ දෝෂ: " + (", ".join("භකූට" if x == "Bhakoot" else "නාඩි" for x in dosha_open) if dosha_open else "නැත") + ".")
    pts.append("විවාහ කාල ගැලපීම: " + (f"ඉදිරි වසර 6 තුළ පොදු කවුළු {len(overlap)}ක්." if overlap else "පැහැදිලි පොදු කවුළුවක් නැත."))
    H.append('<div class="box">' + "<br>".join(pts) + "</div>")
    H.append(note_block(notes, "summary", "ජ්‍යොතිෂවේදියාගේ විග්‍රහය"))
    H.append(note_block(notes, "upcoming", "කාලය පිළිබඳ යෝජනා"))
    H.append(disclaimer_block("අෂ්ටකූට ගුණ මිලන, උපපද ලග්නය සහ චර කාරක — P.V.R. Narasimha Rao, ch. 6, 9, 26. වාර්තා වර්ගය D2. "
                              "මේ වාර්තාව ගැලපීම පිළිබඳ ජ්‍යොතිෂමය දෘෂ්ටි කෝණයක් පමණි; විවාහ තීරණය දෙදෙනාගේ අවබෝධය, "
                              "සන්නිවේදනය සහ පවුල්වල එකඟතාව මත පදනම් විය යුතුයි."))
    return "\n".join(H)


# ================================================================ E1 — Janma Kala Shuddhi (birth-time rectification)
EVENT_TYPES = {
    "marriage": ("විවාහය", [7, 2, 11], ["Ve"], "DK", "UL"),
    "job": ("රැකියාව ආරම්භය / වෙනස", [10, 6, 11, 2], ["Sa"], "AmK", "A10"),
    "education": ("අධ්‍යාපන පියවරක්", [4, 5, 9], ["Me", "Ju"], "AK", "A4"),
    "child": ("දරුවෙකු ලැබීම", [5, 2, 11, 9], ["Ju"], "PK", "A5"),
    "foreign": ("විදේශගත වීම", [12, 9, 3], ["Ra"], "AK", "A12"),
    "property": ("නිවසක්/ඉඩමක්/වාහනයක්", [4, 11, 2], ["Ma", "Ve"], "MK", "A4"),
    "loss": ("ලොකු අලාභයක්/බාධකයක්", [6, 8, 12], ["Sa"], "GK", "A8"),
    "parent": ("දෙමව්පියන් සම්බන්ධ සිදුවීමක්", [4, 9], ["Mo", "Su"], "MK", "A4"),
    "health": ("සෞඛ්‍ය සිදුවීමක්", [6, 8, 1], ["Sa"], "GK", "A6"),
    "move": ("පදිංචිය වෙනස් වීම", [4, 12, 3], ["Mo"], "MK", "A4"),
}


def rectify_scan(a, events, span_min, step_min, workdir):
    """Score candidate birth times: for each event, does the running Vimshottari AD/PD lord
    rule or occupy a house relevant to that event? Returns rows sorted by time."""
    base_dt = datetime.strptime(f"{a.date} {a.time}", "%Y-%m-%d %H:%M")
    out = []
    for off in range(-span_min, span_min + 1, step_min):
        dt = base_dt + timedelta(minutes=off)
        jd, _ = jc.to_jd_ut(dt, a.tz)
        pos, _ = jc.compute_positions(jd)
        lag = jc.compute_lagna(jd, a.lat, a.lon)
        ls = jc.sign_of(lag)
        birth_utc = jc.jd_to_datetime(jd)
        lord0, bal, mds = jc.vimshottari(pos["Mo"]["lon"], birth_utc, 3, jc.YEAR_DAYS)
        score, detail = 0, []
        for ev in events:
            etype, edate = ev["type"], ev["date"]
            try:
                ed = datetime.strptime(edate, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            houses, karakas, ck, ar = EVENT_TYPES[etype][1:]
            hit, why = 0, []
            md = next((m for m in mds if m["start"] <= ed < m["end"]), None)
            if not md:
                continue
            ad = next((x for x in md.get("sub", []) if x["start"] <= ed < x["end"]), None)
            pd_ = next((x for x in ad.get("sub", []) if x["start"] <= ed < x["end"]), None) if ad and ad.get("sub") else None
            for lvl, node, w in (("MD", md, 1), ("AD", ad, 2), ("PD", pd_, 1)):
                if not node:
                    continue
                L = node["lord"]
                lh = jc.house_from(ls, jc.sign_of(pos[L]["lon"]))
                owns = [h for h in range(1, 13) if jc.SIGN_LORD[(ls + h - 1) % 12] == L]
                if lh in houses or any(h in houses for h in owns):
                    hit += w
                    why.append(f"{lvl} {PLANET_SI[L]}")
                elif L in karakas:
                    hit += w
                    why.append(f"{lvl} {PLANET_SI[L]} (කාරක)")
            score += hit
            detail.append((etype, edate, hit, ", ".join(why) or "—"))
        out.append({"off": off, "time": dt.strftime("%H:%M"), "lagna": ls, "lagna_deg": jc.deg_in_sign(lag),
                    "d9": jc.varga_sign(lag, 9), "d10": jc.varga_sign(lag, 10),
                    "score": score, "detail": detail, "nav": jc.varga_sign(lag, 9)})
    return out


def build_e1(d, a, notes, now_local, events, scan):
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    tz = a.tz
    best = max(s["score"] for s in scan) if scan else 0
    tops = [s for s in scan if s["score"] == best]
    # contiguous windows of top score
    wins, cur = [], None
    for s in scan:
        if s["score"] == best:
            if cur and s["off"] - cur[-1]["off"] <= (scan[1]["off"] - scan[0]["off"] if len(scan) > 1 else 1):
                cur.append(s)
            else:
                if cur:
                    wins.append(cur)
                cur = [s]
        else:
            if cur:
                wins.append(cur)
                cur = None
    if cur:
        wins.append(cur)
    labels = {ls: ["ලග්න"]}
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        labels.setdefault(P[c]["sign_idx"], []).append(PLANET_SI[c])
    H = [f'''<div class="cover" style="padding-top:12mm"><div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">ජන්ම කාල ශුද්ධි වාර්තාව</h1><div class="sub">උපන් වේලාව නිවැරදි කිරීම (E1)</div>
      <div class="name">{esc(a.name)}</div>
      <div class="muted">දෙන ලද වේලාව {esc(a.time)} · {esc(a.date)} · {esc(a.place or "")}</div>
      <div style="margin:12pt auto 0 auto; width:100mm">{south_indian_html_si(labels, "දෙන ලද වේලාවට D1", 100)}</div></div>''']
    H.append('<div class="pb"></div><h2>1. ක්‍රමවේදය</h2>')
    H.append('<div class="box">උපන් වේලාව මිනිත්තු කිහිපයකින් වෙනස් වූ විට ලග්නය, නවාංශක ලග්නය සහ දශා ආරම්භය වෙනස් වේ. '
             'මේ වාර්තාවේ කරන්නේ: (1) දෙන ලද වේලාව වටා නියමිත පරාසයක් scan කර, (2) ඔබ දුන් පසුගිය සිදුවීම් එක් එක් '
             'වේලාවකට අදාළ දශා සමඟ ගැලපේද බලා, (3) වැඩිම ගැලපීම ලැබෙන කාල කවුළු ඉදිරිපත් කිරීමයි.<br><br>'
             '<b>වැදගත්:</b> විම්ශෝත්තරී දශා ආරම්භය චන්ද්‍රගේ ස්ථානය මත රඳා පවතින නිසා පැයක් ඇතුළත එය බොහෝ දුරට එකමයි. '
             'වෙනස් වන්නේ <b>ලග්නය</b> — එබැවින් දශාධිපතීන් කුමන භාවවලට අධිපති වෙනවාද, කුමන භාවවල සිටිනවාද යන්නයි. '
             'ලකුණු වෙනස්කම් එන්නේ එතැනින්.<br><br>'
             '<b>මෙය ඇස්තමේන්තුවක්</b> — රෝහල් වාර්තාවක් තරම් නිශ්චිත නොවේ. සිදුවීම් වැඩි වන තරමට නිරවද්‍යතාව වැඩි වේ.</div>')
    H.append("<h2>2. ඔබ දුන් සිදුවීම්</h2><table><tr><th>#</th><th>සිදුවීම</th><th>දිනය</th><th>අදාළ භාව</th></tr>"
             + "".join(f"<tr><td>{i + 1}</td><td>{EVENT_TYPES[e['type']][0]}{(' — ' + esc(e['note'])) if e.get('note') else ''}</td>"
                       f"<td>{esc(e['date'])}</td><td>{', '.join(str(h) for h in EVENT_TYPES[e['type']][1])}</td></tr>"
                       for i, e in enumerate(events)) + "</table>")
    H.append('<div class="pb"></div><h2>3. වේලා scan එක</h2>')
    rows = []
    for s in scan:
        mark = " class=cur" if s["score"] == best else ""
        rows.append(f"<tr{mark}><td>{s['time']}</td><td>{s['off']:+d}</td><td>{SIGN_SI[s['lagna']]} {dms(s['lagna_deg'])}</td>"
                    f"<td>{SIGN_SI[s['d9']]}</td><td>{SIGN_SI[s['d10']]}</td><td><b>{s['score']}</b></td></tr>")
    H.append("<table><tr><th>වේලාව</th><th>වෙනස</th><th>ලග්නය</th><th>D9 ලග්නය</th><th>D10 ලග්නය</th><th>ගැලපීම් ලකුණු</th></tr>"
             + "".join(rows) + "</table>")
    H.append('<p class="small muted">ලකුණු = සිදුවීම් දිනවලදී ක්‍රියාත්මක වූ මහා/අන්තර්/ප්‍රත්‍යන්තර දශාධිපතීන් එම සිදුවීමට අදාළ '
             'භාවවලට සම්බන්ධ වන ගණන (අන්තර් දශාවට බර 2, අනෙක් දෙකට 1).</p>')
    H.append("<h2>4. වඩාත් ගැලපෙන කාල කවුළු</h2>")
    if wins:
        rows = []
        for w in wins:
            t0, t1 = w[0], w[-1]
            rows.append(f"<tr><td>{t0['time']} – {t1['time']}</td><td>{SIGN_SI[t0['lagna']]}"
                        + (f" → {SIGN_SI[t1['lagna']]}" if t1["lagna"] != t0["lagna"] else "")
                        + f"</td><td>{SIGN_SI[t0['d9']]}" + (f" → {SIGN_SI[t1['d9']]}" if t1["d9"] != t0["d9"] else "")
                        + f"</td><td>{best}</td></tr>")
        H.append("<table><tr><th>කාල කවුළුව</th><th>ලග්නය</th><th>D9 ලග්නය</th><th>ලකුණු</th></tr>" + "".join(rows) + "</table>")
        given = next((s for s in scan if s["off"] == 0), None)
        if given:
            H.append(f'<div class="box">දෙන ලද වේලාවේ ({given["time"]}) ලකුණු <b>{given["score"]}</b>; උපරිමය <b>{best}</b>. '
                     + ("දෙන ලද වේලාව දැනටමත් වඩාත් ගැලපෙන කාණ්ඩයේ ය — වෙනසක් අවශ්‍ය නොවේ."
                        if given["score"] == best else
                        f"වඩාත් ගැලපෙන කවුළුව {wins[0][0]['time']} – {wins[0][-1]['time']} අතරයි. "
                        "මෙය යෝජනාවක් පමණි; තවත් සිදුවීම් එකතු කිරීමෙන් නිරවද්‍යතාව වැඩි කරගත හැක.") + "</div>")
    else:
        H.append("<p>scan පරාසය තුළ වෙනසක් හඳුනාගත නොහැක.</p>")
    H.append('<div class="pb"></div><h2>5. සිදුවීම් අනුව විස්තරය</h2>')
    show = [s for s in scan if s["score"] == best][:1] + ([next(s for s in scan if s["off"] == 0)] if best != (next((s["score"] for s in scan if s["off"] == 0), None)) else [])
    for s in show:
        H.append(f"<h3>වේලාව {s['time']} ({s['off']:+d} මිනිත්තු) — ලග්නය {SIGN_SI[s['lagna']]}</h3>")
        H.append("<table><tr><th>සිදුවීම</th><th>දිනය</th><th>ලකුණු</th><th>ගැලපෙන දශාධිපතීන්</th></tr>"
                 + "".join(f"<tr><td>{EVENT_TYPES[t][0]}</td><td>{dt}</td><td>{hit}</td><td>{esc(why)}</td></tr>"
                           for t, dt, hit, why in s["detail"]) + "</table>")
    H.append("<h2>6. ඊළඟ පියවර</h2><ul>"
             "<li>හැකි නම් රෝහල් උපන් සහතිකයේ වේලාව සොයා ගන්න — එය හොඳම මූලාශ්‍රයයි.</li>"
             "<li>තවත් පැහැදිලි දින සහිත සිදුවීම් 3–5ක් එකතු කළොත් කවුළුව පටු කර ගත හැක.</li>"
             "<li>වේලාව නිශ්චිත වන තුරු D9, D10, D60 මත පදනම් වූ අර්ථකථන ප්‍රවේශමෙන් කියවන්න; "
             "D1, දශා සහ ගෝචරය සාපේක්ෂව ස්ථාවරයි.</li></ul>")
    H.append(note_block(notes, "summary", "ජ්‍යොතිෂවේදියාගේ විග්‍රහය"))
    H.append(disclaimer_block("ජන්ම කාල ශුද්ධි — විම්ශෝත්තරී දශා සහ භාව කාරකත්ව මත පදනම් වූ ඇස්තමේන්තු ක්‍රමයක්. "
                              "වාර්තා වර්ගය E1. මෙය සම්භාවිතාව මත පදනම් වූ යෝජනාවක් මිස නිශ්චිත වේලාවක් නොවේ."))
    return "\n".join(H)


# ================================================================ M1 — Muhurta (නැකත්)
MUHURTA_TASK_SI = {
    "wedding": "විවාහ මංගල්‍යය", "griha_pravesha": "ගෘහ ප්‍රවේශය (නව නිවසට ඇතුළු වීම)",
    "house_construction": "නිවස ඉදිකිරීම ආරම්භය", "naming": "නම් තැබීම", "annaprashana": "බත් කැවීම",
    "vidyarambha": "අකුරු කියවීම / අධ්‍යාපන ආරම්භය", "upanayana": "උපනයනය", "idol_installation": "ප්‍රතිමා පිහිටුවීම",
    "job": "නව රැකියාවක් ආරම්භය", "business": "ව්‍යාපාරයක් ආරම්භය", "vehicle": "වාහනයක් ගැනීම/පාවිච්චිය",
    "property": "දේපලක් මිලදී ගැනීම", "travel": "ගමනක් ආරම්භය", "general": "සාමාන්‍ය සුබ ආරම්භයක්",
}


def parse_muhurta_output(text):
    """Parse the engine's --muhurta text output into rows (fixed-width columns)."""
    rows, best, note = [], [], ""
    mode = None
    for ln in text.split("\n"):
        if ln.startswith("Task note:"):
            note = ln.split(":", 1)[1].strip()
            continue
        if "WINDOWS (score" in ln:
            mode = "rows"
            continue
        if ln.startswith("BEST WINDOW DETAIL"):
            mode = "best"
        if mode == "rows":
            if ln.strip().startswith("date "):
                continue
            m = re.match(r"\s{2}(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})-(\d{2}:\d{2})\s+(.*?)\s\s+(-?\d+)\s\s(.*)$", ln)
            if m:
                mid = re.split(r"\s{2,}", m.group(4).strip())
                while len(mid) < 4:
                    mid.append("")
                rows.append(dict(date=m.group(1), t0=m.group(2), t1=m.group(3), lagna=mid[0], tithi=mid[1],
                                 vara=mid[2], nak=mid[3], hora=mid[4] if len(mid) > 4 else "",
                                 score=int(m.group(5)), notes=m.group(6).strip()))
            elif ln.strip() and not ln.startswith("  "):
                mode = None
        if mode == "best" and ln.strip():
            best.append(ln.rstrip())
    return rows, best, note


def build_m1(a, notes, now_local, task, out_text, natal=None):
    rows, best, note = parse_muhurta_output(out_text)
    tsi = MUHURTA_TASK_SI.get(task, task)
    H = [f'''<div class="cover" style="padding-top:12mm"><div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">මුහූර්ත වාර්තාව</h1><div class="sub">සුබ මොහොත් (M1) — {esc(tsi)}</div>
      <div class="name" style="font-size:15pt">{esc(a.name)}</div>
      <div class="muted">පරාසය: {esc(a.muhurta_from)} සිට {esc(a.muhurta_to)} දක්වා · {esc(a.place or "")}</div>
      <div style="margin-top:18pt" class="muted">සොයාගත් සුබ කවුළු: <b>{len(rows)}</b></div></div>''']
    H.append('<div class="pb"></div><h2>1. ක්‍රමවේදය</h2>')
    H.append('<div class="box">මෙහි භාවිත කර ඇත්තේ පරාශර සම්ප්‍රදායේ මුහූර්ත නියම (P.V.R. Narasimha Rao, ch. 36, වගුව 79) ය: '
             'කාර්යයට ගැලපෙන තිථි, වාර, නක්ෂත්‍ර සහ ලග්න; අදාළ භාවය හිස්ව තිබීම. ඊට අමතරව තාරා බලය (වගුව 64), '
             'හෝරාධිපති, කරණය සහ අදාළ භාවවල ග්‍රහ ශක්තිය අනුව ලකුණු දී ඇත.<br><br>'
             '<b>වැදගත්:</b> ලංකාවේ පාරම්පරික ලිත් නැකත් ක්‍රමය මෙයට වඩා වෙනස් ක්‍රමයකි (රාහු කාලය, සුබ දිශාව ආදිය). '
             'මේ වාර්තාව ලිත් නැකතට <b>දෙවන මතයක්</b> ලෙස සලකන්න; දෙකම එකට බැලීම හොඳයි.</div>')
    if note:
        H.append(f'<p class="small muted">කාර්යයට අදාළ විශේෂ නියමය: {esc(si_text(note))}</p>')
    H.append(f"<h2>2. සුබ කවුළු — {esc(tsi)}</h2>")
    if rows:
        H.append("<table><tr><th>දිනය</th><th>වේලාව</th><th>ලග්නය</th><th>තිථි</th><th>වාරය</th><th>නැකත</th><th>හෝරා</th><th>ලකුණු</th><th>සටහන්</th></tr>"
                 + "".join(f"<tr{' class=cur' if r['score'] == max(x['score'] for x in rows) else ''}>"
                           f"<td>{r['date']}</td><td>{r['t0']}–{r['t1']}</td><td>{esc(si_text(r['lagna']))}</td>"
                           f"<td>{esc(si_text(r['tithi']))}</td><td>{esc(VARA_SI2.get(r['vara'], si_text(r['vara'])))}</td><td>{esc(si_text(r['nak']))}</td>"
                           f"<td>{esc(si_text(r['hora']))}</td><td>{r['score']}</td>"
                           f"<td class='small'>{esc(si_text(r['notes'])[:70])}</td></tr>" for r in rows) + "</table>")
        H.append('<p class="small muted">ලකුණු වැඩි කවුළු වඩාත් සුබ ලෙස සලකනු ලැබේ. කවුළුවක් තුළ ඕනෑම මොහොතක් ගත හැක; '
                 'කවුළුවේ මැද වඩාත් ආරක්ෂිතයි (ලග්න මාරුවෙන් දුරින්).</p>')
    else:
        H.append("<p>දෙන ලද පරාසය තුළ සියලු නියම සපුරන කවුළුවක් හමු නොවීය. දින පරාසය පුළුල් කිරීම හෝ "
                 "වේලා පරාසය 0–24 දක්වා විහිදුවීම උත්සාහ කරන්න.</p>")
    if best:
        H.append("<h2>3. හොඳම කවුළුවේ කේන්දරය</h2>")
        H.append('<pre class="small" style="white-space:pre-wrap; font-family:\'Noto Sans Sinhala\', \'Noto Sans\', monospace; background:#faf6ee; padding:8pt; border:1px solid #e4dccb">'
                 + esc(si_text("\n".join(best[:16]))) + "</pre>")
    H.append("<h2>4. ප්‍රායෝගිකව</h2><ul>"
             "<li>කවුළුව තුළ කාර්යය <b>ආරම්භ</b> කිරීම ප්‍රමාණවත් — මුළු කාර්යයම එතුළ අවසන් විය යුතු නැත.</li>"
             "<li>දින දෙකක් සමාන ලකුණු ගත්තොත්, ඔබට ප්‍රායෝගිකව පහසු දිනය තෝරන්න.</li>"
             "<li>ලිත් නැකතක් ද ගන්නවා නම්, දෙකේම පොදු කාලයක් තෝරා ගැනීම හොඳයි.</li></ul>")
    H.append(note_block(notes, "summary", "ජ්‍යොතිෂවේදියාගේ සටහන"))
    H.append(disclaimer_block("මුහූර්ත (නැකත්) — P.V.R. Narasimha Rao, ch. 36, වගුව 79 සහ 64. වාර්තා වර්ගය M1. "
                              "මෙය පාරම්පරික ලිත් නැකතට විකල්ප දෙවන මතයකි."))
    return "\n".join(H)


# ================================================================ N — Nama nakshatra (නම් තැබීම)
def build_n(d, a, notes, now_local):
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    moon = P["Mo"]
    nm = jc.nama_nakshatra(moon["lon"])
    nak_i = jc.NAKSHATRAS.index(moon["nakshatra"])
    labels = {ls: ["ලග්න"]}
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        labels.setdefault(P[c]["sign_idx"], []).append(PLANET_SI[c])
    H = [f'''<div class="cover" style="padding-top:14mm"><div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:16pt">නාම නක්ෂත්‍ර වාර්තාව</h1><div class="sub">නම් තැබීම සඳහා අකුරු (N)</div>
      <div class="name">{esc(a.name)}</div>
      <div class="muted">{esc(a.date)} · {esc(a.time)} · {esc(a.place or "")}</div>
      <div style="margin:16pt auto; font-size:34pt; color:#6b1010"><b>{esc(nm["sinhala"])}</b></div>
      <div class="muted">{NAK_SI[nak_i]} නැකත · {nm["pada"]} වන පාදය</div>
      <div style="margin:14pt auto 0 auto; width:94mm">{south_indian_html_si(labels, "D1 · රාශි චක්‍රය", 94)}</div></div>''']
    H.append('<div class="pb"></div><h2>1. නාම අකුර</h2>')
    H.append("<table>"
             f"<tr><td style='width:34%'><b>ජන්ම නැකත</b></td><td>{NAK_SI[nak_i]} ({esc(moon['nakshatra'])})</td></tr>"
             f"<tr><td><b>පාදය</b></td><td>{nm['pada']} වන පාදය</td></tr>"
             f"<tr><td><b>චන්ද්‍ර රාශිය</b></td><td>{SIGN_SI[moon['sign_idx']]}</td></tr>"
             f"<tr><td><b>නාම අකුර</b></td><td style='font-size:15pt'><b>{esc(nm['sinhala'])}</b> ({esc(nm['syllable'])})</td></tr>"
             "</table>")
    H.append(f'<div class="box">සම්ප්‍රදාය අනුව නම <b>{esc(nm["sinhala"])}</b> යන අකුරින් පටන් ගැනීම සුබ ලෙස සලකනු ලැබේ. '
             f'මෙය චන්ද්‍ර සිටින නැකතේ පාදය අනුව තීරණය වේ.</div>')
    H.append(f"<h2>2. {NAK_SI[nak_i]} නැකතේ පාද හතරේ අකුරු</h2><table><tr><th>පාදය</th><th>අකුර</th><th>ලතින්</th></tr>"
             + "".join(f"<tr{' class=cur' if i + 1 == nm['pada'] else ''}><td>{i + 1}</td><td style='font-size:13pt'>{esc(si_)}</td><td>{esc(la)}</td></tr>"
                       for i, (la, si_) in enumerate(nm["all_padas"])) + "</table>")
    H.append('<p class="small muted">මූලාශ්‍රය: අවකහඩ චක්‍රය (සම්භාව්‍ය නාම නක්ෂත්‍ර වගුව). මෙය ව්‍යාකරණ නීතියක් නොව සම්ප්‍රදායික යෝජනාවකි; '
             'නමේ අර්ථය සහ පවුලේ කැමැත්තද සලකා බලන්න.</p>')
    H.append("<h2>3. නම් තැබීමේ මොහොත</h2>")
    H.append('<p>නම් තැබීමේ උත්සවයට සුබ මොහොතක් අවශ්‍ය නම්, අපගේ <b>මුහූර්ත වාර්තාව (M1 — නම් තැබීම)</b> වෙන් වශයෙන් ලබාගත හැක. '
             'එහි තිථි, වාර, නක්ෂත්‍ර සහ ලග්නය අනුව සුබ කවුළු දක්වා ඇත.</p>')
    H.append(note_block(notes, "summary", "ජ්‍යොතිෂවේදියාගේ සටහන"))
    H.append(disclaimer_block("නාම නක්ෂත්‍රය — අවකහඩ චක්‍රය (සම්භාව්‍ය සම්ප්‍රදාය; ව්‍යාපෘතියේ ප්‍රධාන ග්‍රන්ථයේ නොමැත). වාර්තා වර්ගය N."))
    return "\n".join(H)


# ================================================================ D3 — Multi-match comparison
def build_d3(dA, partners, a, notes, now_local):
    """partners: list of (name, args-like dict, calc JSON with compatibility relative to A)."""
    PA, lsA = dA["planets"], dA["lagna"]["sign_idx"]
    inv = {s: i for i, s in enumerate(jc.SIGNS)}
    labels = {lsA: ["ලග්න"]}
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        labels.setdefault(PA[c]["sign_idx"], []).append(PLANET_SI[c])
    H = [f'''<div class="cover" style="padding-top:12mm"><div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">පොරොන්දම් සංසන්දනය</h1><div class="sub">යෝජනා කිහිපයක් එකට (D3)</div>
      <div class="name">{esc(a.name)}</div>
      <div class="muted">සංසන්දනය කරන යෝජනා: {len(partners)}</div>
      <div style="margin:14pt auto 0 auto; width:96mm">{south_indian_html_si(labels, "D1 · රාශි චක්‍රය", 96)}</div></div>''']
    H.append('<div class="pb"></div><h2>1. සාරාංශ සංසන්දනය</h2>')
    rows = []
    for nm_, meta, dj in partners:
        comp = dj["compatibility"]
        tot = comp["ashtakoota_total"]
        doshas = [k["name"] for k in comp["kootas"] if "dosha" in k["detail"].lower() and "cancel" not in k["detail"].lower()]
        PB = dj["_partner_chart"]["planets"]
        lsB = dj["_partner_chart"]["lagna"]["sign_idx"]
        good = sum(1 for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]
                   if jc.house_from(lsB, PA[c]["sign_idx"]) in (1, 4, 5, 7, 9, 11)) \
            + sum(1 for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]
                  if jc.house_from(lsA, PB[c]["sign_idx"]) in (1, 4, 5, 7, 9, 11))
        bad = sum(1 for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]
                  if jc.house_from(lsB, PA[c]["sign_idx"]) in (6, 8, 12)) \
            + sum(1 for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]
                  if jc.house_from(lsA, PB[c]["sign_idx"]) in (6, 8, 12))
        mh, mc = mangal_check(PB, lsB)
        rows.append(dict(name=nm_, meta=meta, total=tot, kootas=comp["kootas"], doshas=doshas, good=good, bad=bad,
                         lagna=lsB, moon=PB["Mo"]["sign_idx"], nak=PB["Mo"]["nakshatra"], mangal=bool(mh), mangal_c=bool(mc)))
    rows.sort(key=lambda r: (-r["total"], r["bad"] - r["good"]))
    H.append("<table><tr><th>යෝජනාව</th><th>උපන් දිනය</th><th>ලග්නය</th><th>චන්ද්‍ර රාශිය</th><th>අෂ්ටකූට</th>"
             "<th>නිෂ්ප්‍රභ නොවූ දෝෂ</th><th>සංයෝජනය (හිතකර/ඝර්ෂණ)</th><th>කුජ දෝෂ</th></tr>"
             + "".join(f"<tr{' class=cur' if i == 0 else ''}><td><b>{esc(r['name'])}</b></td><td>{esc(r['meta']['date'])}</td>"
                       f"<td>{SIGN_SI[r['lagna']]}</td><td>{SIGN_SI[r['moon']]}</td><td><b>{r['total']:g}</b>/36</td>"
                       f"<td>{', '.join('භකූට' if x == 'Bhakoot' else 'නාඩි' for x in r['doshas']) or '—'}</td>"
                       f"<td>{r['good']} / {r['bad']}</td>"
                       f"<td>{'ඇත' + (' (නිෂ්ප්‍රභ සාධක ඇත)' if r['mangal_c'] else '') if r['mangal'] else 'නැත'}</td></tr>"
                       for i, r in enumerate(rows)) + "</table>")
    H.append('<p class="small muted">වගුව අෂ්ටකූට ලකුණු අනුව පෙළගස්වා ඇත. ලකුණු එකතුව පමණක් නොව දෝෂ සහ සංයෝජනයද බලන්න.</p>')
    H.append('<div class="pb"></div><h2>2. කූට අනුව විස්තර</h2>')
    knames = [k["name"] for k in rows[0]["kootas"]]
    H.append("<table><tr><th>කූටය</th>" + "".join(f"<th>{esc(r['name'])}</th>" for r in rows) + "</tr>"
             + "".join("<tr><td>" + KOOTA_SI.get(kn, (kn, ""))[0] + "</td>"
                       + "".join(f"<td>{next(k['points'] for k in r['kootas'] if k['name'] == kn)} / "
                                 f"{next(k['max'] for k in r['kootas'] if k['name'] == kn)}</td>" for r in rows) + "</tr>"
                       for kn in knames)
             + "<tr class='cur'><td><b>එකතුව</b></td>" + "".join(f"<td><b>{r['total']:g}/36</b></td>" for r in rows) + "</tr></table>")
    H.append('<div class="note"><div class="lbl">තීරණය ගැන</div><p>ලකුණු වැඩිම යෝජනාව හොඳම එක යැයි කියන්නට බැහැ. '
             'නිෂ්ප්‍රභ නොවූ දෝෂ, සංයෝජනයේ ඝර්ෂණ ස්ථාන සහ දෙදෙනාගේ දශා ගැලපීම එකට සලකා බැලිය යුතුයි. '
             'ඉහළම යෝජනා දෙක සඳහා සම්පූර්ණ පොරොන්දම් වාර්තාවක් (D2) ලබා ගැනීම යෝජනා කරමු.</p></div>')
    H.append(note_block(notes, "summary", "ජ්‍යොතිෂවේදියාගේ විග්‍රහය"))
    H.append(disclaimer_block("අෂ්ටකූට ගුණ මිලන — P.V.R. Narasimha Rao, ch. 26. වාර්තා වර්ගය D3. "
                              "විවාහ තීරණය දෙදෙනාගේ අවබෝධය සහ පවුල්වල එකඟතාව මත පදනම් විය යුතුයි."))
    return "\n".join(H)


def _ttf_revision(path):
    """fontRevision from the sfnt 'head' table — stdlib only, no fontTools needed."""
    try:
        with open(path, "rb") as f:
            f.seek(4)
            num = struct.unpack(">H", f.read(2))[0]
            f.seek(12)
            for _ in range(num):
                tag, _chk, off, _len = struct.unpack(">4sIII", f.read(16))
                if tag == b"head":
                    f.seek(off + 4)
                    return struct.unpack(">i", f.read(4))[0] / 65536.0
    except Exception:
        pass
    return None


def check_fonts():
    """Sinhala shapes silently wrong with the old Noto build, so fail loudly instead."""
    d, msgs = fontdir_global(), []
    reg = os.path.join(d, "NotoSansSinhala.ttf")
    if not os.path.exists(reg):
        msgs.append(f"!! {reg} නැත — සිංහල අකුරු වැරදියට render වේ.")
    else:
        rev = _ttf_revision(reg)
        if rev is not None and rev < 3.0:
            msgs.append(f"!! NotoSansSinhala.ttf අනුවාදය {rev:.3f} — මෙය පැරණි (USE shaper එකට නොගැලපේ); "
                        "ේ/ෛ/ා වැනි ස්වර ලකුණු අකුර මතට එකතු වී overlap වේ.\n"
                        "   notofonts.github.io repo එකේ fonts/NotoSansSinhala/hinted/ttf/ වෙතින් "
                        "(v3.000+) බාගන්න.")
    for extra in ("NotoSansSinhala-Bold.ttf", "NotoSans.ttf", "NotoSans-Bold.ttf", "NotoSansSymbols2.ttf", "NotoSansMath.ttf"):
        if not os.path.exists(os.path.join(d, extra)):
            msgs.append(f"   සටහන: {extra} නැත — ඒ බර සඳහා fallback එකක් භාවිත වේ.")
    if msgs:
        print("\n".join(msgs), file=sys.stderr)


def fontdir_global():
    return os.path.join(HERE, "fonts")


def font_uri(fontdir=None):
    """file:// URI of the fonts folder for @font-face. Path.as_uri() gives file:///D:/... on Windows;
    plain "file://" + path would turn the drive letter into a URL host and the fonts would silently fail to load."""
    return Path(fontdir or fontdir_global()).as_uri()


# jyotisha_calc.py runs as a child process; make it print UTF-8 whatever the console code page is
CHILD_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}


# ---------------------------------------------------------------------------
# Visual QA (--qa). Sinhala shaping failures produce NO error anywhere in the
# stack, so the only defences are (a) measuring a rendered probe string and
# (b) looking at the pages. This module does both and writes page PNGs.
# ---------------------------------------------------------------------------
QA_PROBE = "කේන්දරේ ගෝචර ශනිගේ සඩේ සති ජ්‍යොතිෂ ඉන්සයිට්"
QA_PROBE_PT = 12
QA_PROBE_REF = 26.46    # rendered width / font-size with NotoSansSinhala v3.000 + HarfBuzz 8 (measured 2026-10-20)
QA_PROBE_TOL = 0.05     # v2.002 font gives -16 %, a non-Sinhala fallback font gives -9.5 %
# Second probe, dense in ු/ූ and the rakaransaya (්‍ර). An old HarfBuzz (e.g. the 2022 GTK3 runtime for
# Windows) leaves ~0.7 em of extra space after each of these clusters: barely visible in QA_PROBE, but
# a large width change here.
QA_PROBE_MARKS = "මූලික ග්‍රහ ක්‍රමය පිටුව සම්පූර්ණ ප්‍රශ්න"
QA_PROBE_MARKS_REF = 18.99  # same font + HarfBuzz 14.5 (measured 2026-10-22); old HarfBuzz est. +20 %
QA_PROBES = ((QA_PROBE, QA_PROBE_REF), (QA_PROBE_MARKS, QA_PROBE_MARKS_REF))
QA_ALLOWED_FONTS = ("Noto-Sans-Sinhala", "Noto-Sans-Sinhala-Bold", "Noto-Sans", "Noto-Sans-Bold", "Noto-Sans-Symbols-2", "Noto-Sans-Symbols-2-Bold", "Noto-Sans-Math", "Noto-Sans-Math-Bold",
                    "NotoSansSinhala", "NotoSansSinhala-Bold", "NotoSans", "NotoSans-Bold")


def _text_spans(page):
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            for s in ln["spans"]:
                yield s


def _raw_spans(page):
    for b in page.get_text("rawdict")["blocks"]:
        for ln in b.get("lines", []):
            for s in ln["spans"]:
                yield s


def shaping_probe(text=QA_PROBE, ref=QA_PROBE_REF, fontdir=None):
    """Render a probe string through the real CSS and compare its width with the known-good value.
    Returns (ratio, ok, font). Collapsed vowel signs (old font), mis-spaced marks (old HarfBuzz)
    or a fallback font all change the width."""
    import pymupdf
    from weasyprint import HTML
    css = CSS.replace("FONTDIR", font_uri(fontdir)).replace("BRANDNAME", "QA")
    html = (f'<html><head><style>{css} @page{{size:220mm 40mm;margin:5mm}}</style></head>'
            f'<body><p style="font-size:{QA_PROBE_PT}pt;white-space:nowrap">{text}</p></body></html>')
    pdf = HTML(string=html, base_url=HERE).write_pdf()
    page = pymupdf.open(stream=pdf, filetype="pdf")[0]
    for s in _text_spans(page):
        if abs(s["size"] - QA_PROBE_PT) < 0.5:
            ratio = (s["bbox"][2] - s["bbox"][0]) / s["size"]
            return ratio, abs(ratio - ref) / ref <= QA_PROBE_TOL, s["font"]
    return 0.0, False, "?"


def qa_pdf(pdf_path, qa_dir=None, dpi=90, blank_ink=0.002):
    """Rasterise every page to PNG and run cheap structural checks.
    Returns (png_paths, issues). Issues starting with '!!' are failures, '  ' are notes."""
    import pymupdf
    qa_dir = qa_dir or os.path.splitext(pdf_path)[0] + "_qa"
    os.makedirs(qa_dir, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    pngs, issues = [], []
    zoom = dpi / 72.0
    for page in doc:
        n = page.number + 1
        pm = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        out = os.path.join(qa_dir, f"page-{n:02d}.png")
        pm.save(out)
        pngs.append(out)
        # 1. which characters were NOT drawn by our Noto fonts (per glyph, via rawdict).
        #    Sinhala/Latin/digits in a fallback font = real failure (tofu on a machine without that font).
        #    Symbols (→ ⚠ ✔ …) in a fallback font = note only; Noto Sans lacks them.
        fb_text, fb_sym = collections.Counter(), collections.Counter()
        for s in _raw_spans(page):
            if s["font"].rstrip(",") in QA_ALLOWED_FONTS or s["font"].startswith("Noto-Sans-Sinhala"):
                continue
            for ch in s["chars"]:
                c = ch["c"]
                if c.isspace():
                    continue
                (fb_text if (0x0D80 <= ord(c) <= 0x0DFF or c.isalnum()) else fb_sym)[(c, s["font"])] += 1
        if fb_text:
            top = ", ".join(f"'{c}'×{k} ({f})" for (c, f), k in fb_text.most_common(5))
            issues.append(f"!! පිටුව {n}: සිංහල/ලතින් අකුරු fallback font එකකින් — {top}")
        if fb_sym:
            top = ", ".join(f"{c} U+{ord(c):04X} ({f})" for (c, f), k in fb_sym.most_common(5))
            issues.append(f"   පිටුව {n}: සංකේත fallback font එකකින් (Dilshan ගේ machine එකේ ඒ font එක නැත්නම් □ වේ) — {top}")
        # 2. text running off the page
        W, H = page.rect.width, page.rect.height
        off = [s for s in _text_spans(page) if s["bbox"][2] > W + 1 or s["bbox"][3] > H + 1 or s["bbox"][0] < -1]
        if off:
            issues.append(f"!! පිටුව {n}: text {len(off)}ක් පිටුවෙන් පිටතට ගොස් ඇත (overflow) — e.g. @{tuple(round(v) for v in off[0]['bbox'])}")
        # 3. blank / near-blank page (counts non-white pixels)
        samples = pm.samples
        stride = 3 * 7  # every 7th pixel is enough
        dark = sum(1 for i in range(0, len(samples), stride) if samples[i] < 235 or samples[i + 1] < 235 or samples[i + 2] < 235)
        ink = dark / (len(samples) / stride)
        if ink < blank_ink:
            issues.append(f"!! පිටුව {n}: හිස් පිටුවක් (ink {ink:.2%})")
    issues.append(f"   පිටු {len(doc)} → {qa_dir}/page-NN.png (dpi {dpi})")
    return pngs, issues


def run_qa(pdf_path, qa_dir=None):
    """Called from main() after write_pdf when --qa is given. Exit code 3 on any failure."""
    lines = []
    for i, (text, ref) in enumerate(QA_PROBES, 1):
        ratio, ok, font = shaping_probe(text, ref)
        if ok:
            lines.append(f"   shaping probe {i} OK (width/pt {ratio:.2f}, ref {ref}, font {font})")
        else:
            lines.append(f"!! shaping probe {i} FAIL — width/pt {ratio:.2f} vs ref {ref} (font {font}). "
                         "ස්වර ලකුණු overlap වෙනවා / අකුරු අතර හිඩැස්, හෝ සිංහල font එක load වී නැත. "
                         "fonts/NotoSansSinhala.ttf v3.000+ සහ Pango/HarfBuzz අනුවාදය බලන්න.")
    pngs, issues = qa_pdf(pdf_path, qa_dir)
    lines += issues
    fails = [x for x in lines if x.startswith("!!")]
    print("\n".join(["QA:"] + lines + [f"QA: {'FAIL' if fails else 'PASS'} ({len(fails)} ගැටලු) — PNG පිටු ඇසින් බලන්න, probe එක layout වැරදි අල්ලන්නේ නෑ"]), file=sys.stderr)
    return not fails


def main():
    # Sinhala on stdout/stderr must not depend on the console code page (cp1252 on Windows)
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    check_fonts()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", default="A1", choices=["G", "A1", "A2", "A3", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "C1", "C2", "C3", "C4", "C6", "D1", "D2", "D3", "E1", "M1", "N", "P1", "P2"],
                    help="G=free, A1/A2/A3=natal, B1..B8=life areas (විවාහ/වෘත්තීය/අධ්‍යාපන/ධන/සන්තාන/විදේශ/දේපල/මාතෘ-පිතෘ), C1=Varsha, C2=Varsha+Gochara, C3=Sade Sati, C4=Dasha Sandhi, C6=Masa Phala, D1=Porondam, D2=full Porondam+synastry, D3=multi-match, E1=rectification, M1=Muhurta, N=naming letters, P1/P2=Prashna")
    ap.add_argument("--name", default="—")
    ap.add_argument("--date", required=True)
    ap.add_argument("--time", required=True)
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--tz", default="Asia/Colombo")
    ap.add_argument("--place", default="")
    ap.add_argument("--time-exact", default="yes", choices=["yes", "approx"])
    ap.add_argument("--notes", help="JSON file with astrologer's Sinhala notes per section")
    ap.add_argument("--report-date", help="YYYY-MM-DD (default today)")
    ap.add_argument("--out", default="report.pdf")
    ap.add_argument("--html", help="also save the HTML")
    ap.add_argument("--brand", default=None, help="brand name on cover/footer")
    ap.add_argument("--brand-contact", default="", help="contact line on the last page (FB page, phone)")
    ap.add_argument("--no-check", action="store_true", help="skip notes/chart consistency check")
    ap.add_argument("--qa", action="store_true", help="after writing: shaping probe + rasterise every page to PNG + font/overflow/blank checks (exit 3 on failure)")
    ap.add_argument("--qa-dir", help="folder for QA PNGs (default: <out>_qa/)")
    # C1
    ap.add_argument("--year", type=int, help="C1/C2/C6: Tajaka year (default: current)")
    ap.add_argument("--month", type=int, help="C6: month 1-12 of the Tajaka year")
    # D1
    ap.add_argument("--match-name", default="")
    ap.add_argument("--match-date")
    ap.add_argument("--match-time")
    ap.add_argument("--match-lat", type=float)
    ap.add_argument("--match-lon", type=float)
    ap.add_argument("--match-tz", default="Asia/Colombo")
    # P1
    ap.add_argument("--events", help="E1: JSON file — [{\"type\":\"marriage\",\"date\":\"2022-03-04\",\"note\":\"...\"}, ...]; "
                                     "types: " + ", ".join(EVENT_TYPES))
    ap.add_argument("--scan-span", type=int, default=30, help="E1: ± minutes to scan (default 30)")
    # M1
    ap.add_argument("--task", default="general", help="M1: muhurta task (" + ", ".join(MUHURTA_TASK_SI) + ")")
    ap.add_argument("--muhurta-from", help="M1: YYYY-MM-DD")
    ap.add_argument("--muhurta-to", help="M1: YYYY-MM-DD")
    ap.add_argument("--muhurta-hours", default="6-21", help="M1: local hour range, e.g. 6-21 or 0-24")
    ap.add_argument("--muhurta-top", type=int, default=15, help="M1: how many windows to list")
    # D3
    ap.add_argument("--matches", help="D3: JSON file — [{\"name\":..,\"date\":..,\"time\":..,\"lat\":..,\"lon\":..,\"tz\":..}, ...]")
    ap.add_argument("--scan-step", type=int, default=5, help="E1: step in minutes (default 5)")
    ap.add_argument("--question", default="", help="P1: the question, in Sinhala (printed on the cover)")
    ap.add_argument("--matter", type=int, help="P1: house of the matter asked (1-12)")
    ap.add_argument("--shat-topic", default="general",
                    choices=["general", "travel", "abroad", "lost", "dispute", "health", "marriage", "subject", "rain"])
    global BRAND, BRAND_CONTACT
    a = ap.parse_args()
    BRAND, BRAND_CONTACT = (a.brand or BRAND), a.brand_contact

    tz = ZoneInfo(a.tz)
    now_local = datetime.strptime(a.report_date, "%Y-%m-%d").replace(hour=12, tzinfo=tz) if a.report_date else datetime.now(tz)
    notes = json.load(open(a.notes, encoding="utf-8")) if a.notes else {}
    workdir = os.path.dirname(os.path.abspath(a.out)) or "."
    os.makedirs(workdir, exist_ok=True)
    if a.report == "M1":
        if not (a.muhurta_from and a.muhurta_to):
            sys.exit("M1 needs --muhurta-from and --muhurta-to")
        cmd = [sys.executable, os.path.join(HERE, "jyotisha_calc.py"), "--muhurta", a.task,
               "--muhurta-from", a.muhurta_from, "--muhurta-to", a.muhurta_to, "--lat", str(a.lat), "--lon", str(a.lon),
               "--tz", a.tz, "--muhurta-hours", a.muhurta_hours, "--muhurta-top", str(a.muhurta_top)]
        if a.date and a.time:
            cmd += ["--date", a.date, "--time", a.time]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=CHILD_ENV)
        if r.returncode != 0:
            sys.exit("muhurta scan failed:\n" + r.stderr[-1500:])
        body = build_m1(a, notes, now_local, a.task, r.stdout)
        css = CSS.replace("FONTDIR", font_uri()).replace("BRANDNAME", BRAND)
        page = f'<!DOCTYPE html><html lang="si"><head><meta charset="utf-8"><title>{esc(a.name)} — {esc(BRAND)} M1</title>' \
               f'<style>{css}{CHART_CSS}</style></head><body>{body}</body></html>'
        if a.html:
            open(a.html, "w", encoding="utf-8").write(page)
        from weasyprint import HTML
        HTML(string=page, base_url=HERE).write_pdf(a.out)
        print(f"PDF written: {a.out}")
        if a.qa and not run_qa(a.out, a.qa_dir):
            sys.exit(3)
        return
    extra, rep_year = [], a.year or now_local.year
    if a.report == "A2":
        extra += ["--ashtakavarga", "--narayana"]
    if a.report == "A3":
        extra += ["--ashtakavarga", "--narayana", "--yogas", "--argala", "--upagrahas", "--kalachakra", "--ashtottari"]
    if a.report.startswith("B"):
        extra += ["--ashtakavarga", "--narayana"]
    if a.report in ("C1", "C2", "C6"):
        extra += ["--varsha", str(rep_year)]
    if a.report == "C6":
        extra += ["--masa", str(a.month or 1)]
    if a.report in ("C3", "C4"):
        extra += ["--ashtakavarga"]
    if a.report in ("D1", "D2"):
        if not (a.match_date and a.match_time and a.match_lat is not None and a.match_lon is not None):
            sys.exit("D1 needs --match-date --match-time --match-lat --match-lon")
        extra += ["--match-name", a.match_name or "", "--match-date", a.match_date, "--match-time", a.match_time,
                  "--match-lat", str(a.match_lat), "--match-lon", str(a.match_lon), "--match-tz", a.match_tz]
    if a.report in ("P1", "P2"):
        extra += ["--chart-type", "prashna", "--prashna-shat", a.shat_topic]
        if a.matter:
            extra += ["--matter", str(a.matter)]
    d = run_calc(a, now_local.year, now_local.year + 3, workdir, extra)
    if notes and not a.no_check:
        w = check_notes(notes, d)
        if w:
            print("\n!! සටහන් සහ ගණනය අතර නොගැලපීම් (notes cross-check):")
            for x in w:
                print("   " + x)
            print("   (නිවැරදි කර නැවත ධාවනය කරන්න, නැතහොත් --no-check)\n")
        else:
            print("notes cross-check: ගැලපේ ✓")
    if a.report in ("A1", "A2", "A3"):
        yrs = {"A1": 3.0, "A2": 3.0, "A3": 5.0}[a.report]
        tr = transit_snapshot(now_local.astimezone(timezone.utc), d, a.lat, a.lon)
        changes = sign_changes(now_local.astimezone(timezone.utc), yrs)
        body = (build_a1(d, a, tr, changes, notes, now_local) if a.report == "A1"
                else build_a2(d, a, tr, changes, notes, now_local, deep=(a.report == "A3")))
    elif a.report.startswith("B"):
        tr = transit_snapshot(now_local.astimezone(timezone.utc), d, a.lat, a.lon)
        changes = sign_changes(now_local.astimezone(timezone.utc), 7.0)
        body = build_b(d, a, a.report, tr, changes, notes, now_local)
    elif a.report == "G":
        body = build_g(d, a, now_local)
    elif a.report == "C1":
        body = build_c1(d, a, notes, now_local, rep_year)
    elif a.report == "C2":
        tr = transit_snapshot(now_local.astimezone(timezone.utc), d, a.lat, a.lon)
        changes = sign_changes(now_local.astimezone(timezone.utc) - timedelta(days=60), 2.0)
        body = build_c2(d, a, notes, now_local, rep_year, tr, changes)
    elif a.report == "C3":
        tr = transit_snapshot(now_local.astimezone(timezone.utc), d, a.lat, a.lon)
        body = build_c3(d, a, notes, now_local, tr)
    elif a.report == "C4":
        tr = transit_snapshot(now_local.astimezone(timezone.utc), d, a.lat, a.lon)
        body = build_c4(d, a, notes, now_local, tr)
    elif a.report == "C6":
        body = build_c6(d, a, notes, now_local, rep_year, a.month or 1)
    elif a.report == "D1":
        body = build_d1(d, a, notes, now_local)
    elif a.report == "E1":
        if not a.events:
            sys.exit("E1 needs --events events.json")
        evs = json.load(open(a.events, encoding="utf-8"))
        bad = [e for e in evs if e.get("type") not in EVENT_TYPES]
        if bad:
            sys.exit("unknown event type(s): " + ", ".join(str(e.get("type")) for e in bad) + "\nvalid: " + ", ".join(EVENT_TYPES))
        scan = rectify_scan(a, evs, a.scan_span, a.scan_step, workdir)
        body = build_e1(d, a, notes, now_local, evs, scan)
    elif a.report == "D2":
        import copy as _copy
        pa = _copy.copy(a)
        pa.name, pa.date, pa.time = (a.match_name or "සහකරු"), a.match_date, a.match_time
        pa.lat, pa.lon, pa.tz = a.match_lat, a.match_lon, a.match_tz
        pa.report = "A1"
        dB = run_calc(pa, now_local.year, now_local.year + 6, workdir)
        body = build_d2(d, dB, a, notes, now_local)
    elif a.report == "P2":
        body = build_p1(d, a, notes, now_local, a.shat_topic, a.matter)
    elif a.report == "N":
        body = build_n(d, a, notes, now_local)
    elif a.report == "D3":
        if not a.matches:
            sys.exit("D3 needs --matches matches.json")
        import copy as _copy
        plist = json.load(open(a.matches, encoding="utf-8"))
        parts = []
        for p in plist:
            pa = _copy.copy(a)
            pa.report, pa.match_name = "A1", p.get("name", "—")
            pa.match_date, pa.match_time = p["date"], p["time"]
            pa.match_lat, pa.match_lon, pa.match_tz = p["lat"], p["lon"], p.get("tz", a.tz)
            dj = run_calc(pa, now_local.year, now_local.year + 1, workdir,
                          ["--match-name", pa.match_name, "--match-date", pa.match_date, "--match-time", pa.match_time,
                           "--match-lat", str(pa.match_lat), "--match-lon", str(pa.match_lon), "--match-tz", pa.match_tz])
            pb = _copy.copy(a)
            pb.report, pb.name = "A1", p.get("name", "—")
            pb.date, pb.time, pb.lat, pb.lon, pb.tz = p["date"], p["time"], p["lat"], p["lon"], p.get("tz", a.tz)
            dj["_partner_chart"] = run_calc(pb, now_local.year, now_local.year + 1, workdir)
            parts.append((p.get("name", "—"), p, dj))
        body = build_d3(d, parts, a, notes, now_local)
    else:
        body = build_p1(d, a, notes, now_local, a.shat_topic, a.matter)
    css = CSS.replace("FONTDIR", font_uri()).replace("BRANDNAME", BRAND)
    page = f'<!DOCTYPE html><html lang="si"><head><meta charset="utf-8"><title>{esc(a.name)} — {esc(BRAND)} {esc(a.report)}</title><style>{css}{CHART_CSS}</style></head><body>{body}</body></html>'
    if a.html:
        open(a.html, "w", encoding="utf-8").write(page)
    from weasyprint import HTML
    HTML(string=page, base_url=HERE).write_pdf(a.out)
    print(f"PDF written: {a.out}")
    if a.qa and not run_qa(a.out, a.qa_dir):
        sys.exit(3)


if __name__ == "__main__":
    main()
