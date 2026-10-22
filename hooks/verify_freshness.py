#!/usr/bin/env python3
"""sdlc verify-freshness hook.

Active only while an .sdlc feature is in Stage 5 (Verify):
  - PostToolUse Edit/Write/MultiEdit/NotebookEdit on a code file -> mark test results stale
  - PostToolUse Bash running the full test command                -> mark fresh (records time, HEAD, worktree tree)
  - Stop                                                          -> in a git repo, diff the worktree against the
                                                                     tree recorded at the last full run (catches edits
                                                                     made via Bash, formatters, subagents); block if
                                                                     stale with "re-run tests"

The worktree tree is built with a throwaway copy of the git index (the real index is never touched).
State lives in .sdlc/.work/verify-freshness.json. Never fails the session: any error exits 0.
"""
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
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
SHELL_SEP = re.compile(r"\|\||&&|[|;&<>]")
GO_ALL_PACKAGES = ("./...", "...", ".")


def now():
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


def active_verify_feature(root):
    for path in glob.glob(os.path.join(root, ".sdlc", "*", "state.md")):
        try:
            text = open(path, encoding="utf-8").read()
        except OSError:
            continue
        if re.search(r"^Status:\s*active\b", text, re.M | re.I) and re.search(
            r"^Current:\s*Stage\s*5\b", text, re.M | re.I
        ):
            m = re.search(r"test:\s*`([^`]+)`", text)
            return os.path.basename(os.path.dirname(path)), (m.group(1).strip() if m else None)
    return None, None


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
    try:
        return subprocess.run(
            ["git", "-C", root, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip() or None
    except Exception:
        return None


def git(root, *args, env=None):
    p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, timeout=5, env=env)
    return p.stdout.strip() if p.returncode == 0 else None


def worktree_tree(root):
    """Tree object of the current worktree (tracked + untracked, minus ignored), via a temp index copy."""
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
        return git(root, "write-tree", env=env)
    except Exception:
        return None
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def changed_code_files(root, old_tree):
    """Code files that differ from old_tree, or None when it can't be told (no git, tree gone)."""
    new_tree = worktree_tree(root)
    if not new_tree:
        return None
    if new_tree == old_tree:
        return []
    names = git(root, "diff", "--name-only", "--no-renames", old_tree, new_tree)
    top = git(root, "rev-parse", "--show-toplevel")
    if names is None or not top:
        return None
    return [os.path.relpath(os.path.join(top, n), root) for n in names.splitlines()
            if is_code_file(root, os.path.join(top, n))]


def is_code_file(root, file_path):
    if not file_path:
        return False
    rel = os.path.relpath(os.path.abspath(file_path), root).replace(os.sep, "/")
    if rel.startswith("..") or rel.startswith(NON_CODE_DIRS):
        return False
    return not rel.lower().endswith(NON_CODE_EXT)


def names_specific_tests(args, is_go):
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


def is_full_test_run(command, test_cmd):
    if not command or PARTIAL_FLAGS.search(" " + command + " "):
        return False
    if test_cmd:
        if test_cmd not in command:
            return False
        end = command.index(test_cmd) + len(test_cmd)
    else:
        m = GENERIC_TEST.search(command)
        if not m:
            return False
        end = m.end()
    args = SHELL_SEP.split(command[end:])[0]
    return not names_specific_tests(args, is_go=re.search(r"\bgo\s+test\b", command) is not None)


def main():
    data = json.load(sys.stdin)
    event = data.get("hook_event_name", "")
    root = project_root(data.get("cwd"))
    if not root:
        return
    feature, test_cmd = active_verify_feature(root)
    if not feature:
        return
    st = load(root)
    if st.get("feature") != feature:
        st = {"feature": feature, "stale": True, "reason": "no full test run recorded in Stage 5 yet"}

    if event == "PostToolUse":
        tool = data.get("tool_name", "")
        tin = data.get("tool_input") or {}
        if tool in EDIT_TOOLS:
            fp = tin.get("file_path") or tin.get("notebook_path")
            if is_code_file(root, fp):
                st.update(stale=True, reason=f"{os.path.relpath(fp, root)} edited at {now()} after the last full test run",
                          last_edit_at=now(), last_edit_file=os.path.relpath(fp, root))
                save(root, st)
        elif tool == "Bash":
            cmd = tin.get("command", "")
            resp = data.get("tool_response") or {}
            if isinstance(resp, dict) and resp.get("interrupted"):
                return
            if is_full_test_run(cmd, test_cmd):
                st.update(stale=False, reason="", last_test_at=now(), last_test_cmd=cmd, head=git_head(root),
                          tree=worktree_tree(root))
                save(root, st)
        return

    if event == "Stop" and st.get("tree"):
        changed = changed_code_files(root, st["tree"])
        if changed:
            more = f" and {len(changed) - 5} more" if len(changed) > 5 else ""
            st.update(stale=True, reason=f"{', '.join(changed[:5])}{more} changed since the last full test run")
        elif changed == []:
            st.update(stale=False, reason="")  # edits since the run were reverted, or only touched non-code
        save(root, st)

    if event == "Stop" and st.get("stale"):
        save(root, st)
        msg = (f"Verify freshness ({feature}): test results are stale — {st.get('reason')}. "
               f"Run the full test command{f' (`{test_cmd}`)' if test_cmd else ''} again before claiming "
               f"anything passes, or dispatch a fresh sdlc:verifier agent for this round.")
        if data.get("stop_hook_active"):
            print(json.dumps({"systemMessage": "⚠ " + msg}))
        else:
            print(json.dumps({"decision": "block", "reason": msg, "systemMessage": "⚠ Verify: stale test results"}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
