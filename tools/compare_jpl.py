#!/usr/bin/env python3
"""Compare our planet positions with NASA/JPL Horizons (DE441) and save the result.

    python tools/compare_jpl.py            # writes docs/accuracy_jpl.json

For each date and body, Horizons gives the geocentric apparent ecliptic longitude of date
(light-time, aberration and light deflection included). We ask our engine's ephemeris
(pyswisseph with the pinned .se1 files that jyotisha_calc.py loads) for the same quantity:
the tropical position, before the ayanamsa is subtracted. The website's accuracy page shows
the differences. Needs internet (Horizons); the test suite re-checks the saved file offline.
"""
import datetime as dt
import json
import pathlib
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import jyotisha_calc as jc  # noqa: E402  (sets the ephemeris path to ./ephe)
import swisseph as swe  # noqa: E402

BODIES = {"Su": ("10", swe.SUN), "Mo": ("301", swe.MOON), "Ma": ("499", swe.MARS), "Me": ("199", swe.MERCURY),
          "Ju": ("599", swe.JUPITER), "Ve": ("299", swe.VENUS), "Sa": ("699", swe.SATURN)}
DATES_UT = ["1850-01-01 00:00", "1900-06-15 12:00", "1950-03-21 06:00", "1990-05-15 05:00",
            "2000-01-01 12:00", "2026-11-27 00:00", "2050-12-31 18:00", "2100-07-04 00:00"]
API = "https://ssd.jpl.nasa.gov/api/horizons.api"


def jd_ut(s):
    d = dt.datetime.strptime(s, "%Y-%m-%d %H:%M")
    return swe.julday(d.year, d.month, d.day, d.hour + d.minute / 60)


def horizons(command, jds):
    params = {"format": "json", "COMMAND": f"'{command}'", "OBJ_DATA": "'NO'", "MAKE_EPHEM": "'YES'",
              "EPHEM_TYPE": "'OBSERVER'", "CENTER": "'500@399'", "QUANTITIES": "'31'", "ANG_FORMAT": "'DEG'",
              "TIME_TYPE": "'UT'", "TLIST_TYPE": "'JD'", "TLIST": " ".join(f"'{j:.6f}'" for j in jds),
              "CSV_FORMAT": "'YES'"}
    res = json.load(urllib.request.urlopen(API + "?" + urllib.parse.urlencode(params), timeout=120))
    text = res["result"]
    if "$$SOE" not in text:
        raise RuntimeError(f"Horizons error for {command}: {text[:400]}")
    rows = [r.split(",") for r in text[text.index("$$SOE") + 5:text.index("$$EOE")].strip().splitlines()]
    # CSV columns: date, (blank), (blank), ObsEcLon, ObsEcLat
    lons = [float(next(c for c in r[1:] if c.strip() and c.strip().replace(".", "", 1).replace("-", "", 1).isdigit()))
            for r in rows]
    source = "DE441" if "DE441" in text else "?"
    return lons, source


def ours(pid, jd):
    xx, _ = swe.calc_ut(jd, pid, swe.FLG_SWIEPH)   # tropical, apparent, ecliptic of date
    return xx[0]


def diff_arcsec(a, b):
    d = (a - b + 180) % 360 - 180
    return d * 3600


def main():
    jds = [jd_ut(s) for s in DATES_UT]
    rows, sources = [], set()
    for code, (command, pid) in BODIES.items():
        lons, src = horizons(command, jds)
        sources.add(src)
        for s, jd, lon in zip(DATES_UT, jds, lons):
            o = ours(pid, jd)
            rows.append({"date_ut": s, "body": code, "jpl": round(lon, 7), "ours": round(o, 7),
                         "diff_arcsec": round(diff_arcsec(o, lon), 3)})
    out = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "reference": "NASA/JPL Horizons API, " + ", ".join(sorted(sources)),
        "ours": f"Swiss Ephemeris {swe.version} with files from {jc.EPHE_PATH and pathlib.Path(jc.EPHE_PATH).name}/",
        "quantity": "geocentric apparent ecliptic longitude of date (tropical)",
        "max_abs_diff_arcsec": max(abs(r["diff_arcsec"]) for r in rows),
        "max_abs_diff_arcsec_to_today": max(abs(r["diff_arcsec"]) for r in rows if r["date_ut"][:4] <= "2026"),
        # Checked 2026-11-27: comparing in TT (no Delta-T) the 2100 Moon agrees to 0.19". Future dates differ
        # only because Horizons holds Delta-T at its last value (69.18 s) while Swiss Ephemeris extrapolates it.
        "note": "Differences for future dates come from Delta-T (Earth-rotation) forecasts, not the ephemeris: "
                "Horizons keeps Delta-T fixed for future dates while Swiss Ephemeris extrapolates it. "
                "Compared in TT, the 2100 Moon agrees to 0.19 arcseconds.",
        "rows": rows,
    }
    path = ROOT / "docs" / "accuracy_jpl.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"{len(rows)} comparisons, max |difference| {out['max_abs_diff_arcsec']}\" -> {path}")


if __name__ == "__main__":
    main()
