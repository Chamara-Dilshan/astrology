"""KP (Krishnamurti Paddhati): sub-lord table, lords of a longitude, the KP chart.

The star/sub/sub-sub lords were also cross-checked once against PyJHora 5.0.6 (utils.kp_lords_for_longitude)
on 798 longitudes, including both sides of every sub boundary: no differences.
"""
import datetime as dt
import pathlib
import subprocess
import sys

import pytest
import swisseph as swe

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import jyotisha_calc as jc  # noqa: E402


def deg(d, m=0, s=0):
    return d + m / 60 + s / 3600


def test_the_kp_table_has_249_divisions():
    t = jc.kp_sub_table()
    assert len(t) == 249                                           # 243 subs + 6 split by a sign boundary
    assert t[0][0] == 0 and t[-1][1] == 360
    assert all(abs(a[1] - b[0]) < 1e-9 for a, b in zip(t, t[1:]))   # contiguous
    # the start of the published table (Aries, Ashwini) and its very end (Pisces, Revati)
    aries = [(0, "Ke"), (deg(0, 46, 40), "Ve"), (deg(3), "Su"), (deg(3, 40), "Mo"), (deg(4, 46, 40), "Ma"),
             (deg(5, 33, 20), "Ra"), (deg(7, 33, 20), "Ju"), (deg(9, 20), "Sa"), (deg(11, 26, 40), "Me")]
    for row, (start, sub) in zip(t, aries):
        assert row[0] == pytest.approx(start) and row[2:] == ("Ma", "Ke", sub)
    assert t[-1][0] == pytest.approx(330 + deg(27, 53, 20)) and t[-1][2:] == ("Ju", "Me", "Sa")
    # sign boundaries that cut a sub in two: six of them
    starts = {round(r[0], 6) for r in t}
    assert sum(1 for s in range(1, 12) if any(abs(r[0] - 30 * s) < 1e-6 for r in t)) == 11
    assert len(starts) == 249


@pytest.mark.parametrize("lon, lords", [
    (0.0, ["Ma", "Ke", "Ke", "Ke"]),
    (deg(13, 20) + 1e-6, ["Ma", "Ve", "Ve", "Ve"]),               # Bharani begins with Venus' own sub
    (30 + deg(0, 29, 9), ["Ve", "Su", "Ra", "Ke"]),                # Sun of the Colombo 1990 chart
    (359.999999, ["Ju", "Me", "Sa", "Ju"]),                       # Saturn's sub-subs start from Saturn
])
def test_lords_of_a_longitude(lon, lords):
    assert jc.kp_lords(lon) == lords


def test_kp_numbers():
    assert jc.kp_number(0.0) == 1 and jc.kp_number(359.99) == 249
    assert jc.kp_number(deg(0, 46, 40) + 1e-6) == 2


def test_kp_chart():
    jd, _ = jc.to_jd_ut(dt.datetime(1990, 5, 15, 10, 30), "Asia/Colombo")
    lat, lon = 6.9271, 79.8612
    swe.set_sid_mode(jc.SID_MODE)
    lahiri = swe.get_ayanamsa_ut(jd)
    kp = jc.kp_chart(jd, lat, lon, "Asia/Colombo")
    assert jc.SID_MODE == swe.SIDM_LAHIRI and swe.get_ayanamsa_ut(jd) == lahiri     # setting restored
    assert 0.05 < lahiri - kp["ayanamsa"] < 0.15                       # KP ayanamsa is ~6' less than Lahiri
    swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)
    try:
        placidus = swe.houses_ex(jd, lat, lon, b"P", swe.FLG_SIDEREAL)[0]
    finally:
        swe.set_sid_mode(jc.SID_MODE)
    assert [c["lon"] for c in kp["cusps"]] == [round(jc.norm(x), 4) for x in placidus[:12]]
    cusps = [c["lon"] for c in kp["cusps"]]
    for p, v in kp["planets"].items():                                # each planet lies in its house
        h = v["house"]
        assert jc.norm(v["lon"] - cusps[h - 1]) < jc.norm(cusps[h % 12] - cusps[h - 1]) + 1e-3
        assert v["lords"] == jc.kp_lords(v["lon"])
    star = {p: v["lords"][1] for p, v in kp["planets"].items()}
    for h, s in kp["significators"].items():
        occupants = [p for p, v in kp["planets"].items() if v["house"] == h]
        owner = jc.SIGN_LORD[jc.sign_of(cusps[h - 1])]
        assert s == {"L1": [p for p in star if star[p] in occupants], "L2": occupants,
                     "L3": [p for p in star if star[p] == owner], "L4": [owner]}
    assert kp["ruling_planets"]["day_lord"] == "Ma"                     # 15 May 1990 was a Tuesday
    assert kp["ruling_planets"]["moon_star_lord"] == kp["planets"]["Mo"]["lords"][1]


def test_cli_and_a3(tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "jyotisha_calc.py"), "--name", "A", "--date", "1990-05-15", "--time",
                        "10:30", "--lat", "6.9271", "--lon", "79.8612", "--tz", "Asia/Colombo", "--kp"],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0 and "KP CHART" in r.stdout and "RULING PLANETS" in r.stdout
    pytest.importorskip("weasyprint")
    page = tmp_path / "a3.html"
    r = subprocess.run([sys.executable, str(ROOT / "jyotisha_report.py"), "--report=A3", "--name=S", "--date=1990-05-15",
                        "--time=10:30", "--lat=6.9271", "--lon=79.8612", f"--out={tmp_path / 'a3.pdf'}", f"--html={page}"],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-400:]
    h = page.read_text(encoding="utf-8")
    assert "KP — කෘෂ්ණමූර්ති පද්ධතිය" in h and "<th>උප අධිපති</th>" in h
