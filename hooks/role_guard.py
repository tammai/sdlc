#!/usr/bin/env python3
"""sdlc role guard: holds the plugin's own subagents to their role.

PreToolUse on file tools. Claude Code names the subagent making a call in `agent_type` (`sdlc:<agent>`); calls
from the main session or other plugins' agents get no output. Denies, with the reason the agent sees:
  - a reviewer editing any file but its report under .sdlc/.work/findings/: reviewers report, they don't fix
  - the verifier editing anything but test-report.md (in .sdlc/ or the docs folder), .sdlc/baseline.md (it removes
    items that pass), .sdlc/.work/redgreen/ (its worktree) and .sdlc/.work/probes/ (repro scripts): not source,
    the spec, config, state or the hooks' state
  - the qa-tester reading or searching project files other than .sdlc/, the docs folder (docs_dir) and READMEs, or
    writing anything but qa-report.md and .sdlc/.work/qa/
Paths outside the project (scratch dirs) are left alone. Bash stays open to all of them: they need it for git,
tests and running the software, so that part of each role is still instructions. Any error: no output.
"""
import json
import os
import sys

import sdlc_layout  # sibling module: where feature state and sdlc documents live

# Define's explorers write only their report too
REVIEWERS = {"code-explorer", "code-reviewer", "comment-analyzer", "feature-reviewer",
             "pr-test-analyzer", "silent-failure-hunter", "type-design-analyzer", "ui-reviewer"}
WRITES = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
READS = {"Read", "Grep", "Glob"}


def rel_path(root, tool_input, cwd):
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path") or cwd or root
    rel = os.path.relpath(os.path.abspath(os.path.join(cwd or root, path)), root).replace(os.sep, "/")
    return None if rel.startswith("..") else rel  # None: outside the project


def problem(agent, tool, rel, root):
    if rel is None:
        return None
    docs = sdlc_layout.docs_dir(root)
    in_sdlc = rel == ".sdlc" or rel.startswith(".sdlc/") or bool(docs) and (rel == docs or rel.startswith(docs + "/"))
    # Reports go in a feature's folder only: .sdlc/ (old layout) or <docs>/intents/, never elsewhere in the docs
    folder, _, _ = rel.rpartition("/")
    # Case-folded, trailing dots and spaces dropped: Windows and macOS would open .sdlc/STATE/ as .sdlc/state/
    in_reports = (folder.count("/") == 1 and folder.startswith(".sdlc/")
                  and folder.split("/")[1].rstrip(". ").lower() not in ("state", ".work")
                  or bool(docs) and folder.startswith(docs + "/intents/") and "/" not in folder[len(docs + "/intents/"):])
    # Windows short names (WORK~1 for .work) and stream syntax (a:b) reach a folder by another spelling
    plain = not any(c in rel for c in "~:")
    in_reports = in_reports and plain
    findings = rel.startswith(".sdlc/.work/findings/") and plain  # its report, by path
    if agent in REVIEWERS and tool in WRITES and not findings:
        return (f"sdlc: {agent} reports findings; it doesn't edit files. Write your report under "
                ".sdlc/.work/findings/ and put the fix in it.")
    if agent == "qa-tester":
        if tool in WRITES and not (rel.endswith("/qa-report.md") and in_reports or rel.startswith(".sdlc/.work/qa/")):
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
        if not agent.startswith(("sdlc:", "sdlc-extras:")):  # sdlc-extras: the companion plugin's reviewers
            return
        root = os.path.abspath(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd())
        rel = rel_path(root, data.get("tool_input") or {}, data.get("cwd"))
        reason = problem(agent.split(":", 1)[1], data.get("tool_name", ""), rel, root)
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
