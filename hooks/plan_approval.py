#!/usr/bin/env python3
"""sdlc plan approval (ADR 0031): records the user's approval of a plan waiting at Define, which `state.py advance <f> 2`
needs under config `approval` (`ml`: every M and L; `always`: S too).

Two signals count, both the user's own:
  - PostToolUse on AskUserQuestion: the answer `Approve` to a question headed `Approve plan` whose call
    user_answer.py recorded (so the agent didn't pre-fill it). It approves the one waiting feature the question names;
    any other answer takes back that feature's earlier approval.
  - UserPromptSubmit: a prompt that is exactly `approve` (the only feature waiting) or `approve <feature>`, for hosts
    without the dialog. Any other prompt approves nothing (a resumed session's first prompt or autopilot's is a prompt
    too) and takes back the waiting features' approvals: it may ask for a change to the plan.
The record is .sdlc/.work/approvals.json, agent-writable like the other .sdlc/.work records (a notice-level
protection, docs/wiki/Limitations.md). The track a plan is approved at lives in the state file (`Approval floor:`,
state.py). Prints nothing; any error leaves nothing recorded.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

import sdlc_layout  # sibling module: where feature state lives
import sdlc_scopes  # sibling module: the policy, guarded reads and writes
import user_answer  # sibling hook: a question-tool answer the agent didn't write
import verify_freshness as vf  # sibling hook: project root

HEADER = "Approve plan"  # the question tool caps a header at 12 characters
STORE = os.path.join(".sdlc", ".work", "approvals.json")
TYPED = re.compile(r"approve(?:\s+([A-Za-z0-9][\w.-]*?))?[.!]?", re.I)


def load(root):
    try:
        with sdlc_scopes.open_regular(sdlc_scopes._inside(root, STORE)) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


BY = ("dialog", "typed")


def approved(root, feature):
    """How the user approved `feature`'s plan (`dialog` or `typed`), or None. The store is read like input: any
    other value counts as no approval."""
    entry = load(root).get(feature)
    by = entry.get("by") if isinstance(entry, dict) else None
    return by if by in BY else None


def forget(root, feature):
    """Drop `feature`'s approval: the plan it covered changed, or the move to Build used it. No write when there is
    none (every prompt calls it for each waiting feature). False when there was one and it couldn't be dropped."""
    data = load(root)
    if data.pop(feature, None) is not None:
        return sdlc_scopes.write_record(root, STORE, data)
    return True


def _read(root):
    """The store's entries; None when there is no store; raises when one is there but can't be read as an object."""
    path = sdlc_scopes._inside(root, STORE)
    if not os.path.lexists(path):
        return None
    with sdlc_scopes.open_regular(path) as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{STORE} isn't a JSON object")
    return data


def started(root, feature):
    """`state.py new` created `feature`: an approval left under its name by a feature deleted by hand never carries
    over, whatever the policy (this hook records approvals under any). False when that can't be made sure: a store
    there that can't be read (left as it is: it holds other features' approvals) or written."""
    try:
        data = _read(root)
    except Exception:
        return False
    if data is None or feature not in data:
        return True
    data.pop(feature)
    return sdlc_scopes.write_record(root, STORE, data)


def waiting(root):
    """Active features still at Define (Stage 1)."""
    return [name for name, text in sdlc_layout.active(root) if re.search(r"^Current:\s*Stage 1\b", text, re.M)]


def record(root, feature, by):
    data = load(root)
    data[feature] = {"by": by, "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    sdlc_scopes.write_record(root, STORE, data)


def main():
    data = json.load(sys.stdin)
    event = data.get("hook_event_name")
    project = vf.project_root(data.get("cwd"))  # where user_answer.py records the questions asked
    root = (sdlc_scopes.gate_root(project) or project) if project else project  # the store state.py reads
    if not root or event not in ("PostToolUse", "UserPromptSubmit") or sdlc_scopes.advisory_from(root):
        return
    names = sorted(set(waiting(root)) | set(waiting(project)))
    if not names:
        return
    if event == "PostToolUse":
        answer = user_answer.answered(project, data, HEADER)
        if not answer:
            return
        asked = " ".join(str(q.get("question") or "") for q in (data.get("tool_input") or {}).get("questions") or []
                         if isinstance(q, dict) and (q.get("header") or "").strip().lower() == HEADER.lower())
        named = [n for n in names if n in re.findall(r"[A-Za-z0-9][\w.-]*[A-Za-z0-9]|[A-Za-z0-9]", asked)]
        if len(named) != 1:  # the question must name the one waiting feature it asks about
            return
        if re.sub(r"\s*\(recommended\)\s*$", "", answer, flags=re.I).strip().lower() != "approve":
            forget(root, named[0])  # `Change something` or any other answer: the plan shown isn't approved
            return
        chosen, by = named, "dialog"
    else:
        m = TYPED.fullmatch((data.get("prompt") or "").strip())
        if not m:
            for name in names:
                forget(root, name)
            return
        named = [n for n in names if n == m.group(1)] or [n for n in names if m.group(1) and n.lower() == m.group(1).lower()]
        named = named if len(named) == 1 else []  # two names differing only in case: say which exactly
        chosen = named if m.group(1) else names if len(names) == 1 else []
        by = "typed"
    for name in chosen:
        record(root, name, by)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        main()
    except Exception:
        pass
    sys.exit(0)
