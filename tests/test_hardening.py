"""Security hardening of the web app, from the security test of 2026-11-27: request size cap, time zone
allowlist, invisible-character filter, and the panchanga page's rate limit and cache."""
import pytest
from fastapi.testclient import TestClient

from web import app as web

GOOD = dict(name="Sample", birth_date="1990-05-15", birth_time="10:30", place="Colombo",
            lat="6.9271", lon="79.8612", tz="Asia/Colombo", report="G")


@pytest.fixture
def client(monkeypatch):
    web._limiter.reset()
    web._search_limiter.reset()
    web._panchanga_limiter.reset()
    monkeypatch.setattr(web, "REPORTS", dict(web.ALL_REPORTS))
    monkeypatch.setattr(web, "_render", lambda args, workdir, files=None: b"%PDF-1.7 fake")
    return TestClient(web.app)


# ---------------------------------------------------------------- request size

def test_oversized_bodies_are_refused_before_parsing(client):
    r = client.post("/places", content=b"q=" + b"a" * (web.MAX_BODY + 1),
                    headers={"content-type": "application/x-www-form-urlencoded"})
    assert r.status_code == 413 and r.headers["x-content-type-options"] == "nosniff"
    r = client.post("/report", data=GOOD, files={"x": ("a.bin", b"0" * (web.MAX_BODY + 1))})
    assert r.status_code == 413


def test_chunked_bodies_without_a_length_are_capped_too(client):
    def chunks():
        for _ in range(20):
            yield b"q=" + b"a" * 8192
    r = client.post("/places", content=chunks(), headers={"content-type": "application/x-www-form-urlencoded"})
    assert r.status_code == 413


def test_real_forms_fit_comfortably(client):
    events = {"e_type": ["marriage"] * 12, "e_date": ["2015-06-01"] * 12, "e_note": ["ශ්‍රී ලංකාව" * 5] * 12}
    big = {**GOOD, **events, "p_name": ["නම" * 20] * 5}
    body = "&".join(f"{k}={v}" for k, vals in big.items() for v in (vals if isinstance(vals, list) else [vals]))
    assert len(body.encode()) < web.MAX_BODY / 4
    assert client.post("/report", data=GOOD).status_code == 200


def test_a_bad_content_length_is_refused(client):
    r = client.post("/places", content=b"q=kandy",
                    headers={"content-type": "application/x-www-form-urlencoded", "content-length": "-5"})
    assert r.status_code in (400, 413)


# ---------------------------------------------------------------- time zones and text

@pytest.mark.parametrize("tz", ["Asia/Colombo\n", "Asia/Colombo ", "../../etc/passwd", "/etc/localtime",
                                "Asia/../Asia/Colombo", "C:\\Windows", "x" * 300])
def test_time_zone_must_be_a_real_iana_name(client, tz):
    """'Asia/Colombo\\n' used to reach ZoneInfo() and fail with an unhandled OSError (HTTP 500)."""
    assert client.post("/report", data={**GOOD, "tz": tz}).status_code == 400


@pytest.mark.parametrize("name", ["abc\u202edef", "a\u200bb", "a\u2066b", "a\ufeffb", "a\x00b", "a\x7fb"])
def test_invisible_and_control_characters_are_refused(client, name):
    """Bidi overrides (U+202E, U+2066) would make a name display reversed in the PDF."""
    assert client.post("/report", data={**GOOD, "name": name}).status_code == 400


def test_sinhala_joiners_are_kept(client):
    for name in ("ශ්‍රී", "ක්‍රිෂාන්", "කුමාරි"):            # ZWJ (U+200D) is part of Sinhala spelling
        assert client.post("/report", data={**GOOD, "name": name}).status_code == 200, name


# ---------------------------------------------------------------- panchanga page

def test_panchanga_is_rate_limited_per_visitor(client, monkeypatch):
    monkeypatch.setattr(web, "PANCHANGA_PER_IP", 3)
    for d in ("2030-01-01", "2030-01-02", "2030-01-03"):
        assert client.get("/panchanga", params={"date": d}).status_code == 200
    r = client.get("/panchanga", params={"date": "2030-01-04"})
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0
    other = {web.CLIENT_IP_HEADER: "203.0.113.7"}
    assert client.get("/panchanga", params={"date": "2030-01-04"}, headers=other).status_code == 200


def test_panchanga_repeats_come_from_the_cache_and_cost_no_allowance(client, monkeypatch):
    calls = []
    real = web._panchanga_html
    monkeypatch.setattr(web, "_panchanga_html", lambda day, town: calls.append(day) or real(day, town))
    monkeypatch.setattr(web, "PANCHANGA_PER_IP", 1)
    web._PANCHANGA_PAGES.clear()
    for _ in range(5):          # one computation, then four cached pages: the limit of 1 is never hit
        assert client.get("/panchanga", params={"date": "2031-05-05", "town": "Galle"}).status_code == 200
    assert len(calls) == 1
    assert client.get("/panchanga", params={"date": "2031-05-06", "town": "Galle"}).status_code == 429
    web._PANCHANGA_PAGES.clear()


