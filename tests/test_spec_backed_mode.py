"""sdlc 3.5's one switch: without an rspec criteria lock or an acceptance bundle a repo behaves as 3.4.0 (no test
lock, no criteria lint, no new config keys or doctor rows); with one, the test lock and the accept keys apply."""
import json
import os
import re
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT
import test_doctor
import test_verify

STATE = os.path.join(PLUGIN_ROOT, "scripts", "state.py")
# Fails until `done` exists (the feature's code), or always passes once the test file says "weak"
RUN = ("python3 -c \"import os, sys; sys.exit(0 if 'weak' in open('tests/t.py').read() "
       "or os.path.exists('done') else 1)\"")


class ModeVerifyTest(test_verify.VerifyTest):
    def red_then_built(self, header=""):
        self.spec("AC-001")
        self.plan([("AC-001", "tests/t.py › ok", RUN)], tasks=["1. t `tests/t.py` `done`"])
        if header:
            self.write(".sdlc/login/state.md", self.read_state().replace("Base:", header + "Base:", 1))
        self.write("tests/t.py", "assert answer == 42\n")
        code, out, _ = self.verify("red", "AC-001")
        self.assertEqual(code, 0, out)
        self.write("done", "")

    def read_state(self):
        with open(self.path(".sdlc/login/state.md"), encoding="utf-8") as f:
            return f.read()

    def test_a_standalone_repo_has_no_test_lock(self):
        self.red_then_built()
        self.assertNotIn("## Test lock", self.read_state())
        self.write("tests/t.py", "assert answer\n")  # 3.4.0: a test edited after red is the review's to judge
        code, out, _ = self.verify()
        self.assertEqual(code, 0, out)
        self.assertNotIn("test lock", out)
        base = re.search(r"^Base:\s*(\S+)", self.read_state(), re.M).group(1)
        code, out, _ = self.verify("red", "--at", base, "AC-001")
        self.assertEqual(code, 1, out)
        self.assertIn("only in a spec-backed repo", out)

    def test_a_standalone_repo_gets_no_criteria_lint(self):
        # rc.1-rc.5 linted this AC (no Given/when/then, no literal, no tag) on an M feature marked Criteria: c1
        self.red_then_built(header="Track: M\nRisk: low\nCriteria: c1\n")
        code, out, rec = self.verify()
        self.assertEqual(code, 0, out)
        self.assertNotIn("criteria:", out)
        self.assertNotIn("warning:", out)
        self.assertNotIn("lint", rec["last"])

    def test_a_spec_backed_repo_locks_its_tests(self):
        self.write("docs/specs/app/criteria.lock.json", "{}")  # tracked: the repo holds an rspec criteria lock
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "spec")
        head = subprocess.run(["git", "-C", self.root, "rev-parse", "HEAD"], capture_output=True,
                              encoding="utf-8").stdout.strip()
        self.state = re.sub(r"Base: \S+", f"Base: {head}", self.state)
        self.red_then_built()
        self.assertIn("## Test lock", self.read_state())
        self.write("tests/t.py", "assert answer == 42, 'the answer'\n")
        code, out, _ = self.verify()
        self.assertEqual(code, 1, out)
        self.assertIn("test lock: tests/t.py changed since its red run (AC-001)", out)
        p = subprocess.run([sys.executable, STATE, "--root", self.root, "deviation", "login",
                            "test-change tests/t.py What: a message on the assert. Why: the failure said nothing."],
                           capture_output=True, encoding="utf-8", errors="replace")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        code, out, _ = self.verify("red", "--at", head, "AC-001")
        self.assertEqual(code, 0, out)
        code, out, _ = self.verify()
        self.assertEqual(code, 0, out)


class ModeDoctorTest(test_doctor.DoctorTest):
    def keys(self):
        p = subprocess.run([sys.executable, test_doctor.SCAFFOLD, "--root", self.root, "add-config-keys"],
                           capture_output=True, encoding="utf-8", errors="replace")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return json.loads(p.stdout)["added"]

    def config(self):
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_a_standalone_repo_gets_no_new_keys_or_rows(self):
        self.setup_repo()
        subprocess.run(["git", "-C", self.root, "init", "-q"], check=True)
        before = self.config()
        self.assertEqual(self.keys(), [])
        self.assertEqual(self.config(), before)
        rows = self.doctor()[0]
        self.assertNotIn(("repo", "accept keys"), rows)
        self.assertNotIn(("repo", "mutation command"), rows)

    def test_a_spec_backed_repo_gets_the_accept_keys(self):
        self.setup_repo()
        subprocess.run(["git", "-C", self.root, "init", "-q"], check=True)
        self.write("docs/specs/app/criteria.lock.json", "{}")
        subprocess.run(["git", "-C", self.root, "add", "docs/specs/app/criteria.lock.json"], check=True)
        self.assertEqual(sorted(self.keys()), ["accept.base_url", "accept.start"])
        self.assertNotIn("mutation", self.config()["commands"])
        self.assertEqual(self.keys(), [])  # safe to run twice
        c = self.check("accept keys")
        self.assertEqual(c["status"], "warn", c)
        self.assertIn("accept.start", c["detail"])
        self.assertIsNone(self.check("mutation command"))
        self.configure(accept={"start": "npm start", "base_url": "http://localhost:3000"})
        self.assertEqual(self.check("accept keys")["status"], "ok")


def load_tests(loader, tests, pattern):
    """Only the tests this file defines: the fixture classes it extends run in their own files."""
    return unittest.TestSuite(cls(n) for cls in (ModeVerifyTest, ModeDoctorTest)
                              for n in loader.getTestCaseNames(cls) if n in vars(cls))


if __name__ == "__main__":
    unittest.main()
