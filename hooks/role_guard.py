#!/usr/bin/env python3
"""sdlc role guard: recorded acceptance tests stay read-only, and the plugin's own subagents stay in their role.

PreToolUse on file tools (roles, main()).
Recorded acceptance tests (spec 03 S3), for every caller: bundle_problem(), which hooks/pretooluse.py calls on the
edit tools, Bash and PowerShell, for every host (so a repo without a bundle runs no extra hook): in a repo with
acceptance/manifest.json, denies a file tool writing the manifest or a test it lists, and a shell command whose text
writes, moves or removes one (a redirect, tee, sed -i, cp/mv, rm, truncate, git checkout/restore/rm, PowerShell write
cmdlets; through cd, git -C and bash -c too). It reads command text only: a program that opens the file itself isn't
seen (a guard is not a sandbox).
Read-only repos of a workbench: read_only_problem(), also called from hooks/pretooluse.py, denies the same writes into
a `write: false` repo's folder (and touch, mkdir, and git commands that change that repo), naming its owner.
Roles: Claude Code names the subagent making a call in `agent_type` (`sdlc:<agent>`); calls from the main session
or other plugins' agents get no output from this part. Denies, with the reason the agent sees:
  - a reviewer editing any file but its report under .sdlc/.work/findings/: reviewers report, they don't fix
  - the qa-tester reading or searching project files other than .sdlc/, the docs folder (docs_dir) and READMEs, or
    writing anything but qa-report.md and .sdlc/.work/qa/
Paths outside the project (scratch dirs) are left alone. A session started in a folder above sdlc repos is judged
against the repo a call's path is in (sdlc_layout.target_repo). For roles, Bash stays open to all of them: they need it
for git, tests and running the software, so that part of each role is still instructions. Any error: no output.
"""
import fnmatch
import json
import os
import re
import shlex
import sys

import sdlc_layout  # sibling module: where feature state and sdlc documents live

# Define's explorers write only their report too
REVIEWERS = {"code-explorer", "code-reviewer", "comment-analyzer", "feature-reviewer",
             "pr-test-analyzer", "silent-failure-hunter", "type-design-analyzer", "ui-reviewer"}
WRITES = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
READS = {"Read", "Grep", "Glob"}


def rel_path(root, tool_input, cwd):
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path") or cwd or root
    rel = os.path.relpath(os.path.abspath(os.path.join(cwd or root, path)), root).replace(os.sep, "/")
    # None: outside the project. A segment test, so `..hidden/` and `..env` stay inside (as scaffold.rel())
    return None if rel == ".." or rel.startswith("../") else rel


def problem(agent, tool, rel, root):
    if rel is None:
        return None
    docs = sdlc_layout.docs_dir(root)
    in_sdlc = rel == ".sdlc" or rel.startswith(".sdlc/") or bool(docs) and (rel == docs or rel.startswith(docs + "/"))
    # Reports go in a feature's folder only: .sdlc/<feature>/ (old layout), .sdlc/state/<feature>/ (its work folder) or
    # a pre-2.0 <docs>/intents/<feature>/, never elsewhere in the docs and never beside the state files themselves
    folder, _, _ = rel.rpartition("/")
    # Case-folded, trailing dots and spaces dropped: Windows and macOS would open .sdlc/STATE/ as .sdlc/state/
    parts = [p.rstrip(". ").lower() for p in folder.split("/")]
    in_reports = (len(parts) == 2 and parts[0] == ".sdlc" and parts[1] not in ("state", ".work")
                  or len(parts) == 3 and parts[:2] == [".sdlc", "state"] and parts[2] not in ("", ".work")
                  or bool(docs) and folder.startswith(docs + "/intents/") and "/" not in folder[len(docs + "/intents/"):])
    # Windows short names (WORK~1 for .work) and stream syntax (a:b) reach a folder by another spelling
    plain = not any(c in rel for c in "~:")
    in_reports = in_reports and plain
    findings = rel.startswith(".sdlc/.work/findings/") and plain  # its report, by path
    if agent in REVIEWERS and tool in WRITES and not findings:
        return (f"sdlc: {agent} reports findings; it doesn't edit files. Write your report under "
                ".sdlc/.work/findings/ and put the fix in it.")
    if agent == "qa-tester":
        if tool in WRITES and not (rel.endswith("/qa-report.md") and in_reports or rel.startswith(".sdlc/.work/qa/")):
            return "sdlc: the qa-tester writes only qa-report.md and scratch files under .sdlc/.work/qa/."
        readme = os.path.basename(rel).upper().startswith("README")
        if tool in READS and not (in_sdlc or readme):
            return ("sdlc: the qa-tester tests the software without reading its code. Use the spec, quickstart, "
                    "contracts, README and the running software.")
    return None


