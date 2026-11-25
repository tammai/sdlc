"""Approval policy (.sdlc/2026-11-24-m-gh-92-approval-policy, issue #92 part 1): config `approval` makes the move from
Define to Build wait for the user's approval, recorded by hooks/plan_approval.py and checked by state.py."""
import json
import os
import re
import subprocess
import sys
import unittest

from helpers import HOOKS, PLUGIN_ROOT, ProjectTestCase, run_hook

sys.path.insert(0, HOOKS)
STATE_PY = os.path.join(PLUGIN_ROOT, "scripts", "state.py")
SCAFFOLD = os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py")
HOOK = lambda name: [sys.executable, os.path.join(HOOKS, name)]  # noqa: E731  (as hooks.json runs them)
UTF8 = {"PYTHONUTF8": "1"}


class ApprovalBase(ProjectTestCase):
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



class ApprovalTest(ApprovalBase):
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


class HardeningHelpers:
    """Helpers for the 2026-11-25-m-approval-hardening tests."""

    def ask(self, cwd, label, use_id, feature="login", question=None):
        q = {"question": question or f"Approve the plan for {feature}?", "header": "Approve plan",
             "options": [{"label": "Approve"}, {"label": "Change something"}]}
        run_hook(HOOK("user_answer.py"), {"hook_event_name": "PreToolUse", "cwd": cwd, "tool_name": "AskUserQuestion",
                                          "tool_use_id": use_id, "tool_input": {"questions": [q]}}, cwd, UTF8)
        given = {q["question"]: label}
        run_hook(HOOK("plan_approval.py"), {"hook_event_name": "PostToolUse", "cwd": cwd,
                                            "tool_name": "AskUserQuestion", "tool_use_id": use_id,
                                            "tool_input": {"questions": [q], "answers": given},
                                            "tool_response": {"questions": [q], "answers": given}}, cwd, UTF8)

    def hand_edit_track(self, track, name="login", root=None):
        import sdlc_layout
        root = root or self.root
        path = os.path.join(root, sdlc_layout.paths(root, name)["state"])
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(re.sub(r"^Track:.*$", f"Track: {track}", text, count=1, flags=re.M))

    def state_py(self, root, *args, project=None):
        env = {**os.environ, **UTF8}
        env.pop("CLAUDE_PROJECT_DIR", None)
        if project:
            env["CLAUDE_PROJECT_DIR"] = project
        p = subprocess.run([sys.executable, STATE_PY, "--root", root, *args], capture_output=True, encoding="utf-8",
                           errors="replace", env=env)
        return p.returncode, p.stdout + p.stderr


class ApprovalHardeningTest(HardeningHelpers, ApprovalBase):
    """.sdlc/2026-11-25-m-approval-hardening: the approval holds against a hand-edited track and a re-created
    feature, and counts from a session started in a workbench's app repo."""

    # AC-001
    def test_a_hand_edited_track_still_needs_approval(self):
        self.config(approval="ml")
        self.new(track="M")
        import sdlc_layout
        path = os.path.join(self.root, sdlc_layout.paths(self.root, "login")["state"])
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(re.sub(r"^Track:.*$", "Track: S", text, count=1, flags=re.M))
        code, out = self.advance()
        self.assertNotEqual(code, 0, out)
        self.assertIn("Approve plan", out)

    # AC-003
    def test_a_recreated_feature_starts_unapproved(self):
        self.config(approval="ml")
        self.new()
        self.answer("Approve")
        import sdlc_layout
        os.remove(os.path.join(self.root, sdlc_layout.paths(self.root, "login")["state"]))
        self.new()
        code, out = self.advance()
        self.assertNotEqual(code, 0, out)

    # AC-004
    def test_a_dialog_approve_from_an_app_repo_reaches_the_workbench(self):
        self.write("workbench.json", json.dumps({"repos": [{"name": "app", "url": "u1", "role": "app", "write": True}]}))
        self.config(workbench=True, approval="ml")
        os.makedirs(self.path("app/.git"))
        self.write("app/.sdlc/config.json", "{}")
        self.new()
        self.ask(self.path("app"), "Approve", "toolu_app")
        code, out = self.advance()
        self.assertEqual(code, 0, out)

    # AC-005
    def test_the_report_reads_the_sessions_gate(self):
        self.config(approval="ml")
        os.makedirs(self.path("nested/.git"))
        self.write("nested/.sdlc/config.json", "{}")
        env = {**os.environ, "CLAUDE_PROJECT_DIR": self.root, **UTF8}
        p = subprocess.run([sys.executable, SCAFFOLD, "--root", self.path("nested"), "approval"], capture_output=True,
                           encoding="utf-8", errors="replace", env=env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout)["effective"], "ml", p.stdout)


