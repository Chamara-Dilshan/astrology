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
import ipaddress
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import unicodedata
import zoneinfo
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response

import jyotisha_report as jr   # its Sinhala labels, and (as jr.jc) the engine for the panchanga page
from web import catalog, placesearch

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
# Cloudflare gives up on a response after 100 s (error 524), so a longer render only holds the slot.
TIMEOUT_S = int(os.environ.get("REPORT_TIMEOUT", "90"))
RATE_PER_IP = int(os.environ.get("REPORTS_PER_HOUR_PER_IP", "10"))
RATE_TOTAL = int(os.environ.get("REPORTS_PER_HOUR", "120"))
# Town search (the place box asks as you type): generous, but bounded.
SEARCH_PER_IP = int(os.environ.get("SEARCHES_PER_HOUR_PER_IP", "600"))
SEARCH_TOTAL = int(os.environ.get("SEARCHES_PER_HOUR", "20000"))
# Header set by the proxy in front of the app. Checked on Render (2026-10-24): it is behind
# Cloudflare, CF-Connecting-IP holds the visitor's IP, and Cloudflare rejects requests that try to
# set it themselves (error 1000). X-Forwarded-For is NOT used: a forged value is kept at the front.
CLIENT_IP_HEADER = os.environ.get("CLIENT_IP_HEADER", "cf-connecting-ip")

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
_search_limiter = _HourlyLimiter()


def _client_ip(request):
    """Rate-limit key for a visitor: the proxy's client-IP header when it holds a real address (else
    the peer's), IPv6 grouped by /64. An ISP gives each customer a whole /64, so counting single IPv6
    addresses would hand one person billions of separate allowances; and a header that isn't an
    address (forged, if the app is ever reached without the proxy) can't become an unbounded key."""
    for raw in ((request.headers.get(CLIENT_IP_HEADER) or "").strip() if CLIENT_IP_HEADER else "",
                request.client.host if request.client else ""):
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            continue
        if ip.version == 6:
            if ip.ipv4_mapped:                       # ::ffff:a.b.c.d is an IPv4 visitor
                return str(ip.ipv4_mapped)
            return str(ipaddress.ip_network(f"{ip}/64", strict=False))
        return str(ip)
    return "unknown"


def _same_site_only(request):
    """Refuse POSTs sent by other websites' pages: a page anywhere could otherwise make its visitors'
    browsers request reports here, spending their allowance and the site-wide one. Browsers label
    every request (Sec-Fetch-Site, Origin); the form's own fetch() is same-origin. Tools that send
    neither header are unaffected."""
    site = request.headers.get("sec-fetch-site")
    origin = request.headers.get("origin")
    if (site is not None and site not in ("same-origin", "none")) or \
            (origin is not None and (origin == "null" or urlsplit(origin).netloc != request.headers.get("host"))):
        raise HTTPException(403, "Requests from other websites are not accepted")

app = FastAPI(title="Jyothisha Insight", docs_url=None, redoc_url=None, openapi_url=None)


def _csp(template):
    """Content-Security-Policy: nothing loads or runs except the page's own script, allowed by the
    hash of the script in the page's TEMPLATE (so nothing put into the page later can run, even
    inside a <script>), Google Fonts, and fetch() to this site. No framing (clickjacking).
    The template's script must be fixed text; data goes in a type="application/json" block."""
    scripts = re.findall(r"<script>(.*?)</script>", template, re.S)
    assert not any("{{" in s for s in scripts), "a template script must not contain placeholders"
    hashes = " ".join("'sha256-%s'" % base64.b64encode(hashlib.sha256(s.encode()).digest()).decode() for s in scripts)
    script_src = hashes or "'none'"          # a page without scripts may run none
    return ("default-src 'none'; "
            f"script-src {script_src}; "
            "style-src 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; "
            "connect-src 'self'; img-src 'self' data:; form-action 'self'; "
            "base-uri 'none'; frame-ancestors 'none'")


INDEX_CSP = _csp(PAGE)


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


MAX_BODY = 64 * 1024     # the largest real form (E1 with 12 events, D3 with 5 proposals) is under 10 KB


