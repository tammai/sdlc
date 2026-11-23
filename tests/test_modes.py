"""Configurable stages and advisory mode (.sdlc/2026-11-23-l-configurable-stages): `mode` and `skip` in
.sdlc/config.json, set through scaffold.py, read by the hooks."""
import json
import os
import shutil
import subprocess
import sys
import unittest

from helpers import HOOKS, PLUGIN_ROOT, ProjectTestCase, run_hook

sys.path.insert(0, HOOKS)
SCAFFOLD = os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py")
HOOK = lambda name: ["python3", os.path.join(HOOKS, name)]  # noqa: E731
STATE = "# login\nStatus: active\nProcess: 3\nTrack: M\nRisk: low\nTop model: opus\nCurrent: Stage {stage} – x\n"


class ModesTest(ProjectTestCase):
    def config(self, accept=True, root=None, **values):
        """Write config keys; with accept, also record the user's acceptance of the resulting mode and skips, as the
        trust anchor does on their reply (a relaxation counts only once accepted, ADR 0030)."""
        import sdlc_scopes
        root = root or self.root
        path = os.path.join(root, ".sdlc", "config.json")
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
            mode, skip = sdlc_scopes.configured(root)
            anchor = os.path.join(root, ".sdlc", ".work", "trust-anchor.json")
            try:
                with open(anchor, encoding="utf-8") as f:
                    record = json.load(f)
            except (OSError, ValueError):
                record = {}
            record["_config"] = {"mode": mode, "skip": skip, "notices": []}
            os.makedirs(os.path.dirname(anchor), exist_ok=True)
            with open(anchor, "w", encoding="utf-8") as f:
                json.dump(record, f)

    def sc(self, *args):
        p = subprocess.run([sys.executable, SCAFFOLD, "--root", self.root, *args], capture_output=True,
                           encoding="utf-8", errors="replace")
        return p.returncode, p.stdout + p.stderr

    def stored(self):
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            return json.load(f)

    def pre(self, hook, tool, tool_input, **env):
        _, out, raw, err = run_hook(HOOK(hook), {"hook_event_name": "PreToolUse", "cwd": self.root, "session_id": "s",
                                                 "tool_name": tool, "tool_input": tool_input}, self.root, env)
        return (out or {}).get("hookSpecificOutput", {}).get("permissionDecision")

    def init(self):
        code, out = self.sc("init", "--kind", "greenfield", "--host", "claude-code")
        self.assertEqual(code, 0, out)

    # AC-001
    def test_mode_is_set_through_scaffold_only_to_known_values(self):
        import sdlc_scopes
        self.init()
        self.assertEqual(sdlc_scopes.mode(self.root), "full")
        code, out = self.sc("mode", "advisory")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.stored()["mode"], "advisory")
        self.assertEqual(json.loads(out)["effective"]["mode"], "full")  # asked, not yet accepted
        self.assertEqual(sdlc_scopes.mode(self.root), "full")
        self.config(mode="advisory")  # the user accepted it
        self.assertEqual(sdlc_scopes.mode(self.root), "advisory")
        code, out = self.sc("mode", "lenient")
        self.assertEqual(code, 2, out)
        self.assertEqual(self.stored()["mode"], "advisory")
        self.assertEqual(self.sc("mode", "full")[0], 0)
        self.assertEqual(self.stored()["mode"], "full")
        for bad in ("Advisory", ["advisory"], 1, None):
            self.config(mode=bad, accept=False)
            self.assertEqual(sdlc_scopes.mode(self.root), "full", bad)

    # AC-002
    def test_skip_takes_only_named_steps_in_full_mode(self):
        import sdlc_scopes
        self.init()
        self.assertEqual(self.sc("skip", "pr", "security-review")[0], 0)
        self.assertEqual(self.stored()["skip"], ["pr", "security-review"])
        self.assertEqual(sdlc_scopes.skipped(self.root), [])  # not yet accepted
        self.config()
        self.assertEqual(sdlc_scopes.skipped(self.root), ["pr", "security-review"])
        code, out = self.sc("skip", "verify")
        self.assertEqual(code, 2, out)
        self.assertEqual(self.sc("skip", "--clear")[0], 0)
        self.assertNotIn("skip", self.stored())
        self.assertEqual(self.sc("mode", "advisory")[0], 0)
        code, out = self.sc("skip", "pr")
        self.assertEqual(code, 2, out)
        self.assertEqual(self.sc("skip", "--clear")[0], 0)  # clearing is always allowed
        self.config(skip=["pr", "red-step", 3])  # a hand edit: unknown names ignored; none at all in advisory
        self.assertEqual(sdlc_scopes.skipped(self.root), [])
        self.config(mode="full")
        self.assertEqual(sdlc_scopes.skipped(self.root), ["pr"])

    # AC-003
    def test_advisory_silences_the_process_hooks(self):
        self.write(".sdlc/state/login.md", STATE.format(stage=3))
        self.write(".sdlc/.work/findings/login/code-reviewer-r1.md", "VERDICT: FAIL — H1\n")
        self.write(".sdlc/.work/findings/login/code-reviewer-r2.md", "VERDICT: FAIL — H1\n")
        agent = {"subagent_type": "general-purpose", "model": "haiku", "description": "x", "prompt": "x"}
        for mode, expect in (("full", "deny"), ("advisory", None)):
            self.config(mode=mode)
            self.assertEqual(self.pre("model_router.py", "Agent", agent), expect, mode)
            self.assertEqual(self.pre("review_rounds.py", "Edit", {"file_path": self.path("src/a.ts")}), expect, mode)
        # the trust anchor: a field change after the first look, in an advisory repo from the start
        self.write(".sdlc/state/login.md", STATE.format(stage=2))
        stop = {"hook_event_name": "Stop", "cwd": self.root, "stop_hook_active": False}
        run_hook(HOOK("trust_anchor.py"), stop, self.root)
        self.write(".sdlc/state/login.md", STATE.format(stage=2).replace("Risk: low", "Risk: high").replace(
            "Track: M", "Track: S"))
        _, out, raw, _ = run_hook(HOOK("trust_anchor.py"), stop, self.root)
        self.assertNotEqual((out or {}).get("decision"), "block", raw)

    # AC-004
    def test_advisory_silences_the_always_on_layer(self):
        os.makedirs(self.path(".claude"), exist_ok=True)
        shutil.copy(os.path.join(PLUGIN_ROOT, "examples", "hookify", "dangerous-rm.local.md"),
                    self.path(".claude/hookify.dangerous-rm.local.md"))
        for mode, expect in (("full", "deny"), ("advisory", None)):
            self.config(mode=mode)
            self.assertEqual(self.pre("pretooluse.py", "Bash", {"command": "rm -rf node_modules"}), expect, mode)
            self.assertEqual(self.pre("pretooluse.py", "Monitor", {"command": "git commit -m x"}), expect, mode)
            payload = {"hook_event_name": "PostToolUse", "session_id": f"s-{mode}", "cwd": self.root,
                       "tool_name": "Write", "tool_input": {"file_path": self.path("a.js"),
                                                            "content": "el.innerHTML = userInput\n"}}
            _, out, raw, _ = run_hook(HOOK("security_reminder_hook.py"), payload, self.root,
                                      {"SECURITY_WARNINGS_STATE_DIR": self.path(f"state-{mode}")})
            warned = "innerHTML" in (out or {}).get("hookSpecificOutput", {}).get("additionalContext", "")
            self.assertEqual(warned, mode == "full", raw)

    def test_the_session_status_line_names_the_mode_and_skips(self):
        code, out = self.sc("init", "--kind", "greenfield", "--host", "claude-code")
        self.assertEqual(code, 0, out)
        start = {"hook_event_name": "SessionStart", "cwd": self.root, "source": "startup"}
        self.config(skip=["pr"], accept=False)
        _, _, raw, _ = run_hook(HOOK("session_status.py"), start, self.root)
        self.assertIn("skip none (pr asked, not yet accepted)", raw)
        self.config(skip=["pr"])
        _, _, raw, _ = run_hook(HOOK("session_status.py"), start, self.root)
        self.assertIn("skip pr", raw)
        self.config(mode="advisory")
        _, _, raw, _ = run_hook(HOOK("session_status.py"), start, self.root)
        self.assertIn("mode advisory", raw)

    # AC-005
    def test_advisory_workbench_keeps_the_read_only_guard(self):
        subprocess.run(["git", "init", "-q", self.root], check=True)
        self.config(workbench=True, mode="advisory")
        self.write("workbench.json", json.dumps({"repos": [{"name": "specs", "url": "x", "role": "specs"}]}))
        subprocess.run(["git", "init", "-q", self.path("specs")], check=True)
        self.assertEqual(self.pre("pretooluse.py", "Bash", {"command": "echo hi > specs/x.txt"}), "deny")

    # AC-006
    def test_skipped_security_review_turns_off_the_feature_reviews(self):
        import sdlc_review_gate
        git = ["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run(git[:3] + ["init", "-q"], check=True)
        self.write("src/a.ts", "export const a = 1\n")
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "init"], check=True)
        base = subprocess.run(git + ["rev-parse", "--short", "HEAD"], capture_output=True,
                              encoding="utf-8").stdout.strip()
        self.write(".sdlc/state/login.md", STATE.format(stage=2).replace("Risk: low", "Risk: high")
                   + f"Base: {base}\n")
        self.write("src/b.ts", "export const b = 2\n")
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "b"], check=True)
        sha = subprocess.run(git + ["rev-parse", "HEAD"], capture_output=True, encoding="utf-8").stdout.strip()
        self.assertTrue(sdlc_review_gate.review_wanted(self.root))
        self.assertFalse(sdlc_review_gate.decide(self.root, [sha], set()).get("off"))
        self.config(skip=["security-review"])
        self.assertFalse(sdlc_review_gate.review_wanted(self.root))
        self.assertTrue(sdlc_review_gate.decide(self.root, [sha], set()).get("off"))

    # AC-007
    def stop_blocked(self):
        stop = {"hook_event_name": "Stop", "cwd": self.root, "stop_hook_active": False}
        _, out, raw, _ = run_hook(HOOK("trust_anchor.py"), stop, self.root)
        return (out or {}).get("decision") == "block", raw

    def reply(self):
        run_hook(HOOK("trust_anchor.py"), {"hook_event_name": "UserPromptSubmit", "cwd": self.root, "prompt": "ok"},
                 self.root)

    def test_relaxing_mode_or_skip_raises_a_trust_anchor_notice(self):
        import sdlc_scopes
        self.write(".sdlc/state/login.md", STATE.format(stage=2))
        self.config(mode="full", accept=False)
        self.assertFalse(self.stop_blocked()[0])
        self.config(skip=["pr"], accept=False)
        self.assertEqual(sdlc_scopes.skipped(self.root), [])  # asked, not honoured until accepted
        hit, raw = self.stop_blocked()
        self.assertTrue(hit, raw)
        self.assertIn("skip", raw)
        self.reply()
        self.assertEqual(sdlc_scopes.skipped(self.root), ["pr"])
        self.assertFalse(self.stop_blocked()[0])
        self.config(mode="advisory", accept=False)
        hit, raw = self.stop_blocked()
        self.assertTrue(hit, raw)  # said even though advisory silences the rest of the anchor
        self.assertIn("advisory", raw)
        self.reply()
        self.assertEqual(sdlc_scopes.mode(self.root), "advisory")
        self.assertFalse(self.stop_blocked()[0])
        self.config(mode="full", skip=[], accept=False)  # more checks: no notice, honoured at once
        self.assertFalse(self.stop_blocked()[0])
        self.assertEqual(sdlc_scopes.effective(self.root), ("full", []))

    def test_a_reply_accepts_only_what_the_notice_showed(self):
        # security r1 H1 / code r1 H2: a change after the last Stop isn't accepted by the next reply
        import sdlc_scopes
        self.write(".sdlc/state/login.md", STATE.format(stage=2))
        self.config(mode="full", accept=False)
        self.assertFalse(self.stop_blocked()[0])
        self.config(skip=["pr"], accept=False)
        self.assertTrue(self.stop_blocked()[0])
        self.config(skip=["pr", "security-review"], accept=False)  # after the notice, before the reply
        self.reply()
        self.assertEqual(sdlc_scopes.skipped(self.root), ["pr"])
        hit, raw = self.stop_blocked()
        self.assertTrue(hit, raw)
        self.assertIn("security-review", raw)
        self.config(mode="advisory", accept=False)
        self.reply()  # no Stop showed it (an interrupted turn): not accepted
        self.assertEqual(sdlc_scopes.mode(self.root), "full")

    def test_a_damaged_or_deleted_record_never_accepts_a_relaxation(self):
        # security r1 H3 / code r1 M4: a malformed record is said and reset to HEAD; a deleted one starts from HEAD
        import sdlc_scopes
        subprocess.run(["git", "init", "-q", self.root], check=True)
        self.write(".sdlc/state/login.md", STATE.format(stage=2))
        self.config(mode="advisory")
        self.assertEqual(sdlc_scopes.mode(self.root), "advisory")
        os.remove(self.path(".sdlc/.work/trust-anchor.json"))
        self.assertEqual(sdlc_scopes.mode(self.root), "full")  # HEAD has no config: full
        self.write(".sdlc/.work/trust-anchor.json", json.dumps({"_config": ["advisory"]}))
        self.assertEqual(sdlc_scopes.mode(self.root), "full")
        hit, raw = self.stop_blocked()
        self.assertTrue(hit, raw)
        self.assertIn("damaged", raw)
        git = ["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run(git + ["add", "-f", ".sdlc/config.json"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "advisory"], check=True)
        os.remove(self.path(".sdlc/.work/trust-anchor.json"))
        self.assertEqual(sdlc_scopes.mode(self.root), "advisory")  # the team's committed choice, fresh clone

    def test_a_nested_config_or_an_app_repos_own_config_never_decides(self):
        # security r1 H2 / code r1 H1: one resolver; a subfolder's .sdlc or an app repo's config is not the mode
        os.makedirs(self.path(".claude"), exist_ok=True)
        shutil.copy(os.path.join(PLUGIN_ROOT, "examples", "hookify", "dangerous-rm.local.md"),
                    self.path(".claude/hookify.dangerous-rm.local.md"))
        subprocess.run(["git", "init", "-q", self.root], check=True)
        self.config(root=self.path("sub"), mode="advisory")
        _, out, raw, _ = run_hook(HOOK("pretooluse.py"), {"hook_event_name": "PreToolUse", "cwd": self.path("sub"),
                                                           "tool_name": "Bash",
                                                           "tool_input": {"command": "rm -rf node_modules"}},
                                  self.root)
        self.assertEqual((out or {}).get("hookSpecificOutput", {}).get("permissionDecision"), "deny", raw)
        import sdlc_scopes
        self.config(workbench=True)
        self.write("workbench.json", json.dumps({"repos": [{"name": "api", "url": "x", "role": "app", "write": True}]}))
        subprocess.run(["git", "init", "-q", self.path("api")], check=True)
        self.config(root=self.path("api"), mode="advisory", skip=[])
        self.assertEqual(sdlc_scopes.gate_root(self.path("api/src")), self.root)
        self.assertFalse(sdlc_scopes.advisory_from(self.path("api")))  # the workbench is full
        self.config(skip=["security-review"])
        import sdlc_review_gate
        self.assertTrue(sdlc_review_gate._review_skipped(self.path("api")))  # the workbench's skip counts

    def test_always_still_forces_the_security_review_in_advisory(self):
        self.config(mode="advisory")
        payload = {"hook_event_name": "PostToolUse", "session_id": "s", "cwd": self.root, "tool_name": "Write",
                   "tool_input": {"file_path": self.path("a.js"), "content": "el.innerHTML = userInput\n"}}
        _, out, raw, _ = run_hook(HOOK("security_reminder_hook.py"), payload, self.root,
                                  {"SECURITY_WARNINGS_STATE_DIR": self.path("state"), "SDLC_SECURITY_REVIEW": "always"})
        self.assertIn("innerHTML", (out or {}).get("hookSpecificOutput", {}).get("additionalContext", ""), raw)

    def test_advisory_reaches_other_agents_through_the_host_adapter(self):
        os.makedirs(self.path(".claude"), exist_ok=True)
        shutil.copy(os.path.join(PLUGIN_ROOT, "examples", "hookify", "dangerous-rm.local.md"),
                    self.path(".claude/hookify.dangerous-rm.local.md"))
        adapter = ["python3", os.path.join(PLUGIN_ROOT, "hosts", "hook.py"), "codex", "PreToolUse"]
        call = {"hook_event_name": "PreToolUse", "cwd": self.root, "session_id": "s", "tool_name": "Bash",
                "tool_input": {"command": "rm -rf node_modules"}, "tool_use_id": "c"}
        for mode, expect in (("full", "deny"), ("advisory", None)):
            self.config(mode=mode)
            _, out, raw, _ = run_hook(adapter, call, self.root, {"CLAUDE_PROJECT_DIR": ""})
            self.assertEqual((out or {}).get("hookSpecificOutput", {}).get("permissionDecision"), expect, (mode, raw))

    def test_a_config_that_isnt_a_plain_file_reads_as_full(self):
        # security r1 H5: a FIFO config must not hang a hook
        import threading
        import sdlc_scopes
        if not hasattr(os, "mkfifo"):
            self.skipTest("no FIFOs here")
        os.makedirs(self.path(".sdlc"), exist_ok=True)
        os.mkfifo(self.path(".sdlc/config.json"))
        result = []
        t = threading.Thread(target=lambda: result.append(sdlc_scopes.configured(self.root)), daemon=True)
        t.start()
        t.join(5)
        if t.is_alive():
            with open(self.path(".sdlc/config.json"), "w"):
                pass
            self.fail("reading the mode blocked on a FIFO")
        self.assertEqual(result, [("full", [])])

    def test_scaffold_sets_the_mode_where_the_hooks_read_it(self):
        # security r2 R2-H1: run from a workbench app repo, mode/skip are refused (set at the workbench), and the
        # report gives what the hooks honour
        subprocess.run(["git", "init", "-q", self.root], check=True)
        self.config(workbench=True)
        self.write("workbench.json", json.dumps({"repos": [{"name": "api", "url": "x", "role": "app", "write": True}]}))
        subprocess.run(["git", "init", "-q", self.path("api")], check=True)
        self.config(root=self.path("api"), commands={"test": "true"}, accept=False)
        p = subprocess.run([sys.executable, SCAFFOLD, "--root", self.path("api"), "skip", "pr"], capture_output=True,
                           encoding="utf-8", errors="replace")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn(self.root, p.stdout + p.stderr)

    def test_no_stray_sdlc_folder_and_no_reads_without_a_relaxation(self):
        # security r2 R2-H2, R2-H3, R2-M1: sdlc set up in a subfolder of a git repo is the gate; the git top gets no
        # .sdlc; a config asking for nothing reads no record and runs no git; a FIFO record can't hang a hook
        from unittest import mock
        import sdlc_scopes
        import threading
        subprocess.run(["git", "init", "-q", self.root], check=True)
        app = self.path("app")
        self.config(root=app, commands={"test": "true"}, accept=False)
        self.assertEqual(sdlc_scopes.gate_root(os.path.join(app, "src"), session=False), app)
        run_hook(HOOK("trust_anchor.py"), {"hook_event_name": "Stop", "cwd": app, "stop_hook_active": False}, app,
                 {"CLAUDE_PROJECT_DIR": app})
        self.assertFalse(os.path.exists(self.path(".sdlc")))
        with mock.patch.object(sdlc_scopes, "committed", side_effect=AssertionError("git read")), \
                mock.patch.object(sdlc_scopes, "accepted", side_effect=AssertionError("record read")):
            self.assertEqual(sdlc_scopes.effective(app), ("full", []))
        if hasattr(os, "mkfifo"):
            self.config(root=app, mode="advisory", accept=False)
            os.makedirs(os.path.join(app, ".sdlc", ".work"), exist_ok=True)
            fifo = os.path.join(app, ".sdlc", ".work", "trust-anchor.json")
            if os.path.exists(fifo):
                os.remove(fifo)
            os.mkfifo(fifo)
            result = []
            t = threading.Thread(target=lambda: result.append(sdlc_scopes.mode(app)), daemon=True)
            t.start()
            t.join(5)
            if t.is_alive():
                with open(fifo, "w"):
                    pass
                self.fail("reading the accepted mode blocked on a FIFO")
            self.assertEqual(result, ["full"])

    def test_a_malformed_record_is_said_not_crashed_on(self):
        # code r2 R2-M1: unhashable or mixed skip items, a non-object feature entry
        self.write(".sdlc/state/login.md", STATE.format(stage=2))
        for bad in ({"_config": {"mode": "full", "skip": [{}]}}, {"_config": {"mode": "full", "skip": [1, "pr"]}},
                    {"login": "x"}):
            self.write(".sdlc/.work/trust-anchor.json", json.dumps(bad))
            hit, raw = self.stop_blocked()
            self.assertTrue(hit, (bad, raw))
            self.assertIn("damaged", raw)

    def test_switching_the_mode_switches_the_workflow_rule(self):
        # code r2 R2-M2: the advisory note replaces the workflow rule and back, while unedited
        self.init()
        self.assertEqual(self.sc("render", "templates/project/rules/sdlc.md", ".claude/rules/sdlc.md")[0], 0)
        self.assertEqual(self.sc("mode", "advisory")[0], 0)
        with open(self.path(".claude/rules/sdlc.md"), encoding="utf-8") as f:
            self.assertIn("advisory mode", f.read())
        self.assertEqual(self.sc("mode", "full")[0], 0)
        with open(self.path(".claude/rules/sdlc.md"), encoding="utf-8") as f:
            self.assertNotIn("advisory mode", f.read())

    def test_the_committed_config_is_read_where_the_mode_is_set(self):
        # security r3 R3-H1: in a subfolder setup, HEAD's config is the subfolder's, never the repo top's
        import sdlc_scopes
        git = ["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run(["git", "init", "-q", self.root], check=True)
        app = self.path("frontend")
        self.config(root=app, mode="advisory", accept=False)
        subprocess.run(git + ["add", "-f", "frontend/.sdlc/config.json"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "advisory"], check=True)
        self.assertEqual(sdlc_scopes.mode(app), "advisory")  # the team's committed choice, no record
        self.config(root=self.root, mode="advisory", accept=False)  # the repo top's config: never the gate here
        subprocess.run(git + ["add", "-f", ".sdlc/config.json"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "top"], check=True)
        shutil.rmtree(self.path(".sdlc"))
        with open(os.path.join(app, ".sdlc", "config.json"), "w", encoding="utf-8") as f:
            json.dump({"mode": "full"}, f)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "full"], check=True)
        self.config(root=app, mode="advisory", accept=False)
        self.assertEqual(sdlc_scopes.mode(app), "full")  # frontend's HEAD says full; the top's isn't read

    def test_scaffold_refuses_when_the_session_reads_another_folder(self):
        # security r3 R3-H2: a nested repo with its own .sdlc, the session at the outer one
        subprocess.run(["git", "init", "-q", self.root], check=True)
        self.config(commands={"test": "true"}, accept=False)
        sub = self.path("sub")
        subprocess.run(["git", "init", "-q", sub], check=True)
        self.config(root=sub, commands={"test": "true"}, accept=False)
        env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
        env["CLAUDE_PROJECT_DIR"] = self.root
        p = subprocess.run([sys.executable, SCAFFOLD, "--root", sub, "skip", "pr"], capture_output=True,
                           encoding="utf-8", errors="replace", env=env)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertNotIn("skip", json.load(open(os.path.join(sub, ".sdlc", "config.json"), encoding="utf-8")))

    def test_the_anchor_record_is_never_written_through_a_fifo_or_a_link(self):
        # security r3 R3-M1: a FIFO record can't hang the Stop hook; a link isn't written through
        if not hasattr(os, "mkfifo"):
            self.skipTest("no FIFOs here")
        import threading
        self.write(".sdlc/state/login.md", STATE.format(stage=2))
        os.makedirs(self.path(".sdlc/.work"), exist_ok=True)
        record = self.path(".sdlc/.work/trust-anchor.json")
        os.mkfifo(record)
        done = []
        t = threading.Thread(target=lambda: done.append(self.stop_blocked()), daemon=True)
        t.start()
        t.join(8)
        if t.is_alive():
            with open(record, "w"):
                pass
            self.fail("the trust anchor blocked on a FIFO record")
        self.assertTrue(os.path.isfile(record) and not os.path.islink(record))
        outside = self.path("../" + os.path.basename(self.root) + "-outside.json")
        self.addCleanup(lambda: os.path.exists(outside) and os.remove(outside))
        with open(outside, "w", encoding="utf-8") as f:
            f.write("{}")
        os.remove(record)
        os.symlink(outside, record)
        self.stop_blocked()
        with open(outside, encoding="utf-8") as f:
            self.assertEqual(f.read(), "{}")

    def test_a_session_above_the_repo_reads_and_records_no_mode(self):
        # security r4 R4-L1: the session's folder has no .sdlc above it: every reader agrees there is no gate
        parent = os.path.realpath(os.path.join(self.root, ".."))
        self.config(mode="advisory")
        env = {"CLAUDE_PROJECT_DIR": parent}
        start = {"hook_event_name": "SessionStart", "cwd": self.root, "source": "startup"}
        _, _, raw, _ = run_hook(HOOK("session_status.py"), start, self.root, env)
        self.assertNotIn("mode advisory", raw)
        p = subprocess.run([sys.executable, SCAFFOLD, "--root", self.root, "skip", "--clear"], capture_output=True,
                           encoding="utf-8", errors="replace",
                           env={**{k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}, **env})
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)

    def test_the_record_is_never_written_through_a_linked_folder(self):
        # security r4 R4-L2: a linked .sdlc/.work must not carry the record out of the repo
        import sdlc_scopes
        outside = os.path.realpath(self.path("../" + os.path.basename(self.root) + "-work"))
        os.makedirs(outside, exist_ok=True)
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        os.makedirs(self.path(".sdlc"), exist_ok=True)
        os.symlink(outside, self.path(".sdlc/.work"), target_is_directory=True)
        self.assertFalse(sdlc_scopes.write_record(self.root, sdlc_scopes.ANCHOR, {}))
        self.assertEqual(os.listdir(outside), [])

    def test_a_file_swapped_for_a_fifo_after_the_check_is_never_waited_on(self):
        # security review R3-L2 of 2026-11-23-l-configurable-stages: the check and the open are one step
        from unittest import mock
        import threading
        import sdlc_scopes
        if not hasattr(os, "mkfifo"):
            self.skipTest("no FIFOs here")
        os.makedirs(self.path(".sdlc"), exist_ok=True)
        os.mkfifo(self.path(".sdlc/config.json"))
        result = []
        with mock.patch("os.path.isfile", return_value=True), mock.patch("os.path.exists", return_value=False):
            t = threading.Thread(target=lambda: result.append(sdlc_scopes.configured(self.root)), daemon=True)
            t.start()
            t.join(5)
        if t.is_alive():
            with open(self.path(".sdlc/config.json"), "w"):
                pass
            self.fail("a FIFO was opened and waited on")
        self.assertEqual(result, [("full", [])])

    def test_an_accepted_mode_change_reaches_the_agent_at_once(self):
        # security review R3-L5: the status line is built at session start; the reply that accepts says the new mode
        self.write(".sdlc/state/login.md", STATE.format(stage=2))
        self.config(mode="full", accept=False)
        self.stop_blocked()
        self.config(skip=["pr"], accept=False)
        self.assertTrue(self.stop_blocked()[0])
        _, out, raw, _ = run_hook(HOOK("trust_anchor.py"), {"hook_event_name": "UserPromptSubmit", "cwd": self.root,
                                                            "prompt": "ok"}, self.root)
        context = (out or {}).get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertIn("skip pr", context, raw)

    def test_the_acceptance_message_names_what_is_enforced(self):
        # security review SEC-4: config changed between the notice and the reply: the message follows effective()
        self.write(".sdlc/state/login.md", STATE.format(stage=2))
        self.config(mode="full", accept=False)
        self.stop_blocked()
        self.config(mode="advisory", accept=False)
        self.assertTrue(self.stop_blocked()[0])
        self.config(mode="full", accept=False)  # changed back before the reply
        _, out, raw, _ = run_hook(HOOK("trust_anchor.py"), {"hook_event_name": "UserPromptSubmit", "cwd": self.root,
                                                            "prompt": "ok"}, self.root)
        context = (out or {}).get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertNotIn("advisory: no sdlc hook", context, raw)
        self.assertIn("full, nothing skipped", context, raw)  # said, and as the hooks enforce it

    # AC-008
    def test_the_flow_text_names_skip_and_advisory(self):
        def text(rel):
            with open(os.path.join(PLUGIN_ROOT, rel), encoding="utf-8") as f:
                return f.read()

        def section(body):
            start = body.index("**Configured skips and advisory mode.**")
            return body[start:body.index("\n\n", start)]

        skill, start = text("skills/orchestrator/SKILL.md"), text("commands/start.md")
        self.assertEqual(section(skill), section(start))
        for body in (section(skill), text("skills/orchestrator/references/flow.md"),
                     text("skills/orchestrator/references/s-track.md")):
            for word in ("`skip`", "security-review", "`pr`", "advisory"):
                self.assertIn(word, body)

    # AC-009
    def test_advisory_setup_renders_nothing_that_enforces(self):
        self.init()
        self.assertEqual(self.sc("mode", "advisory")[0], 0)
        code, out = self.sc("guardrails", "--render")
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.isdir(self.path(".claude/hookify")) and os.listdir(self.path(".claude/hookify")))
        folder = os.path.join(PLUGIN_ROOT, "skills", "setting-up-projects")
        with open(os.path.join(folder, "SKILL.md"), encoding="utf-8") as f:
            setup = f.read()
        self.assertIn("full or advisory", setup)  # asked first, and the steps it skips are named where it points
        with open(os.path.join(folder, "references", "advisory.md"), encoding="utf-8") as f:
            reference = f.read()
        for step in ("guardrails", "CI", "constitution", "templates/project/advisory/sdlc.md"):
            self.assertIn(step, reference)


if __name__ == "__main__":
    unittest.main()
