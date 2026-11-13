#!/usr/bin/env python3
"""The backstop under the read-only guard, in a session started in a workbench: every read-only repo
(`write: false` in workbench.json) must keep what it held when sdlc first looked at it: the same working-tree changes
(`git status`), the same local commits no remote has, the same branch refs and HEAD (a pull, forward to a commit a
remote has, is not a change), and push URLs that point nowhere (sdlc_scopes.disable_push, applied at that first look).
role_guard denies the writes it can read in a command's text; this sees a change whatever made it.

  SessionStart, PreToolUse   the first look, when the workbench was never seeded (so the first call's change is never
                             absorbed)
  PostToolUse(Failure)       after a call that can write: a new difference is said once, naming what changed
  Stop                       any difference blocks Stop once (never a loop); never seeded yet: the first look
  UserPromptSubmit           the user's prompt `accept read-only [REPO…]` takes the repos as they are now (the guard
                             denies a call that runs this script itself)

The baseline lives outside the repo, in the plugin's data folder (CLAUDE_PLUGIN_DATA, else ~/.cache/sdlc), one file
per workbench; a marker in the workbench (.sdlc/.work/read-only-seeded) remembers that it was seeded and names the
file, so every host on the machine shares it. role_guard denies calls naming this script, those files or the data
folder; an agent set on evading it can still spell around that text check, which the docs say. Either one
gone while the other remains is a difference that only the user's accept clears. A repo cloned later starts from an
empty baseline (a fresh clone has no changes). A listed repo that goes missing or can't be read, or a damaged
baseline entry, is a difference too. Files the repo ignores are not seen. Silent outside a workbench; never blocks on
its own error.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdlc_scopes  # noqa: E402

MARKER = ".sdlc/.work/read-only-seeded"
BASELINE_NAME = "read-only-baseline"  # role_guard denies commands and writes naming it or the marker
WRITERS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Bash", "PowerShell"}
GIT_TIMEOUT = 4  # each git call; the hook has 10 s
ACCEPT = re.compile(r"^\s*accept\s+read-only\b(?P<names>[\w.\- \t]*)$", re.I)
KEYS = ("status", "unpushed", "push", "refs")


def data_dir():
    return os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(os.path.expanduser("~"), ".cache", "sdlc")


def baseline_path(root):
    """The baseline file: the one the workbench's marker names (so every host on this machine shares it, whatever its
    data folder), else a new one in this host's data folder."""
    try:
        with open(os.path.join(root, MARKER), encoding="utf-8") as f:
            named = f.read().strip().splitlines()[-1].strip()
        if os.path.isabs(named) and re.fullmatch(rf"{BASELINE_NAME}-[0-9a-f]{{16}}\.json", os.path.basename(named)):
            return named
    except (OSError, IndexError):
        pass
    key = hashlib.sha256(os.path.normcase(os.path.realpath(root)).encode("utf-8")).hexdigest()[:16]
    return os.path.join(data_dir(), f"{BASELINE_NAME}-{key}.json")


def git(repo, *args):
    p = subprocess.run(["git", "--no-optional-locks", "-C", repo, *args], capture_output=True, encoding="utf-8",
                       errors="replace", timeout=GIT_TIMEOUT)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout).strip()[-200:] or f"git exit {p.returncode}")
    return p.stdout


def snapshot(repo):
    """{"status", "unpushed", "push", "refs"}: porcelain entries, commits on a local branch or HEAD no remote ref has,
    "<remote> <push url>" lines, and {ref: commit} for refs/heads and HEAD."""
    status = [e for e in git(repo, "status", "--porcelain", "-z", "--untracked-files=all").split("\0") if e]
    head = ["HEAD"] if subprocess.run(["git", "-C", repo, "rev-parse", "-q", "--verify", "HEAD"],
                                      capture_output=True, timeout=GIT_TIMEOUT).returncode == 0 else []
    unpushed = git(repo, "rev-list", *head, "--branches", "--not", "--remotes").split()
    push = sorted(" ".join(line.split()[:2]) for line in git(repo, "remote", "-v").splitlines()
                  if line.endswith("(push)"))
    refs = dict(line.split(" ", 1)[::-1] for line in
                git(repo, "for-each-ref", "--format=%(objectname) %(refname)", "refs/heads").splitlines() if " " in line)
    refs["HEAD"] = git(repo, "rev-parse", "HEAD").strip() if head else ""
    return {"status": sorted(status), "unpushed": sorted(unpushed), "push": push, "refs": refs}


def fast_forward(repo, old, new):
    """True when `new` only moves `old` forward to a commit a remote has (a pull), never a reset or a rewrite."""
    try:
        if subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", old, new], capture_output=True,
                          timeout=GIT_TIMEOUT).returncode:
            return False
        return bool(git(repo, "branch", "-r", "--contains", new).strip())
    except (RuntimeError, OSError, subprocess.SubprocessError):
        return False


