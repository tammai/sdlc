"""hooks/user_answer.py: an AskUserQuestion call counts as the user's reply only when the agent left `answers` empty."""
import os
import unittest

from helpers import HOOKS, ProjectTestCase, run_hook

HOOK = ["python3", os.path.join(HOOKS, "user_answer.py")]
STATE = "# login\nStatus: active\nProcess: 3\nTrack: M\nRisk: low\nCurrent: Stage 3 – Review\n"
QUESTION = {"question": "Accept?", "header": "Trust anchor", "options": [{"label": "Accept"}, {"label": "Undo it"}]}


class UserAnswerTest(ProjectTestCase):
    def ask(self, **extra):
        code, out, _, err = run_hook(HOOK, {"hook_event_name": "PreToolUse", "cwd": self.root, "tool_name": "AskUserQuestion",
                                            "tool_use_id": "toolu_1", "tool_input": dict({"questions": [QUESTION]}, **extra)},
                                     self.root)
        self.assertEqual(code, 0, err)
        return (out or {}).get("hookSpecificOutput", {}).get("permissionDecision")

    def test_a_call_with_answers_filled_in_is_denied_and_a_clean_one_recorded(self):
        self.write(".sdlc/state/login.md", STATE)
        self.assertEqual(self.ask(answers={"Accept?": "Accept"}), "deny")
        self.assertFalse(os.path.exists(self.path(".sdlc/.work/asked.json")))
        self.assertIsNone(self.ask())
        with open(self.path(".sdlc/.work/asked.json"), encoding="utf-8") as f:
            self.assertIn("toolu_1", f.read())

    def test_with_no_active_feature_it_is_silent_and_writes_nothing(self):
        # Setup asks questions before it ignores .sdlc/.work/: a store written then would land in its commits
        self.write(".sdlc/config.json", "{}")
        self.assertIsNone(self.ask(answers={"Accept?": "Accept"}))
        self.assertFalse(os.path.exists(self.path(".sdlc/.work/asked.json")))


if __name__ == "__main__":
    unittest.main()
