"""hookify: hooks/pretooluse.py, stop.py, userpromptsubmit.py reading .claude/hookify.*.local.md."""
import os
import shutil
import signal
import time
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

    RM_RULE = ("---\nname: no-x\nenabled: true\nevent: bash\naction: block\nconditions:\n"
               "  - field: command\n    operator: regex_match\n    pattern: forbidden\n---\nnope\n")

    def run_pre(self, command):
        code, out, raw, err = run_hook(hook("pretooluse.py"),
                                       {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}},
                                       self.root)
        self.assertEqual(code, 0, err)
        return out

    def test_notebook_cells_are_a_file_event(self):
        self.write(".claude/hookify/no-secret.md", self.RM_RULE.replace("event: bash", "event: file")
                   .replace("field: command", "field: new_text"))
        out = self.pre("NotebookEdit", notebook_path=self.path("a.ipynb"), new_source="forbidden")
        self.assertDenied(out)

    def test_block_on_prompt_blocks_the_prompt(self):
        self.write(".claude/hookify/no-prompt.md", self.RM_RULE.replace("event: bash", "event: prompt")
                   .replace("field: command", "field: user_prompt"))
        # Claude Code names the field `prompt`; the rule field stays `user_prompt`
        _, out, _, _ = run_hook(hook("userpromptsubmit.py"), {"hook_event_name": "UserPromptSubmit", "prompt": "forbidden"}, self.root)
        self.assertEqual(out.get("decision"), "block", out)

    def test_stop_and_bash_rules_stay_on_their_own_events(self):
        self.install("require-tests-stop.local.md")
        rule = self.path(".claude/hookify.require-tests-stop.local.md")
        with open(rule, encoding="utf-8") as f:
            text = f.read().replace("enabled: false", "enabled: true")
        with open(rule, "w", encoding="utf-8") as f:
            f.write(text)
        self.write("t.jsonl", '{"role":"user","text":"hi"}\n')
        _, out, _, _ = run_hook(hook("pretooluse.py"),
                                {"hook_event_name": "PreToolUse", "tool_name": "Read", "tool_input": {"file_path": "a.py"},
                                 "transcript_path": self.path("t.jsonl")}, self.root)
        self.assertEqual(out, {})
        self.write(".claude/hookify/no-x.md", self.RM_RULE)
        self.assertDenied(self.pre("PowerShell", command="forbidden"))

    def test_own_errors_print_nothing(self):
        for name in ("pretooluse.py", "stop.py", "userpromptsubmit.py"):
            with self.subTest(hook=name):
                code, _, raw, _ = run_hook(hook(name), "not json", self.root)
                self.assertEqual((code, raw), (0, ""))

    def test_formatting_slips_do_not_disarm_a_rule(self):
        slips = {"leading blank line": lambda t: "\n" + t, "BOM": lambda t: "\ufeff" + t,
                 "capitalised action": lambda t: t.replace("action: block", "action: Block"),
                 "capitalised event": lambda t: t.replace("event: bash", "event: Bash"),
                 "capitalised operator": lambda t: t.replace("regex_match", "Regex_Match")}
        for name, slip in slips.items():
            with self.subTest(slip=name):
                self.write(".claude/hookify/no-x.md", slip(self.RM_RULE))
                self.assertDenied(self.run_pre("echo forbidden"))

    def test_broken_rules_are_reported_not_silent(self):
        for name, text, expect in [
            ("typo operator", self.RM_RULE.replace("regex_match", "regex_matc"), "unknown operator"),
            ("unknown event", self.RM_RULE.replace("event: bash", "event: shell"), "unknown event"),
            ("unknown action", self.RM_RULE.replace("action: block", "action: deny"), "unknown action"),
            ("bad regex", self.RM_RULE.replace("forbidden", "(unclosed"), "invalid regex"),
            ("no frontmatter", "just text", "no valid frontmatter"),
        ]:
            with self.subTest(rule=name):
                self.write(".claude/hookify/broken.md", text)
                out = self.run_pre("ls")
                self.assertIn("broken.md", out["systemMessage"])
                self.assertIn(expect, out["systemMessage"])

    @unittest.skipUnless(hasattr(signal, "setitimer"), "no SIGALRM on this platform")
    def test_catastrophic_regex_is_skipped(self):
        self.write(".claude/hookify/slow.md", self.RM_RULE.replace("forbidden", "(a+)+$"))
        started = time.time()
        out = self.run_pre("a" * 40 + "!")
        self.assertLess(time.time() - started, 8)
        self.assertIn("skipped", out["systemMessage"])
        self.assertNotIn("hookSpecificOutput", out)

    def test_long_rule_messages_are_capped(self):
        self.write(".claude/hookify/chatty.md", self.RM_RULE.replace("nope", "x" * 5000))
        out = self.run_pre("forbidden")
        self.assertLess(len(out["hookSpecificOutput"]["permissionDecisionReason"]), 2200)
        self.assertIn("[truncated]", out["hookSpecificOutput"]["permissionDecisionReason"])


if __name__ == "__main__":
    unittest.main()
