"""templates/project/ci/invariants.py: the shared sdlc files, checked in CI whichever agent changed them."""
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "templates", "project", "ci", "invariants.py")
STATE = ("# login\nStatus: active\nOwner: a@x.dev\nTool: codex\nCurrent: Stage {stage} – Verify\n\n"
         "## Deviations\n{deviation}\n\n## Open questions\n-\n")
ROUND = ("## Round {n} — 2026-10-25T10:00Z — commit {commit}\n\n"
         "| Check | Command | Result |\n|---|---|---|\n| Tests | `pytest` | 3 passed |\n\n"
         "| Criterion | Evidence | Status |\n|---|---|---|\n| FR-001 | `t.py` › \"x\" | ✅ |\n\n"
         "**Verdict:** PASS\n")
BASELINE = ("# Known failures baseline\n\n## Failing tests\n\n| Package | Test (file › name) | Failure, one line | Since |\n"
            "|---|---|---|---|\n{rows}\n\n## Lint and type errors\n\n| Package | Tool | Rule | File | Count |\n"
            "|---|---|---|---|---|\n| — | none | | | |\n")


class InvariantsTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.git("init", "-q", "-b", "main")
        self.write(".sdlc/config.json", '{"docs_dir": "docs/sdlc"}\n')
        self.state()

    def git(self, *args):
        return subprocess.run(["git", "-c", "user.email=t@x.dev", "-c", "user.name=t", *args], cwd=self.root,
                              capture_output=True, encoding="utf-8", check=True).stdout.strip()

    def commit(self, message="c"):
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "--short", "HEAD")

    def state(self, stage=5, deviation="-"):
        self.write(".sdlc/state/login.md", STATE.format(stage=stage, deviation=deviation))

    def check(self, *args):
        p = subprocess.run([sys.executable, SCRIPT, *args], cwd=self.root, capture_output=True, encoding="utf-8")
        return p.returncode, p.stdout

    def test_a_clean_repo_passes(self):
        head = self.commit()
        self.write("docs/sdlc/intents/login/test-report.md", ROUND.format(n=1, commit=head))
        self.write("docs/sdlc/intents/login/spec.md", "- FR-001 [user] Sign in.\n")
        base = self.commit()
        self.assertEqual(self.check("--base", base, "--require-ancestor"), (0, "sdlc invariants: ok\n"))

    def test_rounds_in_review_md_are_checked_ahead_of_an_old_test_report(self):
        # Prove logs its rounds in review.md now; a feature started earlier keeps its test-report.md
        head = self.commit()
        self.write("docs/sdlc/intents/login/test-report.md", ROUND.format(n=1, commit=head))
        self.write("docs/sdlc/intents/login/review.md", "# Review\n\n" + ROUND.format(n=2, commit="1234567"))
        self.commit()
        code, out = self.check("--require-ancestor")
        self.assertEqual(code, 1)
        self.assertIn("review.md: round 2", out)

    def test_a_round_that_does_not_prove_this_code_fails(self):
        self.write("docs/sdlc/intents/login/test-report.md", ROUND.format(n=1, commit="1234567"))  # never committed
        self.commit()
        code, out = self.check("--require-ancestor")
        self.assertEqual(code, 1)
        self.assertIn("isn't in this code's history", out)
        head = self.git("rev-parse", "--short", "HEAD")
        # a gate can pass on uncommitted work (state.md records the tree), so +dirty on a real commit is fine
        self.write("docs/sdlc/intents/login/test-report.md", ROUND.format(n=2, commit=head + "+dirty"))
        self.assertEqual(self.check("--require-ancestor")[0], 0)
        self.write("docs/sdlc/intents/login/test-report.md", f"## Round 3 — now — commit {head}\n\nAll good.\n")
        self.assertIn("missing its checks table, criteria table or verdict", self.check()[1])

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
        self.write(".sdlc/state/login.md", STATE.format(stage=11, deviation="- 2026-10-25 baseline: t.py › test_b fails "
                                                        "since the API change; user approved").replace("active", "done"))
        self.assertEqual(self.check("--base", recorded)[0], 0)

    def test_an_inferred_tag_past_stage_1_fails(self):
        self.write("docs/sdlc/intents/login/spec.md", "- FR-002 [inferred] Remember the user.\n")
        self.state(stage=1)
        self.assertEqual(self.check()[0], 0)  # Stage 1's gate is where the user keeps or drops them
        self.state(stage=2)
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("[inferred]", out)


if __name__ == "__main__":
    unittest.main()
