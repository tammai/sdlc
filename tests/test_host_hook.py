"""hosts/hook.py: the plugin's hooks under Codex, from payloads captured from Codex 0.162 (2026-10-25)."""
import os
import shutil
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase, run_hook

ADAPTER = ["python3", os.path.join(PLUGIN_ROOT, "hosts", "hook.py")]


class CodexHookTest(ProjectTestCase):
    def codex(self, event, **fields):
        code, out, raw, err = run_hook(ADAPTER + ["codex", event],
                                       dict({"hook_event_name": event, "cwd": self.root, "session_id": "s"}, **fields),
                                       self.root)
        self.assertEqual(code, 0, err)
        self.assertIsNotNone(out, f"adapter printed non-JSON: {raw!r}")
        return out

    def test_a_guardrail_denies_a_command_in_codex_shape(self):
        os.makedirs(self.path(".claude"), exist_ok=True)
        shutil.copy(os.path.join(PLUGIN_ROOT, "examples", "hookify", "dangerous-rm.local.md"),
                    self.path(".claude/hookify.dangerous-rm.local.md"))
        out = self.codex("PreToolUse", tool_name="Bash", tool_input={"command": "rm -rf node_modules"},
                         tool_use_id="exec-1")
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("block-dangerous-rm", out["hookSpecificOutput"]["permissionDecisionReason"])
        self.assertEqual(self.codex("PreToolUse", tool_name="Bash", tool_input={"command": "ls"}), {})
        self.assertEqual(run_hook(ADAPTER + ["codex", "PreToolUse"], "not json", self.root)[:2], (0, {}))  # never fails the turn

    def test_a_patch_after_the_tests_keeps_stage_5_from_finishing(self):
        self.write(".sdlc/login/state.md", "# Feature: login\nStatus: active\nCurrent: Stage 5\n\n"
                                           "## Commands\n- test: `pytest`\n")
        self.write("a.py", "x = 1\n")
        # Codex sends a command's output without its exit code: the run counts, its result is unknown
        self.assertEqual(self.codex("PostToolUse", tool_name="Bash", tool_input={"command": "pytest"},
                                    tool_response="1 passed\r\n"), {})
        self.assertEqual(self.codex("Stop", stop_hook_active=False, last_assistant_message="Done."), {})
        self.codex("PostToolUse", tool_name="apply_patch",
                   tool_input={"command": "*** Begin Patch\n*** Update File: a.py\n@@\n-x = 1\n+x = 2\n*** End Patch"},
                   tool_response="Exit code: 0\nOutput:\nSuccess. Updated the following files:\nM a.py\n")
        out = self.codex("Stop", stop_hook_active=False, last_assistant_message="Done.")
        self.assertEqual(out["decision"], "block")
        self.assertIn("a.py", out["reason"])
        self.assertNotIn("decision", self.codex("Stop", stop_hook_active=True))  # no loop: the second stop only warns


if __name__ == "__main__":
    unittest.main()
