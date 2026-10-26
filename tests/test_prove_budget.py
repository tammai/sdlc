"""hooks/prove_budget.py: in Prove (Stage 5), non-project Bash commands are capped at 120 s and can't run in the background."""
import json
import os
import unittest

from helpers import HOOKS, ProjectTestCase, run_hook

HOOK = ["python3", os.path.join(HOOKS, "prove_budget.py")]
STATE = "# Feature: login\nStatus: active\nCurrent: Stage {stage} – Prove\n"


class ProveBudgetTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "npm test"}}))

    def bash(self, stage, **tool_input):
        self.write(".sdlc/login/state.md", STATE.format(stage=stage))
        payload = {"hook_event_name": "PreToolUse", "cwd": self.root, "tool_name": "Bash", "tool_input": tool_input}
        code, out, raw, err = run_hook(HOOK, payload, self.root)
        self.assertEqual(code, 0, err)
        return (out or {}).get("hookSpecificOutput", {})

    def test_non_project_commands_run_with_at_most_120_seconds(self):
        out = self.bash(5, command="node probe.js", description="probe", timeout=600000)
        self.assertEqual(out.get("updatedInput"), {"command": "node probe.js", "description": "probe", "timeout": 120000})
        self.assertIsNone(out.get("permissionDecision"))  # the user's permission rules still decide
        self.assertEqual(self.bash(5, command="node probe.js")["updatedInput"]["timeout"], 120000)
        self.assertEqual(self.bash(5, command="cd app && npm test 2>&1 | tail -5", timeout=600000), {})

    def test_background_runs_are_refused_only_in_prove(self):
        out = self.bash(5, command="node probe.js", run_in_background=True)
        self.assertEqual(out.get("permissionDecision"), "deny")
        self.assertTrue(out.get("permissionDecisionReason"))
        self.assertEqual(self.bash(4, command="node probe.js", run_in_background=True), {})


if __name__ == "__main__":
    unittest.main()
