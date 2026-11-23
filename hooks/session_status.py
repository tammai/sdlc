#!/usr/bin/env python3
"""sdlc session status: SessionStart puts the repo's sdlc setup and paths in context, so starting a change needs no
`scaffold.py status` or `scaffold.py paths` call (Claude Code; other agents run those two, as flow.md says).

One line, only in a repo with `.sdlc/`: setup, drift, layout, the path pattern of a feature's change file, state
file and work folder, whether a git remote exists, the PRD's path (or none), team rules, and the active
features with their stage.
Outside an sdlc repo, or on the hook's own error: no output. A lock or config scaffold can't read is the repo's
state, not the hook's error: the line says it is unreadable and points at /sdlc:doctor.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, HERE)
import scaffold  # noqa: E402  (setup state and drift, exactly as `scaffold.py status` reports them)
import sdlc_layout  # noqa: E402
import verify_freshness as vf  # noqa: E402  (project root)


def status_line(root):
    st = scaffold.cmd_status(scaffold.Project(root), None)
    p = sdlc_layout.paths(root, "<feature>")
    remote = subprocess.run(["git", "-C", root, "remote"], capture_output=True, encoding="utf-8",
                            errors="replace", timeout=5).stdout.split()
    active = []
    for name, text in sdlc_layout.active(root):
        m = re.search(r"^Current:\s*(.+?)\s*$", text, re.M)
        active.append(f"{name} ({m.group(1) if m else 'no stage'})")
    parts = [f"setup {st['setup']}", f"drift {st['drift'] or 'n/a'}", f"layout {st['layout']}",
             f"change file {p['change']}", f"state file {p['state']}", f"work folder {p['work']}",
             f"remote {remote[0] if remote else 'none'}", f"active: {', '.join(active) or 'none'}"]
    import sdlc_scopes  # noqa: PLC0415  (the mode and skips the orchestrator follows; they gate nothing here)
    gate = sdlc_scopes.gate_root(root) or root
    (mode, skip), honoured = sdlc_scopes.configured(gate), sdlc_scopes.effective(gate)
    if mode == "advisory":
        parts.append("mode advisory" + ("" if honoured[0] == "advisory" else " (asked, not yet accepted: full rules apply)"))
    elif skip:
        waiting = [x for x in skip if x not in honoured[1]]
        parts.append(f"skip {', '.join(honoured[1]) or 'none'}"
                     + (f" ({', '.join(waiting)} asked, not yet accepted)" if waiting else ""))
    prd = sdlc_layout.prd(root)
    parts.append(f"PRD {prd if os.path.isfile(os.path.join(root, prd)) else 'none'}")
    if st.get("pending_migrations"):
        parts.append(f"pending migrations: {', '.join(st['pending_migrations'])}")
    if st.get("team_rules"):
        parts.append(f"team rules: {json.dumps(st['team_rules'], ensure_ascii=False)}")
    return "sdlc session status (in place of `scaffold.py status` and `paths`): " + " · ".join(parts)


def main():
    data = json.load(sys.stdin)
    root = vf.project_root(data.get("cwd"))
    if not root:
        return
    try:
        context = status_line(root)
    except ValueError as e:  # a lock or config scaffold can't read: say so, rather than start with no status at all
        context = f"sdlc session status: unreadable ({e}); run /sdlc:doctor"
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
