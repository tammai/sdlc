#!/usr/bin/env python3
"""The backstop under the read-only guard, in a session started in a workbench: every read-only repo
(`write: false` in workbench.json) must keep what it held when sdlc first looked at it: the same working-tree changes
(`git status`), the same local commits no remote has, and push URLs that point nowhere (sdlc_scopes.disable_push,
applied at that first look). role_guard denies the writes it can read in a command's text; this sees a change
whatever made it.

  SessionStart, PreToolUse   the first look, if there is none yet (so the first call's change is never absorbed)
  PostToolUse(Failure)       after a call that can write: a new difference is said once, naming what changed
  Stop                       any difference blocks Stop once (never a loop)
  --accept [NAME…]           the user's step: take the repos as they are now (the guard denies it to the agent)

The baseline is one per workbench (.sdlc/.work/read-only-baseline.json), not per session, so a difference no one
resolved is still there in the next session. A repo cloned later starts from an empty baseline (a fresh clone has no
changes). A listed repo that goes missing, or can't be read, is a difference too. Files the repo ignores are not
seen. Silent outside a workbench; never blocks on its own error.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdlc_scopes  # noqa: E402

BASELINE = ".sdlc/.work/read-only-baseline.json"
WRITERS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Bash", "PowerShell"}
GIT_TIMEOUT = 4  # each git call; the hook has 10 s


def git(repo, *args):
    p = subprocess.run(["git", "--no-optional-locks", "-C", repo, *args], capture_output=True, encoding="utf-8",
                       errors="replace", timeout=GIT_TIMEOUT)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout).strip()[-200:] or f"git exit {p.returncode}")
    return p.stdout


def snapshot(repo):
    """{"status": [porcelain entries], "unpushed": [commits on a local branch or HEAD no remote ref has],
    "push": ["<remote> <push url>"]}."""
    status = [e for e in git(repo, "status", "--porcelain", "-z", "--untracked-files=all").split("\0") if e]
    head = ["HEAD"] if subprocess.run(["git", "-C", repo, "rev-parse", "-q", "--verify", "HEAD"],
                                      capture_output=True, timeout=GIT_TIMEOUT).returncode == 0 else []
    unpushed = git(repo, "rev-list", *head, "--branches", "--not", "--remotes").split()
    push = sorted(" ".join(line.split()[:2]) for line in git(repo, "remote", "-v").splitlines()
                  if line.endswith("(push)"))
    return {"status": sorted(status), "unpushed": sorted(unpushed), "push": push}


def changes(base, now):
    """Lines naming what differs between two snapshots of one repo."""
    lines = []
    added = sorted(set(now["status"]) - set(base["status"]))
    gone = sorted(set(base["status"]) - set(now["status"]))
    if added:
        lines.append("changed: " + ", ".join(e[3:] or e for e in added[:10]) + (" ..." if len(added) > 10 else ""))
    if gone:
        lines.append("undone or committed: " + ", ".join(e[3:] or e for e in gone[:10]))
    new_commits = sorted(set(now["unpushed"]) - set(base["unpushed"]))
    if new_commits:
        lines.append(f"{len(new_commits)} new local commit(s): {', '.join(c[:12] for c in new_commits[:5])}")
    elif set(base["unpushed"]) - set(now["unpushed"]):
        lines.append("local commits removed, rewritten or pushed")
    if base.get("push") is not None and now["push"] != base["push"]:
        lines.append("push URL changed: " + (", ".join(now["push"]) or "none"))
    return lines


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) and isinstance(data.get("repos"), dict) else None
    except (OSError, ValueError):
        return None


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, path)


def first_look(folder):
    """A read-only repo seen for the first time: its push URLs pointed nowhere, then its snapshot."""
    sdlc_scopes.disable_push(folder)
    return snapshot(folder)


def look(root, seed_only=False):
    """The differences in the workbench's read-only repos, as report lines ([] when none). The first look of all
    takes the baseline instead; with seed_only, nothing more."""
    path = os.path.join(root, BASELINE)
    listed = sdlc_scopes.read_only_names(root)
    if listed is None:
        return []  # an unreadable manifest: the PreToolUse guard denies writes into every folder meanwhile
    data = load(path)
    if data is None:
        repos = {}
        for name in listed:
            folder = repo_folder(root, name)
            if folder:
                try:
                    repos[name] = first_look(folder)
                except (RuntimeError, ValueError, OSError, subprocess.SubprocessError):
                    continue  # unreadable now: reported at the next look, once it has a baseline
        save(path, {"repos": repos})
        return []
    if seed_only:
        return []
    report, grown = [], False
    base = data["repos"]
    for name in list(base):
        if name not in listed:  # dropped from the manifest (scaffold.py workbench remove): no longer watched
            del base[name]
            grown = True
    for name in listed:
        folder = repo_folder(root, name)
        if not folder:
            if name in base:
                report.append(f"{name}/ (missing, moved or no longer a git repo)")
            continue
        try:
            if name not in base:  # cloned since the first look: a fresh clone holds no change of its own
                now = first_look(folder)
                base[name] = {"status": [], "unpushed": [], "push": now["push"]}
                grown = True
            else:
                now = snapshot(folder)
        except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as e:
            report.append(f"{name}/ (can't be read: {e})")
            continue
        lines = changes(base[name], now)
        if lines:
            report.append(f"{name}/ ({'; '.join(lines)})")
    if grown:
        save(path, data)
    return report


def repo_folder(root, name):
    try:
        folder = sdlc_scopes.repo_dir(root, name)
    except ValueError:
        return None
    return folder if os.path.exists(os.path.join(folder, ".git")) else None


def message(report):
    script = os.path.abspath(__file__)
    return ("sdlc: a read-only repo changed: " + " | ".join(report) + ". sdlc never changes other teams' repos, and "
            "its guard won't run commands there. Stop and tell the user what changed and which call did it: they "
            "undo it (git -C <repo> restore . / clean -fd / reset) or accept it as it is with: "
            f"! python3 \"{script}\" --accept <repo>")


def accept(root, names):
    """The user's step: take the named read-only repos (default: every one) as they are now."""
    path = os.path.join(root, BASELINE)
    data = load(path) or {"repos": {}}
    listed = sdlc_scopes.read_only_names(root) or {}
    done = []
    for name in names or list(listed):
        folder = repo_folder(root, name) if name in listed else None
        if folder:
            data["repos"][name] = first_look(folder)
            done.append(name)
    data.pop("reported", None)
    save(path, data)
    return {"accepted": done}


