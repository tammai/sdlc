#!/usr/bin/env python3
"""Diff facts for the reviewers in Review: comment share, new files, single-use exports, single-implementation
interfaces, new dependencies and the list of changed files, for the changes since a base ref (committed +
uncommitted + untracked). The base defaults to the active feature's `Base:` commit. In a workbench, each read-only repo
the feature recorded (`## Repos`) that has moved since is listed with its files, or as gone after a force-push.
With --plan, new exports and dependencies are checked against the plan's "## Public Surface" list; --plan can repeat
(feature close: every slice's plan-B<n>.md), and then the union of their lists is what's declared.

Reviewers cite these numbers instead of arguing taste. Informational only: always exits 0 unless git fails.
Usage: python3 diff_stats.py [--root DIR] [--base REF] [--plan PLAN.md ...] [--format json|md]
Stdlib only, Python 3.9+.
"""
import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks"))
import sdlc_layout  # noqa: E402  (where feature state and documents live, in either layout)
import sdlc_scopes  # noqa: E402  (a workbench feature's `## Repos`)

C_LIKE = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".vue", ".svelte",
          ".go", ".rs", ".java", ".kt", ".cs", ".swift", ".php"}
HASH = {".py", ".rb"}
SOURCE = C_LIKE | HASH
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec)/|\.(test|spec)\.[^/]+$|(^|/)test_[^/]+\.py$|_test\.(py|go)$")

EXPORT_PATTERNS = {
    "js": re.compile(r"^\s*export\s+(?:default\s+)?(?:declare\s+)?(?:async\s+)?"
                     r"(?:function\*?|const|let|var|class|abstract\s+class|interface|type|enum)\s+([A-Za-z_$][\w$]*)"),
    "py": re.compile(r"^(?:async\s+)?(?:def|class)\s+([A-Za-z]\w*)"),
    "go": re.compile(r"^(?:func\s+(?:\([^)]*\)\s*)?|type\s+)([A-Z]\w*)"),
}
INTERFACE = re.compile(r"^\s*(?:export\s+)?(?:interface|abstract\s+class)\s+([A-Za-z_$][\w$]*)")
SURFACE_LINE = re.compile(r"^\s*[-*]\s*(export|endpoint|command|config|env|dependency)\s+`([^`]+)`", re.I)
COMMENT_RATIO_FLAG = 0.25
COMMENT_RATIO_MIN_LINES = 20


def git(root, *args, check=True):
    p = subprocess.run(["git", "-C", root, *args], capture_output=True, encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr.strip()}")
    return p.stdout if p.returncode == 0 else None


def feature_base(root, plan=None):
    """`Base:` from the plan's state file (the plan itself on sdlc 2.0), else from the only active feature's, if that
    commit exists."""
    located = sdlc_layout.features(root)
    if plan and os.path.basename(os.path.dirname(os.path.abspath(plan))) == "state":  # .sdlc/state/<feature>.md
        paths = [os.path.abspath(plan)]
    elif plan:  # the plan sits in the feature's documents folder, named after the feature
        name = os.path.basename(os.path.dirname(os.path.abspath(plan)))
        state = located[name]["state"] if name in located else sdlc_layout.paths(root, name)["state"]
        paths = [os.path.join(root, state)]
    else:
        paths = [os.path.join(root, f["state"]) for f in located.values()]
    bases = []
    for path in paths:
        try:
            text = open(path, encoding="utf-8").read()
        except OSError:
            continue
        m = re.search(r"^Base:\s*`?([0-9a-f]{7,40})\b", text, re.M)
        if m and (plan or re.search(r"^Status:\s*active\b", text, re.M | re.I)):
            bases.append(m.group(1))
    if len(bases) == 1 and git(root, "rev-parse", "--verify", "-q", bases[0] + "^{commit}", check=False):
        return bases[0]
    return None


def default_base(root):
    for ref in ("origin/main", "origin/master", "main", "master"):
        if git(root, "rev-parse", "--verify", "-q", ref, check=False):
            base = git(root, "merge-base", "HEAD", ref, check=False)
            if base and base.strip() != git(root, "rev-parse", "HEAD").strip():
                return base.strip()
    return "HEAD"  # on main itself: only uncommitted work