# --- recorded acceptance tests (spec 03 S3): read-only for everyone ---------------------------------------------

MANIFEST = "acceptance/manifest.json"
# Windows and macOS file systems ignore case: ACCEPTANCE/Manifest.json is the same file there
FOLD_CASE = os.path.normcase("A") == "a" or sys.platform == "darwin"
SHELLS = {"bash", "sh", "zsh", "dash", "pwsh", "powershell", "cmd"}
PREFIXES = {"sudo", "env", "command", "xargs", "nohup", "time", "exec", "builtin"}
# Write verbs. Every operand counts for these (a move takes the source away too) ...
ANY_OPERAND = {"rm", "unlink", "shred", "truncate", "tee", "mv", "move",
               "set-content", "add-content", "out-file", "clear-content", "remove-item", "new-item", "rename-item",
               "move-item", "sc", "ac", "clc", "ri", "del", "erase", "rd", "rmdir", "ni", "rni", "mi"}
# ... a move or a removal of a folder takes what is inside it (a move's destination is checked as a copy's) ...
WHOLE_TREE = {"mv", "move", "move-item", "mi", "rename-item", "rni", "rd", "rmdir"}
MOVES = {"mv", "move", "move-item", "mi"}
# ... and only the destination counts for a copy
COPY = {"cp", "install", "ln", "rsync", "copy-item", "cpi", "copy"}
# A read-only repo (folder mode) also counts these: they create or change files in it ...
FOLDER_WRITES = {"touch", "mkdir", "md", "chmod", "chown"}
# ... and git commands that change a repo run inside it (pull and fetch stay open: they only follow upstream)
GIT_REPO_WRITES = {"commit", "push", "add", "am", "cherry-pick", "revert", "merge", "rebase", "stash", "tag",
                   "clean", "rm", "mv", "apply", "reset", "commit-tree", "update-ref", "switch", "worktree", "notes",
                   "submodule", "gc", "prune", "init"}
# `git branch` with only these lists branches; anything else (a name, -d, -m, -f) changes them
GIT_BRANCH_READS = {"-a", "--all", "-r", "--remotes", "-v", "-vv", "--verbose", "--list", "-l", "--show-current",
                    "--no-color", "--color"}
# Commands that move the folder later commands (and their redirects) run in
CHDIR = {"cd", "pushd", "chdir", "set-location", "sl", "push-location"}


def canon(rel):
    """A repo-relative path in one spelling: `.` and `..` resolved, no trailing dots or spaces and no NTFS stream
    (`file::$DATA`) on a segment, case-folded where the file system ignores case."""
    parts = []
    for seg in rel.replace("\\", "/").split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if not parts:
                return None
            parts.pop()
            continue
        seg = seg.split(":", 1)[0].rstrip(". ")
        parts.append(seg.lower() if FOLD_CASE else seg)
    return "/".join(parts)


def protected_paths(root):
    """The manifest and every test it lists, in canon() spelling; None when the repo has no bundle."""
    path = os.path.join(root, MANIFEST)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, ValueError):
        manifest = None
    tests = manifest.get("tests") if isinstance(manifest, dict) else None
    paths = {MANIFEST} | {"acceptance/" + t["path"].lstrip("/") for t in tests or []
                          if isinstance(t, dict) and isinstance(t.get("path"), str)}
    return {canon(p) for p in paths}


