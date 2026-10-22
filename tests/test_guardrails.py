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
    ("sdlc-dangerous-rm", "rm -rf /*", True),
    ("sdlc-dangerous-rm", "rm -rf ~/*", True),
    ("sdlc-dangerous-rm", "rm -rf ./*", True),
    ("sdlc-dangerous-rm", "rm -rf ../..", True),
    ("sdlc-dangerous-rm", "rm -rf -- /", True),
    ("sdlc-dangerous-rm", "rm -r -f /", True),
    ("sdlc-dangerous-rm", "rm --recursive --force /", True),
    ("sdlc-dangerous-rm", 'rm -rf "$HOME"', True),
    ("sdlc-dangerous-rm", "rm -rf ${HOME}", True),
    ("sdlc-dangerous-rm", "rm -rf '/'", True),
    ("sdlc-dangerous-rm", "rm -rf dist", False),
    ("sdlc-dangerous-rm", "rm -rf /usr/local/tmp", False),
    ("sdlc-dangerous-rm", "rm -rf *.log", False),
    ("sdlc-dangerous-rm", "rm -rf .gitignore.bak", False),
    ("sdlc-dangerous-rm", "rm -rf build && ls /", False),
    ("sdlc-dangerous-rm", "rm -f /tmp/x.lock", False),
    ("sdlc-dangerous-rm", "rm -rf ./node_modules", False),
    ("sdlc-dangerous-rm", "rm -rf .sdlc/.work/tmp", False),
    ("sdlc-force-push-main", "git push --force origin main", True),
    ("sdlc-force-push-main", "git push -f origin master", True),
    ("sdlc-force-push-main", "git push --force-with-lease origin main", True),
    ("sdlc-force-push-main", "git push origin +main", True),
    ("sdlc-force-push-main", "git -C . push -f origin main", True),
    ("sdlc-force-push-main", "git -c core.editor=true push --force origin master", True),
    ("sdlc-force-push-main", "git --no-pager push -f origin main", True),
    ("sdlc-force-push-main", "git push -fu origin main", True),
    ("sdlc-force-push-main", "git push \\\n  --force origin main", True),
    ("sdlc-force-push-main", "git push --force origin feat/login", False),
    ("sdlc-force-push-main", "git push --force origin feat/login && git checkout main", False),
    ("sdlc-force-push-main", "git commit -m 'push -f main'", False),
    ("sdlc-force-push-main", "git push origin :main", True),
    ("sdlc-force-push-main", "git push --delete origin master", True),
    ("sdlc-force-push-main", "git push --mirror backup", True),
    ("sdlc-force-push-main", "git push origin :feat/login", False),
    ("sdlc-force-push-main", "git push --delete origin feat/login", False),
    ("sdlc-force-push-main", "git stash push -m main", False),
    ("sdlc-force-push-main", "git push origin main", False),
    ("sdlc-secret-values-bash", "export K=sk-ant-api03-abcdefghijklmnopqrstuvwxyz", True),
    ("sdlc-secret-values-bash", "echo ghp_abcdefghijklmnopqrstuvwxyz0123456789 > .npmrc", True),
    ("sdlc-secret-values-bash", "export K=$ANTHROPIC_API_KEY", False),
    ("sdlc-protect-guardrails-bash", "rm .claude/hookify/sdlc-dangerous-rm.md", True),
    ("sdlc-protect-guardrails-bash", "rm -r .claude/hookify", True),
    ("sdlc-protect-guardrails-bash", "rm .claude/hookify/*", True),
    ("sdlc-protect-guardrails-bash", "sed -i '' 's/enabled: true/enabled: false/' .claude/hookify/sdlc-reset-hard.md", True),
    ("sdlc-protect-guardrails-bash", "echo 'enabled: false' > .claude/hookify/sdlc-secret-values.md", True),
    ("sdlc-protect-guardrails-bash", "mv .claude/hookify/sdlc-reset-hard.md /tmp", True),
    ("sdlc-protect-guardrails-bash", "del .claude\\hookify\\sdlc-dangerous-rm.md && rm .claude\\hookify\\sdlc-reset-hard.md", True),
    ("sdlc-protect-guardrails-bash", "cat .claude/hookify/sdlc-dangerous-rm.md", False),
    ("sdlc-protect-guardrails-bash", "ls .claude/hookify/ 2>&1", False),
    ("sdlc-protect-guardrails-bash", "ls .claude/hookify && rm -rf dist", False),
    ("sdlc-protect-guardrails-bash", "rm .claude/hookify/no-rm.md", False),
    ("sdlc-protect-guardrails-bash", "git add .claude/hookify", False),
    ("sdlc-reset-hard", "git reset --hard HEAD~1", True),
    ("sdlc-reset-hard", "git clean -fd", True),
    ("sdlc-reset-hard", "git checkout -- .", True),
    ("sdlc-reset-hard", "git reset --soft HEAD~1", False),
    ("sdlc-reset-hard", "git checkout -- src/a.ts", False),
]

