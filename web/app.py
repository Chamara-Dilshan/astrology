"""Web front-end: a birth-data form that returns the Sinhala PDF report.

    uvicorn web.app:app --port 8000          (or: docker run -p 8000:8000 jyotisha)

Nothing is stored: each request runs jyotisha_report.py in a temporary folder that is
deleted as soon as the PDF has been read back.
"""
import asyncio
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, Response

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
SOURCE_URL = "https://github.com/Chamara-Dilshan/astrology"
REPORTS = {"G": "Free summary (1 page)", "A1": "Natal report (8 pages)",
           "A2": "Full natal report", "A3": "Deep natal report with divisional charts"}
MAX_PARALLEL = int(os.environ.get("MAX_PARALLEL", "2"))
TIMEOUT_S = int(os.environ.get("REPORT_TIMEOUT", "180"))

PLACES = json.loads((HERE / "places.json").read_text(encoding="utf-8"))["places"]
PAGE = (HERE / "index.html").read_text(encoding="utf-8")
_slots = asyncio.Semaphore(MAX_PARALLEL)

app = FastAPI(title="Jyothisha Insight", docs_url=None, redoc_url=None)


@app.get("/", response_class=HTMLResponse)
def index():
    opts = "".join(f'<option value="{c}">{c} — {label}</option>' for c, label in REPORTS.items())
    return PAGE.replace("{{REPORT_OPTIONS}}", opts) \
               .replace("{{PLACES_JSON}}", json.dumps(PLACES)) \
               .replace("{{SOURCE_URL}}", SOURCE_URL)


@app.get("/healthz")
def healthz():
    return {"ok": True}


def _validate(name, birth_date, birth_time, lat, lon, tz, report):
    if report not in REPORTS:
        raise HTTPException(400, "Unknown report type")
    name = " ".join(name.split())
    if not 1 <= len(name) <= 60 or any(ord(c) < 32 for c in name):
        raise HTTPException(400, "Name must be 1–60 characters")
    try:
        d = date.fromisoformat(birth_date)
    except ValueError:
        raise HTTPException(400, "Date must be YYYY-MM-DD")
    if not 1800 <= d.year <= 2399:
        raise HTTPException(400, "Date must be between 1800 and 2399 (ephemeris range)")
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", birth_time):
        raise HTTPException(400, "Time must be HH:MM (24-hour)")
    if not (-66 <= lat <= 66 and -180 <= lon <= 180):
        raise HTTPException(400, "Latitude must be within ±66°, longitude within ±180°")
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(400, "Unknown time zone")
    return name


def _render(args, workdir):
    out = Path(workdir) / "report.pdf"
    r = subprocess.run([sys.executable, str(ROOT / "jyotisha_report.py"), *args, "--out", str(out)],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=TIMEOUT_S)
    if r.returncode != 0 or not out.exists():
        print(r.stderr[-2000:], file=sys.stderr)
        raise HTTPException(500, "Report generation failed")
    return out.read_bytes()


@app.post("/report")
async def report(name: str = Form(...), birth_date: str = Form(...), birth_time: str = Form(...),
                 place: str = Form(""), lat: float = Form(...), lon: float = Form(...),
                 tz: str = Form("Asia/Colombo"), time_exact: str = Form("yes"), report: str = Form("G")):
    name = _validate(name, birth_date, birth_time, lat, lon, tz, report)
    place = " ".join(place.split())[:60]
    args = ["--report", report, "--name", name, "--date", birth_date, "--time", birth_time,
            "--lat", f"{lat:.4f}", "--lon", f"{lon:.4f}", "--tz", tz, "--place", place,
            "--time-exact", "yes" if time_exact == "yes" else "approx", "--brand", "Jyothisha Insight"]
    if _slots.locked():
        raise HTTPException(503, "Busy, please try again in a minute")
    async with _slots:
        with tempfile.TemporaryDirectory(prefix="jyotisha-") as workdir:
            try:
                pdf = await asyncio.to_thread(_render, args, workdir)
            except subprocess.TimeoutExpired:
                raise HTTPException(504, "Report took too long")
    stamp = datetime.now(ZoneInfo(tz)).strftime("%Y%m%d")   # the user's date, not the server's (UTC)
    filename = f"jyotisha_{report}_{stamp}.pdf"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"',
                             "Cache-Control": "no-store"})
