#!/usr/bin/env python3
"""
jyotisha_calc.py — Vedic (Jyotisha) chart calculator for the project.

Standards (fixed, do not change casually):
  * Swiss Ephemeris (pyswisseph), sidereal zodiac, LAHIRI ayanamsa
  * Whole-sign houses (Rasi = Bhava) for D1 and all divisional charts
  * MEAN Rahu/Ketu
  * Vimshottari dasha from Moon's nakshatra, 365.25-day years
  * Divisional charts per Parashara (as taught in P.V.R. Narasimha Rao's
    "Vedic Astrology: An Integrated Approach")
  * Chara karakas: 8-karaka scheme (with Rahu) by default; --karakas 7 for
    the 7-karaka scheme
  * Timezone: IANA zone name (e.g. Asia/Colombo). zoneinfo handles the
    Sri Lanka 1996-2006 offset changes automatically.

Usage examples
  python3 jyotisha_calc.py --name "Dilshan" --date 1995-03-03 --time 04:04 \
      --lat 7.9403 --lon 81.0188 --tz Asia/Colombo --place "Polonnaruwa"
  ... --vargas D9,D10,D7          # only some vargas
  ... --json out.json              # also write machine-readable JSON
  ... --svg chart.svg              # South-Indian D1 chart as SVG
  ... --transit 2026-09-08         # sidereal transit positions for a date
  ... --dasha-depth 3              # maha/antar/pratyantar (default 2)
  ... --dasha-from 2024 --dasha-to 2032   # window of sub-periods to print
  ... --narayana [--narayana-from 2026 --narayana-to 2031]   # Narayana dasa (D1)
  ... --ashtakavarga                # BAV, SAV, Sodhita AV (reductions) + Sodhya pindas
  ... --varsha 2026                 # Tajaka annual chart for the solar year starting 2026
                                    # (varsha pravesha, muntha, harsha/panchavargiya bala,
                                    #  varshesha, sahams, mudda dasa)
  ... --transit 2026-09-08 (with natal data) # gochara from Lagna/Chandra + AV bindus
  ... --narayana-varga D9,D10      # Narayana dasa of divisional charts (textbook 18.5)
  ... --match-date 2001-05-14 --match-time 14:30 --match-lat 6.93 --match-lon 79.86 \
      [--match-tz Asia/Colombo --match-name "B" --role boy|girl]
                                    # Ashtakoota guna milan (Bhakoot/Nadi cancellations),
                                    # Mangal dosha both charts, D1/D9 synastry overlay
  ... --year-length savana         # 360-day Vimshottari years (textbook author's preference;
                                    #   default solar 365.25 d). Validate against life events.
  ... --time-scan 10               # birth-time sensitivity table (±10 min)
  ... --selftest                   # regression tests against textbook examples
  --- v2 additions (Sep 2026) ---
  ... --kalachakra                 # Kalachakra dasa + antardasas, deha/jeeva rasi, gatis (textbook ch.24)
  ... --ashtottari                 # Ashtottari dasa (108y) + applicability views (ch.17)
  ... --yogini                     # Yogini dasa (standard scheme; NOT in the textbook — secondary only)
  ... --sudasa                     # Sudasa from Sree Lagna (ch.20); HL/GL/SL printed with every chart (ch.5)
  ... --sudarsana                  # Sudarsana Chakra dasa sign per year of life (ch.31); also shown inside --varsha
  ... --nama                       # naming syllables from Chandra's nakshatra pada (Avakahada; Sinhala letters)
  ... --chart-type prashna|mundane # horary chart / nation-organisation-business chart (ch.35 significations,
      [--janma-nakshatra Mrigashira] [--compress-days 30]     #  Tajaka yogas, tara, compressed Vimshottari 35.4)
  ... --muhurta wedding --muhurta-from 2026-10-01 --muhurta-to 2026-11-30 --lat .. --lon .. --tz Asia/Colombo
      [--date/--time natal for tara+hora] [--janma-nakshatra ..] [--muhurta-hours 6-21] [--muhurta-top 15]
                                    # tasks: wedding griha_pravesha house_construction naming annaprashana
                                    #   vidyarambha upanayana idol_installation job business vehicle property travel general
                                    # Table 79 hard filters + tara/hora/karana/house-strength score (ch.36)
  Hora lord (1.3.11) is printed with every chart.
  --- v3 additions ---
  ... --yogas                      # full ch.11 detector: Ravi/Chandra/Mahapurusha/Nabhasa/popular/Raja/Dhana/Daridra
  ... --argala                     # argala & virodhargala on 12 houses, Shani and AK (ch.10)
  ... --upagrahas                  # Dhuma..Upaketu (Table 9), Kaala..Gulika/Maandi (Table 10)
  ... --kendradi                   # Lagna Kendradi Rasi dasa (ch.19)     ... --drigdasa  # Drigdasa (ch.21)
  ... --vimshottari-from lagna|kshema|utpanna|adhana   # Vimshottari variations (16.4)
  ... --varsha 2026 --masa 2       # Tajaka monthly chart + lord of the month + SC antardasa sign (27.3, 28.7, 31)
  ... --shashti 2026-09-10         # Tajaka sixty-hour chart containing that date (27.4)
  ... --ashtakavarga-varga D9,D10,D24   # BAV/SAV of divisional charts (Ex.99, 101)
  Special nakshatras (26.4.2) and HL/GL/SL in every varga row are printed automatically; --transit shows tara & special nakshatra.
  --- v3.1 ---
  ... --matter 7                   # Tajaka 29.2 significator ithasala for a matter (prashna chart, --varsha, --masa)
  ... --svg chart.svg --svg-vargas D9,D10   # extra South Indian SVGs chart_D9.svg, chart_D10.svg
  ... --ephe /path/to/ephe         # Swiss Ephemeris .se1 files; auto-detected from ./ephe next to the script
                                    #  (sepl_18, semo_18, seas_18 cover 1800-2400 AD; otherwise Moshier fallback)
  Muhurta window edges are refined by bisection to ~30 s (lagna/nakshatra/tithi ingress).
  Yogini dasa is cross-checked against PyJHora (JHora port) star map and antardasa order.
  ... --chart-type prashna --prashna-shat travel|abroad|lost|dispute|health|marriage|subject|rain|general
                                    # Shatpanchasika (Chappanna, Rao 1946 in project knowledge) stanza rules; verified on Rao's 1921 example
  ... --ayanamsa raman|kp|...      # comparison only (default Lahiri)      ... --sunrise centre  # disc-centre/no-refraction sunrise
  Panchanga (vara, tithi, yoga, karana, sunrise) is printed with every chart.
  Varsha Kundali now includes Tajaka yogas (Ithasala/Eesarpha/Manahoo/Kamboola/Nakta/Yamaya).
  Note: Vashya/Yoni/Gana point tables follow the common classical scheme; minor
  variations exist between texts.

Method sources: P.V.R. Narasimha Rao, "Vedic Astrology: An Integrated Approach"
  ch.5 special lagnas, ch.12 Ashtakavarga, ch.15.5 strength rules, ch.17 Ashtottari, ch.18 Narayana dasa,
  ch.20 Sudasa, ch.24 Kalachakra, ch.27-31 Tajaka & Sudarsana, ch.35 Mundane, ch.36 Muhurta.
Verified (--selftest, 43 checks): Table 40, Example 66, AV examples 40-43, Example 118, Ithasala examples,
  Kalachakra Examples 95-97 & Exercise 34, Tables 44-47, Ashtottari Example 59, Sree Lagna Example 10 &
  Exercise 10, hora example 1.3.11, Sudasa Example 77, Sudarsana Example 127, compressed dasa 35.4.
  v3 (--selftest 43 checks): Upagraha Example 6, Drigdasa Examples 80 & 82, Kendradi 19.2 examples, Argala 10.6 example,
  Vimshottari variants Example 51, Tajaka monthly/sixty-hour 27.3-27.4 times, natural benefics 3.3.
Kalachakra note: Table 45 in the textbook prints "Revati" where the 9-fold Parasara pattern (Tables 42/44/46/47)
  requires Uttarabhadrapada; the script follows the pattern (Revati = Savya-1, U.Bhadra = Savya-2).

Requires:  pip install pyswisseph --break-system-packages
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import os
import swisseph as swe


def setup_ephemeris(path=None):
    """Use Swiss Ephemeris .se1 files if found (./ephe next to the script, $SE_EPHE_PATH, or --ephe);
    otherwise pyswisseph silently falls back to the built-in Moshier model (~0.1" difference)."""
    cands = [path, os.environ.get("SE_EPHE_PATH"),
             os.path.join(os.path.dirname(os.path.abspath(__file__)), "ephe"),
             os.path.join(os.getcwd(), "ephe"), "/mnt/project/ephe", "/mnt/user-data/uploads/ephe"]
    for c in cands:
        if c and os.path.isdir(c) and any(f.endswith(".se1") for f in os.listdir(c)):
            swe.set_ephe_path(c)
            return c
    return None


EPHE_PATH = setup_ephemeris()

# --- global calculation settings (overridable from the CLI) ---
AYANAMSAS = {"lahiri": (swe.SIDM_LAHIRI, "Lahiri"), "raman": (swe.SIDM_RAMAN, "B.V. Raman"),
             "kp": (swe.SIDM_KRISHNAMURTI, "Krishnamurti (KP)"), "yukteshwar": (swe.SIDM_YUKTESHWAR, "Yukteshwar"),
             "true_chitra": (swe.SIDM_TRUE_CITRA, "True Chitrapaksha"), "fagan": (swe.SIDM_FAGAN_BRADLEY, "Fagan-Bradley")}
SID_MODE = swe.SIDM_LAHIRI
AYANAMSA_NAME = "Lahiri"
# sunrise: "limb" = upper limb with refraction (Swiss Ephemeris default, ~-0.833 deg);
#          "centre" = disc centre, no refraction (traditional Hindu panchanga / many Sri Lankan lithas)
RISE_BITS = 0
DAY_ALT = -0.833


def set_ayanamsa(key):
    global SID_MODE, AYANAMSA_NAME
    SID_MODE, AYANAMSA_NAME = AYANAMSAS[key]
    swe.set_sid_mode(SID_MODE)


def set_sunrise_mode(key):
    global RISE_BITS, DAY_ALT
    if key == "centre":
        RISE_BITS = swe.BIT_DISC_CENTER | swe.BIT_NO_REFRACTION
        DAY_ALT = 0.0
    else:
        RISE_BITS = 0
        DAY_ALT = -0.833


def ephemeris_mode():
    xx, rf = swe.calc_ut(2451545.0, swe.MOON, swe.FLG_SWIEPH)
    return f"Swiss Ephemeris files ({EPHE_PATH})" if rf & swe.FLG_SWIEPH else "Moshier fallback (no .se1 files found)"

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------
SIGNS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
         "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"]
SIGNS_EN = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORD = ["Ma", "Ve", "Me", "Mo", "Su", "Me", "Ve", "Ma", "Ju", "Sa", "Sa", "Ju"]

NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
              "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
              "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
              "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
              "Dhanishtha", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
              "Revati"]
# Vimshottari lord by nakshatra index (mod 9)
NAK_LORDS = ["Ke", "Ve", "Su", "Mo", "Ma", "Ra", "Ju", "Sa", "Me"]
DASHA_YEARS = {"Ke": 7, "Ve": 20, "Su": 6, "Mo": 10, "Ma": 7, "Ra": 18,
               "Ju": 16, "Sa": 19, "Me": 17}
YEAR_DAYS = 365.25

PLANETS = [("Su", swe.SUN), ("Mo", swe.MOON), ("Ma", swe.MARS), ("Me", swe.MERCURY),
           ("Ju", swe.JUPITER), ("Ve", swe.VENUS), ("Sa", swe.SATURN),
           ("Ra", swe.MEAN_NODE)]
PLANET_NAME = {"Su": "Surya", "Mo": "Chandra", "Ma": "Kuja", "Me": "Budha", "Ju": "Guru",
               "Ve": "Shukra", "Sa": "Shani", "Ra": "Rahu", "Ke": "Ketu", "La": "Lagna"}

EXALT = {"Su": 0, "Mo": 1, "Ma": 9, "Me": 5, "Ju": 3, "Ve": 11, "Sa": 6, "Ra": 2, "Ke": 8}  # Ra/Ke per textbook Table 6
DEBIL = {k: (v + 6) % 12 for k, v in EXALT.items()}
OWN = {"Su": [4], "Mo": [3], "Ma": [0, 7], "Me": [2, 5], "Ju": [8, 11], "Ve": [1, 6],
       "Sa": [9, 10], "Ra": [10], "Ke": [7]}
MOOLATRIKONA = {"Su": 4, "Mo": 1, "Ma": 0, "Me": 5, "Ju": 8, "Ve": 6, "Sa": 10}

# combustion orbs (degrees from Sun); (direct, retrograde)
COMBUST = {"Mo": (12, 12), "Ma": (17, 17), "Me": (14, 12), "Ju": (11, 11),
           "Ve": (10, 8), "Sa": (15, 15)}

VARGA_DIVISIONS = {"D2": 2, "D3": 3, "D4": 4, "D7": 7, "D9": 9, "D10": 10, "D12": 12,
                   "D16": 16, "D20": 20, "D24": 24, "D27": 27, "D30": 30, "D40": 40,
                   "D45": 45, "D60": 60}
DEFAULT_VARGAS = ["D2", "D3", "D4", "D7", "D9", "D10", "D12", "D24", "D30", "D60"]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def norm(x):
    return x % 360.0


def dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = int(round(((deg - d) * 60 - m) * 60))
    if s == 60:
        s = 0
        m += 1
    if m == 60:
        m = 0
        d += 1
    return f"{d:02d}°{m:02d}'{s:02d}\""


def sign_of(lon):
    return int(norm(lon) // 30)


def deg_in_sign(lon):
    return norm(lon) % 30


def nakshatra_of(lon):
    span = 360.0 / 27
    idx = int(norm(lon) // span)
    within = norm(lon) - idx * span
    pada = int(within // (span / 4)) + 1
    frac_done = within / span
    return idx, pada, frac_done


def sign_type(s):
    # 0 movable, 1 fixed, 2 dual
    return s % 3


def is_odd_sign(s):
    return s % 2 == 0  # Aries=0 is odd sign


def house_from(lagna_sign, sign):
    return (sign - lagna_sign) % 12 + 1


def to_jd_ut(local_dt, tzname):
    tz = ZoneInfo(tzname)
    aware = local_dt.replace(tzinfo=tz)
    ut = aware.astimezone(timezone.utc)
    jd = swe.julday(ut.year, ut.month, ut.day,
                    ut.hour + ut.minute / 60 + ut.second / 3600)
    return jd, aware.utcoffset()


def jd_to_datetime(jd):
    y, m, d, h = swe.revjul(jd)
    hh = int(h)
    mm = int((h - hh) * 60)
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


# --------------------------------------------------------------------------
# Divisional chart formulas (Parashara)
# --------------------------------------------------------------------------
def varga_sign(lon, div):
    s = sign_of(lon)
    d = deg_in_sign(lon)
    part = int(d // (30.0 / div))  # 0-based division index
    st = sign_type(s)
    odd = is_odd_sign(s)

    if div == 1:
        return s
    if div == 2:  # Hora: odd 0-15 Sun(Leo), 15-30 Moon(Cancer); even reversed
        if odd:
            return 4 if part == 0 else 3
        return 3 if part == 0 else 4
    if div == 3:  # Drekkana: 1st, 5th, 9th
        return (s + 4 * part) % 12
    if div == 4:  # Chaturthamsa: 1,4,7,10
        return (s + 3 * part) % 12
    if div == 7:  # Saptamsa: odd from same, even from 7th
        start = s if odd else (s + 6) % 12
        return (start + part) % 12
    if div == 9:  # Navamsa: movable same, fixed 9th, dual 5th
        start = s if st == 0 else ((s + 8) % 12 if st == 1 else (s + 4) % 12)
        return (start + part) % 12
    if div == 10:  # Dasamsa: odd same, even 9th
        start = s if odd else (s + 8) % 12
        return (start + part) % 12
    if div == 12:  # Dwadasamsa: from same sign
        return (s + part) % 12
    if div == 16:  # Shodasamsa: movable Aries, fixed Leo, dual Sag
        start = [0, 4, 8][st]
        return (start + part) % 12
    if div == 20:  # Vimsamsa: movable Aries, fixed Sag, dual Leo
        start = [0, 8, 4][st]
        return (start + part) % 12
    if div == 24:  # Chaturvimsamsa: odd from Leo, even from Cancer
        start = 4 if odd else 3
        return (start + part) % 12
    if div == 27:  # Bhamsa: fiery Aries, earthy Cancer, airy Libra, watery Cap
        start = [0, 3, 6, 9][s % 4]
        return (start + part) % 12
    if div == 30:  # Trimsamsa (unequal)
        if odd:
            bounds = [(5, 0), (10, 10), (18, 8), (25, 2), (30, 6)]  # Ma,Sa,Ju,Me,Ve
        else:
            bounds = [(5, 1), (12, 5), (20, 11), (25, 9), (30, 7)]  # Ve,Me,Ju,Sa,Ma
        for upper, sign in bounds:
            if d < upper:
                return sign
        return bounds[-1][1]
    if div == 40:  # Khavedamsa: odd from Aries, even from Libra
        start = 0 if odd else 6
        return (start + part) % 12
    if div == 45:  # Akshavedamsa: movable Aries, fixed Leo, dual Sag
        start = [0, 4, 8][st]
        return (start + part) % 12
    if div == 60:  # Shashtiamsa: from same sign
        return (s + part) % 12
    raise ValueError(f"Unsupported division D{div}")


# --------------------------------------------------------------------------
# Core chart computation
# --------------------------------------------------------------------------
def compute_positions(jd):
    swe.set_sid_mode(SID_MODE)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
    pos = {}
    for code, pid in PLANETS:
        xx, _ = swe.calc_ut(jd, pid, flags)
        pos[code] = {"lon": norm(xx[0]), "speed": xx[3], "retro": xx[3] < 0}
    pos["Ke"] = {"lon": norm(pos["Ra"]["lon"] + 180), "speed": pos["Ra"]["speed"],
                 "retro": True}
    pos["Ra"]["retro"] = True
    ayan = swe.get_ayanamsa_ut(jd)
    return pos, ayan


def compute_lagna(jd, lat, lon):
    swe.set_sid_mode(SID_MODE)
    cusps, ascmc = swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)
    return norm(ascmc[0])


def dignity(code, sign):
    if code in ("Ra", "Ke"):
        return ""
    if sign == EXALT[code]:
        return "Uchcha (exalted)"
    if sign == DEBIL[code]:
        return "Neecha (debilitated)"
    if MOOLATRIKONA.get(code) == sign:
        return "Moolatrikona/own"
    if sign in OWN[code]:
        return "Swakshetra (own)"
    return ""


def combust(code, pos):
    if code not in COMBUST:
        return False
    sun = pos["Su"]["lon"]
    diff = abs((pos[code]["lon"] - sun + 180) % 360 - 180)
    orb = COMBUST[code][1] if pos[code]["retro"] else COMBUST[code][0]
    return diff <= orb


def neecha_bhanga(code, pos, lagna_sign):
    """Return list of reasons for cancellation of debilitation (textbook rules)."""
    if code in ("Ra", "Ke"):
        return []
    s = sign_of(pos[code]["lon"])
    if s != DEBIL[code]:
        return []
    reasons = []
    moon_sign = sign_of(pos["Mo"]["lon"])
    kendras_l = {(lagna_sign + k) % 12 for k in (0, 3, 6, 9)}
    kendras_m = {(moon_sign + k) % 12 for k in (0, 3, 6, 9)}
    disp = SIGN_LORD[s]
    exalt_lord = [p for p, ex in EXALT.items() if ex == s and p not in ("Ra", "Ke")]
    for p in [disp] + exalt_lord:
        ps = sign_of(pos[p]["lon"])
        if ps in kendras_l:
            reasons.append(f"{PLANET_NAME[p]} in kendra from Lagna")
        if ps in kendras_m and p != "Mo":
            reasons.append(f"{PLANET_NAME[p]} in kendra from Chandra")
    if sign_of(pos[disp]["lon"]) == EXALT.get(disp):
        reasons.append(f"dispositor {PLANET_NAME[disp]} exalted")
    for p in exalt_lord:
        if sign_of(pos[p]["lon"]) == s:
            reasons.append(f"{PLANET_NAME[p]} (exalted here) conjunct")
    # exchange with the planet that is exalted in that sign
    for p in exalt_lord:
        if sign_of(pos[p]["lon"]) == DEBIL[p] and DEBIL[p] == EXALT[code]:
            reasons.append(f"exchange with {PLANET_NAME[p]}")
    return sorted(set(reasons))


def chara_karakas(pos, scheme=8):
    order8 = ["AK", "AmK", "BK", "MK", "PiK", "PK", "GK", "DK"]
    order7 = ["AK", "AmK", "BK", "MK", "PK", "GK", "DK"]
    items = []
    for code in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]:
        items.append((deg_in_sign(pos[code]["lon"]), code))
    if scheme == 8:
        items.append((30 - deg_in_sign(pos["Ra"]["lon"]), "Ra"))
        order = order8
    else:
        order = order7
    items.sort(reverse=True)
    return {order[i]: {"planet": items[i][1], "deg_in_sign": round(items[i][0], 4)}
            for i in range(len(order))}


def arudha_pada(house_sign, pos):
    """Arudha of a house (sign index). For Sc/Aq the stronger co-lord is used
    (textbook 15.5.1, rule 5b for arudhas)."""
    lord = primary_lord(house_sign, pos, purpose="arudha")
    lord_sign = sign_of(pos[lord]["lon"])
    dist = (lord_sign - house_sign) % 12
    pada = (lord_sign + dist) % 12
    if pada == house_sign or pada == (house_sign + 6) % 12:
        pada = (pada + 9) % 12
    return pada, lord


# --------------------------------------------------------------------------
# Jaimini rasi aspects & strength rules (textbook ch. 15.5)
# --------------------------------------------------------------------------
def rasi_aspects(a, b):
    """True if sign a aspects sign b (Jaimini rasi drishti)."""
    if a == b:
        return False
    ta, tb = sign_type(a), sign_type(b)
    adjacent = (b - a) % 12 in (1, 11)
    if ta == 2 and tb == 2:
        return True
    if ta == 0 and tb == 1 and not adjacent:
        return True
    if ta == 1 and tb == 0 and not adjacent:
        return True
    return False


def occupies_or_aspects(planet_code, target_sign, pos):
    ps = sign_of(pos[planet_code]["lon"])
    return ps == target_sign or rasi_aspects(ps, target_sign)


def planets_in_sign(sign, pos, codes=("Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke")):
    return [c for c in codes if sign_of(pos[c]["lon"]) == sign]


def advancement(code, pos):
    d = deg_in_sign(pos[code]["lon"])
    return 30 - d if code in ("Ra", "Ke") else d


def narayana_length_for(sign, lord, pos):
    """Dasa years for a rasi given a specific lord (used in co-lord tie-break)."""
    ls = sign_of(pos[lord]["lon"])
    if sign in (0, 1, 2, 6, 7, 8):      # Ar Ta Ge Li Sc Sg: forward
        count = (ls - sign) % 12 + 1
    else:                                 # Cn Le Vi Cp Aq Pi: backward
        count = (sign - ls) % 12 + 1
    yrs = 12 if count == 1 else count - 1
    if ls == EXALT[lord]:
        yrs += 1
    elif ls == DEBIL[lord]:
        yrs -= 1
    return yrs


def stronger_planet(p1, p2, pos, purpose="arudha", sign=None):
    """Textbook 15.5.1 rules for stronger of two planets. Returns winner code."""
    s1, s2 = sign_of(pos[p1]["lon"]), sign_of(pos[p2]["lon"])
    # (1) joined by more planets
    n1 = len(planets_in_sign(s1, pos)) - 1
    n2 = len(planets_in_sign(s2, pos)) - 1
    if n1 != n2:
        return p1 if n1 > n2 else p2
    # (2) conjoined/aspected by Jupiter, Mercury, dispositor
    def infl(p, s):
        c = 0
        disp = SIGN_LORD[s]
        for q in {"Ju", "Me", disp}:
            if q == p:
                continue
            if occupies_or_aspects(q, s, pos):
                c += 1
        return c
    i1, i2 = infl(p1, s1), infl(p2, s2)
    if i1 != i2:
        return p1 if i1 > i2 else p2
    # (3) exaltation
    e1, e2 = s1 == EXALT[p1], s2 == EXALT[p2]
    if e1 != e2:
        return p1 if e1 else p2
    # (4) natural strength of rasi: dual > fixed > movable
    r1, r2 = sign_type(s1), sign_type(s2)
    if r1 != r2:
        return p1 if r1 > r2 else p2
    # (5)
    if purpose == "dasa" and sign is not None:
        l1, l2 = narayana_length_for(sign, p1, pos), narayana_length_for(sign, p2, pos)
        if l1 != l2:
            return p1 if l1 > l2 else p2
    a1, a2 = advancement(p1, pos), advancement(p2, pos)
    return p1 if a1 >= a2 else p2


def primary_lord(sign, pos, purpose="arudha"):
    """Lord of a sign; for Sc (Ma/Ke) and Aq (Sa/Ra) the stronger co-lord."""
    if sign == 7:
        pair = ("Ma", "Ke")
    elif sign == 10:
        pair = ("Sa", "Ra")
    else:
        return SIGN_LORD[sign]
    in_sign = [p for p in pair if sign_of(pos[p]["lon"]) == sign]
    if len(in_sign) == 1:            # basic rule: if one co-lord is in the rasi, take the other
        return pair[0] if in_sign[0] == pair[1] else pair[1]
    return stronger_planet(pair[0], pair[1], pos, purpose, sign)


def stronger_rasi(a, b, pos, purpose="dasa"):
    """Textbook 15.5.2 rules. Returns the stronger sign index."""
    # (1) more planets
    na, nb = len(planets_in_sign(a, pos)), len(planets_in_sign(b, pos))
    if na != nb:
        return a if na > nb else b
    # (2) occupied/aspected by Jupiter, Mercury, lord
    def infl(s):
        lord = primary_lord(s, pos, purpose)
        return sum(1 for q in {"Ju", "Me", lord} if occupies_or_aspects(q, s, pos))
    ia, ib = infl(a), infl(b)
    if ia != ib:
        return a if ia > ib else b
    # (3) contains exalted planet
    ea = any(sign_of(pos[p]["lon"]) == EXALT[p] for p in planets_in_sign(a, pos))
    eb = any(sign_of(pos[p]["lon"]) == EXALT[p] for p in planets_in_sign(b, pos))
    if ea != eb:
        return a if ea else b
    # (4) lord in rasi of different oddity
    la, lb = primary_lord(a, pos, purpose), primary_lord(b, pos, purpose)
    da = is_odd_sign(sign_of(pos[la]["lon"])) != is_odd_sign(a)
    db = is_odd_sign(sign_of(pos[lb]["lon"])) != is_odd_sign(b)
    if da != db:
        return a if da else b
    # (5) dual > fixed > movable
    if sign_type(a) != sign_type(b):
        return a if sign_type(a) > sign_type(b) else b
    # (6) advancement of lords
    return a if advancement(la, pos) >= advancement(lb, pos) else b


# --------------------------------------------------------------------------
# Narayana Dasa (textbook ch. 18)
# --------------------------------------------------------------------------
ODD_FOOTED = {0, 1, 2, 6, 7, 8}


def narayana_progression(seed, pos):
    """Sequence of 12 dasa rasis from the dasa seed (Table 40 logic)."""
    ninth = (seed + 8) % 12
    forward = ninth in ODD_FOOTED
    occ = planets_in_sign(seed, pos)
    st = sign_type(seed)
    if "Sa" in occ:                 # Saturn exception: regular & zodiacal
        return [(seed + i) % 12 for i in range(12)]
    if "Ke" in occ:                 # Ketu exception: reverse direction
        forward = not forward
    d = 1 if forward else -1
    if st == 2:                     # trinal: seed,5,9 then from 10th, 7th, 4th
        seq = []
        for q in (0, 9, 6, 3):
            base = (seed + d * q) % 12
            seq += [(base + d * k) % 12 for k in (0, 4, 8)]
        return seq
    step = 1 if st == 0 else 5      # Brahma: successive; Shiva: every 6th
    return [(seed + d * step * i) % 12 for i in range(12)]


def narayana_length(sign, pos):
    lord = primary_lord(sign, pos, purpose="dasa")
    return narayana_length_for(sign, lord, pos), lord


def narayana_antardasas(dasa_sign, years, start, pos):
    seed7 = (dasa_sign + 6) % 12
    ad_seed = stronger_rasi(dasa_sign, seed7, pos)
    lord = primary_lord(ad_seed, pos, purpose="dasa")
    first = sign_of(pos[lord]["lon"])
    forward = is_odd_sign(first)
    occ = planets_in_sign(ad_seed, pos)
    if "Sa" in occ:
        forward = True
    elif "Ke" in occ:
        forward = not forward
    d = 1 if forward else -1
    seq = [(first + d * i) % 12 for i in range(12)]
    months = years  # each antardasa = years months
    out = []
    t = start
    for s in seq:
        end = t + timedelta(days=months * YEAR_DAYS / 12)
        out.append({"sign": s, "start": t, "end": end})
        t = end
    return out, ad_seed


def narayana_dasa(lagna_sign, pos, birth_utc, cycles=2, with_antar=True):
    seed = stronger_rasi(lagna_sign, (lagna_sign + 6) % 12, pos)
    seq = narayana_progression(seed, pos)
    lengths = {}
    for s in seq:
        lengths[s] = narayana_length(s, pos)
    dasas = []
    t = birth_utc
    for cyc in range(cycles):
        for s in seq:
            yrs, lord = lengths[s]
            if cyc == 1:
                yrs = 12 - yrs
            if yrs <= 0:
                continue
            end = t + timedelta(days=yrs * YEAR_DAYS)
            d = {"sign": s, "lord": lord, "years": yrs, "start": t, "end": end, "cycle": cyc + 1}
            if with_antar:
                d["antar"], d["ad_seed"] = narayana_antardasas(s, yrs, t, pos)
            dasas.append(d)
            t = end
    return seed, dasas


# --------------------------------------------------------------------------
# Ashtakavarga (Parashara bindu tables; textbook ch. 12)
# --------------------------------------------------------------------------
# For each planet: benefic houses counted from each reference (Su Mo Ma Me Ju Ve Sa La)
# Tables 19-25 of the textbook (Parasara's version; differs from Varahamihira for Moon & Venus)
AV_TABLE = {
    "Su": {"Su": [1, 2, 4, 7, 8, 9, 10, 11], "Mo": [3, 6, 10, 11], "Ma": [1, 2, 4, 7, 8, 9, 10, 11],
           "Me": [3, 5, 6, 9, 10, 11, 12], "Ju": [5, 6, 9, 11], "Ve": [6, 7, 12],
           "Sa": [1, 2, 4, 7, 8, 9, 10, 11], "La": [3, 4, 6, 10, 11, 12]},
    "Mo": {"Su": [3, 6, 7, 8, 10, 11], "Mo": [1, 3, 6, 7, 9, 10, 11], "Ma": [2, 3, 5, 6, 10, 11],
           "Me": [1, 3, 4, 5, 7, 8, 10, 11], "Ju": [1, 4, 7, 8, 10, 11, 12], "Ve": [3, 4, 5, 7, 9, 10, 11],
           "Sa": [3, 5, 6, 11], "La": [3, 6, 10, 11]},
    "Ma": {"Su": [3, 5, 6, 10, 11], "Mo": [3, 6, 11], "Ma": [1, 2, 4, 7, 8, 10, 11],
           "Me": [3, 5, 6, 11], "Ju": [6, 10, 11, 12], "Ve": [6, 8, 11, 12],
           "Sa": [1, 4, 7, 8, 9, 10, 11], "La": [1, 3, 6, 10, 11]},
    "Me": {"Su": [5, 6, 9, 11, 12], "Mo": [2, 4, 6, 8, 10, 11], "Ma": [1, 2, 4, 7, 8, 9, 10, 11],
           "Me": [1, 3, 5, 6, 9, 10, 11, 12], "Ju": [6, 8, 11, 12], "Ve": [1, 2, 3, 4, 5, 8, 9, 11],
           "Sa": [1, 2, 4, 7, 8, 9, 10, 11], "La": [1, 2, 4, 6, 8, 10, 11]},
    "Ju": {"Su": [1, 2, 3, 4, 7, 8, 9, 10, 11], "Mo": [2, 5, 7, 9, 11], "Ma": [1, 2, 4, 7, 8, 10, 11],
           "Me": [1, 2, 4, 5, 6, 9, 10, 11], "Ju": [1, 2, 3, 4, 7, 8, 10, 11], "Ve": [2, 5, 6, 9, 10, 11],
           "Sa": [3, 5, 6, 12], "La": [1, 2, 4, 5, 6, 7, 9, 10, 11]},
    "Ve": {"Su": [8, 11, 12], "Mo": [1, 2, 3, 4, 5, 8, 9, 11, 12], "Ma": [3, 4, 6, 9, 11, 12],
           "Me": [3, 5, 6, 9, 11], "Ju": [5, 8, 9, 10, 11], "Ve": [1, 2, 3, 4, 5, 8, 9, 10, 11],
           "Sa": [3, 4, 5, 8, 9, 10, 11], "La": [1, 2, 3, 4, 5, 8, 9, 11]},
    "Sa": {"Su": [1, 2, 4, 7, 8, 10, 11], "Mo": [3, 6, 11], "Ma": [3, 5, 6, 10, 11, 12],
           "Me": [6, 8, 9, 10, 11, 12], "Ju": [5, 6, 11, 12], "Ve": [6, 11, 12],
           "Sa": [3, 5, 6, 11], "La": [1, 3, 4, 6, 10, 11]},
}
AV_TOTALS = {"Su": 48, "Mo": 49, "Ma": 39, "Me": 54, "Ju": 56, "Ve": 52, "Sa": 39}




RASI_MULT = [7, 10, 8, 4, 10, 6, 7, 8, 9, 5, 11, 12]          # Table 28
GRAHA_MULT = {"Su": 5, "Mo": 5, "Ma": 8, "Me": 5, "Ju": 10, "Ve": 7, "Sa": 5}  # Table 29
SAME_LORD_PAIRS = [(0, 7), (1, 6), (2, 5), (8, 11), (9, 10)]


def trikona_sodhana(bav):
    out = list(bav)
    for t in range(4):
        idx = [t, t + 4, t + 8]
        vals = [out[i] for i in idx]
        if 0 in vals:
            continue
        low = min(vals)
        for i in idx:
            out[i] -= low          # equal values become all zero (rule 2 is a special case)
    return out


def ekadhipatya_sodhana(bav, pos):
    out = list(bav)
    occupied = {sign_of(pos[c]["lon"]) for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]}
    for a, b in SAME_LORD_PAIRS:
        va, vb = out[a], out[b]
        if va == 0 or vb == 0:
            continue
        oa, ob = a in occupied, b in occupied
        if oa and ob:
            continue
        if oa != ob:
            empty, full = (b, a) if oa else (a, b)
            if out[empty] < out[full]:
                out[empty] = 0
            else:
                out[empty] = out[full]
        else:
            if va == vb:
                out[a] = out[b] = 0
            else:
                hi = a if va > vb else b
                out[hi] = min(va, vb)
    return out


def sodhya_pinda(soav, pos):
    rasi_pinda = sum(soav[i] * RASI_MULT[i] for i in range(12))
    graha_pinda = sum(soav[sign_of(pos[c]["lon"])] * GRAHA_MULT[c] for c in GRAHA_MULT)
    return rasi_pinda, graha_pinda, rasi_pinda + graha_pinda


def ashtakavarga(pos, lagna_sign):
    refs = {c: sign_of(pos[c]["lon"]) for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]}
    refs["La"] = lagna_sign
    bav = {}
    for planet, table in AV_TABLE.items():
        bindus = [0] * 12
        for ref, houses in table.items():
            for h in houses:
                bindus[(refs[ref] + h - 1) % 12] += 1
        assert sum(bindus) == AV_TOTALS[planet], f"AV table error for {planet}"
        bav[planet] = bindus
    sav = [sum(bav[p][s] for p in bav) for s in range(12)]
    return bav, sav


