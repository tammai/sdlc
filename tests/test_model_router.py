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

    def test_qa_tester_below_opus_is_denied_on_high_risk(self):
        self.write(".sdlc/login/state.md", "# login\nStatus: active\nTrack: M\nRisk: high\nTop model: opus\n")
        out = self.dispatch(subagent_type="sdlc:qa-tester", model="sonnet")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIsNone(self.dispatch(subagent_type="sdlc:qa-tester", model="opus"))

    def test_dispatch_without_a_model_is_denied(self):
        out = self.dispatch(subagent_type="sdlc:verifier")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("name the subagent's model", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_fable_with_the_users_opt_in_goes_ahead(self):
        self.write(".sdlc/login/state.md", "# login\nStatus: active\nTrack: M\nRisk: low\nTop model: fable\n")
        self.assertIsNone(self.dispatch(subagent_type="sdlc:code-reviewer", model="fable"))

    def test_high_risk_floor_applies_to_reviewers_only(self):
        self.write(".sdlc/login/state.md", "# login\nStatus: active\nTrack: L\nRisk: high\nTop model: opus\n")
        self.assertEqual(self.dispatch(subagent_type="sdlc:verifier", model="sonnet")
                         ["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIsNone(self.dispatch(subagent_type="general-purpose", model="sonnet"))

    def test_forks_are_exempt(self):
        self.assertIsNone(self.dispatch(subagent_type="fork"))

    def test_no_active_feature_is_silent(self):
        self.write(".sdlc/login/state.md", "# login\nStatus: done\n")
        self.assertIsNone(self.dispatch(subagent_type="sdlc:verifier"))


if __name__ == "__main__":
    unittest.main()
