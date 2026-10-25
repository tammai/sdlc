"""hooks/sdlc_review_gate.py: while a feature is active, the commit security review runs once per review-ready diff."""
import os
import subprocess
import sys
import unittest

from helpers import HOOKS, ProjectTestCase

sys.path.insert(0, HOOKS)
import sdlc_review_gate  # noqa: E402

STATE = "# login\nStatus: active\nBase: {base}\nCurrent: Stage {stage} – x\n"


class ReviewGateTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.git("init", "-q")
        self.commit("a.ts", "one\n")
        self.base = self.head()

    def git(self, *args):
        return subprocess.run(["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t", *args],
                              check=True, capture_output=True, encoding="utf-8").stdout.strip()

    def commit(self, rel, text):
        self.write(rel, text)
        self.git("add", rel)
        self.git("commit", "-q", "-m", rel)

    def head(self):
        return self.git("rev-parse", "HEAD")

    def stage(self, n, base=None):
        self.write(".sdlc/state/login.md", STATE.format(base=base or self.base, stage=n))

    def test_build_commits_wait_for_the_review_ready_one_whose_review_covers_their_changes(self):
        self.stage(4)
        self.commit("a.ts", "one\nbuild change\n")
        build = self.head()
        self.assertTrue(sdlc_review_gate.decide(self.root, [build[:7]], set())["defer"])  # not reviewed yet
        self.stage(6)
        self.commit("a.ts", "one\nbuild change\nready change\n")  # the same file again
        ready = self.head()
        plan = sdlc_review_gate.decide(self.root, [ready[:7]], set())
        self.assertEqual(plan["shas"], [ready, build])
        net = self.git("diff", *plan["range"])  # one diff for the whole range: no hunk of either commit is lost
        self.assertIn("+build change", net)
        self.assertIn("+ready change", net)

    def test_without_an_active_feature_a_commit_is_reviewed_as_before(self):
        self.commit("b.ts", "2")
        self.assertEqual(sdlc_review_gate.decide(self.root, ["abc1234"], set()),
                         {"defer": False, "shas": ["abc1234"], "range": None, "active": False})

    def test_a_feature_whose_base_is_not_in_this_history_defers_nothing(self):
        # A stale state file from another branch must not hold back reviews of unrelated work
        self.stage(4, base="0123456789abcdef0123456789abcdef01234567")
        self.commit("hotfix.ts", "fix")
        self.assertFalse(sdlc_review_gate.decide(self.root, [self.head()[:7]], set())["defer"])


if __name__ == "__main__":
    unittest.main()
