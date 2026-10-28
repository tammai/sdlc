"""hooks/sdlc_review_gate.py: while a feature is active, the commit security review runs once per review-ready diff."""
import os
import subprocess
import sys
import unittest

from helpers import HOOKS, ProjectTestCase

sys.path.insert(0, HOOKS)
import sdlc_review_gate  # noqa: E402

STATE = "# login\nStatus: active\nProcess: 2\nRisk: {risk}\nBase: {base}\nCurrent: Stage {stage} – x\n"


class ReviewGateTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.git("init", "-q", "-b", "main")
        self.commit("a.ts", "one\n")
        self.base = self.head()
        self.git("checkout", "-q", "-b", "feature")

    def git(self, *args):
        return subprocess.run(["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t", *args],
                              check=True, capture_output=True, encoding="utf-8").stdout.strip()

    def commit(self, rel, text):
        self.write(rel, text)
        self.git("add", rel)
        self.git("commit", "-q", "-m", rel)

    def head(self):
        return self.git("rev-parse", "HEAD")

    def stage(self, n, base=None, risk="high"):
        self.write(".sdlc/state/login.md", STATE.format(base=base or self.base, stage=n, risk=risk))

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

    def test_only_a_security_touched_change_gets_the_model_review(self):
        self.stage(8, risk="low")
        self.commit("src/list.ts", "sort\n")
        plain = self.head()
        self.assertTrue(sdlc_review_gate.decide(self.root, [plain[:7]], set())["skip"])  # no model call
        self.commit("src/auth/session.ts", "token\n")  # areas.sensitive in the config defaults
        self.assertFalse(sdlc_review_gate.decide(self.root, [self.head()[:7]], set()).get("skip"))
        self.stage(8, risk="high")
        self.commit("src/list.ts", "sort\nagain\n")
        self.assertFalse(sdlc_review_gate.decide(self.root, [self.head()[:7]], set()).get("skip"))
        # The config is agent-writable: emptying its areas, or any uncommitted edit to it, never buys a skip
        self.git("checkout", "-q", "-b", "next", "main")  # a fresh feature: nothing sensitive in its diff yet
        self.stage(8, base=self.head(), risk="low")
        self.write(".sdlc/config.json", '{"areas": {"sensitive": ["nothing/**"], "migrations": []}}')
        self.commit("src/auth/token.ts", "t\n")
        self.assertFalse(sdlc_review_gate.decide(self.root, [self.head()[:7]], set()).get("skip"))
        self.git("checkout", "-q", "-b", "ship", "main")
        self.stage(8, base=self.head(), risk="low")
        self.git("add", "-f", ".sdlc/state/login.md")  # Ship's commit carries the state file
        self.commit("src/list.ts", "s\n")
        self.assertTrue(sdlc_review_gate.decide(self.root, [self.head()[:7]], set()).get("skip"))
        self.git("checkout", "-q", "-b", "cased", "main")
        self.stage(8, base=self.head(), risk="low")
        self.commit("src/Auth/Login.ts", "l\n")  # macOS and Windows checkouts ignore case
        self.assertFalse(sdlc_review_gate.decide(self.root, [self.head()[:7]], set()).get("skip"))

    def test_deferral_is_capped_so_a_stuck_stage_cant_skip_reviews_forever(self):
        # The state file is writable by the agent the review checks: a feature left at Stage 4 stops deferring
        self.stage(4)
        for n in range(sdlc_review_gate.MAX_DEFER):
            self.commit("a.ts", f"one\n{n}\n")
        plan = sdlc_review_gate.decide(self.root, [self.head()[:7]], set())
        self.assertFalse(plan["defer"])
        self.assertEqual(len(plan["shas"]), sdlc_review_gate.MAX_DEFER)
        self.assertEqual(plan["range"][0], self.base)  # the net diff starts at Base: every commit is in it

    def test_moving_base_forward_doesnt_reset_the_deferral_cap(self):
        # Base: is agent-writable; the cap counts from where the branch left main, which the agent can't move
        self.stage(4)
        for n in range(sdlc_review_gate.MAX_DEFER):
            self.commit("a.ts", f"one\n{n}\n")
        self.stage(4, base=self.git("rev-parse", "HEAD~1"))
        plan = sdlc_review_gate.decide(self.root, [self.head()[:7]], set())
        self.assertFalse(plan["defer"])
        self.assertEqual(len(plan["shas"]), sdlc_review_gate.MAX_DEFER)
        self.assertEqual(plan["range"][0], self.base)  # every unreviewed commit is in the diff

    def test_on_the_default_branch_nothing_is_deferred(self):
        # No branch point to count deferrals from: fail closed
        self.git("checkout", "-q", "main")
        self.stage(4)
        self.commit("a.ts", "one\non main\n")
        self.assertFalse(sdlc_review_gate.decide(self.root, [self.head()[:7]], set())["defer"])

    def test_ships_commit_that_marks_the_feature_done_is_still_reviewed(self):
        self.stage(8)
        self.commit(".sdlc/state/login.md", STATE.format(base=self.base, stage=8, risk="high"))
        self.write("src/auth/login.ts", "token\n")
        self.write(".sdlc/state/login.md", STATE.format(base=self.base, stage=8, risk="high")
                   .replace("Status: active", "Status: done"))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "ship")
        plan = sdlc_review_gate.decide(self.root, [self.head()[:7]], set())
        self.assertFalse(plan.get("off") or plan["defer"])
        self.commit("src/auth/later.ts", "x\n")  # a later commit of the finished feature: no longer gated
        self.assertTrue(sdlc_review_gate.decide(self.root, [self.head()[:7]], set()).get("off"))

    def test_without_an_active_feature_a_commit_gets_no_model_review_unless_asked(self):
        # ADR 0019: no review and nothing recorded as reviewed, so the push review still covers it
        self.commit("src/auth/b.ts", "2")
        plan = sdlc_review_gate.decide(self.root, ["abc1234"], set())
        self.assertTrue(plan["defer"] and plan["off"])
        self.assertEqual(plan["shas"], [])
        os.environ["SDLC_SECURITY_REVIEW"] = "always"
        self.addCleanup(os.environ.pop, "SDLC_SECURITY_REVIEW", None)
        self.assertEqual(sdlc_review_gate.decide(self.root, ["abc1234"], set()),
                         {"defer": False, "shas": ["abc1234"], "own": ["abc1234"], "range": None, "active": False})

    def test_the_turn_end_review_runs_only_for_a_security_touched_feature(self):
        self.write("src/list.ts", "sort")
        self.assertFalse(sdlc_review_gate.review_wanted(self.root))  # no active feature
        self.stage(5, risk="low")
        self.assertFalse(sdlc_review_gate.review_wanted(self.root))
        self.write("src/auth/login.ts", "x")  # untracked, in areas.sensitive
        self.assertTrue(sdlc_review_gate.review_wanted(self.root))

    def test_a_feature_whose_base_is_not_in_this_history_defers_nothing(self):
        # A stale state file from another branch must not hold back reviews of unrelated work
        self.stage(4, base="0123456789abcdef0123456789abcdef01234567")
        self.commit("hotfix.ts", "fix")
        self.assertFalse(sdlc_review_gate.decide(self.root, [self.head()[:7]], set())["defer"])


if __name__ == "__main__":
    unittest.main()