def changes(base, now, repo):
    """Lines naming what differs between two snapshots of one repo."""
    lines = []
    for ref in sorted(set(base["refs"]) | set(now["refs"])):
        old, new = base["refs"].get(ref), now["refs"].get(ref)
        if old != new and not (old and new and fast_forward(repo, old, new)):
            lines.append(f"{ref.replace('refs/heads/', '')} moved: {(old or 'none')[:12]} -> {(new or 'none')[:12]}")
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
    if now["push"] != base["push"]:
        lines.append("push URL changed: " + (", ".join(now["push"]) or "none"))
    return lines


def entry_ok(entry):
    return (isinstance(entry, dict) and all(k in entry for k in KEYS) and isinstance(entry["refs"], dict)
            and all(isinstance(entry[k], list) for k in ("status", "unpushed", "push")))


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


def repo_folder(root, name):
    try:
        folder = sdlc_scopes.repo_dir(root, name)
    except ValueError:
        return None
    return folder if os.path.exists(os.path.join(folder, ".git")) else None


def first_look(folder):
    """A read-only repo seen for the first time: its push URLs pointed nowhere, then its snapshot."""
    sdlc_scopes.disable_push(folder)
    return snapshot(folder)


def seed(root, listed, names=None):
    """Take the named repos (default: every listed one) as they are now, and mark the workbench seeded."""
    path = baseline_path(root)
    data = load(path) or {"repos": {}}
    done = []
    for name in names if names is not None else list(listed):
        folder = repo_folder(root, name) if name in listed else None
        if not folder:
            continue
        try:
            data["repos"][name] = first_look(folder)
            done.append(name)
        except (RuntimeError, ValueError, OSError, subprocess.SubprocessError):
            continue  # unreadable now: reported at the next look
    data.pop("reported", None)
    save(path, data)
    marker = os.path.join(root, MARKER)
    os.makedirs(os.path.dirname(marker), exist_ok=True)
    with open(marker, "w", encoding="utf-8") as f:
        f.write(f"the read-only watch's baseline for this workbench:\n{path}\n")
    return done


def look(root, listed):
    """The differences in the workbench's read-only repos, as report lines ([] when none)."""
    path = baseline_path(root)
    data = load(path)
    seeded = os.path.exists(os.path.join(root, MARKER))
    if data is None or not seeded:
        what = "the baseline in the plugin's data folder" if seeded else f"the workbench's marker ({MARKER})"
        return [f"{what} is missing or unreadable, so changes can't be checked"]
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
                base[name] = {"status": [], "unpushed": [], "push": now["push"], "refs": now["refs"]}
                grown = True
            elif not entry_ok(base[name]):
                report.append(f"{name}/ (its baseline entry is damaged)")
                continue
            else:
                now = snapshot(folder)
        except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as e:
            report.append(f"{name}/ (can't be read: {e})")
            continue
        lines = changes(base[name], now, folder)
        if lines:
            report.append(f"{name}/ ({'; '.join(lines)})")
    if grown:
        save(path, data)
    return report


def message(report):
    return ("sdlc: a read-only repo changed: " + " | ".join(report) + ". sdlc never changes other teams' repos, and "
            "its guard won't run commands there. Stop and tell the user what changed and which call did it: they "
            "undo it (git -C <repo> restore . / clean -fd / reset) or accept it as it is by typing "
            "`accept read-only <repo>` as their message.")


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
    listed = sdlc_scopes.read_only_names(root)
    if listed is None:
        return  # an unreadable manifest: the PreToolUse guard denies writes into every folder meanwhile
    never = not os.path.exists(os.path.join(root, MARKER)) and load(baseline_path(root)) is None
    if event == "UserPromptSubmit":
        m = ACCEPT.match(str(data.get("prompt") or ""))
        if not m:
            return
        names = m.group("names").split() or None
        done = seed(root, listed, names)
        note = f"sdlc: accepted the read-only repos as they are now: {', '.join(done) or 'none found'}."
        print(json.dumps({"systemMessage": note,
                          "hookSpecificOutput": {"hookEventName": event, "additionalContext": note}}))
        return
    if event in ("SessionStart", "PreToolUse") or never:
        if never:  # the first look of all; afterwards only the user's accept takes a new one
            seed(root, listed)
        return
    if event not in ("PostToolUse", "PostToolUseFailure", "Stop"):
        return
    report = look(root, listed)
    path = baseline_path(root)
    state = load(path)
    signature = " | ".join(report)
    if state is not None:
        if state.get("reported") == (signature or None) and event != "Stop":
            return  # said already after an earlier call: once is enough until something changes
        if state.get("reported") != (signature or None):
            state["reported"] = signature or None
            save(path, state)
    if not report:
        return
    reason = message(report)
    if event == "Stop":
        out = {"systemMessage": reason} if data.get("stop_hook_active") else {"decision": "block", "reason": reason}
    else:
        out = {"decision": "block", "reason": reason,
               "hookSpecificOutput": {"hookEventName": event, "additionalContext": reason}}
    print(json.dumps(out))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # never blocks on its own error
        pass
    sys.exit(0)
