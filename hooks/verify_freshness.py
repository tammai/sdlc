#!/usr/bin/env python3
"""sdlc verify-freshness hook.

Active only while an sdlc feature is in Stage 3 (Review), at every track. Freshness is tracked per scope: each package of a monorepo (`packages` in
.sdlc/config.json), or the whole project; in a workbench, each writable repo (its tree taken in its own git repo, a
repo the feature never branched starting fresh) and the workbench itself (a file in no app repo).
  - PostToolUse Edit/Write/MultiEdit/NotebookEdit on a code file -> the owning package goes stale (a file outside
                                                                     every package: all of them)
  - PostToolUse / PostToolUseFailure Bash running a scope's full   -> that scope goes fresh (records time, HEAD,
    test command, in that scope's directory (`cd <path> && <test>`,   worktree tree and the result: pass, fail, or
    or the session cwd)                                               unknown when a command runs after it); a root `commands.test`
                                                                     next to packages makes every scope fresh
  - Stop                                                          -> in a git repo, diff the worktree against each
                                                                     scope's tree from its last full run (catches
                                                                     edits via Bash, formatters, subagents); block if
                                                                     any scope is stale, naming what to rerun
  - PostToolUse / PostToolUseFailure Bash running scripts/verify.py,  -> the hook's own copy of the run under "verify"
    in Build or Review (Stage 2 or 3), alone or in any segment of a       (verify.json's entry for that run, when its tree
    chained command                                                     is the current code: `red AC-nnn`, or a full
                                                                     run's result, which marks every scope fresh); the
                                                                     trust anchor compares the two records later

The worktree tree is built with a throwaway copy of the git index (the real index is never touched).
Test commands: `commands.test` / `packages[].commands.test` from .sdlc/config.json; without a config, the
`test:` command in state.md, else generic runner patterns.
State lives in .sdlc/.work/verify-freshness.json. Never fails the session: any error exits 0 silently and leaves
.sdlc/.work/verify-freshness.error, which /sdlc:doctor reports; the next clean run removes it.
"""
import json
import os
import re
import sys

# subprocess, tempfile, shutil, shlex and datetime are imported where used: most runs exit before needing them, and
# they cost about 25 ms on every tool call this hook (and prove_budget and trust_anchor, which import it) sees

import sdlc_layout  # sibling module: where feature state and sdlc documents live
import sdlc_scopes  # sibling module: the packages, read as scripts read them

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}  # Windows sessions run commands through either
NON_CODE_DIRS = (".sdlc/", "knowledge/", ".claude/", ".git/", "docs/")
NON_CODE_EXT = (".md", ".mdx", ".txt", ".rst")
GENERIC_TEST = re.compile(
    r"\b(npm|pnpm|yarn|bun)\s+(run\s+)?test\b|\bnpx\s+(vitest|jest)\b|\bvitest\b|\bjest\b|"
    r"\bpytest\b|\bgo\s+test\b|\bcargo\s+test\b|\bmvn\s+\S*\s*test\b|\bgradlew?\s+\S*test\b|"
    r"\bdotnet\s+test\b|\brspec\b|\bphpunit\b|\bmake\s+test\b"
)
PARTIAL_FLAGS = re.compile(
    r"(\s-t\s|--testNamePattern|\s-k\s|--grep\b|\s-run\s|--filter\b|--only\b|\.only\b|--bail\b)"
)
# A positional argument naming one test file (or a pytest node id) makes the run partial
TEST_FILE_ARG = re.compile(
    r"(\.(test|spec)\.[cm]?[jt]sx?|_test\.go|_test\.py|_spec\.rb|Test\.(java|kt))$|(^|/)test_[^/]*\.py$|::"
)
SHELL_SEP = re.compile(r"\|\||&&|[|;&]")
# Redirects (2>&1, >out, &>log, <in) are removed, not cut at: arguments after them still filter the run
REDIRECT = re.compile(r"&?\d*[<>]{1,2}&?\s*[^\s;&|<>]*")
GO_ALL_PACKAGES = ("./...", "...", ".")
# The plugin's verify script, optionally after `cd <dir> &&`; options take a value, so their values aren't actions
# A run of verify.py as the command itself: optionally after `cd <dir> &&`, redirects removed first, and followed
# only by output filters (`| tail`, `| head`, `| grep`, `| cat`) or `; echo …`. Anywhere else it may not run
# (`true || verify.py`), or something after it may rewrite its record (`verify.py; sed … verify.json`)
VERIFY_CMD = re.compile(r"""^\s*(?:cd\s+(?:"[^"]+"|'[^']+'|[^\s;&|]+)\s*&&\s*)*"""
                        r"""python3?(?:\.exe)?[ \t]+(?:"(?P<dq>[^"]+)"|'(?P<sq>[^']+)'|(?P<bare>[^ \t"';&|]+))"""
                        r"""(?P<args>[^;&|\n\r]*)"""
                        r"""(?P<tail>(?:[ \t]*\|[ \t]*(?:tail|head|grep|cat)\b[^;&|\n\r`$()<>]*)*"""
                        r"""(?:[ \t]*;[ \t]*echo\b[^;&|\n\r`()<>]*)?)[ \t]*\Z""")
