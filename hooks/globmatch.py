"""Matching a committed glob (`**`, `*`, `?`, `{a,b}`; `[` is literal) against a repo-relative path, in time that a
hostile glob can't blow up: the commit review's security areas and doctor's rule paths come from files anyone can
commit.

The language is exactly the one the commit review's old regex had (sdlc_review_gate._glob_re before c9e318b):
`**/` is an optional `.*/`, any other `**` is `.*`, `*` is `[^/]*`, `?` is `[^/]`, `{a,b}` (up to the first `}`) is
an alternation of literals, anything else is literal; anchored at both ends. But instead of a backtracking regex, the
glob is compiled into a small automaton and run over the path with a set of states (Thompson's construction), so the
time is linear in the path for any glob: no glob can stall it, and none is left unjudged.
"""
import functools

ANY, NOSLASH = object(), object()  # the two character classes; anything else on an edge is a literal character


def _tokens(pattern):
    """The old regex's reading of a glob, as tokens: ("lit", c), ("star",), ("qm",), ("any",), ("optdir",),
    ("alt", [str, ...])."""
    out, i = [], 0
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**/", i):
            out.append(("optdir",))
            i += 3
            continue
        if pattern.startswith("**", i):
            out.append(("any",))
            i += 2
            continue
        if c == "{":
            end = pattern.find("}", i)
            if end > i:
                out.append(("alt", pattern[i + 1:end].split(",")))
                i = end + 1
                continue
        out.append(("star",) if c == "*" else ("qm",) if c == "?" else ("lit", c))
        i += 1
    return out


@functools.lru_cache(maxsize=256)
def _compile(pattern):
    """(edges, eps, accept): edges[n] = [(label, m)], eps[n] = [m]; node 0 starts."""
    edges, eps = [[]], [[]]

    def node():
        edges.append([])
        eps.append([])
        return len(edges) - 1

    cur = 0
    for tok in _tokens(pattern):
        kind = tok[0]
        nxt = node()
        if kind == "lit":
            edges[cur].append((tok[1], nxt))
        elif kind == "qm":
            edges[cur].append((NOSLASH, nxt))
        elif kind in ("star", "any"):
            loop = node()
            eps[cur].append(loop)
            edges[loop].append((NOSLASH if kind == "star" else ANY, loop))
            eps[loop].append(nxt)
        elif kind == "optdir":  # (?:.*/)?
            eps[cur].append(nxt)
            loop = node()
            eps[cur].append(loop)
            edges[loop].append((ANY, loop))
            edges[loop].append(("/", nxt))
        else:  # alt: each literal as its own chain to nxt
            for word in tok[1]:
                at = cur
                for ch in word[:-1]:
                    step = node()
                    edges[at].append((ch, step))
                    at = step
                if word:
                    edges[at].append((word[-1], nxt))
                else:
                    eps[at].append(nxt)
        cur = nxt
    return edges, eps, cur


def _closure(states, eps):
    todo, seen = list(states), set(states)
    while todo:
        for m in eps[todo.pop()]:
            if m not in seen:
                seen.add(m)
                todo.append(m)
    return seen


def glob_match(pattern, path):
    """Whether the repo-relative `path` matches the glob `pattern`, anchored at both ends."""
    edges, eps, accept = _compile(pattern)
    states = _closure({0}, eps)
    for ch in path:
        step = set()
        for n in states:
            for label, m in edges[n]:
                if label is ANY or (label is NOSLASH and ch != "/") or label == ch:
                    step.add(m)
        if not step:
            return False
        states = _closure(step, eps)
    return accept in states


def judgeable(pattern):
    """Every glob is judged (kept for callers): True."""
    return True


class Glob:
    """A glob with a regex-like `match(path)`, for callers that hold a list of compiled patterns."""

    def __init__(self, pattern):
        self.pattern = pattern

    def match(self, path):
        return glob_match(self.pattern, path)
