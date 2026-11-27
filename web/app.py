"""Web front-end: a birth-data form that returns the Sinhala PDF report.

    uvicorn web.app:app --port 8000          (or: docker run -p 8000:8000 jyotisha)

Nothing is stored: each request runs jyotisha_report.py in a temporary folder that is
deleted as soon as the PDF has been read back.
"""
import asyncio
import base64
import collections
import hashlib
import html
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

import jyotisha_report as jr   # only for its Sinhala labels (topics, houses, muhurta purposes)
from web import catalog

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
SOURCE_URL = "https://github.com/Chamara-Dilshan/astrology"
ALL_REPORTS = {c: v[2] for c, v in catalog.REPORTS.items()}   # every report the site shows
# Reports the site makes for free. The owner chose G and A1-A3; N and C3 are added as free samples.
# Every other catalogue report is shown with its price and an Order button.
REPORTS = {c: ALL_REPORTS[c] for c in os.environ.get("WEB_REPORTS", "G,A1,A2,A3,N,C3").upper()
           .replace(" ", "").split(",") if c in ALL_REPORTS} or {"G": ALL_REPORTS["G"]}
# Printed at the bottom of each PDF, and where the "order a personal reading" button links to.
# Defaults are the Jyothisha Insight Facebook page; set either to "" in the environment to hide it.
FACEBOOK_PAGE = "https://www.facebook.com/profile.php?id=61594028591573"
BRAND_CONTACT = os.environ.get("BRAND_CONTACT", "Facebook: Jyothisha Insight · facebook.com/profile.php?id=61594028591573").strip()
ORDER_URL = os.environ.get("ORDER_URL", FACEBOOK_PAGE).strip()
# Optional WhatsApp number (international digits, e.g. 9471xxxxxxx) for orders: the order button then
# opens WhatsApp with the details filled in. Without it, the details are copied for pasting on Facebook.
ORDER_WHATSAPP = re.sub(r"\D", "", os.environ.get("ORDER_WHATSAPP", ""))
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

app = FastAPI(title="Jyothisha Insight", docs_url=None, redoc_url=None, openapi_url=None)


def _csp(page_html):
    """Content-Security-Policy for the form page: nothing loads or runs except our own inline
    script (allowed by hash, so an injected script would not run), Google Fonts, and fetch() to
    this site. The page also can't be framed (clickjacking)."""
    scripts = re.findall(r"<script>(.*?)</script>", page_html, re.S)
    hashes = " ".join("'sha256-%s'" % base64.b64encode(hashlib.sha256(s.encode()).digest()).decode() for s in scripts)
    return ("default-src 'none'; "
            f"script-src {hashes}; "
            "style-src 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; "
            "connect-src 'self'; img-src 'self' data:; form-action 'self'; "
            "base-uri 'none'; frame-ancestors 'none'")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    h = response.headers
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("Referrer-Policy", "no-referrer")
    h.setdefault("X-Frame-Options", "DENY")
    h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
        h.setdefault("Strict-Transport-Security", "max-age=31536000")
    return response


@app.get("/", response_class=HTMLResponse)
def index():
    page = _index_html()
    return HTMLResponse(page, headers={"Content-Security-Policy": _csp(page)})


def _catalog():
    return catalog.entries(set(REPORTS))


def _report_options(entries):
    """<optgroup>s of the catalogue; each option says free or its price."""
    out = []
    for gkey, glabel in catalog.GROUPS.items():
        items = [e for e in entries if e["group"] == gkey]
        if not items:
            continue
        # price before the title: a closed <select> on a phone cuts off the end of the label
        opts = "".join(
            f'<option value="{e["code"]}">{e["code"]} · '
            f'{"නොමිලේ" if e["free"] else ("Rs " + format(e["price"], ",") if e["price"] else "ඇණවුම")}'
            f' — {html.escape(e["si"])}</option>'
            for e in items)
        out.append(f'<optgroup label="{html.escape(glabel)}">{opts}</optgroup>')
    return "".join(out)