def lang(path):
    ext = os.path.splitext(path)[1]
    if ext == ".py":
        return "py"
    if ext == ".go":
        return "go"
    if ext in C_LIKE:
        return "js" if ext not in {".rs", ".java", ".kt", ".cs", ".swift", ".php"} else None
    return None


# --- comment classification --------------------------------------------------------------

class CommentScanner:
    """Classifies successive added lines of one hunk as comment or code (block-comment/docstring aware)."""

    def __init__(self, ext):
        self.ext, self.in_block, self.in_doc = ext, False, None

    def is_comment(self, line):
        s = line.strip()
        if not s:
            return None  # blank: neither
        if self.ext in C_LIKE:
            if self.in_block:
                self.in_block = "*/" not in s
                return True
            if s.startswith("//"):
                return True
            if s.startswith("/*"):
                self.in_block = "*/" not in s[2:]
                return True
            return False
        if self.ext == ".py":
            if self.in_doc:
                if self.in_doc in s:
                    self.in_doc = None
                return True
            for q in ('"""', "'''"):
                if s.startswith(q) or re.match(r"^[rbuRBU]{0,2}" + q, s):
                    if s.count(q) == 1:
                        self.in_doc = q
                    return True
        return s.startswith("#")


C_ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}


def unquote(path):
    """A path as git's diff header writes it (C-quoted when it holds non-ASCII or special characters), as on disk."""
    if len(path) < 2 or not (path.startswith('"') and path.endswith('"')):
        return path
    out, s, i = bytearray(), path[1:-1], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in "01234567" and re.match(r"[0-7]{3}", s[i + 1:i + 4]):
                out.append(int(s[i + 1:i + 4], 8))
                i += 4
                continue
            if nxt in C_ESCAPES:
                out.append(C_ESCAPES[nxt])
                i += 2
                continue
        out += c.encode("utf-8")
        i += 1
    return out.decode("utf-8", errors="replace")


def nul_names(text):
    """Paths from git's -z (NUL-separated) name output."""
    return [n for n in (text or "").split("\0") if n]


def parse_diff(diff_text):
    """{path: [added lines in order, with None separating hunks]}"""
    files, current = {}, None
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            path = line[4:].rstrip("\t")  # git ends a header name holding a space with a tab
            if path == "/dev/null":
                current = None
                continue
            path = unquote(path)
            current = files.setdefault(path[2:] if path.startswith("b/") else path, [])
        elif line.startswith("@@") and current is not None:
            current.append(None)
        elif current is not None and line.startswith("+"):
            current.append(line[1:])
    return files


def read_lines(root, path):
    try:
        with open(os.path.join(root, path), encoding="utf-8", errors="replace") as f:
            return [None] + f.read().splitlines()
    except OSError:
        return []


# --- references ----------------------------------------------------------------------------

def count_refs(root, name, def_path):
    """Caller files (non-test, other than def_path), test files, and uses inside def_path itself."""
    out = git(root, "grep", "-n", "-w", "--untracked", "-I", "-e", name, check=False) or ""
    callers, tests, internal = set(), set(), 0
    defined = False
    for hit in out.splitlines():
        path, _, rest = hit.partition(":")
        text = rest.partition(":")[2]
        pattern = EXPORT_PATTERNS.get(lang(path) or "", None)
        if not defined and path == def_path and pattern and (m := pattern.match(text)) and m.group(1) == name:
            defined = True
            continue
        if path == def_path:
            internal += 1
        elif TEST_PATH.search(path):
            tests.add(path)
        else:
            callers.add(path)
    return len(callers), len(tests), internal


def implementations(root, name):
    # Word-grep in git, regex in Python: git's -E engine varies by platform (\s, \b unreliable on macOS)
    out = git(root, "grep", "-n", "-w", "--untracked", "-I", "-e", name, check=False) or ""
    uses = re.compile(rf"\b(implements|extends)\b[^{{]*\b{re.escape(name)}\b")
    declares = re.compile(rf"\b(interface|class)\s+{re.escape(name)}\b")
    return sum(1 for hit in out.splitlines() if uses.search(hit) and not declares.search(hit))


# --- dependencies -----------------------------------------------------------------------------

def show(root, base, path):
    return git(root, "show", f"{base}:{path}", check=False)


