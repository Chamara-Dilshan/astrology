"""The report catalogue shown on the website.

Every report type the generator (jyotisha_report.py) makes, with its Sinhala title (as printed on
the PDF), a short English line, its group in the menu, and the extra input it needs beyond the
person's birth details. A report only appears on the site once the form supports its inputs.
Prices come from prices.json (the same file the price-list PDF uses).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GROUPS = {
    "natal": "ජන්ම කේන්දර · Birth chart",
    "life": "ජීවන ක්ෂේත්‍ර · Life areas",
    "timing": "කාල විග්‍රහ · Timing",
    "year": "වාර්ෂික / මාසික · Year and month ahead",
    "match": "පොරොන්දම් · Marriage matching",
    "ask": "ප්‍රශ්න සහ මුහූර්ත · Questions and auspicious times",
}

# code: (group, Sinhala title, English line, extra input needed)
# extra input: None = birth details only. Others are added to the form phase by phase.
REPORTS = {
    "G":  ("natal", "ඔබේ කේන්දරයේ මූලික තොරතුරු", "Free 1-page summary", None),
    "A1": ("natal", "ජන්ම කේන්දර වාර්තාව – කේන්ද්‍ර සාර", "Natal report, 8 pages", None),
    "A2": ("natal", "සම්පූර්ණ කේන්දර විග්‍රහය", "Full natal report with Sripati bhava chart and Shadbala, 10 pages", None),
    "A3": ("natal", "ගැඹුරු කේන්දර විග්‍රහය", "Deep natal report: divisional charts, bhava chart, Shadbala and KP, 17 pages", None),
    "B1": ("life", "විවාහ විග්‍රහය", "Marriage and partner", None),
    "B2": ("life", "වෘත්තීය විග්‍රහය", "Career and business", None),
    "B3": ("life", "අධ්‍යාපන විග්‍රහය", "Education and exams", None),
    "B4": ("life", "ධන විග්‍රහය", "Wealth and income", None),
    "B5": ("life", "සන්තාන විග්‍රහය", "Children", None),
    "B6": ("life", "විදේශ විග්‍රහය", "Foreign travel and residence", None),
    "B7": ("life", "දේපල විග්‍රහය", "House, land and vehicles", None),
    "B8": ("life", "මාතෘ–පිතෘ විග්‍රහය", "Relationship with parents", None),
    "C3": ("timing", "සඩේ සති වාර්තාව", "Sade Sati: Saturn's 7½-year transit", None),
    "C4": ("timing", "දශා සන්ධි වාර්තාව", "Change of Maha Dasa", None),
    "N":  ("timing", "නාම නක්ෂත්‍ර වාර්තාව", "Letters for naming a child", None),
    "E1": ("timing", "ජන්ම කාල ශුද්ධි වාර්තාව", "Birth-time correction from past life events", "events"),
    "C1": ("year", "වාර්ෂික ඵල වාර්තාව", "Year ahead from your birthday (Tajaka annual chart)", "year"),
    "C2": ("year", "වාර්ෂික ඵල සහ ගෝචර", "Year ahead with transits and a month-by-month calendar", "year"),
    "C6": ("year", "මාස ඵල වාර්තාව", "One month ahead (Tajaka monthly chart)", "year_month"),
    "D1": ("match", "පොරොන්දම් වාර්තාව", "Marriage matching: the Sri Lankan 20 porondam and Ashtakoota (36)", "partner"),
    "D2": ("match", "සම්පූර්ණ පොරොන්දම් වාර්තාව", "Full matching: 20 porondam, Ashtakoota and both charts compared", "partner"),
    "D3": ("match", "පොරොන්දම් සංසන්දනය", "Compare 2–5 marriage proposals side by side (20 porondam and Ashtakoota)", "partners"),
    "P1": ("ask", "ප්‍රශ්න වාර්තාව", "Prashna: an answer from the chart of the moment you ask", "prashna"),
    "P2": ("ask", "ප්‍රශ්න වාර්තාව – ෂට්පංචාශිකා", "Detailed prashna with the Shatpanchasika rules", "prashna"),
    "M1": ("ask", "මුහූර්ත වාර්තාව", "Auspicious times for a purpose within a date range", "muhurta"),
}

# Choices for the prashna and muhurta inputs, with the report's own Sinhala labels
# (filled in from jyotisha_report by the web app, so the two never disagree).
PRASHNA_TOPICS = ["general", "travel", "abroad", "lost", "dispute", "health", "marriage", "subject", "rain"]
MUHURTA_HOURS = {"6-21": "6:00 – 21:00", "0-24": "දවස පුරා · all day"}
MUHURTA_MAX_DAYS = 62
EVENTS_MIN, EVENTS_MAX = 3, 12          # E1: the plan recommends 8-12 past events
# Time zone menu: Sri Lanka (the default), then places where Sri Lankans are often born or living
# abroad, then every zone. Asia/Colombo also covers Sri Lanka's clock changes of 1996-2006.
HOME_TZ = "Asia/Colombo"
COMMON_TIME_ZONES = {
    "Asia/Kolkata": "India", "Indian/Maldives": "Maldives", "Asia/Dubai": "UAE", "Asia/Qatar": "Qatar",
    "Asia/Riyadh": "Saudi Arabia", "Asia/Kuwait": "Kuwait", "Asia/Muscat": "Oman", "Asia/Bahrain": "Bahrain",
    "Asia/Jerusalem": "Israel", "Asia/Nicosia": "Cyprus", "Asia/Singapore": "Singapore",
    "Asia/Kuala_Lumpur": "Malaysia", "Asia/Seoul": "South Korea", "Asia/Tokyo": "Japan",
    "Australia/Sydney": "Australia – Sydney", "Australia/Melbourne": "Australia – Melbourne",
    "Australia/Brisbane": "Australia – Brisbane", "Australia/Adelaide": "Australia – Adelaide",
    "Australia/Perth": "Australia – Perth", "Pacific/Auckland": "New Zealand",
    "Europe/London": "United Kingdom", "Europe/Rome": "Italy", "Europe/Paris": "France",
    "Europe/Berlin": "Germany", "Europe/Zurich": "Switzerland", "Europe/Oslo": "Norway",
    "Europe/Stockholm": "Sweden", "America/Toronto": "Canada – Toronto", "America/Vancouver": "Canada – Vancouver",
    "America/New_York": "USA – Eastern", "America/Chicago": "USA – Central", "America/Denver": "USA – Mountain",
    "America/Los_Angeles": "USA – Pacific",
}
TZ_REGIONS = ("Africa/", "America/", "Antarctica/", "Asia/", "Atlantic/", "Australia/", "Europe/", "Indian/", "Pacific/")
# Report languages: every report is in Sinhala; these can also be made in English (jyotisha_report --lang).
LANGS = {"G": ("si", "en")}
LANG_NAMES = {"si": "සිංහල · Sinhala", "en": "English"}


def prices():
    """{code: price in LKR} from prices.json; G is always free."""
    try:
        p = json.loads((ROOT / "prices.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        p = {}
    return {c: v for c, v in p.items() if c in REPORTS and isinstance(v, (int, float))}


def entries(free_codes):
    """Catalogue entries for the page, in menu order, marking which are free to generate."""
    price = prices()
    out = []
    for code, (group, si, en, needs) in REPORTS.items():
        free = code in free_codes
        out.append({"code": code, "group": group, "si": si, "en": en, "needs": needs,
                    "free": free, "price": None if free else price.get(code), "langs": list(LANGS.get(code, ("si",)))})
    return out
