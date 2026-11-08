#!/usr/bin/env python3
"""sdlc brief: everything Define reads before the code, printed in one call, so reading takes one turn, not four.

Prints, each under a `===== <path> =====` line and cut at a line limit: the feature's paths (with a name), the
project's .sdlc/config.json, .sdlc/baseline.md, knowledge/index.md, <docs>/recurring-defects.md, the constitution,
the PRD, README.md, the package manifest, the tracked files and the plugin's change template. A missing file is one
`(none)` line. The code the change touches isn't printed: the agent reads that itself, in the same turn. Run when
sizing a new request, so the router's reading and Define's are one turn.
Spec-backed work (spec 03 S2): `--criteria ID ...` (the slice's criteria), and the IDs NAME's change file cites,
print as `cited criteria`: each criterion's line from the spec, with its level and recorded test from the lock.
Usage: python3 brief.py [--root DIR] [NAME] [--criteria ID ...]. Read-only. Exit 0; 2 usage. Stdlib only, Python 3.9+.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "hooks"))
import sdlc_layout  # noqa: E402  (where the feature's state and documents live)
sys.path.insert(0, HERE)
import spec_lock  # noqa: E402  (the criteria an rspec spec locked)

LIMIT = 200  # lines per file: a long README or PRD is cut, and the cut says so
MANIFESTS = ("package.json", "pyproject.toml", "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "Gemfile",
             "composer.json")


def section(title, text, limit=LIMIT):
    lines = text.rstrip("\n").split("\n") if text else []
    out = [f"===== {title} ====="]
    if not lines or lines == [""]:
        out.append("(none)")
    else:
        out += lines[:limit]
        if len(lines) > limit:
            out.append(f"... ({len(lines) - limit} more lines: read the file for the rest)")
    return "\n".join(out)


def read(root, rel):
    try:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def tracked(root):
    try:
        p = subprocess.run(["git", "-C", root, "ls-files"], capture_output=True, encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return p.stdout if p.returncode == 0 else ""


def criteria_text(root, ids):
    """One line per criterion ID: its text from the spec, its level and recorded test; or why it can't be shown."""
    locked, problems = spec_lock.load(root)
    out = list(problems)
    for cid in dict.fromkeys(ids):
        entry = locked.get(cid)
        if entry is None:
            out.append(f"{cid}: not in the lock")
            continue
        line = spec_lock.criterion_line(root, entry)
        out.append(f"{line or cid + ': (its line is not in ' + entry.get('file', '?') + ')'}"
                   f"   [level {entry.get('level')}; test: {entry.get('test') or 'none recorded'}]")
    return "\n".join(out)


def brief(root, name=None, criteria=()):
    docs = sdlc_layout.docs_dir(root) or sdlc_layout.SDLC
    parts = []
    ids = list(criteria)
    if name:
        parts.append(section("paths", json.dumps(sdlc_layout.paths(root, name), indent=1)))
        change = read(root, sdlc_layout.paths(root, name)["change"])
        ids += [cid for found in spec_lock.cited(spec_lock.entries(change)).values() for cid in found]
    if ids:
        parts.append(section("cited criteria", criteria_text(root, ids)))
    for rel in (".sdlc/config.json", ".sdlc/baseline.md", "knowledge/index.md", f"{docs}/recurring-defects.md",
                f"{docs}/constitution.md", sdlc_layout.prd(root), "README.md"):
        parts.append(section(rel, read(root, rel)))
    manifest = next((m for m in MANIFESTS if os.path.isfile(os.path.join(root, m))), None)
    parts.append(section(manifest or "package manifest", read(root, manifest) if manifest else "", 80))
    parts.append(section("git ls-files", tracked(root), 300))
    parts.append(section("change template", read(os.path.dirname(HERE), os.path.join("templates", "change-template.md"))))
    return "\n\n".join(parts) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("name", nargs="?")
    ap.add_argument("--criteria", nargs="+", default=[], metavar="ID", help="criterion IDs to print from the lock")
    a = ap.parse_intermixed_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(brief(os.path.abspath(a.root), a.name, a.criteria))
    return 0


if __name__ == "__main__":
    sys.exit(main())
