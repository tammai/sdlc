"""scripts/ship.py: Ship's one command readies the commit, and moves nothing when verify fails."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "ship.py")
STATE = ("# Feature: login\nStatus: active\nProcess: 3\nCurrent: Stage 2 – Build\nBase: {base}\n\n## Stages\n"
         "- [ ] 1 Define\n- [ ] 2 Build\n- [ ] 4 Ship\n\n## Tasks\n\n1. **Store**\n   - Files: `src/store.py`\n\n"
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

    def ship(self, *extra):
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, "login", "--review", "No review ran: low risk.", *extra],
                           capture_output=True, encoding="utf-8")
        return p.returncode, p.stdout + p.stderr

    def baseline(self, row):
        self.write(".sdlc/baseline.md", "# Known failures baseline\n\n## Failing tests\n\n"
                   "| Package | Test (file › name) | Failure, one line | Since |\n|---|---|---|---|\n" + row + "\n\n"
                   "## Lint and type errors\n\n| Package | Tool | Rule | File | Count |\n|---|---|---|---|---|\n| — | none | | | |\n")

    def failing(self, step="test"):
        self.write(".sdlc/config.json", json.dumps({"commands": {step: "python3 -c \"raise SystemExit(1)\""}}))

    def state_text(self):
        with open(self.path(".sdlc/login/state.md"), encoding="utf-8") as f:
            return f.read()

    def test_readies_the_commit_in_one_call(self):
        code, out = self.ship()
        self.assertEqual(code, 0, out)
        with open(self.path(".sdlc/login/state.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Current: Stage 4", text)
        self.assertIn("Status: done", text)  # committed with the change, so the kept record says done
        with open(self.path(".sdlc/login/change.md"), encoding="utf-8") as f:
            self.assertIn("## Review\n\nNo review ran: low risk.", f.read())
        self.assertEqual(self.out("branch", "--show-current").strip(), "login")
        staged = self.out("diff", "--cached", "--name-only").split()
        self.assertIn("src/store.py", staged)
        self.assertIn(".sdlc/login/change.md", staged)
        self.assertFalse([f for f in staged if "__pycache__" in f])  # what the tests leave behind isn't committed
        self.assertFalse([f for f in staged if f.endswith((".json", ".jsonl")) and f.startswith(".sdlc/state/")])
        with open(self.path(".sdlc/.work/commit-msg.txt"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "Change\n\nRecord: .sdlc/login/change.md\n")  # the change file's title

    def test_a_failing_verify_moves_nothing(self):
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"raise SystemExit(1)\""}}))
        code, out = self.ship()
        self.assertEqual(code, 1)
        self.assertIn("verify failed", out)
        with open(self.path(".sdlc/login/state.md"), encoding="utf-8") as f:
            self.assertIn("Current: Stage 2", f.read())
        self.assertEqual(self.out("diff", "--cached", "--name-only"), "")

    def test_a_baseline_listed_test_failure_ships_only_when_waived_and_is_logged(self):
        self.failing()
        self.baseline("| (root) | src/div.test.js › div by zero throws | returns Infinity | b8392a3 |")
        code, out = self.ship()  # without the flag the failure still stops Ship, and says how to proceed
        self.assertEqual(code, 1)
        self.assertIn("--waive-baseline", out)
        self.assertIn("Current: Stage 2", self.state_text())
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 0, out)
        text = self.state_text()
        self.assertIn("Current: Stage 4", text)
        self.assertRegex(text, r"Stage 4: baseline failures waived: only the test step failed; 1 listed in \.sdlc/baseline\.md")

    def test_the_waiver_needs_the_baseline_to_list_a_failing_test(self):
        self.failing()
        self.baseline("| — | none | | |")  # the template's empty row lists nothing
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 1)
        self.assertNotIn("--waive-baseline", out.split("verify failed", 1)[1])  # no hint where a waiver can't apply
        self.assertIn("Current: Stage 2", self.state_text())
        os.remove(self.path(".sdlc/baseline.md"))
        self.assertEqual(self.ship("--waive-baseline")[0], 1)  # nor with no baseline file

    def test_the_waiver_covers_the_test_step_only(self):
        self.write(".sdlc/config.json", json.dumps({"commands": {
            "test": "python3 -c \"print('ok')\"", "lint": "python3 -c \"raise SystemExit(1)\""}}))
        self.baseline("| (root) | src/div.test.js › div by zero throws | returns Infinity | b8392a3 |")
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 1, out)
        self.assertIn("Current: Stage 2", self.state_text())


    def test_ship_checks_every_ac_even_with_a_part_left_in_progress(self):
        self.write(".sdlc/login/change.md", "# Change\n\n## Acceptance criteria\n\n- **AC-001** x\n\n## Acceptance tests\n\n"
                   "| AC | Test | Run |\n|---|---|---|\n| AC-001 | tests/t.py › a | `python3 -c \"pass\"` |\n")
        self.write(".sdlc/login/backlog.md", "| ID | Slice | ACs | Deps | Status |\n|---|---|---|---|---|\n"
                   "| B1 | a | — | — | in progress |\n| B2 | b | 1 | — | todo |\n")
        code, out = self.ship()
        self.assertEqual(code, 1)
        self.assertIn("AC-001: tests/t.py not found", out)


if __name__ == "__main__":
    unittest.main()
