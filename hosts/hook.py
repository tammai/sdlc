#!/usr/bin/env python3
"""Run the plugin's Claude Code hooks under another agent. Claude Code never runs this file.

Usage, from the host's hooks.json:  python3 hosts/hook.py <host> <event>   host: codex, cursor or antigravity; event:
Claude Code's

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
Cursor: camelCase events with their own output fields (`permission`, `followup_message`), `Shell` for Bash, edits as
`Write` with the whole file, and an empty cwd: the workspace root stands in.
Antigravity: camelCase payloads with no event name and no exit code, `run_command`/`edit_file`/`write_file`; it denies
a tool call whose hook prints no decision, and has no prompt hook: PreInvocation stands in.

Never fails the host's turn: any error prints `{}` (Antigravity's tool calls: `ask`) and exits 0. Stdlib only,
Python 3.9+.
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
TOO_BIG = "sdlc: too many edits in one call to check them all in time. Split the change into smaller calls."
EXIT_CODE = re.compile(r"^Exit code: (-?\d+)", re.M)


def patch_edits(patch, cwd):
    """One Claude Code Write or Edit input per file an apply_patch touches; a moved file counts at both paths.
    Headers match with surrounding spaces, as Codex accepts them. An indented one may be a context line instead, so
    the lines after it count for the file before it too. A patch with no header is still checked, as one edit of no
    file, so a guardrail on its content isn't skipped."""
    edits, targets = [], []
    for line in patch.replace("\r\n", "\n").split("\n"):
        m = PATCH_FILE.match(line.strip())
        if m:
            kind, path, moved = m.groups()
            edit = {"tool_name": "Write" if kind == "Add" else "Edit",
                    "tool_input": {"file_path": os.path.join(cwd, moved or path), "old_string": "", "new_string": ""}}
            edits.append(edit)
            targets = targets + [edit] if line[:1].isspace() else [edit]
        elif line[:1] in ("+", "-"):
            for edit in targets:
                edit["tool_input"]["new_string" if line[0] == "+" else "old_string"] += line[1:] + "\n"
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
    """Each script's output for one Claude Code payload, and whether every script ran before the deadline."""
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=PLUGIN_ROOT, PYTHONIOENCODING="utf-8")
    env.pop("CLAUDE_PROJECT_DIR", None)  # an agent started from a Claude Code shell inherits that session's project
    if project_dir:
        env["CLAUDE_PROJECT_DIR"] = project_dir
    outs = []
    for name in SCRIPTS.get(payload["hook_event_name"], []):
        left = deadline - time.monotonic()
        if left <= 0:
            return outs, False
        try:
            p = subprocess.run([sys.executable, os.path.join(PLUGIN_ROOT, "hooks", name)], input=json.dumps(payload),
                               capture_output=True, encoding="utf-8", errors="replace", env=env,
                               cwd=payload.get("cwd") or None, timeout=min(CHILD_TIMEOUT, left))
            out = json.loads(p.stdout.strip() or "{}")
            if isinstance(out, dict):
                outs.append(out)
        except subprocess.TimeoutExpired:
            if left < CHILD_TIMEOUT:  # cut short by the deadline, not its own timeout: unchecked
                return outs, False
        except (OSError, ValueError):  # as a failed hook in Claude Code: no say
            continue
    return outs, True


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


def cursor_root(data):
    return (data.get("workspace_roots") or [None])[0] or os.environ.get("CURSOR_PROJECT_DIR")


def cursor_events(event, data):
    """Claude Code payload for one Cursor hook call. Hooks run in the plugin folder and tool calls carry an empty cwd,
    so the workspace stands in."""
    payload = dict(data, hook_event_name=event, cwd=data.get("cwd") or cursor_root(data) or os.getcwd())
    tool, tin = data.get("tool_name"), dict(data.get("tool_input") or {})
    if tool == "Shell":
        payload.update(tool_name="Bash", tool_input=tin)
        try:
            failed = json.loads(data.get("tool_output") or "{}").get("exitCode") not in (None, 0)
        except (ValueError, AttributeError):
            failed = False
        if event == "PostToolUse" and failed:
            payload["hook_event_name"] = "PostToolUseFailure"
    elif tool == "Delete":
        payload.update(tool_name="Edit", tool_input={"file_path": tin.get("file_path") or tin.get("path") or "",
                                                     "old_string": "", "new_string": ""})
    if event == "Stop":  # Cursor counts the follow-ups it has sent; Claude Code flags the first one
        payload["stop_hook_active"] = (data.get("loop_count") or 0) > 0
    return [payload]


def cursor_output(event, m):
    """Cursor's own fields: permission on tool calls, a follow-up message to keep the agent going."""
    out = {}
    if event == "PreToolUse" and m["denied"]:
        reason = m["deny"] or "sdlc: denied by a guardrail."
        out.update(permission="deny", agent_message=reason, user_message=m["notes"] or reason)
    elif event == "Stop" and m["blocked"]:
        out["followup_message"] = m["block"] or "sdlc: a hook asked to continue."
    elif event == "UserPromptSubmit" and m["blocked"]:
        out.update({"continue": False, "user_message": m["block"] or "sdlc: a hook stopped this prompt."})
    elif event in ("PostToolUse", "PostToolUseFailure") and (m["context"] or m["notes"]):
        out["additional_context"] = m["context"] or m["notes"]
    elif event == "PreToolUse" and (m["context"] or m["notes"]):
        out["additional_context"] = m["context"] or m["notes"]  # no `permission`: an allow would skip the approval
    return out


