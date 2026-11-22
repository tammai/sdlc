"""Matching a committed glob (`**`, `*`, `?`, `{a,b}`; `[` is literal) against a repo-relative path, in time that a
hostile glob can't blow up: the commit review's security areas and doctor's rule paths come from files anyone can commit.

The path and the glob are compared segment by segment (`/`), each segment with fnmatch, whose translation needs no
backtracking across a `*`; `**` as a whole segment takes any number of segments, and one inside a segment crosses `/`
as it always did. Braces are expanded, up to
MAX_EXPANSIONS patterns: past that, or past MAX_LENGTH characters, the glob isn't judged and `match` says True (the
caller then errs on its safe side: a security area that matches is reviewed, a rule that matches isn't called dead).
"""
import fnmatch
import functools
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


def _deep(pattern, limit=MAX_EXPANSIONS):
    """`pattern` with each `**` inside a segment (`**.pem`, `secrets**`, `a**/b`) made whole: `A**B` is `A*B` or
    `A*/**/*B`, so it still crosses `/` as it always did. None past `limit` patterns."""
    out, todo = [], [pattern]
    while todo:
        p = todo.pop()
        segs = p.split("/")
        k = next((n for n, g in enumerate(segs) if "**" in g and g != "**"), None)
        if k is None:
            out.append(p)
        else:
            a, b = segs[k].split("**", 1)
            for seg in (f"{a}*{b}", f"{a}*/**/*{b}"):
                todo.append("/".join(segs[:k] + [seg] + segs[k + 1:]))
        if len(out) + len(todo) > limit:
            return None
    return out


@functools.lru_cache(maxsize=256)
def _globs(pattern):
    """The segment lists `pattern` stands for, or None when it's too big to judge (or its braces don't balance)."""
    if len(pattern) > MAX_LENGTH or pattern.count("{") != pattern.count("}"):
        return None
    braced = expand_braces(pattern)
    if braced is None or any("{" in p or "}" in p for p in braced):
        return None
    out = []
    for p in braced:
        deep = _deep(re.sub(r"(?:\*\*/)+", "**/", re.sub(r"\*{3,}", "**", p)))  # a run of `*` crosses `/` once
        if deep is None or len(out) + len(deep) > MAX_EXPANSIONS:
            return None
        out += [d.split("/") for d in deep]
    return tuple(tuple(g) for g in out)


def judgeable(pattern):
    """Whether `pattern` is small enough to judge (glob_match says True for one that isn't)."""
    return _globs(pattern) is not None


def glob_match(pattern, path):
    """Whether the repo-relative `path` matches the glob `pattern` (anchored at the repo root); True when the glob is
    too big to judge (see the module's docstring)."""
    globs = _globs(pattern)
    if globs is None:
        return True
    parts = path.split("/")
    return any(_segments_match(g, parts) for g in globs)


class Glob:
    """A glob with a regex-like `match(path)`, for callers that hold a list of compiled patterns."""

    def __init__(self, pattern):
        self.pattern = pattern

    def match(self, path):
        return glob_match(self.pattern, path)
