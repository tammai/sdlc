"""templates/project/ci/invariants.py: the shared sdlc files, checked in CI whichever agent changed them."""
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "templates", "project", "ci", "invariants.py")
STATE = ("# login\nStatus: active\nProcess: 2\nOwner: a@x.dev\nTool: codex\nCurrent: Stage {stage} – Build\n\n"
         "## Deviations\n{deviation}\n\n## Open questions\n-\n")
SPEC = ("# Spec\n\n## Acceptance criteria\n\n- **AC-001** Sign in.\n\n## Acceptance tests\n\n"
        "| AC | Test | Run |\n|---|---|---|\n| AC-001 | t.py › test_sign_in | `pytest t.py` |\n")
REVIEW = ("# Review\n\n## Recommended and chosen\n\n- Recommended: code, default, because a few files changed\n"
          "- Chosen: code, default, by the user\n\n## Verdicts\n\n| Review | Report | Verdict |\n|---|---|---|\n"
          "| code, default | `code-reviewer-r1.md` | PASS |\n")
BASELINE = ("# Known failures baseline\n\n## Failing tests\n\n| Package | Test (file › name) | Failure, one line | Since |\n"
            "|---|---|---|---|\n{rows}\n\n## Lint and type errors\n\n| Package | Tool | Rule | File | Count |\n"
            "|---|---|---|---|---|\n| — | none | | | |\n")


class InvariantsTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.git("init", "-q", "-b", "main")
        self.write(".sdlc/config.json", '{"docs_dir": "docs/sdlc"}\n')
        self.state()
        self.write("docs/sdlc/intents/login/spec.md", SPEC)

    def git(self, *args):
        return subprocess.run(["git", "-c", "user.email=t@x.dev", "-c", "user.name=t", *args], cwd=self.root,
                              capture_output=True, encoding="utf-8", check=True).stdout.strip()

    def commit(self, message="c"):
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "--short", "HEAD")

    def state(self, stage=4, deviation="-"):
        self.write(".sdlc/state/login.md", STATE.format(stage=stage, deviation=deviation))

    def check(self, *args):
        p = subprocess.run([sys.executable, SCRIPT, *args], cwd=self.root, capture_output=True, encoding="utf-8")
        return p.returncode, p.stdout

    def test_a_clean_repo_passes(self):
        base = self.commit()
        self.assertEqual(self.check("--base", base), (0, "sdlc invariants: ok\n"))

    def test_the_record_matches_the_phase_reached(self):
        # sdlc 2.0: past Define each AC names its test in spec.md; in Ship, review.md says what was reviewed
        self.write("docs/sdlc/intents/login/spec.md", "# Spec\n\n## Acceptance criteria\n\n- **AC-001** Sign in.\n")
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("## Acceptance tests", out)
        self.write("docs/sdlc/intents/login/spec.md", SPEC)
        self.state(stage=8)
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("review.md", out)
        self.write("docs/sdlc/intents/login/review.md", REVIEW)
        self.assertEqual(self.check()[0], 0)

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
        self.write(".sdlc/state/login.md", STATE.format(stage=8, deviation="- 2026-10-25 baseline: t.py › test_b fails "
                                                        "since the API change; user approved").replace("active", "done"))
        self.assertEqual(self.check("--base", recorded)[0], 0)


if __name__ == "__main__":
    unittest.main()
