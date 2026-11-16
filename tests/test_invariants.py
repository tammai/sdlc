"""templates/project/ci/invariants.py: the shared sdlc files, checked in CI whichever agent changed them."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "templates", "project", "ci", "invariants.py")
STATE = ("# login\nStatus: active\nProcess: 3\nOwner: a@x.dev\nTool: codex\nCurrent: Stage {stage} – Build\n\n"
         "## Deviations\n{deviation}\n\n## Open questions\n-\n")
CHANGE = ("# login\n\n## Acceptance criteria\n\n- **AC-001** Sign in.\n\n## Acceptance tests\n\n"
          "| AC | Test | Run |\n|---|---|---|\n| AC-001 | t.py › test_sign_in | `pytest t.py` |\n")
TEST = "def test_sign_in():\n    assert sign_in()\n"
REVIEW = "\n## Review\n\n- Recommended and chosen: code, low (no trigger fired), by the user\n- code, low: PASS\n"
BASELINE = ("# Known failures baseline\n\n## Failing tests\n\n| Package | Test (file › name) | Failure, one line | Since |\n"
            "|---|---|---|---|\n{rows}\n\n## Lint and type errors\n\n| Package | Tool | Rule | File | Count |\n"
            "|---|---|---|---|---|\n| — | none | | | |\n")


class InvariantsTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.git("init", "-q", "-b", "main")
        self.write(".sdlc/config.json", '{"docs_dir": "docs/sdlc"}\n')
        self.state()
        self.write("docs/sdlc/changes/login.md", CHANGE)
        self.write("t.py", TEST)  # AC-001's test file (#56 P6 checks it exists)

    def git(self, *args):
        return subprocess.run(["git", "-c", "user.email=t@x.dev", "-c", "user.name=t", *args], cwd=self.root,
                              capture_output=True, encoding="utf-8", check=True).stdout.strip()

    def commit(self, message="c"):
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "--short", "HEAD")

    def state(self, stage=2, deviation="-", process=3):
        self.write(".sdlc/state/login.md", STATE.format(stage=stage, deviation=deviation)
                   .replace("Process: 3", f"Process: {process}"))

    def check(self, *args):
        p = subprocess.run([sys.executable, SCRIPT, *args], cwd=self.root, capture_output=True, encoding="utf-8")
        return p.returncode, p.stdout

    def test_a_clean_repo_passes(self):
        base = self.commit()
        self.assertEqual(self.check("--base", base), (0, "sdlc invariants: ok\n"))

    def test_the_record_matches_the_phase_reached(self):
        # past Define each AC names its test in change.md; in Ship, its Review section says what was reviewed
        self.write("docs/sdlc/changes/login.md", "# login\n\n## Acceptance criteria\n\n- **AC-001** Sign in.\n")
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("## Acceptance tests", out)
        self.write("docs/sdlc/changes/login.md", CHANGE)
        self.state(stage=4)
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("## Review", out)
        self.write("docs/sdlc/changes/login.md", CHANGE + REVIEW)
        self.assertEqual(self.check()[0], 0)

    def test_a_feature_not_yet_migrated_keeps_the_old_stage_numbers(self):
        # Process: 2 counted Build as 4 and Ship as 8; Stage 4 there is Build, so no Review section is due yet
        self.state(stage=4, process=2)
        self.assertEqual(self.check()[0], 0)
        self.state(stage=8, process=2)
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("## Review", out)

    def test_a_grown_baseline_needs_a_deviation(self):
        self.write(".sdlc/baseline.md", BASELINE.format(rows="| — | none | | |"))
        empty = self.commit()
        self.write(".sdlc/baseline.md", BASELINE.format(rows="| api | t.py › test_a | boom | abc |"))
        self.assertEqual(self.check("--base", empty)[0], 0)  # the first fill records what already failed
        recorded = self.commit()
        self.write(".sdlc/baseline.md", BASELINE.format(rows="| api | t.py › test_a | boom | abc |\n"
                                                             "| api | t.py › test_b | bang | def |"))
        code, out = self.check("--base", recorded)
        self.assertEqual(code, 1)
        self.assertIn("t.py › test_b", out)
        # recorded by a feature that finished in the same push
        self.write(".sdlc/state/login.md", STATE.format(stage=4, deviation="- 2026-10-25 baseline: t.py › test_b fails "
                                                        "since the API change; user approved").replace("active", "done"))
        self.assertEqual(self.check("--base", recorded)[0], 0)


class TestLockTest(InvariantsTest):
    """#56 P6: the test lock and each AC's test file, checked in CI."""
    TEST = TEST

    def locked(self, status="active", deviation="-"):
        import hashlib
        sha = hashlib.sha256(self.TEST.encode()).hexdigest()  # LF; the file on a Windows checkout is CRLF
        self.write(".sdlc/state/login.md", STATE.format(stage=2, deviation=deviation).replace(
            "Status: active", f"Status: {status}").replace("## Deviations", f"## Test lock\n- `t.py` sha256:{sha}\n\n"
                                                           "## Deviations"))

    def test_the_test_lock_is_checked(self):
        self.write("t.py", self.TEST)
        self.locked()
        self.assertEqual(self.check(), (0, "sdlc invariants: ok\n"))
        self.write("t.py", "def test_sign_in():\n    assert True\n")
        code, out = self.check()
        self.assertEqual(code, 1, out)
        self.assertIn("t.py changed since its red run", out)
        self.locked(deviation="- test-change t.py What: the assert. Why: it named the wrong call.")
        self.assertEqual(self.check()[0], 0)
        os.remove(self.path("t.py"))
        self.locked()
        code, out = self.check("--json")  # #76: one document, each problem with its stable code
        self.assertEqual((code, json.loads(out)["result"]), (1, "fail"))
        self.assertEqual([(p["code"], p["target"]) for p in json.loads(out)["problems"]],
                         [("test_lock_changed", "t.py"), ("test_file_missing", "t.py")])
        code, out = self.check()
        self.assertEqual(code, 1, out)
        self.assertIn("t.py was deleted since its red run", out)

    def test_a_done_feature_is_checked_in_the_push_that_finished_it(self):
        self.write("t.py", self.TEST)
        self.locked()
        base = self.commit()
        self.write("t.py", "def test_sign_in():\n    assert True\n")
        self.locked(status="done")  # Ship's commit: Status done, with the weakened test
        code, out = self.check("--base", base)
        self.assertEqual(code, 1, out)
        self.assertIn("t.py changed since its red run", out)
        later = self.commit()
        self.assertEqual(self.check("--base", later)[0], 0)  # finished earlier: its tests may move on

    def test_each_ac_test_file_exists(self):
        self.write("docs/sdlc/changes/login.md", CHANGE.replace(
            "| AC-001 | t.py › test_sign_in | `pytest t.py` |\n",
            "| AC-001 | t.py › test_sign_in | `pytest t.py` |\n| AC-002 | manual | read it |\n"
            "| AC-003 | departure D-004 | acceptance/http/x.yaml |\n"))
        os.remove(self.path("t.py"))
        code, out = self.check()
        self.assertEqual(code, 1, out)
        self.assertIn("AC-001: its test file t.py doesn't exist", out)
        self.assertNotIn("AC-002", out)
        self.assertNotIn("AC-003", out)
        self.write("t.py", self.TEST)
        self.assertEqual(self.check()[0], 0)
        # A workbench: a test in an app repo isn't in the workbench's checkout, so its own CI covers it
        self.write("workbench.json", '{"repos": [{"name": "api", "role": "app", "write": true}]}\n')
        self.write("docs/sdlc/changes/login.md", CHANGE.replace("t.py › test_sign_in", "api/t.py › test_sign_in"))
        self.assertEqual(self.check(), (0, "sdlc invariants: ok\n"))


def load_tests(loader, tests, pattern):
    """Each class's own tests once: TestLockTest extends InvariantsTest for its fixture only."""
    suite = unittest.TestSuite()
    for cls in (InvariantsTest, TestLockTest):
        for name in loader.getTestCaseNames(cls):
            if name in vars(cls):
                suite.addTest(cls(name))
    return suite


if __name__ == "__main__":
    unittest.main()
