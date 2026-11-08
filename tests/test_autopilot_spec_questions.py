"""Autopilot with spec questions (spec 03 S10): a blocked part waits, the others run (ported from 3.5.0-rc.3,
4e7a911)."""
import json
import os
import unittest

import test_autopilot
from test_autopilot import BACKLOG


class SpecQuestionAutopilotTest(test_autopilot.AutopilotTest):
    def test_a_spec_question_blocks_only_its_part(self):
        self.write("docs/sdlc/intents/login/backlog.md", BACKLOG.replace(
            "| B1 | Form | FR-01 | 1 | — | S | todo |", "| B1 | Form | FR-01 | 1 | — | S | blocked: spec question SQ-0001 on F-APP-01.AC1 |")
            .replace("| 2 | B1 |", "| 2 | — |"))
        out, calls = self.autopilot("done")
        self.assertEqual(calls, ["/sdlc:start B2 --autopilot"])
        self.assertIn("waiting on spec questions", out["stopped"])

    def test_a_state_file_it_cannot_read_stops_with_a_reason_not_a_traceback(self):
        self.write(".sdlc/state/login.md", "# login\nStatus: active\nProcess: 3\nCurrent: Stage 3 – Review\n\n"
                   "## Spec questions\n- SQ-0001 F-APP-01.AC1 sha256:" + "0" * 64 + " B1\n")
        self.write(".sdlc/.work/spec-questions/login-SQ-0001.json", "{}")
        self.write(".sdlc/.work/spec-questions/resolved", "")  # a file where the folder goes: the move fails
        self.write(".sdlc/config.json", "{\"spec_lock\": \"lock.json\"}")
        self.write("lock.json", json.dumps({"spec": ".", "criteria": [{"id": "F-APP-01.AC1", "file": "f.md",
                                                                       "text_sha256": "1" * 64}]}))
        out, calls = self.autopilot("done")
        self.assertEqual(calls, [])
        self.assertIn("spec questions not checked", out["stopped"])

    def test_a_leftover_question_file_is_filed_away_without_open_questions(self):
        self.write(".sdlc/.work/spec-questions/login-SQ-0003.json", "{}")  # a run killed before its state
        self.autopilot("done")
        self.assertFalse(os.path.exists(self.path(".sdlc/.work/spec-questions/login-SQ-0003.json")))
        self.assertTrue(os.path.exists(self.path(".sdlc/.work/spec-questions/resolved/login-SQ-0003.json")))


def load_tests(loader, tests, pattern):
    """Only the tests this file defines: the fixture class it extends runs in its own file."""
    return unittest.TestSuite(SpecQuestionAutopilotTest(n) for n in loader.getTestCaseNames(SpecQuestionAutopilotTest) if n in vars(SpecQuestionAutopilotTest))


if __name__ == "__main__":
    unittest.main()
