"""hooks/trust_anchor.py: changes to what verification trusts are shown to the user, not made silently."""
import json
import os
import subprocess
import unittest
from datetime import datetime, timezone

from helpers import HOOKS, ProjectTestCase, run_hook

HOOK = ["python3", os.path.join(HOOKS, "trust_anchor.py")]
FRESHNESS = ["python3", os.path.join(HOOKS, "verify_freshness.py")]
STATE = "# login\nStatus: active\nTrack: {track}\nRisk: {risk}\nTop model: opus\nBase: {base}\nCurrent: Stage {stage}\n"
BASELINE = "# Known failures baseline\n\n## Failing tests\n\n| Package | Test | Failure | Since |\n|---|---|---|---|\n{rows}\n## Lint\n"


class TrustAnchorTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.git = ["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t"]
        self.write(".gitignore", ".sdlc/.work/\n")
        self.write("src/login.ts", "export const a = 1\n")
        self.write(".sdlc/baseline.md", BASELINE.format(rows="| api | t › old | boom | abc |\n"))
        subprocess.run(self.git + ["init", "-q"], check=True)
        subprocess.run(self.git + ["add", "-A"], check=True)
        subprocess.run(self.git + ["commit", "-q", "-m", "init"], check=True)
        self.base = subprocess.run(self.git + ["rev-parse", "--short", "HEAD"], capture_output=True,
                                   encoding="utf-8").stdout.strip()

    def state(self, stage=4, risk="high", flow=None, track="M"):
        self.write(".sdlc/login/state.md",
                   STATE.format(track=track, risk=risk, base=self.base, stage=stage) + (f"Flow: {flow}\n" if flow else ""))

    def full_run(self):
        run_hook(FRESHNESS, {"hook_event_name": "PostToolUse", "cwd": self.root, "tool_name": "Bash",
                             "tool_input": {"command": "npm test"}, "tool_response": {}}, self.root)

    def stop(self, hook=HOOK, active=False):
        code, out, raw, err = run_hook(hook, {"hook_event_name": "Stop", "cwd": self.root, "stop_hook_active": active},
                                       self.root)
        self.assertEqual(code, 0, err)
        return out

    def prompt(self):
        run_hook(HOOK, {"hook_event_name": "UserPromptSubmit", "cwd": self.root, "prompt": "ok"}, self.root)

    def test_lowering_risk_reaches_the_user_once_and_a_prompt_accepts_it(self):
        self.state(risk="high")
        self.assertIsNone(self.stop())
        self.state(risk="low")
        out = self.stop()
        self.assertEqual(out["decision"], "block")
        self.assertIn("Risk: high → low", out["systemMessage"])
        self.assertNotIn("decision", self.stop(active=True) or {})  # no loop: a shown notice doesn't block again
        self.prompt()
        self.assertIsNone(self.stop())

    def test_switching_to_the_lite_flow_is_a_notice(self):
        # Lite drops the top-tier review, so moving a full-flow feature onto it must reach the user
        self.state(risk="low", flow="full")
        self.stop()
        self.state(risk="low", flow="lite")
        self.assertIn("Flow: full → lite", self.stop()["systemMessage"])

    def test_a_stricter_flow_or_risk_needs_no_second_word_but_moving_back_does(self):
        # The user approved the switch to the full flow already: shown, but blocking would ask them again
        self.state(risk="low", flow="lite")
        self.stop()
        self.state(risk="high", flow="full")
        out = self.stop()
        self.assertNotIn("decision", out)
        self.assertIn("Flow: lite → full", out["systemMessage"])
        self.state(risk="high", flow="lite")
        self.assertIn("Flow: full → lite", self.stop()["systemMessage"])

    def test_a_backlog_feature_leaving_the_lite_flow_still_blocks(self):
        # Slices must stay on Lite, and an autopilot session has no one to read a non-blocking message
        self.write(".sdlc/login/backlog.md", "| ID | Status |\n|---|---|\n| B1 | todo |\n")
        self.state(risk="low", flow="lite")
        self.stop()
        self.state(risk="low", flow="full")
        self.assertEqual(self.stop()["decision"], "block")

    def test_removing_an_active_features_state_is_a_notice(self):
        self.state()
        self.stop()
        os.remove(self.path(".sdlc/login/state.md"))
        self.assertIn("state.md was removed while active", self.stop()["systemMessage"])

    def test_a_new_baseline_failure_is_a_notice(self):
        self.state()
        self.stop()
        self.write(".sdlc/baseline.md", BASELINE.format(rows="| api | t › old | boom | abc |\n| api | t › new | x | def |\n"))
        self.assertIn("didn't at Base: api | t › new", self.stop()["systemMessage"])

    def test_leaving_stage_5_with_code_changed_since_the_last_full_run(self):
        self.state(stage=5)
        self.stop()
        run_hook(FRESHNESS, {"hook_event_name": "PostToolUse", "cwd": self.root, "tool_name": "Bash",
                             "tool_input": {"command": "npm test"}, "tool_response": {}}, self.root)
        self.write("src/login.ts", "export const a = 2\n")  # a shell edit, then straight on to Stage 6
        self.state(stage=6)
        out = self.stop()
        self.assertIn("left Stage 5", out["systemMessage"])
        self.assertIn("src/login.ts", out["systemMessage"])


    def test_an_s_fix_proven_by_a_fresh_full_run_passes_stage_5_without_a_verifier(self):
        self.state(stage=4, risk="low", track="S")
        self.stop()
        self.write("src/login.ts", "export const a = 2\n")  # the fix, then the full suite in the session
        self.state(stage=5, risk="low", track="S")
        self.full_run()
        self.state(stage=8, risk="low", track="S")
        self.assertIsNone(self.stop())
        self.state(stage=4, risk="low", track="S")  # a second fix, edited after its last full run
        self.stop()
        self.state(stage=5, risk="low", track="S")
        self.full_run()
        self.write("src/login.ts", "export const a = 3\n")
        self.state(stage=8, risk="low", track="S")
        self.assertIn("without Stage 5", self.stop()["systemMessage"])

    def dispatch(self, agent):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(self.path(".sdlc/.work/dispatches.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"time": now, "agent": agent, "stages": ["Stage 5"], "denied": False}) + "\n")

    def test_an_ac_checker_round_on_a_passing_verify_passes_stage_5(self):
        self.state(stage=4, risk="low")
        self.stop()
        self.write("src/login.ts", "export const a = 2\n")
        self.state(stage=5, risk="low")
        self.full_run()
        self.state(stage=8, risk="low")
        self.assertIn("without Stage 5", self.stop()["systemMessage"])  # a passing suite alone isn't Prove on M
        self.prompt()
        self.state(stage=4, risk="low")
        self.stop()
        self.write("src/login.ts", "export const a = 3\n")
        self.state(stage=5, risk="low")
        self.full_run()
        self.dispatch("sdlc:ac-checker")
        self.state(stage=8, risk="low")
        self.assertIsNone(self.stop())

    def test_hand_edited_verify_record_is_a_notice(self):
        self.state(stage=5)
        self.write(".sdlc/.work/verify-freshness.json",
                   json.dumps({"feature": "login", "verify": {"last": {"tree": "abc", "result": "fail"}}}))
        self.write(".sdlc/.work/verify.json", json.dumps({"feature": "login", "last": {"tree": "abc", "result": "pass"}}))
        self.assertIn("verify records disagree", self.stop()["systemMessage"])

    def test_lite_flow_review_fix_rerun_in_stage_6_is_not_a_notice(self):
        self.state(stage=5, risk="low", flow="lite")
        self.full_run()
        self.stop()
        self.state(stage=6, risk="low", flow="lite")
        self.write("src/login.ts", "export const a = 2\n")  # a review fix, re-verified in-session
        self.full_run()
        self.assertIsNone(self.stop())

    def slice_in_one_turn(self, untested_fix=False, end=3):
        # A whole slice between two Stops, as Lite and back-to-back slices run: no Stop lands in Stages 4-6
        self.state(stage=3, risk="low", flow="lite")
        self.stop()
        self.write("src/login.ts", "export const a = 2\n")
        self.state(stage=5, risk="low", flow="lite")
        self.full_run()
        self.write(".sdlc/.work/dispatches.jsonl", json.dumps({
            "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "stages": ["Stage 5 – Verify"],
            "agent": "sdlc:verifier", "model": "sonnet", "denied": False}) + "\n")
        if untested_fix:
            self.write("src/login.ts", "export const a = 3\n")  # a review fix with no full run after it
        self.state(stage=end, risk="low", flow="lite")  # 3: committed, the next slice starts; 8: feature done
        return self.stop()

    def test_lite_flow_slice_verified_within_one_turn_is_not_a_notice(self):
        self.assertIsNone(self.slice_in_one_turn(end=8))  # Stage 5 ran unseen: the verifier dispatch shows it

    def test_lite_flow_untested_fix_is_a_notice_until_the_user_accepts_it(self):
        out = self.slice_in_one_turn(untested_fix=True)
        self.assertIn("code changed since the last full test run: src/login.ts", out["systemMessage"])
        self.prompt()
        self.assertIsNone(self.stop())  # accepted: the same untested change doesn't block every later Stop
        self.state(stage=5, risk="low", flow="lite")  # the next slice: a full run, then a new untested fix
        self.full_run()
        self.write("src/login.ts", "export const a = 4\n")
        self.state(stage=3, risk="low", flow="lite")
        self.assertIn("src/login.ts", self.stop()["systemMessage"])


if __name__ == "__main__":
    unittest.main()
