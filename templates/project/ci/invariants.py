#!/usr/bin/env python3
"""Check the shared sdlc files, whichever agent or person changed them (seeded by the sdlc plugin v{{plugin_version}}).

Only active features count (`Status: active` in their state file):
  - the record matches the phase reached: past Define (Stage 1), the change file (<docs>/changes/<feature>.md) has its
    `## Acceptance tests` table; in Ship (Stage 4), its `## Review` section says what was reviewed.
  - the baseline: against --base, a new row or a higher lint count needs a feature's Deviations entry naming it.
  - past Define, each `## Acceptance tests` row's test file exists (`manual` and `departure D-nnn` rows name none).
  - the test lock: each file under the state file's `## Test lock` still has the sha256 it had at its red run (LF or
    CRLF), unless a `test-change <file> What: … Why: …` deviation names it. With --base, a feature whose state file
    changed since then is checked too, active or not: Ship marks it done in the commit that finishes it.

Usage: python3 .sdlc/ci/invariants.py [--base REF] [--require-ancestor]   (--require-ancestor: accepted, unused since 2.0)
Exits 1 and prints one line per problem. As a pre-commit hook: python3 .sdlc/ci/invariants.py --base HEAD
Stdlib only, Python 3.9+; it imports nothing from the plugin.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

SDLC = ".sdlc"
STAGE = re.compile(r"^Current:\s*Stage\s+(\d+)", re.M)


def git(*args):
    p = subprocess.run(["git", *args], capture_output=True, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().replace("\r\n", "\n")
    except OSError:
        return None


def config():
    try:
        return json.loads(read(os.path.join(SDLC, "config.json")) or "{}")
    except ValueError:
        return {}


def features():
    """{name: (state path, change file)} in either layout; the new one wins a name in both."""
    docs = str(config().get("docs_dir") or "docs/sdlc").strip("/")
    found = {}
    for path in sorted(glob.glob(os.path.join(SDLC, "*", "state.md"))):
        name = os.path.basename(os.path.dirname(path))
        found[name] = (path, os.path.join(os.path.dirname(path), "change.md"))
    for path in sorted(glob.glob(os.path.join(SDLC, "state", "*.md"))):
        found[os.path.basename(path)[:-3]] = (path, os.path.join(docs, "changes", os.path.basename(path)))
    return found


def section(text, heading):
    m = re.search(rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def check_record(path, stage, build=2, ship=4):
    problems = []
    change = read(path) or ""
    if stage >= build and "## Acceptance tests" not in change:
        problems.append(f"{path}: past Define but no `## Acceptance tests` table naming each AC's test")
    if stage >= ship and not section(change, "Review").strip():
        problems.append(f"{path}: in Ship but no `## Review` section saying what was reviewed")
    return problems


LOCK_LINE = re.compile(r"^- `([^`]+)` sha256:([0-9a-f]{64})\s*$", re.M)
ROW = re.compile(r"^\s*\|\s*(AC-\d{3})\s*\|(.*?)\|(.*?)\|\s*$", re.M)


def sha256s(path):
    """The file's sha256 as it is, and with its line endings as LF and as CRLF: the lock was written on whichever
    checkout the developer had; None when there's no file."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    lf = data.replace(b"\r\n", b"\n")
    return {hashlib.sha256(d).hexdigest() for d in (data, lf, lf.replace(b"\n", b"\r\n"))}


def app_repos():
    """In a workbench, the app repos cloned inside it (workbench.json, each in a folder named after it): their files
    aren't in the workbench's checkout, so CI can't check them here; each repo's own CI covers its tests."""
    try:
        data = json.loads(read("workbench.json") or "{}")
    except ValueError:
        return ()
    repos = data.get("repos") if isinstance(data, dict) else None
    return tuple(r["name"].strip("/") + "/" for r in repos or [] if isinstance(r, dict) and isinstance(r.get("name"), str))


