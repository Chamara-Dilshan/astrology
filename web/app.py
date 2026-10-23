"""Web front-end: a birth-data form that returns the Sinhala PDF report.

    uvicorn web.app:app --port 8000          (or: docker run -p 8000:8000 jyotisha)

Nothing is stored: each request runs jyotisha_report.py in a temporary folder that is
deleted as soon as the PDF has been read back.
"""
import asyncio
import collections
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
SOURCE_URL = "https://github.com/Chamara-Dilshan/astrology"
REPORTS = {"G": "Free summary (1 page)", "A1": "Natal report (8 pages)",
           "A2": "Full natal report", "A3": "Deep natal report with divisional charts"}
MAX_PARALLEL = int(os.environ.get("MAX_PARALLEL", "2"))
TIMEOUT_S = int(os.environ.get("REPORT_TIMEOUT", "180"))
RATE_PER_IP = int(os.environ.get("REPORTS_PER_HOUR_PER_IP", "10"))
RATE_TOTAL = int(os.environ.get("REPORTS_PER_HOUR", "120"))
# Header set by the proxy in front of the app. Checked on Render (2026-10-24): it is behind
# Cloudflare, CF-Connecting-IP holds the visitor's IP, and Cloudflare rejects requests that try to
# set it themselves (error 1000). X-Forwarded-For is NOT used: a forged value is kept at the front.
CLIENT_IP_HEADER = os.environ.get("CLIENT_IP_HEADER", "cf-connecting-ip")

PLACES = json.loads((HERE / "places.json").read_text(encoding="utf-8"))["places"]
PAGE = (HERE / "index.html").read_text(encoding="utf-8")
_slots = asyncio.Semaphore(MAX_PARALLEL)


class _HourlyLimiter:
    """Sliding one-hour windows of report timestamps: per client IP and in total.
    In memory, so it resets on restart; fine for a single small instance."""

    WINDOW = 3600.0

    def __init__(self):
        self.reset()

    def reset(self):
        self.per_ip, self.total = {}, collections.deque()

    def _prune(self, q, now):
        while q and now - q[0] >= self.WINDOW:
            q.popleft()

    def check(self, ip, per_ip_limit, total_limit, now=None):
        """Record a report for ip, or return seconds to wait if a limit is reached."""
        now = time.monotonic() if now is None else now
        self._prune(self.total, now)
        if len(self.total) >= total_limit:
            return max(1, int(self.WINDOW - (now - self.total[0])) + 1)
        q = self.per_ip.setdefault(ip, collections.deque())
        self._prune(q, now)
        if len(q) >= per_ip_limit:
            return max(1, int(self.WINDOW - (now - q[0])) + 1)
        q.append(now)
        self.total.append(now)
        if len(self.per_ip) > 5000:          # forget idle clients so memory stays bounded
            for k in [k for k, v in self.per_ip.items() if not v or now - v[-1] >= self.WINDOW]:
                del self.per_ip[k]
        return 0


_limiter = _HourlyLimiter()


def _client_ip(request):
    ip = request.headers.get(CLIENT_IP_HEADER)
    return ip.strip() if ip else (request.client.host if request.client else "unknown")

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
async def report(request: Request, name: str = Form(...), birth_date: str = Form(...), birth_time: str = Form(...),
                 place: str = Form(""), lat: float = Form(...), lon: float = Form(...),
                 tz: str = Form("Asia/Colombo"), time_exact: str = Form("yes"), report: str = Form("G")):
    name = _validate(name, birth_date, birth_time, lat, lon, tz, report)
    place = " ".join(place.split())[:60]
    args = ["--report", report, "--name", name, "--date", birth_date, "--time", birth_time,
            "--lat", f"{lat:.4f}", "--lon", f"{lon:.4f}", "--tz", tz, "--place", place,
            "--time-exact", "yes" if time_exact == "yes" else "approx", "--brand", "Jyothisha Insight"]
    if _slots.locked():
        raise HTTPException(503, "Busy, please try again in a minute")
    # counted only once the request is valid and a slot is free, so typos and "busy" don't use it up
    wait = _limiter.check(_client_ip(request), RATE_PER_IP, RATE_TOTAL)
    if wait:
        minutes = max(1, round(wait / 60))
        raise HTTPException(429, f"Report limit reached, please try again in about {minutes} min",
                            headers={"Retry-After": str(wait)})
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
