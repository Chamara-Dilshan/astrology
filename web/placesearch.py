"""Town search for the website's place box: every Sri Lankan town and village in places_lk.json.

Matches the start of the name ("hingu" -> Hingurakgoda), of a later word in it ("kotte" ->
Sri Jayewardenepura Kotte), the name without spaces ("nuwaraeliya"), and alternate names,
including Sinhala and Tamil ones ("මහනුවර" -> Kandy). Exact matches come first, then matches
on the place's own name, then better-known places: curated towns, district capitals, other
towns (see tools/build_places.py), then villages with more recorded names.
Lookups use a sorted key list and binary search, so a query costs microseconds, not a scan.
"""
import bisect
import json
import re
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
_DATA = json.loads((HERE / "places_lk.json").read_text(encoding="utf-8"))
AREAS = _DATA["areas"]
PLACES = _DATA["places"]   # [name, sinhala, lat, lon, area index, rank, population, fame, alternates]
MIN_QUERY, MAX_QUERY, MAX_RESULTS = 2, 40, 12

_JOINERS = dict.fromkeys(map(ord, "‌‍"))   # Sinhala conjuncts are typed with or without a joiner


def norm(text):
    """Case-, space- and joiner-insensitive form used for matching."""
    text = unicodedata.normalize("NFC", text).translate(_JOINERS).casefold()
    return " ".join(text.split())


def _compact(text):
    return re.sub(r"[\s\-'.]", "", text)


def _build_keys():
    """(key, kind, place index), sorted. kind 0: the name; 1: a later word of it; 2: an alternate."""
    keys = set()
    for i, p in enumerate(PLACES):
        for kind, names in ((0, [p[0]]), (2, p[8])):
            for n in map(norm, names):
                keys.update({(n, kind, i), (_compact(n), kind, i)})
                words = re.split(r"[\s\-]+", n)
                keys.update((" ".join(words[k:]), max(kind, 1), i) for k in range(1, len(words)))
    return sorted(k for k in keys if k[0])


_KEYS = _build_keys()
_TEXT = [k[0] for k in _KEYS]


def public(p):
    return {"name": p[0], "si": p[1], "lat": p[2], "lon": p[3], "area": AREAS[p[4]]}


def search(query):
    """Up to MAX_RESULTS places for what the visitor has typed so far, best first."""
    q = norm(query)[:MAX_QUERY]
    if len(q) < MIN_QUERY:
        return []
    best = {}
    for qq in {q, _compact(q)}:
        for j in range(bisect.bisect_left(_TEXT, qq), len(_KEYS)):
            key, kind, i = _KEYS[j]
            if not key.startswith(qq):
                break
            score = (key != qq, kind)          # (exact match first, then name / word / alternate)
            if score < best.get(i, (2, 0)):
                best[i] = score
    # exact first; then the place's own name before an alternate; then the better-known place
    rank = lambda i: (best[i][0], best[i][1] == 2, PLACES[i][5], best[i][1], -PLACES[i][6], -PLACES[i][7], PLACES[i][0])  # noqa: E731
    order = sorted(best, key=rank)
    return [public(PLACES[i]) for i in order[:MAX_RESULTS]]


DEFAULT = public(next(p for p in PLACES if p[0] == "Colombo"))
