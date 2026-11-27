"""Shadbala (jyotisha_calc.shadbala), checked against the two classic worked examples and for
internal consistency on many charts.

Book values (virupas, Sun..Saturn) are from B.V. Raman, "Graha and Bhava Balas" (1918-10-16 14:22:16
IST, Bangalore 13N 77E35, Raman ayanamsa) and V.P. Jain, "Shadbala and Bhavabala" (1981-09-13 01:30
IST, Delhi 28N39 77E13, Lahiri), as transcribed in PyJHora's test suite. Known differences, each
checked below rather than hidden:
  - Raman's printed dig bala of Mars (64.30) is above the 60 maximum: the distance was not folded.
  - Raman's printed uchcha bala of Saturn (34.08) disagrees with his own sthana total (177.30), which ours matches.
  - Chesta bala of Mercury and Venus: the books take mean positions from Raman's Surya-Siddhanta
    tables (Mercury's ~12 deg ahead of the modern value); we use modern mean elements.
"""
import datetime as dt
import json
import math
import pathlib
import random
import subprocess
import sys

import pytest
import swisseph as swe

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import jyotisha_calc as jc  # noqa: E402

P = jc.SEVEN


def run(ut, lat, lon, ayanamsa="lahiri", tz="Asia/Kolkata"):
    saved = jc.SID_MODE, jc.AYANAMSA_NAME
    jc.set_ayanamsa(ayanamsa)
    try:
        jd = swe.julday(*ut)
        pos, _ = jc.compute_positions(jd)
        sb = jc.shadbala(jd, lat, lon, tz, pos, jc.compute_lagna(jd, lat, lon),
                         jc.sripati_bhavas(jd, lat, lon, pos)["madhya"])
    finally:
        jc.SID_MODE, jc.AYANAMSA_NAME = saved
        swe.set_sid_mode(saved[0])
    return sb, pos


def column(sb, key):
    def get(o):
        if key in o["sthana"]:
            return o["sthana"][key]
        if key in o["kala"]:
            return o["kala"][key]
        return sum(o[key].values()) if isinstance(o[key], dict) else o[key]
    return [get(sb[p]) for p in P]


RAMAN = run((1918, 10, 16, 14 + 22 / 60 + 16 / 3600 - 5.5), 13.0, 77 + 35 / 60, "raman")[0]
JAIN = run((1981, 9, 12, 20.0), 28 + 39 / 60, 77 + 13 / 60)[0]

BOOKS = {  # key: (raman, jain, tolerance)
    "saptavargaja": ([90, 48.75, 90, 135, 71.25, 116.25, 97.5], [127.5, 30, 135, 120, 58.13, 150, 82.5], 0.01),
    "ojayugma": ([30, 15, 15, 30, 15, 30, 15], [15, 0, 15, 0, 0, 15, 0], 0),
    "kendradi": ([60, 30, 30, 60, 15, 15, 30], None, 0),
    "drekkana": ([15, 0, 0, 0, 0, 15, 0], None, 0),
    "tribhaga": ([0, 0, 0, 0, 60, 0, 60], [0, 0, 0, 0, 60, 60, 0], 0),
    "abda": ([0, 0, 0, 0, 0, 0, 15], [0, 0, 15, 0, 0, 0, 0], 0),
    "masa": ([0, 0, 0, 30, 0, 0, 0], [0, 0, 30, 0, 0, 0, 0], 0),
    "vara": ([0, 0, 0, 45, 0, 0, 0], [0, 0, 0, 0, 0, 0, 45], 0),
    "hora": ([0, 60, 0, 0, 0, 0, 0], [0, 0, 0, 60, 0, 0, 0], 0),
    "paksha": ([16.54, 86.92, 16.54, 16.54, 43.46, 43.46, 16.54], [5.62, 108.76, 5.62, 54.38, 54.38, 54.38, 5.62], 0.05),
    "nathonnata": ([48.32, 11.68, 11.68, 60, 48.32, 48.32, 11.68], [6.1, 53.9, 53.9, 60, 6.1, 6.1, 53.9], 0.3),
    "ayana": ([38.12, 43.44, 1.84, 41.25, 59.4, 23.75, 13.75], [70.08, 43.19, 53.56, 37.10, 22.94, 15.41, 35.04], 0.55),
    "drik": ([15.86, -21.73, 0.95, 15.64, -16.04, 18.47, 7.21], [11.24, -0.32, -5.10, 4.29, 4.32, -2.86, 5.82], 0.05),
    "sthana": ([198, 126.5, 172.06, 279.5, 157.58, 178.2, 177.3], [172.04, 77.17, 184.94, 238.16, 152.98, 198.08, 206.31], 0.1),
    # the Mercury-Jupiter war in Jain's chart (0.13 deg apart): Jupiter, further north, wins about 0.8
    "kala": ([102.98, 202.04, 30.06, 192.79, 211.18, 115.53, 116.97], [81.80, 205.85, 158.08, 210.68, 144.22, 135.89, 139.56], 0.65),
}


