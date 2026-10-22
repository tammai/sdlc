"""hookify: hooks/pretooluse.py, posttooluse.py, stop.py, userpromptsubmit.py reading .claude/hookify.*.local.md."""
import os
import shutil
import unittest

from helpers import HOOKS, PLUGIN_ROOT, ProjectTestCase, run_hook

EXAMPLES = os.path.join(PLUGIN_ROOT, "examples", "hookify")


def hook(name):
    return ["python3", os.path.join(HOOKS, name)]


class HookifyTest(ProjectTestCase):
    def install(self, example):
        os.makedirs(self.path(".claude"), exist_ok=True)
        shutil.copy(os.path.join(EXAMPLES, example), self.path(".claude/hookify." + example.split(".", 1)[0] + ".local.md"))

    def pre(self, tool, **tool_input):
        code, out, raw, err = run_hook(hook("pretooluse.py"),
                                       {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input},
                                       self.root)
        self.assertEqual(code, 0, err)
        self.assertIsNotNone(out, f"hook printed non-JSON: {raw!r}")
        self.assertNotIn("error", out.get("systemMessage", "").lower(), out)
        return out

    def assertDenied(self, out):
        self.assertEqual(out.get("hookSpecificOutput", {}).get("permissionDecision"), "deny", out)

    def test_no_rules_allows_everything(self):
        self.assertEqual(self.pre("Bash", command="rm -rf /"), {})

    def test_dangerous_rm_is_blocked(self):
        self.install("dangerous-rm.local.md")
        for cmd in ["rm -rf /", "rm -rf node_modules", "sudo rm  -rf ~/x"]:
            with self.subTest(cmd=cmd):
                out = self.pre("Bash", command=cmd)
                self.assertDenied(out)
                self.assertIn("block-dangerous-rm", out["systemMessage"])

    def test_safe_bash_is_allowed(self):
        self.install("dangerous-rm.local.md")
        self.assertEqual(self.pre("Bash", command="rm file.txt"), {})

    def test_bash_rule_ignores_file_tools(self):
        self.install("dangerous-rm.local.md")
        self.assertEqual(self.pre("Write", file_path="x.sh", content="rm -rf /"), {})

    def test_file_rule_warns_without_blocking(self):
        self.install("console-log-warning.local.md")
        out = self.pre("Write", file_path=self.path("src/a.ts"), content="console.log(user)")
        self.assertNotIn("permissionDecision", out["hookSpecificOutput"])
        self.assertIn("warn-console-log", out["systemMessage"])
        self.assertIn("warn-console-log", out["hookSpecificOutput"]["additionalContext"])  # reaches Claude

    def test_block_tells_claude_why(self):
        self.install("dangerous-rm.local.md")
        out = self.pre("Bash", command="rm -rf build")
        self.assertIn("block-dangerous-rm", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_committed_team_rules_are_loaded(self):
        os.makedirs(self.path(".claude/hookify"))
        shutil.copy(os.path.join(EXAMPLES, "dangerous-rm.local.md"), self.path(".claude/hookify/no-rm.md"))
        self.assertDenied(self.pre("Bash", command="rm -rf build"))

    def test_posttooluse_is_not_registered(self):
        with open(os.path.join(HOOKS, "hooks.json")) as f:
            self.assertNotIn("posttooluse.py", f.read())

    def test_condition_rule_on_file_path(self):
        self.install("sensitive-files-warning.local.md")
        self.assertIn("warn-sensitive-files",
                      self.pre("Edit", file_path=self.path(".env.local"), old_string="a", new_string="b")["systemMessage"])
        self.assertEqual(self.pre("Edit", file_path=self.path("src/env.ts"), old_string="a", new_string="b"), {})

    def test_disabled_rule_is_ignored(self):
        self.install("require-tests-stop.local.md")  # enabled: false
        transcript = self.write("t.jsonl", '{"role":"assistant"}\n')
        _, out, _, _ = run_hook(hook("stop.py"), {"hook_event_name": "Stop", "transcript_path": transcript}, self.root)
        self.assertEqual(out, {})

    def test_enabled_stop_rule_blocks(self):
        self.install("require-tests-stop.local.md")
        rule = self.path(".claude/hookify.require-tests-stop.local.md")
        with open(rule) as f:
            text = f.read().replace("enabled: false", "enabled: true")
        self.write(".claude/hookify.require-tests-stop.local.md", text)
        transcript = self.write("t.jsonl", '{"role":"assistant","text":"done"}\n')
        _, out, _, _ = run_hook(hook("stop.py"), {"hook_event_name": "Stop", "transcript_path": transcript}, self.root)
        self.assertEqual(out.get("decision"), "block")
        self.write("t.jsonl", '{"role":"assistant","text":"ran npm test"}\n')
        _, out, _, _ = run_hook(hook("stop.py"), {"hook_event_name": "Stop", "transcript_path": transcript}, self.root)
        self.assertEqual(out, {})

    def test_every_hookify_entry_point_runs_clean(self):
        self.install("dangerous-rm.local.md")
        for name, payload in [
            ("posttooluse.py", {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}}),
            ("stop.py", {"hook_event_name": "Stop"}),
            ("userpromptsubmit.py", {"hook_event_name": "UserPromptSubmit", "prompt": "hi"}),
        ]:
            with self.subTest(hook=name):
                code, out, raw, err = run_hook(hook(name), payload, self.root)
                self.assertEqual(code, 0, err)
                self.assertIsNotNone(out, raw)
                self.assertNotIn("error", out.get("systemMessage", "").lower(), out)

    def test_bad_input_never_blocks(self):
        self.install("dangerous-rm.local.md")
        code, out, _, _ = run_hook(hook("pretooluse.py"), "not json", self.root)
        self.assertEqual(code, 0)
        self.assertNotIn("hookSpecificOutput", out or {})


if __name__ == "__main__":
    unittest.main()
