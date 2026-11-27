"""Tests for the web front-end (web/app.py).

Most tests replace the PDF renderer with a stub that records its arguments, so they run in
milliseconds; test_real_report_* runs the actual pipeline end to end.

    pytest -q
"""
import asyncio
import json
import re

import pytest
from fastapi.testclient import TestClient

from web import app as web

GOOD = dict(name="Sample", birth_date="1990-05-15", birth_time="10:30", place="Colombo",
            lat="6.9271", lon="79.8612", tz="Asia/Colombo", report="G")


@pytest.fixture(autouse=True)
def fresh_limits(monkeypatch):
    """Every test starts with empty rate-limit windows, generous limits, all report types on,
    and no contact line or order link."""
    web._limiter.reset()
    web._search_limiter.reset()
    web._panchanga_limiter.reset()
    monkeypatch.setattr(web, "RATE_PER_IP", 1000)
    monkeypatch.setattr(web, "RATE_TOTAL", 1000)
    monkeypatch.setattr(web, "REPORTS", dict(web.ALL_REPORTS))
    monkeypatch.setattr(web, "BRAND_CONTACT", "")
    monkeypatch.setattr(web, "ORDER_URL", "")


@pytest.fixture
def calls(monkeypatch):
    """Stub the renderer: record the CLI arguments, return a tiny fake PDF."""
    class Calls(list):
        """The argument lists, plus .files: the extra files each call would write."""

    seen = Calls()
    seen.files = []

    def fake_render(args, workdir, files=None):
        seen.append(args)
        seen.files.append(files or {})
        return b"%PDF-1.7 fake"

    monkeypatch.setattr(web, "_render", fake_render)
    return seen


@pytest.fixture
def client():
    return TestClient(web.app)


def post(client, headers=None, **changes):
    return client.post("/report", data={**GOOD, **changes}, headers=headers or {})


def arg(args, flag):
    """Value of --flag=value in the report's argument list."""
    return next(a.split("=", 1)[1] for a in args if a.startswith(flag + "="))


# ---------------------------------------------------------------- pages

def test_index_has_form_and_places(client):
    r = client.get("/")
    assert r.status_code == 200
    for code in web.REPORTS:
        assert f'value="{code}"' in r.text
    assert json.dumps(web.placesearch.DEFAULT) in r.text                                   # default place
    assert web.placesearch.DEFAULT["name"] == "Colombo" and web.placesearch.DEFAULT["lat"] == 6.9271
    assert 'role="combobox"' in r.text and "geonames.org" in r.text                          # search + credit
    assert "{{" not in r.text            # every template placeholder was filled


def test_no_page_links_to_the_source_code(client):
    """The owner's choice (2026-11-27): the public pages don't link to the code repository."""
    for path in ("/", "/accuracy", "/panchanga"):
        page = client.get(path).text
        assert "github.com" not in page and "Source code" not in page and "{{" not in page, path


@pytest.mark.parametrize("path,media", list(web.STATIC_FILES.items()))
def test_logo_files_are_served(client, path, media):
    r = client.get(path)
    assert r.status_code == 200 and r.headers["content-type"].startswith(media) and len(r.content) > 100
    assert "max-age" in r.headers["cache-control"] and r.headers["x-content-type-options"] == "nosniff"
    if path.endswith(".svg"):
        assert "default-src 'none'" in r.headers["content-security-policy"] and b"<script" not in r.content


def test_every_page_has_the_logo_and_the_home_page_a_share_preview(client):
    for path in ("/", "/accuracy", "/panchanga"):
        page = client.get(path).text
        assert 'rel="icon" href="/favicon.svg"' in page and 'rel="apple-touch-icon"' in page, path
    home = client.get("/").text
    # absolute, as Facebook needs; the file is renamed for each new picture (no ?query: WhatsApp)
    assert f'property="og:image" content="{web.SITE_URL}/og-image-2.png"' in home
    assert 'property="og:image:type" content="image/png"' in home