def project_root(cwd):
    root = os.environ.get("CLAUDE_PROJECT_DIR") or sdlc_scopes.workbench_root(cwd)
    return os.path.abspath(root) if root and sdlc_scopes.is_workbench(root) else None


def main():
    data = json.load(sys.stdin)
    event = data.get("hook_event_name", "")
    if event in ("PreToolUse", "PostToolUse", "PostToolUseFailure") and data.get("tool_name") not in WRITERS:
        return
    root = project_root(data.get("cwd") or os.getcwd())
    if not root:
        return
    if event in ("SessionStart", "PreToolUse"):
        if not os.path.exists(os.path.join(root, BASELINE)):
            look(root, seed_only=True)
        return
    if event not in ("PostToolUse", "PostToolUseFailure", "Stop"):
        return
    report = look(root)
    path = os.path.join(root, BASELINE)
    state = load(path)
    signature = " | ".join(report)
    if state is not None and state.get("reported") != (signature or None):
        state["reported"] = signature or None
        save(path, state)
    elif event != "Stop":
        return  # said already after an earlier call: once is enough until something changes
    if not report:
        return
    reason = message(report)
    if event == "Stop":
        out = {"systemMessage": reason} if data.get("stop_hook_active") else {"decision": "block", "reason": reason}
    else:
        out = {"decision": "block", "reason": reason,
               "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": reason}}
    print(json.dumps(out))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--accept"]:
        here = project_root(os.getcwd())
        if not here:
            print(json.dumps({"error": "not in a workbench"}))
            sys.exit(1)
        print(json.dumps(accept(here, sys.argv[2:])))
        sys.exit(0)
    try:
        main()
    except Exception:  # never blocks on its own error
        pass
    sys.exit(0)