class ApprovalHardeningReviewTest(HardeningHelpers, ApprovalBase):
    """Code review round 1 of .sdlc/2026-11-25-m-approval-hardening: each finding's class, test first."""

    # H2: a nested repo's features record into the session repo's store
    def test_a_nested_repos_created_track_survives_another_feature(self):
        self.config(approval="ml")
        os.makedirs(self.path("nested/.git"))
        self.write("nested/.sdlc/config.json", "{}")
        nested = self.path("nested")
        args = ("--track", "M", "--risk", "low", "--footprint", "1", "--task", "Build it | AC-001 | a.py")
        code, out = self.state_py(nested, "new", "x", *args, project=self.root)
        self.assertEqual(code, 0, out)
        code, out = self.state_py(self.root, "new", "y", *args, project=self.root)
        self.assertEqual(code, 0, out)
        self.hand_edit_track("S", "x", nested)
        code, out = self.state_py(nested, "advance", "x", "2", "--gate", "pass", project=self.root)
        self.assertNotEqual(code, 0, out)

    # M1: a prompt with nothing to take back leaves the store alone
    def test_a_prompt_with_no_approval_to_take_back_writes_nothing(self):
        self.config(approval="ml")
        self.new()
        store = self.write(".sdlc/.work/approvals.json", json.dumps({"other": {"by": "dialog"}}))
        with open(store, encoding="utf-8") as f:
            before = f.read()
        os.utime(store, ns=(10**18, 10**18))
        self.prompt("what does the plan do?")
        self.assertEqual(os.stat(store).st_mtime_ns, 10**18)
        with open(store, encoding="utf-8") as f:
            self.assertEqual(f.read(), before)

    # M2: the questions record an app repo gets ignores itself
    def test_the_asked_record_in_an_app_repo_ignores_itself(self):
        self.write("workbench.json", json.dumps({"repos": [{"name": "app", "url": "u1", "role": "app", "write": True}]}))
        self.config(workbench=True, approval="ml")
        os.makedirs(self.path("app/.git"))
        self.write("app/.sdlc/config.json", "{}")
        self.new()
        self.ask(self.path("app"), "Approve", "toolu_app")
        self.assertTrue(os.path.isfile(self.path("app/.sdlc/.work/asked.json")))
        self.assertTrue(os.path.isfile(self.path("app/.sdlc/.work/.gitignore")))

    # M3: a store that can't be written refuses `new` instead of keeping a namesake's approval
    def test_new_is_refused_when_the_store_cant_be_written(self):
        self.config(approval="ml")
        os.makedirs(self.path(".sdlc/.work/approvals.json"))  # a folder where the record goes
        code, out = self.run_py(STATE_PY, "new", "login", "--track", "M", "--risk", "low", "--footprint", "1",
                                "--task", "Build it | AC-001 | a.py")
        self.assertNotEqual(code, 0, out)
        import sdlc_layout
        self.assertNotIn("login", sdlc_layout.features(self.root))

    # L1: a plan sent back keeps its created track
    def test_a_plan_sent_back_keeps_its_created_track(self):
        self.config(approval="ml")
        self.new()
        self.answer("Approve")
        self.answer("Change something", use_id="toolu_2")
        self.hand_edit_track("S")
        code, out = self.advance()
        self.assertNotEqual(code, 0, out)


class ApprovalHardeningRound2Test(HardeningHelpers, ApprovalBase):
    """Code review round 2 of .sdlc/2026-11-25-m-approval-hardening: each finding's class, test first."""

    # R2-2: a created track that's gone counts as the stricter case
    def test_a_wiped_store_still_needs_approval(self):
        self.config(approval="ml")
        self.new()
        if os.path.exists(self.path(".sdlc/.work/approvals.json")):
            os.remove(self.path(".sdlc/.work/approvals.json"))
        self.hand_edit_track("S")
        code, out = self.advance()
        self.assertNotEqual(code, 0, out)

    # R2-3: a raise through `set Track` raises the created track too
    def test_a_raised_track_stays_raised(self):
        self.config(approval="ml")
        self.new(track="S")
        code, out = self.run_py(STATE_PY, "set", "login", "Track", "M")
        self.assertEqual(code, 0, out)
        self.hand_edit_track("S")
        code, out = self.advance()
        self.assertNotEqual(code, 0, out)



