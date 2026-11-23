"""sdlc patch: the turn-end (Stop) review's other repos in a workbench.

The Stop review resolves one repo per turn (reporesolve.resolve_repo_root). A turn in a workbench can also edit
other app repos, whose files the workbench's .gitignore hides from that repo's diff: each other touched repo the
review gate wants gets its own diff, from the time the turn began (the session's stored baseline belongs to the
first repo), and its files join the same review call in the slots the first repo's leave, each named by its path
from the session's cwd.
"""
import os

import diffstate
import gitutil
import reporesolve
import sdlc_review_gate
import sdlc_scopes


def _workbench_root(repo):
    """The guarded workbench `repo` is, or is an app repo of; else None."""
    real = os.path.realpath(repo)
    for cand in (real, os.path.dirname(real)):
        if sdlc_scopes.guarded_workbench(cand):
            return cand
    return None


def other_repos(primary, touched_paths, cwd):
    """The repos other than `primary` (any folder in it) that this turn's edit tools touched, in the same workbench:
    its root or one of its app repos (one level below it). Not a workbench: none, so a plain repo keeps one review."""
    primary = gitutil._git_toplevel(primary) or primary
    root = _workbench_root(primary)
    if not root:
        return []
    out = []
    for repo in reporesolve.repos_from_paths(touched_paths, cwd or primary):
        real = os.path.realpath(repo)
        if real == os.path.realpath(primary):
            continue
        if real == root or os.path.dirname(real) == root:
            out.append(repo)
    return sorted(out)


def name_prefix(repo, cwd):
    """What a repo's files are prefixed with in the review: the repo's folder relative to the session's cwd, so the
    agent can open each path as written; none for the repo the session sits at the top of, whose files keep the
    names its own one-repo and commit reviews give them. Within one review no two repos share a prefix."""
    real = os.path.realpath(repo)
    try:
        rel = os.path.relpath(real, os.path.realpath(cwd or repo))
    except ValueError:  # another drive
        return real.replace(os.sep, "/") + "/"
    return "" if rel == "." else rel.replace(os.sep, "/") + "/"


# What the other repos' diffs read (git output bytes, files and bytes cut, timeouts): each get_git_diff call resets
# gitutil's own counters, so the Stop hook adds these to the first repo's.
read_totals = {"bytes": 0, "cut_files": 0, "cut_bytes": 0, "timeouts": 0}


def repo_diff_files(repo, prompt_at, cwd, max_paths=None, max_files=None):
    """`repo`'s reviewable files changed since the turn began (`prompt_at`, seconds), as (prefix, repo-relative path,
    diff). [] when there are none, the turn's start is unknown (every dirty file would look like this turn's), the
    change is past the first repo's size limits (more than `max_paths` reviewable source paths, 10 x `max_files` diff
    files), or git can't say. Never raises."""
    try:
        at = prompt_at if isinstance(prompt_at, (int, float)) and 0 < prompt_at < 1e11 else None
        if at is None:
            return []
        head_at = gitutil._git_head_at(repo, at)
        paths, base, top, untracked, _ = diffstate.compute_v2_review_set(
            repo, None, head_at, {}, since_ns=int(at * 1e9))
        if not paths or (max_paths and sum(gitutil._is_reviewable_source(os.path.relpath(p, top))
                                           for p in paths) > max_paths):
            return []
        timeouts = gitutil._diff_read.get("timeouts", 0)  # the one counter get_git_diff doesn't reset
        diff = gitutil.get_git_diff(top, base, full_context=False, paths=paths, untracked_paths=untracked)
        for key in read_totals:
            read_totals[key] += gitutil._diff_read.get(key, 0) - (timeouts if key == "timeouts" else 0)
        if not diff or not diff.strip():
            return []
        files = gitutil.parse_diff_into_files(diff)
        if max_files and len(files) > 10 * max_files:
            return []
        files = gitutil.filter_preexisting_from_diff(files, top, head_at or "HEAD")
        prefix = name_prefix(top, cwd)
        return [(prefix, path, content) for path, content in files]
    except Exception:
        return []


def other_repo_files(primary, touched_paths, prompt_at, cwd, max_paths=None, max_files=None):
    """The files of every other touched repo of the workbench that the review gate wants reviewed, as (prefix,
    repo-relative path, diff)."""
    out = []
    for repo in other_repos(primary, touched_paths, cwd):
        try:
            wanted = sdlc_review_gate.review_wanted(repo)
        except Exception:
            wanted = True  # the gate's own rule: an error reviews
        if wanted:
            out.extend(repo_diff_files(repo, prompt_at, cwd, max_paths, max_files))
    return out


def pick(files, slots):
    """At most `slots` of the (prefix, path, diff) files, ranked as the first repo's are but on the repo-relative
    path (a repo folder named `api` or `auth` must not outrank the rest), as (prefixed path, diff) pairs."""
    if slots <= 0:
        return []
    pairs = [(path, content) for _, path, content in files]
    prefix_of = {id(pair): prefix for pair, (prefix, _, _) in zip(pairs, files)}
    chosen, _ = gitutil._prioritize_diff_files(pairs, slots)
    return [(prefix_of[id(pair)] + pair[0], pair[1]) for pair in chosen]
