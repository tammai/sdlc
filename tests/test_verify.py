"""scripts/verify.py: one command proves every acceptance criterion, records red runs and catches drift from the plan."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "verify.py")
STATE = "# Feature: login\nStatus: active\nProcess: 3\nCurrent: Stage 2 – Build\nBase: {base}\n"


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
        self.state = STATE.format(base=base)
        self.write(".sdlc/login/state.md", self.state)
        self.acs, self.rows = (), ()

    def git(self, *args):
        subprocess.run(["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t", *args], check=True)

    def change(self):
        """change.md, the human record: the criteria and the table naming each one's test."""
        table = "| AC | Test | Run |\n|---|---|---|\n" + "".join(
            f"| {ac} | {test} | {run if test == 'manual' else '`' + run + '`'} |\n" for ac, test, run in self.rows)
        self.write(".sdlc/login/change.md", "# Change\n\n## Acceptance criteria\n\n" +
                   "".join(f"- **{ac}** something observable\n" for ac in self.acs) +
                   "\n## Acceptance tests\n\n" + table)

    def spec(self, *acs):
        self.acs = acs
        self.change()

    def plan(self, rows, tasks=(), deviations=()):
        """The rows go in change.md; the tasks, surface and deviations in the state file, the agent's record."""
        self.rows = rows
        self.change()
        self.write(".sdlc/login/state.md", self.state + "\n## Tasks\n\n" + "\n".join(tasks) +
                   "\n\n## Public Surface\n\n- none\n\n## Gate log\n-\n\n## Deviations\n\n" + "\n".join(deviations) + "\n")

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

    def test_one_test_proving_several_acs_runs_once(self):
        self.spec("AC-001", "AC-002")
        count = "python3 -c \"open('runs.txt', 'a').write('x'); import os, sys; sys.exit(0 if os.path.exists('done') else 1)\""
        self.plan([("AC-001", "tests/t.py › flow", count), ("AC-002", "tests/t.py › flow", count)])
        self.write("tests/t.py", "")
        code, out, rec = self.verify("red", "AC-001", "AC-002")
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(rec["red"]), ["AC-001", "AC-002"])  # red is recorded for each AC it proves
        with open(self.path("runs.txt"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "x")

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

    def test_one_red_call_records_every_ac_or_none(self):
        self.spec("AC-001", "AC-002")
        fails = 'python3 -c "import sys; sys.exit(1)"'
        self.write("tests/t.py", "")
        self.plan([("AC-001", "tests/t.py › a", fails), ("AC-002", "tests/t.py › b", 'python3 -c "pass"')])
        code, out, rec = self.verify("red", "AC-001", "AC-002")
        self.assertEqual(code, 1)
        self.assertIn("AC-002: its test passes", out)
        self.assertEqual(rec.get("red", {}), {})  # AC-001 failed as it should, but the batch is all or nothing
        self.plan([("AC-001", "tests/t.py › a", fails), ("AC-002", "tests/t.py › b", fails)])
        code, out, rec = self.verify("red", "AC-001", "AC-002")
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(rec["red"]), ["AC-001", "AC-002"])

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

    def test_a_task_that_changes_only_markdown_is_not_drift(self):
        self.spec()
        self.plan([], tasks=["1. **Docs** — FR-001\n   - Files: `README.md`"])
        code, out, _ = self.verify()
        self.assertIn("drift: task 1", out)  # still drift while the README is untouched
        self.write("README.md", "usage\n")
        code, out, _ = self.verify()
        self.assertEqual(code, 0, out)

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
        # Writing the record (the review in change.md, a lesson) after the run isn't a code change: the run still counts
        self.write(".sdlc/login/change.md", "# Change\n\n## Review\n")
        self.write("docs/notes.md", "lesson\n")
        self.assertTrue(self.status()["reuse"])
        self.write("src/late.py", "z = 3\n")  # an edit after verify
        self.assertEqual(self.status()["reason"], "code changed since verify")
        # The tree Ship checks against Verified comes from here, so Ship needs no git call of its own;
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
        self.write(".sdlc/login/state.md", text.replace("Status: active", "Status: active\nProcess: 3\nTrack: S") +
                   'Repro: `tests/t.py` › cascade removes done | `python3 -c "import sys; sys.exit(1)"`\n')
        self.write("tests/t.py", "")
        self.write("src/fix.py", "x = 1\n")  # no plan, so no drift check
        code, out, _ = self.verify()
        self.assertEqual(code, 1)
        self.assertIn("AC-001: no red run recorded", out)
        code, out, _ = self.verify("red", "AC-001")
        self.assertEqual(code, 0, out)
        self.write(".sdlc/login/state.md", text.replace("Status: active", "Status: active\nProcess: 3\nTrack: S") +
                   'Repro: `tests/t.py` › cascade removes done | `python3 -c "pass"`\n')  # the fix makes it pass
        code, out, rec = self.verify()
        self.assertEqual(code, 0, out)

    def test_an_ac_without_a_row_fails(self):
        self.spec("AC-001", "AC-002")
        self.plan([("AC-001", "tests/t.py › ok", 'python3 -c "pass"')])
        code, out, _ = self.verify()
        self.assertEqual(code, 1)
        self.assertIn("AC-002: no row in ## Acceptance tests", out)


    def backlog(self, *rows):
        self.write(".sdlc/login/backlog.md", "# Backlog: login\n\n| ID | Slice | FRs | ACs | Deps | Size | Status |\n"
                   "|---|---|---|---|---|---|---|\n" + "".join(f"| {i} | part | — | {acs} | — | S | {st} |\n"
                                                              for i, acs, st in rows))

    def test_a_part_checks_only_the_acs_of_parts_already_started(self):
        # The part in progress can't have later parts' tests yet: their ACs and tasks wait, and nothing reuses the run
        self.spec("AC-001", "AC-002", "AC-003")
        self.plan([("AC-001", "tests/t.py › a", 'python3 -c "pass"'), ("AC-002", "tests/t2.py › b", 'python3 -c "pass"'),
                   ("AC-003", "tests/t2.py › c", 'python3 -c "pass"')],
                  tasks=["1. **A** — AC-001\n   - Files: `src/a.py`", "2. **B** — AC-002 AC-003\n   - Files: `src/b.py`"])
        self.write("tests/t.py", "")
        self.write("src/a.py", "x = 1\n")
        self.backlog(("B1", "1", "in progress"), ("B2", "AC-002–003", "todo"))
        self.verify()
        self.write_red("AC-001")
        code, out, rec = self.verify()
        self.assertEqual(code, 0, out)
        self.assertIn("not checked yet, later parts: AC-002 (B2), AC-003 (B2)", out)
        self.assertEqual(rec["last"]["skipped"], ["AC-002", "AC-003"])
        self.assertNotIn("task 2", out)
        st = self.status()
        self.assertFalse(st["reuse"])
        self.assertIn("later parts", st["reason"])
        self.backlog(("B1", "1", "done"), ("B2", "2-3", "todo"))  # no part in progress: everything is checked
        code, out, rec = self.verify()
        self.assertEqual(code, 1)
        self.assertIn("AC-002: tests/t2.py not found", out)
        self.assertIn("drift: task 2", out)
        self.assertEqual(rec["last"]["skipped"], [])

    def test_an_ac_a_started_part_also_owns_is_checked(self):
        self.spec("AC-001")
        self.plan([("AC-001", "tests/t.py › a", 'python3 -c "pass"')])
        self.write("tests/t.py", "")
        self.backlog(("B1", "1", "in progress"), ("B2", "1", "todo"))
        code, out, _ = self.verify()
        self.assertEqual(code, 1)
        self.assertIn("AC-001: no red run recorded", out)

    SPEC = "# Product\n\n## 4.1 Sign in\n\nFR-001 a user signs in.\n\n## 4.2 Sign out\n\nFR-002 a user signs out.\n"

    def traced(self, acs, out_of_scope="- nothing\n", spec=SPEC, tail=""):
        """A change file whose ACs cite docs/prd.md, over a spec with FR ids."""
        self.write("docs/prd.md", spec)
        self.write(".sdlc/login/change.md", "# Change\n\n## Acceptance criteria\n\n" + acs +
                   "\n## Out of scope\n\n" + out_of_scope + tail)

    def test_trace_passes_when_every_cited_ref_exists_and_every_fr_has_an_ac(self):
        self.traced("- **AC-001** docs/prd.md §FR-001: signs in\n- **AC-002** docs/prd.md §4.2, §FR-002: signs out\n")
        code, out, _ = self.verify("trace")
        self.assertEqual(code, 0, out)
        self.assertIn("traced", out)
        os.remove(self.path(".sdlc/login/state.md"))  # L's gate runs it before `state.py new`: --feature names it
        code, out, _ = self.verify("--feature", "login", "trace")
        self.assertEqual(code, 0, out)
        self.assertIn("traced", out)

    def test_trace_flags_a_cited_requirement_the_spec_does_not_have(self):
        self.traced("- **AC-001** docs/prd.md §FR-001: signs in\n- **AC-002** docs/prd.md §4.9: ghost\n"
                    "- **AC-003** docs/prd.md §FR-002: signs out\n")
        code, out, _ = self.verify("trace")
        self.assertEqual(code, 1)
        self.assertIn("AC-002: docs/prd.md §4.9 is not in the spec", out)

    def test_trace_flags_a_spec_requirement_no_ac_covers_unless_it_is_out_of_scope(self):
        self.traced("- **AC-001** docs/prd.md §FR-001: signs in\n")
        code, out, _ = self.verify("trace")
        self.assertEqual(code, 1)
        self.assertIn("FR-002 (docs/prd.md) has no AC and isn't in ## Out of scope", out)
        self.traced("- **AC-001** docs/prd.md §FR-001: signs in\n", out_of_scope="- FR-002: sign-out waits for v2\n")
        code, out, _ = self.verify("trace")
        self.assertEqual(code, 0, out)

    def test_trace_does_not_take_a_deeper_heading_for_the_one_cited(self):
        self.traced("- **AC-001** docs/prd.md §4: everything\n", spec="# P\n\n## 4.1 Sign in\n")
        code, out, _ = self.verify("trace")
        self.assertEqual(code, 1)
        self.assertIn("§4 is not in the spec", out)

    def test_trace_is_silent_without_spec_refs_and_stays_inside_the_repo(self):
        self.spec("AC-001")
        code, out, _ = self.verify("trace")
        self.assertEqual(code, 0, out)
        self.assertIn("no spec refs", out)
        self.traced("- **AC-001** ../outside.md §1: reaches out\n")
        code, out, _ = self.verify("trace")
        self.assertEqual(code, 1)
        self.assertIn("is not in the spec", out)

    def test_a_full_run_reports_trace_findings_as_notes_and_does_not_fail_on_them(self):
        self.traced("- **AC-001** docs/prd.md §FR-001: signs in\n",
                    tail="\n## Acceptance tests\n\n| AC | Test | Run |\n|---|---|---|\n"
                         "| AC-001 | tests/t.py › ok | `python3 -c \"pass\"` |\n")
        self.write(".sdlc/login/state.md", self.state + "\n## Tasks\n\n1. t `tests/t.py`\n\n## Public Surface\n\n"
                   "- none\n\n## Gate log\n-\n\n## Deviations\n\n")
        self.write("tests/t.py", "")
        self.assertEqual(self.verify()[0], 1)  # no red yet; this run also stamps the record with its feature
        self.write_red("AC-001")
        code, out, rec = self.verify()
        self.assertEqual(code, 0, out)
        self.assertIn("trace: FR-002 (docs/prd.md) has no AC", out)
        self.assertEqual(rec["last"]["trace"], ["FR-002 (docs/prd.md) has no AC and isn't in ## Out of scope"])


if __name__ == "__main__":
    unittest.main()
