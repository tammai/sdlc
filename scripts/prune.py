#!/usr/bin/env python3
"""sdlc prune: delete the working files of finished features, keep their record.

A feature qualifies when its state.md on the main branch says `Status: done` (so it's merged) and
hasn't changed for --older-than days. Its plan, reports, review and checklists go; spec, design,
retro and state stay, and security.md stays on Risk: high. Git history keeps everything deleted.
Usage: python3 prune.py [--root DIR] [--main REF] list [--older-than 45d]
       python3 prune.py [--root DIR] [--main REF] apply [--older-than 45d] FEATURE...
Prints one JSON object. Stdlib only, Python 3.9+.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

DELETE = ["plan.md", "test-report.md", "qa-report.md", "review.md", "checklists"]


def git(root, *args):
    p = subprocess.run(["git", "-C", root, *args], capture_output=True, encoding="utf-8", errors="replace")
    return p.stdout.strip() if p.returncode == 0 else None


def main_ref(root, given):
    for ref in [given] if given else ["main", "master"]:
        if git(root, "rev-parse", "--verify", "--quiet", ref + "^{commit}"):
            return ref
    return None


def days(text):
    m = re.fullmatch(r"(\d+)d?", text)
    if not m:
        raise argparse.ArgumentTypeError("use a number of days, e.g. 45d")
    return int(m.group(1))


def candidate(root, ref, name, older_than):
    """Return the files to delete for one feature, or the reason it doesn't qualify."""
    state = git(root, "show", f"{ref}:.sdlc/{name}/state.md")
    if state is None:
        return {"feature": name, "skip": f"no state.md on {ref} (not merged)"}
    if not re.search(r"^Status:\s*done\b", state, re.M | re.I):
        return {"feature": name, "skip": f"not done on {ref}"}
    changed = int(git(root, "log", "-1", "--format=%ct", ref, "--", f".sdlc/{name}/state.md") or 0)
    age = int((time.time() - changed) // 86400)
    if age < older_than:
        return {"feature": name, "skip": f"done {age} days ago (under {older_than})"}
    delete = list(DELETE)
    if not re.search(r"^Risk:\s*high\b", state, re.M | re.I):
        delete.append("security.md")
    here = [f for f in delete if os.path.exists(os.path.join(root, ".sdlc", name, f))]
    return {"feature": name, "age_days": age, "delete": here}


def features(root):
    base = os.path.join(root, ".sdlc")
    if not os.path.isdir(base):
        return []
    return sorted(d for d in os.listdir(base) if os.path.isfile(os.path.join(base, d, "state.md")))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--main", help="the branch features merge into (default: main, else master)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("list", "apply"):
        s = sub.add_parser(name)
        s.add_argument("--older-than", type=days, default=45)
        if name == "apply":
            s.add_argument("feature", nargs="+")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    root = git(os.path.abspath(a.root), "rev-parse", "--show-toplevel")
    if root is None:
        print(json.dumps({"error": "not a git repository"}))
        return 1
    ref = main_ref(root, a.main)
    if ref is None:
        print(json.dumps({"error": f"no main branch found ({a.main or 'main, master'}); pass --main"}))
        return 1
    if a.cmd == "list":
        found = [candidate(root, ref, n, a.older_than) for n in features(root)]
        print(json.dumps({"main": ref, "prune": [c for c in found if "delete" in c and c["delete"]],
                          "skipped": [c for c in found if "skip" in c]}, indent=2))
        return 0
    pruned, refused = [], []
    for name in a.feature:
        c = candidate(root, ref, name, a.older_than) if name in features(root) else {"feature": name, "skip": "no such feature"}
        if "skip" in c:
            refused.append(c)
            continue
        for f in c["delete"]:
            path = os.path.join(root, ".sdlc", name, f)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
        pruned.append(c)
    print(json.dumps({"main": ref, "pruned": pruned, "refused": refused}, indent=2))
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
