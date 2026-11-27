"""Daily panchanga and Rahu kalaya (jyotisha_calc.day_panchanga, GET /panchanga)."""
import datetime as dt
import os

import pytest
from fastapi.testclient import TestClient

import jyotisha_calc as jc
from web import app as web

COLOMBO = (6.9271, 79.8612, "Asia/Colombo")
TZ = jc.ZoneInfo("Asia/Colombo")

# Sunrise and sunset in Colombo, November 2026, from timeanddate.com (fetched 2026-11-27)
TIMEANDDATE = {1: ("05:57", "17:50"), 5: ("05:58", "17:49"), 10: ("05:59", "17:49"), 15: ("06:00", "17:49"),
               20: ("06:02", "17:49"), 25: ("06:04", "17:50"), 27: ("06:05", "17:50"), 30: ("06:06", "17:51")}


def local_minutes(jd):
    t = jc.jd_to_datetime(jd).astimezone(TZ)
    return t.hour * 60 + t.minute + t.second / 60


@pytest.mark.parametrize("day", TIMEANDDATE)
def test_sunrise_and_sunset_agree_with_timeanddate(day):
    p = jc.day_panchanga(dt.date(2026, 11, day), *COLOMBO)
    for jd, ref in zip((p["sunrise"], p["sunset"]), TIMEANDDATE[day]):
        assert abs(local_minutes(jd) - (int(ref[:2]) * 60 + int(ref[3:]))) <= 1.0     # printed to the minute


def test_rahu_kalaya_is_the_weekdays_eighth_of_the_day():
    """With the day split into eight, Rahu kalaya is the 8th part on Sunday, 2nd Monday, 7th Tuesday,
    5th Wednesday, 6th Thursday, 4th Friday and 3rd Saturday: the familiar 6:00-18:00 table."""
    fixed = {0: 16.5, 1: 7.5, 2: 15.0, 3: 12.0, 4: 13.5, 5: 10.5, 6: 9.0}       # start hour, 6am sunrise
    for i in range(7):
        day = dt.date(2026, 11, 29) + dt.timedelta(days=i)                     # Sunday 29 Nov onwards
        p = jc.day_panchanga(day, *COLOMBO)
        eighth = (p["sunset"] - p["sunrise"]) / 8
        for key, parts in (("rahu", jc.RAHU_PART), ("yamaganda", jc.YAMAGANDA_PART), ("gulika", jc.GULIKA_PART)):
            start, end = p[key]
            assert start == pytest.approx(p["sunrise"] + (parts[p["weekday"]] - 1) * eighth)
            assert end - start == pytest.approx(eighth)
        assert p["weekday"] == (day.weekday() + 1) % 7
        # Colombo's sunrise is within half an hour of 6:00, so the start is close to the fixed table
        assert abs(local_minutes(p["rahu"][0]) - fixed[p["weekday"]] * 60) < 25


# Day Rahu kalaya for Colombo as published by Sri Lankan almanac sites (fetched 2026-11-27):
# litha.lk and porondam.lk (27 Nov), suhadaastrology.lk (27 Nov - 3 Dec, "eight equal periods from sunrise
# to sunset"). They differ among themselves by up to 2 minutes; ours must be within 2 of each.
PUBLISHED = {
    (11, 27): [("10:29", "11:58"), ("10:29", "11:57"), ("10:31", "11:59")],
    (11, 28): [("09:01", "10:29"), ("09:03", "10:31")],
    (11, 29): [("16:24", "17:52")], (11, 30): [("07:36", "09:04")], (12, 1): [("14:57", "16:25")],
    (12, 2): [("12:01", "13:29")], (12, 3): [("13:29", "14:57")],
}


@pytest.mark.parametrize("md", PUBLISHED)
def test_rahu_kalaya_agrees_with_sri_lankan_almanacs(md):
    p = jc.day_panchanga(dt.date(2026, *md), *COLOMBO)
    for start, end in PUBLISHED[md]:
        for jd, ref in zip(p["rahu"], (start, end)):
            assert abs(local_minutes(jd) - (int(ref[:2]) * 60 + int(ref[3:]))) <= 2, (md, ref)


def test_end_times_are_when_the_element_changes():
    p = jc.day_panchanga(dt.date(2026, 11, 27), *COLOMBO)
    minute = 1 / 1440
    for key, f, size in (("tithi_end", lambda pos: jc.norm(pos["Mo"]["lon"] - pos["Su"]["lon"]) // 12, None),
                         ("nakshatra_end", lambda pos: pos["Mo"]["lon"] // (360 / 27), None),
                         ("karana_end", lambda pos: jc.norm(pos["Mo"]["lon"] - pos["Su"]["lon"]) // 6, None)):
        end = p[key]
        assert p["sunrise"] < end < p["sunrise"] + 1.2
        before, after = f(jc.compute_positions(end - minute)[0]), f(jc.compute_positions(end + minute)[0])
        assert after == (before + 1) % (30 if key == "tithi_end" else 27 if key == "nakshatra_end" else 60)


# ---------------------------------------------------------------- the page

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(web, "PANCHANGA_PAGE", True)
    return TestClient(web.app)


def test_page_is_on_by_default_and_can_be_switched_off(monkeypatch):
    assert web.PANCHANGA_PAGE == (os.environ.get("PANCHANGA_PAGE", "1") == "1")
    monkeypatch.setattr(web, "PANCHANGA_PAGE", False)
    c = TestClient(web.app)
    assert c.get("/panchanga").status_code == 404
    assert 'href="/panchanga"' not in c.get("/").text


def test_page(client):
    r = client.get("/panchanga", params={"date": "2026-11-27", "town": "Kandy"})
    assert r.status_code == 200
    assert "{{" not in r.text
    assert "script-src 'none'" in r.headers["content-security-policy"]
    assert r.headers["cache-control"] == "public, max-age=86400"
    assert "මහනුවර · Kandy" in r.text and "2026-11-27 · සිකුරාදා" in r.text
    assert r.text.count("<tr") >= 9 + 7                                    # panchanga rows + the week
    assert 'href="/panchanga"' in client.get("/").text                     # linked from the form when on


def test_today_is_not_cached(client):
    r = client.get("/panchanga")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-cache"


@pytest.mark.parametrize("params", [{"town": "Atlantis"}, {"date": "27-11-2026"}, {"date": "1850-01-01"},
                                    {"date": "2026-02-30"}, {"town": "<script>"}])
def test_bad_input_is_refused(client, params):
    assert client.get("/panchanga", params=params).status_code == 400


def test_clock_format():
    day = dt.date(2026, 11, 27)
    jd = lambda h, m, d=27: jc.to_jd_ut(dt.datetime(2026, 11, d, h, m), "Asia/Colombo")[0]  # noqa: E731
    assert web._clock(jd(10, 30), day) == "පෙ.ව. 10.30"
    assert web._clock(jd(12, 0), day) == "ප.ව. 12.00"
    assert web._clock(jd(0, 5, 28), day) == "හෙට පෙ.ව. 12.05"
    assert web._span((jd(10, 30), jd(11, 58)), day) == "පෙ.ව. 10.30 – 11.58"
    assert web._span((jd(11, 59), jd(13, 26)), day) == "පෙ.ව. 11.59 – ප.ව. 1.26"