def new_dependencies(root, base, changed):
    deps = []
    for path in changed:
        name = os.path.basename(path)
        if name == "package.json":
            try:
                old = json.loads(show(root, base, path) or "{}")
                new = json.loads(open(os.path.join(root, path), encoding="utf-8").read())
            except (ValueError, OSError):
                continue
            for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                for dep in sorted(set(new.get(section, {})) - set(old.get(section, {}))):
                    deps.append({"file": path, "name": dep, "section": section})
        elif name == "go.mod" or re.match(r"requirements.*\.txt$", name):
            old = set((show(root, base, path) or "").splitlines())
            for line in read_lines(root, path)[1:]:
                s = line.strip()
                if not s or s.startswith(("#", "//", "module ", "go ", "require (", ")")) or line in old:
                    continue
                if name == "go.mod":
                    dep = re.sub(r"^require\s+", "", s).split()[0]
                else:
                    # PEP 508: the name ends at the first specifier, extra or marker; option lines (-r, --index-url) have none
                    m = re.match(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?", s)
                    if not m:
                        continue
                    dep = m.group(0)
                deps.append({"file": path, "name": dep, "section": name})
    return deps


# --- plan surface -----------------------------------------------------------------------------

def plan_surface(plan_path):
    """{kind: [names]} from the plan's "## Public Surface" section, or None if the section is missing."""
    try:
        with open(plan_path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    m = re.search(r"^##\s+Public Surface\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        return None
    surface = {}
    for line in m.group(1).splitlines():
        sm = SURFACE_LINE.match(line)
        if sm:
            surface.setdefault(sm.group(1).lower(), []).append(sm.group(2).strip())
    return surface


def check_surface(surface, exports, deps):
    declared_exports = set(surface.get("export", []))
    declared_deps = set(surface.get("dependency", []))
    built_exports = {e["name"] for e in exports}
    built_deps = {d["name"] for d in deps}
    return {
        "declared": surface,
        "undeclared_exports": sorted(built_exports - declared_exports),
        "undeclared_dependencies": sorted(built_deps - declared_deps),
        "declared_not_built": sorted((declared_exports - built_exports) | (declared_deps - built_deps)),
        "check_by_hand": {k: v for k, v in surface.items() if k not in ("export", "dependency")},
    }


# --- main -----------------------------------------------------------------------------------

def scan(repo, base):
    """One repo's added lines against base: ({path: [None, lines…]}, new files, changed files, new dependencies)."""
    diff = git(repo, "diff", "--no-color", "--no-ext-diff", "-U0", "--diff-filter=AMR", base)
    added = parse_diff(diff)
    status_new = set(nul_names(git(repo, "diff", "-z", "--name-only", "--diff-filter=A", base)))
    untracked = nul_names(git(repo, "ls-files", "-z", "--others", "--exclude-standard"))
    for path in untracked:
        added[path] = [None] + read_lines(repo, path)[1:]
    changed = set(nul_names(git(repo, "diff", "-z", "--name-only", base))) | set(untracked)
    return added, status_new | set(untracked), changed, new_dependencies(repo, base, sorted(added))


def collect(root, base, plans=()):
    # The workbench (or the one repo), then each app repo a workbench feature branched, against its own base; an app
    # repo's paths are prefixed with its folder, its references counted inside it
    sources, flags = [(root, base, "")], []
    branched, why = branched_repos(root, plans)
    flags += why
    sources += [(os.path.join(root, name), rec["base"], name + "/") for name, rec in branched]
    files, exports, interfaces, deps, new_set, changed_set = [], [], [], [], set(), set()
    for repo, repo_base, prefix in sources:
        try:
            added, new, changed, repo_deps = scan(repo, repo_base)
        except RuntimeError as e:
            if not prefix:
                raise
            flags.append(f"app repo {prefix.rstrip('/')} not scanned: {e}")
            continue
        new_set |= {prefix + n for n in new}
        changed_set |= {prefix + n for n in changed}
        deps += [dict(d, file=prefix + d["file"]) for d in repo_deps]
        for path, lines in sorted(added.items()):
            ext = os.path.splitext(path)[1]
            if ext not in SOURCE:
                continue
            code = comments = 0
            scanner = CommentScanner(ext)
            for line in lines:
                if line is None:
                    scanner = CommentScanner(ext)
                    continue
                kind = scanner.is_comment(line)
                if kind is True:
                    comments += 1
                elif kind is False:
                    code += 1
            total = code + comments
            is_test = bool(TEST_PATH.search(path))
            files.append({"path": prefix + path, "new": path in new, "test": is_test, "added_code": code,
                          "added_comments": comments, "comment_ratio": round(comments / total, 2) if total else 0.0})
            if is_test:
                continue
            pattern = EXPORT_PATTERNS.get(lang(path) or "")
            for line in (l for l in lines if l is not None):
                m = pattern.match(line) if pattern else None
                if m and not (lang(path) == "py" and line[:1].isspace()):
                    callers, tests, internal = count_refs(repo, m.group(1), path)
                    exports.append({"name": m.group(1), "file": prefix + path, "caller_files": callers,
                                    "test_files": tests, "internal_uses": internal})
                im = INTERFACE.match(line) if lang(path) == "js" else None
                if im:
                    interfaces.append({"name": im.group(1), "file": prefix + path,
                                       "implementations": implementations(repo, im.group(1))})
    new_files, changed_files = sorted(new_set), sorted(changed_set)
    src = [f for f in files if not f["test"]]
    code_total = sum(f["added_code"] for f in src)
    comment_total = sum(f["added_comments"] for f in src)
    for f in src:
        if f["added_code"] + f["added_comments"] >= COMMENT_RATIO_MIN_LINES and f["comment_ratio"] > COMMENT_RATIO_FLAG:
            flags.append(f"comment-heavy: {f['path']} ({int(f['comment_ratio'] * 100)}% of added lines are comments)")
    if code_total + comment_total >= COMMENT_RATIO_MIN_LINES and comment_total / (code_total + comment_total) > COMMENT_RATIO_FLAG:
        flags.append(f"comment-heavy diff: {int(100 * comment_total / (code_total + comment_total))}% "
                     f"of added source lines are comments")
    for e in exports:
        where = f"{e['name']} in {e['file']}"
        if e["caller_files"] == 0 and e["internal_uses"]:
            flags.append(f"needless export: {where} (only used inside its own file)")
        elif e["caller_files"] == 0:
            flags.append(f"unused export: {where} " + (f"(only used by {e['test_files']} test file(s))"
                                                        if e["test_files"] else "(never used)"))
        elif e["caller_files"] == 1:
            flags.append(f"single-use export: {where} (one caller file; inline it or keep it private?)")
    for i in interfaces:
        if i["implementations"] <= 1:
            flags.append(f"single-implementation abstraction: {i['name']} in {i['file']} "
                         f"({i['implementations']} implementation{'s' if i['implementations'] != 1 else ''})")
    for d in deps:
        flags.append(f"new dependency: {d['name']} ({d['file']} {d['section']})")
    surface = None
    declared = None
    for plan in plans:
        found = plan_surface(plan)
        if found is None:
            flags.append(f"plan not found: {plan}" if not os.path.isfile(plan)
                         else f"plan has no '## Public Surface' section: {plan}")
            continue
        declared = declared or {}
        for kind, names in found.items():
            declared.setdefault(kind, []).extend(n for n in names if n not in declared.get(kind, []))
    if declared is not None:
        surface = check_surface(declared, exports, deps)
        for name in surface["undeclared_exports"]:
            flags.append(f"undeclared export: {name} (not in the plan's Public Surface: unrequested surface)")
        for name in surface["undeclared_dependencies"]:
            flags.append(f"undeclared dependency: {name} (not in the plan's Public Surface: unrequested surface)")
        for name in surface["declared_not_built"]:
            flags.append(f"declared but not built: {name} (in the plan's Public Surface, not in the diff)")
    read_only = moved_read_only(root, plans)
    for m in read_only:
        if m["gone"]:
            flags.append(f"read-only repo {m['repo']}: the recorded commit {m['recorded'][:12]} no longer exists "
                         f"(force-pushed?); it is now at {m['current'][:12]}")
        else:
            flags.append(f"read-only repo moved: {m['repo']} {m['recorded'][:12]} -> {m['current'][:12]} "
                         f"({len(m['files'])} file(s): {', '.join(m['files'][:10])})")
    return {
        "base": base, "read_only": read_only,
        "totals": {"source_files": len(src), "test_files": len(files) - len(src), "new_files": len(new_files),
                   "added_code": code_total, "added_comments": comment_total,
                   "comment_ratio": round(comment_total / (code_total + comment_total), 2)
                   if code_total + comment_total else 0.0},
        "changed_files": changed_files, "new_files": new_files, "files": files, "exports": exports, "interfaces": interfaces,
        "dependencies": deps, "surface": surface, "flags": flags,
    }


def feature_state(root, plans):
    """In a workbench, the feature's state text: the first --plan holding `## Repos`, else the only active feature's;
    else None (never a guess between several features)."""
    if not sdlc_scopes.is_workbench(root):
        return None
    texts = []
    for plan in plans:
        try:
            with open(plan, encoding="utf-8") as f:
                texts.append(f.read())
        except OSError:
            pass
    found = next((t for t in texts if sdlc_scopes.feature_repos(t)), None)
    if found is None:
        active = [t for _, t in sdlc_layout.active(root)]
        found = active[0] if len(active) == 1 else None
    return found


def branched_repos(root, plans):
    """([(name, record)], [flag]): the app repos the workbench feature branched that sdlc may read
    (sdlc_scopes.branched_repos), and a flag for each branch line it leaves out."""
    text = feature_state(root, plans)
    if text is None:
        return [], []
    try:
        kept, dropped = sdlc_scopes.branched_repos(root, text)
    except ValueError as e:
        return [], [f"app repos not scanned: {e}"]
    return kept, [f"app repo {name} not scanned: {why}" for name, why in dropped]


def moved_read_only(root, plans):
    """In a workbench: each read-only repo the feature recorded (`## Repos`, `<name>: read <commit>`) that has moved
    since: [{repo, recorded, current, files, gone}], `gone` when the recorded commit no longer exists (the state:
    feature_state)."""
    out = []
    recorded = sdlc_scopes.feature_repos(feature_state(root, plans))
    for name, rec in recorded.items():
        if not rec.get("read"):
            continue
        try:
            repo = sdlc_scopes.repo_dir(root, name)
        except ValueError:
            continue
        current = (git(repo, "rev-parse", "HEAD", check=False) or "").strip()
        if not current or current.startswith(rec["read"]):
            continue
        gone = git(repo, "cat-file", "-e", rec["read"] + "^{commit}", check=False) is None
        names = None if gone else git(repo, "diff", "-z", "--name-only", rec["read"], current, check=False)
        out.append({"repo": name, "recorded": rec["read"], "current": current,
                    "files": sorted(n for n in (names or "").split("\0") if n), "gone": gone})
    return out


def to_markdown(r):
    t = r["totals"]
    lines = [f"### Diff stats (vs `{r['base'][:12]}`)", "",
             f"- Source files: {t['source_files']} (+{t['test_files']} test files), new files: {t['new_files']}",
             f"- Added: {t['added_code']} code lines, {t['added_comments']} comment lines "
             f"({int(t['comment_ratio'] * 100)}% comments)",
             f"- Changed files ({len(r['changed_files'])}): " + (", ".join(r["changed_files"]) or "none"), ""]
    for m in r.get("read_only") or []:
        lines.append(f"- Read-only repo {m['repo']}: recorded `{m['recorded'][:12]}`, now `{m['current'][:12]}`: "
                     + ("the recorded commit no longer exists" if m["gone"]
                        else ", ".join(m["files"]) or "no file changes"))
    if r.get("read_only"):
        lines.append("")
    if r["flags"]:
        lines += ["**Flags** (facts to check, not verdicts):", ""] + [f"- {f}" for f in r["flags"]]
    else:
        lines.append("No flags.")
    by_hand = (r.get("surface") or {}).get("check_by_hand")
    if by_hand:
        lines += ["", "**Declared surface to check by hand** (endpoints, commands, config, env aren't detected):", ""]
        lines += [f"- {kind} `{name}`" for kind, names in by_hand.items() for name in names]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--base", help="base ref (default: the feature's `Base:` from state.md beside --plan, or from "
                                   "the only active feature; else merge-base with origin/main|main|master, else HEAD)")
    ap.add_argument("--plan", action="append", default=[],
                    help="plan.md whose '## Public Surface' the diff is checked against; repeat for the union")
    ap.add_argument("--format", choices=["json", "md"], default="json")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    root = os.path.abspath(a.root)
    try:
        top = git(root, "rev-parse", "--show-toplevel").strip()
        plans = [os.path.abspath(p) for p in a.plan]
        result = collect(top, a.base or feature_base(top, plans[0] if plans else None) or default_base(top), plans)
    except RuntimeError as e:
        print(json.dumps({"error": str(e)}))
        return 1
    print(to_markdown(result) if a.format == "md" else json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
