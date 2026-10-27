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
Current: Stage 4 – Build

## Stages
- [x] 1 Define   — spec.md
- [ ] 4 Build
- [ ] 5 Prove    — test-report.md, review.md, security.md
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
        self.assertIn("Current: Stage 5 – Prove\n", text)
        self.assertIn("- [x] 4 Build", text)
        self.assertIn("Stage 4: pass — suite green\n\n## Open questions", text)
        with open(self.snapshot_path, encoding="utf-8") as f:
            snapshot = json.load(f)
        self.assertEqual((snapshot["current"], snapshot["phase"], snapshot["contract_version"]),
                         ({"stage": 5, "name": "Prove"}, "prove", 2))
        [event] = self.events()
        self.assertEqual((event["type"], event["from"], event["stage"], event["gate"]), ("stage_entered", 4, 5, "pass"))
        # The hooks read what it wrote: Stage 5 without a full test run blocks the turn's end
        _, out, _, _ = run_hook(FRESHNESS, {"hook_event_name": "Stop", "cwd": self.root}, self.root)
        self.assertEqual(out["decision"], "block")

    def test_a_feature_started_under_the_eleven_stages_moves_on_to_ship(self):
        old = STATE.split("Current:")[0] + """Current: Stage 6 – Review

## Stages
- [x] 1 Discover   — spec.md
- [x] 4 Implement
- [x] 5 Verify     — test-report.md
- [ ] 6 Review     — review.md
- [ ] 7 Security   — security.md
- [ ] 8 PR / CI    — PR:
- [ ] 9 Deploy     — release.md
- [ ] 10 Operate
- [ ] 11 Learn     — retro.md

## Gate log
-
"""
        self.write(".sdlc/state/login.md", old)
        self.assertEqual(self.state("advance", "login", "8", "--gate", "pass")[0], 0)
        with open(self.md, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Current: Stage 8 – Ship\n", text)
        self.assertIn("- [x] 6 Review", text)
        with open(self.snapshot_path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["phase"], "ship")

    def test_slice_gates_are_set_on_the_slice_line(self):
        self.write(".sdlc/state/login.md", STATE.replace("Current:", "Slice: B1   Slice base: abc1234   Slice gates: none\nCurrent:"))
        self.assertEqual(self.state("set", "login", "Slice gates", "plan, commit")[0], 0)
        with open(self.md, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Slice: B1   Slice base: abc1234   Slice gates: plan, commit\n", text)
        self.assertEqual(text.count("Slice gates:"), 1)

    def test_an_s_fix_records_its_intent_and_repro_in_state(self):
        # S writes no documents: Define puts the one-line intent and the repro test in the state file
        self.write(".sdlc/state/login.md", STATE)
        self.assertEqual(self.state("set", "login", "Intent", "remove --cascade skips done dependents")[0], 0)
        repro = "`test/p.test.js` › removes done | `node --test test/p.test.js`"
        self.assertEqual(self.state("set", "login", "Repro", repro)[0], 0)
        with open(self.md, encoding="utf-8") as f:
            self.assertIn(f"Repro: {repro}\n", f.read())

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
            self.assertIn("- [ ] 5 Prove", f.read())

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
