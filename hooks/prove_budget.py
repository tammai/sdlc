#!/usr/bin/env python3
"""sdlc prove budget: Prove's command budget, enforced (ADR 0012).

PreToolUse on Bash, PowerShell and Monitor, active only while an .sdlc feature is in Stage 5 (Prove), for every
caller (session, verifier, reviewers). A command that isn't one of the project's own (`commands` and
`packages[].commands` in .sdlc/config.json: install, build, lint, typecheck, test; extra arguments, builtins like
`cd <dir> &&` beside them and a pipe into a filter like `tail` allowed, nothing else chained):
  - Bash: is killed at 120 s. At its own `timeout` Claude Code moves a command to the background instead of killing
    it, which an agent can then poll, so the hook rewrites the command: `timeout -k 5 120 <command>` for one step
    (each stage of a pipe; leading `cd`, `export` and the like stay as they are), which the user's permission rules
    still match through the wrapper. The tool `timeout` becomes 130 s, past the kill. Returned as `updatedInput` with
    no permission decision. Without a `timeout` binary (macOS without coreutils) only the tool `timeout` is lowered,
    to 120 s.
  - Bash that can't take the prefix (two timed steps, loops, subshells, `$(...)`, `&`), Bash with
    `run_in_background`, PowerShell and Monitor: denied with the reason. Wrapping the first in `bash -c` would hide
    it from the user's deny rules.
The project's own commands are left alone. Any error: no output.
"""
import json
import os
import re
import shlex
import shutil
import sys

import sdlc_layout  # sibling module: where feature state and sdlc documents live
import verify_freshness as vf  # sibling hook: project root

CAP_S = 120
TOOL_TIMEOUT_MS = 130000  # past the kill (CAP_S + 5 s grace), so Claude Code never backgrounds the command
# Git Bash ships coreutils' timeout; Python on Windows would find System32's timeout.exe (a pause command) instead
TIMEOUT_BIN = "timeout" if os.name == "nt" else next((t for t in ("timeout", "gtimeout") if shutil.which(t)), None)
# Builtins (which timeout can't run) and commands that need no limit: left as they are
UNTIMED = {"cd", "pushd", "popd", "export", "unset", "set", "shopt", "alias", "source", ".", ":", "true", "false",
           "echo", "printf", "exit"}
COMPOUND = {"if", "then", "else", "elif", "fi", "for", "while", "until", "do", "done", "case", "esac", "select",
            "function", "time", "{", "}", "(", ")", "[[", "!"}
# What a project command's output may be piped into and still count as the project's run (`npm test | tail -5`)
FILTERS = {"tail", "head", "grep", "tee", "cat", "sort", "uniq", "wc", "cut"}
CHAINABLE = UNTIMED - {"source", "."}  # beside a project command: `cd app && npm test; echo done`
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
PLUGIN_VERIFY = re.compile(r"""^python3?(?:\.exe)?[ \t]+(?:"([^"]+)"|([^ \t"]+))(?:[ \t]+[\w.=-]+)*\Z""")


def in_prove(root):
    for f in sdlc_layout.features(root).values():
        try:
            text = open(os.path.join(root, f["state"]), encoding="utf-8").read()
        except OSError:
            continue
        if (re.search(r"^Status:\s*active\b", text, re.M | re.I)
                and re.search(r"^Current:\s*Stage\s*5\b", text, re.M | re.I)):
            return True
    return False


def project_commands(root):
    try:
        with open(os.path.join(root, ".sdlc", "config.json"), encoding="utf-8") as f:
            config = json.load(f)
    except (OSError, ValueError):
        return []
    sets = [config.get("commands")] + [pk.get("commands") for pk in config.get("packages") or [] if isinstance(pk, dict)]
    return [c.strip() for s in sets if isinstance(s, dict) for c in s.values() if isinstance(c, str) and c.strip()]


def is_plugin_verify(command):
    """The plugin's own scripts/verify.py, alone: it runs only the project's commands and each acceptance test's own
    Run command, so it counts as the project's (ADR 0013). A lookalike path or anything chained after it doesn't."""
    if "\n" in command or "\r" in command:
        return False
    m = PLUGIN_VERIFY.match(command.strip())
    if not m:
        return False
    return vf.is_plugin_verify(m.group(1) or m.group(2))


def is_project_command(command, commands):
    """Every step chained with &&, || or ; is a project command or a builtin like `cd`, piped only into a filter:
    anything else chained after one (`npm test && sleep 900`) would run unbounded under its name."""
    if is_plugin_verify(command):
        return True
    parts = [(step.strip(), sep) for step, sep in split_top_level(command) or []]
    if not parts or any(sep == "&" for _, sep in parts):
        return False
    # A configured command may itself be a chain (`npm run build && npm test`): matched as a run of steps
    configured = [[(st.strip(), sep) for st, sep in split_top_level(c) or [(c, "")]] for c in commands]
    i, piped = 0, False
    while i < len(parts):
        step, sep = parts[i]
        if piped:
            if step.split(" ", 1)[0] not in FILTERS:
                return False
            i += 1
        elif step.split(" ", 1)[0] in CHAINABLE:
            i += 1
        else:
            run = next((c for c in configured if matches(parts[i:i + len(c)], c)), None)
            if not run:
                return False
            i += len(run)
            sep = parts[i - 1][1]
        piped = sep == "|"
    return True