def hits(root, cwd, operand, protected, tree=False, folders=False):
    """The operand (a path, folder or glob, from `cwd`) names a protected file, or with `tree` a folder holding one.
    With `folders`, the protected entries are folders and any path at or under one counts (links resolved)."""
    if not operand or operand.startswith("-"):
        return False
    operand = operand.strip("\"'").replace("\\", "/")
    full = operand if os.path.isabs(operand) or re.match(r"^[A-Za-z]:/", operand) else \
        os.path.join(cwd or root, operand)
    try:
        rel = os.path.relpath(os.path.normpath(full), root)
    except ValueError:  # another drive: not in the repo
        return False
    c = canon(rel)
    if c is None:
        return False
    glob = any(ch in c for ch in "*?[")
    for p in protected:
        if c == p or tree and (c == "" or p.startswith(c + "/")) or folders and c.startswith(p + "/"):
            return True
        if glob:
            g, s = c.split("/"), p.split("/")
            if (len(g) == len(s) or tree and len(g) < len(s) or folders and len(g) > len(s)) and all(fnmatch.fnmatchcase(a, b)
                                                                      for a, b in zip(s, g)):
                return True
    if folders and not glob:  # through a link to the folder (the path itself may not exist yet)
        real = os.path.normcase(os.path.realpath(full))
        for p in protected:
            target = os.path.normcase(os.path.realpath(os.path.join(root, p)))
            if real == target or real.startswith(target.rstrip(os.sep) + os.sep):
                return True
    # Another name for the same file: a short name (ACCEPT~1), a link
    if not glob and os.path.exists(full):
        for p in protected:
            target = os.path.join(root, p)
            try:
                if os.path.exists(target) and os.path.samefile(full, target):
                    return True
                if tree and os.path.isdir(full) and os.path.realpath(target).startswith(
                        os.path.realpath(full).rstrip(os.sep) + os.sep):
                    return True
            except OSError:
                pass
    return False