@pytest.mark.parametrize("key", BOOKS)
def test_matches_the_books(key):
    raman, jain, tol = BOOKS[key]
    for ours, book in ((column(RAMAN, key), raman), (column(JAIN, key), jain)):
        if book is not None:
            assert max(abs(a - b) for a, b in zip(ours, book)) <= tol, (key, ours, book)


def test_book_exceptions_are_what_we_say_they_are():
    # uchcha: Raman's Saturn misprint; the rest agree
    assert max(abs(a - b) for a, b in zip(column(RAMAN, "uchcha")[:6], [3.0, 32.75, 37.06, 54.5, 56.33, 1.95])) < 0.1
    assert abs(sum(RAMAN["Sa"]["sthana"].values()) - 177.30) < 0.05          # his own total for Saturn
    # dig: everything within 0.4 except Raman's Mars, whose printed 64.30 is 120 minus the folded value
    dig_r, dig_j = column(RAMAN, "dig"), column(JAIN, "dig")
    assert all(abs(a - b) <= 0.4 for i, (a, b) in enumerate(zip(dig_r, [48.10, 31.56, 64.30, 21.09, 11.50, 15.15, 58.02])) if i != 2)
    assert abs((120 - dig_r[2]) - 64.30) < 0.5
    assert max(abs(a - b) for a, b in zip(dig_j, [6.59, 12.22, 20.99, 31.97, 31.99, 53.29, 26.67])) < 0.05
    # chesta: Mars, Jupiter, Saturn within 0.5; Mercury and Venus differ by the mean-position convention only
    for ours, book in ((column(RAMAN, "chesta"), [0, 0, 22.23, 2.3, 35.26, 5.95, 21.14]),
                       (column(JAIN, "chesta"), [0, 0, 20.93, 28.76, 8.43, 28.18, 5.05])):
        assert all(abs(ours[i] - book[i]) <= 0.5 for i in (0, 1, 2, 4, 6))
        assert abs(ours[3] - book[3]) < 5 and abs(ours[5] - book[5]) < 1.5


def test_planetary_war_victor_is_the_northern_planet():
    assert JAIN["Ju"]["kala"]["yuddha"] > 0.5 and JAIN["Me"]["kala"]["yuddha"] == -JAIN["Ju"]["kala"]["yuddha"]
    assert all(RAMAN[p]["kala"]["yuddha"] == 0 for p in P)                 # no two planets within 1 degree
    # the great conjunction of 2020-12-21: Saturn, north of Jupiter, wins
    sb, pos = run((2020, 12, 21, 13.0), 6.9271, 79.8612, tz="Asia/Colombo")
    assert jc._arc(pos["Ju"]["lon"], pos["Sa"]["lon"]) < 1
    assert sb["Sa"]["kala"]["yuddha"] > 0 > sb["Ju"]["kala"]["yuddha"]


def test_mercury_tie_goes_to_the_nearest_planet():
    """Galle 2010-03-15 18:45: Mercury in Pisces with the Sun (malefic, 1 deg away) and Venus (benefic):
    a tie, so the Sun decides and Mercury counts as a malefic for paksha and drik bala."""
    jd, _ = jc.to_jd_ut(dt.datetime(2010, 3, 15, 18, 45), "Asia/Colombo")
    pos, _ = jc.compute_positions(jd)
    assert "Me" not in jc.shadbala_benefics(pos)
    assert "Me" in jc.natural_benefics(pos)                                  # the engine's general rule differs


