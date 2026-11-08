"""Spec 03 S4 in a spec-backed repo: a test recorded red is locked (ported from 3.5.0-rc.2, ff2ac10)."""
import json
import os
import re
import subprocess
import sys
import time
import unittest

from helpers import PLUGIN_ROOT
import test_verify


class VerifyBase(test_verify.VerifyTest):
    """3.4.0's verify fixture; its own tests run in test_verify.py, not again here (load_tests)."""

    def read_state(self):
        with open(self.path(".sdlc/login/state.md"), encoding="utf-8") as f:
            return f.read()


class TestLockTest(VerifyBase):
    """Spec 03 S4: a test recorded red is locked; changing it needs a recorded reason and a red run at Base."""
    # Fails until `done` exists (the feature's code), or always passes once the test file says "weak"
    RUN = ("python3 -c \"import os, sys; sys.exit(0 if 'weak' in open('tests/t.py').read() "
           "or os.path.exists('done') else 1)\"")

    def setUp(self):
        super().setUp()  # a spec-backed repo: config names its criteria lock (spec_lock.spec_backed_repo)
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"print('ok')\""},
                                                    "spec_lock": "docs/specs/app/criteria.lock.json"}))

    def locked(self):
        self.spec("AC-001")
        self.plan([("AC-001", "tests/t.py › ok", self.RUN)], tasks=["1. t `tests/t.py` `done`"])
        self.write("tests/t.py", "assert answer == 42\n")
        code, out, _ = self.verify("red", "AC-001")
        self.assertEqual(code, 0, out)
        self.write("done", "")

    def deviation(self, text):
        p = subprocess.run([sys.executable, os.path.join(PLUGIN_ROOT, "scripts", "state.py"), "--root", self.root,
                            "deviation", "login", text], capture_output=True, encoding="utf-8")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_red_locks_each_test_file_it_ran(self):
        self.locked()
        import hashlib
        with open(self.path("tests/t.py"), "rb") as f:  # as written on this platform (CRLF on Windows)
            sha = hashlib.sha256(f.read()).hexdigest()
        self.assertIn(f"## Test lock\n- `tests/t.py` sha256:{sha}", self.read_state().replace("\r\n", "\n"))
        code, out, _ = self.verify()
        self.assertEqual(code, 0, out)

    def test_a_changed_locked_test_fails_the_run(self):
        self.locked()
        self.write("tests/t.py", "assert answer\n")
        self.write("tests/new.py", "")  # a test file created after the red step is free
        code, out, _ = self.verify()
        self.assertEqual(code, 1, out)
        self.assertIn("test lock: tests/t.py changed since its red run (AC-001)", out)
        self.assertNotIn("test lock: tests/new.py", out)

    def test_a_recorded_test_change_re_red_at_base_passes(self):
        self.locked()
        self.write("tests/t.py", "assert answer == 42, 'the answer'\n")
        self.deviation("test-change tests/t.py What: a message on the assert. Why: the failure didn't say what.")
        base = re.search(r"^Base:\s*(\S+)", self.read_state(), re.M).group(1)
        code, out, rec = self.verify("red", "--at", base, "AC-001")
        self.assertEqual(code, 0, out)
        self.assertIn("AC-001", rec["red_at_base"])
        code, out, _ = self.verify()
        self.assertEqual(code, 0, out)
        self.assertIn("PASS", out)
        listed = subprocess.run(["git", "-C", self.root, "worktree", "list"], capture_output=True,
                                encoding="utf-8").stdout
        self.assertEqual(len(listed.strip().splitlines()), 1, listed)  # the temporary worktree is gone

    def test_a_test_changed_in_an_earlier_part_still_passes_when_the_next_part_starts(self):
        self.locked()
        self.write("tests/t.py", "assert answer == 42, 'the answer'\n")
        self.deviation("test-change tests/t.py What: a message. Why: clearer.")
        base = re.search(r"^Base:\s*(\S+)", self.read_state(), re.M).group(1)
        # Another part's work runs in this repo at the same time: its worktree is left alone
        import tempfile
        other = os.path.join(tempfile.mkdtemp(prefix="sdlc-red-at-"), "base")
        self.git("worktree", "add", "--detach", other, base)
        self.addCleanup(self.git, "worktree", "remove", "--force", other)
        old = time.time() - 600  # a long run started with a larger --timeout is still going
        os.utime(os.path.dirname(other), (old, old))
        self.assertEqual(self.verify("--timeout", "10", "red", "--at", base, "AC-001")[0], 0)
        self.assertTrue(os.path.isdir(other))
        # B2 starts from a later commit: the red run at the feature's Base still counts
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "B1")
        head = subprocess.run(["git", "-C", self.root, "rev-parse", "HEAD"], capture_output=True,
                              encoding="utf-8").stdout.strip()
        self.write(".sdlc/login/state.md", self.read_state().replace(
            "Current:", f"Slice: B2   Slice base: {head}   Slice gates: none\nCurrent:", 1))
        code, out, _ = self.verify()
        self.assertNotIn("test lock", out)

    def test_red_at_base_refuses_a_test_that_passes_there(self):
        self.locked()
        self.write("tests/t.py", "weak = True\n")
        self.deviation("test-change tests/t.py What: weakened. Why: to see it refused.")
        base = re.search(r"^Base:\s*(\S+)", self.read_state(), re.M).group(1)
        code, out, rec = self.verify("red", "--at", base, "AC-001")
        self.assertEqual(code, 1, out)
        self.assertIn("passes at", out)
        self.assertNotIn("red_at_base", rec)
        listed = subprocess.run(["git", "-C", self.root, "worktree", "list"], capture_output=True,
                                encoding="utf-8").stdout
        self.assertEqual(len(listed.strip().splitlines()), 1, listed)
        self.assertEqual(self.verify()[0], 1)

    def test_a_re_red_does_not_move_the_lock(self):
        self.locked()
        os.remove(self.path("done"))  # the code set aside, so a looser test still fails
        self.write("tests/t.py", "assert answer\n")
        self.assertEqual(self.verify("red", "AC-001")[0], 0)
        self.write("done", "")
        code, out, _ = self.verify()
        self.assertEqual(code, 1, out)
        self.assertIn("test lock: tests/t.py changed", out)

    def test_red_at_runs_only_at_the_features_base(self):
        self.locked()
        self.write("other.txt", "x")
        self.git("add", "other.txt")
        self.git("commit", "-q", "-m", "later")
        self.write("tests/t.py", "assert answer == 42, 'the answer'\n")
        self.deviation("test-change tests/t.py What: a message. Why: clearer.")
        code, out, rec = self.verify("red", "--at", "HEAD", "AC-001")
        self.assertEqual(code, 1, out)
        self.assertIn("isn't the feature's Base", out)
        p = subprocess.run([sys.executable, os.path.join(PLUGIN_ROOT, "scripts", "state.py"), "--root", self.root,
                            "lock", "login", "a`b.py", "0" * 64], capture_output=True, encoding="utf-8")
        self.assertEqual(p.returncode, 1, p.stdout)  # a file name that would break the state file's line

    def test_a_deleted_locked_test_fails_the_run(self):
        self.locked()
        os.remove(self.path("tests/t.py"))
        code, out, _ = self.verify()
        self.assertEqual(code, 1, out)
        self.assertIn("test lock: tests/t.py", out)


def load_tests(loader, tests, pattern):
    """Only the tests this file defines: the fixture classes it extends run in their own files."""
    suite = unittest.TestSuite()
    for cls in (TestLockTest,):
        for name in loader.getTestCaseNames(cls):
            if name in vars(cls):
                suite.addTest(cls(name))
    return suite


if __name__ == "__main__":
    unittest.main()
