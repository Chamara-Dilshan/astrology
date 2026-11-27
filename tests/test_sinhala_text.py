"""The Sinhala reports must not show the engine's English. Found 2026-11-27: yoga names, Tajaka lines,
porondam details and the muhurta chart came through in English in A1-A3, B, C1/C2, D1/D2 and M1.
Prashna (Shatpanchasika) rules are not covered yet: that table is still being translated."""
import random
import re
from datetime import datetime

import jyotisha_calc as jc
import jyotisha_report as jr

OK = {"R"}   # retrograde mark in Tajaka lines


def english(text):
    return [w for w in re.findall(r"[A-Za-z]{2,}", text) if w not in OK]


def charts(n, seed=11):
    rnd = random.Random(seed)
    for _ in range(n):
        dt = datetime(rnd.randint(1940, 2030), rnd.randint(1, 12), rnd.randint(1, 28), rnd.randint(0, 23), rnd.randint(0, 59))
        jd, _ = jc.to_jd_ut(dt, "Asia/Colombo")
        pos, _ = jc.compute_positions(jd)
        yield pos, jc.sign_of(jc.compute_lagna(jd, rnd.uniform(5.9, 9.8), rnd.uniform(79.7, 81.9)))


def test_engine_text_in_the_natal_reports_is_all_sinhala():
    left = []
    for pos, ls in charts(80):
        for _, name, det in jc.full_yogas(pos, ls):
            left += [(name, w) for w in english(jr.si_yoga_name(name))]
            left += [(det, w) for w in english(jr.si_text(det))]
        for y in jc.basic_yogas(pos, ls):
            key = next(k for k in jr.YOGA_SI if k.lower() in y.lower())
            left += [(y, w) for w in english(jr.YOGA_SI[key] + jr.si_yoga_why(y))]
    assert not left, left[:10]


def test_tajaka_and_porondam_lines_are_all_sinhala():
    left, moons = [], []
    for pos, ls in charts(80, seed=12):
        ty = jc.tajaka_yogas(pos, ls)
        for s in ty["general"] + ty["ithasala"] + ty["eesarpha"] + ty["nakta_yamaya"]:
            left += [(s, w) for w in english(jr.si_text(s))]
        moons.append(pos["Mo"]["lon"])
    for a, b in zip(moons, moons[1:]):
        for _, _, _, det in jc.ashtakoota(a, b)[1]:
            left += [(det, w) for w in english(jr.si_koota(det))]
    assert not left, left[:10]


def test_phrases_replace_whole_words_only():
    # "rain" must not be swapped inside "restraint"
    assert "restraint" in jr.si_text("has suffered restraint / hardship")
    assert "වර්ෂාව" not in jr.si_text("restraint")


def test_tajaka_aspects_are_named_by_their_houses():
    # sextile is the 3/11 aspect (ෂඩාෂ්ටක would mean 6/8); semi-sextile is 2/12
    assert "3/11" in jr.si_text("sextile") and "ෂඩාෂ්ටක" not in jr.si_text("sextile")
    assert "2/12" in jr.si_text("semi-sextile")


def test_a_table_header_row_repeats_on_the_next_page():
    page = '<table class="x"><tr><th>a</th><th>b</th></tr><tr><td>1</td><td>2</td></tr></table><table><tr><td>no header</td></tr></table>'
    out = jr.with_thead(page)
    assert out.count("<thead>") == 1 and '<table class="x"><thead><tr><th>a</th>' in out


def test_planets_named_either_way_come_out_in_sinhala():
    assert jr.pl_si("Mo") == jr.pl_si("Chandra") == "චන්ද්‍ර"
    assert jr.si_yoga_why("Mangal dosha indication (Kuja in house 8 from Lagna) — check cancellations") == "ලග්නයෙන් 8 වැන්නේ කුජ"