FILES = [
    ("sdlc-protect-guardrails-file", ".claude/hookify/sdlc-dangerous-rm.md", "enabled: false", True),
    ("sdlc-protect-guardrails-file", "pkg/.claude/hookify/sdlc-secret-values.md", "x", True),
    ("sdlc-protect-guardrails-file", ".claude\\hookify\\sdlc-dangerous-rm.md", "x", True),
    ("sdlc-protect-guardrails-file", ".claude/hookify/no-rm.md", "x", False),
    ("sdlc-protect-guardrails-file", ".claude/hookify.mine.local.md", "x", False),
    ("sdlc-protect-guardrails-file", "templates/project/hookify/sdlc-dangerous-rm.md", "x", False),
    ("sdlc-sensitive-files", "config/.env", "X=1", True),
    ("sdlc-sensitive-files", ".env.local", "X=1", True),
    ("sdlc-sensitive-files", "config\\.env", "X=1", True),
    ("sdlc-sensitive-files", ".ssh\\id_rsa", "x", True),
    ("sdlc-sensitive-files", "certs/server.pem", "x", True),
    ("sdlc-sensitive-files", "src/environment.ts", "x", False),
    ("sdlc-secret-values", "src/a.ts", 'const k = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz"', True),
    ("sdlc-secret-values", "src/a.ts", 'const k = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"', True),
    ("sdlc-secret-values", "src/a.ts", "key = AKIAABCDEFGHIJKLMNOP", True),
    ("sdlc-secret-values", "src/a.ts", 'const k = "sk-proj-' + "aB3_-" * 12 + '"', True),
    ("sdlc-secret-values", "src/a.ts", 'const k = "github_pat_' + "A" * 40 + '"', True),
    ("sdlc-secret-values", "src/a.ts", 'const k = "sk_live_' + "a" * 24 + '"', True),
    ("sdlc-secret-values", "src/a.ts", 'const k = "AIza' + "A" * 35 + '"', True),
    ("sdlc-secret-values", "k.pem", "-----BEGIN RSA PRIVATE KEY-----\nabc", True),
    ("sdlc-secret-values", "src/a.ts", "const k = process.env.ANTHROPIC_API_KEY", False),
    ("sdlc-console-log", "src/a.ts", "console.log(user)", True),
    ("sdlc-console-log", "src/a.ts", "console.error(err)", False),
    ("sdlc-console-log", "README.md", "console.log(x)", False),
    ("sdlc-ui-hardcoded-values", "src/Button.tsx", '<div className="bg-[#1a2b3c] p-4" />', True),
    ("sdlc-ui-hardcoded-values", "src/Button.tsx", '<div className="w-[13px]" />', True),
    ("sdlc-ui-hardcoded-values", "src/Card.tsx", "<div style={{ color: 'red' }} />", True),
    ("sdlc-ui-hardcoded-values", "src/app.module.css", ".title { color: #333; }", True),
    ("sdlc-ui-hardcoded-values", "src/app.module.css", ".title { color: rgba(0, 0, 0, 0.5); }", True),
    ("sdlc-ui-hardcoded-values", "src/app.module.css", ".title { color: var(--text-muted); }", False),
    ("sdlc-ui-hardcoded-values", "src/styles/tokens.css", ".x { color: #1a2b3c; }", False),
    ("sdlc-ui-hardcoded-values", "src/index.css", "@theme {\n  --color-brand: #1a2b3c;\n}", False),
    ("sdlc-ui-hardcoded-values", "src/Button.tsx", '<a href="#top" className="text-primary p-4" />', False),
    ("sdlc-ui-hardcoded-values", "scripts/plot.py", 'color = "#1a2b3c"', False),
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

    def test_secrets_are_blocked_in_notebook_cells(self):
        out = self.pre("NotebookEdit", {"notebook_path": self.path("a.ipynb"), "new_source": "k = 'ghp_" + "a" * 36 + "'"})
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_file_guardrails_on_edit(self):
        out = self.pre("Edit", {"file_path": self.path("src/a.ts"), "old_string": "x",
                                "new_string": "// Step 1: load\nload()"})
        self.assertTrue(self.fired(out, "sdlc-narration-comments"))

    def test_actions(self):
        blocks = {"sdlc-dangerous-rm", "sdlc-force-push-main", "sdlc-secret-values",
                  "sdlc-protect-guardrails-file", "sdlc-protect-guardrails-bash", "sdlc-secret-values-bash"}
        out = self.pre("Bash", {"command": "git push --force origin main"})
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        out = self.pre("Write", {"file_path": self.path("src/a.ts"), "content": "// Step 1: x\nx()"})
        self.assertNotIn("permissionDecision", out["hookSpecificOutput"])
        names = {os.path.basename(f)[:-3] for f in glob.glob(os.path.join(RULES, "*.md"))}
        for name in names:
            with open(os.path.join(RULES, name + ".md")) as f:
                self.assertEqual("action: block" in f.read(), name in blocks, name)

    def test_rules_load_when_the_hook_starts_in_a_subdirectory(self):
        sub = self.path("packages/web")
        os.makedirs(sub)
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}
        for project_dir in (self.root, ""):
            with self.subTest(CLAUDE_PROJECT_DIR=project_dir):
                code, out, raw, err = run_hook(["python3", os.path.join(HOOKS, "pretooluse.py")], payload, sub,
                                               {"CLAUDE_PROJECT_DIR": project_dir})
                self.assertEqual(code, 0, err)
                self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny", raw)

    def test_stop_and_prompt_hooks_also_find_rules_from_a_subdirectory(self):
        self.write(".claude/hookify/stop-rule.md",
                   "---\nname: stop-rule\nenabled: true\nevent: stop\naction: block\nconditions:\n"
                   "  - field: reason\n    operator: contains\n    pattern: done\n---\nnot yet\n")
        sub = self.path("packages/web")
        os.makedirs(sub)
        code, out, raw, err = run_hook(["python3", os.path.join(HOOKS, "stop.py")],
                                       {"hook_event_name": "Stop", "reason": "done"}, sub,
                                       {"CLAUDE_PROJECT_DIR": ""})
        self.assertEqual(code, 0, err)
        self.assertEqual(out.get("decision"), "block", raw)


if __name__ == "__main__":
    unittest.main()
