#!/usr/bin/env python3
"""Download the Swiss Ephemeris data files into ./ephe/ and verify their SHA-256.

    python fetch_ephe.py [target_dir]

Pinned to one upstream commit, so builds can't silently pick up changed files: upstream
replaced sepl_18/seas_18 on 2026-11-21 ("compressed ephemeris update"). These are the May 2026
files that jyotisha_calc.py --selftest was verified with. To upgrade, change COMMIT and the
hashes together and run the selftest.
"""
import hashlib
import pathlib
import sys
import urllib.request

COMMIT = "cae9ecd4b201544d85e411aced17660932514d43"   # aloistr/swisseph, 2026-05-29
FILES = {
    "sepl_18.se1": "ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66",
    "semo_18.se1": "1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7",
    "seas_18.se1": "a2cd8fc33807c78ca9a700c91c2e042258b12fc4796519e00781440b5ad8b2e2",
}
URL = "https://raw.githubusercontent.com/aloistr/swisseph/{}/ephe/{}"


def main():
    target = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).parent / "ephe")
    target.mkdir(parents=True, exist_ok=True)
    for name, want in FILES.items():
        data = urllib.request.urlopen(URL.format(COMMIT, name), timeout=60).read()
        got = hashlib.sha256(data).hexdigest()
        if got != want:
            sys.exit(f"{name}: SHA-256 mismatch (got {got}, expected {want}); not writing it")
        (target / name).write_bytes(data)
        print(f"{name}: ok ({len(data)} bytes)")


if __name__ == "__main__":
    main()