def segments(command):
    """[(simple command, its redirect targets)] of a shell command line, splitting on ; & | && || and newlines and
    finding `>`/`>>` only outside quotes, so a `>` in a commit message is text. Each target stays with its own
    command, so it resolves against the folder a `cd` before it moved to."""
    parts, targets, buf, quote, i = [], [], [], None, 0
    while i < len(command):
        ch = command[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch in ";|&\n":
            parts.append(("".join(buf), targets))
            buf, targets = [], []
        elif ch == ">":
            j = i + 1
            if j < len(command) and command[j] in ">|":  # `>>` appends, `>|` overwrites despite noclobber
                j += 1
            if j < len(command) and command[j] == "&":  # 2>&1: a stream, not a file
                i = j + 1
                continue
            while j < len(command) and command[j] in " \t":
                j += 1
            k = j
            if k < len(command) and command[k] in "\"'":
                end = command.find(command[k], k + 1)
                k = len(command) if end < 0 else end + 1
            else:
                while k < len(command) and command[k] not in " \t;|&<>\n":
                    k += 1
            targets.append(command[j:k])
            i = k
            continue
        else:
            buf.append(ch)
        i += 1
    parts.append(("".join(buf), targets))
    return [(p, t) for p, t in parts if p.strip() or t]


def shell_write(command, root, cwd, protected, depth=0, folders=False):
    """The protected path a shell command line writes, moves or removes, or None (`folders`: see hits)."""
    for part, targets in segments(command):
        for t in targets:
            if hits(root, cwd, t, protected, folders=folders):
                return t.strip("\"'")
        try:
            words = shlex.split(re.sub(r"\\(?=[\w.$~-])", "/", part), posix=True)
        except ValueError:
            words = re.sub(r"\\(?=[\w.$~-])", "/", part).split()
        env_words = []
        while words and (re.match(r"^[A-Za-z_]\w*=", words[0]) or words[0].lower() in PREFIXES):
            env_words.append(words[0])
            words = words[1:]
        if not words:
            continue
        verb = os.path.basename(words[0]).lower()
        if verb.endswith(".exe"):
            verb = verb[:-4]
        args = words[1:]
        if verb in CHDIR:
            operand = next((w for w in args if not w.startswith("-")), None)
            cwd = os.path.join(cwd or root, operand.strip("\"'")) if operand else root
            continue
        if verb in SHELLS:
            for n, w in enumerate(args[:-1]):
                if w.lower() in ("-c", "-command", "/c") and depth < 3:
                    found = shell_write(args[n + 1], root, cwd, protected, depth + 1, folders)
                    if found:
                        return found
            continue
        if verb == "git":
            here = cwd
            for w in env_words:  # GIT_DIR=specs/.git git commit: the repo it names
                key, _, value = w.partition("=")
                if key in ("GIT_DIR", "GIT_WORK_TREE") and value:
                    here = os.path.join(cwd or root, value.strip("\"'"))
            while args and args[0].startswith("-"):  # git -C <dir> / -c <key=value> / --git-dir=… / --work-tree …
                flag, eq, value = args[0].partition("=")
                if flag in ("-C", "-c", "--git-dir", "--work-tree") and (eq or len(args) > 1):
                    value = value if eq else args[1]
                    if flag != "-c":
                        here = os.path.join(here or root, value)
                    args = args[1:] if eq else args[2:]
                else:
                    args = args[1:]
            writes = args and (args[0] in GIT_REPO_WRITES or args[0] == "branch" and any(
                w not in GIT_BRANCH_READS for w in args[1:]))
            if folders and writes and hits(root, here, ".", protected, folders=True):
                return here or root
            if args and args[0] in ("checkout", "restore", "rm", "mv", "apply", "reset"):
                for w in args[1:]:
                    if w.startswith("-"):
                        continue
                    try:
                        whole = canon(os.path.relpath(os.path.normpath(os.path.join(here or root, w.strip("\"'"))),
                                                      root)) == ""
                    except ValueError:  # another drive: not in the repo, and the next operand still counts
                        continue
                    if hits(root, here, w, protected, tree=not whole, folders=folders):
                        return w
            continue
        operands = [w for w in args if not w.startswith("-")]
        # -r, -R, -rf, -fR …: a short-option cluster; PowerShell's -Recurse (never -Force or -Verbose)
        recursive = any(re.fullmatch(r"-[a-zA-Z]{0,3}[rR][a-zA-Z]{0,3}", w) and len(w) <= 4
                        or w.lower() in ("--recursive", "-recurse") for w in args)
        if verb == "sed":
            if any(re.match(r"^-[a-zA-Z]*i", w) or w.startswith("--in-place") for w in args):
                for w in operands:
                    if hits(root, cwd, w, protected, folders=folders):
                        return w
        named = next((args[n + 1] for n, w in enumerate(args[:-1]) if w.lower() in ("-destination", "-t")), None)
        # Where a copy or a move goes: -Destination/-t, else the last operand when there are two or more
        dest = named or (operands[-1] if len(operands) > 1 or verb in COPY and operands else None)
        sources = [w for w in operands if w != dest] if named else operands[:-1] if dest else operands
        if verb != "sed" and (verb in ANY_OPERAND or folders and verb in FOLDER_WRITES):
            # A move takes its sources away; its destination is checked below as a copy's
            for w in sources if verb in MOVES else operands:
                if hits(root, cwd, w, protected, tree=recursive or verb in WHOLE_TREE, folders=folders):
                    return w
        if (verb in COPY or verb in MOVES) and dest:
            folder = dest.endswith("/") or dest in (".", "..") or os.path.isdir(os.path.join(cwd or root, dest))
            for src in sources or [dest]:
                into = os.path.join(dest, os.path.basename(src.rstrip("/"))) if folder else dest
                if hits(root, cwd, into, protected, tree=recursive, folders=folders):
                    return into
    return None


def written(data, root, protected, folders=False):
    """The protected path (or, with `folders`, a path inside a protected folder) this call writes, or None."""
    tool, tin, cwd = data.get("tool_name", ""), data.get("tool_input") or {}, data.get("cwd")
    if tool in WRITES:
        path = tin.get("file_path") or tin.get("notebook_path") or tin.get("path") or ""
        return path if path and hits(root, cwd, path, protected, folders=folders) else None
    if tool in ("Bash", "PowerShell"):
        return shell_write(str(tin.get("command") or ""), root, cwd, protected, folders=folders)
    return None


def read_only_problem(data, root):
    """The deny reason when this call writes into a `write: false` repo of the workbench at root, naming the repo and
    its owner; None outside a workbench. Entries are read one by one, so one malformed entry never unguards the
    others; only a file that isn't JSON with a `repos` list leaves nothing to guard (doctor reports it)."""
    import sdlc_scopes
    if not sdlc_scopes.is_workbench(root):
        return None
    for name, owner in (sdlc_scopes.read_only_names(root) or {}).items():
        found = written(data, root, {canon(name)}, folders=True)
        if found:
            owner = owner or "its owners"
            return (f"sdlc: {found} is in {name}/, a read-only repo owned by {owner} (workbench.json): "
                    f"sdlc doesn't change other teams' repos. Ask {owner} for the change.")
    return None


def unbranched_problem(data, root):
    """The deny reason when this call writes into a writable repo of the workbench at root while a feature is active
    there and no active feature has branched that repo yet (its `## Repos`): the first write would land on whatever
    branch the repo has checked out. None outside a workbench, with no active feature, or on a manifest it can't
    read (setup and doctor handle those)."""
    import sdlc_layout
    import sdlc_scopes
    if not sdlc_scopes.is_workbench(root):
        return None
    try:
        writable = [r["name"] for r in sdlc_scopes.manifest(root) if r["write"]]
    except ValueError:
        return None
    features = list(sdlc_layout.active(root))
    if not features or not writable:
        return None
    branched = set()
    for _, text in features:
        branched |= {n for n, rec in sdlc_scopes.feature_repos(text).items() if rec.get("branch")}
    for name in writable:
        if name in branched:
            continue
        found = written(data, root, {canon(name)}, folders=True)
        if found:
            feature = features[0][0] if len(features) == 1 else "<feature>"
            script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "state.py")
            return (f"sdlc: {found} is in {name}/, which the active feature hasn't branched yet. First run "
                    f"python3 \"{script}\" repo {feature} {name} (it creates the feature's branch there from the "
                    "default branch), then make the change.")
    return None


def bundle_problem(data, root):
    protected = protected_paths(root)
    if not protected:
        return None
    found = written(data, root, protected)
    if not found:
        return None
    return (f"sdlc: {found} is a recorded acceptance test or its manifest ({MANIFEST}): the spec owns it, so it is "
            "read-only here. Run it; if it is wrong, raise a spec question (/rspec:amend), never edit it.")


def main():
    try:
        data = json.load(sys.stdin)
        agent = str(data.get("agent_type") or "")
        root = os.path.abspath(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd())
        # A session started above the repo (a workbench of repos): judge the call against the repo it acts in
        root = sdlc_layout.target_repo(root, data.get("tool_name", ""), data.get("tool_input"), data.get("cwd")) or root
        reason = None
        if agent.startswith(("sdlc:", "sdlc-extras:")):  # sdlc-extras: the companion's reviewers
            rel = rel_path(root, data.get("tool_input") or {}, data.get("cwd"))
            reason = problem(agent.split(":", 1)[1], data.get("tool_name", ""), rel, root)
        if reason:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }}))
    except Exception:
        pass


if __name__ == "__main__":
    main()
    sys.exit(0)
