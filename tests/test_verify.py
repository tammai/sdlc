"""scripts/verify.py: one command proves every acceptance criterion, records red runs and catches drift from the plan."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "verify.py")
STATE = "# Feature: login\nStatus: active\nProcess: 2\nCurrent: Stage 4 – Build\nBase: {base}\n"


class VerifyTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.git("init", "-q", "-b", "main")
        self.write(".gitignore", ".sdlc/.work/\n")
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"print('ok')\""}}))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        base = subprocess.run(["git", "-C", self.root, "rev-parse", "HEAD"], capture_output=True,
                              encoding="utf-8").stdout.strip()
        self.write(".sdlc/login/state.md", STATE.format(base=base))

    def git(self, *args):
        subprocess.run(["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t", *args], check=True)

    def spec(self, *acs):
        self.write(".sdlc/login/spec.md", "# Spec\n\n## Acceptance criteria\n\n" +
                   "".join(f"- **{ac}** something observable\n" for ac in acs))

    def plan(self, rows, tasks=(), deviations=()):
        table = "| AC | Test | Run |\n|---|---|---|\n" + "".join(
            f"| {ac} | {test} | {run if test == 'manual' else '`' + run + '`'} |\n" for ac, test, run in rows)
        self.write(".sdlc/login/plan.md", "# Plan\n\n## Tasks\n\n" + "\n".join(tasks) +
                   "\n\n## Acceptance tests\n\n" + table + "\n## Public Surface\n\n- none\n\n## Deviations\n\n" +
                   "\n".join(deviations) + "\n")

    def record(self):
        try:
            with open(self.path(".sdlc/.work/verify.json"), encoding="utf-8") as f:
                return json.load(f)
        except OSError:
            return {}

    def verify(self, *args):
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, *args], capture_output=True,
                           encoding="utf-8", errors="replace")
        return p.returncode, p.stdout + p.stderr, self.record()

    def write_red(self, ac):
        rec = self.record()
        rec.setdefault("red", {})[ac] = {"at": "2026-10-27T00:00:00Z", "tree": "t", "exit": 1}
        self.write(".sdlc/.work/verify.json", json.dumps(rec))

    def test_every_ac_needs_a_red_record_and_a_passing_test(self):
        self.spec("AC-001", "AC-002")
        self.plan([("AC-001", "`tests/t.py` › ok", 'python3 -c "pass"'),  # a backticked path is still the path
                   ("AC-002", "manual", "visual check of the badge")])
        self.write("tests/t.py", "")
        code, out, rec = self.verify()
        self.assertEqual(code, 1)
        self.assertIn("AC-001: no red run recorded", out)
        self.write_red("AC-001")
        code, out, rec = self.verify()
        self.assertEqual(code, 0, out)
        self.assertEqual(rec["last"]["result"], "pass")
        self.assertEqual(rec["last"]["manual"], ["AC-002"])

    def test_a_2_0_spec_carries_each_criterions_test_beside_it(self):
        # sdlc 2.0: spec.md is permanent and holds the AC → test table; plan.md (tasks) is a working file
        self.write(".sdlc/login/spec.md", "# Spec\n\n## Acceptance criteria\n\n- **AC-001** something observable\n\n"
                   "## Acceptance tests\n\n| AC | Test | Run |\n|---|---|---|\n"
                   "| AC-001 | tests/t.py › ok | `python3 -c \"pass\"` |\n")
        self.write(".sdlc/login/plan.md", "# Plan\n\n## Tasks\n\n1. **t** — AC-001\n   - Files: `tests/t.py`\n\n"
                   "## Public Surface\n\n- none\n\n## Deviations\n\n")
        self.write("tests/t.py", "")
        code, out, rec = self.verify()
        self.assertEqual(code, 1)  # the spec's table is read: AC-001 still needs its red record
        self.assertIn("AC-001: no red run recorded", out)
        self.write_red("AC-001")
        code, out, rec = self.verify()
        self.assertEqual(code, 0, out)
        self.assertEqual(rec["last"]["result"], "pass")

    def test_red_records_a_failing_test_and_refuses_a_passing_or_missing_one(self):
        self.spec("AC-001")
        self.plan([("AC-001", "tests/t.py › ok", 'python3 -c "import sys; sys.exit(1)"')])
        self.write("tests/t.py", "")
        code, out, rec = self.verify("red", "AC-001")
        self.assertEqual(code, 0, out)
        self.assertIn("AC-001", rec["red"])
        self.plan([("AC-001", "tests/t.py › ok", 'python3 -c "pass"')])
        code, out, _ = self.verify("red", "AC-001")
        self.assertEqual(code, 1)
        self.assertIn("passes before its code exists", out)
        self.plan([("AC-001", "tests/missing.py › ok", 'python3 -c "import sys; sys.exit(1)"')])
        code, out, _ = self.verify("red", "AC-001")
        self.assertEqual(code, 1)
        self.assertIn("tests/missing.py not found", out)
        # The file exists but the id is wrong: the runner fails without running the test, which proves nothing
        self.plan([("AC-001", "tests/t.py › typo", 'python3 -c "import sys; print(\'AttributeError: module has no attribute test_typo\'); sys.exit(1)"')])
        code, out, _ = self.verify("red", "AC-001")
        self.assertEqual(code, 1)
        self.assertIn("did not run", out)
        self.plan([("AC-001", "tests/t.py › ok", 'python3 -c "import sys; sys.exit(4)"')])  # pytest: node id not found
        self.assertEqual(self.verify("red", "AC-001")[0], 1)

    def test_drift_needs_a_deviation_with_what_why_and_effect(self):
        self.spec()  # no ACs: only the commands and the drift check run
        tasks = ["1. **Store** — FR-001\n   - Files: `src/store.py`"]
        self.plan([], tasks=tasks)
        self.write("src/store.py", "x = 1\n")
        self.write("src/cache.py", "y = 2\n")  # untracked, not in the plan
        self.write("src/__pycache__/store.cpython-310.pyc", "bytecode")  # what running the tests leaves behind
        code, out, _ = self.verify()
        self.assertEqual(code, 1)
        self.assertIn("drift: src/cache.py", out)
        self.assertNotIn("__pycache__", out)
        self.plan([], tasks=tasks, deviations=["- `src/cache.py` (task 1) — What: helper · Why: reuse · Effect: none on ACs"])
        code, out, rec = self.verify()
        self.assertEqual(code, 0, out)
        self.assertEqual(rec["last"]["drift"][0]["covered"], True)

    def status(self):
        code, out, _ = self.verify("status")
        self.assertEqual(code, 0, out)
        return json.loads(out)

    def test_reuse_only_when_both_records_match_the_current_code(self):
        self.spec()
        self.plan([])
        self.verify()
        tree = self.record()["last"]["tree"]
        self.write(".sdlc/.work/verify-freshness.json",  # the hook's copy of the same run
                   json.dumps({"feature": "login", "verify": {"last": {"tree": tree, "result": "pass"}}}))
        self.assertTrue(self.status()["reuse"])
        # Writing the record (review.md, a lesson) after the run isn't a code change: the run still counts
        self.write(".sdlc/login/review.md", "# Review\n")
        self.write("docs/notes.md", "lesson\n")
        self.assertTrue(self.status()["reuse"])
        self.write("src/late.py", "z = 3\n")  # an edit after verify
        self.assertEqual(self.status()["reason"], "code changed since verify")
        # The tree Ship checks against Verified comes from here, since a chained git command is refused in Prove;
        # it leaves out .sdlc/.work/, so scratch files a repo tracks by mistake don't count as code changes
        tree = self.status()["tree"]
        self.write(".sdlc/.work/trust-anchor.json", "{}")
        self.git("add", "-f", ".sdlc/.work/trust-anchor.json")
        self.assertEqual(self.status()["tree"], tree)
        self.write(".sdlc/.work/trust-anchor.json", '{"changed": 1}')
        self.assertEqual(self.status()["tree"], tree)

    def test_a_run_the_hook_never_saw_still_counts_for_reuse(self):
        # A subagent's `verify.py …; git status --short` is a spelling the hook doesn't match: verify.py writes
        # the hook's copy itself, so Prove can reuse the run
        self.spec("AC-001")
        self.plan([("AC-001", "tests/t.py › ok", 'python3 -c "import sys; sys.exit(1)"')])
        self.write("tests/t.py", "")
        self.assertEqual(self.verify("red", "AC-001")[0], 0)
        self.plan([("AC-001", "tests/t.py › ok", 'python3 -c "pass"')])
        code, out, _ = self.verify()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.status()["reason"], "")

    def test_an_s_fix_is_proven_from_the_repro_line_in_its_state(self):
        # S writes no spec.md or plan.md: the state file's Repro line is its one acceptance test (AC-001)
        state = self.path(".sdlc/login/state.md")
        with open(state, encoding="utf-8") as f:
            text = f.read()
        self.write(".sdlc/login/state.md", text.replace("Status: active", "Status: active\nProcess: 2\nTrack: S") +
                   'Repro: `tests/t.py` › cascade removes done | `python3 -c "import sys; sys.exit(1)"`\n')
        self.write("tests/t.py", "")
        self.write("src/fix.py", "x = 1\n")  # no plan, so no drift check
        code, out, _ = self.verify()
        self.assertEqual(code, 1)
        self.assertIn("AC-001: no red run recorded", out)
        code, out, _ = self.verify("red", "AC-001")
        self.assertEqual(code, 0, out)
        self.write(".sdlc/login/state.md", text.replace("Status: active", "Status: active\nProcess: 2\nTrack: S") +
                   'Repro: `tests/t.py` › cascade removes done | `python3 -c "pass"`\n')  # the fix makes it pass
        code, out, rec = self.verify()
        self.assertEqual(code, 0, out)

    def test_an_ac_without_a_row_fails(self):
        self.spec("AC-001", "AC-002")
        self.plan([("AC-001", "tests/t.py › ok", 'python3 -c "pass"')])
        code, out, _ = self.verify()
        self.assertEqual(code, 1)
        self.assertIn("AC-002: no row in ## Acceptance tests", out)


if __name__ == "__main__":
    unittest.main()
