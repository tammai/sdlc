#!/usr/bin/env python3
"""sdlc role guard: recorded acceptance tests stay read-only, and the plugin's own subagents stay in their role.

PreToolUse on file tools, Bash and PowerShell (other agents: through hosts/hook.py).
Recorded acceptance tests (spec 03 S3), for every caller: in a repo with acceptance/manifest.json, denies a file tool
writing the manifest or a test it lists, and a shell command whose text writes, moves or removes one (a redirect, tee,
sed -i, cp/mv, rm, truncate, git checkout/restore/rm, PowerShell write cmdlets; through cd, git -C and bash -c too).
It reads command text only: a program that opens the file itself isn't seen (a guard is not a sandbox).
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


def hits(root, cwd, operand, protected, tree=False):
    """The operand (a path, folder or glob, from `cwd`) names a protected file, or with `tree` a folder holding one."""
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
        if c == p or tree and (c == "" or p.startswith(c + "/")):
            return True
        if glob:
            g, s = c.split("/"), p.split("/")
            if (len(g) == len(s) or tree and len(g) < len(s)) and all(fnmatch.fnmatchcase(a, b)
                                                                      for a, b in zip(s, g)):
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
    """(simple commands, redirect targets) of a shell command line, splitting on ; & | && || and newlines and finding
    `>`/`>>` only outside quotes, so a `>` in a commit message is text."""
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
            parts.append("".join(buf))
            buf = []
        elif ch == ">":
            j = i + 1
            if j < len(command) and command[j] == ">":
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
    parts.append("".join(buf))
    return [p for p in parts if p.strip()], targets


def shell_write(command, root, cwd, protected, depth=0):
    """The protected path a shell command line writes, moves or removes, or None."""
    parts, targets = segments(command)
    for t in targets:
        if hits(root, cwd, t, protected):
            return t.strip("\"'")
    for part in parts:
        try:
            words = shlex.split(re.sub(r"\\(?=[\w.$~-])", "/", part), posix=True)
        except ValueError:
            words = re.sub(r"\\(?=[\w.$~-])", "/", part).split()
        while words and (re.match(r"^[A-Za-z_]\w*=", words[0]) or words[0].lower() in PREFIXES):
            words = words[1:]
        if not words:
            continue
        verb = os.path.basename(words[0]).lower()
        if verb.endswith(".exe"):
            verb = verb[:-4]
        args = words[1:]
        if verb == "cd":
            cwd = os.path.join(cwd or root, args[0].strip("\"'")) if args else root
            continue
        if verb in SHELLS:
            for n, w in enumerate(args[:-1]):
                if w.lower() in ("-c", "-command", "/c") and depth < 3:
                    found = shell_write(args[n + 1], root, cwd, protected, depth + 1)
                    if found:
                        return found
            continue
        if verb == "git":
            here = cwd
            while args and args[0].startswith("-"):  # git -C <dir> / -c <key=value> / --git-dir=…
                if args[0] in ("-C", "-c") and len(args) > 1:
                    if args[0] == "-C":
                        here = os.path.join(here or root, args[1])
                    args = args[2:]
                else:
                    args = args[1:]
            if args and args[0] in ("checkout", "restore", "rm", "mv", "apply", "reset"):
                for w in args[1:]:
                    if w.startswith("-"):
                        continue
                    try:
                        whole = canon(os.path.relpath(os.path.normpath(os.path.join(here or root, w.strip("\"'"))),
                                                      root)) == ""
                    except ValueError:  # another drive: not in the repo, and the next operand still counts
                        continue
                    if hits(root, here, w, protected, tree=not whole):
                        return w
            continue
        operands = [w for w in args if not w.startswith("-")]
        # -r, -R, -rf, -fR …: a short-option cluster; PowerShell's -Recurse (never -Force or -Verbose)
        recursive = any(re.fullmatch(r"-[a-zA-Z]{0,3}[rR][a-zA-Z]{0,3}", w) and len(w) <= 4
                        or w.lower() in ("--recursive", "-recurse") for w in args)
        if verb == "sed":
            if any(re.match(r"^-[a-zA-Z]*i", w) or w.startswith("--in-place") for w in args):
                for w in operands:
                    if hits(root, cwd, w, protected):
                        return w
        named = next((args[n + 1] for n, w in enumerate(args[:-1]) if w.lower() in ("-destination", "-t")), None)
        # Where a copy or a move goes: -Destination/-t, else the last operand when there are two or more
        dest = named or (operands[-1] if len(operands) > 1 or verb in COPY and operands else None)
        sources = [w for w in operands if w != dest] if named else operands[:-1] if dest else operands
        if verb != "sed" and verb in ANY_OPERAND:
            # A move takes its sources away; its destination is checked below as a copy's
            for w in sources if verb in MOVES else operands:
                if hits(root, cwd, w, protected, tree=recursive or verb in WHOLE_TREE):
                    return w
        if (verb in COPY or verb in MOVES) and dest:
            folder = dest.endswith("/") or dest in (".", "..") or os.path.isdir(os.path.join(cwd or root, dest))
            for src in sources or [dest]:
                into = os.path.join(dest, os.path.basename(src.rstrip("/"))) if folder else dest
                if hits(root, cwd, into, protected, tree=recursive):
                    return into
    return None


def bundle_problem(data, root):
    protected = protected_paths(root)
    if not protected:
        return None
    tool, tin, cwd = data.get("tool_name", ""), data.get("tool_input") or {}, data.get("cwd")
    if tool in WRITES:
        path = tin.get("file_path") or tin.get("notebook_path") or tin.get("path") or ""
        found = path if path and hits(root, cwd, path, protected) else None
    elif tool in ("Bash", "PowerShell"):
        found = shell_write(str(tin.get("command") or ""), root, cwd, protected)
    else:
        return None
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
        reason = bundle_problem(data, root)
        if not reason and agent.startswith(("sdlc:", "sdlc-extras:")):  # sdlc-extras: the companion's reviewers
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