def matches(steps, configured):
    """The steps are the configured chain, its last step with extra arguments allowed."""
    if len(steps) != len(configured):
        return False
    for k, ((step, sep), (want, want_sep)) in enumerate(zip(steps, configured)):
        last = k == len(configured) - 1
        if not (step == want or last and step.startswith(want) and step[len(want)].isspace()):
            return False
        if not last and sep != want_sep:
            return False
    return True


def split_top_level(command):
    """[(step, separator)] split at unquoted |, ||, &&, ; and &; None when the syntax is more than a flat list."""
    if any(c in command for c in ("\n", "$(", "`", "<<", "<(", ">(")):
        return None
    parts, cur, quote, i = [], "", None, 0
    while i < len(command):
        ch, two = command[i], command[i:i + 2]
        if quote or ch in "'\"":
            quote = None if ch == quote else quote or ch
        elif ch == "\\":
            cur, i = cur + two, i + 2
            continue
        elif two in ("&&", "||"):
            parts.append((cur, two))
            cur, i = "", i + 2
            continue
        # & inside a redirect (2>&1, &>, >&) separates nothing
        elif ch in "|;" or ch == "&" and command[i - 1:i] not in "<>" and command[i + 1:i + 2] != ">":
            parts.append((cur, ch))
            cur, i = "", i + 1
            continue
        cur, i = cur + ch, i + 1
    return None if quote else parts + [(cur, "")]


def wrap_step(step):
    """The step with the timeout in front, the step itself when it needs none, or None when it can't take one."""
    try:
        words = shlex.split(step)
    except ValueError:
        return None
    if not words or words[0] in UNTIMED:
        return step
    if words[0] in COMPOUND or ASSIGNMENT.match(words[0]) or step.lstrip().startswith(("(", "{")):
        return None
    lead = step[:len(step) - len(step.lstrip())]
    return f"{lead}{TIMEOUT_BIN} -k 5 {CAP_S} {step.lstrip()}"


def bounded(command):
    """The command, killed at CAP_S, or None. One timed step (a pipeline counts as one): each of its commands gets the
    timeout in front, which permission rules see through. Nothing else is rewritten: hidden in `bash -c`, the command
    would slip past the user's deny rules."""
    parts = split_top_level(command)
    if parts and "&" not in (sep for _, sep in parts):
        wrapped = [(wrap_step(step), step, sep) for step, sep in parts]
        timed_steps, in_pipe = 0, False
        for w, step, sep in wrapped:
            if w is None:
                break
            timed_steps += w != step and not in_pipe
            in_pipe = sep == "|" and (in_pipe or w != step)
        else:
            if timed_steps <= 1:
                return "".join(w + sep for w, _, sep in wrapped)
    return None


def deny(reason):
    return {"permissionDecision": "deny", "permissionDecisionReason": reason}


def main():
    data = json.load(sys.stdin)
    tool = data.get("tool_name")
    if tool not in ("Bash", "PowerShell", "Monitor"):
        return
    root = vf.project_root(data.get("cwd"))
    if not root or not in_prove(root):
        return
    tin = data.get("tool_input") or {}
    command = str(tin.get("command") or "")
    if is_project_command(command, project_commands(root)):
        return
    if tool == "Monitor":
        out = deny("sdlc: in Prove there is no waiting on a run: only the project's own commands run in the "
                   "background. Run the check once, in the foreground, with Bash (killed at 120 s).")
    elif tool == "PowerShell":
        out = deny("sdlc: in Prove, run commands other than the project's own with the Bash tool, where they are "
                   "killed at 120 s.")
    elif tin.get("run_in_background"):
        out = deny("sdlc: in Prove, only the project's own commands run in the background. Run this in the "
                   "foreground (killed at 120 s) instead of starting it and polling.")
    elif TIMEOUT_BIN and bounded(command) is None:
        out = deny("sdlc: in Prove, a command other than the project's own runs one step at a time, killed at 120 s: "
                   "no loops, subshells, `$(...)`, `&` or several chained commands. Split it into separate calls.")
    elif TIMEOUT_BIN:
        out = {"updatedInput": dict(tin, command=bounded(command), timeout=TOOL_TIMEOUT_MS)}  # replaces the input
    elif not isinstance(tin.get("timeout"), (int, float)) or tin["timeout"] > CAP_S * 1000:
        out = {"updatedInput": dict(tin, timeout=CAP_S * 1000)}
    else:
        return
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", **out}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
