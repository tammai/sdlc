#!/usr/bin/env python3
"""sdlc user answer: lets an AskUserQuestion answer stand in for a typed prompt at the gates that need a person.

The trust anchor and the review round cap open only when the user replies. A prompt is one signal the agent can't fake;
an AskUserQuestion answer can be the other, but only if the agent didn't write it: the tool's input has an `answers`
field the caller may fill. So:
  - PreToolUse (this script, on AskUserQuestion): a call that arrives with `answers` already filled is denied; any
    other call's tool_use_id is recorded in .sdlc/.work/asked.json.
  - PostToolUse (trust_anchor.py, review_rounds.py, on AskUserQuestion): `answered()` counts the call as the user's
    reply only when its id was recorded here, and only for the question whose header names that gate. Its answers
    then come from the dialog, since only the harness runs a tool and reports PostToolUse.
Silent outside an active feature; any error: no output, which leaves the call allowed but unrecorded, so its answer
lifts nothing.
"""
import json
import os
import sys

import sdlc_layout  # sibling module: where feature state lives
import verify_freshness as vf  # sibling hook: project root

STATE = os.path.join(".sdlc", ".work", "asked.json")
KEEP = 50  # recorded ids; a PostToolUse follows its PreToolUse within the same turn
TOOL = "AskUserQuestion"


def load(root):
    try:
        with open(os.path.join(root, STATE), encoding="utf-8") as f:
            ids = json.load(f)
        return [i for i in ids if isinstance(i, str)] if isinstance(ids, list) else []
    except (OSError, ValueError):
        return []


def answered(root, data, header):
    """The answer the user gave in the dialog to the question headed `header`, or None."""
    if data.get("hook_event_name") != "PostToolUse" or data.get("tool_name") != TOOL:
        return None
    if not data.get("tool_use_id") or data["tool_use_id"] not in load(root):
        return None
    tool_input = data.get("tool_input") or {}
    response = data.get("tool_response") if isinstance(data.get("tool_response"), dict) else {}
    answers = response.get("answers") or tool_input.get("answers") or {}
    for q in tool_input.get("questions") or []:
        if isinstance(q, dict) and (q.get("header") or "").strip().lower() == header.lower():
            answer = answers.get(q.get("question")) if isinstance(answers, dict) else None
            if isinstance(answer, str) and answer.strip():
                return answer.strip()
    return None


def main():
    data = json.load(sys.stdin)
    if data.get("hook_event_name") != "PreToolUse" or data.get("tool_name") != TOOL:
        return
    root = vf.project_root(data.get("cwd"))
    if not root or not list(sdlc_layout.active(root)):  # setup asks too, before it ignores .sdlc/.work/
        return
    if (data.get("tool_input") or {}).get("answers"):
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny",
            "permissionDecisionReason": "sdlc: ask without `answers`; the user picks the answer in the dialog."}}))
        return
    if not data.get("tool_use_id"):
        return
    ids = (load(root) + [data["tool_use_id"]])[-KEEP:]
    path = os.path.join(root, STATE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ids, f)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        main()
    except Exception:
        pass
    sys.exit(0)