def agy_root(data):
    return os.path.normpath((data.get("workspacePaths") or [""])[0] or ".")


def strings(value):
    """Every string in a JSON value, however nested."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, (dict, list)):
        for v in value.values() if isinstance(value, dict) else value:
            yield from strings(v)


def agy_tool(call, cwd):
    """Claude Code payload fields for an Antigravity tool call. Patch text counts as one edit per file, and any other
    write tool as an edit of its file with every string it carries, nested or not, so a guardrail sees all of it."""
    name, args = call.get("name"), call.get("args") or {}
    if isinstance(args, str):  # arguments as JSON text: still checked, not skipped by an error
        try:
            args = json.loads(args)
        except ValueError:
            args = {"CommandLine": args} if name == "run_command" else {"Content": args}
    if not isinstance(args, dict):
        args = {}
    if name == "run_command":
        return [{"tool_name": "Bash", "tool_input": {"command": str(args.get("CommandLine") or "")}}]
    path = str(args.get("Path") or args.get("TargetFile") or "")
    rest = {k: v for k, v in args.items() if k not in ("Path", "TargetFile")}
    if name == "write_file" and set(rest) <= {"Content"}:
        return [{"tool_name": "Write", "tool_input": {"file_path": path, "content": str(args.get("Content") or "")}}]
    if name == "edit_file" and set(rest) <= {"Target", "Replacement"}:
        return [{"tool_name": "Edit", "tool_input": {"file_path": path, "old_string": str(args.get("Target") or ""),
                                                     "new_string": str(args.get("Replacement") or "")}}]
    patch = next((s for s in strings(rest) if "*** Begin Patch" in s), None)
    # the whole call is checked as well: patch text inside other content must not hide the file really written
    return (patch_edits(patch, cwd) if patch else []) + [
        {"tool_name": "Edit", "tool_input": {"file_path": path, "old_string": "", "new_string": "\n".join(strings(rest))}}]


def agy_events(event, data):
    """Claude Code payloads for one Antigravity hook call. Hooks run in the plugin folder: the workspace stands in.
    PreInvocation stands in for UserPromptSubmit on a prompt's first model call only, and Stop only for a finished turn,
    as in Claude Code."""
    payload = {"hook_event_name": event, "cwd": agy_root(data), "session_id": data.get("conversationId", ""),
               "transcript_path": data.get("transcriptPath", "")}
    if event == "UserPromptSubmit":
        return [dict(payload, prompt=data.get("lastUserInput", ""))] if data.get("invocationNum", 0) == 0 else []
    if event == "Stop":  # Antigravity counts the continues it has granted; Claude Code flags the first one
        return [dict(payload, stop_hook_active=(data.get("executionNum") or 0) > 0)] \
            if data.get("terminationReason") == "NO_TOOL_CALL" else []
    payloads = [dict(payload, **e) for e in agy_tool(data.get("toolCall") or {}, payload["cwd"])]
    for p in payloads:
        if event == "PostToolUse" and p["tool_name"] == "Bash":
            if data.get("error"):
                p["hook_event_name"] = "PostToolUseFailure"
            else:  # a failed command also arrives with no error: a trailing pipe makes its result `unknown`, not `pass`
                p["tool_input"]["command"] += " | cat"
    return payloads


def agy_output(event, m):
    """Antigravity's own fields, and no others: it rejects unknown ones. A tool call always gets a decision, because
    none denies it; `ask` is its usual permission check, so an allow-listed or workspace call still runs unasked."""
    if event == "PreToolUse":
        if m["denied"]:
            return {"decision": "deny", "reason": m["deny"] or "sdlc: denied by a guardrail."}
        note = m["context"] or m["notes"]
        return dict({"decision": "ask"}, **({"reason": note} if note else {}))
    if event == "Stop" and m["blocked"]:
        return {"decision": "continue", "reason": m["block"] or "sdlc: a hook asked to continue."}
    if event == "UserPromptSubmit":  # nothing can stop a prompt here: a block is told to the agent instead
        text = "\n\n".join(p for p in (m["block"], m["context"]) if p)
        return {"injectSteps": [{"ephemeralMessage": text}]} if text else {}
    return {}


HOSTS = {"codex": (codex_events, codex_output, lambda data: None),
         "cursor": (cursor_events, cursor_output, cursor_root),
         "antigravity": (agy_events, agy_output, agy_root)}


def fallback(argv):
    """What a failed run prints: nothing that blocks, and for Antigravity's tool calls its usual check, not a deny."""
    return {"decision": "ask"} if argv[1:3] == ["antigravity", "PreToolUse"] else {}


def main(argv):
    host, event = argv[1], argv[2]
    to_claude, to_host, project_dir = HOSTS[host]
    data = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    outs, checked, deadline = [], True, time.monotonic() + DEADLINE
    for payload in to_claude(event, data):
        ran, done = run_scripts(payload, project_dir(data), deadline)
        outs, checked = outs + ran, checked and done
    m = merge(outs)
    if event == "PreToolUse" and not checked:  # too many edits to check in time: the unchecked ones never run
        m.update(denied=True, deny="\n\n".join(p for p in (m["deny"], TOO_BIG) if p))
    return to_host(event, m)


if __name__ == "__main__":
    try:
        result = main(sys.argv)
    except Exception:
        result = fallback(sys.argv)
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8"))
    sys.exit(0)
