"""scripts/backlog.py: the next ready slice is the first todo row whose dependencies are done."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "backlog.py")
BACKLOG = """# Backlog: login

| ID | Slice | FRs | ACs | Deps | Size | Status |
|---|---|---|---|---|---|---|
| B1 | Form | FR-01 | 1 | — | S | done abc1234 |
| B2 | Session | FR-02 | 2 | B1 | M | todo |
| B3 | Logout | FR-03 | 3 | B2 | S | todo |
"""


class BacklogTest(ProjectTestCase):
    def run_script(self, *args):
        p = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, encoding="utf-8")
        return p.returncode, json.loads(p.stdout)

    def test_next_is_the_first_todo_with_its_dependencies_done(self):
        path = self.write("backlog.md", BACKLOG)
        self.assertEqual(self.run_script("next", path), (0, {"next": "B2", "done": False}))

    def test_a_slice_with_an_open_dependency_is_refused(self):
        path = self.write("backlog.md", BACKLOG)
        code, out = self.run_script("check", path, "B3")
        self.assertEqual(code, 1)
        self.assertIn("B2", out["reason"])

    def test_an_escaped_pipe_in_a_title_stays_in_its_cell(self):
        # Markdown tables write a literal | as \|; splitting on it shifted Deps and Status, and B3 ran before B2
        path = self.write("backlog.md", BACKLOG.replace("| B2 | Session |", "| B2 | Session: native \\| subagent |"))
        self.assertEqual(self.run_script("next", path), (0, {"next": "B2", "done": False}))

    def test_a_bold_id_reads_as_its_plain_id(self):
        # `**B1**` was kept as written, so B2's dependency on B1 never counted as done and `next` stalled silently
        path = self.write("backlog.md", BACKLOG.replace("| B1 | Form |", "| **B1** | Form |"))
        self.assertEqual(self.run_script("next", path), (0, {"next": "B2", "done": False}))

    def test_a_slice_depending_on_a_bold_done_id_is_ready(self):
        path = self.write("backlog.md", BACKLOG.replace("| B1 | Form |", "| **B1** | Form |"))
        self.assertEqual(self.run_script("check", path, "B2"), (0, {"ok": True}))

    def test_a_file_without_a_backlog_table_is_an_error_not_an_empty_backlog(self):
        path = self.write("backlog.md", "# Backlog\n\nnothing here\n")
        code, out = self.run_script("next", path)
        self.assertEqual(code, 2)
        self.assertIn("no table", out["error"])


class AcIdsTest(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        self.addCleanup(sys.path.remove, os.path.join(PLUGIN_ROOT, "scripts"))
        import backlog
        self.ac_ids = backlog.ac_ids

    def test_digits_inside_words_are_not_ac_numbers(self):
        # AC_SPAN had no leading boundary: OAuth2 read as AC-002, B3 as AC-003
        self.assertEqual(self.ac_ids("AC-001 (OAuth2 login)"), ["AC-001"])
        self.assertEqual(self.ac_ids("AC-001, see B3"), ["AC-001"])

    def test_ac_tokens_numbers_and_ranges_still_count(self):
        self.assertEqual(self.ac_ids("1, 2"), ["AC-001", "AC-002"])
        self.assertEqual(self.ac_ids("AC-001 AC-002"), ["AC-001", "AC-002"])
        self.assertEqual(self.ac_ids("AC-001–003"), ["AC-001", "AC-002", "AC-003"])
        self.assertEqual(self.ac_ids("2-3, AC-005 – AC-006"), ["AC-002", "AC-003", "AC-005", "AC-006"])


if __name__ == "__main__":
    unittest.main()
