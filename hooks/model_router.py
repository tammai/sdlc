#!/usr/bin/env python3
"""sdlc model router: checks every subagent dispatch's model while an .sdlc feature is active.

PreToolUse on Agent/Task. Denies, with the reason Claude sees:
  - no `model`                                   (an omitted model inherits the session's)
  - `model: fable` unless every active state.md says `Top model: fable`
  - a reviewer (code-reviewer, feature-reviewer, ui-reviewer, verifier, qa-tester) below opus when any active feature is `Risk: high`
Forks are exempt: they always run on the session model. Picking the tier for a task stays with
Model Selection in sdlc:subagent-driven-development; this only enforces its floor and ceiling.
No active feature, or any error: no output, the dispatch goes ahead.
While a feature is active, every dispatch is logged to .sdlc/.work/dispatches.jsonl (time, the features' current
stage, agent, model, denied or not), so a gate can check which agent did a stage's work.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

import sdlc_layout  # sibling module: where feature state and sdlc documents live

REVIEWERS = {"code-reviewer", "feature-reviewer", "ui-reviewer", "verifier", "qa-tester"}
TIERS = "haiku (cheap), sonnet (standard), opus (top); see Model Selection in sdlc:subagent-driven-development"


def active_states(root):
    states = []
    for f in sdlc_layout.features(root).values():
        path = os.path.join(root, f["state"])
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


def log(root, tool_input, states, reason):
    stages = [m.group(1).strip() for s in states for m in [re.search(r"^Current:\s*(.+)$", s, re.M)] if m]
    entry = {"time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "stages": stages,
             "agent": tool_input.get("subagent_type") or "general-purpose", "model": tool_input.get("model"),
             "denied": bool(reason)}
    path = os.path.join(root, ".sdlc", ".work", "dispatches.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


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
        if states:
            try:  # a failed log write must never cost the deny above
                log(root, data.get("tool_input") or {}, states, reason)
            except OSError:
                pass
    except Exception:
        pass


if __name__ == "__main__":
    main()
    sys.exit(0)
