#!/usr/bin/env python3
"""sdlc session status: SessionStart puts the repo's sdlc setup and paths in context, so starting a change needs no
`scaffold.py status` or `scaffold.py paths` call (Claude Code; other agents run those two, as flow.md says).

One line, only in a repo with `.sdlc/`: setup, drift, layout, the path pattern of a feature's change file, state
file and work folder, whether a git remote exists, the PRD's path (or none), team rules, and the active
features with their stage.
Outside an sdlc repo, or on any error: no output.
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
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": status_line(root)}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
