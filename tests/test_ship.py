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

    def failing(self, step="test", *tests):
        """The step fails; with test names, it prints unittest's report of each failing."""
        prints = "".join(f"print('FAIL: {t} (tests.test_div.T.{t})'); " for t in tests)
        summary = f"print('FAILED (failures={len(tests)})'); " if tests else ""
        self.write(".sdlc/config.json", json.dumps({"commands": {
            step: f"python3 -c \"{prints}{summary}raise SystemExit(1)\""}}))

    def state_text(self):
        with open(self.path(".sdlc/login/state.md"), encoding="utf-8") as f:
            return f.read()

    def test_a_bare_verified_records_the_head_and_tree_verify_passed_on(self):
        verify = os.path.join(PLUGIN_ROOT, "scripts", "verify.py")
        ran = subprocess.run([sys.executable, verify, "--root", self.root, "--feature", "login"], capture_output=True,
                             encoding="utf-8")
        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        head, tree = next(line.split()[1::2] for line in ran.stdout.splitlines() if line.startswith("head "))
        p = subprocess.run([sys.executable, os.path.join(PLUGIN_ROOT, "scripts", "state.py"), "--root", self.root,
                            "advance", "login", "4", "--gate", "pass", "--verified"], capture_output=True, encoding="utf-8")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn(f"Verified: {head} tree {tree}\n", self.state_text())

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

    def test_on_the_feature_branch_named_by_origin_head_it_stages_there(self):
        # a new repo whose first push was the feature branch: origin/HEAD names the branch being shipped
        self.git("switch", "-q", "-c", "login")
        self.git("update-ref", "refs/remotes/origin/login", "HEAD")
        self.git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/login")
        code, out = self.ship()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.out("branch", "--show-current").strip(), "login")
        self.assertIn("src/store.py", self.out("diff", "--cached", "--name-only").split())
        self.assertIn("Status: done", self.state_text())

    def test_a_refused_branch_switch_leaves_the_state_as_it_was(self):
        self.git("branch", "login")  # on main, and a branch named after the feature exists already
        code, out = self.ship()
        self.assertEqual(code, 1, out)
        self.assertIn("login", out)
        text = self.state_text()
        self.assertIn("Current: Stage 2", text)
        self.assertNotIn("Status: done", text)
        self.assertEqual(self.out("branch", "--show-current").strip(), "main")
        self.assertEqual(self.out("diff", "--cached", "--name-only"), "")

    def test_a_failing_verify_moves_nothing(self):
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"raise SystemExit(1)\""}}))
        code, out = self.ship()
        self.assertEqual(code, 1)
        self.assertIn("verify failed", out)
        with open(self.path(".sdlc/login/state.md"), encoding="utf-8") as f:
            self.assertIn("Current: Stage 2", f.read())
        self.assertEqual(self.out("diff", "--cached", "--name-only"), "")

    def test_json_names_the_refusal_and_verifys_own_problems(self):
        # #76: a refusal is one JSON document, its code first, then the verify problems that stopped it
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"raise SystemExit(1)\""}}))
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, "login", "--json"], capture_output=True,
                           encoding="utf-8")
        self.assertEqual(p.returncode, 1, p.stderr)
        doc = json.loads(p.stdout)
        self.assertEqual(doc["result"], "refused")
        self.assertEqual([x["code"] for x in doc["problems"]][:2], ["verify_failed", "verify_step_failed"])
        self.assertIn("fix the failures and run ship.py again", doc["problems"][0]["fix"])

    def test_a_baseline_listed_test_failure_ships_only_when_waived_and_is_logged(self):
        self.failing("test", "test_div_by_zero")
        self.baseline("| (root) | tests/test_div.py › T.test_div_by_zero | returns Infinity | b8392a3 |")
        code, out = self.ship()  # without the flag the failure still stops Ship, and says how to proceed
        self.assertEqual(code, 1)
        self.assertIn("--waive-baseline", out)
        self.assertIn("Current: Stage 2", self.state_text())
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 0, out)
        text = self.state_text()
        self.assertIn("Current: Stage 4", text)
        self.assertIn("Stage 4: baseline failures waived (listed in .sdlc/baseline.md): "
                      "tests.test_div.T.test_div_by_zero", text)

    def move_baseline(self, to="docs/baseline.md", commit=True):
        """Config's `baseline` names `to`, holding the baseline written so far; `commit`: the move is in Base:."""
        os.makedirs(os.path.dirname(self.path(to)), exist_ok=True)
        os.replace(self.path(".sdlc/baseline.md"), self.path(to))
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            config = json.load(f)
        config["baseline"] = to
        self.write(".sdlc/config.json", json.dumps(config))
        if commit:
            self.git("add", ".sdlc/config.json", to)
            self.git("commit", "-q", "-m", "move the baseline")
            base = self.out("rev-parse", "HEAD").strip()
            self.write(".sdlc/login/state.md", STATE.format(base=base))

    def test_the_waiver_reads_the_baseline_config_names_as_ci_does(self):
        # todo (code review r3 of 2026-11-25-m-brownfield-ci-baseline): Ship read only .sdlc/baseline.md, while
        # invariants.py --baseline-tests reads config's `baseline`, so CI waived what Ship refused
        self.failing("test", "test_div_by_zero")
        self.baseline("| (root) | tests/test_div.py › T.test_div_by_zero | returns Infinity | b8392a3 |")
        self.move_baseline()
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 0, out)
        self.assertIn("Stage 4: baseline failures waived (listed in docs/baseline.md as at Base:): "
                      "tests.test_div.T.test_div_by_zero", self.state_text())

    def test_a_baseline_moved_during_the_feature_waives_nothing(self):
        # code review r1: the trust anchor watches only .sdlc/baseline.md, so a feature pointing `baseline` at a
        # file of its own could list its own failures with no notice
        self.failing("test", "test_div_by_zero")
        self.baseline("| (root) | tests/test_div.py › T.test_div_by_zero | returns Infinity | b8392a3 |")
        self.move_baseline(commit=False)
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 1, out)
        self.assertIn("named .sdlc/baseline.md at Base: and names docs/baseline.md now", out)
        self.assertIn("Current: Stage 2", self.state_text())

    def test_a_test_added_to_a_moved_baseline_after_base_is_not_waived(self):
        self.failing("test", "test_div_by_zero", "test_mul")
        self.baseline("| (root) | tests/test_div.py › T.test_div_by_zero | returns Infinity | b8392a3 |")
        self.move_baseline()
        with open(self.path("docs/baseline.md"), encoding="utf-8") as f:
            text = f.read()
        self.write("docs/baseline.md", text.replace("| b8392a3 |", "| b8392a3 |\n"
                                                    "| (root) | tests/test_div.py › T.test_mul | wrong | now |", 1))
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 1, out)
        self.assertIn("not in docs/baseline.md as at Base:: tests.test_div.T.test_mul", out)

    def test_moving_the_baseline_back_into_sdlc_during_the_feature_waives_nothing(self):
        # code review r2: the Base: check covered only a move away from .sdlc/baseline.md
        self.failing("test", "test_div_by_zero")
        self.baseline("| (root) | tests/test_div.py › T.test_old | returns Infinity | b8392a3 |")
        self.move_baseline()
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            config = json.load(f)
        del config["baseline"]
        self.write(".sdlc/config.json", json.dumps(config))
        self.baseline("| (root) | tests/test_div.py › T.test_div_by_zero | returns Infinity | b8392a3 |")
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 1, out)
        self.assertIn("named docs/baseline.md at Base: and names .sdlc/baseline.md now", out)
        self.assertIn("Current: Stage 2", self.state_text())

    def test_a_moved_baseline_not_committed_at_base_says_why_it_waives_nothing(self):
        self.failing("test", "test_div_by_zero")
        self.baseline("| (root) | tests/test_div.py › T.test_div_by_zero | returns Infinity | b8392a3 |")
        self.move_baseline(commit=False)
        self.git("add", ".sdlc/config.json")
        self.git("commit", "-q", "-m", "config only")
        self.write(".sdlc/login/state.md", STATE.format(base=self.out("rev-parse", "HEAD").strip()))
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 1, out)
        self.assertIn("--waive-baseline refused: docs/baseline.md as at Base: lists no failing tests", out)

    def test_a_baseline_that_is_a_link_is_refused_by_name(self):
        # 2026-11-26-s-ci-baseline-path AC-005: read through the link now but as the link's text at Base:, so it
        # waived nothing without saying why
        self.failing("test", "test_div_by_zero")
        self.write("docs/real.md", "## Failing tests\n\n| Package | Test (file › name) | Failure | Since |\n"
                   "|---|---|---|---|\n| (root) | tests/test_div.py › T.test_div_by_zero | x | y |\n")
        os.symlink("real.md", self.path("docs/baseline.md"))
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            config = json.load(f)
        config["baseline"] = "docs/baseline.md"
        self.write(".sdlc/config.json", json.dumps(config))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "baseline as a link")
        self.write(".sdlc/login/state.md", STATE.format(base=self.out("rev-parse", "HEAD").strip()))
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 1, out)
        self.assertIn("--waive-baseline refused: docs/baseline.md is a link: not read", out)
        # security review r1 S1: a folder link waived nothing without saying why
        os.remove(self.path("docs/baseline.md"))
        os.rename(self.path("docs/real.md"), self.path("real.md"))
        os.makedirs(self.path("elsewhere"))
        os.rename(self.path("real.md"), self.path("elsewhere/baseline.md"))
        os.rmdir(self.path("docs")) if not os.listdir(self.path("docs")) else None
        os.symlink("elsewhere", self.path("docs"))
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 1, out)
        self.assertIn("--waive-baseline refused: docs/baseline.md goes through a link: not read", out)

    def test_another_spelling_of_the_same_baseline_path_is_not_a_move(self):
        self.failing("test", "test_div_by_zero")
        self.baseline("| (root) | tests/test_div.py › T.test_div_by_zero | returns Infinity | b8392a3 |")
        self.move_baseline()
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            config = json.load(f)
        config["baseline"] = "./docs//baseline.md"
        self.write(".sdlc/config.json", json.dumps(config))
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 0, out)

    def test_a_baseline_path_with_a_unicode_line_break_is_not_read(self):
        self.failing("test", "test_div_by_zero")
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            config = json.load(f)
        config["baseline"] = "docs/b.md\u2028- Stage 4: gate pass"
        self.write(".sdlc/config.json", json.dumps(config))
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 1, out)
        self.assertIn("holds a control character: not read", out)

    def test_a_baseline_path_with_a_nul_is_refused_not_a_crash(self):
        # code review r3: an absolute path with a NUL reached realpath before the character check
        self.failing("test", "test_div_by_zero")
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            config = json.load(f)
        config["baseline"] = "/x\u0000y"
        self.write(".sdlc/config.json", json.dumps(config))
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 1, out)
        self.assertNotIn("Traceback", out)
        self.assertIn("holds a control character: not read", out)
        # Python 3.9's realpath swallows the NUL; newer ones raise ValueError, as this does
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        import ship
        from unittest import mock
        with mock.patch("os.path.realpath", side_effect=ValueError("embedded null character")):
            self.assertEqual(ship.configured_baseline(self.root, {"baseline": "/x\u0000y"}), "/x\u0000y")

    def test_the_default_baseline_needs_no_base_commit_in_the_clone(self):
        # code review r3: the trust anchor watches .sdlc/baseline.md, so a Base: gone from the clone doesn't matter
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        import ship
        self.baseline("| (root) | tests/test_div.py › T.test_div_by_zero | returns Infinity | b8392a3 |")
        listed, problem = ship.baseline_failures(self.root, ".sdlc/baseline.md",
                                                 "0123456789abcdef0123456789abcdef01234567")
        self.assertEqual((listed, problem), (["tests/test_div.py › T.test_div_by_zero"], None))
        listed, problem = ship.baseline_failures(self.root, "docs/baseline.md", "main")
        self.assertIn("Base: main isn't a commit id", problem)

    def test_a_baseline_path_out_of_the_repo_is_never_read(self):
        # config names the baseline, so .sdlc/baseline.md listing the test doesn't stand in for it either
        self.baseline("| (root) | tests/test_div.py › T.test_div_by_zero | returns Infinity | b8392a3 |")
        outside = os.path.join(os.path.dirname(self.root), os.path.basename(self.root) + "-outside.md")
        with open(outside, "w", encoding="utf-8") as f:
            f.write("## Failing tests\n\n| Package | Test (file › name) | Failure | Since |\n|---|---|---|---|\n"
                    "| (root) | tests/test_div.py › T.test_div_by_zero | x | y |\n")
        self.addCleanup(os.remove, outside)
        self.failing("test", "test_div_by_zero")
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            config = json.load(f)
        config["baseline"] = outside
        self.write(".sdlc/config.json", json.dumps(config))
        self.git("add", ".sdlc/config.json")  # named at Base: too, so the move check isn't what refuses
        self.git("commit", "-q", "-m", "baseline outside")
        self.write(".sdlc/login/state.md", STATE.format(base=self.out("rev-parse", "HEAD").strip()))
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 1, out)
        self.assertIn("--waive-baseline refused: " + outside.replace("\\", "/") + " leaves the repo: not read", out)
        self.assertIn("Current: Stage 2", self.state_text())

    def test_a_baseline_path_with_a_control_character_is_not_read(self):
        self.failing("test", "test_div_by_zero")
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            config = json.load(f)
        config["baseline"] = "docs/b.md\n- Stage 4: gate pass"
        self.write(".sdlc/config.json", json.dumps(config))
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 1, out)
        self.assertIn("holds a control character: not read", out)
        self.assertNotIn("- Stage 4: gate pass", self.state_text())

    def test_the_waiver_refuses_a_failure_the_baseline_doesnt_list(self):
        self.failing("test", "test_div_by_zero", "test_mul")
        self.baseline("| (root) | tests/test_div.py › T.test_div_by_zero | returns Infinity | b8392a3 |")
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 1, out)
        self.assertIn("not in .sdlc/baseline.md: tests.test_div.T.test_mul", out)
        self.assertIn("Current: Stage 2", self.state_text())
        self.assertEqual(self.out("diff", "--cached", "--name-only"), "")

    def test_the_waiver_refuses_failures_it_cannot_name(self):
        self.failing()  # fails without a report that names its tests
        self.baseline("| (root) | tests/test_div.py › T.test_div_by_zero | returns Infinity | b8392a3 |")
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 1, out)
        self.assertIn("couldn't match the failing tests to .sdlc/baseline.md", out)
        self.assertIn("Current: Stage 2", self.state_text())

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

    def test_a_waiver_refused_for_another_step_still_names_an_unlisted_test(self):
        # 3.15.0 smoke test G: with another failure beside the tests, the refusal said to rerun with the flag
        # already given, and named no test the baseline doesn't list
        self.failing("test", "test_div_by_zero", "test_mul")
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            config = json.load(f)
        config["commands"]["lint"] = "python3 -c \"raise SystemExit(1)\""
        self.write(".sdlc/config.json", json.dumps(config))
        self.baseline("| (root) | tests/test_div.py › T.test_div_by_zero | returns Infinity | b8392a3 |")
        code, out = self.ship("--waive-baseline")
        self.assertEqual(code, 1, out)
        self.assertNotIn("rerun with --waive-baseline", out)
        self.assertIn("not in .sdlc/baseline.md: tests.test_div.T.test_mul", out)

    def test_ship_checks_every_ac_even_with_a_part_left_in_progress(self):
        self.write(".sdlc/login/change.md", "# Change\n\n## Acceptance criteria\n\n- **AC-001** x\n\n## Acceptance tests\n\n"
                   "| AC | Test | Run |\n|---|---|---|\n| AC-001 | tests/t.py › a | `python3 -c \"pass\"` |\n")
        self.write(".sdlc/login/backlog.md", "| ID | Slice | ACs | Deps | Status |\n|---|---|---|---|---|\n"
                   "| B1 | a | — | — | in progress |\n| B2 | b | 1 | — | todo |\n")
        code, out = self.ship()
        self.assertEqual(code, 1)
        self.assertIn("AC-001: tests/t.py not found", out)