def check_lock(state_path, state):
    """A test file locked at its red run (`## Test lock`) that changed or was deleted, without a `test-change <file>
    What: … Why: …` deviation naming it. CI can't rerun the red step; the deviation records why it changed."""
    deviations = section(state, "Deviations").splitlines()
    problems = []
    for file, sha in LOCK_LINE.findall(section(state, "Test lock")):
        if file.replace("\\", "/").startswith(app_repos()):
            continue
        now = sha256s(file)
        if now is not None and sha in now:
            continue
        if any(f"test-change {file} " in line and re.search(r"What:\s*\S", line) and re.search(r"Why:\s*\S", line)
               for line in deviations):
            continue
        what = "was deleted" if now is None else "changed"
        problems.append(f"{state_path}: {file} {what} since its red run (## Test lock) and no `test-change {file} "
                        "What: … Why: …` deviation says why")
    return problems


def check_test_files(path):
    """Each `## Acceptance tests` row's test file exists; `manual` and `departure D-nnn` rows name none."""
    problems = []
    for ac, test, _ in ROW.findall(section(read(path) or "", "Acceptance tests")):
        test = test.strip().strip("`").strip()
        if test.lower() == "manual" or re.fullmatch(r"departure\s+D-\d{3,}", test, re.I):
            continue
        file = test.split("›")[0].strip().strip("`").strip()
        if file and not file.replace("\\", "/").startswith(app_repos()) and not os.path.exists(file):
            problems.append(f"{path}: {ac}: its test file {file} doesn't exist")
    return problems


def changed_since(base):
    """Paths changed between `base` and the working tree; None when git can't tell."""
    code, out = git("diff", "--name-only", base)
    return set(out.splitlines()) if code == 0 else None


def baseline_rows(text):
    """{key: count}: failing tests by (package, test), lint by (package, tool, rule, file); placeholder rows skipped."""
    rows = {}
    for heading in ("Failing tests", "Lint and type errors"):
        for line in section(text or "", heading).splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not line.startswith("|") or len(cells) < 2 or set(cells[0]) <= set("-: ") \
                    or cells[0] in ("Package", "—", "-") or cells[1].lower() == "none":
                continue
            if heading == "Failing tests":
                rows[("test", cells[0], cells[1])] = 1
            elif len(cells) >= 5:
                try:
                    count = int(cells[4])
                except ValueError:
                    count = 1
                rows[("lint", *cells[:4])] = count
    return rows


def check_baseline(base, deviations):
    path = str(config().get("baseline") or os.path.join(SDLC, "baseline.md")).replace("\\", "/")
    code, before = git("show", f"{base}:{path}")
    old = baseline_rows(before) if code == 0 else {}
    if not old:
        return []  # no baseline at the base yet: the first fill is the recording, not growth
    problems = []
    for key, count in baseline_rows(read(path)).items():
        if count <= old.get(key, 0):
            continue
        names = [key[2]] if key[0] == "test" else [key[3], key[4]]
        if not all(n in deviations for n in names):
            what = key[2] if key[0] == "test" else f"{key[3]} in {key[4]}"
            problems.append(f"{path}: `{what}` was added or went up without a Deviations entry in a feature's "
                            "state file naming it")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", help="the commit to compare the baseline against")
    ap.add_argument("--require-ancestor", action="store_true", help="accepted for old CI workflows; unused since 2.0")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")  # file names and messages aren't ASCII; Windows consoles default to cp1252
    problems, deviations = [], ""
    changed = changed_since(a.base) if a.base else None
    for name, (state_path, change_path) in features().items():
        state = read(state_path) or ""
        deviations += section(state, "Deviations")  # any feature's: one may record it and finish in the same push
        active = re.search(r"^Status:\s*active\b", state, re.M)
        # Ship marks the feature done in its own commit, so the push that finishes it is checked too
        if active or (changed and state_path.replace(os.sep, "/") in changed):
            problems += check_lock(state_path, state)
        if not active:
            continue
        stage = STAGE.search(state)
        # a feature not yet migrated to Process: 3 (sdlc 2.x) still counts Build as 4 and Ship as 8
        current = re.search(r"^Process:\s*3\b", state, re.M)
        build, ship = (2, 4) if current else (4, 8)
        stage = int(stage.group(1)) if stage else 0
        problems += check_record(change_path, stage, build, ship)
        if stage >= build:
            problems += check_test_files(change_path)
    if a.base:
        problems += check_baseline(a.base, deviations)
    for line in problems:
        print(f"sdlc invariants: {line}")
    if not problems:
        print("sdlc invariants: ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