def _script_json(value):
    """JSON safe to put inside <script>: no '<' can close the tag early."""
    return json.dumps(value).replace("<", "\\u003c")


def _index_html():
    entries = _catalog()
    order_cfg = {"url": ORDER_URL if ORDER_URL.startswith(("https://", "http://")) else "",
                 "whatsapp": ORDER_WHATSAPP}
    order = ""
    if ORDER_URL.startswith(("https://", "http://")):
        order = ('<div class="order"><p>ජ්‍යොතිෂවේදියාගේ සටහන් සහිත පුද්ගලික වාර්තාවක් අවශ්‍යද?<br>'
                 '<span class="hint">Want a personal reading with the astrologer\'s own notes?</span></p>'
                 f'<a class="orderbtn" href="{html.escape(ORDER_URL)}" target="_blank" rel="noopener">'
                 'Facebook හරහා ඇණවුම් කරන්න · Order on Facebook</a></div>')
    opt = lambda pairs: "".join(f'<option value="{html.escape(str(k))}">{html.escape(v)}</option>' for k, v in pairs)
    return PAGE.replace("{{REPORT_OPTIONS}}", _report_options(entries)) \
               .replace("{{TOPIC_OPTIONS}}", opt((t, jr.PRASHNA_TOPIC_SI[t]) for t in catalog.PRASHNA_TOPICS)) \
               .replace("{{HOUSE_OPTIONS}}", opt((h, f"{h} – {jr.HOUSE_SI[h]}") for h in range(1, 13))) \
               .replace("{{TASK_OPTIONS}}", opt(jr.MUHURTA_TASK_SI.items())) \
               .replace("{{HOURS_OPTIONS}}", opt(catalog.MUHURTA_HOURS.items())) \
               .replace("{{ORDER_LINK}}", order) \
               .replace("{{PLACES_JSON}}", _script_json(PLACES)) \
               .replace("{{CATALOG_JSON}}", _script_json(entries)) \
               .replace("{{ORDER_JSON}}", _script_json(order_cfg)) \
               .replace("{{SOURCE_URL}}", SOURCE_URL)


@app.get("/healthz")
def healthz():
    # RENDER_GIT_COMMIT is set by Render; shows which commit is live ("dev" when run locally)
    return {"ok": True, "version": os.environ.get("RENDER_GIT_COMMIT", "dev")[:7]}


def _clean_text(value, field, required, max_len=60):
    """Collapse whitespace; 1-max_len chars (0 allowed if optional); no control chars and no < >.
    Names and places never need markup characters, and refusing them keeps HTML out of the
    report even if some template forgot to escape (the report also escapes, and its PDF
    renderer can't load files or URLs; see jyotisha_report.safe_url_fetcher)."""
    value = " ".join(value.split())
    if not (1 if required else 0) <= len(value) <= max_len:
        raise HTTPException(400, f"{field} must be {'1' if required else '0'}–{max_len} characters")
    if any(ord(c) < 32 or c in "<>" for c in value):
        raise HTTPException(400, f"{field} contains characters that aren't allowed")
    return value


def _validate(name, birth_date, birth_time, lat, lon, tz, report):
    if report in ALL_REPORTS and report not in REPORTS:
        raise HTTPException(400, "This report is available by order only")
    if report not in REPORTS:
        raise HTTPException(400, "Unknown report type")
    name = _clean_text(name, "Name", required=True)
    _validate_birth(birth_date, birth_time, lat, lon, tz)
    return name


def _validate_birth(birth_date, birth_time, lat, lon, tz, who=""):
    """Date, time, place and time zone of a birth (the main person's or a partner's)."""
    p = f"{who}: " if who else ""
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", birth_date):   # fromisoformat also takes 19900515
            raise ValueError
        d = date.fromisoformat(birth_date)
    except ValueError:
        raise HTTPException(400, f"{p}Date must be YYYY-MM-DD")
    if not 1800 <= d.year <= 2399:
        raise HTTPException(400, f"{p}Date must be between 1800 and 2399 (ephemeris range)")
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", birth_time):
        raise HTTPException(400, f"{p}Time must be HH:MM (24-hour)")
    if not (-66 <= lat <= 66 and -180 <= lon <= 180):
        raise HTTPException(400, f"{p}Latitude must be within ±66°, longitude within ±180°")
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(400, f"{p}Unknown time zone")


