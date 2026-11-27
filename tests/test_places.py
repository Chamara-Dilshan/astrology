"""Town search for the place box (web/placesearch.py, POST /places) and its data file.

places_lk.json is built by tools/build_places.py from the GeoNames Sri Lanka list, with the
curated town centres of web/places.json merged in.
"""
import json

import pytest
from fastapi.testclient import TestClient

from web import app as web
from web import placesearch as ps

CURATED = json.loads((web.HERE / "places.json").read_text(encoding="utf-8"))["places"]


@pytest.fixture
def client(monkeypatch):
    web._search_limiter.reset()
    monkeypatch.setattr(web, "SEARCH_PER_IP", 1000)
    monkeypatch.setattr(web, "SEARCH_TOTAL", 1000)
    return TestClient(web.app)


def names(query):
    return [p["name"] for p in ps.search(query)]


# ---------------------------------------------------------------- the data

def test_data_covers_the_whole_island():
    assert len(ps.PLACES) > 15000
    for name, si, lat, lon, area, rank, pop, fame, alts in ps.PLACES:
        assert 5.8 < lat < 9.9 and 79.5 < lon < 82.0, name          # inside Sri Lanka
        assert 0 < len(name) <= 60 and name.isprintable()           # fits the form's place field
        assert not set(name) & set("<>&\""), name                   # the server refuses these characters
        assert 0 <= area < len(ps.AREAS) and rank in (0, 1, 2, 3)
    districts = {a.split(" ·")[0] for a in ps.AREAS if " District" in a}
    assert len(districts) == 25                                     # all 25 districts


def test_curated_towns_keep_their_coordinates_and_rank_first():
    by_name = {}
    for p in ps.PLACES:
        if p[5] == 0:
            by_name[p[0]] = p
    assert set(by_name) == {c[0] for c in CURATED}
    for name, lat, lon, si in CURATED:
        p = by_name[name]
        assert (p[2], p[3], p[1]) == (lat, lon, si)                 # same as before the full list
        assert names(name)[0] == name                               # and found first by name


# ---------------------------------------------------------------- matching

@pytest.mark.parametrize("query, first", [
    ("kand", "Kandy"),                        # start of the name, best-known first
    ("Hingu", "Hingurakgoda"),                # a town outside the curated list
    ("nuwaraeliya", "Nuwara Eliya"),          # spaces don't matter
    ("NUWARA  ELIYA", "Nuwara Eliya"),        # nor case or doubled spaces
    ("borella", "Borella"),                   # a Colombo suburb
    ("mullaittivu", "Mullaitivu"),            # GeoNames spelling finds our spelling
    ("මහනුවර", "Kandy"),                      # Sinhala name
    ("මහනු", "Kandy"),                        # start of the Sinhala name
    ("ත්‍රිකුණාමලය", "Trincomalee"),          # Sinhala with the joiner (ZWJ) ...
    ("ත්රිකුණාමලය", "Trincomalee"),           # ... and without it
    ("யாழ்", "Jaffna"),                       # Tamil name
])
def test_search_finds(query, first):
    assert names(query)[0] == first


def test_search_matches_later_words_and_alternate_names():
    assert "Sri Jayewardenepura Kotte" in names("kotte")[:3]
    assert names("mahanuwara")[0] == "Kandy"                     # a Latin alternate name


def test_same_named_villages_are_told_apart_by_district():
    found = [p for p in ps.search("maharagama") if p["name"] == "Maharagama"]
    assert len(found) == 2
    assert found[0]["area"].startswith("Colombo District")       # the big suburb first
    assert found[0]["area"] != found[1]["area"]


def test_search_limits():
    assert ps.search("") == ps.search("k") == []                # too short to be useful
    assert len(ps.search("ka")) == ps.MAX_RESULTS
    assert ps.search("london") == []
    assert ps.search("x" * 500) == []                           # long input is cut, not an error


def test_result_shape():
    p = ps.search("hingurakgoda")[0]
    assert set(p) == {"name", "si", "lat", "lon", "area"}
    assert p["area"].startswith("Polonnaruwa District")
    assert abs(p["lat"] - 8.03) < 0.05 and abs(p["lon"] - 80.95) < 0.05


# ---------------------------------------------------------------- the endpoint

def test_places_endpoint(client):
    r = client.post("/places", data={"q": "polonnaruwa"})
    assert r.status_code == 200
    first = r.json()["places"][0]
    assert first["name"] == "Polonnaruwa" and (first["lat"], first["lon"]) == (7.9403, 81.0188)
    assert client.post("/places", data={"q": "k"}).json() == {"places": []}
    assert client.post("/places").json() == {"places": []}


def test_places_is_post_only(client):
    """GET would put what visitors type into the server's access log."""
    assert client.get("/places", params={"q": "kandy"}).status_code == 405


def test_places_rate_limit(client, monkeypatch):
    monkeypatch.setattr(web, "SEARCH_PER_IP", 3)
    for _ in range(3):
        assert client.post("/places", data={"q": "kandy"}).status_code == 200
    r = client.post("/places", data={"q": "kandy"})
    assert r.status_code == 429
    assert client.post("/places", data={"q": "k"}).status_code == 200     # too short: not searched, not counted
    other = {web.CLIENT_IP_HEADER: "203.0.113.9"}
    assert client.post("/places", data={"q": "kandy"}, headers=other).status_code == 200


def test_picked_place_makes_a_report(client, monkeypatch):
    """A suggestion's name and coordinates go straight into the report form."""
    seen = []
    monkeypatch.setattr(web, "_render", lambda args, workdir, files=None: seen.append(args) or b"%PDF-1.7 fake")
    monkeypatch.setattr(web, "REPORTS", dict(web.ALL_REPORTS))
    web._limiter.reset()
    p = client.post("/places", data={"q": "hingurakgoda"}).json()["places"][0]
    r = client.post("/report", data=dict(name="S", birth_date="1990-05-15", birth_time="10:30", place=p["name"],
                                         lat=str(p["lat"]), lon=str(p["lon"]), tz="Asia/Colombo", report="G"))
    assert r.status_code == 200
    assert "--place=Hingurakgoda" in seen[0] and f"--lat={p['lat']:.4f}" in seen[0]
