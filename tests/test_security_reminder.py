"""hooks/security_reminder_hook.py: a risky edit gets its security warning; a plain one gets none."""
import json
import os
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
