"""hooks/stuck_turn.py: the same failure three times in one Build turn gets one nudge to debug."""
import os
import unittest

from helpers import HOOKS, ProjectTestCase, run_hook

HOOK = ["python3", os.path.join(HOOKS, "stuck_turn.py")]


def state(stage):
    return f"# login\nStatus: active\nProcess: 3\nTrack: M\nRisk: low\nCurrent: Stage {stage}\n"


class StuckTurnTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.write(".sdlc/state/login.md", state("2 – Build"))
        self.write(".sdlc/config.json", '{"commands": {"test": "npm test"}}')

    def failure(self, command="npm test", error="Exit code 1\nFAIL login.test.js (0.31 s)", **extra):
        payload = {"hook_event_name": "PostToolUseFailure", "cwd": self.root, "session_id": "s1",
                   "tool_name": "Bash", "tool_input": {"command": command}, "error": error, "is_interrupt": False}
        payload.update(extra)
        _, out, _, _ = run_hook(HOOK, payload, self.root)
        return (out or {}).get("hookSpecificOutput", {}).get("additionalContext")

    def prompt(self):
        run_hook(HOOK, {"hook_event_name": "UserPromptSubmit", "cwd": self.root, "session_id": "s1",
                        "prompt": "go on"}, self.root)

    def test_third_same_failure_nudges_once_per_turn(self):
        self.prompt()
        self.assertIsNone(self.failure())
        self.assertIsNone(self.failure())
        note = self.failure()
        self.assertIn("sdlc:systematic-debugging", note or "")
        self.assertIsNone(self.failure())  # one nudge per turn
        self.prompt()
        self.assertIsNone(self.failure())
        self.assertIsNone(self.failure())
        self.assertIn("sdlc:systematic-debugging", self.failure() or "")

    def test_different_failures_are_counted_apart(self):
        self.prompt()
        self.assertIsNone(self.failure())
        self.assertIsNone(self.failure(command="npm run lint"))
        self.assertIsNone(self.failure(error="Exit code 1\nTypeError: x is undefined"))
        self.assertIsNone(self.failure(error="Exit code 1\nFAIL login.test.js (1.07 s)"))  # same failure, other timing
        self.assertIn("sdlc:systematic-debugging", self.failure(error="Exit code 1\nFAIL login.test.js (2.4 s)") or "")

    def test_silent_outside_build_under_cap_and_in_subagents(self):
        self.prompt()
        for _ in range(3):
            self.assertIsNone(self.failure(agent_type="general-purpose", agent_id="a1"))
        self.write(".sdlc/state/login.md", state("3 – Review"))
        for _ in range(3):
            self.assertIsNone(self.failure(command="npm run build"))
        self.write(".sdlc/state/login.md", state("2 – Build"))
        for n in (1, 2):
            self.write(f".sdlc/.work/findings/login/code-reviewer-r{n}.md", f"# r{n}\n\nVERDICT: FAIL — F1\n")
        for _ in range(3):
            self.assertIsNone(self.failure(command="npm run typecheck"))
        os.remove(self.path(".sdlc/state/login.md"))
        for _ in range(3):
            self.assertIsNone(self.failure(command="npm run e2e"))
        # the same session in Build with no cap: the hook speaks, so the silences above are its choice
        self.write(".sdlc/state/login.md", state("2 – Build"))
        for n in (1, 2):
            os.remove(self.path(f".sdlc/.work/findings/login/code-reviewer-r{n}.md"))
        self.assertIsNone(self.failure(command="npm run format"))
        self.assertIsNone(self.failure(command="npm run format"))
        self.assertIn("sdlc:systematic-debugging", self.failure(command="npm run format") or "")


if __name__ == "__main__":
    unittest.main()
