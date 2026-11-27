"""Visi porondam: the Sri Lankan twenty-fold matching (jyotisha_calc.visi_porondam) and its report.

The rules follow the Lanka Panchanga and Epa Panchanga lithas as transcribed in the Sinhala Wikipedia
article "පොරොන්දම්" (revision 604901). Each rule test below quotes the article's own example or
wording; the group tables are also checked against a second, independent Sri Lankan implementation
(github.com/sampathmenuka/horoscope-reader, backend/main.py) where the two overlap.
"""
import itertools
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import jyotisha_calc as jc  # noqa: E402

NAK = {n: i for i, n in enumerate(jc.NAKSHATRAS)}
SIGN = {s: i for i, s in enumerate(jc.SIGNS)}


def lon_of(nak, sign=None):
    """A Moon longitude in the given nakshatra (and sign, where the nakshatra spans two)."""
    lo, hi = NAK[nak] * 360 / 27, (NAK[nak] + 1) * 360 / 27
    if sign is not None:
        lo, hi = max(lo, SIGN[sign] * 30), min(hi, SIGN[sign] * 30 + 30)
        assert lo < hi, (nak, sign)
    return (lo + hi) / 2


def person(nak, sign=None, weekday=0, pos=None, lagna=0):
    p = pos or {k: {"lon": 100.0} for k in ("Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke")}
    return {"moon": lon_of(nak, sign), "weekday": weekday, "pos": p, "lagna_sign": lagna}


def grade(key, bride, groom):
    rows = jc.visi_porondam(bride, groom)
    return next(r for r in rows if r["key"] == key)["grade"]


# ---------------------------------------------------------------- the tables

def test_groups_match_the_litha_and_the_engine():
    # gana and nadi: the Ashtakoota tables already in the engine are the same as the litha's
    deva = {i for i, g in enumerate(jc.NAK_GANA) if g == "Deva"}
    assert deva == {NAK[n] for n in ("Ashwini", "Mrigashira", "Punarvasu", "Pushya", "Hasta", "Swati", "Anuradha",
                                      "Shravana", "Revati")}
    # rajju (pada, uru, nabhi, bahu, shiro): as printed, and as in the independent implementation
    groups = [{i for i, r in enumerate(jc.PR_RAJJU) if r == k} for k in range(5)]
    assert groups == [{0, 8, 9, 17, 18, 26}, {1, 7, 10, 16, 19, 25}, {2, 6, 11, 15, 20, 24},
                      {3, 5, 12, 14, 21, 23}, {4, 13, 22}]
    assert len(jc.PR_VEDHA) == 15 and all(len(p) == 2 for p in jc.PR_VEDHA)
    assert sorted(len(set(jc.PR_GOTRAS[i] for i in range(27)) & {g}) for g in set(jc.PR_GOTRAS)) == [1] * 7
    assert [jc.PR_GOTRAS.count(g) for g in dict.fromkeys(jc.PR_GOTRAS)] == [4, 4, 4, 4, 4, 3, 4]
    assert sorted(jc.PR_LINGA.count(x) for x in "MFN") == [3, 11, 13]


# ---------------------------------------------------------------- the rules, with the litha's examples

def test_nakshatra_porondam_example():
    """Litha: bride Ashwini, groom Pushya - Pushya is the 8th star, so it matches."""
    assert grade("nakshatra", person("Ashwini"), person("Pushya")) == 1
    good = {2, 4, 6, 8, 9, 11, 13, 15, 17, 18, 20, 22, 24, 26, 27}
    for c in range(1, 28):
        groom = jc.NAKSHATRAS[(NAK["Ashwini"] + c - 1) % 27]
        assert (grade("nakshatra", person("Ashwini"), person(groom)) == 1) == (c in good), c


@pytest.mark.parametrize("count, mahendra, stree", [(4, 2, -1), (5, -1, -1), (8, -1, -1), (9, -1, -1), (10, 2, 0),
                                                    (13, 2, 0), (14, -1, 2), (25, 2, 2), (27, -1, 2)])
