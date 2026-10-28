"""hooks/trust_anchor.py: changes to what verification trusts are shown to the user, not made silently."""
import json
import os
import subprocess
import sys
import unittest
from datetime import datetime, timezone

from helpers import HOOKS, PLUGIN_ROOT, ProjectTestCase, run_hook

sys.path.insert(0, HOOKS)
import verify_freshness as vf  # noqa: E402  (the tree the hook computes)

HOOK = ["python3", os.path.join(HOOKS, "trust_anchor.py")]
FRESHNESS = ["python3", os.path.join(HOOKS, "verify_freshness.py")]
STATE = "# login\nStatus: active\nProcess: 2\nTrack: {track}\nRisk: {risk}\nTop model: opus\nBase: {base}\nCurrent: Stage {stage}\n"
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

    def verify_run(self):
        """A passing verify.py run as Build leaves it: verify.json, then the freshness hook sees the command."""
        tree = vf.worktree_tree(self.root)
        self.write(".sdlc/.work/verify.json", json.dumps({"feature": "login", "last": {"tree": tree, "result": "pass"}}))
        verify = os.path.join(PLUGIN_ROOT, "scripts", "verify.py")
        run_hook(FRESHNESS, {"hook_event_name": "PostToolUse", "cwd": self.root, "tool_name": "Bash",
                             "tool_input": {"command": f'python3 "{verify}"'}, "tool_response": {}}, self.root)

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

    def test_a_stricter_track_or_risk_needs_no_second_word_but_moving_back_does(self):
        # The user approved the bigger track already: shown, but blocking would ask them again
        self.state(risk="low", track="M")
        self.stop()
        self.state(risk="high", track="L")
        out = self.stop()
        self.assertNotIn("decision", out)
        self.assertIn("Track: M → L", out["systemMessage"])
        self.state(risk="high", track="M")
        self.assertIn("Track: L → M", self.stop()["systemMessage"])

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


    def test_leaving_review_needs_a_passing_full_run_at_every_size(self):
        # 2.0: no verifier or checker round; at every size the passing full run on the current code is the evidence
        for n, track in enumerate(("S", "M", "L"), start=2):
            self.state(stage=4, risk="low", track=track)
            self.stop()
            self.prompt()
            self.write("src/login.ts", f"export const a = {n}\n")
            self.state(stage=5, risk="low", track=track)
            self.full_run()
            self.state(stage=8, risk="low", track=track)
            self.assertIsNone(self.stop(), track)
        self.write(".sdlc/login/state.md", STATE.format(track="L", risk="low", base=self.base, stage=8)
                   .replace("Process: 2\n", "Process: 1\n"))
        self.assertIn("Process", self.stop()["systemMessage"])  # the 2.0 marker changed under the hook

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

    def test_a_review_fail_verdict_blocks_ship_unless_waived(self):
        # Under the relay only the checker judges: its report's VERDICT line, not the maker's DONE, decides the round
        self.state(stage=4, risk="low")
        self.stop()
        self.write("src/login.ts", "export const a = 4\n")
        self.state(stage=5, risk="low")
        self.full_run()
        self.dispatch("sdlc:code-reviewer")
        self.write(".sdlc/.work/findings/login/code-reviewer-r1.md", "H1 lock token not re-checked\n\nVERDICT: FAIL — 1 high: H1\n")
        self.state(stage=8, risk="low")
        self.assertIn("review's verdict is FAIL", self.stop()["systemMessage"])
        self.prompt()
        self.write(".sdlc/.work/findings/login/code-reviewer-r2.md", "none\n\nVERDICT: PASS\n")  # the fix, re-checked
        self.state(stage=5, risk="low")
        self.stop()
        self.dispatch("sdlc:code-reviewer")
        self.state(stage=8, risk="low")
        self.assertIsNone(self.stop())

    def test_a_round_cap_fail_the_user_waived_goes_to_ship_without_a_notice(self):
        self.state(stage=5, risk="low")
        self.write(".sdlc/.work/findings/login/code-reviewer-r3.md", "R3-1 comment wording\n\nVERDICT: FAIL — 1 high: R3-1\n")
        self.stop()
        self.prompt()
        self.state(stage=8, risk="low")
        self.assertIn("review's verdict is FAIL", self.stop()["systemMessage"])  # no waiver: still a notice
        self.prompt()
        self.state(stage=5, risk="low")
        self.stop()
        self.write(".sdlc/login/state.md", STATE.format(track="M", risk="low", base=self.base, stage=8)
                   + "\n## Deviations\n- 2026-10-27 waived round 3: R3-1, the user's call\n")
        self.assertIsNone(self.stop())

    def test_ships_own_status_done_is_not_a_notice(self):
        # Ship advances to 8 and sets Status done in one turn: the last Stop saw Stage 5
        self.state(stage=5, risk="low")
        self.stop()
        self.write(".sdlc/login/state.md", STATE.format(track="M", risk="low", base=self.base, stage=8)
                   .replace("Status: active", "Status: done"))
        self.assertIsNone(self.stop())

    def test_review_writing_its_section_of_change_md_is_not_a_notice_but_editing_a_criterion_is(self):
        change = "# Change\n\n## Acceptance criteria\n\n- **AC-001** login works\n"
        self.write("docs/sdlc/intents/login/change.md", change)
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc"}))
        self.write(".sdlc/state/login.md", STATE.format(track="M", risk="low", base=self.base, stage=5))
        self.stop()
        self.write("docs/sdlc/intents/login/change.md", change + "\n## Review\n\n- code, low: PASS\n")
        self.assertIsNone(self.stop())
        self.write("docs/sdlc/intents/login/change.md", change.replace("works", "sometimes works"))
        self.assertIn("criteria or tests changed", self.stop()["systemMessage"])

    def test_only_checker_reports_carry_a_verdict(self):
        # The relay's diff facts and Define's explorer reports share the folder and have no VERDICT line
        self.state(stage=4, risk="low")
        self.stop()
        self.write("src/login.ts", "export const a = 4\n")
        self.state(stage=5, risk="low")
        self.full_run()
        self.dispatch("sdlc:code-reviewer")
        self.write(".sdlc/.work/findings/login/diff-r1.md", "| file | lines |\n")
        self.write(".sdlc/.work/findings/login/code-explorer-r1.md", "entry points\n")
        self.write(".sdlc/.work/findings/login/code-reviewer-r1.md", "none\n\nVERDICT: PASS\n")
        self.state(stage=8, risk="low")
        self.assertIsNone(self.stop())

    def read_state(self):
        with open(self.path(".sdlc/login/state.md"), encoding="utf-8") as f:
            return f.read()

    def test_hand_edited_verify_record_is_a_notice(self):
        self.state(stage=5)
        self.write(".sdlc/.work/verify-freshness.json",
                   json.dumps({"feature": "login", "verify": {"last": {"tree": "abc", "result": "fail"}}}))
        self.write(".sdlc/.work/verify.json", json.dumps({"feature": "login", "last": {"tree": "abc", "result": "pass"}}))
        self.assertIn("verify records disagree", self.stop()["systemMessage"])
        self.prompt()
        self.write(".sdlc/.work/verify.json", "[]")  # malformed or deleted while the hook holds a run: still a notice
        self.assertIn("verify records disagree", self.stop()["systemMessage"])

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


if __name__ == "__main__":
    unittest.main()