class BodyLimit:
    """Refuse request bodies over MAX_BODY (413) before anything parses them. Starlette caps each
    form field at 1 MB, but would still read a body of any size, or spool a file part to disk."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        length = dict(scope["headers"]).get(b"content-length")
        if length is not None and (not length.isdigit() or int(length) > MAX_BODY):
            return await self._refuse(send)
        body, more = b"", True
        while more:                        # chunked bodies have no length: read up to the cap first
            msg = await receive()
            if msg["type"] != "http.request":
                return                     # client went away
            body += msg.get("body", b"")
            more = msg.get("more_body", False)
            if len(body) > MAX_BODY:
                return await self._refuse(send)
        replayed = False

        async def replay():
            nonlocal replayed
            if replayed:
                return await receive()
            replayed = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay, send)

    @staticmethod
    async def _refuse(send):
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"), (b"x-content-type-options", b"nosniff")]})
        await send({"type": "http.response.body", "body": b'{"detail":"Request too large"}'})


app.add_middleware(BodyLimit)


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(_index_html(), headers={"Content-Security-Policy": INDEX_CSP})


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
               .replace("{{LANG_OPTIONS}}", opt(catalog.LANG_NAMES.items())) \
               .replace("{{EVENT_OPTIONS}}", opt((k, v[0]) for k, v in jr.EVENT_TYPES.items())) \
               .replace("{{ORDER_LINK}}", order) \
               .replace("{{PAGE_DATA_JSON}}", _script_json({"place": placesearch.DEFAULT, "catalog": entries,
                                                            "order": order_cfg})) \
               .replace("{{PANCHANGA_LINK}}", '<a href="/panchanga">අද රාහු කාලය · Today’s Rahu kalaya</a><br>'
                         if PANCHANGA_PAGE else "") \
               .replace("{{SOURCE_URL}}", SOURCE_URL)


ACCURACY_PAGE = (HERE / "accuracy.html").read_text(encoding="utf-8")
CI_URL = SOURCE_URL + "/actions/workflows/ci.yml"


@lru_cache(maxsize=1)
def _accuracy_html():
    """The accuracy page, from the saved NASA comparison and the engine's own selftest names
    (built once: neither changes while the app runs)."""
    data = json.loads((ROOT / "docs" / "accuracy_jpl.json").read_text(encoding="utf-8"))
    checks = re.findall(r'^\s+check\(\s*"([^"]+)"', (ROOT / "jyotisha_calc.py").read_text(encoding="utf-8"), re.M)
    bodies = list(dict.fromkeys(r["body"] for r in data["rows"]))
    names = {c: jr.PLANET_SI[c] for c in bodies}
    by_date = {}
    for r in data["rows"]:
        by_date.setdefault(r["date_ut"], {})[r["body"]] = r["diff_arcsec"]
    year_now = str(date.today().year)
    rows = "".join(
        f'<tr><td>{d}</td>' + "".join(
            f'<td class="{"future" if d[:4] > year_now else ""}">{v[b]:+.2f}</td>' for b in bodies) + "</tr>"
        for d, v in by_date.items())
    past = data["max_abs_diff_arcsec_to_today"]
    fill = {
        "{{N_PAST_DATES}}": str(sum(1 for d in by_date if d[:4] <= year_now)),
        "{{REFERENCE}}": html.escape(data["reference"].split(", ")[-1]),
        "{{MAX_PAST}}": f"{past:.2f}",
        "{{LAGNA_SECONDS}}": f"{past / 15:.2f}",        # lagna ~1° per 240 s, so 1″ ≈ 1/15 s
        "{{BODY_HEADERS}}": "".join(f"<th>{html.escape(names[b])}</th>" for b in bodies),
        "{{ROWS}}": rows,
        "{{NOTE}}": html.escape(data["note"]),
        "{{GENERATED}}": html.escape(data["generated_utc"]) + " UTC",
        "{{N_CHECKS}}": str(len(checks)),
        "{{CHECKS}}": "".join(f"<li>{html.escape(c)}</li>" for c in checks),
        "{{CI_URL}}": CI_URL,
        "{{SOURCE_URL}}": SOURCE_URL,
    }
    page = ACCURACY_PAGE
    for k, v in fill.items():
        page = page.replace(k, v)
    return page


@app.get("/accuracy", response_class=HTMLResponse)
def accuracy():
    page = _accuracy_html()
    return HTMLResponse(page, headers={"Content-Security-Policy": _csp(ACCURACY_PAGE)})


# ---- daily panchanga / Rahu kalaya page. Its Rahu kalaya agrees within 2 minutes with the Sri Lankan
# almanac sites litha.lk, porondam.lk and suhadaastrology.lk (checked 2026-11-27, tests/test_panchanga.py).
# PANCHANGA_PAGE=0 switches it (and its link on the form page) off.
PANCHANGA_PAGE = os.environ.get("PANCHANGA_PAGE", "1") == "1"
# Each new date/town costs CPU, and Render's free instance has a fraction of one core: cap it like the search.
PANCHANGA_PER_IP = int(os.environ.get("PANCHANGA_PER_HOUR_PER_IP", "120"))
PANCHANGA_TOTAL = int(os.environ.get("PANCHANGA_PER_HOUR", "3000"))
_panchanga_limiter = _HourlyLimiter()
PANCHANGA_TEMPLATE = (HERE / "panchanga.html").read_text(encoding="utf-8")
TOWNS = json.loads((HERE / "places.json").read_text(encoding="utf-8"))["places"]   # [name, lat, lon, Sinhala]
SL_TZ = "Asia/Colombo"
WEEKDAY_SI = ["ඉරිදා", "සඳුදා", "අඟහරුවාදා", "බදාදා", "බ්‍රහස්පතින්දා", "සිකුරාදා", "සෙනසුරාදා"]   # Sunday first


def _clock(jd, day):
    """Sri Lankan 12-hour time, e.g. 'පෙ.ව. 10.30'; 'හෙට' (tomorrow) if it falls after `day`."""
    t = jr.jc.jd_to_datetime(jd + 30 / 86400).astimezone(ZoneInfo(SL_TZ))   # rounded to the minute
    ampm = "පෙ.ව." if t.hour < 12 else "ප.ව."
    s = f"{ampm} {(t.hour - 1) % 12 + 1}.{t.minute:02d}"
    return ("හෙට " + s) if t.date() > day else s


def _span(pair, day):
    """'පෙ.ව. 10.30 – 11.58': the second time drops the පෙ.ව./ප.ව. it shares with the first."""
    a, b = _clock(pair[0], day), _clock(pair[1], day)
    if a.split(" ")[0] == b.split(" ")[0] and not b.startswith("හෙට"):
        b = b.split(" ", 1)[1]
    return f"{a} – {b}"


def _panchanga_html(day, town):
    name, lat, lon, si = town
    jc = jr.jc
    p = jc.day_panchanga(day, lat, lon, SL_TZ)
    names = jr.pch_si({"vara": p["vara"] + "vara", "tithi": p["tithi"], "yoga": p["yoga"], "karana": p["karana"]})
    row = lambda k, v: f"<tr><th>{k}</th><td>{v}</td></tr>"  # noqa: E731
    until = lambda key: f" — {_clock(p[key + '_end'], day)} දක්වා"  # noqa: E731
    rows = "".join([
        row("හිරු උදාව · Sunrise", _clock(p["sunrise"], day)),
        row("හිරු බැසීම · Sunset", _clock(p["sunset"], day)),
        row("තිථිය · Tithi", html.escape(names["tithi"]) + until("tithi")),
        row("නැකත · Nakshatra", html.escape(jr.NAK_SI[p["nakshatra_index"]]) + until("nakshatra")),
        row("යෝගය · Yoga", html.escape(names["yoga"]) + until("yoga")),
        row("කරණය · Karana", html.escape(names["karana"]) + until("karana")),
        row("චන්ද්‍ර රාශිය · Moon sign", jr.SIGN_SI[jc.SIGNS.index(p["moon_sign"])]),
        row("යමගණ්ඩය · Yamaganda", _span(p["yamaganda"], day)),
        row("ගුලික කාලය · Gulika kalaya", _span(p["gulika"], day)),
    ])
    week = []
    for i in range(7):
        d = day + timedelta(days=i)
        w = p if i == 0 else jc.day_panchanga(d, lat, lon, SL_TZ)
        week.append(f"<tr{' class=today' if i == 0 else ''}><td>{d.day}/{d.month}<br>"
                    f"<span class=muted>{WEEKDAY_SI[w['weekday']]}</span></td><td>{_span(w['rahu'], d)}</td></tr>")
    town_opts = "".join(f'<option value="{html.escape(t[0])}"{" selected" if t[0] == name else ""}>'
                        f"{html.escape(t[3])} · {html.escape(t[0])}</option>" for t in TOWNS)
    fill = {
        "{{TITLE_DATE}}": day.isoformat(), "{{DATE_VALUE}}": day.isoformat(), "{{TOWN_OPTIONS}}": town_opts,
        "{{HEADING_DATE}}": f"{day.isoformat()} · {WEEKDAY_SI[p['weekday']]}",
        "{{RAHU}}": _span(p["rahu"], day), "{{TOWN}}": f"{html.escape(si)} · {html.escape(name)}",
        "{{ROWS}}": rows, "{{WEEK_ROWS}}": "".join(week), "{{SOURCE_URL}}": SOURCE_URL,
    }
    page = PANCHANGA_TEMPLATE
    for k, v in fill.items():
        page = page.replace(k, v)
    return page


# Pages already made, (date, town) -> HTML, most recently used last. A page costs about 35 ms of CPU
# (eight days of sunrise and Moon positions); from here it costs nothing and isn't rate-limited.
_PANCHANGA_PAGES = collections.OrderedDict()
PANCHANGA_CACHE = 512                      # ~12 KB each


@app.get("/panchanga", response_class=HTMLResponse)
async def panchanga_page(request: Request, date_: str = Query("", alias="date"), town: str = "Colombo"):
    if not PANCHANGA_PAGE:
        raise HTTPException(404, "Not Found")
    place = next((t for t in TOWNS if t[0] == town), None)
    if place is None:
        raise HTTPException(400, "Unknown town")
    if date_:
        day = _iso_date(date_, "Date")
        if not 1900 <= day.year <= 2100:
            raise HTTPException(400, "Date must be between 1900 and 2100")
    else:
        day = datetime.now(ZoneInfo(SL_TZ)).date()
    key = (day, place[0])
    page = _PANCHANGA_PAGES.get(key)
    if page is None:                       # only pages that must be computed count against the limits
        wait = _panchanga_limiter.check(_client_ip(request), PANCHANGA_PER_IP, PANCHANGA_TOTAL)
        if wait:
            raise HTTPException(429, "Too many requests, please try again later", headers={"Retry-After": str(wait)})
        page = await asyncio.to_thread(_panchanga_html, day, place)
        _PANCHANGA_PAGES[key] = page
        if len(_PANCHANGA_PAGES) > PANCHANGA_CACHE:
            _PANCHANGA_PAGES.popitem(last=False)
    _PANCHANGA_PAGES.move_to_end(key)
    # a dated page never changes; "today" must not outlive midnight in a cache
    cache = "public, max-age=86400" if date_ else "no-cache"
    return HTMLResponse(page, headers={"Content-Security-Policy": _csp(PANCHANGA_TEMPLATE), "Cache-Control": cache})


@app.post("/places")
async def places(request: Request, q: str = Form("")):
    """Town suggestions for the place box. POST, so what visitors type stays out of access logs."""
    _same_site_only(request)
    if len(placesearch.norm(q[:200])) < placesearch.MIN_QUERY:
        return {"places": []}
    if _search_limiter.check(_client_ip(request), SEARCH_PER_IP, SEARCH_TOTAL):
        raise HTTPException(429, "Too many searches. Enter the latitude and longitude instead, or try later.")
    return {"places": placesearch.search(q[:200])}


@app.get("/healthz")
def healthz():
    # RENDER_GIT_COMMIT is set by Render; shows which commit is live ("dev" when run locally)
    return {"ok": True, "version": os.environ.get("RENDER_GIT_COMMIT", "dev")[:7]}


# Control, format and unassigned characters are refused in text fields (they include the bidi
# overrides that would let a name display reversed); Sinhala needs the two joiners, so they stay.
SINHALA_JOINERS = {"‌", "‍"}
TIME_ZONES = frozenset(zoneinfo.available_timezones())


def _clean_text(value, field, required, max_len=60):
    """Collapse whitespace; 1-max_len chars (0 allowed if optional); no control chars and no < >.
    Names and places never need markup characters, and refusing them keeps HTML out of the
    report even if some template forgot to escape (the report also escapes, and its PDF
    renderer can't load files or URLs; see jyotisha_report.safe_url_fetcher)."""
    value = " ".join(value.split())
    if not (1 if required else 0) <= len(value) <= max_len:
        raise HTTPException(400, f"{field} must be {'1' if required else '0'}–{max_len} characters")
    if any(c in "<>" or (unicodedata.category(c)[0] == "C" and c not in SINHALA_JOINERS) for c in value):
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
    if tz not in TIME_ZONES:            # an allowlist: ZoneInfo() itself opens files named by the key
        raise HTTPException(400, f"{p}Unknown time zone")


def _render(args, workdir, files=None):
    out = Path(workdir) / "report.pdf"
    for fname, text in (files or {}).items():                   # e.g. matches.json for D3
        (Path(workdir) / fname).write_text(text, encoding="utf-8")
    # point file arguments at this request's own temporary folder
    args = [a.replace("{workdir}", workdir) if a.startswith(("--matches=", "--events=")) else a for a in args]
    # Its own process group, so a timeout also stops the calculation processes it starts
    posix = os.name == "posix"
    proc = subprocess.Popen([sys.executable, str(ROOT / "jyotisha_report.py"), *args, "--out", str(out)],
                            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                            env={**os.environ, "PYTHONIOENCODING": "utf-8"}, start_new_session=posix)
    try:
        _, err = proc.communicate(timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        if posix:
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
        proc.communicate()
        raise
    if proc.returncode != 0 or not out.exists():
        # Log only the error type, never the output: it can contain the client's name and birth data
        last = (err.strip().splitlines() or ["?"])[-1]
        print(f"report failed: exit {proc.returncode}: {last.split(':')[0][:80]}", file=sys.stderr)
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


def _events(birth_date, e_type, e_date, e_note):
    """Checked life events for E1 from the repeated e_* form fields."""
    if not len(e_type) == len(e_date):
        raise HTTPException(400, "Event details are incomplete")
    if not catalog.EVENTS_MIN <= len(e_type) <= catalog.EVENTS_MAX:
        raise HTTPException(400, f"Enter {catalog.EVENTS_MIN}–{catalog.EVENTS_MAX} past events")
    born = date.fromisoformat(birth_date)
    rows = []
    for i, (t, d) in enumerate(zip(e_type, e_date)):
        label = f"Event {i + 1}"
        if t not in jr.EVENT_TYPES:
            raise HTTPException(400, f"{label}: unknown kind of event")
        when = _iso_date(d, f"{label} date")
        if not born <= when <= date.today() + timedelta(days=1):   # +1: server is UTC, Sri Lanka is ahead
            raise HTTPException(400, f"{label}: the date must be between the birth date and today")
        note = _clean_text(e_note[i] if i < len(e_note) else "", f"{label} note", required=False)
        rows.append({"type": t, "date": when.isoformat(), "note": note})
    return rows


def _extra_args(report, birth_date, year, month, role="boy", partners=(), question="", topic="general",
                matter=None, task="general", m_from="", m_to="", m_hours="6-21", events=()):
    """Checked arguments for the report's extra input (see catalog.REPORTS), plus any files the
    report needs written into its temporary folder: ([args], {filename: text})."""
    needs = catalog.REPORTS[report][3]
    args, files = [], {}
    if needs == "events":
        files["events.json"] = json.dumps(list(events), ensure_ascii=False)
        args.append("--events={workdir}/events.json")
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
                 m_to: str = Form(""), m_hours: str = Form("6-21"),
                 e_type: list[str] = Form([]), e_date: list[str] = Form([]), e_note: list[str] = Form([]),
                 lang: str = Form("si")):
    _same_site_only(request)
    name = _validate(name, birth_date, birth_time, lat, lon, tz, report)
    if lang not in catalog.LANGS.get(report, ("si",)):
        raise HTTPException(400, f"Report {report} is only available in Sinhala")
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
    if lang != "si":
        args.append(f"--lang={lang}")
    events = ()
    if catalog.REPORTS[report][3] == "events":                       # ignored for other reports
        events = _events(birth_date, e_type, e_date, e_note)
    extra, files = _extra_args(report, birth_date, year, month, role, partners, question, topic, matter,
                               task, m_from, m_to, m_hours, events)
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
    filename = f"jyotisha_{report}{'_' + lang if lang != 'si' else ''}_{stamp}.pdf"
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"',
                             "Cache-Control": "no-store"})
