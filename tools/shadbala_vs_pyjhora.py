"""Cross-check jyotisha_calc.shadbala against PyJHora (a Python port of Jagannatha Hora), component by component.

PyJHora pins old libraries, so it lives in its own environment (Python 3.11):

    py -3.11 -m venv jhvenv && jhvenv\\Scripts\\pip install PyJHora==5.0.6
    python tools/shadbala_vs_pyjhora.py jhvenv\\Scripts\\python.exe

Result on 2026-11-27 (PyJHora 5.0.6, 8 charts: Sri Lanka, London, night/dawn/dusk births, a planetary war):
  identical (<= 0.05 virupa): uchcha, saptavargaja, ojayugma, kendradi, drekkana, tribhaga, abda, masa,
    vara, ayana, drik.
  every other difference is a PyJHora defect, not a convention:
    dig and paksha bala: angles above 180 deg are not folded (values up to 114, or negative; ours + theirs = 120);
    chesta bala: same, plus mean and true longitudes averaged across 0/360 (e.g. London 1988 Mars);
    hora bala: its hora-lord formula disagrees with the textbook rule (first hora = weekday lord), which
      both books' examples follow;
    yuddha bala: applied to the two closest planets however far apart (BPHS: within 1 degree);
    nathonnata: its midnight is off by minutes on some dates (up to 1.7 virupa at London in December).
  Chesta bala of Mercury/Venus also differs by convention: PyJHora uses Raman's Surya-Siddhanta tables
  for mean positions, we use modern mean elements (Mercury's sighrocca differs by ~12 deg, ~4 virupas).
The worked examples in Raman's and V.P. Jain's books are checked in tests/test_shadbala.py and --selftest.
"""
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

CHARTS = [  # name, local datetime, tz name, lat, lon
    ("Colombo 1990", dt.datetime(1990, 5, 15, 10, 30), "Asia/Colombo", 6.9271, 79.8612),
    ("Jaffna 1975 night", dt.datetime(1975, 1, 3, 23, 50), "Asia/Colombo", 9.6615, 80.0255),
    ("Kandy 2004 pre-dawn", dt.datetime(2004, 9, 21, 5, 5), "Asia/Colombo", 7.2906, 80.6337),
    ("Polonnaruwa 1999", dt.datetime(1999, 10, 28, 8, 5), "Asia/Colombo", 7.9403, 81.0188),
    ("London 1988", dt.datetime(1988, 12, 1, 14, 0), "Europe/London", 51.5074, -0.1278),
    ("Galle 2010 dusk", dt.datetime(2010, 3, 15, 18, 45), "Asia/Colombo", 6.0535, 80.2210),
    ("Matara 1965", dt.datetime(1965, 7, 4, 3, 20), "Asia/Colombo", 5.9549, 80.5550),
    ("Colombo 2020 Ju-Sa war", dt.datetime(2020, 12, 21, 18, 30), "Asia/Colombo", 6.9271, 79.8612),
]
KEYS = ["uchcha", "saptavargaja", "ojayugma", "kendradi", "drekkana", "DIG", "nathonnata", "paksha", "tribhaga",
        "abda", "masa", "vara", "hora", "ayana", "yuddha", "CHESTA", "DRIK"]


def pyjhora_side(spec_path):
    """Runs inside the PyJHora environment: print PyJHora's components for each chart as JSON."""
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        from jhora import const, utils
        from jhora.horoscope.chart import charts, strength
        from jhora.panchanga import drik
        drik.set_ayanamsa_mode("LAHIRI")
    out = []
    for c in json.loads(Path(spec_path).read_text()):
        place = drik.Place(c["name"], c["lat"], c["lon"], c["tz"])
        jd = utils.julian_day_number(tuple(c["date"]), tuple(c["time"]))
        with contextlib.redirect_stdout(io.StringIO()):
            pp1 = charts.divisional_chart(jd, place, divisional_chart_factor=1)[:const._pp_count_upto_ketu]
            pp9 = charts.divisional_chart(jd, place, divisional_chart_factor=9)[:const._pp_count_upto_ketu]
            s = strength
            r = {"uchcha": s._uchcha_bala(pp1), "saptavargaja": s._sapthavargaja_bala1(jd, place),
                 "ojayugma": s._ojayugama_bala(pp1, pp9), "kendradi": s._kendra_bala(pp1), "drekkana": s._dreshkon_bala(pp1),
                 "DIG": s._dig_bala(jd, place), "nathonnata": s._nathonnath_bala(jd, place),
                 "paksha": s._paksha_bala(jd, place), "tribhaga": s._tribhaga_bala(jd, place),
                 "abda": s._abdadhipathi(jd, place), "masa": s._masadhipathi(jd, place), "vara": s._vaaradhipathi(jd, place),
                 "hora": s._hora_bala(jd, place), "ayana": s._ayana_bala(jd, place), "yuddha": s._yuddha_bala(jd, place),
                 "CHESTA": s._cheshta_bala_new(jd, place, use_epoch_table=True), "DRIK": s._drik_bala(jd, place)}
        out.append({k: [float(x) for x in v][:7] for k, v in r.items()})
    print(json.dumps(out))


def main(pyjhora_python):
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))
    import tempfile
    import jyotisha_calc as jc
    spec = []
    for name, when, tz, lat, lon in CHARTS:
        off = when.replace(tzinfo=jc.ZoneInfo(tz)).utcoffset().total_seconds() / 3600
        spec.append({"name": name, "date": [when.year, when.month, when.day], "time": [when.hour, when.minute, 0],
                     "lat": lat, "lon": lon, "tz": off})
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "charts.json"
        path.write_text(json.dumps(spec))
        jh = json.loads(subprocess.run([pyjhora_python, "-I", __file__, "--pyjhora-side", str(path)],
                                       capture_output=True, text=True, check=True).stdout)
    worst = {k: 0.0 for k in KEYS}
    for (name, when, tz, lat, lon), theirs in zip(CHARTS, jh):
        jd, _ = jc.to_jd_ut(when, tz)
        pos, _ = jc.compute_positions(jd)
        sb = jc.shadbala(jd, lat, lon, tz, pos, jc.compute_lagna(jd, lat, lon), jc.sripati_bhavas(jd, lat, lon, pos)["madhya"])
        print(f"\n{name}")
        for k in KEYS:
            ours = [{**o["sthana"], **o["kala"], "DIG": o["dig"], "CHESTA": o["chesta"], "DRIK": o["drik"]}[k]
                    for o in (sb[p] for p in jc.SEVEN)]
            diff = max(abs(a - b) for a, b in zip(ours, theirs[k]))
            worst[k] = max(worst[k], diff)
            if diff > 0.6:
                print(f"  {k:12} " + "  ".join(f"{p} {a:.2f}/{b:.2f}" for p, a, b in zip(jc.SEVEN, ours, theirs[k]) if abs(a - b) > 0.6))
    print("\nlargest difference per component, virupas (ours vs PyJHora):")
    print("  " + ", ".join(f"{k} {v:.2f}" for k, v in worst.items()))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--pyjhora-side":
        pyjhora_side(sys.argv[2])
    elif len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        sys.exit(__doc__)
