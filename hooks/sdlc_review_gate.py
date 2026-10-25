"""sdlc gate for the commit security review: once per review-ready diff while a feature is active.

The vendored commit review (security_reminder_hook.py) reviews every commit with the top tier. Under the sdlc
workflow a feature's build commits (before Stage 5) are work in progress: reviewing each one costs a top-tier
call per task commit and re-reviews code the next commit changes. So, while exactly one feature is active and
its `Base:` is an ancestor of HEAD (a state file from another branch never holds back unrelated work):
  - before Stage 5, a commit is deferred: not reviewed and not recorded as reviewed;
  - from Stage 5 on, the commit is reviewed together with every unreviewed commit since `Base:`, as one net diff
    (`range`), so a file changed in several commits keeps all its hunks. More than MAX_WIDEN unreviewed commits:
    no widening (the push review, or a later commit, still sees the rest).
Anything else, or any error: the commits are reviewed exactly as given. The push review is untouched.
"""
import os
import re
import subprocess

import sdlc_layout  # sibling module: where feature state lives

MAX_WIDEN = 30


def _git(root, *args):
    try:
        p = subprocess.run(["git", "-C", root, *args], capture_output=True, encoding="utf-8", errors="replace",
                           timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout.strip() if p.returncode == 0 else None


def _active_feature(root):
    found = []
    for f in sdlc_layout.features(root).values():
        try:
            with open(os.path.join(root, f["state"]), encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        if re.search(r"^Status:[ \t]*active[ \t]*(\(|$)", text, re.M | re.I):
            found.append(text)
    return found[0] if len(found) == 1 else None


def decide(repo_root, shas, reviewed):
    """{defer, shas, range, active}. defer: review nothing now. shas: the commits this review covers (and marks
    reviewed), newest first. range: (from, to) for one net `git diff` when widened, else None. active: the gate
    applied (a feature's review-ready commit), so an amend is reviewed whole, never as a delta. Never raises."""
    given = {"defer": False, "shas": list(shas), "range": None, "active": False}
    try:
        text = _active_feature(repo_root)
        stage = re.search(r"^Current:\s*Stage\s*(\d+)\b", text or "", re.M)
        base = re.search(r"^Base:\s*`?([0-9a-f]{7,40})\b", text or "", re.M)
        if not (stage and base) or _git(repo_root, "merge-base", "--is-ancestor", base.group(1), "HEAD") is None:
            return given
        if int(stage.group(1)) < 5:
            return {"defer": True, "shas": [], "range": None, "active": True}
        full = [_git(repo_root, "rev-parse", "--verify", "-q", s) or s for s in shas]
        since = (_git(repo_root, "rev-list", f"{base.group(1)}..HEAD") or "").split()
        extra = [s for s in since if s not in reviewed and s not in full]
        if not extra or len(extra) > MAX_WIDEN:
            return {"defer": False, "shas": full, "range": None, "active": True}
        oldest = extra[-1]  # rev-list is newest first
        start = _git(repo_root, "rev-parse", "--verify", "-q", f"{oldest}^") or base.group(1)
        return {"defer": False, "shas": full + extra, "range": (start, full[0]), "active": True}
    except Exception:
        return given