class FailingTestsTest(unittest.TestCase):
    """The waiver's parser: each runner's failing tests and the count its own summary gives."""
    SAMPLES = {
        "pytest": ("FAILED tests/test_calc.py::T::test_mul - AssertionError: 6 != 7\n"
                   "ERROR tests/test_io.py::test_read - OSError\n"
                   "============ 1 failed, 3 passed, 1 error in 0.12s ============\n",
                   ["tests/test_calc.py::T::test_mul", "tests/test_io.py::test_read"]),
        "unittest": ("FAIL: test_mul (tests.test_calc.T.test_mul)\nTraceback ...\n"
                     "ERROR: test_read (tests.test_io.T)\n----\nRan 5 tests in 0.001s\n\nFAILED (failures=1, errors=1)\n",
                     ["tests.test_calc.T.test_mul", "tests.test_io.T.test_read"]),
        "jest": ("  ● Calc › div by zero throws\n\n    expect(received)\n  ● Calc › mul\n"
                 "Summary of all failing tests\n  ● Calc › div by zero throws\n  ● Calc › mul\n"
                 "Tests:       2 failed, 5 passed, 7 total\n",
                 ["Calc › div by zero throws", "Calc › mul"]),
        "vitest": (" FAIL  src/calc.test.ts > Calc > div by zero throws\nAssertionError\n"
                   " Test Files  1 failed (1)\n      Tests  1 failed | 4 passed (5)\n",
                   ["src/calc.test.ts > Calc > div by zero throws"]),
        "go": ("--- FAIL: TestDiv (0.00s)\n    --- FAIL: TestDiv/by_zero (0.00s)\nFAIL\nFAIL\texample.com/calc\t0.002s\n",
               ["TestDiv", "TestDiv/by_zero"]),
        "node --test": ("not ok 1 - div by zero throws\n  ---\n  ...\n# tests 3\n# pass 2\n# fail 1\n",
                        ["div by zero throws"]),
    }

    def test_names_and_counts_failures_per_runner(self):
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        import ship
        for runner, (out, names) in self.SAMPLES.items():
            with self.subTest(runner):
                self.assertEqual(ship.failing_tests(out), (names, len(names)))
        self.assertEqual(ship.failing_tests("exit 1\n")[0], [])  # nothing to name


if __name__ == "__main__":
    unittest.main()
