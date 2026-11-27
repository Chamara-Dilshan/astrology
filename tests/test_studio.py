"""Studio mode (STUDIO=1, "Jyothisha Studio.bat"): the site on the owner's computer, for the paid reports.
Every report is made, with the astrologer's notes; it answers only this computer; the public site is unchanged."""
import json
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient

from web import app as web

BIRTH = dict(name="Sample", birth_date="1990-05-15", birth_time="10:30", place="Colombo",
             lat="6.9271", lon="79.8612", tz="Asia/Colombo", time_exact="yes")


@pytest.fixture
def seen(monkeypatch):
    calls = []

    def fake_render(args, workdir, files=None):
        calls.append((args, files or {}))
        return b"%PDF-1.7 fake"
    monkeypatch.setattr(web, "_render", fake_render)
    web._limiter.reset()
    return calls


@pytest.fixture
def studio(monkeypatch):
    monkeypatch.setattr(web, "STUDIO", True)
    monkeypatch.setattr(web, "REPORTS", dict(web.ALL_REPORTS))
    return TestClient(web.app, client=("127.0.0.1", 50000))


def test_the_public_site_has_no_studio(seen, monkeypatch):
    monkeypatch.setattr(web, "REPORTS", dict(web.ALL_REPORTS))
    c = TestClient(web.app)
    page = c.get("/").text
    assert 'id="orderpaste"' not in page and 'name="note_summary"' not in page and '"studio": false' in page
    r = c.post("/report", data={**BIRTH, "report": "A1", "note_summary": "ignored"})
    assert r.status_code == 200 and "X-Notes-Check" not in r.headers
    assert not any(a.startswith("--notes") for a in seen[0][0])       # notes are a studio thing only


def test_studio_answers_only_this_computer(monkeypatch):
    monkeypatch.setattr(web, "STUDIO", True)
    assert TestClient(web.app, client=("203.0.113.9", 50000)).get("/").status_code == 403
    assert TestClient(web.app, client=("127.0.0.1", 50000)).get("/").status_code == 200
    assert TestClient(web.app, client=("::1", 50000)).get("/healthz").status_code == 200


def test_studio_page_has_the_order_box_and_note_boxes(studio):
    page = studio.get("/").text
    assert 'id="orderpaste"' in page and 'id="fillorder"' in page and '"studio": true' in page
    for key, _ in web.NOTE_SECTIONS:
        assert f'name="note_{key}"' in page
    assert "Order on Messenger" not in page                       # no ordering from yourself


def test_studio_makes_a_paid_report_with_the_notes(studio, seen):
    r = studio.post("/report", data={**BIRTH, "report": "B3", "note_summary": "පළමු ඡේදය.\r\n\r\nදෙවැන්න.",
                                     "note_dasha": "  ", "note_remedies": "ගුරු දශාව"})
    assert r.status_code == 200
    args, files = seen[0]
    assert "--report=B3" in args and "--notes={workdir}/notes.json" in args
    assert json.loads(files["notes.json"]) == {"summary": "පළමු ඡේදය.\n\nදෙවැන්න.", "remedies": "ගුරු දශාව"}
    assert json.loads(unquote(r.headers["X-Notes-Check"])) == []      # nothing printed: no disagreement


def test_studio_keeps_only_the_notes_the_report_prints(studio, seen):
    r = studio.post("/report", data={**BIRTH, "report": "M1", "task": "wedding", "m_from": "2026-12-05",
                                     "m_to": "2026-12-31", "m_hours": "6-21",
                                     "note_summary": "දෙසැම්බර් 11", "note_dosha": "not printed by M1"})
    assert r.status_code == 200
    assert json.loads(seen[0][1]["notes.json"]) == {"summary": "දෙසැම්බර් 11"}


def test_studio_page_knows_each_reports_note_boxes(studio):
    page = studio.get("/").text
    data = json.loads(page.split('id="page-data">', 1)[1].split("</script>", 1)[0])
    notes = {e["code"]: e["notes"] for e in data["catalog"]}
    assert notes["D3"] == ["summary"] and notes["G"] == [] and "areas" in notes["A2"]
    for key, _ in web.NOTE_SECTIONS:
        assert f'data-note="{key}"' in page


def test_note_keys_match_what_each_report_prints():
    """NOTE_KEYS (the Studio's boxes per report) against the note_block calls in each build_* function."""
    import inspect
    import re
    from web import catalog
    jr = web.jr
    builders = {"A1": [jr.build_a1], "A2": [jr.build_a2], "A3": [jr.build_a2], "C1": [jr.build_c1],
                "C2": [jr.build_c2, jr.build_c1], "C3": [jr.build_c3], "C4": [jr.build_c4], "C6": [jr.build_c6],
                "N": [jr.build_n], "E1": [jr.build_e1], "D1": [jr.build_d1], "D2": [jr.build_d2],
                "D3": [jr.build_d3], "P1": [jr.build_p1], "P2": [jr.build_p1], "M1": [jr.build_m1],
                "G": [jr.build_g], **{f"B{i}": [jr.build_b] for i in range(1, 9)}}
    # a box that only fills in when another is empty is left out of the Studio, on purpose
    fallback = {"A2": {"lagna2"}, "A3": {"lagna2"}, "C2": {"gochara"}, "D1": {"yogas"}}
    sections = {k for k, _ in web.NOTE_SECTIONS}
    assert set(jr.NOTE_KEYS) == set(catalog.REPORTS) == set(builders)
    for code, fns in builders.items():
        src = "".join(inspect.getsource(f) for f in fns)
        printed = set(re.findall(r'note_block\(notes, "(\w+)"', src))
        assert set(jr.NOTE_KEYS[code]) <= sections, code
        assert set(jr.NOTE_KEYS[code]) == printed - fallback.get(code, set()), code


def test_studio_without_notes_sends_none(studio, seen):
    r = studio.post("/report", data={**BIRTH, "report": "D1", "role": "boy", "p_name": "Sample Two",
                                     "p_date": "1992-08-20", "p_time": "07:45", "p_place": "Kandy",
                                     "p_lat": "7.2906", "p_lon": "80.6337", "p_tz": "Asia/Colombo"})
    assert r.status_code == 200 and "X-Notes-Check" not in r.headers
    assert not any(a.startswith("--notes") for a in seen[0][0])


@pytest.mark.parametrize("note,detail", [("x" * (web.NOTE_MAX + 1), "at most"), ("bad\x00byte", "aren't allowed")])
def test_studio_checks_the_notes(studio, seen, note, detail):
    r = studio.post("/report", data={**BIRTH, "report": "A1", "note_lagna": note})
    assert r.status_code == 400 and detail in r.json()["detail"] and not seen


def test_notes_check_is_read_from_the_report_output():
    printed = ("notes cross-check heading\n\n!! සටහන් සහ ගණනය අතර නොගැලපීම් (notes cross-check):\n"
               "   lagna: සටහනේ මේෂ, කේන්දරයේ වෘශ්චික\n   (නිවැරදි කර නැවත ධාවනය කරන්න, නැතහොත් --no-check)\n\nPDF written")
    assert web._notes_check(printed) == ["lagna: සටහනේ මේෂ, කේන්දරයේ වෘශ්චික"]
    assert web._notes_check("notes cross-check: ගැලපේ ✓\nPDF written") == []
