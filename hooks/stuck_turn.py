#!/usr/bin/env python3
"""sdlc stuck turn: the same failure three times in one Build turn gets one nudge to debug instead of retrying.

The same failure is a failed Bash or PowerShell call (PostToolUseFailure) with the same command and the same `error`
text once digits and whitespace are evened out, so a timing in the output doesn't split it. A turn runs from one
UserPromptSubmit to the next: the prompt starts the count over. One nudge per turn, as context, never a block. Silent
outside an active feature in Build, while the review round cap holds the feature, and for calls a subagent makes.
The counts are kept for one session at a time in `.sdlc/.work/stuck-turn.json`: another session starts it over.
Taken from microsoft/TokenEconomizer's failure-loop guard, without its model judge. Any error: no output.
"""
import hashlib
import json
import os
import re
import sys

import sdlc_layout  # sibling module: where feature state lives
import verify_freshness as vf  # sibling hook: project root

REPEATS = 3
STATE = os.path.join(".sdlc", ".work", "stuck-turn.json")


def signature(command, error):
    text = re.sub(r"\s+", " ", re.sub(r"\d+", "0", error or "")).strip()[-1000:]
    return hashlib.sha1(f"{(command or '').strip()}\0{text}".encode("utf-8")).hexdigest()


def in_build(root):
    return any(re.search(rf"^Current:\s*Stage\s*{sdlc_layout.BUILD}\b", text, re.M | re.I)
               for _, text in sdlc_layout.active(root))


def capped(root):
    import review_rounds  # sibling hook, loaded only at a third repeat: the round cap
    return bool(review_rounds.capped(root, review_rounds.load(root)))


def main():
    data = json.load(sys.stdin)
    event = data.get("hook_event_name")
    root = vf.project_root(data.get("cwd"))
    import sdlc_scopes  # noqa: PLC0415
    if not root or sdlc_scopes.advisory_from(root):
        return
    path = os.path.join(root, STATE)
    if event == "UserPromptSubmit":
        if os.path.exists(path):
            os.remove(path)
        return
    if event != "PostToolUseFailure" or data.get("tool_name") not in ("Bash", "PowerShell") or data.get("agent_type"):
        return
    if not in_build(root):
        return
    session = str(data.get("session_id") or "")
    try:
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
    except (OSError, ValueError):
        saved = {}
    if not isinstance(saved, dict) or saved.get("session") != session or not isinstance(saved.get("counts"), dict):
        saved = {"session": session, "counts": {}, "nudged": False}
    command = (data.get("tool_input") or {}).get("command") or ""
    key = signature(command, data.get("error"))
    count = saved["counts"].get(key)
    saved["counts"][key] = (count if isinstance(count, int) else 0) + 1
    nudge = saved["counts"][key] >= REPEATS and not saved.get("nudged") and not capped(root)
    if nudge:
        saved["nudged"] = True
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(saved, f)
    if nudge:
        shown = command if len(command) <= 80 else command[:77] + "..."
        note = (f"sdlc: `{shown}` has failed the same way {REPEATS} times this turn. Stop retrying it: load "
                "`sdlc:systematic-debugging` and find the root cause before the next change. If the cause is outside "
                "this change, tell the user.")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUseFailure", "additionalContext": note}}))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        main()
    except Exception:
        pass
    sys.exit(0)