# --------------------------------------------------------------------------
# Tajaka / Varsha Kundali (textbook ch. 27-30)
# --------------------------------------------------------------------------
NAT_FRIENDS = {"Su": {"Mo", "Ma", "Ju"}, "Mo": {"Su", "Me"}, "Ma": {"Su", "Mo", "Ju"},
               "Me": {"Su", "Ve"}, "Ju": {"Su", "Mo", "Ma"}, "Ve": {"Me", "Sa"}, "Sa": {"Me", "Ve"}}
NAT_ENEMIES = {"Su": {"Ve", "Sa"}, "Mo": set(), "Ma": {"Me"}, "Me": {"Mo"}, "Ju": {"Me", "Ve"},
               "Ve": {"Su", "Mo"}, "Sa": {"Su", "Mo", "Ma"}}
DEEP_EXALT = {"Su": 10, "Mo": 33, "Ma": 298, "Me": 165, "Ju": 95, "Ve": 357, "Sa": 200}
# Hadda lords (Table 72): list of (upper_bound_deg, lord) per sign
HADDA = [
    [(6, "Ju"), (12, "Ve"), (20, "Me"), (25, "Ma"), (30, "Sa")],
    [(8, "Ve"), (14, "Me"), (22, "Ju"), (27, "Sa"), (30, "Ma")],
    [(6, "Me"), (12, "Ve"), (17, "Ju"), (24, "Ma"), (30, "Sa")],
    [(7, "Ma"), (13, "Ve"), (19, "Me"), (26, "Ju"), (30, "Sa")],
    [(6, "Ju"), (11, "Ve"), (18, "Sa"), (24, "Me"), (30, "Ma")],
    [(7, "Me"), (17, "Ve"), (21, "Ju"), (28, "Ma"), (30, "Sa")],
    [(6, "Sa"), (14, "Me"), (21, "Ju"), (28, "Ve"), (30, "Ma")],
    [(7, "Ma"), (11, "Ve"), (19, "Me"), (24, "Ju"), (30, "Sa")],
    [(12, "Ju"), (17, "Ve"), (21, "Me"), (26, "Ma"), (30, "Sa")],
    [(7, "Me"), (14, "Ju"), (22, "Ve"), (26, "Sa"), (30, "Ma")],
    [(7, "Me"), (13, "Ve"), (20, "Ju"), (25, "Ma"), (30, "Sa")],
    [(12, "Ve"), (16, "Ju"), (19, "Me"), (28, "Ma"), (30, "Sa")],
]
TRIRASI = {0: ("Su", "Ju"), 1: ("Ve", "Mo"), 2: ("Sa", "Me"), 3: ("Ve", "Ma"), 4: ("Ju", "Su"),
           5: ("Mo", "Ve"), 6: ("Me", "Sa"), 7: ("Ma", "Ve"), 8: ("Sa", "Sa"), 9: ("Ma", "Ma"),
           10: ("Ju", "Ju"), 11: ("Mo", "Mo")}
MUDDA_ORDER = ["Su", "Mo", "Ma", "Ra", "Ju", "Sa", "Me", "Ke", "Ve"]
MUDDA_DAYS = {"Su": 18, "Mo": 30, "Ma": 21, "Ra": 54, "Ju": 48, "Sa": 57, "Me": 51, "Ke": 21, "Ve": 60}
TAJAKA_ASPECT = {1: ("conjunction", "strong malefic"), 3: ("sextile", "weak benefic"),
                 4: ("square", "weak malefic"), 5: ("trine", "strong benefic"),
                 7: ("opposition", "strong malefic"), 9: ("trine", "strong benefic"),
                 10: ("square", "weak malefic"), 11: ("sextile", "weak benefic"),
                 2: ("semi-sextile", "neutral"), 12: ("semi-sextile", "neutral"), 6: ("none", "none"), 8: ("none", "none")}


def sun_lon_at(jd):
    swe.set_sid_mode(SID_MODE)
    return norm(swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0])


def find_sun_at(target_lon, jd_guess):
    """Newton-iterate to the JD (UT) when sidereal Sun == target_lon near jd_guess."""
    jd = jd_guess
    for _ in range(30):
        diff = (target_lon - sun_lon_at(jd) + 180) % 360 - 180
        if abs(diff) < 1e-6:
            break
        jd += diff / 0.98565
    return jd


def relation(p, owner):
    if p == owner:
        return "own"
    if owner in NAT_FRIENDS.get(p, set()):
        return "friend"
    if owner in NAT_ENEMIES.get(p, set()):
        return "enemy"
    return "neutral"


def bala_by_relation(rel, own, friend, enemy):
    return {"own": own, "friend": friend, "neutral": friend, "enemy": enemy}[rel]


def pancha_vargeeya(pos):
    """Returns dict planet -> (total, components). Natural friendship is used for
    friend/enemy (the textbook does not fix a scheme); neutrals get friend value."""
    out = {}
    for p in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]:
        lon = pos[p]["lon"]
        s = sign_of(lon)
        d = deg_in_sign(lon)
        kshetra = bala_by_relation(relation(p, SIGN_LORD[s]), 30, 15, 7.5)
        debil_pt = (DEEP_EXALT[p] + 180) % 360
        diff = abs((lon - debil_pt + 180) % 360 - 180)
        uchcha = 20 * diff / 180
        hl = next(l for ub, l in HADDA[s] if d < ub)
        hadda = bala_by_relation(relation(p, hl), 15, 7.5, 3.75)
        drek = bala_by_relation(relation(p, SIGN_LORD[varga_sign(lon, 3)]), 10, 5, 2.5)
        nav = bala_by_relation(relation(p, SIGN_LORD[varga_sign(lon, 9)]), 5, 2.5, 1.25)
        total = (kshetra + uchcha + hadda + drek + nav) / 4
        out[p] = (round(total, 2), {"kshetra": kshetra, "uchcha": round(uchcha, 2),
                                    "hadda": hadda, "drekkana": drek, "navamsa": nav})
    return out


def harsha_bala(pos, lagna_sign, is_day):
    special = {"Su": 9, "Mo": 3, "Ma": 6, "Me": 1, "Ju": 11, "Ve": 5, "Sa": 12}
    fem = {"Mo", "Me", "Ve", "Sa"}
    out = {}
    for p in special:
        s = sign_of(pos[p]["lon"])
        h = house_from(lagna_sign, s)
        b = 0
        if h == special[p]:
            b += 5
        if s == EXALT[p] or s in OWN[p]:
            b += 5
        if (p in fem and h in (1, 2, 3, 7, 8, 9)) or (p not in fem and h in (4, 5, 6, 10, 11, 12)):
            b += 5
        if (is_day and p not in fem) or (not is_day and p in fem):
            b += 5
        out[p] = b
    return out


def saham(a, b, c, is_day, same_day_night=False):
    """A - B + C with the textbook's +30 rule; reversed at night unless flagged."""
    if not is_day and not same_day_night:
        a, b = b, a
    val = norm(a - b + c)
    # is C between B and A going zodiacally from B?
    arc_ba = (a - b) % 360
    arc_bc = (c - b) % 360
    if not (arc_bc <= arc_ba):
        val = norm(val + 30)
    return val


def sahams(pos, lagna, is_day):
    L = lagna
    ls = sign_of(L)
    P = {k: pos[k]["lon"] for k in pos}
    def house_lon(n):
        return norm(L + 30 * (n - 1))
    def lord_lon(n):
        return P[SIGN_LORD[(ls + n - 1) % 12]]
    out = {}
    out["Punya (fortune)"] = saham(P["Mo"], P["Su"], L, is_day)
    punya = out["Punya (fortune)"]
    out["Vidya (education)"] = saham(P["Su"], P["Mo"], L, is_day)
    out["Yasas (fame)"] = saham(P["Ju"], punya, L, is_day)
    out["Karma (work)"] = saham(P["Ma"], P["Me"], L, is_day)
    out["Vivaha (marriage)"] = saham(P["Ve"], P["Sa"], L, is_day)
    out["Putra (children)"] = saham(P["Ju"], P["Mo"], L, is_day)
    out["Artha (money)"] = saham(house_lon(2), lord_lon(2), L, is_day, True)
    out["Labha (gains)"] = saham(house_lon(11), lord_lon(11), L, is_day, True)
    out["Paradesa (foreign)"] = saham(house_lon(9), lord_lon(9), L, is_day, True)
    out["Rajya (position)"] = saham(P["Sa"], P["Su"], L, is_day)
    out["Roga (illness)"] = saham(L, P["Mo"], L, is_day)
    out["Vyapara (business)"] = saham(P["Ma"], P["Sa"], L, is_day, True)
    out["Matri (mother)"] = saham(P["Mo"], P["Ve"], L, is_day)
    out["Bhratri (siblings)"] = saham(P["Ju"], P["Sa"], L, is_day, True)
    return out


def is_daytime(jd, lat, lon):
    swe.set_sid_mode(SID_MODE)
    xx, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)
    az, alt_true, _ = swe.azalt(jd, swe.EQU2HOR, [lon, lat, 0], 0, 0, [xx[0], xx[1], xx[2]])
    return alt_true > DAY_ALT


def varsha_kundali(natal_sun_lon, natal_lagna_sign, birth_year, birth_month, birth_day, year,
                   lat, lon, tzname, moon_natal_lon):
    """Compute the Tajaka annual chart for the solar year starting in `year`."""
    completed = year - birth_year
    # guess: birthday in that year
    jd_guess = swe.julday(year, birth_month, min(birth_day, 28), 12.0)
    jd_vp = find_sun_at(natal_sun_lon, jd_guess)
    pos, _ = compute_positions(jd_vp)
    vlagna = compute_lagna(jd_vp, lat, lon)
    vls = sign_of(vlagna)
    day = is_daytime(jd_vp, lat, lon)
    muntha_sign = (natal_lagna_sign + completed) % 12
    hb = harsha_bala(pos, vls, day)
    pvb = pancha_vargeeya(pos)
    # Varshesha candidates
    lum = "Su" if day else "Mo"
    cands = [("lord of %s's rasi" % PLANET_NAME[lum], SIGN_LORD[sign_of(pos[lum]["lon"])]),
             ("natal lagna lord", SIGN_LORD[natal_lagna_sign]),
             ("Muntha lord", SIGN_LORD[muntha_sign]),
             ("varsha lagna lord", SIGN_LORD[vls]),
             ("trirasi lord", TRIRASI[vls][0 if day else 1])]
    cand_info = []
    for why, p in cands:
        ps = sign_of(pos[p]["lon"])
        h = (vls - ps) % 12 + 1  # house of lagna counted from planet
        asp_name, asp_kind = TAJAKA_ASPECT[h]
        cand_info.append({"planet": p, "why": why, "aspect_on_lagna": asp_name, "kind": asp_kind,
                          "pvb": pvb[p][0]})
    counts = {}
    for c in cand_info:
        counts[c["planet"]] = counts.get(c["planet"], 0) + 1
    benefic = [c for c in cand_info if "benefic" in c["kind"]]
    pool = benefic or [c for c in cand_info if c["kind"] not in ("none", "neutral")] or cand_info
    pool = sorted(pool, key=lambda c: (c["pvb"], counts[c["planet"]]), reverse=True)
    varshesha = pool[0]["planet"]
    # Mudda dasa
    nk, _, frac_done = nakshatra_of(moon_natal_lon)
    natal_lord = NAK_LORDS[nk % 9]
    idx = (MUDDA_ORDER.index(natal_lord) + completed) % 9
    seq = [MUDDA_ORDER[(idx + i) % 9] for i in range(9)]
    mudda = []
    jd_t = jd_vp
    sun_t = natal_sun_lon
    for i, p in enumerate(seq):
        days = MUDDA_DAYS[p] * ((1 - frac_done) if i == 0 else 1)
        sun_end = norm(sun_t + days)          # 1 solar day = 1 degree of Sun
        jd_end = find_sun_at(sun_end, jd_t + days * 1.0146)
        mudda.append({"lord": p, "start": jd_t, "end": jd_end, "solar_days": round(days, 2)})
        jd_t, sun_t = jd_end, sun_end
    return {"jd_vp": jd_vp, "pos": pos, "lagna": vlagna, "lagna_sign": vls, "day": day,
            "muntha": muntha_sign, "completed_years": completed, "harsha": hb, "pvb": pvb,
            "candidates": cand_info, "varshesha": varshesha, "sahams": sahams(pos, vlagna, day),
            "mudda": mudda}


def vimshottari(moon_lon, birth_dt_utc, depth=2, year_days=YEAR_DAYS):
    idx, _, frac_done = nakshatra_of(moon_lon)
    lord0 = NAK_LORDS[idx % 9]
    seq = ["Ke", "Ve", "Su", "Mo", "Ma", "Ra", "Ju", "Sa", "Me"]
    start_i = seq.index(lord0)
    balance_years = DASHA_YEARS[lord0] * (1 - frac_done)
    # Mahadasha list starts before birth so that the running dasha is complete
    md_start = birth_dt_utc - timedelta(days=(DASHA_YEARS[lord0] - balance_years) * year_days)
    periods = []
    t = md_start
    for k in range(9):
        lord = seq[(start_i + k) % 9]
        yrs = DASHA_YEARS[lord]
        end = t + timedelta(days=yrs * year_days)
        md = {"lord": lord, "start": t, "end": end, "sub": []}
        if depth >= 2:
            md["sub"] = sub_periods(lord, t, yrs, depth - 1, year_days)
        periods.append(md)
        t = end
    return lord0, balance_years, periods


def sub_periods(parent_lord, start, parent_years, depth, year_days=YEAR_DAYS):
    seq = ["Ke", "Ve", "Su", "Mo", "Ma", "Ra", "Ju", "Sa", "Me"]
    i0 = seq.index(parent_lord)
    out = []
    t = start
    for k in range(9):
        lord = seq[(i0 + k) % 9]
        yrs = parent_years * DASHA_YEARS[lord] / 120.0
        end = t + timedelta(days=yrs * year_days)
        p = {"lord": lord, "start": t, "end": end, "sub": []}
        if depth >= 2:
            p["sub"] = sub_periods(lord, t, yrs, depth - 1, year_days)
        out.append(p)
        t = end
    return out


# --------------------------------------------------------------------------
# Yogas (a few key ones; interpretation stays with the astrologer)
# --------------------------------------------------------------------------
def basic_yogas(pos, lagna_sign):
    notes = []
    mo = sign_of(pos["Mo"]["lon"])
    ju = sign_of(pos["Ju"]["lon"])
    if (ju - mo) % 12 in (0, 3, 6, 9):
        notes.append("Gaja-Kesari yoga (Guru in kendra from Chandra)")
    # Kemadruma: no planet (excl Sun, nodes) in 2nd/12th from Moon
    others = [c for c in ["Ma", "Me", "Ju", "Ve", "Sa"]
              if sign_of(pos[c]["lon"]) in ((mo + 1) % 12, (mo + 11) % 12)]
    if not others:
        notes.append("Kemadruma indication (no planets 2nd/12th from Chandra) — check cancellations")
    # Mangal dosha (from Lagna): Mars in 1,2,4,7,8,12
    h = house_from(lagna_sign, sign_of(pos["Ma"]["lon"]))
    if h in (1, 2, 4, 7, 8, 12):
        notes.append(f"Mangal dosha indication (Kuja in house {h} from Lagna) — check cancellations")
    # Kala Sarpa: all planets on one side of Rahu-Ketu axis
    ra = pos["Ra"]["lon"]
    side = [((pos[c]["lon"] - ra) % 360) < 180 for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]]
    if all(side) or not any(side):
        notes.append("Kala Sarpa yoga indication (all grahas within Rahu-Ketu axis)")
    # Budha-Aditya
    if sign_of(pos["Su"]["lon"]) == sign_of(pos["Me"]["lon"]):
        notes.append("Budha-Aditya yoga (Surya-Budha conjunct)")
    # Chandra-Mangala
    if sign_of(pos["Mo"]["lon"]) == sign_of(pos["Ma"]["lon"]):
        notes.append("Chandra-Mangala yoga")
    return notes


# --------------------------------------------------------------------------
# SVG South Indian chart
# --------------------------------------------------------------------------
def south_indian_svg(placements, title="D1"):
    """placements: dict sign_index -> list of labels (e.g. ['La','Su','Me(R)'])."""
    # South Indian fixed grid: Pisces top-left, going clockwise.
    grid = {11: (0, 0), 0: (1, 0), 1: (2, 0), 2: (3, 0),
            3: (3, 1), 4: (3, 2), 5: (3, 3), 6: (2, 3),
            7: (1, 3), 8: (0, 3), 9: (0, 2), 10: (0, 1)}
    cell = 110
    W = H = cell * 4
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
           f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fffdf7" stroke="#333" stroke-width="2"/>']
    for s, (cx, cy) in grid.items():
        x, y = cx * cell, cy * cell
        out.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="none" stroke="#333" stroke-width="1.5"/>')
        out.append(f'<text x="{x+4}" y="{y+13}" font-size="10" fill="#888" font-family="sans-serif">{SIGNS[s][:5]}</text>')
        labels = placements.get(s, [])
        for i, lab in enumerate(labels):
            col, row = i % 2, i // 2
            out.append(f'<text x="{x+8+col*52}" y="{y+34+row*18}" font-size="13" '
                       f'font-family="sans-serif" fill="{"#b00" if lab.startswith("La") else "#111"}">{lab}</text>')
    out.append(f'<text x="{W/2}" y="{H/2-6}" text-anchor="middle" font-size="18" font-family="serif" fill="#333">{title}</text>')
    out.append(f'<text x="{W/2}" y="{H/2+14}" text-anchor="middle" font-size="10" font-family="sans-serif" fill="#777">South Indian · Lahiri</text>')
    out.append("</svg>")
    return "\n".join(out)



# --------------------------------------------------------------------------
# Panchanga
# --------------------------------------------------------------------------
TITHI_NAMES = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami",
               "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi"]
YOGA_NAMES = ["Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda", "Sukarma",
              "Dhriti", "Shula", "Ganda", "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
              "Siddhi", "Vyatipata", "Variyan", "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha",
              "Shukla", "Brahma", "Indra", "Vaidhriti"]
KARANA_MOVABLE = ["Bava", "Balava", "Kaulava", "Taitila", "Garaja", "Vanija", "Vishti (Bhadra)"]
VARA = ["Ravi", "Soma", "Mangala", "Budha", "Guru", "Shukra", "Shani"]  # Sunday..Saturday