def _render(args, workdir, files=None):
    out = Path(workdir) / "report.pdf"
    for fname, text in (files or {}).items():                   # e.g. matches.json for D3
        (Path(workdir) / fname).write_text(text, encoding="utf-8")
    # point file arguments at this request's own temporary folder
    args = [a.replace("{workdir}", workdir) if a.startswith("--matches=") else a for a in args]
    r = subprocess.run([sys.executable, str(ROOT / "jyotisha_report.py"), *args, "--out", str(out)],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=TIMEOUT_S)
    if r.returncode != 0 or not out.exists():
        # Log only the error type, never the output: it can contain the client's name and birth data
        last = (r.stderr.strip().splitlines() or ["?"])[-1]
        print(f"report failed: exit {r.returncode}: {last.split(':')[0][:80]}", file=sys.stderr)
        raise HTTPException(500, "Report generation failed")
    return out.read_bytes()


MAX_PROPOSALS = 5


def _partners(p_name, p_date, p_time, p_place, p_lat, p_lon, p_tz):
    """Checked partner rows from the repeated p_* form fields."""
    n = len(p_date)
    if not all(len(x) == n for x in (p_name, p_time, p_lat, p_lon)):
        raise HTTPException(400, "Partner details are incomplete")
    rows = []
    for i in range(n):
        label = f"Partner {i + 1}"
        name = _clean_text(p_name[i], f"{label} name", required=False) or f"සහකරු {i + 1}"
        place = _clean_text(p_place[i] if i < len(p_place) else "", f"{label} place", required=False)
        try:
            lat, lon = float(p_lat[i]), float(p_lon[i])
        except ValueError:
            raise HTTPException(400, f"{label}: latitude and longitude must be numbers")
        tz = p_tz[i] if i < len(p_tz) and p_tz[i] else "Asia/Colombo"
        _validate_birth(p_date[i], p_time[i], lat, lon, tz, label)
        rows.append({"name": name, "date": p_date[i], "time": p_time[i], "lat": round(lat, 4),
                     "lon": round(lon, 4), "tz": tz, "place": place})
    return rows


def _iso_date(value, field):
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or ""):
            raise ValueError
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(400, f"{field} must be YYYY-MM-DD")


def _extra_args(report, birth_date, year, month, role="boy", partners=(), question="", topic="general",
                matter=None, task="general", m_from="", m_to="", m_hours="6-21"):
    """Checked arguments for the report's extra input (see catalog.REPORTS), plus any files the
    report needs written into its temporary folder: ([args], {filename: text})."""
    needs = catalog.REPORTS[report][3]
    args, files = [], {}
    if needs == "prashna":
        args.append(f"--question={_clean_text(question, 'Question', required=True, max_len=150)}")
        if topic not in catalog.PRASHNA_TOPICS:
            raise HTTPException(400, "Unknown question topic")
        args.append(f"--shat-topic={topic}")
        if matter is not None:
            if not 1 <= matter <= 12:
                raise HTTPException(400, "House of the matter must be 1–12")
            args.append(f"--matter={matter}")
    if needs == "muhurta":
        if task not in jr.MUHURTA_TASK_SI:
            raise HTTPException(400, "Unknown purpose")
        start, end = _iso_date(m_from, "Start date"), _iso_date(m_to, "End date")
        if not 0 <= (end - start).days < catalog.MUHURTA_MAX_DAYS:
            raise HTTPException(400, f"The date range must run forwards and be under {catalog.MUHURTA_MAX_DAYS} days")
        if not (1800 <= start.year and end.year <= 2399):
            raise HTTPException(400, "Dates must be between 1800 and 2399")
        if m_hours not in catalog.MUHURTA_HOURS:
            raise HTTPException(400, "Unknown hours choice")
        args += [f"--task={task}", f"--muhurta-from={start}", f"--muhurta-to={end}", f"--muhurta-hours={m_hours}"]
    if needs in ("partner", "partners"):
        if role not in ("boy", "girl"):
            raise HTTPException(400, "Say whether the first person is the groom or the bride")
        args.append(f"--role={role}")
    if needs == "partner":
        if len(partners) != 1:
            raise HTTPException(400, "Enter the partner's birth details")
        p = partners[0]
        args += [f"--match-name={p['name']}", f"--match-date={p['date']}", f"--match-time={p['time']}",
                 f"--match-lat={p['lat']:.4f}", f"--match-lon={p['lon']:.4f}", f"--match-tz={p['tz']}"]
    if needs == "partners":
        if not 2 <= len(partners) <= MAX_PROPOSALS:
            raise HTTPException(400, f"Enter 2–{MAX_PROPOSALS} proposals to compare")
        files["matches.json"] = json.dumps([{k: p[k] for k in ("name", "date", "time", "lat", "lon", "tz")}
                                            for p in partners], ensure_ascii=False)
        args.append("--matches={workdir}/matches.json")
    if needs in ("year", "year_month"):
        birth_year = int(birth_date[:4])
        if year is None or not birth_year <= year <= min(birth_year + 120, 2399):
            raise HTTPException(400, f"Year must be between {birth_year} and {min(birth_year + 120, 2399)}")
        args.append(f"--year={year}")
    if needs == "year_month":
        if month is None or not 1 <= month <= 12:
            raise HTTPException(400, "Month must be 1–12 (counted from the birthday)")
        args.append(f"--month={month}")
    return args, files


