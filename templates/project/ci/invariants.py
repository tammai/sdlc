#!/usr/bin/env python3
"""Check the shared sdlc files, whichever agent or person changed them (seeded by the sdlc plugin v{{plugin_version}}).

Only active features count (`Status: active` in their state file):
  - test-report.md: the latest round has its header, both tables and a verdict; with --require-ancestor, the round's
    commit is in this code's history.
  - the baseline: against --base, a new row or a higher lint count needs a feature's Deviations entry naming it.
  - spec.md: no `[inferred]` tag past Stage 1.

Usage: python3 .sdlc/ci/invariants.py [--base REF] [--require-ancestor]
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
ROUND = re.compile(r"^## Round (\d+)\b.*?\bcommit ([0-9a-f]{7,40})(\+dirty)?\s*$", re.M)
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


def check_report(name, docs, require_ancestor):
    path = os.path.join(docs, "test-report.md")
    text = read(path)
    rounds = list(ROUND.finditer(text or ""))
    if text is None or (not rounds and "## Round" not in text):
        return []  # not verified yet
    if not rounds:
        return [f"{path}: the latest round has no `## Round <n> — <time> — commit <hash>` header"]
    last = rounds[-1]
    body = text[last.end():]
    problems = []
    if not re.search(r"^\|\s*Check\s*\|\s*Command\s*\|\s*Result\s*\|", body, re.M) \
            or not re.search(r"^\|\s*Criterion\s*\|\s*Evidence\s*\|\s*Status\s*\|", body, re.M) \
            or not re.search(r"^\*\*Verdict:\*\*\s*(PASS|FAIL)\b", body, re.M):
        problems.append(f"{path}: round {last.group(1)} is missing its checks table, criteria table or verdict")
    # `+dirty` is normal: the gate records the worktree tree, so a round can cover uncommitted work on that commit
    if require_ancestor and git("merge-base", "--is-ancestor", last.group(2), "HEAD")[0] != 0:
        problems.append(f"{path}: round {last.group(1)}'s commit {last.group(2)} isn't in this code's history: "
                        "verify again on this code")
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
    ap.add_argument("--require-ancestor", action="store_true", help="a round's commit must be in HEAD's history")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")  # file names and messages aren't ASCII; Windows consoles default to cp1252
    problems, deviations = [], ""
    for name, (state_path, docs) in features().items():
        state = read(state_path) or ""
        deviations += section(state, "Deviations")  # any feature's: one may record it and finish in the same push
        if not re.search(r"^Status:\s*active\b", state, re.M):
            continue
        problems += check_report(name, docs, a.require_ancestor)
        stage = STAGE.search(state)
        spec = os.path.join(docs, "spec.md")
        if stage and int(stage.group(1)) >= 2 and "[inferred]" in (read(spec) or ""):
            problems.append(f"{spec}: `[inferred]` tags are left past Stage 1: the user keeps or drops each one")
    if a.base:
        problems += check_baseline(a.base, deviations)
    for line in problems:
        print(f"sdlc invariants: {line}")
    if not problems:
        print("sdlc invariants: ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