@pytest.mark.parametrize("path", ["/", "/og-image-2.png", "/favicon.ico", "/healthz"])
def test_head_is_answered_like_get(client, path):
    """Link-preview fetchers may ask HEAD first; it was refused with 405."""
    get, head = client.get(path), client.head(path)
    assert head.status_code == 200 == get.status_code and head.content == b""
    assert head.headers["content-type"] == get.headers["content-type"]
    assert web.SITE_URL.startswith("https://")


def test_accuracy_page(client):
    r = client.get("/accuracy")
    assert r.status_code == 200
    page = r.text
    assert "{{" not in page
    assert "NASA" in page and "DE441" in page
    assert page.count("<li>") >= 42 + 4                     # every selftest check, plus the 4 facts
    assert "Ashtakavarga totals = 337" in page
    data = json.loads((web.ROOT / "docs" / "accuracy_jpl.json").read_text(encoding="utf-8"))
    assert f'{data["max_abs_diff_arcsec_to_today"]:.2f}″' in page
    assert "script-src 'none'" in r.headers["content-security-policy"]
    assert 'href="/accuracy"' in client.get("/").text        # linked from the form page


def test_page_script_is_valid_javascript(client, tmp_path):
    """A syntax error would silently disable the whole form, and nothing server-side would notice."""
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("node not installed")
    script = re.search(r"<script>(.*?)</script>", client.get("/").text, re.S).group(1)
    path = tmp_path / "page.js"
    path.write_text(script, encoding="utf-8")
    r = subprocess.run([node, "--check", str(path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_healthz(client, monkeypatch):
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    assert client.get("/healthz").json() == {"ok": True, "version": "dev"}
    monkeypatch.setenv("RENDER_GIT_COMMIT", "67b2668a1b2c3d4e")
    assert client.get("/healthz").json()["version"] == "67b2668"


# ---------------------------------------------------------------- input validation

@pytest.mark.parametrize("field, value, message", [
    ("birth_time", "25:00", "Time must be HH:MM"),
    ("birth_time", "7:5", "Time must be HH:MM"),
    ("birth_date", "1990-13-01", "Date must be YYYY-MM-DD"),
    ("birth_date", "1700-01-01", "between 1800 and 2399"),
    ("report", "ZZ", "Unknown report type"),
    ("tz", "Mars/Base", "Unknown time zone"),
    ("lat", "95", "Latitude must be within"),
    ("lon", "-181", "Latitude must be within"),
    ("birth_date", "19900515", "Date must be YYYY-MM-DD"),
    ("name", "x" * 61, "Name must be 1–60 characters"),
    ("name", "bad\x07name", "Name contains characters that aren't allowed"),
    ("name", "<a rel=attachment href=file:///etc/passwd>x</a>", "Name contains characters"),
    ("place", "<img src=http://169.254.169.254/>", "Place contains characters"),
    ("place", "y" * 61, "Place must be 0–60 characters"),
])
def test_rejects_bad_input(client, calls, field, value, message):
    r = post(client, **{field: value})
    assert r.status_code == 400
    assert message in r.json()["detail"]
    assert calls == []                   # nothing was rendered


def test_missing_field_is_422(client, calls):
    data = {k: v for k, v in GOOD.items() if k != "name"}
    assert client.post("/report", data=data).status_code == 422
    assert calls == []


# ---------------------------------------------------------------- what reaches the report

def test_passes_form_values_to_report(client, calls):
    r = post(client, name="  නිමාලි   සේනානායක ", place="Haputale", lat="6.76561", lon="80.951",
             time_exact="approx", report="A1")
    assert r.status_code == 200
    a = calls[0]
    assert arg(a, "--name") == "නිමාලි සේනානායක"        # whitespace collapsed
    assert arg(a, "--place") == "Haputale"
    assert (arg(a, "--lat"), arg(a, "--lon")) == ("6.7656", "80.9510")
    assert arg(a, "--time-exact") == "approx"
    assert arg(a, "--report") == "A1"


def test_time_exact_defaults_to_yes_anything_else_means_approx(client, calls):
    post(client)
    post(client, time_exact="maybe")
    assert [arg(a, "--time-exact") for a in calls] == ["yes", "approx"]


def test_pdf_response_headers(client, calls):
    r = post(client)
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["cache-control"] == "no-store"
    assert re.fullmatch(r'attachment; filename="jyotisha_G_\d{8}\.pdf"', r.headers["content-disposition"])


# ---------------------------------------------------------------- free vs paid reports, contact

def test_defaults_offer_all_reports_with_facebook_contact(monkeypatch):
    for var in ("WEB_REPORTS", "BRAND_CONTACT", "ORDER_URL"):
        monkeypatch.delenv(var, raising=False)
    import importlib
    fresh = importlib.reload(web)
    try:
        assert list(fresh.REPORTS) == ["G", "A1", "A2", "A3", "N", "C3"]   # owner's free set + samples
        assert "facebook.com/JyothishaInsight" in fresh.BRAND_CONTACT
        assert fresh.ORDER_URL == fresh.MESSENGER == "https://m.me/JyothishaInsight"   # opens the Page's chat
    finally:
        importlib.reload(web)


def test_web_reports_env_can_limit_to_g(monkeypatch):
    monkeypatch.setenv("WEB_REPORTS", "g")
    import importlib
    fresh = importlib.reload(web)
    try:
        assert list(fresh.REPORTS) == ["G"]
    finally:
        monkeypatch.delenv("WEB_REPORTS")
        importlib.reload(web)


def test_paid_report_refused_when_not_offered(client, calls, monkeypatch):
    monkeypatch.setattr(web, "REPORTS", {"G": web.ALL_REPORTS["G"]})
    r = post(client, report="A1")
    assert r.status_code == 400 and r.json()["detail"] == "This report is available by order only"
    assert calls == []
    page = client.get("/").text
    # order-only reports are still listed, with their price instead of "free"
    a1 = re.search(r'<option value="A1">[^<]*</option>', page).group(0)
    assert "Rs 2,500" in a1 and "නොමිලේ" not in a1
    assert "නොමිලේ" in re.search(r'<option value="G">[^<]*</option>', page).group(0)


def test_catalogue_lists_reports_in_groups(client):
    page = client.get("/").text
    for code in ["G", "A1", "A2", "A3", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "C3", "C4", "N",
                 "C1", "C2", "C6"]:
        assert f'value="{code}"' in page
    assert page.count("<optgroup") == 6
    needs = {e["code"]: e["needs"] for e in web._catalog() if e["needs"]}
    assert needs == {"C1": "year", "C2": "year", "C6": "year_month",
                     "D1": "partner", "D2": "partner", "D3": "partners",
                     "P1": "prashna", "P2": "prashna", "M1": "muhurta", "E1": "events"}


# ---------------------------------------------------------------- phase 2: year / month

@pytest.mark.parametrize("report", ["C1", "C2"])
def test_year_reports_pass_the_year(client, calls, report):
    assert post(client, report=report, year="2027").status_code == 200
    assert arg(calls[0], "--year") == "2027"
    assert not any(a.startswith("--month") for a in calls[0])


def test_month_report_passes_year_and_month(client, calls):
    assert post(client, report="C6", year="2027", month="3").status_code == 200
    assert (arg(calls[0], "--year"), arg(calls[0], "--month")) == ("2027", "3")


@pytest.mark.parametrize("fields, message", [
    ({"report": "C1"}, "Year must be between 1990 and 2110"),                  # missing
    ({"report": "C1", "year": "1989"}, "Year must be between 1990 and 2110"),  # before birth
    ({"report": "C1", "year": "2111"}, "Year must be between 1990 and 2110"),
    ({"report": "C6", "year": "2027"}, "Month must be 1–12"),                  # month missing
    ({"report": "C6", "year": "2027", "month": "13"}, "Month must be 1–12"),
])
def test_year_and_month_are_checked(client, calls, fields, message):
    r = post(client, **fields)
    assert r.status_code == 400 and message in r.json()["detail"]
    assert calls == []


def test_year_is_ignored_for_reports_that_dont_need_it(client, calls):
    post(client, report="A1", year="2027", month="5")
    assert not any(a.startswith(("--year", "--month")) for a in calls[0])


def partner(n=1, **over):
    """Form fields for n partners (repeated p_* keys)."""
    base = dict(p_name="Kamala", p_date="1992-02-12", p_time="12:00", p_place="Kandy",
                p_lat="7.2906", p_lon="80.6337", p_tz="Asia/Colombo")
    base.update(over)
    return {k: [v] * n for k, v in base.items()}


# ---------------------------------------------------------------- phase 3: marriage matching

@pytest.mark.parametrize("report", ["D1", "D2"])
def test_matching_passes_partner_and_role(client, calls, report):
    assert post(client, report=report, role="girl", **partner()).status_code == 200
    a = calls[0]
    assert arg(a, "--role") == "girl"
    assert (arg(a, "--match-name"), arg(a, "--match-date"), arg(a, "--match-time")) == ("Kamala", "1992-02-12", "12:00")
    assert (arg(a, "--match-lat"), arg(a, "--match-lon"), arg(a, "--match-tz")) == ("7.2906", "80.6337", "Asia/Colombo")


def test_d3_writes_proposals_file(client, calls):
    r = post(client, report="D3", **partner(3, p_name="Nimal"))
    assert r.status_code == 200
    assert arg(calls[0], "--matches") == "{workdir}/matches.json"
    rows = json.loads(calls.files[0]["matches.json"])
    assert len(rows) == 3 and rows[0] == {"name": "Nimal", "date": "1992-02-12", "time": "12:00",
                                          "lat": 7.2906, "lon": 80.6337, "tz": "Asia/Colombo"}


@pytest.mark.parametrize("fields, message", [
    (dict(report="D1"), "Enter the partner's birth details"),
    (dict(report="D1", **partner(2)), "Enter the partner's birth details"),
    (dict(report="D3", **partner(1)), "Enter 2–5 proposals"),
    (dict(report="D3", **partner(6)), "At most 5 proposals"),
    (dict(report="D1", role="other", **partner()), "groom or the bride"),
    (dict(report="D1", **partner(p_time="25:00")), "Partner 1: Time must be HH:MM"),
    (dict(report="D1", **partner(p_date="1700-01-01")), "Partner 1: Date must be between"),
    (dict(report="D1", **partner(p_lat="95")), "Partner 1: Latitude"),
    (dict(report="D1", **partner(p_name="<b>x</b>")), "Partner 1 name contains characters"),
    (dict(report="D1", **partner(p_place="<img>")), "Partner 1 place contains characters"),
    (dict(report="D1", **partner(p_tz="Mars/Base")), "Partner 1: Unknown time zone"),
])
def test_partner_details_are_checked(client, calls, fields, message):
    r = post(client, **fields)
    assert r.status_code == 400 and message in r.json()["detail"]
    assert calls == []


def test_partner_fields_are_ignored_for_other_reports(client, calls):
    assert post(client, report="A1", **partner(p_time="garbage")).status_code == 200
    assert not any(a.startswith(("--match", "--role", "--matches")) for a in calls[0])


@pytest.mark.parametrize("report, proposals", [("D1", 1), ("D3", 3)])
def test_real_matching_reports_are_pdfs(client, report, proposals):
    pymupdf = pytest.importorskip("pymupdf")
    r = post(client, report=report, name="Test", **partner(proposals))
    assert r.status_code == 200, r.text[:200]
    assert len(pymupdf.open(stream=r.content, filetype="pdf")) >= 3


# ---------------------------------------------------------------- phase 4: prashna and muhurta

def test_page_has_prashna_and_muhurta_choices(client):
    page = client.get("/").text
    for value in ('value="lost"', 'value="abroad"', 'value="wedding"', 'value="griha_pravesha"', 'value="0-24"'):
        assert value in page
    assert "10 – රැකියාව" in page                          # houses with the report's own meanings


@pytest.mark.parametrize("report", ["P1", "P2"])
def test_prashna_passes_question_topic_and_matter(client, calls, report):
    r = post(client, report=report, question="මට මේ රැකියාව ලැබේද?", topic="lost", matter="10")
    assert r.status_code == 200
    a = calls[0]
    assert (arg(a, "--question"), arg(a, "--shat-topic"), arg(a, "--matter")) == ("මට මේ රැකියාව ලැබේද?", "lost", "10")


def test_prashna_house_is_optional(client, calls):
    assert post(client, report="P1", question="Will it rain?", topic="rain", matter="").status_code == 200
    assert not any(a.startswith("--matter") for a in calls[0])


def test_muhurta_passes_task_range_and_hours(client, calls):
    r = post(client, report="M1", task="wedding", m_from="2027-01-01", m_to="2027-01-31", m_hours="0-24")
    assert r.status_code == 200
    a = calls[0]
    assert (arg(a, "--task"), arg(a, "--muhurta-from"), arg(a, "--muhurta-to"), arg(a, "--muhurta-hours")) == \
           ("wedding", "2027-01-01", "2027-01-31", "0-24")


MUH = dict(report="M1", task="wedding", m_from="2027-01-01", m_to="2027-01-31", m_hours="6-21")


@pytest.mark.parametrize("fields, message", [
    (dict(report="P1", question=""), "Question must be 1–150 characters"),
    (dict(report="P1", question="x" * 151), "Question must be 1–150 characters"),
    (dict(report="P1", question="<script>"), "Question contains characters"),
    (dict(report="P1", question="ok?", topic="astral"), "Unknown question topic"),
    (dict(report="P1", question="ok?", matter="13"), "House of the matter must be 1–12"),
    ({**MUH, "task": "heist"}, "Unknown purpose"),
    ({**MUH, "m_from": "2027-02-01"}, "must run forwards"),
    ({**MUH, "m_to": "2027-03-15"}, "under 62 days"),
    ({**MUH, "m_from": "01/01/2027"}, "Start date must be YYYY-MM-DD"),
    ({**MUH, "m_hours": "3-4"}, "Unknown hours choice"),
])
def test_prashna_and_muhurta_inputs_are_checked(client, calls, fields, message):
    r = post(client, **fields)
    assert r.status_code == 400 and message in r.json()["detail"]
    assert calls == []


@pytest.mark.parametrize("fields", [
    dict(report="P1", question="මට මේ රැකියාව ලැබේද?", topic="general", matter="10"),
    dict(report="M1", task="travel", m_from="2027-01-01", m_to="2027-01-20", m_hours="6-21"),
])
def test_real_prashna_and_muhurta_reports_are_pdfs(client, fields):
    pymupdf = pytest.importorskip("pymupdf")
    r = post(client, name="Test", **fields)
    assert r.status_code == 200, r.text[:200]
    assert len(pymupdf.open(stream=r.content, filetype="pdf")) >= 3


# ---------------------------------------------------------------- phase 5: birth-time correction

def events(rows=None):
    rows = rows or [("marriage", "2018-03-04", "Galle"), ("job", "2014-01-10", ""), ("child", "2020-07-01", "")]
    return {"e_type": [r[0] for r in rows], "e_date": [r[1] for r in rows], "e_note": [r[2] for r in rows]}


def test_e1_writes_events_file(client, calls):
    assert post(client, report="E1", **events()).status_code == 200
    assert arg(calls[0], "--events") == "{workdir}/events.json"
    rows = json.loads(calls.files[0]["events.json"])
    assert rows[0] == {"type": "marriage", "date": "2018-03-04", "note": "Galle"} and len(rows) == 3


@pytest.mark.parametrize("rows, message", [
    ([("job", "2014-01-10", "")] * 2, "Enter 3–12 past events"),
    ([("job", "2014-01-10", "")] * 13, "Enter 3–12 past events"),
    ([("job", "2014-01-10", "")] * 2 + [("wedding-cake", "2014-01-10", "")], "Event 3: unknown kind of event"),
    ([("job", "2014-01-10", "")] * 2 + [("job", "1980-01-01", "")], "Event 3: the date must be between"),
    ([("job", "2014-01-10", "")] * 2 + [("job", "2999-01-01", "")], "Event 3: the date must be between"),
    ([("job", "2014-01-10", "")] * 2 + [("job", "10/01/2014", "")], "Event 3 date must be YYYY-MM-DD"),
    ([("job", "2014-01-10", "")] * 2 + [("job", "2014-01-10", "<b>")], "Event 3 note contains characters"),
])
def test_events_are_checked(client, calls, rows, message):
    r = post(client, report="E1", **events(rows))
    assert r.status_code == 400 and message in r.json()["detail"]
    assert calls == []


def test_events_are_ignored_for_other_reports(client, calls):
    assert post(client, report="A1", e_type=["nonsense"], e_date=["x"]).status_code == 200
    assert not any(a.startswith("--events") for a in calls[0])


def test_real_report_e1_is_a_pdf(client):
    pymupdf = pytest.importorskip("pymupdf")
    r = post(client, report="E1", name="Test", **events())
    assert r.status_code == 200, r.text[:200]
    assert len(pymupdf.open(stream=r.content, filetype="pdf")) >= 3


def test_real_report_c1_is_a_pdf(client):
    pymupdf = pytest.importorskip("pymupdf")
    r = post(client, report="C1", year="2027", name="Test")
    assert r.status_code == 200
    doc = pymupdf.open(stream=r.content, filetype="pdf")
    assert len(doc) >= 3 and "2027" in "".join(p.get_text() for p in doc)


def test_catalogue_prices_come_from_prices_json(monkeypatch):
    monkeypatch.setattr(web, "REPORTS", {"G": "x", "N": "x"})
    by_code = {e["code"]: e for e in web._catalog()}
    assert by_code["G"]["free"] and by_code["G"]["price"] is None
    assert by_code["B2"]["price"] == 3000 and not by_code["B2"]["free"]
    assert by_code["A3"]["price"] == 9500


def test_order_settings_reach_the_page(client, monkeypatch):
    monkeypatch.setattr(web, "ORDER_WHATSAPP", "94711234567")
    monkeypatch.setattr(web, "ORDER_URL", "https://facebook.com/example")
    page = client.get("/").text
    assert '"whatsapp": "94711234567"' in page and '"url": "https://facebook.com/example"' in page


def test_whatsapp_setting_keeps_digits_only(monkeypatch):
    monkeypatch.setenv("ORDER_WHATSAPP", "+94 71-123 4567")
    import importlib
    fresh = importlib.reload(web)
    try:
        assert fresh.ORDER_WHATSAPP == "94711234567"
    finally:
        monkeypatch.delenv("ORDER_WHATSAPP")
        importlib.reload(web)


def test_script_json_cannot_close_the_script_tag():
    assert "</script>" not in web._script_json({"x": "</script><b>"})


def test_contact_line_reaches_the_pdf(client, calls, monkeypatch):
    monkeypatch.setattr(web, "BRAND_CONTACT", "facebook.com/example")
    post(client)
    assert arg(calls[0], "--brand-contact") == "facebook.com/example"


def test_no_contact_line_by_default(client, calls):
    post(client)
    assert not any(a.startswith("--brand-contact") for a in calls[0])


def test_value_starting_with_dash_stays_a_value(client, calls):
    post(client, name="-Nimal", place="--out=/tmp/x.pdf")
    assert arg(calls[0], "--name") == "-Nimal"
    assert arg(calls[0], "--place") == "--out=/tmp/x.pdf"
    assert not any(a.startswith("--out") for a in calls[0])   # the app adds --out itself, in _render


# ---------------------------------------------------------------- security headers

def test_security_headers_and_csp(client):
    r = client.get("/")
    h = r.headers
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert h["referrer-policy"] == "no-referrer"
    csp = h["content-security-policy"]
    assert "default-src 'none'" in csp and "frame-ancestors 'none'" in csp
    assert "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]   # scripts by hash only
    import base64, hashlib
    script = re.search(r"<script>(.*?)</script>", r.text, re.S).group(1)
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    assert f"'sha256-{digest}'" in csp
    assert client.get("/healthz").headers["x-content-type-options"] == "nosniff"
    for hidden in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(hidden).status_code == 404


def test_failed_report_does_not_log_birth_data(client, monkeypatch, capsys):
    class P:                                   # a report process that fails with the client's data in stderr
        pid, returncode = 0, 1

        def __init__(self, *a, **k):
            pass

        def communicate(self, timeout=None):
            return "", "Traceback ...\nValueError: bad date for Nimali Senanayake 1985-03-21\n"
    monkeypatch.setattr(web.subprocess, "Popen", P)
    assert post(client, name="Nimali Senanayake").status_code == 500
    logged = capsys.readouterr().err
    assert "ValueError" in logged and "Nimali" not in logged and "1985" not in logged


def test_order_button_shown_only_for_web_urls(client, monkeypatch):
    assert "Order on Messenger" not in client.get("/").text
    monkeypatch.setattr(web, "ORDER_URL", "https://facebook.com/example?a=1&b=2")
    page = client.get("/").text
    assert "Order on Messenger" in page
    assert 'href="https://facebook.com/example?a=1&amp;b=2"' in page
    monkeypatch.setattr(web, "ORDER_URL", "javascript:alert(1)")
    assert "Order on Messenger" not in client.get("/").text


# ---------------------------------------------------------------- limits

def test_per_ip_limit(client, calls, monkeypatch):
    monkeypatch.setattr(web, "RATE_PER_IP", 2)
    alice = {"cf-connecting-ip": "203.0.113.5"}
    assert [post(client, headers=alice).status_code for _ in range(2)] == [200, 200]
    r = post(client, headers=alice)
    assert r.status_code == 429
    assert 0 < int(r.headers["retry-after"]) <= 3600
    assert post(client, headers={"cf-connecting-ip": "198.51.100.7"}).status_code == 200   # someone else


def test_rejected_input_does_not_use_up_the_limit(client, calls, monkeypatch):
    monkeypatch.setattr(web, "RATE_PER_IP", 1)
    for _ in range(3):
        assert post(client, birth_time="99:99").status_code == 400
    assert post(client).status_code == 200


def test_global_limit(client, calls, monkeypatch):
    monkeypatch.setattr(web, "RATE_TOTAL", 3)
    codes = [post(client, headers={"cf-connecting-ip": f"203.0.113.{i}"}).status_code for i in range(4)]
    assert codes == [200, 200, 200, 429]


def test_spoofed_forwarded_for_does_not_bypass_limit(client, calls, monkeypatch):
    """A client can send its own X-Forwarded-For; the proxy-set header must win."""
    monkeypatch.setattr(web, "RATE_PER_IP", 1)
    real = "203.0.113.5"
    assert post(client, headers={"cf-connecting-ip": real, "x-forwarded-for": "1.1.1.1"}).status_code == 200
    assert post(client, headers={"cf-connecting-ip": real, "x-forwarded-for": "2.2.2.2"}).status_code == 429


def test_busy_when_all_slots_taken(client, calls, monkeypatch):
    monkeypatch.setattr(web, "_slots", asyncio.Semaphore(0))
    r = post(client)
    assert r.status_code == 503
    assert "Busy" in r.json()["detail"]


# ---------------------------------------------------------------- real pipeline

def test_real_report_g_is_a_pdf(client, monkeypatch):
    pymupdf = pytest.importorskip("pymupdf")
    monkeypatch.setattr(web, "BRAND_CONTACT", "facebook.com/example")
    r = post(client, name="Test", place="Kandy", lat="7.2906", lon="80.6337")
    assert r.status_code == 200
    doc = pymupdf.open(stream=r.content, filetype="pdf")
    text = doc[0].get_text()
    assert len(doc) == 1 and "Test" in text and "Kandy" in text
    assert "facebook.com/example" in text
    fonts = {s["font"] for b in doc[0].get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"]}
    assert fonts and all(f.startswith("Noto") for f in fonts)