class ApprovalHardeningRound3Test(HardeningHelpers, ApprovalBase):
    """Code review round 3 of .sdlc/2026-11-25-m-approval-hardening (written with the floor's move into the state file,
    after the code: see the feature's deviations)."""

    # R3-1: a `set Track` to the hand-edited value never lowers the floor
    def test_set_track_after_a_hand_edit_keeps_the_floor(self):
        self.config(approval="ml")
        self.new()
        self.hand_edit_track("S")
        code, out = self.run_py(STATE_PY, "set", "login", "Track", "S")  # a downsize from the floor: needs approval
        self.assertNotEqual(code, 0, out)
        code, out = self.advance()
        self.assertNotEqual(code, 0, out)

    # R3-4: a feature started before the policy keeps its track as it stood: an S isn't stopped by `ml`
    def test_a_feature_started_before_the_policy_is_judged_by_its_track(self):
        self.new(track="S")
        self.config(approval="ml")
        code, out = self.advance()
        self.assertEqual(code, 0, out)


class ApprovalHardeningRound4Test(HardeningHelpers, ApprovalBase):
    """Code review round 4 of .sdlc/2026-11-25-m-approval-hardening: each finding's class, test first."""

    # R4-1: a raise outside Define raises the floor too, so a plan sent back to Define keeps it
    def test_a_raise_at_build_holds_when_sent_back(self):
        self.config(approval="ml")
        self.new(track="S")
        self.assertEqual(self.advance()[0], 0)
        code, out = self.run_py(STATE_PY, "set", "login", "Track", "M")
        self.assertEqual(code, 0, out)
        code, out = self.run_py(STATE_PY, "advance", "login", "1", "--gate", "fail")
        self.assertEqual(code, 0, out)
        self.hand_edit_track("S")
        code, out = self.advance()
        self.assertNotEqual(code, 0, out)

    # R4-6: an approved downsize lowers the floor with it
    def test_an_approved_downsize_lowers_the_floor(self):
        self.config(approval="ml")
        self.new()
        self.answer("Approve")
        code, out = self.run_py(STATE_PY, "set", "login", "Track", "S")
        self.assertEqual(code, 0, out)
        self.prompt("thanks")  # a later prompt takes the approval back; S needs none under ml
        code, out = self.advance()
        self.assertEqual(code, 0, out)


class ApprovalHardeningRound5Test(HardeningHelpers, ApprovalBase):
    """Code review round 5 of .sdlc/2026-11-25-m-approval-hardening: each finding's class, test first."""

    # R5-1: a session folder with no .sdlc above --root: the report reads what the scripts read
    def test_the_report_reads_what_the_scripts_read(self):
        os.makedirs(self.path("x/.git"))
        self.write("x/.sdlc/config.json", json.dumps({"approval": "ml"}))
        env = {**os.environ, "CLAUDE_PROJECT_DIR": self.root, **UTF8}
        p = subprocess.run([sys.executable, SCAFFOLD, "--root", self.path("x"), "approval"], capture_output=True,
                           encoding="utf-8", errors="replace", env=env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout)["effective"], "ml", p.stdout)

    # R5-3: a same-size `set Track` (a new reason) keeps the approval
    def test_a_same_size_set_keeps_the_approval(self):
        self.new()  # before the policy: no floor
        self.config(approval="ml")
        self.answer("Approve")
        code, out = self.run_py(STATE_PY, "set", "login", "Track", "M   (sized up because: auth)")
        self.assertEqual(code, 0, out)
        code, out = self.advance()
        self.assertEqual(code, 0, out)

    # R5-4: `new` clears a namesake's approval under any policy
    def test_new_clears_a_namesakes_approval_under_any_policy(self):
        self.new()
        self.answer("Approve")  # recorded though the default policy doesn't ask for it
        import sdlc_layout
        os.remove(os.path.join(self.root, sdlc_layout.paths(self.root, "login")["state"]))
        self.new()
        self.config(approval="ml")
        code, out = self.advance()
        self.assertNotEqual(code, 0, out)

    # R5-5: a store that can't be read is left alone, and `new` says so
    def test_new_leaves_an_unreadable_store_alone(self):
        self.config(approval="ml")
        self.write(".sdlc/.work/approvals.json", '{"other": {"by": "dialog"')
        code, out = self.run_py(STATE_PY, "new", "login", "--track", "M", "--risk", "low", "--footprint", "1",
                                "--task", "Build it | AC-001 | a.py")
        self.assertNotEqual(code, 0, out)
        with open(self.path(".sdlc/.work/approvals.json"), encoding="utf-8") as f:
            self.assertEqual(f.read(), '{"other": {"by": "dialog"')

    # R5-6: a question naming the feature inside a path still names it
    def test_a_feature_named_inside_a_path_is_approved(self):
        self.config(approval="ml")
        self.new()
        self.ask(self.root, "Approve", "toolu_path", question="Approve the plan in .sdlc/login/change.md?")
        code, out = self.advance()
        self.assertEqual(code, 0, out)


