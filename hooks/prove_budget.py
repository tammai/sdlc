#!/usr/bin/env python3
"""sdlc prove budget: Prove's command budget, enforced (ADR 0012).

PreToolUse on Bash, active only while an .sdlc feature is in Stage 5 (Prove), for every caller (session, verifier,
reviewers). A command that isn't one of the project's own (`commands` and `packages[].commands` in .sdlc/config.json:
install, build, lint, typecheck, test; extra arguments and leading `cd <dir> &&` allowed):
  - runs with a timeout of at most 120 s: a larger or missing `timeout` comes back lowered as `updatedInput`, with no
    permission decision, so the user's permission rules still apply to it
  - can't use `run_in_background`: denied with the reason, so there is no run to poll
The project's own commands keep their timeout and may run in the background. Any error: no output.
"""
import json
import os
import re
import sys

import sdlc_layout  # sibling module: where feature state and sdlc documents live
import verify_freshness as vf  # sibling hook: project root

CAP_MS = 120000
LEADING_CD = re.compile(r"""^\s*cd\s+("[^"]+"|'[^']+'|[^\s;&|]+)\s*&&\s*""")


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


def is_project_command(command, commands):
    while LEADING_CD.match(command):
        command = LEADING_CD.sub("", command, count=1)
    command = command.strip()
    return any(command == c or command.startswith(c) and command[len(c)].isspace() for c in commands)


def main():
    data = json.load(sys.stdin)
    if data.get("tool_name") != "Bash":
        return
    root = vf.project_root(data.get("cwd"))
    if not root or not in_prove(root):
        return
    tin = data.get("tool_input") or {}
    if is_project_command(str(tin.get("command") or ""), project_commands(root)):
        return
    if tin.get("run_in_background"):
        out = {"permissionDecision": "deny", "permissionDecisionReason": (
            "sdlc: in Prove, only the project's own commands run in the background. Run this in the foreground "
            "(at most 120 s) instead of starting it and polling.")}
    elif not isinstance(tin.get("timeout"), (int, float)) or tin["timeout"] > CAP_MS:
        out = {"updatedInput": dict(tin, timeout=CAP_MS)}  # the whole input: updatedInput replaces it
    else:
        return
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", **out}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
