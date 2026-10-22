"""hooks/model_router.py: subagent dispatches name a model, and fable needs the user's opt-in."""
import os
import unittest

from helpers import HOOKS, ProjectTestCase, run_hook

HOOK = ["python3", os.path.join(HOOKS, "model_router.py")]


class ModelRouterTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.write(".sdlc/login/state.md", "# login\nStatus: active\nTrack: M\nRisk: low\nTop model: opus\n")

    def dispatch(self, **tool_input):
        payload = {"hook_event_name": "PreToolUse", "cwd": self.root, "tool_name": "Agent",
                   "tool_input": {"description": "Review task 1", "prompt": "...", **tool_input}}
        code, out, raw, err = run_hook(HOOK, payload, self.root)
        self.assertEqual(code, 0, err)
        return out

    def test_dispatch_naming_a_tier_goes_ahead(self):
        self.assertIsNone(self.dispatch(subagent_type="sdlc:code-reviewer", model="opus"))

    def test_fable_without_the_users_opt_in_is_denied(self):
        out = self.dispatch(subagent_type="general-purpose", model="fable")
        decision = out["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn("Top model: fable", decision["permissionDecisionReason"])


if __name__ == "__main__":
    unittest.main()
