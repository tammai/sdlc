#!/usr/bin/env python3
"""sdlc review rounds: at most 3 review rounds fix their own findings; after that, only the user says what happens.

A round is one set of review reports, `.sdlc/.work/findings/<feature>/<reviewer>-r<N>.md`: the review, then its bugs
fixed test first, then round N+1 checks the fixes. When an active feature's round 3 (or later) still ends
`VERDICT: FAIL` and the user hasn't waived it (`waived round <N>`), PreToolUse denies every edit, shell command,
subagent and skill, so the agent can only read and ask the user: one more round, waive, or stop. Writes to
`.sdlc/.work/findings/` stay open, so a round-3 reviewer still finishing its report isn't cut off.
The user's next prompt grants one more round; nothing the agent writes can, since only the user sends a prompt. The
highest round seen is kept in `.sdlc/.work/review-rounds.json`, so deleting a report doesn't reset the count.
Silent outside an active 2.0 feature; any error: no output.
"""
import json
import os
import re
import sys

import sdlc_layout  # sibling module: where feature state and sdlc documents live
import trust_anchor  # sibling hook: the latest round's failed reports and the user's waiver
import verify_freshness as vf  # sibling hook: project root

CAP = 3
STATE = os.path.join(".sdlc", ".work", "review-rounds.json")
GUARDED = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Bash", "PowerShell", "Agent", "Task", "Skill"}


def load(root):
    try:
        with open(os.path.join(root, STATE), encoding="utf-8") as f:
            saved = json.load(f)
        return saved if isinstance(saved, dict) else {}
    except (OSError, ValueError):
        return {}


def save(root, saved):
    path = os.path.join(root, STATE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(saved, f, indent=2)


def latest_round(root, name):
    folder = os.path.join(root, ".sdlc", ".work", "findings", name)
    try:
        files = [f for f in os.listdir(folder) if re.fullmatch(trust_anchor.CHECKER_REPORT, f)]
    except OSError:
        return 0
    return max((int(re.search(r"-r(\d+)\.md$", f).group(1)) for f in files), default=0)


def capped(root, saved):
    """{feature: round} for each active feature past its rounds, with a failing verdict the user hasn't waived."""
    out = {}
    for name, text in sdlc_layout.active(root):
        rec = saved.setdefault(name, {})
        rec["seen"] = max(int(rec.get("seen") or 0), latest_round(root, name))
        failed = trust_anchor.failed_verdicts(root, name)
        if rec["seen"] >= CAP + int(rec.get("granted") or 0) and failed and not trust_anchor.waived(text, failed):
            out[name] = rec["seen"]
    return out


def main():
    data = json.load(sys.stdin)
    event = data.get("hook_event_name")
    root = vf.project_root(data.get("cwd"))
    if not root or event not in ("PreToolUse", "UserPromptSubmit"):
        return
    saved = load(root)
    over = capped(root, saved)
    if event == "UserPromptSubmit":
        for name in over:  # the user has answered: one more round
            saved[name]["granted"] = int(saved[name].get("granted") or 0) + 1
        save(root, saved)
        return
    save(root, saved)
    tool = data.get("tool_name")
    if not over or tool not in GUARDED:
        return
    path = (data.get("tool_input") or {}).get("file_path") or ""
    rel = os.path.relpath(os.path.abspath(os.path.join(data.get("cwd") or root, path)), root).replace(os.sep, "/")
    if path and rel.startswith(".sdlc/.work/findings/") and not any(c in rel for c in "~:"):
        return  # a reviewer finishing its report
    rounds = ", ".join(f"{n} (round {r})" for n, r in over.items())
    reason = (f"sdlc: {rounds}: the review still finds bugs after {CAP} rounds, so the fixing stops here. Tell the "
              "user which findings are left (the latest reports in .sdlc/.work/findings/) and ask: one more round, "
              "waive them (`waived round <N>` deviation), or stop. Their reply lifts this for one round.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        main()
    except Exception:
        pass
    sys.exit(0)
