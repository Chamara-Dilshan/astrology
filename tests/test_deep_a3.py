"""A3, the deep reading: its descriptive texts, the life-area engine and the report's order (reading first,
the astrologer's tables as an appendix)."""
import json
import os
import re
import subprocess
import sys

import pytest

import jyotisha_deep_texts as deep
import jyotisha_report as jr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = ["--name=Sample", "--date=1990-05-15", "--time=10:30", "--lat=6.9271", "--lon=79.8612", "--tz=Asia/Colombo"]
PLANETS = {"Su", "Mo", "Ma", "Me", "Ju", "Ve", "Sa", "Ra", "Ke"}
ENGLISH = re.compile(r"[A-Za-z]{3,}")   # what the QA tool calls English in a Sinhala report ("D9" is fine)


def test_texts_have_every_entry_and_no_english():
    assert len(deep.LAGNA_DEEP_SI) == len(deep.MOON_SIGN_SI) == 12 and len(deep.NAKSHATRA_SI) == 27
    for name in ("CAREER_FIELDS_SI", "STUDY_FIELDS_SI", "PARTNER_NATURE_SI"):
        assert set(getattr(deep, name)) == PLANETS, name
    for name in ("AK_SI", "PLANET_STRONG_SI", "PLANET_WEAK_SI"):
        assert set(getattr(deep, name)) == PLANETS - {"Ke"}, name
    for name in ("LAGNA_LORD_HOUSE_SI", "INCOME_FROM_SI"):
        assert set(getattr(deep, name)) == set(range(1, 13)), name
    every = [*deep.LAGNA_DEEP_SI, *deep.MOON_SIGN_SI, *deep.NAKSHATRA_SI]
    for name in ("AK_SI", "LAGNA_LORD_HOUSE_SI", "CAREER_FIELDS_SI", "STUDY_FIELDS_SI", "PARTNER_NATURE_SI",
                 "INCOME_FROM_SI", "PLANET_STRONG_SI", "PLANET_WEAK_SI"):
        every += list(getattr(deep, name).values())
    assert all(t.strip() for t in every)
    assert not [t for t in every if ENGLISH.search(t)]


@pytest.fixture(scope="module")
def chart(tmp_path_factory):
    out = tmp_path_factory.mktemp("a3") / "calc.json"
    subprocess.run([sys.executable, os.path.join(ROOT, "jyotisha_calc.py"), *SAMPLE, "--ashtakavarga", "--narayana",
                    "--yogas", f"--json={out}"], check=True, capture_output=True, cwd=ROOT)
    return json.loads(out.read_text(encoding="utf-8"))


def test_every_life_area_gets_a_level_reasons_and_advice(chart):
    for area in jr.DEEP_AREAS:
        score, reasons, lord = jr.area_reading_a3(chart, area)
        lvl, word = jr._level_a3(score, area["key"])
        assert 1 <= lvl <= 5 and word and reasons, area["key"]
        assert not [w for _, w in reasons if ENGLISH.search(w)], area["key"]
        assert not ENGLISH.search(re.sub(r"<[^>]+>", "", jr._area_advice_a3(chart, area, lvl))), area["key"]


def test_levels_rise_with_the_score_against_each_areas_average():
    assert set(jr._BASE_A3) == {a["key"] for a in jr.DEEP_AREAS}
    for key, base in jr._BASE_A3.items():
        lv = [jr._level_a3(base + x, key)[0] for x in (-3, -1, 0, 1.5, 3)]
        assert lv == sorted(lv) and lv[0] == 1 and lv[-1] == 5, key


def test_a3_reads_first_and_keeps_the_tables_as_an_appendix(tmp_path):
    page = tmp_path / "a3.html"
    r = subprocess.run([sys.executable, "jyotisha_report.py", "--report=A3", *SAMPLE, "--place=Colombo",
                        "--report-date=2026-11-28", f"--out={tmp_path / 'a3.pdf'}", f"--html={page}"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-800:]
    t = page.read_text(encoding="utf-8")
    where = [t.index(x) for x in ("1. සාරාංශය", "2. ඔබ කවුද", "3. ඔබේ ජීවිතයේ ක්ෂේත්‍ර දහය", "4. ඉදිරි අවුරුදු 20",
                                  "ඇමුණුම 1 —", "වචන කිහිපයක තේරුම")]
    assert where == sorted(where)
    assert t.count('<div class="area">') == 10
    assert "ජීවන ක්ෂේත්‍ර</h2>" not in t and "සම්මුඛ වන කවුළු" not in t     # the old thin sections are gone