# ---------------------------------------------------------------- rate-limit keys and cross-site requests

class FakeRequest:
    def __init__(self, header=None, peer="198.51.100.20"):
        self.headers = {web.CLIENT_IP_HEADER: header} if header is not None else {}
        self.client = type("C", (), {"host": peer})()


@pytest.mark.parametrize("header, key", [
    ("203.0.113.9", "203.0.113.9"),
    (" 203.0.113.9 ", "203.0.113.9"),
    ("2001:db8:1:2:3:4:5:6", "2001:db8:1:2::/64"),          # one /64 = one visitor
    ("2001:db8:1:2:ffff:ffff:ffff:ffff", "2001:db8:1:2::/64"),
    ("::ffff:203.0.113.9", "203.0.113.9"),                   # IPv4 written as IPv6
    ("not-an-ip", "198.51.100.20"),                          # junk header: the peer's address instead
    ("x" * 5000, "198.51.100.20"),
    (None, "198.51.100.20"),
])
def test_rate_limit_key(header, key):
    assert web._client_ip(FakeRequest(header)) == key


def test_rate_limit_key_without_any_address():
    assert web._client_ip(FakeRequest("junk", peer="testclient")) == "unknown"


@pytest.mark.parametrize("headers", [{"sec-fetch-site": "cross-site"}, {"sec-fetch-site": "same-site"},
                                     {"origin": "https://evil.example"}, {"origin": "null"}])
def test_other_websites_cannot_post(client, headers):
    assert client.post("/report", data=GOOD, headers=headers).status_code == 403
    assert client.post("/places", data={"q": "kandy"}, headers=headers).status_code == 403


@pytest.mark.parametrize("headers", [{}, {"sec-fetch-site": "same-origin"}, {"sec-fetch-site": "none"},
                                     {"origin": "http://testserver"}])
def test_the_site_itself_and_tools_can_post(client, headers):
    assert client.post("/report", data=GOOD, headers=headers).status_code == 200
    assert client.post("/places", data={"q": "kandy"}, headers=headers).status_code == 200


# ---------------------------------------------------------------- Content-Security-Policy

def test_csp_allows_only_the_template_script(client):
    import base64
    import hashlib
    import json
    import re
    r = client.get("/")
    csp = r.headers["content-security-policy"]
    scripts = re.findall(r"<script>(.*?)</script>", r.text, re.S)
    assert len(scripts) == 1 and "{{" not in scripts[0]
    digest = base64.b64encode(hashlib.sha256(scripts[0].encode()).digest()).decode()
    assert f"script-src 'sha256-{digest}';" in csp                        # the served script is allowed ...
    assert csp.count("'sha256-") == 1                                      # ... and nothing else
    data = re.search(r'<script type="application/json" id="page-data">(.*?)</script>', r.text, re.S).group(1)
    assert "<" not in data and set(json.loads(data)) == {"place", "catalog", "order", "studio"}
    for path in ("/accuracy", "/panchanga"):
        assert "script-src 'none'" in client.get(path).headers["content-security-policy"]


# ---------------------------------------------------------------- the report subprocess

def test_names_starting_with_a_dash_work(tmp_path):
    """'-Nimal' used to be read by the calculation script as an option (HTTP 500)."""
    import subprocess
    import sys
    pytest.importorskip("weasyprint")
    r = subprocess.run([sys.executable, str(web.ROOT / "jyotisha_report.py"), "--report=G", "--name=-Nimal",
                        "--place=--json", "--date=1990-05-15", "--time=10:30", "--lat=6.9271", "--lon=79.8612",
                        f"--out={tmp_path / 'g.pdf'}"], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-300:]


@pytest.mark.skipif(__import__("os").name != "posix", reason="process groups are POSIX")
def test_a_timed_out_report_leaves_no_processes(monkeypatch, tmp_path):
    import subprocess
    import time
    monkeypatch.setattr(web, "TIMEOUT_S", 1)
    marker = f"TimeoutProbe{time.time_ns()}"
    args = ["--report=A3", f"--name={marker}", "--date=1990-05-15", "--time=10:30", "--lat=6.9271",
            "--lon=79.8612", "--tz=Asia/Colombo"]
    with pytest.raises(subprocess.TimeoutExpired):
        web._render(args, str(tmp_path))
    time.sleep(1)
    ps = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True).stdout
    assert marker not in ps
