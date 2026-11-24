"""Approval policy (.sdlc/2026-11-24-m-gh-92-approval-policy, issue #92 part 1): config `approval` makes the move from
Define to Build wait for the user's approval, recorded by hooks/plan_approval.py and checked by state.py."""
import json
import os
import subprocess
import sys
import unittest

from helpers import HOOKS, PLUGIN_ROOT, ProjectTestCase, run_hook

sys.path.insert(0, HOOKS)
STATE_PY = os.path.join(PLUGIN_ROOT, "scripts", "state.py")
SCAFFOLD = os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py")
HOOK = lambda name: [sys.executable, os.path.join(HOOKS, name)]  # noqa: E731  (as hooks.json runs them)
UTF8 = {"PYTHONUTF8": "1"}


class ApprovalTest(ProjectTestCase):
    def config(self, accept=True, **values):
        """Write config keys; with accept, record the user's acceptance as the trust anchor does on their reply."""
        import sdlc_scopes
        path = self.path(".sdlc/config.json")
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except OSError:
            data = {}
        data.update(values)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        if accept:
            mode, skip = sdlc_scopes.configured(self.root)
            anchor = self.path(".sdlc/.work/trust-anchor.json")
            os.makedirs(os.path.dirname(anchor), exist_ok=True)
            with open(anchor, "w", encoding="utf-8") as f:
                json.dump({"_config": {"mode": mode, "skip": skip, "notices": [],
                                       "approval": sdlc_scopes.approval_configured(self.root)}}, f)

    def run_py(self, script, *args):
        p = subprocess.run([sys.executable, script, "--root", self.root, *args], capture_output=True,
                           encoding="utf-8", errors="replace")
        return p.returncode, p.stdout + p.stderr

    def new(self, name="login", track="M"):
        code, out = self.run_py(STATE_PY, "new", name, "--track", track, "--risk", "low", "--footprint", "1",
                                "--task", "Build it | AC-001 | a.py")
        self.assertEqual(code, 0, out)

    def advance(self, name="login"):
        return self.run_py(STATE_PY, "advance", name, "2", "--gate", "pass")

    def state_text(self, name="login"):
        import sdlc_layout
        with open(os.path.join(self.root, sdlc_layout.paths(self.root, name)["state"]), encoding="utf-8") as f:
            return f.read()

    def answer(self, label, header="Approve plan", use_id="toolu_1", feature="login"):
        q = {"question": f"Approve the plan for {feature}?", "header": header,
             "options": [{"label": "Approve"}, {"label": "Change something"}]}
        run_hook(HOOK("user_answer.py"), {"hook_event_name": "PreToolUse", "cwd": self.root,
                                          "tool_name": "AskUserQuestion", "tool_use_id": use_id,
                                          "tool_input": {"questions": [q]}}, self.root, UTF8)
        given = {q["question"]: label}
        run_hook(HOOK("plan_approval.py"), {"hook_event_name": "PostToolUse", "cwd": self.root,
                                            "tool_name": "AskUserQuestion", "tool_use_id": use_id,
                                            "tool_input": {"questions": [q], "answers": given},
                                            "tool_response": {"questions": [q], "answers": given}}, self.root, UTF8)

    def prompt(self, text):
        run_hook(HOOK("plan_approval.py"), {"hook_event_name": "UserPromptSubmit", "cwd": self.root, "prompt": text},
                 self.root, UTF8)

    # AC-001
    def test_ml_refuses_the_build_until_approved(self):
        self.config(approval="ml")
        self.new()
        before = self.state_text()
        code, out = self.advance()
        self.assertNotEqual(code, 0, out)
        self.assertIn("Approve plan", out)
        self.assertEqual(self.state_text(), before)
        self.assertNotEqual(self.run_py(STATE_PY, "advance", "login", "3", "--gate", "pass")[0], 0)  # no stage skips it

    # AC-002
    def test_the_dialog_approve_lets_the_build_start(self):
        self.config(approval="ml")
        self.new()
        self.answer("Approve")
        code, out = self.advance()
        self.assertEqual(code, 0, out)
        self.assertIn("approved by the user", self.state_text())

    # AC-003
    def test_other_answers_and_prompts_approve_nothing(self):
        self.config(approval="ml")
        self.new()
        self.answer("Change something")
        self.answer("Approve", header="Something else", use_id="toolu_2")
        self.answer("Approve with changes", use_id="toolu_3")
        self.answer("Approve", use_id="toolu_4", feature="signup")  # names a feature that isn't waiting
        self.prompt("ok, go on")
        self.prompt("/sdlc:start B2 --autopilot")
        code, out = self.advance()
        self.assertNotEqual(code, 0, out)

    # AC-008
    def test_an_approval_holds_only_for_the_plan_and_track_shown(self):
        self.config(approval="ml")
        self.new()
        self.answer("Approve (Recommended)")
        self.answer("Change something", use_id="toolu_2")  # a later change takes the approval back
        self.assertNotEqual(self.advance()[0], 0)
        code, out = self.run_py(STATE_PY, "set", "login", "Track", "S")  # resizing down doesn't skip the stop
        self.assertNotEqual(code, 0, out)
        self.answer("Approve", use_id="toolu_3")
        self.prompt("actually, rename the flag first")  # a typed change takes it back too
        self.assertNotEqual(self.advance()[0], 0)
        self.answer("Approve", use_id="toolu_4")
        self.assertEqual(self.advance()[0], 0)

    # AC-004
    def test_a_typed_approve_approves_the_waiting_feature(self):
        self.config(approval="ml")
        self.new()
        self.prompt("Approve")
        self.assertEqual(self.advance()[0], 0)
        self.new("signup")
        self.prompt("Approve signup.")  # a capital and a full stop still name it
        self.assertEqual(self.advance("signup")[0], 0)

    # AC-005
    def test_always_covers_s_and_the_default_refuses_nothing(self):
        self.config(approval="always")
        self.new(track="S")
        self.assertNotEqual(self.advance()[0], 0)
        self.config(approval="high-risk")
        self.new("signup")
        self.assertEqual(self.advance("signup")[0], 0)
        self.config(approval=None)
        self.new("profile")
        self.assertEqual(self.advance("profile")[0], 0)

    # AC-006
    def test_fewer_stops_wait_for_the_trust_anchor(self):
        import sdlc_scopes
        self.new()
        self.config(approval="ml", accept=False)  # stricter: honoured at once
        self.assertEqual(sdlc_scopes.approval(self.root), "ml")
        stop = {"hook_event_name": "Stop", "cwd": self.root, "stop_hook_active": False}
        run_hook(HOOK("trust_anchor.py"), stop, self.root, UTF8)
        self.config(approval="high-risk", accept=False)  # fewer stops: waits
        self.assertEqual(sdlc_scopes.approval(self.root), "ml")
        _, out, raw, _ = run_hook(HOOK("trust_anchor.py"), stop, self.root, UTF8)
        self.assertEqual((out or {}).get("decision"), "block", raw)
        self.assertIn("approval", raw)
        run_hook(HOOK("trust_anchor.py"), {"hook_event_name": "UserPromptSubmit", "cwd": self.root, "prompt": "ok"},
                 self.root, UTF8)
        self.assertEqual(sdlc_scopes.approval(self.root), "high-risk")

    # AC-007
    def test_scaffold_sets_it_and_the_status_line_shows_it(self):
        code, out = self.run_py(SCAFFOLD, "init", "--kind", "greenfield", "--host", "claude-code")
        self.assertEqual(code, 0, out)
        code, out = self.run_py(SCAFFOLD, "approval", "sometimes")
        self.assertNotEqual(code, 0, out)
        code, out = self.run_py(SCAFFOLD, "approval", "ml")
        self.assertEqual(code, 0, out)
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["approval"], "ml")
        start = {"hook_event_name": "SessionStart", "cwd": self.root, "source": "startup"}
        _, _, raw, _ = run_hook(HOOK("session_status.py"), start, self.root, UTF8)
        self.assertIn("approval ml", raw)
        self.config(approval="ml")  # the trust anchor recorded it
        self.config(approval="high-risk", accept=False)
        _, _, raw, _ = run_hook(HOOK("session_status.py"), start, self.root, UTF8)
        self.assertIn("high-risk asked, not yet accepted", raw)


if __name__ == "__main__":
    unittest.main()
