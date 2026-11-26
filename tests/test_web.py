"""Tests for the web front-end (web/app.py).

Most tests replace the PDF renderer with a stub that records its arguments, so they run in
milliseconds; test_real_report_* runs the actual pipeline end to end.

    pytest -q
"""
import asyncio
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
    monkeypatch.setattr(web, "RATE_PER_IP", 1000)
    monkeypatch.setattr(web, "RATE_TOTAL", 1000)
    monkeypatch.setattr(web, "REPORTS", dict(web.ALL_REPORTS))
    monkeypatch.setattr(web, "BRAND_CONTACT", "")
    monkeypatch.setattr(web, "ORDER_URL", "")


@pytest.fixture
def calls(monkeypatch):
    """Stub the renderer: record the CLI arguments, return a tiny fake PDF."""
    seen = []

    def fake_render(args, workdir):
        seen.append(args)
        return b"%PDF-1.7 fake"

    monkeypatch.setattr(web, "_render", fake_render)
    return seen


@pytest.fixture
def client():
    return TestClient(web.app)


def post(client, headers=None, **changes):
    return client.post("/report", data={**GOOD, **changes}, headers=headers or {})


def arg(args, flag):
    return args[args.index(flag) + 1]


# ---------------------------------------------------------------- pages

def test_index_has_form_places_and_source_link(client):
    r = client.get("/")
    assert r.status_code == 200
    for code in web.REPORTS:
        assert f'value="{code}"' in r.text
    assert '"Polonnaruwa", 7.9403, 81.0188' in r.text
    assert web.SOURCE_URL in r.text
    assert "{{" not in r.text            # every template placeholder was filled


def test_healthz(client):
    assert client.get("/healthz").json() == {"ok": True}


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
    ("name", "x" * 61, "Name must be 1–60 characters"),
    ("name", "bad\x07name", "Name must be 1–60 characters"),
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

def test_default_config_offers_only_free_g(monkeypatch):
    monkeypatch.delenv("WEB_REPORTS", raising=False)
    import importlib
    fresh = importlib.reload(web)
    try:
        assert list(fresh.REPORTS) == ["G"]
    finally:
        importlib.reload(web)


def test_paid_report_refused_when_not_offered(client, calls, monkeypatch):
    monkeypatch.setattr(web, "REPORTS", {"G": web.ALL_REPORTS["G"]})
    r = post(client, report="A1")
    assert r.status_code == 400 and r.json()["detail"] == "This report is available by order only"
    assert calls == []
    page = client.get("/").text
    assert 'value="G"' in page and 'value="A1"' not in page


def test_contact_line_reaches_the_pdf(client, calls, monkeypatch):
    monkeypatch.setattr(web, "BRAND_CONTACT", "facebook.com/example")
    post(client)
    assert arg(calls[0], "--brand-contact") == "facebook.com/example"


def test_no_contact_line_by_default(client, calls):
    post(client)
    assert "--brand-contact" not in calls[0]


def test_order_link_shown_only_for_web_urls(client, monkeypatch):
    assert "Order here" not in client.get("/").text
    monkeypatch.setattr(web, "ORDER_URL", "https://facebook.com/example?a=1&b=2")
    assert 'href="https://facebook.com/example?a=1&amp;b=2"' in client.get("/").text
    monkeypatch.setattr(web, "ORDER_URL", "javascript:alert(1)")
    assert "Order here" not in client.get("/").text


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
