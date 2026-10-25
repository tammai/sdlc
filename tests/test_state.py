"""scripts/state.py: one call changes state.md and the control contract together; the hooks still read state.md."""
import json
import os
import subprocess
import sys
import unittest

from helpers import HOOKS, PLUGIN_ROOT, ProjectTestCase, run_hook

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "state.py")
FRESHNESS = ["python3", os.path.join(HOOKS, "verify_freshness.py")]
STATE = """# login
Status: active
Track: M
Risk: low
Flow: lite
Base: abc1234
Current: Stage 4 – Implement

## Stages
- [x] 1 Discover   — spec.md
- [ ] 4 Implement
- [ ] 5 Verify     — test-report.md

## Gate log
- 2026-10-25 Stage 1: pass — spec approved

## Open questions
-
"""


class StateTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.md = self.write(".sdlc/state/login.md", STATE)
        self.contract = self.path(".sdlc/.work/contract/login")

    def state(self, *args):
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, *args], capture_output=True,
                           encoding="utf-8", errors="replace")
        return p.returncode, json.loads(p.stdout)

    def events(self):
        path = os.path.join(self.contract, "events.jsonl")
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return [json.loads(l) for l in f]

    def test_advancing_a_stage_updates_state_md_the_snapshot_and_one_event(self):
        code, _ = self.state("advance", "login", "5", "--gate", "pass", "--note", "suite green")
        self.assertEqual(code, 0)
        with open(self.md, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Current: Stage 5 – Verify\n", text)
        self.assertIn("- [x] 4 Implement", text)
        self.assertIn("Stage 4: pass — suite green\n\n## Open questions", text)
        with open(os.path.join(self.contract, "state.json"), encoding="utf-8") as f:
            snapshot = json.load(f)
        self.assertEqual(snapshot["current"], {"stage": 5, "name": "Verify"})
        self.assertIn("contract_version", snapshot)
        [event] = self.events()
        self.assertEqual((event["type"], event["from"], event["stage"], event["gate"]), ("stage_entered", 4, 5, "pass"))
        # The hooks read what it wrote: Stage 5 without a full test run blocks the turn's end
        _, out, _, _ = run_hook(FRESHNESS, {"hook_event_name": "Stop", "cwd": self.root}, self.root)
        self.assertEqual(out["decision"], "block")

    def test_slice_gates_are_set_on_the_slice_line(self):
        self.write(".sdlc/state/login.md", STATE.replace("Current:", "Slice: B1   Slice base: abc1234   Slice gates: none\nCurrent:"))
        self.assertEqual(self.state("set", "login", "Slice gates", "plan, commit")[0], 0)
        with open(self.md, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Slice: B1   Slice base: abc1234   Slice gates: plan, commit\n", text)
        self.assertEqual(text.count("Slice gates:"), 1)

    def test_a_malformed_state_file_is_reported_not_mirrored(self):
        self.write(".sdlc/state/login.md", STATE.replace("Current: Stage 4 – Implement\n", ""))
        code, out = self.state("advance", "login", "5")
        self.assertEqual(code, 1)
        self.assertIn("Current:", out["error"])
        self.assertFalse(os.path.exists(self.contract))


if __name__ == "__main__":
    unittest.main()
