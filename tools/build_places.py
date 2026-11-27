"""Build web/places_lk.json, the website's town search list, from the GeoNames Sri Lanka file.

    curl -O https://download.geonames.org/export/dump/LK.zip
    python -I tools/build_places.py LK.zip

GeoNames (https://www.geonames.org) is CC BY 4.0: the site credits it under the form.
Every populated place is kept (towns, villages, suburbs; not historical or abandoned ones), with
its district (or province where GeoNames gives no district) for telling same-named villages apart.
The curated town centres in web/places.json are merged in: their coordinates and Sinhala names
win, and they rank first in search.
"""
import datetime as dt
import heapq
import json
import math
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "places_lk.json"
CURATED = ROOT / "web" / "places.json"

KEEP = {"PPL", "PPLA", "PPLA2", "PPLA3", "PPLA4", "PPLC", "PPLX", "PPLL", "PPLS", "PPLF", "PPLR", "PPLG"}
DISTRICT_SI = {
    "Colombo": "කොළඹ", "Gampaha": "ගම්පහ", "Kalutara": "කළුතර", "Kandy": "මහනුවර", "Matale": "මාතලේ",
    "Nuwara Eliya": "නුවරඑළිය", "Galle": "ගාල්ල", "Matara": "මාතර", "Hambantota": "හම්බන්තොට",
    "Jaffna": "යාපනය", "Kilinochchi": "කිලිනොච්චිය", "Mannar": "මන්නාරම", "Vavuniya": "වවුනියාව",
    "Mullaitivu": "මුලතිව්", "Batticaloa": "මඩකලපුව", "Ampara": "අම්පාර", "Trincomalee": "ත්‍රිකුණාමලය",
    "Kurunegala": "කුරුණෑගල", "Puttalam": "පුත්තලම", "Anuradhapura": "අනුරාධපුරය", "Polonnaruwa": "පොළොන්නරුව",
    "Badulla": "බදුල්ල", "Moneragala": "මොණරාගල", "Ratnapura": "රත්නපුර", "Kegalle": "කෑගල්ල",
}
PROVINCE_SI = {
    "Western": "බස්නාහිර", "Central": "මධ්‍යම", "Southern": "දකුණු", "Northern": "උතුරු", "Eastern": "නැගෙනහිර",
    "North Western": "වයඹ", "North Central": "උතුරු මැද", "Uva": "ඌව", "Sabaragamuwa": "සබරගමුව",
}


def sinhala(s):
    return any("඀" <= c <= "෿" for c in s)


def tamil(s):
    return any("஀" <= c <= "௿" for c in s)


def km(a, b):
    """Rough distance in km between (lat, lon) points; plenty for 'is this the same town'."""
    dy = (a[0] - b[0]) * 111.0
    dx = (a[1] - b[1]) * 111.0 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot(dx, dy)


def area_labels(rows):
    """{("29", "21"): "Kandy District · මහනුවර දිස්ත්‍රික්කය", ("29", ""): "Central Province · ..."}"""
    out = {}
    for r in rows:
        if r[7] == "ADM2":
            d = r[1].removesuffix(" District")
            out[(r[10], r[11])] = f"{d} District · {DISTRICT_SI[d]} දිස්ත්‍රික්කය"
        elif r[7] == "ADM1":
            p = r[1].removesuffix(" Province").removeprefix("Province of ")
            out[(r[10], "")] = f"{p} Province · {PROVINCE_SI[p]} පළාත"
    return out


def alternates(name, field):
    """Alternate names worth matching: Sinhala, Tamil, and capitalised Latin spellings
    (e.g. Mahanuwara for Kandy). Codes like 'CMB' and foreign transliterations are dropped."""
    seen, out = {name.casefold()}, []
    for a in field.split(","):
        a = a.strip()
        ok = sinhala(a) or tamil(a) or (a.isascii() and len(a) >= 4 and a[0].isupper() and not a.isupper())
        if ok and a.casefold() not in seen:
            seen.add(a.casefold())
            out.append(a)
    return out


def rank(code, population, seat, coded):
    """0 curated (set later), 1 provincial/district capital, 2 a town: has a population figure, is
    the seat of its Divisional Secretariat, or has a station/airport code (e.g. HIM, Hingurakgoda);
    3 everything else (villages, hamlets)."""
    if code in ("PPLC", "PPLA", "PPLA2"):
        return 1
    return 2 if population > 0 or code in ("PPLA3", "PPLA4") or seat or coded else 3


