"""sdlc gate for the commit security review: once per review-ready diff while a feature is active.

The vendored commit review (security_reminder_hook.py) reviews every commit with the top tier. Under the sdlc
workflow a feature's build commits (before Stage 5) are work in progress: reviewing each one costs a top-tier
call per task commit and re-reviews code the next commit changes. So, while exactly one feature is active and
its `Base:` is an ancestor of HEAD (a state file from another branch never holds back unrelated work):
  - before Stage 5, a commit is deferred: not reviewed and not recorded as reviewed;
  - from Stage 5 on, the commit is reviewed together with every unreviewed commit since `Base:`, as one net diff
    from `Base:` (`range`), so every hunk of every commit, side branches included, is in what's reviewed.
The state file is writable by the agent the review checks, so deferral is bounded: never for a commit that
touches the hooks or the agent's or sdlc's config, and not once MAX_DEFER commits are unreviewed (the review then
widens). More than MAX_WIDEN unreviewed commits: no widening (the push review still sees them).
Anything else, or any error: the commits are reviewed exactly as given. The push review is untouched.
"""
import os
import re
import subprocess

import sdlc_layout  # sibling module: where feature state lives

MAX_DEFER = 10
MAX_WIDEN = 30
NEVER_DEFER = re.compile(r"^(\.claude/|\.sdlc/config\.json$|\.github/|hooks/|\.codex/|\.cursor/|\.agents/)")


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


def _touches_guarded_paths(root, shas):
    for s in shas:
        files = _git(root, "show", "--name-only", "--format=", s)
        if files is None or any(NEVER_DEFER.match(f) for f in files.splitlines()):
            return True
    return False


def decide(repo_root, shas, reviewed):
    """{defer, shas, range, active}. defer: review nothing now. shas: the commits this review covers (and marks
    reviewed), newest first. range: (from, to) for one net `git diff` when widened, else None. active: the gate
    applied, so an amend is reviewed whole, never as a delta. Never raises."""
    given = {"defer": False, "shas": list(shas), "range": None, "active": False}
    try:
        text = _active_feature(repo_root)
        stage = re.search(r"^Current:\s*Stage\s*(\d+)\b", text or "", re.M)
        base = re.search(r"^Base:\s*`?([0-9a-f]{7,40})\b", text or "", re.M)
        if not (stage and base) or _git(repo_root, "merge-base", "--is-ancestor", base.group(1), "HEAD") is None:
            return given
        start = _git(repo_root, "rev-parse", "--verify", "-q", base.group(1))
        full = [_git(repo_root, "rev-parse", "--verify", "-q", s) or s for s in shas]
        since = (_git(repo_root, "rev-list", f"{start}..HEAD") or "").split()
        unreviewed = [s for s in since if s not in reviewed]
        if (int(stage.group(1)) < 5 and len(unreviewed) < MAX_DEFER
                and not _touches_guarded_paths(repo_root, full)):
            return {"defer": True, "shas": [], "range": None, "active": True}
        extra = [s for s in unreviewed if s not in full]
        if not extra or len(extra) >= MAX_WIDEN:
            return {"defer": False, "shas": full, "range": None, "active": True}
        return {"defer": False, "shas": full + extra, "range": (start, full[0]), "active": True}
    except Exception:
        return given
