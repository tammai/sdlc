"""sdlc gate for the commit security review: once per review-ready diff while a feature is active.

The vendored commit review (security_reminder_hook.py) reviews every commit with the top tier. Under the sdlc
workflow a feature's build commits (before Stage 5) are work in progress: reviewing each one costs a top-tier
call per task commit and re-reviews code the next commit changes. So, while exactly one feature is active and
its `Base:` is an ancestor of HEAD (a state file from another branch never holds back unrelated work):
  - before Stage 5, a commit is deferred: not reviewed and not recorded as reviewed;
  - from Stage 5 on, the commit is reviewed together with every unreviewed commit since `Base:`, as one net diff
    from `Base:` (`range`), so every hunk of every commit, side branches included, is in what's reviewed.
The state file is writable by the agent the review checks, so deferral is bounded: never for a commit that
touches the hooks, the agents' instructions or config, or sdlc's state and config (paths read NUL-separated, every
parent of a merge, both sides of a rename), and not once MAX_DEFER commits are unreviewed, counted from where the
branch left the default branch (a point `Base:` can't move; on the default branch itself nothing is deferred); the
review then widens. The widened diff starts at
`Base:` only when every commit it covers descends from it, else at that branch point. MAX_WIDEN or more unreviewed
commits: no widening (the push review still sees them).
Anything else, or any error: the commits are reviewed exactly as given. The push review is untouched.
"""
import os
import re
import subprocess

import sdlc_layout  # sibling module: where feature state lives

MAX_DEFER = 10
MAX_WIDEN = 30
NEVER_DEFER = re.compile(r"^(\.claude/|\.sdlc/(config\.json|state/)|\.github/|hooks/|\.codex/|\.cursor/|\.agents/"
                         r"|AGENTS\.md$|CLAUDE\.md$|\.mcp\.json$)")


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
        files = _git(root, "diff-tree", "-r", "--no-commit-id", "--name-only", "-z", "--no-renames", "-m", "--root", s)
        if files is None or any(NEVER_DEFER.match(f) for f in files.split("\0") if f):
            return True
    return False


def _branch_point(root):
    """Where HEAD left the default branch, which no file in the repo can move; None on the default branch itself."""
    for ref in ("origin/HEAD", "origin/main", "origin/master", "main", "master"):
        point = _git(root, "merge-base", "HEAD", ref)
        if point:
            return None if point == _git(root, "rev-parse", "HEAD") else point
    return None


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
        point = _branch_point(repo_root)  # None on the default branch: nothing to count from, so never defer
        anchor = point or start
        if anchor != start and _git(repo_root, "merge-base", "--is-ancestor", anchor, start) is None:
            anchor = start  # Base: predates the branch point (a long-lived branch): count from Base:
        full = [_git(repo_root, "rev-parse", "--verify", "-q", s) or s for s in shas]
        since = (_git(repo_root, "rev-list", f"{anchor}..HEAD") or "").split()
        unreviewed = [s for s in since if s not in reviewed]
        if (point and int(stage.group(1)) < 5 and len(unreviewed) < MAX_DEFER
                and not _touches_guarded_paths(repo_root, full)):
            return {"defer": True, "shas": [], "range": None, "active": True}
        extra = [s for s in unreviewed if s not in full]
        if not extra or len(extra) >= MAX_WIDEN:
            return {"defer": False, "shas": full, "range": None, "active": True}
        covered = all(_git(repo_root, "merge-base", "--is-ancestor", start, s) is not None for s in extra)
        return {"defer": False, "shas": full + extra, "range": (start if covered else anchor, full[0]), "active": True}
    except Exception:
        return given
