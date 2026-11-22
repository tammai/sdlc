"""Matching a committed glob (`**`, `*`, `?`, `{a,b}`; `[` is literal) against a repo-relative path, in time that a
hostile glob can't blow up: the commit review's security areas and doctor's rule paths come from files anyone can commit.

The path and the glob are compared segment by segment (`/`), each segment with fnmatch, whose translation needs no
backtracking across a `*`; `**` as a whole segment takes any number of segments. Braces are expanded, up to
MAX_EXPANSIONS patterns: past that, or past MAX_LENGTH characters, the glob isn't judged and `match` says True (the
caller then errs on its safe side: a security area that matches is reviewed, a rule that matches isn't called dead).
"""
import fnmatch
import re

MAX_EXPANSIONS = 64
MAX_LENGTH = 300


def expand_braces(pattern, limit=MAX_EXPANSIONS):
    """Every brace alternative of `pattern` (innermost first), or None when there would be more than `limit`."""
    out, todo = [], [pattern]
    while todo:
        p = todo.pop()
        m = re.search(r"\{([^{}]*)\}", p)
        if not m:
            out.append(p)
        else:
            todo.extend(p[:m.start()] + alt + p[m.end():] for alt in m.group(1).split(","))
        if len(out) + len(todo) > limit:
            return None
    return out


def _segment(glob):
    """One segment for fnmatch: a run of `*` is one, and `[` is literal (as in `app/[id].ts`), never a class."""
    return re.sub(r"\*+", "*", glob.replace("[", "[[]"))


def _segments_match(globs, parts):
    memo = {}

    def at(i, j):
        if (i, j) in memo:
            return memo[(i, j)]
        if i == len(globs):
            found = j == len(parts)
        elif globs[i] == "**":
            found = any(at(i + 1, k) for k in range(j, len(parts) + 1))
        else:
            found = j < len(parts) and fnmatch.fnmatchcase(parts[j], _segment(globs[i])) and at(i + 1, j + 1)
        memo[(i, j)] = found
        return found

    return at(0, 0)


def judgeable(pattern):
    """Whether `pattern` is small enough to judge (glob_match says True for one that isn't)."""
    return len(pattern) <= MAX_LENGTH and expand_braces(pattern) is not None


def glob_match(pattern, path):
    """Whether the repo-relative `path` matches the glob `pattern` (anchored at the repo root); True when the glob is
    too big to judge (see the module's docstring)."""
    if len(pattern) > MAX_LENGTH:
        return True
    expanded = expand_braces(pattern)
    if expanded is None:
        return True
    parts = path.split("/")
    for p in expanded:
        globs = [g for g in re.sub(r"(?:\*\*/)+", "**/", p).split("/")]
        if _segments_match(globs, parts):
            return True
    return False


class Glob:
    """A glob with a regex-like `match(path)`, for callers that hold a list of compiled patterns."""

    def __init__(self, pattern):
        self.pattern = pattern

    def match(self, path):
        return glob_match(self.pattern, path)
