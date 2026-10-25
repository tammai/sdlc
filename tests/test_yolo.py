"""scripts/yolo.py: one fresh claude session per ready slice, then feature close; stops instead of looping or
accepting a notice the user hasn't seen."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "yolo.py")
BACKLOG = """| ID | Slice | FRs | ACs | Deps | Size | Status |
|---|---|---|---|---|---|---|
| B1 | Form | FR-01 | 1 | — | S | todo |
| B2 | Session | FR-02 | 2 | B1 | M | todo |
"""
# Stands in for the claude CLI: logs its prompt and, in "done" mode, marks the slice it was given done
STUB = r'''import os, re, sys
prompt = sys.argv[sys.argv.index("-p") + 1]
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as f:
    f.write(prompt + "\n")
m = re.search(r"B\d+", prompt)
if m and os.environ.get("STUB_MODE", "").startswith("done"):
    path = os.environ["STUB_BACKLOG"]
    text = open(path, encoding="utf-8").read()
    text = re.sub(rf"(?m)^(\| {m.group(0)} \|.*\| )todo( \|)$", r"\1done abc1234\2", text)
    open(path, "w", encoding="utf-8").write(text)
if not m and os.environ.get("STUB_MODE") == "done":  # feature close reaches its Stage 8 question
    with open(os.environ["STUB_STATE"], "a", encoding="utf-8") as f:
        f.write("Current: Stage 8 – PR / CI\n")
'''


class YoloTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.state = self.write(".sdlc/state/login.md", "# login\nStatus: active\nCurrent: Stage 5 – Verify\n")
        self.backlog = self.write("docs/sdlc/intents/login/backlog.md", BACKLOG)
        self.log = self.path("calls.log")
        stub = self.write("bin/stub.py", STUB)
        if os.name == "nt":
            self.write("bin/claude.cmd", f'@"{sys.executable}" "{stub}" %*\n')
        else:
            self.write("bin/claude", f'#!/bin/sh\nexec "{sys.executable}" "{stub}" "$@"\n')
            os.chmod(self.path("bin/claude"), 0o755)

    def yolo(self, mode):
        env = dict(os.environ, PATH=self.path("bin") + os.pathsep + os.environ["PATH"], STUB_LOG=self.log,
                   STUB_MODE=mode, STUB_BACKLOG=self.backlog, STUB_STATE=self.state)
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, "login"], capture_output=True,
                           encoding="utf-8", env=env)
        calls = open(self.log, encoding="utf-8").read().splitlines() if os.path.exists(self.log) else []
        return json.loads(p.stdout), calls

    def test_runs_each_ready_slice_then_feature_close_once(self):
        out, calls = self.yolo("done")
        self.assertEqual(calls, ["/sdlc:start B1 --yolo", "/sdlc:start B2 --yolo", "/sdlc:start --yolo"])
        self.assertIn("feature close ran", out["stopped"])

    def test_a_failed_feature_close_is_not_reported_as_done(self):
        out, calls = self.yolo("done-then-fail")
        self.assertEqual(calls[-1], "/sdlc:start --yolo")
        self.assertIn("feature close stopped at Stage 5", out["stopped"])

    def test_a_run_that_leaves_its_slice_unchanged_stops(self):
        out, calls = self.yolo("idle")
        self.assertEqual(calls, ["/sdlc:start B1 --yolo"])
        self.assertIn("B1 is still todo", out["stopped"])

    def test_a_slice_id_that_isnt_b_and_a_number_never_reaches_claude(self):
        # The ID becomes part of a command line (a .cmd shim on Windows), and backlog.md is hand-edited text
        self.write("docs/sdlc/intents/login/backlog.md", BACKLOG.replace("| B1 |", "| B1 & calc |", 1))
        out, calls = self.yolo("done")
        self.assertEqual(calls, [])
        self.assertIn("B1 & CALC", out["stopped"])

    def test_an_open_trust_anchor_notice_stops_before_any_run(self):
        self.write(".sdlc/.work/trust-anchor.json", json.dumps({"login": {"notices": ["Risk: high → low"]}}))
        out, calls = self.yolo("done")
        self.assertEqual(calls, [])
        self.assertIn("Risk: high", out["stopped"])


if __name__ == "__main__":
    unittest.main()
