"""hooks/prove_budget.py: in Prove (Stage 5), non-project shell commands are killed at 120 s and never run in the background."""
import json
import os
import unittest

from helpers import HOOKS, PLUGIN_ROOT, ProjectTestCase, run_hook

HOOK = ["python3", os.path.join(HOOKS, "prove_budget.py")]
STATE = "# Feature: login\nStatus: active\nProcess: 2\nCurrent: Stage {stage} – Prove\n"


class ProveBudgetTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "npm test"}}))

    def call(self, stage, tool="Bash", **tool_input):
        self.write(".sdlc/login/state.md", STATE.format(stage=stage))
        payload = {"hook_event_name": "PreToolUse", "cwd": self.root, "tool_name": tool, "tool_input": tool_input}
        code, out, raw, err = run_hook(HOOK, payload, self.root)
        self.assertEqual(code, 0, err)
        return (out or {}).get("hookSpecificOutput", {})

    def test_non_project_commands_are_killed_at_120_seconds(self):
        out = self.call(5, command="node probe.js", description="probe", timeout=600000)
        self.assertIsNone(out.get("permissionDecision"))  # the user's permission rules still decide
        self.assertRegex(out["updatedInput"]["command"], r"^g?timeout -k 5 120 node probe\.js$")
        self.assertEqual(out["updatedInput"]["description"], "probe")
        self.assertEqual(out["updatedInput"]["timeout"], 130000)  # past the kill, so Claude Code never backgrounds it
        # A loop can't take the prefix, and hiding it in `bash -c` would slip past the user's deny rules
        self.assertEqual(self.call(5, command="until grep -q done log; do sleep 3; done").get("permissionDecision"), "deny")
        # A heredoc append to the change file is refused too, and the reason points at the file tools instead
        out = self.call(5, command="cd app && cat >> docs/sdlc/changes/f.md <<'EOF'\n## Review\nEOF")
        self.assertEqual(out.get("permissionDecision"), "deny")
        self.assertIn("Edit or Write tool", out["permissionDecisionReason"])
        # Variables set first, as the relay's state.py calls do: the assignments run nothing, the call is timed
        out = self.call(5, command='S="python3 state.py"; F=login; $S round $F 1 fail "R1"')
        self.assertRegex(out["updatedInput"]["command"],
                         r'^S="python3 state.py"; F=login; g?timeout -k 5 120 \$S round \$F 1 fail "R1"$')

    def test_quick_read_only_steps_chain_untimed(self):
        cmd = "git remote -v; git branch --show-current; tail -5 docs/change.md"
        out = self.call(5, command=cmd)
        self.assertIsNone(out.get("permissionDecision"))
        self.assertEqual(out["updatedInput"]["command"], cmd)
        # Following a file never ends: still killed at 120 s
        self.assertRegex(self.call(5, command="tail -f log")["updatedInput"]["command"], r"^g?timeout -k 5 120 tail -f log$")

    def test_ships_one_call_runs_whole(self):
        ship = os.path.join(PLUGIN_ROOT, "scripts", "ship.py")
        cmd = (f'python3 "{ship}" login --message "feat: x" && git commit -F .sdlc/.work/commit-msg.txt'
               " && git push -u origin HEAD && gh pr create --fill")
        self.assertEqual(self.call(5, command=cmd), {})
        self.assertNotEqual(self.call(5, command=cmd + " && sleep 900"), {})  # nothing else rides along

    def test_project_commands_are_left_alone(self):
        self.assertEqual(self.call(5, command="cd app && npm test 2>&1 | tail -5", timeout=600000), {})
        # A project command doesn't carry what is chained after it
        self.assertNotEqual(self.call(5, command="npm test && sleep 900"), {})
        self.assertEqual(self.call(5, command="npm test; node probe.js", run_in_background=True)
                         .get("permissionDecision"), "deny")
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "npm run build && npm test"}}))
        self.assertEqual(self.call(5, command="npm run build && npm test -- --ci"), {})  # a chained project command
        self.assertNotEqual(self.call(5, command="npm run build && npm test && sleep 900"), {})
        # verify.py runs only the project's commands and each acceptance test's own Run command (ADR 0013)
        verify = os.path.join(PLUGIN_ROOT, "scripts", "verify.py")
        self.assertEqual(self.call(5, command=f'python3 "{verify}" red AC-001', timeout=600000), {})
        self.assertEqual(self.call(5, command='python3 "${CLAUDE_PLUGIN_ROOT}/scripts/verify.py"'), {})  # unexpanded
        self.assertIn("updatedInput", self.call(5, command='python3 "/tmp/scripts/verify.py"'))  # a lookalike
        self.assertNotEqual(self.call(5, command=f'python3 "{verify}"; node probe.js'), {})  # not exempt
        self.assertNotEqual(self.call(5, command=f'python3 "{verify}"\nnode probe.js'), {})  # a second line
        self.assertNotEqual(self.call(5, command="cd /elsewhere && python3 scripts/verify.py"), {})  # relative
        smuggled = os.path.join(PLUGIN_ROOT, "scripts", "$(node probe.js)", "..", "verify.py")
        self.assertNotEqual(self.call(5, command=f'python3 "{smuggled}"'), {})  # the shell runs $(...) first
        escaped = os.path.join(PLUGIN_ROOT, "scripts", "verify.py").replace("\\", "/").replace("verify", "veri\\fy")
        self.assertNotEqual(self.call(5, command=f"python3 {escaped}"), {})  # only the exact spellings count

    def test_background_runs_are_refused_only_in_prove(self):
        out = self.call(5, command="node probe.js", run_in_background=True)
        self.assertEqual(out.get("permissionDecision"), "deny")
        self.assertTrue(out.get("permissionDecisionReason"))
        self.assertEqual(self.call(5, "Monitor", command="until grep -q done log; do sleep 2; done")
                         .get("permissionDecision"), "deny")
        self.assertEqual(self.call(5, "PowerShell", command="node probe.js").get("permissionDecision"), "deny")
        self.assertEqual(self.call(4, command="node probe.js", run_in_background=True), {})


if __name__ == "__main__":
    unittest.main()