@app.post("/report")
async def report(request: Request, name: str = Form(...), birth_date: str = Form(...), birth_time: str = Form(...),
                 place: str = Form(""), lat: float = Form(...), lon: float = Form(...),
                 tz: str = Form("Asia/Colombo"), time_exact: str = Form("yes"), report: str = Form("G"),
                 year: int | None = Form(None), month: int | None = Form(None), role: str = Form("boy"),
                 p_name: list[str] = Form([]), p_date: list[str] = Form([]), p_time: list[str] = Form([]),
                 p_place: list[str] = Form([]), p_lat: list[str] = Form([]), p_lon: list[str] = Form([]),
                 p_tz: list[str] = Form([]), question: str = Form(""), topic: str = Form("general"),
                 matter: int | None = Form(None), task: str = Form("general"), m_from: str = Form(""),
                 m_to: str = Form(""), m_hours: str = Form("6-21")):
    name = _validate(name, birth_date, birth_time, lat, lon, tz, report)
    place = _clean_text(place, "Place", required=False)
    partners = ()
    if catalog.REPORTS[report][3] in ("partner", "partners"):      # ignored for other reports
        if len(p_date) > MAX_PROPOSALS:
            raise HTTPException(400, f"At most {MAX_PROPOSALS} proposals")
        partners = _partners(p_name, p_date, p_time, p_place, p_lat, p_lon, p_tz)
    # --opt=value form: a value starting with "-" can't be taken for another option
    args = [f"--report={report}", f"--name={name}", f"--date={birth_date}", f"--time={birth_time}",
            f"--lat={lat:.4f}", f"--lon={lon:.4f}", f"--tz={tz}", f"--place={place}",
            f"--time-exact={'yes' if time_exact == 'yes' else 'approx'}", "--brand=Jyothisha Insight"]
    extra, files = _extra_args(report, birth_date, year, month, role, partners, question, topic, matter,
                               task, m_from, m_to, m_hours)
    args += extra
    if BRAND_CONTACT:
        args.append(f"--brand-contact={BRAND_CONTACT}")
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
                pdf = await asyncio.to_thread(_render, args, workdir, files)
            except subprocess.TimeoutExpired:
                raise HTTPException(504, "Report took too long")
    stamp = datetime.now(ZoneInfo(tz)).strftime("%Y%m%d")   # the user's date, not the server's (UTC)
    filename = f"jyotisha_{report}_{stamp}.pdf"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"',
                             "Cache-Control": "no-store"})
