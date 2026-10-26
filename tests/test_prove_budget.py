"""hooks/prove_budget.py: in Prove (Stage 5), non-project shell commands are killed at 120 s and never run in the background."""
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

    def call(self, stage, tool="Bash", **tool_input):
        self.write(".sdlc/login/state.md", STATE.format(stage=stage))
        payload = {"hook_event_name": "PreToolUse", "cwd": self.root, "tool_name": tool, "tool_input": tool_input}
        code, out, raw, err = run_hook(HOOK, payload, self.root)
        self.assertEqual(code, 0, err)
        return (out or {}).get("hookSpecificOutput", {})

    def test_non_project_commands_are_killed_at_120_seconds(self):
        out = self.call(5, command="node probe.js", description="probe", timeout=600000)
        self.assertIsNone(out.get("permissionDecision"))  # the user's permission rules still decide
        self.assertRegex(out["updatedInput"]["command"], r"^g?timeout -k 5 120 node probe\.js$")
        self.assertEqual(out["updatedInput"]["description"], "probe")
        self.assertEqual(out["updatedInput"]["timeout"], 130000)  # past the kill, so Claude Code never backgrounds it
        # A loop can't take the prefix, and hiding it in `bash -c` would slip past the user's deny rules
        self.assertEqual(self.call(5, command="until grep -q done log; do sleep 3; done").get("permissionDecision"), "deny")

    def test_project_commands_are_left_alone(self):
        self.assertEqual(self.call(5, command="cd app && npm test 2>&1 | tail -5", timeout=600000), {})

    def test_background_runs_are_refused_only_in_prove(self):
        out = self.call(5, command="node probe.js", run_in_background=True)
        self.assertEqual(out.get("permissionDecision"), "deny")
        self.assertTrue(out.get("permissionDecisionReason"))
        self.assertEqual(self.call(5, "Monitor", command="until grep -q done log; do sleep 2; done")
                         .get("permissionDecision"), "deny")
        self.assertEqual(self.call(5, "PowerShell", command="node probe.js").get("permissionDecision"), "deny")
        self.assertEqual(self.call(4, command="node probe.js", run_in_background=True), {})


if __name__ == "__main__":
    unittest.main()
