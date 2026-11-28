"""The Sinhala reports must not show the engine's English. Found 2026-11-27: yoga names, Tajaka lines,
porondam details, the muhurta chart and most Prashna (Shatpanchasika) stanzas came through in English
in A1-A3, B, C1/C2, D1/D2, M1 and P1/P2."""
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


# Shatpanchasika lines too rare to count on in random charts (the engine's exact wording)
RARE_RULES = ["Kuja & Shani in 9th", "Surya & Chandra in 4th", "Guru/Shukra in 2nd or 3rd",
              "bright (full) Chandra in lagna aspected by Guru/Shukra", "movable lagna in a movable navamsa beyond the 5th",
              "Shani with malefics in 9th, no benefic aspect", "Chandra in lagna in a watery sign",
              "no planet in kendras; lagna lord Shani", "fixed lagna with Guru/Shani", "movable lagna with Surya/Guru",
              "Chandra in Lagna", "Chandra in 10th", "navamsa lord of lagna is in lagna", "lagna: fixed sign, vargottama",
              "Rahu in 8th (no benefic association)", "Guru in 8th with benefic Shukr/Budha", "7th lord Kuja retrograde",
              "first occupied sign from Lagna is 3th (Meena, Shani) retrograde", "Sirshodaya lagna Simha with benefic Guru, benefic aspect"]
RARE_VERDICTS = ["opponent halts permanently (retrograde Shani)", "query about -: still in the first place; caution",
                 "opponent withdraws after a heavy defeat", "traveller suffering ill-health (recommend checking on them)",
                 "return within 3 days (retrograde rule, Rao)", "safe return with wealth & honour", "SPEEDY recovery"]


def shat_lines(n=60, seed=13):
    rules, verdicts = set(RARE_RULES), set(RARE_VERDICTS)
    rnd = random.Random(seed)
    for pos, ls in charts(n, seed):
        llon = ls * 30 + rnd.uniform(0, 30)   # the degree matters (navamsa, drekkana)
        for topic in jc.SHAT_TOPICS:
            for _, rule, verdict in jc.shatpanchasika(pos, llon, topic):
                rules.add(rule)
                verdicts.add(verdict)
    return rules, verdicts


def test_prashna_stanzas_are_all_sinhala():
    rules, verdicts = shat_lines()
    left = [(r, w) for r in rules for w in english(jr.si_shat_rule(r))]
    left += [(v, w) for v in verdicts for w in english(jr.si_shat_verdict(v)[0])]
    assert not left, left[:10]
    # and each line was translated as a sentence, not word by word
    assert [r for r in rules if not any(rx.fullmatch(r) for rx, _, _ in jr.SHAT_RULE_SI)] == []


def test_every_prashna_pattern_is_used():
    rules, verdicts = shat_lines()
    unused = [rx.pattern for rx, _, _ in jr.SHAT_RULE_SI if not any(rx.fullmatch(r) for r in rules)]
    unused += [rx.pattern for rx, *_ in jr.SHAT_VERDICT_RX if not any(rx.fullmatch(v) for v in verdicts)]
    assert not unused, unused


def test_prashna_verdicts_carry_their_tone():
    assert jr.si_shat_verdict("VICTORY to the querent")[1] == 1
    assert jr.si_shat_verdict("they will fight")[1] == -1
    assert jr.si_shat_verdict("opponent arrives within ~3 days") == ("දින 3ක් පමණ ඇතුළත ප්‍රතිවාදියා පැමිණේ", 0)


def test_muhurta_rows_are_read_by_name_not_by_gaps():
    """"Mangala" is exactly as wide as the engine's vara column and "Uttara Bhadrapada" overflows the nakshatra
    one, so a single space can separate two columns: Tuesday windows once came out as "Mangala Magha" in English."""
    text = ("TOP 3 WINDOWS (score = soft points; higher is better):\n"
            "  date       start-end    lagna      tithi                  vara    nakshatra        hora         score  notes\n"
            "  2026-12-01 07:17-09:10  Dhanu      Krishna Ashtami        Mangala Magha            Surya/Shukr      3  a\n"
            "  2026-12-02 07:17-09:10  Dhanu      Krishna Navami         Budha   Uttara Bhadrapada Budha           2  b\n"
            "  2026-12-04 07:05-09:13  Dhanu      Krishna Ekadashi       Shukra  Hasta            Budha/Chand/Shani     5  c\n")
    rows, _, _ = jr.parse_muhurta_output(text)
    assert [(r["vara"], r["nak"], r["hora"], r["score"]) for r in rows] == [
        ("Mangala", "Magha", "Surya/Shukr", 3), ("Budha", "Uttara Bhadrapada", "Budha", 2),
        ("Shukra", "Hasta", "Budha/Chand/Shani", 5)]


def test_utc_offsets_read_as_plus_or_minus_hours():
    """Births abroad are possible now: west of Greenwich Python writes -5 h as '-1 day, 19:00:00'."""
    from datetime import timedelta
    assert [jr.utc_offset_txt(str(timedelta(hours=h))) for h in (5.5, 6, 0, -5, -3.5, 9.75)] == \
        ["+5:30", "+6:00", "+0:00", "-5:00", "-3:30", "+9:45"]


def test_coordinates_say_north_south_east_west():
    assert jr.latlon_txt(6.9271, 79.8612) == "6.9271° N, 79.8612° E"
    assert jr.latlon_txt(-33.8688, 151.2093) == "33.8688° S, 151.2093° E"
    assert jr.latlon_txt(40.7128, -74.006) == "40.7128° N, 74.0060° W"


def test_a_moon_only_ithasala_with_the_matter_counts_as_kamboola():
    """P1: the Moon (the one who asks) in ithasala with one of the matter's planets is a weaker yes; with the lagna
    lord alone it is not (that links the asker only to themself). Mesha lagna, matter 10: Makara's lord Shani,
    karaka Surya, Rajya saham lord Surya; Kuja is only the lagna lord."""
    d = {"lagna": {"sign_idx": 0}, "matter_lines": [
        "  Rajya (position) saham at Simha 05°00′ (house 5), lord Surya",
        "  Chandra ithasala (vartamana) with Kuja — Kamboola support (29.2)",
        "  Chandra ithasala (bhavishya) with Shani — Kamboola support (29.2)"]}
    assert jr.p1_kamboola(d, 10) == ["Sa"]
    assert jr.p1_kamboola(d, None) == []
    d["matter_lines"] = d["matter_lines"][:2]
    assert jr.p1_kamboola(d, 10) == []
