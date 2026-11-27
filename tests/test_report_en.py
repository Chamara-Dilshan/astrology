"""The English version of the free summary (G --lang en), from the generator and the website."""
import re
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from web import app as web

ROOT = web.ROOT
BIRTH = ["--name=Sample", "--date=1990-05-15", "--time=10:30", "--lat=6.9271", "--lon=79.8612",
         "--place=Colombo", "--report-date=2026-11-27"]


def render(tmp_path, *extra):
    page = tmp_path / ("g_" + "_".join(e.split("=")[-1] for e in extra) + ".html")
    r = subprocess.run([sys.executable, str(ROOT / "jyotisha_report.py"), "--report=G", *BIRTH, *extra,
                        f"--out={page.with_suffix('.pdf')}", f"--html={page}"],
                       capture_output=True, text=True, encoding="utf-8")
    return r, (page.read_text(encoding="utf-8") if page.exists() else "")


def test_english_g_has_the_same_chart_as_the_sinhala_one(tmp_path):
    pytest.importorskip("weasyprint")
    r_en, en = render(tmp_path, "--lang=en")
    r_si, si = render(tmp_path)
    assert r_en.returncode == 0 and r_si.returncode == 0, r_en.stderr[-400:] + r_si.stderr[-400:]
    assert '<html lang="en">' in en and "Your Birth Chart at a Glance" in en
    assert 'class="logo small"' in en and 'class="logo small"' in si   # the logo above the brand name
    assert 'content: "Page " counter(page)' in en
    # Karka lagna 04°19′, Moon in Dhanu, Uttara Ashadha pada 1, Rahu maha dasha: in both languages
    assert "Karka (Cancer) 04°19′" in en and "කටක (04°19′)" in si
    assert "Dhanu (Sagittarius)" in en and "ධනු" in si
    assert "Uttara Ashadha, pada 1" in en
    assert "Rahu (2011-12-10 – 2029-12-09)" in en and "රාහු (2011-12-10 – 2029-12-09)" in si
    assert "Mangalavara (Tuesday)" in en
    text = re.sub(r"<[^>]+>|<style>.*?</style>", " ", en.split("<body>", 1)[1])
    assert not re.search(r"[඀-෿]{3,}", text.replace("බෙ", ""))   # no Sinhala prose left in
    assert '<html lang="si">' in si


def test_english_is_refused_for_other_reports(tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "jyotisha_report.py"), "--report=A1", "--lang=en", *BIRTH,
                        f"--out={tmp_path / 'a1.pdf'}"], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode != 0 and "G report only" in r.stderr


# ---------------------------------------------------------------- website

@pytest.fixture
def calls(monkeypatch):
    seen = []
    monkeypatch.setattr(web, "_render", lambda args, workdir, files=None: seen.append(args) or b"%PDF-1.7 fake")
    monkeypatch.setattr(web, "REPORTS", dict(web.ALL_REPORTS))
    monkeypatch.setattr(web, "RATE_PER_IP", 1000)
    web._limiter.reset()
    return seen


FORM = dict(name="Sample", birth_date="1990-05-15", birth_time="10:30", place="Colombo",
            lat="6.9271", lon="79.8612", tz="Asia/Colombo", report="G")


def test_site_makes_english_g(calls):
    r = TestClient(web.app).post("/report", data={**FORM, "lang": "en"})
    assert r.status_code == 200
    assert "--lang=en" in calls[0]
    assert re.search(r'filename="jyotisha_G_en_\d{8}\.pdf"', r.headers["content-disposition"])


def test_site_default_is_sinhala(calls):
    r = TestClient(web.app).post("/report", data=FORM)
    assert r.status_code == 200 and not any(a.startswith("--lang") for a in calls[0])
    assert re.search(r'filename="jyotisha_G_\d{8}\.pdf"', r.headers["content-disposition"])


@pytest.mark.parametrize("report, lang", [("A1", "en"), ("G", "ta"), ("G", "EN")])
def test_site_refuses_languages_a_report_does_not_have(calls, report, lang):
    r = TestClient(web.app).post("/report", data={**FORM, "report": report, "lang": lang})
    assert r.status_code == 400 and not calls


def test_form_offers_the_language_choice(calls):
    page = TestClient(web.app).get("/").text
    assert '<select id="lang" name="lang"><option value="si">' in page and '<option value="en">English</option>' in page
    g = next(c for c in web._catalog() if c["code"] == "G")
    assert g["langs"] == ["si", "en"]
    assert all(c["langs"] == ["si"] for c in web._catalog() if c["code"] != "G")
