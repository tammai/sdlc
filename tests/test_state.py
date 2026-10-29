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
Process: 2
Base: abc1234
Current: Stage 4 – Build

## Stages
- [x] 1 Define   — intent.md, spec.md, plan.md
- [ ] 4 Build
- [ ] 5 Review   — review.md
- [ ] 8 Ship     — PR:

## Gate log
- 2026-10-25 Stage 1: pass — spec approved

## Open questions
-
"""


class StateTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.md = self.write(".sdlc/state/login.md", STATE)
        self.snapshot_path = self.path(".sdlc/state/login.json")  # beside state.md, git-ignored
        self.events_path = self.path(".sdlc/state/login.events.jsonl")

    def state(self, *args):
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, *args], capture_output=True,
                           encoding="utf-8", errors="replace")
        return p.returncode, json.loads(p.stdout)

    def events(self):
        path = self.events_path
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as f:
            return [json.loads(l) for l in f]

    def test_advancing_a_stage_updates_state_md_the_snapshot_and_one_event(self):
        code, _ = self.state("advance", "login", "5", "--gate", "pass", "--note", "suite green")
        self.assertEqual(code, 0)
        with open(self.md, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Current: Stage 5 – Review\n", text)
        self.assertIn("- [x] 4 Build", text)
        self.assertIn("Stage 4: pass — suite green\n\n## Open questions", text)
        with open(self.snapshot_path, encoding="utf-8") as f:
            snapshot = json.load(f)
        self.assertEqual((snapshot["current"], snapshot["phase"], snapshot["contract_version"]),
                         ({"stage": 5, "name": "Review"}, "review", 2))
        [event] = self.events()
        self.assertEqual((event["type"], event["from"], event["stage"], event["gate"]), ("stage_entered", 4, 5, "pass"))
        # The hooks read what it wrote: Stage 5 without a full test run blocks the turn's end
        _, out, _, _ = run_hook(FRESHNESS, {"hook_event_name": "Stop", "cwd": self.root}, self.root)
        self.assertEqual(out["decision"], "block")

    def test_new_writes_the_state_file_from_defines_answers(self):
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc", "commands": {"test": "npm test"}}))
        code, out = self.state("new", "2026-10-30-m-prio", "--track", "M", "--risk", "high", "--risk-why", "public API",
                               "--footprint", "3", "--task", "Priority command | AC-001 AC-002 | bin/planner.js, README.md",
                               "--surface", "command `priority <id> <level>` — AC-002")
        self.assertEqual(code, 0, out)
        with open(self.path(".sdlc/state/2026-10-30-m-prio.md"), encoding="utf-8") as f:
            text = f.read()
        for line in ("Process: 2\n", "Change: docs/sdlc/changes/2026-10-30-m-prio.md", "Risk: high   (public API)\n",
                     "Commands: test: `npm test`\n", "Current: Stage 1 – Define\n",
                     "1. **Priority command** — AC-001 AC-002\n   - Files: `bin/planner.js`, `README.md`\n",
                     "## Public Surface\n- command `priority <id> <level>` — AC-002\n"):
            self.assertIn(line, text)
        self.assertEqual(self.state("advance", "2026-10-30-m-prio", "4", "--gate", "pass")[0], 0)  # the flow goes on
        # A name already in use is refused, so a resumed feature's record is never overwritten
        code, out = self.state("new", "login", "--track", "S", "--risk", "low", "--task", "x | AC-001 | a.js")
        self.assertEqual(code, 1)
        self.assertIn("already has a state file", out["error"])

    def test_a_2_0_feature_moves_through_four_phases(self):
        for stage, name in (("5", "Review"), ("8", "Ship")):
            self.assertEqual(self.state("advance", "login", stage, "--gate", "pass")[0], 0)
            with open(self.md, encoding="utf-8") as f:
                self.assertIn(f"Current: Stage {stage} – {name}\n", f.read())
        code, out = self.state("advance", "login", "6")
        self.assertEqual(code, 1)
        self.assertIn("no Stage 6", out["error"])

    def test_a_phase_end_records_the_verified_tree_and_the_move_in_one_call(self):
        code, out = self.state("advance", "login", "5", "--gate", "pass", "--verified", "abc1234", "f00d")
        self.assertEqual(code, 0, out)
        with open(self.md, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Verified: abc1234 tree f00d\n", text)
        self.assertIn("Current: Stage 5 – Review\n", text)
        self.assertEqual(self.state("advance", "login", "5", "--verified", "abc1234")[0], 2)  # a tree is required

    def test_a_1x_feature_is_refused_with_how_to_finish_it(self):
        self.write(".sdlc/state/login.md", STATE.replace("Process: 2\n", ""))
        code, out = self.state("advance", "login", "5")
        self.assertEqual(code, 1)
        self.assertIn("sdlc 1.8.1", out["error"])

    def test_slice_gates_are_set_on_the_slice_line(self):
        self.write(".sdlc/state/login.md", STATE.replace("Current:", "Slice: B1   Slice base: abc1234   Slice gates: none\nCurrent:"))
        self.assertEqual(self.state("set", "login", "Slice gates", "plan, commit")[0], 0)
        with open(self.md, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Slice: B1   Slice base: abc1234   Slice gates: plan, commit\n", text)
        self.assertEqual(text.count("Slice gates:"), 1)

    def test_a_deviation_goes_under_deviations(self):
        # The sdlc-invariants CI check looks for a baseline change named under ## Deviations, not the Gate log
        self.write(".sdlc/state/login.md", STATE.replace("## Open questions", "## Deviations\n-\n\n## Open questions"))
        self.assertEqual(self.state("deviation", "login", "baselined t › old: flaky upstream")[0], 0)
        with open(self.md, encoding="utf-8") as f:
            self.assertIn("## Deviations\n- 2", f.read())
        self.assertEqual(self.events()[-1]["type"], "deviation_logged")

    def test_advancing_to_the_current_stage_is_refused(self):
        # A second advance into the same stage ticked it as passed before its gate ran
        self.state("advance", "login", "5", "--gate", "pass")
        code, out = self.state("advance", "login", "5", "--gate", "pass")
        self.assertEqual(code, 1)
        with open(self.md, encoding="utf-8") as f:
            self.assertIn("- [ ] 5 Review", f.read())

    def test_an_old_layout_feature_keeps_its_contract_where_the_ignore_patterns_cover_it(self):
        os.remove(self.md)
        self.write(".sdlc/legacy/state.md", STATE)
        self.assertEqual(self.state("sync", "legacy")[0], 0)
        self.assertTrue(os.path.exists(self.path(".sdlc/state/legacy.json")))
        self.assertFalse(os.path.exists(self.path(".sdlc/legacy/state.json")))

    def test_a_malformed_state_file_is_reported_not_mirrored(self):
        self.write(".sdlc/state/login.md", STATE.replace("Current: Stage 4 – Build\n", ""))
        code, out = self.state("advance", "login", "5")
        self.assertEqual(code, 1)
        self.assertIn("Current:", out["error"])
        self.assertFalse(os.path.exists(self.snapshot_path) or os.path.exists(self.events_path))


if __name__ == "__main__":
    unittest.main()
