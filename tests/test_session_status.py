"""hooks/session_status.py: SessionStart puts the sdlc setup and paths in context, only in an sdlc repo."""
import json
import os
import unittest

from helpers import HOOKS, ProjectTestCase, run_hook

HOOK = ["python3", os.path.join(HOOKS, "session_status.py")]


class SessionStatusTest(ProjectTestCase):
    def call(self):
        code, out, raw, err = run_hook(HOOK, {"hook_event_name": "SessionStart", "cwd": self.root}, self.root)
        self.assertEqual(code, 0, err)
        return (out or {}).get("hookSpecificOutput", {}).get("additionalContext")

    def test_status_and_paths_in_an_sdlc_repo_only(self):
        self.assertIsNone(self.call())  # not an sdlc repo: nothing added to every session
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "npm test"}}))
        self.write(".sdlc/login/state.md", "# login\nStatus: active\nProcess: 2\nCurrent: Stage 4 – Build\n")
        line = self.call()
        self.assertIn("setup none", line)
        self.assertIn("state file .sdlc/<feature>/state.md", line)
        self.assertIn("remote none", line)
        self.assertIn("active: login (Stage 4 – Build)", line)


if __name__ == "__main__":
    unittest.main()
