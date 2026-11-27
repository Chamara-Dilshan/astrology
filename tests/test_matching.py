"""Marriage matching must not depend on who is entered first.

Ashtakoota is asymmetric (e.g. Tara, Vashya), so the engine needs to know which chart is the
groom's. jyotisha_report passes --role through to jyotisha_calc for D1/D2/D3.
"""
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
# Moons in Ashwini (Kshatriya) and Krittika (Vaishya): Varna scores 1 one way and 0 the other,
# so entering the two in the wrong roles visibly changes the result.
MAN = dict(date="1990-03-01", time="12:00", lat="6.9271", lon="79.8612")
WOMAN = dict(date="1992-02-12", time="12:00", lat="7.2906", lon="80.6337")


def ashtakoota(main, other, role, tmp_path):
    out = tmp_path / f"{role}-{main['date']}.json"
    cmd = [sys.executable, str(ROOT / "jyotisha_calc.py"), "--name", "A", "--date", main["date"], "--time", main["time"],
           "--lat", main["lat"], "--lon", main["lon"], "--tz", "Asia/Colombo", "--match-name", "B",
           "--match-date", other["date"], "--match-time", other["time"], "--match-lat", other["lat"],
           "--match-lon", other["lon"], "--role", role, "--json", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    comp = json.loads(out.read_text(encoding="utf-8"))["compatibility"]
    return comp["ashtakoota_total"], [(k["name"], k["points"]) for k in comp["kootas"]]


def test_order_does_not_change_the_score_when_role_is_given(tmp_path):
    man_first = ashtakoota(MAN, WOMAN, "boy", tmp_path)
    woman_first = ashtakoota(WOMAN, MAN, "girl", tmp_path)
    assert man_first == woman_first


def test_without_the_role_woman_first_scores_differently(tmp_path):
    """Shows why the role matters: treating the woman as the groom changes the kootas."""
    assert ashtakoota(MAN, WOMAN, "boy", tmp_path)[1] != ashtakoota(WOMAN, MAN, "boy", tmp_path)[1]


@pytest.mark.parametrize("role, first", [("boy", "මනාලයා"), ("girl", "මනාලිය")])
def test_d1_report_passes_role_and_labels_people(tmp_path, role, first):
    """Checked in the report's HTML: the PDF text layer garbles some Sinhala conjuncts."""
    pytest.importorskip("weasyprint")
    out, page = tmp_path / f"d1-{role}.pdf", tmp_path / f"d1-{role}.html"
    main, other = (MAN, WOMAN) if role == "boy" else (WOMAN, MAN)
    r = subprocess.run([sys.executable, str(ROOT / "jyotisha_report.py"), "--report=D1", "--name=A",
                        f"--date={main['date']}", f"--time={main['time']}", f"--lat={main['lat']}", f"--lon={main['lon']}",
                        "--match-name=B", f"--match-date={other['date']}", f"--match-time={other['time']}",
                        f"--match-lat={other['lat']}", f"--match-lon={other['lon']}", f"--role={role}",
                        f"--out={out}", f"--html={page}"], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-400:]
    html = page.read_text(encoding="utf-8")
    assert f"පළමු අය ({first})" in html
    total = ashtakoota(MAN, WOMAN, "boy", tmp_path)[0]      # same couple, same score, whoever is first
    assert f"<b>{total:g} / 36</b>" in html