def random_charts(n=40, seed=7):
    rng = random.Random(seed)
    for _ in range(n):
        when = dt.datetime(1900, 1, 1) + dt.timedelta(minutes=rng.randrange(200 * 365 * 24 * 60))
        yield when, rng.uniform(-60, 60), rng.uniform(-180, 180)


@pytest.mark.parametrize("when, lat, lon", list(random_charts()))
def test_every_component_stays_in_range(when, lat, lon):
    jd = swe.julday(when.year, when.month, when.day, when.hour + when.minute / 60)
    pos, _ = jc.compute_positions(jd)
    sb = jc.shadbala(jd, lat, lon, "UTC", pos, jc.compute_lagna(jd, lat, lon),
                     jc.sripati_bhavas(jd, lat, lon, pos)["madhya"])
    for p in P:
        o, k = sb[p], sb[p]["kala"]
        assert 0 <= o["sthana"]["uchcha"] <= 60 and 0 <= o["dig"] <= 60 and 0 <= o["chesta"] <= 60
        assert 0 <= k["paksha"] <= (120 if p == "Mo" else 60)
        assert 0 <= k["ayana"] <= (120 if p == "Su" else 60)
        assert 0 <= k["nathonnata"] <= 60
        total = sum(o["sthana"].values()) + o["dig"] + sum(k.values()) + o["chesta"] + o["naisargika"] + o["drik"]
        assert math.isclose(o["total"], total) and math.isclose(o["ratio"], total / 60 / o["required"])
    lords = {key: [p for p in P if sb[p]["kala"][key] > 0] for key in ("abda", "masa", "vara", "hora")}
    assert all(len(v) == 1 for v in lords.values())                            # one lord of each
    assert sorted(p for p in P if sb[p]["kala"]["tribhaga"]) == sorted({"Ju", *[p for p in P if p != "Ju" and sb[p]["kala"]["tribhaga"]]})
    assert sum(1 for p in P if sb[p]["kala"]["tribhaga"]) == 2                 # Jupiter and the ruler of the third
    assert math.isclose(sb["Su"]["kala"]["nathonnata"] + sb["Mo"]["kala"]["nathonnata"], 60)
    assert abs(sum(sb[p]["kala"]["yuddha"] for p in P)) < 1e-9


def test_engine_json_and_polar_case(tmp_path):
    def calc(lat, date="1990-05-15", time="10:30", tz="Asia/Colombo"):
        out = tmp_path / f"c{lat}.json"
        subprocess.run([sys.executable, str(ROOT / "jyotisha_calc.py"), "--name", "A", "--date", date, "--time", time,
                        "--lat", str(lat), "--lon", "25", "--tz", tz, "--json", str(out)], check=True, capture_output=True)
        return json.loads(out.read_text(encoding="utf-8"))["shadbala"]
    sb = calc(6.9271)
    assert set(sb) == set(P) and all(abs(sb[p]["rupas"] * 60 - sb[p]["total"]) <= 0.31 for p in P)   # 2-dp rounding
    assert calc(66, "2000-06-21", "12:00", "Europe/Helsinki") is None        # midnight sun: no kala bala


def test_a2_report_shows_shadbala(tmp_path):
    pytest.importorskip("weasyprint")
    page = tmp_path / "a2.html"
    r = subprocess.run([sys.executable, str(ROOT / "jyotisha_report.py"), "--report=A2", "--name=S", "--date=1990-05-15",
                        "--time=10:30", "--lat=6.9271", "--lon=79.8612", f"--out={tmp_path / 'a2.pdf'}", f"--html={page}"],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-400:]
    h = page.read_text(encoding="utf-8")
    assert "ෂඩ්බල — ග්‍රහයන්ගේ ශක්තිය" in h and "<th>අනුපාතය</th>" in h
