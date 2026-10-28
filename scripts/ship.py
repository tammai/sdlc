#!/usr/bin/env python3
"""Ship's one command: everything before the commit, so Ship is a single shell call (ADR 0020).

Usage: ship.py [--root DIR] FEATURE --message SUBJECT [--review TEXT] [--note TEXT] [--timeout S]
  1. `Owner:` must be `git config user.email`; someone else's is refused (the user decides a handover).
  2. `--review TEXT`: when the change file has no `## Review` yet, appends one holding TEXT (an S change, or an M no
     review ran on); one written already is left as it is.
  3. The last passing verify.py run is reused when the code hasn't changed since (`verify.py status`); otherwise
     verify.py runs now, and a failure stops here with nothing moved.
  4. `state.py advance FEATURE 8 --gate pass --verified <head> <tree>`; already at Stage 8 (a rerun) is fine.
  5. On the default branch, switches to a branch named after the feature.
  6. Stages every changed and untracked file except .sdlc/.work/ and what the tests leave behind (`__pycache__`,
     caches), and writes the commit message (SUBJECT, then `Record: <change>`) to .sdlc/.work/commit-msg.txt.
The commit stays in the caller's command, where the commit's security review and the user's permission rules see
it: `ship.py … && git commit -F .sdlc/.work/commit-msg.txt && git push -u origin HEAD && gh pr create --fill`.
`Status: done` comes after, in its own call, so that review still sees an active feature.
Exit 0 ready to commit, 1 refused or verify failed, 2 usage. Stdlib only, Python 3.9+.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "hooks"))
sys.path.insert(0, HERE)
import sdlc_layout  # noqa: E402
import verify  # noqa: E402  (status, the full run, and what the tests leave behind)

MESSAGE = os.path.join(".sdlc", ".work", "commit-msg.txt")


class Refused(Exception):
    pass


def git(root, *args, check=True):
    p = subprocess.run(["git", "-C", root, *args], capture_output=True, encoding="utf-8", errors="replace")
    if check and p.returncode:
        raise Refused(f"git {args[0]}: {(p.stderr or p.stdout).strip()}")
    return p.stdout


def field(text, name):
    m = re.search(rf"^{name}:[ \t]*(\S+)", text, re.M)
    return m.group(1) if m else None


def add_review(root, change, text):
    path = os.path.join(root, change)
    body = verify.read(path)
    if body is None:
        raise Refused(f"{change} not found")
    if re.search(r"^## Review\b", body, re.M):
        return False
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(body.rstrip("\n") + f"\n\n## Review\n\n{text}\n")
    return True


def verified(root, feature, timeout):
    st = verify.status(root, feature)
    if st["reuse"]:
        return st["head"], st["tree"]
    last, notes = verify.full(root, feature, timeout)
    if last["result"] != "pass":
        raise Refused("verify failed:\n" + "\n".join(notes + last["failures"]))
    return last["head"], last["tree"]


def advance(root, feature, head, tree, note):
    cmd = [sys.executable, os.path.join(HERE, "state.py"), "--root", root, "advance", feature, "8", "--gate", "pass",
           "--verified", head, tree] + (["--note", note] if note else [])
    p = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")
    if p.returncode and "already at Stage 8" not in p.stdout:
        raise Refused(f"state.py advance: {p.stdout.strip()}")


def on_default_branch(root):
    current = git(root, "branch", "--show-current").strip()
    remote_head = git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD", check=False).strip()
    default = remote_head.split("/", 1)[1] if "/" in remote_head else None
    return current == default if default else current in ("main", "master")


def to_stage(root):
    tracked = git(root, "diff", "-z", "--name-only", "HEAD").split("\0")
    untracked = git(root, "ls-files", "-z", "--others", "--exclude-standard").split("\0")
    return sorted({f for f in tracked + untracked
                   if f and not f.startswith(".sdlc/.work/") and not verify.GENERATED.search(f)})


def ship(root, feature, message, review=None, note=None, timeout=1800):
    paths = sdlc_layout.paths(root, feature)
    state = verify.read(os.path.join(root, paths["state"]))
    if state is None:
        raise Refused(f"no state file for {feature}")
    owner, me = field(state, "Owner"), git(root, "config", "user.email", check=False).strip()
    if owner and me and owner != me:
        raise Refused(f"Owner is {owner}, not {me}: ask the user before taking it over")
    if review:
        add_review(root, paths["change"], review)
    head, tree = verified(root, feature, timeout)
    advance(root, feature, head, tree, note)
    branch = None
    if on_default_branch(root):
        branch = feature
        git(root, "switch", "-c", branch)
    files = to_stage(root)
    if files:
        git(root, "add", "-A", "--", *files)
    os.makedirs(os.path.join(root, ".sdlc", ".work"), exist_ok=True)
    with open(os.path.join(root, MESSAGE), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{message}\n\nRecord: {paths['change']}\n")
    return {"ok": True, "head": head, "tree": tree, "branch": branch, "staged": files, "message": MESSAGE}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("feature")
    ap.add_argument("--message", required=True)
    ap.add_argument("--review")
    ap.add_argument("--note")
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        out = ship(os.path.abspath(a.root), a.feature, a.message, a.review, a.note, a.timeout)
    except Refused as e:
        print(f"ship: {e}")
        return 1
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
