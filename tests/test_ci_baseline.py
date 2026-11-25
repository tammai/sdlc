"""Brownfield CI (.sdlc/2026-11-25-m-brownfield-ci-baseline): the generated test step passes when only tests listed in
.sdlc/baseline.md fail, through invariants.py --baseline-tests, as ship.py --waive-baseline does locally."""
import json
import os
import subprocess
import sys
import unittest

from helpers import BASH, PLUGIN_ROOT, ProjectTestCase, run_hook

SCAFFOLD = os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py")
BASELINE = """# Known failures baseline

## Failing tests

| Package | Test (file › name) | Failure, one line | Since |
|---|---|---|---|
| (root) | tests/test_x.py › test_old | assert | 2026-11-25 |
"""
PYTEST = "FAILED tests/test_x.py::{name} - assert 1 == 2\n=========== 1 failed, 3 passed in 0.12s ===========\n"


class CiBaselineTest(ProjectTestCase):
    def sc(self, *args):
        code, out, raw, err = run_hook([sys.executable, SCAFFOLD, "--root", self.root, *args], "", self.root)
        self.assertEqual(code, 0, raw + err)
        return out

    def setUp(self):
        super().setUp()
        self.sc("init", "--kind", "brownfield")
        self.write(".sdlc/config.json", json.dumps({
            "project": {"kind": "brownfield", "stack": ["python"]},
            "commands": {"test": "python3 fake_tests.py", "lint": "python3 -c pass"}}))
        self.write(".sdlc/ci/invariants.py",
                   self.sc("preview", "templates/project/ci/invariants.py")["text"])

    def config_json(self):
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            return json.load(f)

    def check(self, log_text):
        log = self.write("test.log", log_text)
        p = subprocess.run([sys.executable, self.path(".sdlc/ci/invariants.py"), "--baseline-tests", log],
                           capture_output=True, encoding="utf-8", errors="replace", cwd=self.root)
        return p.returncode, p.stdout + p.stderr

    def generated_test_step(self):
        """The generated workflow's test step: its run script, unindented."""
        lines = self.sc("preview", "builtin:ci")["text"].splitlines()
        start = next(i for i, l in enumerate(lines) if l.strip() == '- name: "test"')
        run = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
        indent = len(lines[run + 1]) - len(lines[run + 1].lstrip())
        body = []
        for l in lines[run + 1:]:
            if l.strip() and len(l) - len(l.lstrip()) < indent:
                break
            body.append(l[indent:])
        return "\n".join(body).strip() + "\n"

    # AC-001
    def test_the_log_check_passes_only_listed_failures(self):
        self.write(".sdlc/baseline.md", BASELINE)
        code, out = self.check(PYTEST.format(name="test_old"))
        self.assertEqual(code, 0, out)
        code, out = self.check(PYTEST.format(name="test_new"))
        self.assertEqual(code, 1, out)
        self.assertIn("test_new", out)
        code, out = self.check("something broke\n=========== 2 failed in 0.1s ===========\n")
        self.assertEqual(code, 1, out)
        log = self.write("test.log", "something broke\n=========== 2 failed in 0.1s ===========\n")
        p = subprocess.run([sys.executable, self.path(".sdlc/ci/invariants.py"), "--baseline-tests", log, "--json"],
                           capture_output=True, encoding="utf-8", errors="replace", cwd=self.root)
        self.assertEqual([x["code"] for x in json.loads(p.stdout)["problems"]], ["baseline_unmatched"], p.stdout)

    # AC-002
    def test_the_generated_test_step_waives_listed_failures(self):
        self.write(".sdlc/baseline.md", BASELINE)
        script = self.generated_test_step()
        env = {**os.environ, "GITHUB_WORKSPACE": self.root, "RUNNER_TEMP": self.root}
        for name, want in (("test_old", 0), ("test_new", 1)):
            self.write("fake_tests.py", f"import sys\nprint({PYTEST.format(name=name)!r})\nsys.exit(1)\n")
            p = subprocess.run([BASH, "-e", "-c", script], capture_output=True, encoding="utf-8", errors="replace",
                               cwd=self.root, env=env)
            self.assertEqual(p.returncode, want, (name, script, p.stdout + p.stderr))

    def run_step(self, test_command, fake):
        """The generated test step for `test_command`, run in bash with the runner's flags; its exit code."""
        cfg = self.config_json()
        cfg["commands"]["test"] = test_command
        self.write(".sdlc/config.json", json.dumps(cfg))
        self.write("fake_tests.py", fake)
        env = {**os.environ, "GITHUB_WORKSPACE": self.root, "RUNNER_TEMP": self.root}
        p = subprocess.run([BASH, "--noprofile", "--norc", "-eo", "pipefail", "-c", self.generated_test_step()],
                           capture_output=True, encoding="utf-8", errors="replace", cwd=self.root, env=env)
        return p.returncode, p.stdout + p.stderr

    # R1-1, R1-2: a command of several commands, or ending in a comment, keeps its own failures
    def test_a_compound_test_command_keeps_its_failures(self):
        self.write(".sdlc/baseline.md", BASELINE)
        listed = f"import sys\nprint({PYTEST.format(name='test_old')!r})\nsys.exit(1)\n"
        code, out = self.run_step("python3 fake_tests.py; python3 -c 'print(1)'", listed)
        self.assertEqual(code, 0, out)  # the listed failure, then a passing command: waived
        code, out = self.run_step("python3 -c 'import sys; sys.exit(3)'; python3 -c 'print(1)'", listed)
        self.assertNotEqual(code, 0, out)  # an earlier command failed with nothing named
        code, out = self.run_step("python3 fake_tests.py  # unit tests", listed)
        self.assertEqual(code, 0, out)

    # R2-2, R2-3: CI matches names as ship.py --waive-baseline does (go's parent line, `file › name` rows)
    def test_ci_matches_names_as_ship_does(self):
        self.write(".sdlc/baseline.md", BASELINE + "| (root) | TestFoo/sub1 | x | 2026-11-25 |\n"
                   "| (root) | src/calc.test.js › adds numbers | x | 2026-11-25 |\n")
        code, out = self.check("--- FAIL: TestFoo (0.00s)\n    --- FAIL: TestFoo/sub1 (0.00s)\nFAIL\n")
        self.assertEqual(code, 0, out)
        code, out = self.check("not ok 1 - adds numbers\n# fail 1\n")
        self.assertEqual(code, 0, out)
        code, out = self.check("FAIL: test_old (tests.test_x.T.test_old)\n\nFAILED (failures=1)\n")
        self.assertEqual(code, 0, out)
        code, out = self.check("FAILED tests/test_x.py::test_brand_new - x\n==== 1 failed in 0.1s ====\n")
        self.assertEqual(code, 1, out)

    # R3-1: a go name failing in two packages is one name with a count of two, as ship.py reads it: not matched
    def test_a_repeated_go_failure_is_not_waived(self):
        self.write(".sdlc/baseline.md", BASELINE + "| (root) | TestFoo | x | 2026-11-25 |\n")
        code, out = self.check("--- FAIL: TestFoo (0.00s)\nFAIL\ta\n--- FAIL: TestFoo (0.00s)\nFAIL\tb\n")
        self.assertEqual(code, 1, out)

    # R3-2: a baseline that isn't UTF-8 neither stops the workflow's generation nor crashes the check
    def test_a_baseline_that_isnt_utf8_is_read(self):
        with open(self.path(".sdlc/baseline.md"), "wb") as f:
            f.write(BASELINE.replace("assert", "caf\xe9").encode("cp1252"))
        self.assertIn("--baseline-tests", self.generated_test_step())
        code, out = self.check(PYTEST.format(name="test_old"))  # cp1252's `›` can't be read back: fails closed
        self.assertNotIn("Traceback", out)
        log = self.write("test.log", PYTEST.format(name="test_new"))
        p = subprocess.run([sys.executable, self.path(".sdlc/ci/invariants.py"), "--baseline-tests", log, "--json"],
                           capture_output=True, encoding="utf-8", errors="replace", cwd=self.root)
        self.assertEqual([x["code"] for x in json.loads(p.stdout)["problems"]], ["baseline_test_failed"], p.stdout)

    # R2-4: a log that isn't UTF-8 (cp1252 from a Windows runner) is still read
    def test_a_log_that_isnt_utf8_is_read(self):
        self.write(".sdlc/baseline.md", BASELINE)
        log = self.path("test.log")
        with open(log, "wb") as f:
            f.write("FAILED tests/test_x.py::test_old - caf\xe9\n==== 1 failed in 0.1s ====\n".encode("cp1252"))
        p = subprocess.run([sys.executable, self.path(".sdlc/ci/invariants.py"), "--baseline-tests", log],
                           capture_output=True, encoding="utf-8", errors="replace", cwd=self.root)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    # R1-6: colour codes in the log
    def test_a_coloured_log_still_matches(self):
        self.write(".sdlc/baseline.md", BASELINE)
        code, out = self.check("\x1b[31mFAILED\x1b[0m tests/test_x.py::test_old - x\n"
                               "\x1b[31m==== 1 failed in 0.1s ====\x1b[0m\n")
        self.assertEqual(code, 0, out)

    # R1-7: a multi-line step command stays inside its run block
    def test_a_multi_line_command_is_indented(self):
        cfg = self.config_json()
        cfg["commands"]["lint"] = "python3 -c pass\npython3 -c pass"
        self.write(".sdlc/config.json", json.dumps(cfg))
        lines = self.sc("preview", "builtin:ci")["text"].splitlines()
        self.assertFalse([l for l in lines if l.startswith("python3")], lines)

    # R1-8, R1-9: config's baseline path, and --json
    def test_configs_baseline_path_and_json(self):
        cfg = self.config_json()
        cfg["baseline"] = "docs/baseline.md"
        self.write(".sdlc/config.json", json.dumps(cfg))
        self.write("docs/baseline.md", BASELINE)
        self.assertNotEqual(self.generated_test_step(), "python3 fake_tests.py\n")
        log = self.write("test.log", PYTEST.format(name="test_new"))
        p = subprocess.run([sys.executable, self.path(".sdlc/ci/invariants.py"), "--baseline-tests", log, "--json"],
                           capture_output=True, encoding="utf-8", errors="replace", cwd=self.root)
        self.assertEqual(json.loads(p.stdout)["result"], "fail", p.stdout)

    # AC-003
    def test_without_a_baselined_test_the_step_is_plain(self):
        self.assertEqual(self.generated_test_step(), "python3 fake_tests.py\n")


if __name__ == "__main__":
    unittest.main()
