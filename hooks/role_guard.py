#!/usr/bin/env python3
"""sdlc role guard: holds the plugin's own subagents to their role.

PreToolUse on file tools. Claude Code names the subagent making a call in `agent_type` (`sdlc:<agent>`); calls
from the main session or other plugins' agents get no output. Denies, with the reason the agent sees:
  - a reviewer editing any file: reviewers report, they don't fix
  - the verifier editing anything but test-report.md, .sdlc/baseline.md (it removes items that pass) and
    .sdlc/.work/redgreen/ (its worktree): not source, the spec, config, state.md or the hooks' own state
  - the qa-tester reading or searching project files other than .sdlc/ and READMEs, or writing anything but
    qa-report.md and .sdlc/.work/qa/
Paths outside the project (scratch dirs) are left alone. Bash stays open to all of them: they need it for git,
tests and running the software, so that part of each role is still instructions. Any error: no output.
"""
import json
import os
import sys

REVIEWERS = {"code-reviewer", "comment-analyzer", "feature-reviewer", "pr-test-analyzer", "silent-failure-hunter",
             "type-design-analyzer", "ui-reviewer"}
WRITES = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
READS = {"Read", "Grep", "Glob"}


def rel_path(root, tool_input, cwd):
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path") or cwd or root
    rel = os.path.relpath(os.path.abspath(os.path.join(cwd or root, path)), root).replace(os.sep, "/")
    return None if rel.startswith("..") else rel  # None: outside the project


def problem(agent, tool, rel):
    if rel is None:
        return None
    in_sdlc = rel == ".sdlc" or rel.startswith(".sdlc/")
    if agent in REVIEWERS and tool in WRITES:
        return f"sdlc: {agent} reports findings; it doesn't edit files. Put the fix in your report instead."
    if agent == "verifier" and tool in WRITES and not (
            rel.endswith("/test-report.md") and in_sdlc or rel == ".sdlc/baseline.md" or rel.startswith(".sdlc/.work/redgreen/")):
        return ("sdlc: the verifier writes only test-report.md, the baseline and its .sdlc/.work/redgreen/ worktree: it never edits "
                "source, the spec, config or state.md. Report the problem; the fix goes back to Stage 4.")
    if agent == "qa-tester":
        if tool in WRITES and not (rel.endswith("/qa-report.md") and in_sdlc or rel.startswith(".sdlc/.work/qa/")):
            return "sdlc: the qa-tester writes only qa-report.md and scratch files under .sdlc/.work/qa/."
        readme = os.path.basename(rel).upper().startswith("README")
        if tool in READS and not (in_sdlc or readme):
            return ("sdlc: the qa-tester tests the software without reading its code. Use the spec, quickstart, "
                    "contracts, README and the running software.")
    return None


def main():
    try:
        data = json.load(sys.stdin)
        agent = str(data.get("agent_type") or "")
        if not agent.startswith("sdlc:"):
            return
        root = os.path.abspath(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd())
        rel = rel_path(root, data.get("tool_input") or {}, data.get("cwd"))
        reason = problem(agent.split(":", 1)[1], data.get("tool_name", ""), rel)
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
