"""hosts/hook.py: the plugin's hooks under Codex and Cursor, from payloads captured from Codex 0.162 and
cursor-agent 2026.10.22 (2026-10-25)."""
import importlib.util
import io
import json
import os
import shutil
import unittest
from unittest import mock

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



class CursorHookTest(ProjectTestCase):
    def cursor(self, event, cursor_event, **fields):
        # Cursor runs plugin hooks in the plugin folder and sends an empty cwd; the workspace comes in workspace_roots
        payload = dict({"hook_event_name": cursor_event, "cwd": "", "workspace_roots": [self.root],
                        "conversation_id": "c"}, **fields)
        code, out, raw, err = run_hook(ADAPTER + ["cursor", event], payload, PLUGIN_ROOT, {"CLAUDE_PROJECT_DIR": ""})
        self.assertEqual(code, 0, err)
        self.assertIsNotNone(out, f"adapter printed non-JSON: {raw!r}")
        return out

    def test_a_guardrail_denies_a_command_in_cursor_shape(self):
        os.makedirs(self.path(".claude"), exist_ok=True)
        shutil.copy(os.path.join(PLUGIN_ROOT, "examples", "hookify", "dangerous-rm.local.md"),
                    self.path(".claude/hookify.dangerous-rm.local.md"))
        out = self.cursor("PreToolUse", "preToolUse", tool_name="Shell",
                          tool_input={"command": "rm -rf node_modules", "cwd": "", "timeout": 30000})
        self.assertEqual(out["permission"], "deny")
        self.assertIn("block-dangerous-rm", out["agent_message"])
        self.assertEqual(self.cursor("PreToolUse", "preToolUse", tool_name="Shell", tool_input={"command": "ls"}), {})

    def test_an_edit_after_the_tests_sends_a_follow_up_once(self):
        self.write(".sdlc/login/state.md", "# Feature: login\nStatus: active\nCurrent: Stage 5\n\n"
                                           "## Commands\n- test: `pytest`\n")
        self.cursor("PostToolUseFailure", "postToolUseFailure", tool_name="Shell", tool_input={"command": "pytest"},
                    error_message="Command failed with exit code 1", failure_type="error")
        self.assertEqual(self.cursor("Stop", "stop", status="completed", loop_count=0), {})
        self.cursor("PostToolUse", "postToolUse", tool_name="Write",
                    tool_input={"file_path": self.path("a.py"), "content": "x = 2\n"},
                    tool_output='{"success":true}')
        self.assertIn("a.py", self.cursor("Stop", "stop", status="completed", loop_count=0)["followup_message"])
        self.assertEqual(self.cursor("Stop", "stop", status="completed", loop_count=1), {})  # no loop


class AntigravityHookTest(ProjectTestCase):
    def agy(self, event, **fields):
        # Antigravity runs plugin hooks in the plugin folder; the workspace comes in workspacePaths, with forward slashes
        payload = dict({"conversationId": "c", "workspacePaths": [self.root.replace("\\", "/")]}, **fields)
        code, out, raw, err = run_hook(ADAPTER + ["antigravity", event], payload, PLUGIN_ROOT, {"CLAUDE_PROJECT_DIR": ""})
        self.assertEqual(code, 0, err)
        self.assertIsNotNone(out, f"adapter printed non-JSON: {raw!r}")
        return out

    def test_a_guardrail_denies_a_command_and_other_calls_keep_the_usual_check(self):
        os.makedirs(self.path(".claude"), exist_ok=True)
        shutil.copy(os.path.join(PLUGIN_ROOT, "examples", "hookify", "dangerous-rm.local.md"),
                    self.path(".claude/hookify.dangerous-rm.local.md"))
        out = self.agy("PreToolUse", stepIdx=2,
                       toolCall={"name": "run_command", "args": {"CommandLine": "rm -rf node_modules"}})
        self.assertEqual(out["decision"], "deny")
        self.assertIn("block-dangerous-rm", out["reason"])
        # Antigravity denies a call whose hook gives no decision, so a call no rule objects to, or an error, gets `ask`
        self.assertEqual(self.agy("PreToolUse", toolCall={"name": "run_command", "args": {"CommandLine": "ls"}}),
                         {"decision": "ask"})
        self.assertEqual(run_hook(ADAPTER + ["antigravity", "PreToolUse"], "not json", self.root)[:2],
                         (0, {"decision": "ask"}))

    def test_an_edit_after_the_tests_continues_the_turn_once(self):
        self.write(".sdlc/login/state.md", "# Feature: login\nStatus: active\nCurrent: Stage 5\n\n"
                                           "## Commands\n- test: `pytest`\n")
        self.write("a.py", "x = 1\n")
        # A command's result comes with no exit code, even when it fails: the run counts, its result is unknown
        self.agy("PostToolUse", error="", toolCall={"name": "run_command", "args": {"CommandLine": "pytest"}})
        stop = {"terminationReason": "NO_TOOL_CALL", "fullyIdle": True, "error": ""}
        self.assertEqual(self.agy("Stop", executionNum=0, **stop), {})
        self.agy("PostToolUse", error="", toolCall={"name": "edit_file", "args": {
            "Path": self.path("a.py"), "Target": "x = 1", "Replacement": "x = 2"}})
        out = self.agy("Stop", executionNum=0, **stop)
        self.assertEqual(out["decision"], "continue")
        self.assertIn("a.py", out["reason"])
        self.assertEqual(self.agy("Stop", executionNum=1, **stop), {})  # no loop


def load_adapter():
    spec = importlib.util.spec_from_file_location("host_hook", os.path.join(PLUGIN_ROOT, "hosts", "hook.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class GuardrailCoverageTest(unittest.TestCase):
    """What the guardrails see of an edit: nothing an agent sends is left out of the check."""

    def test_lines_after_an_indented_patch_header_count_for_the_file_before_it_too(self):
        # Codex may read " *** Update File: b.py" as a context line of a.py, so "+secret" may land in a.py
        patch = "*** Begin Patch\n*** Update File: a.py\n@@\n *** Update File: b.py\n+secret\n*** End Patch"
        edits = {os.path.basename(e["tool_input"]["file_path"]): e["tool_input"]["new_string"]
                 for e in load_adapter().patch_edits(patch, "/r")}
        self.assertEqual(edits, {"a.py": "secret\n", "b.py": "secret\n"})

    def test_a_call_with_more_edits_than_can_be_checked_in_time_is_denied(self):
        hook = load_adapter()
        hook.DEADLINE = 0
        stdin = io.TextIOWrapper(io.BytesIO(json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}).encode()))
        with mock.patch.object(hook.sys, "stdin", stdin):
            out = hook.main(["hook.py", "codex", "PreToolUse"])
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("Split the change", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_antigravity_write_tools_are_checked_with_every_argument(self):
        tool = load_adapter().agy_tool
        nested = tool({"name": "replace_file_content", "args": {
            "TargetFile": "/r/a.py", "ReplacementChunks": [{"TargetContent": "x", "ReplacementContent": "secret"}]}}, "/r")
        self.assertIn("secret", nested[0]["tool_input"]["new_string"])
        patched = tool({"name": "apply_patch", "args": {
            "Patch": "*** Begin Patch\n*** Add File: b.py\n+secret\n*** End Patch"}}, "/r")
        self.assertEqual([(os.path.basename(e["tool_input"]["file_path"]), e["tool_input"]["content"]) for e in patched],
                         [("b.py", "secret\n")])


if __name__ == "__main__":
    unittest.main()
