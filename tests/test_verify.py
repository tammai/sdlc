"""scripts/verify.py: one command proves every acceptance criterion, records red runs and catches drift from the plan."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "verify.py")
STATE = "# Feature: login\nStatus: active\nCurrent: Stage 4 – Build\nBase: {base}\n"


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
            return json.load(open(self.path(".sdlc/.work/verify.json"), encoding="utf-8"))
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
        self.plan([("AC-001", "tests/t.py › ok", 'python3 -c "pass"'),
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

    def test_drift_needs_a_deviation_with_what_why_and_effect(self):
        self.spec()  # no ACs: only the commands and the drift check run
        tasks = ["1. **Store** — FR-001\n   - Files: `src/store.py`"]
        self.plan([], tasks=tasks)
        self.write("src/store.py", "x = 1\n")
        self.write("src/cache.py", "y = 2\n")  # untracked, not in the plan
        code, out, _ = self.verify()
        self.assertEqual(code, 1)
        self.assertIn("drift: src/cache.py", out)
        self.plan([], tasks=tasks, deviations=["- `src/cache.py` (task 1) — What: helper · Why: reuse · Effect: none on ACs"])
        code, out, rec = self.verify()
        self.assertEqual(code, 0, out)
        self.assertEqual(rec["last"]["drift"][0]["covered"], True)

    def test_an_ac_without_a_row_fails(self):
        self.spec("AC-001", "AC-002")
        self.plan([("AC-001", "tests/t.py › ok", 'python3 -c "pass"')])
        code, out, _ = self.verify()
        self.assertEqual(code, 1)
        self.assertIn("AC-002: no row in ## Acceptance tests", out)


if __name__ == "__main__":
    unittest.main()
