"""Two reports made at the same time into one folder must not share a calculation file.
Until 2026-11-27 every report wrote calc.json next to its PDF, so a build could read another's chart."""
import concurrent.futures as cf
from types import SimpleNamespace

import jyotisha_report as jr

PEOPLE = [("One", "1990-05-15", "10:30", 6.9271, 79.8612), ("Two", "1992-08-20", "07:45", 7.2906, 80.6337),
          ("Three", "1985-01-02", "23:10", 9.6615, 80.0255), ("Four", "2001-12-31", "04:05", 6.0535, 80.2210)]


def calc(person, workdir):
    name, date, time, lat, lon = person
    a = SimpleNamespace(name=name, date=date, time=time, lat=lat, lon=lon, tz="Asia/Colombo", place="",
                        node="mean", report="A1")
    return jr.run_calc(a, 2026, 2027, str(workdir))


def test_parallel_calculations_in_one_folder_keep_their_own_charts(tmp_path):
    with cf.ThreadPoolExecutor(max_workers=len(PEOPLE)) as ex:
        results = list(ex.map(lambda p: calc(p, tmp_path), PEOPLE * 2))
    for person, d in zip(PEOPLE * 2, results):
        assert (d["name"], d["birth"]["date"], d["birth"]["time"]) == person[:3]
    assert list(tmp_path.iterdir()) == []          # each call removes its own file