def fill_districts(places):
    """GeoNames leaves the district off some towns (Kandy, Galle). Take it from the five nearest
    places when they all agree, are in the same province and lie within 10 km; else keep the province."""
    known = [p for p in places if p["district"]]
    filled = 0
    for p in places:
        if p["district"]:
            continue
        near = heapq.nsmallest(5, known, key=lambda q: (q["lat"] - p["lat"]) ** 2 + (q["lon"] - p["lon"]) ** 2)
        if (len({q["area"] for q in near}) == 1 and all(q["admin1"] == p["admin1"] for q in near)
                and all(km((q["lat"], q["lon"]), (p["lat"], p["lon"])) < 10 for q in near)):
            p["area"], filled = near[0]["area"], filled + 1
    print(f"district filled in from neighbours for {filled} of {len(places) - len(known)} places")


def build(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        rows = [line.split("\t") for line in z.read("LK.txt").decode("utf-8").splitlines() if line]
    areas = area_labels(rows)
    # Divisional Secretariat divisions (ADM3, "Hingurakgoda Division") are named after their main town
    seats = {(r[10], r[11], r[1].removesuffix(" Division").casefold()) for r in rows if r[7] == "ADM3"}
    places = []
    for r in rows:
        if r[6] != "P" or r[7] not in KEEP:
            continue
        name = " ".join(r[1].split())
        if not name or len(name) > 60 or any(c in name for c in "<>&\"") or not name.isprintable():
            continue
        alts = alternates(name, r[3])
        population = int(r[14] or 0)
        district = areas.get((r[10], r[11])) if r[11] else None
        places.append({"name": name, "si": next((a for a in alts if sinhala(a)), ""),
                       "lat": round(float(r[4]), 4), "lon": round(float(r[5]), 4),
                       "area": district or areas.get((r[10], ""), ""), "district": bool(district), "admin1": r[10],
                       "rank": rank(r[7], population, (r[10], r[11], name.casefold()) in seats,
                                    any(len(a) == 3 and a.isupper() and a.isalpha() for a in r[3].split(","))),
                       "pop": population,
                       "fame": sum(1 for a in r[3].split(",") if a.strip()), "alts": alts})
    fill_districts(places)

    curated = json.loads(CURATED.read_text(encoding="utf-8"))["places"]
    for name, lat, lon, si in curated:
        dist = lambda p: km((p["lat"], p["lon"]), (lat, lon))  # noqa: E731
        near = [p for p in places if p["name"].casefold() == name.casefold() and dist(p) < 15]
        towns = [p for p in places if p["rank"] <= 2 and dist(p) < 2]
        if near:
            p = min(near, key=dist)
        elif towns:   # GeoNames spells it differently (Mullaittivu): same town, use our spelling
            p = min(towns, key=dist)
            print(f"note: {name} is spelled {p['name']} in GeoNames; using {name}")
            p["alts"] = [p["name"]] + [a for a in p["alts"] if a.casefold() != name.casefold()]
            p["name"] = name
        else:         # not in GeoNames at all: add it, in the nearest place's area
            p = {"name": name, "si": "", "lat": 0, "lon": 0, "area": min(places, key=dist)["area"],
                 "district": True, "admin1": "", "rank": 0, "pop": 0, "fame": 0, "alts": []}
            places.append(p)
            print(f"note: {name} is not in GeoNames; added (area {p['area']})")
        p.update(lat=lat, lon=lon, rank=0)
        if si not in p["alts"]:
            p["alts"].insert(0, si)
        p["si"] = si

    places.sort(key=lambda p: (p["rank"], -p["pop"], -p["fame"], p["name"], p["area"]))
    area_list = sorted({p["area"] for p in places})
    index = {a: i for i, a in enumerate(area_list)}
    lines = ",\n".join(json.dumps([p["name"], p["si"], p["lat"], p["lon"], index[p["area"]], p["rank"], p["pop"], p["fame"], p["alts"]],
                                  ensure_ascii=False, separators=(",", ":")) for p in places)
    head = {
        "_note": "Generated by tools/build_places.py; edit web/places.json (curated towns) instead.",
        "source": f"GeoNames LK.txt, downloaded {dt.date.today().isoformat()}, CC BY 4.0 (https://www.geonames.org); "
                  "curated town centres from web/places.json",
        "fields": ["name", "sinhala", "lat", "lon", "area", "rank", "population", "fame", "alternate names"],
        "areas": area_list,
    }
    body = json.dumps(head, ensure_ascii=False, indent=1)[:-2]
    OUT.write_text(body + ',\n "places": [\n' + lines + "\n]}\n", encoding="utf-8", newline="\n")
    print(f"{len(places)} places, {len(area_list)} areas -> {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.stdout.reconfigure(encoding="utf-8")
    build(sys.argv[1])
