"""sdlc gate for the commit security review: once per review-ready diff while a feature is active.

The vendored commit review (security_reminder_hook.py) reviews every commit with the top tier. Under the sdlc
workflow a feature's build commits (before Stage 5) are work in progress: reviewing each one costs a top-tier
call per task commit and re-reviews code the next commit changes. So, while exactly one feature is active and
its `Base:` is an ancestor of HEAD (a state file from another branch never holds back unrelated work):
  - before Stage 5, a commit is deferred: not reviewed and not recorded as reviewed;
  - from Stage 5 on, the commit is reviewed together with every unreviewed commit since `Base:`, as one net diff
    from `Base:` (`range`), so every hunk of every commit, side branches included, is in what's reviewed;
  - but only a security-touched change gets that model review (`Risk: high`, or the change since `Base:` touches
    `areas.sensitive` or `areas.migrations` of .sdlc/config.json, else the plugin's defaults); any other is `skip`:
    recorded as reviewed with no model call, so a later review doesn't widen over it.
The state file is writable by the agent the review checks, so deferral is bounded: never for a commit that
touches the hooks, the agents' instructions or config, or sdlc's state and config (paths read NUL-separated, every
parent of a merge, both sides of a rename), and not once MAX_DEFER commits are unreviewed, counted from where the
branch left the default branch (a point `Base:` can't move; on the default branch itself nothing is deferred); the
review then widens. The widened diff starts at
`Base:` only when every commit it covers descends from it, else at that branch point. MAX_WIDEN or more unreviewed
commits: no widening (the push review still sees them).
With no active feature the commit gets no model review and isn't recorded as reviewed (`off`), so the push review
still covers it; review_wanted() tells the Stop review the same (ADR 0019); SDLC_SECURITY_REVIEW=always restores the review outside the flow.
Anything else, or any error: the commits are reviewed exactly as given. The push review is untouched.
"""
import json
import os
import re
import subprocess

import sdlc_layout  # sibling module: where feature state lives

MAX_DEFER = 10
MAX_WIDEN = 30
_STEERING = r"\.claude/|\.github/|hooks/|\.codex/|\.cursor/|\.agents/|AGENTS\.md$|CLAUDE\.md$|\.mcp\.json$"
NEVER_DEFER = re.compile(rf"^({_STEERING}|\.sdlc/(config\.json|state/))")
# Always reviewed, even when not security-touched: what steers the agent or this gate. Not .sdlc/state/: every Ship
# and slice commit carries it, and the trust anchor already reports the fields that matter (Risk, Track, Process)
NEVER_SKIP = re.compile(rf"^({_STEERING}|\.sdlc/config\.json$)")


