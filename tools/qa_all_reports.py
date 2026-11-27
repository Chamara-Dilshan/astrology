"""Build every report type with fictional data and check each PDF: the generator's own --qa (shaping,
fonts, text off the page, blank pages), plus leftover placeholders and engine English in the Sinhala
reports, and checks that Sinhala copied out of each PDF (with PDFium, Chrome's engine) is the report's real
text. Run it before a release; CI runs it on every change.

    python tools/qa_all_reports.py [out_dir] [--jobs N] [--only A1,M1]

Exit code 1 if any report fails. Data and dates are fixed, so the output is the same every day."""
import argparse
import concurrent.futures as cf
import html
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = ["--name=Sample", "--date=1990-05-15", "--time=10:30", "--lat=6.9271", "--lon=79.8612",
        "--tz=Asia/Colombo", "--place=Colombo", "--time-exact=yes", "--report-date=2026-11-27",
        "--brand=Jyothisha Insight", "--brand-contact=Facebook: Jyothisha Insight"]
MATCH = ["--match-name=Sample Two", "--match-date=1992-08-20", "--match-time=07:45", "--match-lat=7.2906",
         "--match-lon=80.6337", "--match-tz=Asia/Colombo", "--role=boy"]
MATCHES = [{"name": "Proposal One", "date": "1992-08-20", "time": "07:45", "lat": 7.2906, "lon": 80.6337, "tz": "Asia/Colombo"},
           {"name": "Proposal Two", "date": "1991-02-03", "time": "16:20", "lat": 6.0535, "lon": 80.2210, "tz": "Asia/Colombo"},
           {"name": "Proposal Three", "date": "1993-11-11", "time": "23:05", "lat": 9.6615, "lon": 80.0255, "tz": "Asia/Colombo"}]
EVENTS = [{"type": "education", "date": "2008-12-10", "note": ""}, {"type": "job", "date": "2013-06-01", "note": ""},
          {"type": "marriage", "date": "2018-03-04", "note": ""}, {"type": "child", "date": "2020-09-15", "note": ""}]
EXTRA = {"C1": ["--year=2026"], "C2": ["--year=2026"], "C6": ["--year=2026", "--month=3"],
         "D1": MATCH, "D2": MATCH, "D3": ["--matches={out}/matches.json", "--role=girl"],
         "E1": ["--events={out}/events.json", "--time-exact=approx"],
         "M1": ["--task=wedding", "--muhurta-from=2026-12-01", "--muhurta-to=2026-12-31", "--muhurta-hours=6-21"],
         "P1": ["--question=මගේ විවාහය කවදා සිදුවේද?", "--matter=7", "--shat-topic=marriage"],
         "P2": ["--question=ගමන සාර්ථකද?", "--matter=9", "--shat-topic=travel"]}
CODES = ["G", "A1", "A2", "A3", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "C1", "C2", "C3", "C4", "C6",
         "D1", "D2", "D3", "E1", "M1", "N", "P1", "P2"]
LEFTOVER = re.compile(r"\bNone\b|\bnan\b|\{\{|\}\}|Traceback|\bundefined\b|\[\]|\{\}|KeyError")
# English that belongs in the Sinhala reports: abbreviations with a Sinhala gloss, the book cited, names
ENGLISH_OK = set("""Jyothisha Insight JYOTHISHA INSIGHT YOT HISHA Facebook Sample Two Proposal One Three Colombo Asia
UTC AK AmK BK MK PiK PK GK DK AL UL BAV SAV KP PVB Vedic Astrology An Integrated Approach Narasimha Rao Suryanarain
Swiss Ephemeris Lahiri Sahams synastry Synastry Uttara Ashadha Bhe Bho Ja Ji""".split())


SINHALA = re.compile(r"[඀-෿‌‍]+")


def copy_check(pdf, page_html):
    """Every Sinhala word PDFium (Chrome, Edge, Android) copies out of the PDF must be a word of the report."""
    try:
        import pypdfium2 as pdfium
    except ImportError:      # a dev dependency; without it this check is skipped
        return []
    src = open(page_html, encoding="utf-8").read()
    src = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<style.*?</style>", " ", src, flags=re.S)))
    want = set(SINHALA.findall(src)) | {"පිටුව"}   # the page-number footer comes from the stylesheet
    bad = set()
    for page in pdfium.PdfDocument(pdf):
        bad |= {w for w in SINHALA.findall(page.get_textpage().get_text_range()) if w not in want}
    return [f"copied Sinhala is not the report's text: {', '.join(sorted(bad)[:8])}"] if bad else []


def build(tag, code, out):
    args = [a.replace("{out}", out) for a in EXTRA.get(code, [])]
    pdf, page_html = os.path.join(out, f"{tag}.pdf"), os.path.join(out, f"{tag}.html")
    cmd = [sys.executable, os.path.join(ROOT, "jyotisha_report.py"), f"--report={code}", *BASE, *args,
           *(["--lang=en"] if tag == "G-en" else []), f"--out={pdf}", f"--html={page_html}", "--qa",
           f"--qa-dir={os.path.join(out, tag + '_qa')}"]
    t = time.time()
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    problems = [ln for ln in p.stderr.splitlines() if ln.startswith("!!")]
    if p.returncode != 0:
        problems.append(f"exit {p.returncode}: " + " | ".join(p.stderr.strip().splitlines()[-3:]))
    elif os.path.exists(pdf):
        import pymupdf
        for page in pymupdf.open(pdf):
            text = page.get_text()
            for m in LEFTOVER.finditer(text):
                problems.append(f"p{page.number + 1}: leftover '{m.group()}' …{text[max(0, m.start() - 30):m.end() + 30]!r}…")
            if tag != "G-en":
                eng = sorted({w for w in re.findall(r"[A-Za-z]{3,}", text) if w not in ENGLISH_OK})
                if eng:
                    problems.append(f"p{page.number + 1}: English in a Sinhala report: {', '.join(eng[:12])}")
        problems += copy_check(pdf, page_html)
    return tag, time.time() - t, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", nargs="?", default="qa_all")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    json.dump(MATCHES, open(os.path.join(out, "matches.json"), "w", encoding="utf-8"))
    json.dump(EVENTS, open(os.path.join(out, "events.json"), "w", encoding="utf-8"))
    jobs = [(c, c) for c in CODES] + [("G-en", "G")]
    if a.only:
        jobs = [j for j in jobs if j[0] in a.only.split(",")]
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        results = list(ex.map(lambda j: build(j[0], j[1], out), jobs))
    failed = 0
    for tag, secs, problems in results:
        print(f"{tag:5} {secs:5.1f}s  {'OK' if not problems else 'FAIL'}")
        for pr in problems:
            print("      " + pr)
        failed += bool(problems)
    print(f"{len(results) - failed}/{len(results)} reports OK → {out}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    main()
