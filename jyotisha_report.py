#!/usr/bin/env python3
"""jyotisha_report.py — Sinhala PDF report generator on top of jyotisha_calc.py

Report types (product scope): A1 Kendra Sara (basic natal)  [A2/A3/B/C/D modules to follow]

Usage:
  python3 jyotisha_report.py --report A1 --name "නම" --date 1990-05-15 --time 10:30 --lat 6.9271 --lon 79.8612 \
      --tz Asia/Colombo --place Colombo --out report_A1.pdf [--notes notes.json] [--time-exact yes|approx]
  notes.json (optional, astrologer's Sinhala text):
      {"summary": "...", "lagna": "...", "yogas": "...", "dasha": "...", "gochara": "...", "upcoming": "...", "remedies": "..."}

Requires: weasyprint, pymupdf (for --qa), fonts/ next to this script: NotoSansSinhala(.ttf,-Bold.ttf) v3.0+, NotoSans(.ttf,-Bold.ttf), NotoSansSymbols2.ttf, NotoSansMath.ttf — all from notofonts.github.io; jyotisha_calc.py in the same dir.
All calculations come from jyotisha_calc.py (Lahiri, whole-sign, mean nodes, Swiss Ephemeris).
"""
import argparse
import base64
import collections
import html
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BRAND = "Jyothisha Insight"
BRAND_SI = "ජ්‍යොතිෂ ඉන්සයිට්"
BRAND_TAGLINE = "පාරම්පරික ජ්‍යොතිෂය · නවීන නිරවද්‍යතාව"
BRAND_CONTACT = ""   # e.g. "facebook.com/JyothishaInsight · 07X XXX XXXX"
LOGO_MAROON, LOGO_GOLD = "#6b1010", "#c9a24d"


def logo_svg(rounded=True, background=True, stroke=20):
    """The Jyothisha Insight mark, 512x512: the South Indian chart frame (the 12 houses around an empty
    centre, as on every report) with the Sun in the middle. Chosen by the owner on 2026-11-28; the PDF
    covers, the site's icons and the Facebook images (tools/brand_assets.py) are all drawn from this.
    rounded: app-icon corners (off for Facebook, which crops to a circle)."""
    bg = f'<rect width="512" height="512" rx="{104 if rounded else 0}" fill="{LOGO_MAROON}"/>' if background else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">{bg}'
            f'<g fill="none" stroke="{LOGO_GOLD}" stroke-width="{stroke}" stroke-linecap="square">'
            '<rect x="76" y="76" width="360" height="360"/><rect x="166" y="166" width="180" height="180"/>'
            '<path d="M166 76V166M256 76V166M346 76V166M166 346V436M256 346V436M346 346V436'
            'M76 166H166M76 256H166M76 346H166M346 166H436M346 256H436M346 346H436"/></g>'
            f'<circle cx="256" cy="256" r="34" fill="{LOGO_GOLD}"/></svg>')


_LOGO_URI = "data:image/svg+xml;base64," + base64.b64encode(logo_svg().encode()).decode()
LOGO_IMG = f'<img class="logo" alt="" src="{_LOGO_URI}">'                 # report covers
LOGO_IMG_SMALL = f'<img class="logo small" alt="" src="{_LOGO_URI}">'     # the one-page G summary

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jyotisha_calc as jc  # noqa: E402
import jyotisha_pdftext  # noqa: E402

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
PLANET_NATURE_SI = {"Su": "ආත්ම විශ්වාසය, පියා, නායකත්වය, රජයේ කටයුතු", "Mo": "සිත, මව, හැඟීම්, ජනතාව, සුවපහසුව",
                    "Ma": "ශක්තිය, ධෛර්යය, සහෝදරයන්, ඉඩකඩම්, තාක්ෂණික කටයුතු", "Me": "බුද්ධිය, කථනය, ව්‍යාපාර, අධ්‍යාපනය, ලේඛන",
                    "Ju": "ප්‍රඥාව, ගුරුවරුන්, දරුවන්, ධනය, ධර්මය, වාසනාව", "Ve": "ආදරය, විවාහය, කලා, සුඛෝපභෝග, වාහන",
                    "Sa": "මහන්සිය, විනය, ඉවසීම, ප්‍රමාද, දිගු කාලීන ප්‍රතිඵල", "Ra": "විශාල අභිලාශ, විදේශ, නව තාක්ෂණය, අනපේක්ෂිත වෙනස්කම්",
                    "Ke": "ඇලීම් අඩු වීම, අධ්‍යාත්මිකත්වය, පර්යේෂණ, අතීත කර්ම"}
# Saturn and Jupiter in transit, counted from the natal Moon, in everyday words (Sri Lankan names:
# ඒරාෂ්ටක ශනි = Sade Sati, 12/1/2 from the Moon; අෂ්ටම / අර්ධාෂ්ටම ශනි = 8th / 4th)
SATURN_FROM_MOON_SI = {1: "ඒරාෂ්ටක ශනියේ (සඩේ සති) මැද කාලය — වගකීම් වැඩි විය හැක; සෞඛ්‍යය සහ සිතේ සමබරතාව රැකගන්න",
                       2: "ඒරාෂ්ටක ශනියේ (සඩේ සති) අවසාන කාලය — මුදල් සහ පවුල් වගකීම් ගැන සැලකිලිමත් වන්න; ක්‍රමයෙන් සැහැල්ලු වේ",
                       3: "හොඳ කාලයක් — මහන්සියට හොඳ ප්‍රතිඵල, ධෛර්යය වැඩි වේ",
                       4: "අර්ධාෂ්ටම ශනි (අවුරුදු 2½ක කාලයක්) — නිවස, මව සහ සිතේ සැනසීම ගැන සැලකිලිමත් වන්න",
                       5: "දරුවන් සහ අධ්‍යාපන කටයුතු ප්‍රමාද විය හැක — ඉවසීමෙන් කටයුතු කරන්න",
                       6: "හොඳ කාලයක් — ගැටලු, ණය සහ තරඟ ජය ගැනීමට ශක්තිය ලැබේ",
                       7: "විවාහ සහ හවුල් සම්බන්ධතා වල ඉවසීම සහ අවබෝධය අවශ්‍යයි",
                       8: "අෂ්ටම ශනි (අවුරුදු 2½ක කාලයක්) — හදිසි බාධා සහ වියදම් ගැන ප්‍රවේශම් වන්න; සෞඛ්‍යය රැකගන්න",
                       9: "වාසනාව, පියා සහ දුර ගමන් සම්බන්ධ කටයුතු ප්‍රමාද විය හැක; ධර්මයට නැඹුරු වේ",
                       10: "රැකියාවේ වගකීම් වැඩි වේ — මහන්සියෙන් තත්ත්වය ගොඩනැගේ",
                       11: "හොඳ කාලයක් — මහන්සියට ලාභ, ස්ථාවර ආදායම්",
                       12: "ඒරාෂ්ටක ශනියේ (සඩේ සති) ආරම්භය — වියදම් වැඩි විය හැක; විවේකය සහ නින්ද රැකගන්න"}
JUPITER_FROM_MOON_SI = {1: "මිශ්‍ර කාලයක් — පෞද්ගලික දියුණුව, නමුත් අධික විශ්වාසයෙන් වළකින්න",
                        2: "හොඳ කාලයක් — මුදල්, පවුලේ සතුට, කථනයට බලය", 3: "එතරම් හිතකර නැත — වෙහෙස වැඩි විය හැක; සහෝදර කටයුතු",
                        4: "එතරම් හිතකර නැත — නිවස හෝ මව සම්බන්ධ වෙනස්කම්", 5: "හොඳ කාලයක් — දරුවන්, අධ්‍යාපනය, බුද්ධිය",
                        6: "එතරම් හිතකර නැත — සෞඛ්‍යය සහ තරඟ ගැන සැලකිලිමත් වන්න", 7: "හොඳ කාලයක් — විවාහය, සම්බන්ධතා, ගමන්",
                        8: "එතරම් හිතකර නැත — වියදම් සහ බාධා ගැන සැලකිලිමත් වන්න", 9: "හොඳ කාලයක් — වාසනාව, ධර්මය, උසස් අධ්‍යාපනය",
                        10: "මිශ්‍ර කාලයක් — රැකියා වෙනස්කම්, වැඩි උත්සාහයක් අවශ්‍යයි",
                        11: "හොඳ කාලයක් — ලාභ, මිතුරන්, බලාපොරොත්තු ඉටුවීම", 12: "එතරම් හිතකර නැත — වියදම්; විදේශ ගමන් වලට ඉඩ"}
# The life area each house stands for, in plain words: short (a label) and in full. HOUSE_SI keeps
# the traditional significations (the prashna form lists those); readings use these.
HOUSE_AREA_SI = {1: "ඔබේ පෞරුෂය සහ සුවය", 2: "මුදල් සහ පවුල", 3: "උත්සාහය සහ සහෝදරයන්", 4: "නිවස සහ මව",
                 5: "දරුවන් සහ අධ්‍යාපනය", 6: "වැඩ, සෞඛ්‍ය පුරුදු සහ තරඟ", 7: "විවාහය සහ හවුල්කාරිත්වය",
                 8: "හදිසි වෙනස්කම් සහ උරුම", 9: "වාසනාව සහ පියා", 10: "රැකියාව සහ තනතුර", 11: "ආදායම සහ ලාභ",
                 12: "වියදම් සහ විදේශ"}
HOUSE_PLAIN_SI = {1: "ඔබ ගැනම — පෞරුෂය, ශරීර සුවය, ආත්ම විශ්වාසය", 2: "මුදල්, පවුල, කථනය, ආහාර",
                  3: "උත්සාහය, ධෛර්යය, සහෝදරයන්, කෙටි ගමන්, සන්නිවේදනය", 4: "නිවස, මව, වාහන, අධ්‍යාපනය, සිතේ සැනසීම",
                  5: "දරුවන්, බුද්ධිය, අධ්‍යාපනය, නිර්මාණශීලීත්වය, පින", 6: "දෛනික වැඩ, සේවය, සෞඛ්‍ය පුරුදු, ණය, තරඟ",
                  7: "විවාහය, සහකරු, හවුල් ව්‍යාපාර", 8: "හදිසි වෙනස්කම්, රහස්, උරුම, පර්යේෂණ",
                  9: "වාසනාව, පියා, ධර්මය, උසස් අධ්‍යාපනය, දුර ගමන්", 10: "රැකියාව, වෘත්තිය, තනතුර, සමාජ පිළිගැනීම",
                  11: "ආදායම, ලාභ, මිතුරන්, බලාපොරොත්තු ඉටුවීම", 12: "වියදම්, විදේශ, නින්ද සහ විවේකය, අධ්‍යාත්මිකත්වය"}
# Each Lagna in two plain sentences: what the person is like, and one friendly tip.
LAGNA_PLAIN_SI = [
    ("ක්‍රියාශීලී, ඉක්මනින් තීරණ ගන්නා, නායකත්වය ගන්නට කැමති කෙනෙක්", "ඉවසීම පුරුදු කර ගැනීම ඔබට වාසිදායකයි"),
    ("ස්ථාවර, ඉවසිලිවන්ත, ජීවිතයේ සුවපහසුව අගය කරන කෙනෙක්", "අලුත් වෙනස්කම් වලට ටිකක් විවෘත වීම හොඳයි"),
    ("බුද්ධිමත්, කතාවට දක්ෂ, අලුත් දේ ඉගෙන ගන්නට කැමති කෙනෙක්", "එකවර වැඩ ගොඩකට අත නොගසා එකකට අවධානය දෙන්න"),
    ("සංවේදී, පවුලට ආදරය කරන, ආරක්ෂිත බව සොයන කෙනෙක්", "හැඟීම් වලට පමණක් නොව, හොඳින් සිතා බලා තීරණ ගන්න"),
    ("ආත්ම විශ්වාසය ඇති, ගෞරවය අගය කරන, ත්‍යාගශීලී කෙනෙක්", "අභිමානය තුලනය කර ගැනීම ඔබට වාසිදායකයි"),
    ("විස්තර ගැන සැලකිලිමත්, පිළිවෙළට වැඩ කරන, අනුන්ට උදව් කරන්නට කැමති කෙනෙක්", "තමන්ටත් අනුන්ටත් අධික ලෙස විවේචනය නොකරන්න"),
    ("සමබර, සම්බන්ධතා අගය කරන, සුන්දර දේට කැමති කෙනෙක්", "තීරණ කල් නොදමා, නියමිත වේලාවට තීරණය කරන්න"),
    ("ගැඹුරින් සිතන, දැඩි කැපවීමක් ඇති, දේවල් ගවේෂණය කරන්නට කැමති කෙනෙක්", "අනුන් කෙරෙහි විශ්වාසය සහ නම්‍යශීලී බව වර්ධනය කර ගන්න"),
    ("අවංක, ධර්මයට ළැදි, දුර දකින, දාර්ශනික කෙනෙක්", "විශාල අවදානම් ගැනීමට පෙර හොඳින් සිතා බලන්න"),
    ("විනයගරුක, ප්‍රායෝගික, මහන්සියෙන් ඉහළට යන කෙනෙක්", "ළඟ ඉන්න අයට ඔබේ හැඟීම් පෙන්වන්නත් ඉඩ දෙන්න"),
    ("අලුත් අදහස් ඇති, මානුෂීය, ස්වාධීන කෙනෙක්", "හුදකලා නොවී, ළඟ ඉන්න අය සමඟ සම්බන්ධතා රැකගන්න"),
    ("අනුකම්පාව ඇති, කලාත්මක, අධ්‍යාත්මික නැඹුරුවක් ඇති කෙනෙක්", "ප්‍රායෝගික සීමා සහ සැලසුම් තබා ගැනීම වැදගත්"),
]
TONE_GOOD_SI, TONE_CARE_SI = "හොඳ කාලයක්", "ඉවසීමෙන් සහ සැලකිලිමත්ව කටයුතු කළ යුතු කාලයක්"
# Words a reader meets in the reports, explained once (the glossary page)
GLOSSARY_SI = [
    ("ලග්නය", "ඔබ උපන් මොහොතේ නැගෙනහිර ක්ෂිතිජයෙන් උදා වෙමින් තිබූ රාශිය. කේන්දරයේ පළමු කොටුව (1 වන භාවය) එයයි."),
    ("රාශිය", "ග්‍රහයන් අහසේ ගමන් කරන මාර්ගයේ සමාන කොටස් 12න් එකක් — මේෂ සිට මීන දක්වා."),
    ("භාවය", "ජීවිතයේ ක්ෂේත්‍ර 12: 1 ඔබ ගැනම, 2 මුදල් සහ පවුල, 4 නිවස, 5 දරුවන්, 7 විවාහය, 10 රැකියාව, 11 ආදායම, 12 වියදම් ආදී ලෙස."),
    ("ලග්නාධිපති", "ලග්න රාශියේ අධිපති ග්‍රහයා — ඔබේ කේන්දරයේ ප්‍රධාන ග්‍රහයා."),
    ("නැකත සහ පාදය", "උපන් මොහොතේ චන්ද්‍රයා සිටි තාරකා කොටස (27න් එකක්); පාදය එහි හතරෙන් කොටසක්."),
    ("මහා දශාව / අන්තර් දශාව", "ජීවිතය කාල පරිච්ඡේද වලට බෙදා, එක් එක් කාලය එක් ග්‍රහයෙකුට දෙන ක්‍රමය. "
     "මහා දශාව අවුරුදු ගණනක්; අන්තර් දශාව ඒ තුළ කෙටි කොටසක්; ප්‍රත්‍යන්තර ඊටත් කෙටි."),
    ("ගෝචරය", "දැන් අහසේ ග්‍රහයන් සිටින තැන, ඔබේ කේන්දරයට සාපේක්ෂව."),
    ("වක්‍ර (ව)", "පෘථිවියේ සිට බලන විට ග්‍රහයා පසුපසට යන ලෙස පෙනෙන කාලය."),
    ("උච්ච / නීච / ස්වක්ෂේත්‍ර", "ග්‍රහයා ඉතා ශක්තිමත් වන රාශිය (උච්ච), දුර්වල වන රාශිය (නීච), සහ තමන්ගේම රාශිය (ස්වක්ෂේත්‍ර)."),
    ("අස්තංගත", "ග්‍රහයා සූර්යයාට ඉතා ළං වී එහි බලය අඩු වීම."),
    ("යෝගය / දෝෂය", "ග්‍රහයන්ගේ විශේෂ සංයෝග. යෝග බොහෝ විට ශුභ ප්‍රතිඵල පෙන්වයි; දෝෂ සැලකිලිමත් විය යුතු කරුණු පෙන්වයි — "
     "බොහෝ දෝෂ වෙනත් ග්‍රහ ස්ථාන නිසා අඩු වේ හෝ නැති වේ."),
    ("නවාංශකය (D9)", "එක් එක් රාශිය කොටස් 9කට බෙදා සාදන දෙවන කේන්දරය; විවාහය සහ ග්‍රහයන්ගේ සැබෑ බලය බැලීමට භාවිත වේ."),
    ("වර්ගෝත්තම", "ග්‍රහයා D1 සහ D9 කේන්දර දෙකේම එකම රාශියේ සිටීම — එය ග්‍රහයා ශක්තිමත් කරයි."),
    ("ඒරාෂ්ටක ශනි (සඩේ සති)", "ශනි ඔබේ චන්ද්‍ර රාශියට පෙර රාශිය, චන්ද්‍ර රාශිය සහ ඊළඟ රාශිය හරහා යන අවුරුදු 7½ක කාලය. "
     "අෂ්ටම / අර්ධාෂ්ටම ශනි: චන්ද්‍රගෙන් 8 / 4 වැනි රාශියේ ශනි යන අවුරුදු 2½ක කාල. මේවා බිය විය යුතු කාල නොව, ඉවසීම සහ වගකීම වැඩෙන කාලයි."),
]


def glossary_html(terms=None, extra=()):
    """The glossary table: the shared terms (all, or just the named ones), then a report's own (term, meaning) pairs."""
    rows = [(t, m) for t, m in GLOSSARY_SI if terms is None or t in terms] + list(extra)
    return ('<table class="gloss">' + "".join(f"<tr><td style='width:31%'><b>{esc(t)}</b></td><td>{esc(m)}</td></tr>"
                                               for t, m in rows) + "</table>")


def period_tone_si(P, lord):
    """A dasha period's tone from where its lord sits: good houses (and not debilitated) or a time for care."""
    good = P[lord]["house"] in (1, 2, 4, 5, 7, 9, 10, 11) and "නීච" not in si_dignity(P[lord]["dignity"])
    return TONE_GOOD_SI if good else TONE_CARE_SI


def transit_meaning_si(p, from_moon, from_lagna):
    """What a slow planet's move means, in plain words (Saturn/Jupiter from the Moon, Rahu by house)."""
    if p == "Sa":
        return SATURN_FROM_MOON_SI[from_moon]
    if p == "Ju":
        return JUPITER_FROM_MOON_SI[from_moon]
    return f"{HOUSE_AREA_SI[from_lagna]} සම්බන්ධ අලුත් අභිලාශ හෝ අනපේක්ෂිත වෙනස්කම්"


def plain_summary_si(d, a, now_local, tr=None, compact=False):
    """'In simple words': the chart's main points in everyday Sinhala, for readers who are not astrologers.
    compact: smaller type and no closing line (the one-page G, whose disclaimer says it)."""
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    tz = ZoneInfo(a.tz)
    now_utc = now_local.astimezone(timezone.utc)
    md, ad = current_dashas(d, now_local)
    ym = lambda x: datetime.fromisoformat(x).astimezone(tz).strftime("%Y-%m")  # noqa: E731
    traits, tip = LAGNA_PLAIN_SI[ls]
    L = [f"<li><b>ඔබේ ස්වභාවය:</b> {SIGN_SI[ls]} ලග්නය අනුව ඔබ {traits}. {tip}.</li>"]
    if md:
        h = P[md["lord"]]["house"]
        L.append(f"<li><b>දැන් ගත වන කාලය:</b> {ym(md['start'])[:4]} සිට {ym(md['end'])[:4]} දක්වා ඔබ සිටින්නේ "
                 f"{PLANET_SI[md['lord']]} මහා දශාවේ. මේ අවුරුදු වල ජීවිතයේ වැඩි අවධානය යොමු වන්නේ "
                 f"{HOUSE_AREA_SI[h] if compact else HOUSE_PLAIN_SI[h]} වෙතයි.</li>")
    if ad:
        L.append(f"<li><b>{ym(ad['end'])} දක්වා:</b> {HOUSE_AREA_SI[P[ad['lord']]['house']]} සම්බන්ධ කාරණා ඉස්මතු වේ — "
                 f"{period_tone_si(P, ad['lord'])}.</li>")
    after = datetime.fromisoformat(ad["end"]) if ad else now_utc
    for m in d["vimshottari"]["mahadashas"]:
        nxt = next((x for x in m.get("sub", []) if datetime.fromisoformat(x["start"]) >= after
                    and period_tone_si(P, x["lord"]) == TONE_GOOD_SI), None)
        if nxt and datetime.fromisoformat(nxt["start"]) < now_utc + timedelta(days=6 * 365):
            L.append(f"<li><b>ඉදිරියේ හොඳ කාලයක්:</b> {ym(nxt['start'])} සිට {ym(nxt['end'])} දක්වා — "
                     f"{HOUSE_AREA_SI[P[nxt['lord']]['house']]}.</li>")
            break
    if tr:
        L.append(f"<li><b>දැන් ශනි:</b> {SATURN_FROM_MOON_SI[tr['Sa']['from_moon']]}. "
                 f"<b>ගුරු:</b> {JUPITER_FROM_MOON_SI[tr['Ju']['from_moon']]}.</li>")
    if not compact:
        L.append("<li>මේවා ප්‍රවණතා පමණි — ඔබේ උත්සාහය සහ හොඳ තීරණ ඊටත් වඩා වැදගත්.</li>")
    return (f'<div class="box plain{" compact" if compact else ""}"><div class="lbl">සරලව කිවහොත්</div><ul>'
            + "".join(L) + "</ul></div>")


DIGNITY_SI = [("Uchcha", "උච්ච"), ("Neecha", "නීච"), ("Moolatrikona", "මූලත්‍රිකෝණ"), ("Swakshetra", "ස්වක්ෂේත්‍ර"), ("Own", "ස්වක්ෂේත්‍ර"),
              ("exalted", "උච්ච"), ("debilitated", "නීච"), ("friend", "මිත්‍ර ක්ෂේත්‍ර"), ("enemy", "සතුරු ක්ෂේත්‍ර"), ("neutral", "සම ක්ෂේත්‍ර")]
YOGA_SI = {"Gaja-Kesari": "ගජකේසරී යෝගය — කීර්තිය, බුද්ධිය, ගුරු–චන්ද්‍ර සම්බන්ධය",
           "Mangal dosha": "කුජ දෝෂ ඇඟවීම — විවාහ ගැලපීමේදී (පොරොන්දම් බැලීමේදී) පමණක් සලකා බලන කරුණකි; බොහෝ විට වෙනත් ග්‍රහ ස්ථාන නිසා නිෂ්ප්‍රභ වේ",
           "Kemadruma": "කේමද්‍රුම යෝගය — චන්ද්‍රයාට දෙපසින් ග්‍රහ සහාය නැත; තමන්ගේම උත්සාහයෙන් ජය ගන්නා බව",
           "Raja": "රාජ යෝගය — තනතුර, බලය සහ සාර්ථකත්වය පෙන්වන ශුභ සංයෝගයක් (කේන්ද්‍ර–ත්‍රිකෝණ අධිපති සම්බන්ධය)", "Dhana": "ධන යෝගය", "Budha-Aditya": "බුධාදිත්‍ය යෝගය — බුද්ධිය, දක්ෂතාව",
           "Chandra-Mangala": "චන්ද්‍ර–මංගල යෝගය — ලෞකික සාර්ථකත්වය", "Kala Sarpa": "කාල සර්ප යෝග ඇඟවීම — සියලු ග්‍රහයන් රාහු–කේතු අතර; ජීවිතයේ උස් පහත් වැඩි විය හැකි නමුත් මහන්සියෙන් ඉහළ යා හැක",
           "Neecha Bhanga": "නීච භංග රාජ යෝගය", "Vipareeta": "විපරීත රාජ යෝගය — බාධක වලින්ම ජය"}
_YOGA_WHY_SI = [("Guru in kendra from Chandra", "චන්ද්‍රයාගෙන් කේන්ද්‍රයක ගුරු"),
                ("no planets 2nd/12th from Chandra", "චන්ද්‍රයාගෙන් 2 සහ 12 වැන්නේ ග්‍රහයන් නැත"),
                ("all grahas within Rahu-Ketu axis", "සියලු ග්‍රහයෝ රාහු–කේතු අක්ෂයේ එක් පැත්තක"),
                ("Surya-Budha conjunct", "රවි සහ බුධ එකම රාශියේ")]


def si_yoga_why(y):
    """The reason in brackets after a basic yoga line, in Sinhala: the engine's
    'Mangal dosha indication (Kuja in house 8 from Lagna) — check cancellations' -> 'ලග්නයෙන් 8 වැන්නේ කුජ'."""
    m = re.search(r"Kuja in house (\d+) from Lagna", y)
    if m:
        return f"ලග්නයෙන් {m.group(1)} වැන්නේ කුජ"
    return next((si for en, si in _YOGA_WHY_SI if en in y), "")


def pl_si(x):
    """A planet in Sinhala from its code ('Mo') or the engine's name for it ('Chandra')."""
    return PLANET_SI.get(x) or PL_EN2SI.get(x, x)


WEEKDAY_SI = ["සඳුදා", "අඟහරුවාදා", "බදාදා", "බ්‍රහස්පතින්දා", "සිකුරාදා", "සෙනසුරාදා", "ඉරිදා"]

# ---------------------------------------------------------------- English vocabulary (G report with --lang en)
# Same meanings as the Sinhala lists above, line for line; Sanskrit terms are kept with an English gloss.
BRAND_TAGLINE_EN = "Traditional astrology · modern precision"
PLANET_EN = {"Su": "Sun", "Mo": "Moon", "Ma": "Mars", "Me": "Mercury", "Ju": "Jupiter", "Ve": "Venus",
             "Sa": "Saturn", "Ra": "Rahu", "Ke": "Ketu"}
HOUSE_EN = {1: "body, personality, self-confidence", 2: "wealth, speech, family, food",
            3: "siblings, courage, short journeys, communication", 4: "mother, home, vehicles, education, peace of mind",
            5: "children, intelligence, merit from past lives, creativity", 6: "illness, debts, enemies, service, competition",
            7: "marriage, partner, business partnerships", 8: "longevity, sudden changes, hidden knowledge, inheritance",
            9: "father, dharma, fortune, higher education, long journeys", 10: "career, karma, reputation, social standing",
            11: "gains, income, friends, hopes", 12: "expenses, foreign lands, sleep, letting go, liberation"}
LAGNA_NATURE_EN = [
    "active, quick to decide, with natural leadership; patience is worth developing",
    "steady, patient, appreciates comfort and fine things; can resist change",
    "intelligent, a good talker, curious; attention can scatter",
    "sensitive, devoted to family, seeks security; take care not to decide on feelings alone",
    "self-confident, values dignity, generous; pride needs balancing",
    "analytical, careful with detail, service-minded; can be over-critical",
    "balanced, values relationships, refined taste; can hesitate over decisions",
    "deep, intense, searching, wholly committed; watch for mistrust and rigidity",
    "philosophical, honest, devoted to dharma, far-sighted; can be over-bold",
    "disciplined, practical, rises through dedication; may come across as cold",
    "original thinker, humanitarian, independent; tends to keep apart",
    "compassionate, artistic, spiritually inclined; needs practical limits",
]
PLANET_NATURE_EN = {"Su": "the self, father, authority, government, self-confidence",
                    "Mo": "the mind, mother, feelings, the public, comfort",
                    "Ma": "energy, courage, brothers, land, engineering and technical work",
                    "Me": "intellect, speech, business, education, writing",
                    "Ju": "wisdom, teachers, children, wealth, dharma, fortune",
                    "Ve": "love, marriage, the arts, comforts, vehicles",
                    "Sa": "karma, hard work, discipline, delays, long-term results",
                    "Ra": "ambition, foreign lands, technology, the unexpected, illusion",
                    "Ke": "detachment, spirituality, research, past karma"}
WEEKDAY_EN = {"Ravi": "Sunday", "Soma": "Monday", "Mangala": "Tuesday", "Budha": "Wednesday", "Guru": "Thursday",
              "Shukra": "Friday", "Shani": "Saturday"}


def sign_en(i):
    """'Karka (Cancer)': the Sanskrit name a Sri Lankan reader knows, with the Western one."""
    return f"{jc.SIGNS[i]} ({jc.SIGNS_EN[i]})"


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


def south_indian_html_si(sign_labels, title, size_mm=120, lang="si"):
    """sign_labels: {sign_idx: [labels]} — South Indian fixed layout as an HTML grid (proper text shaping).
    The Lagna label (ලග්න / Lagna) is shown in bold. lang="en" names the signs in English."""
    names, lagna = (SIGN_SI, "ලග්න") if lang == "si" else (jc.SIGNS, "Lagna")
    sub = "දකුණු ඉන්දීය ක්‍රමය · ලාහිරි අයනාංශය" if lang == "si" else "South Indian style · Lahiri ayanamsa"
    cells = []
    for si, (cx, cy) in _GRID.items():
        labs = sign_labels.get(si, [])
        pl = "<br>".join(f"<b>{html.escape(l)}</b>" if l.startswith(lagna) else html.escape(l) for l in labs[:6])
        cells.append(f'<div class="c" style="left:{cx * 25}%;top:{cy * 25}%"><div class="sn">{names[si]}</div><div class="pl">{pl}</div></div>')
    mid = f'<div class="mid"><div class="t">{html.escape(title)}</div><div class="s">{sub}</div></div>'
    return f'<div class="sic" style="width:{size_mm}mm;height:{size_mm}mm">' + "".join(cells) + mid + "</div>"


# ---------------------------------------------------------------- compute
def with_thead(page):
    """Each table's first row of header cells becomes a <thead>. WeasyPrint repeats a thead on every
    page a table runs onto, so a long table never leaves its header alone at the foot of a page
    (D2's 'එක් එක් අයගේ කවුළු' did) and its continuation is labelled."""
    return re.sub(r"(<table[^>]*>)\s*(<tr[^>]*>\s*<th\b.*?</tr>)", r"\1<thead>\2</thead>", page, flags=re.S)


def run_calc(a, dasha_from, dasha_to, workdir, extra=()):
    # A file of its own for each call: with one shared calc.json, two reports made at the same
    # time into one folder could read each other's chart (found 2026-11-27, four builds at once).
    fd, jpath = tempfile.mkstemp(prefix="calc-", suffix=".json", dir=workdir)
    os.close(fd)
    try:
        return _run_calc(a, dasha_from, dasha_to, jpath, extra)
    finally:
        os.remove(jpath)


def _run_calc(a, dasha_from, dasha_to, jpath, extra):
    # --opt=value for text: a name like "-Nimal" would otherwise be read as an option
    cmd = [sys.executable, os.path.join(HERE, "jyotisha_calc.py"), f"--name={a.name}", "--date", a.date, "--time", a.time,
           "--lat", str(a.lat), "--lon", str(a.lon), "--tz", a.tz, f"--place={a.place or ''}", "--vargas", "D9,D10",
           "--dasha-depth", "3", "--dasha-from", str(dasha_from), "--dasha-to", str(dasha_to), "--json", jpath,
           "--node", getattr(a, "node", "mean")] + list(extra)
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
    out["sade_sati"] = ("ඒරාෂ්ටක ශනි (සඩේ සති)" if hm in (12, 1, 2) else "අර්ධාෂ්ටම ශනි" if hm == 4
                        else "අෂ්ටම ශනි" if hm == 8 else "නැත")
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
.plain .lbl { font-weight: 700; color: #6b1010; font-size: 10.5pt; margin-bottom: 2pt; }
.plain ul { margin: 2pt 0 0 0; padding-left: 13pt; } .plain li { margin: 2.5pt 0; }
.plain.compact { padding: 6pt 9pt; margin: 6pt 0; } .plain.compact li { font-size: 9.6pt; margin: 1.5pt 0; }
.gloss td { font-size: 8.6pt; line-height: 1.35; vertical-align: top; padding: 2.5pt 6pt; }
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
.logo { display: block; width: 17mm; height: 17mm; margin: 0 auto 7pt auto; }
.logo.small { width: 11mm; height: 11mm; margin-bottom: 4pt; }
.brandmark { font-family: "Noto Sans", sans-serif; font-size: 15pt; letter-spacing: 2.5px; color: #6b1010; font-weight: 700; text-transform: uppercase; }
.brandline { width: 46mm; height: 2px; background: #c9a24d; margin: 7pt auto 5pt auto; }
.brandtag { font-size: 9.5pt; color: #8a7f7f; letter-spacing: .5px; }
.brandfoot { text-align: center; margin-top: 14pt; padding-top: 8pt; border-top: 1px solid #e4dccb; }
"""


CSS_EN = """
body { font-family: "Noto Sans", "Noto Sans Sinhala", "Noto Sans Symbols 2", "Noto Sans Math", sans-serif; }
@page { @bottom-right { font-family: "Noto Sans"; } }
"""


def esc(x):
    return html.escape(str(x))


def latlon_txt(lat, lon):
    """'6.9271° N, 79.8612° E'; a birth abroad can be south or west: '33.8688° S, 151.2093° E'."""
    return f"{abs(lat):.4f}° {'S' if lat < 0 else 'N'}, {abs(lon):.4f}° {'W' if lon < 0 else 'E'}"


def utc_offset_txt(off):
    """The engine's UTC offset (Python's timedelta text) as '+5:30' or '-5:00': west of Greenwich
    Python writes -5 h as '-1 day, 19:00:00'."""
    m = re.match(r"(?:(-?\d+) days?, )?(\d+):(\d\d):\d\d$", str(off))
    if not m:
        return str(off)
    mins = int(m.group(1) or 0) * 1440 + int(m.group(2)) * 60 + int(m.group(3))
    return f"{'-' if mins < 0 else '+'}{abs(mins) // 60}:{abs(mins) % 60:02d}"


def note_block(notes, key, label="ජ්‍යොතිෂවේදියාගේ සටහන"):
    t = (notes or {}).get(key)
    if not t:
        return ""
    paras = "".join(f"<p>{esc(p)}</p>" for p in str(t).split("\n\n") if p.strip())
    return f'<div class="note"><div class="lbl">{label}</div>{paras}</div>'


# The notes.json sections each report prints (a note under any other key is not shown). The web
# Studio offers only these boxes; tests/test_studio.py checks them against the build_* functions.
_NATAL_NOTES = ("summary", "lagna", "yogas", "dasha", "gochara", "upcoming", "remedies")
NOTE_KEYS = {
    "G": (),
    "A1": _NATAL_NOTES,
    "A2": _NATAL_NOTES + ("areas",),
    "A3": _NATAL_NOTES + ("areas",),
    **{f"B{i}": _NATAL_NOTES for i in range(1, 9)},
    "C1": ("summary", "yogas", "dasha", "upcoming", "remedies"),
    "C2": ("summary", "yogas", "dasha", "upcoming", "remedies", "calendar"),
    "C3": ("summary", "remedies"),
    "C4": ("summary", "upcoming"),
    "C6": ("summary", "upcoming"),
    "N": ("summary",),
    "E1": ("summary",),
    "D1": ("summary", "dosha", "upcoming"),
    "D2": ("summary", "upcoming"),
    "D3": ("summary",),
    "P1": ("summary", "upcoming"),
    "P2": ("summary", "upcoming"),
    "M1": ("summary",),
}


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
    traits, tip = LAGNA_PLAIN_SI[ls]
    lagna_txt = (f"ඔබේ ලග්නය — ඔබ උපන් මොහොතේ නැගෙනහිරින් උදා වෙමින් තිබූ රාශිය — <b>{SIGN_SI[ls]}</b> ({dms(d['lagna']['deg_in_sign'])}). "
                 f"ස්වභාවයෙන් ඔබ {traits}; {tip}. "
                 f"ලග්නයේ අධිපති ග්‍රහයා (ලග්නාධිපති) <b>{PLANET_SI[lord]}</b>, {SIGN_SI[P[lord]['sign_idx']]} රාශියේ <b>{lord_house} වන භාවයේ</b> සිටී; "
                 f"එනිසා {HOUSE_PLAIN_SI[lord_house]} ඔබේ ජීවිතයේ වැදගත් තැනක් ගනී"
                 + (f" (ග්‍රහයාගේ තත්ත්වය: {si_dignity(P[lord]['dignity'])})" if si_dignity(P[lord]['dignity']) != "—" else "") + ".")
    moon_txt = (f"ඔබේ සිත සහ හැඟීම් පෙන්වන චන්ද්‍රයා <b>{SIGN_SI[moon['sign_idx']]}</b> රාශියේ, <b>{NAK_SI[jc.NAKSHATRAS.index(moon['nakshatra'])]}</b> නැකතේ "
                f"{moon['pada']} වන පාදයේ, {moon['house']} වන භාවයේ ({HOUSE_PLAIN_SI[moon['house']]}) සිටී. ඔබේ සිතේ ස්වභාවය සහ මානසික සුවය මෙයින් කියවේ"
                + (f" (තත්ත්වය: {si_dignity(moon['dignity'])})" if si_dignity(moon['dignity']) != "—" else "") + ".")

    # yogas
    yl = []
    for y in d.get("yoga_indications", []):
        key = next((k for k in YOGA_SI if k.lower() in y.lower()), None)
        why = si_yoga_why(y)
        yl.append(f"<li><b>{esc(YOGA_SI[key].split(' — ')[0]) if key else esc(si_text(y))}</b>" + (f" — {esc(YOGA_SI[key].split(' — ', 1)[1])}" if key and ' — ' in YOGA_SI[key] else "") +
                  (f' <span class="muted">({esc(why)})</span>' if why else "") + "</li>")
    vt = d.get("vargottama", [])
    if vt:
        yl.append(f"<li><b>වර්ගෝත්තම</b>: {esc(', '.join(pl_si(v) for v in vt))} — D1 සහ D9 කේන්දර දෙකේම එකම රාශියේ සිටින නිසා ශක්තිමත්</li>")
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]:
        dg = si_dignity(P[c]["dignity"])
        if "උච්ච" in dg or "නීච" in dg:
            yl.append(f"<li>{PLANET_SI[c]} {dg} ({SIGN_SI[P[c]['sign_idx']]}, {P[c]['house']} වැන්න) — {PLANET_NATURE_SI[c]} සම්බන්ධ කාරණා {'ශක්තිමත්' if 'උච්ච' in dg else 'වැඩි උත්සාහයක් ඉල්ලයි (මෙම දුර්වලකම ඉවත් වන නීච භංග තත්ත්වයක් තිබේදැයි ජ්‍යොතිෂවේදියා බලයි)'}</li>")
    if not yl:
        yl.append("<li>ප්‍රධාන යෝග/දෝෂ ඇඟවීම් නැත (මූලික පරීක්ෂාව)</li>")

    def dasha_row(m, s=None, p=None):
        node = p or s or m
        return f"<tr><td>{PLANET_SI[m['lord']]}</td><td>{PLANET_SI[s['lord']] if s else '—'}</td><td>{PLANET_SI[p['lord']] if p else '—'}</td><td>{fmt_date(node['start'], tz)}</td><td>{fmt_date(node['end'], tz)}</td></tr>"

    md_txt = ""
    if md:
        L = md["lord"]
        md_txt = (f"දැන් ඔබ සිටින්නේ <b>{PLANET_SI[L]}</b> මහා දශාවේ ({fmt_date(md['start'], tz)} – {fmt_date(md['end'], tz)}). "
                  f"{PLANET_SI[L]} ග්‍රහයා නියෝජනය කරන්නේ {PLANET_NATURE_SI[L]}. ඔබේ කේන්දරයේ එය {SIGN_SI[P[L]['sign_idx']]} රාශියේ "
                  f"{P[L]['house']} වන භාවයේ ({HOUSE_PLAIN_SI[P[L]['house']]}) සිටින නිසා"
                  + (f" ({si_dignity(P[L]['dignity'])})" if si_dignity(P[L]['dignity']) != "—" else "")
                  + ", මේ දශාව පුරා එම කාරණා ඔබේ ජීවිතයේ ඉදිරියට එයි.")
        if ad:
            A = ad["lord"]
            md_txt += (f" දැනට ක්‍රියාත්මක අන්තර් දශාව <b>{PLANET_SI[A]}</b> ({fmt_date(ad['start'], tz)} – {fmt_date(ad['end'], tz)}): "
                       f"මේ කාලයේ {HOUSE_PLAIN_SI[P[A]['house']]} සම්බන්ධ සිදුවීම් ඉස්මතු වීමට ඉඩ ඇත — {period_tone_si(P, A)}.")

    up_rows = []
    for m, s, st, en, subs in upcoming:
        up_rows.append(f"<tr{' class=cur' if st <= now_utc < en else ''}><td>{PLANET_SI[m]} / {PLANET_SI[s]}</td><td>{st.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</td>"
                       f"<td>{en.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</td><td>{HOUSE_AREA_SI[P[s]['house']]} — {'හොඳයි' if period_tone_si(P, s) == TONE_GOOD_SI else 'සැලකිලිමත් වන්න'} <span class=muted>({PLANET_SI[s]} {P[s]['house']} වැන්නේ)</span></td></tr>")

    # transits
    sa, ju, ra = tr["Sa"], tr["Ju"], tr["Ra"]
    goch = [
        f"<li><b>ශනි</b> {SIGN_SI[sa['sign']]} රාශියේ{' (වක්‍ර)' if sa['retro'] else ''} — චන්ද්‍රගෙන් {sa['from_moon']} වැන්න, ලග්නයෙන් {sa['from_lagna']} වැන්න: {SATURN_FROM_MOON_SI[sa['from_moon']]}</li>",
        f"<li><b>ගුරු</b> {SIGN_SI[ju['sign']]} රාශියේ{' (වක්‍ර)' if ju['retro'] else ''} — චන්ද්‍රගෙන් {ju['from_moon']} වැන්න, ලග්නයෙන් {ju['from_lagna']} වැන්න: {JUPITER_FROM_MOON_SI[ju['from_moon']]}</li>",
        f"<li><b>රාහු–කේතු</b> {SIGN_SI[ra['sign']]}–{SIGN_SI[(ra['sign'] + 6) % 12]} අක්ෂය — ලග්නයෙන් {ra['from_lagna']}/{(ra['from_lagna'] + 5) % 12 + 1} වැනි භාව: {HOUSE_AREA_SI[ra['from_lagna']]} සහ {HOUSE_AREA_SI[(ra['from_lagna'] + 5) % 12 + 1]} සම්බන්ධ අලුත් අභිලාශ හෝ අනපේක්ෂිත වෙනස්කම්</li>",
        f"<li><b>ඒරාෂ්ටක / අෂ්ටම ශනි</b>: {tr['sade_sati']}</li>",
    ]
    ch_rows = "".join(f"<tr><td>{dt.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}{'<br><span class=muted>ස්ථිර ' + st.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d') + '</span>' if (st - dt).days > 20 else ''}</td><td>{PLANET_SI[p]}</td><td>{SIGN_SI[s]}</td>"
                      f"<td>චන්ද්‍රගෙන් {jc.house_from(moon['sign_idx'], s)}, ලග්නයෙන් {jc.house_from(ls, s)}</td>"
                      f"<td>{(transit_meaning_si(p, jc.house_from(moon['sign_idx'], s), jc.house_from(ls, s)))}</td></tr>"
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
                    + f"ශනි ගෝචරය: {tr['sade_sati'] if tr['sade_sati'] != 'නැත' else 'ඒරාෂ්ටක / අෂ්ටම ශනි නැත'}; ගුරු චන්ද්‍රගෙන් {ju['from_moon']} වැන්නේ.")

    birth_rows = [("නම", a.name), ("උපන් දිනය", a.date), ("උපන් වේලාව", f"{a.time} ({'නිශ්චිත' if not approx else 'ආසන්න'})"),
                  ("ස්ථානය", a.place or "—"), ("අක්ෂාංශ / දේශාංශ", latlon_txt(a.lat, a.lon)),
                  ("කාල කලාපය", f"{a.tz} (UTC{utc_offset_txt(d['birth']['utc_offset'])})"),
                  ("අයනාංශය", f"ලාහිරි {dms(d['ayanamsa'])}"), ("පංචාංගය", f"{esc(pch_si(d['panchanga'])['vara'])} · {esc(pch_si(d['panchanga'])['tithi'])} තිථි · {esc(pch_si(d['panchanga'])['yoga'])} යෝග · {esc(pch_si(d['panchanga'])['karana'])} කරණ · හිරු උදාව {d['panchanga']['sunrise']}"),
                  ("වාර්තා දිනය", now_local.strftime("%Y-%m-%d"))]

    H = []
    H.append(f"""<div class="cover">{LOGO_IMG}<div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:20pt">ජන්ම කේන්දර වාර්තාව</h1><div class="sub">කේන්දර සාර — මූලික විග්‍රහය (A1)</div>
      <div class="name">{esc(a.name)}</div>
      <div>{esc(a.date)} · {esc(a.time)} · {esc(a.place or '')}</div>
      <div style="margin:16pt auto 0 auto; width:116mm">{svg_d1}</div>
      <p class="muted" style="margin-top:12pt; font-size:8.5pt">පරාශර සහ ජෛමිනි සම්ප්‍රදාය · ලාහිරි අයනාංශය · සම්පූර්ණ රාශි භාව ක්‍රමය · මධ්‍යම රාහු-කේතු · Swiss Ephemeris</p></div>""")
    H.append('<div class="pb"></div><h2>1. සාරාංශය</h2>')
    H.append(plain_summary_si(d, a, now_local, tr))
    H.append(f'<p class="small muted"><b>ජ්‍යොතිෂ කෙටි සටහන:</b> {esc(summary_auto)}</p>')
    H.append(note_block(notes, "summary"))
    if approx:
        H.append('<div class="note"><div class="lbl">උපන් වේලාව ගැන</div><p>උපන් වේලාව ආසන්න වශයෙන් දී ඇති නිසා මේ වාර්තාවේ D1 කේන්දරය, දශා සහ ගෝචරය ප්‍රමුඛ කර ඇත; සියුම් වර්ග (D9, D10) කේන්දර වල ලග්නය මිනිත්තු කිහිපයකින් වෙනස් විය හැක.</p></div>')
    H.append("<h2>2. උපන් දත්ත</h2><table>" + "".join(f"<tr><td style='width:34%'><b>{k}</b></td><td>{esc(v)}</td></tr>" for k, v in birth_rows) + "</table>")
    H.append('<p class="small muted">දත්ත වැරදි නම් වහාම දන්වන්න — වේලාව මිනිත්තු 10ක් වෙනස් වුවත් සමහර ප්‍රතිඵල වෙනස් විය හැක.</p>')

    H.append("<h2>3. ලග්නය සහ ග්‍රහ ස්ථාන (D1)</h2>")
    H.append(f"<p>{lagna_txt}</p><p>{moon_txt}</p>")
    H.append("<table><tr><th>ග්‍රහයා</th><th>රාශිය</th><th>අංශක</th><th>භාවය</th><th>නැකත / පාදය</th><th>තත්ත්වය</th></tr>" + "".join(prow) + "</table>")
    H.append('<p class="small muted">වගුව කියවන හැටි: <b>භාවය</b> = ග්‍රහයා බලපාන ජීවිත ක්ෂේත්‍රය (1–12); <b>වක්‍ර</b> = පසුපසට යන ලෙස පෙනෙන කාලය; '
             '<b>උච්ච</b> = ඉතා ශක්තිමත්, <b>නීච</b> = දුර්වල, <b>ස්වක්ෂේත්‍ර</b> = තමන්ගේම රාශිය; <b>අස්තංගත</b> = සූර්යයාට ළං වී බලය අඩු වීම.</p>')
    H.append(note_block(notes, "lagna"))
    H.append('<h3>ජෛමිනි කාරක සහ ආරූඪ (සංක්ෂිප්ත)</h3>')
    H.append("<table><tr><th>ආත්මකාරක (AK)</th><th>අමාත්‍යකාරක (AmK)</th><th>දාරාකාරක (DK)</th><th>ආරූඪ ලග්නය (AL)</th><th>උපපද (UL)</th></tr>"
             f"<tr><td>{PLANET_SI[kk['AK']['planet']]}</td><td>{PLANET_SI[kk['AmK']['planet']]}</td><td>{PLANET_SI[kk['DK']['planet']]}</td>"
             f"<td>{SIGN_SI[inv[ar['AL']]]}</td><td>{SIGN_SI[inv[ar['UL']]]}</td></tr></table>")
    H.append('<p class="small muted">ජෛමිනි ක්‍රමයේ දර්ශක: ආත්මකාරක (AK) = ජීවිතයේ ප්‍රධාන පාඩම් පෙන්වන ග්‍රහයා; අමාත්‍යකාරක (AmK) = රැකියාව සහ වෘත්තිය; '
             'දාරාකාරක (DK) = සහකරු; ආරූඪ ලග්නය (AL) = සමාජය ඔබව දකින ආකාරය; උපපද (UL) = විවාහය. විස්තර A2/A3 වාර්තා වල.</p>')

    H.append('<div class="pb"></div><h2>4. නවාංශකය (D9) සහ යෝග</h2>')
    if svg_d9:
        H.append(f'<div class="two"><div class="chart" style="width:90mm; flex: 0 0 90mm">{svg_d9}</div><div><p class="small">නවාංශකය (D9) යනු එක් එක් රාශිය කොටස් 9කට බෙදා සාදන දෙවන කේන්දරයයි — විවාහය, අභ්‍යන්තර ශක්තිය සහ ග්‍රහයන්ගේ සැබෑ බලය බැලීමට භාවිත වේ. '
                 f'D9 ලග්නය <b>{SIGN_SI[inv[d9["La"]]]}</b>.' + (' උපන් වේලාව ආසන්න නිසා D9 ලග්නය වෙනස් විය හැක.' if approx else '') + '</p></div></div>')
    H.append("<h3>ප්‍රධාන යෝග / දෝෂ සහ තත්ත්ව</h3>"
             '<p class="small">යෝග යනු ග්‍රහයන්ගේ විශේෂ සංයෝග; දෝෂ යනු සැලකිලිමත් විය යුතු සංයෝග. තනි දෝෂයක් ගැන බිය විය යුතු නැත — '
             'බොහෝ ඒවා වෙනත් ග්‍රහ ස්ථාන නිසා අඩු වේ හෝ නැති වේ.</p><ul>' + "".join(yl) + "</ul>")
    H.append(note_block(notes, "yogas"))

    H.append("<h2>5. විම්ශෝත්තරී දශා — ඔබේ ජීවිතයේ කාල පරිච්ඡේද</h2>")
    H.append('<p class="small muted">දශා ක්‍රමයේදී ජීවිතය කාල පරිච්ඡේද වලට බෙදී, එක් එක් කාලය එක් ග්‍රහයෙකුගේ පාලනයට යටත් වේ. '
             'මහා දශාව අවුරුදු ගණනක් පවතී; අන්තර් දශාව ඒ තුළ කෙටි කොටසක්; ප්‍රත්‍යන්තර දශාව ඊටත් කෙටි.</p>')
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

    H.append('<div class="pb"></div><h2>6. ගෝචරය — දැන් ග්‍රහයන් ගමන් කරන තැන</h2>')
    H.append('<p class="small">ශනි, ගුරු, රාහු වැනි සෙමින් ගමන් කරන ග්‍රහයන් දැන් ඔබේ කේන්දරයට සාපේක්ෂව සිටින තැනින් ඉදිරි මාස සහ අවුරුදු කිහිපයේ '
             'ප්‍රවණතා කියවේ. “චන්ද්‍රගෙන් 4 වැන්න” යනු ඔබේ චන්ද්‍ර රාශියේ සිට ගණන් කළ විට ග්‍රහයා සිටින රාශියයි.</p>')
    H.append(f'<p class="small muted">{now_local.strftime("%Y-%m-%d")} දිනට</p><ul>' + "".join(goch) + "</ul>")
    if ch_rows:
        H.append("<h3>ඉදිරි වසර 3 තුළ ශනි / ගුරු / රාහු රාශි මාරු</h3><table><tr><th>දිනය</th><th>ග්‍රහයා</th><th>නව රාශිය</th><th>භාවය</th><th>ප්‍රවණතාව</th></tr>" + ch_rows + "</table>")
    H.append(note_block(notes, "gochara"))

    H.append("<h2>7. ඉදිරි කාලය — සාරාංශ කවුළු</h2>")
    win = []
    for m, s, st, en, subs in upcoming:
        if en <= now_utc:
            continue
        win.append(f"<li><b>{max(st, now_utc).astimezone(ZoneInfo(tz)).strftime('%Y-%m')} → {en.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</b> — {PLANET_SI[m]}/{PLANET_SI[s]}: "
                   f"{HOUSE_AREA_SI[P[s]['house']]} — {period_tone_si(P, s)}</li>")
    for dt, p, s, st in changes:
        win.append(f"<li><b>{dt.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</b> — {PLANET_SI[p]} {SIGN_SI[s]} රාශියට"
                   + (f" (වක්‍ර චලනයෙන් පසු ස්ථිර {st.astimezone(ZoneInfo(tz)).strftime('%Y-%m')})" if (st - dt).days > 20 else "")
                   + f": {transit_meaning_si(p, jc.house_from(moon['sign_idx'], s), jc.house_from(ls, s))}</li>")
    H.append("<ul>" + "".join(sorted(win)) + "</ul>")
    H.append('<p class="small muted">වක්‍ර චලනය නිසා ග්‍රහයෙක් රාශියකට ඇතුළු වී ආපසු ගොස් නැවත ඇතුළු වන විට පළමු ඇතුළුවීමේ දිනයත්, ස්ථිර වන දිනයත් දෙකම දක්වා ඇත.</p>')
    H.append('<p class="small">දශාව, ගෝචරය සහ වාර්ෂික චක්‍රය එකට ගැලපෙන කාල කවුළු වඩාත් වැදගත්; තනි ඇඟවීමක් මත පමණක් තීරණ නොගන්න. සවිස්තර කාල නිර්ණය A2 වාර්තාවේත්, වර්ෂ කේන්දරය (වර්ෂඵල) C1 වාර්තාවේත් ඇත.</p>')
    H.append(note_block(notes, "upcoming"))
    if (notes or {}).get("remedies"):
        H.append("<h2>8. යෝජනා</h2>" + note_block(notes, "remedies", "ප්‍රතිකර්ම / ආකල්ප යෝජනා"))

    H.append('<div class="pb"></div><h2>වචන කිහිපයක තේරුම</h2>' + glossary_html())
    H.append('<h2>ක්‍රමවේදය සහ වගකීම් ප්‍රකාශය</h2>')
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
              "Tula": "තුලා", "Vrischika": "වෘශ්චික", "Dhanu": "ධනු", "Makara": "මකර", "Kumbha": "කුම්භ", "Meena": "මීන",
              # the engine's five-letter forms (Tajaka yoga lines print SIGNS[s][:5])
              "Vrish": "වෘෂභ", "Mithu": "මිථුන", "Vrisc": "වෘශ්චික", "Makar": "මකර", "Kumbh": "කුම්භ"}
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
    ("deeply exalted", "ගැඹුරින් උච්ච"), ("moolatrikona", "මූලත්‍රිකෝණ"), ("own/exalted", "ස්වක්ෂේත්‍ර/උච්ච"),
    ("exalted", "උච්ච"), ("debilitated", "නීච"), ("mutual", "අන්‍යෝන්‍ය"),
    ("strong", "ශක්තිමත්"), ("together", "එකට"), ("benefic", "ශුභ ග්‍රහ"), ("malefic", "පාප ග්‍රහ"),
    (" & ", " සහ "), (" or ", " හෝ "),
    # Tajaka aspects / yogas
    ("conjunction", "සංයෝගය"), ("opposition", "ප්‍රතියෝගය"), ("trine", "ත්‍රිකෝණ දෘෂ්ටිය"), ("square", "චතුරස්‍ර දෘෂ්ටිය"),
    # a Tajaka sextile is the 3/11 aspect and semi-sextile 2/12 (ෂඩාෂ්ටක would mean 6/8)
    ("semi-sextile", "ද්වි-ද්වාදශ (2/12) දෘෂ්ටිය"), ("sextile", "ත්‍රි-ඒකාදශ (3/11) දෘෂ්ටිය"), ("vartamana", "වර්තමාන"),
    ("ITHASALA", "ඉථසාල"), ("ithasala", "ඉථසාල"), ("EESARPHA", "ඊසර්ඵ"), ("MANAHOO", "මනාහූ"),
    ("Hora lord", "හෝරාධිපති"), ("lagna lord", "ලග්නාධිපති"), ("in 6/8/12 from lagna", "ලග්නයෙන් 6/8/12 වැන්නේ"),
    ("(unfavorable)", "(අශුභ)"),
    # yoga reasons (ch.11)
    ("papa-kartari", "පාප කර්තරී"), ("exchange (parivartana)", "පරිවර්තනය"), ("parivartana", "පරිවර්තනය"),
    ("exchanges", "පරිවර්තන"), ("exchange", "පරිවර්තනය"),
    ("all grahas in movable rasis", "සියලු ග්‍රහයෝ චර රාශිවල"), ("all grahas in fixed rasis", "සියලු ග්‍රහයෝ ස්ථිර රාශිවල"),
    ("all grahas in dual rasis", "සියලු ග්‍රහයෝ ද්විස්වභාව රාශිවල"),
    ("(malefic also in a kendra — weakened)", "(කේන්ද්‍රයක පාප ග්‍රහයෙක්ද සිටී — දුර්වල වී ඇත)"),
    ("(benefic also in a kendra — weakened)", "(කේන්ද්‍රයක ශුභ ග්‍රහයෙක්ද සිටී — දුර්වල වී ඇත)"),
    ("even houses", "යුග්ම භාවවල"), ("odd houses", "ඔජ භාවවල"),
    ("movable rasi", "චර රාශිය"), ("well placed", "හොඳ ස්ථානයක"), ("unafflicted", "පීඩාවකින් තොරව"),
    ("maraka-afflicted", "මාරක පීඩිත"), ("maraka", "මාරක"),
    # Ashtakoota notes
    ("(same rasi, different nakshatra)", "(එකම රාශිය, වෙනස් නැකත්)"),
    ("(same nakshatra, different rasi)", "(එකම නැකත, වෙනස් රාශි)"),
    ("(same nakshatra & rasi, different pada)", "(එකම නැකත සහ රාශිය, වෙනස් පාද)"), ("poorna", "පූර්ණ"), ("bhavishya", "භවිෂ්‍ය"),
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
            "empty": "හිස්", "conjunct": "සංයුක්ත", "retrograde": "වක්‍ර", "secondary": "ද්විතීයික",
            "without": "නොමැතිව", "only": "පමණක්", "two": "දෙකක්", "nakshatra": "නැකත", "graha": "ග්‍රහයා"}


# Whole engine sentences, translated as a unit: word-by-word Sinhala comes out in the wrong order.
WHOLE_SI = {
    # ch.11 "popular" yogas: the condition behind each
    "benefic in Lagna or subha-kartari": "ලග්නයේ ශුභ ග්‍රහයෙක්, හෝ ලග්නය ශුභ කර්තරියේ",
    "malefic in Lagna or papa-kartari": "ලග්නයේ පාප ග්‍රහයෙක්, හෝ ලග්නය පාප කර්තරියේ",
    "Guru & Kuja conjunct/opposite": "ගුරු සහ කුජ එකට, හෝ එකිනෙකාට 7 වැන්නේ",
    "kendras only benefics; 7th/8th empty or benefic": "කේන්ද්‍රවල ශුභ ග්‍රහයන් පමණක්; 7 සහ 8 වැන්න හිස් හෝ ශුභ ග්‍රහයන් සහිත",
    "4th lord exalted/own with 10th lord": "4 වන අධිපති උච්ච/ස්වක්ෂේත්‍රව, 10 වන අධිපති සමඟ",
    "4th lord & Guru in mutual kendras, Lagna lord strong": "4 වන අධිපති සහ ගුරු අන්‍යෝන්‍ය කේන්ද්‍රවල; ලග්නාධිපති ශක්තිමත්",
    "Lagna lord exalted in kendra with Guru's aspect, or two benefics in 7/9/10":
        "ලග්නාධිපති කේන්ද්‍රයක උච්චව ගුරු දෘෂ්ටිය සහිතව, හෝ 7/9/10 හි ශුභ ග්‍රහයන් දෙදෙනෙක්",
    "Lagna lord strong; 5th & 6th lords in mutual kendras": "ලග්නාධිපති ශක්තිමත්; 5 සහ 6 වන අධිපතීන් අන්‍යෝන්‍ය කේන්ද්‍රවල",
    "Lagna & 10th lords together in movable rasi; 9th lord strong":
        "ලග්නාධිපති සහ 10 වන අධිපති චර රාශියක එකට; 9 වන අධිපති ශක්තිමත්",
    "9th lord strong; 1/2/7/12 occupied or Guru-Shukra-Lagna lord in mutual kendras":
        "9 වන අධිපති ශක්තිමත්; 1/2/7/12 භාවවල ග්‍රහයන්, හෝ ගුරු, ශුක්‍ර සහ ලග්නාධිපති අන්‍යෝන්‍ය කේන්ද්‍රවල",
    "own/exalted graha in kendra/trikona; Lagna lord strong": "කේන්ද්‍ර/ත්‍රිකෝණයක ස්වක්ෂේත්‍ර/උච්ච ග්‍රහයෙක්; ලග්නාධිපති ශක්තිමත්",
    "7th lord exalted in 10th; 10th & 9th lords together": "7 වන අධිපති 10 වැන්නේ උච්චව; 10 සහ 9 වන අධිපතීන් එකට",
    "benefics in 1 & 9, grahas in 5, malefics in 4/8": "1 සහ 9 හි ශුභ ග්‍රහයන්, 5 හි ග්‍රහයන්, 4/8 හි පාප ග්‍රහයන්",
    "2nd-9th lords exchange; Lagna lord in kendra/trikona": "2 සහ 9 වන අධිපතීන්ගේ පරිවර්තනය; ලග්නාධිපති කේන්ද්‍ර/ත්‍රිකෝණයක",
    "fixed Lagna, Shukra in kendra, Chandra in trikona with benefic, Shani in 10th":
        "ස්ථිර ලග්නය; ශුක්‍ර කේන්ද්‍රයක, චන්ද්‍ර ශුභ ග්‍රහයෙකු සමඟ ත්‍රිකෝණයක, ශනි 10 වැන්නේ",
    "benefics in 7 & 8 from Lagna, unafflicted": "ලග්නයෙන් 7 සහ 8 හි ශුභ ග්‍රහයන්, පීඩාවකින් තොරව",
    "benefics in 2/12/8 from 2nd lord": "2 වන අධිපතිගෙන් 2/12/8 හි ශුභ ග්‍රහයන්",
    "benefics in 4/9/8 from 7th lord": "7 වන අධිපතිගෙන් 4/9/8 හි ශුභ ග්‍රහයන්",
    "benefics in 4/10/11 from Lagna lord": "ලග්නාධිපතිගෙන් 4/10/11 හි ශුභ ග්‍රහයන්",
    "Guru kendra from 9L, Shukra kendra from 11L, Budha kendra from 1L/10L":
        "9 වන අධිපතිගෙන් කේන්ද්‍රයක ගුරු, 11 වන අධිපතිගෙන් කේන්ද්‍රයක ශුක්‍ර, 1/10 වන අධිපතීන්ගෙන් කේන්ද්‍රයක බුධ",
    "9th & 10th lords and navamsa dispositor of 9L in 2nd": "9 සහ 10 වන අධිපතීන් සහ 9 වන අධිපතිගේ නවාංශ අධිපති 2 වැන්නේ",
    "5L in 9, 9L in 10, 10L in 5": "5 වන අධිපති 9 හි, 9 වන අධිපති 10 හි, 10 වන අධිපති 5 හි",
    "Surya, Chandra, Kuja in mutual trines": "රවි, චන්ද්‍ර, කුජ අන්‍යෝන්‍ය ත්‍රිකෝණවල",
    "navamsa dispositor of 10L exalted in 10th with Lagna lord": "10 වන අධිපතිගේ නවාංශ අධිපති උච්චව ලග්නාධිපති සමඟ 10 වැන්නේ",
    "9th lord own/exalted in kendra; Lagna lord strong": "9 වන අධිපති කේන්ද්‍රයක ස්වක්ෂේත්‍ර/උච්චව; ලග්නාධිපති ශක්තිමත්",
    "10L in 5, Budha kendra, Surya in Simha, Budha/Guru trine from Chandra, Kuja in 11":
        "10 වන අධිපති 5 හි, බුධ කේන්ද්‍රයක, රවි සිංහයේ, චන්ද්‍රයාගෙන් ත්‍රිකෝණයක බුධ/ගුරු, කුජ 11 හි",
    "Budha, Guru, Shukra in kendra/trikona/2nd; Guru well placed": "බුධ, ගුරු, ශුක්‍ර කේන්ද්‍ර/ත්‍රිකෝණ/2 වැන්නේ; ගුරු හොඳ ස්ථානයක",
    "Guru, Shukra & exalted Shani in kendras": "ගුරු, ශුක්‍ර සහ උච්ච ශනි කේන්ද්‍රවල",
    "fixed Lagna; 2-10 and 1-11 exchanges": "ස්ථිර ලග්නය; 2–10 සහ 1–11 අධිපති පරිවර්තන",
    "5-11 exchange; Chandra in 5th": "5–11 අධිපති පරිවර්තනය; චන්ද්‍ර 5 වැන්නේ",
    "Surya in 10; 10L in 3 with Shani": "රවි 10 හි; 10 වන අධිපති ශනි සමඟ 3 හි",
    "Chandra 12th & Budha 2nd from Surya; Guru 5/9 from Chandra": "රවිගෙන් 12 වැන්නේ චන්ද්‍ර සහ 2 වැන්නේ බුධ; චන්ද්‍රයාගෙන් 5/9 හි ගුරු",
    "every graha in 5th from Lagna, Chandra or Surya": "සෑම ග්‍රහයෙක්ම ලග්නය, චන්ද්‍ර හෝ රවිගෙන් 5 වැන්නේ",
    "10L trine from 7th; Guru with Lagna lord; Surya exalted; Chandra in 9":
        "10 වන අධිපති 7 වැන්නෙන් ත්‍රිකෝණයක; ගුරු ලග්නාධිපති සමඟ; රවි උච්ච; චන්ද්‍ර 9 හි",
    "Guru in moolatrikona with 2L; Lagna lord exalted": "ගුරු මූලත්‍රිකෝණයේ 2 වන අධිපති සමඟ; ලග්නාධිපති උච්ච",
    "11L deeply exalted with Shukra, kendra from Lagna lord": "11 වන අධිපති ගැඹුරින් උච්චව ශුක්‍ර සමඟ, ලග්නාධිපතිගෙන් කේන්ද්‍රයක",
    "4-10 exchange; Lagna lord exalted": "4–10 අධිපති පරිවර්තනය; ලග්නාධිපති උච්ච",
    "Guru 9th from 9L; benefic 9th from Guru; Shani in 10": "9 වන අධිපතිගෙන් 9 වැන්නේ ගුරු; ගුරුගෙන් 9 වැන්නේ ශුභ ග්‍රහයෙක්; ශනි 10 හි",
    "10L deeply exalted; 6L debilitated": "10 වන අධිපති ගැඹුරින් උච්ච; 6 වන අධිපති නීච",
    "no grahas in 1/2/12 from Chandra and none in kendras from Lagna":
        "චන්ද්‍රයාගෙන් 1/2/12 හි ග්‍රහයන් නැත; ලග්නයෙන් කේන්ද්‍රවලද ග්‍රහයන් නැත",
    "no grahas 1/2/12 from Chandra, but kendras from Lagna occupied (cancellation per 11.3.4)":
        "චන්ද්‍රයාගෙන් 1/2/12 හි ග්‍රහයන් නැත, නමුත් ලග්නයෙන් කේන්ද්‍රවල ග්‍රහයන් සිටී (11.3.4 අනුව නිෂ්ප්‍රභ වේ)",
    # Tajaka general yogas
    "Ishkavala yoga (all grahas in kendras/panapharas) — wealth, fortune":
        "ඉෂ්කවාල යෝගය (සියලු ග්‍රහයෝ කේන්ද්‍ර/පණපර ස්ථානවල) — ධනය, වාසනාව",
    "Induvara yoga (all grahas in apoklimas) — disappointments":
        "ඉන්දුවාර යෝගය (සියලු ග්‍රහයෝ අපොක්ලිම ස්ථානවල) — බලාපොරොත්තු කඩවීම්",
    # muhurta task notes (textbook ch.36)
    "8th house should be empty (Le, Sc lagnas also acceptable)": "8 වන භාවය හිස්ව තිබිය යුතුයි (සිංහ, වෘශ්චික ලග්නද පිළිගත හැක)",
    "8th empty, 4th strong; hora lord favorable w.r.t. natal 4th/A4; check D-4 (Venus strong)":
        "8 වැන්න හිස්, 4 වැන්න ශක්තිමත්; හෝරාධිපති ජන්ම කේන්දරයේ 4 වැන්නට/A4ට හිතකර විය යුතුයි; D-4 බලන්න (ශුක්‍ර ශක්තිමත්)",
    "8th house should be empty": "8 වන භාවය හිස්ව තිබිය යුතුයි",
    "10th house should be empty; even/odd month for boys/girls":
        "10 වන භාවය හිස්ව තිබිය යුතුයි; පිරිමි දරුවන්ට ඉරට්ටේ මාස, ගැහැනු දරුවන්ට ඔත්තේ මාස",
    "8th empty; Uttarayana better; check D-24": "8 වැන්න හිස්; උත්තරායනය වඩා හොඳයි; D-24 බලන්න",
    "8th empty (tithis 6, 12 secondary)": "8 වැන්න හිස් (6 සහ 12 තිථි ද්විතීයික)",
    "7th house should be clean; hora lord favorable w.r.t. natal 7th & UL; check D-9":
        "7 වන භාවය පිරිසිදුව තිබිය යුතුයි; හෝරාධිපති ජන්ම කේන්දරයේ 7 වැන්නට සහ උපපද ලග්නයට හිතකර විය යුතුයි; D-9 බලන්න",
    "Uttarayana for gentle deities, Dakshinayana for aggressive deities": "සෞම්‍ය දෙවිවරුන්ට උත්තරායනය, උග්‍ර දෙවිවරුන්ට දක්ෂිණායනය",
    "36.4: Lagna, 6th, 10th strong in rasi and D-10; first Vimshottari dasa lord favorable":
        "36.4: රාශි සහ D-10 කේන්දරවල ලග්නය, 6 සහ 10 වැන්න ශක්තිමත්; පළමු විංශෝත්තරී දශා අධිපති හිතකර",
    "Treat like job/venture start: 1, 2, 10, 11 strong; check D-10":
        "රැකියාවක්/ව්‍යාපාරයක් ආරම්භයක් ලෙස සලකන්න: 1, 2, 10, 11 ශක්තිමත්; D-10 බලන්න",
    "36.4: 1st, 4th (and A4) strong in rasi and D-16": "36.4: රාශි සහ D-16 කේන්දරවල 1 සහ 4 වැන්න (සහ A4) ශක්තිමත්",
    "36.4: 1st, 4th strong; Mars strong in D-4": "36.4: 1 සහ 4 වැන්න ශක්තිමත්; D-4 හි කුජ ශක්තිමත්",
    "General: benefic lagna, good tara, 8th empty": "සාමාන්‍ය: ශුභ ලග්නය, හොඳ තාරා බලය, 8 වැන්න හිස්",
    "Generic auspicious start: good tara, benefic hora/lagna, 8th empty":
        "සාමාන්‍ය සුබ ආරම්භය: හොඳ තාරා බලය, ශුභ හෝරාව/ලග්නය, 8 වැන්න හිස්",
}

# Engine sentences with a planet, sign or number in them. Applied once planets and signs are in Sinhala.
_PW = r"[^\s;,()\[\]—]+"   # one word: a Sinhala planet name, a number, a slash list
_FROM_SI = {"ලග්නය": "ලග්නයෙන්", "Lagna": "ලග්නයෙන්", "චන්ද්‍ර": "චන්ද්‍රයාගෙන්", "රවි": "රවිගෙන්"}
REGEX_SI = [
    (rf"only benefics \(({_PW})\) in 10th from ({_PW})", lambda m: f"{_FROM_SI.get(m[2], m[2] + 'ගෙන්')} 10 වැන්නේ ශුභ ග්‍රහයන් පමණක් ({m[1]})"),
    (r"ගුරු in (\d+)th with බුධ & ශුක්‍ර association", r"ගුරු \1 වැන්නේ, බුධ සහ ශුක්‍ර සම්බන්ධයෙන්"),
    (r"^(.+) all in kendra/trikona/exaltation$", r"\1 සියල්ලම කේන්ද්‍ර/ත්‍රිකෝණ/උච්ච ස්ථානවල"),
    (r"navamsa dispositor of (\d+)L exalted with 9L", r"\1 වන අධිපතිගේ නවාංශ අධිපති උච්චව, 9 වන අධිපති සමඟ"),
    (rf"benefics ({_PW}) in 6/7/8 from චන්ද්‍ර", r"චන්ද්‍රයාගෙන් 6/7/8 හි ශුභ ග්‍රහයන් (\1)"),
    (rf"({_PW}) 2nd & ({_PW}) 12th from (රවි|චන්ද්‍ර)", lambda m: f"{_FROM_SI[m[3]]} 2 වැන්නේ {m[1]}, 12 වැන්නේ {m[2]}"),
    (rf"({_PW}) in ({_PW}) in house (\d+)", r"\1 \2 රාශියේ, \3 වැන්නේ"),
    (r"benefics in kendras (\[[\d, ]+\])", r"කේන්ද්‍රවල ශුභ ග්‍රහයන් \1"),
    (r"malefics in kendras (\[[\d, ]+\])", r"කේන්ද්‍රවල පාප ග්‍රහයන් \1"),
    (rf"({_PW}) in Lagna with ({_PW})", r"\1 ලග්නයේ, \2 සමඟ"),
    (rf"MANAHOO by ({_PW}) \(ithasala spoiled\)", r"\1 නිසා මනාහූ (ඉථසාල බිඳේ)"),
    (rf"Kamboola \(({_PW}) ithasala with ({_PW})\)", r"කම්බූල (\1–\2 ඉථසාල)"),
    (rf"Nakta: ({_PW}) – ({_PW}) via ({_PW})", r"නක්ත: \1 – \2, \3 හරහා"),
    (rf"Yamaya: ({_PW}) – ({_PW}) via ({_PW}) \(after delay\)", r"යමයා: \1 – \2, \3 හරහා (ප්‍රමාදයකින් පසු)"),
    (rf"Hora lord ({_PW}) \(hora (\d+) from sunrise\)", r"හෝරාධිපති \1 (හිරු උදාවේ සිට \2 වන හෝරාව)"),
    (r"karana (.+?) \(unfavorable\)", lambda m: f"{KARANA_SI.get(m[1], m[1])} කරණය (අශුභ)"),
    (r"\bin house (\d{1,2})\b", r"\1 වැන්නේ"),
]
REGEX_SI = [(re.compile(p), r) for p, r in REGEX_SI]


YOGA_NAME_SI = {"Dharma-Karmadhipati Raja yoga": "ධර්ම-කර්මාධිපති රාජ යෝගය",
                "Vipareeta Raja yoga": "විපරීත රාජ යෝගය", "Raja yoga": "රාජ යෝගය",
                "Chandra from Surya": "සූර්යයාගෙන් චන්ද්‍රයා", "Ardha Chandra": "අර්ධ චන්ද්‍ර",
                "Gaja-Kesari": "ගජකේසරී", "Budha-Aditya": "බුධාදිත්‍ය", "Ubhayachari": "උභයචරී",
                "Anapha": "අනඵා", "Sunapha": "සුනඵා", "Durudhara": "දුරුධරා", "Kemadruma": "කේමද්‍රැම",
                "Subha": "ශුභ", "Asubha": "අශුභ", "Nipuna": "නිපුණ",
                "Daridra yoga": "දරිද්‍ර යෝගය", "Dhana yoga": "ධන යෝගය", "association": "සම්බන්ධය",
                # every other name the ch.11 detector prints, in Sinhala script
                "Duradhara": "දුරුධරා", "Adhi yoga": "අධි යෝගය", "Chandra-Mangala": "චන්ද්‍ර-මංගල",
                "Guru-Mangala": "ගුරු-මංගල", "Vesi": "වේසි", "Vosi": "වෝසි", "Kemadruma — partial": "කේමද්‍රැම — අර්ධ",
                "Ruchaka": "රුචක", "Bhadra": "භද්‍ර", "Sasa": "ශශ", "Malavya": "මාලව්‍ය", "Hamsa": "හංස",
                "Rajju": "රජ්ජු", "Musala": "මුසල", "Nala": "නල", "Maala": "මාලා", "Sarpa": "සර්ප",
                "Chakra": "චක්‍ර", "Chapa": "චාප", "Chatra": "ඡත්‍ර", "Dama": "දාම", "Danda": "දණ්ඩ", "Gada": "ගදා",
                "Gola": "ගෝල", "Hala": "හල", "Kedara": "කේදාර", "Kuta": "කූට", "Nauka": "නෞකා", "Pasa": "පාශ",
                "Sakata": "ශකට", "Sakti": "ශක්ති", "Samudra": "සමුද්‍ර", "Sara": "ශර", "Sringataka": "ශෘංගාටක",
                "Sula": "ශූල", "Vajra": "වජ්‍ර", "Vapi": "වාපී", "Veena": "වීණා", "Vihanga": "විහඟ", "Yava": "යව",
                "Yuga": "යුග", "Yupa": "යූප", "Kamala": "කමල",
                "Harsha": "හර්ෂ", "Sarala": "සරල", "Vimala": "විමල",
                "Amala": "අමල", "Parvata": "පර්වත", "Kahala": "කාහල", "Chamara": "චාමර", "Sankha": "ශංඛ",
                "Bheri": "භේරී", "Mridanga": "මෘදංග", "Sreenatha": "ශ්‍රීනාථ", "Matsya": "මත්ස්‍ය", "Khadga": "ඛඩ්ග",
                "Kusuma": "කුසුම", "Kalanidhi": "කලානිධි", "Kalpadruma": "කල්පද්‍රැම", "Parijata": "පාරිජාත",
                "Lagnadhi": "ලග්නාධි", "Hari": "හරි", "Hara": "හර", "Brahma": "බ්‍රහ්ම", "Vishnu": "විෂ්ණු",
                "Siva": "ශිව", "Trilochana": "ත්‍රිලෝචන", "Gouri": "ගෞරී", "Lakshmi": "ලක්ෂ්මී", "Saarada": "ශාරදා",
                "Bharathi": "භාරතී", "Saraswathi": "සරස්වතී", "Amsavatara": "අංශාවතාර", "Devendra": "දේවේන්ද්‍ර",
                "Indra": "ඉන්ද්‍ර", "Ravi": "රවි", "Bhaskara": "භාස්කර", "Kulavardhana": "කුලවර්ධන",
                "Gandharva": "ගන්ධර්ව", "Go": "ගෝ", "Vidyut": "විද්‍යුත්", "Makuta": "මකුට", "Jaya": "ජය",
                "Vasumati": "වසුමතී", "(full)": "(සම්පූර්ණ)", "(bad)": "(අශුභ)", "(alt.)": "(විකල්ප)",
                "Exalted benefic in 2nd": "2 වැන්නේ උච්ච ශුභ ග්‍රහයෙක්", "Parasara lagna-specific": "පරාශර ලග්න-විශේෂ",
                "(1) 1L-12L exchange with maraka": "(1) 1 සහ 12 වන අධිපතීන්ගේ පරිවර්තනය, මාරක සම්බන්ධයෙන්",
                "(3) Ketu with Lagna/Chandra, 1L in 8 with maraka": "(3) ලග්නය/චන්ද්‍ර සමඟ කේතු; 1 වන අධිපති මාරක සමඟ 8 හි",
                "(4) 1L with malefic in dusthana; 2L weak": "(4) 1 වන අධිපති පාප ග්‍රහයෙකු සමඟ දුස්ථානයක; 2 වන අධිපති දුර්වල",
                "(5) 5L in 6, 9L in 12 with maraka": "(5) 5 වන අධිපති 6 හි, 9 වන අධිපති මාරක සමඟ 12 හි",
                "(6) malefics in Lagna without 9L/10L, maraka-afflicted":
                    "(6) 9/10 වන අධිපතීන් නොමැතිව ලග්නයේ පාප ග්‍රහයන්; මාරක පීඩිත"}


# Whole words only: a plain replace turned "restraint" into "restවර්ෂාවt" ("rain" inside it).
# A phrase that starts or ends with a letter must not touch a letter outside it.
_PHRASE_RX = [(re.compile((r"(?<![A-Za-z])" if en[0].isalpha() else "") + re.escape(en)
                          + (r"(?![A-Za-z])" if en[-1].isalpha() else "")), si.replace("\\", "\\\\"))
              for en, si in sorted(PHRASE_SI, key=lambda kv: -len(kv[0]))]


def si_yoga_name(s):
    """Yoga names in Sinhala script; the English qualifiers around them too."""
    out = str(s)
    for en, si in sorted(YOGA_NAME_SI.items(), key=lambda kv: -len(kv[0])):
        # whole words only: "Go" must not eat the start of "Gola"
        out = re.sub(r"(?<![A-Za-z])" + re.escape(en) + r"(?![A-Za-z])", si, out)
    out = re.sub(r"(\d{1,2})L\b", r"\1ප", out)
    for rx, si in _PHRASE_RX:
        out = rx.sub(si, out)
    out = re.sub(r"\b(" + "|".join(_WORD_SI) + r")\b", lambda m: _WORD_SI[m.group(1)], out)
    return re.sub(r"\s{2,}", " ", out).strip()


def si_text(s):
    """Best-effort Sinhala rendering of an engine-generated English line.
    Order matters: proper names first (so 'Chand' is not eaten by the word 'and'), then phrases, then single words."""
    out = str(s)
    if out.strip() in WHOLE_SI:
        return WHOLE_SI[out.strip()]
    for en, si in sorted(PL_EN2SI.items(), key=lambda kv: -len(kv[0])):
        out = out.replace(en, si)
    for en, si in sorted(SIGN_EN2SI.items(), key=lambda kv: -len(kv[0])):
        out = out.replace(en, si)
    for rx, rep in REGEX_SI:
        out = rx.sub(rep, out)
    out = re.sub(r"\b(\d{1,2})L\b", r"\1 වන අධිපති", out)
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
    for rx, si in _PHRASE_RX:
        out = rx.sub(si, out)
    out = re.sub(r"\b(" + "|".join(_WORD_SI) + r")\b", lambda m: _WORD_SI[m.group(1)], out)
    out = re.sub(r"\b(\d{1,2})(st|nd|rd|th)\b", r"\1 වැනි", out)
    out = out.replace("ලග්නයගෙන්", "ලග්නයෙන්").replace("චන්ද්‍රගෙන්", "චන්ද්‍රයාගෙන්")
    return re.sub(r"\s{2,}", " ", out).strip()


VARNA_SI = {"Brahmana": "බ්‍රාහ්මණ", "Brahmin": "බ්‍රාහ්මණ", "Kshatriya": "ක්ෂත්‍රිය", "Vaishya": "වෛශ්‍ය", "Shudra": "ශූද්‍ර"}
VASHYA_SI = {"Chatushpada": "චතුෂ්පද", "Manava": "මානව", "Jalachara": "ජලචර", "Vanachara": "වනචර", "Keeta": "කීට"}
YONI_SI = {"Horse": "අශ්ව", "Elephant": "ගජ", "Sheep": "මේෂ", "Serpent": "සර්ප", "Dog": "ශ්වාන", "Cat": "මාර්ජාර",
           "Rat": "මූෂික", "Cow": "ගෝ", "Buffalo": "මහිෂ", "Tiger": "ව්‍යාඝ්‍ර", "Deer": "මෘග", "Monkey": "වානර",
           "Mongoose": "නකුල", "Lion": "සිංහ"}
GANA_SI = {"Deva": "දේව", "Manushya": "මනුෂ්‍ය", "Rakshasa": "රාක්ෂස"}
NADI_SI = {"Adi": "ආදි", "Aadi": "ආදි", "Madhya": "මධ්‍ය", "Antya": "අන්ත්‍ය"}
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
_KOOTA_WORDS_SI = [("Bhakoot dosha", "භකූට දෝෂය"), ("Nadi dosha", "නාඩි දෝෂය"), ("cancelled", "නිෂ්ප්‍රභ වී ඇත"),
                   ("same/friendly අධිපතීන්", "අධිපතීන් සම/මිත්‍ර"), ("same/friendly lords", "අධිපතීන් සම/මිත්‍ර"),
                   ("(same)", "(සම)"), ("(6/8)", "(6/8 තත්ත්වය)"), ("(friend)", "(මිත්‍ර)"), ("(neutral)", "(සම)"),
                   ("(enemy)", "(සතුරු)"), ("(own)", "(ස්වකීය)")]


def si_koota(det):
    """Sinhala for an Ashtakoota detail line, e.g. 'Guru (friend) / Kuja (friend)' or
    'Dhanu / Mesha (5/9) — Bhakoot dosha, cancelled (same/friendly lords)'."""
    for tbl in (VARNA_SI, VASHYA_SI, YONI_SI, GANA_SI, NADI_SI, NAK_EN2SI):
        for en, si in sorted(tbl.items(), key=lambda kv: -len(kv[0])):
            det = re.sub(r"\b" + re.escape(en) + r"\b", si, det)
    det = si_text(det)
    for en, si in _KOOTA_WORDS_SI:
        det = det.replace(en, si)
    return det
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
    H = [f'''<div style="text-align:center">{LOGO_IMG_SMALL}<div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:9pt; font-size:17pt">ඔබේ කේන්දරයේ මූලික තොරතුරු</h1>
      <div class="muted">{esc(a.name)} · {esc(a.date)} · {esc(a.time)} · {esc(a.place or "")}</div></div>''']
    H.append(f'<div class="two" style="margin-top:6pt"><div style="flex:0 0 76mm">{south_indian_html_si(labels, "රාශි චක්‍රය", 76)}</div><div>')
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
    H.append(plain_summary_si(d, a, now_local, compact=True))
    H.append('<p class="muted" style="font-size:8.3pt; margin:4pt 0"><b>ලග්නය</b> = ඔබ උපන් මොහොතේ නැගෙනහිරින් උදා වූ රාශිය · <b>ලග්නාධිපති</b> = ලග්න රාශියේ අධිපති ග්‍රහයා · '
             '<b>නැකත</b> = උපන් මොහොතේ චන්ද්‍රයා සිටි තාරකා කොටස · <b>දශාව</b> = ජීවිතයේ මේ කාලය පාලනය කරන ග්‍රහයා.</p>')
    H.append('<p class="small" style="margin:6pt 0"><b>මේක නොමිලේ ලැබෙන මූලික පත්‍රිකාවක්.</b> යෝග, දශා කාල, ගෝචරය සහ ඉදිරි අවුරුදු ගැන '
             'සම්පූර්ණ විග්‍රහයකට අපගේ <b>කේන්දර සාර (A1)</b> වාර්තාව බලන්න.</p>')
    H.append('<p class="disc">ජ්‍යොතිෂය ප්‍රවණතා ගැන ප්‍රතිබිම්බනාත්මක මගපෙන්වීමකි; ස්ථිර අනාවැකි නොවේ. වෛද්‍ය, නීතිමය හෝ මූල්‍ය උපදෙස් නොවේ. '
             'උපන් වේලාවේ නිරවද්‍යතාව ප්‍රතිඵල වලට බලපායි. ගණනය: Swiss Ephemeris.</p>')
    H.append(f'<div class="brandfoot" style="margin-top:6pt; padding-top:4pt"><div class="brandmark" style="font-size:11pt">{esc(BRAND)}</div>'
             + (f'<div class="muted">{esc(BRAND_CONTACT)}</div>' if BRAND_CONTACT else "") + "</div>")
    return "\n".join(H)


def current_dashas(d, now_local):
    """(maha dasha, antar dasha) running at now_local, or None for either."""
    now_utc = now_local.astimezone(timezone.utc)
    for m in d["vimshottari"]["mahadashas"]:
        if datetime.fromisoformat(m["start"]) <= now_utc < datetime.fromisoformat(m["end"]):
            ad = next((s for s in m.get("sub", [])
                       if datetime.fromisoformat(s["start"]) <= now_utc < datetime.fromisoformat(s["end"])), None)
            return m, ad
    return None, None


def pch_en(p):
    """English rendering of the engine's panchanga: 'Mangalavara (Tuesday)', 'Krishna Panchami'."""
    vara = str(p.get("vara", ""))
    base = re.sub(r"\s*\(.*?\)\s*$", "", vara)
    day = WEEKDAY_EN.get(re.sub(r"vara$", "", base, flags=re.I).strip(), "")
    out = f"{base} ({day})" if day else base
    if "before sunrise" in vara:
        out += ", born before sunrise: the previous day's vara"
    return {"vara": out, "tithi": str(p.get("tithi", ""))}


# Plain English for the English G (the Sinhala G's LAGNA_PLAIN_SI / HOUSE_AREA_SI in English)
LAGNA_PLAIN_EN = [
    ("active, quick to decide and happy to lead", "learning patience will help you"),
    ("steady, patient and fond of life's comforts", "being a little more open to change helps"),
    ("clever, a good talker and keen to learn new things", "finish one task before starting the next"),
    ("sensitive, loving towards your family and in need of security", "think things through rather than deciding on feelings alone"),
    ("confident, dignified and generous", "keeping pride in balance works in your favour"),
    ("careful with detail, orderly and glad to help others", "go easy on criticism, of yourself and of others"),
    ("balanced, warm in relationships and fond of beautiful things", "make decisions on time instead of putting them off"),
    ("deep-thinking, deeply committed and drawn to explore", "let trust and flexibility grow"),
    ("honest, principled, far-sighted and philosophical", "think carefully before taking big risks"),
    ("disciplined, practical and willing to work your way up", "let the people close to you see your feelings too"),
    ("full of new ideas, humane and independent", "stay close to the people around you"),
    ("compassionate, artistic and spiritually inclined", "keep practical limits and plans"),
]
HOUSE_AREA_EN = {1: "yourself, your health and personality", 2: "money and family", 3: "effort and siblings",
                 4: "home and mother", 5: "children and education", 6: "work, health habits and competition",
                 7: "marriage and partnerships", 8: "sudden changes and inheritance", 9: "fortune and father",
                 10: "career and position", 11: "income and gains", 12: "expenses and foreign lands"}


def plain_summary_en(d, a, now_local):
    """'In simple words' for the English G (same points as plain_summary_si, compact)."""
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    tz = ZoneInfo(a.tz)
    now_utc = now_local.astimezone(timezone.utc)
    md, ad = current_dashas(d, now_local)
    ym = lambda x: datetime.fromisoformat(x).astimezone(tz).strftime("%Y-%m")  # noqa: E731
    tone = lambda lord: "a good time" if period_tone_si(P, lord) == TONE_GOOD_SI else "a time for patience and care"  # noqa: E731
    traits, tip = LAGNA_PLAIN_EN[ls]
    L = [f"<li><b>Your nature:</b> with {esc(sign_en(ls))} Lagna you are {traits}. {tip[0].upper() + tip[1:]}.</li>"]
    if md:
        L.append(f"<li><b>The period you are in:</b> from {ym(md['start'])[:4]} to {ym(md['end'])[:4]} you are in the "
                 f"{PLANET_EN[md['lord']]} Maha Dasha; in these years life's main focus is "
                 f"{HOUSE_AREA_EN[P[md['lord']]['house']]}.</li>")
    if ad:
        L.append(f"<li><b>Until {ym(ad['end'])}:</b> {HOUSE_AREA_EN[P[ad['lord']]['house']]} come to the fore, "
                 f"{tone(ad['lord'])}.</li>")
    after = datetime.fromisoformat(ad["end"]) if ad else now_utc
    for m in d["vimshottari"]["mahadashas"]:
        nxt = next((x for x in m.get("sub", []) if datetime.fromisoformat(x["start"]) >= after
                    and period_tone_si(P, x["lord"]) == TONE_GOOD_SI), None)
        if nxt and datetime.fromisoformat(nxt["start"]) < now_utc + timedelta(days=6 * 365):
            L.append(f"<li><b>A good time ahead:</b> {ym(nxt['start'])} to {ym(nxt['end'])}, for "
                     f"{HOUSE_AREA_EN[P[nxt['lord']]['house']]}.</li>")
            break
    return '<div class="box plain compact"><div class="lbl">In simple words</div><ul>' + "".join(L) + "</ul></div>"


def build_g_en(d, a, now_local):
    """The free one-page summary (G) in English: the same facts and wording as build_g."""
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    moon, lord = P["Mo"], jc.SIGN_LORD[d["lagna"]["sign_idx"]]
    labels = {ls: ["Lagna"]}
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        labels.setdefault(P[c]["sign_idx"], []).append(PLANET_EN[c])
    md, ad = current_dashas(d, now_local)
    nama = jc.nama_nakshatra(moon["lon"])
    pch = pch_en(d["panchanga"])
    span = lambda x: f" ({fmt_date(x['start'], a.tz)} – {fmt_date(x['end'], a.tz)})"  # noqa: E731
    H = [f'''<div style="text-align:center">{LOGO_IMG_SMALL}<div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE_EN)}</div>
      <h1 style="margin-top:9pt; font-size:17pt">Your Birth Chart at a Glance</h1>
      <div class="muted">{esc(a.name)} · {esc(a.date)} · {esc(a.time)} · {esc(a.place or "")}</div></div>''']
    H.append(f'<div class="two" style="margin-top:6pt"><div style="flex:0 0 76mm">'
             f'{south_indian_html_si(labels, "Rasi chart", 76, lang="en")}</div><div>')
    H.append("<table>"
             f"<tr><td><b>Lagna (Ascendant)</b></td><td>{sign_en(ls)} {dms(d['lagna']['deg_in_sign'])}</td></tr>"
             f"<tr><td><b>Lagna lord</b></td><td>{PLANET_EN[lord]}, in house {P[lord]['house']}</td></tr>"
             f"<tr><td><b>Moon sign (Rasi)</b></td><td>{sign_en(moon['sign_idx'])}</td></tr>"
             f"<tr><td><b>Birth star (Nakshatra)</b></td><td>{esc(moon['nakshatra'])}, pada {moon['pada']}</td></tr>"
             f"<tr><td><b>Naming letter</b></td><td>{esc(nama['syllable'])} · {esc(nama['sinhala'])}</td></tr>"
             f"<tr><td><b>Current Maha Dasha</b></td><td>{PLANET_EN[md['lord']] + span(md) if md else '—'}</td></tr>"
             + (f"<tr><td><b>Antar Dasha</b></td><td>{PLANET_EN[ad['lord']]}{span(ad)}</td></tr>" if ad else "")
             + f"<tr><td><b>Panchanga</b></td><td>{esc(pch['vara'])} · {esc(pch['tithi'])}</td></tr>"
             "</table></div></div>")
    H.append(plain_summary_en(d, a, now_local))
    H.append('<p class="muted" style="font-size:8.3pt; margin:4pt 0"><b>Lagna</b> = the sign rising in the east at your birth · '
             '<b>Lagna lord</b> = the planet that rules it · <b>Nakshatra</b> = the star the Moon was in · '
             '<b>Dasha</b> = the planet that governs this part of your life.</p>')
    H.append('<p class="small" style="margin:6pt 0"><b>This is a free summary sheet.</b> For a full reading (yogas, dasha '
             'periods, transits and the years ahead), see our <b>Kendra Sara (A1)</b> report, written in Sinhala.</p>')
    H.append('<p class="disc">Astrology offers reflective guidance on tendencies, not fixed predictions, and is not '
             'medical, legal or financial advice. Results depend on an accurate birth time. Calculation: Swiss Ephemeris.</p>')
    H.append(f'<div class="brandfoot" style="margin-top:6pt; padding-top:4pt"><div class="brandmark" style="font-size:11pt">{esc(BRAND)}</div>'
             + (f'<div class="muted">{esc(BRAND_CONTACT)}</div>' if BRAND_CONTACT else "") + "</div>")
    return "\n".join(H)


# ================================================================ C1 — Varsha Phala
# Plain words for the C series (year, month, Sade Sati, dasha change): the "simple words" box of each
# report, and the glossary page. Everything here reads data the reports already show.
_PLAIN_SLOT_C = "<!--c2-plain-->"   # where C2 puts its own box inside C1's pages
_SAHAM_PLAIN_C = {"Roga (illness)": "සෞඛ්‍යය (රෝග සහමය)"}
_GLOSS_YEAR_C = ("ලග්නය", "රාශිය", "භාවය", "වක්‍ර (ව)")
_GLOSS_YEAR_EXTRA_C = (
    ("වර්ෂ ඵල (තාජක ක්‍රමය)", "උපන් දිනයෙන් උපන් දිනයට අවුරුද්දකට වෙනම කේන්දරයක් සාදා කියවන ක්‍රමය."),
    ("වර්ෂ ප්‍රවේශය / වර්ෂ කුණ්ඩලිය", "රවි ඔබ උපන් මොහොතේ සිටි ස්ථානයටම නැවත එන මොහොත, සහ ඒ මොහොතට සාදන අවුරුද්දේ කේන්දරය."),
    ("මුන්ථා", "ජන්ම ලග්නයේ සිට අවුරුද්දකට රාශියක් බැගින් යන ලක්ෂ්‍යය; අවුරුද්දේ අවධානය පෙන්වයි."),
    ("වර්ෂේශ", "අවුරුද්ද පාලනය කරන ප්‍රධාන ග්‍රහයා."),
    ("හර්ෂ බල / පංච වර්ගීය බල", "තාජක ක්‍රමයේ ග්‍රහ ශක්තිය මනින ක්‍රම දෙකක් (0–20; වැඩි = ශක්තිමත්)."),
    ("ඉථසාල / ඊසර්ඵ", "ග්‍රහයන් දෙදෙනෙක් ළං වෙමින් (ඉථසාල — කාරණය ඉටු වීමට නැඹුරු) හෝ වෙන් වෙමින් (ඊසර්ඵ — ප්‍රමාද විය හැක). "
     "මනාහූ = වෙනත් ග්‍රහයෙක් ඉථසාලය බිඳීම; කම්බූල = චන්ද්‍රයාගේ සහාය."),
    ("සහමය", "ජීවිතයේ එක් කාරණයක් (වාසනාව, රැකියාව ආදී) සඳහා ගණනය කරන ලක්ෂ්‍යයක්."),
    ("මුද්දා දශා", "අවුරුද්ද ග්‍රහයන් 9 අතර කෙටි කාල වලට බෙදන ක්‍රමය."),
)
_GLOSS_CAL_C = _GLOSS_YEAR_C + ("මහා දශාව / අන්තර් දශාව", "ගෝචරය", "ඒරාෂ්ටක ශනි (සඩේ සති)")
_LORD_HOUSES_C = ("අධිපති භාව", "ග්‍රහයා අධිපති වන රාශි ඔබේ කේන්දරයේ වැටෙන භාව; ඒ ග්‍රහයාගේ කාලවලදී එම ජීවිත ක්ෂේත්‍ර ඉස්මතු වේ.")
_GLOSS_SS_C = ("ලග්නය", "රාශිය", "භාවය", "වක්‍ර (ව)", "උච්ච / නීච / ස්වක්ෂේත්‍ර", "ගෝචරය", "ඒරාෂ්ටක ශනි (සඩේ සති)")
_GLOSS_SS_EXTRA_C = (
    ("ජන්ම චන්ද්‍ර රාශිය", "ඔබ උපන් මොහොතේ චන්ද්‍රයා සිටි රාශිය. ඒරාෂ්ටක, අෂ්ටම සහ අර්ධාෂ්ටම ශනි ගණන් කරන්නේ මෙතැන් සිටයි."),
    ("ආරෝහණ / ශිඛර / අවරෝහණ", "ඒරාෂ්ටක ශනියේ අවධි තුන: පටන් ගැනීම (චන්ද්‍රගෙන් 12), මැද කාලය (චන්ද්‍ර රාශියේම), "
     "සහ ක්‍රමයෙන් සැහැල්ලු වන අවසානය (චන්ද්‍රගෙන් 2)."),
    _LORD_HOUSES_C,
    ("අෂ්ටකවර්ගය (BAV / SAV)", "එක් එක් රාශියට ග්‍රහයන්ගෙන් ලැබෙන හොඳ ලකුණු (බින්දු) ගණන් කරන ක්‍රමය. "
     "BAV = එක් ග්‍රහයෙකුගේ ලකුණු (0–8); SAV = සියලු ග්‍රහයන්ගේ ලකුණු එකතුව."),
)
_GLOSS_SANDHI_C = ("ලග්නය", "භාවය", "මහා දශාව / අන්තර් දශාව", "ගෝචරය", "උච්ච / නීච / ස්වක්ෂේත්‍ර", "ඒරාෂ්ටක ශනි (සඩේ සති)")
_GLOSS_SANDHI_EXTRA_C = (
    ("දශා සන්ධිය", "එක් මහා දශාවක් අවසන් වී ඊළඟ එක පටන් ගන්නා මාරු කාලය; මාරු දිනයට පෙර සහ පසු මාස කිහිපයක් පුරා පැතිරේ."),
    _LORD_HOUSES_C,
    ("කාරකත්වය", "ග්‍රහයා ස්වභාවයෙන්ම නියෝජනය කරන දේ — උදාහරණයක් ලෙස ගුරු: ප්‍රඥාව, දරුවන්, ධනය."),
)
_GLOSS_MONTH_C = ("ලග්නය", "රාශිය", "භාවය")
_GLOSS_MONTH_EXTRA_C = (
    ("මාස ඵල (මාස කුණ්ඩලිය)", "රවි ඔබ උපන් මොහොතේ සිටි ස්ථානයේ සිට තවත් රාශියක් (අංශක 30ක්) ගමන් කරන සෑම මොහොතකම "
     "සාදන කේන්දරය; අවුරුද්දේ එක් මාසයක ප්‍රවණතා කියවයි."),
    ("මාසේශ / වර්ෂේශ", "මාසය පාලනය කරන ප්‍රධාන ග්‍රහයා / අවුරුද්ද පාලනය කරන ප්‍රධාන ග්‍රහයා."),
    _GLOSS_YEAR_EXTRA_C[2],
    ("සුදර්ශන චක්‍ර අන්තර් රාශිය", "මුන්ථාවේ සිට මාසයකට එක රාශියක් බැගින් ඉදිරියට යන රාශිය; මේ මාසයේ ග්‍රහ ස්ථාන ඒ රාශියේ සිටද කියවයි."),
)
_CLOSING_C = "<li>මේවා ප්‍රවණතා පමණි — ඔබේ උත්සාහය සහ හොඳ තීරණ ඊටත් වඩා වැදගත්.</li>"


def _plain_box_c(items):
    return '<div class="box plain"><div class="lbl">සරලව කිවහොත්</div><ul>' + "".join(items) + "</ul></div>"


_GLOSS_HEAD_C = '<div class="vblock"><h2 class="sec">වචන කිහිපයක තේරුම</h2>'


def _gloss_method_c(terms, extra, method_line):
    """A C report's last page: the glossary, then the method note, on one page as in A1. They go as one block
    that is never split, with no forced page break: a page that runs a few lines long then moves the pair to
    the next page whole, instead of leaving those few lines on a page of their own."""
    return (_GLOSS_HEAD_C + glossary_html(terms, extra)
            + disclaimer_block(method_line).replace('<div class="pb"></div>', "", 1) + "</div>")


def _mudda_strength_c(v):
    """C1 section 5's own rule: the three strongest planets by Pancha Vargeeya Bala give the fruitful mudda
    periods, the two weakest the ones for patience."""
    pv = v["pancha_vargeeya"]
    return ({k for k, _ in sorted(pv.items(), key=lambda kv: -kv[1])[:3]},
            {k for k, _ in sorted(pv.items(), key=lambda kv: kv[1])[:2]})


def _runs_c(items):
    """[(label, flag)] -> 'a – b, c': the flagged labels, runs of neighbouring rows joined into one span."""
    runs, run = [], []
    for lab, ok in list(items) + [(None, False)]:
        if ok:
            run.append(lab)
        elif run:
            runs.append(run[0] if len(run) == 1 else f"{run[0]} – {run[-1]}")
            run = []
    return ", ".join(runs)


def _plain_year_c(d, a, now_local, year, months=None, tr=None):
    """'In simple words' for the year reports: the year's theme (Muntha, Varshesha), what runs now, its good
    stretches and the ones for care. C1 times the year by its mudda periods; C2 passes its calendar's
    (month, tone) rows instead, plus the transit snapshot."""
    v = d["varsha_kundali"]
    inv = {s: i for i, s in enumerate(jc.SIGNS)}
    mh = jc.house_from(d["lagna"]["sign_idx"], inv[v["muntha"]])
    vsh = v["varshesha"]
    today, nowl = now_local.strftime("%Y-%m-%d"), now_local.strftime("%Y-%m-%d %H:%M")
    L = [f"<li><b>මේ අවුරුද්දේ ප්‍රධාන තේමාව:</b> {v['varsha_pravesha_local'][:10]} සිට ඊළඟ උපන් දිනය දක්වා "
         f"ඔබේ වැඩි අවධානය යොමු වන්නේ {HOUSE_PLAIN_SI[mh]} වෙතයි.</li>",
         f"<li><b>අවුරුද්දේ ප්‍රධාන ග්‍රහයා:</b> {PLANET_SI[vsh]} — {PLANET_NATURE_SI[vsh]}.</li>"]
    if months is None:
        strong, weak = _mudda_strength_c(v)
        tone = lambda m: (" — වඩාත් හොඳ කාලයක්" if m["lord"] in strong  # noqa: E731
                          else " — ඉවසීමෙන් කටයුතු කළ යුතු කාලයක්" if m["lord"] in weak else "")
        cur = next((m for m in v["mudda"] if m["start"][:16] <= nowl < m["end"][:16]), None)
        if cur:
            L.append(f"<li><b>දැන්:</b> {cur['end'][:10]} දක්වා ගත වන්නේ {PLANET_SI[cur['lord']]} ග්‍රහයාගේ කාලයයි "
                     f"({MUDDA_HINT[cur['lord']]}){tone(cur)}.</li>")
        # what is still ahead; for a year already over, the whole year
        left = [m for m in v["mudda"] if m["start"][:16] > nowl] or ([] if cur else v["mudda"])
        span = lambda m: f"{m['start'][:10]} – {m['end'][:10]} ({MUDDA_HINT[m['lord']]})"  # noqa: E731
        good = [span(m) for m in left if m["lord"] in strong]
        care = [span(m) for m in left if m["lord"] in weak]
        if good:
            L.append("<li><b>වඩාත් හොඳ කාල:</b> " + "; ".join(good) + " — උත්සාහයට හොඳ ප්‍රතිඵල ලැබෙන කාල.</li>")
        elif not (cur and cur["lord"] in strong):
            L.append("<li><b>වඩාත් හොඳ කාල:</b> මේ අවුරුද්දේ ශක්තිමත්ම කාල දැනටමත් ගෙවී ඇත; "
                     "ඉතිරි කාලය ස්ථාවරව, සැලසුම් සහිතව ගත කරන්න.</li>")
        if care:
            L.append("<li><b>ඉවසීමෙන් කටයුතු කළ යුතු කාල:</b> " + "; ".join(care)
                     + " — ලොකු තීරණ හොඳින් සිතා බලා ගන්න.</li>")
    else:
        left = [(lab, t) for lab, t in months if lab >= today[:7]] or list(months)
        good = _runs_c((lab, t == "හිතකර") for lab, t in left)
        care = _runs_c((lab, t == "අවධානය") for lab, t in left)
        L.append("<li><b>හොඳ මාස:</b> " + (f"{good} — ඔබේ දශා කාල හිතකර පැත්තට යොමු වන මාස." if good else
                 "ඉතිරි මාස බොහොමයක් මිශ්‍රයි — ස්ථාවරව, සැලසුම් සහිතව කටයුතු කරන්න.") + "</li>")
        L.append("<li><b>සැලකිලිමත් විය යුතු මාස:</b> " + (f"{care} — ලොකු තීරණ ඉවසීමෙන්, හොඳින් සිතා බලා ගන්න." if care else
                 "ඉතිරි මාස අතර විශේෂයෙන් අපහසු මාසයක් පෙනෙන්නේ නැත.") + "</li>")
        if tr:
            L.append(f"<li><b>දැන් ශනි:</b> {SATURN_FROM_MOON_SI[tr['Sa']['from_moon']]}. "
                     f"<b>ගුරු:</b> {JUPITER_FROM_MOON_SI[tr['Ju']['from_moon']]}.</li>")
    return _plain_box_c(L + [_CLOSING_C])


def _plain_month_c(d, a, year, month):
    """'In simple words' for the month report: its dates, its theme (the month lord's natal house), the year's
    mudda periods that fall in it (C1's strong/weak rule) and the year behind it."""
    v = d["varsha_kundali"]
    m = v["masa"]
    inv = {s: i for i, s in enumerate(jc.SIGNS)}
    jd0, _ = jc.to_jd_ut(datetime.strptime(m["pravesha_local"], "%Y-%m-%d %H:%M"), a.tz)
    # the month ends when the Sun has gone one more sign on: the next month's pravesha (as the engine finds it)
    end = jc.jd_to_datetime(jc.find_sun_at((d["planets"]["Su"]["lon"] + 30 * month) % 360, jd0 + 30.44))
    s0, s1 = m["pravesha_local"], end.astimezone(ZoneInfo(a.tz)).strftime("%Y-%m-%d %H:%M")
    ms = m["masesha"]
    mh = jc.house_from(d["lagna"]["sign_idx"], inv[v["muntha"]])
    strong, weak = _mudda_strength_c(v)
    parts = []
    for x in v["mudda"]:
        if x["start"] < s1 and x["end"] > s0:
            tone = " — වඩාත් හොඳ කාලයක්" if x["lord"] in strong else " — ඉවසීමෙන් කටයුතු කරන්න" if x["lord"] in weak else ""
            parts.append(f"{max(x['start'], s0)[:10]} – {min(x['end'], s1)[:10]}: {PLANET_SI[x['lord']]} කාලය "
                         f"({MUDDA_HINT[x['lord']]}){tone}")
    h = d["planets"][ms]["house"]
    L = [f"<li><b>මේ මාසය:</b> {s0[:10]} සිට {s1[:10]} දක්වා ({year} උපන් දිනයෙන් පසු {month} වන මාසය).</li>",
         f"<li><b>මාසයේ ප්‍රධාන තේමාව:</b> {HOUSE_PLAIN_SI[h]}. හේතුව: මාසයේ ප්‍රධාන ග්‍රහයා (මාසේශ) {PLANET_SI[ms]} "
         f"ඔබේ ජන්ම කේන්දරයේ {h} වැන්නේ සිටීම.</li>"]
    if parts:
        L.append("<li><b>මාසය තුළ:</b> " + "; ".join(parts) + ".</li>")
    L.append(f"<li><b>අවුරුද්ද පුරා:</b> අවධානය {HOUSE_AREA_SI[mh]} වෙත; ප්‍රධාන ග්‍රහයා {PLANET_SI[v['varshesha']]}.</li>")
    return _plain_box_c(L + [_CLOSING_C])


def _plain_sadesati_c(spells, now_utc, tz, sa_n):
    """'In simple words' for C3: where the person is now, the next Saturn spell, the next 7½ years, and how
    natal Saturn colours them (section 2's own rule)."""
    ym = lambda x: x.astimezone(ZoneInfo(tz)).strftime("%Y-%m")  # noqa: E731
    whole = merge_spells(spells)   # 12 -> 1 -> 2 as one 7½-year stretch
    cur = next((x for x in spells if x[0] <= now_utc <= x[1]), None)
    cur_w = next((x for x in whole if x[0] <= now_utc <= x[1]), None)
    nxt = next((x for x in whole if x[0] > now_utc and (not cur_w or x[0] >= cur_w[1])), None)
    ss = next((x for x in whole if x[2] == "ඒරාෂ්ටක ශනි" and x[0] > now_utc), None)
    L = []
    if cur:
        L.append(f"<li><b>දැන් ඔබට ({ym(cur[0])} – {ym(cur[1])}):</b> {SATURN_FROM_MOON_SI[cur[3]]}.</li>")
        if cur_w and nxt:
            L.append("<li><b>ඉන්පසු:</b> " + (f"මුළු ඒරාෂ්ටක ශනිය {ym(cur_w[1])} දී අවසන් වේ. " if cur_w[1] > cur[1] else "")
                     + f"{ym(cur_w[1])} සිට {ym(nxt[0])} දක්වා ශනිගෙන් විශේෂ බරක් නැති, සැහැල්ලු කාලයක්.</li>")
    else:
        L.append("<li><b>දැන් ඔබට:</b> " + (f"{ym(nxt[0])} දක්වා " if nxt else "")
                 + "ඒරාෂ්ටක, අෂ්ටම හෝ අර්ධාෂ්ටම ශනි කාලයක් නැත — ශනිගෙන් විශේෂ බරක් නැති කාලයක්.</li>")
    if nxt:
        about = SS_PHASE_SI[nxt[3]][1] if nxt[2] != "ඒරාෂ්ටක ශනි" else "වගකීම් සහ ඉවසීම වැඩෙන අවුරුදු 7½ක කාලයක්"
        L.append(f"<li><b>ඊළඟ ශනි කාලය:</b> {nxt[2]}, {ym(nxt[0])} සිට {ym(nxt[1])} දක්වා — {about}.</li>")
    if ss and ss is not nxt and not (cur and cur[2] == "ඒරාෂ්ටක ශනි"):
        L.append(f"<li><b>ඊළඟ ඒරාෂ්ටක ශනිය (සඩේ සති):</b> {ym(ss[0])} දී පටන් ගනී (අවුරුදු 7½ක් පමණ).</li>")
    good = sa_n["house"] in (3, 6, 10, 11) or si_dignity(sa_n["dignity"]) in ("උච්ච", "ස්වක්ෂේත්‍ර", "මූලත්‍රිකෝණ")
    L.append("<li><b>ඔබේ ජන්ම ශනි:</b> " + ("ශක්තිමත් ස්ථානයක සිටින නිසා මේ කාලවල බර සාපේක්ෂව අඩුයි." if good
                                            else "මේ කාලවලදී ඉවසීම සහ ක්‍රමවත් බව ඔබට විශේෂයෙන් උපකාරී වේ.") + "</li>")
    L.append("<li>මේවා බිය විය යුතු කාල නොවේ — වගකීම, ඉවසීම සහ විනය වැඩෙන කාලයි.</li>")
    return _plain_box_c(L)


def _plain_sandhi_c(P, cur_md, nxt_md, tz):
    """'In simple words' for C4: the date of the change, the period ending and the one beginning, how to take it."""
    A, B = cur_md["lord"], nxt_md["lord"]
    loc = lambda x: datetime.fromisoformat(x).astimezone(ZoneInfo(tz))  # noqa: E731
    yrs = lambda m: f"{loc(m['start']).year}–{loc(m['end']).year}"  # noqa: E731
    return _plain_box_c([
        f"<li><b>ලොකු කාල මාරුවක්:</b> {loc(cur_md['end']).strftime('%Y-%m-%d')} දින ඔබේ {PLANET_SI[A]} මහා දශාව අවසන් වී "
        f"{PLANET_SI[B]} මහා දශාව පටන් ගනී. මහා දශාව යනු ජීවිතයේ අවුරුදු ගණනක කාලයක් එක් ග්‍රහයෙකුගේ බලපෑමට යටත් වීමයි.</li>",
        f"<li><b>දැන් ගෙවෙන කාලය ({yrs(cur_md)}):</b> {PLANET_SI[A]} දශාවේ වැඩි අවධානය {HOUSE_PLAIN_SI[P[A]['house']]} වෙතයි.</li>",
        f"<li><b>ඉදිරි කාලය ({yrs(nxt_md)}):</b> "
        + (f"{PLANET_SI[B]} දශාවේදීත් ප්‍රධාන අවධානය එම කාරණා වෙතම රැඳේ. " if P[B]["house"] == P[A]["house"]
           else f"{PLANET_SI[B]} දශාවේ අවධානය {HOUSE_PLAIN_SI[P[B]['house']]} දෙසට හැරේ. ")
        + ("නව ග්‍රහයා හොඳ ස්ථානයක සිටින නිසා මාරුව සාපේක්ෂව පහසුයි." if period_tone_si(P, B) == TONE_GOOD_SI
           else "මුල් කාලයේ අලුත් තත්ත්වයට හැඩ ගැසීමට ටික කාලයක් ගත විය හැක — ඉවසීමෙන් කටයුතු කරන්න.") + "</li>",
        "<li><b>මාරු කාලය:</b> වෙනස එක දිනකින් සිදු නොවේ; මාරු දිනයට පෙර සහ පසු මාස 6–12ක් පමණ ක්‍රමයෙන් සිදු වේ. "
        "ඒ කාලයේ ලොකු, ආපසු හැරවිය නොහැකි තීරණ කලබලයෙන් නොගන්න.</li>",
        _CLOSING_C])


def build_c1(d, a, notes, now_local, year, plain=None):
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
    H = [f'''<div class="cover" style="padding-top:12mm">{LOGO_IMG}<div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">වාර්ෂික ඵල වාර්තාව</h1><div class="sub">වර්ෂ ඵල — තාජක ක්‍රමය (C1) · {year}–{year + 1}</div>
      <div class="name">{esc(a.name)}</div>
      <div class="muted">ජන්ම: {esc(a.date)} · {esc(a.time)} · {esc(a.place or "")}</div>
      <div style="margin:14pt auto 0 auto; width:112mm">{south_indian_html_si(labels, f"වර්ෂ කුණ්ඩලිය {year}", 112)}</div>
      <p class="muted" style="margin-top:10pt; font-size:8.5pt">වර්ෂ ප්‍රවේශය {esc(v["varsha_pravesha_local"])} ({esc(a.tz)}) · තාජක ක්‍රමය · ලාහිරි අයනාංශය</p></div>''']
    H.append('<div class="pb"></div>' + (_plain_year_c(d, a, now_local, year) if plain is None else plain)
             + '<h2>1. වර්ෂයේ මූලික ව්‍යුහය</h2>')
    H.append("<table>"
             f"<tr><td style='width:34%'><b>වර්ෂ ප්‍රවේශය</b></td><td>{esc(v['varsha_pravesha_local'])} ({esc(a.tz)}) — රවි ඔබ උපන් මොහොතේ සිටි ස්ථානයටම නැවත එන මොහොත</td></tr>"
             f"<tr><td><b>වර්ෂ ලග්නය</b></td><td>{SIGN_SI[vls]} ({dms(v['lagna_deg'])}) — අවුරුද්දේ කේන්දරයේ ලග්නය</td></tr>"
             f"<tr><td><b>මුන්ථා</b></td><td>{SIGN_SI[inv[v['muntha']]]} — වර්ෂ ලග්නයෙන් {jc.house_from(vls, inv[v['muntha']])} වැන්නේ, "
             f"ජන්ම ලග්නයෙන් {jc.house_from(nls, inv[v['muntha']])} වැන්නේ ({HOUSE_PLAIN_SI[jc.house_from(nls, inv[v['muntha']])]})</td></tr>"
             f"<tr><td><b>වර්ෂේශ (වර්ෂාධිපති)</b></td><td>{PLANET_SI[vsh]} — {PLANET_NATURE_SI[vsh]}</td></tr>"
             f"<tr><td><b>දින/රාත්‍රී කේන්දරය</b></td><td>{'දිවා (වර්ෂ ප්‍රවේශය දහවල්)' if v['day_chart'] else 'රාත්‍රී (වර්ෂ ප්‍රවේශය රාත්‍රියේ)'}</td></tr>"
             "</table>")
    H.append(f'<div class="box">මුන්ථා යනු ජන්ම ලග්නයේ සිට අවුරුද්දකට එක රාශියක් බැගින් ඉදිරියට යන ලක්ෂ්‍යයයි. '
             f'එය ජන්ම කේන්දරයේ {jc.house_from(nls, inv[v["muntha"]])} වැන්නට පැමිණීම මේ වර්ෂයේ '
             f'{HOUSE_PLAIN_SI[jc.house_from(nls, inv[v["muntha"]])]} සම්බන්ධ කාරණා ඉදිරියට එන ප්‍රවණතාවක් පෙන්වයි. '
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
    H.append('<p class="small muted">වගුව කියවන හැටි: <b>වර්ෂ භාවය</b> = අවුරුද්දේ කේන්දරයේ ග්‍රහයා සිටින භාවය (ජීවිත ක්ෂේත්‍රය); '
             '<b>හර්ෂ බල</b> (0–20) සහ <b>පංච වර්ගීය බල</b> (0–20) තාජක ක්‍රමයේ ග්‍රහ ශක්තිය මනින ක්‍රම දෙකකි; ඉහළ අගය = ශක්තිමත්.</p>')

    H.append('<h2 class="sec">2. තාජක යෝග</h2>'
             '<p class="small muted">තාජක යෝග = අවුරුද්දේ කේන්දරයේ ග්‍රහයන් දෙදෙනෙකු අතර සම්බන්ධතා. පේළියක ඇත්තේ ග්‍රහයන් දෙදෙනා, '
             'ඔවුන් අතර දෘෂ්ටිය (2/12, 3/11 වැනි කෝණ සම්බන්ධය) සහ පරතරය (හරියටම ගැලපීමේ සිට අංශක දුර). '
             'පූර්ණ = සම්පූර්ණයෙන් ගැලපී ඇත; වර්තමාන = දැන් ළං වෙමින්.</p>')
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
        srow.append(f"<tr><td>{esc(_SAHAM_PLAIN_C.get(k) or SAHAM_SI.get(k, k))}</td><td>{SIGN_SI[s]} {dms(lon % 30)}</td>"
                    f"<td>{jc.house_from(vls, s)}</td><td>{PLANET_SI[jc.SIGN_LORD[s]]}</td></tr>")
    H.append("<table><tr><th>සහමය</th><th>ස්ථානය</th><th>වර්ෂ භාවය</th><th>අධිපති</th></tr>" + "".join(srow) + "</table>")
    H.append('<p class="small muted">වගුව කියවන හැටි: <b>සහමය</b> = ජීවිතයේ එක් කාරණයක් සඳහා ගණනය කරන ලක්ෂ්‍යයක්; '
             '<b>වර්ෂ භාවය</b> = එය අවුරුද්දේ කේන්දරයේ වැටෙන භාවය; <b>අධිපති</b> = ඒ රාශියේ අධිපති ග්‍රහයා. '
             'සහමයක් ශක්තිමත් ග්‍රහයෙකු සමඟ සම්බන්ධ වන කාලවලදී එම කාරණය ඉදිරියට එන ප්‍රවණතාවක් ඇත.</p>')

    H.append('<h2 class="sec">4. මුද්දා දශා — වර්ෂයේ කාල බෙදීම</h2>')
    mrow = []
    nowl = now_local.strftime("%Y-%m-%d %H:%M")
    for m in v["mudda"]:
        curr = m["start"][:16] <= nowl < m["end"][:16]
        mrow.append(f"<tr{' class=cur' if curr else ''}><td>{PLANET_SI[m['lord']]}</td><td>{esc(m['start'])}</td><td>{esc(m['end'])}</td>"
                    f"<td>{MUDDA_HINT[m['lord']]}</td></tr>")
    H.append("<table><tr><th>දශාධිපති</th><th>ආරම්භය</th><th>අවසානය</th><th>ප්‍රවණතාව</th></tr>" + "".join(mrow) + "</table>")
    H.append('<p class="small muted">මුද්දා දශා = අවුරුද්ද ග්‍රහයන් 9 අතර කෙටි කාල වලට බෙදන ක්‍රමය (අවුරුද්දකට කෙටි කළ විම්ශෝත්තරී දශාව). '
             '<b>දශාධිපති</b> = ඒ කාලය පාලනය කරන ග්‍රහයා; තද කළ පේළිය = දැන් ගත වන කාලය.</p>')
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
    H.append(_gloss_method_c(_GLOSS_YEAR_C, _GLOSS_YEAR_EXTRA_C, "වර්ෂ ඵල (තාජක) ක්‍රමය — P.V.R. Narasimha Rao, ch. 27–31. වර්ෂ කුණ්ඩලිය සෑදෙන්නේ රවි නැවත ජන්ම ස්ථානයට පැමිණෙන මොහොතටයි. "
                              "මේ වාර්තාව ජන්ම කේන්දරයට අතිරේකයකි; ජන්ම කේන්දරය සමඟ එකට කියවිය යුතුයි."))
    return "\n".join(H)


# ================================================================ D1 — Porondam (compatibility)
# ---------------------------------------------------------------- plain words for D1, D2, D3 and N
# The Ashtakoota kootas in everyday words (KOOTA_SI keeps the textbook meaning shown in the tables)
_KOOTA_PLAIN_DN = {"Varna": "මානසික ගැලපීම", "Vashya": "එකිනෙකා කෙරෙහි ආකර්ෂණය", "Tara": "වාසනාව සහ සුවය",
                   "Yoni": "ශාරීරික සමීපත්වය", "Graha Maitri": "අදහස් සහ මිත්‍රත්වය", "Gana": "ස්වභාවය සහ හැසිරීම",
                   "Bhakoot": "පවුලේ සමගිය සහ දියුණුව", "Nadi": "සෞඛ්‍යය සහ දරුවන්"}
_DOSHA_NAME_DN = {"Bhakoot": "භකූට දෝෂය", "Nadi": "නාඩි දෝෂය"}
_DOSHA_MEANING_DN = {
    "Bhakoot": "පවුලේ සමගිය ගැන සැලකිලිමත් වන්නට කියන ඇඟවීමකි",
    "Nadi": "සෞඛ්‍යය සහ දරුවන් ගැන සැලකිලිමත් වන්නට කියන ඇඟවීමකි"}
_CANC_YES_DN = "<b>නිෂ්ප්‍රභ වී ඇත</b> (ග්‍රන්ථවල නියමයක් අනුව බලය නැත)."
_CANC_NO_DN = "නිෂ්ප්‍රභ වීමේ නියමයක් මෙහි නැත; එය තනිවම තීරණය කරන කරුණක් නොවේ."
_KUJA_MEANING_DN = ("කුජ (අඟහරු) ලග්නයෙන්, චන්ද්‍රයාගෙන් හෝ ශුක්‍රයාගෙන් 1, 2, 4, 7, 8 හෝ 12 වැනි තැනක සිටීම. "
                    "බොහෝ කේන්දරවල දක්නට ලැබෙන මෙය, වෙනත් ග්‍රහ ස්ථාන නිසා බොහෝ විට අඩු වේ හෝ නැති වේ; "
                    "දෙදෙනාගේම කේන්දරවල තිබේ නම් එකිනෙක සමබර වන බව සම්ප්‍රදායික මතයයි.")
_DOSHA_INTRO_DN = ('<p class="small">දෝෂයක් යනු සැලකිලිමත් විය යුතු කරුණක් මිස විවාහය නොකළ යුතු බවට සලකුණක් නොවේ; '
                   'බොහෝ ඒවා <b>නිෂ්ප්‍රභ</b> වේ (බලය අඩු වේ හෝ නැති වේ).</p>')
_KUJA_FROM_DN = {"ලග්නය": "ලග්නයෙන්", "චන්ද්‍ර": "චන්ද්‍රයාගෙන්", "ශුක්‍ර": "ශුක්‍රයාගෙන්"}
_CLOSING_DN = ("<li><b>මතක තබා ගන්න:</b> පොරොන්දම් යනු එක් මගපෙන්වීමක් පමණි. විවාහයක සතුට රඳා පවතින්නේ "
               "ඔබ දෙදෙනාගේ අවබෝධය, ගෞරවය සහ සන්නිවේදනය මතයි.</li>")
_PR_READ_DN = ('<p class="small muted">වගුව කියවන හැටි: <b>ඉතා ශුභ, ශුභ, මධ්‍යම</b> = ගැලපේ; <b>අශුභ</b> (පාට කළ පේළි) = '
               'නොගැලපේ — එක් පොරොන්දමක් නොගැලපීමෙන් විවාහය නරක බවක් අදහස් නොවේ; <b>—</b> = ලිතේ නියමයක් නැත. '
               'කුඩා අකුරින් ඇති දෙවන පේළිය එම නියමයම ලග්න දෙකට යෙදූ ප්‍රතිඵලයයි. තේරුම් “වචන කිහිපයක තේරුම” කොටසේ.</p>')
_BIRTH_READ_DN = ('<p class="small muted">වගුව කියවන හැටි: <b>ලග්නය</b> = උපන් මොහොතේ නැගෙනහිරින් උදා වූ රාශිය; '
                  '<b>චන්ද්‍ර රාශිය</b> = උපන් මොහොතේ චන්ද්‍රයා සිටි රාශිය — පොරොන්දම් ගණන් කරන්නේ මෙයින් සහ ජන්ම නැකතෙනි.</p>')

# The glossary: the twenty porondam, the Ashtakoota and the doshas, one short line each (grouped where alike)
_VISI_GLOSS_DN = ("විසි පොරොන්දම", "ශ්‍රී ලාංකික ලිත් අනුව කරුණු 20කින් ගැලපීම බලන ක්‍රමය.")
_PR_GLOSS_DN = [
    _VISI_GLOSS_DN,
    ("නක්ෂත්‍ර, මහේන්ද්‍ර, ස්ත්‍රී දීර්ඝ", "නැකත් අතර ගණන අනුව: එදිනෙදා සතුට; පවුලේ දියුණුව; බිරිඳගේ සුවය."),
    ("ගණ", "ස්වභාවය: දේව (මෘදු), මනුෂ්‍ය (මධ්‍යස්ථ), රාක්ෂස (දැඩි — නරක නොවේ)."),
    ("යෝනි", "නැකතට අයත් සතා අනුව ශාරීරික සමීපත්වය සහ ආකර්ෂණය."),
    ("රාශි, රාශ්‍යාධිපති, වශ්‍ය", "චන්ද්‍ර රාශි අතර දුර, අධිපතීන්ගේ මිත්‍රත්වය සහ එකිනෙකා කෙරෙහි ඇදීම."),
    ("රජ්ජු", "නැකත් කණ්ඩායම් පහ (පාද, ඌරු, නාභි, බාහු, ශිරෝ); එකම එකේ නම් නොගැලපේ."),
    ("වේධ", "එකිනෙකට බාධා කරන ලෙස සලකන නැකත් යුගල; එසේ නොවේ නම් ගැලපේ."),
    ("ආයුෂ", "එකට ගත කරන දිගු ජීවිතය; ලිතේ ක්‍රමයක් නැති නිසා ප්‍රතිඵලයක් නැත."),
    ("වෘක්ෂ, පක්ෂි, භූත, ගෝත්‍ර, වර්ණ, ලිංග", "නැකතට අයත් ගස (කිරි ගසක්ද), පක්ෂියා, පංච භූතය, ඍෂි ගෝත්‍රය, වර්ණය "
     "(කුලය නොවේ) සහ ලිංගය අනුව ගැලපීම."),
    ("නාඩි", "නැකත් කණ්ඩායම් තුන (පූර්ව, මධ්‍ය, අන්ත්‍ය); එකම එකේ නම් නාඩි දෝෂයයි."),
    ("දින", "උපන් සතියේ දින අතර ගණන; එදිනෙදා එකඟතාව."),
    ("ග්‍රහ", "කුජ, ශනි, රාහු ලග්නයෙන්, චන්ද්‍රයාගෙන් හෝ ශුක්‍රයාගෙන් 1, 7, 8 වැන්නේ සිටීම."),
]
_ASHTA_GLOSS_DN = ("අෂ්ටකූට", "චන්ද්‍ර නැකත් අනුව කරුණු 8කින් (කූට) ගැලපීම ලකුණු 36න් මනින ක්‍රමය.")
_DOSHA_GLOSS_DN = [
    ("නිෂ්ප්‍රභ වීම", "දෝෂයක බලය නැති වීම හෝ අඩු වීම; බොහෝ දෝෂවලට එවැනි නියම ඇත."),
    ("භකූට දෝෂය", "චන්ද්‍ර රාශි 2/12, 5/9 හෝ 6/8 වීම; අධිපතීන් එකම හෝ මිත්‍ර නම් නිෂ්ප්‍රභ වේ."),
    ("කුජ (අඟහරු) දෝෂය", "කුජ ලග්නයෙන්, චන්ද්‍රයාගෙන් හෝ ශුක්‍රයාගෙන් 1, 2, 4, 7, 8, 12 වැන්නේ සිටීම; ඉතා සුලබයි."),
]
_NADI_GLOSS_DN = ("නාඩි දෝෂය", "නැකත් දෙක එකම නාඩි කණ්ඩායමේ වීම; එකම රාශියේ වෙනස් නැකත් වැනි අවස්ථාවල නිෂ්ප්‍රභ වේ.")
_SYN_GLOSS_DN = ("සංයෝජනය", "එක් අයෙකුගේ ග්‍රහයන් අනෙකාගේ කේන්දරයේ වැටෙන භාවය: 1, 4, 5, 7, 9, 11 හිතකර; "
                 "6, 8, 12 ඉවසීම ඉල්ලයි.")
_D1_TERMS_DN = ("ලග්නය", "නැකත සහ පාදය")
_D1_GLOSS_DN = _PR_GLOSS_DN + [_ASHTA_GLOSS_DN] + _DOSHA_GLOSS_DN
# D2 explains its UL / DK, marriage planets, kendra / trikona, synastry and Jupiter's transit where they appear
_D2_TERMS_DN = ("ලග්නය", "භාවය", "නැකත සහ පාදය", "මහා දශාව / අන්තර් දශාව", "උච්ච / නීච / ස්වක්ෂේත්‍ර", "නවාංශකය (D9)")
_D2_GLOSS_DN = _D1_GLOSS_DN
_D3_GLOSS_DN = [
    _VISI_GLOSS_DN,
    ("අෂ්ටකූට", _ASHTA_GLOSS_DN[1] + " කූට 8 (වරහන් තුළ උපරිම ලකුණු): වර්ණ (1) — මානසික ගැලපීම; වශ්‍ය (2) — එකිනෙකා කෙරෙහි "
     "ආකර්ෂණය; තාරා (3) — වාසනාව සහ සුවය; යෝනි (4) — ශාරීරික සමීපත්වය; ග්‍රහ මෛත්‍රී (5) — අදහස් සහ මිත්‍රත්වය; "
     "ගණ (6) — ස්වභාවය; භකූට (7) — පවුලේ සමගිය සහ දියුණුව; නාඩි (8) — සෞඛ්‍යය සහ දරුවන්."),
    _DOSHA_GLOSS_DN[0], _DOSHA_GLOSS_DN[1], _NADI_GLOSS_DN, _DOSHA_GLOSS_DN[2],
    ("රජ්ජු / වේධ පොරොන්දම", "රජ්ජු: නැකත් කණ්ඩායම් පහෙන් දෙදෙනාම එකම එකේ නම් නොගැලපේ (සමහර ග්‍රන්ථවල ව්‍යතිරේක ඇත). "
     "වේධ: එකිනෙකට බාධා කරන ලෙස සලකන නැකත් යුගල."),
    _SYN_GLOSS_DN,
]
_N_GLOSS_DN = [
    ("නාම අකුර", "දරුවාගේ නම පටන් ගැනීමට සම්ප්‍රදායිකව සුබ යැයි සලකන අකුර; උපන් මොහොතේ චන්ද්‍රයා සිටි නැකතේ පාදයෙන් තීරණය වේ."),
    ("අවකහඩ චක්‍රය", "නැකත් 27හි පාද 108ට එක් අකුර බැගින් දෙන සම්ප්‍රදායික වගුව."),
    ("චන්ද්‍ර රාශිය", "උපන් මොහොතේ චන්ද්‍රයා සිටි රාශිය."),
    ("මුහූර්තය (නැකත් වේලාව)", "වැදගත් කටයුත්තක් ඇරඹීමට සුබ යැයි සලකන වේලාව; තිථිය, වාරය, නැකත සහ ලග්නය අනුව තෝරයි."),
]


def _gloss_disc_dn(terms, extra, method_line, new_page=True):
    """The glossary (on a new page, or straight on where the last page has room), then the method note on
    the same page (disclaimer_block without its page break)."""
    return (('<div class="pb"></div>' if new_page else '') + '<h2>වචන කිහිපයක තේරුම</h2>' + glossary_html(terms, extra)
            + disclaimer_block(method_line).replace('<div class="pb"></div>', "", 1))


def _box_dn(items):
    return '<div class="box plain"><div class="lbl">සරලව කිවහොත්</div><ul>' + "".join(items) + "</ul></div>"


def _verdict_dn(total):
    """The Ashtakoota total in everyday words (the reports' own 24 / 18 lines)."""
    if total >= 24:
        return "සමස්තයක් ලෙස හොඳ ගැලපීමක්"
    if total >= 18:
        return "මධ්‍යම ගැලපීමක් — හොඳ පැති මෙන්ම සැලකිලිමත් විය යුතු පැතිද ඇත"
    return "ලකුණු අඩු ගැලපීමක් — නමුත් ලකුණු පමණක් බලා තීරණය නොකර, කේන්දර දෙකම සම්පූර්ණයෙන් බලන්න"


def _koota_plain_dn(k):
    return f"{_KOOTA_PLAIN_DN.get(k['name'], k['name'])} ({KOOTA_SI.get(k['name'], (k['name'], ''))[0]})"


_KOOTA_PORONDAM_DN = {"Varna": "varna", "Vashya": "vashya", "Yoni": "yoni", "Gana": "gana", "Nadi": "nadi"}


def _visi_grade_dn(comp, koota):
    """The grade of the twenty-porondam rule with the same name as an Ashtakoota koota (None if none)."""
    key = _KOOTA_PORONDAM_DN.get(koota)
    return next((r["grade"] for r in comp.get("visi_porondam") or [] if r["key"] == key), None)


def _strengths_dn(comp, n=3):
    """Kootas with full points, heaviest first. A dosha that was only cancelled is said with the doshas, and a
    koota whose namesake porondam does not match is left out (the two systems would seem to disagree)."""
    full = [k for k in comp["kootas"] if k["points"] >= k["max"] and "dosha" not in k["detail"].lower()
            and not (_visi_grade_dn(comp, k["name"]) or 0) < 0]
    return [_koota_plain_dn(k) for k in sorted(full, key=lambda k: -k["max"])[:n]]


def _weak_dn(comp, n=2):
    """Kootas with half the points or fewer, weakest first (doshas are said on their own; a koota whose
    namesake porondam matches well is left out)."""
    low = [k for k in comp["kootas"] if k["points"] <= k["max"] / 2 and "dosha" not in k["detail"].lower()
           and not (_visi_grade_dn(comp, k["name"]) or 0) > 0]
    return [_koota_plain_dn(k) for k in sorted(low, key=lambda k: (k["points"] / k["max"], -k["max"]))[:n]]


def _porondam_names_dn(comp, test):
    return [PORONDAM_SI[r["key"]] for r in comp.get("visi_porondam") or [] if r["grade"] is not None and test(r["grade"])]


def _pr_bad_dn(comp, key):
    r = next((r for r in comp.get("visi_porondam") or [] if r["key"] == key), None)
    return bool(r) and r["grade"] is not None and r["grade"] < 0


def _rajju_vedha_li_dn(comp):
    """The rajju and vedha porondam, when they do not match, said kindly (the dosha sections)."""
    out = []
    if _pr_bad_dn(comp, "rajju"):
        out.append("<li><b>රජ්ජු පොරොන්දම</b> — නැකත් දෙක එකම රජ්ජු කණ්ඩායමේ නිසා නොගැලපේ. සම්ප්‍රදායිකව වැදගත් ලෙස "
                   "සලකන නමුත්, සමහර ග්‍රන්ථවල මෙයට ව්‍යතිරේක ඇත.</li>")
    if _pr_bad_dn(comp, "vedha"):
        out.append("<li><b>වේධ පොරොන්දම</b> — නැකත් දෙක එකිනෙකට බාධා කරන (වේධ වන) ලෙස සලකන යුගලයකි; මෙයද තනිවම "
                   "තීරණය කරන කරුණක් නොවේ.</li>")
    return out


def _match_lis_dn(comp, total, good=(), care=(), kuja=()):
    """The points every matching report's box shares: overall, strengths, what needs care, the doshas.
    kuja: short phrases naming a kuja dosha indication (said with the other doshas)."""
    vs = comp.get("visi_summary")
    L = [f"<li><b>සමස්ත ගැලපීම:</b> අෂ්ටකූට ක්‍රමයට (කරුණු 8කින් ගැලපීම මනින ක්‍රමය) ලකුණු 36න් <b>{total:g}</b>ක් "
         f"ලැබේ — {_verdict_dn(total)}."
         + (f" ශ්‍රී ලාංකික විසි පොරොන්දමෙන් <b>{vs['match']}</b>ක් ගැලපේ." if vs else "") + "</li>"]
    gl = []
    st = _strengths_dn(comp)
    if st:
        gl.append(f"{', '.join(st)} යන පැතිවලින් ඔබ දෙදෙනා හොඳින් ගැලපේ")
    vg = _porondam_names_dn(comp, lambda g: g == 2)
    if vg:
        gl.append(f"විසි පොරොන්දමේ {', '.join(vg)} {'පොරොන්දම්' if len(vg) > 1 else 'පොරොන්දම'} ඉතා හොඳින් ගැලපේ")
    gl += list(good)
    if gl:
        L.append("<li><b>ශක්තිමත් පැති:</b> " + "; ".join(gl) + ".</li>")
    cl = []
    wk = _weak_dn(comp)
    if wk:
        cl.append(f"{', '.join(wk)} අතින් ලකුණු අඩුයි")
    nm = _porondam_names_dn(comp, lambda g: g < 0)
    if nm:
        cl.append(f"විසි පොරොන්දමෙන් {len(nm)}ක් ({', '.join(nm)}) නොගැලපේ")
    cl += list(care)
    L.append("<li><b>සැලකිලිමත් විය යුතු තැන්:</b> "
             + ("; ".join(cl) + ". මේවා බිය විය යුතු දේ නොව, අවබෝධයෙන් සහ ඉවසීමෙන් කටයුතු කළ යුතු පැති ලෙස සලකන්න."
                if cl else "විශේෂයෙන් අඩු ලකුණු ලැබුණු කරුණක් නැත.") + "</li>")
    canc, open_ = [], []
    for k in comp["kootas"]:
        if "dosha" in k["detail"].lower():
            (canc if "cancel" in k["detail"].lower() else open_).append(_DOSHA_NAME_DN.get(k["name"], k["name"]))
    if _pr_bad_dn(comp, "rajju"):
        open_.append("රජ්ජු පොරොන්දම නොගැලපීම")
    if _pr_bad_dn(comp, "vedha"):
        open_.append("වේධ නැකත් යුගලය")
    open_ += list(kuja)
    t = []
    if canc:
        t.append(f"{' සහ '.join(canc)} පෙනුණත් {'එය' if len(canc) == 1 else 'ඒවා'} නිෂ්ප්‍රභ වී ඇත (බලය නැත).")
    if open_:
        t.append("සලකා බැලිය යුතු කරුණු: " + ", ".join(open_) + ". " + ("මෙය" if len(open_) == 1 else "මේ කිසිවක්")
                 + " තනිවම තීරණය කරන කරුණක් නොවේ — බොහෝ දෝෂවලට නිෂ්ප්‍රභ වීම් හෝ ව්‍යතිරේක ඇති නිසා, ජ්‍යොතිෂවේදියා "
                 "කේන්දර දෙකම එකට බලා තක්සේරු කරයි. දෝෂයක් යනු සැලකිලිමත් විය යුතු කරුණක් මිස විවාහය නොකළ යුතු බවට සලකුණක් නොවේ.")
    else:
        t.append("භකූට, නාඩි, රජ්ජු, වේධ වැනි ප්‍රධාන දෝෂ කිසිවක් මෙහි ක්‍රියාත්මක නැත.")
    L.append("<li><b>දෝෂ ගැන:</b> " + " ".join(t) + "</li>")
    return L


def _d1_plain_dn(d, a, comp, total):
    kuja = []
    for y in d.get("yoga_indications", []):
        if "Mangal" in y:
            why = si_yoga_why(y)
            kuja.append(f"{esc(a.name)} ගේ කේන්දරයේ කුජ දෝෂ ඇඟවීම ({why + ', ' if why else ''}ඉතා සුලබ ඇඟවීමකි)")
    return _box_dn(_match_lis_dn(comp, total, kuja=kuja) + [_CLOSING_DN])


def _d2_plain_dn(comp, total, kuja_hits, good, bad, overlap, tz):
    """kuja_hits: [(name, hits, cancellations)] for both; good/bad: the synastry tally; overlap: shared windows."""
    eg, ec = [], []
    if good > bad + 2:
        eg.append("ග්‍රහ ස්ථාන අනුවද (කේන්දර දෙකේ සංයෝජනය) ඔබ දෙදෙනා එකිනෙකාට සහාය වන පැත්තට බර වැඩියි")
    elif bad > good:
        ec.append("ග්‍රහ ස්ථාන අනුව (කේන්දර දෙකේ සංයෝජනය) ඝර්ෂණ ඇති විය හැකි තැන් වැඩියි — සන්නිවේදනය සහ ඉවසීම වැදගත්")
    else:
        ec.append("ග්‍රහ ස්ථාන අනුව (කේන්දර දෙකේ සංයෝජනය) ශක්තිමත් පැති මෙන්ම ඝර්ෂණ ඇති විය හැකි තැන්ද ඇත")
    if all(h for _, h, _ in kuja_hits):
        kj = ["දෙදෙනාගේම කේන්දරවල කුජ දෝෂ ඇඟවීම් (දෙදෙනාටම ඇති නිසා සම්ප්‍රදාය අනුව එකිනෙක සමබර වේ)"]
    else:
        kj = [f"{esc(n)} ගේ කේන්දරයේ කුජ දෝෂ ඇඟවීම (ඉතා සුලබ ඇඟවීමකි" + ("; අඩු කරන සාධකද ඇත)" if c else ")")
              for n, h, c in kuja_hits if h]
    L = _match_lis_dn(comp, total, eg, ec, kj)
    ym = lambda x: x.astimezone(ZoneInfo(tz)).strftime("%Y-%m")  # noqa: E731
    if overlap:
        first = f"{ym(overlap[0][0])} සිට {ym(overlap[0][1])} දක්වා"
        L.append("<li><b>විවාහ කාලය:</b> ඉදිරි වසර 6 තුළ දෙදෙනාගේම විවාහය පෙන්වන ග්‍රහ කාල (දශා) එකවර ක්‍රියාත්මක වන "
                 + (f"කාලයක් ඇත: {first}.</li>" if len(overlap) == 1
                    else f"කාල {len(overlap)}ක් ඇත; පළමුවැන්න {first}.</li>"))
    else:
        L.append("<li><b>විවාහ කාලය:</b> ඉදිරි වසර 6 තුළ දෙදෙනාගේම විවාහය පෙන්වන ග්‍රහ කාල (දශා) එකවර එන පැහැදිලි කාලයක් "
                 "නැත. එයින් බාධාවක් අදහස් නොවේ — ජ්‍යොතිෂවේදියා ගුරු ග්‍රහයාගේ ගමන (ගෝචරය) සමඟ සුදුසු කාලය බලයි.</li>")
    return _box_dn(L + [_CLOSING_DN])


def _verdict_short_dn(total):
    return "හොඳ ගැලපීමක්" if total >= 24 else "මධ්‍යම ගැලපීමක්" if total >= 18 else "ලකුණු අඩු ගැලපීමක්"


def _d3_plain_dn(rows):
    """One line per proposal: how well it matches, its strengths, what needs care; best score first."""
    L = [f"<li><b>යෝජනා {len(rows)}ක් සංසන්දනය කර ඇත.</b> අෂ්ටකූට ලකුණු (චන්ද්‍ර නැකත් අනුව කරුණු 8කින් ගැලපීම මනින "
         f"ක්‍රමය, 36න්) අනුව ඉහළින්ම සිටින්නේ <b>{esc(rows[0]['name'])}</b>. නමුත් ලකුණු පමණක් නොව, එක් එක් යෝජනාවේ "
         "සැලකිලිමත් විය යුතු කරුණුද බලන්න.</li>"]
    for r in rows:
        comp = r["comp"]
        st = _strengths_dn(comp, 2)
        care = [_DOSHA_NAME_DN.get(x, x) + " (නිෂ්ප්‍රභ නැත)" for x in r["doshas"]]
        if _pr_bad_dn(comp, "rajju"):
            care.append("රජ්ජු පොරොන්දම නොගැලපීම")
        if _pr_bad_dn(comp, "vedha"):
            care.append("වේධ නැකත් යුගලයක් වීම")
        if r["mangal"]:
            care.append("කුජ දෝෂ ඇඟවීම" + (" (අඩු කරන සාධක ඇත)" if r["mangal_c"] else ""))
        if r["bad"] > r["good"]:
            care.append("ග්‍රහ ස්ථාන අතර ඝර්ෂණ වැඩි වීම")
        care += [w + " අතින් අඩු ලකුණු" for w in _weak_dn(comp, 1)]
        L.append(f"<li><b>{esc(r['name'])}</b> — {_verdict_short_dn(r['total'])}: අෂ්ටකූට {r['total']:g}/36"
                 + (f", විසි පොරොන්දම {r['visi']}/20" if r["visi"] is not None else "") + ". "
                 + (f"ශක්තිමත් පැති: {', '.join(st)}. " if st else "")
                 + f"සැලකිලිමත් විය යුතු: {', '.join(care) if care else 'විශේෂ කරුණක් නැත'}.</li>")
    if len(rows) <= 4:
        L.append("<li><b>මතක තබා ගන්න:</b> දෝෂයක් යනු සැලකිලිමත් විය යුතු කරුණක් පමණි; බොහෝ දෝෂ නිෂ්ප්‍රභ වේ හෝ අඩු වේ. "
                 "අවසන් තීරණය දෙදෙනාගේ අවබෝධය සහ පවුල්වල එකඟතාව මතයි.</li>")
    return _box_dn(L)


def _n_plain_dn(nm, nak_si):
    return _box_dn([
        f"<li><b>නමට සුදුසු අකුර:</b> සම්ප්‍රදාය අනුව දරුවාගේ නම <b>{esc(nm['sinhala'])}</b> අකුරින් (ශබ්දයෙන්) පටන් ගැනීම සුබයි.</li>",
        f"<li><b>මේ අකුර ලැබුණේ ඇයි:</b> දරුවා උපන් මොහොතේ චන්ද්‍රයා සිටියේ <b>{nak_si}</b> නැකතේ (තාරකා කොටසේ) "
        f"{nm['pada']} වන පාදයේ. සෑම නැකතක්ම පාද (කොටස්) හතරකට බෙදී ඇති අතර, එක් පාදයකට එක් අකුර බැගින් ලැබේ.</li>",
        "<li><b>නම තෝරන හැටි:</b> මේ අකුරින් පටන් ගන්නා, හොඳ අර්ථයක් ඇති, කීමට පහසු නමක් තෝරන්න. "
        "මෙය සම්ප්‍රදායික යෝජනාවක් පමණි; පවුලේ කැමැත්තද වැදගත්.</li>"])


def build_d1(d, a, notes, now_local):
    comp = d["compatibility"]
    if not comp:
        sys.exit("compatibility data missing — check --match-* arguments")
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    pt = comp["partner"]
    inv = {s: i for i, s in enumerate(jc.SIGNS)}
    total = comp["ashtakoota_total"]
    verdict = ("හොඳ ගැලපීමක්" if total >= 24 else "මධ්‍යම ගැලපීමක්" if total >= 18 else "අඩු ලකුණු ගැලපීමක්")
    visi_line = (f'<br><span style="font-size:12.5pt">විසි පොරොන්දම: <b>{comp["visi_summary"]["match"]} / 20</b></span>'
                 if comp.get("visi_summary") else "")
    labels = {ls: ["ලග්න"]}
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        labels.setdefault(P[c]["sign_idx"], []).append(PLANET_SI[c])
    H = [f'''<div class="cover" style="padding-top:12mm">{LOGO_IMG}<div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">පොරොන්දම් වාර්තාව</h1><div class="sub">අෂ්ටකූට ගැලපීම (D1)</div>
      <div class="name">{esc(a.name)} &nbsp;·&nbsp; {esc(a.match_name or "සහකරු")}</div>
      <div style="margin:16pt auto; font-size:15pt"><b>{total} / 36</b> — {verdict}{visi_line}</div>
      <div style="width:104mm; margin:0 auto">{south_indian_html_si(labels, "රාශි චක්‍රය (පළමු කේන්දරය)", 104)}</div></div>''']
    first, second = ("මනාලයා", "මනාලිය") if getattr(a, "role", "boy") == "boy" else ("මනාලිය", "මනාලයා")
    H.append('<div class="pb"></div>' + _d1_plain_dn(d, a, comp, total) + '<h2>1. උපන් දත්ත</h2><table>'
             f'<tr><th></th><th>පළමු අය ({first})</th><th>දෙවන අය ({second})</th></tr>'
             f'<tr><td><b>නම</b></td><td>{esc(a.name)}</td><td>{esc(a.match_name or "—")}</td></tr>'
             f'<tr><td><b>උපන් දිනය</b></td><td>{esc(a.date)}</td><td>{esc(pt["date"])}</td></tr>'
             f'<tr><td><b>වේලාව</b></td><td>{esc(a.time)}</td><td>{esc(pt["time"])}</td></tr>'
             f'<tr><td><b>ලග්නය</b></td><td>{SIGN_SI[ls]}</td><td>{SIGN_SI[inv[pt["lagna"]]]}</td></tr>'
             f'<tr><td><b>චන්ද්‍ර රාශිය</b></td><td>{SIGN_SI[P["Mo"]["sign_idx"]]}</td><td>{SIGN_SI[inv[pt["moon"]]]}</td></tr>'
             "</table>" + _BIRTH_READ_DN)
    H.append(porondam_block(comp, title="2. විසි පොරොන්දම (ශ්‍රී ලාංකික ක්‍රමය)")
             + (_PR_READ_DN if comp.get("visi_porondam") else ""))
    H.append('<div class="pb"></div><h2>3. අෂ්ටකූට ලකුණු</h2>')
    krow = []
    for k in comp["kootas"]:
        si, meaning = KOOTA_SI.get(k["name"], (k["name"], ""))
        det = si_koota(k["detail"])
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
            # just the signs or nadis here: the cancellation is said in Sinhala right after
            dosha.append(f"<li><b>{nm}</b> — {esc(si_koota(k['detail'].split(' — ')[0]))}"
                         + (f". {_CANC_YES_DN}" if canc else f": {_DOSHA_MEANING_DN[k['name']]}. {_CANC_NO_DN}") + "</li>")
    dosha += _rajju_vedha_li_dn(comp)
    mangal = [y for y in d.get("yoga_indications", []) if "Mangal" in y]
    if mangal:
        why = si_yoga_why(mangal[0])
        dosha.append(f"<li><b>කුජ දෝෂ ඇඟවීම</b> (පළමු කේන්දරයේ{', ' + why if why else ''}) — ඉතා සුලබ, බොහෝ විට "
                     "වෙනත් ග්‍රහ ස්ථාන නිසා අඩු වන ඇඟවීමකි; දෙදෙනාගේම කේන්දරවල ඇත්නම් එකිනෙක සමබර වේ.</li>")
    H.append("<h2>4. දෝෂ සහ නිෂ්ප්‍රභ වීම්</h2>" + _DOSHA_INTRO_DN + "<ul>"
             + ("".join(dosha) if dosha else "<li>ප්‍රධාන දෝෂ ඇඟවීම් නොමැත.</li>") + "</ul>")
    H.append(note_block(notes, "dosha") or note_block(notes, "yogas"))
    # its own page only when the astrologer wrote something for it
    H.append(('<div class="pb"></div>' if (notes or {}).get("summary") else '') + '<h2>5. ජ්‍යොතිෂවේදියාගේ විග්‍රහය</h2>')
    H.append(note_block(notes, "summary") or '<p class="muted">(සවිස්තර විග්‍රහය සඳහා සම්පූර්ණ පොරොන්දම් වාර්තාව — D2 — බලන්න.)</p>')
    H.append(note_block(notes, "upcoming", "විවාහ කාලය සහ ඉදිරි කාලය"))
    H.append(_gloss_disc_dn(_D1_TERMS_DN, _D1_GLOSS_DN, new_page=False, method_line="අෂ්ටකූට ගුණ මිලන ක්‍රමය සහ දෝෂ නිෂ්ප්‍රභ වීමේ නියම — P.V.R. Narasimha Rao, ch. 26. "
                              "මේ වාර්තාව ගැලපීම පිළිබඳ එක් දෘෂ්ටි කෝණයක් පමණි. විවාහය පිළිබඳ තීරණය දෙදෙනාගේ අවබෝධය, "
                              "සන්නිවේදනය සහ පවුල්වල එකඟතාව මත පදනම් විය යුතුයි — ලකුණු එකතුවක් මත නොවේ."))
    return "\n".join(H)


# ---------------------------------------------------------------- visi porondam (D1, D2, D3)
PORONDAM_SI = {"nakshatra": "නක්ෂත්‍ර", "gana": "ගණ", "mahendra": "මහේන්ද්‍ර", "stree_deergha": "ස්ත්‍රී දීර්ඝ",
               "yoni": "යෝනි", "rashi": "රාශි", "rashyadhipati": "රාශ්‍යාධිපති", "vashya": "වශ්‍ය", "rajju": "රජ්ජු",
               "vedha": "වේධ", "vriksha": "වෘක්ෂ", "ayushya": "ආයුෂ", "pakshi": "පක්ෂි", "bhuta": "භූත",
               "gotra": "ගෝත්‍ර", "varna": "වර්ණ", "linga": "ලිංග", "nadi": "නාඩි", "dina": "දින", "graha": "ග්‍රහ"}
GRADE_SI = {2: "ඉතා ශුභ", 1: "ශුභ", 0: "මධ්‍යම", -1: "අශුභ", -2: "ඉතා අශුභ", None: "—"}
PR_YONI_SI = {"horse": "අශ්ව", "elephant": "ඇත්", "sheep": "එළු", "serpent": "සර්ප", "dog": "සුනඛ", "cat": "බළල්",
              "rat": "මූසික", "cow": "ගව", "buffalo": "මී ගව", "tiger": "ව්‍යාඝ්‍ර", "deer": "මුව", "monkey": "වඳුරු",
              "mongoose": "මුගටි", "lion": "සිංහ"}    # the litha's names (YONI_SI is the Ashtakoota set)
PR_LABELS_SI = {
    "rajju": ["පාද", "ඌරු", "නාභි", "බාහු", "ශිරෝ"],
    "pakshi": {"Herunda": "හේරුණ්ඩ", "Pingala": "පිංගල", "Kaka": "කාක", "Kukkuta": "කුක්කුට", "Mayura": "මයුර"},
    "bhuta": {"Pathavi": "පඨවි", "Apo": "ආපෝ", "Tejo": "තේජෝ", "Vayo": "වායෝ", "Akasha": "ආකාශ"},
    "gotra": {"Marichi": "මරීචි", "Atri": "අත්‍රි", "Vasishta": "වශිෂ්ට", "Angira": "අංගිර", "Pulastya": "පුලස්ති",
              "Pulaha": "පුලහ", "Kratu": "කෘතු"},
    "varna": {"Brahmana": "බ්‍රාහ්මණ", "Kshatriya": "ක්ෂත්‍රිය", "Vaishya": "වෛශ්‍ය", "Shudra": "ශුද්‍ර",
              "Panchama": "පංචම", "Sankara": "සංකර"},
    "linga": {"M": "පුරුෂ", "F": "ස්ත්‍රී", "N": "නපුංසක"},
    "nadi": {"Adi": "පූර්ව", "Madhya": "මධ්‍ය", "Antya": "අන්ත්‍ය"},
}


def _porondam_detail(r):
    """Sinhala 'bride → groom' detail for one porondam row from the engine."""
    k, b, g, c = r["key"], r["bride"], r["groom"], r["count"]
    nak = lambda n: NAK_SI[jc.NAKSHATRAS.index(n)]  # noqa: E731
    sign = lambda s: SIGN_SI[jc.SIGNS.index(s)]  # noqa: E731
    arrow = lambda x, y: f"{x} → {y}"  # noqa: E731
    if k == "nakshatra":
        return f"{arrow(nak(b), nak(g))} ({c} වැනි නැකත)"
    if k in ("mahendra", "stree_deergha"):
        return f"මනාලියගේ නැකතේ සිට {c} වැනි නැකත"
    if k == "gana":
        return arrow(GANA_SI[b], GANA_SI[g])
    if k == "yoni":
        def y(v):
            animal, sex = v.split(" ")
            return f"{PR_YONI_SI[animal]} ({'පුරුෂ' if sex == '(m)' else 'ස්ත්‍රී'})"
        return arrow(y(b), y(g))
    if k == "rashi":
        return f"{arrow(sign(b), sign(g))} ({c} වැනි රාශිය)"
    if k == "vashya":
        return arrow(sign(b), sign(g))
    if k == "rashyadhipati":
        return arrow(PLANET_SI[b], PLANET_SI[g]) + ("" if r["grade"] is not None else " — සම සම්බන්ධතාව; ලිතේ නියමයක් නැත")
    if k == "vedha":
        return "වේධ වන නැකත් දෙකකි" if r["grade"] == -1 else "වේධ නොවේ"
    if k == "vriksha":
        milk = lambda v: "කිරි වෘක්ෂ" if v else "කිරි නැති වෘක්ෂ"  # noqa: E731
        return arrow(milk(b), milk(g)) + ("" if r["grade"] is not None else " — ලිතේ නියමයක් නැත")
    if k == "ayushya":
        return "ගණනය කිරීමේ ක්‍රමය ලිතේ දක්වා නැත"
    if k == "dina":
        return f"{arrow(VARA_SI2[b], VARA_SI2[g])} ({c} වැනි දිනය)"
    if k == "graha":
        def g_(v):
            return f"{len(v)} ලක්ෂණ" if v else "නැත"
        return f"මනාලිය: {g_(b)} · මනාලයා: {g_(g)}" + ("" if r["grade"] is not None else " — ලිතේ නියමයක් නැත")
    if k in PR_LABELS_SI:
        lab = PR_LABELS_SI[k]
        return arrow(lab[b], lab[g]) + ("" if r["grade"] is not None else " — ලිතේ නියමයක් නැත")
    return ""


def porondam_block(comp, heading="h2", title="විසි පොරොන්දම (ශ්‍රී ලාංකික ක්‍රමය)"):
    """The twenty porondam table with its tally. Empty if the engine gave none."""
    rows = comp.get("visi_porondam")
    if not rows:
        return ""
    s = comp["visi_summary"]

    def lagna_line(r):
        """Second line for rashi, rashyadhipati, vashya: the same rule on the two Lagnas."""
        lg = r.get("lagna")
        if not lg:
            return ""
        grade = GRADE_SI[lg["grade"]] if lg["grade"] is not None else "ලිතේ නියමයක් නැත"
        detail = _porondam_detail({**lg, "key": r["key"], "grade": lg["grade"] if lg["grade"] is not None else 0})
        return f"<br><span class='muted'>ලග්න අනුව: {esc(detail)} — <b>{grade}</b></span>"

    body = "".join(
        f"<tr{' class=cur' if r['grade'] is not None and r['grade'] < 0 else ''}><td>{r['no']}</td>"
        f"<td>{PORONDAM_SI[r['key']]}</td><td><b>{GRADE_SI[r['grade']]}</b></td>"
        f"<td>{esc(_porondam_detail(r))}{lagna_line(r)}</td></tr>"
        for r in rows)
    return (f"<{heading}>{title}</{heading}>"
            f"<div class='box'><b>පොරොන්දම් 20න් {s['match']}ක් ගැලපේ</b> (ශුභ හෝ මධ්‍යම) · {s['no_match']}ක් නොගැලපේ"
            + (f" · {s['no_rule']}ක් සඳහා ලිතේ නියමයක් නැත" if s["no_rule"] else "") + ". "
            "සාමාන්‍යයෙන් 50%ට වැඩි ගැලපීමක් පොරොන්දම් ගැලපීමක් ලෙස සලකයි.</div>"
            "<table><tr><th></th><th>පොරොන්දම</th><th>ප්‍රතිඵලය</th><th>විස්තරය (මනාලිය → මනාලයා)</th></tr>"
            + body + "</table>"
            "<p class='small muted'>නැකත්, රාශි සහ දින ගණන් කරන්නේ මනාලියගේ නැකතේ (රාශියේ, දිනයේ) සිට මනාලයාගේ දක්වාය. "
            "රාශි, රාශ්‍යාධිපති සහ වශ්‍ය පොරොන්දම් ලිතේ නියමය අනුව චන්ද්‍ර රාශි දෙකෙන් තීරණය වන අතර එකතුවට ගැනෙන්නේ එයයි; "
            "සමහර ජ්‍යොතිෂවේදීන් ලග්න දෙකද සලකන බැවින් එම නියමයම ලග්න දෙකට යෙදූ ප්‍රතිඵලයද දක්වා ඇත. "
            "යෝනි, ලිංග සහ ග්‍රහ පොරොන්දම් විශේෂයෙන් වැදගත් වන අතර අවසන් තීරණය ග්‍රහ පොරොන්දම අනුව ගත යුතු බව ලිත සඳහන් කරයි; "
            "ග්‍රහ පොරොන්දමේ ග්‍රහයන්ගේ බලය ජ්‍යොතිෂවේදියා විසින් සලකා බැලිය යුතුය. "
            "මූලාශ්‍රය: ලංකා පංචාංග සහ ඈපා පංචාංග ග්‍රහස්ඵුට ලිතවල නියම.</p>")


# ================================================================ P1 — Prashna
# ---------------------------------------------------------------- plain words for P1/P2, M1 and E1
# The "සරලව කිවහොත්" boxes say what each report found, in everyday Sinhala; the glossaries explain the
# words the reports use. The boxes only restate the signs the reports already weigh (p1_auto_summary's
# ithasala / eesarpha and Shatpanchasika tones, the muhurta scores, the rectification scores).
GLOSS_P1_SHARED_PME = ("රාශිය", "භාවය", "ලග්නාධිපති", "වක්‍ර (ව)", "නවාංශකය (D9)")
GLOSS_P1_PME = [
    ("ප්‍රශ්න කේන්දරය", "ප්‍රශ්නය අසන මොහොතට සාදන කේන්දරය. උපන් වේලාවක් අවශ්‍ය නැත."),
    ("ප්‍රශ්න ලග්නය", "ප්‍රශ්නය ඇසූ මොහොතේ නැගෙනහිරින් උදා වෙමින් තිබූ රාශිය; එය ප්‍රශ්නකරු (ඔබ) නියෝජනය කරයි."),
    ("කේන්ද්‍ර / ත්‍රිකෝණ / දුස්ථාන", "කේන්දරයේ කොටු වර්ග: කේන්ද්‍ර (1, 4, 7, 10) සහ ත්‍රිකෝණ (1, 5, 9) ශක්තිමත් තැන්; "
     "දුස්ථාන (6, 8, 12) අපහසු තැන්."),
    ("ශුභ / පාප ග්‍රහයන්", "සාමාන්‍යයෙන් හිතකර ග්‍රහයන් (ගුරු, ශුක්‍ර, බුධ, චන්ද්‍ර) සහ අභියෝග ගෙන එන ග්‍රහයන් "
     "(ශනි, කුජ, රවි, රාහු, කේතු)."),
    ("තාජක", "ග්‍රහයන් එකිනෙකා දකින කෝණ (දෘෂ්ටි) සහ අංශක මත පදනම් වූ ක්‍රමය; ප්‍රශ්න සහ වර්ෂ ඵල සඳහා භාවිත වේ."),
    ("ඉථසාල / ඊසර්ඵ", "ඉථසාල: ග්‍රහයන් දෙදෙනෙකු එකිනෙකා වෙත ළං වීම — කාරණය ඉටුවීමේ ලකුණ. "
     "ඊසර්ඵ: ඔවුන් ඈත් වීම — ලිස්සා යාමේ හෝ ප්‍රමාදයේ ලකුණ."),
    ("දෘෂ්ටිය / පරතරය", "දෘෂ්ටිය: ග්‍රහයන් එකිනෙකා දකින කෝණය (ත්‍රිකෝණ, චතුරස්‍ර ආදී). පරතරය: ඔවුන්ගේ අංශක අතර වෙනස."),
    ("හර්ෂ බල / පංච වර්ගීය බල", "ග්‍රහයෙකුගේ ශක්තිය 0–20 පරිමාණයෙන් මනින තාජක ක්‍රම දෙකක්."),
    ("සහමය", "කාරණයකට (විවාහය, වාසනාව ආදී) අදාළව ග්‍රහ හෝ ලග්න ස්ථාන තුනකින් ගණනය කරන සංවේදී ලක්ෂ්‍යයක්."),
    ("කාරකයා", "යම් කාරණයක් ස්වභාවයෙන්ම පෙන්වන ග්‍රහයා (උදා: විවාහයට ශුක්‍ර)."),
    ("ෂට්පංචාශිකා", "ප්‍රිථුයශස් රචිත, ප්‍රශ්න ජ්‍යොතිෂය ගැන ශ්ලෝක 56කින් යුත් පැරණි ග්‍රන්ථය."),
    ("හෝරාධිපති", "ප්‍රශ්නය ඇසූ පැයට අධිපති ග්‍රහයා."),
    ("තිථිය / කරණය", "තිථිය: චන්ද්‍ර දිනය (පුර හෝ අව පක්ෂයේ දින). කරණය: තිථියෙන් භාගයක්."),
]
GLOSS_M1_SHARED_PME = ("රාශිය", "භාවය", "වක්‍ර (ව)")
GLOSS_M1_PME = [
    ("මුහූර්තය (නැකත)", "වැදගත් කටයුත්තක් ආරම්භ කිරීමට තෝරා ගන්නා සුබ මොහොත."),
    ("සුබ කවුළුව", "මූලික නියම සියල්ල සපුරන අඛණ්ඩ කාලයක්; කටයුත්ත ඒ තුළ ඕනෑම මොහොතක ආරම්භ කළ හැක."),
    ("ලකුණු", "මූලික නියමවලට අමතර හොඳ ලක්ෂණ සඳහා එකතු වී, අඩුපාඩු සඳහා අඩු වන අගය; වැඩි තරමට වඩාත් සුබයි."),
    ("ලග්නය", "යම් මොහොතක නැගෙනහිරින් උදා වෙමින් තිබෙන රාශිය; පැය දෙකකට පමණ වරක් මාරු වේ."),
    ("තිථිය", "චන්ද්‍ර දිනය — පුර පක්ෂයේ සහ අව පක්ෂයේ දින 15 බැගින්."),
    ("වාරය", "සතියේ දවස (ඉරිදා, සඳුදා ආදී)."),
    ("නැකත (නක්ෂත්‍රය)", "චන්ද්‍රයා ගමන් කරන තාරකා කොටස — 27න් එකක්; දිනකට පමණ වරක් මාරු වේ."),
    ("තාරා බලය", "එදින නැකත ඔබේ උපන් නැකතේ සිට ගණන් කළ විට ලැබෙන තත්ත්වය (සම්පත්, ක්ෂේම, මිත්‍ර ආදී); "
     "හිතකර තාරාවක් ලකුණු වැඩි කරයි."),
    ("හෝරාව / හෝරාධිපති", "දවසේ සෑම පැයක්ම එක් ග්‍රහයෙකුට අයත් වේ; ඒ පැයට අධිපති ග්‍රහයා හෝරාධිපතියි."),
    ("කරණය", "තිථියෙන් භාගයක්; සමහර කරණ (උදා: විෂ්ටි) ආරම්භයන්ට නුසුදුසු ලෙස සැලකේ."),
    ("D-9, D-10 ආදී කේන්දර", "රාශි කුඩා කොටස් වලට බෙදා සාදන සියුම් කේන්දර; කාර්යයට අදාළ එක (විවාහයට D-9, රැකියාවට D-10) බලා ඇත."),
    ("ලිත් නැකත", "ලංකාවේ පාරම්පරික නැකත් ක්‍රමය (රාහු කාලය, සුබ දිශාව ආදිය සහිතව)."),
]
GLOSS_E1_SHARED_PME = ("ලග්නය", "රාශිය", "භාවය", "මහා දශාව / අන්තර් දශාව", "නවාංශකය (D9)")
GLOSS_E1_PME = [
    ("ජන්ම කාල ශුද්ධිය", "ජීවිතයේ සිදු වූ සිදුවීම් භාවිත කර උපන් වේලාව නිවැරදි කිරීම."),
    ("දශාංශකය (D10)", "රාශිය කොටස් 10කට බෙදා සාදන කේන්දරය; රැකියාව බැලීමට භාවිත වේ. එහි ලග්නය මිනිත්තු කිහිපයකින් වෙනස් වේ."),
    ("MD / AD / PD", "මහා දශාව / අන්තර් දශාව / ප්‍රත්‍යන්තර දශාව — සිදුවීම් දිනයේ ක්‍රියාත්මක වූ ඒවා."),
    ("දශාධිපති", "යම් දශා කාලයක් පාලනය කරන ග්‍රහයා."),
    ("කාරක ග්‍රහයා", "සිදුවීමක් ස්වභාවයෙන්ම පෙන්වන ග්‍රහයා — උදා: විවාහයට ශුක්‍ර, දරුවන්ට ගුරු."),
    ("ගැලපීම් ලකුණු", "සිදුවීම් දිනවල ක්‍රියාත්මක දශාධිපතීන් එම සිදුවීමේ භාවවලට සම්බන්ධ වන ගණන "
     "(අන්තර් දශාවට 2, අනෙක් දෙකට 1)."),
    ("කාල කවුළුව", "ඉහළම ලකුණු ලැබෙන අඛණ්ඩ වේලා පරාසය."),
]
_M1_TARA_PME = {"Janma": "ජන්ම", "Sampat": "සම්පත්", "Kshema": "ක්ෂේම", "Sadhana": "සාධන", "Mitra": "මිත්‍ර",
                "Parama": "පරම මිත්‍ර"}


def plain_box_pme(items):
    """The simple-words box (same HTML as plain_summary_si)."""
    return ('<div class="box plain"><div class="lbl">සරලව කිවහොත්</div><ul>'
            + "".join(f"<li>{x}</li>" for x in items) + "</ul></div>")


def disc_nopb_pme(method_line):
    """disclaimer_block without its page break: the glossary opens that page and the method note follows it."""
    return disclaimer_block(method_line).replace('<div class="pb"></div>', "", 1)


def plain_p1_pme(d, a, matter, shat_topic, notes):
    """P1/P2 in simple words: the answer from the same signs p1_auto_summary weighs (the matter's
    significators in ithasala or eesarpha, the count of Tajaka yogas, the Shatpanchasika tones)."""
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    lh = P[jc.SIGN_LORD[ls]]["house"]
    ty = d.get("tajaka_yogas", {})
    ith, ees = len(ty.get("ithasala", [])), len(ty.get("eesarpha", []))
    lean = ("කාරණය ඉටුවීම පෙන්වන ලකුණු වැඩියි" if ith > ees else "ප්‍රමාද හෝ බාධා පෙන්වන ලකුණු වැඩියි" if ees > ith
            else "දෙපැත්තම සමානයි")
    q = str(getattr(a, "question", "") or "").strip()
    L = [(f"<b>ඔබේ ප්‍රශ්නය:</b> “{esc(q)}” — " if q else "")
         + "පිළිතුර කියවන්නේ ඔබ ප්‍රශ්නය ඇසූ මොහොතේ ග්‍රහ පිහිටීමෙනි"
         + (f", විශේෂයෙන් {matter} වන භාවයෙන් ({HOUSE_PLAIN_SI[matter]})" if matter else "") + "."]
    slip = False
    if matter:
        ml = " ".join(d.get("matter_lines", []))
        if "ITHASALA" in ml:
            ans = ("<b>කෙටි පිළිතුර: හිතකරයි.</b> ප්‍රශ්නයට අදාළ ග්‍රහයන් එකිනෙකා වෙත ළං වෙමින් සිටී (ඉථසාල යෝගය) — "
                   "කාරණය ඉටුවීමට නැඹුරු හොඳ ලකුණකි.")
        elif "EESARPHA" in ml:
            slip = True
            ans = ("<b>කෙටි පිළිතුර: ප්‍රමාද විය හැක.</b> ප්‍රශ්නයට අදාළ ග්‍රහයන් එකිනෙකාගෙන් ඈත් වෙමින් සිටී (ඊසර්ඵ යෝගය) — "
                   "කාරණය ප්‍රමාද වීමට හෝ අතින් ගිලිහී යාමට ඉඩ ඇත; අමතර උත්සාහයක් අවශ්‍ය විය හැක.")
        else:
            ans = ("<b>කෙටි පිළිතුර: පැහැදිලි “ඔව්” හෝ “නැහැ” නැත.</b> ප්‍රශ්නයට අදාළ ප්‍රධාන ග්‍රහයන් අතර ළං වීමක් නැති නිසා "
                   "මේ ක්‍රමයෙන් ශක්තිමත් පිළිතුරක් නොලැබේ; අනෙක් ලකුණු පහතින්.")
    else:
        ans = f"<b>කෙටි පිළිතුර:</b> කේන්දරයේ ළං වීම් (ඉථසාල) {ith}ක් සහ ඈත් වීම් (ඊසර්ඵ) {ees}ක් ඇත — {lean}."
    if lh in (1, 4, 5, 7, 9, 10):
        ans += " ඔබව නියෝජනය කරන ග්‍රහයා (ප්‍රශ්න ලග්නයේ අධිපති) ශක්තිමත් තැනක සිටින නිසා, කාරණය ඉදිරියට ගෙන යාමට ඔබට ශක්තිය ඇත."
    L.append(ans)
    other, neg = [], 0
    if matter:
        other.append(f"මුළු කේන්දරයේම ළං වීම් (ඉථසාල) {ith}ක් සහ ඈත් වීම් (ඊසර්ඵ) {ees}ක් ඇත — {lean}.")
    sh = d.get("shatpanchasika") or []
    if sh:
        tones = [si_shat_verdict(r["verdict"])[1] for r in sh]
        pos, neg = tones.count(1), tones.count(-1)
        other.append(f"පැරණි ෂට්පංචාශිකා ග්‍රන්ථයේ නියම අනුව හිතකර ලකුණු {pos}ක් සහ සැලකිලිමත් විය යුතු ලකුණු {neg}ක් ඇත — "
                     + ("සමස්තයක් ලෙස හිතකර පැත්තට බර වැඩියි." if pos > neg
                        else "සමස්තයක් ලෙස සැලකිලිමත් විය යුතු පැත්තට බර වැඩියි." if neg > pos else "ලකුණු මිශ්‍රයි."))
    if other:
        L.append("<b>අනෙක් ලකුණු:</b> " + " ".join(other))
    watch = []
    if lh in (6, 8, 12):
        watch.append("ඔබව නියෝජනය කරන ග්‍රහයා අපහසු තැනක සිටින නිසා ඔබේ පැත්තෙන් වැඩි උත්සාහයක් අවශ්‍යයි")
    if slip or ees > ith:
        watch.append("ප්‍රමාද හෝ බාධා ඇති විය හැක — ඉක්මන් ප්‍රතිඵල බලාපොරොත්තු නොවී, ඉවසීමෙන් සහ සැලැස්මකින් කටයුතු කරන්න")
    if neg:
        watch.append(f"ග්‍රන්ථයේ අවවාද {neg}ක් (4 වන කොටස) ස්ථිර අනාවැකි නොව, සැලකිලිමත් විය යුතු කරුණු පමණි")
    L.append("<b>සැලකිලිමත් විය යුතු දේ:</b> " + ("; ".join(watch) + "." if watch else
                                                 "විශේෂ අවවාදයක් නැත; එහෙත් කාරණය සාර්ථක කර ගැනීමට අවශ්‍ය පියවර ඔබම ගත යුතුයි."))
    L.append("මේ ලකුණු ප්‍රවණතා පමණි; සමහර ඒවා එකිනෙකට පරස්පර විය හැක. අවසන් තීරණය ඔබේ විචාරය මතයි."
             + (" කාලය ගැන ජ්‍යොතිෂවේදියාගේ සටහන 5 වන කොටසේ ඇත." if (notes or {}).get("upcoming") else ""))
    return plain_box_pme(L)


def _m1_why_pme(notes):
    """The engine's reasons for one muhurta window (English, '; '-separated) in plain Sinhala:
    (good points, small drawbacks). Reasons it does not know are left out, never shown in English."""
    good, less = [], []
    for x in (y.strip() for y in notes.split(";")):
        m = re.fullmatch(r"lagna lord (\w+) in kendra/trikona", x)
        if m:
            good.append(f"එම වේලාවේ ලග්නයේ අධිපති ({pl_si(m[1])}) ශක්තිමත් තැනක සිටී")
            continue
        m = re.fullmatch(r"tara (\w+)", x)
        if m and m[1] in _M1_TARA_PME:
            if m[1] == "Janma":
                less.append("එදින නැකත ඔබේ උපන් නැකතේ කාණ්ඩයේම වීම (ජන්ම තාරාව — මිශ්‍ර ලෙස සැලකේ)")
            else:
                good.append(f"එදින නැකත ඔබේ උපන් නැකතට හිතකරයි ({_M1_TARA_PME[m[1]]} තාරාව)")
            continue
        m = re.fullmatch(r"malefic ([A-Za-z/]+) in house (\d+)", x)
        if m:
            less.append(f"{m[2]} වන භාවයේ {'/'.join(pl_si(p) for p in m[1].split('/'))} සිටීම")
            continue
        if x == "Chandra in 6/8/12 from lagna":
            less.append("චන්ද්‍රයා ලග්නයෙන් 6, 8 හෝ 12 වැනි තැනක සිටීම")
            continue
        m = re.fullmatch(r"karana (.+) \(unfavorable\)", x)
        if m and m[1] in KARANA_SI:
            less.append(f"{KARANA_SI[m[1]]} කරණය")
            continue
        if re.fullmatch(r"nakshatra .+ \(secondary\)", x):
            less.append("නැකත දෙවන පෙළේ එකක් වීම")
    return good, less


def plain_m1_pme(a, rows, best, tsi):
    """M1 in simple words: the best window (the engine's: highest score, earliest first) and why, the next
    choices, and how to use the list."""
    if not rows:
        return plain_box_pme([
            f"{esc(a.muhurta_from)} සිට {esc(a.muhurta_to)} දක්වා, {esc(tsi)} සඳහා මූලික නියම සියල්ල සපුරන කාලයක් හමු නොවීය.",
            "දින පරාසය පුළුල් කර, හෝ උදේ සහ රාත්‍රී වේලාවන් ද ඇතුළත් කර නැවත සෙවීමට ජ්‍යොතිෂවේදියාගෙන් ඉල්ලන්න.",
            "ලිත් නැකතක් ද බලනවා නම්, එය සමඟ සසඳා බලන්න."])
    top = max(r["score"] for r in rows)
    b = next(r for r in rows if r["score"] == top)
    # the weekday from the date itself (a Tuesday row's vara column is not parsed cleanly)
    day = lambda r: f"{r['date']} {WEEKDAY_SI[datetime.strptime(r['date'], '%Y-%m-%d').weekday()]}"  # noqa: E731
    when = re.search(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})", best[0]) if best else None
    mid = (f" — මැද කාලය, {when[2]} පමණ, වඩාත් සුදුසුයි" if when and when[1] == b["date"] else "")
    L = [f"<b>හොඳම කාලය:</b> {day(b)}, {b['t0']} – {b['t1']}{mid}."]
    ties = sum(r["score"] == top for r in rows)
    why = (f"කවුළු {len(rows)} අතරින් වැඩිම ලකුණු ({top}) මෙයටයි" if ties == 1
           else f"ඉහළම ලකුණු ({top}) ලැබුණු කවුළු {ties}ක් ඇත; ඒවායින් මුලින්ම එන්නේ මෙයයි")
    good, less = _m1_why_pme(b["notes"])
    why += ": මූලික නියම සියල්ල සපුරන අතර" + (", " + "; ".join(good) if good else " ලකුණු ලැබුණේ ග්‍රහ ශක්තියෙනි") + "."
    if less:
        why += " සුළු අඩුපාඩු: " + "; ".join(less) + "."
    L.append(f"<b>ඇයි?</b> {why}")
    alts = sorted((r for r in rows if r is not b), key=lambda r: -r["score"])[:2]
    if alts:
        L.append("<b>ඊළඟ හොඳම විකල්ප:</b> "
                 + "; ".join(f"{day(r)}, {r['t0']} – {r['t1']} (ලකුණු {r['score']})" for r in alts) + ".")
    L.append("<b>ලැයිස්තුව භාවිත කරන හැටි:</b> 2 වන කොටසේ ඇත්තේ මූලික නියම සපුරන කාල පමණි; ලකුණු වැඩි තරමට වඩාත් සුබයි. "
             "ඔබට පහසු කවුළුවක් තෝරා, කටයුත්ත එය තුළ <b>ආරම්භ</b> කළ විට ප්‍රමාණවත්.")
    L.append("මෙය ලිත් නැකතට <b>දෙවන මතයකි</b>; ලිත් නැකතක් ද ගන්නවා නම් දෙකටම ගැලපෙන කාලයක් තෝරන්න.")
    return plain_box_pme(L)


def plain_e1_pme(a, scan, wins, best):
    """E1 in simple words: which time fits the events best, how far to trust it, what to do next.
    The trust line only restates the scores (best, next best, the most an event list can score)."""
    if not scan:
        return ""
    given = next((s for s in scan if s["off"] == 0), None)
    n = len(scan[0]["detail"])
    span = max(abs(s["off"]) for s in scan)
    win = lambda w: f"{w[0]['time']} – {w[-1]['time']}" if len(w) > 1 else w[0]["time"]  # noqa: E731
    lag = lambda w: SIGN_SI[w[0]["lagna"]] + (f" / {SIGN_SI[w[-1]['lagna']]}" if w[-1]["lagna"] != w[0]["lagna"] else "")  # noqa: E731
    L = [f"<b>මේ වාර්තාව කළේ:</b> ඔබ දුන් වේලාවට ({esc(a.time)}) පෙර සහ පසු මිනිත්තු {span} ඇතුළත වේලාවන් {len(scan)}ක්, "
         f"ඔබේ ජීවිතයේ සිදුවීම් {n} සමඟ සසඳා බැලුවා."]
    if given and given["score"] == best:
        wg = next((w for w in wins if given in w), wins[0])
        t = (f"ඔබ දුන් වේලාව ({given['time']}) දැනටමත් වඩාත්ම ගැලපෙන කවුළුවේ ({win(wg)}, {lag(wg)} ලග්නය) ඇත. "
             "එබැවින් වේලාව වෙනස් කිරීමට අවශ්‍ය නැත.")
    else:
        w0 = wins[0]
        t = f"ඔබ දුන් සිදුවීම් වලට වඩාත්ම ගැලපෙන්නේ {win(w0)} අතර උපන් වේලාවකි ({lag(w0)} ලග්නය)."
        if given:
            t += (f" ඔබ දුන් වේලාව {given['time']} ({SIGN_SI[given['lagna']]} ලග්නය)"
                  + ("; ලග්නය ද වෙනස් වන නිසා මෙය කේන්දරය කියවීමට බලපාන වැදගත් වෙනසකි."
                     if given["lagna"] != w0[0]["lagna"] else "; ලග්නය දෙකේම එකමයි."))
    if len(wins) > 1:
        t += f" ඉහළම ලකුණු ලැබෙන කවුළු {len(wins)}ක් ඇත (4 වන කොටස)."
    L.append(f"<b>වඩාත්ම ගැලපෙන වේලාව:</b> {t}")
    lower = [s["score"] for s in scan if s["score"] < best]
    c = f"මෙය ඇස්තමේන්තුවකි. සිදුවීම් {n}කින් ලැබිය හැකි උපරිම ලකුණු {4 * n}යි; හොඳම වේලාවට {best}ක්"
    if lower:
        c += f", ඊළඟ හොඳම වේලාවන්ට {max(lower)}ක්"
        if best - max(lower) == 1:
            c += " — වෙනස ලකුණු 1ක් පමණක් නිසා අවට වේලාවන් ද බැහැර කළ නොහැක"
    L.append(f"<b>කෙතරම් විශ්වාස කළ හැකිද:</b> {c}.")
    L.append("<b>ඊළඟට කළ යුත්තේ:</b> උපන් සහතිකයේ හෝ රෝහල් වාර්තාවේ වේලාවක් ඇත්නම් එය සසඳා බලන්න — එය හොඳම සාක්ෂියයි. "
             "නැත්නම්, දිනය හරියටම මතක ඇති තවත් සිදුවීම් 3–5ක් ජ්‍යොතිෂවේදියාට දෙන්න; සිදුවීම් වැඩි වන තරමට ප්‍රතිඵලය විශ්වාසදායකයි.")
    return plain_box_pme(L)


def build_p1(d, a, notes, now_local, shat_topic, matter):
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    labels = {ls: ["ලග්න"]}
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        labels.setdefault(P[c]["sign_idx"], []).append(PLANET_SI[c] + (" (ව)" if P[c]["retro"] and c not in ("Ra", "Ke") else ""))
    H = [f'''<div class="cover" style="padding-top:12mm">{LOGO_IMG}<div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">ප්‍රශ්න වාර්තාව</h1><div class="sub">ප්‍රශ්න ජ්‍යොතිෂය ({esc(a.report)}) — තාජක සහ ෂට්පංචාශිකා</div>
      <div class="name" style="font-size:14pt">{esc(a.question or a.name)}</div>
      <div class="muted">ප්‍රශ්න මොහොත: {esc(a.date)} · {esc(a.time)} · {esc(a.place or "")}</div>
      <div style="margin:14pt auto 0 auto; width:112mm">{south_indian_html_si(labels, "ප්‍රශ්න කේන්දරය", 112)}</div></div>''']
    H.append('<div class="pb"></div>' + plain_p1_pme(d, a, matter, shat_topic, notes)
             + '<h2>1. ප්‍රශ්න කේන්දරයේ මූලික තොරතුරු</h2>')
    lord = jc.SIGN_LORD[ls]
    H.append("<table>"
             f"<tr><td style='width:34%'><b>ප්‍රශ්න ලග්නය</b></td><td>{SIGN_SI[ls]} ({dms(d['lagna']['deg_in_sign'])}) — අධිපති {PLANET_SI[lord]}, {P[lord]['house']} වැන්නේ</td></tr>"
             f"<tr><td><b>චන්ද්‍ර</b></td><td>{SIGN_SI[P['Mo']['sign_idx']]} — {P['Mo']['house']} වැන්නේ, {NAK_SI[jc.NAKSHATRAS.index(P['Mo']['nakshatra'])]} නැකත</td></tr>"
             f"<tr><td><b>හෝරාධිපති</b></td><td>{esc(si_text(d.get('hora', '')))}</td></tr>"
             f"<tr><td><b>පංචාංගය</b></td><td>{esc(pch_si(d['panchanga'])['vara'])} · {esc(pch_si(d['panchanga'])['tithi'])} · {esc(pch_si(d['panchanga'])['karana'])} කරණ</td></tr>"
             "</table>")
    H.append('<p class="small muted">වගුව කියවන හැටි: <b>ප්‍රශ්න ලග්නය</b> = ප්‍රශ්නය ඇසූ මොහොතේ නැගෙනහිරින් උදා වෙමින් තිබූ රාශිය — '
             'එය ඔබ (ප්‍රශ්නකරු) නියෝජනය කරයි, එහි අධිපති ඔබේ ග්‍රහයායි; <b>චන්ද්‍ර</b> = ප්‍රශ්නකරුගේ සිත; '
             '<b>හෝරාධිපති</b> = ඒ පැයට අධිපති ග්‍රහයා; <b>පංචාංගය</b> = දවස, තිථිය (චන්ද්‍ර දිනය) සහ කරණය (තිථියෙන් භාගයක්).</p>')
    ps = d.get("prashna_strengths", {})
    if ps:
        H.append("<h3>ග්‍රහ බල (තාජක)</h3><table><tr><th>ග්‍රහයා</th>"
                 + "".join(f"<th>{PLANET_SI[c]}</th>" for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]) + "</tr>"
                 + "<tr><td>හර්ෂ බල</td>" + "".join(f"<td>{ps['harsha'][c]}</td>" for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]) + "</tr>"
                 + "<tr><td>පංච වර්ගීය</td>" + "".join(f"<td>{ps['pvb'][c]}</td>" for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]) + "</tr></table>")
        H.append('<p class="small muted">වගුව කියවන හැටි: ග්‍රහයෙකුගේ ශක්තිය මනින තාජක ක්‍රම දෙකක් — <b>හර්ෂ බල</b> සහ '
                 '<b>පංච වර්ගීය බල</b> (දෙකම 0–20). අගය වැඩි තරමට ග්‍රහයා ශක්තිමත්.</p>')
    ty = d.get("tajaka_yogas", {})
    lines = [("ඉථසාල", ty.get("ithasala", [])), ("ඊසර්ඵ", ty.get("eesarpha", [])), ("වෙනත්", ty.get("general", []) + ty.get("nakta_yamaya", []))]
    H.append("<h2>2. තාජක යෝග</h2>")
    H.append('<p class="small">තාජක යෝග යනු ග්‍රහයන් දෙදෙනෙකු එකිනෙකා දකින (දෘෂ්ටි) සම්බන්ධතා. <b>ඉථසාල</b> = වේගයෙන් යන ග්‍රහයා '
             'සෙමින් යන ග්‍රහයා වෙත ළං වෙමින් සිටීම — කාරණය ඉටුවීමේ ලකුණක්. <b>ඊසර්ඵ</b> = ඔවුන් එකිනෙකාගෙන් ඈත් වෙමින් සිටීම — '
             'කාරණය ලිස්සා යාමේ හෝ ප්‍රමාද වීමේ ලකුණක්.</p>')
    if any(l for _, l in lines):
        for t, l in lines:
            if l:
                H.append(f"<h3>{t}</h3><ul>" + "".join(f"<li>{esc(si_text(x))}</li>" for x in l) + "</ul>")
        H.append('<p class="small muted">කියවන හැටි: වරහන් තුළ = ග්‍රහයා සිටින රාශිය සහ අංශකය (R = වක්‍ර); '
                 '<b>පරතරය</b> = ග්‍රහයන් දෙදෙනාගේ අංශක අතර වෙනස; <b>පූර්ණ</b> = අංශක 1ක් ඇතුළත, <b>වර්තමාන</b> = දැන් ළං වෙමින්, '
                 '<b>භවිෂ්‍ය</b> = ළඟදීම ළං වේ.</p>')
    else:
        H.append("<p>දෘෂ්ටි කක්ෂ තුළ (ග්‍රහයන් එකිනෙකාට බලපාන අංශක සීමාව තුළ) ප්‍රධාන තාජක යෝග නොමැත.</p>")
    if matter:
        H.append(f"<h2>3. කාරණය — {matter} වන භාවය ({HOUSE_PLAIN_SI[matter]})</h2><ul>"
                 + "".join(f"<li>{esc(si_text(x.strip()))}</li>" for x in d.get("matter_lines", [])) + "</ul>")
        H.append('<p class="small muted">කියවන හැටි: ලග්නාධිපති (ඔබ), කාරණයේ භාවාධිපති (කාරණය), අදාළ සහමයේ '
                 '(කාරණයට අදාළව ගණනය කරන සංවේදී ලක්ෂ්‍යයේ) අධිපති සහ ස්වාභාවික කාරකයා (කාරණය ස්වභාවයෙන් පෙන්වන ග්‍රහයා) '
                 'අතර ඉථසාල යෝගයක් කාරණය ඉටුවීමට නැඹුරුව පෙන්වයි; ඊසර්ඵ ලිස්සා යාම පෙන්වයි (තාජක 29.2). (R) = වක්‍ර.</p>')
    if d.get("shatpanchasika"):
        H.append(f'<h2>4. ෂට්පංචාශිකා — {PRASHNA_TOPIC_SI.get(shat_topic, shat_topic)}</h2>')
        H.append('<p class="small">ෂට්පංචාශිකා (“පනස් හය”) යනු ප්‍රශ්න ජ්‍යොතිෂය ගැන ශ්ලෝක 56කින් යුත් පැරණි ග්‍රන්ථයකි. '
                 'මෙහි ඇත්තේ මේ ප්‍රශ්න කේන්දරයට අදාළ වන ශ්ලෝක සහ ඒවා පෙන්වන දේයි.</p>')
        H.append("<table><tr><th style='width:8%'>ශ්ලෝකය</th><th>නියමය</th><th>ඇඟවීම</th></tr>"
                 + "".join(f"<tr><td>{r['stanza']}</td><td>{esc(si_shat_rule(r['rule']))}</td><td>{esc(si_shat_verdict(r['verdict'])[0])}</td></tr>"
                           for r in d["shatpanchasika"]) + "</table>")
        H.append('<p class="small muted">වගුව කියවන හැටි: <b>නියමය</b> = කේන්දරයේ දකින තත්ත්වය; <b>ඇඟවීම</b> = ග්‍රන්ථය අනුව '
                 'එහි තේරුම. එක් ඇඟවීමක් තනිව නොගෙන, සියල්ල එකට බලන්න.</p>')
        H.append('<p class="small muted">මූලාශ්‍රය: ප්‍රිථුයශස් ගේ ෂට්පංචාශිකා (චප්පන්න), B. Suryanarain Rao ගේ 1946 ඉංග්‍රීසි පරිවර්තනය. '
                 'නූපන් දරුවාගේ ලිංගය, ලිංගික හැසිරීම සහ මරණය පිළිබඳ ශ්ලෝක මෙහි ඉදිරිපත් නොකෙරේ.</p>')
    H.append("<h2>5. විග්‍රහය</h2>")
    H.append(f'<div class="box">{p1_auto_summary(d, matter, shat_topic)}</div>')
    H.append(note_block(notes, "summary"))
    H.append(note_block(notes, "upcoming", "කාල සීමා"))
    H.append('<div class="pb"></div><h2>වචන කිහිපයක තේරුම</h2>' + glossary_html(GLOSS_P1_SHARED_PME, GLOSS_P1_PME))
    H.append(disc_nopb_pme("ප්‍රශ්න ජ්‍යොතිෂය — තාජක ක්‍රමය (P.V.R. Narasimha Rao ch. 27–29) සහ ෂට්පංචාශිකා. "
                              "ප්‍රශ්න කේන්දරය සෑදෙන්නේ ප්‍රශ්නය අසන මොහොතටයි; එම මොහොත වැරදි නම් ප්‍රතිඵලයද වෙනස් වේ. "
                              "මේ ඇඟවීම් ප්‍රවණතා පෙන්වන අතර, ඔබේ තීරණය ඔබේ විචාරය මතයි."))
    return "\n".join(H)


POS_MARKS = ("සාර්ථක", "ලැබීම", "ලාභ", "ජය", "සමෘද්ධි", "හිතකර", "ඉටුවීම", "සාමය", "සුවය", "විවාහය සිදුවීම", "ගෞරව")
NEG_MARKS = ("අසාර්ථක", "අලාභ", "පරාජය", "නොවේ", "නැත", "ලිස්සා", "බිය", "බාධක", "ප්‍රවේශම්", "අහිමි")


# ================================================================ Shatpanchasika (P1/P2) in Sinhala
# Every rule and verdict the engine's shatpanchasika() can print (B. Suryanarain Rao's 1946 rendering),
# translated sentence by sentence. Word-by-word translation left most of the travel, lost-article,
# dispute, health, subject and rain stanzas in English (found 2026-11-27).
_SH_TYPE = {"movable": "චර", "fixed": "ස්ථිර", "dual": "ද්විස්වභාව"}
_SH_WHO8 = {"father": "පියා", "mother / maternal relations": "මව / මව් පාර්ශ්වයේ ඥාතීන්", "brothers, cousins": "සහෝදරයන්, ඥාති සහෝදරයන්",
            "maternal uncles": "මාමලා", "children, preceptor": "දරුවන්, ගුරුවරයා", "wife, female relations": "බිරිඳ, කාන්තා ඥාතීන්",
            "servants, dependents": "සේවකයන්, යැපෙන්නන්", "-": "—"}
_SH_WHO49 = {"someone like / connected to the querent himself": "ප්‍රශ්නකරු වැනි හෝ ඔහුට සම්බන්ධ කෙනෙක්", "brothers": "සහෝදරයන්",
             "mother or sisters": "මව හෝ සහෝදරියන්", "children": "දරුවන්", "enemies / opponents": "සතුරන් / ප්‍රතිවාදීන්",
             "wife / spouse": "බිරිඳ / කලත්‍රයා", "a virtuous person / elder": "ගුණවත් කෙනෙක් / වැඩිහිටියෙක්",
             "preceptor / person venerated": "ගුරුවරයා / ගෞරවනීය කෙනෙක්", "not classified by the text (2/8/11/12)": "ග්‍රන්ථයේ වර්ග කර නැත (2/8/11/12)"}
_SH_AGE = {"young": "තරුණ", "old": "වැඩිහිටි", "post-natal / mature": "මේරූ", "restless / difficult": "නොසන්සුන් / අපහසු",
           "pleasure-loving": "සැප විඳීමට කැමති"}
_SH_LAGNA38 = {"fixed sign": "ස්ථිර රාශිය", "fixed navamsa": "ස්ථිර නවාංශය", "vargottama": "වර්ගෝත්තම"}
_SH_SHAPE = {"long": "දිගු", "broad": "පළල්", "small": "කුඩා"}
_SH_GROUP = {"Dhatu (mineral/inanimate)": "ධාතු (ලෝහ/අජීවී)", "Moola (vegetable/root)": "මූල (ශාක/මුල්)", "Jeeva (living being)": "ජීව (ප්‍රාණීන්)"}
_SH_DIR = {"East": "නැගෙනහිර", "South-East": "අග්නිදිග", "South": "දකුණ", "South-West": "නිරිත දිග", "West": "බටහිර",
           "North-West": "වයඹ දිග", "North": "උතුර", "North-East": "ඊසාන දිග"}


def _sh_planets(s):
    """'Guru/Shukr' (the engine's five-letter forms) or '-' -> Sinhala."""
    s = s.strip()
    return "නැත" if s in ("", "-") else "/".join(PL_EN2SI.get(x, x) for x in s.split("/"))


_SH_CONV = {"p": _sh_planets, "s": lambda s: SIGN_EN2SI.get(s, s), "n": str, "t": lambda s: _SH_TYPE[s],
            "b": lambda s: {"benefic": "ශුභ", "malefic": "පාප"}[s], "o": lambda s: {"odd": "ඔජ", "even": "යුග්ම"}[s],
            "u": lambda s: {"Sirshodaya": "ශීර්ෂෝදය", "Prishtodaya": "පෘෂ්ඨෝදය", "Ubhayodaya": "උභයෝදය"}[s],
            "r": lambda s: " — වක්‍ර" if s else "", "w": lambda s: _SH_WHO8.get(s, s), "q": lambda s: _SH_WHO49.get(s, s),
            "a": lambda s: ", ".join(_SH_AGE.get(x, x) for x in s.split(", ")), "v": lambda s: ", ".join(_SH_LAGNA38[x] for x in s.split(", ")),
            "h": lambda s: _SH_SHAPE[s], "g": lambda s: _SH_GROUP.get(s, s), "d": lambda s: _SH_DIR.get(s, s),
            "c": lambda s: " — ශුභ සම්බන්ධයක් නැත" if s == " (no benefic association)" else f", ශුභ {_sh_planets(s.replace(' with benefic ', ''))} සමඟ"}
_PL = r"([A-Za-z/-]+)"     # a planet list as printed, or "-"
_SG = r"([A-Z][a-z]+)"     # a sign
SHAT_RULE_SI = [(re.compile(rx), si, conv) for rx, si, conv in [
    # general
    (rf"Lagna {_SG}: (benefic|malefic)-owned, (\d)/6 benefic shadvarga lords, (Sirshodaya|Prishtodaya|Ubhayodaya)",
     "ලග්නය {0}: {1} ග්‍රහයෙකුට අයත්; ෂඩ්වර්ග අධිපතීන් 6න් {2}ක් ශුභ; {3}", "sbnu"),
    (r"Lagna navamsa (\d) in (odd|even) sign", "ලග්න නවාංශය {0} ({1} රාශියක)", "no"),
    (rf"benefics {_PL} in kendra/trikona, no malefics in kendras/8th",
     "කේන්ද්‍ර/ත්‍රිකෝණවල ශුභ ග්‍රහයන් {0}; කේන්ද්‍රවල හෝ 8 වැන්නේ පාප ග්‍රහයන් නැත", "p"),
    (rf"malefics {_PL} in kendras/8th, no benefics in kendra/trikona",
     "කේන්ද්‍රවල හෝ 8 වැන්නේ පාප ග්‍රහයන් {0}; කේන්ද්‍ර/ත්‍රිකෝණවල ශුභ ග්‍රහයන් නැත", "p"),
    (rf"benefics {_PL} in kendra/trikona but malefics {_PL} in kendras/8th",
     "කේන්ද්‍ර/ත්‍රිකෝණවල ශුභ ග්‍රහයන් {0}, නමුත් කේන්ද්‍රවල හෝ 8 වැන්නේ පාප ග්‍රහයන් {1}", "pp"),
    (rf"3/5/7/11: benefics {_PL}, malefics {_PL}", "3/5/7/11 භාවවල: ශුභ ග්‍රහයන් {0}, පාප ග්‍රහයන් {1}", "pp"),
    (rf"Lagna {_SG} \(Ge/Vi/Li/Aq\) with benefic {_PL}", "ලග්නය {0} (මිථුන/කන්‍යා/තුලා/කුම්භ), ශුභ {1} සමඟ", "sp"),
    (rf"benefics in 7th/10th: {_PL}", "7/10 වැන්නේ ශුභ ග්‍රහයන්: {0}", "p"),
    (rf"benefics in 1/2/5: {_PL}", "1/2/5 හි ශුභ ග්‍රහයන්: {0}", "p"),
    (rf"malefics in 11th/12th: {_PL}", "11/12 වැන්නේ පාප ග්‍රහයන්: {0}", "p"),
    (r"Chandra in Lagna", "චන්ද්‍ර ලග්නයේ", ""),
    (r"Chandra in 10th", "චන්ද්‍ර 10 වැන්නේ", ""),
    (r"Chandra in (\d+) aspected by Guru", "චන්ද්‍ර {0} වැන්නේ, ගුරු දෘෂ්ටිය සහිතව", "n"),
    (rf"malefics {_PL} in 1/3/5/8/9", "1/3/5/8/9 හි පාප ග්‍රහයන් {0}", "p"),
    (rf"benefics {_PL} in 1/3/5/8/9", "1/3/5/8/9 හි ශුභ ග්‍රහයන් {0}", "p"),
    # travel and return
    (rf"Lagna {_SG} is (movable|fixed|dual)", "ලග්නය {0} — {1} රාශියකි", "st"),
    (rf"Lagna & Chandra influences: benefic {_PL}, malefic {_PL}", "ලග්නයට සහ චන්ද්‍රයාට බලපෑම්: ශුභ {0}, පාප {1}", "pp"),
    (rf"planets in 2/3/5: {_PL}", "2/3/5 හි ග්‍රහයන්: {0}", "p"),
    (r"planet in 6th/7th, with Guru in kendra or Budha/Shukra in 5th/9th",
     "6/7 වැන්නේ ග්‍රහයෙක්; ගුරු කේන්ද්‍රයක හෝ බුධ/ශුක්‍ර 5/9 වැන්නේ", ""),
    (rf"Chandra in 8th; kendras: malefics {_PL}, benefics {_PL}", "චන්ද්‍ර 8 වැන්නේ; කේන්ද්‍රවල: පාප {0}, ශුභ {1}", "pp"),
    (rf"Prishtodaya lagna aspected by malefic {_PL}", "පෘෂ්ඨෝදය ලග්නයට පාප ග්‍රහ {0} දෘෂ්ටිය", "p"),
    (rf"malefics {_PL} in (\d+)th, no benefic aspect", "{1} වැන්නේ පාප ග්‍රහයන් {0}, ශුභ දෘෂ්ටියක් නැත", "pn"),
    (rf"malefics {_PL} in kendras without benefic aspect", "ශුභ දෘෂ්ටියක් නැති කේන්ද්‍රවල පාප ග්‍රහයන් {0}", "p"),
    (rf"first occupied sign from Lagna is (\d+)th \({_SG}, {_PL}\)( retrograde)?",
     "ලග්නයෙන් පසු ග්‍රහයෙක් සිටින පළමු රාශිය {0} වැන්න ({1}, {2}){3}", "nspr"),
    (r"movable lagna in a movable navamsa beyond the 5th", "චර ලග්නය, 5 වැන්නෙන් ඔබ්බට චර නවාංශයක", ""),
    (rf"retrograde {_PL} in houses 8-12", "8–12 භාවවල වක්‍ර {0}", "p"),
    (rf"([A-Z][a-z]+) in 8th( with benefic [A-Za-z/-]+| \(no benefic association\))", "{0} 8 වැන්නේ{1}", "pc"),
    (r"Shani with malefics in 9th, no benefic aspect", "9 වැන්නේ පාප ග්‍රහයන් සමඟ ශනි, ශුභ දෘෂ්ටියක් නැත", ""),
    (rf"movable lagna with benefic {_PL}", "චර ලග්නය, ශුභ {0} සමඟ", "p"),
    (rf"malefics {_PL} in prashna lagna", "ප්‍රශ්න ලග්නයේ පාප ග්‍රහයන් {0}", "p"),
    # lost article
    (r"bright \(full\) Chandra in lagna aspected by Guru/Shukra", "පූර්ණ (දීප්තිමත්) චන්ද්‍ර ලග්නයේ, ගුරු/ශුක්‍ර දෘෂ්ටිය සහිතව", ""),
    (rf"powerful benefic {_PL} in 11th", "11 වැන්නේ ශක්තිමත් ශුභ ග්‍රහ {0}", "p"),
    (rf"Sirshodaya lagna {_SG} with benefic {_PL}, benefic aspect", "ශීර්ෂෝදය ලග්නය {0}, ශුභ {1} සමඟ, ශුභ දෘෂ්ටිය සහිතව", "sp"),
    (r"none of the recovery combinations \(7, 40\) present", "නැවත ලැබීමේ සංයෝග (7, 40) කිසිවක් නැත", ""),
    (r"lagna: ((?:fixed sign|fixed navamsa|vargottama)(?:, (?:fixed sign|fixed navamsa|vargottama))*)", "ලග්නය: {0}", "v"),
    (r"lagna neither fixed, fixed-navamsa nor vargottama", "ලග්නය ස්ථිර රාශියක්, ස්ථිර නවාංශයක් හෝ වර්ගෝත්තම නොවේ", ""),
    (r"drekkana (\d) rising", "උදා වන ද්‍රේෂ්කාණය {0}", "n"),
    (r"strongest planet in kendras: ([A-Z][a-z]+)", "කේන්ද්‍රවල ශක්තිමත්ම ග්‍රහයා: {0}", "p"),
    (r"no planet in kendras; lagna lord ([A-Z][a-z]+)", "කේන්ද්‍රවල ග්‍රහයන් නැත; ලග්නාධිපති {0}", "p"),
    (rf"lagna {_SG}", "ලග්නය {0}", "s"),
    # dispute
    (rf"benefics {_PL} in 1/7/10", "1/7/10 හි ශුභ ග්‍රහයන් {0}", "p"),
    (r"Kuja & Shani in 9th", "කුජ සහ ශනි 9 වැන්නේ", ""),
    (rf"{_PL} in 9th", "{0} 9 වැන්නේ", "p"),
    (rf"benefics on querent's half \(3-8\): {_PL}; on opponent's half \(9-2\): {_PL}",
     "ප්‍රශ්නකරුගේ පැත්තේ (3–8) ශුභ ග්‍රහයන්: {0}; ප්‍රතිවාදියාගේ පැත්තේ (9–2): {1}", "pp"),
    (rf"malefics {_PL} in 10/11/12", "10/11/12 හි පාප ග්‍රහයන් {0}", "p"),
    (r"male-sign lagna with benefic, or benefics in 11th/12th", "ශුභ ග්‍රහයෙකු සහිත පුරුෂ රාශි ලග්නයක්, හෝ 11/12 වැන්නේ ශුභ ග්‍රහයන්", ""),
    (rf"malefics {_PL} in dual signs", "ද්විස්වභාව රාශිවල පාප ග්‍රහයන් {0}", "p"),
    (rf"benefics {_PL} in kendras", "කේන්ද්‍රවල ශුභ ග්‍රහයන් {0}", "p"),
    (rf"malefics {_PL} in kendras", "කේන්ද්‍රවල පාප ග්‍රහයන් {0}", "p"),
    (r"(movable|fixed|dual) lagna, Chandra in (movable|fixed|dual) sign", "{0} ලග්නය, චන්ද්‍ර {1} රාශියක", "tt"),
    (r"fixed lagna with Guru/Shani", "ස්ථිර ලග්නය, ගුරු/ශනි සමඟ", ""),
    (r"movable lagna with Surya/Guru", "චර ලග්නය, රවි/ගුරු සමඟ", ""),
    (rf"movable lagna with {_PL}", "චර ලග්නය, {0} සමඟ", "p"),
    (rf"malefics {_PL} in 4th", "4 වැන්නේ පාප ග්‍රහයන් {0}", "p"),
    (rf"4th house is {_SG} \(Pi/Sc/Aq/Cn\)", "4 වැන්න {0} (මීන/වෘශ්චික/කුම්භ/කටක)", "s"),
    (r"lagna or 4th in Ar/Le/Ta/Sg", "ලග්නය හෝ 4 වැන්න මේෂ/සිංහ/වෘෂභ/ධනු රාශියක", ""),
    (r"Surya & Chandra in 4th", "රවි සහ චන්ද්‍ර 4 වැන්නේ", ""),
    (rf"{_PL} in 4th", "{0} 4 වැන්නේ", "p"),
    (r"Guru/Shukra in 2nd or 3rd", "ගුරු/ශුක්‍ර 2 හෝ 3 වැන්නේ", ""),
    (r"strongest planet ([A-Z][a-z]+) is (\d+)th from lagna; navamsa (movable|fixed|dual) \(x(\d)\)",
     "ශක්තිමත්ම ග්‍රහයා {0} ලග්නයෙන් {1} වැන්නේ; නවාංශය {2} (×{3})", "pntn"),
    (r"7th lord ([A-Z][a-z]+) retrograde", "7 වන අධිපති {0} වක්‍ර", "p"),
    (r"Chandra (\d+)th from lagna, no planet between", "චන්ද්‍ර ලග්නයෙන් {0} වැන්නේ, අතර ග්‍රහයෙක් නැත", "n"),
    # health, marriage, subject, rain
    (rf"benefics in 1/5/7/8: {_PL}; Chandra in (\d+)", "1/5/7/8 හි ශුභ ග්‍රහයන්: {0}; චන්ද්‍ර {1} වැන්නේ", "pn"),
    (r"Shani in (\d+)th", "ශනි {0} වැන්නේ", "n"),
    (r"Chandra in (\d+) aspected by Guru/Surya/Budha", "චන්ද්‍ර {0} වැන්නේ, ගුරු/රවි/බුධ දෘෂ්ටිය සහිතව", "n"),
    (rf"benefics {_PL} in kendra/trikona", "කේන්ද්‍ර/ත්‍රිකෝණවල ශුභ ග්‍රහයන් {0}", "p"),
    (r"strongest planet ([A-Z][a-z]+) \(PVB ([\d.]+)\) in house (\d+)", "ශක්තිමත්ම ග්‍රහයා {0} (පංචවර්ගීය බලය {1}) {2} වැන්නේ", "pnn"),
    (r"navamsa lord of lagna is in lagna", "ලග්නයේ නවාංශ අධිපති ලග්නයේම සිටී", ""),
    (rf"planets in/aspecting lagna: {_PL}", "ලග්නයේ සිටින හෝ ලග්නයට දෘෂ්ටි කරන ග්‍රහයන්: {0}", "p"),
    (r"Shani 7th from Chandra / Shani 4th & Shukra 8th / both in 2nd-3rd",
     "චන්ද්‍රයාගෙන් 7 වැන්නේ ශනි / ශනි 4 සහ ශුක්‍ර 8 වැන්නේ / දෙදෙනාම 2–3 වැන්නේ", ""),
    (rf"benefics {_PL} in watery signs in 1/2/3/4/7/10, bright fortnight", "1/2/3/4/7/10 හි ජල රාශිවල ශුභ ග්‍රහයන් {0}; පුර පක්ෂය", "p"),
    (r"Chandra in lagna in a watery sign", "ජල රාශියක චන්ද්‍ර ලග්නයේ", ""),
    (r"no rain combination", "වර්ෂා සංයෝගයක් නැත", ""),
]]

# verdict -> (Sinhala, tone): +1 favours the querent, -1 against, 0 information only
SHAT_VERDICT_SI = {
    "SUCCESS indicated": ("සාර්ථක වීමේ ප්‍රවණතාව", 1), "FAILURE indicated": ("අසාර්ථක වීමේ ප්‍රවණතාව", -1),
    "MIXED — success only with great effort": ("මිශ්‍ර — විශාල උත්සාහයකින් පමණක් සාර්ථකත්වය", 0),
    "querent gains ALL desired in full": ("අපේක්ෂිත දේ සම්පූර්ණයෙන් ලැබීමේ ප්‍රවණතාව", 1),
    "complete failure of the desire; caution": ("අපේක්ෂාව ඉටු නොවීමේ ප්‍රවණතාව; ප්‍රවේශම්", -1),
    "partial — obstacles": ("අර්ධ ප්‍රතිඵල — බාධක", 0),
    "gains & success": ("ලාභ සහ සාර්ථකත්වය", 1), "losses": ("අලාභ", -1), "gains and losses both": ("ලාභ සහ අලාභ දෙකම", 0),
    "success foretold": ("සාර්ථකත්වය", 1), "gain of land/position": ("ඉඩම්/තනතුරු ලාභය", 1),
    "wealth & honour from authorities": ("අධිකාරි මගින් ධනය සහ ගෞරවය", 1), "no success in the matter": ("කාරණයේ සාර්ථකත්වයක් නැත", -1),
    "not favourable for the matter": ("කාරණයට හිතකර නැත", -1), "prosperity": ("සමෘද්ධිය", 1),
    "success through a woman's help": ("කාන්තාවකගේ සහාය මගින් සාර්ථකත්වය", 1),
    "loss of the object in mind, monetary loss, fear": ("අපේක්ෂිත දේ අහිමි වීම, මුදල් අලාභ, බිය", -1),
    "good in all these respects": ("මේ සියලු අතින් හිතකර", 1),
    # travel
    "traveller has suffered / moved / met loss": ("ගමන් ගිය අය දුෂ්කරතා විඳ, ස්ථාන මාරු වී හෝ අලාභ ලබා ඇත", -1),
    "traveller has not left, no harm, no loss, no defeat": ("ගමන් ගිය අය තවම පිටත්ව ගොස් නැත; හානියක්, අලාභයක්, පරාජයක් නැත", 1),
    "mixed results": ("මිශ්‍ර ප්‍රතිඵල", 0), "good": ("හිතකර", 1), "unfavourable": ("අහිතකර", -1), "mixed": ("මිශ්‍ර", 0),
    "return with property/riches": ("ධනය/සම්පත් සමඟ ආපසු පැමිණීම", 1),
    "return, but without gains": ("ආපසු පැමිණීම, නමුත් ලාභ නොමැතිව", 0),
    "return with property/riches; SPEEDY return (Guru/Shukra there)": ("ධනය/සම්පත් සමඟ, ඉක්මනින් ආපසු පැමිණීම (ගුරු/ශුක්‍ර එහි)", 1),
    "return, but without gains; SPEEDY return (Guru/Shukra there)": ("ඉක්මනින් ආපසු පැමිණීම (ගුරු/ශුක්‍ර එහි), නමුත් ලාභ නොමැතිව", 1),
    "traveller WILL return (Rao's reading)": ("ගමන් ගිය අය ආපසු පැමිණේ (රාවෝගේ කියවීම)", 1),
    "safe return": ("ආරක්ෂිතව ආපසු පැමිණීම", 1), "safe return with wealth & honour": ("ධනය සහ ගෞරවය සමඟ ආරක්ෂිතව ආපසු පැමිණීම", 1),
    "return uncertain (malefics in kendras)": ("ආපසු පැමිණීම අවිනිශ්චිතයි (කේන්ද්‍රවල පාප ග්‍රහයන්)", -1),
    "traveller has suffered restraint / hardship": ("ගමන් ගිය අය බාධා / දුෂ්කරතා විඳ ඇත", -1),
    "traveller has left the place he first went to": ("ගමන් ගිය අය මුලින් ගිය ස්ථානයෙන් ඉවත්ව ගොස් ඇත", 0),
    "grave danger to the traveller — classical text gives the worst reading; not predicted here":
        ("ගමන් ගිය අයට බරපතළ අවදානම් ඇඟවීමක් — සම්භාව්‍ය ග්‍රන්ථයේ දරුණුම කියවීම මෙහි අනාවැකියක් ලෙස නොදක්වේ", -1),
    "traveller waylaid / removed by robbers (classical)": ("ගමනේදී බාධා හෝ සොරුන්ගෙන් හානි (සම්භාව්‍ය කියවීම)", -1),
    "query concerns a person gone to a foreign land": ("ප්‍රශ්නය විදේශගත කෙනෙකු ගැනයි", 0),
    "return of the person indicated": ("එම පුද්ගලයා ආපසු පැමිණීමේ ප්‍රවණතාව", 1),
    # Rahu/Ketu in the 8th: the text names no relative for them
    "query about -: has moved on to another country; safe & prosperous return":
        ("වෙනත් රටකට ගොස් ඇත; ආරක්ෂිතව, සමෘද්ධිමත්ව ආපසු පැමිණේ (ග්‍රන්ථය රාහු/කේතුට ඥාතියෙක් නියම නොකරයි)", 1),
    "query about -: still in the first place; caution":
        ("තවම මුල් ස්ථානයේමයි; ප්‍රවේශම් (ග්‍රන්ථය රාහු/කේතුට ඥාතියෙක් නියම නොකරයි)", 0),
    "traveller suffering ill-health (recommend checking on them)": ("ගමන් ගිය අයගේ සෞඛ්‍යය දුර්වල විය හැක (ඔවුන් ගැන විමසා බැලීම හොඳයි)", -1),
    "prosperity to the traveller": ("ගමන් ගිය අයට සමෘද්ධිය", 1), "trouble to the traveller": ("ගමන් ගිය අයට කරදර", -1),
    "trouble to the traveller (fixed lagna: mixed)": ("ගමන් ගිය අයට කරදර (ස්ථිර ලග්නය: මිශ්‍ර)", -1),
    # lost article
    "SPEEDY recovery": ("ඉක්මනින් නැවත ලැබීම", 1), "recovery indicated": ("නැවත ලැබීමේ ප්‍රවණතාව", 1),
    "stolen article recovered soon": ("සොරකම් කළ දේ ඉක්මනින් ලැබීම", 1),
    "recovery not promised by this prashna": ("මේ ප්‍රශ්න කේන්දරයෙන් නැවත ලැබීමක් පෙන්නුම් නොකරයි", -1),
    "article is still in the same place; taken by a close relation / insider": ("දේ තවම එම ස්ථානයේම; ළඟ කෙනෙකු/ඇතුළාන්තයේ කෙනෙකු විසින් ගෙන ඇත", 0),
    "article has been moved away": ("දේ වෙනත් තැනකට ගෙන ගොස් ඇත", 0),
    "front part of the house": ("ගෙදර ඉදිරි කොටසේ", 0), "middle of the house": ("ගෙදර මැද කොටසේ", 0),
    "back of the house or beyond": ("ගෙදර පිටුපස හෝ ඉන් ඔබ්බේ", 0),
    # dispute
    "VICTORY to the querent": ("ප්‍රශ්නකරුට ජය", 1), "defeat to the opponent": ("ප්‍රතිවාදියාට පරාජය", 1),
    "victory to the OPPONENT": ("ප්‍රතිවාදියාට ජය", -1), "favours querent": ("ප්‍රශ්නකරුට වාසි", 1),
    "favours opponent": ("ප්‍රතිවාදියාට වාසි", -1), "balanced": ("සමබර", 0),
    "defeat to the querent's side": ("ප්‍රශ්නකරුගේ පැත්තට පරාජය", -1),
    "settlement / accommodation between the parties": ("පාර්ශ්ව අතර සමථයක්", 1),
    "fighting & enmity continue": ("ගැටුම සහ වෛරය දිගටම", -1), "peace between the parties": ("පාර්ශ්ව අතර සාමය", 1),
    "they will fight": ("ගැටුම දිගටම", -1), "opponent does not come forward": ("ප්‍රතිවාදියා ඉදිරිපත් නොවේ", 1),
    "opponent comes in strength and presses": ("ප්‍රතිවාදියා ශක්තියෙන් ඉදිරිපත් වේ", -1),
    "opponent turns back after advancing far": ("ප්‍රතිවාදියා දුර ඇවිත් ආපසු හැරේ", 1),
    "opponent returns after coming half-way": ("ප්‍රතිවාදියා අඩක් ඇවිත් ආපසු යයි", 1),
    "opponent withdraws": ("ප්‍රතිවාදියා පසුබසී", 1),
    "opponent withdraws after a heavy defeat": ("ප්‍රතිවාදියා දැඩි පරාජයකින් පසු පසුබසී", 1),
    "opponent does not come": ("ප්‍රතිවාදියා නොපැමිණේ", 1), "opponent comes well prepared": ("ප්‍රතිවාදියා හොඳින් සූදානම්ව පැමිණේ", -1),
    "opponent turns back part-way": ("ප්‍රතිවාදියා අතරමගදී ආපසු හැරේ", 1),
    "opponent retires disappointed after close approach": ("ප්‍රතිවාදියා ළං වී කලකිරී ආපසු යයි", 1),
    "opponent retreats in disgrace": ("ප්‍රතිවාදියා අපකීර්තියෙන් පසුබසී", 1),
    "opponent cannot stand; early retreat": ("ප්‍රතිවාදියාට ඔරොත්තු දිය නොහැක; ඉක්මන් පසුබැසීම", 1),
    "hostile party will not arrive (Rao)": ("විරුද්ධ පාර්ශ්වය නොපැමිණේ (රාවෝ)", 1),
    "hostile party arrives quickly (Rao)": ("විරුද්ධ පාර්ශ්වය ඉක්මනින් පැමිණේ (රාවෝ)", -1),
    "party gone out returns immediately (Rao)": ("පිටව ගිය පාර්ශ්වය වහාම ආපසු එයි (රාවෝ)", 0),
    "opponent clears out when the 7th lord turns direct": ("7 වන අධිපති ඍජු ගමනට හැරෙන විට ප්‍රතිවාදියා ඉවත් වේ", 0),
    # health, marriage, subject, rain
    "safe recovery indicated": ("සුවය ලැබීමේ ප්‍රවණතාව", 1),
    "recovery combination incomplete — no strong promise (astrology is not medical advice)":
        ("සුවය පිළිබඳ සංයෝගය සම්පූර්ණ නැත — ශක්තිමත් ඇඟවීමක් නැත (ජ්‍යොතිෂය වෛද්‍ය උපදෙස් නොවේ)", 0),
    "marriage indicated (Shani in 7th)": ("විවාහයේ ප්‍රවණතාව (ශනි 7 වැන්නේ)", 1),
    "Shani not in 7th — no promise from this stanza alone": ("ශනි 7 වැන්නේ නැත — මේ ශ්ලෝකයෙන් පමණක් ඇඟවීමක් නැත", 0),
    "marriage will be celebrated": ("විවාහය සිදුවීමේ ප්‍රවණතාව", 1),
    "marriage celebrated speedily": ("විවාහය ඉක්මනින් සිදුවීමේ ප්‍රවණතාව", 1),
    "query is about the querent himself": ("ප්‍රශ්නය ප්‍රශ්නකරු ගැනමයි", 0),
    "early rain in the season": ("කන්නයේ මුල් වර්ෂාව", 1), "combination absent": ("සංයෝගය නැත", 0),
    "plentiful rain": ("බහුල වර්ෂාව", 1), "rain": ("වර්ෂාව", 1), "-": ("—", 0),
}
SHAT_VERDICT_RX = [(re.compile(rx), si, conv, tone) for rx, si, conv, tone in [
    (r"object of the query: (.+)", "ප්‍රශ්නයේ විෂය: {0}", "g", 0),
    (r"return within (\d+) days \(retrograde rule, Rao\)", "දින {0}ක් ඇතුළත ආපසු පැමිණීම (වක්‍ර නියමය, රාවෝ)", "n", 0),
    (r"return within (\d+) x 12 = (\d+) days", "දින {0} × 12 = {1}ක් ඇතුළත ආපසු පැමිණීම", "nn", 0),
    (r"query about (.+?): has moved on to another country; safe & prosperous return",
     "ප්‍රශ්නය {0} ගැන: වෙනත් රටකට ගොස් ඇත; ආරක්ෂිතව, සමෘද්ධිමත්ව ආපසු පැමිණේ", "w", 1),
    (r"query about (.+?): still in the first place; caution", "ප්‍රශ්නය {0} ගැන: තවම මුල් ස්ථානයේමයි; ප්‍රවේශම්", "w", 0),
    (r"direction: (.+)", "දිශාව: {0}", "d", 0),
    (rf"article shape: (long|broad|small); colour/nature from navamsa {_SG} \(lord ([A-Z][a-z]+)\)",
     "දෙයේ හැඩය: {0}; වර්ණය/ස්වභාවය නවාංශ රාශිය {1} අනුව (අධිපති {2})", "hsp", 0),
    (rf"opponent halts permanently \(retrograde {_PL}\)", "ප්‍රතිවාදියා ස්ථිරවම නතර වේ (වක්‍ර {0})", "p", 1),
    (r"opponent withdraws within ~(\d+) months", "මාස {0}ක් පමණ ඇතුළත ප්‍රතිවාදියා පසුබසී", "n", 0),
    (r"opponent arrives within ~(\d+) days", "දින {0}ක් පමණ ඇතුළත ප්‍රතිවාදියා පැමිණේ", "n", 0),
    (r"query concerns: (.+)", "ප්‍රශ්නය සම්බන්ධ වන්නේ: {0}", "q", 0),
    (r"person's age/type: (.+)", "පුද්ගලයාගේ වයස/ස්වභාවය: {0}", "a", 0),
]]


def _sh_fill(m, si, conv):
    return si.format(*[_SH_CONV[c](g or "") for c, g in zip(conv, m.groups())])


def si_shat_rule(rule):
    """A Shatpanchasika rule line in Sinhala (falls back to word-by-word for anything new)."""
    for rx, si, conv in SHAT_RULE_SI:
        m = rx.fullmatch(rule.strip())
        if m:
            return _sh_fill(m, si, conv)
    return si_text(rule)


def si_shat_verdict(verdict):
    """(Sinhala, tone) for a Shatpanchasika verdict; tone +1 favours the querent, -1 is against, 0 neither."""
    v = verdict.strip()
    if v in SHAT_VERDICT_SI:
        return SHAT_VERDICT_SI[v]
    for rx, si, conv, tone in SHAT_VERDICT_RX:
        m = rx.fullmatch(v)
        if m:
            return _sh_fill(m, si, conv), tone
    s = si_text(v)
    return s, (1 if any(w in s for w in POS_MARKS) and not any(w in s for w in NEG_MARKS) else -1 if any(w in s for w in NEG_MARKS) else 0)


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
            bits.append(f"<b>{matter} වන භාවය</b> ({HOUSE_PLAIN_SI[matter]}) සම්බන්ධ කාරක ග්‍රහයන් අතර <b>ඉථසාල</b> යෝගයක් ඇත — "
                        "කාරණය ඉටුවීමට නැඹුරු ප්‍රවණතාවක්.")
        elif "EESARPHA" in ml:
            bits.append(f"<b>{matter} වන භාවය</b> ({HOUSE_PLAIN_SI[matter]}) සම්බන්ධ කාරක ග්‍රහයන් අතර <b>ඊසර්ඵ</b> යෝගයක් ඇත — "
                        "කාරණය ලිස්සා යාමට හෝ ප්‍රමාද වීමට නැඹුරු ප්‍රවණතාවක්; අමතර උත්සාහයක් අවශ්‍ය විය හැක.")
        else:
            bits.append(f"<b>{matter} වන භාවය</b> සම්බන්ධ කාරක ග්‍රහයන් අතර ඉථසාල/ඊසර්ඵ යෝගයක් නැත — "
                        "තාජක ක්‍රමයෙන් මේ කාරණයට ශක්තිමත් ඇඟවීමක් නොලැබේ.")
    bits.append(f"තාජක යෝග: ඉථසාල {ith}ක්, ඊසර්ඵ {ees}ක් — "
                + ("ඉටුවීමේ ඇඟවීම් වැඩියි." if ith > ees else "ප්‍රමාද/බාධක ඇඟවීම් වැඩියි." if ees > ith else "දෙපැත්තම සමානයි."))
    sh = d.get("shatpanchasika") or []
    if sh:
        tones = [si_shat_verdict(r["verdict"])[1] for r in sh]
        pos, neg = tones.count(1), tones.count(-1)
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
    bits = [f"<b>{house} වන භාවය</b> ({SIGN_SI[hs]}) — {HOUSE_PLAIN_SI[house]}."]
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
        tag = "ඒරාෂ්ටක ශනි" if h in (12, 1, 2) else ("අෂ්ටම ශනි" if h == 8 else "අර්ධාෂ්ටම ශනි" if h == 4 else None)
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
                   "නිෂ්ප්‍රභ වීමේ නීති පරීක්ෂා කළ යුතුය.")
    else:
        verdict = (f"ලග්නයෙන් දෝෂයක් නැත; {', '.join(flagged)} අනුව පමණක් ලකුණක් ඇත — "
                   "එබැවින් මෘදු ලෙස සලකනු ලැබේ. පොරොන්දම් අවස්ථාවකදී තහවුරු කර ගන්න.")
    return ('<h3>කුජ (මංගල) දෝෂය</h3>'
            '<p class="small">කුජ ලග්නය, චන්ද්‍රයා සහ ශුක්‍ර යන තිදෙනාගෙන් 1, 2, 4, 7, 8, 12 '
            'භාවවල පිහිටීම සලකා බලයි.</p>'
            f'<table><tr><th style="width:34%">ගණන් ගන්නේ</th><th>කුජ</th><th>තත්ත්වය</th></tr>{rows}</table>'
            f'<p class="small">{esc(verdict)}</p>')


def sripati_block(d, P):
    """Sripati bhava chart (A2/A3): the 12 bhavas with madhya, span and planets, and the planets whose
    bhava differs from their rashi (whole-sign) house. Empty if the engine gave no Sripati data."""
    s = d.get("sripati")
    if not s:
        return ""
    pos_si = lambda lon: f"{SIGN_SI[int(lon // 30) % 12]} {dms(lon % 30)}"
    order = ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]
    rows = []
    for n in range(1, 13):
        inside = [PLANET_SI[c] for c in order if s["planet_bhava"].get(c) == n]
        rows.append(f"<tr><td>{n}</td><td>{pos_si(s['madhya'][n - 1])}</td>"
                    f"<td>{pos_si(s['sandhi'][n - 1])} – {pos_si(s['sandhi'][n % 12])}</td>"
                    f"<td>{', '.join(inside) or '—'}</td></tr>")
    moved = [f"{PLANET_SI[c]} ({P[c]['house']} → {s['planet_bhava'][c]})"
             for c in order if c in P and s["planet_bhava"].get(c) not in (None, P[c]["house"])]
    return ("<h3>ශ්‍රීපති භාව කේන්දරය</h3>"
            "<p class='small'>භාව මධ්‍ය ලග්නයෙන් සහ දශම භාවයෙන් (MC) ගණනය කෙරේ; භාව සන්ධි ඒවා අතර මැදයි. "
            "රාශි කේන්දරයේ භාවයට වඩා වෙනස් භාවයක සිටින ග්‍රහයන් පහත දැක්වේ.</p>"
            "<table><tr><th>භාවය</th><th>භාව මධ්‍යය</th><th>පරාසය (සන්ධියේ සිට සන්ධියට)</th><th>ග්‍රහයන්</th></tr>"
            + "".join(rows) + "</table>"
            + (f"<p class='small'><b>භාව චලනය (රාශි භාවය → ශ්‍රීපති භාවය):</b> {', '.join(moved)}</p>" if moved
               else "<p class='small'>සියලු ග්‍රහයන් රාශි කේන්දරයේ භාවයේම සිටී.</p>"))


SHADBALA_PARTS_SI = [("sthana", "ස්ථාන"), ("dig", "දිග්"), ("kala", "කාල"), ("chesta", "චේෂ්ට"),
                     ("naisargika", "නෛසර්ගික"), ("drik", "දෘක්")]


def shadbala_block(d):
    """Shadbala table (A2/A3): the six strengths in virupas, the total in rupas against the BPHS
    minimum, and which planets are strongest or below the minimum. Empty without engine data."""
    sb = d.get("shadbala")
    if not sb:
        return ""
    order = ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]
    part = lambda o, k: sum(o[k].values()) if isinstance(o[k], dict) else o[k]  # noqa: E731
    top = max(order, key=lambda p: sb[p]["ratio"])
    rows = "".join(
        f"<tr{' class=cur' if p == top else ''}><td>{PLANET_SI[p]}</td>"
        + "".join("<td>—</td>" if k == "chesta" and p in ("Su", "Mo") else f"<td>{part(sb[p], k):.1f}</td>"
                  for k, _ in SHADBALA_PARTS_SI)
        + f"<td><b>{sb[p]['rupas']:.2f}</b></td><td>{sb[p]['required']:g}</td><td><b>{sb[p]['ratio']:.2f}</b></td></tr>"
        for p in order)
    ranked = sorted(order, key=lambda p: -sb[p]["ratio"])
    weak = [p for p in order if sb[p]["ratio"] < 1]
    summary = (f"ශක්තිමත්ම ග්‍රහයන්: {', '.join(f'{PLANET_SI[p]} ({sb[p]['ratio']:.2f})' for p in ranked[:3])}. "
               + (f"අවම මට්ටමට වඩා අඩු: {', '.join(f'{PLANET_SI[p]} ({sb[p]['ratio']:.2f})' for p in weak)}."
                  if weak else "සියලු ග්‍රහයන් අවම ශක්ති මට්ටම ඉක්මවයි."))
    return ("<h3>ෂඩ්බල — ග්‍රහයන්ගේ ශක්තිය</h3>"
            "<p class='small'>ෂඩ්බලය ග්‍රහයෙකුගේ ශක්තිය මූලාශ්‍ර හයකින් මනී (විරූප වලින්; 60 විරූප = 1 රූප). "
            "අනුපාතය (එකතුව ÷ අවම) 1 හෝ ඊට වැඩි නම් ග්‍රහයාට තම ඵල දීමට ප්‍රමාණවත් ශක්තියක් ඇත. "
            "රවි සහ චන්ද්‍රගේ චේෂ්ට බලය කාල බලයේ අයන / පක්ෂ බලයට ඇතුළත් ය. "
            "ගණනය: බී.වී. රාමන්ගේ ක්‍රමය (බෘහත් පරාශර හෝරා ශාස්ත්‍රය 27).</p>"
            "<table><tr><th>ග්‍රහයා</th>" + "".join(f"<th>{si}</th>" for _, si in SHADBALA_PARTS_SI)
            + "<th>එකතුව (රූප)</th><th>අවම</th><th>අනුපාතය</th></tr>" + rows + "</table>"
            f"<p class='small'>{summary}</p>")


def kp_block(d):
    """KP (Krishnamurti Paddhati) section for A3: cusps and planets with their star and sub lords,
    the significators of each house (strongest first) and the ruling planets of the birth moment."""
    kp = d.get("kp")
    if not kp:
        return ""
    pos_si = lambda lon: f"{SIGN_SI[int(lon // 30) % 12]} {dms(lon % 30)}"  # noqa: E731
    cusp_rows = "".join(f"<tr><td>{h}</td><td>{pos_si(c['lon'])}</td><td>{PLANET_SI[c['lords'][0]]}</td>"
                        f"<td>{PLANET_SI[c['lords'][1]]}</td><td><b>{PLANET_SI[c['lords'][2]]}</b></td></tr>"
                        for h, c in enumerate(kp["cusps"], 1))
    planet_rows = "".join(f"<tr><td>{PLANET_SI[p]}</td><td>{pos_si(v['lon'])}</td><td>{v['house']}</td>"
                          f"<td>{PLANET_SI[v['lords'][1]]}</td><td>{PLANET_SI[v['lords'][2]]}</td></tr>"
                          for p, v in kp["planets"].items())
    sig_rows = []
    for h, s in kp["significators"].items():
        ranked = list(dict.fromkeys(s["L1"] + s["L2"] + s["L3"] + s["L4"]))
        sig_rows.append(f"<tr><td>{h}</td><td>{HOUSE_AREA_SI[int(h)]}</td>"
                        f"<td>{', '.join(PLANET_SI[p] for p in ranked)}</td></tr>")
    rp = kp["ruling_planets"]
    ruling = (f"දින අධිපති {PLANET_SI[rp['day_lord']]} · චන්ද්‍ර: රාශි {PLANET_SI[rp['moon_sign_lord']]}, "
              f"නැකත් {PLANET_SI[rp['moon_star_lord']]}, උප {PLANET_SI[rp['moon_sub_lord']]} · "
              f"ලග්නය: රාශි {PLANET_SI[rp['lagna_sign_lord']]}, නැකත් {PLANET_SI[rp['lagna_star_lord']]}, "
              f"උප {PLANET_SI[rp['lagna_sub_lord']]}")
    return ("<h3>KP — කෘෂ්ණමූර්ති පද්ධතිය</h3>"
            "<p class='small'>KP ක්‍රමය ප්ලැසිඩස් භාව සන්ධි සහ කෘෂ්ණමූර්ති අයනාංශය "
            f"({dms(kp['ayanamsa'])}) යොදා ගනී; සෑම සන්ධියක්ම එම භාවයේ ආරම්භයයි. නැකත් විම්ශෝත්තරී "
            "දශා අනුපාතයට කොටස් නවයකට බෙදූ විට ලැබෙන උප අධිපති, භාවයක ප්‍රතිඵලය තීරණය කිරීමේදී ප්‍රධාන වේ.</p>"
            "<table><tr><th>භාවය</th><th>සන්ධිය</th><th>රාශි අධිපති</th><th>නැකත් අධිපති</th><th>උප අධිපති</th></tr>"
            + cusp_rows + "</table>"
            "<table><tr><th>ග්‍රහයා</th><th>ස්ථානය</th><th>භාවය</th><th>නැකත් අධිපති</th><th>උප අධිපති</th></tr>"
            + planet_rows + "</table>"
            "<p class='small'><b>භාව කාරකයන්</b> (ශක්තිමත්ම මුලින්: භාවයේ සිටින ග්‍රහයන්ගේ නැකතේ සිටින ග්‍රහයන්, "
            "භාවයේ සිටින ග්‍රහයන්, භාවාධිපතිගේ නැකතේ සිටින ග්‍රහයන්, භාවාධිපති)</p>"
            "<table><tr><th>භාවය</th><th>කාරණය</th><th>කාරක ග්‍රහයන්</th></tr>" + "".join(sig_rows) + "</table>"
            f"<p class='small'><b>පාලක ග්‍රහයන් (උපත් මොහොතේ):</b> {ruling}</p>")


# ---------------------------------------------------------------- plain words for A2/A3 and B1–B8
# Terms these reports use beyond the shared GLOSSARY_SI, one line each on the glossary page (the
# technical tables explain their own terms in the line under them).
GLOSS_TERMS_AB = {
    "භාවාධිපති": "භාවයේ රාශියට අධිපති ග්‍රහයා; එය සිටින තැන භාවයට බලපායි.",
    "කාරකයා": "එක් කාරණයක් ස්වභාවයෙන් පෙන්වන ග්‍රහයා — උදා: විවාහයට ශුක්‍ර.",
    "ආරූඪය (AL, UL…)": "ලෝකයාට ඔබ හෝ ඔබේ ජීවිතයේ කාරණයක් පෙනෙන ආකාරය.",
    "වර්ග කේන්දර (D9, D10…)": "රාශි කුඩා කොටස්වලට බෙදා, එක් ක්ෂේත්‍රයක් බලන අමතර කේන්දර.",
    "අෂ්ටකවර්ග (SAV)": "ග්‍රහයන් රාශිවලට දෙන ශුභ ලකුණු; SAV 28ට වැඩි = හොඳ.",
    "ශුභ / පාප ග්‍රහයන්": "මෘදු ග්‍රහයන් (ගුරු, ශුක්‍ර) ශුභ; දැඩි ග්‍රහයන් (ශනි, කුජ) පාප.",
}
GLOSS_A2_AB = ["කාරකයා", "ආරූඪය (AL, UL…)"]
GLOSS_A3_AB = ["කාරකයා", "ශුභ / පාප ග්‍රහයන්"]  # A3 explains ආරූඪය in its arudha line
GLOSS_B_AB = ["භාවාධිපති", "කාරකයා", "ආරූඪය (AL, UL…)", "වර්ග කේන්දර (D9, D10…)", "අෂ්ටකවර්ග (SAV)"]
GLOSS_B_SHARED_AB = ["ලග්නය", "රාශිය", "භාවය", "නැකත සහ පාදය", "මහා දශාව / අන්තර් දශාව", "ගෝචරය", "වක්‍ර (ව)",
                     "උච්ච / නීච / ස්වක්ෂේත්‍ර", "යෝගය / දෝෂය", "ඒරාෂ්ටක ශනි (සඩේ සති)"]
# B reports: the life area in plain words, and what the area's karaka planet stands for here
B_PLAIN_AB = {"B1": ("ඔබේ විවාහය සහ සහකරු", "ආදරය සහ විවාහය"),
              "B2": ("ඔබේ රැකියාව සහ ව්‍යාපාර කටයුතු", "මහන්සිය සහ වෘත්තිය"),
              "B3": ("ඔබේ අධ්‍යාපනය සහ ඉගෙනීම", "බුද්ධිය සහ ඉගෙනීම"),
              "B4": ("ඔබේ මුදල්, ආදායම සහ ඉතිරි කිරීම", "ධනය සහ වාසනාව"),
              "B5": ("දරුවන්", "දරුවන් සහ ප්‍රඥාව"),
              "B6": ("විදේශ ගමන්, විදේශ අධ්‍යාපනය සහ පදිංචිය", "විදේශ සහ අලුත් අත්දැකීම්"),
              "B7": ("ඔබේ නිවස, ඉඩම් සහ වාහන", "ඉඩකඩම් සහ දේපල"),
              "B8": ("ඔබේ දෙමව්පියන් සමඟ සම්බන්ධතාව", "මව සහ සිතේ සැනසීම")}
CK_ROLE_AB = {"AK": "ඔබේ ආත්මය සහ ජීවිත ඉලක්ක", "AmK": "වෘත්තිය", "MK": "මව", "PiK": "පියා", "PK": "දරුවන්", "DK": "සහකරු"}


def gloss_disc_ab(terms, extra_keys, method_line):
    """The glossary page, then the method and disclaimer on that same page (disclaimer_block without its page break)."""
    return ('<div class="pb"></div><h2>වචන කිහිපයක තේරුම</h2>'
            + glossary_html(terms, [(k, GLOSS_TERMS_AB[k]) for k in extra_keys])
            + disclaimer_block(method_line).replace('<div class="pb"></div>', "", 1))


def plain_a2_ab(d, a, now_local, tr):
    """A2/A3's 'in simple words' box: the shared natal summary, plus the chart's strongest planet (Shadbala)."""
    box = plain_summary_si(d, a, now_local, tr)
    sb = d.get("shadbala")
    if sb:
        top = max(["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"], key=lambda p: sb[p]["ratio"])
        li = (f"<li><b>ඔබේ ශක්තිමත්ම ග්‍රහයා:</b> {PLANET_SI[top]}. {', '.join(PLANET_NATURE_SI[top].split(', ')[:3])} "
              "සම්බන්ධ කාරණා ඔබේ ජීවිතයේ ශක්තිමත් පැත්තයි.</li>")
        last = "<li>මේවා ප්‍රවණතා පමණි"
        box = box.replace(last, li + last, 1) if last in box else box.replace("</ul></div>", li + "</ul></div>", 1)
    return box


def plain_b_ab(d, a, code, tr, now_local):
    """B1–B8's 'in simple words' box: what this chart says about the report's life area, in everyday words."""
    spec = B_SPECS[code]
    area, role = B_PLAIN_AB[code]
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    h, kar = spec["house"], spec["karaka"]
    hs = (ls + h - 1) % 12
    hlord = jc.SIGN_LORD[hs]
    lh = P[hlord]["house"]
    L = [f"<li><b>මේ වාර්තාව:</b> {area} ගැනයි. ඒ සඳහා ප්‍රධාන වශයෙන් බලන්නේ ඔබේ කේන්දරයේ "
         f"{h} වන භාවයයි ({HOUSE_PLAIN_SI[h]}).</li>"]
    if lh == h:
        L.append(f"<li><b>භාවයේ අධිපති ග්‍රහයා:</b> {PLANET_SI[hlord]} තමන්ගේම භාවයේ සිටී — එය මේ ක්ෂේත්‍රයට ශක්තියකි.</li>")
    else:
        good = lh in (1, 4, 5, 7, 9, 10, 11) and "නීච" not in si_dignity(P[hlord]["dignity"])
        L.append(f"<li><b>භාවයේ අධිපති ග්‍රහයා:</b> {PLANET_SI[hlord]}, ඔබේ කේන්දරයේ {lh} වන භාවයේ ({HOUSE_AREA_SI[lh]}) සිටී. "
                 f"එනිසා මේ ක්ෂේත්‍රය {HOUSE_AREA_SI[lh]} සමඟ බැඳී පවතී — "
                 + ("එය හිතකර ස්ථානයකි." if good else "මෙහි ප්‍රතිඵල ඉවසීමෙන් සහ උත්සාහයෙන් ලැබේ.") + "</li>")
    dg, kh = si_dignity(P[kar]["dignity"]), P[kar]["house"]
    where = f"{kh} වන භාවයේ ({HOUSE_AREA_SI[kh]})"
    if "නීච භංග" in dg:
        kst = f"{where} දුර්වල රාශියක සිටියත්, එම දුර්වලකම අඩු කරන තත්ත්වයක් (නීච භංග) ඇත"
    elif "නීච" in dg:
        kst = f"{where} දුර්වල රාශියක සිටී — එනිසා මේ ක්ෂේත්‍රයට වැඩි ඉවසීමක් සහ උත්සාහයක් අවශ්‍යයි"
    elif any(w in dg for w in ("උච්ච", "ස්වක්ෂේත්‍ර", "මූලත්‍රිකෝණ")):
        kst = f"{where} ශක්තිමත්ව සිටී — මේ ක්ෂේත්‍රයට හොඳ ලකුණකි"
    else:
        kst = f"{where} සිටී"
    if P[kar].get("combust"):
        kst += "; සූර්යයාට ළං වී (අස්තංගත වී) ඇති නිසා එහි ඵල ටිකක් ප්‍රමාද විය හැක"
    L.append(f"<li><b>{PLANET_SI[kar]}</b> ({role} පෙන්වන ග්‍රහයා) ඔබේ කේන්දරයේ {kst}.</li>")
    av = d.get("ashtakavarga")
    if av:
        n = av["sav"][hs]
        L.append(f"<li><b>ශක්ති ලකුණු:</b> අෂ්ටකවර්ග ක්‍රමයට මේ භාවයට ලකුණු {n}ක් ලැබී ඇත — "
                 + ("සාමාන්‍යය (28) හෝ ඊට වැඩි නිසා මේ ක්ෂේත්‍රය ස්වභාවයෙන්ම ශක්තිමත්." if n >= 28
                    else "සාමාන්‍යයට (28) වඩා අඩු නිසා මෙහි ප්‍රතිඵලවලට වැඩි උත්සාහයක් අවශ්‍ය විය හැක.") + "</li>")
    # the same dasha windows as the report's section 5 (house lord, karaka, chara karakas, first two support lords)
    key = {hlord, kar} | {d["chara_karakas"][k]["planet"] for k in spec["ck"] if k in d["chara_karakas"]}
    key |= {jc.SIGN_LORD[(ls + x - 1) % 12] for x in spec["support"][:2]}
    now_utc = now_local.astimezone(timezone.utc)
    horizon = now_utc + timedelta(days=int(7 * 365.25))
    spans = []
    for m in d["vimshottari"]["mahadashas"]:
        for s_ in m.get("sub", []):
            st, en = datetime.fromisoformat(s_["start"]), datetime.fromisoformat(s_["end"])
            if en > now_utc and st < horizon and (m["lord"] in key or s_["lord"] in key):
                if spans and (st - spans[-1][1]).total_seconds() < 2 * 86400:
                    spans[-1][1] = en
                else:
                    spans.append([st, en])
    ym = lambda x: x.astimezone(ZoneInfo(a.tz)).strftime("%Y-%m")  # noqa: E731
    if spans:
        parts = [f"{ym(max(s0, now_utc))} සිට {ym(s1)} දක්වා" + (" (දැන් ගත වන කාලය)" if s0 <= now_utc else "")
                 for s0, s1 in spans[:3]]
        tl = ("<li><b>වැදගත් කාල:</b> ඉදිරි වසර 7 තුළ මේ ක්ෂේත්‍රයේ කාරණා ඉස්මතු වීමට ඉඩ ඇති දශා කාල — "
              + "; ".join(parts) + ".")
    else:
        tl = ("<li><b>වැදගත් කාල:</b> ඉදිරි වසර 7 තුළ මේ ක්ෂේත්‍රයට කෙලින්ම සම්බන්ධ දශා කාලයක් නැත; "
              "ග්‍රහ ගමන් (ගෝචරය) කොටස බලන්න.")
    if tr["Ju"]["from_lagna"] in [h] + spec["support"]:
        tl += f" දැන් ගුරු ලග්නයෙන් {tr['Ju']['from_lagna']} වැන්නේ ගමන් කිරීමද මේ ක්ෂේත්‍රයට හිතකරයි."
    L.append(tl + "</li>")
    L.append("<li>මේවා ප්‍රවණතා පමණි — ඔබේ උත්සාහය සහ හොඳ තීරණ ඊටත් වඩා වැදගත්.</li>")
    return '<div class="box plain"><div class="lbl">සරලව කිවහොත්</div><ul>' + "".join(L) + "</ul></div>"


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
    H = [f'''<div class="cover" style="padding-top:12mm">{LOGO_IMG}<div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
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
    H.append(plain_a2_ab(d, a, now_local, tr))
    H.append(f'<p class="small muted"><b>ජ්‍යොතිෂ කෙටි සටහන:</b> {SIGN_SI[ls]} ලග්නය; ලග්නාධිපති {PLANET_SI[lord]} {P[lord]["house"]} වැන්නේ. '
             f'චන්ද්‍ර {SIGN_SI[moon["sign_idx"]]} ({NAK_SI[jc.NAKSHATRAS.index(moon["nakshatra"])]}), {moon["house"]} වැන්නේ. '
             + (f'වත්මන් දශාව {PLANET_SI[md["lord"]]}' + (f"/{PLANET_SI[ad['lord']]}" if ad else "") + ". " if md else "")
             + f'ශනි ගෝචරය: {tr["sade_sati"] if tr["sade_sati"] != "නැත" else "ඒරාෂ්ටක / අෂ්ටම ශනි නැත"}.</p>')
    H.append(note_block(notes, "summary"))
    if approx:
        H.append('<div class="note"><div class="lbl">උපන් වේලාව ගැන</div><p>උපන් වේලාව ආසන්න බැවින් D1, දශා සහ ගෝචරය ප්‍රමුඛ කර ඇත; '
                 'සියුම් වර්ග (D9, D10, D24, D60) ලග්න මිනිත්තු කිහිපයකින් වෙනස් විය හැක. නිශ්චිත වේලාවක් සොයා ගැනීමට E1 (ජන්ම කාල ශුද්ධි) වාර්තාව උපකාරී වේ.</p></div>')
    birth_rows = [("නම", a.name), ("උපන් දිනය", a.date), ("උපන් වේලාව", f"{a.time} ({'නිශ්චිත' if not approx else 'ආසන්න'})"),
                  ("ස්ථානය", a.place or "—"), ("අක්ෂාංශ / දේශාංශ", latlon_txt(a.lat, a.lon)),
                  ("කාල කලාපය", f"{a.tz} (UTC{utc_offset_txt(d['birth']['utc_offset'])})"), ("අයනාංශය", f"ලාහිරි {dms(d['ayanamsa'])} (රාශි චක්‍රය ගණන් කරන ආරම්භක ලක්ෂ්‍යය)"),
                  ("පංචාංගය", f"{pch_si(d['panchanga'])['vara']} · {pch_si(d['panchanga'])['tithi']} · {pch_si(d['panchanga'])['yoga']} යෝග · {pch_si(d['panchanga'])['karana']} කරණ · හිරු උදාව {d['panchanga']['sunrise']}"),
                  ("වාර්තා දිනය", now_local.strftime("%Y-%m-%d"))]
    H.append("<h2>2. උපන් දත්ත</h2><table>" + "".join(f"<tr><td style='width:34%'><b>{k}</b></td><td>{esc(v)}</td></tr>" for k, v in birth_rows) + "</table>")

    # ---- 3 planets
    H.append(time_sensitivity_html(a))
    H.append('<p class="small muted">වගුව කියවන හැටි: ✓ = වේලාව ටිකක් වෙනස් වුවත් වෙනස් නොවේ; ⚠ = වෙනස් විය හැක — ප්‍රවේශමෙන් කියවන්න.</p>')
    H.append("<h2>3. ග්‍රහ ස්ථාන (D1)</h2>")
    prow = []
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        p = P[c]
        prow.append(f"<tr><td>{PLANET_SI[c]}</td><td>{SIGN_SI[p['sign_idx']]}</td><td>{dms(p['deg_in_sign'])}</td><td>{p['house']}</td>"
                    f"<td>{NAK_SI[jc.NAKSHATRAS.index(p['nakshatra'])]} {p['pada']}</td>"
                    f"<td>{'වක්‍ර ' if p['retro'] and c not in ('Ra', 'Ke') else ''}{'අස්තංගත ' if p.get('combust') else ''}{si_dignity(p['dignity']) if si_dignity(p['dignity']) != '—' else ''}</td>"
                    f"<td>{PLANET_NATURE_SI[c].split(',')[0] if c in PLANET_NATURE_SI else ''}</td></tr>")
    H.append("<table><tr><th>ග්‍රහයා</th><th>රාශිය</th><th>අංශක</th><th>භාවය</th><th>නැකත</th><th>තත්ත්වය</th><th>කාරකත්වය</th></tr>" + "".join(prow) + "</table>")
    H.append('<p class="small muted">වගුව කියවන හැටි: <b>භාවය</b> = ග්‍රහයා බලපාන ජීවිත ක්ෂේත්‍රය (1–12); <b>වක්‍ර</b> = පසුපසට යන ලෙස පෙනෙන කාලය; '
             '<b>උච්ච</b> = ඉතා ශක්තිමත්, <b>නීච</b> = දුර්වල, <b>ස්වක්ෂේත්‍ර</b> = තමන්ගේම රාශිය; <b>අස්තංගත</b> = සූර්යයාට ළං වී බලය අඩු වීම; '
             '<b>කාරකත්වය</b> = ග්‍රහයාගේ ප්‍රධාන කාරණය.</p>')
    sl = d.get("special_lagnas", {})
    if sl:
        H.append("<p class='small'><b>විශේෂ ලග්න</b> (HL = හෝරා ලග්නය — ධනය · GL = ඝටී ලග්නය — බලය සහ තනතුර · SL = ශ්‍රී ලග්නය — සමෘද්ධිය): " + " · ".join(
            f"{k} {SIGN_SI[inv[v['sign']]]}" for k, v in sl.items() if isinstance(v, dict)) + "</p>")
    sp_ab = sripati_block(d, P)
    H.append(sp_ab + ('<p class="small muted">වගුව කියවන හැටි: සන්ධි උපන් වේලාව අනුව ගණනය වේ; භාවය මාරු වූ ග්‍රහයා නව භාවයේ ඵලද දෙයි.</p>'
                      if sp_ab else ""))
    H.append(note_block(notes, "lagna"))

    # ---- 4 Jaimini
    kk, ar = d["chara_karakas"], d["arudhas"]
    H.append("<h2>4. ජෛමිනි ස්තරය</h2><p class='small'>ජෛමිනි ක්‍රමයේදී අංශක අනුව එක් එක් ග්‍රහයාට එක් ජීවිත කාරණයක් ලැබේ "
             "(වැඩිම අංශක = AK).</p><table><tr><th>කාරකය</th><th>ග්‍රහයා</th><th>භාවය</th><th>අර්ථය</th></tr>")
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
    H.append('<p class="small muted">ආරූඪය = ලෝකයාට කාරණයක් පෙනෙන ආකාරය: AL = සමාජය ඔබ දකින ආකාරය · UL = සහකරු සහ විවාහය · '
             'A7 = හවුල්කරුවන් · A10 = රැකියාව' + ('; අනෙක් ඒවා (A2–A12) එම අංකයේ භාවයයි.' if deep else '.') + '</p>')

    # ---- 5 vargas
    H.append('<h2 class="sec">5. වර්ග කේන්දර</h2>')
    H.append('<p class="small">වර්ග කේන්දර = රාශි කුඩා කොටස්වලට බෙදා එක් ක්ෂේත්‍රයක් බලන අමතර කේන්දර (D9 විවාහය, D10 රැකියාව).</p>')
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
                 + (f' වර්ගෝත්තම: {", ".join(pl_si(x) for x in d.get("vargottama", []))}.' if vname == "D9" and d.get("vargottama") else "")
                 + "</p></div></div>")

    # ---- 6 yogas
    H.append('<h2 class="sec">6. යෝග සහ දෝෂ</h2>')
    H.append('<p class="small">යෝග = විශේෂ ග්‍රහ සංයෝග; දෝෂ = සැලකිලිමත් විය යුතු සංයෝග. ඵල ලැබෙන්නේ අදාළ දශාවලදී; '
             'බොහෝ දෝෂ වෙනත් ග්‍රහ ස්ථාන නිසා අඩු වේ හෝ නැති වේ.</p>')
    yf = d.get("yogas_full")
    if yf and deep:
        cat = None
        H.append("<table><tr><th style='width:22%'>වර්ගය</th><th style='width:26%'>යෝගය</th><th>විස්තරය</th></tr>")
        for y in yf:
            csi = YOGA_CAT_SI.get(y["category"], y["category"])
            H.append(f"<tr><td>{csi if csi != cat else ''}</td><td>{esc(si_yoga_name(y['name']))}</td><td>{esc(si_text(y['detail']))}</td></tr>")
            cat = csi
        H.append("</table>")
        H.append('<p class="small muted">වගුව කියවන හැටි: “විස්තරය” = යෝගය සෑදෙන හේතුව. සමහර පැරණි නම් බිය ගෙන දෙන සුළු වුවත්, '
                 'තනි යෝගයක් ප්‍රතිඵල තීරණය නොකරයි.</p>')
    else:
        yl = []
        for y in d.get("yoga_indications", []):
            key = next((k for k in YOGA_SI if k.lower() in y.lower()), None)
            why = si_yoga_why(y)
            yl.append(f"<li><b>{esc(YOGA_SI[key].split(' — ')[0]) if key else esc(si_text(y))}</b>"
                      + (f" — {esc(YOGA_SI[key].split(' — ', 1)[1])}" if key and " — " in YOGA_SI[key] else "")
                      + (f' <span class="muted">({esc(why)})</span>' if why else "") + "</li>")
        for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]:
            dg = si_dignity(P[c]["dignity"])
            if "උච්ච" in dg or "නීච" in dg:
                yl.append(f"<li>{PLANET_SI[c]} {dg} ({SIGN_SI[P[c]['sign_idx']]}, {P[c]['house']} වැන්න) — {PLANET_NATURE_SI[c]}</li>")
        H.append("<ul>" + ("".join(yl) or "<li>ප්‍රධාන යෝග/දෝෂ ඇඟවීම් නැත.</li>") + "</ul>")
    H.append(mangal_dosha_html(d))
    H.append('<p class="small muted">කුජ දෝෂය බලන්නේ පොරොන්දම් ගලපන විට පමණි; එය බොහෝ විට නිෂ්ප්‍රභ වේ (බලය නැති වේ).</p>')
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
        H.append("<p class='small muted'>වගුව කියවන හැටි: අෂ්ටකවර්ග = ග්‍රහයන් හත සහ ලග්නය රාශිවලට දෙන ශුභ ලකුණු; "
                 "SAV = එකතුව (සාමාන්‍යය 28). ලකුණු වැඩිම භාව: "
                 + ", ".join(f"{jc.house_from(ls, i)} ({HOUSE_AREA_SI[jc.house_from(ls, i)]})" for i in best) + "."
                 + (" BAV පේළි 0–8; 4ට වැඩි = හොඳ." if deep else "") + "</p>")
    sb_ab = shadbala_block(d)
    H.append(sb_ab + ('<p class="small muted">වගුව කියවන හැටි: වැදගත්ම තීරුව “අනුපාතය” — 1ට වැඩි = ශක්තිමත්; 1ට අඩු = එම ග්‍රහයාගේ කාරණාවලට '
                      'වැඩි උත්සාහයක්. කොටස්: ස්ථාන (පිහිටීම), දිග් (දිශාව), කාල (වේලාව), චේෂ්ට (චලනය), නෛසර්ගික (ස්වභාවික), '
                      'දෘක් (දෘෂ්ටිය).</p>' if sb_ab else ""))

    # ---- 8 argala / upagrahas (A3)
    if deep:
        H.append('<h2>8. අර්ගල, උපග්‍රහ සහ KP පද්ධතිය</h2>')
        arg = d.get("argala", {})
        rows = []
        for h in range(1, 13):
            g = arg.get(str(h)) or arg.get(h)
            if not g:
                continue
            sub = ", ".join(PLANET_SI[p] for p, _ in g["subha"]) or "—"
            pap = ", ".join(PLANET_SI[p] for p, _ in g["papa"]) or "—"
            vir = ", ".join(PLANET_SI[p] for p, _, _b in g["virodha"]) or "—"
            rows.append(f"<tr><td>{h}</td><td>{HOUSE_AREA_SI[h]}</td><td>{sub}</td><td>{pap}</td><td>{vir}</td></tr>")
        H.append("<table><tr><th>භාවය</th><th>කාරණය</th><th>ශුභ අර්ගල</th><th>පාප අර්ගල</th><th>විරෝධාර්ගල</th></tr>" + "".join(rows) + "</table>")
        H.append('<p class="small muted">වගුව කියවන හැටි: අර්ගල = 2, 4, 11 වැනි භාවවල ග්‍රහයන් මේ භාවයට කරන බලපෑම — <b>ශුභ අර්ගල</b> උදව්වකි, '
                 '<b>පාප අර්ගල</b> උත්සාහය ඉල්ලයි; <b>විරෝධාර්ගල</b> (12, 10, 3 සිට) එම බලපෑම අඩු කරයි.</p>')
        up = d.get("upagrahas", {})
        if up:
            H.append("<h3>උපග්‍රහ</h3><table><tr><th>උපග්‍රහයා</th><th>රාශිය</th><th>අංශක</th><th>භාවය</th></tr>"
                     + "".join(f"<tr><td>{UPAGRAHA_SI.get(k, k)}</td><td>{SIGN_SI[jc.sign_of(v)]}</td><td>{dms(v % 30)}</td>"
                               f"<td>{jc.house_from(ls, jc.sign_of(v))}</td></tr>" for k, v in up.items()) + "</table>")
            H.append('<p class="small muted">උපග්‍රහ = රවිගේ පිහිටීම හෝ දිනයේ කාලය අනුව ගණනය කරන ගණිත ලක්ෂ්‍ය, සැබෑ ග්‍රහයන් නොවේ; '
                     'පාප ලක්ෂ්‍ය ලෙස සැලකේ, ගුලික/මාන්දි ශනි වැනිය. නම් පැරණි සම්ප්‍රදායික නම් පමණි — බිය විය යුතු නැත.</p>')
        kp_ab = kp_block(d)
        H.append(kp_ab + ('<p class="small muted">වගු කියවන හැටි: KP (කෘෂ්ණමූර්ති ක්‍රමය) කාල නිර්ණයට යොදයි. භාවයක ප්‍රතිඵලය තීරණය කරන්නේ '
                          'තද අකුරින් ඇති උප අධිපති; මුලින් ඇති කාරක ග්‍රහයන්ගේ දශාවලදී එම භාවයේ කාරණා සිදුවීමට ඉඩ වැඩියි.</p>' if kp_ab else ""))

    # ---- 9 life areas
    H.append('<h2 style="page-break-before:auto">' + ("9" if deep else "8") + '. ජීවන ක්ෂේත්‍ර</h2>')
    H.append('<p class="small">එක් එක් ක්ෂේත්‍රයට භාවය, එහි අධිපති, කාරකයා සහ වර්ග කේන්දරය; අවසාන <b>ප්‍රවණතාව</b> සරල නිගමනයයි.</p>')
    for k in ["career", "marriage", "wealth", "education", "family"]:
        t, para = area_paragraph(d, k)
        H.append(f"<h3>{t}</h3><p>{para}</p>")
    H.append(note_block(notes, "areas") or note_block(notes, "lagna2"))

    # ---- 10 dashas
    n = "10" if deep else "9"
    H.append(f'<h2 class="sec">{n}. දශා</h2>')
    H.append('<p class="small muted">දශා = ජීවිතය ග්‍රහයන්ට බෙදූ කාල; ඒ ග්‍රහයා සිටින භාවයේ කාරණා එම කාලයේ ඉස්මතු වේ.</p>')
    if md:
        L = md["lord"]
        H.append(f'<p>වත්මන් මහා දශාව <b>{PLANET_SI[L]}</b> ({fmt_date(md["start"], tz)} – {fmt_date(md["end"], tz)}): {PLANET_NATURE_SI[L]}; '
                 f'ජන්ම කේන්දරයේ {SIGN_SI[P[L]["sign_idx"]]} රාශියේ {P[L]["house"]} වැන්නේ ({HOUSE_PLAIN_SI[P[L]["house"]]}).'
                 + (f' වත්මන් අන්තර් දශාව <b>{PLANET_SI[ad["lord"]]}</b> ({fmt_date(ad["start"], tz)} – {fmt_date(ad["end"], tz)})'
                    f' — {P[ad["lord"]]["house"]} වැන්න: {HOUSE_AREA_SI[P[ad["lord"]]["house"]]} — '
                    f'{period_tone_si(P, ad["lord"])}.' if ad else "")
                 + (f' ප්‍රත්‍යන්තර {PLANET_SI[pd_["lord"]]} ({fmt_date(pd_["start"], tz)} – {fmt_date(pd_["end"], tz)}).' if pd_ else "") + "</p>")
    horizon = now_utc + timedelta(days=int((10 if deep else 5) * 365.25))
    rows = []
    for m in vim["mahadashas"]:
        for s_ in m.get("sub", []):
            st, en = datetime.fromisoformat(s_["start"]), datetime.fromisoformat(s_["end"])
            if en > now_utc and st < horizon:
                tone = "හිතකර" if P[s_["lord"]]["house"] in (1, 2, 4, 5, 7, 9, 10, 11) and "නීච" not in si_dignity(P[s_["lord"]]["dignity"]) else "සැලකිලිමත් වන්න"
                rows.append(f"<tr{' class=cur' if st <= now_utc < en else ''}><td>{PLANET_SI[m['lord']]}/{PLANET_SI[s_['lord']]}</td>"
                            f"<td>{st.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</td><td>{en.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</td>"
                            f"<td>{PLANET_SI[s_['lord']]} {P[s_['lord']]['house']} වැන්නේ — {HOUSE_AREA_SI[P[s_['lord']]['house']]} ({tone})</td></tr>")
    H.append(f"<h3>ඉදිරි වසර {10 if deep else 5} — අන්තර් දශා</h3><table><tr><th>දශාව</th><th>ආරම්භය</th><th>අවසානය</th><th>ප්‍රවණතාව</th></tr>" + "".join(rows) + "</table>")
    H.append('<p class="small muted">වගුව කියවන හැටි: “ගුරු/ශනි” = ගුරු මහා දශාව තුළ ශනි අන්තර් දශාව; පාට කළ පේළිය දැන් ගත වන කාලයයි.</p>')
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
        H.append('<p class="small muted">වගුව කියවන හැටි: කාල රාශිවලට අයත්ය; “ලග්නයෙන් භාවය” = එම කාලයේ ඉස්මතු වන ක්ෂේත්‍රය.</p>')
    if deep and d.get("kalachakra"):
        kc = d["kalachakra"]
        H.append(f"<h3>කාලචක්‍ර දශා</h3><p class='small'>චන්ද්‍ර නැකත් පාදය අනුව රාශි අනුපිළිවෙළකට කාලය බෙදන පැරණි ක්‍රමයකි (තහවුරු කිරීමට). "
                 f"චන්ද්‍ර {NAK_SI[jc.NAKSHATRAS.index(kc['nakshatra'])]} නැකතේ {kc['pada']} වන පාදයේ; "
                 f"දේහ රාශිය (ශරීරය) {SIGN_SI[inv[kc['deha']]]}, ජීව රාශිය (ජීවය) {SIGN_SI[inv[kc['jeeva']]]}.</p>"
                 "<table><tr><th>රාශිය</th><th>ආරම්භය</th><th>අවසානය</th></tr>"
                 + "".join(f"<tr{' class=cur' if datetime.fromisoformat(x['start']) <= now_utc < datetime.fromisoformat(x['end']) else ''}>"
                           f"<td>{SIGN_SI[inv[x['sign']]]}</td><td>{fmt_date(x['start'], tz)}</td><td>{fmt_date(x['end'], tz)}</td></tr>"
                           for x in kc["dasas"][:8]) + "</table>")
    H.append(note_block(notes, "dasha"))

    # ---- 11 gochara
    n2 = "11" if deep else "10"
    H.append(f'<h2>{n2}. ගෝචරය</h2>')
    H.append('<p class="small">සෙමින් යන ශනි, ගුරු, රාහුගෙන් ඉදිරි ප්‍රවණතා කියවේ; “චන්ද්‍රගෙන් 4” = චන්ද්‍ර රාශියේ සිට 4 වැනි රාශිය.</p>')
    sa, ju, ra = tr["Sa"], tr["Ju"], tr["Ra"]
    H.append(f'<p class="small muted">{now_local.strftime("%Y-%m-%d")} දිනට</p><ul>'
             f'<li><b>ශනි</b> {SIGN_SI[sa["sign"]]}{" (වක්‍ර)" if sa["retro"] else ""} — චන්ද්‍රගෙන් {sa["from_moon"]}, ලග්නයෙන් {sa["from_lagna"]}: {SATURN_FROM_MOON_SI[sa["from_moon"]]}</li>'
             f'<li><b>ගුරු</b> {SIGN_SI[ju["sign"]]}{" (වක්‍ර)" if ju["retro"] else ""} — චන්ද්‍රගෙන් {ju["from_moon"]}, ලග්නයෙන් {ju["from_lagna"]}: {JUPITER_FROM_MOON_SI[ju["from_moon"]]}</li>'
             f'<li><b>රාහු–කේතු</b> {SIGN_SI[ra["sign"]]}–{SIGN_SI[(ra["sign"] + 6) % 12]} — ලග්නයෙන් {ra["from_lagna"]}/{(ra["from_lagna"] + 5) % 12 + 1} වැනි භාව '
             f'({HOUSE_AREA_SI[ra["from_lagna"]]} / {HOUSE_AREA_SI[(ra["from_lagna"] + 5) % 12 + 1]}): අලුත් අභිලාශ හෝ අනපේක්ෂිත වෙනස්කම්</li>'
             f'<li><b>ඒරාෂ්ටක / අෂ්ටම ශනි</b>: {tr["sade_sati"]}</li></ul>')
    if av:
        sav = av["sav"]
        H.append("<p class='small'><b>අෂ්ටකවර්ග බින්දු ගෝචර ග්‍රහයන්ට:</b> "
                 + " · ".join(f"{PLANET_SI[c]} {SIGN_SI[tr[c]['sign']]} = {sav[tr[c]['sign']]}" for c in ["Sa", "Ju"]) + " (SAV; 28ට වැඩි = වඩා හිතකර)</p>")
    if changes:
        H.append(f"<h3>ඉදිරි වසර {3 if not deep else 5} — රාශි මාරු</h3><table><tr><th>දිනය</th><th>ග්‍රහයා</th><th>නව රාශිය</th><th>භාවය</th><th>ප්‍රවණතාව</th></tr>"
                 + "".join(f"<tr><td>{dt.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}"
                           + (f"<br><span class=muted>ස්ථිර {st.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</span>" if (st - dt).days > 20 else "")
                           + f"</td><td>{PLANET_SI[p]}</td><td>{SIGN_SI[s_]}</td>"
                           f"<td>චන්ද්‍රගෙන් {jc.house_from(moon['sign_idx'], s_)}, ලග්නයෙන් {jc.house_from(ls, s_)}</td>"
                           f"<td>{transit_meaning_si(p, jc.house_from(moon['sign_idx'], s_), jc.house_from(ls, s_))}</td></tr>"
                           for dt, p, s_, st in changes) + "</table>")
    ss = merge_spells(sade_sati_timeline(moon["sign_idx"], now_utc - timedelta(days=365 * 3), 18 if deep else 12))
    if ss:
        H.append("<h3>ඒරාෂ්ටක / අෂ්ටම ශනි කාල රේඛාව</h3><table><tr><th>වර්ගය</th><th>ආරම්භය</th><th>අවසානය</th><th>භාවය (චන්ද්‍රගෙන්)</th></tr>"
                 + "".join(f"<tr{' class=cur' if s0 <= now_utc <= s1 else ''}><td>{tag}</td>"
                           f"<td>{s0.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</td><td>{s1.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</td><td>{h}</td></tr>"
                           for s0, s1, tag, h in ss) + "</table>")
        H.append('<p class="small muted">ඒරාෂ්ටක ශනි (සඩේ සති) = ශනි චන්ද්‍රගෙන් 12, 1, 2 වැනි රාශිවලින් යන කාලය (වසර ~7½); අෂ්ටම / අර්ධාෂ්ටම ශනි = 8 හෝ 4 වැන්නෙන් යන කාලය (~2½). '
                 'මේවා බියවිය යුතු කාල නොව, වගකීම් සහ පරිණතභාවය වැඩෙන කාල ලෙස සලකනු ලැබේ.</p>')
    H.append(note_block(notes, "gochara"))

    # ---- 12 convergence
    n3 = "12" if deep else "11"
    H.append(f'<h2>{n3}. ඉදිරි කාලය — සම්මුඛ වන කවුළු</h2>')
    H.append('<p class="small">දශා, රාශි මාරු සහ ශනි කාල දින අනුව; කිහිපයක් එකට ගැලපෙන කාල වඩා වැදගත් (රාශි මාරුවල අර්ථය ඉහත).</p>')
    win = []
    for m in vim["mahadashas"]:
        for s_ in m.get("sub", []):
            st, en = datetime.fromisoformat(s_["start"]), datetime.fromisoformat(s_["end"])
            if en > now_utc and st < horizon:
                h = P[s_["lord"]]["house"]
                tone = "හිතකර" if h in (1, 2, 4, 5, 7, 9, 10, 11) else "සැලකිලිමත් වන්න"
                win.append((max(st, now_utc), f"<li><b>{max(st, now_utc).astimezone(ZoneInfo(tz)).strftime('%Y-%m')} → {en.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</b> — "
                                              f"{PLANET_SI[m['lord']]}/{PLANET_SI[s_['lord']]}: {HOUSE_AREA_SI[h]} ({tone})</li>"))
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
    H.append(gloss_disc_ab(None, GLOSS_A3_AB if deep else GLOSS_A2_AB,
                           f"පරාශර හෝරා ශාස්ත්‍රය සහ ජෛමිනි සම්ප්‍රදාය; P.V.R. Narasimha Rao ගේ Vedic Astrology: An Integrated Approach ප්‍රධාන යොමුව. "
                           f"වාර්තා වර්ගය {code}. විම්ශෝත්තරී දශා සෞර වර්ෂ අනුව."))
    return "\n".join(H)


# ================================================================ B series — life-area reports
# spec: (code, Sinhala title, subtitle, main house, support houses, main varga, extra vargas,
#        karaka planet, chara karakas, arudha, matter house for Tajaka, notes key set)
B_SPECS = {
    "B1": dict(title="විවාහ විග්‍රහය", sub="විවාහය සහ සහකරු (B1)", house=7, support=[2, 8, 12, 4],
               varga="D9", extra=["D9"], karaka="Ve", ck=["DK"], arudha="UL", matter=7,
               intro="විවාහය, සහකරු සහ දිගු කාලීන සම්බන්ධතා පිළිබඳ ප්‍රවණතා. 7 වන භාවය (විවාහයේ ක්ෂේත්‍රය), එහි අධිපති, "
                     "ශුක්‍ර (විවාහය පෙන්වන ග්‍රහයා), උපපද ලග්නය (UL — විවාහය පෙන්වන ජෛමිනි ලක්ෂ්‍යය), "
                     "දාරාකාරක (DK — සහකරු පෙන්වන ග්‍රහයා) සහ නවාංශකය (D9 — විවාහය සියුම්ව බලන කේන්දරය) "
                     "එකට කියවීමෙන් මේ ක්ෂේත්‍රයේ රටාව පෙනේ.",
               timing="විවාහ කාලය සාමාන්‍යයෙන් 7 වන භාවය/අධිපති, UL, DK හෝ ශුක්‍ර සම්බන්ධ දශා කාලවලදී, "
                      "ගුරු ගෝචරයෙන් 7 වැන්නට හෝ චන්ද්‍රගෙන් හිතකර ස්ථානයකට පැමිණෙන විට කැපී පෙනේ."),
    "B2": dict(title="වෘත්තීය විග්‍රහය", sub="රැකියාව සහ ව්‍යාපාරය (B2)", house=10, support=[1, 2, 6, 11, 7],
               varga="D10", extra=["D10"], karaka="Sa", ck=["AmK"], arudha="A10", matter=10,
               intro="රැකියාව, ව්‍යාපාරය සහ සමාජ තත්ත්වය පිළිබඳ ප්‍රවණතා. 10 වන භාවය (රැකියාවේ ක්ෂේත්‍රය), එහි අධිපති, "
                     "ශනි (මහන්සිය සහ වෘත්තිය පෙන්වන කර්ම කාරකයා), අමාත්‍යකාරක (AmK — වෘත්තිය පෙන්වන ජෛමිනි ග්‍රහයා), "
                     "A10 ආරූඪය (ලෝකයාට ඔබේ රැකියාව පෙනෙන ආකාරය) සහ දශාංශකය (D10 — රැකියාව සියුම්ව බලන කේන්දරය) ප්‍රධාන මෙවලම්.",
               timing="රැකියා වෙනස්කම් 10, 6, 11 භාවාධිපතීන්ගේ දශා කාලවලදී සහ ශනි/ගුරු ගෝචරයෙන් 10 වැන්නට හෝ "
                      "ලග්නයට පැමිණෙන කාලවලදී කැපී පෙනේ."),
    "B3": dict(title="අධ්‍යාපන විග්‍රහය", sub="ඉගෙනීම සහ විභාග (B3)", house=4, support=[2, 5, 9, 11],
               varga="D24", extra=["D24"], karaka="Me", ck=["AK"], arudha="A4", matter=4,
               intro="අධ්‍යාපනය, විෂය ප්‍රවණතාව සහ උසස් අධ්‍යාපනය. 4 වන (මූලික අධ්‍යාපනය), 5 වන (බුද්ධිය), "
                     "9 වන (උසස් අධ්‍යාපනය) භාව, බුධ (බුද්ධිය සහ ඉගෙනීම පෙන්වන ග්‍රහයා), ගුරු (ප්‍රඥාව) "
                     "සහ චතුර්විංශාංශකය (D24 — අධ්‍යාපනය සියුම්ව බලන කේන්දරය).",
               timing="විභාග සහ අධ්‍යාපන පියවර 4, 5, 9 භාවාධිපතීන්ගේ සහ බුධ/ගුරු දශා කාලවලදී කැපී පෙනේ."),
    "B4": dict(title="ධන විග්‍රහය", sub="ධනය සහ ආදායම (B4)", house=2, support=[5, 9, 11, 6, 12],
               varga="D2", extra=["D2"], karaka="Ju", ck=["AmK"], arudha="A2", matter=2,
               intro="ආදායම් මාර්ග, ඉතිරි කිරීම සහ මූල්‍ය රටාව. 2 වන (ධනය), 11 වන (ලාභ), 5/9 (පූර්ව පුණ්‍ය — පෙර පිනෙන් ලැබෙන වාසනාව) භාව, "
                     "ගුරු (ධනය පෙන්වන ග්‍රහයා), හෝරා කේන්දරය (D2 — ධනය සියුම්ව බලන කේන්දරය) "
                     "සහ ධන යෝග (ධනයට හිතකර ග්‍රහ සංයෝග).",
               timing="ධන යෝගවලට සම්බන්ධ ග්‍රහයන්ගේ දශා කාල මූල්‍ය වශයෙන් කැපී පෙනේ. "
                      "මෙය ආයෝජන උපදෙස් නොවේ — මූල්‍ය තීරණවලට සුදුසුකම් ලත් උපදේශකයෙකු හමුවන්න."),
    "B5": dict(title="සන්තාන විග්‍රහය", sub="දරුවන් (B5)", house=5, support=[2, 9, 11, 7],
               varga="D7", extra=["D7"], karaka="Ju", ck=["PK"], arudha="A5", matter=5,
               intro="දරුවන් පිළිබඳ ප්‍රවණතා. 5 වන භාවය (දරුවන්ගේ ක්ෂේත්‍රය), එහි අධිපති, ගුරු (දරුවන් පෙන්වන ග්‍රහයා), "
                     "පුත්‍රකාරක (PK — දරුවන් පෙන්වන ජෛමිනි ග්‍රහයා) සහ සප්තාංශකය (D7 — දරුවන් සියුම්ව බලන කේන්දරය). "
                     "මෙය වෛද්‍ය තොරතුරු නොවේ; සෞඛ්‍ය කාරණා සඳහා වෛද්‍යවරයෙකු හමුවන්න.",
               timing="5 වන භාවය, එහි අධිපති හෝ ගුරු සම්බන්ධ දශා කාල සහ ගුරු ගෝචරයෙන් 5 වැන්නට පැමිණෙන කාල."),
    "B6": dict(title="විදේශ විග්‍රහය", sub="විදේශ ගමන් සහ පදිංචිය (B6)", house=12, support=[3, 7, 9, 4],
               varga="D4", extra=["D4"], karaka="Ra", ck=["AK"], arudha="A12", matter=12,
               intro="විදේශ ගමන්, අධ්‍යාපනය හෝ පදිංචිය පිළිබඳ ප්‍රවණතා. 12 වන (විදේශ), 9 වන (දුර ගමන්), "
                     "3 වන (කෙටි ගමන්) භාව, රාහු (විදේශ සහ අලුත් අත්දැකීම් පෙන්වන ග්‍රහයා) "
                     "සහ චතුර්ථාංශකය (D4 — නිවස සහ පදිංචිය සියුම්ව බලන කේන්දරය).",
               timing="12, 9, 3 භාවාධිපතීන්ගේ සහ රාහු දශා කාල; ශනි/ගුරු ගෝචරයෙන් එම භාවවලට පැමිණෙන කාල."),
    "B7": dict(title="දේපල විග්‍රහය", sub="නිවස, ඉඩම් සහ වාහන (B7)", house=4, support=[2, 11, 12, 8],
               varga="D4", extra=["D4"], karaka="Ma", ck=["MK"], arudha="A4", matter=4,
               intro="නිවස, ඉඩම් සහ වාහන පිළිබඳ ප්‍රවණතා. 4 වන භාවය (නිවසේ ක්ෂේත්‍රය), එහි අධිපති, "
                     "කුජ (ඉඩම් කාරකයා — ඉඩකඩම් පෙන්වන ග්‍රහයා), ශුක්‍ර (වාහන) "
                     "සහ චතුර්ථාංශකය (D4 — දේපල සියුම්ව බලන කේන්දරය).",
               timing="4 වන භාවාධිපති, කුජ හෝ ශුක්‍ර සම්බන්ධ දශා කාල; ගුරු ගෝචරයෙන් 4 වැන්නට පැමිණෙන කාල."),
    "B8": dict(title="මාතෘ–පිතෘ විග්‍රහය", sub="දෙමව්පියන් සමඟ සම්බන්ධතාව (B8)", house=4, support=[9, 10, 2, 12],
               varga="D12", extra=["D12"], karaka="Mo", ck=["MK", "PiK"], arudha="A4", matter=4,
               intro="දෙමව්පියන් සමඟ සම්බන්ධතාව සහ ඔවුන්ගෙන් ලැබෙන සහාය පිළිබඳ පොදු ප්‍රවණතා. "
                     "4 වන (මව), 9 වන (පියා) භාව, චන්ද්‍ර (මව පෙන්වන ග්‍රහයා), රවි (පියා පෙන්වන ග්‍රහයා) "
                     "සහ ද්වාදශාංශකය (D12 — දෙමව්පියන් සියුම්ව බලන කේන්දරය). "
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
    H = [f'''<div class="cover" style="padding-top:12mm">{LOGO_IMG}<div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">{spec["title"]}</h1><div class="sub">{spec["sub"]}</div>
      <div class="name">{esc(a.name)}</div>
      <div class="muted">{esc(a.date)} · {esc(a.time)} · {esc(a.place or "")}</div>
      <div style="margin:14pt auto 0 auto; width:110mm">{south_indian_html_si(labels, "D1 · රාශි චක්‍රය", 110)}</div></div>''']

    H.append('<div class="pb"></div><h2>1. මේ වාර්තාව ගැන</h2>')
    H.append(plain_b_ab(d, a, code, tr, now_local))
    H.append(f'<p class="small"><b>මේ වාර්තාවේ බලන දේ:</b> {spec["intro"]}</p>')
    if approx:
        H.append(f'<div class="note"><div class="lbl">උපන් වේලාව</div><p>වේලාව ආසන්න බැවින් {spec["varga"]} වර්ග කේන්දරයේ ලග්නය '
                 'මිනිත්තු කිහිපයකින් වෙනස් විය හැක; D1, දශා සහ ගෝචරය ප්‍රමුඛ කර කියවන්න.</p></div>')
    H.append("<table>"
             f"<tr><td style='width:34%'><b>ලග්නය</b></td><td>{SIGN_SI[ls]} — අධිපති {PLANET_SI[jc.SIGN_LORD[ls]]}, {P[jc.SIGN_LORD[ls]]['house']} වැන්නේ</td></tr>"
             f"<tr><td><b>චන්ද්‍ර</b></td><td>{SIGN_SI[P['Mo']['sign_idx']]} — {P['Mo']['house']} වැන්නේ, {NAK_SI[jc.NAKSHATRAS.index(P['Mo']['nakshatra'])]} නැකත</td></tr>"
             f"<tr><td><b>ප්‍රධාන භාවය</b></td><td>{h} වැන්න ({SIGN_SI[hs]}) — {HOUSE_PLAIN_SI[h]}</td></tr>"
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
    H.append('<p class="small muted">වගුව කියවන හැටි: <b>භාවාධිපති</b> = මේ භාවයේ අධිපති ග්‍රහයා (එය සිටින භාවයේ කාරණා මේ ක්ෂේත්‍රයට බැඳේ); '
             '<b>කාරකයා</b> = මේ කාරණය ස්වභාවයෙන් පෙන්වන ග්‍රහයා; '
             + "".join(f"<b>{KAR_SI_B.get(k, k)}</b> = ජෛමිනි ක්‍රමයේ {CK_ROLE_AB.get(k, '')} පෙන්වන ග්‍රහයා; " for k in spec["ck"])
             + '<b>ආරූඪය</b> = ලෝකයාට මේ ක්ෂේත්‍රය පෙනෙන ආකාරය.</p>')
    good = P[hlord]["house"] in (1, 4, 5, 7, 9, 10, 11) and "නීච" not in si_dignity(P[hlord]["dignity"])
    H.append(f'<div class="box"><b>ප්‍රවණතාව:</b> භාවාධිපති {PLANET_SI[hlord]} {P[hlord]["house"]} වැන්නේ '
             f'({HOUSE_PLAIN_SI[P[hlord]["house"]]}) සිටීම මේ ක්ෂේත්‍රය එම කාරණා සමඟ බැඳෙන බව පෙන්වයි. '
             + ("භාවාධිපති හිතකර ස්ථානයක සිටීම සහායකයි." if good else "ප්‍රතිඵල ශ්‍රමයෙන් සහ ඉවසීමෙන් ලැබෙන ප්‍රවණතාවක් ඇත.")
             + (f' භාවයේ {", ".join(PLANET_SI[c] for c in occ)} සිටීම එම ග්‍රහයන්ගේ ස්වභාවය මේ ක්ෂේත්‍රයට එකතු කරයි.' if occ else "")
             + "</div>")
    sup = []
    for sh in spec["support"]:
        shs = (ls + sh - 1) % 12
        sl = jc.SIGN_LORD[shs]
        sup.append(f"<tr><td>{sh}</td><td>{HOUSE_AREA_SI[sh]}</td><td>{SIGN_SI[shs]}</td><td>{PLANET_SI[sl]} — {P[sl]['house']} වැන්නේ</td>"
                   f"<td>{', '.join(PLANET_SI[c] for c in ['Su', 'Mo', 'Ma', 'Me', 'Ju', 'Ve', 'Sa', 'Ra', 'Ke'] if P[c]['sign_idx'] == shs) or '—'}</td></tr>")
    H.append("<h3>සහායක භාව</h3><table><tr><th>භාවය</th><th>කාරණය</th><th>රාශිය</th><th>අධිපති</th><th>ග්‍රහයන්</th></tr>" + "".join(sup) + "</table>")
    H.append('<p class="small muted">වගුව කියවන හැටි: මේ ක්ෂේත්‍රයට සම්බන්ධ අනෙක් ජීවිත ක්ෂේත්‍ර; ප්‍රධාන භාවය සමඟ එකට කියවේ.</p>')
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
        H.append(f'<h2 class="sec">3. {spec["varga"]} — {nm} කේන්දරය</h2>')
        H.append(f'<div class="two vblock"><div style="flex:0 0 86mm">{south_indian_html_si(vlab, f'{spec["varga"]} · {nm}' , 86)}</div>'
                 f'<div><p class="small">{spec["varga"]} ({nm}) යනු රාශි කුඩා කොටස්වලට බෙදා සාදන අමතර (වර්ග) කේන්දරයකි — '
                 f'{purpose} සියුම්ව බැලීමට. ලග්නය <b>{SIGN_SI[vl]}</b>; අධිපති {PLANET_SI[jc.SIGN_LORD[vl]]} '
                 f'එම කේන්දරයේ {jc.house_from(vl, inv[v[jc.SIGN_LORD[vl]]])} වැන්නේ. '
                 f'D1 හි {h} වන භාවාධිපති {PLANET_SI[hlord]} මෙහි {vh} වැන්නේ. '
                 + (f'වර්ගෝත්තම ග්‍රහයන්: {", ".join(pl_si(x) for x in d.get("vargottama", []))}.' if spec["varga"] == "D9" and d.get("vargottama") else "")
                 + "</p></div></div>")
        vrow = []
        for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
            vs = inv[v[c]]
            vrow.append(f"<tr><td>{PLANET_SI[c]}</td><td>{SIGN_SI[vs]}</td><td>{jc.house_from(vl, vs)}</td>"
                        f"<td>{SIGN_SI[P[c]['sign_idx']]} ({P[c]['house']})</td></tr>")
        H.append(f"<table><tr><th>ග්‍රහයා</th><th>{spec['varga']} රාශිය</th><th>{spec['varga']} භාවය</th><th>D1 රාශිය (භාවය)</th></tr>" + "".join(vrow) + "</table>")
        H.append(f'<p class="small muted">වගුව කියවන හැටි: ග්‍රහයන් {spec["varga"]} කේන්දරයේ සිටින රාශිය සහ භාවය, ප්‍රධාන (D1) කේන්දරයේ ස්ථානය සමඟ; '
                 'දෙකේම එකම රාශිය නම් (වර්ගෝත්තම) ග්‍රහයා ශක්තිමත්.</p>')

    # --- 4 yogas relevant
    H.append("<h2>4. අදාළ යෝග සහ තත්ත්ව</h2><p class='small'>යෝග = ග්‍රහයන්ගේ විශේෂ සංයෝග; දෝෂ = සැලකිලිමත් විය යුතු සංයෝග. "
             "තනි දෝෂයක් ගැන බිය විය යුතු නැත — බොහෝ ඒවා වෙනත් ග්‍රහ ස්ථාන නිසා අඩු වේ හෝ නැති වේ.</p><ul>")
    ylist = []
    for y in d.get("yoga_indications", []):
        key = next((k for k in YOGA_SI if k.lower() in y.lower()), None)
        ylist.append(f"<li><b>{YOGA_SI[key].split(' — ')[0] if key else esc(y)}</b>"
                     + (f" — {YOGA_SI[key].split(' — ', 1)[1]}" if key and " — " in YOGA_SI[key] else "") + "</li>")
    for c in [hlord, kar]:
        dg = si_dignity(P[c]["dignity"])
        if dg != "—":
            ylist.append(f"<li>{PLANET_SI[c]} {dg} — මේ ක්ෂේත්‍රයට {'ශක්තියක්' if 'උච්ච' in dg or 'ස්වක්ෂේත්‍ර' in dg or 'මූලත්‍රිකෝණ' in dg else 'අභියෝගයක් — උත්සාහයෙන් ජය ගත හැක'}</li>")
        if P[c].get("combust"):
            ylist.append(f"<li>{PLANET_SI[c]} අස්තංගත — එහි ඵල ප්‍රකාශ වීම දුර්වල විය හැක</li>")
    av = d.get("ashtakavarga")
    if av:
        ylist.append(f"<li>අෂ්ටකවර්ග (ග්‍රහයන් රාශියකට දෙන ශුභ ලකුණු; SAV = එකතුව): {h} වන භාවයේ SAV බින්දු <b>{av['sav'][hs]}</b> "
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
    H.append('<p class="small muted">දශා = ජීවිතය ග්‍රහයන්ට බෙදූ කාල පරිච්ඡේද (මහා දශාව අවුරුදු ගණනක්; අන්තර් දශාව ඒ තුළ කෙටි කොටසක්). '
             'මේ ක්ෂේත්‍රයට සම්බන්ධ ග්‍රහයෙකුගේ දශාවේදී මේ කාරණා ඉස්මතු වේ.</p>')
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
    if rows:
        H.append('<p class="small muted">වගුව කියවන හැටි: “ගුරු/ශනි” = ගුරු මහා දශාව තුළ ශනි අන්තර් දශාව; '
                 '“ඇයි” = එම ග්‍රහයා මේ ක්ෂේත්‍රයට සම්බන්ධ වන හේතුව.</p>')
    nd = d.get("narayana_dasa")
    if nd:
        rel_nd = [x for x in nd if datetime.fromisoformat(x["end"]) > now_utc and datetime.fromisoformat(x["start"]) < horizon]
        if rel_nd:
            H.append("<h3>නාරායණ දශා (තහවුරු කිරීම)</h3><table><tr><th>රාශිය</th><th>ආරම්භය</th><th>අවසානය</th><th>ලග්නයෙන්</th><th>අදාළද</th></tr>"
                     + "".join(f"<tr><td>{SIGN_SI[inv[x['sign']]]}</td><td>{fmt_date(x['start'], tz)}</td><td>{fmt_date(x['end'], tz)}</td>"
                               f"<td>{jc.house_from(ls, inv[x['sign']])} වැන්න</td>"
                               f"<td>{'✔ මේ ක්ෂේත්‍රයට' if jc.house_from(ls, inv[x['sign']]) in [h] + spec['support'] else '—'}</td></tr>"
                               for x in rel_nd[:8]) + "</table>")
            H.append('<p class="small muted">වගුව කියවන හැටි: මෙහි කාල රාශිවලට අයත්ය; ✔ ඇති කාලවලදී මේ ක්ෂේත්‍රයේ භාවයක් ක්‍රියාත්මකයි '
                     '(ඉහත දශා තහවුරු කිරීමට).</p>')
    H.append(note_block(notes, "dasha"))

    # --- 6 gochara
    H.append("<h2>6. ගෝචරය</h2>")
    H.append('<p class="small">ගෝචරය = දැන් අහසේ ග්‍රහයන් සිටින තැන. “ලග්නයෙන් 9 වැන්න” = ඔබේ ලග්න රාශියේ සිට ගණන් කළ විට 9 වැනි රාශිය; '
             '“චන්ද්‍රගෙන්” ගණන් කරන්නේ චන්ද්‍ර රාශියේ සිටයි.</p>')
    sa, ju = tr["Sa"], tr["Ju"]
    hs_house_from_lagna = h
    H.append("<ul>"
             f"<li><b>ශනි</b> {SIGN_SI[sa['sign']]} — ලග්නයෙන් {sa['from_lagna']} වැන්න"
             + (f" (මේ ක්ෂේත්‍රයේ ප්‍රධාන භාවය — වගකීම් සහ ප්‍රමාද, ඒත් ස්ථාවර පදනමක්)" if sa["from_lagna"] == hs_house_from_lagna else "")
             + f"; චන්ද්‍රගෙන් {sa['from_moon']}: {SATURN_FROM_MOON_SI[sa['from_moon']]}</li>"
             f"<li><b>ගුරු</b> {SIGN_SI[ju['sign']]} — ලග්නයෙන් {ju['from_lagna']} වැන්න"
             + (" (මේ ක්ෂේත්‍රයට හිතකර ගෝචරයක්)" if ju["from_lagna"] in [h] + spec["support"] else "")
             + f"; චන්ද්‍රගෙන් {ju['from_moon']}: {JUPITER_FROM_MOON_SI[ju['from_moon']]}</li>"
             f"<li><b>ඒරාෂ්ටක / අෂ්ටම ශනි</b>: {tr['sade_sati']}</li></ul>")
    rel_ch = [(dt, p, s_, st) for dt, p, s_, st in changes if jc.house_from(ls, s_) in [h] + spec["support"]]
    if rel_ch:
        H.append("<h3>මේ ක්ෂේත්‍රයට වැදගත් ගෝචර මාරු</h3><table><tr><th>දිනය</th><th>ග්‍රහයා</th><th>රාශිය</th><th>භාවය</th></tr>"
                 + "".join(f"<tr><td>{dt.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</td><td>{PLANET_SI[p]}</td><td>{SIGN_SI[s_]}</td>"
                           f"<td>ලග්නයෙන් {jc.house_from(ls, s_)} වැන්න</td></tr>" for dt, p, s_, st in rel_ch) + "</table>")
        H.append('<p class="small muted">වගුව කියවන හැටි: මේ ක්ෂේත්‍රයේ භාවවලට ග්‍රහයන් ඇතුළු වන දින — ගුරු උදව්වක්; ශනි වගකීම් සහ ඉවසීම ඉල්ලයි; '
                 'රාහු අලුත් අභිලාශ හෝ අනපේක්ෂිත වෙනස්කම් ගෙන එයි.</p>')
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
                        f"(ලග්නයෙන් {jc.house_from(ls, s_)} වැන්න — {HOUSE_AREA_SI[jc.house_from(ls, s_)]})</li>"))
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
    H.append(gloss_disc_ab(GLOSS_B_SHARED_AB + (["අස්තංගත"] if P[hlord].get("combust") or P[kar].get("combust") else []), GLOSS_B_AB,
                           f"පරාශර හෝරා ශාස්ත්‍රය සහ ජෛමිනි සම්ප්‍රදාය; P.V.R. Narasimha Rao ගේ Vedic Astrology: An Integrated Approach. "
                           f"වාර්තා වර්ගය {code} — {spec['sub']}.{extra_disc}"))
    return "\n".join(H)


# ================================================================ C series — annual / time-based reports
SS_PHASE_SI = {12: ("පළමු අවධිය (ආරෝහණ)", "වියදම්, නින්ද/විවේකය, විදේශ හෝ ස්ථාන වෙනස්කම්; අභ්‍යන්තර සූදානම"),
               1: ("මධ්‍ය අවධිය (ශිඛර)", "වගකීම් බර, ශරීර/මානසික ශක්තිය, පෞද්ගලික අනන්‍යතාවය පිළිබඳ ප්‍රශ්න"),
               2: ("තෙවන අවධිය (අවරෝහණ)", "ධන කටයුතු, පවුල, කථනය; ක්‍රමයෙන් සැහැල්ලු වීම"),
               4: ("අර්ධාෂ්ටම ශනි", "නිවස, මව, මානසික සතුට සහ දේපල සම්බන්ධ වගකීම්"),
               8: ("අෂ්ටම ශනි", "හදිසි වෙනස්කම්, වියදම්, සෞඛ්‍ය පුරුදු ගැන අවධානය")}
SS_ADVICE = ["නියමිත වේලාවට වැඩ කිරීම සහ පොරොන්දු ඉටු කිරීම — ශනි විනය අගය කරයි",
             "නින්ද, ආහාර සහ ව්‍යායාම නිතිපතා තබා ගැනීම",
             "වැඩිහිටියන්, සේවකයන් සහ අඩු පහසුකම් ඇති අය සමඟ ඉවසීමෙන් සහ ගෞරවයෙන් කටයුතු කිරීම",
             "මූල්‍ය සැලසුම් සහ අනවශ්‍ය ණය වළක්වා ගැනීම",
             "ලොකු තීරණ කලබලයෙන් නොගෙන, කරුණු ලියා තබා ගෙන ගැනීම"]


def build_c2(d, a, notes, now_local, year, tr, changes):
    """C2 = C1 (Varsha) + that year's transits + Vimshottari AD/PD overlay -> convergence calendar."""
    base = build_c1(d, a, notes, now_local, year, plain=_PLAIN_SLOT_C)   # C2's own box goes in at the end
    # cut C1's glossary and disclaimer; we add our own at the end
    base = base.split(_GLOSS_HEAD_C)[0]
    base = base.replace("වර්ෂ ඵල — තාජක ක්‍රමය (C1)", "වර්ෂ ඵල + ගෝචර දින දර්ශනය (C2)")
    P, ls = d["planets"], d["lagna"]["sign_idx"]
    moon = P["Mo"]
    tz = a.tz
    v = d["varsha_kundali"]
    inv = {s: i for i, s in enumerate(jc.SIGNS)}
    H = [base]
    y0 = datetime.strptime(v["varsha_pravesha_local"], "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(a.tz)).astimezone(timezone.utc)
    y1 = y0 + timedelta(days=366)
    # flows on after C1's pages (a forced break left a near-empty page when they ran a few lines long);
    # heading, note and list stay together
    H.append('<div class="vblock"><h2 class="sec">6. වර්ෂය තුළ ගෝචරය</h2>'
             f'<p class="small muted">{now_local.strftime("%Y-%m-%d")} දිනට ශනි, ගුරු, රාහු වැනි සෙමින් ගමන් කරන ග්‍රහයන් සිටින තැන. '
             '“චන්ද්‍රගෙන් 4” යනු ඔබේ ජන්ම චන්ද්‍ර රාශියේ සිට ගණන් කළ විට ග්‍රහයා සිටින රාශිය; “ලග්නයෙන් 9” යනු ලග්නයේ සිට ගණන් කළ විට.</p>')
    sa, ju, ra = tr["Sa"], tr["Ju"], tr["Ra"]
    H.append("<ul>"
             f"<li><b>ශනි</b> {SIGN_SI[sa['sign']]} — චන්ද්‍රගෙන් {sa['from_moon']}, ලග්නයෙන් {sa['from_lagna']}: {SATURN_FROM_MOON_SI[sa['from_moon']]}</li>"
             f"<li><b>ගුරු</b> {SIGN_SI[ju['sign']]} — චන්ද්‍රගෙන් {ju['from_moon']}, ලග්නයෙන් {ju['from_lagna']}: {JUPITER_FROM_MOON_SI[ju['from_moon']]}</li>"
             f"<li><b>රාහු–කේතු</b> {SIGN_SI[ra['sign']]}–{SIGN_SI[(ra['sign'] + 6) % 12]} — ලග්නයෙන් {ra['from_lagna']}/{(ra['from_lagna'] + 5) % 12 + 1} වැනි භාව: "
             f"{HOUSE_AREA_SI[ra['from_lagna']]}; {HOUSE_AREA_SI[(ra['from_lagna'] + 5) % 12 + 1]} — අලුත් අභිලාශ හෝ අනපේක්ෂිත වෙනස්කම්</li>"
             f"<li><b>ඒරාෂ්ටක / අෂ්ටම ශනි</b>: {tr['sade_sati']}</li></ul></div>")
    yr_ch = [c for c in changes if y0 <= c[0].astimezone(timezone.utc) <= y1]
    if yr_ch:
        H.append("<h3>වර්ෂය තුළ රාශි මාරු</h3><table><tr><th>දිනය</th><th>ග්‍රහයා</th><th>නව රාශිය</th><th>භාවය</th><th>ප්‍රවණතාව</th></tr>"
                 + "".join(f"<tr><td>{dt.astimezone(ZoneInfo(tz)).strftime('%Y-%m-%d')}</td><td>{PLANET_SI[p]}</td><td>{SIGN_SI[s_]}</td>"
                           f"<td>චන්ද්‍රගෙන් {jc.house_from(moon['sign_idx'], s_)}, ලග්නයෙන් {jc.house_from(ls, s_)}</td>"
                           f"<td>{transit_meaning_si(p, jc.house_from(moon['sign_idx'], s_), jc.house_from(ls, s_))}</td></tr>"
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
    rows, cal = [], []
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
        focus = HOUSE_AREA_SI[P[pd_["lord"]]["house"]] if pd_ else (HOUSE_AREA_SI[P[ad["lord"]]["house"]] if ad else "—")
        rows.append(f"<tr><td>{cur.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</td><td>{dash}</td>"
                    f"<td>{PLANET_SI[mud['lord']] if mud else '—'}</td><td>{focus}</td><td>{', '.join(ev) or '—'}</td><td>{tone}</td></tr>")
        cal.append((cur.astimezone(ZoneInfo(tz)).strftime('%Y-%m'), tone))
        cur += timedelta(days=30.44)
    H.append("<table><tr><th>මාසය</th><th>විම්ශෝත්තරී (MD/AD/PD)</th><th>මුද්දා</th><th>අවධානය යොමු වන ක්ෂේත්‍රය</th><th>ගෝචර සිදුවීම්</th><th>ප්‍රවණතාව</th></tr>"
             + "".join(rows) + "</table>")
    H.append('<p class="small muted">වගුව කියවන හැටි: <b>විම්ශෝත්තරී</b> = ඔබේ ජන්ම කේන්දරයේ දශා — මහා / අන්තර් / ප්‍රත්‍යන්තර (MD/AD/PD); '
             '<b>මුද්දා</b> = අවුරුද්දේ කේන්දරයේ කෙටි දශාව; <b>ප්‍රවණතාව</b>: හිතකර = හොඳ මාසයක්, මිශ්‍ර = හොඳ සහ අපහසු දෙකම, '
             'අවධානය = ඉවසීමෙන් සහ සැලකිලිමත්ව කටයුතු කළ යුතු මාසයක්.</p>')
    H.append(note_block(notes, "calendar") or note_block(notes, "gochara"))
    H[0] = H[0].replace(_PLAIN_SLOT_C, _plain_year_c(d, a, now_local, year, months=cal, tr=tr))
    H.append(_gloss_method_c(_GLOSS_CAL_C, _GLOSS_YEAR_EXTRA_C, "වර්ෂ ඵල (තාජක) සහ ගෝචර ක්‍රම — P.V.R. Narasimha Rao, ch. 25–31. වාර්තා වර්ගය C2. "
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
              if cur_sp else (f"දැනට ඒරාෂ්ටක (සඩේ සති), අෂ්ටම හෝ අර්ධාෂ්ටම ශනි නැත. ඊළඟ කාලය <b>{nxt[2]}</b> — {nxt[0].astimezone(ZoneInfo(tz)).strftime('%Y-%m')} සිට" if nxt else "දැනට ඒරාෂ්ටක (සඩේ සති), අෂ්ටම හෝ අර්ධාෂ්ටම ශනි නැත."))
    H = [f'''<div class="cover" style="padding-top:12mm">{LOGO_IMG}<div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">සඩේ සති වාර්තාව</h1><div class="sub">ඒරාෂ්ටක, අෂ්ටම සහ අර්ධාෂ්ටම ශනි කාල (C3)</div>
      <div class="name">{esc(a.name)}</div>
      <div class="muted">{esc(a.date)} · {esc(a.time)} · {esc(a.place or "")}</div>
      <div style="margin:12pt auto 0 auto; width:100mm">{south_indian_html_si(labels, "D1 · රාශි චක්‍රය", 100)}</div>
      <p style="margin-top:10pt">{status}</p></div>''']
    H.append('<div class="pb"></div>' + _plain_sadesati_c(spells, now_utc, tz, P["Sa"])
             + '<h2>1. ඒරාෂ්ටක ශනි (සඩේ සති) යනු මොකක්ද?</h2>')
    H.append('<div class="box">ඔබේ <b>ජන්ම චන්ද්‍ර රාශිය</b> යනු ඔබ උපන් මොහොතේ චන්ද්‍රයා සිටි රාශියයි. ශනි ඒ රාශියට පෙර රාශිය, '
             'ඒ රාශිය සහ ඊළඟ රාශිය (චන්ද්‍රගෙන් 12, 1, 2) හරහා ගමන් කරන කාලය ලංකාවේ <b>ඒරාෂ්ටක ශනි</b> ලෙස හැඳින්වේ '
             '(පොත්පත්වල <b>සඩේ සති</b> — “හත්හමාර” යන අරුතින්). රාශියකට වසර 2½ බැගින්, මුළු කාලය වසර 7½ක් පමණ. '
             'ශනි චන්ද්‍රගෙන් 8 හෝ 4 වැනි රාශියේ සිටින වසර 2½ <b>අෂ්ටම / අර්ධාෂ්ටම ශනි</b> ලෙස හැඳින්වේ.<br><br>'
             'මේ කාල ගැන බොහෝ දෙනා බිය වුවත්, සම්භාව්‍ය ග්‍රන්ථවල දැක්වෙන්නේ මේවා <b>වගකීම්, විනය සහ පරිණතභාවය</b> වැඩෙන කාල ලෙසයි. '
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
             f"<tr><td><b>ශනි අධිපති භාව</b></td><td>{', '.join(str(x) + ' වැන්න' for x in own)} — {'; '.join(HOUSE_AREA_SI[x] for x in own)}</td></tr>"
             f"<tr><td><b>චන්ද්‍රගෙන් ශනි</b></td><td>{jc.house_from(ms, sa_n['sign_idx'])} වැන්නේ</td></tr>"
             + (f"<tr><td><b>ශනිගේ අෂ්ටකවර්ග බින්දු</b></td><td>{sum(sat_bav)} (සියලු රාශිවල එකතුව)</td></tr>" if sat_bav else "")
             + "</table>")
    H.append('<p class="small muted">වගුව කියවන හැටි: <b>ජන්ම ශනි</b> = ඔබ උපන් විට ශනි සිටි රාශිය, අංශක සහ භාවය; '
             '<b>අධිපති භාව</b> = ශනි පාලනය කරන ජීවිත ක්ෂේත්‍ර — ශනි කාලවලදී මේවා ඉස්මතු වේ; '
             '<b>චන්ද්‍රගෙන් ශනි</b> = ජන්ම චන්ද්‍ර රාශියේ සිට ගණන් කළ විට ශනි සිටි රාශිය'
             + ('; <b>අෂ්ටකවර්ග බින්දු</b> = ශනිට ලැබෙන හොඳ ලකුණු (4 වන කොටස බලන්න).</p>' if sat_bav else '.</p>'))
    good_sa = sa_n["house"] in (3, 6, 10, 11) or si_dignity(sa_n["dignity"]) in ("උච්ච", "ස්වක්ෂේත්‍ර", "මූලත්‍රිකෝණ")
    H.append(f'<div class="box"><b>ප්‍රවණතාව:</b> ' + ("ජන්ම කේන්දරයේ ශනි ශක්තිමත් ස්ථානයක සිටීම මේ කාලවල බර සාපේක්ෂව අඩු කරන සාධකයකි."
                                                       if good_sa else "ජන්ම ශනිගේ ස්ථානය අනුව මේ කාලවලදී ඉවසීම සහ ක්‍රමවත් බව වැඩිපුර අවශ්‍ය විය හැක.")
             + " ශනි අධිපති භාවවල කාරණා මේ කාලවලදී ප්‍රමුඛ වේ.</div>")
    H.append('<div class="pb"></div><h2>3. ඔබේ ඒරාෂ්ටක / අෂ්ටම ශනි කාල රේඛාව</h2>')
    rows = []
    for s0, s1, tag, h in spells:
        ph = SS_PHASE_SI.get(h, ("", ""))
        mark = " class=cur" if s0 <= now_utc <= s1 else ""
        past = "අවසන්" if s1 < now_utc else ("ක්‍රියාත්මක" if s0 <= now_utc <= s1 else "ඉදිරියේ")
        rows.append(f"<tr{mark}><td>{tag}</td><td>{ph[0]}</td><td>{s0.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</td>"
                    f"<td>{s1.astimezone(ZoneInfo(tz)).strftime('%Y-%m')}</td><td>{past}</td><td>{ph[1]}</td></tr>")
    H.append("<table><tr><th>වර්ගය</th><th>අවධිය</th><th>ආරම්භය</th><th>අවසානය</th><th>තත්ත්වය</th><th>ප්‍රමුඛ කාරණා</th></tr>" + "".join(rows) + "</table>")
    H.append('<p class="small muted">ශනිගේ වක්‍ර චලනය නිසා රාශි මාරු දෙවරක් සිදුවිය හැක; මෙහි කාල එකතු කර දක්වා ඇත. '
             'දිනවලට දින කිහිපයක නිරවද්‍යතාවක් ඇත. තද කළ පේළිය = දැන් ගත වන කාලය; <b>අවධිය</b>: ආරෝහණ = පටන් ගැනීම, '
             'ශිඛර = මැද කාලය (වගකීම් වැඩිම), අවරෝහණ = ක්‍රමයෙන් සැහැල්ලු වීම.</p>')
    if sat_bav:
        H.append("<h2>4. අෂ්ටකවර්ග අනුව ශනි ගෝචරයේ බර</h2>")
        H.append("<table><tr><th>රාශිය</th>" + "".join(f"<th>{SIGN_SI[i][:3]}</th>" for i in range(12)) + "</tr>"
                 + "<tr><td>ශනි BAV</td>" + "".join(f"<td>{sat_bav[i]}</td>" for i in range(12)) + "</tr>"
                 + "<tr><td>SAV</td>" + "".join(f"<td>{av['sav'][i]}</td>" for i in range(12)) + "</tr></table>")
        H.append('<p class="small muted">වගුව කියවන හැටි: අෂ්ටකවර්ගය = එක් එක් රාශියට ග්‍රහයන්ගෙන් ලැබෙන හොඳ ලකුණු (බින්දු). '
                 '<b>ශනි BAV</b> = ශනිගේ ලකුණු (0–8); <b>SAV</b> = සියලු ග්‍රහයන්ගේ ලකුණු එකතුව '
                 '(සාමාන්‍යය 28ක් පමණ; ඊට වැඩි නම් සාමාන්‍යයට වඩා හිතකරයි).</p>')
        H.append('<p class="small">ශනි ගමන් කරන රාශියේ ශනිගේ බින්දු 4 හෝ ඊට වැඩි නම් එම කාලයේ ප්‍රතිඵල සාපේක්ෂව පහසු වන ප්‍රවණතාවක් ඇත; '
                 '2ට අඩු නම් වැඩි ඉවසීමක් අවශ්‍ය විය හැක.</p>')
        for s0, s1, tag, h in spells:
            if s1 < now_utc:
                continue
            sgn = (ms + h - 1) % 12
            H.append(f'<p class="small">• {tag} — {ph_label(h)} — {SIGN_SI[sgn]} රාශියේ ({s0.astimezone(ZoneInfo(tz)).strftime("%Y-%m")}–'
                     f'{s1.astimezone(ZoneInfo(tz)).strftime("%Y-%m")}): ශනි බින්දු <b>{sat_bav[sgn]}</b>, SAV {av["sav"][sgn]}</p>')
    H.append('<h2>5. ප්‍රායෝගික ආකල්ප</h2><ul>' + "".join(f"<li>{x}</li>" for x in SS_ADVICE) + "</ul>")
    H.append('<div class="note"><div class="lbl">වැදගත්</div><p>ඒරාෂ්ටක (සඩේ සති) හෝ අෂ්ටම ශනි කාලයක් සෞඛ්‍ය ප්‍රශ්නයක් හෝ අර්බුදයක් ලෙස නොසලකන්න. '
             'සෞඛ්‍ය, මූල්‍ය හෝ නීතිමය කාරණා සඳහා අදාළ වෘත්තිකයන් හමුවන්න. ජ්‍යොතිෂය එම උපදෙස් වෙනුවට නොවේ.</p></div>')
    H.append(note_block(notes, "summary", "ජ්‍යොතිෂවේදියාගේ විග්‍රහය"))
    H.append(note_block(notes, "remedies", "ප්‍රතිකර්ම / ආකල්ප යෝජනා"))
    H.append(_gloss_method_c(_GLOSS_SS_C, [x for x in _GLOSS_SS_EXTRA_C if sat_bav or "BAV" not in x[0]],
                             "ශනි ගෝචරය සහ අෂ්ටකවර්ග — P.V.R. Narasimha Rao, ch. 12, 25. වාර්තා වර්ගය C3."))
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
    H = [f'''<div class="cover" style="padding-top:12mm">{LOGO_IMG}<div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">දශා සන්ධි වාර්තාව</h1><div class="sub">මහා දශා මාරුව (C4)</div>
      <div class="name">{esc(a.name)}</div>
      <div style="margin:10pt 0; font-size:14pt"><b>{PLANET_SI[A]} → {PLANET_SI[B]}</b> · {change.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d")}</div>
      <div style="width:96mm; margin:8pt auto 0 auto">{south_indian_html_si(labels, "D1 · රාශි චක්‍රය", 96)}</div></div>''']
    H.append('<div class="pb"></div>' + _plain_sandhi_c(P, cur_md, nxt_md, tz) + '<h2>1. දශා සන්ධිය යනු</h2>')
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
    H.append('<p class="small muted">වගුව කියවන හැටි: <b>ස්ථානය</b> = ජන්ම කේන්දරයේ ග්‍රහයා සිටින රාශිය සහ භාවය; '
             '<b>තත්ත්වය</b> = උච්ච, නීච වැනි විශේෂ බලය (— = විශේෂ තත්ත්වයක් නැත); <b>අධිපති භාව</b> = ග්‍රහයා පාලනය කරන ජීවිත ක්ෂේත්‍ර; '
             '<b>කාරකත්වය</b> = ග්‍රහයා ස්වභාවයෙන් නියෝජනය කරන දේ.</p>')
    ha, hb = P[A]["house"], P[B]["house"]
    H.append(f'<div class="box"><b>වෙනස:</b> {PLANET_SI[A]} දශාවේදී {HOUSE_PLAIN_SI[ha]} සම්බන්ධ කාරණා ප්‍රමුඛ වූ බව පෙනේ. '
             f'{PLANET_SI[B]} දශාවේදී අවධානය {HOUSE_PLAIN_SI[hb]} දෙසට හැරෙන ප්‍රවණතාවක් ඇත. '
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
                        f"<td>{PLANET_SI[s_['lord']]} {hh} වැන්නේ — {HOUSE_AREA_SI[hh]}</td></tr>")
    H.append("<table><tr><th>දශාව</th><th>ආරම්භය</th><th>අවසානය</th><th>ප්‍රවණතාව</th></tr>" + "".join(rows) + "</table>")
    H.append('<p class="small muted">වගුව කියවන හැටි: <b>දශාව</b> තීරුවේ පළමු නම මහා දශාව, දෙවැන්න ඒ තුළ ගෙවෙන අන්තර් දශාව; '
             '<b>ප්‍රවණතාව</b> = ඒ අන්තර් දශාවේ ඉස්මතු වන ජීවිත ක්ෂේත්‍රය (ග්‍රහයා ජන්ම කේන්දරයේ සිටින භාවය අනුව).</p>')
    H.append(f'<p class="small">මාරු දිනය <b>{change.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d")}</b>. '
             f'ඊට කලින් අවසන් අන්තර් දශාව සහ පසුව පළමු අන්තර් දශාව මාරුවේ ස්වභාවය තීරණය කරයි.</p>')
    H.append("<h2>4. ගෝචරය මාරු කාලයේ</h2>"
             f'<p class="small muted">{now_local.strftime("%Y-%m-%d")} දිනට ශනි සහ ගුරු සිටින තැන. '
             '“චන්ද්‍රගෙන් 4” යනු ඔබේ ජන්ම චන්ද්‍ර රාශියේ සිට ගණන් කළ විට ග්‍රහයා සිටින රාශියයි.</p>')
    sa, ju = tr["Sa"], tr["Ju"]
    H.append("<ul>"
             f"<li><b>ශනි</b> {SIGN_SI[sa['sign']]} — චන්ද්‍රගෙන් {sa['from_moon']}: {SATURN_FROM_MOON_SI[sa['from_moon']]}</li>"
             f"<li><b>ගුරු</b> {SIGN_SI[ju['sign']]} — චන්ද්‍රගෙන් {ju['from_moon']}: {JUPITER_FROM_MOON_SI[ju['from_moon']]}</li>"
             f"<li><b>ඒරාෂ්ටක / අෂ්ටම ශනි</b>: {tr['sade_sati']}</li></ul>")
    H.append("<h2>5. ප්‍රායෝගිකව</h2><ul>"
             f"<li>නව දශාධිපති {PLANET_SI[B]} නියෝජනය කරන කාරණා ({PLANET_NATURE_SI[B]}) ක්‍රමයෙන් ඉදිරියට එනවා — ඒවාට කලින් සූදානම් වීම ප්‍රයෝජනවත්.</li>"
             f"<li>{HOUSE_PLAIN_SI[hb]} සම්බන්ධ දේවල් නව අවධියේ තේමාව වීමට ඉඩ ඇත.</li>"
             "<li>මාරු කාලයේ ලොකු, ආපසු හැරවිය නොහැකි තීරණ ගැනීමට කලින් කරුණු ලියා තබා ගෙන සලකා බලන්න.</li>"
             "<li>පැරණි දශාවේ ඉතිරි වී ඇති කටයුතු (ණය, පොරොන්දු, අවසන් නොකළ වැඩ) මාරුවට කලින් අවසන් කර ගැනීම ප්‍රයෝජනවත්.</li></ul>")
    H.append(note_block(notes, "summary", "ජ්‍යොතිෂවේදියාගේ විග්‍රහය"))
    H.append(note_block(notes, "upcoming"))
    H.append(_gloss_method_c(_GLOSS_SANDHI_C, _GLOSS_SANDHI_EXTRA_C,
                             "විම්ශෝත්තරී දශා — P.V.R. Narasimha Rao, ch. 16. වාර්තා වර්ගය C4. දශා දින සෞර වර්ෂ අනුව."))
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
    H = [f'''<div class="cover" style="padding-top:12mm">{LOGO_IMG}<div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">මාස ඵල වාර්තාව</h1><div class="sub">තාජක මාසික කේන්දරය (C6) · {year} වර්ෂයේ {month} වන මාසය</div>
      <div class="name">{esc(a.name)}</div>
      <div class="muted">මාස ප්‍රවේශය {esc(m["pravesha_local"])} ({esc(a.tz)})</div>
      <div style="margin:12pt auto 0 auto; width:104mm">{south_indian_html_si(labels, "මාස කුණ්ඩලිය", 104)}</div></div>''']
    H.append('<div class="pb"></div>' + _plain_month_c(d, a, year, month) + '<h2>1. මාසයේ ව්‍යුහය</h2>')
    H.append("<table>"
             f"<tr><td style='width:34%'><b>මාස ප්‍රවේශය</b></td><td>{esc(m['pravesha_local'])} — {f'රවි, උපන් විට සිටි තැනින් {30 * (month - 1)}° ඉදිරියට එන මොහොත' if month > 1 else 'වර්ෂ ප්‍රවේශයම'}</td></tr>"
             f"<tr><td><b>මාස ලග්නය</b></td><td>{SIGN_SI[mls]}</td></tr>"
             f"<tr><td><b>මාසේශ (මාසාධිපති)</b></td><td>{PLANET_SI[m['masesha']]} — {PLANET_NATURE_SI[m['masesha']]}</td></tr>"
             f"<tr><td><b>වර්ෂේශ</b></td><td>{PLANET_SI[v['varshesha']]}</td></tr>"
             f"<tr><td><b>වර්ෂ මුන්ථා</b></td><td>{SIGN_SI[inv[v['muntha']]]}</td></tr>"
             f"<tr><td><b>සුදර්ශන චක්‍ර අන්තර් රාශිය</b></td><td>{SIGN_SI[inv[m['sc_antar_sign']]]} — මේ මාසයේ ග්‍රහයන් මේ රාශියෙන් බලන්න</td></tr>"
             "</table>")
    H.append('<p class="small muted">වගුව කියවන හැටි: <b>මාස ලග්නය</b> = මාසය පටන් ගන්නා මොහොතේ ලග්නය; '
             '<b>මුන්ථා</b> = අවුරුද්දේ අවධානය පෙන්වන ලක්ෂ්‍යය; '
             '<b>සුදර්ශන චක්‍ර අන්තර් රාශිය</b> = මුන්ථාවේ සිට මාසයකට රාශියක් බැගින් යන රාශිය.</p>')
    # the month lord's sentence is in the simple-words box at the top (_plain_month_c)
    rows = []
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        sgn = inv[m["planets"][c]]
        rows.append(f"<tr><td>{PLANET_SI[c]}</td><td>{SIGN_SI[sgn]}</td><td>{jc.house_from(mls, sgn)}</td>"
                    f"<td>{SIGN_SI[P[c]['sign_idx']]} ({P[c]['house']})</td></tr>")
    H.append("<h3>මාස කුණ්ඩලියේ ග්‍රහ ස්ථාන</h3><table><tr><th>ග්‍රහයා</th><th>රාශිය</th><th>මාස භාවය</th><th>ජන්ම රාශිය (භාවය)</th></tr>"
             + "".join(rows) + "</table>")
    H.append('<p class="small muted">වගුව කියවන හැටි: <b>මාස භාවය</b> = මාසයේ කේන්දරයේ ග්‍රහයා සිටින භාවය; <b>ජන්ම රාශිය (භාවය)</b> = '
             'ඔබ උපන් විට ඒ ග්‍රහයා සිටි රාශිය සහ භාවය. මාස කුණ්ඩලිය වර්ෂ කුණ්ඩලියට යටත් වේ; වර්ෂ ඵල වාර්තාව (C1/C2) සමඟ එකට කියවන්න.</p>')
    H.append(note_block(notes, "summary", "ජ්‍යොතිෂවේදියාගේ විග්‍රහය"))
    H.append(note_block(notes, "upcoming", "මාසය තුළ අවධානය"))
    H.append(_gloss_method_c(_GLOSS_MONTH_C, _GLOSS_MONTH_EXTRA_C,
                             "තාජක මාසික කේන්දරය — P.V.R. Narasimha Rao, ch. 27.3, 28.7, 31. වාර්තා වර්ගය C6."))
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

    H = [f'''<div class="cover" style="padding-top:12mm">{LOGO_IMG}<div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">සම්පූර්ණ පොරොන්දම් වාර්තාව</h1><div class="sub">අෂ්ටකූට + කේන්දර දෙකේ සංයෝජන විග්‍රහය (D2)</div>
      <div class="name">{esc(nameA)} &nbsp;·&nbsp; {esc(nameB)}</div>
      <div style="margin:12pt 0; font-size:15pt"><b>{total} / 36</b> — {verdict}</div>
      <div class="two" style="margin-top:6pt"><div style="flex:1">{chart(PA, lsA, nameA, 80)}</div><div style="flex:1">{chart(PB, lsB, nameB, 80)}</div></div></div>''']

    # --- 1 birth data
    H.append('<div class="pb"></div>')
    plain_at = len(H)      # the "in simple words" box goes here once the whole match is worked out
    H.append('<h2>1. උපන් දත්ත</h2><table><tr><th></th><th>' + esc(nameA) + "</th><th>" + esc(nameB) + "</th></tr>"
             f'<tr><td><b>උපන් දිනය</b></td><td>{esc(a.date)}</td><td>{esc(a.match_date)}</td></tr>'
             f'<tr><td><b>වේලාව</b></td><td>{esc(a.time)}</td><td>{esc(a.match_time)}</td></tr>'
             f'<tr><td><b>ලග්නය</b></td><td>{SIGN_SI[lsA]} ({dms(dA["lagna"]["deg_in_sign"])})</td><td>{SIGN_SI[lsB]} ({dms(dB["lagna"]["deg_in_sign"])})</td></tr>'
             f'<tr><td><b>චන්ද්‍ර රාශිය</b></td><td>{SIGN_SI[PA["Mo"]["sign_idx"]]}</td><td>{SIGN_SI[PB["Mo"]["sign_idx"]]}</td></tr>'
             f'<tr><td><b>ජන්ම නැකත</b></td><td>{NAK_SI[jc.NAKSHATRAS.index(PA["Mo"]["nakshatra"])]} {PA["Mo"]["pada"]}</td>'
             f'<td>{NAK_SI[jc.NAKSHATRAS.index(PB["Mo"]["nakshatra"])]} {PB["Mo"]["pada"]}</td></tr>'
             f'<tr><td><b>ලග්නාධිපති</b></td><td>{PLANET_SI[jc.SIGN_LORD[lsA]]} — {PA[jc.SIGN_LORD[lsA]]["house"]} වැන්නේ</td>'
             f'<td>{PLANET_SI[jc.SIGN_LORD[lsB]]} — {PB[jc.SIGN_LORD[lsB]]["house"]} වැන්නේ</td></tr></table>'
             + _BIRTH_READ_DN.replace("නැකතෙනි.</p>", "නැකතෙනි (චන්ද්‍රයා සිටි තාරකා කොටස); <b>ලග්නාධිපති</b> = ලග්න රාශියේ අධිපති ග්‍රහයා සහ එය සිටින භාවය.</p>"))

    # --- 2 ashtakoota
    H.append("<h2>2. අෂ්ටකූට ලකුණු</h2>")
    krow = []
    for k in comp["kootas"]:
        si, meaning = KOOTA_SI.get(k["name"], (k["name"], ""))
        det = si_koota(k["detail"])
        krow.append(f"<tr><td>{si}</td><td>{meaning}</td><td><b>{k['points']}</b> / {k['max']}</td><td>{esc(det)}</td></tr>")
    H.append("<table><tr><th>කූටය</th><th>මනින දේ</th><th>ලකුණු</th><th>විස්තර</th></tr>" + "".join(krow)
             + f"<tr class='cur'><td colspan='2'><b>එකතුව</b></td><td><b>{total} / 36</b></td><td>{verdict}</td></tr></table>")
    H.append('<div class="note"><div class="lbl">ලකුණු කියවන ආකාරය</div>'
             '<p>අෂ්ටකූට ලකුණු ගැලපීමේ එක් ස්තරයක් පමණි: ලකුණු 36න් 24ක් හෝ වැඩි නම් හොඳ, 18–24 මධ්‍යම ලෙස සැලකේ. '
             'පහත කේන්දර දෙකේ සංයෝජනය (synastry), 7 වන භාවය, උපපද ලග්නය සහ දශා ගැලපීම '
             'ලකුණු එකතුවට වඩා ප්‍රායෝගික තොරතුරු දෙයි.</p></div>')
    H.append(porondam_block(comp, heading="h3") + (_PR_READ_DN if comp.get("visi_porondam") else ""))

    # --- 3 doshas
    H.append('<h2>3. දෝෂ සහ නිෂ්ප්‍රභ වීම්</h2>' + _DOSHA_INTRO_DN.replace("</p>", f" <b>කුජ දෝෂය</b> යනු {_KUJA_MEANING_DN}</p>"))
    dl = []
    for k in comp["kootas"]:
        if "dosha" in k["detail"].lower():
            nm = "භකූට දෝෂය" if k["name"] == "Bhakoot" else "නාඩි දෝෂය"
            canc = "cancel" in k["detail"].lower()
            dl.append(f"<li><b>{nm}</b> — " + (_CANC_YES_DN if canc else f"{_DOSHA_MEANING_DN[k['name']]}. {_CANC_NO_DN}") + "</li>")
    dl += _rajju_vedha_li_dn(comp)
    kuja_dn = []
    for nm_, P_, ls_ in ((nameA, PA, lsA), (nameB, PB, lsB)):
        hits, canc = mangal_check(P_, ls_)
        kuja_dn.append((nm_, hits, canc))
        if hits:
            dl.append(f"<li><b>කුජ දෝෂ ඇඟවීම — {esc(nm_)}</b>: කුජ {', '.join(f'{_KUJA_FROM_DN.get(k, k)} {v} වැන්නේ' for k, v in hits.items())}. "
                      + (f"නිෂ්ප්‍රභ වීමේ සාධක: {', '.join(canc)}." if canc
                         else "පැහැදිලි නිෂ්ප්‍රභ වීමේ සාධකයක් නැත; අනෙක් කේන්දරයේ කුජ ස්ථානය සමඟ එකට බැලිය යුතුයි.") + "</li>")
        else:
            dl.append(f"<li>කුජ දෝෂ ඇඟවීමක් නැත — {esc(nm_)}</li>")
    if all(h for _, h, _ in kuja_dn):
        dl.append("<li>දෙදෙනාගේම කේන්දරවල කුජ දෝෂ ඇඟවීම් ඇති නිසා, සම්ප්‍රදායික මතය අනුව ඒවා එකිනෙක සමබර වේ.</li>")
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
    H.append(f'<p class="small muted">වගුව කියවන හැටි: “{esc(nameA)} රාශිය” = {esc(nameA)} ගේ කේන්දරයේ එම ග්‍රහයා සිටින රාශිය; '
             f'“→ {esc(nameB)} භාවය” = එම රාශිය {esc(nameB)} ගේ ලග්නයෙන් කීවෙනි භාවයද යන්න (අනෙක් තීරු දෙක එලෙසම අනෙක් පැත්තට). '
             '<b>හිතකර</b> = සහාය; <b>අවධානය</b> = ඉවසීම සහ සන්නිවේදනය ඉල්ලන තැන; <b>මධ්‍යම</b> = සාමාන්‍ය.</p>')
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
    H.append('<p class="small muted">වගුව කියවන හැටි: 7 වන භාවය සහකරු සහ විවාහ ජීවිතය; 7 වන අධිපති = එම රාශියේ අධිපති ග්‍රහයා සහ එය සිටින තැන; '
             'උපපද ලග්නය (UL) විවාහයේ පිටතට පෙනෙන ස්වරූපය; '
             'දාරාකාරක (DK) සහකරු පිළිබඳ ජෛමිනි කාරකයා (වරහන් තුළ එය සිටින භාවය); ශුක්‍ර ආකර්ෂණය සහ රසිකත්වය.</p>')
    H.append('<h3>නවාංශක (D9) කේන්දර</h3>')
    H.append(f'<div class="two"><div style="flex:1">{varga_chart(dA, "D9", f"D9 · {nameA}", 80)}</div>'
             f'<div style="flex:1">{varga_chart(dB, "D9", f"D9 · {nameB}", 80)}</div></div>')
    v9A, v9B = dA["vargas"].get("D9"), dB["vargas"].get("D9")
    if v9A and v9B:
        H.append(f'<p class="small">D9 ලග්න: {esc(nameA)} — {SIGN_SI[inv[v9A["La"]]]}; {esc(nameB)} — {SIGN_SI[inv[v9B["La"]]]}. '
                 f'{esc(nameA)} ගේ D9 චන්ද්‍ර {SIGN_SI[inv[v9A["Mo"]]]}, {esc(nameB)} ගේ {SIGN_SI[inv[v9B["Mo"]]]}. '
                 'නවාංශකයේ (විවාහය බලන දෙවන කේන්දරයේ) ලග්න හෝ චන්ද්‍ර රාශි එකිනෙකට කේන්ද්‍ර/ත්‍රිකෝණ (1, 4, 7, 10 හෝ 5, 9 වැනි තැන්) '
                 'වීම දිගු කාලීන ගැලපීමට හිතකර ලෙස සලකනු ලැබේ — '
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
    H.append(f'<p class="small">විවාහ කාරක ග්‍රහයන් (විවාහය පෙන්වන ග්‍රහයන්: 7 වන අධිපති, ශුක්‍ර, දාරාකාරක සහ උපපද අධිපති) — {esc(nameA)}: {", ".join(PLANET_SI[p] for p in sorted(kA))}; '
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
        H.append('<p class="small">දෙදෙනාගේම විවාහ කාරක දශා එකවර ක්‍රියාත්මක වන කාල ඉහත දැක්වේ (දශාව තීරුවේ “X/Y” = X මහා දශාවේ '
                 'Y අන්තර් දශාව; “දින” = එම කාලය පවතින දින ගණන). ගුරු ගෝචරය (ගුරු ග්‍රහයා දැන් ගමන් කරන තැන) එම කාලවලට ගැලපේද යන්නත් බලන්න.</p>')
    else:
        H.append("<p>ඉදිරි වසර 6 තුළ දෙදෙනාගේම විවාහ කාරක දශා එකවර ක්‍රියාත්මක වන පැහැදිලි කවුළුවක් නැත; "
                 "එක් අයෙකුගේ දශාව සහ ගුරු ගෝචරය එකට ගැලපෙන කාල බලන්න. එයින් විවාහයට බාධාවක් අදහස් නොවේ.</p>")
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
    H.insert(plain_at, _d2_plain_dn(comp, total, kuja_dn, good, bad, overlap, tz))
    H.append(_gloss_disc_dn(_D2_TERMS_DN, _D2_GLOSS_DN, new_page=False, method_line="අෂ්ටකූට ගුණ මිලන, උපපද ලග්නය සහ චර කාරක — P.V.R. Narasimha Rao, ch. 6, 9, 26. වාර්තා වර්ගය D2. "
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
    H = [f'''<div class="cover" style="padding-top:12mm">{LOGO_IMG}<div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">ජන්ම කාල ශුද්ධි වාර්තාව</h1><div class="sub">උපන් වේලාව නිවැරදි කිරීම (E1)</div>
      <div class="name">{esc(a.name)}</div>
      <div class="muted">දෙන ලද වේලාව {esc(a.time)} · {esc(a.date)} · {esc(a.place or "")}</div>
      <div style="margin:12pt auto 0 auto; width:100mm">{south_indian_html_si(labels, "දෙන ලද වේලාවට D1", 100)}</div></div>''']
    H.append('<div class="pb"></div>' + plain_e1_pme(a, scan, wins, best) + '<h2>1. ක්‍රමවේදය</h2>')
    H.append('<div class="box">උපන් වේලාව මිනිත්තු කිහිපයකින් වෙනස් වූ විට ලග්නය (උපන් මොහොතේ නැගෙනහිරින් උදා වූ රාශිය), '
             'නවාංශක ලග්නය (D9 — රාශිය 9කට බෙදූ සියුම් කේන්දරයේ ලග්නය) සහ දශා (ජීවිතයේ කාල පරිච්ඡේද) ආරම්භය වෙනස් වේ. '
             'මේ වාර්තාවේ කරන්නේ: (1) දෙන ලද වේලාව වටා නියමිත පරාසයක සෑම වේලාවක්ම පරීක්ෂා කර, (2) ඔබ දුන් පසුගිය සිදුවීම් එක් එක් '
             'වේලාවකට අදාළ දශා සමඟ ගැලපේද බලා, (3) වැඩිම ගැලපීම ලැබෙන කාල කවුළු ඉදිරිපත් කිරීමයි.<br><br>'
             '<b>වැදගත්:</b> විම්ශෝත්තරී දශා ආරම්භය චන්ද්‍රගේ ස්ථානය මත රඳා පවතින නිසා පැයක් ඇතුළත එය බොහෝ දුරට එකමයි. '
             'වෙනස් වන්නේ <b>ලග්නය</b> — එබැවින් දශාධිපතීන් (දශා කාලය පාලනය කරන ග්‍රහයන්) කුමන භාවවලට (ජීවිත ක්ෂේත්‍රවලට) '
             'අධිපති වෙනවාද, කුමන භාවවල සිටිනවාද යන්නයි. '
             'ලකුණු වෙනස්කම් එන්නේ එතැනින්.<br><br>'
             '<b>මෙය ඇස්තමේන්තුවක්</b> — රෝහල් වාර්තාවක් තරම් නිශ්චිත නොවේ. සිදුවීම් වැඩි වන තරමට නිරවද්‍යතාව වැඩි වේ.</div>')
    H.append("<h2>2. ඔබ දුන් සිදුවීම්</h2><table><tr><th>#</th><th>සිදුවීම</th><th>දිනය</th><th>අදාළ භාව</th></tr>"
             + "".join(f"<tr><td>{i + 1}</td><td>{EVENT_TYPES[e['type']][0]}{(' — ' + esc(e['note'])) if e.get('note') else ''}</td>"
                       f"<td>{esc(e['date'])}</td><td>{', '.join(str(h) for h in EVENT_TYPES[e['type']][1])}</td></tr>"
                       for i, e in enumerate(events)) + "</table>")
    H.append('<p class="small muted">වගුව කියවන හැටි: <b>අදාළ භාව</b> = ඒ සිදුවීම කේන්දරයේ පෙන්වන ජීවිත ක්ෂේත්‍ර '
             '(උදා: 7 = විවාහය, 10 = රැකියාව).</p>')
    H.append('<div class="pb"></div><h2>3. වේලා පරීක්ෂාව</h2>')
    rows = []
    for s in scan:
        mark = " class=cur" if s["score"] == best else ""
        rows.append(f"<tr{mark}><td>{s['time']}</td><td>{s['off']:+d}</td><td>{SIGN_SI[s['lagna']]} {dms(s['lagna_deg'])}</td>"
                    f"<td>{SIGN_SI[s['d9']]}</td><td>{SIGN_SI[s['d10']]}</td><td><b>{s['score']}</b></td></tr>")
    H.append("<table><tr><th>වේලාව</th><th>වෙනස</th><th>ලග්නය</th><th>D9 ලග්නය</th><th>D10 ලග්නය</th><th>ගැලපීම් ලකුණු</th></tr>"
             + "".join(rows) + "</table>")
    H.append('<p class="small muted">වගුව කියවන හැටි: <b>වෙනස</b> = ඔබ දුන් වේලාවට වඩා මිනිත්තු කීයක් පසු (+) හෝ පෙර (−)ද; '
             '<b>D9 / D10 ලග්නය</b> = විවාහය සහ රැකියාව බලන සියුම් කේන්දරවල ලග්නය; තද පසුබිම් පේළි = ඉහළම ලකුණු. '
             'ලකුණු = සිදුවීම් දිනවලදී ක්‍රියාත්මක වූ මහා/අන්තර්/ප්‍රත්‍යන්තර දශාධිපතීන් එම සිදුවීමට අදාළ '
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
        H.append("<p>පරීක්ෂා කළ පරාසය තුළ වෙනසක් හඳුනාගත නොහැක.</p>")
    H.append('<div class="pb"></div><h2>5. සිදුවීම් අනුව විස්තරය</h2>')
    show = [s for s in scan if s["score"] == best][:1] + ([next(s for s in scan if s["off"] == 0)] if best != (next((s["score"] for s in scan if s["off"] == 0), None)) else [])
    for s in show:
        H.append(f"<h3>වේලාව {s['time']} ({s['off']:+d} මිනිත්තු) — ලග්නය {SIGN_SI[s['lagna']]}</h3>")
        H.append("<table><tr><th>සිදුවීම</th><th>දිනය</th><th>ලකුණු</th><th>ගැලපෙන දශාධිපතීන්</th></tr>"
                 + "".join(f"<tr><td>{EVENT_TYPES[t][0]}</td><td>{dt}</td><td>{hit}</td><td>{esc(why)}</td></tr>"
                           for t, dt, hit, why in s["detail"]) + "</table>")
    if show:
        H.append('<p class="small muted">වගුව කියවන හැටි: <b>MD / AD / PD</b> = සිදුවීම් දිනයේ ක්‍රියාත්මක වූ මහා / අන්තර් / '
                 'ප්‍රත්‍යන්තර දශාවේ අධිපති ග්‍රහයා, ඒ සිදුවීමේ භාවයකට අධිපති වීම හෝ එහි සිටීම; <b>(කාරක)</b> = ඒ සිදුවීම '
                 'ස්වභාවයෙන්ම පෙන්වන ග්‍රහයා (උදා: විවාහයට ශුක්‍ර); “—” = ගැලපීමක් නැත.</p>')
    H.append("<h2>6. ඊළඟ පියවර</h2><ul>"
             "<li>හැකි නම් රෝහල් උපන් සහතිකයේ වේලාව සොයා ගන්න — එය හොඳම මූලාශ්‍රයයි.</li>"
             "<li>තවත් පැහැදිලි දින සහිත සිදුවීම් 3–5ක් එකතු කළොත් කවුළුව පටු කර ගත හැක.</li>"
             "<li>වේලාව නිශ්චිත වන තුරු D9, D10, D60 මත පදනම් වූ අර්ථකථන ප්‍රවේශමෙන් කියවන්න; "
             "D1, දශා සහ ගෝචරය සාපේක්ෂව ස්ථාවරයි.</li></ul>")
    H.append(note_block(notes, "summary", "ජ්‍යොතිෂවේදියාගේ විග්‍රහය"))
    H.append('<div class="pb"></div><h2>වචන කිහිපයක තේරුම</h2>' + glossary_html(GLOSS_E1_SHARED_PME, GLOSS_E1_PME))
    H.append(disc_nopb_pme("ජන්ම කාල ශුද්ධි — විම්ශෝත්තරී දශා සහ භාව කාරකත්ව මත පදනම් වූ ඇස්තමේන්තු ක්‍රමයක්. "
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


_MUHURTA_MID = re.compile(r"(\S+)\s+(.+?)\s+(" + "|".join(jc.VARA) + r")\s+("
                          + "|".join(sorted(map(re.escape, jc.NAKSHATRAS), key=len, reverse=True)) + r")\s*(.*)$")


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
                # by name, not by gaps: "Mangala" fills the vara column and "Uttara Bhadrapada" overflows the
                # nakshatra one, so a single space can separate two columns
                named = _MUHURTA_MID.match(m.group(4).strip())
                mid = list(named.groups()) if named else re.split(r"\s{2,}", m.group(4).strip())
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


def muhurta_chart_html(a, when, best):
    """M1 section 3: the chart for the middle of the best window, drawn and tabled in Sinhala.
    (The engine prints it as English text for the astrologer; `best` holds those lines, used for the D-n note.)"""
    jd, _ = jc.to_jd_ut(datetime.strptime(when, "%Y-%m-%d %H:%M"), a.tz)
    pos, _ = jc.compute_positions(jd)
    ls = jc.sign_of(jc.compute_lagna(jd, a.lat, a.lon))
    labels, rows = {ls: ["ලග්න"]}, []
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        s = jc.sign_of(pos[c]["lon"])
        retro = " (වක්‍ර)" if pos[c].get("retro") and c not in ("Ra", "Ke") else ""
        labels.setdefault(s, []).append(PLANET_SI[c])
        rows.append(f"<tr><td>{PLANET_SI[c]}{retro}</td><td>{SIGN_SI[s]}</td>"
                    f"<td>{jc.dms(jc.deg_in_sign(pos[c]['lon']))}</td><td>{jc.house_from(ls, s)}</td></tr>")
    varga = ""
    for ln in best:
        m = re.search(r"D-(\d+) lagna (\w+); relevant houses \[([\d, ]+)\] in D-\d+: (.*)$", ln)
        if m:
            parts = []
            for hp in m[4].split("; "):
                h, _, who = hp.partition(": ")
                names = [PL_EN2SI.get(w.strip(), w.strip()) for w in who.split(",") if w.strip() not in ("", "-")]
                parts.append(f"{h.lstrip('h')} වැන්න: {', '.join(names) or 'හිස්'}")
            varga = (f'<p class="small">D-{m[1]} කේන්දරයේ ලග්නය {SIGN_EN2SI.get(m[2], m[2])}; '
                     f'කාර්යයට අදාළ භාව — {"; ".join(parts)}.</p>')
    return (f'<div class="two"><div style="flex:0 0 80mm">{south_indian_html_si(labels, f"මුහූර්ත කේන්දරය · {when}", 80)}</div>'
            '<div><table><tr><th>ග්‍රහයා</th><th>රාශිය</th><th>අංශක</th><th>භාවය</th></tr>' + "".join(rows) + "</table></div></div>"
            + varga
            + '<p class="small muted">කවුළුවේ මැද මොහොතේ ග්‍රහ පිහිටීම. ග්‍රහ ශක්තිය සාමාන්‍ය නියමවලට වඩා වැදගත් බැවින් (ch. 36.4), '
              'අවසන් තීරණයට පෙර මේ කේන්දරය ජන්ම කේන්දරයක් මෙන් පරීක්ෂා කිරීම සුදුසුයි.</p>')


def build_m1(a, notes, now_local, task, out_text, natal=None):
    rows, best, note = parse_muhurta_output(out_text)
    tsi = MUHURTA_TASK_SI.get(task, task)
    H = [f'''<div class="cover" style="padding-top:12mm">{LOGO_IMG}<div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:18pt">මුහූර්ත වාර්තාව</h1><div class="sub">සුබ මොහොත් (M1) — {esc(tsi)}</div>
      <div class="name" style="font-size:15pt">{esc(a.name)}</div>
      <div class="muted">පරාසය: {esc(a.muhurta_from)} සිට {esc(a.muhurta_to)} දක්වා · {esc(a.place or "")}</div>
      <div style="margin-top:18pt" class="muted">සොයාගත් සුබ කවුළු: <b>{len(rows)}</b></div></div>''']
    H.append('<div class="pb"></div>' + plain_m1_pme(a, rows, best, tsi) + '<h2>1. ක්‍රමවේදය</h2>')
    H.append('<div class="box">මෙහි භාවිත කර ඇත්තේ පරාශර සම්ප්‍රදායේ මුහූර්ත නියම (P.V.R. Narasimha Rao, ch. 36, වගුව 79) ය: '
             'කාර්යයට ගැලපෙන තිථි (චන්ද්‍ර දින), වාර (සතියේ දවස්), නක්ෂත්‍ර (චන්ද්‍රයා සිටින තාරකා කොටස්) සහ ලග්න '
             '(නැගෙනහිරින් උදා වන රාශිය); අදාළ භාවය හිස්ව තිබීම. ඊට අමතරව තාරා බලය (එදින නැකත ඔබේ උපන් නැකතට '
             'ගැලපීම — වගුව 64), හෝරාධිපති (ඒ පැයේ අධිපති ග්‍රහයා), කරණය (තිථියෙන් භාගයක්) සහ අදාළ භාවවල ග්‍රහ ශක්තිය '
             'අනුව ලකුණු දී ඇත.<br><br>'
             '<b>වැදගත්:</b> ලංකාවේ පාරම්පරික ලිත් නැකත් ක්‍රමය මෙයට වඩා වෙනස් ක්‍රමයකි (රාහු කාලය, සුබ දිශාව ආදිය). '
             'මේ වාර්තාව ලිත් නැකතට <b>දෙවන මතයක්</b> ලෙස සලකන්න; දෙකම එකට බැලීම හොඳයි.</div>')
    if note:
        H.append(f'<p class="small muted">කාර්යයට අදාළ විශේෂ නියමය: {esc(si_text(note))}</p>')
    H.append(f"<h2>2. සුබ කවුළු — {esc(tsi)}</h2>")
    if rows:
        # the weekday sits under the date, so the notes column gets room to breathe
        H.append("<table><tr><th>දිනය</th><th>වේලාව</th><th>ලග්නය</th><th>තිථි</th><th>නැකත</th><th>හෝරා</th><th>ලකුණු</th>"
                 "<th style='width:32%'>සටහන්</th></tr>"
                 + "".join(f"<tr{' class=cur' if r['score'] == max(x['score'] for x in rows) else ''}>"
                           f"<td>{r['date']}<br><span class='small'>{esc(VARA_SI2.get(r['vara'], si_text(r['vara'])))}</span></td>"
                           f"<td>{r['t0']}–{r['t1']}</td><td>{esc(si_text(r['lagna']))}</td>"
                           f"<td>{esc(si_text(r['tithi']))}</td><td>{esc(si_text(r['nak']))}</td>"
                           f"<td>{esc(si_text(r['hora']))}</td><td>{r['score']}</td>"
                           # one reason per line, each whole (cutting Sinhala mid-word can break a letter)
                           f"<td class='small'>{'<br>'.join(esc(si_text(x)).replace('(අශුභ)', '(නුසුදුසු)') for x in r['notes'].split('; ') if x)}</td></tr>"
                           for r in rows) + "</table>")
        H.append('<p class="small muted">වගුව කියවන හැටි: <b>සටහන්</b> = ලකුණු වැඩි/අඩු වූ හේතු; '
                 'තද පසුබිම = ඉහළම ලකුණු; හෝරා කිහිපයක් = කවුළුව පැය කිහිපයක් දිගුයි. '
                 'ලකුණු වැඩි කවුළු වඩාත් සුබ ලෙස සලකනු ලැබේ. කවුළුවක් තුළ ඕනෑම මොහොතක් ගත හැක; '
                 'කවුළුවේ මැද වඩාත් ආරක්ෂිතයි (ලග්න මාරුවෙන් දුරින්).</p>')
    else:
        H.append("<p>දෙන ලද පරාසය තුළ සියලු නියම සපුරන කවුළුවක් හමු නොවීය. දින පරාසය පුළුල් කිරීම හෝ "
                 "වේලා පරාසය 0–24 දක්වා විහිදුවීම උත්සාහ කරන්න.</p>")
    when = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", best[0]) if best else None
    H.append('<div class="vblock">')
    if when:
        H.append("<h2>3. හොඳම කවුළුවේ කේන්දරය</h2>")
        H.append(muhurta_chart_html(a, when.group(1), best))
    H.append("<h2>4. ප්‍රායෝගිකව</h2><ul>"
             "<li>කවුළුව තුළ කාර්යය <b>ආරම්භ</b> කිරීම ප්‍රමාණවත් — මුළු කාර්යයම එතුළ අවසන් විය යුතු නැත.</li>"
             "<li>දින දෙකක් සමාන ලකුණු ගත්තොත්, ඔබට ප්‍රායෝගිකව පහසු දිනය තෝරන්න.</li>"
             "<li>ලිත් නැකතක් ද ගන්නවා නම්, දෙකේම පොදු කාලයක් තෝරා ගැනීම හොඳයි.</li></ul></div>")
    H.append(note_block(notes, "summary", "ජ්‍යොතිෂවේදියාගේ සටහන"))
    H.append('<div class="pb"></div><h2>වචන කිහිපයක තේරුම</h2>' + glossary_html(GLOSS_M1_SHARED_PME, GLOSS_M1_PME))
    H.append(disc_nopb_pme("මුහූර්ත (නැකත්) — P.V.R. Narasimha Rao, ch. 36, වගුව 79 සහ 64. වාර්තා වර්ගය M1. "
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
    H = [f'''<div class="cover" style="padding-top:14mm">{LOGO_IMG}<div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
      <div class="brandtag">{esc(BRAND_TAGLINE)}</div>
      <h1 style="margin-top:16pt">නාම නක්ෂත්‍ර වාර්තාව</h1><div class="sub">නම් තැබීම සඳහා අකුරු (N)</div>
      <div class="name">{esc(a.name)}</div>
      <div class="muted">{esc(a.date)} · {esc(a.time)} · {esc(a.place or "")}</div>
      <div style="margin:16pt auto; font-size:34pt; color:#6b1010"><b>{esc(nm["sinhala"])}</b></div>
      <div class="muted">{NAK_SI[nak_i]} නැකත · {nm["pada"]} වන පාදය</div>
      <div style="margin:14pt auto 0 auto; width:94mm">{south_indian_html_si(labels, "D1 · රාශි චක්‍රය", 94)}</div></div>''']
    H.append('<div class="pb"></div>' + _n_plain_dn(nm, NAK_SI[nak_i]) + '<h2>1. නාම අකුර</h2>')
    H.append("<table>"
             f"<tr><td style='width:34%'><b>ජන්ම නැකත</b></td><td>{NAK_SI[nak_i]} ({esc(moon['nakshatra'])})</td></tr>"
             f"<tr><td><b>පාදය</b></td><td>{nm['pada']} වන පාදය</td></tr>"
             f"<tr><td><b>චන්ද්‍ර රාශිය</b></td><td>{SIGN_SI[moon['sign_idx']]}</td></tr>"
             f"<tr><td><b>නාම අකුර</b></td><td style='font-size:15pt'><b>{esc(nm['sinhala'])}</b> ({esc(nm['syllable'])})</td></tr>"
             "</table>")
    H.append(f'<div class="box">සම්ප්‍රදාය අනුව නම <b>{esc(nm["sinhala"])}</b> යන අකුරින් පටන් ගැනීම සුබ ලෙස සලකනු ලැබේ. '
             f'මෙය උපන් මොහොතේ චන්ද්‍රයා සිටි නැකතේ පාදය අනුව තීරණය වේ.</div>')
    H.append(f"<h2>2. {NAK_SI[nak_i]} නැකතේ පාද හතරේ අකුරු</h2><table><tr><th>පාදය</th><th>අකුර</th><th>ලතින්</th></tr>"
             + "".join(f"<tr{' class=cur' if i + 1 == nm['pada'] else ''}><td>{i + 1}</td><td style='font-size:13pt'>{esc(si_)}</td><td>{esc(la)}</td></tr>"
                       for i, (la, si_) in enumerate(nm["all_padas"])) + "</table>")
    H.append('<p class="small muted">වගුව කියවන හැටි: පාට කළ පේළිය දරුවා උපන් පාදයයි; “ලතින්” තීරුවේ ඇත්තේ එම අකුර ඉංග්‍රීසි අකුරින් ලියූ ආකාරයයි. '
             'මූලාශ්‍රය: අවකහඩ චක්‍රය (සම්භාව්‍ය නාම නක්ෂත්‍ර වගුව). මෙය ව්‍යාකරණ නීතියක් නොව සම්ප්‍රදායික යෝජනාවකි; '
             'නමේ අර්ථය සහ පවුලේ කැමැත්තද සලකා බලන්න.</p>')
    H.append("<h2>3. නම් තැබීමේ මොහොත</h2>")
    H.append('<p>නම් තැබීමේ උත්සවයට සුබ මොහොතක් අවශ්‍ය නම්, අපගේ <b>මුහූර්ත වාර්තාව (M1 — නම් තැබීම)</b> වෙන් වශයෙන් ලබාගත හැක. '
             'එහි තිථිය (චන්ද්‍ර මාසයේ දිනය), වාරය (සතියේ දිනය), නැකත සහ ලග්නය අනුව සුබ කාල (කවුළු) දක්වා ඇත.</p>')
    H.append(note_block(notes, "summary", "ජ්‍යොතිෂවේදියාගේ සටහන"))
    H.append(_gloss_disc_dn(("ලග්නය", "රාශිය", "නැකත සහ පාදය"), _N_GLOSS_DN, new_page=False, method_line="නාම නක්ෂත්‍රය — අවකහඩ චක්‍රය (සම්භාව්‍ය සම්ප්‍රදාය; ව්‍යාපෘතියේ ප්‍රධාන ග්‍රන්ථයේ නොමැත). වාර්තා වර්ගය N."))
    return "\n".join(H)


# ================================================================ D3 — Multi-match comparison
def build_d3(dA, partners, a, notes, now_local):
    """partners: list of (name, args-like dict, calc JSON with compatibility relative to A)."""
    PA, lsA = dA["planets"], dA["lagna"]["sign_idx"]
    inv = {s: i for i, s in enumerate(jc.SIGNS)}
    labels = {lsA: ["ලග්න"]}
    for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        labels.setdefault(PA[c]["sign_idx"], []).append(PLANET_SI[c])
    H = [f'''<div class="cover" style="padding-top:12mm">{LOGO_IMG}<div class="brandmark">{esc(BRAND)}</div><div class="brandline"></div>
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
                         lagna=lsB, moon=PB["Mo"]["sign_idx"], nak=PB["Mo"]["nakshatra"], mangal=bool(mh), mangal_c=bool(mc),
                         visi=(comp.get("visi_summary") or {}).get("match"), comp=comp))
    rows.sort(key=lambda r: (-r["total"], r["bad"] - r["good"]))
    H.append(_d3_plain_dn(rows))
    H.append("<table><tr><th>යෝජනාව</th><th>උපන් දිනය</th><th>ලග්නය</th><th>චන්ද්‍ර රාශිය</th><th>අෂ්ටකූට</th>"
             "<th>විසි පොරොන්දම</th><th>නිෂ්ප්‍රභ නොවූ දෝෂ</th><th>සංයෝජනය (හිතකර/ඝර්ෂණ)</th><th>කුජ දෝෂ</th></tr>"
             + "".join(f"<tr{' class=cur' if i == 0 else ''}><td><b>{esc(r['name'])}</b></td><td>{esc(r['meta']['date'])}</td>"
                       f"<td>{SIGN_SI[r['lagna']]}</td><td>{SIGN_SI[r['moon']]}</td><td><b>{r['total']:g}</b>/36</td>"
                       f"<td>{'—' if r['visi'] is None else str(r['visi']) + '/20'}</td>"
                       f"<td>{', '.join('භකූට' if x == 'Bhakoot' else 'නාඩි' for x in r['doshas']) or '—'}</td>"
                       f"<td>{r['good']} / {r['bad']}</td>"
                       f"<td>{'ඇත' + (' (නිෂ්ප්‍රභ සාධක ඇත)' if r['mangal_c'] else '') if r['mangal'] else 'නැත'}</td></tr>"
                       for i, r in enumerate(rows)) + "</table>")
    H.append('<p class="small muted">වගුව කියවන හැටි: යෝජනා අෂ්ටකූට ලකුණු අනුව (වැඩිම ලකුණු ඉහළින්) පෙළගස්වා ඇත. '
             '<b>නිෂ්ප්‍රභ නොවූ දෝෂ</b> = බලය නැති නොවූ භකූට හෝ නාඩි දෝෂ; <b>සංයෝජනය</b> = ග්‍රහයන් එකිනෙකාගේ කේන්දරයේ '
             'හිතකර / ඝර්ෂණ තැන්වලට වැටෙන වාර ගණන (14න්); <b>කුජ දෝෂ</b> = යෝජිත අයගේ කේන්දරයේ. '
             'ලකුණු එකතුව පමණක් නොව දෝෂ සහ සංයෝජනයද බලන්න.</p>')
    H.append('<div class="pb"></div><h2>2. කූට අනුව විස්තර</h2>')
    knames = [k["name"] for k in rows[0]["kootas"]]
    H.append("<table><tr><th>කූටය</th>" + "".join(f"<th>{esc(r['name'])}</th>" for r in rows) + "</tr>"
             + "".join("<tr><td>" + KOOTA_SI.get(kn, (kn, ""))[0] + "</td>"
                       + "".join(f"<td>{next(k['points'] for k in r['kootas'] if k['name'] == kn)} / "
                                 f"{next(k['max'] for k in r['kootas'] if k['name'] == kn)}</td>" for r in rows) + "</tr>"
                       for kn in knames)
             + "<tr class='cur'><td><b>එකතුව</b></td>" + "".join(f"<td><b>{r['total']:g}/36</b></td>" for r in rows) + "</tr></table>")
    H.append('<p class="small muted">වගුව කියවන හැටි: එක් එක් කූටයට ලැබුණු ලකුණු / එම කූටයේ උපරිම ලකුණු. '
             'එක් එක් කූටය මනින දේ “වචන කිහිපයක තේරුම” පිටුවේ ඇත.</p>')
    H.append('<div class="note"><div class="lbl">තීරණය ගැන</div><p>ලකුණු වැඩිම යෝජනාව හොඳම එක යැයි කියන්නට බැහැ. '
             'නිෂ්ප්‍රභ නොවූ දෝෂ, සංයෝජනයේ ඝර්ෂණ ස්ථාන සහ දෙදෙනාගේ දශා ගැලපීම එකට සලකා බැලිය යුතුයි. '
             'ඉහළම යෝජනා දෙක සඳහා සම්පූර්ණ පොරොන්දම් වාර්තාවක් (D2) ලබා ගැනීම යෝජනා කරමු.</p></div>')
    H.append(note_block(notes, "summary", "ජ්‍යොතිෂවේදියාගේ විග්‍රහය"))
    H.append(_gloss_disc_dn(("ලග්නය", "රාශිය", "නැකත සහ පාදය"), _D3_GLOSS_DN, new_page=False,
                            method_line="අෂ්ටකූට ගුණ මිලන — P.V.R. Narasimha Rao, ch. 26. වාර්තා වර්ගය D3. "
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


def safe_url_fetcher():
    """WeasyPrint URL fetcher that may load only data: URIs and files inside fonts/.

    Report HTML contains client input (name, place). It is escaped, but if markup ever got
    through, WeasyPrint would otherwise follow it: <a rel=attachment href=file:///...> embeds a
    server file in the PDF, and <img src=http://...> makes the server fetch URLs (SSRF). This
    fetcher makes both impossible regardless of escaping."""
    from urllib.parse import urlsplit
    from urllib.request import url2pathname
    from weasyprint.urls import URLFetcher

    fonts = Path(fontdir_global()).resolve()

    class FontsOnly(URLFetcher):
        def __init__(self):
            super().__init__(timeout=5, allowed_protocols={"file", "data"}, allow_redirects=False)

        def fetch(self, url, headers=None):
            parts = urlsplit(url)
            if parts.scheme == "file":
                path = Path(url2pathname(parts.path)).resolve()
                if parts.netloc not in ("", "localhost") or not path.is_relative_to(fonts):
                    raise ValueError(f"blocked: {url}")
            elif parts.scheme != "data":
                raise ValueError(f"blocked: {url}")
            return super().fetch(url, headers)

    return FontsOnly()


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


# QA reads glyph positions and fonts, so MuPDF must not apply the ActualText spans (jyotisha_pdftext.py):
# it scatters a word's ActualText over its glyphs and splits the line.
def _qa_flags(base):
    import pymupdf
    return base | getattr(pymupdf, "TEXT_IGNORE_ACTUALTEXT", 0)


def _text_spans(page):
    import pymupdf
    for b in page.get_text("dict", flags=_qa_flags(pymupdf.TEXTFLAGS_DICT))["blocks"]:
        for ln in b.get("lines", []):
            for s in ln["spans"]:
                yield s


def _raw_spans(page):
    import pymupdf
    for b in page.get_text("rawdict", flags=_qa_flags(pymupdf.TEXTFLAGS_RAWDICT))["blocks"]:
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
    pdf = HTML(string=html, base_url=HERE, url_fetcher=safe_url_fetcher()).write_pdf()
    page = pymupdf.open(stream=pdf, filetype="pdf")[0]
    # the whole probe line, left edge of its first span to right edge of its last (the ActualText word
    # spans of jyotisha_pdftext.py make MuPDF start a new span at each word)
    spans = [s for s in _text_spans(page) if abs(s["size"] - QA_PROBE_PT) < 0.5]
    if spans:
        ratio = (max(s["bbox"][2] for s in spans) - min(s["bbox"][0] for s in spans)) / spans[0]["size"]
        return ratio, abs(ratio - ref) / ref <= QA_PROBE_TOL, spans[0]["font"]
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
    ap.add_argument("--lang", choices=["si", "en"], default="si", help="report language; English is available for G")
    ap.add_argument("--node", choices=["mean", "true"], default="mean",
                    help="Rahu/Ketu: mean node (default, the project standard) or true node")
    ap.add_argument("--role", choices=["boy", "girl"], default="boy",
                    help="D1/D2/D3: the main person is the groom (boy) or the bride (girl); Ashtakoota depends on it")
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
    if a.lang == "en" and a.report != "G":
        sys.exit("--lang en is available for the G report only")

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
        page = with_thead(page)
        if a.html:
            open(a.html, "w", encoding="utf-8").write(page)
        from weasyprint import HTML
        jyotisha_pdftext.install()   # copyable Sinhala text
        HTML(string=page, base_url=HERE, url_fetcher=safe_url_fetcher()).write_pdf(a.out)
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
        extra += [f"--match-name={a.match_name or ''}", "--match-date", a.match_date, "--match-time", a.match_time,
                  "--match-lat", str(a.match_lat), "--match-lon", str(a.match_lon), "--match-tz", a.match_tz,
                  "--role", a.role]
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
        body = build_g_en(d, a, now_local) if a.lang == "en" else build_g(d, a, now_local)
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
                          [f"--match-name={pa.match_name}", "--match-date", pa.match_date, "--match-time", pa.match_time,
                           "--match-lat", str(pa.match_lat), "--match-lon", str(pa.match_lon), "--match-tz", pa.match_tz,
                           "--role", a.role])
            pb = _copy.copy(a)
            pb.report, pb.name = "A1", p.get("name", "—")
            pb.date, pb.time, pb.lat, pb.lon, pb.tz = p["date"], p["time"], p["lat"], p["lon"], p.get("tz", a.tz)
            dj["_partner_chart"] = run_calc(pb, now_local.year, now_local.year + 1, workdir)
            parts.append((p.get("name", "—"), p, dj))
        body = build_d3(d, parts, a, notes, now_local)
    else:
        body = build_p1(d, a, notes, now_local, a.shat_topic, a.matter)
    css = CSS.replace("FONTDIR", font_uri()).replace("BRANDNAME", BRAND)
    if a.lang == "en":   # English page numbers, and Latin text set in Noto Sans rather than the Sinhala font's Latin
        css = css.replace('content: "පිටුව " counter(page)', 'content: "Page " counter(page)') + CSS_EN
    page = f'<!DOCTYPE html><html lang="{a.lang}"><head><meta charset="utf-8"><title>{esc(a.name)} — {esc(BRAND)} {esc(a.report)}</title><style>{css}{CHART_CSS}</style></head><body>{body}</body></html>'
    page = with_thead(page)
    if a.html:
        open(a.html, "w", encoding="utf-8").write(page)
    from weasyprint import HTML
    jyotisha_pdftext.install()   # copyable Sinhala text (ActualText spans)
    HTML(string=page, base_url=HERE, url_fetcher=safe_url_fetcher()).write_pdf(a.out)
    print(f"PDF written: {a.out}")
    if a.qa and not run_qa(a.out, a.qa_dir):
        sys.exit(3)


if __name__ == "__main__":
    main()
