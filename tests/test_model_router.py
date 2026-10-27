"""hooks/model_router.py: subagent dispatches name a model, never haiku, and fable needs the user's opt-in."""
import json
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

    def test_haiku_is_denied(self):
        out = self.dispatch(subagent_type="general-purpose", model="haiku")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("sonnet", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_m_reviewers_run_on_sonnet_even_on_high_risk(self):
        self.write(".sdlc/login/state.md", "# login\nStatus: active\nTrack: M\nRisk: high\nTop model: opus\n")
        self.assertIsNone(self.dispatch(subagent_type="sdlc:qa-tester", model="sonnet"))

    def test_a_code_reviewer_runs_on_opus_on_every_track_and_risk(self):
        # The user's decision: the review stays on the top tier, M at risk low included (the checker is a code-reviewer)
        out = self.dispatch(subagent_type="sdlc:code-reviewer", model="sonnet")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIsNone(self.dispatch(subagent_type="general-purpose", model="sonnet"))  # the maker keeps its tier

    def test_dispatch_without_a_model_is_denied(self):
        out = self.dispatch(subagent_type="sdlc:verifier")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("name the subagent's model", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_active_feature_in_the_new_layout_is_seen(self):
        os.remove(self.path(".sdlc/login/state.md"))
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc"}))
        self.write(".sdlc/state/login.md", "# login\nStatus: active\nTrack: M\nRisk: low\nTop model: opus\n")
        out = self.dispatch(subagent_type="sdlc:verifier")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_fable_with_the_users_opt_in_goes_ahead(self):
        self.write(".sdlc/login/state.md", "# login\nStatus: active\nTrack: M\nRisk: low\nTop model: fable\n")
        self.assertIsNone(self.dispatch(subagent_type="sdlc:code-reviewer", model="fable"))

    def test_track_l_floor_applies_to_reviewers_only(self):
        self.write(".sdlc/login/state.md", "# login\nStatus: active\nTrack: L\nRisk: low\nTop model: opus\n")
        self.assertEqual(self.dispatch(subagent_type="sdlc:verifier", model="sonnet")
                         ["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIsNone(self.dispatch(subagent_type="general-purpose", model="sonnet"))

    def test_forks_are_exempt(self):
        self.assertIsNone(self.dispatch(subagent_type="fork"))

    def test_dispatches_are_logged_with_the_stage(self):
        self.write(".sdlc/login/state.md", "# login\nStatus: active\nRisk: low\nCurrent: Stage 5 – Verify\n")
        self.dispatch(subagent_type="general-purpose", model="sonnet", description="verify round 1")
        with open(self.path(".sdlc/.work/dispatches.jsonl"), encoding="utf-8") as f:
            entry = json.loads(f.read().splitlines()[-1])
        self.assertEqual((entry["stages"], entry["agent"], entry["model"]), (["Stage 5 – Verify"], "general-purpose", "sonnet"))

    def test_no_active_feature_is_silent(self):
        self.write(".sdlc/login/state.md", "# login\nStatus: done\n")
        self.assertIsNone(self.dispatch(subagent_type="sdlc:verifier"))


if __name__ == "__main__":
    unittest.main()
