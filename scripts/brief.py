#!/usr/bin/env python3
"""sdlc brief: everything Define reads before the code, printed in one call, so reading takes one turn, not four.

Prints, each under a `===== <path> =====` line and cut at a line limit: the feature's paths (with a name), the
project's .sdlc/config.json, .sdlc/baseline.md, knowledge/index.md, <docs>/recurring-defects.md, the constitution,
the PRD, README.md, the package manifest, the tracked files and the plugin's change template. A missing file is one
`(none)` line. The code the change touches isn't printed: the agent reads that itself, in the same turn. Run when
sizing a new request, so the router's reading and Define's are one turn.
Usage: python3 brief.py [--root DIR] [NAME]. Read-only. Exit 0; 2 usage. Stdlib only, Python 3.9+.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "hooks"))
import sdlc_layout  # noqa: E402  (where the feature's state and documents live)

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


def brief(root, name=None):
    docs = sdlc_layout.docs_dir(root) or sdlc_layout.SDLC
    parts = []
    if name:
        parts.append(section("paths", json.dumps(sdlc_layout.paths(root, name), indent=1)))
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
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(brief(os.path.abspath(a.root), a.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
