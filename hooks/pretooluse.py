#!/usr/bin/env python3
"""PreToolUse hook executor for hookify plugin.

This script is called by Claude Code before any tool executes.
It reads .claude/hookify.*.local.md files and evaluates rules.
"""

import os
import sys
import json

# Add plugin root to Python path for imports
PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT')
if PLUGIN_ROOT and PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

try:
    from core.config_loader import attach_problems, load_rules
    from core.rule_engine import RuleEngine
except ImportError:
    sys.exit(0)  # never blocks or speaks on its own error (.claude/rules/hooks.md)


def _target_repo(input_data):
    """The sdlc repo below a session started above it that this call acts in, or None (sdlc_layout.target_repo)."""
    try:
        import sdlc_layout
        import sdlc_scopes
        return sdlc_layout.target_repo(sdlc_scopes.session_project(input_data.get('cwd')), input_data.get('tool_name', ''),
                                       input_data.get('tool_input'), input_data.get('cwd'))
    except Exception:
        return None


def _recorded_test_write(input_data):
    """sdlc patch (spec 03 S3): the deny reason when this call writes a recorded acceptance test or its manifest, in
    a repo with acceptance/manifest.json (hooks/role_guard.py bundle_problem); else None, and None on its own error.
    It runs here because this hook already runs on exactly these tools, for every host (hosts/hook.py)."""
    try:
        import role_guard
        import sdlc_scopes
        project = os.path.abspath(sdlc_scopes.session_project(input_data.get('cwd')) or input_data.get('cwd')
                                  or os.getcwd())
        target = _target_repo(input_data)
        # The repo the call is routed to, and the session's own root: at a workbench's root that covers every app
        # repo's recorded tests, whatever path or folder change the command uses to reach them
        return ((target and role_guard.bundle_problem(input_data, target))
                or role_guard.bundle_problem(input_data, project))
    except Exception:
        return None


def _unbranched_write(input_data):
    """The unbranched-repo check alone (a process gate, off in advisory); None on its own error."""
    try:
        import role_guard
        import sdlc_scopes
        cwd = input_data.get('cwd') or os.getcwd()
        root = os.path.abspath(sdlc_scopes.session_project(cwd)
                               or sdlc_scopes.workbench_root(cwd, guarded=True) or cwd)
        return role_guard.unbranched_problem(input_data, root)
    except Exception:
        return None


def role_guard_read_only(input_data):
    """The read-only guard alone, before anything reads the mode (a config that hangs can't delay it)."""
    try:
        import role_guard
        import sdlc_scopes
        cwd = input_data.get('cwd') or os.getcwd()
        root = os.path.abspath(sdlc_scopes.session_project(cwd)
                               or sdlc_scopes.workbench_root(cwd, guarded=True) or cwd)
        return role_guard.read_only_problem(input_data, root)
    except Exception:
        return None


def _monitor_commit(input_data):
    """The deny reason when a Monitor command commits or pushes: the commit and push security reviews run after a
    Bash or PowerShell call, and a Monitor call's end isn't its command's, so it would skip them. The review hook's
    own patterns decide, so Monitor is denied exactly where Bash would get a commit or push review."""
    if input_data.get("tool_name") != "Monitor":
        return None
    command = str((input_data.get("tool_input") or {}).get("command") or "")
    try:
        import git_commands  # a leaf module: the review hook's own patterns, nothing else
        reviewed = git_commands.GIT_COMMIT_RE.search(command) or git_commands.GIT_PUSH_RE.search(command)
    except Exception:  # never off on an error: anything that looks like a commit or push is denied
        import re
        reviewed = re.search(r"\bg(?:i)?t\b.*\b(?:commit|push|submit|create|modify)\b", command)
    if reviewed:
        return ("sdlc: run git commit and git push with the Bash tool, not Monitor: they get their security review "
                "there.")
    return None


def main():
    """Main entry point for PreToolUse hook."""
    try:
        # Read input from stdin
        input_data = json.load(sys.stdin)
        import sdlc_scopes  # noqa: PLC0415
        reason = role_guard_read_only(input_data)  # first: the read-only guard holds in every mode
        # advisory: only a workbench's read-only guard still decides (it protects other teams' repos)
        advisory = not reason and sdlc_scopes.advisory_from(input_data.get("cwd"))
        reason = reason or (None if advisory else _unbranched_write(input_data)) or (
            None if advisory else _recorded_test_write(input_data) or _monitor_commit(input_data))
        if reason:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                     "permissionDecisionReason": reason}}))
            return
        if advisory:  # no hookify rules either
            print(json.dumps({}))
            return

        # Determine event type for filtering
        # For PreToolUse, we use tool_name to determine "bash" vs "file" event
        tool_name = input_data.get('tool_name', '')

        # Any other tool gets only `event: all` rules: load_rules(None) would add stop and prompt rules too
        event = 'all'
        if tool_name in ('Bash', 'PowerShell'):
            event = 'bash'
        elif tool_name in ['Edit', 'Write', 'MultiEdit', 'NotebookEdit']:
            event = 'file'

        # Load rules
        problems = []
        rules = load_rules(event=event, problems=problems, extra_root=_target_repo(input_data))

        # Evaluate rules
        engine = RuleEngine()
        result = engine.evaluate_rules(rules, input_data)
        result = attach_problems(result, problems + engine.problems)

        # Always output JSON (even if empty)
        print(json.dumps(result), file=sys.stdout)

    except Exception:
        pass  # on its own error: allow, with no output

    finally:
        # ALWAYS exit 0 - never block operations due to hook errors
        sys.exit(0)


if __name__ == '__main__':
    main()