def _git(root, *args):
    try:
        p = subprocess.run(["git", "-C", root, *args], capture_output=True, encoding="utf-8", errors="replace",
                           timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout.strip() if p.returncode == 0 else None


def _active_features(root):
    found = []
    for f in sdlc_layout.features(root).values():
        try:
            with open(os.path.join(root, f["state"]), encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        if re.search(r"^Status:[ \t]*active[ \t]*(\(|$)", text, re.M | re.I) and re.search(r"^Process:\s*2\b", text, re.M):
            found.append(text)  # a 1.x feature (no `Process: 2`) is finished on 1.8.1, not gated here
    return found


def _active_feature(root):
    found = _active_features(root)
    return found[0] if len(found) == 1 else None


def _always():
    return os.environ.get("SDLC_SECURITY_REVIEW", "").strip().lower() == "always"


def _touches_guarded_paths(root, shas, guard=NEVER_DEFER):
    for s in shas:
        files = _git(root, "diff-tree", "-r", "--no-commit-id", "--name-only", "-z", "--no-renames", "-m", "--root", s)
        if files is None or any(guard.match(f) for f in files.split("\0") if f):
            return True
    return False


DEFAULT_AREAS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "project",
                             "config.defaults.json")


def _glob_re(pattern):
    """A .gitignore-style glob (`**`, `*`, `?`, `{a,b}`) as a regex over a repo-relative path."""
    out, i = "", 0
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
            continue
        if pattern.startswith("**", i):
            out, i = out + ".*", i + 2
            continue
        if c == "{":
            end = pattern.find("}", i)
            if end > i:
                out += "(?:" + "|".join(re.escape(p) for p in pattern[i + 1:end].split(",")) + ")"
                i = end + 1
                continue
        out += "[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c)
        i += 1
    return re.compile(out + r"\Z")


def _globs(text):
    try:
        areas = json.loads(text).get("areas") or {}
    except (ValueError, AttributeError):
        return None
    return [g for k in ("sensitive", "migrations") for g in (areas.get(k) or []) if isinstance(g, str)]


def _security_areas(root):
    """areas.sensitive and areas.migrations: the plugin's defaults plus whatever the project's config adds (a
    union: the config is agent-writable, so it can add areas, never remove one). None when the defaults can't be
    read: the caller then treats every change as security-touched."""
    try:
        with open(DEFAULT_AREAS, encoding="utf-8") as f:
            globs = _globs(f.read())
    except OSError:
        return None
    if not globs:
        return None
    try:
        with open(os.path.join(root, ".sdlc", "config.json"), encoding="utf-8") as f:
            globs += _globs(f.read()) or []
    except OSError:
        pass
    return [_glob_re(g.lower()) for g in globs]  # case-folded both sides: folding only adds matches


def _names(root, *args):
    out = _git(root, *args, "-z", "--no-renames")
    return None if out is None else [n for n in out.split("\0") if n]


def _untracked(root):
    out = _git(root, "ls-files", "--others", "--exclude-standard", "-z")
    return None if out is None else [n for n in out.split("\0") if n]


def _security_touched(root, text, start, anchor, shas, worktree=False):
    """Risk: high, an uncommitted change to .sdlc/config.json, or a change since the branch point and Base: (and
    these commits; with worktree, uncommitted and untracked files too) that touches a sensitive or migration path.
    Anything it can't tell counts as touched."""
    if re.search(r"^Risk:\s*high\b", text, re.M | re.I):
        return True
    if _git(root, "diff", "--quiet", "HEAD", "--", ".sdlc/config.json") is None:
        return True  # edited and not committed: its areas aren't the ones a reviewer would see
    areas = _security_areas(root)
    lists = [_names(root, "diff", "--name-only", ref, "HEAD") for ref in {start, anchor} if ref]
    lists += [_names(root, "diff-tree", "-r", "--no-commit-id", "--name-only", "-m", "--root", s) for s in shas]
    if worktree:
        lists += [_names(root, "diff", "--name-only", "HEAD"), _untracked(root)]
    if areas is None or any(names is None for names in lists):
        return True
    names = {n.lower() for names in lists for n in names}  # src/Auth/ on a case-insensitive checkout too
    return any(rx.match(n) for n in names for rx in areas)


def _branch_point(root):
    """Where HEAD left the default branch, which no file in the repo can move; None on the default branch itself."""
    for ref in ("origin/HEAD", "origin/main", "origin/master", "main", "master"):
        point = _git(root, "merge-base", "HEAD", ref)
        if point:
            return None if point == _git(root, "rev-parse", "HEAD") else point
    return None


def review_wanted(repo_root):
    """For the Stop review: True only when SDLC_SECURITY_REVIEW=always, or the one active feature's change (committed
    since Base:, uncommitted or untracked) is security-touched. No active feature: False. Several active features, a
    state without Base:, or any error: True."""
    try:
        if _always():
            return True
        found = _active_features(repo_root)
        if not found:
            return False
        base = re.search(r"^Base:\s*`?([0-9a-f]{7,40})\b", found[0], re.M)
        if len(found) > 1 or not base:
            return True
        start = _git(repo_root, "rev-parse", "--verify", "-q", base.group(1))
        return not start or _security_touched(repo_root, found[0], start, None, [], worktree=True)
    except Exception:
        return True


def decide(repo_root, shas, reviewed):
    """{defer, shas, own, range, active}. defer: review nothing now. shas: the commits this review covers (and
    marks reviewed), newest first; own: the commits that triggered it, the only ones to mark if the reviewer had to
    drop files from a widened diff. range: (from, to) for one net `git diff` when widened, else None. active: the
    gate applied, so an amend is reviewed whole, never as a delta. Never raises."""
    given = {"defer": False, "shas": list(shas), "own": list(shas), "range": None, "active": False}
    try:
        if not _always() and not _active_features(repo_root):
            return {"defer": True, "off": True, "shas": [], "own": [], "range": None, "active": False}
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
            return {"defer": True, "shas": [], "own": [], "range": None, "active": True}
        if (not _touches_guarded_paths(repo_root, full, NEVER_SKIP)
                and not _security_touched(repo_root, text, start, anchor, full)):
            # Not security-touched: no model review; marked reviewed so a later review doesn't widen over it
            return {"defer": False, "skip": True, "shas": full, "own": full, "range": None, "active": True}
        extra = [s for s in unreviewed if s not in full]
        if not extra or len(extra) >= MAX_WIDEN:
            return {"defer": False, "shas": full, "own": full, "range": None, "active": True}
        covered = all(_git(repo_root, "merge-base", "--is-ancestor", start, s) is not None for s in extra)
        return {"defer": False, "shas": full + extra, "own": full, "range": (start if covered else anchor, full[0]),
                "active": True}
    except Exception:
        return given
