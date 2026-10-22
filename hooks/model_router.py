#!/usr/bin/env python3
"""sdlc model router: checks every subagent dispatch's model while an .sdlc feature is active.

PreToolUse on Agent/Task. Denies, with the reason Claude sees:
  - no `model`                                   (an omitted model inherits the session's)
  - `model: fable` unless every active state.md says `Top model: fable`
  - a reviewer (code-reviewer, feature-reviewer, verifier) below opus when any active feature is `Risk: high`
Forks are exempt: they always run on the session model. Picking the tier for a task stays with
Model Selection in sdlc:subagent-driven-development; this only enforces its floor and ceiling.
No active feature, or any error: no output, the dispatch goes ahead.
"""
import glob
import json
import os
import re
import sys

REVIEWERS = {"code-reviewer", "feature-reviewer", "verifier"}
TIERS = "haiku (cheap), sonnet (standard), opus (top); see Model Selection in sdlc:subagent-driven-development"


def active_states(root):
    states = []
    for path in glob.glob(os.path.join(root, ".sdlc", "*", "state.md")):
        try:
            text = open(path, encoding="utf-8").read()
        except OSError:
            continue
        if re.search(r"^Status:\s*active\b", text, re.M | re.I):
            states.append(text)
    return states


def problem(tool_input, states):
    agent = str(tool_input.get("subagent_type") or "").split(":")[-1]
    if agent == "fork":
        return None
    model = str(tool_input.get("model") or "").strip().lower()
    if not model:
        return f"sdlc: name the subagent's model. Tiers: {TIERS}."
    if model == "fable" and not all(re.search(r"^Top model:\s*fable\b", s, re.M | re.I) for s in states):
        return ("sdlc: the top tier is opus; fable is used only when the user chooses it. "
                "If the user asked for fable, set `Top model: fable` in state.md first.")
    high_risk = any(re.search(r"^Risk:\s*high\b", s, re.M | re.I) for s in states)
    if high_risk and agent in REVIEWERS and model not in ("opus", "fable"):
        return f"sdlc: this feature is Risk: high, so {agent} runs on the top tier (opus)."
    return None


def main():
    try:
        data = json.load(sys.stdin)
        if data.get("tool_name") not in ("Agent", "Task"):
            return
        root = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
        states = active_states(root)
        reason = problem(data.get("tool_input") or {}, states) if states else None
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
