#!/usr/bin/env python3
"""sdlc prune: delete the working files of finished features, keep their record.

A feature qualifies when its state.md on the main branch says `Status: done` (so it's merged) and
hasn't changed for --older-than days. Its plans (plan.md and the parts' plan-B<n>.md), reports, review and
checklists go; change.md (2.0), intent, spec, design, retro and state stay; review.md stays on a 2.0 feature (`Process: 2`: it is the
review's record) and on Risk: high (its `## Security` section), with an older security.md. Git history keeps
everything deleted.
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

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks"))
import sdlc_layout  # noqa: E402  (where feature state and documents live, in either layout)

DELETE = ["plan.md", "test-report.md", "qa-report.md", "review.md", "checklists"]
SLICE_PLAN = re.compile(r"plan-B\d+\.md")  # a backlog's per-slice plans


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
    loc = sdlc_layout.features(root)[name]
    # On the main branch the feature may still be in the old layout (merged before the move)
    on_ref = next((s for s in (loc["state"], f".sdlc/{name}/state.md")
                   if git(root, "cat-file", "-e", f"{ref}:{s}") is not None), None)
    state = git(root, "show", f"{ref}:{on_ref}") if on_ref else None
    if state is None:
        return {"feature": name, "skip": f"no state.md on {ref} (not merged)"}
    if not re.search(r"^Status:\s*done\b", state, re.M | re.I):
        return {"feature": name, "skip": f"not done on {ref}"}
    # --follow: the move to the new layout must not restart every feature's age
    changed = int(git(root, "log", "-1", "--follow", "--format=%ct", ref, "--", on_ref) or 0)
    age = int((time.time() - changed) // 86400)
    if age < older_than:
        return {"feature": name, "skip": f"done {age} days ago (under {older_than})"}
    # sdlc 2.0 keeps its working files beside the state file (the record is the change file and the state);
    # 1.x kept them with its documents
    where = loc["work"] if re.search(r"^Process:\s*2\b", state, re.M) else loc["intents"]
    # Deleting from the working tree is only safe when it matches what git already holds.
    dirty = git(root, "status", "--porcelain", "--", loc["state"], where)
    if dirty is None or dirty:
        return {"feature": name, "skip": "uncommitted changes in its folder" if dirty else "git status failed"}
    folder = os.path.realpath(os.path.join(root, where))
    if not folder.startswith(os.path.realpath(root) + os.sep):
        return {"feature": name, "skip": f"{where} is outside the repo"}
    local = os.path.join(root, loc["state"])
    with open(local, encoding="utf-8", errors="replace") as f:
        if not re.search(r"^Status:\s*done\b", f.read(), re.M | re.I):
            return {"feature": name, "skip": "not done in the working tree (reopened?)"}
    delete = list(DELETE)
    if re.search(r"^Risk:\s*high\b", state, re.M | re.I) or re.search(r"^Process:\s*2\b", state, re.M):
        delete.remove("review.md")  # sdlc 2.0 records every review there; 1.x only its security section
    if not re.search(r"^Risk:\s*high\b", state, re.M | re.I):
        delete.append("security.md")
    here = [f for f in delete if os.path.exists(os.path.join(root, where, f))]
    if os.path.isdir(folder):
        here += sorted(f for f in os.listdir(folder) if SLICE_PLAN.fullmatch(f))
    return {"feature": name, "age_days": age, "delete": here, "dir": where}


def features(root):
    return sorted(sdlc_layout.features(root))


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
            path = os.path.join(root, c["dir"], f)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
        pruned.append(c)
    print(json.dumps({"main": ref, "pruned": pruned, "refused": refused}, indent=2))
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
