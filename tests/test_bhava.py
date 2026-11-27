"""Sripati bhava chart and the true-node option (jyotisha_calc.sripati_bhavas, --node).

Sripati is checked against its definition, computed independently here: bhava madhyas are the
Porphyry cusps (Lagna, MC, trisected quadrants) and the sandhis are the midpoints between them.
"""
import datetime as dt
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import jyotisha_calc as jc  # noqa: E402
import swisseph as swe  # noqa: E402

CHARTS = [  # (local datetime, tz, lat, lon): Colombo, Jaffna, Kandy, London (high latitude)
    (dt.datetime(1990, 5, 15, 10, 30), "Asia/Colombo", 6.9271, 79.8612),
    (dt.datetime(1975, 1, 3, 23, 50), "Asia/Colombo", 9.6615, 80.0255),
    (dt.datetime(2004, 9, 21, 5, 5), "Asia/Colombo", 7.2906, 80.6337),
    (dt.datetime(1988, 12, 1, 14, 0), "Europe/London", 51.5074, -0.1278),
]


def norm(x):
    return x % 360


def angle(a, b):
    return abs((a - b + 180) % 360 - 180)


def porphyry_definition(jd, lat, lon):
    """Madhyas from the Lagna and MC by trisecting each quadrant, written out by hand."""
    swe.set_sid_mode(jc.SID_MODE)
    _, ascmc = swe.houses_ex(jd, lat, lon, b"O", swe.FLG_SIDEREAL)
    asc, mc = ascmc[0], ascmc[1]
    ic, dsc = norm(mc + 180), norm(asc + 180)
    madhya = []
    for start, end in ((asc, ic), (ic, dsc), (dsc, mc), (mc, asc)):   # houses 1-3, 4-6, 7-9, 10-12
        span = norm(end - start)
        madhya += [norm(start + span * k / 3) for k in range(3)]
    sandhi = [norm(madhya[i - 1] + norm(madhya[i] - madhya[i - 1]) / 2) for i in range(12)]
    return madhya, sandhi


@pytest.mark.parametrize("when, tz, lat, lon", CHARTS)
def test_sripati_matches_its_definition(when, tz, lat, lon):
    jd, _ = jc.to_jd_ut(when, tz)
    pos, _ = jc.compute_positions(jd)
    s = jc.sripati_bhavas(jd, lat, lon, pos)
    madhya, sandhi = porphyry_definition(jd, lat, lon)
    assert max(angle(a, b) for a, b in zip(s["madhya"], madhya)) < 1e-3
    assert max(angle(a, b) for a, b in zip(s["sandhi"], sandhi)) < 1e-3
    assert angle(s["madhya"][0], jc.compute_lagna(jd, lat, lon)) < 1e-3     # bhava 1 madhya is the Lagna


@pytest.mark.parametrize("when, tz, lat, lon", CHARTS)
def test_every_planet_lies_inside_its_bhava(when, tz, lat, lon):
    jd, _ = jc.to_jd_ut(when, tz)
    pos, _ = jc.compute_positions(jd)
    s = jc.sripati_bhavas(jd, lat, lon, pos)
    for code, n in s["planet_bhava"].items():
        start, end = s["sandhi"][n - 1], s["sandhi"][n % 12]
        assert norm(pos[code]["lon"] - start) < norm(end - start), (code, n)


def test_true_node_option(tmp_path):
    def rahu(node):
        out = tmp_path / f"{node}.json"
        subprocess.run([sys.executable, str(ROOT / "jyotisha_calc.py"), "--name", "A", "--date", "1990-05-15",
                        "--time", "10:30", "--lat", "6.9271", "--lon", "79.8612", "--tz", "Asia/Colombo",
                        "--node", node, "--json", str(out)], check=True, capture_output=True)
        d = json.loads(out.read_text(encoding="utf-8"))
        return d["node"], d["planets"]["Ra"]["lon"], d["planets"]["Ke"]["lon"]
    mean, true = rahu("mean"), rahu("true")
    assert (mean[0], true[0]) == ("mean", "true")
    assert 0 < angle(mean[1], true[1]) < 2            # the true node oscillates within ~1.7° of the mean
    assert angle(true[2], norm(true[1] + 180)) < 1e-6  # Ketu stays opposite Rahu


def test_a2_report_shows_the_bhava_chart(tmp_path):
    pytest.importorskip("weasyprint")
    page = tmp_path / "a2.html"
    r = subprocess.run([sys.executable, str(ROOT / "jyotisha_report.py"), "--report=A2", "--name=S", "--date=1990-05-15",
                        "--time=10:30", "--lat=6.9271", "--lon=79.8612", f"--out={tmp_path / 'a2.pdf'}", f"--html={page}"],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-400:]
    h = page.read_text(encoding="utf-8")
    assert "ශ්‍රීපති භාව කේන්දරය" in h
    assert "(6 → 7)" in h and "(8 → 9)" in h        # Moon and Mars change house in this chart


def test_default_is_still_the_mean_node():
    assert jc.NODE_KIND == "mean"
    assert dict(jc.PLANETS)["Ra"] == swe.MEAN_NODE
