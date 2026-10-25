#!/usr/bin/env python3
"""Run the plugin's Claude Code hooks under another agent. Claude Code never runs this file.

Usage, from hosts/<host>/hooks.json:  python3 hosts/hook.py <host> <event>     host: codex

Turns the host's payload into Claude Code's, runs the hook scripts Claude Code runs for that event, unchanged, as child
processes, and turns their output back into the host's:
  - PreToolUse         hooks/pretooluse.py (hookify)                    a deny from any of them denies the call
  - PostToolUse(Failure) hooks/verify_freshness.py                      edits make Stage 5 results stale, full runs fresh
  - UserPromptSubmit   hooks/userpromptsubmit.py, hooks/trust_anchor.py
  - Stop               hooks/stop.py, hooks/verify_freshness.py, hooks/trust_anchor.py   a block from any keeps the agent going
Left out: the security review and the Ralph loop (bash launchers and model calls), the role guard (no host names the
plugin's agents on tool calls) and the model router (subagent dispatches carry no model).

Codex: payloads are Claude Code's, except that edits arrive as `apply_patch` with the patch text, which becomes one
Write or Edit per file, and a failed command arrives as PostToolUse with no exit code, so a full test run records
`unknown`, not `pass`.

Never fails the host's turn: any error prints `{}` and exits 0. Stdlib only, Python 3.9+.
"""
import json
import os
import re
import subprocess
import sys
import time

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = {
    "PreToolUse": ["pretooluse.py"],
    "PostToolUse": ["verify_freshness.py"],
    "PostToolUseFailure": ["verify_freshness.py"],
    "UserPromptSubmit": ["userpromptsubmit.py", "trust_anchor.py"],
    "Stop": ["stop.py", "verify_freshness.py", "trust_anchor.py"],
}
CHILD_TIMEOUT = 10  # each script's own timeout in hooks/hooks.json
DEADLINE = 45  # all of them, under the 60 s hosts.py gives the host
PATCH_FILE = re.compile(r"^\*\*\*\s*(Add|Update|Delete) File:\s*(.+?)$|^\*\*\*\s*Move to:\s*(.+?)$")
EXIT_CODE = re.compile(r"^Exit code: (-?\d+)", re.M)


def patch_edits(patch, cwd):
    """One Claude Code Write or Edit input per file an apply_patch touches; a moved file counts at both paths.
    Headers match with surrounding spaces, as Codex accepts them. A patch with none is still checked, as one edit of
    no file, so a guardrail on its content isn't skipped."""
    edits, current = [], None
    for line in patch.replace("\r\n", "\n").split("\n"):
        m = PATCH_FILE.match(line.strip())
        if m:
            kind, path, moved = m.groups()
            current = {"tool_name": "Write" if kind == "Add" else "Edit",
                       "tool_input": {"file_path": os.path.join(cwd, moved or path), "old_string": "", "new_string": ""}}
            edits.append(current)
        elif current and line[:1] in ("+", "-"):
            current["tool_input"]["new_string" if line[0] == "+" else "old_string"] += line[1:] + "\n"
    if not edits and patch.strip():
        edits.append({"tool_name": "Edit", "tool_input": {"file_path": "", "old_string": "", "new_string": patch}})
    for e in edits:
        if e["tool_name"] == "Write":
            e["tool_input"] = {"file_path": e["tool_input"]["file_path"], "content": e["tool_input"]["new_string"]}
    return edits


def codex_events(event, data):
    """Claude Code payloads for one Codex hook call."""
    cwd = data.get("cwd") or os.getcwd()
    if data.get("tool_name") == "apply_patch":
        patch = str((data.get("tool_input") or {}).get("command") or "")
        return [dict(data, hook_event_name=event, **e) for e in patch_edits(patch, cwd)]
    if event == "PostToolUse" and data.get("tool_name") == "Bash":
        resp = data.get("tool_response")
        m = EXIT_CODE.match(resp) if isinstance(resp, str) else None
        if m and m.group(1) != "0":
            return [dict(data, hook_event_name="PostToolUseFailure")]
        if not m:  # no exit code: a trailing pipe makes the freshness hook record `unknown` instead of `pass`
            tin = dict(data.get("tool_input") or {})
            tin["command"] = str(tin.get("command") or "") + " | cat"
            return [dict(data, hook_event_name=event, tool_input=tin)]
    return [dict(data, hook_event_name=event)]


def run_scripts(payload, project_dir, deadline):
    """Each script's output for one Claude Code payload."""
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=PLUGIN_ROOT, PYTHONIOENCODING="utf-8")
    env.pop("CLAUDE_PROJECT_DIR", None)  # an agent started from a Claude Code shell inherits that session's project
    if project_dir:
        env["CLAUDE_PROJECT_DIR"] = project_dir
    outs = []
    for name in SCRIPTS.get(payload["hook_event_name"], []):
        left = deadline - time.monotonic()
        if left <= 0:  # as a timed-out hook in Claude Code: the call goes ahead
            break
        try:
            p = subprocess.run([sys.executable, os.path.join(PLUGIN_ROOT, "hooks", name)], input=json.dumps(payload),
                               capture_output=True, encoding="utf-8", errors="replace", env=env,
                               cwd=payload.get("cwd") or None, timeout=min(CHILD_TIMEOUT, left))
            out = json.loads(p.stdout.strip() or "{}")
            if isinstance(out, dict):
                outs.append(out)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            continue
    return outs


def merge(outs):
    """Claude Code outputs, combined: denied, blocked, what the agent is told and what the user is shown."""
    deny, block, context, notes = [], [], [], []
    for out in outs:
        spec = out.get("hookSpecificOutput") or {}
        if spec.get("permissionDecision") == "deny":
            deny.append(spec.get("permissionDecisionReason") or "")
        elif out.get("decision") == "block":
            block.append(out.get("reason") or "")
        if spec.get("additionalContext"):
            context.append(spec["additionalContext"])
        if out.get("systemMessage"):
            notes.append(out["systemMessage"])
    join = lambda parts: "\n\n".join(p for p in dict.fromkeys(parts) if p)
    return {"deny": join(deny), "block": join(block), "context": join(context), "notes": join(notes),
            "denied": bool(deny), "blocked": bool(block)}


def codex_output(event, m):
    """Codex reads Claude Code's fields, but only on the events that take them; a block must carry a reason."""
    out = {}
    if event == "PreToolUse" and m["denied"]:
        out["hookSpecificOutput"] = {"hookEventName": event, "permissionDecision": "deny",
                                     "permissionDecisionReason": m["deny"] or "sdlc: denied by a guardrail."}
    elif event in ("Stop", "UserPromptSubmit") and m["blocked"]:
        out.update(decision="block", reason=m["block"] or "sdlc: a hook asked to continue.")
    if m["context"] and event in ("PreToolUse", "PostToolUse", "UserPromptSubmit") and "hookSpecificOutput" not in out:
        out["hookSpecificOutput"] = {"hookEventName": event, "additionalContext": m["context"]}
    if m["notes"]:
        out["systemMessage"] = m["notes"]
    return out


HOSTS = {"codex": (codex_events, codex_output, lambda data: None)}


def main(argv):
    host, event = argv[1], argv[2]
    to_claude, to_host, project_dir = HOSTS[host]
    data = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    outs, deadline = [], time.monotonic() + DEADLINE
    for payload in to_claude(event, data):
        outs += run_scripts(payload, project_dir(data), deadline)
    return to_host(event, merge(outs))


if __name__ == "__main__":
    try:
        result = main(sys.argv)
    except Exception:
        result = {}
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8"))
    sys.exit(0)