def test_mahendra_and_stree_deergha(count, mahendra, stree):
    groom = jc.NAKSHATRAS[(NAK["Rohini"] + count - 1) % 27]
    assert grade("mahendra", person("Rohini"), person(groom)) == mahendra
    assert grade("stree_deergha", person("Rohini"), person(groom)) == stree


def test_gana():
    assert grade("gana", person("Ashwini"), person("Revati")) == 2          # both deva: very good
    assert grade("gana", person("Ashwini"), person("Bharani")) == 0         # deva-manushya: medium
    assert grade("gana", person("Krittika"), person("Ashwini")) == -1       # rakshasa with another: bad


def test_yoni():
    horse_m, horse_f, buffalo_f, buffalo_m = "Ashwini", "Shatabhisha", "Hasta", "Swati"
    assert grade("yoni", person(horse_f), person(horse_m)) == 2              # same animal, female to the bride
    assert grade("yoni", person(horse_m), person(horse_f)) == 0              # same animal, crossed: medium
    assert grade("yoni", person(buffalo_f), person(horse_m)) == -2           # great enemies: very bad
    assert grade("yoni", person(buffalo_f), person(horse_f)) == -1           # great enemies, both female: bad
    assert grade("yoni", person("Krittika"), person(horse_m)) == 1           # sheep (f) and horse (m): good
    assert grade("yoni", person("Pushya"), person(buffalo_m)) == 0           # two males, not enemies: medium
    assert grade("yoni", person(horse_m), person(buffalo_m)) == -2
    assert grade("yoni", person(horse_m), person("Krittika")) is None        # bride male, groom female: no rule