VERIFY_OPTS = ("--root", "--feature", "--timeout")
PLUGIN_VERIFY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "verify.py")
ERROR_FILE = os.path.join(".sdlc", ".work", "verify-freshness.error")
_root = None  # for the error marker


def now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def project_root(cwd):
    root = os.environ.get("CLAUDE_PROJECT_DIR") or cwd or os.getcwd()
    d = os.path.abspath(root)
    while True:
        if os.path.isdir(os.path.join(d, ".sdlc")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def feature_state(root, feature):
    """The feature's state file text, or None."""
    try:
        with open(os.path.join(root, sdlc_layout.features(root)[feature]["state"]), encoding="utf-8") as f:
            return f.read()
    except (OSError, KeyError):
        return None


def feature_base(root, feature):
    """The commit the feature started from (`Base:` in its state.md), or None."""
    text = feature_state(root, feature)
    if text is None:
        return None
    m = re.search(r"^Base:\s*`?([0-9a-f]{7,40})\b", text, re.M)
    return m.group(1) if m else None


def changed_since(root, base):
    """Code files changed since `base` (committed, uncommitted, untracked), or None if git can't tell."""
    diff = git(root, "diff", "--name-only", "--no-renames", base)
    untracked = git(root, "ls-files", "--others", "--exclude-standard")
    top = git(root, "rev-parse", "--show-toplevel")
    if diff is None or untracked is None or not top:
        return None
    names = set(diff.splitlines()) | set(untracked.splitlines())
    return [norm(os.path.relpath(os.path.join(top, n), root)) for n in sorted(names)
            if n and is_code_file(root, os.path.join(top, n))]


def initial_scope_state(root, feature, scopes):
    """On entering Stage 3: every scope stale, except, in a monorepo with a recorded feature base, packages the
    feature hasn't touched. Those start fresh from a worktree snapshot, so later changes to them still count."""
    stale = {"stale": True, "reason": "no full test run recorded in Stage 3 yet"}
    states = {sc["name"]: dict(stale) for sc in scopes}
    if any(sc.get("repo") for sc in scopes):
        return initial_workbench_state(root, feature, scopes, states)
    base = feature_base(root, feature) if len(scopes) > 1 else None
    changed = changed_since(root, base) if base else None
    if not changed:  # no base, git can't tell, or nothing detected: stay conservative
        return states
    touched = {sc["name"] for f in changed for sc in scope_for(scopes, f)}
    tree = worktree_tree(root)
    for sc in scopes:
        if sc["name"] not in touched and tree:
            states[sc["name"]] = {"stale": False, "reason": "", "tree": tree, "head": git_head(root),
                                  "note": f"unchanged since the feature base {base}"}
    return states


def initial_workbench_state(root, feature, scopes, states):
    """A workbench: a repo the feature never branched (no `## Repos` line) starts fresh, and so does one whose code
    is unchanged since its recorded base, like the workbench itself since `Base:`; anything git can't tell stays stale."""
    recorded = sdlc_scopes.feature_repos(feature_state(root, feature))
    base = feature_base(root, feature)
    for sc in scopes:
        where = scope_dir(root, sc)
        if sc.get("repo"):
            rec = recorded.get(sc["name"]) or {}
            changed = changed_since(where, rec["base"]) if rec.get("branch") else []
            note = f"unchanged since its base {rec['base']}" if rec.get("branch") else "not touched by the feature"
        else:
            changed = changed_since(where, base) if base else None
            note = f"unchanged since the feature base {base}"
        tree = worktree_tree(where)
        if changed == [] and tree:
            states[sc["name"]] = {"stale": False, "reason": "", "tree": tree, "head": git_head(where), "note": note}
    return states


def active_verify_feature(root):
    for name, text in sdlc_layout.active(root):
        if re.search(rf"^Current:\s*Stage\s*{sdlc_layout.REVIEW}\b", text, re.M | re.I):
            m = re.search(r"test:\s*`([^`]+)`", text)
            return name, (m.group(1).strip() if m else None)
    return None, None


ROOT = "(root)"


def load_scopes(root, state_test_cmd):
    """([{name, path, tests}], root_tests): one scope per package, else the whole project. `tests` empty means
    "use the generic runner patterns"; root_tests (monorepo only) are root-level commands that cover every scope."""
    try:
        with open(os.path.join(root, ".sdlc", "config.json"), encoding="utf-8") as f:
            config = json.load(f)
    except (OSError, ValueError):
        config = {}
    config = config if isinstance(config, dict) else {}
    if config.get("workbench") is True and sdlc_scopes.is_workbench(root):
        try:
            return [{"name": sc["name"], "path": sc["path"], "repo": sc["repo"] is not None,
                     "tests": [t for t in [sc["commands"].get("test")] if t]}
                    for sc in sdlc_scopes.workbench_scopes(root)], []
        except ValueError:
            pass  # a manifest it can't read: the workbench alone, as before (doctor reports the manifest)
    if sdlc_scopes.packages(config):
        scopes = [{"name": sc["name"], "path": sc["path"], "tests": [t for t in [sc["commands"].get("test")] if t]}
                  for sc in sdlc_scopes.scopes(config)]
        root_test = sdlc_scopes.root_commands(config).get("test")
        return scopes, [root_test] if root_test else []
    root_test = sdlc_scopes.scopes(config)[0]["commands"].get("test")
    tests = [t for t in (state_test_cmd, root_test) if t]
    return [{"name": ROOT, "path": ".", "tests": list(dict.fromkeys(tests))}], []


def norm(path):
    p = os.path.normpath(path).replace(os.sep, "/")
    return "." if p in ("", ".") else p.strip("/")


def scope_for(scopes, rel_path):
    """Scopes a changed file belongs to: the package whose path contains it, else (shared file) all of them."""
    if len(scopes) == 1:
        return scopes
    owners = [sc for sc in scopes if sc["path"] != "." and (rel_path == sc["path"] or rel_path.startswith(sc["path"] + "/"))]
    if owners:
        return [max(owners, key=lambda sc: len(sc["path"]))]
    # A workbench: a file in no app repo is the workbench's own
    return [sc for sc in scopes if sc["name"] == sdlc_scopes.WORKBENCH_SCOPE] or scopes


def scope_dir(root, sc):
    """The git worktree a scope's tree is taken in: its own repo in a workbench, else the project."""
    return os.path.join(root, sc["path"]) if sc.get("repo") else root


def run_dir(command, end, root, cwd):
    """Directory (relative to root) a command runs in: the last `cd` before position `end`, else the hook's cwd."""
    base = cwd or root
    for target in re.findall(r"""\bcd\s+("[^"]+"|'[^']+'|[^\s;&|]+)\s*(?:&&|;)""", command[:end]):
        base = os.path.join(base, os.path.expanduser(target.strip("\"'")))
    return norm(os.path.relpath(os.path.abspath(base), root))


def state_path(root):
    return os.path.join(root, ".sdlc", ".work", "verify-freshness.json")


def load(root):
    try:
        return json.load(open(state_path(root), encoding="utf-8"))
    except Exception:
        return {}


def save(root, data):
    os.makedirs(os.path.dirname(state_path(root)), exist_ok=True)
    with open(state_path(root), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def git_head(root):
    import subprocess
    try:
        return subprocess.run(
            ["git", "-C", root, "rev-parse", "--short", "HEAD"],
            capture_output=True, encoding="utf-8", errors="replace", timeout=5,
        ).stdout.strip() or None
    except Exception:
        return None


def git(root, *args, env=None):
    import subprocess
    # git writes paths as UTF-8; the default (Windows code page) decoding crashes on a non-ASCII repo folder
    p = subprocess.run(["git", "-C", root, *args], capture_output=True, encoding="utf-8", errors="replace",
                       timeout=5, env=env)
    return p.stdout.strip() if p.returncode == 0 else None


def worktree_tree(root):
    """Tree object of the current worktree (tracked + untracked, minus ignored, minus .sdlc/.work/: the hooks' scratch
    changes on every run, and a repo that committed it before ignoring it would never match), via a temp index copy."""
    import shutil
    import tempfile
    index = git(root, "rev-parse", "--path-format=absolute", "--git-path", "index")
    if not index:
        return None
    fd, tmp = tempfile.mkstemp(prefix="sdlc-verify-index-")
    os.close(fd)
    try:
        if os.path.exists(index):
            # Reuse stat info so unchanged files aren't rehashed; copy2 keeps the index mtime,
            # which git needs to detect same-second ("racy") edits
            shutil.copy2(index, tmp)
        else:
            os.remove(tmp)
        env = dict(os.environ, GIT_INDEX_FILE=tmp)
        if git(root, "add", "-A", env=env) is None:
            return None
        if git(root, "rm", "-r", "--cached", "-q", "--ignore-unmatch", "--", ".sdlc/.work", env=env) is None:
            return None
        return git(root, "write-tree", env=env)
    except Exception:
        return None
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def changed_code_files(root, old_tree, new_tree):
    """Code files that differ between the trees, or None when it can't be told (tree gone)."""
    if new_tree == old_tree:
        return []
    # -z: NUL-separated and unquoted, so names with spaces or non-ASCII come back as on disk
    names = git(root, "diff", "-z", "--name-only", "--no-renames", old_tree, new_tree)
    top = git(root, "rev-parse", "--show-toplevel")
    if names is None or not top:
        return None
    return [norm(os.path.relpath(os.path.join(top, n), root)) for n in names.split("\0")
            if n and is_code_file(root, os.path.join(top, n))]


def is_code_file(root, file_path):
    if not file_path:
        return False
    rel = os.path.relpath(os.path.abspath(file_path), root).replace(os.sep, "/")
    docs = sdlc_layout.docs_dir(root)
    if rel.startswith("..") or rel.startswith(NON_CODE_DIRS) or (docs and rel.startswith(docs + "/")):
        return False
    return not rel.lower().endswith(NON_CODE_EXT)


def names_specific_tests(args, is_go):
    import shlex
    try:
        tokens = shlex.split(args)
    except ValueError:
        tokens = args.split()
    for t in (t for t in tokens if not t.startswith("-")):
        if TEST_FILE_ARG.search(t):
            return True
        if is_go and t not in GO_ALL_PACKAGES and not t.endswith("/..."):
            return True
    return False


def match_full_run(command, tests):
    """End position of a full (unfiltered) run of one of `tests` (or of a generic runner when `tests` is empty)
    in `command`, else None."""
    if not command:
        return None
    if tests:
        hits = [(m.end(), t) for t in tests
                for m in [re.search(r"(^|[\s;&|(])" + re.escape(t) + r"(?=$|[\s;&|)])", command)] if m]
        if not hits:
            return None
        end = min(hits)[0]
    else:
        m = GENERIC_TEST.search(command)
        if not m:
            return None
        end = m.end()
    # Only arguments added after the test command filter it: flags inside it (unittest's `-t .`) are its own
    args = SHELL_SEP.split(REDIRECT.sub(" ", command[end:]))[0]
    if PARTIAL_FLAGS.search(" " + args + " "):
        return None
    if names_specific_tests(args, is_go=re.search(r"\bgo\s+test\b", command) is not None):
        return None
    return end


def exit_is_the_tests(command, tests):
    end = match_full_run(command, tests)
    if end is None:
        return False
    after = SHELL_SEP.split(REDIRECT.sub(" ", command[end:]))[1:]
    return not any(part.strip(" ()\t\n") for part in after)


def fresh_scopes(command, scopes, root_tests, root, cwd, configured):
    """Names of the scopes a Bash command fully tests."""
    end = match_full_run(command, root_tests) if root_tests else None
    if end is not None and run_dir(command, end, root, cwd) == ".":
        return [sc["name"] for sc in scopes]
    names = []
    for sc in scopes:
        end = match_full_run(command, sc["tests"])
        if end is None:
            continue
        # A configured scope's command only counts in that scope's own directory; legacy (no config) ignores cd
        if not configured or run_dir(command, end, root, cwd) == sc["path"]:
            names.append(sc["name"])
    return names


def is_plugin_verify(path):
    """The plugin's own scripts/verify.py, spelled exactly one of the ways it's written: its absolute path (native,
    with forward slashes, or Git Bash's /c/...) or `${CLAUDE_PLUGIN_ROOT}/scripts/verify.py`. Nothing is resolved:
    the shell expands the text before python runs, so anything it could reinterpret (`$(…)`, globs, `..`, escapes)
    simply doesn't match. A project script with the same name, or a relative path, isn't it."""
    native = os.path.abspath(PLUGIN_VERIFY)
    slashed = native.replace("\\", "/")
    forms = {native, slashed, "${CLAUDE_PLUGIN_ROOT}/scripts/verify.py"}
    if re.match(r"^[A-Za-z]:/", slashed):
        forms.add(f"/{slashed[0].lower()}{slashed[2:]}")
    if os.name == "nt":
        return path.lower() in {f.lower() for f in forms}
    return path in forms


def verify_runs(command, root, cwd, feature):
    """([("red", "AC-nnn") | ("full", None)], whether the call's exit code is verify.py's) for a run of the plugin's
    scripts/verify.py on this project and feature; ([], False) for anything else, including a run against another
    root, directory or feature, or `--help`."""
    flat = REDIRECT.sub(" ", command or "")
    m = VERIFY_CMD.match(flat)
    if not m or not is_plugin_verify(m.group("dq") or m.group("sq") or m.group("bare")):
        return [], False
    import shlex
    try:
        words = shlex.split(m.group("args"))
    except ValueError:
        return [], False
    words = [part for w in words for part in (w.split("=", 1) if w.startswith("--") and "=" in w else [w])]
    if any(w.startswith("-") and w not in VERIFY_OPTS for w in words):
        return [], False  # --help, or an option verify.py doesn't take: nothing was verified
    opts = {w: words[i + 1] for i, w in enumerate(words[:-1]) if w in VERIFY_OPTS}
    here = os.path.join(root, run_dir(flat, m.start("args"), root, cwd))
    if os.path.normcase(os.path.abspath(os.path.join(here, opts.get("--root", ".")))) != os.path.normcase(root):
        return [], False
    if opts.get("--feature", feature) != feature:
        return [], False
    args = [w for i, w in enumerate(words) if not w.startswith("-") and not (i and words[i - 1] in VERIFY_OPTS)]
    observable = not m.group("tail").strip()  # after a pipe or an echo, the exit code is another command's
    if not args:
        return [("full", None)], observable
    if args[0] == "red" and len(args) > 1:
        return [("red", ac) for ac in args[1:]], observable
    return [], False  # status, or something verify.py won't accept


def active_build_or_prove_feature(root):
    return next((name for name, text in sdlc_layout.active(root)
                 if re.search(rf"^Current:\s*Stage\s*[{sdlc_layout.BUILD}{sdlc_layout.REVIEW}]\b", text, re.M | re.I)), None)


def record_verify(root, feature, runs, exit_result=None):
    """The hook's own copy of verify runs: the entry verify.py just wrote to verify.json, taken only when it is for
    the code as it is now. Not the command's exit code: after `| tail` or `; echo $?` that's another command's. A
    later edit to verify.json, in another call, then no longer matches this copy (the trust anchor reports it). When
    the call's exit code is verify.py's own (`exit_result`), the entry must agree with it. A
    full run also counts as a full test run of every scope, so Build's verify carries into Review: the Stop check
    compares that tree with the code, so later edits still make it stale. Without a tree nothing is recorded."""
    tree = worktree_tree(root)
    try:
        with open(os.path.join(root, ".sdlc", ".work", "verify.json"), encoding="utf-8") as f:
            script = json.load(f)
    except (OSError, ValueError):
        return
    if not tree or not isinstance(script, dict) or script.get("feature") != feature:
        return
    st = load(root)
    if st.get("feature") != feature:
        st = {"feature": feature, "scopes": {}}
    rec = st.setdefault("verify", {})
    recorded = False
    for kind, ac in runs:
        if kind == "red":
            if exit_result == "fail":  # verify.py red exits non-zero when it refuses: nothing was recorded
                continue
            entry = (script.get("red") or {}).get(ac)
            if isinstance(entry, dict) and entry.get("tree") == tree:
                rec.setdefault("red", {})[ac] = tree
                recorded = True
            continue
        last = script.get("last")
        if not isinstance(last, dict) or last.get("tree") != tree or last.get("result") not in ("pass", "fail"):
            continue
        if exit_result and exit_result != last["result"]:
            continue
        rec["last"] = {"tree": tree, "result": last["result"], "at": now()}
        recorded = True
        scopes, _ = load_scopes(root, None)
        for sc in scopes:
            where = scope_dir(root, sc)  # a workbench's app repo: its own tree, so the Stop check can diff it
            st.setdefault("scopes", {}).setdefault(sc["name"], {}).update(
                stale=False, reason="", last_test_at=now(), last_test_cmd="verify.py", last_result=last["result"],
                head=git_head(where), tree=tree if where == root else worktree_tree(where))
    if recorded:
        save(root, st)


def main():
    data = json.load(sys.stdin)
    event = data.get("hook_event_name", "")
    global _root
    root = _root = project_root(data.get("cwd"))
    if not root:
        return
    if event in ("PostToolUse", "PostToolUseFailure") and data.get("tool_name") in SHELL_TOOLS:
        resp = data.get("tool_response") or {}
        building = active_build_or_prove_feature(root)
        runs, observable = verify_runs((data.get("tool_input") or {}).get("command", ""), root, data.get("cwd"),
                                       building) if building else ([], False)
        if runs:
            if not (data.get("is_interrupt") or (isinstance(resp, dict) and resp.get("interrupted"))):
                exit_result = ("fail" if event == "PostToolUseFailure" else "pass") if observable else None
                record_verify(root, building, runs, exit_result)
            return
    feature, test_cmd = active_verify_feature(root)
    if not feature:
        return
    scopes, root_tests = load_scopes(root, test_cmd)
    configured = os.path.exists(os.path.join(root, ".sdlc", "config.json"))
    st = load(root)
    if st.get("feature") != feature or "scopes" not in st:
        st = {"feature": feature, "scopes": initial_scope_state(root, feature, scopes)}
    for sc in scopes:
        st["scopes"].setdefault(sc["name"], {"stale": True, "reason": "no full test run recorded in Stage 3 yet"})

    if event in ("PostToolUse", "PostToolUseFailure"):
        tool = data.get("tool_name", "")
        tin = data.get("tool_input") or {}
        if tool in EDIT_TOOLS and event == "PostToolUse":
            fp = tin.get("file_path") or tin.get("notebook_path")
            if is_code_file(root, fp):
                rel = norm(os.path.relpath(os.path.abspath(fp), root))
                for sc in scope_for(scopes, rel):
                    st["scopes"][sc["name"]].update(stale=True, last_edit_at=now(), last_edit_file=rel,
                                                    reason=f"{rel} edited at {now()} after the last full test run")
                save(root, st)
        elif tool in SHELL_TOOLS:
            cmd = tin.get("command", "")
            resp = data.get("tool_response") or {}
            if data.get("is_interrupt") or (isinstance(resp, dict) and resp.get("interrupted")):
                return
            names = fresh_scopes(cmd, scopes, root_tests, root, data.get("cwd"), configured)
            if names:
                trees = {}
                # A non-zero exit arrives as PostToolUseFailure. It's the tests' only when nothing runs after them
                # (`| tail`, `; echo $?` report their own exit)
                tests = [sc["tests"] for sc in scopes if sc["name"] in names] + [root_tests]
                last = any(exit_is_the_tests(cmd, t) for t in tests)
                result = ("fail" if event == "PostToolUseFailure" else "pass") if last else "unknown"
                for sc in scopes:
                    if sc["name"] not in names:
                        continue
                    where = scope_dir(root, sc)
                    if where not in trees:
                        trees[where] = (worktree_tree(where), git_head(where))
                    tree, head = trees[where]
                    st["scopes"][sc["name"]].update(stale=False, reason="", last_test_at=now(), last_test_cmd=cmd,
                                                    last_result=result, head=head, tree=tree)
                save(root, st)
        return

    if event != "Stop":
        return
    tracked = [sc for sc in scopes if st["scopes"][sc["name"]].get("tree")]
    trees = {}
    for sc in tracked:
        where = scope_dir(root, sc)
        if where not in trees:
            trees[where] = worktree_tree(where)
        new_tree = trees[where]
        if not new_tree:
            continue
        s_st = st["scopes"][sc["name"]]
        changed = changed_code_files(where, s_st["tree"], new_tree)
        if changed is None:
            continue
        if sc.get("repo"):  # every change in its own repo is its, named from the workbench
            mine = [f"{sc['path']}/{f}" for f in changed]
        else:
            mine = [f for f in changed if sc in scope_for(scopes, f)]
        if mine:
            more = f" and {len(mine) - 5} more" if len(mine) > 5 else ""
            s_st.update(stale=True, reason=f"{', '.join(mine[:5])}{more} changed since the last full test run")
        else:  # edits since the run were reverted, or only touched other scopes or non-code
            s_st.update(stale=False, reason="")
    save(root, st)
    stale = [sc for sc in scopes if st["scopes"][sc["name"]].get("stale")]
    if not stale:
        return
    parts = []
    for sc in stale:
        how = sc["tests"][0] if sc["tests"] else None
        if how and sc["path"] != ".":
            how = f"cd {sc['path']} && {how}"
        label = "" if sc["name"] == ROOT else f"{sc['name']}: "
        parts.append(f"{label}{st['scopes'][sc['name']]['reason']}" + (f" → run `{how}`" if how else ""))
    msg = (f"Verify freshness ({feature}): test results are stale — " + "; ".join(parts) +
           ". Rerun verify.py (or the full tests) before claiming anything passes.")
    if data.get("stop_hook_active"):
        print(json.dumps({"systemMessage": "⚠ " + msg}))
    else:
        print(json.dumps({"decision": "block", "reason": msg, "systemMessage": "⚠ Verify: stale test results"}))


if __name__ == "__main__":
    try:
        main()
        if _root and os.path.exists(os.path.join(_root, ERROR_FILE)):
            os.remove(os.path.join(_root, ERROR_FILE))
    except Exception as e:
        try:
            if _root:
                os.makedirs(os.path.dirname(os.path.join(_root, ERROR_FILE)), exist_ok=True)
                with open(os.path.join(_root, ERROR_FILE), "w", encoding="utf-8") as f:
                    f.write(f"{now()} {type(e).__name__}: {e}\n")
        except Exception:
            pass
    sys.exit(0)
