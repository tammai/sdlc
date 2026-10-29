"""hooks/review_rounds.py: after 3 review rounds that still find bugs, only the user's reply lets work go on."""
import os
import unittest

from helpers import HOOKS, ProjectTestCase, run_hook

HOOK = ["python3", os.path.join(HOOKS, "review_rounds.py")]
STATE = "# login\nStatus: active\nProcess: 2\nTrack: M\nRisk: low\nCurrent: Stage 5 – Review\n"


class ReviewRoundsTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.write(".sdlc/state/login.md", STATE)

    def report(self, n, verdict):
        self.write(f".sdlc/.work/findings/login/code-reviewer-r{n}.md", f"# r{n}\n\nVERDICT: {verdict}\n")

    def edit(self, path="src/login.ts"):
        _, out, _, err = run_hook(HOOK, {"hook_event_name": "PreToolUse", "cwd": self.root, "tool_name": "Edit",
                                         "tool_input": {"file_path": self.path(path)}}, self.root)
        return (out or {}).get("hookSpecificOutput", {}).get("permissionDecision")

    def test_a_third_failing_round_stops_the_fixing_until_the_user_answers(self):
        self.report(1, "FAIL — 1 high: H1")
        self.report(2, "FAIL — 1 high: H1")
        self.assertIsNone(self.edit())  # round 2's bugs are still fixed without asking
        self.report(3, "FAIL — 1 high: H1")
        self.assertEqual(self.edit(), "deny")
        self.assertIsNone(self.edit(".sdlc/.work/findings/login/security-r3.md"))  # a reviewer finishing its report
        os.remove(self.path(".sdlc/.work/findings/login/code-reviewer-r3.md"))  # deleting the report doesn't reset it
        self.assertEqual(self.edit(), "deny")
        run_hook(HOOK, {"hook_event_name": "UserPromptSubmit", "cwd": self.root, "prompt": "one more round"}, self.root)
        self.assertIsNone(self.edit())
        self.report(4, "FAIL — 1 high: H1")
        self.assertEqual(self.edit(), "deny")  # the granted round failed too: ask again


if __name__ == "__main__":
    unittest.main()