def test_rashi_and_its_lord():
    """Litha: bride Makara, groom Simha - Saturn and the Sun are enemies, so rashyadhipati fails."""
    assert grade("rashyadhipati", person("Shravana", "Makara"), person("Magha", "Simha")) == -1
    assert grade("rashyadhipati", person("Ashwini", "Mesha"), person("Jyeshtha", "Vrischika")) == 1   # same lord
    rashi = {1: 2, 2: -1, 3: 0, 4: 0, 5: -1, 6: -1, 7: 1, 8: 0, 9: 1, 10: 1, 11: 1, 12: 0}
    for c, want in rashi.items():
        groom_sign = jc.SIGNS[(SIGN["Mesha"] + c - 1) % 12]
        groom_nak = next(n for n in jc.NAKSHATRAS if lon_of(n) // 30 == SIGN[groom_sign])
        assert grade("rashi", person("Bharani", "Mesha"), person(groom_nak, groom_sign)) == want, c


def test_vashya():
    assert grade("vashya", person("Ashwini", "Mesha"), person("Magha", "Simha")) == 1          # Mesha -> Simha
    assert grade("vashya", person("Magha", "Simha"), person("Ashwini", "Mesha")) == 1          # either way
    assert grade("vashya", person("Rohini", "Vrishabha"), person("Ashwini", "Mesha")) == -1


def test_rajju_and_vedha():
    assert grade("rajju", person("Ashwini"), person("Magha")) == -1           # both pada
    assert grade("rajju", person("Ashwini"), person("Bharani")) == 1
    assert grade("vedha", person("Ashwini"), person("Jyeshtha")) == -1        # see the correction in jyotisha_calc
    assert grade("vedha", person("Ashwini"), person("Dhanishtha")) == 1
    assert grade("vedha", person("Chitra"), person("Dhanishtha")) == -1       # Mars' three stars
    assert grade("vedha", person("Bharani"), person("Anuradha")) == -1


def test_trees_birds_elements():
    assert grade("vriksha", person("Pushya"), person("Revati")) == 1         # both milk trees
    assert grade("vriksha", person("Ashwini"), person("Bharani")) == -1      # neither
    assert grade("vriksha", person("Pushya"), person("Ashwini")) is None     # mixed: no rule
    assert grade("pakshi", person("Ardra"), person("Hasta")) == -1            # litha: Pingala + Kaka, enemies
    assert grade("pakshi", person("Hasta"), person("Anuradha")) == 1          # litha: Kaka + Kukkuta, friends
    assert grade("pakshi", person("Ashwini"), person("Bharani")) is None      # same bird: no rule
    assert grade("bhuta", person("Ashwini"), person("Ardra")) == 2            # Pathavi + Apo: the best
    assert grade("bhuta", person("Ardra"), person("Hasta")) == -2             # Apo + Tejo: water and fire
    assert grade("bhuta", person("Ashwini"), person("Hasta")) is None         # Pathavi + Tejo: no rule


def test_gotra_varna_linga_nadi():
    assert grade("gotra", person("Anuradha"), person("Purva Ashadha")) == -1  # both Pulastya (corrected range)
    assert grade("gotra", person("Ashwini"), person("Mrigashira")) == 1
    assert grade("varna", person("Bharani"), person("Ashwini")) == 1          # groom Brahmana, bride Kshatriya
    assert grade("varna", person("Ashwini"), person("Bharani")) == -1         # bride of the higher varna
    assert grade("linga", person("Krittika"), person("Ashwini")) == 1         # bride stri, groom purusha
    assert grade("linga", person("Ashwini"), person("Bharani")) == -1         # both purusha
    assert grade("linga", person("Ashwini"), person("Krittika")) is None      # crossed: no rule
    assert grade("nadi", person("Ashwini"), person("Ardra")) == -1            # both purva nadi


def test_dina():
    """Litha: bride Sunday, groom Monday (the 2nd day) matches; the 6th and 7th days do not."""
    def dina(b, g):
        return grade("dina", person("Ashwini", weekday=b), person("Ashwini", weekday=g))
    assert dina(0, 1) == 1 and dina(0, 0) == 1 and dina(0, 4) == 1
    assert dina(0, 5) == -1 and dina(0, 6) == -1 and dina(3, 1) == -1


def test_graha_and_ayushya():
    calm = {k: {"lon": v} for k, v in dict(Su=10, Mo=40, Ma=100, Me=20, Ju=130, Ve=70, Sa=160, Ra=310, Ke=130).items()}
    stormy = dict(calm, Ma={"lon": 225.0})           # Mars 8th from a Mesha Lagna
    assert jc.graha_dosha(calm, 0) == []
    b_calm, b_storm = person("Ashwini", pos=calm), person("Ashwini", pos=stormy)
    assert grade("graha", b_calm, b_calm) == 1
    assert grade("graha", b_storm, b_calm) == -1     # only the bride's chart
    assert grade("graha", b_storm, b_storm) == 0     # both: balanced
    assert grade("graha", b_calm, b_storm) is None   # only the groom's: the litha does not say
    assert grade("ayushya", b_calm, b_calm) is None


@pytest.mark.parametrize("bn, gn", list(itertools.product(range(27), repeat=2)))
def test_every_pair_gives_twenty_sane_results(bn, gn):
    rows = jc.visi_porondam(person(jc.NAKSHATRAS[bn]), person(jc.NAKSHATRAS[gn]))
    assert [r["key"] for r in rows] == jc.PORONDAM_NAMES and [r["no"] for r in rows] == list(range(1, 21))
    assert all(r["grade"] in (2, 1, 0, -1, -2, None) for r in rows)
    assert sum(jc.porondam_summary(rows)) == 20
    g = {r["key"]: r["grade"] for r in rows}
    assert (g["rajju"] == -1) == (jc.PR_RAJJU[bn] == jc.PR_RAJJU[gn])
    assert (g["nadi"] == -1) == (jc.NAK_NADI[bn] == jc.NAK_NADI[gn])
    assert g["vedha"] == grade("vedha", person(jc.NAKSHATRAS[gn]), person(jc.NAKSHATRAS[bn]))   # symmetric


# ---------------------------------------------------------------- against an established calculator

# Four made-up couples (bride, groom; Sri Lanka time) entered in porondam.lk's free 20-porondam
# calculator on 2026-11-27. Over all 80 verdicts, 59 agree on match / no match (48 with the same grade)
# and 11 are cases our litha gives no rule for. The 10 that disagree come from different conventions:
# porondam.lk also uses the Lagna signs for rashi, vashya and rashyadhipati (the litha says to use the
# Moon's), treats Kaka-Herunda as friends (the litha's bird table: enemies), and judges graha its own way.
# The porondam below are decided by the Moon's star alone and agree in every couple; they must stay so.
PORONDAM_LK = [
    (("1992-02-12", "11:00", 7.2906, 80.6337), ("1990-03-01", "13:00", 6.9271, 79.8612),
     dict(nakshatra=1, gana=-1, mahendra=-1, stree_deergha=1, rajju=1, vedha=1, gotra=-1, nadi=1, dina=1, linga=1)),
    (("1994-08-10", "10:00", 6.0535, 80.2210), ("1991-11-20", "15:00", 7.4863, 80.3647),
     dict(nakshatra=1, gana=0, mahendra=-1, stree_deergha=1, rajju=1, vedha=1, gotra=1, nadi=-1, dina=1, linga=1)),
    (("1988-05-05", "09:30", 5.9549, 80.5550), ("1986-12-15", "11:45", 9.6615, 80.0255),
     dict(nakshatra=1, gana=-1, mahendra=1, stree_deergha=0, rajju=1, vedha=1, gotra=1, nadi=1, dina=1)),
    (("1995-01-25", "14:20", 6.9271, 79.8612), ("1989-06-30", "08:15", 7.2906, 80.6337),
     dict(nakshatra=1, gana=1, mahendra=-1, stree_deergha=1, rajju=-1, vedha=-1, gotra=1, nadi=-1, dina=1, linga=1)),
]


def real_person(date_, time_, lat, lon):
    import datetime as dt
    jd, _ = jc.to_jd_ut(dt.datetime.fromisoformat(f"{date_}T{time_}"), "Asia/Colombo")
    pos, _ = jc.compute_positions(jd)
    return {"moon": pos["Mo"]["lon"], "weekday": jc.birth_weekday(jd, lat, lon, "Asia/Colombo"), "pos": pos,
            "lagna_sign": jc.sign_of(jc.compute_lagna(jd, lat, lon))}


PORONDAM_LK_LAGNAS = [("Mesha", "Mithuna"), ("Kanya", "Meena"), ("Mithuna", "Kumbha"), ("Vrishabha", "Karka")]


@pytest.mark.parametrize("couple, lagnas", list(zip(PORONDAM_LK, PORONDAM_LK_LAGNAS)))
def test_lagnas_agree_with_porondam_lk(couple, lagnas):
    """porondam.lk printed each person's Lagna: ours is the same for all eight."""
    bride, groom, _ = couple
    assert (jc.SIGNS[real_person(*bride)["lagna_sign"]], jc.SIGNS[real_person(*groom)["lagna_sign"]]) == lagnas


def test_lagna_results_shown_alongside():
    """Rashi, rashyadhipati and vashya: the verdict comes from the Moon signs (the litha's rule); the same
    rules on the two Lagnas are given alongside, and the tally ignores them."""
    bride = dict(person("Krittika", "Vrishabha"), lagna_sign=SIGN["Makara"])
    groom = dict(person("Ashwini", "Mesha"), lagna_sign=SIGN["Simha"])
    rows = {r["key"]: r for r in jc.visi_porondam(bride, groom)}
    moon, lagna = jc.sign_rules(SIGN["Vrishabha"], SIGN["Mesha"]), jc.sign_rules(SIGN["Makara"], SIGN["Simha"])
    for key in ("rashi", "rashyadhipati", "vashya"):
        assert {k: v for k, v in rows[key].items() if k in moon[key]} == moon[key]
        assert rows[key]["lagna"] == lagna[key]
    assert rows["rashyadhipati"]["lagna"]["grade"] == -1          # Saturn and the Sun: the litha's own example
    assert [k for k, r in rows.items() if "lagna" in r] == ["rashi", "rashyadhipati", "vashya"]
    plain = dict(groom, lagna_sign=SIGN["Mesha"])
    assert jc.porondam_summary(jc.visi_porondam(bride, groom)) == jc.porondam_summary(jc.visi_porondam(bride, plain))


@pytest.mark.parametrize("bride, groom, expected", PORONDAM_LK)
def test_agrees_with_porondam_lk_where_the_moon_decides(bride, groom, expected):
    rows = {r["key"]: r["grade"] for r in jc.visi_porondam(real_person(*bride), real_person(*groom))}
    got = {k: max(-1, min(1, rows[k])) for k in expected}       # porondam.lk has no "very" grades
    assert got == expected


# ---------------------------------------------------------------- engine output and the reports

COUPLE = ["--date", "1990-03-01", "--time", "12:00", "--lat", "6.9271", "--lon", "79.8612", "--tz", "Asia/Colombo"]
PARTNER = ["--match-date", "1992-02-12", "--match-time", "12:00", "--match-lat", "7.2906", "--match-lon", "80.6337"]


def calc_json(tmp_path, args):
    out = tmp_path / "c.json"
    subprocess.run([sys.executable, str(ROOT / "jyotisha_calc.py"), "--name", "X", *args, "--json", str(out)],
                   check=True, capture_output=True)
    return json.loads(out.read_text(encoding="utf-8"))["compatibility"]


def test_bride_and_groom_follow_the_role(tmp_path):
    """The same two people give the same porondam whichever of them is entered first."""
    a = calc_json(tmp_path, COUPLE + PARTNER + ["--role", "boy"])
    swapped = ["--date", "1992-02-12", "--time", "12:00", "--lat", "7.2906", "--lon", "80.6337", "--tz", "Asia/Colombo",
               "--match-date", "1990-03-01", "--match-time", "12:00", "--match-lat", "6.9271", "--match-lon", "79.8612",
               "--role", "girl"]
    b = calc_json(tmp_path, swapped)
    assert a["visi_porondam"] == b["visi_porondam"] and a["visi_summary"] == b["visi_summary"]
    assert a["visi_summary"] == {"match": 12, "no_match": 5, "no_rule": 3}


def test_d1_report_shows_the_twenty(tmp_path):
    pytest.importorskip("weasyprint")
    page = tmp_path / "d1.html"
    r = subprocess.run([sys.executable, str(ROOT / "jyotisha_report.py"), "--report=D1", "--name=K", "--date=1990-03-01",
                        "--time=12:00", "--lat=6.9271", "--lon=79.8612", "--match-name=N", "--match-date=1992-02-12",
                        "--match-time=12:00", "--match-lat=7.2906", "--match-lon=80.6337", "--role=boy",
                        f"--out={tmp_path / 'd1.pdf'}", f"--html={page}"], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-400:]
    h = page.read_text(encoding="utf-8")
    assert "2. විසි පොරොන්දම (ශ්‍රී ලාංකික ක්‍රමය)" in h and "පොරොන්දම් 20න් 12ක් ගැලපේ" in h
    assert "විසි පොරොන්දම: <b>12 / 20</b>" in h                               # on the cover
    assert h.count("ලග්න අනුව:") == 3                                        # rashi, rashyadhipati, vashya
    assert h.count("<td>") >= 20 * 4 and "3. අෂ්ටකූට ලකුණු" in h
