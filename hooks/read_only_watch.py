#!/usr/bin/env python3
"""The backstop under the read-only guard: in a session started in a workbench, after each call that can write
(PostToolUse on Edit, Write, MultiEdit, NotebookEdit, Bash, PowerShell) and at Stop, every read-only repo
(`write: false` in workbench.json) must hold what it held when the session first looked: the same working-tree
changes (`git status`) and the same local commits no remote has. role_guard denies the writes it can read in a
command's text; this sees a change whatever the syntax that made it, says so after the call that made it, and blocks
Stop until it is undone (once: never a loop). Files the repo ignores are not seen.

The first look of each session is its baseline (.sdlc/.work/read-only-baseline.json), so the user's own edits from
before the session never count. Silent outside a workbench; never blocks on its own error.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdlc_scopes  # noqa: E402

BASELINE = os.path.join(".sdlc", ".work", "read-only-baseline.json")
WRITERS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Bash", "PowerShell"}
KEEP_SESSIONS = 20


def git(repo, *args):
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True, encoding="utf-8", errors="replace",
                       timeout=20)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout).strip())
    return p.stdout


def snapshot(repo):
    """{"status": [porcelain entries], "unpushed": [commits on a local branch or HEAD that no remote ref has]}."""
    status = [e for e in git(repo, "status", "--porcelain", "-z", "--untracked-files=all").split("\0") if e]
    unpushed = git(repo, "rev-list", "HEAD", "--branches", "--not", "--remotes").split()
    return {"status": sorted(status), "unpushed": sorted(unpushed)}


def read_only_repos(root):
    """{name: folder} of the read-only repos cloned in the workbench; an unreadable manifest: {} (the PreToolUse
    guard denies every write into the workbench's folders then)."""
    out = {}
    for name in sdlc_scopes.read_only_names(root) or {}:
        try:
            folder = sdlc_scopes.repo_dir(root, name)
        except ValueError:
            continue
        if os.path.exists(os.path.join(folder, ".git")):
            out[name] = folder
    return out


def changes(base, now):
    """Lines naming what differs between two snapshots of one repo."""
    lines = []
    added = sorted(set(now["status"]) - set(base["status"]))
    gone = sorted(set(base["status"]) - set(now["status"]))
    new_commits = sorted(set(now["unpushed"]) - set(base["unpushed"]))
    if added:
        lines.append("changed: " + ", ".join(e[3:] or e for e in added[:10]) + (" …" if len(added) > 10 else ""))
    if gone:
        lines.append("undone or committed: " + ", ".join(e[3:] or e for e in gone[:10]))
    if new_commits:
        lines.append(f"{len(new_commits)} new local commit(s): {', '.join(c[:12] for c in new_commits[:5])}")
    elif set(base["unpushed"]) - set(now["unpushed"]):
        lines.append("local commits removed or rewritten")
    return lines


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def check(root, session):
    """The report of what changed in read-only repos since this session's baseline, or None."""
    repos = read_only_repos(root)
    if not repos:
        return None
    path = os.path.join(root, BASELINE)
    data = load(path)
    base = data.get(session)
    now = {name: snapshot(folder) for name, folder in repos.items()}
    if not isinstance(base, dict):
        data[session] = now
        for old in list(data)[:-KEEP_SESSIONS]:
            data.pop(old, None)
        save(path, data)
        return None
    report, grown = [], False
    for name, snap in now.items():
        if name not in base:  # cloned since the baseline: its first look is its baseline
            base[name], grown = snap, True
            continue
        lines = changes(base[name], snap)
        if lines:
            report.append(f"{name}/ ({'; '.join(lines)})")
    if grown:
        save(path, data)
    if not report:
        return None
    return ("sdlc: a read-only repo changed in this session: " + " | ".join(report) + ". sdlc never changes "
            "other teams' repos: undo it now (git -C <repo> restore / clean / reset to what it held), then go on. "
            "If the user made this change themselves, tell them; they can accept it by deleting "
            f"{BASELINE.replace(os.sep, '/')}.")


def main():
    data = json.load(sys.stdin)
    event = data.get("hook_event_name", "")
    if event == "PostToolUse" and data.get("tool_name") not in WRITERS:
        return
    if event not in ("PostToolUse", "Stop"):
        return
    cwd = data.get("cwd") or os.getcwd()
    root = os.environ.get("CLAUDE_PROJECT_DIR") or sdlc_scopes.workbench_root(cwd)
    if not root or not sdlc_scopes.is_workbench(root):
        return
    reason = check(os.path.abspath(root), str(data.get("session_id") or "default"))
    if not reason:
        return
    if event == "Stop":
        out = {"systemMessage": reason} if data.get("stop_hook_active") else {"decision": "block", "reason": reason}
    else:
        out = {"decision": "block", "reason": reason,
               "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": reason}}
    print(json.dumps(out))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # never blocks on its own error
        pass
    sys.exit(0)
