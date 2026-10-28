"""scripts/ship.py: Ship's one command readies the commit, and moves nothing when verify fails."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "ship.py")
STATE = ("# Feature: login\nStatus: active\nProcess: 2\nCurrent: Stage 4 – Build\nBase: {base}\n\n## Stages\n"
         "- [ ] 1 Define\n- [ ] 4 Build\n- [ ] 8 Ship\n\n## Tasks\n\n1. **Store**\n   - Files: `src/store.py`\n\n"
         "## Public Surface\n\n- none\n\n## Gate log\n-\n\n## Deviations\n-\n")


class ShipTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.git("init", "-q", "-b", "main")
        self.write(".gitignore", ".sdlc/.work/\n")
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"print('ok')\""}}))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        base = self.out("rev-parse", "HEAD").strip()
        self.write(".sdlc/login/state.md", STATE.format(base=base))
        self.write(".sdlc/login/change.md", "# Change\n\n## Acceptance criteria\n\n## Acceptance tests\n\n"
                   "| AC | Test | Run |\n|---|---|---|\n")
        self.write("src/store.py", "x = 1\n")
        self.write("src/__pycache__/store.cpython-310.pyc", "bytecode")

    def git(self, *args):
        subprocess.run(["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t", *args], check=True)

    def out(self, *args):
        return subprocess.run(["git", "-C", self.root, *args], capture_output=True, encoding="utf-8").stdout

    def ship(self):
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, "login", "--message", "feat: store",
                            "--review", "No review ran: low risk."], capture_output=True, encoding="utf-8")
        return p.returncode, p.stdout + p.stderr

    def test_readies_the_commit_in_one_call(self):
        code, out = self.ship()
        self.assertEqual(code, 0, out)
        with open(self.path(".sdlc/login/state.md"), encoding="utf-8") as f:
            self.assertIn("Current: Stage 8", f.read())
        with open(self.path(".sdlc/login/change.md"), encoding="utf-8") as f:
            self.assertIn("## Review\n\nNo review ran: low risk.", f.read())
        self.assertEqual(self.out("branch", "--show-current").strip(), "login")
        staged = self.out("diff", "--cached", "--name-only").split()
        self.assertIn("src/store.py", staged)
        self.assertIn(".sdlc/login/change.md", staged)
        self.assertFalse([f for f in staged if "__pycache__" in f])  # what the tests leave behind isn't committed
        with open(self.path(".sdlc/.work/commit-msg.txt"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "feat: store\n\nRecord: .sdlc/login/change.md\n")

    def test_a_failing_verify_moves_nothing(self):
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"raise SystemExit(1)\""}}))
        code, out = self.ship()
        self.assertEqual(code, 1)
        self.assertIn("verify failed", out)
        with open(self.path(".sdlc/login/state.md"), encoding="utf-8") as f:
            self.assertIn("Current: Stage 4", f.read())
        self.assertEqual(self.out("diff", "--cached", "--name-only"), "")


if __name__ == "__main__":
    unittest.main()
