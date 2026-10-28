#!/usr/bin/env python3
"""Check the shared sdlc files, whichever agent or person changed them (seeded by the sdlc plugin v{{plugin_version}}).

Only active features count (`Status: active` in their state file):
  - the record matches the phase reached: past Define (Stage 1), change.md has its `## Acceptance tests` table; in
    Ship (Stage 8), its `## Review` section says what was reviewed.
  - the baseline: against --base, a new row or a higher lint count needs a feature's Deviations entry naming it.

Usage: python3 .sdlc/ci/invariants.py [--base REF] [--require-ancestor]   (--require-ancestor: accepted, unused since 2.0)
Exits 1 and prints one line per problem. As a pre-commit hook: python3 .sdlc/ci/invariants.py --base HEAD
Stdlib only, Python 3.9+; it imports nothing from the plugin.
"""
import argparse
import glob
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
    """{name: (state path, documents folder)} in either layout; the new one wins a name in both."""
    docs = str(config().get("docs_dir") or "docs/sdlc").strip("/")
    found = {}
    for path in sorted(glob.glob(os.path.join(SDLC, "*", "state.md"))):
        name = os.path.basename(os.path.dirname(path))
        found[name] = (path, os.path.dirname(path))
    for path in sorted(glob.glob(os.path.join(SDLC, "state", "*.md"))):
        found[os.path.basename(path)[:-3]] = (path, os.path.join(docs, "intents", os.path.basename(path)[:-3]))
    return found


def section(text, heading):
    m = re.search(rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def check_record(docs, stage):
    problems = []
    path = os.path.join(docs, "change.md")
    change = read(path) or ""
    if stage >= 4 and "## Acceptance tests" not in change:
        problems.append(f"{path}: past Define but no `## Acceptance tests` table naming each AC's test")
    if stage >= 8 and not section(change, "Review").strip():
        problems.append(f"{path}: in Ship but no `## Review` section saying what was reviewed")
    return problems


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
    for name, (state_path, docs) in features().items():
        state = read(state_path) or ""
        deviations += section(state, "Deviations")  # any feature's: one may record it and finish in the same push
        if not re.search(r"^Status:\s*active\b", state, re.M):
            continue
        stage = STAGE.search(state)
        problems += check_record(docs, int(stage.group(1)) if stage else 0)
    if a.base:
        problems += check_baseline(a.base, deviations)
    for line in problems:
        print(f"sdlc invariants: {line}")
    if not problems:
        print("sdlc invariants: ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
