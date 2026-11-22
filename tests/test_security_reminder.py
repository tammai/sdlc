"""hooks/security_reminder_hook.py: a risky edit gets its security warning; a plain one gets none."""
import json
import os
import subprocess
import unittest

from helpers import HOOKS, ProjectTestCase, run_hook

HOOK = ["python3", os.path.join(HOOKS, "security_reminder_hook.py")]


class SecurityReminderTest(ProjectTestCase):
    def write_tool(self, content, session):
        payload = {"hook_event_name": "PostToolUse", "session_id": session, "cwd": self.root, "tool_name": "Write",
                   "tool_input": {"file_path": self.path("a.js"), "content": content}}
        code, out, raw, err = run_hook(HOOK, payload, self.root, {"SECURITY_WARNINGS_STATE_DIR": self.path("state")})
        self.assertEqual(code, 0, err)
        return (out or {}).get("hookSpecificOutput", {}).get("additionalContext", "")

    def test_a_risky_edit_is_warned_and_a_plain_one_is_not(self):
        self.assertIn("innerHTML", self.write_tool("el.innerHTML = userInput\n", "s1"))
        self.assertEqual(self.write_tool("el.textContent = userInput\n", "s2"), "")

    def commit_call(self, tool):
        payload = {"hook_event_name": "PostToolUse", "session_id": "s3", "cwd": self.root, "tool_name": tool,
                   "tool_use_id": "toolu_ps1", "tool_input": {"command": "git commit -m x && git push"},
                   "tool_response": {"stdout": ""}}
        code, out, raw, err = run_hook(HOOK, payload, self.root, {"SECURITY_WARNINGS_STATE_DIR": self.path("state")})
        self.assertEqual(code, 0, err)
        return out or {}

    def test_a_commit_through_powershell_reaches_the_commit_review(self):
        subprocess.run(["git", "init", "-q", self.root], check=True)
        self.commit_call("PowerShell")
        # a second spawn for the same call (the push `if` entry) is de-duped: the first one claimed the review
        self.assertEqual(self.commit_call("PowerShell").get("metrics"), {"bash_hook_dedup": True})

    def test_hooks_json_routes_powershell_commits_and_pushes_to_the_review(self):
        with open(os.path.join(HOOKS, "hooks.json"), encoding="utf-8") as f:
            post = json.load(f)["hooks"]["PostToolUse"]
        ifs = {(h.get("if"), entry["matcher"]) for entry in post for h in entry["hooks"] if h.get("if")}
        for pattern in ("git*commit*", "git*push*", "gt *"):
            self.assertIn((f"PowerShell({pattern})", "PowerShell"), ifs, pattern)
            self.assertIn((f"Bash({pattern})", "Bash"), ifs, pattern)

    def test_session_start_installs_no_sdk(self):
        # ADR 0019: the reviewer's SDK is installed only when a review first wants it
        code, _, raw, err = run_hook(["python3", os.path.join(HOOKS, "ensure_agent_sdk.py")],
                                     {"hook_event_name": "SessionStart"}, self.root,
                                     {"SECURITY_WARNINGS_STATE_DIR": self.path("state")})
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(raw.splitlines()[-1])["metrics"]["sdk_bootstrap"], 11)  # after the async line
        self.assertFalse(os.path.exists(self.path("state/agent-sdk-venv")))


if __name__ == "__main__":
    unittest.main()