def panchanga(pos, jd, lat, lon, tzname):
    diff = norm(pos["Mo"]["lon"] - pos["Su"]["lon"])
    t = int(diff // 12)  # 0..29
    if t < 15:
        tithi = f"Shukla {TITHI_NAMES[t]}" if t < 14 else "Purnima"
    else:
        tithi = f"Krishna {TITHI_NAMES[t - 15]}" if t < 29 else "Amavasya"
    paksha = "Shukla" if t < 15 else "Krishna"
    yoga = YOGA_NAMES[int(norm(pos["Mo"]["lon"] + pos["Su"]["lon"]) // (360 / 27))]
    k = int(diff // 6)  # 0..59
    if k == 0:
        karana = "Kimstughna"
    elif k >= 57:
        karana = ["Shakuni", "Chatushpada", "Naga"][k - 57]
    else:
        karana = KARANA_MOVABLE[(k - 1) % 7]
    # vara: Hindu weekday changes at sunrise; find sunrise of the civil day
    swe.set_sid_mode(SID_MODE)
    local = jd_to_datetime(jd).astimezone(ZoneInfo(tzname))
    jd0, _ = to_jd_ut(datetime(local.year, local.month, local.day, 0, 0), tzname)
    try:
        _, tret = swe.rise_trans(jd0, swe.SUN, swe.CALC_RISE | RISE_BITS, [lon, lat, 0])
        sunrise_jd = tret[0]
    except Exception:
        sunrise_jd = None
    civil_wd = (local.weekday() + 1) % 7  # Monday=0 -> Sunday=0 scheme
    if sunrise_jd is not None and jd < sunrise_jd:
        civil_wd = (civil_wd - 1) % 7
        note = " (before sunrise: previous vara)"
    else:
        note = ""
    sunrise_txt = (jd_to_datetime(sunrise_jd).astimezone(ZoneInfo(tzname)).strftime("%H:%M")
                   if sunrise_jd else "?")
    return {"tithi": tithi, "paksha": paksha, "yoga": yoga, "karana": karana,
            "vara": VARA[civil_wd] + "vara" + note, "sunrise": sunrise_txt,
            "moon_phase_deg": round(diff, 2)}


# --------------------------------------------------------------------------
# Narayana dasa of divisional charts (textbook 18.5)
# --------------------------------------------------------------------------
def varga_positions(pos, div):
    """Pseudo-position dict where each planet's lon lies in its D-n sign
    (degree within sign kept from D1 for tie-break purposes only)."""
    out = {}
    for c, p in pos.items():
        out[c] = {"lon": varga_sign(p["lon"], div) * 30 + deg_in_sign(p["lon"]),
                  "speed": p["speed"], "retro": p["retro"]}
    return out


def varga_narayana(pos, lagna_sign, div, birth_utc):
    seed_house = ((div - 1) % 12) + 1          # D-n seed = nth house (mod 12)
    seed_sign_d1 = (lagna_sign + seed_house - 1) % 12
    lord = primary_lord(seed_sign_d1, pos, "dasa")
    vpos = varga_positions(pos, div)
    vlagna = sign_of(vpos[lord]["lon"])         # rasi of that lord in D-n acts as lagna
    seed, dasas = narayana_dasa(vlagna, vpos, birth_utc, cycles=2)
    return seed_house, seed_sign_d1, lord, vlagna, seed, dasas


# --------------------------------------------------------------------------
# Ashtakoota (guna milan) — classical Parashari/Muhurta tables
# --------------------------------------------------------------------------
VARNA = {3: 4, 7: 4, 11: 4, 0: 3, 4: 3, 8: 3, 1: 2, 5: 2, 9: 2, 2: 1, 6: 1, 10: 1}  # Brahmin 4 .. Shudra 1
VARNA_NAME = {4: "Brahmana", 3: "Kshatriya", 2: "Vaishya", 1: "Shudra"}
VASHYA_GROUPS = ["Chatushpada", "Manava", "Jalachara", "Vanachara", "Keeta"]
VASHYA_MATRIX = [[2, 1, 1, 0, 1], [1, 2, 0.5, 0, 1], [1, 0.5, 2, 1, 1], [0, 0, 1, 2, 0], [1, 1, 1, 0, 2]]
YONI_ANIMALS = ["Horse", "Elephant", "Sheep", "Serpent", "Dog", "Cat", "Rat", "Cow", "Buffalo",
                "Tiger", "Deer", "Monkey", "Mongoose", "Lion"]
NAK_YONI = ["Horse", "Elephant", "Sheep", "Serpent", "Serpent", "Dog", "Cat", "Sheep", "Cat", "Rat",
            "Rat", "Cow", "Buffalo", "Tiger", "Buffalo", "Tiger", "Deer", "Deer", "Dog", "Monkey",
            "Mongoose", "Monkey", "Lion", "Horse", "Lion", "Cow", "Elephant"]
YONI_MATRIX = [
    [4, 2, 2, 3, 2, 2, 2, 1, 0, 1, 3, 3, 2, 1],
    [2, 4, 3, 3, 2, 2, 2, 2, 3, 1, 2, 3, 2, 0],
    [2, 3, 4, 2, 1, 2, 1, 3, 3, 1, 2, 0, 3, 1],
    [3, 3, 2, 4, 2, 1, 1, 1, 1, 2, 2, 2, 0, 2],
    [2, 2, 1, 2, 4, 2, 1, 2, 2, 1, 0, 2, 1, 1],
    [2, 2, 2, 1, 2, 4, 0, 2, 2, 1, 3, 3, 2, 1],
    [2, 2, 1, 1, 1, 0, 4, 2, 2, 2, 2, 2, 1, 2],
    [1, 2, 3, 1, 2, 2, 2, 4, 3, 0, 3, 2, 2, 1],
    [0, 3, 3, 1, 2, 2, 2, 3, 4, 1, 2, 2, 2, 1],
    [1, 1, 1, 2, 1, 1, 2, 0, 1, 4, 1, 1, 2, 1],
    [3, 2, 2, 2, 0, 3, 2, 3, 2, 1, 4, 2, 2, 1],
    [3, 3, 0, 2, 2, 3, 2, 2, 2, 1, 2, 4, 3, 2],
    [2, 2, 3, 0, 1, 2, 1, 2, 2, 2, 2, 3, 4, 2],
    [1, 0, 1, 2, 1, 1, 2, 1, 1, 1, 1, 2, 2, 4]]
NAK_GANA = ["Deva", "Manushya", "Rakshasa", "Manushya", "Deva", "Manushya", "Deva", "Deva", "Rakshasa",
            "Rakshasa", "Manushya", "Manushya", "Deva", "Rakshasa", "Deva", "Rakshasa", "Deva",
            "Rakshasa", "Rakshasa", "Manushya", "Manushya", "Deva", "Rakshasa", "Rakshasa",
            "Manushya", "Manushya", "Deva"]
NAK_NADI = ["Adi", "Madhya", "Antya", "Antya", "Madhya", "Adi", "Adi", "Madhya", "Antya", "Antya",
            "Madhya", "Adi", "Adi", "Madhya", "Antya", "Antya", "Madhya", "Adi", "Adi", "Madhya",
            "Antya", "Antya", "Madhya", "Adi", "Adi", "Madhya", "Antya"]


def vashya_group(lon):
    s, d = sign_of(lon), deg_in_sign(lon)
    if s in (0, 1):
        return 0
    if s in (2, 5, 6, 10):
        return 1
    if s in (3, 11):
        return 2
    if s == 4:
        return 3
    if s == 7:
        return 4
    if s == 8:
        return 1 if d < 15 else 0
    if s == 9:
        return 0 if d < 15 else 2
    return 1


def planet_relation_simple(a, b):
    if a == b:
        return "same"
    if b in NAT_FRIENDS[a]:
        return "friend"
    if b in NAT_ENEMIES[a]:
        return "enemy"
    return "neutral"


def ashtakoota(boy_moon, girl_moon):
    """Returns (total, rows) for boy's and girl's Moon longitudes."""
    bs, gs = sign_of(boy_moon), sign_of(girl_moon)
    bn, _, _ = nakshatra_of(boy_moon)
    gn, _, _ = nakshatra_of(girl_moon)
    rows = []
    # 1 Varna
    v = 1 if VARNA[bs] >= VARNA[gs] else 0
    rows.append(("Varna", v, 1, f"{VARNA_NAME[VARNA[bs]]} / {VARNA_NAME[VARNA[gs]]}"))
    # 2 Vashya
    vb, vg = vashya_group(boy_moon), vashya_group(girl_moon)
    rows.append(("Vashya", VASHYA_MATRIX[vb][vg], 2, f"{VASHYA_GROUPS[vb]} / {VASHYA_GROUPS[vg]}"))
    # 3 Tara
    t1 = ((gn - bn) % 27 + 1) % 9 not in (3, 5, 7)
    t2 = ((bn - gn) % 27 + 1) % 9 not in (3, 5, 7)
    tara = 3 if (t1 and t2) else (1.5 if (t1 or t2) else 0)
    rows.append(("Tara", tara, 3, f"{NAKSHATRAS[bn]} / {NAKSHATRAS[gn]}"))
    # 4 Yoni
    yb, yg = YONI_ANIMALS.index(NAK_YONI[bn]), YONI_ANIMALS.index(NAK_YONI[gn])
    rows.append(("Yoni", YONI_MATRIX[yb][yg], 4, f"{NAK_YONI[bn]} / {NAK_YONI[gn]}"))
    # 5 Graha Maitri
    lb, lg = SIGN_LORD[bs], SIGN_LORD[gs]
    r1, r2 = planet_relation_simple(lb, lg), planet_relation_simple(lg, lb)
    rel = {r1, r2}
    if lb == lg or rel == {"friend"}:
        gm = 5
    elif rel == {"friend", "neutral"}:
        gm = 4
    elif rel == {"neutral"}:
        gm = 3
    elif rel == {"friend", "enemy"}:
        gm = 1
    elif rel == {"neutral", "enemy"}:
        gm = 0.5
    else:
        gm = 0
    rows.append(("Graha Maitri", gm, 5, f"{PLANET_NAME[lb]} ({r1}) / {PLANET_NAME[lg]} ({r2})"))
    # 6 Gana
    gb, gg = NAK_GANA[bn], NAK_GANA[gn]
    if gb == gg:
        gana = 6
    elif {gb, gg} == {"Deva", "Manushya"}:
        gana = 5
    elif {gb, gg} == {"Deva", "Rakshasa"}:
        gana = 1
    else:
        gana = 0
    rows.append(("Gana", gana, 6, f"{gb} / {gg}"))
    # 7 Bhakoot
    dist = (gs - bs) % 12 + 1
    bad = dist in (2, 12, 5, 9, 6, 8)
    bh = 0 if bad else 7
    note = f"{SIGNS[bs]} / {SIGNS[gs]} ({dist}/{(bs - gs) % 12 + 1})"
    if bad:
        if lb == lg or (r1 == "friend" and r2 == "friend"):
            note += " — Bhakoot dosha, cancelled (same/friendly lords)"
            bh = 7
        else:
            note += " — Bhakoot dosha"
    rows.append(("Bhakoot", bh, 7, note))
    # 8 Nadi
    nb, ng = NAK_NADI[bn], NAK_NADI[gn]
    nadi = 8
    note = f"{nb} / {ng}"
    if nb == ng:
        nadi = 0
        note += " — Nadi dosha"
        if bs == gs and bn != gn:
            nadi = 8
            note += ", cancelled (same rasi, different nakshatra)"
        elif bn == gn and bs != gs:
            nadi = 8
            note += ", cancelled (same nakshatra, different rasi)"
        elif bn == gn and bs == gs:
            _, pb, _ = nakshatra_of(boy_moon)
            _, pg, _ = nakshatra_of(girl_moon)
            if pb != pg:
                nadi = 8
                note += ", cancelled (same nakshatra & rasi, different pada)"
    rows.append(("Nadi", nadi, 8, note))
    total = sum(r[1] for r in rows)
    return total, rows


def synastry_overlay(posA, lagnaA, posB, lagnaB, label_a, label_b, div=1):
    """Where B's planets fall from A's lagna and Moon (in D-n), and vice versa."""
    pa = varga_positions(posA, div) if div != 1 else posA
    pb = varga_positions(posB, div) if div != 1 else posB
    la = varga_sign(lagnaA, div)
    lb = varga_sign(lagnaB, div)
    lines = []
    for src, dst, dl, dm, sl, dlbl in ((pb, pa, la, sign_of(pa["Mo"]["lon"]), label_b, label_a),
                                       (pa, pb, lb, sign_of(pb["Mo"]["lon"]), label_a, label_b)):
        parts = []
        for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
            s = sign_of(src[c]["lon"])
            parts.append(f"{PLANET_NAME[c][:5]}:{house_from(dl, s)}/{house_from(dm, s)}")
        lines.append(f"  {sl}'s grahas in {dlbl}'s houses (from La/from Mo): " + " ".join(parts))
    return lines



# --------------------------------------------------------------------------
# Tajaka yogas (textbook ch. 29): Ishkavala, Induvara, Ithasala, Eesarpha,
# Manahoo, Kamboola, Nakta, Yamaya
# --------------------------------------------------------------------------
DEEPTAMSA = {"Su": 15, "Mo": 12, "Ma": 8, "Me": 7, "Ju": 9, "Ve": 7, "Sa": 9}
SPEED_ORDER = ["Sa", "Ju", "Ma", "Su", "Ve", "Me", "Mo"]  # slow -> fast (7 Tajaka planets)


def tajaka_has_aspect(s1, s2):
    d = (s2 - s1) % 12 + 1
    return d not in (6, 8)


def tajaka_aspect_name(s1, s2):
    return TAJAKA_ASPECT[(s2 - s1) % 12 + 1][0]


def ithasala_between(p_fast, p_slow, pos):
    """Return ('poorna'|'vartamana'|'bhavishya'|'eesarpha'|None, diff) for a pair
    where p_fast is the faster planet. Uses deeptamsa orbs and the textbook's
    retrogression rules."""
    s_f, s_s = sign_of(pos[p_fast]["lon"]), sign_of(pos[p_slow]["lon"])
    if not tajaka_has_aspect(s_f, s_s):
        return None, None
    a_f, a_s = deg_in_sign(pos[p_fast]["lon"]), deg_in_sign(pos[p_slow]["lon"])
    orb = min(DEEPTAMSA[p_fast], DEEPTAMSA[p_slow])
    diff = a_s - a_f            # positive = faster is behind (applying)
    fast_retro = pos[p_fast]["retro"]
    if fast_retro:
        diff = -diff            # retrograde faster planet moves backward: rules invert
    if abs(diff) <= 1 and diff >= 0:
        return "poorna", diff
    if 0 <= diff <= orb:
        return "vartamana", diff
    if orb < diff <= orb + 1:
        return "bhavishya", diff
    if diff < 0 and abs(diff) <= orb:
        return "eesarpha", diff
    return None, diff


def tajaka_yogas(pos, lagna_sign):
    out = {"general": [], "ithasala": [], "eesarpha": [], "nakta_yamaya": []}
    houses = [house_from(lagna_sign, sign_of(pos[p]["lon"])) for p in SPEED_ORDER]
    if all(h in (1, 4, 7, 10, 2, 5, 8, 11) for h in houses):
        out["general"].append("Ishkavala yoga (all grahas in kendras/panapharas) — wealth, fortune")
    if all(h in (3, 6, 9, 12) for h in houses):
        out["general"].append("Induvara yoga (all grahas in apoklimas) — disappointments")
    pairs = {}
    for i, p_slow in enumerate(SPEED_ORDER):
        for p_fast in SPEED_ORDER[i + 1:]:
            kind, diff = ithasala_between(p_fast, p_slow, pos)
            pairs[(p_fast, p_slow)] = kind
            if kind is None:
                continue
            asp = tajaka_aspect_name(sign_of(pos[p_fast]["lon"]), sign_of(pos[p_slow]["lon"]))
            desc = (f"{PLANET_NAME[p_fast]} ({SIGNS[sign_of(pos[p_fast]['lon'])][:5]} "
                    f"{deg_in_sign(pos[p_fast]['lon']):.1f}°{' R' if pos[p_fast]['retro'] else ''}) – "
                    f"{PLANET_NAME[p_slow]} ({SIGNS[sign_of(pos[p_slow]['lon'])][:5]} "
                    f"{deg_in_sign(pos[p_slow]['lon']):.1f}°{' R' if pos[p_slow]['retro'] else ''}) "
                    f"{asp}, gap {abs(diff):.1f}°")
            if kind == "eesarpha":
                out["eesarpha"].append(desc)
                continue
            tags = [kind]
            # Manahoo: Sa/Ma conjunct the faster planet within its deeptamsa
            for m in ("Sa", "Ma"):
                if m in (p_fast, p_slow):
                    continue
                if sign_of(pos[m]["lon"]) == sign_of(pos[p_fast]["lon"]) and \
                        abs(deg_in_sign(pos[m]["lon"]) - deg_in_sign(pos[p_fast]["lon"])) <= DEEPTAMSA[p_fast]:
                    tags.append(f"MANAHOO by {PLANET_NAME[m]} (ithasala spoiled)")
            # Kamboola: Moon in ithasala with either planet
            if "Mo" not in (p_fast, p_slow):
                for q in (p_fast, p_slow):
                    k2, _ = ithasala_between("Mo", q, pos)
                    if k2 in ("poorna", "vartamana", "bhavishya"):
                        tags.append(f"Kamboola (Chandra ithasala with {PLANET_NAME[q]})")
                        break
            out["ithasala"].append(f"{desc} — {', '.join(tags)}")
    # Nakta / Yamaya for pairs without mutual aspect
    for i, p1 in enumerate(SPEED_ORDER):
        for p2 in SPEED_ORDER[i + 1:]:
            if tajaka_has_aspect(sign_of(pos[p1]["lon"]), sign_of(pos[p2]["lon"])):
                continue
            for p3 in SPEED_ORDER:
                if p3 in (p1, p2):
                    continue
                i3 = SPEED_ORDER.index(p3)
                faster_than_both = i3 > SPEED_ORDER.index(p2)
                slower_than_both = i3 < SPEED_ORDER.index(p1)
                if not (faster_than_both or slower_than_both):
                    continue
                def ith(a, b):
                    fa, sb = (a, b) if SPEED_ORDER.index(a) > SPEED_ORDER.index(b) else (b, a)
                    k, _ = ithasala_between(fa, sb, pos)
                    return k in ("poorna", "vartamana", "bhavishya")
                if ith(p3, p1) and ith(p3, p2):
                    nm = "Nakta" if faster_than_both else "Yamaya"
                    out["nakta_yamaya"].append(f"{nm}: {PLANET_NAME[p1]} – {PLANET_NAME[p2]} via {PLANET_NAME[p3]}"
                                               + (" (after delay)" if nm == "Yamaya" else ""))
    return out


# --------------------------------------------------------------------------
# Birth-time sensitivity scan
# --------------------------------------------------------------------------
def time_scan(local_dt, tzname, lat, lon, minutes, step=1):
    rows = []
    for off in range(-minutes, minutes + 1, step):
        dt = local_dt + timedelta(minutes=off)
        jd, _ = to_jd_ut(dt, tzname)
        pos, _ = compute_positions(jd)
        lag = compute_lagna(jd, lat, lon)
        nk, pd, frac = nakshatra_of(pos["Mo"]["lon"])
        rows.append({"off": off, "time": dt.strftime("%H:%M"), "lagna": lag,
                     "d9": varga_sign(lag, 9), "d10": varga_sign(lag, 10), "d60": varga_sign(lag, 60),
                     "d7": varga_sign(lag, 7), "d24": varga_sign(lag, 24),
                     "mo_nak": nk, "mo_pada": pd, "mo_frac": frac,
                     "sunrise_flag": ""})
    return rows


# --------------------------------------------------------------------------
# Kalachakra Dasa (textbook ch. 24; Parasara)
# --------------------------------------------------------------------------
# Table 43: the two 24-rasi wheels. Savya = main(Ar..Pi) + mirrored;
# Apasavya = mirrored + main (reversed).  Sign indices 0=Ar..11=Pi.
KC_SAVYA = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11,        # Ar Ta Ge Cn Le Vi Li Sc Sg Cp Aq Pi
            7, 6, 5, 3, 4, 2, 1, 0, 11, 10, 9, 8]        # Sc Li Vi Cn Le Ge Ta Ar Pi Aq Cp Sg
KC_APASAVYA = [8, 9, 10, 11, 0, 1, 2, 4, 3, 5, 6, 7,     # Sg Cp Aq Pi Ar Ta Ge Le Cn Vi Li Sc
               11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]     # Pi Aq Cp Sg Sc Li Vi Le Cn Ge Ta Ar
KC_YEARS = [7, 16, 9, 21, 5, 9, 16, 7, 10, 4, 4, 10]     # Table 48 by sign index
# Nakshatra type, 9-fold cycle (Table 42 triads; Tables 44-47):
#  A = Savya-1 (Aswini type, wheel offset 0)   B = Savya-2 (Bharani type, offset 12)
#  R = Apasavya-1 (Rohini type, offset 0)      M = Apasavya-2 (Mrigasira type, offset 12)
# NOTE: textbook Table 45 prints "Revati" where the 9-fold Parasara pattern (and Tables 42/44/46/47)
# require Uttarabhadrapada; Revati is Savya-1 like Aswini.  We follow the pattern.
KC_TYPE = ["A", "B", "A", "R", "M", "M", "A", "B", "A"]


def kalachakra_wheel(nak_idx):
    t = KC_TYPE[nak_idx % 9]
    wheel = KC_SAVYA if t in ("A", "B") else KC_APASAVYA
    offset = 0 if t in ("A", "R") else 12
    return t, wheel, offset


def kalachakra_pada_rasis(nak_idx, pada):
    """9 rasis for a nakshatra pada + start index in the 24-wheel (Tables 44-47)."""
    t, wheel, offset = kalachakra_wheel(nak_idx)
    start = (offset + (pada - 1) * 9) % 24
    rasis = [wheel[(start + i) % 24] for i in range(9)]
    savya = t in ("A", "B")
    deha, jeeva = (rasis[0], rasis[-1]) if savya else (rasis[-1], rasis[0])
    return rasis, start, wheel, savya, deha, jeeva


def kalachakra_gati(prev_sign, sign, savya):
    """Special leaps (24.3.3)."""
    pair = (prev_sign, sign)
    if pair in ((8, 0), (0, 8), (11, 7), (7, 11)):
        return "Simhavalokana (lion's leap)"
    if savya and pair == (3, 4):
        return "Markati (monkey's leap)"
    if not savya and pair == (4, 3):
        return "Markati (monkey's leap)"
    if savya and pair in ((5, 3), (4, 2)):
        return "Mandooki (frog's leap)"
    if not savya and pair in ((2, 4), (3, 5)):
        return "Mandooki (frog's leap)"
    return ""


def kalachakra_dasa(moon_lon, birth_dt_utc, year_days=YEAR_DAYS, n_dasas=12, with_antar=True):
    nak, pada, _ = nakshatra_of(moon_lon)
    span = 360.0 / 27
    pada_len = span / 4
    within_pada = (norm(moon_lon) - nak * span) - (pada - 1) * pada_len
    frac = within_pada / pada_len
    rasis, start, wheel, savya, deha, jeeva = kalachakra_pada_rasis(nak, pada)
    paramayush = sum(KC_YEARS[r] for r in rasis)
    elapsed = frac * paramayush
    cum = 0.0
    k = 0
    for k, r in enumerate(rasis):
        if cum + KC_YEARS[r] > elapsed + 1e-9:
            break
        cum += KC_YEARS[r]
    balance = cum + KC_YEARS[rasis[k]] - elapsed
    idx0 = start + k  # position in 24-wheel of the dasa running at birth
    dasas = []
    t = birth_dt_utc - timedelta(days=(KC_YEARS[rasis[k]] - balance) * year_days)
    prev_sign = wheel[(idx0 - 1) % 24]
    for i in range(n_dasas):
        idx = idx0 + i
        sign = wheel[idx % 24]
        yrs = KC_YEARS[sign]
        end = t + timedelta(days=yrs * year_days)
        d = {"sign": sign, "years": yrs, "start": t, "end": end,
             "gati": kalachakra_gati(prev_sign, sign, savya) if i > 0 else "", "antar": []}
        if with_antar:
            asigns = [wheel[(idx + j) % 24] for j in range(9)]
            tot = sum(KC_YEARS[s] for s in asigns)
            ta = t
            for s in asigns:
                ayrs = yrs * KC_YEARS[s] / tot
                aend = ta + timedelta(days=ayrs * year_days)
                d["antar"].append({"sign": s, "start": ta, "end": aend})
                ta = aend
        dasas.append(d)
        prev_sign = sign
        t = end
    return {"nakshatra": nak, "pada": pada, "frac_pada": frac, "type": kalachakra_wheel(nak)[0],
            "savya": savya, "pada_rasis": rasis, "paramayush": paramayush, "deha": deha, "jeeva": jeeva,
            "balance_years": balance, "dasas": dasas}


# --------------------------------------------------------------------------
# Ashtottari Dasa (textbook ch. 17, Table 39) — 108 years, 8 lords
# --------------------------------------------------------------------------
ASHT_ORDER = ["Su", "Mo", "Ma", "Me", "Sa", "Ju", "Ra", "Ve"]
ASHT_YEARS = {"Su": 6, "Mo": 15, "Ma": 8, "Me": 17, "Sa": 10, "Ju": 19, "Ra": 12, "Ve": 21}
# arcs start at Ardra (66°40'); Su 4 naks, Mo 3, Ma 4, Me 3, Sa 3, Ju 3, Ra 4, Ve 3
ASHT_ARC_NAKS = [4, 3, 4, 3, 3, 3, 4, 3]


def ashtottari_dasa(moon_lon, birth_dt_utc, year_days=YEAR_DAYS, with_antar=True):
    span = 360.0 / 27
    rel = norm(moon_lon - 5 * span)  # measured from start of Ardra
    acc = 0.0
    lord_i = 0
    for i, n in enumerate(ASHT_ARC_NAKS):
        arc = n * span
        if rel < acc + arc:
            lord_i = i
            break
        acc += arc
    lord = ASHT_ORDER[lord_i]
    arc = ASHT_ARC_NAKS[lord_i] * span
    frac_left = (acc + arc - rel) / arc
    balance = ASHT_YEARS[lord] * frac_left
    t = birth_dt_utc - timedelta(days=(ASHT_YEARS[lord] - balance) * year_days)
    dasas = []
    for k in range(8):
        L = ASHT_ORDER[(lord_i + k) % 8]
        yrs = ASHT_YEARS[L]
        end = t + timedelta(days=yrs * year_days)
        d = {"lord": L, "years": yrs, "start": t, "end": end, "antar": []}
        if with_antar:
            ta = t
            li = ASHT_ORDER.index(L)
            for j in range(1, 9):  # first antardasa = planet after dasa lord; last = dasa lord
                A = ASHT_ORDER[(li + j) % 8]
                ayrs = yrs * ASHT_YEARS[A] / 108.0
                aend = ta + timedelta(days=ayrs * year_days)
                d["antar"].append({"lord": A, "start": ta, "end": aend})
                ta = aend
        dasas.append(d)
        t = end
    return lord, balance, dasas


def ashtottari_applicability(pos, lagna_sign, is_day):
    """17.2.3 views (2) and (3)."""
    notes = []
    ra_s = sign_of(pos["Ra"]["lon"])
    ll = SIGN_LORD[lagna_sign]
    ll_s = sign_of(pos[ll]["lon"])
    h = (ra_s - ll_s) % 12 + 1
    view2 = ra_s != lagna_sign and h in (1, 4, 7, 10, 5, 9)
    notes.append(f"View 2 (Rahu not in Lagna, in kendra/trikona from Lagna lord): {'YES' if view2 else 'no'} "
                 f"(Rahu is {h}th from {PLANET_NAME[ll]})")
    diff = norm(pos["Mo"]["lon"] - pos["Su"]["lon"])
    krishna = diff >= 180
    view3 = (is_day and krishna) or ((not is_day) and (not krishna))
    notes.append(f"View 3 ({'day' if is_day else 'night'} birth in {'Krishna' if krishna else 'Shukla'} paksha): "
                 f"{'YES' if view3 else 'no'}")
    return notes


# --------------------------------------------------------------------------
# Yogini Dasa — NOT in the project textbook; standard scheme (36-year cycle)
# --------------------------------------------------------------------------
YOGINI = [("Mangala", "Mo", 1), ("Pingala", "Su", 2), ("Dhanya", "Ju", 3), ("Bhramari", "Ma", 4),
          ("Bhadrika", "Me", 5), ("Ulka", "Sa", 6), ("Siddha", "Ve", 7), ("Sankata", "Ra", 8)]


def yogini_dasa(moon_lon, birth_dt_utc, year_days=YEAR_DAYS, cycles=2, with_antar=True):
    nak, _, frac_done = nakshatra_of(moon_lon)
    y0 = (nak + 1 + 3) % 8  # (nakshatra number + 3) mod 8 -> 1 Mangala .. 0 Sankata
    i0 = (y0 - 1) % 8
    name, lord, yrs0 = YOGINI[i0]
    balance = yrs0 * (1 - frac_done)
    t = birth_dt_utc - timedelta(days=(yrs0 - balance) * year_days)
    out = []
    for k in range(8 * cycles):
        nm, L, yrs = YOGINI[(i0 + k) % 8]
        end = t + timedelta(days=yrs * year_days)
        d = {"yogini": nm, "lord": L, "years": yrs, "start": t, "end": end, "antar": []}
        if with_antar:
            ta = t
            ii = (i0 + k) % 8
            for j in range(8):
                an, al, ay = YOGINI[(ii + j) % 8]
                aend = ta + timedelta(days=yrs * ay / 36.0 * year_days)
                d["antar"].append({"yogini": an, "lord": al, "start": ta, "end": aend})
                ta = aend
        out.append(d)
        t = end
    return name, balance, out


# --------------------------------------------------------------------------
# Special lagnas (textbook ch. 5): Hora Lagna, Ghati Lagna, Sree Lagna
# --------------------------------------------------------------------------
def sunrise_before(jd, lat, lon):
    """JD of the most recent sunrise at or before jd (Hindu day starts at sunrise)."""
    swe.set_sid_mode(SID_MODE)
    try:
        _, tret = swe.rise_trans(jd - 1.2, swe.SUN, swe.CALC_RISE | RISE_BITS, [lon, lat, 0])
        sr = tret[0]
        while True:
            _, t2 = swe.rise_trans(sr + 0.01, swe.SUN, swe.CALC_RISE | RISE_BITS, [lon, lat, 0])
            if t2[0] > jd:
                return sr
            sr = t2[0]
    except Exception:
        return None


def special_lagnas(jd, lat, lon, lagna_lon, moon_lon):
    sr = sunrise_before(jd, lat, lon)
    out = {}
    if sr is not None:
        sun_sr = norm(swe.calc_ut(sr, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0])
        mins = (jd - sr) * 1440.0
        out["HL"] = norm(sun_sr + mins * 0.5)       # 30° per hour
        out["GL"] = norm(sun_sr + mins * 1.25)      # 30° per ghati (24 min)
        out["sunrise_jd"] = sr
    _, _, frac = nakshatra_of(moon_lon)
    out["SL"] = norm(lagna_lon + frac * 360.0)
    return out


def hora_lord(jd, sunrise_jd, weekday_lord):
    """1.3.11: 24 equal horas from sunrise; first hora = weekday lord, then Sa Ju Ma Su Ve Me Mo cycle."""
    order = ["Sa", "Ju", "Ma", "Su", "Ve", "Me", "Mo"]
    n = int((jd - sunrise_jd) * 24)  # 0-based hora index
    i = (order.index(weekday_lord) + n) % 7
    return order[i], n + 1


VARA_LORD = ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]  # Sunday..Saturday

TARA_NAMES = ["Janma (mixed)", "Sampat (good)", "Vipat (bad)", "Kshema (good)", "Pratyak (bad)",
              "Sadhana (good)", "Naidhana (bad)", "Mitra (good)", "Parama Mitra (good)"]


def tara_of(janma_nak, nak):
    """Table 64: tara index 0..8 counted from janma nakshatra."""
    return ((nak - janma_nak) % 27) % 9


# --------------------------------------------------------------------------
# Sudasa (textbook ch. 20) — rasi dasa from Sree Lagna, Narayana lengths
# --------------------------------------------------------------------------
def sudasa(sl_lon, pos, birth_dt_utc, cycles=2, year_days=YEAR_DAYS):
    sl = sign_of(sl_lon)
    step = 1 if is_odd_sign(sl) else -1
    order = []
    for grp in ((0, 3, 6, 9), (1, 4, 7, 10), (2, 5, 8, 11)):
        for h in grp:
            order.append((sl + step * h) % 12)
    frac_left = (30.0 - deg_in_sign(sl_lon)) / 30.0
    out = []
    t = birth_dt_utc
    for cyc in range(1, cycles + 1):
        for i, s in enumerate(order):
            yrs = narayana_length(s, pos)[0]
            if cyc == 2:
                yrs = 12 - yrs  # second cycle, as in Narayana dasa (script convention)
            if yrs <= 0:
                continue
            eff = yrs * frac_left if (cyc == 1 and i == 0) else yrs
            end = t + timedelta(days=eff * year_days)
            out.append({"sign": s, "years": round(eff, 3), "full_years": yrs, "start": t, "end": end, "cycle": cyc})
            t = end
    return sl, frac_left, order, out


# --------------------------------------------------------------------------
# Sudarsana Chakra dasa (textbook ch. 31): house N in year N from La/Mo/Su
# --------------------------------------------------------------------------
def sudarsana_dasa(year_of_life, lagna_sign, pos):
    h = year_of_life % 12 or 12
    la = (lagna_sign + h - 1) % 12
    mo = (sign_of(pos["Mo"]["lon"]) + h - 1) % 12
    su = (sign_of(pos["Su"]["lon"]) + h - 1) % 12
    # strongest reference of Lagna/Moon/Sun by rasi strength rules (approximation, 31.3)
    best = stronger_rasi(stronger_rasi(lagna_sign, sign_of(pos["Mo"]["lon"]), pos), sign_of(pos["Su"]["lon"]), pos)
    ref = "Lagna" if best == lagna_sign else ("Chandra" if best == sign_of(pos["Mo"]["lon"]) else "Surya")
    return {"house": h, "from_lagna": la, "from_moon": mo, "from_sun": su, "strongest_ref": ref,
            "dasa_sign": (best + h - 1) % 12}


# --------------------------------------------------------------------------
# Compressed Vimshottari (textbook 35.4) — for muhurta / mundane / prashna charts
# --------------------------------------------------------------------------
def compressed_vimshottari(moon_lon, start_dt, total_days):
    """120 years -> total_days; first dasa runs full (no balance), per 35.4 rule (3)."""
    nak, _, _ = nakshatra_of(moon_lon)
    seq = ["Ke", "Ve", "Su", "Mo", "Ma", "Ra", "Ju", "Sa", "Me"]
    i0 = seq.index(NAK_LORDS[nak % 9])
    out = []
    t = start_dt
    for k in range(9):
        L = seq[(i0 + k) % 9]
        days = DASHA_YEARS[L] / 120.0 * total_days
        end = t + timedelta(days=days)
        sub = []
        ts = t
        for j in range(9):
            A = seq[(seq.index(L) + j) % 9]
            aend = ts + timedelta(days=days * DASHA_YEARS[A] / 120.0)
            sub.append({"lord": A, "start": ts, "end": aend})
            ts = aend
        out.append({"lord": L, "days": days, "start": t, "end": end, "sub": sub})
        t = end
    return out


# --------------------------------------------------------------------------
# Mundane house significations (textbook 35.2)
# --------------------------------------------------------------------------
MUNDANE_HOUSES = {
    1: "General state of affairs, public health, cabinet / (org: identity, leadership, overall health)",
    2: "State revenue, wealth, imports, commerce, allies / (org: finances, income)",
    3: "Telecommunications, transport, journalism, media / (org: communication, marketing, staff initiative)",
    4: "Education, students, real estate, well-being, trade, agriculture / (org: premises, assets, morale)",
    5: "Children, new births, crime, parks, mentality of leaders / (org: new products, strategy, followers)",
    6: "State loans, debt, diseases, armed forces, attacks / (org: debts, disputes, competition, employees)",
    7: "Health of women, war, relations with other nations / (org: partners, clients, contracts)",
    8: "Death rate, treasury, unexpected troubles, instability / (org: sudden losses, restructuring, hidden funds)",
    9: "Temples, righteousness, judiciary, fortune / (org: ethics, legal, luck, long-distance links)",
    10: "The ruler, politics, parliament, foreign trade, exports / (org: management, reputation, market position)",
    11: "Gains from other nations, gains in trade, friendship / (org: profits, networks)",
    12: "Secret enemies, plots, hospitals, losses / (org: expenses, foreign ties, hidden losses)",
}


# --------------------------------------------------------------------------
# Muhurta (textbook ch. 36, Table 79 + taras Table 64 + hora 1.3.11)
# --------------------------------------------------------------------------
_S16 = [0, 3, 4, 6, 7, 11, 12, 13, 14, 16, 20, 21, 22, 23, 25, 26]
BENEFIC_OWNED = [1, 2, 3, 5, 6, 8, 11]  # Ta Ge Cn Vi Li Sg Pi
# name: (tithis, vara idx Sun=0.., lagnas or "benefic", nakshatras, secondary naks, empty_house, houses_to_be_strong, note)
MUHURTA_TASKS = {
    "house_construction": ([2, 3, 5, 7, 11, 13, 15], [1, 3, 4, 5], [1, 2, 5, 8, 10, 11], [x for x in _S16 if x != 7], [4, 7],
                           8, [1, 4], "8th house should be empty (Le, Sc lagnas also acceptable)"),
    "griha_pravesha": ([2, 3, 5, 7, 10, 11, 13, 15], [1, 3, 4, 5], [1, 2, 4, 5, 7, 8, 10, 11],
                       [3, 4, 11, 13, 16, 20, 22, 23, 25, 26], [], 8, [1, 4],
                       "8th empty, 4th strong; hora lord favorable w.r.t. natal 4th/A4; check D-4 (Venus strong)"),
    "naming": ([2, 3, 5, 7, 10, 11, 13], [0, 1, 3, 4, 6], "benefic", _S16, [], 8, [1, 2], "8th house should be empty"),
    "annaprashana": ([2, 3, 5, 7, 10, 13, 15], [0, 1, 3, 4, 5], "benefic", _S16, [], 10, [1, 2, 4],
                     "10th house should be empty; even/odd month for boys/girls"),
    "vidyarambha": ([2, 3, 5, 7, 10, 11, 12], [1, 3, 4, 5], [2, 5, 8, 11], [0, 6, 12, 13, 14, 16, 21, 26],
                    [4, 5, 22, 23], 8, [1, 2, 4, 5], "8th empty; Uttarayana better; check D-24"),
    "upanayana": ([2, 3, 5, 10, 11], [1, 3, 4, 5], "benefic", _S16, [], 8, [1, 5, 9], "8th empty (tithis 6, 12 secondary)"),
    "wedding": ([2, 3, 5, 7, 10, 11, 12, 13, 15], [1, 3, 4, 5], "benefic", [3, 4, 9, 11, 12, 14, 16, 18, 20, 25, 26], [],
                7, [1, 7], "7th house should be clean; hora lord favorable w.r.t. natal 7th & UL; check D-9"),
    "idol_installation": ([2, 3, 5, 7, 8, 10, 11, 12, 13], [0, 1, 3, 4, 5], [1, 2, 4, 5, 7, 8, 10, 11], _S16, [], None, [1, 9],
                          "Uttarayana for gentle deities, Dakshinayana for aggressive deities"),
    # textbook 36.4 strength-based tasks (no Table 79 row): generic panchanga filters + relevant houses
    "job": (None, None, "benefic", None, [], 8, [1, 6, 10], "36.4: Lagna, 6th, 10th strong in rasi and D-10; first Vimshottari dasa lord favorable"),
    "business": (None, None, "benefic", None, [], 8, [1, 2, 10, 11], "Treat like job/venture start: 1, 2, 10, 11 strong; check D-10"),
    "vehicle": (None, None, "benefic", None, [], 8, [1, 4], "36.4: 1st, 4th (and A4) strong in rasi and D-16"),
    "property": (None, None, "benefic", None, [], 8, [1, 4], "36.4: 1st, 4th strong; Mars strong in D-4"),
    "travel": (None, None, "benefic", None, [], 8, [1, 3, 9, 12], "General: benefic lagna, good tara, 8th empty"),
    "general": (None, None, "benefic", None, [], 8, [1], "Generic auspicious start: good tara, benefic hora/lagna, 8th empty"),
}
RIKTA_TITHIS = (4, 9, 14)
BAD_KARANAS = ("Vishti (Bhadra)", "Shakuni", "Chatushpada", "Naga", "Kimstughna")
NAT_BENEFIC = ("Ju", "Ve", "Me", "Mo")
NAT_MALEFIC = ("Sa", "Ma", "Su", "Ra", "Ke")


def _muhurta_eval(jd, task, lat, lon, tzname, janma_nak, natal):
    """Evaluate one instant. Returns dict(ok, fail[], score, ...)."""
    tithis, varas, lagnas, naks, naks2, empty_h, strong_h, note = MUHURTA_TASKS[task]
    pos, _ = compute_positions(jd)
    lag = compute_lagna(jd, lat, lon)
    ls = sign_of(lag)
    pch = panchanga(pos, jd, lat, lon, tzname)
    diff = norm(pos["Mo"]["lon"] - pos["Su"]["lon"])
    t30 = int(diff // 12) + 1
    tithi_n = t30 if t30 <= 15 else t30 - 15
    amavasya = t30 == 30
    vara_i = VARA.index(pch["vara"].split("vara")[0])
    nak, _, _ = nakshatra_of(pos["Mo"]["lon"])
    reasons, hard_fail = [], []
    score = 0
    if tithis is not None:
        if tithi_n not in tithis or amavasya:
            hard_fail.append(f"tithi {pch['tithi']}")
    elif tithi_n in RIKTA_TITHIS or amavasya:
        hard_fail.append(f"rikta/amavasya tithi {pch['tithi']}")
    if varas is not None and vara_i not in varas:
        hard_fail.append(f"vara {VARA[vara_i]}")
    if naks is not None:
        if nak in naks:
            pass
        elif nak in naks2:
            reasons.append(f"nakshatra {NAKSHATRAS[nak]} (secondary)")
            score -= 1
        else:
            hard_fail.append(f"nakshatra {NAKSHATRAS[nak]}")
    if lagnas == "benefic":
        if ls not in BENEFIC_OWNED:
            hard_fail.append(f"lagna {SIGNS[ls]} (not benefic-owned)")
    elif lagnas is not None and ls not in lagnas:
        hard_fail.append(f"lagna {SIGNS[ls]}")
    if empty_h:
        occ = [PLANET_NAME[p] for p in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]
               if house_from(ls, sign_of(pos[p]["lon"])) == empty_h]
        if occ:
            hard_fail.append(f"{empty_h}th house occupied ({', '.join(occ)})")
    tara = None
    if janma_nak is not None:
        tara = tara_of(janma_nak, nak)
        if tara in (2, 4, 6):
            hard_fail.append(f"bad tara {TARA_NAMES[tara]}")
        elif tara in (1, 3, 5, 7, 8):
            score += 1
            reasons.append(f"tara {TARA_NAMES[tara]}")
        else:
            reasons.append("janma tara (mixed)")
    if hard_fail:
        return {"jd": jd, "ok": False, "fail": hard_fail}
    sr = sunrise_before(jd, lat, lon)
    hl, hn = hora_lord(jd, sr, VARA_LORD[vara_i]) if sr else ("?", 0)
    if hl in NAT_BENEFIC:
        score += 1
        reasons.append(f"hora {PLANET_NAME[hl]}")
    else:
        reasons.append(f"hora {PLANET_NAME[hl]} (malefic)")
    if natal:
        npos, nls = natal["pos"], natal["lagna_sign"]
        good_h = [h for h in strong_h if SIGN_LORD[(nls + h - 1) % 12] == hl or
                  house_from(nls, sign_of(npos[hl]["lon"])) == h]
        if good_h:
            score += 1
            reasons.append(f"hora lord linked to natal house {good_h}")
        if hl in (SIGN_LORD[(nls + 5) % 12], SIGN_LORD[(nls + 7) % 12], SIGN_LORD[(nls + 11) % 12]):
            score -= 1
            reasons.append("hora lord owns natal 6/8/12")
    if pch["karana"] in BAD_KARANAS:
        score -= 1
        reasons.append(f"karana {pch['karana']} (unfavorable)")
    for h in strong_h:
        hs = (ls + h - 1) % 12
        mal = [p for p in NAT_MALEFIC if sign_of(pos[p]["lon"]) == hs]
        ben = [p for p in NAT_BENEFIC if occupies_or_aspects(p, hs, pos)]
        if ben and not mal:
            score += 1
        elif mal:
            score -= 1
            reasons.append(f"malefic {'/'.join(PLANET_NAME[m] for m in mal)} in house {h}")
    if sign_of(pos["Mo"]["lon"]) in ((ls + 5) % 12, (ls + 7) % 12, (ls + 11) % 12):
        score -= 1
        reasons.append("Chandra in 6/8/12 from lagna")
    ll = SIGN_LORD[ls]
    if house_from(ls, sign_of(pos[ll]["lon"])) in (1, 4, 7, 10, 5, 9):
        score += 1
        reasons.append(f"lagna lord {PLANET_NAME[ll]} in kendra/trikona")
    return {"jd": jd, "ok": True, "score": score, "lagna": ls, "lagna_lon": lag, "nak": nak,
            "tithi": pch["tithi"], "vara": VARA[vara_i], "hora": hl, "tara": tara,
            "karana": pch["karana"], "reasons": reasons, "pos": pos}


def muhurta_scan(task, date_from, date_to, lat, lon, tzname, janma_nak=None, hours=(6, 21),
                 natal=None, step_min=10, min_score=0, refine=True):
    """Return list of candidate windows (edges refined to ~30 s by bisection when refine=True)."""
    note = MUHURTA_TASKS[task][7]
    swe.set_sid_mode(SID_MODE)
    day = date_from
    samples = []
    while day <= date_to:
        jd_a, _ = to_jd_ut(datetime(day.year, day.month, day.day, 0, 0) + timedelta(hours=hours[0]), tzname)
        jd_b, _ = to_jd_ut(datetime(day.year, day.month, day.day, 0, 0) + timedelta(hours=hours[1]), tzname)
        t = jd_a
        while t < jd_b:
            samples.append(_muhurta_eval(t, task, lat, lon, tzname, janma_nak, natal))
            t += step_min / 1440.0
        day += timedelta(days=1)
    windows, cur = [], None
    prev = None
    for s in samples:
        if s["ok"] and s["score"] >= min_score:
            key = (s["lagna"], s["nak"], s["tithi"])
            if cur and cur["key"] == key and s["jd"] - cur["jd_end"] <= step_min / 1440.0 + 1e-6:
                cur["jd_end"] = s["jd"]
                cur["score"] = max(cur["score"], s["score"])
                cur["horas"].add(s["hora"])
                cur["reasons"] |= set(s["reasons"])
            else:
                if cur:
                    windows.append(cur)
                cur = {"key": key, "jd_start": s["jd"], "jd_end": s["jd"], "jd_before": prev["jd"] if prev else None,
                       "lagna": s["lagna"], "score": s["score"], "nak": s["nak"], "tithi": s["tithi"], "vara": s["vara"],
                       "horas": {s["hora"]}, "tara": s["tara"], "reasons": set(s["reasons"]), "pos": s["pos"], "lagna_lon": s["lagna_lon"]}
        else:
            if cur:
                cur["jd_after"] = s["jd"]
                windows.append(cur)
                cur = None
        prev = s
    if cur:
        windows.append(cur)
    for w in windows:
        if refine:
            # start edge: between previous (failing/different) sample and first passing sample
            if w.get("jd_before") is not None:
                lo, hi = w["jd_before"], w["jd_start"]
                while (hi - lo) * 1440 > 0.5:
                    mid = (lo + hi) / 2
                    e = _muhurta_eval(mid, task, lat, lon, tzname, janma_nak, natal)
                    if e["ok"] and (e["lagna"], e["nak"], e["tithi"]) == w["key"]:
                        hi = mid
                    else:
                        lo = mid
                w["jd_start"] = hi
            if w.get("jd_after") is not None:
                lo, hi = w["jd_end"], w["jd_after"]
                while (hi - lo) * 1440 > 0.5:
                    mid = (lo + hi) / 2
                    e = _muhurta_eval(mid, task, lat, lon, tzname, janma_nak, natal)
                    if e["ok"] and (e["lagna"], e["nak"], e["tithi"]) == w["key"]:
                        lo = mid
                    else:
                        hi = mid
                w["jd_end"] = lo
            else:
                w["jd_end"] += step_min / 1440.0
        else:
            w["jd_end"] += step_min / 1440.0
    return windows, note, samples


# --------------------------------------------------------------------------
# Nama nakshatra (naming syllables) — classical Avakahada chakra (not in textbook)
# --------------------------------------------------------------------------
NAMA_SYLLABLES = [
    (["Chu", "Che", "Cho", "La"], ["චු", "චේ", "චෝ", "ලා"]),
    (["Li", "Lu", "Le", "Lo"], ["ලී", "ලූ", "ලේ", "ලෝ"]),
    (["A", "I", "U", "E"], ["අ", "ඉ", "උ", "ඒ"]),
    (["O", "Va", "Vi", "Vu"], ["ඕ", "වා", "වී", "වූ"]),
    (["Ve", "Vo", "Ka", "Ki"], ["වේ", "වෝ", "කා", "කී"]),
    (["Ku", "Gha", "Nga", "Chha"], ["කූ", "ඝ", "ඞ", "ඡ"]),
    (["Ke", "Ko", "Ha", "Hi"], ["කේ", "කෝ", "හා", "හී"]),
    (["Hu", "He", "Ho", "Da"], ["හූ", "හේ", "හෝ", "ඩා"]),
    (["Di", "Du", "De", "Do"], ["ඩී", "ඩූ", "ඩේ", "ඩෝ"]),
    (["Ma", "Mi", "Mu", "Me"], ["මා", "මී", "මූ", "මේ"]),
    (["Mo", "Ta", "Ti", "Tu"], ["මෝ", "ටා", "ටී", "ටූ"]),
    (["Te", "To", "Pa", "Pi"], ["ටේ", "ටෝ", "පා", "පී"]),
    (["Pu", "Sha", "Na", "Tha"], ["පූ", "ෂ", "ණ", "ඨ"]),
    (["Pe", "Po", "Ra", "Ri"], ["පේ", "පෝ", "රා", "රී"]),
    (["Ru", "Re", "Ro", "Ta"], ["රූ", "රේ", "රෝ", "තා"]),
    (["Ti", "Tu", "Te", "To"], ["තී", "තූ", "තේ", "තෝ"]),
    (["Na", "Ni", "Nu", "Ne"], ["නා", "නී", "නූ", "නේ"]),
    (["No", "Ya", "Yi", "Yu"], ["නෝ", "යා", "යී", "යූ"]),
    (["Ye", "Yo", "Bha", "Bhi"], ["යේ", "යෝ", "භා", "භී"]),
    (["Bhu", "Dha", "Pha", "Dha"], ["භූ", "ධා", "ඵා", "ඨා"]),
    (["Bhe", "Bho", "Ja", "Ji"], ["භේ", "භෝ", "ජා", "ජී"]),
    (["Khi (Ju)", "Khu (Je)", "Khe (Jo)", "Kho (Gha)"], ["ඛී (ජු)", "ඛූ (ජේ)", "ඛේ (ජෝ)", "ඛෝ (ඝ)"]),
    (["Ga", "Gi", "Gu", "Ge"], ["ගා", "ගී", "ගූ", "ගේ"]),
    (["Go", "Sa", "Si", "Su"], ["ගෝ", "සා", "සී", "සූ"]),
    (["Se", "So", "Da", "Di"], ["සේ", "සෝ", "දා", "දී"]),
    (["Du", "Tha", "Jha", "Gna"], ["දූ", "ථ", "ඣ", "ඤ"]),
    (["De", "Do", "Cha", "Chi"], ["දේ", "දෝ", "චා", "චී"]),
]


def nama_nakshatra(moon_lon):
    nak, pada, _ = nakshatra_of(moon_lon)
    lat, sin = NAMA_SYLLABLES[nak]
    return {"nakshatra": NAKSHATRAS[nak], "pada": pada, "syllable": lat[pada - 1], "sinhala": sin[pada - 1],
            "all_padas": list(zip(lat, sin))}


# --------------------------------------------------------------------------
# Natural benefics/malefics (textbook 3.3), graha drishti (10.2), argala (10.5-10.6)
# --------------------------------------------------------------------------
def natural_benefics(pos):
    """Ju, Ve always; Mo if waxing (Sukla paksha); Me if alone or with more benefics than malefics."""
    ben = {"Ju", "Ve"}
    if norm(pos["Mo"]["lon"] - pos["Su"]["lon"]) < 180:
        ben.add("Mo")
    ms = sign_of(pos["Me"]["lon"])
    with_me = [p for p in ["Su", "Mo", "Ma", "Ju", "Ve", "Sa", "Ra", "Ke"] if sign_of(pos[p]["lon"]) == ms]
    nb = sum(1 for p in with_me if p in ben)
    nm = sum(1 for p in with_me if p in ("Su", "Ma", "Sa", "Ra", "Ke") or (p == "Mo" and "Mo" not in ben))
    if not with_me or nb >= nm:
        ben.add("Me")
    return ben


def natural_malefics(pos):
    return {p for p in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"] if p not in natural_benefics(pos)}


GRAHA_DRISHTI_EXTRA = {"Ma": (4, 8), "Ju": (5, 9), "Sa": (3, 10)}


def graha_aspects_sign(p, target_sign, pos):
    """Graha drishti (10.2): 7th from planet; Ma 4/8, Ju 5/9, Sa 3/10 in addition. Nodes: 7th only."""
    ps = sign_of(pos[p]["lon"])
    h = (target_sign - ps) % 12 + 1
    return h == 7 or h in GRAHA_DRISHTI_EXTRA.get(p, ())


def graha_aspects_planet(p, q, pos):
    return p != q and graha_aspects_sign(p, sign_of(pos[q]["lon"]), pos)


def conj_or_graha_aspect(p, q, pos):
    return sign_of(pos[p]["lon"]) == sign_of(pos[q]["lon"]) or graha_aspects_planet(p, q, pos) or graha_aspects_planet(q, p, pos)


def argala_on(target_sign, pos, ketu_reverse=True):
    """Argalas (2,4,11 primary; 5 secondary) and virodhargalas (12,10,3,9) on a sign.
    If Ketu occupies the sign, counting is anti-zodiacal (10.6 NOTE).
    Returns dict with lists of (planet, house_from_target)."""
    rev = ketu_reverse and any(sign_of(pos[p]["lon"]) == target_sign for p in ["Ke"])
    ben = natural_benefics(pos)
    def hf(s):
        d = (s - target_sign) % 12
        if rev:
            d = (-d) % 12
        return d + 1
    out = {"subha": [], "papa": [], "secondary": [], "virodha": []}
    occ = {}
    for p in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        h = hf(sign_of(pos[p]["lon"]))
        occ.setdefault(h, []).append(p)
    for h in (2, 4, 11):
        for p in occ.get(h, []):
            out["subha" if p in ben else "papa"].append((p, h))
    for p in occ.get(5, []):
        out["secondary"].append((p, 5))
    # virodhargala: 12 blocks 2; 10 blocks 4; 3 blocks 11; 9 blocks 5. Several malefics in 3rd -> argala instead.
    for h, blocks in ((12, 2), (10, 4), (3, 11), (9, 5)):
        ps = occ.get(h, [])
        if h == 3 and sum(1 for p in ps if p not in ben) >= 2:
            for p in ps:
                out["papa" if p not in ben else "subha"].append((p, 3))
            continue
        for p in ps:
            out["virodha"].append((p, h, blocks))
    return out


def argala_report(pos, lagna_sign, targets=None):
    """Lines for houses 1-12 (or given list) plus Saturn/AK style karaka targets."""
    ben = natural_benefics(pos)
    lines = []
    for h in (targets or range(1, 13)):
        s = (lagna_sign + h - 1) % 12
        a = argala_on(s, pos)
        sub = ", ".join(f"{PLANET_NAME[p][:5]}({hh})" for p, hh in a["subha"]) or "-"
        pap = ", ".join(f"{PLANET_NAME[p][:5]}({hh})" for p, hh in a["papa"]) or "-"
        sec = ", ".join(f"{PLANET_NAME[p][:5]}" for p, hh in a["secondary"]) or "-"
        vir = ", ".join(f"{PLANET_NAME[p][:5]}({hh}→blocks {b})" for p, hh, b in a["virodha"]) or "-"
        n_arg = len(a["subha"]) + len(a["papa"])
        n_vir = len(a["virodha"])
        verdict = "argala dominates" if n_arg > n_vir else ("obstruction dominates" if n_vir > n_arg else ("balanced" if n_arg else ""))
        lines.append(f"  H{h:>2} {SIGNS[s]:10} subha: {sub:24} papa: {pap:24} 5th: {sec:10} virodha: {vir:30} {verdict}")
    return lines


# --------------------------------------------------------------------------
# Upagrahas (textbook ch.4)
# --------------------------------------------------------------------------
UPAGRAHA_SUN = ["Dhuma", "Vyatipata", "Parivesha", "Indrachapa", "Upaketu"]
UPAGRAHA_TIME = {"Kaala": ("Su", 0.5), "Mrityu": ("Ma", 0.5), "Arthaprahara": ("Me", 0.5),
                 "Yamaghantaka": ("Ju", 0.5), "Gulika": ("Sa", 0.5), "Maandi": ("Sa", 0.0)}
WEEKDAY_ORDER = ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]


def sun_upagrahas(sun_lon):
    dh = norm(sun_lon + 133 + 20 / 60)
    vy = norm(360 - dh)
    pa = norm(vy + 180)
    ind = norm(360 - pa)
    up = norm(ind + 16 + 40 / 60)
    return {"Dhuma": dh, "Vyatipata": vy, "Parivesha": pa, "Indrachapa": ind, "Upaketu": up}


def time_upagrahas(jd, lat, lon, tzname="UTC"):
    """Kaala, Mrityu, Arthaprahara, Yamaghantaka, Gulika, Maandi from the 8 parts of day/night (Table 10)."""
    swe.set_sid_mode(SID_MODE)
    sr = sunrise_before(jd, lat, lon)
    if sr is None:
        return {}
    try:
        _, t_set = swe.rise_trans(sr, swe.SUN, swe.CALC_SET | RISE_BITS, [lon, lat, 0])
        ss = t_set[0]
        _, t_nr = swe.rise_trans(ss, swe.SUN, swe.CALC_RISE | RISE_BITS, [lon, lat, 0])
        nsr = t_nr[0]
    except Exception:
        return {}
    # weekday of the Hindu day (starting at sr): use local weekday of sr + 12h approx via revjul in UT is risky;
    # weekday lord = planet ruling the day that began at `sr`: compute from JD (JD 0.5 boundary = Monday 0h UT ... use formula)
    wd = (jd_to_datetime(sr).astimezone(ZoneInfo(tzname)).weekday() + 1) % 7  # 0=Sunday, local date of sunrise
    day_lord = WEEKDAY_ORDER[wd]
    is_day = jd < ss
    if is_day:
        start, end = sr, ss
        first = WEEKDAY_ORDER.index(day_lord)
        rulers = []
        i = first
        while len(rulers) < 8:
            rulers.append(WEEKDAY_ORDER[i % 7])
            if WEEKDAY_ORDER[i % 7] == "Sa":
                rulers.append(None)
            i += 1
        rulers = rulers[:8]
    else:
        start, end = ss, nsr
        first = (WEEKDAY_ORDER.index(day_lord) + 4) % 7  # 5th planet from weekday lord
        rulers = []
        i = first
        while len(rulers) < 8:
            rulers.append(WEEKDAY_ORDER[i % 7])
            if WEEKDAY_ORDER[i % 7] == "Sa":
                rulers.append(None)
            i += 1
        rulers = rulers[:8]
    part = (end - start) / 8.0
    out = {"_rulers": rulers, "_day": is_day, "_weekday_lord": day_lord}
    for name, (pl, frac) in UPAGRAHA_TIME.items():
        k = rulers.index(pl)
        t = start + (k + frac) * part
        out[name] = compute_lagna(t, lat, lon)
    return out


# --------------------------------------------------------------------------
# Full yoga detector (textbook ch.11) — objective conditions only
# --------------------------------------------------------------------------
SEVEN = ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]
KENDRA, TRIKONA = (1, 4, 7, 10), (1, 5, 9)
PANAPHARA, APOKLIMA = (2, 5, 8, 11), (3, 6, 9, 12)
DUSTHANA, UPACHAYA = (6, 8, 12), (3, 6, 10, 11)
FRIENDS = {"Su": {"Mo", "Ma", "Ju"}, "Mo": {"Su", "Me"}, "Ma": {"Su", "Mo", "Ju"}, "Me": {"Su", "Ve"},
           "Ju": {"Su", "Mo", "Ma"}, "Ve": {"Me", "Sa"}, "Sa": {"Me", "Ve"}}
ENEMIES = {"Su": {"Ve", "Sa"}, "Mo": set(), "Ma": {"Me"}, "Me": {"Mo"}, "Ju": {"Me", "Ve"}, "Ve": {"Su", "Mo"}, "Sa": {"Su", "Mo", "Ma"}}


def is_strong(p, pos):
    """Working definition for 'strong' in yoga rules: exalted / own / moolatrikona / vargottama, not combust or debilitated."""
    if p in ("Ra", "Ke"):
        return False
    s = sign_of(pos[p]["lon"])
    if s == DEBIL[p] or combust(p, pos):
        return False
    return s == EXALT[p] or s in OWN[p] or varga_sign(pos[p]["lon"], 9) == s


def deep_exalted(p, pos):
    return p in DEEP_EXALT and abs((pos[p]["lon"] - DEEP_EXALT[p] + 180) % 360 - 180) <= 3.0


def full_yogas(pos, lagna_sign, ayanamsa=None):
    """Returns list of (category, name, detail). Rahu/Ketu excluded from 'planets' in Nabhasa yogas."""
    Y = []
    ben = natural_benefics(pos)
    mal = {p for p in SEVEN + ["Ra", "Ke"] if p not in ben}
    S = {p: sign_of(pos[p]["lon"]) for p in pos}
    H = {p: house_from(lagna_sign, S[p]) for p in pos}
    def lord(h):
        return SIGN_LORD[(lagna_sign + h - 1) % 12]
    def in_house(h):
        return [p for p in SEVEN + ["Ra", "Ke"] if H[p] == h]
    def house_of_sign(s):
        return house_from(lagna_sign, s)
    def exch(a, b):
        return S[lord(a)] == (lagna_sign + b - 1) % 12 and S[lord(b)] == (lagna_sign + a - 1) % 12
    def hf(ref, p):  # house of p counted from ref planet
        return (S[p] - S[ref]) % 12 + 1
    def add(cat, name, det=""):
        Y.append((cat, name, det))

    # ---- Ravi yogas 11.2
    p2 = [p for p in SEVEN if p not in ("Su", "Mo") and hf("Su", p) == 2]
    p12 = [p for p in SEVEN if p not in ("Su", "Mo") and hf("Su", p) == 12]
    if p2 and p12:
        add("Ravi", "Ubhayachari", f"{'/'.join(PLANET_NAME[x] for x in p2)} 2nd & {'/'.join(PLANET_NAME[x] for x in p12)} 12th from Surya")
    elif p2:
        add("Ravi", "Vesi", f"{'/'.join(PLANET_NAME[x] for x in p2)} in 2nd from Surya")
    elif p12:
        add("Ravi", "Vosi", f"{'/'.join(PLANET_NAME[x] for x in p12)} in 12th from Surya")
    if S["Su"] == S["Me"]:
        add("Ravi", "Budha-Aditya (Nipuna)", "Surya-Budha conjunct" + (" — Budha combust, weakened" if combust("Me", pos) else ""))
    # ---- Chandra yogas 11.3
    m2 = [p for p in SEVEN if p not in ("Su", "Mo") and hf("Mo", p) == 2]
    m12 = [p for p in SEVEN if p not in ("Su", "Mo") and hf("Mo", p) == 12]
    if m2 and m12:
        add("Chandra", "Duradhara", f"{'/'.join(PLANET_NAME[x] for x in m2)} 2nd & {'/'.join(PLANET_NAME[x] for x in m12)} 12th from Chandra")
    elif m2:
        add("Chandra", "Sunapha", f"{'/'.join(PLANET_NAME[x] for x in m2)} in 2nd from Chandra")
    elif m12:
        add("Chandra", "Anapha", f"{'/'.join(PLANET_NAME[x] for x in m12)} in 12th from Chandra")
    else:
        with_mo = [p for p in SEVEN if p not in ("Su", "Mo") and S[p] == S["Mo"]]
        kendra_planets = [p for p in SEVEN if p != "Mo" and H[p] in KENDRA]
        if not with_mo and not kendra_planets:
            add("Chandra", "Kemadruma (bad)", "no grahas in 1/2/12 from Chandra and none in kendras from Lagna")
        elif not with_mo:
            add("Chandra", "Kemadruma — partial", "no grahas 1/2/12 from Chandra, but kendras from Lagna occupied (cancellation per 11.3.4)")
    if S["Mo"] == S["Ma"]:
        add("Chandra", "Chandra-Mangala", "Chandra-Kuja conjunct")
    adhi = [p for p in ("Me", "Ju", "Ve") if hf("Mo", p) in (6, 7, 8)]
    if len(adhi) >= 3 or (len(adhi) >= 2 and all(hf("Mo", p) in (6, 7, 8) for p in ben if p in SEVEN and p != "Mo")):
        add("Chandra", "Adhi yoga", f"benefics {'/'.join(PLANET_NAME[x] for x in adhi)} in 6/7/8 from Chandra")
    mh = hf("Su", "Mo")
    add("Chandra", "Chandra from Surya", f"Chandra in {'kendra (little)' if mh in KENDRA else 'panaphara (average)' if mh in PANAPHARA else 'apoklima (much)'} — wealth/intelligence guideline 11.3(1)")
    # ---- Pancha Mahapurusha 11.4
    for p, nm in (("Ma", "Ruchaka"), ("Me", "Bhadra"), ("Sa", "Sasa"), ("Ve", "Malavya"), ("Ju", "Hamsa")):
        if H[p] in KENDRA and (S[p] == EXALT[p] or S[p] in OWN[p]):
            add("Mahapurusha", nm, f"{PLANET_NAME[p]} in {SIGNS[S[p]]} in house {H[p]}" + (" (combust)" if combust(p, pos) else ""))
    # ---- Nabhasa 11.5 (7 planets, no nodes)
    hs = [H[p] for p in SEVEN]
    types = {sign_type(S[p]) for p in SEVEN}
    if types == {0}:
        add("Nabhasa-Asraya", "Rajju", "all grahas in movable rasis")
    elif types == {1}:
        add("Nabhasa-Asraya", "Musala", "all grahas in fixed rasis")
    elif types == {2}:
        add("Nabhasa-Asraya", "Nala", "all grahas in dual rasis")
    kb = {H[p] for p in ben if p in SEVEN and H[p] in KENDRA}
    km = {H[p] for p in mal if H[p] in KENDRA}
    if len(kb) >= 3:
        add("Nabhasa-Dala", "Maala", f"benefics in kendras {sorted(kb)}" + (" (malefic also in a kendra — weakened)" if km else ""))
    if len(km) >= 3:
        add("Nabhasa-Dala", "Sarpa (bad)", f"malefics in kendras {sorted(km)}" + (" (benefic also in a kendra — weakened)" if kb else ""))
    occ = set(hs)
    akriti = None
    if occ <= set(KENDRA):
        if len(occ) == 4:
            akriti = ("Kamala", "all grahas in the 4 kendras")
        elif occ == {1, 7}:
            akriti = ("Sakata", "all grahas in 1st & 7th")
        elif occ == {4, 10}:
            akriti = ("Vihanga", "all grahas in 4th & 10th")
        elif len(occ) == 2:
            akriti = ("Gada", f"all grahas in two successive kendras {sorted(occ)}")
    if not akriti and occ <= set(TRIKONA):
        akriti = ("Sringataka", "all grahas in trikonas")
    if not akriti:
        for tri in ((2, 6, 10), (3, 7, 11), (4, 8, 12)):
            if occ <= set(tri):
                akriti = ("Hala", f"all grahas in mutual trines {tri}")
    if not akriti:
        b17 = all(p in ben for p in in_house(1) + in_house(7) if p in SEVEN) and (in_house(1) or in_house(7))
        m410 = all(p in mal for p in in_house(4) + in_house(10) if p in SEVEN) and (in_house(4) or in_house(10))
        b410 = all(p in ben for p in in_house(4) + in_house(10) if p in SEVEN) and (in_house(4) or in_house(10))
        m17 = all(p in mal for p in in_house(1) + in_house(7) if p in SEVEN) and (in_house(1) or in_house(7))
        if b17 and m410 and occ <= set(KENDRA):
            akriti = ("Vajra", "benefics in 1/7, malefics in 4/10")
        elif m17 and b410 and occ <= set(KENDRA):
            akriti = ("Yava", "malefics in 1/7, benefics in 4/10")
    if not akriti and (occ <= set(PANAPHARA) or occ <= set(APOKLIMA)):
        akriti = ("Vapi", "all grahas in panapharas / apoklimas")
    if not akriti:
        for nm, rng in (("Yupa", (1, 2, 3, 4)), ("Sara", (4, 5, 6, 7)), ("Sakti", (7, 8, 9, 10)), ("Danda", (10, 11, 12, 1))):
            if occ <= set(rng):
                akriti = (nm, f"all grahas in houses {rng}")
                break
    if not akriti:
        for nm, st in (("Nauka", 1), ("Kuta", 4), ("Chatra", 7), ("Chapa", 10)):
            rng = {(st + i - 1) % 12 + 1 for i in range(7)}
            if occ <= rng and len(occ) >= 5:
                akriti = (nm, f"all grahas in 7 houses from house {st}")
                break
    if not akriti:
        for st in PANAPHARA + APOKLIMA:
            rng = {(st + i - 1) % 12 + 1 for i in range(7)}
            if occ <= rng and len(occ) >= 5:
                akriti = ("Ardha Chandra", f"all grahas in 7 houses from house {st}")
                break
    if not akriti and occ <= {1, 3, 5, 7, 9, 11} and len(occ) >= 5:
        akriti = ("Chakra", "all grahas in odd houses")
    if not akriti and occ <= {2, 4, 6, 8, 10, 12} and len(occ) >= 5:
        akriti = ("Samudra", "all grahas in even houses")
    if akriti:
        add("Nabhasa-Akriti", *akriti)
    else:
        n = len({S[p] for p in SEVEN})
        add("Nabhasa-Sankhya", {7: "Veena", 6: "Dama", 5: "Pasa", 4: "Kedara", 3: "Sula", 2: "Yuga", 1: "Gola"}[n],
            f"7 grahas in {n} distinct rasis")
    # ---- Other popular yogas 11.6
    l1 = in_house(1)
    if any(p in ben for p in l1) or (any(p in ben for p in in_house(2)) and any(p in ben for p in in_house(12))):
        add("Popular", "Subha", "benefic in Lagna or subha-kartari")
    if any(p in mal for p in l1) or (any(p in mal for p in in_house(2)) and any(p in mal for p in in_house(12))):
        add("Popular", "Asubha", "malefic in Lagna or papa-kartari")
    if hf("Mo", "Ju") in KENDRA:
        ok_b = any(conj_or_graha_aspect("Ju", b, pos) for b in ben if b not in ("Ju",))
        weak = S["Ju"] == DEBIL["Ju"] or combust("Ju", pos) or SIGN_LORD[S["Ju"]] in ENEMIES["Ju"]
        add("Popular", "Gaja-Kesari" + ("" if ok_b and not weak else " (conditions partly unmet)"),
            f"Guru in kendra from Chandra" + ("" if ok_b else "; no benefic association") + ("; Guru weak" if weak else ""))
    if S["Ju"] == S["Ma"] or hf("Ju", "Ma") == 7:
        add("Popular", "Guru-Mangala", "Guru & Kuja conjunct/opposite")
    for ref, rs in (("Lagna", lagna_sign), ("Chandra", S["Mo"])):
        t10 = [p for p in SEVEN + ["Ra", "Ke"] if (S[p] - rs) % 12 == 9]
        if t10 and all(p in ben for p in t10):
            add("Popular", "Amala", f"only benefics ({'/'.join(PLANET_NAME[x] for x in t10)}) in 10th from {ref}")
    kp = [p for p in SEVEN + ["Ra", "Ke"] if H[p] in KENDRA]
    if kp and all(p in ben for p in kp) and all(p in ben for p in in_house(7) + in_house(8)):
        add("Popular", "Parvata", "kendras only benefics; 7th/8th empty or benefic")
    if (S[lord(4)] == EXALT[lord(4)] or S[lord(4)] in OWN[lord(4)]) and S[lord(10)] == S[lord(4)]:
        add("Popular", "Kahala (alt.)", "4th lord exalted/own with 10th lord")
    elif hf(lord(4), "Ju") in KENDRA and is_strong(lord(1), pos):
        add("Popular", "Kahala", "4th lord & Guru in mutual kendras, Lagna lord strong")
    if (S[lord(1)] == EXALT[lord(1)] and H[lord(1)] in KENDRA and conj_or_graha_aspect("Ju", lord(1), pos)) or \
            any(len([p for p in in_house(h) if p in ben]) >= 2 for h in (7, 9, 10)):
        add("Popular", "Chamara", "Lagna lord exalted in kendra with Guru's aspect, or two benefics in 7/9/10")
    if is_strong(lord(1), pos) and hf(lord(5), lord(6)) in KENDRA:
        add("Popular", "Sankha", "Lagna lord strong; 5th & 6th lords in mutual kendras")
    elif S[lord(1)] == S[lord(10)] and sign_type(S[lord(1)]) == 0 and is_strong(lord(9), pos):
        add("Popular", "Sankha (alt.)", "Lagna & 10th lords together in movable rasi; 9th lord strong")
    if is_strong(lord(9), pos) and (all(in_house(h) for h in (1, 2, 7, 12)) or
                                    (hf("Ju", "Ve") in KENDRA and hf("Ju", lord(1)) in KENDRA and hf("Ve", lord(1)) in KENDRA)):
        add("Popular", "Bheri", "9th lord strong; 1/2/7/12 occupied or Guru-Shukra-Lagna lord in mutual kendras")
    if is_strong(lord(1), pos) and any((S[p] == EXALT[p] or S[p] in OWN[p]) and H[p] in KENDRA + TRIKONA for p in SEVEN):
        add("Popular", "Mridanga", "own/exalted graha in kendra/trikona; Lagna lord strong")
    if S[lord(7)] == EXALT[lord(7)] and H[lord(7)] == 10 and S[lord(10)] == S[lord(9)]:
        add("Popular", "Sreenatha", "7th lord exalted in 10th; 10th & 9th lords together")
    if any(p in ben for p in l1) and any(p in ben for p in in_house(9)) and in_house(5) and \
            any(p in mal for p in in_house(4) + in_house(8)):
        add("Popular", "Matsya", "benefics in 1 & 9, grahas in 5, malefics in 4/8")
    if exch(2, 9) and H[lord(1)] in KENDRA + TRIKONA:
        add("Popular", "Khadga", "2nd-9th lords exchange; Lagna lord in kendra/trikona")
    if sign_type(lagna_sign) == 1 and H["Ve"] in KENDRA and H["Sa"] == 10 and H["Mo"] in TRIKONA and \
            any(p in ben and p != "Mo" and S[p] == S["Mo"] for p in SEVEN):
        add("Popular", "Kusuma", "fixed Lagna, Shukra in kendra, Chandra in trikona with benefic, Shani in 10th")
    if H["Ju"] in (2, 5) and conj_or_graha_aspect("Ju", "Me", pos) and conj_or_graha_aspect("Ju", "Ve", pos):
        add("Popular", "Kalanidhi", f"Guru in {H['Ju']}th with Budha & Shukra association")
    # Kalpadruma: lagna lord, its dispositor, that one's dispositor in rasi and in navamsa
    kl = lord(1)
    d1 = SIGN_LORD[S[kl]]
    d2 = SIGN_LORD[S[d1]]
    d3 = SIGN_LORD[varga_sign(pos[d1]["lon"], 9)]
    kq = [kl, d1, d2, d3]
    if all(H[p] in KENDRA + TRIKONA or S[p] == EXALT[p] for p in kq):
        add("Popular", "Kalpadruma (Parijata)", f"{', '.join(PLANET_NAME[p] for p in kq)} all in kendra/trikona/exaltation")
    b78 = in_house(7) + in_house(8)
    if b78 and all(p in ben for p in b78) and not any(conj_or_graha_aspect(m, b, pos) for m in mal for b in b78):
        add("Popular", "Lagnadhi", "benefics in 7 & 8 from Lagna, unafflicted")
    def ben_in(ref_sign, houses):
        return all(any(p in ben for p in SEVEN if (S[p] - ref_sign) % 12 + 1 == h) for h in houses)
    if ben_in(S[lord(2)], (2, 12, 8)):
        add("Popular", "Hari", "benefics in 2/12/8 from 2nd lord")
    if ben_in(S[lord(7)], (4, 9, 8)):
        add("Popular", "Hara", "benefics in 4/9/8 from 7th lord")
    if ben_in(S[lord(1)], (4, 10, 11)):
        add("Popular", "Brahma", "benefics in 4/10/11 from Lagna lord")
    if hf(lord(9), "Ju") in KENDRA and hf(lord(11), "Ve") in KENDRA and (hf(lord(1), "Me") in KENDRA or hf(lord(10), "Me") in KENDRA):
        add("Popular", "Brahma (variant)", "Guru kendra from 9L, Shukra kendra from 11L, Budha kendra from 1L/10L")
    if H[lord(9)] == 2 and H[lord(10)] == 2 and H[SIGN_LORD[varga_sign(pos[lord(9)]["lon"], 9)]] == 2:
        add("Popular", "Vishnu", "9th & 10th lords and navamsa dispositor of 9L in 2nd")
    if H[lord(5)] == 9 and H[lord(9)] == 10 and H[lord(10)] == 5:
        add("Popular", "Siva", "5L in 9, 9L in 10, 10L in 5")
    if hf("Su", "Mo") in TRIKONA and hf("Su", "Ma") in TRIKONA and hf("Mo", "Ma") in TRIKONA:
        add("Popular", "Trilochana", "Surya, Chandra, Kuja in mutual trines")
    g10 = SIGN_LORD[varga_sign(pos[lord(10)]["lon"], 9)]
    if S[g10] == EXALT[g10] and H[g10] == 10 and S[lord(1)] == S[g10]:
        add("Popular", "Gouri", "navamsa dispositor of 10L exalted in 10th with Lagna lord")
    if (S[lord(9)] in OWN[lord(9)] or S[lord(9)] == EXALT[lord(9)]) and H[lord(9)] in KENDRA and is_strong(lord(1), pos):
        add("Popular", "Lakshmi", "9th lord own/exalted in kendra; Lagna lord strong")
    if H[lord(10)] == 5 and H["Me"] in KENDRA and S["Su"] == 4 and (hf("Mo", "Me") in TRIKONA or hf("Mo", "Ju") in TRIKONA) and H["Ma"] == 11:
        add("Popular", "Saarada", "10L in 5, Budha kendra, Surya in Simha, Budha/Guru trine from Chandra, Kuja in 11")
    for h in (2, 5, 11):
        nl = SIGN_LORD[varga_sign(pos[lord(h)]["lon"], 9)]
        if S[nl] == EXALT[nl] and S[nl] == S[lord(9)]:
            add("Popular", "Bharathi", f"navamsa dispositor of {h}L exalted with 9L")
            break
    if all(H[p] in KENDRA + TRIKONA + (2,) for p in ("Me", "Ju", "Ve")) and \
            (S["Ju"] in OWN["Ju"] or S["Ju"] == EXALT["Ju"] or SIGN_LORD[S["Ju"]] in FRIENDS["Ju"]):
        add("Popular", "Saraswathi", "Budha, Guru, Shukra in kendra/trikona/2nd; Guru well placed")
    if H["Ju"] in KENDRA and H["Ve"] in KENDRA and S["Sa"] == EXALT["Sa"] and H["Sa"] in KENDRA:
        add("Popular", "Amsavatara", "Guru, Shukra & exalted Shani in kendras")
    if sign_type(lagna_sign) == 1 and exch(2, 10) and exch(1, 11):
        add("Popular", "Devendra", "fixed Lagna; 2-10 and 1-11 exchanges")
    if exch(5, 11) and H["Mo"] == 5:
        add("Popular", "Indra", "5-11 exchange; Chandra in 5th")
    if H["Su"] == 10 and H[lord(10)] == 3 and S[lord(10)] == S["Sa"]:
        add("Popular", "Ravi", "Surya in 10; 10L in 3 with Shani")
    if hf("Su", "Mo") == 12 and hf("Su", "Me") == 2 and hf("Mo", "Ju") in (5, 9):
        add("Popular", "Bhaskara", "Chandra 12th & Budha 2nd from Surya; Guru 5/9 from Chandra")
    if all(any((S[p] - r) % 12 == 4 for r in (lagna_sign, S["Mo"], S["Su"])) for p in SEVEN if p not in ("Mo", "Su")):
        add("Popular", "Kulavardhana", "every graha in 5th from Lagna, Chandra or Surya")
    ub = [p for p in ben if p in SEVEN and H[p] in UPACHAYA]
    if ub:
        um = [p for p in mal if H[p] in UPACHAYA]
        add("Popular", "Vasumati" + (" (full)" if len(ub) >= 3 and not um else ""),
            f"benefics {'/'.join(PLANET_NAME[x] for x in ub)} in upachayas" + (f"; malefics also there: {'/'.join(PLANET_NAME[x] for x in um)}" if um else ""))
    if (S[lord(10)] - (lagna_sign + 6)) % 12 in (0, 4, 8) and conj_or_graha_aspect(lord(1), "Ju", pos) and S["Su"] == EXALT["Su"] and H["Mo"] == 9:
        add("Popular", "Gandharva", "10L trine from 7th; Guru with Lagna lord; Surya exalted; Chandra in 9")
    if S["Ju"] == MOOLATRIKONA["Ju"] and S[lord(2)] == S["Ju"] and S[lord(1)] == EXALT[lord(1)]:
        add("Popular", "Go", "Guru in moolatrikona with 2L; Lagna lord exalted")
    if deep_exalted(lord(11), pos) and S[lord(11)] == S["Ve"] and hf(lord(1), lord(11)) in KENDRA:
        add("Popular", "Vidyut", "11L deeply exalted with Shukra, kendra from Lagna lord")
    if exch(4, 10) and S[lord(1)] == EXALT[lord(1)]:
        add("Popular", "Chapa", "4-10 exchange; Lagna lord exalted")
    if hf(lord(9), "Ju") == 9 and any(p in ben for p in SEVEN if hf("Ju", p) == 9) and H["Sa"] == 10:
        add("Popular", "Makuta", "Guru 9th from 9L; benefic 9th from Guru; Shani in 10")
    if deep_exalted(lord(10), pos) and S[lord(6)] == DEBIL[lord(6)]:
        add("Popular", "Jaya", "10L deeply exalted; 6L debilitated")
    if H[lord(6)] == 6:
        add("Vipareeta", "Harsha", "6th lord in 6th")
    if H[lord(8)] == 8:
        add("Vipareeta", "Sarala", "8th lord in 8th")
    if H[lord(12)] == 12:
        add("Vipareeta", "Vimala", "12th lord in 12th")
    # ---- Raja yogas 11.7
    klords = {lord(h) for h in KENDRA}
    tlords = {lord(h) for h in TRIKONA}
    seen = set()
    for a in klords:
        for b in tlords:
            if a == b or (a, b) in seen or (b, a) in seen:
                continue
            seen.add((a, b))
            rel = None
            if S[a] == S[b]:
                gap = abs(deg_in_sign(pos[a]["lon"]) - deg_in_sign(pos[b]["lon"]))
                rel = f"conjunct ({gap:.1f}° apart{'; wide' if gap > 6 else ''})"
            elif graha_aspects_planet(a, b, pos) and graha_aspects_planet(b, a, pos):
                rel = "mutual graha drishti"
            else:
                ha = [h for h in range(1, 13) if lord(h) == a]
                hb = [h for h in range(1, 13) if lord(h) == b]
                if any(exch(x, y) for x in ha for y in hb):
                    rel = "parivartana"
            if rel:
                nm = "Dharma-Karmadhipati Raja yoga" if {a, b} == {lord(9), lord(10)} else "Raja yoga"
                add("Raja", nm, f"{PLANET_NAME[a]} (kendra lord) & {PLANET_NAME[b]} (trikona lord) {rel}")
    dl = {lord(h) for h in DUSTHANA}
    vry = [p for p in dl if H[p] in DUSTHANA or any(S[p] == S[q] for q in dl if q != p)]
    if vry:
        add("Raja", "Vipareeta Raja yoga", f"dusthana lords {'/'.join(PLANET_NAME[x] for x in vry)} in/with dusthanas")
    # ---- Dhana 11.9
    for p in ("Mo", "Me", "Ju", "Ve"):
        if H[p] == 2 and S[p] == EXALT[p]:
            add("Dhana", "Exalted benefic in 2nd", PLANET_NAME[p])
    if conj_or_graha_aspect(lord(5), lord(9), pos) or S[lord(5)] == S[lord(9)]:
        add("Dhana", "5L-9L association", f"{PLANET_NAME[lord(5)]} & {PLANET_NAME[lord(9)]}")
    DHANA = {0: (["Su"], ["Sa", "Mo", "Ju"], "Ma", ["Me", "Ve", "Sa"]), 1: (["Me"], ["Mo", "Ma", "Ju"], "Ve", ["Me", "Sa"]),
             2: (["Ve"], ["Ma"], "Me", ["Ju", "Sa"]), 3: (["Ma"], ["Ve"], "Mo", ["Me", "Ju"]), 4: (["Ju"], ["Me"], "Su", ["Ma", "Ju"]),
             5: (["Sa"], ["Su", "Mo"], "Me", ["Ju", "Sa"]), 6: (["Sa"], ["Su", "Mo"], "Ve", ["Me", "Sa"]), 7: (["Ju"], ["Me"], "Ma", ["Me", "Ve", "Sa"]),
             8: (["Ma"], ["Ve"], "Ju", ["Ma", "Me"]), 9: (["Ve"], ["Ma"], "Sa", ["Ma", "Ju"]), 10: (["Me"], ["Mo", "Ma", "Ju"], "Sa", ["Ma", "Ju"]),
             11: (["Mo"], ["Ma"], "Ju", ["Ma", "Me"])}
    f5, f11, lp, assoc = DHANA[lagna_sign]
    if all(H[p] == 5 for p in f5) and all(H[p] == 11 for p in f11):
        add("Dhana", "Parasara lagna-specific (a)", f"{'/'.join(PLANET_NAME[x] for x in f5)} in 5th, {'/'.join(PLANET_NAME[x] for x in f11)} in 11th")
    if H[lp] == 1 and all(conj_or_graha_aspect(lp, q, pos) for q in assoc):
        add("Dhana", "Parasara lagna-specific (b)", f"{PLANET_NAME[lp]} in Lagna with {'/'.join(PLANET_NAME[x] for x in assoc)}")
    # ---- Daridra 11.10 (marakas = 2nd/7th lords and malefics in 2/7)
    marakas = {lord(2), lord(7)} | {p for p in mal if H[p] in (2, 7)}
    def mar_assoc(p):
        return any(conj_or_graha_aspect(m, p, pos) for m in marakas if m != p)
    if exch(1, 12) and (mar_assoc(lord(1)) or mar_assoc(lord(12))):
        add("Daridra", "(1) 1L-12L exchange with maraka", "")
    if (S["Ke"] == lagna_sign or S["Ke"] == S["Mo"]) and H[lord(1)] == 8 and mar_assoc(lord(1)):
        add("Daridra", "(3) Ketu with Lagna/Chandra, 1L in 8 with maraka", "")
    if H[lord(1)] in DUSTHANA and any(p in mal and S[p] == S[lord(1)] for p in SEVEN + ["Ra", "Ke"] if p != lord(1)) and \
            (S[lord(2)] == DEBIL[lord(2)] or SIGN_LORD[S[lord(2)]] in ENEMIES.get(lord(2), set())):
        add("Daridra", "(4) 1L with malefic in dusthana; 2L weak", "")
    if H[lord(5)] == 6 and H[lord(9)] == 12 and (mar_assoc(lord(5)) or mar_assoc(lord(9))):
        add("Daridra", "(5) 5L in 6, 9L in 12 with maraka", "")
    if l1 and all(p in mal for p in l1) and lord(9) not in l1 and lord(10) not in l1 and any(mar_assoc(p) for p in l1):
        add("Daridra", "(6) malefics in Lagna without 9L/10L, maraka-afflicted", "")
    return Y


def print_full_yogas(pos, lagna_sign):
    Y = full_yogas(pos, lagna_sign)
    print("\nYOGAS (textbook ch.11 — objective conditions; 'strong' = exalted/own/moolatrikona/vargottama & not combust/debilitated)")
    print(f"  Natural benefics here: {', '.join(PLANET_NAME[p] for p in sorted(natural_benefics(pos)))}")
    cur = None
    for cat, nm, det in Y:
        if cat != cur:
            print(f"  [{cat}]")
            cur = cat
        print(f"     {nm:34} {det}")
    return Y


# --------------------------------------------------------------------------
# Lagna Kendradi Rasi Dasa (textbook ch.19)
# --------------------------------------------------------------------------
def kendradi_rasi_dasa(lagna_sign, pos, birth_dt_utc, cycles=2, year_days=YEAR_DAYS):
    seed = stronger_rasi(lagna_sign, (lagna_sign + 6) % 12, pos)
    step = 1 if is_odd_sign(lagna_sign) else -1
    if any(sign_of(pos[p]["lon"]) == seed for p in ["Sa"]):
        step = 1
    if any(sign_of(pos[p]["lon"]) == seed for p in ["Ke"]):
        step = -1
    order = [(seed + step * h) % 12 for grp in ((0, 3, 6, 9), (1, 4, 7, 10), (2, 5, 8, 11)) for h in grp]
    out, t = [], birth_dt_utc
    for cyc in range(1, cycles + 1):
        for s in order:
            yrs = narayana_length(s, pos)[0]
            if cyc == 2:
                yrs = 12 - yrs
            if yrs <= 0:
                continue
            end = t + timedelta(days=yrs * year_days)
            out.append({"sign": s, "years": yrs, "start": t, "end": end, "cycle": cyc})
            t = end
    return seed, step, order, out


# --------------------------------------------------------------------------
# Drigdasa (textbook ch.21) — from 9th house, each house + 3 signs it aspects
# --------------------------------------------------------------------------
def drigdasa(lagna_sign, pos, birth_dt_utc, cycles=2, year_days=YEAR_DAYS):
    order = []
    for h in (9, 10, 11):
        s = (lagna_sign + h - 1) % 12
        step = 1 if s in ODD_FOOTED else -1
        grp = [s]
        k = 1
        while len(grp) < 4:
            c = (s + step * k) % 12
            if rasi_aspects(s, c):
                grp.append(c)
            k += 1
        order += grp
    out, t = [], birth_dt_utc
    for cyc in range(1, cycles + 1):
        for s in order:
            yrs = narayana_length(s, pos)[0]
            if cyc == 2:
                yrs = 12 - yrs
            if yrs <= 0:
                continue
            end = t + timedelta(days=yrs * year_days)
            out.append({"sign": s, "years": yrs, "start": t, "end": end, "cycle": cyc})
            t = end
    return order, out


# --------------------------------------------------------------------------
# Vimshottari variations (textbook 16.4): start from Lagna, kshema (4th), utpanna (5th), adhana (8th) star
# --------------------------------------------------------------------------
def vimshottari_variant(moon_lon, lagna_lon, birth_dt_utc, variant, depth=2, year_days=YEAR_DAYS):
    """variant in moon|lagna|kshema|utpanna|adhana. Fraction left always from the reference point's own star."""
    if variant == "lagna":
        return vimshottari(lagna_lon, birth_dt_utc, depth, year_days)
    idx, _, frac_done = nakshatra_of(moon_lon)
    off = {"moon": 0, "kshema": 3, "utpanna": 4, "adhana": 7}[variant]
    start_nak = (idx + off) % 27
    lord0 = NAK_LORDS[start_nak % 9]
    seq = ["Ke", "Ve", "Su", "Mo", "Ma", "Ra", "Ju", "Sa", "Me"]
    i0 = seq.index(lord0)
    balance = DASHA_YEARS[lord0] * (1 - frac_done)
    t = birth_dt_utc - timedelta(days=(DASHA_YEARS[lord0] - balance) * year_days)
    periods = []
    for k in range(9):
        L = seq[(i0 + k) % 9]
        yrs = DASHA_YEARS[L]
        end = t + timedelta(days=yrs * year_days)
        md = {"lord": L, "start": t, "end": end, "sub": sub_periods(L, t, yrs, depth - 1, year_days) if depth >= 2 else []}
        periods.append(md)
        t = end
    return lord0, balance, periods


def utpanna_sign_compare(moon_lon, pos):
    """16.5.2: compare strength of Moon's sign vs the sign of the 5th star's same pada."""
    idx, pada, _ = nakshatra_of(moon_lon)
    span = 360.0 / 27
    star5 = (idx + 4) % 27
    lon5 = star5 * span + (pada - 0.5) * span / 4
    s5 = sign_of(lon5)
    sm = sign_of(moon_lon)
    return sm, s5, stronger_rasi(sm, s5, pos) if sm != s5 else sm


# --------------------------------------------------------------------------
# Tajaka monthly (maasa) and sixty-hour (shashti-hora) charts (textbook 27.3-27.4, 28.7, 31)
# --------------------------------------------------------------------------
def masa_kundali(vk, natal_sun_lon, natal_lagna_sign, month, lat, lon, tzname):
    """month 1..12 of the Tajaka year in vk (from varsha_kundali)."""
    target = norm(natal_sun_lon + 30 * (month - 1))
    jd_mp = find_sun_at(target, vk["jd_vp"] + 30.44 * (month - 1)) if month > 1 else vk["jd_vp"]
    pos, _ = compute_positions(jd_mp)
    mlagna = compute_lagna(jd_mp, lat, lon)
    mls = sign_of(mlagna)
    day = is_daytime(jd_mp, lat, lon)
    hb = harsha_bala(pos, mls, day)
    pvb = pancha_vargeeya(pos)
    lum = "Su" if day else "Mo"
    cands = [("lord of %s's rasi" % PLANET_NAME[lum], SIGN_LORD[sign_of(pos[lum]["lon"])]),
             ("natal lagna lord", SIGN_LORD[natal_lagna_sign]),
             ("Muntha lord", SIGN_LORD[vk["muntha"]]),
             ("masa lagna lord", SIGN_LORD[mls]),
             ("trirasi lord", TRIRASI[mls][0 if day else 1]),
             ("Varshesha", vk["varshesha"])]
    info = []
    for why, p in cands:
        h = (mls - sign_of(pos[p]["lon"])) % 12 + 1
        an, ak = TAJAKA_ASPECT[h]
        info.append({"planet": p, "why": why, "aspect_on_lagna": an, "kind": ak, "pvb": pvb[p][0]})
    counts = {}
    for c in info:
        counts[c["planet"]] = counts.get(c["planet"], 0) + 1
    benefic = [c for c in info if "benefic" in c["kind"]]
    pool = benefic or [c for c in info if c["kind"] not in ("none", "neutral")] or info
    pool = sorted(pool, key=lambda c: (c["pvb"], counts[c["planet"]]), reverse=True)
    sc_antar = (vk["muntha"] + month - 1) % 12  # SC antardasa sign (31.3), muntha progressed one house per month
    return {"jd_mp": jd_mp, "pos": pos, "lagna": mlagna, "lagna_sign": mls, "day": day, "harsha": hb, "pvb": pvb,
            "candidates": info, "masesha": pool[0]["planet"], "sc_antar_sign": sc_antar,
            "yogas": tajaka_yogas(pos, mls), "month": month}


def shashti_hora_chart(natal_sun_lon, jd_when, lat, lon):
    """Chart at the start of the 60-hour period containing jd_when (Sun in 2°30' steps from natal Sun)."""
    sl = sun_lon_at(jd_when)
    steps = int(norm(sl - natal_sun_lon) // 2.5)
    target = norm(natal_sun_lon + 2.5 * steps)
    jd_s = find_sun_at(target, jd_when - 1.3)
    if jd_s > jd_when:
        jd_s = find_sun_at(target, jd_when - 3.8)
    pos, _ = compute_positions(jd_s)
    lag = compute_lagna(jd_s, lat, lon)
    jd_e = find_sun_at(norm(target + 2.5), jd_s + 2.55)
    return {"jd_start": jd_s, "jd_end": jd_e, "pos": pos, "lagna": lag, "lagna_sign": sign_of(lag),
            "index_in_month": steps % 12 + 1, "yogas": tajaka_yogas(pos, sign_of(lag))}


# --------------------------------------------------------------------------
# Special nakshatras (textbook 26.4.2)
# --------------------------------------------------------------------------
SPECIAL_NAKS = [(1, "Janma", "general well-being"), (4, "Jaati", "community / peers"), (7, "Naidhana", "suffering"),
                (10, "Karma", "profession, workplace"), (12, "Desa", "country"), (13, "Abhisheka (Rajya)", "power, authority"),
                (16, "Sanghatika", "group / social activities"), (18, "Saamudayika", "crowds, mass activities"),
                (19, "Aadhaana", "well-being of family/lineage")]


def special_nakshatras(janma_nak):
    return {(janma_nak + n - 1) % 27: (name, meaning) for n, name, meaning in SPECIAL_NAKS}


# --------------------------------------------------------------------------
# Matter analysis in Tajaka / prashna charts (textbook 29.2 Ithasala results):
# ithasala involving lagna lord, lord of the related house, lord of the related saham,
# or the natural karaka -> fulfilment of the matter; eesarpha -> slipping away.
# --------------------------------------------------------------------------
MATTER_MAP = {1: ("Punya (fortune)", "Su"), 2: ("Artha (money)", "Ju"), 3: ("Bhratri (siblings)", "Ma"),
              4: ("Vidya (education)", "Me"), 5: ("Putra (children)", "Ju"), 6: ("Roga (illness)", "Sa"),
              7: ("Vivaha (marriage)", "Ve"), 8: (None, "Sa"), 9: ("Punya (fortune)", "Ju"),
              10: ("Rajya (position)", "Su"), 11: ("Labha (gains)", "Ju"), 12: ("Paradesa (foreign)", "Sa")}


def matter_analysis(pos, lagna_lon, house, is_day):
    ls = sign_of(lagna_lon)
    hs = (ls + house - 1) % 12
    ll = SIGN_LORD[ls]
    hl = SIGN_LORD[hs]
    saham_name, karaka = MATTER_MAP[house]
    sh = sahams(pos, lagna_lon, is_day)
    lines = []
    sig = {"lagna lord": ll, f"{house}th lord": hl, "karaka": karaka}
    if saham_name and saham_name in sh:
        slon = sh[saham_name]
        sig[f"{saham_name} lord"] = SIGN_LORD[sign_of(slon)]
        lines.append(f"  {saham_name} saham at {SIGNS[sign_of(slon)]} {dms(deg_in_sign(slon))} (house {house_from(ls, sign_of(slon))}), lord {PLANET_NAME[SIGN_LORD[sign_of(slon)]]}")
    occ = [PLANET_NAME[p] for p in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"] if sign_of(pos[p]["lon"]) == hs]
    lines.append(f"  House {house} = {SIGNS[hs]}: {', '.join(occ) or 'empty'}; lord {PLANET_NAME[hl]} in house {house_from(ls, sign_of(pos[hl]['lon']))}"
                 f"{' (R)' if pos[hl]['retro'] and hl not in ('Ra','Ke') else ''}")
    lines.append(f"  Lagna lord {PLANET_NAME[ll]} in house {house_from(ls, sign_of(pos[ll]['lon']))}; Chandra in house {house_from(ls, sign_of(pos['Mo']['lon']))}")
    plist = list(dict.fromkeys(p for p in sig.values() if p in SPEED_ORDER))
    found = False
    for i, a in enumerate(plist):
        for b in plist[i + 1:]:
            fa, sb = (a, b) if SPEED_ORDER.index(a) > SPEED_ORDER.index(b) else (b, a)
            kind, gap = ithasala_between(fa, sb, pos)
            if kind:
                roles_a = "/".join(k for k, v in sig.items() if v == a)
                roles_b = "/".join(k for k, v in sig.items() if v == b)
                lines.append(f"  {'ITHASALA (' + kind + ')' if kind != 'eesarpha' else 'EESARPHA'}: {PLANET_NAME[a]} [{roles_a}] – {PLANET_NAME[b]} [{roles_b}], gap {abs(gap):.1f}°"
                             + ("  -> favours fulfilment" if kind != "eesarpha" else "  -> matter slipping away / delayed"))
                found = True
    for q in plist:
        if q == "Mo":
            continue
        k2, g2 = ithasala_between("Mo", q, pos)
        if k2 and k2 != "eesarpha":
            lines.append(f"  Chandra ithasala ({k2}) with {PLANET_NAME[q]} — Kamboola support (29.2)")
            found = True
    if not found:
        lines.append("  No ithasala among the significators — no strong Tajaka promise for this matter in this chart")
    return lines


# --------------------------------------------------------------------------
# Shatpanchasika / Chappanna of Prithuyasas — prashna rules (project text: B. Suryanarain Rao,
# "Chappanna or Prasna Sastra", 1946, with Rao's corrected renderings in [ ]).
# Only objective, house/sign-based rules are implemented. Stanzas on sex of unborn child (43b, 47),
# sexual union (51) and the explicit death clauses (36, 55) are NOT rendered as predictions (project policy).
# --------------------------------------------------------------------------
SIRSHODAYA = {2, 4, 5, 6, 7, 10}          # Ge Le Vi Li Sc Aq
PRISHTODAYA = {0, 1, 3, 8, 9}             # Ar Ta Cn Sg Cp   (Pi = ubhayodaya)
MALE_SIGNS = {0, 2, 4, 6, 8, 10}
JALA_RASIS = {3, 11, 9}                   # Cn Pi Cp (Rao: Kumbha per some)
DIRECTION = {"Su": "East", "Ve": "South-East", "Ma": "South", "Ra": "South-West", "Sa": "West",
             "Mo": "North-West", "Me": "North", "Ju": "North-East", "Ke": "South-West"}
SHAT_TOPICS = ["general", "travel", "abroad", "lost", "dispute", "health", "marriage", "subject", "rain"]


def _sh_ctx(pos, lagna_lon):
    ls = sign_of(lagna_lon)
    ben = natural_benefics(pos)
    mal = {p for p in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"] if p not in ben}
    S = {p: sign_of(pos[p]["lon"]) for p in pos}
    H = {p: house_from(ls, S[p]) for p in pos}
    def inh(h, grp=None):
        return [p for p in (grp if grp is not None else pos) if H[p] == h]
    def ben_in(h):
        return [p for p in ben if H[p] == h]
    def mal_in(h):
        return [p for p in mal if H[p] == h]
    def ben_asp(h):
        hs = (ls + h - 1) % 12
        return [p for p in ben if S[p] == hs or (p not in ("Ra", "Ke") and graha_aspects_sign(p, hs, pos))]
    def mal_asp(h):
        hs = (ls + h - 1) % 12
        return [p for p in mal if p not in ("Ra", "Ke") and graha_aspects_sign(p, hs, pos)]
    pvb = pancha_vargeeya(pos)
    strongest = max(["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"], key=lambda p: pvb[p][0])
    moon_bright = norm(pos["Mo"]["lon"] - pos["Su"]["lon"])
    full_moon = 120 <= moon_bright <= 240
    return dict(ls=ls, ben=ben, mal=mal, S=S, H=H, inh=inh, ben_in=ben_in, mal_in=mal_in, ben_asp=ben_asp,
                mal_asp=mal_asp, pvb=pvb, strongest=strongest, full_moon=full_moon, stype=sign_type(ls))


def _names(ps):
    return "/".join(PLANET_NAME[p][:5] for p in ps) if ps else "-"


def shatpanchasika(pos, lagna_lon, topic="general", is_day=True):
    c = _sh_ctx(pos, lagna_lon)
    ls, S, H, ben, mal = c["ls"], c["S"], c["H"], c["ben"], c["mal"]
    inh, ben_in, mal_in, ben_asp, mal_asp = c["inh"], c["ben_in"], c["mal_in"], c["ben_asp"], c["mal_asp"]
    K = (1, 4, 7, 10)
    out = []
    def add(st, rule, verdict):
        out.append((st, rule, verdict))

    # ---------- general (stanzas 3, 4, 5, 28-31) ----------
    if topic in ("general", "travel", "abroad", "lost", "dispute", "health", "marriage"):
        lagna_ben_owner = ls in BENEFIC_OWNED
        # benefic vargas of lagna: count benefic lords among D1,D2,D3,D9,D12,D30 (shadvarga)
        vl = [SIGN_LORD[varga_sign(lagna_lon, d)] for d in (1, 2, 3, 9, 12, 30)]
        nb = sum(1 for p in vl if p in ("Ju", "Ve", "Me", "Mo"))
        sir = ls in SIRSHODAYA
        pts = (1 if lagna_ben_owner else -1) + (1 if nb >= 4 else -1 if nb <= 2 else 0) + (1 if sir else -1 if ls in PRISHTODAYA else 0)
        verdict = "SUCCESS indicated" if pts >= 2 else "FAILURE indicated" if pts <= -2 else "MIXED — success only with great effort"
        add(4, f"Lagna {SIGNS[ls]}: {'benefic-owned' if lagna_ben_owner else 'malefic-owned'}, {nb}/6 benefic shadvarga lords, "
               f"{'Sirshodaya' if sir else 'Prishtodaya' if ls in PRISHTODAYA else 'Ubhayodaya'}", verdict)
        # Stanza 5: Dhatu/Moola/Jeeva from lagna navamsa
        nv = int(deg_in_sign(lagna_lon) // (30 / 9)) + 1
        grp = ["Dhatu (mineral/inanimate)", "Moola (vegetable/root)", "Jeeva (living being)"][(nv - 1) // 3]
        if not is_odd_sign(ls):
            grp = ["Jeeva (living being)", "Moola (vegetable/root)", "Dhatu (mineral/inanimate)"][(nv - 1) // 3]
        add(5, f"Lagna navamsa {nv} in {'odd' if is_odd_sign(ls) else 'even'} sign", f"object of the query: {grp}")
        # Stanza 28
        bk = [p for p in ben if H[p] in K + (5, 9)]
        mk = [p for p in mal if H[p] in K + (8,)]
        if bk and not mk:
            add(28, f"benefics {_names(bk)} in kendra/trikona, no malefics in kendras/8th", "querent gains ALL desired in full")
        elif mk and not bk:
            add(28, f"malefics {_names(mk)} in kendras/8th, no benefics in kendra/trikona", "complete failure of the desire; caution")
        elif mk:
            add(28, f"benefics {_names(bk)} in kendra/trikona but malefics {_names(mk)} in kendras/8th", "partial — obstacles")
        # Stanza 29
        g = [p for p in ben if H[p] in (3, 5, 7, 11)]
        l = [p for p in mal if H[p] in (3, 5, 7, 11)]
        if g or l:
            add(29, f"3/5/7/11: benefics {_names(g)}, malefics {_names(l)}", ("gains & success" if len(g) > len(l) else "losses" if len(l) > len(g) else "gains and losses both"))
        if ls in (2, 5, 6, 10) and ben_in(1):
            add(29, f"Lagna {SIGNS[ls]} (Ge/Vi/Li/Aq) with benefic {_names(ben_in(1))}", "success foretold")
        # Stanza 30
        if ben_in(7) or ben_in(10):
            add(30, f"benefics in 7th/10th: {_names(ben_in(7) + ben_in(10))}", "gain of land/position")
        if ben_in(2) or ben_in(5) or ben_in(1):
            add(30, f"benefics in 1/2/5: {_names(ben_in(1) + ben_in(2) + ben_in(5))}", "wealth & honour from authorities")
        if mal_in(11) or mal_in(12):
            add(30, f"malefics in 11th/12th: {_names(mal_in(11) + mal_in(12))}", "no success in the matter")
        if H["Mo"] == 1:
            add(30, "Chandra in Lagna", "not favourable for the matter")
        elif H["Mo"] == 10:
            add(30, "Chandra in 10th", "prosperity")
        # Stanza 31
        if H["Mo"] in (2, 3, 6, 7, 10, 11) and graha_aspects_planet("Ju", "Mo", pos):
            add(31, f"Chandra in {H['Mo']} aspected by Guru", "success through a woman's help")
        ml = [p for p in mal if H[p] in (1, 3, 5, 8, 9)]
        bl = [p for p in ben if H[p] in (1, 3, 5, 8, 9)]
        if ml and not bl:
            add(31, f"malefics {_names(ml)} in 1/3/5/8/9", "loss of the object in mind, monetary loss, fear")
        elif bl and not ml:
            add(31, f"benefics {_names(bl)} in 1/3/5/8/9", "good in all these respects")

    # ---------- travel & return (stanzas 2, 8, 33-37, 52-56) ----------
    if topic in ("travel", "abroad"):
        st = c["stype"]
        add(8, f"Lagna {SIGNS[ls]} is {['movable', 'fixed', 'dual'][st]}",
            ["traveller has suffered / moved / met loss", "traveller has not left, no harm, no loss, no defeat", "mixed results"][st])
        lb, lm = ben_asp(1) + ben_in(1), mal_asp(1) + mal_in(1)
        mb = [p for p in ben if S[p] == S["Mo"] or graha_aspects_planet(p, "Mo", pos)]
        mm = [p for p in mal if p != "Mo" and (S[p] == S["Mo"] or graha_aspects_planet(p, "Mo", pos))]
        add(8, f"Lagna & Chandra influences: benefic {_names(set(lb) | set(mb))}, malefic {_names(set(lm) | set(mm))}",
            "good" if (lb or mb) and not (lm or mm) else "unfavourable" if (lm or mm) and not (lb or mb) else "mixed")
        p235 = [p for p in inh(2) + inh(3) + inh(5) if p not in ("Ra", "Ke")]
        if p235:
            b = [p for p in p235 if p in ben]
            add(33, f"planets in 2/3/5: {_names(p235)}", ("return with property/riches" if b else "return, but without gains")
                + ("; SPEEDY return (Guru/Shukra there)" if any(p in ("Ju", "Ve") for p in p235) else ""))
        if (inh(6) or inh(7)) and (H["Ju"] in K or H["Me"] in (5, 9) or H["Ve"] in (5, 9)):
            add(34, "planet in 6th/7th, with Guru in kendra or Budha/Shukra in 5th/9th", "traveller WILL return (Rao's reading)")
        if H["Mo"] == 8:
            km = [p for p in mal if H[p] in K]
            kb = [p for p in ben if H[p] in K]
            add(35, f"Chandra in 8th; kendras: malefics {_names(km)}, benefics {_names(kb)}",
                "safe return" + (" with wealth & honour" if kb else "") if not km else "return uncertain (malefics in kendras)")
        if ls in PRISHTODAYA and mal_asp(1):
            add(36, f"Prishtodaya lagna aspected by malefic {_names(mal_asp(1))}", "traveller has suffered restraint / hardship")
        for h, txt in ((3, "traveller has left the place he first went to"), (6, "grave danger to the traveller — classical text gives the worst reading; not predicted here"),):
            m = mal_in(h)
            if m and not ben_asp(h):
                add(36, f"malefics {_names(m)} in {h}th, no benefic aspect", txt)
        kmu = [p for p in mal if H[p] in K and not ben_asp(H[p])]
        if kmu:
            add(36, f"malefics {_names(kmu)} in kendras without benefic aspect", "traveller waylaid / removed by robbers (classical)")
        # Stanza 37 timing
        for k in range(1, 12):
            hs = (ls + k) % 12
            occ = [p for p in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"] if S[p] == hs]
            if occ:
                n = k + 1
                retro = any(pos[p]["retro"] for p in occ)
                add(37, f"first occupied sign from Lagna is {n}th ({SIGNS[hs]}, {_names(occ)}){' retrograde' if retro else ''}",
                    f"return within {n} days (retrograde rule, Rao)" if retro else f"return within {n} x 12 = {n * 12} days")
                break
        # Stanza 52-56 (person abroad)
        if c["stype"] == 0 and int(deg_in_sign(lagna_lon) // (30 / 9)) + 1 > 5 and sign_type(varga_sign(lagna_lon, 9)) == 0:
            add(52, "movable lagna in a movable navamsa beyond the 5th", "query concerns a person gone to a foreign land")
        rr = [p for p in ["Ma", "Me", "Ju", "Ve", "Sa"] if pos[p]["retro"] and H[p] in (8, 9, 10, 11, 12)]
        if rr:
            add(52, f"retrograde {_names(rr)} in houses 8-12", "return of the person indicated")
        p8 = inh(8)
        if p8:
            who = {"Su": "father", "Mo": "mother / maternal relations", "Ma": "brothers, cousins", "Me": "maternal uncles",
                   "Ju": "children, preceptor", "Ve": "wife, female relations", "Sa": "servants, dependents", "Ra": "-", "Ke": "-"}
            for p in p8:
                asp_b = [q for q in ben if q != p and (S[q] == S[p] or graha_aspects_planet(q, p, pos))]
                add(54 if p != "Su" else 53, f"{PLANET_NAME[p]} in 8th{' with benefic ' + _names(asp_b) if asp_b else ' (no benefic association)'}",
                    f"query about {who.get(p, '-')}: " + ("has moved on to another country; safe & prosperous return" if asp_b else "still in the first place; caution"))
        if H["Sa"] == 9 and [p for p in mal if p != "Sa" and S[p] == S["Sa"]] and not ben_asp(9):
            add(55, "Shani with malefics in 9th, no benefic aspect", "traveller suffering ill-health (recommend checking on them)")
        if c["stype"] == 0 and ben_in(1):
            add(56, f"movable lagna with benefic {_names(ben_in(1))}", "prosperity to the traveller")
        elif mal_in(1):
            add(56, f"malefics {_names(mal_in(1))} in prashna lagna", "trouble to the traveller" + (" (fixed lagna: mixed)" if c["stype"] == 1 else ""))

    # ---------- lost / stolen property (stanzas 7, 38-42) ----------
    if topic == "lost":
        fm = c["full_moon"]
        if H["Mo"] == 1 and fm and (graha_aspects_planet("Ju", "Mo", pos) or graha_aspects_planet("Ve", "Mo", pos)):
            add(7, "bright (full) Chandra in lagna aspected by Guru/Shukra", "SPEEDY recovery")
        pb11 = [p for p in ben_in(11) if is_strong(p, pos) or c["pvb"].get(p, (0,))[0] >= 12]
        if pb11:
            add(7, f"powerful benefic {_names(pb11)} in 11th", "recovery indicated")
        if ls in SIRSHODAYA and ben_in(1) and ben_asp(1):
            add(40, f"Sirshodaya lagna {SIGNS[ls]} with benefic {_names(ben_in(1))}, benefic aspect", "stolen article recovered soon")
        if not any(o[0] in (7, 40) for o in out):
            add(40, "none of the recovery combinations (7, 40) present", "recovery not promised by this prashna")
        nvs = varga_sign(lagna_lon, 9)
        if c["stype"] == 1 or sign_type(nvs) == 1 or nvs == ls:
            add(38, "lagna: " + ", ".join(x for x, ok in (("fixed sign", c["stype"] == 1), ("fixed navamsa", sign_type(nvs) == 1), ("vargottama", nvs == ls)) if ok),
                "article is still in the same place; taken by a close relation / insider")
        else:
            add(38, "lagna neither fixed, fixed-navamsa nor vargottama", "article has been moved away")
        dk = int(deg_in_sign(lagna_lon) // 10) + 1
        add(39, f"drekkana {dk} rising", ["front part of the house", "middle of the house", "back of the house or beyond"][dk - 1])
        kp = [p for p in pos if H[p] in K]
        ref = max(kp, key=lambda p: c["pvb"].get(p, (0,))[0]) if kp else SIGN_LORD[ls]
        add(41, f"strongest planet in kendras: {PLANET_NAME[ref]}" if kp else f"no planet in kendras; lagna lord {PLANET_NAME[ref]}", f"direction: {DIRECTION[ref]}")
        shape = "long" if ls in (4, 5, 6, 7) else "broad" if ls in (2, 3, 8, 9) else "small"
        add(42, f"lagna {SIGNS[ls]}", f"article shape: {shape}; colour/nature from navamsa {SIGNS[nvs]} (lord {PLANET_NAME[SIGN_LORD[nvs]]})")

    # ---------- dispute / competition / conflict (stanzas 9-27) ----------
    if topic == "dispute":
        b = [p for p in ben if H[p] in (1, 7, 10)]
        if b:
            add(24, f"benefics {_names(b)} in 1/7/10", "VICTORY to the querent")
        if H["Ma"] == 9 and H["Sa"] == 9:
            add(24, "Kuja & Shani in 9th", "defeat to the opponent")
        e9 = [p for p in ("Ju", "Me", "Ve") if H[p] == 9]
        if e9:
            add(24, f"{_names(e9)} in 9th", "victory to the OPPONENT")
        q = [p for p in ben if 3 <= H[p] <= 8]
        o = [p for p in ben if H[p] >= 9 or H[p] <= 2]
        add(25, f"benefics on querent's half (3-8): {_names(q)}; on opponent's half (9-2): {_names(o)}",
            "favours querent" if len(q) > len(o) else "favours opponent" if len(o) > len(q) else "balanced")
        m1012 = [p for p in mal if H[p] in (10, 11, 12)]
        if m1012:
            add(25, f"malefics {_names(m1012)} in 10/11/12", "defeat to the querent's side")
        if (ls in MALE_SIGNS and ben_in(1)) or ben_in(11) or ben_in(12):
            add(26, "male-sign lagna with benefic, or benefics in 11th/12th", "settlement / accommodation between the parties")
        md = [p for p in mal if sign_type(S[p]) == 2]
        if md:
            add(26, f"malefics {_names(md)} in dual signs", "fighting & enmity continue")
        bk = [p for p in ben if H[p] in K]
        mk = [p for p in mal if H[p] in K]
        if bk and not mk:
            add(27, f"benefics {_names(bk)} in kendras", "peace between the parties")
        elif mk and not bk:
            add(27, f"malefics {_names(mk)} in kendras", "they will fight")
        # opponent's movement (9-23) — court case / hostile party approaching
        st, mst = c["stype"], sign_type(S["Mo"])
        if st == 0 and mst == 1:
            add(11, "movable lagna, Chandra in fixed sign", "opponent does not come forward")
        elif st == 1 and mst == 0:
            add(11, "fixed lagna, Chandra in movable sign", "opponent comes in strength and presses")
        elif st == 1 and mst == 2:
            add(12, "fixed lagna, Chandra in dual sign", "opponent turns back after advancing far")
        elif st == 2 and mst == 0:
            add(13, "dual lagna, Chandra in movable sign", "opponent returns after coming half-way")
        elif st == 0 and mst == 2:
            add(13, "movable lagna, Chandra in dual sign", "opponent withdraws" + (" after a heavy defeat" if mal_asp(1) else ""))
        if st == 1 and (H["Ju"] == 1 or H["Sa"] == 1):
            add(16, "fixed lagna with Guru/Shani", "opponent does not come")
        if st == 0 and (H["Su"] == 1 or H["Ju"] == 1):
            add(16, "movable lagna with Surya/Guru", "opponent comes well prepared")
        if st == 0 and [p for p in ("Su", "Sa", "Me", "Ve") if H[p] == 1]:
            rp = [p for p in ("Sa", "Me", "Ve") if H[p] == 1 and pos[p]["retro"]]
            add(14, f"movable lagna with {_names([p for p in ('Su', 'Sa', 'Me', 'Ve') if H[p] == 1])}", "opponent turns back part-way" if not rp else f"opponent halts permanently (retrograde {_names(rp)})")
        if mal_in(4):
            add(9, f"malefics {_names(mal_in(4))} in 4th", "opponent retires disappointed after close approach")
        if (ls + 3) % 12 in (11, 7, 10, 3):
            add(10, f"4th house is {SIGNS[(ls + 3) % 12]} (Pi/Sc/Aq/Cn)", "opponent retreats in disgrace")
        if ls in (0, 4, 1, 8) or (ls + 3) % 12 in (0, 4, 1, 8):
            add(19, "lagna or 4th in Ar/Le/Ta/Sg", "opponent cannot stand; early retreat")
        if H["Su"] == 4 and H["Mo"] == 4:
            add(18, "Surya & Chandra in 4th", "hostile party will not arrive (Rao)")
        elif [p for p in ("Ju", "Me", "Ve") if H[p] == 4]:
            add(18, f"{_names([p for p in ('Ju', 'Me', 'Ve') if H[p] == 4])} in 4th", "hostile party arrives quickly (Rao)")
        if H["Ju"] == 2 or H["Ju"] == 3 or H["Ve"] == 2 or H["Ve"] == 3:
            add(17, "Guru/Shukra in 2nd or 3rd", "party gone out returns immediately (Rao)")
        n = (S[c["strongest"]] - ls) % 12 + 1
        mult = [1, 2, 3][sign_type(varga_sign(pos[c["strongest"]]["lon"], 9))]
        add(20, f"strongest planet {PLANET_NAME[c['strongest']]} is {n}th from lagna; navamsa {['movable', 'fixed', 'dual'][mult - 1]} (x{mult})",
            f"opponent withdraws within ~{n * mult} months")
        l7 = SIGN_LORD[(ls + 6) % 12]
        if pos[l7]["retro"]:
            add(21, f"7th lord {PLANET_NAME[l7]} retrograde", "opponent clears out when the 7th lord turns direct")
        nm = (S["Mo"] - ls) % 12 + 1
        between = [p for p in pos if p != "Mo" and 1 < (S[p] - ls) % 12 + 1 < nm]
        if not between:
            add(23, f"Chandra {nm}th from lagna, no planet between", f"opponent arrives within ~{nm} days")

    # ---------- health (stanza 32) ----------
    if topic == "health":
        b = [p for p in ben if H[p] in (1, 5, 7, 8)]
        ok = b and all(ben_asp(H[p]) for p in b) and H["Mo"] in (3, 6, 10, 11)
        add(32, f"benefics in 1/5/7/8: {_names(b)}; Chandra in {H['Mo']}",
            "safe recovery indicated" if ok else "recovery combination incomplete — no strong promise (astrology is not medical advice)")

    # ---------- marriage (stanzas 43a, 44) ----------
    if topic == "marriage":
        add(43, f"Shani in {H['Sa']}th", "marriage indicated (Shani in 7th)" if H["Sa"] == 7 else "Shani not in 7th — no promise from this stanza alone")
        if H["Mo"] in (3, 5, 6, 7, 11) and any(graha_aspects_planet(p, "Mo", pos) for p in ("Ju", "Su", "Me")):
            add(44, f"Chandra in {H['Mo']} aspected by Guru/Surya/Budha", "marriage will be celebrated")
        bk = [p for p in ben if H[p] in K + (5, 9)]
        if bk:
            add(44, f"benefics {_names(bk)} in kendra/trikona", "marriage celebrated speedily")

    # ---------- subject of the query (stanzas 49-50) ----------
    if topic == "subject":
        who = {1: "someone like / connected to the querent himself", 3: "brothers", 4: "mother or sisters", 5: "children",
               6: "enemies / opponents", 7: "wife / spouse", 9: "a virtuous person / elder", 10: "preceptor / person venerated"}
        sp = c["strongest"]
        add(49, f"strongest planet {PLANET_NAME[sp]} (PVB {c['pvb'][sp][0]}) in house {H[sp]}", f"query concerns: {who.get(H[sp], 'not classified by the text (2/8/11/12)')}")
        if SIGN_LORD[varga_sign(lagna_lon, 9)] in inh(1):
            add(50, "navamsa lord of lagna is in lagna", "query is about the querent himself")
        a48 = [p for p in ("Mo", "Me", "Sa", "Su", "Ju", "Ma", "Ve") if H[p] == 1 or graha_aspects_sign(p, ls, pos)]
        if a48:
            cls = {"Mo": "young", "Me": "young", "Sa": "old", "Su": "post-natal / mature", "Ju": "post-natal / mature", "Ma": "restless / difficult", "Ve": "pleasure-loving"}
            add(48, f"planets in/aspecting lagna: {_names(a48)}", "person's age/type: " + ", ".join(sorted({cls[p] for p in a48})))

    # ---------- rain (stanzas 45-46) ----------
    if topic == "rain":
        c1 = (S["Sa"] - S["Mo"]) % 12 == 6 or (H["Sa"] == 4 and H["Ve"] == 8) or (H["Sa"] in (2, 3) and H["Ve"] in (2, 3))
        add(45, "Shani 7th from Chandra / Shani 4th & Shukra 8th / both in 2nd-3rd", "early rain in the season" if c1 else "combination absent")
        bw = [p for p in ben if H[p] in (1, 2, 3, 4, 7, 10) and S[p] in JALA_RASIS]
        bright = norm(pos["Mo"]["lon"] - pos["Su"]["lon"]) < 180
        if bw and bright:
            add(46, f"benefics {_names(bw)} in watery signs in 1/2/3/4/7/10, bright fortnight", "plentiful rain")
        elif H["Mo"] == 1 and S["Mo"] in JALA_RASIS:
            add(46, "Chandra in lagna in a watery sign", "rain")
        else:
            add(46, "no rain combination", "-")
    return out


def print_shatpanchasika(pos, lagna_lon, topic, is_day):
    rules = shatpanchasika(pos, lagna_lon, topic, is_day)
    print(f"\nSHATPANCHASIKA (Prithuyasas; Rao 1946) — topic: {topic}   [St. = stanza]")
    for st, rule, verdict in rules:
        print(f"  St.{st:>2}  {rule}")
        print(f"         -> {verdict}")
    print("  Note: stanzas on sex of an unborn child (43b, 47), sexual conduct (51) and explicit death clauses are not rendered (project policy).")
    return [{"stanza": s, "rule": r, "verdict": v} for s, r, v in rules]


# --------------------------------------------------------------------------
# Self test (textbook examples)
# --------------------------------------------------------------------------
def selftest():
    ok = True
    def check(name, cond):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name)
        ok = ok and cond
    # AV totals
    pos = {c: {"lon": 35.0 + 7 * i, "speed": 1, "retro": False} for i, c in enumerate(["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"])}
    bav, sav = ashtakavarga(pos, 0)
    check("Ashtakavarga totals = 337", sum(sav) == 337)
    # Example 40-43: Mercury BAV of Chart 11 -> SoAV & sodhya pinda 152
    merc_bav = [7, 4, 7, 4, 4, 3, 4, 4, 4, 3, 6, 4]
    tri = trikona_sodhana(merc_bav)
    check("Example 40 Trikona sodhana", tri == [3, 1, 3, 0, 0, 0, 0, 0, 0, 0, 2, 0])
    p11 = {"Su": 65, "Ma": 66, "Me": 67, "Ve": 5, "Mo": 100, "Ju": 130, "Sa": 160, "Ra": 200, "Ke": 20}
    p11 = {k: {"lon": v, "speed": 1, "retro": False} for k, v in p11.items()}
    so = ekadhipatya_sodhana(tri, p11)
    check("Example 41 Ekadhipatya sodhana (no change)", so == tri)
    check("Example 43 Sodhya pinda = 152 (77 + 75)", sodhya_pinda(so, p11) == (77, 75, 152))
    # Narayana progression (Table 40)
    AB = ["Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi"]
    def seq(seed, occ=None):
        p = {c: {"lon": 185.0, "speed": 1, "retro": False} for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]}
        if occ:
            p[occ]["lon"] = seed * 30 + 5
        return " ".join(AB[x] for x in narayana_progression(seed, p))
    check("Table 40: Ta", seq(1) == "Ta Sg Cn Aq Vi Ar Sc Ge Cp Le Pi Li")
    check("Table 40: Pi", seq(11) == "Pi Cn Sc Sg Ar Le Vi Cp Ta Ge Li Aq")
    check("Table 40: Sc+Ke", seq(7, "Ke") == "Sc Ar Vi Aq Cn Sg Ta Li Pi Le Cp Ge")
    check("Table 40: Sc+Sa", seq(7, "Sa") == "Sc Sg Cp Aq Pi Ar Ta Ge Cn Le Vi Li")
    # Example 66 dasa lengths
    p = {"Su": 100, "Mo": 40, "Ma": 130, "Me": 132, "Ju": 220, "Ve": 134, "Sa": 42, "Ra": 280, "Ke": 100}
    p = {k: {"lon": v, "speed": 1, "retro": False} for k, v in p.items()}
    exp = [4, 3, 2, 3, 1, 1, 10, 9, 11, 8, 9, 4]
    check("Example 66 dasa lengths", [narayana_length(s_, p)[0] for s_ in range(12)] == exp)
    # Example 118 varsha pravesha 2000-03-08 04:41:21 IST
    jd, _ = to_jd_ut(datetime(1967, 3, 8, 17, 40), "Asia/Kolkata")
    npos, _ = compute_positions(jd)
    nlag = sign_of(compute_lagna(jd, 26.3, 73.0667))
    vk = varsha_kundali(npos["Su"]["lon"], nlag, 1967, 3, 8, 2000, 26.3, 73.0667, "Asia/Kolkata", npos["Mo"]["lon"])
    vp_local = jd_to_datetime(vk["jd_vp"]).astimezone(ZoneInfo("Asia/Kolkata"))
    check("Example 118 varsha pravesha 2000-03-08 04:41 IST",
          (vp_local.year, vp_local.month, vp_local.day, vp_local.hour, vp_local.minute) == (2000, 3, 8, 4, 41))
    check("Example 118 varsha lagna Cp, Muntha Ta, Varshesha Ma",
          vk["lagna_sign"] == 9 and vk["muntha"] == 1 and vk["varshesha"] == "Ma")
    # Ithasala textbook example: Moon 14 Le, Venus 19 Li -> vartamana; Moon 23 Le -> eesarpha
    tp = {c: {"lon": 5.0, "speed": 1, "retro": False} for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]}
    tp["Mo"]["lon"] = 4 * 30 + 14; tp["Ve"]["lon"] = 6 * 30 + 19
    check("Ithasala example (vartamana)", ithasala_between("Mo", "Ve", tp)[0] == "vartamana")
    tp["Mo"]["lon"] = 4 * 30 + 18 + 25 / 60
    check("Ithasala example (poorna)", ithasala_between("Mo", "Ve", tp)[0] == "poorna")
    tp["Mo"]["lon"] = 4 * 30 + 23
    check("Eesarpha example", ithasala_between("Mo", "Ve", tp)[0] == "eesarpha")
    # Sri Lanka historical offset
    _, off = to_jd_ut(datetime(1999, 10, 28, 8, 11), "Asia/Colombo")
    check("Asia/Colombo Oct 1999 = UTC+6:00", off == timedelta(hours=6))
    # --- Kalachakra (ch.24) ---
    b0 = datetime(2000, 1, 1, tzinfo=timezone.utc)
    kc = kalachakra_dasa(30 + 15 + 50 / 60, b0, 360)
    check("Example 95 Kalachakra: Rohini-2 rasis, paramayush 83, Sc dasa 4.75y left",
          [AB[r] for r in kc["pada_rasis"]] == "Vi Li Sc Pi Aq Cp Sg Sc Li".split() and kc["paramayush"] == 83
          and AB[kc["dasas"][0]["sign"]] == "Sc" and abs(kc["balance_years"] - 4.75) < 1e-9
          and [AB[d["sign"]] for d in kc["dasas"][1:9]] == "Li Vi Le Cn Ge Ta Ar Sg".split())
    check("Example 97 Kalachakra antardasas of Sc and Le dasas",
          [AB[a["sign"]] for a in kc["dasas"][0]["antar"]] == "Sc Li Vi Le Cn Ge Ta Ar Sg".split()
          and [AB[a["sign"]] for a in kc["dasas"][3]["antar"]] == "Le Cn Ge Ta Ar Sg Cp Aq Pi".split())
    kc = kalachakra_dasa(93.0, b0, 360)
    check("Example 96 Kalachakra: Punarvasu-4, 86y, Pi dasa 8.6y left",
          kc["paramayush"] == 86 and AB[kc["dasas"][0]["sign"]] == "Pi" and abs(kc["balance_years"] - 8.6) < 1e-9
          and [AB[d["sign"]] for d in kc["dasas"][1:9]] == "Sc Li Vi Cn Le Ge Ta Ar".split())
    kc = kalachakra_dasa(300 + 5 + 50 / 60, b0, 360)
    check("Exercise 34 Kalachakra: Dhanishtha-4, 100y, Ge 2y left, deha Ar jeeva Sg",
          kc["paramayush"] == 100 and AB[kc["dasas"][0]["sign"]] == "Ge" and abs(kc["balance_years"] - 2.0) < 1e-9
          and [AB[d["sign"]] for d in kc["dasas"][1:10]] == "Ta Ar Sg Cp Aq Pi Ar Ta Ge".split()
          and AB[kc["deha"]] == "Ar" and AB[kc["jeeva"]] == "Sg")
    check("Tables 44-47 spot rows", all(" ".join(AB[x] for x in kalachakra_pada_rasis(n_, p_)[0]) == e_ for n_, p_, e_ in
          [(0, 3, "Ta Ar Pi Aq Cp Sg Ar Ta Ge"), (1, 3, "Li Sc Sg Cp Aq Pi Sc Li Vi"), (3, 3, "Vi Le Cn Ge Ta Ar Sg Cp Aq"),
           (4, 2, "Ge Ta Ar Sg Cp Aq Pi Ar Ta"), (25, 1, "Sc Li Vi Cn Le Ge Ta Ar Pi")]))
    # --- Ashtottari (ch.17) ---
    L_, bal_, ad_ = ashtottari_dasa(144.0, b0, 360)
    check("Example 59 Ashtottari: Moon 24Le -> Mo 6y, then Ma Me Sa; Ju antardasas start Ra end Ju",
          L_ == "Mo" and abs(bal_ - 6) < 1e-9 and [x["lord"] for x in ad_[1:4]] == ["Ma", "Me", "Sa"]
          and [a["lord"] for a in [x for x in ad_ if x["lord"] == "Ju"][0]["antar"]] == ["Ra", "Ve", "Su", "Mo", "Ma", "Me", "Sa", "Ju"])
    check("Ashtottari Rahu arc wrap (10Ar -> 3.75y, 20Pi -> 8.25y)",
          abs(ashtottari_dasa(10.0, b0, 360)[1] - 3.75) < 1e-9 and abs(ashtottari_dasa(350.0, b0, 360)[1] - 8.25) < 1e-9)
    # --- Special lagnas (ch.5) ---
    sl_ = special_lagnas(2451545.0, 0, 0, 175 + 5 / 60, 193 + 6 / 60)["SL"]
    check("Example 10 Sree Lagna = 18Pi47", sign_of(sl_) == 11 and abs(deg_in_sign(sl_) - (18 + 47 / 60)) < 0.02)
    sl_ = special_lagnas(2451545.0, 0, 0, 224 + 19 / 60, 135 + 29 / 60)["SL"]
    check("Exercise 10 Sree Lagna = 12Cp22", sign_of(sl_) == 9 and abs(deg_in_sign(sl_) - (12 + 22 / 60)) < 0.02)
    check("Hora example 1.3.11 (Wed 21:40, sunrise 6:10 -> Chandra hora)", hora_lord(2451545.0 + 15.5 / 24, 2451545.0, "Me")[0] == "Mo")
    check("Tara Table 64 (7th from janma = Naidhana)", TARA_NAMES[tara_of(0, 6)].startswith("Naidhana") and TARA_NAMES[tara_of(0, 10)].startswith("Sampat"))
    # --- Sudasa Example 77: SL 12Cp21 -> Cp Li Cn Ar Sg Vi Ge Pi Sc Le Ta Aq, first fraction 0.5883
    p77 = {c: {"lon": 100.0, "speed": 1, "retro": False} for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]}
    sls_, sfr_, sord_, _ = sudasa(270 + 12 + 21 / 60, p77, b0)
    check("Example 77 Sudasa order & first fraction", [AB[x] for x in sord_] == "Cp Li Cn Ar Sg Vi Ge Pi Sc Le Ta Aq".split() and abs(sfr_ - 0.5883) < 1e-3)
    # --- Sudarsana Example 127: 60th year -> 12th house
    check("Example 127 Sudarsana: year 60 -> house 12", sudarsana_dasa(60, 0, p77)["house"] == 12 and sudarsana_dasa(45, 0, p77)["house"] == 9)
    # --- Compressed Vimshottari 35.4: 120y -> 360d, Sun dasa 18 d
    cv_ = compressed_vimshottari(66.7, b0, 360)  # Moon in Ardra (Rahu) -> Ra first
    check("35.4 compressed dasa: Ardra -> Rahu first 54d, Sun 18d", cv_[0]["lord"] == "Ra" and abs(cv_[0]["days"] - 54) < 1e-9
          and abs([x for x in cv_ if x["lord"] == "Su"][0]["days"] - 18) < 1e-9)
    # --- Upagrahas Example 6: Sun 9Sg36 -> Dhuma 22Ar56, Vyatipata 7Pi04, Parivesha 7Vi04, Indrachapa 22Li56
    u_ = sun_upagrahas(240 + 9 + 36 / 60)
    check("Example 6 Sun-based upagrahas", sign_of(u_["Dhuma"]) == 0 and abs(deg_in_sign(u_["Dhuma"]) - (22 + 56 / 60)) < 0.01
          and sign_of(u_["Vyatipata"]) == 11 and abs(deg_in_sign(u_["Vyatipata"]) - (7 + 4 / 60)) < 0.01
          and sign_of(u_["Parivesha"]) == 5 and sign_of(u_["Indrachapa"]) == 6)
    # --- Drigdasa Examples 80 & 82
    check("Example 80 Drigdasa order (Li lagna)", [AB[x] for x in drigdasa(6, p77, b0)[0]] == "Ge Vi Sg Pi Cn Ta Aq Sc Le Ar Cp Li".split())
    check("Example 82 Drigdasa order (Aq lagna)", [AB[x] for x in drigdasa(10, p77, b0)[0]] == "Li Aq Ta Le Sc Cp Ar Cn Sg Pi Ge Vi".split())
    # --- Kendradi ch.19 examples (Ge forward, Ta backward)
    pk_ = {c: {"lon": 100.0, "speed": 1, "retro": False} for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]}
    pk_["Ju"]["lon"] = 65
    check("19.2 Kendradi order Ge forward", [AB[x] for x in kendradi_rasi_dasa(2, pk_, b0)[2]] == "Ge Vi Sg Pi Cn Li Cp Ar Le Sc Aq Ta".split())
    pk_["Ju"]["lon"] = 35
    check("19.2 Kendradi order Ta backward", [AB[x] for x in kendradi_rasi_dasa(1, pk_, b0)[2]] == "Ta Aq Sc Le Ar Cp Li Cn Pi Sg Vi Ge".split())
    # --- Argala 10.6 example: Me Ge, Ju Pi, Ve Ar, Sa Vi
    pa_ = {c: {"lon": 100.0, "speed": 1, "retro": False} for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]}
    for c, v in (("Me", 65), ("Ju", 335), ("Ve", 5), ("Sa", 155), ("Su", 65)):
        pa_[c]["lon"] = v
    a_ = argala_on(2, pa_)
    check("10.6 Argala example (Sa papa 4, Ve subha 11, Ju virodha 10)",
          ("Sa", 4) in a_["papa"] and ("Ve", 11) in a_["subha"] and any(v[0] == "Ju" and v[1] == 10 for v in a_["virodha"]))
    # --- Vimshottari variations Example 51 (frac left 0.32125): kshema Sa 6.10375, utpanna Me 5.46125, adhana Su 1.9275
    span_ = 360 / 27
    ml_ = 22 * span_ + (1 - 0.32125) * span_
    check("Example 51 Vimshottari variants", all(vimshottari_variant(ml_, 0, b0, v_, 1)[0] == L_ and abs(vimshottari_variant(ml_, 0, b0, v_, 1)[1] - e_) < 1e-6
          for v_, L_, e_ in (("kshema", "Sa", 6.10375), ("utpanna", "Me", 5.46125), ("adhana", "Su", 1.9275))))
    # --- Tajaka monthly / sixty-hour (27.3, 27.4): 2000-04-07 10:38 IST; 2000-04-09 23:40 IST
    mk_ = masa_kundali(vk, npos["Su"]["lon"], nlag, 2, 26.3, 73.0667, "Asia/Kolkata")
    mp_l = jd_to_datetime(mk_["jd_mp"]).astimezone(ZoneInfo("Asia/Kolkata"))
    check("27.3 second monthly chart 2000-04-07 ~10:38 IST", (mp_l.month, mp_l.day, mp_l.hour) == (4, 7, 10) and abs(mp_l.minute - 38) <= 2)
    jq_, _ = to_jd_ut(datetime(2000, 4, 10, 12, 0), "Asia/Kolkata")
    sh_ = shashti_hora_chart(npos["Su"]["lon"], jq_, 26.3, 73.0667)
    sh_l = jd_to_datetime(sh_["jd_start"]).astimezone(ZoneInfo("Asia/Kolkata"))
    check("27.4 second shashti-hora 2000-04-09 ~23:40 IST", (sh_l.month, sh_l.day, sh_l.hour) == (4, 9, 23) and abs(sh_l.minute - 40) <= 2 and sh_["index_in_month"] == 2)
    # --- natural benefics 3.3
    pb_ = {c: {"lon": 10.0, "speed": 1, "retro": False} for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]}
    pb_["Mo"]["lon"] = 100; pb_["Ju"]["lon"] = 200; pb_["Ve"]["lon"] = 200; pb_["Sa"]["lon"] = 200; pb_["Ra"]["lon"] = 200; pb_["Ke"]["lon"] = 20
    check("3.3 natural benefics (waxing Chandra benefic; Budha with Surya+Kuja malefic)", natural_benefics(pb_) == {"Ju", "Ve", "Mo"})
    # --- Shatpanchasika: Rao's worked example under stanza 37 — 1921-07-27 15:30 IST Bangalore: Sc lagna, Chandra 6th -> 72 days
    jq_, _ = to_jd_ut(datetime(1921, 7, 27, 15, 30), "Asia/Kolkata")
    pq_, _ = compute_positions(jq_)
    lq_ = compute_lagna(jq_, 12.97, 77.59)
    r37 = [r for r in shatpanchasika(pq_, lq_, "travel") if r[0] == 37]
    check("Chappanna stanza 37 example: Sc lagna, Chandra 6th, 72 days",
          sign_of(lq_) == 7 and house_from(sign_of(lq_), sign_of(pq_["Mo"]["lon"])) == 6 and r37 and "72 days" in r37[0][2])
    # --- Yogini: Aswini -> (1+3)%8=4 Bhramari; Rohini(4) -> 7 Siddha
    check("Yogini start (Aswini->Bhramari, Rohini->Siddha)", yogini_dasa(1.0, b0)[0] == "Bhramari" and yogini_dasa(41.0, b0)[0] == "Siddha")
    # cross-check vs independent implementation (PyJHora, a JHora port): star->yogini map & antardasa order
    jh_map = {"Mangala": [6, 14, 22], "Pingala": [7, 15, 23], "Dhanya": [8, 16, 24], "Bhramari": [1, 9, 17, 25],
              "Bhadrika": [2, 10, 18, 26], "Ulka": [3, 11, 19, 27], "Siddha": [4, 12, 20], "Sankata": [5, 13, 21]}
    ok_y = all(yogini_dasa((n_ - 1) * 360 / 27 + 1, b0)[0] == y_ for y_, stars in jh_map.items() for n_ in stars)
    yd_ = yogini_dasa(41.0, b0)[2][0]
    ok_y = ok_y and [a["yogini"] for a in yd_["antar"]][:3] == ["Siddha", "Sankata", "Mangala"] and abs(sum(a["end"].timestamp() - a["start"].timestamp() for a in yd_["antar"]) - (yd_["end"] - yd_["start"]).total_seconds()) < 1
    check("Yogini star map & antardasa order agree with PyJHora (JHora port)", ok_y)
    print("\nALL PASS" if ok else "\nSOME TESTS FAILED")
    return ok


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Jyotisha chart calculator (Lahiri, whole-sign, mean nodes)")
    ap.add_argument("--name", default="Native")
    ap.add_argument("--date", help="YYYY-MM-DD (local)")
    ap.add_argument("--time", help="HH:MM[:SS] (local)")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lon", type=float)
    ap.add_argument("--tz", default="Asia/Colombo", help="IANA timezone, e.g. Asia/Colombo")
    ap.add_argument("--place", default="")
    ap.add_argument("--vargas", default=",".join(DEFAULT_VARGAS), help="comma list, e.g. D9,D10 or 'all'")
    ap.add_argument("--karakas", type=int, choices=[7, 8], default=8)
    ap.add_argument("--dasha-depth", type=int, default=2, help="1=maha, 2=antar, 3=pratyantar")
    ap.add_argument("--dasha-from", type=int, help="print sub-periods only from this year")
    ap.add_argument("--dasha-to", type=int, help="print sub-periods only up to this year")
    ap.add_argument("--json", help="write full result to this JSON file")
    ap.add_argument("--svg", help="write South Indian D1 chart SVG here")
    ap.add_argument("--transit", help="YYYY-MM-DD: print sidereal transit positions for that date (12:00 local)")
    ap.add_argument("--narayana", action="store_true", help="print Narayana dasa (D1) with antardasas")
    ap.add_argument("--narayana-from", type=int, help="print Narayana antardasas only from this year")
    ap.add_argument("--narayana-to", type=int, help="print Narayana antardasas only up to this year")
    ap.add_argument("--ashtakavarga", action="store_true", help="print Bhinna & Sarva Ashtakavarga")
    ap.add_argument("--varsha", type=int, help="YEAR: Tajaka annual chart for the solar year starting on the birthday in YEAR")
    ap.add_argument("--narayana-varga", default="", help="comma list e.g. D9,D10: Narayana dasa of those vargas")
    ap.add_argument("--match-name", default="Partner")
    ap.add_argument("--match-date", help="partner's YYYY-MM-DD (enables Ashtakoota + synastry)")
    ap.add_argument("--match-time")
    ap.add_argument("--match-lat", type=float)
    ap.add_argument("--match-lon", type=float)
    ap.add_argument("--match-tz", default=None)
    ap.add_argument("--role", choices=["boy", "girl"], default="boy", help="role of the PRIMARY native in matching")
    ap.add_argument("--year-length", choices=["solar", "savana"], default="solar",
                    help="Vimshottari year: solar=365.25d (Sanjay Rath & most scholars), savana=360d (P.V.R. Rao's preference)")
    ap.add_argument("--time-scan", type=int, default=0, help="MINUTES: show how Lagna/varga lagnas/Moon change over ±MINUTES")
    ap.add_argument("--kalachakra", action="store_true", help="Kalachakra dasa (textbook ch.24) with antardasas")
    ap.add_argument("--ashtottari", action="store_true", help="Ashtottari dasa (textbook ch.17) + applicability views")
    ap.add_argument("--yogini", action="store_true", help="Yogini dasa (standard scheme; NOT in project textbook)")
    ap.add_argument("--sudasa", action="store_true", help="Sudasa / Sree Lagna rasi dasa (textbook ch.20)")
    ap.add_argument("--sudarsana", action="store_true", help="Sudarsana Chakra dasa sign per year of life (textbook ch.31)")
    ap.add_argument("--nama", action="store_true", help="naming syllables (nama nakshatra) from Chandra's pada")
    ap.add_argument("--chart-type", choices=["natal", "prashna", "mundane"], default="natal",
                    help="prashna = chart of the question moment; mundane = nation/organisation/business chart")
    ap.add_argument("--compress-days", type=float, help="compress Vimshottari (120y) into N days (textbook 35.4; muhurta/prashna/mundane)")
    ap.add_argument("--janma-nakshatra", help="natal Chandra nakshatra name (for tara in prashna/muhurta when no natal data)")
    ap.add_argument("--muhurta", choices=sorted(MUHURTA_TASKS.keys()), help="scan for auspicious windows for this task")
    ap.add_argument("--muhurta-from", help="YYYY-MM-DD start of scan")
    ap.add_argument("--muhurta-to", help="YYYY-MM-DD end of scan (inclusive)")
    ap.add_argument("--muhurta-hours", default="6-21", help="local hour range to scan, e.g. 6-21 or 0-24")
    ap.add_argument("--muhurta-top", type=int, default=15, help="how many windows to list")
    ap.add_argument("--yogas", action="store_true", help="full yoga detector (textbook ch.11: Ravi, Chandra, Mahapurusha, Nabhasa, popular, Raja, Dhana, Daridra)")
    ap.add_argument("--argala", action="store_true", help="argala / virodhargala on all 12 houses (textbook 10.5-10.7)")
    ap.add_argument("--upagrahas", action="store_true", help="Dhuma..Upaketu and Kaala..Maandi (textbook ch.4)")
    ap.add_argument("--kendradi", action="store_true", help="Lagna Kendradi Rasi dasa (textbook ch.19)")
    ap.add_argument("--drigdasa", action="store_true", help="Drigdasa (textbook ch.21)")
    ap.add_argument("--vimshottari-from", choices=["moon", "lagna", "kshema", "utpanna", "adhana"], default="moon",
                    help="Vimshottari variation (textbook 16.4): start from Lagna star or 4th/5th/8th star from Chandra")
    ap.add_argument("--masa", type=int, help="MONTH 1-12 of the --varsha year: Tajaka monthly chart (27.3, 28.7)")
    ap.add_argument("--shashti", help="YYYY-MM-DD: Tajaka sixty-hour chart containing that date (27.4)")
    ap.add_argument("--ashtakavarga-varga", default="", help="comma list e.g. D9,D10,D24: BAV/SAV of divisional charts")
    ap.add_argument("--ayanamsa", choices=sorted(AYANAMSAS), default="lahiri", help="ayanamsa (default Lahiri — the project standard; others only for comparing with another astrologer's chart)")
    ap.add_argument("--sunrise", choices=["limb", "centre"], default="limb", help="sunrise definition: upper limb+refraction (default) or disc centre without refraction (traditional litha)")
    ap.add_argument("--ephe", help="directory with Swiss Ephemeris .se1 files (default: ./ephe next to the script)")
    ap.add_argument("--svg-vargas", default="", help="comma list e.g. D9,D10: write South Indian SVG for those vargas (files <svg-stem>_D9.svg)")
    ap.add_argument("--matter", type=int, help="HOUSE 1-12 of the matter asked (prashna/varsha/masa): ithasala among lagna lord, house lord, saham lord, karaka (29.2)")
    ap.add_argument("--prashna-shat", choices=SHAT_TOPICS, help="Shatpanchasika (Chappanna) prashna rules for a topic (use with --chart-type prashna)")
    ap.add_argument("--selftest", action="store_true", help="run textbook-example regression tests")
    args = ap.parse_args()
    if args.ephe:
        setup_ephemeris(args.ephe)
    set_ayanamsa(args.ayanamsa)
    set_sunrise_mode(args.sunrise)
    if args.ayanamsa != "lahiri":
        print(f"NOTE: ayanamsa {AYANAMSA_NAME} selected for comparison only — the project standard and all textbook verification use Lahiri.")

    if args.selftest:
        sys.exit(0 if selftest() else 1)
    if args.transit and not args.date:
        print_transit(args.transit, args.tz)
        return
    if args.muhurta:
        run_muhurta(args, ap)
        return
    if not (args.date and args.time and args.lat is not None and args.lon is not None):
        ap.error("--date, --time, --lat, --lon are required (or use --transit alone / --muhurta)")

    parts = [int(x) for x in args.time.split(":")]
    while len(parts) < 3:
        parts.append(0)
    y, m, d = [int(x) for x in args.date.split("-")]
    local_dt = datetime(y, m, d, *parts)
    jd, offset = to_jd_ut(local_dt, args.tz)
    birth_utc = jd_to_datetime(jd)

    pos, ayan = compute_positions(jd)
    lagna = compute_lagna(jd, args.lat, args.lon)
    lagna_sign = sign_of(lagna)

    # --- header ---
    print("=" * 72)
    ctype = {"natal": "JYOTISHA CHART", "prashna": "PRASHNA (HORARY) CHART", "mundane": "MUNDANE / ORGANISATION CHART"}[args.chart_type]
    print(f"{ctype} — {args.name}")
    print(f"{'Birth data' if args.chart_type != 'prashna' else 'Question moment'}: {args.date} {args.time} ({args.tz}, UTC{offset}) | {args.place} "
          f"lat {args.lat}, lon {args.lon}")
    print(f"Julian Day (UT): {jd:.5f} | Ayanamsa ({AYANAMSA_NAME}): {dms(ayan)} | Whole-sign | Mean nodes | sunrise: {'disc centre, no refraction' if RISE_BITS else 'upper limb + refraction'} | {ephemeris_mode()}")
    print("=" * 72)

    # --- Lagna ---
    ldeg = deg_in_sign(lagna)
    warn = ""
    if ldeg < 2 or ldeg > 28:
        warn = "  ** WARNING: Lagna within 2° of sign boundary — verify birth time **"
    print(f"\nLAGNA: {SIGNS[lagna_sign]} ({SIGNS_EN[lagna_sign]}) {dms(ldeg)}  lord {PLANET_NAME[SIGN_LORD[lagna_sign]]}{warn}")
    nk, pd, _ = nakshatra_of(lagna)
    print(f"       nakshatra {NAKSHATRAS[nk]} pada {pd}")
    spl = special_lagnas(jd, args.lat, args.lon, lagna, pos["Mo"]["lon"])
    spl_txt = "  ".join(f"{k} {SIGNS[sign_of(spl[k])][:5]} {dms(deg_in_sign(spl[k]))}" for k in ("HL", "GL", "SL") if k in spl)
    print(f"SPECIAL LAGNAS (ch.5): {spl_txt}")
    hora_txt = ""
    if spl.get("sunrise_jd"):
        _pv = panchanga(pos, jd, args.lat, args.lon, args.tz)
        _vi = VARA.index(_pv["vara"].split("vara")[0])
        hl_, hn_ = hora_lord(jd, spl["sunrise_jd"], VARA_LORD[_vi])
        hora_txt = f"Hora lord {PLANET_NAME[hl_]} (hora {hn_} from sunrise)"
    janma_nak_idx = None
    if args.janma_nakshatra:
        try:
            janma_nak_idx = int(args.janma_nakshatra) - 1
        except ValueError:
            m_ = [i for i, n_ in enumerate(NAKSHATRAS) if n_.lower().startswith(args.janma_nakshatra.lower()[:5])]
            janma_nak_idx = m_[0] if m_ else None
    if janma_nak_idx is not None:
        tnk = nakshatra_of(pos["Mo"]["lon"])[0]
        hora_txt += f" | Tara of Chandra ({NAKSHATRAS[tnk]}) from janma {NAKSHATRAS[janma_nak_idx]}: {TARA_NAMES[tara_of(janma_nak_idx, tnk)]}"
    if hora_txt:
        print(hora_txt)

    if args.time_scan:
        step = 1 if args.time_scan <= 15 else (2 if args.time_scan <= 30 else 5)
        rows = time_scan(local_dt, args.tz, args.lat, args.lon, args.time_scan, step)
        print(f"\nBIRTH-TIME SENSITIVITY (±{args.time_scan} min, step {step})")
        print(f"  {'off':>5} {'time':5}  {'Lagna':16} {'D9La':6}{'D10La':6}{'D60La':6}{'D7La':6}{'D24La':6} Chandra nak/pada   dasha bal")
        prev = None
        for r in rows:
            lag_s = sign_of(r["lagna"])
            ch = []
            if prev:
                if sign_of(prev["lagna"]) != lag_s: ch.append("LAGNA")
                if prev["d9"] != r["d9"]: ch.append("D9")
                if prev["d10"] != r["d10"]: ch.append("D10")
                if prev["d60"] != r["d60"]: ch.append("D60")
                if prev["d7"] != r["d7"]: ch.append("D7")
                if prev["d24"] != r["d24"]: ch.append("D24")
                if prev["mo_pada"] != r["mo_pada"] or prev["mo_nak"] != r["mo_nak"]: ch.append("MoPada")
            mark = " <-- birth" if r["off"] == 0 else ""
            lord_ = NAK_LORDS[r["mo_nak"] % 9]
            bal_ = DASHA_YEARS[lord_] * (1 - r["mo_frac"])
            print(f"  {r['off']:>+5} {r['time']:5}  {SIGNS[lag_s][:9]:9} {deg_in_sign(r['lagna']):5.2f}° "
                  f"{SIGNS[r['d9']][:5]:6}{SIGNS[r['d10']][:5]:6}{SIGNS[r['d60']][:5]:6}{SIGNS[r['d7']][:5]:6}{SIGNS[r['d24']][:5]:6} "
                  f"{NAKSHATRAS[r['mo_nak']][:10]:10} p{r['mo_pada']}  {bal_:5.2f}y"
                  + (f"  [changes: {', '.join(ch)}]" if ch else "") + mark)
            prev = r
        print("  Stable across the range = safe to interpret; items that change = weight lightly unless time is exact.")

    pch = panchanga(pos, jd, args.lat, args.lon, args.tz)
    print(f"PANCHANGA: {pch['vara']} | Tithi {pch['tithi']} | Nakshatra {NAKSHATRAS[nakshatra_of(pos['Mo']['lon'])[0]]} | "
          f"Yoga {pch['yoga']} | Karana {pch['karana']} | sunrise {pch['sunrise']}")
    sp_naks = special_nakshatras(nakshatra_of(pos["Mo"]["lon"])[0])
    print("SPECIAL NAKSHATRAS (26.4.2): " + ", ".join(f"{nm} = {NAKSHATRAS[k]}" for k, (nm, _) in sorted(sp_naks.items(), key=lambda kv: SPECIAL_NAKS[[x[1] for x in SPECIAL_NAKS].index(kv[1][0])][0])))

    # --- D1 table ---
    print("\nD1 (RASI) POSITIONS")
    print(f"{'Graha':8}{'Rasi':12}{'Deg':13}{'House':6}{'Nakshatra':18}{'Pd':3}{'R':3}{'C':3}Dignity")
    result_planets = {}
    for code in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        p = pos[code]
        s = sign_of(p["lon"])
        nk, pd, _ = nakshatra_of(p["lon"])
        h = house_from(lagna_sign, s)
        dig = dignity(code, s)
        nb = neecha_bhanga(code, pos, lagna_sign)
        if nb:
            dig += " | NB: " + "; ".join(nb)
        cb = combust(code, pos)
        r = "R" if p["retro"] and code not in ("Ra", "Ke") else ""
        dsg = deg_in_sign(p["lon"])
        flag = " *boundary*" if (dsg < 2 or dsg > 28) else ""
        print(f"{PLANET_NAME[code]:8}{SIGNS[s]:12}{dms(dsg):13}{h:<6}{NAKSHATRAS[nk]:18}{pd:<3}{r:3}{'C' if cb else '':3}{dig}{flag}")
        result_planets[code] = {"lon": round(p["lon"], 5), "sign": SIGNS[s], "sign_idx": s,
                                "deg_in_sign": round(dsg, 4), "house": h,
                                "nakshatra": NAKSHATRAS[nk], "pada": pd,
                                "retro": bool(p["retro"]), "combust": bool(cb),
                                "dignity": dig, "boundary_flag": bool(flag)}

    # --- Vargottama ---
    vt = [PLANET_NAME[c] for c in result_planets if varga_sign(pos[c]["lon"], 9) == sign_of(pos[c]["lon"])]
    if varga_sign(lagna, 9) == lagna_sign:
        vt.insert(0, "Lagna")
    print(f"\nVargottama (same rasi in D1 & D9): {', '.join(vt) if vt else 'none'}")

    # --- Yogas ---
    print("\nKEY YOGA/DOSHA INDICATIONS (verify cancellations manually)")
    yg = basic_yogas(pos, lagna_sign)
    for n in yg:
        print("  - " + n)
    if not yg:
        print("  (none of the screened yogas)")

    # --- Karakas ---
    kk = chara_karakas(pos, args.karakas)
    print(f"\nCHARA KARAKAS ({args.karakas}-karaka scheme)")
    print("  " + "  ".join(f"{k}={PLANET_NAME[v['planet']]}({v['deg_in_sign']:.2f})" for k, v in kk.items()))

    # --- Arudhas ---
    print("\nARUDHA PADAS")
    arudhas = {}
    for hnum in range(1, 13):
        hs = (lagna_sign + hnum - 1) % 12
        pada, lord = arudha_pada(hs, pos)
        label = {1: "AL", 12: "UL"}.get(hnum, f"A{hnum}")
        arudhas[label] = SIGNS[pada]
        extra = " (stronger co-lord used)" if hs in (7, 10) else ""
        print(f"  {label:3} house {hnum:2} ({SIGNS[hs]}) lord {PLANET_NAME[lord]:8} -> {SIGNS[pada]} (house {house_from(lagna_sign, pada)}){extra}")

    # --- Vargas ---
    want = list(VARGA_DIVISIONS) if args.vargas.strip().lower() == "all" else \
        [v.strip().upper() for v in args.vargas.split(",") if v.strip()]
    vargas_out = {}
    print("\nDIVISIONAL CHARTS (whole-sign; sign of each graha)")
    for v in want:
        div = VARGA_DIVISIONS[v]
        vl = varga_sign(lagna, div)
        row = {"La": vl}
        for code in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
            row[code] = varga_sign(pos[code]["lon"], div)
        vargas_out[v] = {k: SIGNS[s] for k, s in row.items()}
        vargas_out[v]["_houses_from_varga_lagna"] = {k: house_from(vl, s) for k, s in row.items() if k != "La"}
        # varga lagna boundary check (approximate: how close natal lagna is to a division edge)
        edge = (deg_in_sign(lagna) % (30.0 / div)) / (30.0 / div)
        edge_warn = " *lagna near division edge*" if (edge < 0.08 or edge > 0.92) else ""
        spl_v = " ".join(f"{k}:{SIGNS[varga_sign(spl[k], div)][:5]}({house_from(vl, varga_sign(spl[k], div))})" for k in ("HL", "GL", "SL") if k in spl)
        vargas_out[v]["special_lagnas"] = {k: SIGNS[varga_sign(spl[k], div)] for k in ("HL", "GL", "SL") if k in spl}
        print(f"  {v:4} La:{SIGNS[vl][:5]}  " +
              " ".join(f"{k}:{SIGNS[s][:5]}({house_from(vl, s)})" for k, s in row.items() if k != "La") + "  | " + spl_v + edge_warn)

    # --- Vimshottari ---
    year_days = 360.0 if args.year_length == "savana" else YEAR_DAYS
    if args.vimshottari_from != "moon":
        lord0, bal, mds = vimshottari_variant(pos["Mo"]["lon"], lagna, birth_utc, args.vimshottari_from, args.dasha_depth, year_days)
        sm_, s5_, st_ = utpanna_sign_compare(pos["Mo"]["lon"], pos)
        print(f"\n[Vimshottari variation 16.4: started from {args.vimshottari_from.upper()} star"
              f"{' (Lagna nakshatra)' if args.vimshottari_from == 'lagna' else ''}; fraction left taken from Chandra's star as in Example 51."
              + (" 4th/8th-star variants are used by the textbook mainly for longevity — this script does not perform longevity analysis; use them only for event validation.]" if args.vimshottari_from in ("kshema", "adhana") else
                 f" 16.5.2: Chandra's rasi {SIGNS[sm_]} vs utpanna rasi {SIGNS[s5_]} — stronger: {SIGNS[st_]}]"))
    else:
        lord0, bal, mds = vimshottari(pos["Mo"]["lon"], birth_utc, args.dasha_depth, year_days)
    nk, pd, _ = nakshatra_of(pos["Mo"]["lon"])
    print(f"\nVIMSHOTTARI DASHA{' (natal-style; for a prashna/muhurta chart prefer --compress-days)' if args.chart_type != 'natal' else ''} — Chandra in {NAKSHATRAS[nk]} (lord {PLANET_NAME[lord0]}), "
          f"balance at birth {bal:.3f} years  [{args.year_length} years = {year_days:g} days"
          + ("; savana dates fall ~5.25 d/yr earlier than solar" if args.year_length == "savana" else
             "; use --year-length savana for P.V.R. Rao's 360-day variant") + "]")
    now = datetime.now(timezone.utc)

    def fmt(dt):
        return dt.strftime("%Y-%m-%d")

    yfrom = args.dasha_from or 0
    yto = args.dasha_to or 9999
    for md in mds:
        cur = " <== current" if md["start"] <= now < md["end"] else ""
        print(f"  {PLANET_NAME[md['lord']]:8} {fmt(md['start'])} -> {fmt(md['end'])}{cur}")
        for ad in md["sub"]:
            if ad["end"].year < yfrom or ad["start"].year > yto:
                continue
            cur2 = " <== current" if ad["start"] <= now < ad["end"] else ""
            print(f"      {PLANET_NAME[md['lord']][:5]}/{PLANET_NAME[ad['lord']]:8} {fmt(ad['start'])} -> {fmt(ad['end'])}{cur2}")
            for pd_ in ad["sub"]:
                if pd_["end"].year < yfrom or pd_["start"].year > yto:
                    continue
                cur3 = " <==" if pd_["start"] <= now < pd_["end"] else ""
                print(f"          /{PLANET_NAME[pd_['lord']]:8} {fmt(pd_['start'])} -> {fmt(pd_['end'])}{cur3}")

    extra_out = {}
    if args.chart_type in ("prashna", "mundane"):
        ty0 = tajaka_yogas(pos, lagna_sign)
        print(f"\nTAJAKA YOGAS in this {args.chart_type} chart (textbook 29; applies to prasna charts too):")
        for g in ty0["general"] + [f"Ithasala: {x}" for x in ty0["ithasala"]] + [f"Eesarpha: {x}" for x in ty0["eesarpha"]] + ty0["nakta_yamaya"]:
            print(f"    {g}")
        if not any(ty0.values()):
            print("    (none within orbs)")
        if args.chart_type == "prashna":
            pd_ = is_daytime(jd, args.lat, args.lon)
            hb_ = harsha_bala(pos, lagna_sign, pd_)
            pv_ = pancha_vargeeya(pos)
            print(f"\nTAJAKA STRENGTHS in prashna chart ({'day' if pd_ else 'night'}; 28.3 Harsha bala / 28.4 Pancha Vargeeya bala):")
            print("  " + "  ".join(f"{PLANET_NAME[p][:5]} H{hb_[p]:>2} P{pv_[p][0]:>5}" for p in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"]))
            print("  Tajaka aspects on lagna (28.2):  " + "; ".join(f"{PLANET_NAME[p][:5]} {TAJAKA_ASPECT[(lagna_sign - sign_of(pos[p]['lon'])) % 12 + 1][0]}"
                  for p in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa"] if TAJAKA_ASPECT[(lagna_sign - sign_of(pos[p]['lon'])) % 12 + 1][1] != "none"))
            extra_out["prashna_strengths"] = {"harsha": hb_, "pvb": {p: pv_[p][0] for p in pv_}}
        if args.prashna_shat:
            extra_out["shatpanchasika"] = print_shatpanchasika(pos, lagna, args.prashna_shat, is_daytime(jd, args.lat, args.lon))
        if args.matter:
            print(f"\nMATTER ANALYSIS — house {args.matter} (Tajaka 29.2 significator ithasala; prashna chart):")
            for ln in matter_analysis(pos, lagna, args.matter, is_daytime(jd, args.lat, args.lon)):
                print(ln)
        if args.chart_type == "mundane":
            print("\nMUNDANE HOUSE SIGNIFICATIONS (textbook 35.2) — planets in each house:")
            for h in range(1, 13):
                hs = (lagna_sign + h - 1) % 12
                occ = ", ".join(PLANET_NAME[p] for p in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"] if sign_of(pos[p]["lon"]) == hs)
                print(f"  {h:>2} {SIGNS[hs]:10} {occ or '-':22} {MUNDANE_HOUSES[h]}")
        extra_out["tajaka_yogas"] = ty0
    if args.compress_days:
        cd = compressed_vimshottari(pos["Mo"]["lon"], birth_utc, args.compress_days)
        print(f"\nCOMPRESSED VIMSHOTTARI — 120 years -> {args.compress_days:g} days (textbook 35.4; first dasa runs in full)")
        for d_ in cd:
            cur = " <== current" if d_["start"] <= now < d_["end"] else ""
            print(f"  {PLANET_NAME[d_['lord']]:8} {d_['start'].astimezone(ZoneInfo(args.tz)).strftime('%Y-%m-%d %H:%M')} -> "
                  f"{d_['end'].astimezone(ZoneInfo(args.tz)).strftime('%Y-%m-%d %H:%M')}  ({d_['days']:.2f} d){cur}")
            for a_ in d_["sub"]:
                if a_["start"] <= now < a_["end"]:
                    print(f"      /{PLANET_NAME[a_['lord']]:8} {a_['start'].astimezone(ZoneInfo(args.tz)).strftime('%Y-%m-%d %H:%M')} -> "
                          f"{a_['end'].astimezone(ZoneInfo(args.tz)).strftime('%Y-%m-%d %H:%M')} <==")
        extra_out["compressed_vimshottari"] = [{"lord": d_["lord"], "start": d_["start"].isoformat(), "end": d_["end"].isoformat()} for d_ in cd]

    if args.kalachakra:
        kc = kalachakra_dasa(pos["Mo"]["lon"], birth_utc, year_days, n_dasas=12)
        print(f"\nKALACHAKRA DASA (textbook ch.24) — Chandra in {NAKSHATRAS[kc['nakshatra']]} pada {kc['pada']} "
              f"({kc['type']} = {'Savya' if kc['savya'] else 'Apasavya'}-{1 if kc['type'] in 'AR' else 2}), {kc['frac_pada']*100:.1f}% of pada elapsed")
        print(f"  Pada rasis: {' '.join(SIGNS[r][:3] for r in kc['pada_rasis'])}  paramayush {kc['paramayush']}y | "
              f"Deha rasi {SIGNS[kc['deha']]}, Jeeva rasi {SIGNS[kc['jeeva']]} | balance at birth {kc['balance_years']:.3f}y "
              f"[{args.year_length} years; author prefers savana for nakshatra dasas]")
        for d_ in kc["dasas"]:
            cur = " <== current" if d_["start"] <= now < d_["end"] else ""
            g_ = f"  ** {d_['gati']}" if d_["gati"] else ""
            print(f"  {SIGNS[d_['sign']]:10} {d_['years']:2}y  {fmt(d_['start'])} -> {fmt(d_['end'])}{g_}{cur}")
            for a_ in d_["antar"]:
                if a_["end"].year < yfrom or a_["start"].year > yto:
                    continue
                cur2 = " <==" if a_["start"] <= now < a_["end"] else ""
                print(f"      /{SIGNS[a_['sign']]:10} {fmt(a_['start'])} -> {fmt(a_['end'])}{cur2}")
        extra_out["kalachakra"] = {"nakshatra": NAKSHATRAS[kc["nakshatra"]], "pada": kc["pada"], "savya": kc["savya"],
                                   "deha": SIGNS[kc["deha"]], "jeeva": SIGNS[kc["jeeva"]], "paramayush": kc["paramayush"],
                                   "dasas": [{"sign": SIGNS[d_["sign"]], "years": d_["years"], "start": d_["start"].isoformat(),
                                              "end": d_["end"].isoformat(), "gati": d_["gati"],
                                              "antar": [{"sign": SIGNS[a_["sign"]], "start": a_["start"].isoformat(), "end": a_["end"].isoformat()} for a_ in d_["antar"]]}
                                             for d_ in kc["dasas"]]}

    if args.ashtottari:
        al, abal, ads = ashtottari_dasa(pos["Mo"]["lon"], birth_utc, year_days)
        print(f"\nASHTOTTARI DASA (textbook ch.17, 108y) — first lord {PLANET_NAME[al]}, balance {abal:.3f}y [{args.year_length} years]")
        for n_ in ashtottari_applicability(pos, lagna_sign, is_daytime(jd, args.lat, args.lon)):
            print(f"  applicability: {n_}")
        for d_ in ads:
            cur = " <== current" if d_["start"] <= now < d_["end"] else ""
            print(f"  {PLANET_NAME[d_['lord']]:8} {d_['years']:2}y  {fmt(d_['start'])} -> {fmt(d_['end'])}{cur}")
            for a_ in d_["antar"]:
                if a_["end"].year < yfrom or a_["start"].year > yto:
                    continue
                cur2 = " <==" if a_["start"] <= now < a_["end"] else ""
                print(f"      /{PLANET_NAME[a_['lord']]:8} {fmt(a_['start'])} -> {fmt(a_['end'])}{cur2}")
        extra_out["ashtottari"] = [{"lord": d_["lord"], "start": d_["start"].isoformat(), "end": d_["end"].isoformat(),
                                    "antar": [{"lord": a_["lord"], "start": a_["start"].isoformat(), "end": a_["end"].isoformat()} for a_ in d_["antar"]]} for d_ in ads]

    if args.yogini:
        yn, ybal, yds = yogini_dasa(pos["Mo"]["lon"], birth_utc, year_days)
        print(f"\nYOGINI DASA (36y cycle; standard scheme — NOT covered by the project textbook, use as secondary only) — "
              f"first {yn}, balance {ybal:.3f}y")
        for d_ in yds:
            cur = " <== current" if d_["start"] <= now < d_["end"] else ""
            print(f"  {d_['yogini']:9}({PLANET_NAME[d_['lord']][:5]}) {d_['years']}y  {fmt(d_['start'])} -> {fmt(d_['end'])}{cur}")
            for a_ in d_["antar"]:
                if a_["end"].year < yfrom or a_["start"].year > yto:
                    continue
                cur2 = " <==" if a_["start"] <= now < a_["end"] else ""
                print(f"      /{a_['yogini']:9}({PLANET_NAME[a_['lord']][:5]}) {fmt(a_['start'])} -> {fmt(a_['end'])}{cur2}")
        extra_out["yogini"] = [{"yogini": d_["yogini"], "lord": d_["lord"], "start": d_["start"].isoformat(), "end": d_["end"].isoformat()} for d_ in yds]

    if args.sudasa:
        sls, sfrac, sorder, sds = sudasa(spl["SL"], pos, birth_utc, cycles=2)
        print(f"\nSUDASA (textbook ch.20) — Sree Lagna {SIGNS[sls]} {dms(deg_in_sign(spl['SL']))}, "
              f"{'forward' if is_odd_sign(sls) else 'backward'} reckoning, first dasa fraction {sfrac:.4f}")
        print(f"  Order: {' '.join(SIGNS[x][:3] for x in sorder)}  (kendras, panapharas, apoklimas from SL)")
        for d_ in sds:
            cur = " <== current" if d_["start"] <= now < d_["end"] else ""
            print(f"  {SIGNS[d_['sign']]:10} {d_['years']:6.3f}y  {fmt(d_['start'])} -> {fmt(d_['end'])}  (cycle {d_['cycle']}){cur}")
        print("  Interpretation 20.3: dasas of HL / 7th from HL / signs aspecting HL -> finance; same with GL -> power; upachayas from AL -> status")
        extra_out["sudasa"] = {"sree_lagna": SIGNS[sls], "dasas": [{"sign": SIGNS[d_["sign"]], "years": d_["years"], "start": d_["start"].isoformat(),
                                                                    "end": d_["end"].isoformat(), "cycle": d_["cycle"]} for d_ in sds]}

    if args.sudarsana:
        print("\nSUDARSANA CHAKRA DASA (textbook ch.31) — dasa of house N in year N of life (from Lagna / Chandra / Surya)")
        age_now = (now - birth_utc).days / YEAR_DAYS
        y_start = max(1, int(age_now) - 1)
        sc_rows = []
        for yol in range(y_start, y_start + 12):
            sc = sudarsana_dasa(yol, lagna_sign, pos)
            mark = " <== current year of life" if yol == int(age_now) + 1 else ""
            print(f"  year {yol:3} (age {yol-1:2}-{yol:2}): house {sc['house']:2} -> from La {SIGNS[sc['from_lagna']]:10} "
                  f"Mo {SIGNS[sc['from_moon']]:10} Su {SIGNS[sc['from_sun']]:10} | strongest ref {sc['strongest_ref']}: {SIGNS[sc['dasa_sign']]}{mark}")
            sc_rows.append({"year_of_life": yol, "house": sc["house"], "dasa_sign": SIGNS[sc["dasa_sign"]], "ref": sc["strongest_ref"]})
        print("  Judge planets in the Varsha Kundali (--varsha) from the dasa sign; antardasas = 12 houses from dasa sign, one per month.")
        extra_out["sudarsana"] = sc_rows

    if args.nama:
        nm_ = nama_nakshatra(pos["Mo"]["lon"])
        print(f"\nNAMA NAKSHATRA (Avakahada chakra; classical, not from textbook) — Chandra {nm_['nakshatra']} pada {nm_['pada']}")
        print(f"  Name should begin with: {nm_['syllable']}  ({nm_['sinhala']})")
        print(f"  All 4 padas of {nm_['nakshatra']}: " + ", ".join(f"{a} ({b})" for a, b in nm_["all_padas"]))
        extra_out["nama"] = nm_

    if args.yogas:
        extra_out["yogas_full"] = [{"category": c, "name": n, "detail": d} for c, n, d in print_full_yogas(pos, lagna_sign)]
    if args.argala:
        print("\nARGALA / VIRODHARGALA on houses (textbook 10.5-10.7; primary 2/4/11, secondary 5; blocked from 12/10/3/9; Ketu-sign counted reverse)")
        for ln in argala_report(pos, lagna_sign):
            print(ln)
        ak_ = kk["AK"]["planet"] if isinstance(kk, dict) and "AK" in kk else None
        for tgt, lbl in (("Sa", "Shani (karma/livelihood, Example 35)"), (ak_, "AK (atmakaraka)")):
            if tgt and tgt in pos:
                a_ = argala_on(sign_of(pos[tgt]["lon"]), pos)
                print(f"  On {lbl}: subha {', '.join(f'{PLANET_NAME[p][:5]}({h})' for p, h in a_['subha']) or '-'}; "
                      f"papa {', '.join(f'{PLANET_NAME[p][:5]}({h})' for p, h in a_['papa']) or '-'}; "
                      f"virodha {', '.join(f'{PLANET_NAME[p][:5]}({h})' for p, h, _b in a_['virodha']) or '-'}")
        extra_out["argala"] = {h: {k: [list(x) for x in v] for k, v in argala_on((lagna_sign + h - 1) % 12, pos).items()} for h in range(1, 13)}
    if args.upagrahas:
        su_ = sun_upagrahas(pos["Su"]["lon"])
        tu_ = time_upagrahas(jd, args.lat, args.lon, args.tz)
        print("\nUPAGRAHAS (textbook ch.4)")
        print("  Sun-based (Table 9, malefic — spoil the house occupied):")
        for k_, v_ in su_.items():
            print(f"    {k_:13} {SIGNS[sign_of(v_)]:11} {dms(deg_in_sign(v_))}  house {house_from(lagna_sign, sign_of(v_))}")
        if tu_:
            print(f"  Time-based (Table 10; {'day' if tu_['_day'] else 'night'} birth, weekday lord {PLANET_NAME[tu_['_weekday_lord']]}, "
                  f"parts: {' '.join((PLANET_NAME[r][:2] if r else '--') for r in tu_['_rulers'])}):")
            for k_ in UPAGRAHA_TIME:
                v_ = tu_[k_]
                print(f"    {k_:13} {SIGNS[sign_of(v_)]:11} {dms(deg_in_sign(v_))}  house {house_from(lagna_sign, sign_of(v_))}"
                      + ("  (Gulika/Maandi ~ Shani; Ex.142: Gulika within 1° of Lagna undesirable)" if k_ == "Gulika" else ""))
        extra_out["upagrahas"] = {**{k_: round(v_, 4) for k_, v_ in su_.items()}, **{k_: round(tu_[k_], 4) for k_ in UPAGRAHA_TIME if k_ in tu_}}
    if args.kendradi:
        seed_, step_, ord_, kds = kendradi_rasi_dasa(lagna_sign, pos, birth_utc, 2, YEAR_DAYS)
        print(f"\nLAGNA KENDRADI RASI DASA (textbook ch.19) — seed {SIGNS[seed_]} (stronger of Lagna/7th), {'forward' if step_ == 1 else 'backward'}; material prosperity (Lakshmi movement)")
        print(f"  Order: {' '.join(SIGNS[x][:3] for x in ord_)}")
        for d_ in kds:
            cur = " <== current" if d_["start"] <= now < d_["end"] else ""
            print(f"  {SIGNS[d_['sign']]:10} {d_['years']:2}y  {fmt(d_['start'])} -> {fmt(d_['end'])}  (cycle {d_['cycle']}){cur}")
        extra_out["kendradi"] = [{"sign": SIGNS[d_["sign"]], "years": d_["years"], "start": d_["start"].isoformat(), "end": d_["end"].isoformat(), "cycle": d_["cycle"]} for d_ in kds]
    if args.drigdasa:
        ord_, dds = drigdasa(lagna_sign, pos, birth_utc, 2, YEAR_DAYS)
        print(f"\nDRIGDASA (textbook ch.21) — from 9th house; spiritual vision. Order: {' '.join(SIGNS[x][:3] for x in ord_)}")
        for d_ in dds:
            cur = " <== current" if d_["start"] <= now < d_["end"] else ""
            tags = []
            if SIGNS[d_["sign"]] == arudhas.get("AL"):
                tags.append("AL")
            if SIGNS[d_["sign"]] == arudhas.get("A5"):
                tags.append("A5 mantra")
            if SIGNS[d_["sign"]] == arudhas.get("A8"):
                tags.append("A8")
            if d_["sign"] == lagna_sign or d_["sign"] == (lagna_sign + 6) % 12:
                tags.append("Lagna/7th")
            if sign_of(pos["Ke"]["lon"]) == d_["sign"]:
                tags.append("Ketu (moksha)")
            if sign_of(pos["Ra"]["lon"]) == d_["sign"]:
                tags.append("Rahu")
            print(f"  {SIGNS[d_['sign']]:10} {d_['years']:2}y  {fmt(d_['start'])} -> {fmt(d_['end'])}  (cycle {d_['cycle']}){cur}" + (f"  [{', '.join(tags)}]" if tags else ""))
        print("  21.3: AL dasa -> renunciation if parivraja yogas; Lagna/7th -> inner awakening; A5 -> mantra; A8 -> yogic sadhana; Ketu -> liberation")
        extra_out["drigdasa"] = [{"sign": SIGNS[d_["sign"]], "years": d_["years"], "start": d_["start"].isoformat(), "end": d_["end"].isoformat(), "cycle": d_["cycle"]} for d_ in dds]
    if args.ashtakavarga_varga:
        extra_out["ashtakavarga_varga"] = {}
        for v_ in [x.strip().upper() for x in args.ashtakavarga_varga.split(",") if x.strip()]:
            div_ = VARGA_DIVISIONS[v_]
            vpos_ = varga_positions(pos, div_)
            vl_ = varga_sign(lagna, div_)
            bav_, sav_ = ashtakavarga(vpos_, vl_)
            print(f"\nASHTAKAVARGA OF {v_} (lagna {SIGNS[vl_]}; rasis with >=30 SAV are strong for that chart — textbook Ex.99)")
            print("  " + " " * 8 + "".join(f"{SIGNS[i][:3]:>4}" for i in range(12)) + "  total")
            for p_, b_ in bav_.items():
                print(f"  {PLANET_NAME[p_]:8}" + "".join(f"{x:>4}" for x in b_) + f"  {sum(b_)}")
            print(f"  {'SAV':8}" + "".join(f"{x:>4}" for x in sav_) + f"  {sum(sav_)}")
            strong_ = [f"{SIGNS[i]}(h{house_from(vl_, i)})={sav_[i]}" for i in range(12) if sav_[i] >= 30]
            print(f"  Strong rasis (>=30): {', '.join(strong_) or 'none'}")
            extra_out["ashtakavarga_varga"][v_] = {"bav": bav_, "sav": sav_}

    # --- Sade Sati quick check for today ---
    swe.set_sid_mode(SID_MODE)
    jd_now = swe.julday(now.year, now.month, now.day, now.hour + now.minute / 60)
    sat_now = norm(swe.calc_ut(jd_now, swe.SATURN, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0])
    moon_sign = sign_of(pos["Mo"]["lon"])
    rel = (sign_of(sat_now) - moon_sign) % 12 + 1
    tag = {12: "Sade Sati phase 1 (12th from Chandra)", 1: "Sade Sati phase 2 (over Chandra)",
           2: "Sade Sati phase 3 (2nd from Chandra)", 4: "Ardhashtama Shani (4th from Chandra)",
           8: "Ashtama Shani (8th from Chandra)"}.get(rel, "")
    print(f"\nGOCHARA TODAY ({fmt(now)}): Shani in {SIGNS[sign_of(sat_now)]} = house {rel} from natal Chandra" +
          (f"  -> {tag}" if tag else ""))

    def fmt_local(jdx):
        return jd_to_datetime(jdx).astimezone(ZoneInfo(args.tz)).strftime("%Y-%m-%d %H:%M")

    # --- Narayana dasa ---
    nar_out = None
    if args.narayana:
        seed, nds = narayana_dasa(lagna_sign, pos, birth_utc, cycles=2)
        sc_lord = primary_lord(7, pos, "dasa")
        aq_lord = primary_lord(10, pos, "dasa")
        print(f"\nNARAYANA DASA (D1) — dasa seed {SIGNS[seed]} (stronger of Lagna/7th); "
              f"co-lords used: Vrischika={PLANET_NAME[sc_lord]}, Kumbha={PLANET_NAME[aq_lord]}")
        yfrom = args.narayana_from or 0
        yto = args.narayana_to or 9999
        nar_out = []
        for nd in nds:
            cur = " <== current" if nd["start"] <= now < nd["end"] else ""
            print(f"  {SIGNS[nd['sign']]:10} {nd['years']:2}y  {fmt(nd['start'])} -> {fmt(nd['end'])}  (cycle {nd['cycle']}){cur}")
            for a in nd["antar"]:
                if a["end"].year < yfrom or a["start"].year > yto:
                    continue
                cur2 = " <==" if a["start"] <= now < a["end"] else ""
                print(f"      /{SIGNS[a['sign']]:10} {fmt(a['start'])} -> {fmt(a['end'])}{cur2}")
            nar_out.append({"sign": SIGNS[nd["sign"]], "years": nd["years"], "start": nd["start"].isoformat(),
                            "end": nd["end"].isoformat(), "cycle": nd["cycle"],
                            "antar": [{"sign": SIGNS[a["sign"]], "start": a["start"].isoformat(),
                                       "end": a["end"].isoformat()} for a in nd["antar"]]})

    # --- Ashtakavarga ---
    av_out = None
    if args.ashtakavarga:
        bav, sav = ashtakavarga(pos, lagna_sign)
        print("\nASHTAKAVARGA (bindus per rasi; * = natal rasi of that graha)")
        print("  " + " " * 8 + "".join(f"{SIGNS[i][:3]:>4}" for i in range(12)) + "  total")
        for p, b in bav.items():
            ns = sign_of(pos[p]["lon"])
            cells = "".join(f"{v:>3}{'*' if i == ns else ' '}" for i, v in enumerate(b))
            print(f"  {PLANET_NAME[p]:8}{cells}  {sum(b)}")
        print(f"  {'SAV':8}" + "".join(f"{v:>4}" for v in sav) + f"  {sum(sav)}")
        print("  Natal bindus: " + ", ".join(f"{PLANET_NAME[p]}={bav[p][sign_of(pos[p]['lon'])]}" for p in bav))
        print("\n  SODHITA ASHTAKAVARGA (after Trikona + Ekadhipatya sodhana) and Sodhya Pindas (textbook 12.7)")
        print("  " + " " * 8 + "".join(f"{SIGNS[i][:3]:>4}" for i in range(12)) + "   rasiP grahaP sodhyaP")
        soav_all, pinda_all = {}, {}
        for p, b in bav.items():
            so = ekadhipatya_sodhana(trikona_sodhana(b), pos)
            rp, gp, sp = sodhya_pinda(so, pos)
            soav_all[p], pinda_all[p] = so, {"rasi": rp, "graha": gp, "sodhya": sp}
            print(f"  {PLANET_NAME[p]:8}" + "".join(f"{v:>4}" for v in so) + f"   {rp:>5} {gp:>6} {sp:>7}")
        av_out = {"bav": {p: b for p, b in bav.items()}, "sav": sav, "soav": soav_all, "pindas": pinda_all}

    # --- Tajaka annual chart ---
    vk_out = None
    if args.varsha:
        vk = varsha_kundali(pos["Su"]["lon"], lagna_sign, y, m, d, args.varsha, args.lat, args.lon,
                            args.tz, pos["Mo"]["lon"])
        vp = vk["pos"]
        print(f"\nVARSHA KUNDALI (Tajaka) — year {vk['completed_years'] + 1} of life, "
              f"{args.varsha}-{args.varsha + 1}")
        print(f"  Varsha pravesha: {fmt_local(vk['jd_vp'])} ({args.tz}) at birthplace — "
              f"{'DAY' if vk['day'] else 'NIGHT'} chart")
        vls = vk["lagna_sign"]
        print(f"  Varsha Lagna: {SIGNS[vls]} {dms(deg_in_sign(vk['lagna']))}   "
              f"Muntha: {SIGNS[vk['muntha']]} (house {house_from(vls, vk['muntha'])} from varsha lagna, "
              f"lord {PLANET_NAME[SIGN_LORD[vk['muntha']]]})")
        print(f"  {'Graha':8}{'Rasi':12}{'Deg':13}{'House':6}{'R':3}{'Harsha':7}{'PVB':6}Natal house")
        for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
            ps = sign_of(vp[c]["lon"])
            r = "R" if vp[c]["retro"] and c not in ("Ra", "Ke") else ""
            hbv = vk["harsha"].get(c, "")
            pv = vk["pvb"][c][0] if c in vk["pvb"] else ""
            print(f"  {PLANET_NAME[c]:8}{SIGNS[ps]:12}{dms(deg_in_sign(vp[c]['lon'])):13}"
                  f"{house_from(vls, ps):<6}{r:3}{str(hbv):7}{str(pv):6}{house_from(lagna_sign, ps)}")
        print("  Varshesha candidates:")
        for cnd in vk["candidates"]:
            print(f"    {PLANET_NAME[cnd['planet']]:8} ({cnd['why']}): {cnd['aspect_on_lagna']} on lagna "
                  f"[{cnd['kind']}], PVB {cnd['pvb']}")
        print(f"  => Varshesha (lord of the year): {PLANET_NAME[vk['varshesha']]}  "
              f"(PVB uses natural friendship; textbook rule 28.6 — verify in borderline cases)")
        sc_ = sudarsana_dasa(vk["completed_years"] + 1, lagna_sign, pos)
        print(f"  Sudarsana Chakra dasa this year (ch.31): house {sc_['house']} -> {SIGNS[sc_['from_lagna']]} from La, "
              f"{SIGNS[sc_['from_moon']]} from Mo, {SIGNS[sc_['from_sun']]} from Su; strongest ref {sc_['strongest_ref']} -> judge varsha planets from {SIGNS[sc_['dasa_sign']]}")
        if args.matter:
            print(f"  MATTER ANALYSIS in varsha chart — house {args.matter} (29.2):")
            for ln in matter_analysis(vp, vk["lagna"], args.matter, vk["day"]):
                print("  " + ln)
        ty = tajaka_yogas(vp, vls)
        print("  Tajaka yogas (deeptamsa orbs; 7 grahas):")
        for g in ty["general"]:
            print(f"    {g}")
        for it in ty["ithasala"]:
            print(f"    Ithasala: {it}")
        for e in ty["eesarpha"]:
            print(f"    Eesarpha: {e}")
        for n in ty["nakta_yamaya"]:
            print(f"    {n}")
        if not (ty["general"] or ty["ithasala"] or ty["eesarpha"] or ty["nakta_yamaya"]):
            print("    (none within orbs)")
        print("  Sahams:")
        for nm, lo in vk["sahams"].items():
            print(f"    {nm:22} {SIGNS[sign_of(lo)]:11} {dms(deg_in_sign(lo))}  (house {house_from(vls, sign_of(lo))})")
        print("  Mudda dasa (Varsha Vimshottari):")
        for md_ in vk["mudda"]:
            print(f"    {PLANET_NAME[md_['lord']]:8} {fmt_local(md_['start'])} -> {fmt_local(md_['end'])}  ({md_['solar_days']} solar days)")
        vk_out = {"varsha_pravesha_local": fmt_local(vk["jd_vp"]), "day_chart": vk["day"], "tajaka_yogas": ty,
                  "lagna": SIGNS[vls], "lagna_deg": round(deg_in_sign(vk["lagna"]), 4),
                  "muntha": SIGNS[vk["muntha"]], "varshesha": vk["varshesha"],
                  "planets": {c: {"sign": SIGNS[sign_of(vp[c]["lon"])], "lon": round(vp[c]["lon"], 4),
                                  "retro": bool(vp[c]["retro"])} for c in vp},
                  "harsha_bala": vk["harsha"], "pancha_vargeeya": {p: v[0] for p, v in vk["pvb"].items()},
                  "candidates": vk["candidates"],
                  "sahams": {k: {"sign": SIGNS[sign_of(v)], "lon": round(v, 4)} for k, v in vk["sahams"].items()},
                  "mudda": [{"lord": x["lord"], "start": fmt_local(x["start"]), "end": fmt_local(x["end"])} for x in vk["mudda"]]}
        if args.masa:
            mk = masa_kundali(vk, pos["Su"]["lon"], lagna_sign, args.masa, args.lat, args.lon, args.tz)
            mp_ = mk["pos"]
            mls_ = mk["lagna_sign"]
            print(f"\n  TAJAKA MONTHLY CHART — month {args.masa} of the year (27.3): maasa pravesha {fmt_local(mk['jd_mp'])} ({args.tz}), "
                  f"{'DAY' if mk['day'] else 'NIGHT'} chart")
            print(f"    Masa Lagna {SIGNS[mls_]} {dms(deg_in_sign(mk['lagna']))} | annual Muntha {SIGNS[vk['muntha']]} | "
                  f"Sudarsana antardasa sign this month (31.3): {SIGNS[mk['sc_antar_sign']]} (judge planets from it)")
            print(f"    {'Graha':8}{'Rasi':12}{'Deg':13}{'House':6}{'R':3}{'Harsha':7}{'PVB':6}")
            for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
                ps_ = sign_of(mp_[c]["lon"])
                print(f"    {PLANET_NAME[c]:8}{SIGNS[ps_]:12}{dms(deg_in_sign(mp_[c]['lon'])):13}{house_from(mls_, ps_):<6}"
                      f"{('R' if mp_[c]['retro'] and c not in ('Ra', 'Ke') else ''):3}{str(mk['harsha'].get(c, '')):7}{str(mk['pvb'][c][0] if c in mk['pvb'] else ''):6}")
            print("    Masesha candidates (28.7, six):")
            for cnd in mk["candidates"]:
                print(f"      {PLANET_NAME[cnd['planet']]:8} ({cnd['why']}): {cnd['aspect_on_lagna']} on lagna [{cnd['kind']}], PVB {cnd['pvb']}")
            print(f"    => Lord of the month: {PLANET_NAME[mk['masesha']]}")
            if args.matter:
                print(f"    MATTER ANALYSIS in monthly chart — house {args.matter} (29.2):")
                for ln in matter_analysis(mp_, mk["lagna"], args.matter, mk["day"]):
                    print("    " + ln)
            ym = mk["yogas"]
            for g in ym["general"] + [f"Ithasala: {x}" for x in ym["ithasala"]] + [f"Eesarpha: {x}" for x in ym["eesarpha"]] + ym["nakta_yamaya"]:
                print(f"      {g}")
            vk_out["masa"] = {"month": args.masa, "pravesha_local": fmt_local(mk["jd_mp"]), "lagna": SIGNS[mls_], "masesha": mk["masesha"],
                              "sc_antar_sign": SIGNS[mk["sc_antar_sign"]],
                              "planets": {c: SIGNS[sign_of(mp_[c]["lon"])] for c in mp_}}

    if args.shashti:
        sy_, smo_, sd_ = [int(x) for x in args.shashti.split("-")]
        jdq_, _ = to_jd_ut(datetime(sy_, smo_, sd_, 12, 0), args.tz)
        sh = shashti_hora_chart(pos["Su"]["lon"], jdq_, args.lat, args.lon)
        print(f"\nTAJAKA SIXTY-HOUR CHART (27.4) containing {args.shashti}: shashti-hora {sh['index_in_month']} of the month, "
              f"{fmt_local(sh['jd_start'])} -> {fmt_local(sh['jd_end'])} ({args.tz}); lagna {SIGNS[sh['lagna_sign']]} {dms(deg_in_sign(sh['lagna']))}")
        for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
            ps_ = sign_of(sh["pos"][c]["lon"])
            print(f"    {PLANET_NAME[c]:8}{SIGNS[ps_]:12}{dms(deg_in_sign(sh['pos'][c]['lon'])):13}house {house_from(sh['lagna_sign'], ps_)}")
        for g in sh["yogas"]["general"] + [f"Ithasala: {x}" for x in sh["yogas"]["ithasala"]] + [f"Eesarpha: {x}" for x in sh["yogas"]["eesarpha"]] + sh["yogas"]["nakta_yamaya"]:
            print(f"      {g}")
        extra_out["shashti_hora"] = {"start": fmt_local(sh["jd_start"]), "end": fmt_local(sh["jd_end"]), "lagna": SIGNS[sh["lagna_sign"]]}

    # --- Narayana dasa of vargas ---
    vnar_out = {}
    if args.narayana_varga:
        for v in [x.strip().upper() for x in args.narayana_varga.split(",") if x.strip()]:
            div = VARGA_DIVISIONS[v]
            sh, ss, lord, vl, seed, nds = varga_narayana(pos, lagna_sign, div, birth_utc)
            print(f"\nNARAYANA DASA OF {v} — seed house {sh} ({SIGNS[ss]}), lord {PLANET_NAME[lord]} "
                  f"in {SIGNS[vl]} in {v} taken as lagna; dasa seed {SIGNS[seed]}")
            vnar_out[v] = []
            for nd in nds:
                if nd["end"].year < (args.narayana_from or 0) - 20 or nd["start"].year > (args.narayana_to or 9999) + 20:
                    pass
                cur = " <== current" if nd["start"] <= now < nd["end"] else ""
                print(f"  {SIGNS[nd['sign']]:10} {nd['years']:2}y  {fmt(nd['start'])} -> {fmt(nd['end'])}  (cycle {nd['cycle']}){cur}")
                yfrom = args.narayana_from or 0
                yto = args.narayana_to or 9999
                for a in nd["antar"]:
                    if a["end"].year < yfrom or a["start"].year > yto:
                        continue
                    cur2 = " <==" if a["start"] <= now < a["end"] else ""
                    print(f"      /{SIGNS[a['sign']]:10} {fmt(a['start'])} -> {fmt(a['end'])}{cur2}")
                vnar_out[v].append({"sign": SIGNS[nd["sign"]], "years": nd["years"], "start": nd["start"].isoformat(),
                                    "end": nd["end"].isoformat(), "cycle": nd["cycle"]})

    # --- Compatibility ---
    match_out = None
    if args.match_date:
        if not (args.match_time and args.match_lat is not None and args.match_lon is not None):
            ap.error("--match-time, --match-lat, --match-lon required with --match-date")
        mtz = args.match_tz or args.tz
        mp = [int(x) for x in args.match_time.split(":")]
        while len(mp) < 3:
            mp.append(0)
        my_, mm_, md_ = [int(x) for x in args.match_date.split("-")]
        jd2, off2 = to_jd_ut(datetime(my_, mm_, md_, *mp), mtz)
        pos2, _ = compute_positions(jd2)
        lagna2 = compute_lagna(jd2, args.match_lat, args.match_lon)
        l2s = sign_of(lagna2)
        print(f"\nCOMPATIBILITY — {args.name} ({args.role}) & {args.match_name} "
              f"({'girl' if args.role == 'boy' else 'boy'})")
        print(f"  {args.match_name}: {args.match_date} {args.match_time} ({mtz}, UTC{off2}) lat {args.match_lat} lon {args.match_lon}")
        print(f"  {args.match_name} Lagna {SIGNS[l2s]} {dms(deg_in_sign(lagna2))}, Chandra {SIGNS[sign_of(pos2['Mo']['lon'])]} "
              f"{dms(deg_in_sign(pos2['Mo']['lon']))} ({NAKSHATRAS[nakshatra_of(pos2['Mo']['lon'])[0]]} p{nakshatra_of(pos2['Mo']['lon'])[1]})")
        boy_moon, girl_moon = (pos["Mo"]["lon"], pos2["Mo"]["lon"]) if args.role == "boy" else (pos2["Mo"]["lon"], pos["Mo"]["lon"])
        total, rows = ashtakoota(boy_moon, girl_moon)
        print(f"  {'Koota':14}{'Pts':>5}{'Max':>5}  Detail (boy / girl)")
        for nm_, pts, mx, det in rows:
            print(f"  {nm_:14}{pts:>5}{mx:>5}  {det}")
        print(f"  TOTAL {total}/36  ({'good' if total >= 18 else 'below 18 — traditional threshold'}; "
              f"Bhakoot/Nadi are weighted heaviest — read notes above)")
        # Mangal dosha both
        def mangal(p_, ls_):
            h = house_from(ls_, sign_of(p_["Ma"]["lon"]))
            hm = house_from(sign_of(p_["Mo"]["lon"]), sign_of(p_["Ma"]["lon"]))
            hv = house_from(sign_of(p_["Ve"]["lon"]), sign_of(p_["Ma"]["lon"]))
            return h, hm, hv
        for lbl, p_, ls_ in ((args.name, pos, lagna_sign), (args.match_name, pos2, l2s)):
            h, hm, hv = mangal(p_, ls_)
            flag = [x for x, hh in (("Lagna", h), ("Chandra", hm), ("Shukra", hv)) if hh in (1, 2, 4, 7, 8, 12)]
            print(f"  Kuja position {lbl}: house {h} from La, {hm} from Mo, {hv} from Ve"
                  + (f"  -> Mangal dosha indication from {', '.join(flag)} (check cancellations)" if flag else "  -> no Mangal dosha"))
        print("  Synastry overlay D1:")
        for ln in synastry_overlay(pos, lagna, pos2, lagna2, args.name, args.match_name, 1):
            print(ln)
        print("  Synastry overlay D9:")
        for ln in synastry_overlay(pos, lagna, pos2, lagna2, args.name, args.match_name, 9):
            print(ln)
        match_out = {"partner": {"date": args.match_date, "time": args.match_time, "tz": mtz,
                                 "lagna": SIGNS[l2s], "moon": SIGNS[sign_of(pos2["Mo"]["lon"])]},
                     "ashtakoota_total": total,
                     "kootas": [{"name": r[0], "points": r[1], "max": r[2], "detail": r[3]} for r in rows]}

    # --- transit with ashtakavarga ---
    if args.transit:
        ty, tm, td = [int(x) for x in args.transit.split("-")]
        jd_t, _ = to_jd_ut(datetime(ty, tm, td, 12, 0), args.tz)
        tpos, _ = compute_positions(jd_t)
        bav, sav = ashtakavarga(pos, lagna_sign)
        print(f"\nGOCHARA {args.transit} (from natal Lagna/Chandra, with Ashtakavarga bindus)")
        for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
            ts = sign_of(tpos[c]["lon"])
            r = " R" if tpos[c]["retro"] and c not in ("Ra", "Ke") else ""
            bv = f"BAV {bav[c][ts]}, SAV {sav[ts]}" if c in bav else f"SAV {sav[ts]}"
            tnk_ = nakshatra_of(tpos[c]["lon"])[0]
            sp_ = sp_naks.get(tnk_)
            tara_ = TARA_NAMES[tara_of(nakshatra_of(pos["Mo"]["lon"])[0], tnk_)]
            print(f"  {PLANET_NAME[c]:8}{SIGNS[ts]:12}{dms(deg_in_sign(tpos[c]['lon'])):12}{r:3}"
                  f"house {house_from(lagna_sign, ts):2} from La, {house_from(moon_sign, ts):2} from Mo   {bv}   "
                  f"{NAKSHATRAS[tnk_][:10]:10} tara {tara_.split(' ')[0]:12}" + (f" ** {sp_[0]} nakshatra ({sp_[1]})" if sp_ else ""))

    # --- outputs ---
    if args.svg:
        pl = {}
        pl.setdefault(lagna_sign, []).append(f"La {int(ldeg)}°")
        for code, r in result_planets.items():
            lab = PLANET_NAME[code][:5] + (" R" if r["retro"] and code not in ("Ra", "Ke") else "")
            pl.setdefault(r["sign_idx"], []).append(lab)
        with open(args.svg, "w") as f:
            f.write(south_indian_svg(pl, f"D1 · {args.name}"))
        print(f"\nSVG written: {args.svg}")
    if args.svg_vargas:
        stem = (args.svg[:-4] if args.svg and args.svg.lower().endswith(".svg") else (args.svg or args.name.replace(" ", "_")))
        for v in [x.strip().upper() for x in args.svg_vargas.split(",") if x.strip()]:
            div = VARGA_DIVISIONS[v]
            pl = {}
            pl.setdefault(varga_sign(lagna, div), []).append("La")
            for code, r in result_planets.items():
                lab = PLANET_NAME[code][:5] + (" R" if r["retro"] and code not in ("Ra", "Ke") else "")
                pl.setdefault(varga_sign(pos[code]["lon"], div), []).append(lab)
            fn = f"{stem}_{v}.svg"
            with open(fn, "w") as f:
                f.write(south_indian_svg(pl, f"{v} · {args.name}"))
            print(f"SVG written: {fn}")

    if args.json:
        def ser(p):
            return {"lord": p["lord"], "start": p["start"].isoformat(), "end": p["end"].isoformat(),
                    "sub": [ser(x) for x in p["sub"]]}
        out = {
            "name": args.name, "birth": {"date": args.date, "time": args.time, "tz": args.tz,
                                         "utc_offset": str(offset), "place": args.place,
                                         "lat": args.lat, "lon": args.lon, "jd_ut": jd},
            "ayanamsa": ayan,
            "lagna": {"lon": round(lagna, 5), "sign": SIGNS[lagna_sign], "sign_idx": lagna_sign,
                      "deg_in_sign": round(ldeg, 4)},
            "planets": result_planets, "vargottama": vt, "yoga_indications": yg,
            "chara_karakas": kk, "arudhas": arudhas, "vargas": vargas_out,
            "vimshottari": {"moon_nakshatra": NAKSHATRAS[nk], "start_lord": lord0, "year_length": args.year_length,
                            "balance_years": bal, "mahadashas": [ser(m) for m in mds]},
            "narayana_dasa": nar_out, "narayana_varga": vnar_out, "ashtakavarga": av_out,
            "varsha_kundali": vk_out, "panchanga": pch, "compatibility": match_out,
            "chart_type": args.chart_type,
            "special_lagnas": {k: {"sign": SIGNS[sign_of(spl[k])], "lon": round(spl[k], 4)} for k in ("HL", "GL", "SL") if k in spl},
            "hora": hora_txt, **extra_out,
        }
        with open(args.json, "w") as f:
            json.dump(out, f, indent=1, ensure_ascii=False)
        print(f"JSON written: {args.json}")


def run_muhurta(args, ap):
    if not (args.muhurta_from and args.muhurta_to and args.lat is not None and args.lon is not None):
        ap.error("--muhurta needs --muhurta-from, --muhurta-to, --lat, --lon (optionally --date/--time for the natal chart)")
    y0, m0, d0 = [int(x) for x in args.muhurta_from.split("-")]
    y1, m1, d1 = [int(x) for x in args.muhurta_to.split("-")]
    h0, h1 = [int(x) for x in args.muhurta_hours.split("-")]
    natal, janma = None, None
    if args.date and args.time:
        parts = [int(x) for x in args.time.split(":")]
        while len(parts) < 3:
            parts.append(0)
        y, m, d = [int(x) for x in args.date.split("-")]
        jdn, _ = to_jd_ut(datetime(y, m, d, *parts), args.tz)
        npos, _ = compute_positions(jdn)
        nlag = sign_of(compute_lagna(jdn, args.lat, args.lon))
        natal = {"pos": npos, "lagna_sign": nlag}
        janma = nakshatra_of(npos["Mo"]["lon"])[0]
    elif args.janma_nakshatra:
        try:
            janma = int(args.janma_nakshatra) - 1
        except ValueError:
            m_ = [i for i, n_ in enumerate(NAKSHATRAS) if n_.lower().startswith(args.janma_nakshatra.lower()[:5])]
            janma = m_[0] if m_ else None
    tz = ZoneInfo(args.tz)
    from datetime import date as _date
    windows, note, samples = muhurta_scan(args.muhurta, _date(y0, m0, d0), _date(y1, m1, d1), args.lat, args.lon, args.tz,
                                          janma_nak=janma, hours=(h0, h1), natal=natal)
    print("=" * 72)
    print(f"MUHURTA SCAN — task: {args.muhurta}  |  {args.muhurta_from} to {args.muhurta_to}, {h0:02d}:00-{h1:02d}:00 {args.tz}  |  lat {args.lat} lon {args.lon}")
    print(f"Rules: textbook Table 79 (tithi/vara/nakshatra/lagna/empty house) as hard filters; tara (Table 64), hora (1.3.11), karana and house strength (36.4) as score.")
    print(f"Task note: {note}")
    print(f"Janma nakshatra for tara: {NAKSHATRAS[janma] if janma is not None else '(not given — tara not applied; pass --date/--time or --janma-nakshatra)'}")
    print("=" * 72)
    ok_days = sorted({jd_to_datetime(w["jd_start"]).astimezone(tz).date() for w in windows})
    print(f"\nDays with at least one passing window: {len(ok_days)} of {(_date(y1, m1, d1) - _date(y0, m0, d0)).days + 1}")
    if not windows:
        fails = {}
        for smp in samples:
            for f in smp.get("fail", []):
                key = f.split(" ")[0]
                fails[key] = fails.get(key, 0) + 1
        print("  No window passed all hard filters. Most common blockers: " + ", ".join(f"{k} x{v}" for k, v in sorted(fails.items(), key=lambda kv: -kv[1])[:5]))
        print("  Try a wider date range, --muhurta-hours 0-24, or a different task profile.")
        return
    print(f"\nTOP {min(args.muhurta_top, len(windows))} WINDOWS (score = soft points; higher is better):")
    print(f"  {'date':10} {'start':5}-{'end':5}  {'lagna':10} {'tithi':22} {'vara':7} {'nakshatra':16} {'hora':12} score  notes")
    ranked = sorted(windows, key=lambda w: (-w["score"], w["jd_start"]))[:args.muhurta_top]
    for w in sorted(ranked, key=lambda w: w["jd_start"]):
        a = jd_to_datetime(w["jd_start"]).astimezone(tz)
        b = jd_to_datetime(w["jd_end"]).astimezone(tz)
        horas = "/".join(PLANET_NAME[h][:5] for h in sorted(w["horas"]))
        tara = f"; tara {TARA_NAMES[w['tara']].split(' ')[0]}" if w["tara"] is not None else ""
        notes = "; ".join(sorted(r for r in w["reasons"] if not r.startswith(("hora", "tara", "janma tara"))))
        print(f"  {a.strftime('%Y-%m-%d')} {a.strftime('%H:%M')}-{b.strftime('%H:%M')}  {SIGNS[w['lagna']]:10} {w['tithi']:22} {w['vara']:7} "
              f"{NAKSHATRAS[w['nak']]:16} {horas:12} {w['score']:>5}  {notes}{tara}")
    # detail of the best window
    best = ranked[0] if ranked else None
    if best:
        jd_mid = (best["jd_start"] + best["jd_end"]) / 2
        a = jd_to_datetime(jd_mid).astimezone(tz)
        spec = MUHURTA_TASKS[args.muhurta]
        vmap = {"wedding": 9, "job": 10, "business": 10, "vidyarambha": 24, "griha_pravesha": 4, "property": 4, "vehicle": 16, "house_construction": 4}
        pos, _ = compute_positions(jd_mid)
        best["lagna_lon"] = compute_lagna(jd_mid, args.lat, args.lon)
        best["lagna"] = sign_of(best["lagna_lon"])
        print(f"\nBEST WINDOW DETAIL (mid-point) — {a.strftime('%Y-%m-%d %H:%M')} lagna {SIGNS[best['lagna']]} {dms(deg_in_sign(best['lagna_lon']))}")
        for c in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
            print(f"    {PLANET_NAME[c]:8}{SIGNS[sign_of(pos[c]['lon'])]:12}{dms(deg_in_sign(pos[c]['lon'])):13} house {house_from(best['lagna'], sign_of(pos[c]['lon']))}")
        if args.muhurta in vmap:
            dv = vmap[args.muhurta]
            vl = varga_sign(best["lagna_lon"], dv)
            occ = {h: [PLANET_NAME[p][:5] for p in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"] if house_from(vl, varga_sign(pos[p]["lon"], dv)) == h] for h in spec[6]}
            print(f"    D-{dv} lagna {SIGNS[vl]}; relevant houses {spec[6]} in D-{dv}: " + "; ".join(f"h{h}: {', '.join(v) or '-'}" for h, v in occ.items()))
        print("    Planetary strength outweighs thumb-rules (36.4) — read the muhurta chart like a natal chart before finalising.")
    print("\nNOTE: Sri Lankan traditional nakath practice (rahu kalaya, litha) is a different system; present this as a Parasara-based second opinion.")


def print_transit(date_str, tzname):
    y, m, d = [int(x) for x in date_str.split("-")]
    jd, offset = to_jd_ut(datetime(y, m, d, 12, 0), tzname)
    pos, ayan = compute_positions(jd)
    print(f"TRANSIT (sidereal, Lahiri) {date_str} 12:00 {tzname}")
    for code in ["Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"]:
        p = pos[code]
        s = sign_of(p["lon"])
        nk, pd, _ = nakshatra_of(p["lon"])
        r = " R" if p["retro"] and code not in ("Ra", "Ke") else ""
        print(f"  {PLANET_NAME[code]:8}{SIGNS[s]:12}{dms(deg_in_sign(p['lon']))}  {NAKSHATRAS[nk]} p{pd}{r}")


if __name__ == "__main__":
    main()
