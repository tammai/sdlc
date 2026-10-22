"""templates/project/hookify/sdlc-*.md: each guardrail fires on what it targets and stays quiet otherwise."""
import glob
import os
import shutil
import unittest

from helpers import HOOKS, PLUGIN_ROOT, ProjectTestCase, run_hook

RULES = os.path.join(PLUGIN_ROOT, "templates", "project", "hookify")

# (rule, tool, tool_input, should_fire)
BASH = [
    ("sdlc-dangerous-rm", "rm -rf /", True),
    ("sdlc-dangerous-rm", "rm -rf ~", True),
    ("sdlc-dangerous-rm", "rm -fr ..", True),
    ("sdlc-dangerous-rm", "sudo rm -rf --no-preserve-root /", True),
    ("sdlc-dangerous-rm", "rm -rf .git", True),
    ("sdlc-dangerous-rm", "cd x && rm -rf * ", True),
    ("sdlc-dangerous-rm", "rm -rf dist", False),
    ("sdlc-dangerous-rm", "rm -rf ./node_modules", False),
    ("sdlc-dangerous-rm", "rm -rf .sdlc/.work/tmp", False),
    ("sdlc-force-push-main", "git push --force origin main", True),
    ("sdlc-force-push-main", "git push -f origin master", True),
    ("sdlc-force-push-main", "git push --force-with-lease origin main", True),
    ("sdlc-force-push-main", "git push origin +main", True),
    ("sdlc-force-push-main", "git push --force origin feat/login", False),
    ("sdlc-force-push-main", "git push origin main", False),
    ("sdlc-reset-hard", "git reset --hard HEAD~1", True),
    ("sdlc-reset-hard", "git clean -fd", True),
    ("sdlc-reset-hard", "git checkout -- .", True),
    ("sdlc-reset-hard", "git reset --soft HEAD~1", False),
    ("sdlc-reset-hard", "git checkout -- src/a.ts", False),
]

FILES = [
    ("sdlc-sensitive-files", "config/.env", "X=1", True),
    ("sdlc-sensitive-files", ".env.local", "X=1", True),
    ("sdlc-sensitive-files", "certs/server.pem", "x", True),
    ("sdlc-sensitive-files", "src/environment.ts", "x", False),
    ("sdlc-secret-values", "src/a.ts", 'const k = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz"', True),
    ("sdlc-secret-values", "src/a.ts", 'const k = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"', True),
    ("sdlc-secret-values", "src/a.ts", "key = AKIAABCDEFGHIJKLMNOP", True),
    ("sdlc-secret-values", "k.pem", "-----BEGIN RSA PRIVATE KEY-----\nabc", True),
    ("sdlc-secret-values", "src/a.ts", "const k = process.env.ANTHROPIC_API_KEY", False),
    ("sdlc-console-log", "src/a.ts", "console.log(user)", True),
    ("sdlc-console-log", "src/a.ts", "console.error(err)", False),
    ("sdlc-console-log", "README.md", "console.log(x)", False),
    ("sdlc-focused-tests", "src/a.test.ts", "it.only('works', () => {})", True),
    ("sdlc-focused-tests", "src/a.test.ts", "describe.skip('x', () => {})", True),
    ("sdlc-focused-tests", "tests/test_a.py", "@pytest.mark.skip\ndef test_a(): ...", True),
    ("sdlc-focused-tests", "src/a.test.ts", "it('works', () => {})", False),
    ("sdlc-suppressions", "src/a.ts", "// @ts-ignore\nfoo()", True),
    ("sdlc-suppressions", "src/a.ts", "/* eslint-disable */", True),
    ("sdlc-suppressions", "a.py", "x = f()  # type: ignore", True),
    ("sdlc-suppressions", "src/a.ts", "foo()", False),
    ("sdlc-narration-comments", "src/a.ts", "// Step 1: load the user\nconst u = load()", True),
    ("sdlc-narration-comments", "src/a.ts", "  // Now we validate the input\nvalidate(x)", True),
    ("sdlc-narration-comments", "a.py", "# This function returns the total\ndef total(): ...", True),
    ("sdlc-narration-comments", "src/a.ts", " * We need to sort first\n", True),
    ("sdlc-narration-comments", "src/a.ts", "// Retry once: the upstream API drops the first request after idle\nretry()", False),
    ("sdlc-narration-comments", "docs/guide.md", "# Step 1: install", False),
    ("sdlc-history-comments", "src/a.ts", "// Added for the login task\nconst x = 1", True),
    ("sdlc-history-comments", "src/a.ts", "// as requested in review\nconst x = 1", True),
    ("sdlc-history-comments", "a.py", "# changed to fix issue 123\nx = 2", True),
    ("sdlc-history-comments", "src/a.ts", "// Updated for JIRA-42 story\nconst x = 1", True),
    ("sdlc-history-comments", "src/a.ts", "// Retries are added to the request queue in order\nq.push(r)", False),
    ("sdlc-history-comments", "a.py", "# was previously a list\nitems = {}", True),
    ("sdlc-history-comments", "src/a.ts", "// New implementation using a map\nconst m = new Map()", True),
    ("sdlc-history-comments", "src/a.ts", "// Keys are lowercased: the API is case-insensitive\nconst k = s.toLowerCase()", False),
    ("sdlc-long-doc-comments", "src/a.ts", "/**\n" + " * line\n" * 8 + " */\nexport function f() {}", True),
    ("sdlc-long-doc-comments", "a.py", 'def f():\n    """Summary.\n' + "    more\n" * 9 + '    """\n', True),
    ("sdlc-long-doc-comments", "src/a.ts", "\n// a" * 9, True),
    ("sdlc-long-doc-comments", "src/a.ts", "/** Loads the user by id. */\nexport function load() {}", False),
    ("sdlc-long-doc-comments", "a.py", 'def f():\n    """Return the total."""\n', False),
]


class GuardrailsTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        os.makedirs(self.path(".claude/hookify"))
        for f in glob.glob(os.path.join(RULES, "*.md")):
            shutil.copy(f, self.path(".claude/hookify"))

    def pre(self, tool, tool_input):
        code, out, raw, err = run_hook(["python3", os.path.join(HOOKS, "pretooluse.py")],
                                       {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input},
                                       self.root)
        self.assertEqual(code, 0, err)
        self.assertNotIn("hookify error", (out or {}).get("systemMessage", "").lower(), out)
        return out or {}

    def fired(self, out, rule):
        return f"[{rule}]" in out.get("systemMessage", "")

    def test_bash_guardrails(self):
        for rule, command, fires in BASH:
            with self.subTest(rule=rule, command=command):
                self.assertEqual(self.fired(self.pre("Bash", {"command": command}), rule), fires)

    def test_file_guardrails_on_write(self):
        for rule, path, content, fires in FILES:
            with self.subTest(rule=rule, path=path, content=content[:40]):
                out = self.pre("Write", {"file_path": self.path(path), "content": content})
                self.assertEqual(self.fired(out, rule), fires)

    def test_file_guardrails_on_edit(self):
        out = self.pre("Edit", {"file_path": self.path("src/a.ts"), "old_string": "x",
                                "new_string": "// Step 1: load\nload()"})
        self.assertTrue(self.fired(out, "sdlc-narration-comments"))

    def test_actions(self):
        blocks = {"sdlc-dangerous-rm", "sdlc-force-push-main", "sdlc-secret-values"}
        out = self.pre("Bash", {"command": "git push --force origin main"})
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        out = self.pre("Write", {"file_path": self.path("src/a.ts"), "content": "// Step 1: x\nx()"})
        self.assertNotIn("permissionDecision", out["hookSpecificOutput"])
        names = {os.path.basename(f)[:-3] for f in glob.glob(os.path.join(RULES, "*.md"))}
        for name in names:
            with open(os.path.join(RULES, name + ".md")) as f:
                self.assertEqual("action: block" in f.read(), name in blocks, name)


if __name__ == "__main__":
    unittest.main()
