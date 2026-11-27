"""The NASA/JPL comparison shown on the website's accuracy page must stay true.

docs/accuracy_jpl.json is made by tools/compare_jpl.py (needs internet). These tests are offline:
they recompute our side for the saved dates, so a change to the engine or its ephemeris files
that moves any planet is caught, and they check the published agreement.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "docs" / "accuracy_jpl.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(ROOT / "tools"))
import compare_jpl as cj  # noqa: E402


def test_our_positions_have_not_drifted():
    for r in DATA["rows"]:
        now = cj.ours(cj.BODIES[r["body"]][1], cj.jd_ut(r["date_ut"]))
        assert abs(cj.diff_arcsec(now, r["ours"])) < 0.01, r


def test_agreement_with_nasa_up_to_today_is_under_half_an_arcsecond():
    past = [r for r in DATA["rows"] if r["date_ut"][:4] <= "2026"]
    assert len(past) >= 40
    assert max(abs(r["diff_arcsec"]) for r in past) < 0.5
    assert DATA["max_abs_diff_arcsec_to_today"] < 0.5


def test_future_differences_are_explained_and_small():
    assert "Delta-T" in DATA["note"]
    assert DATA["max_abs_diff_arcsec"] < 20          # 2100 Moon, from Delta-T forecasts only
    assert "DE441" in DATA["reference"]
