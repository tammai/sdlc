"""Spec-backed changes and spec questions (spec 03 S2, S10): the edges the first review found."""
import json
import os
import subprocess
import sys
import unittest

from test_spec_backed import BACKLOG, LINES, SCRIPTS, SpecBackedTest


class SpecBackedEdgesTest(SpecBackedTest):
    def part(self, slice_id, backlog=BACKLOG):
        self.state()
        self.write(".sdlc/login/backlog.md", backlog)
        state = self.read(".sdlc/login/state.md").replace(
            "Current:", f"Slice: {slice_id}   Slice base: abc1234   Slice gates: none\nCurrent:", 1)
        self.write(".sdlc/login/state.md", state)

    def ask(self, cid, text="Which?", expect=0):
        code, out = self.run_script("state.py", "question", "login", cid, text)
        self.assertEqual(code, expect, out)
        return out

    def test_a_question_blocks_only_a_running_part_and_two_questions_both_hold_it(self):
        self.part("B1")  # B1 is done: no running part, so the question is a blocker, not a status change
        self.ask("F-APP-01.AC1")
        self.assertIn("| B1 | Sign in | AC-001 | — | S | done |", self.read(".sdlc/login/backlog.md"))
        self.assertIn("spec question SQ-0001 on F-APP-01.AC1", self.read(".sdlc/login/state.md"))
        import shutil
        shutil.rmtree(self.path(".sdlc/.work/spec-questions"))  # a fresh feature state: its questions go too
        self.part("B2")
        self.ask("F-APP-01.AC1")
        self.ask("F-APP-01.AC2")
        row = next(l for l in self.read(".sdlc/login/backlog.md").splitlines() if l.startswith("| B2"))
        self.assertIn("SQ-0001", row)
        self.assertIn("SQ-0002", row)
        self.amend()  # only AC1 is answered
        out = json.loads(self.run_script("state.py", "questions", "login")[1])
        self.assertEqual(out["resolved"], ["SQ-0001"])
        row = next(l for l in self.read(".sdlc/login/backlog.md").splitlines() if l.startswith("| B2"))
        self.assertIn("blocked: spec question SQ-0002 on F-APP-01.AC2", row)
        self.assertNotIn("SQ-0001", row)

    def test_a_question_file_left_by_a_kill_is_filed_away(self):
        self.part("B2")
        self.write(".sdlc/.work/spec-questions/login-SQ-0007.json", "{}")  # written, then the state write never ran
        out = json.loads(self.run_script("state.py", "questions", "login")[1])
        self.assertEqual(out["open"], [])
        self.assertFalse(os.path.exists(self.path(".sdlc/.work/spec-questions/login-SQ-0007.json")))
        self.assertTrue(os.path.exists(self.path(".sdlc/.work/spec-questions/resolved/login-SQ-0007.json")))

    def test_out_of_scope_needs_a_reason_on_the_ids_own_line(self):
        self.state(header="Track: L\nRisk: low\nSlice criteria: F-APP-01.AC1 F-APP-01.AC2\n")
        self.change(["- **AC-001** → F-APP-01.AC1"], out_of_scope="- F-APP-01.AC2\n- Reading build-plan.md")
        self.run_script("state.py", "cite", "login", "F-APP-01.AC1")
        self.built(["AC-001"])
        code, out = self.verify()
        self.assertEqual(code, 1, out)
        self.assertIn("F-APP-01.AC2 is not covered", out)

    def test_out_of_scope_reads_a_reason_before_the_id_and_not_another_id(self):
        self.state(header="Track: L\nRisk: low\nSlice criteria: F-APP-01.AC1 F-APP-01.AC2\n")
        self.run_script("state.py", "cite", "login", "F-APP-01.AC1")
        self.change(["- **AC-001** → F-APP-01.AC1"], out_of_scope="- Later slice: F-APP-01.AC2")
        self.built(["AC-001"])
        code, out = self.verify()
        self.assertEqual(code, 0, out)
        self.change(["- **AC-001** → F-APP-01.AC1"], out_of_scope="- F-APP-01.AC2, F-APP-01.AC3")
        code, out = self.verify()
        self.assertEqual(code, 1, out)
        self.assertIn("F-APP-01.AC2 is not covered", out)

    def test_a_block_whose_question_never_reached_the_state_is_cleared(self):
        self.part("B2", backlog=BACKLOG.replace("in progress", "blocked: spec question SQ-0009 on F-APP-01.AC1"))
        self.run_script("state.py", "questions", "login")
        self.assertIn("| B2 | Sign out | AC-002 | — | S | todo |", self.read(".sdlc/login/backlog.md"))

    def test_a_block_without_a_colon_doesnt_stop_the_check(self):
        self.part("B2", backlog=BACKLOG.replace("in progress", "Blocked - waiting"))
        code, out = self.run_script("state.py", "questions", "login")
        self.assertEqual(code, 0, out)
        self.assertIn("| B2 | Sign out | AC-002 | — | S | Blocked - waiting |", self.read(".sdlc/login/backlog.md"))

    def test_a_numbered_or_ticked_marker_is_no_reason(self):
        self.state(header="Track: L\nRisk: low\nSlice criteria: F-APP-01.AC1 F-APP-01.AC2\n")
        self.run_script("state.py", "cite", "login", "F-APP-01.AC1")
        self.built_once = False
        for line in ("1. F-APP-01.AC2", "- [x] F-APP-01.AC2"):
            with self.subTest(line=line):
                self.change(["- **AC-001** → F-APP-01.AC1"], out_of_scope=line)
                if not self.built_once:
                    self.built(["AC-001"])
                    self.built_once = True
                code, out = self.verify()
                self.assertEqual(code, 1, out)
                self.assertIn("F-APP-01.AC2 is not covered", out)

    def test_a_hand_written_block_keeps_its_reason(self):
        self.part("B2", backlog=BACKLOG.replace("in progress", "Blocked: waiting on the design"))
        self.ask("F-APP-01.AC1")
        self.assertIn("Blocked: waiting on the design; spec question SQ-0001 on F-APP-01.AC1",
                      self.read(".sdlc/login/backlog.md"))

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root writes through read-only permissions")
    def test_a_question_whose_state_write_fails_leaves_no_finding(self):
        import stat
        self.state()  # no running part: the state file is the first thing written after the finding
        target = self.path(".sdlc/login/state.md") if os.name == "nt" else self.path(".sdlc/login")
        mode = os.stat(target).st_mode
        os.chmod(target, stat.S_IREAD | (stat.S_IEXEC if os.name != "nt" else 0))
        try:
            code, out = self.run_script("state.py", "question", "login", "F-APP-01.AC1", "Which?")
        finally:
            os.chmod(target, mode)
        self.assertEqual(code, 1, out)
        self.assertFalse(os.path.exists(self.path(".sdlc/.work/spec-questions/login-SQ-0001.json")))

    def test_a_rejected_lock_is_named_not_taken_for_a_missing_id(self):
        self.state()
        self.write("docs/specs/app/criteria.lock.json", "not json")
        for args in (("cite", "login", "F-APP-01.AC1"), ("question", "login", "F-APP-01.AC1", "Which?")):
            with self.subTest(cmd=args[0]):
                code, out = self.run_script("state.py", *args)
                self.assertEqual(code, 1, out)
                self.assertIn("isn't a criteria lock", out)

    def test_a_lock_that_is_not_a_lock_or_leaves_the_repo_is_not_run(self):
        self.state()
        self.change(["- **AC-001** → F-APP-01.AC1"])
        for lock in ("not json", json.dumps({"spec": "docs/specs/app", "criteria": [{"id": "F-APP-01.AC1"}]}),
                     json.dumps({"spec": "../outside", "criteria": [{"id": "F-APP-01.AC1", "file": "f.md",
                                                                     "text_sha256": "0" * 64}]})):
            with self.subTest(lock=lock[:20]):
                self.write("docs/specs/app/criteria.lock.json", lock)
                code, out = self.verify("trace")
                self.assertEqual(code, 1, out)
                self.assertIn("isn't a criteria lock", out)
                self.assertNotIn("Traceback", out)

    def test_a_cited_criterion_missing_from_its_story_file_is_a_finding(self):
        self.state()
        self.change(["- **AC-001** → F-APP-01.AC1"])
        self.run_script("state.py", "cite", "login", "F-APP-01.AC1")
        self.write("docs/specs/app/features/F-APP-01.md", "# F-APP-01\n\n## Acceptance criteria\n\n" + LINES["F-APP-01.AC2"] + "\n")
        code, out = self.verify("trace")
        self.assertEqual(code, 1, out)
        self.assertIn("F-APP-01.AC1: its line isn't in features/F-APP-01.md", out)

    def test_malformed_ids_and_an_empty_question_are_refused(self):
        code, out = self.run_script("state.py", "new", "2026-11-08-m-x", "--track", "M", "--risk", "low",
                                    "--task", "t | AC-001 | a.py", "--criteria", "F-APP-01.AC1", "AC1")
        self.assertEqual(code, 1, out)
        self.part("B2")
        self.ask("F-APP-01.AC1", text="  ", expect=1)

    def test_brief_shows_a_citation_wrapped_onto_a_second_line(self):
        self.state()
        self.write(".sdlc/login/change.md", "# Change\n\n## Acceptance criteria\n\n- **AC-001** → F-APP-01.AC1,\n"
                                            "  F-APP-01.AC2\n")
        code, out = self.run_script("brief.py", "login")
        self.assertEqual(code, 0, out)
        self.assertIn('then "Bye" is shown.', out)


def load_tests(loader, tests, pattern):
    """Only this file's tests: the fixture class it extends has its own file."""
    names = [n for n in loader.getTestCaseNames(SpecBackedEdgesTest) if n in SpecBackedEdgesTest.__dict__]
    return unittest.TestSuite(SpecBackedEdgesTest(n) for n in names)


if __name__ == "__main__":
    unittest.main()
