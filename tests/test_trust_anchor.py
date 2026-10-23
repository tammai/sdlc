"""hooks/trust_anchor.py: changes to what verification trusts are shown to the user, not made silently."""
import os
import subprocess
import unittest

from helpers import HOOKS, ProjectTestCase, run_hook

HOOK = ["python3", os.path.join(HOOKS, "trust_anchor.py")]
FRESHNESS = ["python3", os.path.join(HOOKS, "verify_freshness.py")]
STATE = "# login\nStatus: active\nTrack: M\nRisk: {risk}\nTop model: opus\nBase: {base}\nCurrent: Stage {stage}\n"
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

    def state(self, stage=4, risk="high"):
        self.write(".sdlc/login/state.md", STATE.format(risk=risk, base=self.base, stage=stage))

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


if __name__ == "__main__":
    unittest.main()