class ApprovalHardeningRound6Test(HardeningHelpers, ApprovalBase):
    """Code review round 6 of .sdlc/2026-11-25-m-approval-hardening (the scope cut back to 3.16's keys)."""

    # R6-1: a prompt that starts with `approve` but asks for a change takes the approval back
    def test_approve_but_change_takes_the_approval_back(self):
        self.config(approval="ml")
        self.new()
        self.answer("Approve")
        self.prompt("approve but rename the helper first")
        code, out = self.advance()
        self.assertNotEqual(code, 0, out)

    # R6-3: outside the session, the report reads the folder a value is written to
    def test_the_report_outside_the_session_reads_the_folder_written(self):
        os.makedirs(self.path("a/.git"))
        self.write("a/.sdlc/config.json", "{}")
        os.makedirs(self.path("b/.git"))
        self.write("b/.sdlc/config.json", "{}")
        env = {**os.environ, "CLAUDE_PROJECT_DIR": self.path("a"), **UTF8}
        p = subprocess.run([sys.executable, SCAFFOLD, "--root", self.path("b"), "approval", "ml"], capture_output=True,
                           encoding="utf-8", errors="replace", env=env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout)["approval"], "ml", p.stdout)

    # R6-5: any approval is spent on leaving Define, so back at Define the plan needs approving again
    def test_an_approval_kept_by_a_downsize_is_spent_on_leaving_define(self):
        self.config(approval="ml")
        self.new()
        self.answer("Approve")
        self.assertEqual(self.run_py(STATE_PY, "set", "login", "Track", "S")[0], 0)  # approved downsize
        self.assertEqual(self.advance()[0], 0)
        self.assertEqual(self.run_py(STATE_PY, "advance", "login", "1", "--gate", "fail")[0], 0)
        self.hand_edit_track("M")
        code, out = self.advance()
        self.assertNotEqual(code, 0, out)

    # R7-1: a raise at Define takes back an approval of the smaller plan under any policy
    def test_a_raise_under_the_default_takes_back_the_approval(self):
        self.new(track="S")
        self.answer("Approve")  # recorded though the default doesn't ask
        self.assertEqual(self.run_py(STATE_PY, "set", "login", "Track", "L")[0], 0)
        self.config(approval="ml")
        code, out = self.advance()
        self.assertNotEqual(code, 0, out)

    # R7-2: an approval that can't be spent on leaving Define is said, not kept silently
    def test_an_unspendable_approval_is_said(self):
        self.config(approval="ml")
        self.new()
        self.answer("Approve")
        store = self.path(".sdlc/.work/approvals.json")
        os.chmod(store, 0o444)  # os.replace over a read-only file fails on Windows; a read-only folder elsewhere
        if os.name != "nt":
            os.chmod(os.path.dirname(store), 0o555)
        self.addCleanup(os.chmod, os.path.dirname(store), 0o755)
        self.addCleanup(os.chmod, store, 0o644)
        code, out = self.advance()
        with open(store, encoding="utf-8") as f:
            if "login" not in f.read():
                self.skipTest("the store was rewritten anyway (running as root?)")
        self.assertNotEqual(code, 0, out)
        self.assertIn("approval", out)

    # R7-4: a lower-case track is the same track
    def test_a_lower_case_track_raises_the_floor(self):
        self.new(track="S")
        self.config(approval="ml")
        self.assertEqual(self.run_py(STATE_PY, "set", "login", "Track", "m")[0], 0)
        code, out = self.advance()
        self.assertNotEqual(code, 0, out)

    # R6-7: under the default policy an unreadable store doesn't stop `new`
    def test_the_default_policy_ignores_an_unreadable_store(self):
        self.write(".sdlc/.work/approvals.json", '{"other": ')
        code, out = self.run_py(STATE_PY, "new", "login", "--track", "M", "--risk", "low", "--footprint", "1",
                                "--task", "Build it | AC-001 | a.py")
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
