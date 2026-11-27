"""The lock files (what Docker and CI install, with hashes) must still satisfy the requirements*.txt
they were generated from, so a floor raised for a security fix can't be forgotten in the lock."""
import re
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parent.parent


def wanted(name):
    """Requirements in a requirements*.txt, following its -r includes."""
    out = []
    for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line.startswith("-r "):
            out += wanted(line[3:].strip())
        elif line:
            out.append(Requirement(line))
    return out


def pins(name):
    """{package: (version, number of hashes)} from a pip-compile lock."""
    text = (ROOT / name).read_text(encoding="utf-8")
    blocks = re.findall(r"^([A-Za-z0-9_.-]+)==(\S+)((?:\s*\\\s*--hash=sha256:[0-9a-f]{64})*)", text, re.M)
    return {canonicalize_name(n): (v, b.count("--hash=")) for n, v, b in blocks}


def test_every_requirement_is_pinned_within_its_bounds():
    for txt, lock in (("requirements.txt", "requirements.lock"), ("requirements-web.txt", "requirements.lock"),
                      ("requirements-dev.txt", "requirements-dev.lock")):
        locked = pins(lock)
        for req in wanted(txt):
            name = canonicalize_name(req.name)
            assert name in locked, f"{req.name} ({txt}) is missing from {lock}"
            assert req.specifier.contains(locked[name][0], prereleases=True), \
                f"{lock} pins {req.name}=={locked[name][0]}, outside {req.specifier} in {txt}: regenerate the locks"


def test_every_pin_has_hashes_and_the_locks_agree():
    run, dev = pins("requirements.lock"), pins("requirements-dev.lock")
    assert run and dev
    assert all(n >= 1 for _, n in run.values()) and all(n >= 1 for _, n in dev.values())
    assert {k: v[0] for k, v in run.items()} == {k: dev[k][0] for k in run}, "the two locks pin different versions"
