"""A session started in a folder above sdlc repos (a workbench of repos or worktrees): hookify and the role guard
judge a call by the repo it acts in. A session started in a repo, the only kind before, is unchanged."""
import os
import shutil
import unittest

from helpers import HOOKS, PLUGIN_ROOT, ProjectTestCase, run_hook

PRE = ["python3", os.path.join(HOOKS, "pretooluse.py")]
GUARD = ["python3", os.path.join(HOOKS, "role_guard.py")]
ADAPTER = ["python3", os.path.join(PLUGIN_ROOT, "hosts", "hook.py")]
TEMPLATES = os.path.join(PLUGIN_ROOT, "templates", "project", "hookify")


def block_rule(name, word, event="bash", field="command"):
    return (f"---\nname: {name}\nenabled: true\nevent: {event}\naction: block\nconditions:\n"
            f"  - field: {field}\n    operator: regex_match\n    pattern: {word}\n---\n{name} says no\n")


class SessionAboveRepoTest(ProjectTestCase):
    """self.root is the workbench (no .sdlc/); api/ is a set-up sdlc repo inside it with the team guardrails."""

    def setUp(self):
        super().setUp()
        self.write("api/.sdlc/config.json", '{"docs_dir": "docs/sdlc"}')
        self.write("api/.sdlc/state/feat.md", "Status: active\nProcess: 3\nCurrent: build\n")
        os.makedirs(self.path("api/.claude/hookify"))
        for name in os.listdir(TEMPLATES):
            shutil.copy(os.path.join(TEMPLATES, name), self.path("api/.claude/hookify"))

    def pre(self, project, tool, cwd=None, **tool_input):
        payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input,
                   "cwd": cwd or project}
        code, out, raw, err = run_hook(PRE, payload, project)
        self.assertEqual(code, 0, err)
        self.assertIsNotNone(out, raw)
        return out

    def guard(self, project, tool, path, agent, cwd=None):
        key = "path" if tool in ("Grep", "Glob") else "file_path"
        payload = {"hook_event_name": "PreToolUse", "cwd": cwd or project, "tool_name": tool,
                   "tool_input": {key: path}, "agent_type": agent}
        code, out, raw, err = run_hook(GUARD, payload, project)
        self.assertEqual(code, 0, err)
        return (out or {}).get("hookSpecificOutput", {}).get("permissionDecision")

    def denied_by(self, out):
        hso = out.get("hookSpecificOutput", {})
        return hso.get("permissionDecisionReason", "") if hso.get("permissionDecision") == "deny" else None

    # a. hookify loads the rules of the repo a call acts in
    def test_force_push_into_a_repo_below_is_denied(self):
        api = self.path("api")
        push = "git push --force origin main"
        self.assertIn("sdlc-force-push-main", self.denied_by(self.pre(self.root, "Bash", command=f"cd {api} && {push}")))
        self.assertIn("sdlc-force-push-main", self.denied_by(self.pre(self.root, "Bash", command=f"cd api && {push}")))
        self.assertIn("sdlc-force-push-main", self.denied_by(self.pre(self.root, "Bash", cwd=api, command=push)))
        self.assertIn("sdlc-force-push-main",
                      self.denied_by(self.pre(self.root, "Bash", command=f"git -C {api} push -f origin main")))
        self.assertEqual(self.pre(self.root, "Bash", command=f"cd {api} && git push origin feat"), {})

    def test_a_file_rule_of_the_repo_below_applies_to_its_files(self):
        self.write("api/.claude/hookify/no-secret.md", block_rule("no-secret", "SECRET", "file", "new_text"))
        out = self.pre(self.root, "Write", file_path=self.path("api/src/a.ts"), content="SECRET=1")
        self.assertIn("no-secret", self.denied_by(out))
        self.assertEqual(self.pre(self.root, "Write", file_path=self.path("other/a.ts"), content="SECRET=1"), {})

    def test_a_rule_in_both_places_fires_once_and_the_workbench_rules_still_apply(self):
        self.write(".claude/hookify/no-x.md", block_rule("no-x", "forbidden"))
        self.write(".claude/hookify/top-only.md", block_rule("top-only", "toponly"))
        self.write("api/.claude/hookify/no-x.md", block_rule("no-x", "forbidden"))
        reason = self.denied_by(self.pre(self.root, "Bash", command="cd api && echo forbidden"))
        self.assertEqual(reason.count("no-x says no"), 1, reason)
        self.assertIn("top-only", self.denied_by(self.pre(self.root, "Bash", command="cd api && echo toponly")))

    # b. the role guard judges paths against the repo they're in
    def test_role_guard_uses_the_repo_below(self):
        api = self.path("api")
        self.assertIsNone(self.guard(self.root, "Write", f"{api}/.sdlc/.work/findings/r.md", "sdlc:code-reviewer"))
        self.assertEqual(self.guard(self.root, "Write", f"{api}/src/a.ts", "sdlc:code-reviewer"), "deny")
        self.assertEqual(self.guard(self.root, "Write", f"{api}/.sdlc/state/feat.md", "sdlc:code-reviewer"), "deny")
        self.assertEqual(self.guard(self.root, "Read", f"{api}/src/x.go", "sdlc:qa-tester"), "deny")
        self.assertEqual(self.guard(self.root, "Grep", f"{api}/src", "sdlc:qa-tester"), "deny")
        self.assertIsNone(self.guard(self.root, "Read", f"{api}/docs/sdlc/changes/feat.md", "sdlc:qa-tester"))
        self.assertIsNone(self.guard(self.root, "Write", f"{api}/.sdlc/state/feat/qa-report.md", "sdlc:qa-tester"))
        # relative to a cwd inside the repo, and a path that climbs out of it, are judged where they land
        self.assertIsNone(self.guard(self.root, "Write", ".sdlc/.work/findings/r.md", "sdlc:code-reviewer", cwd=api))
        self.assertEqual(self.guard(self.root, "Write", f"{api}/../api/src/a.ts", "sdlc:code-reviewer"), "deny")
        self.assertEqual(self.guard(self.root, "Write", f"{api}/.sdlc/.work/findings/../../../src/a.ts",
                                    "sdlc:code-reviewer"), "deny")

    # c. a session started in a repo: unchanged, and a nested sdlc repo below it is never consulted
    def test_a_session_in_the_repo_is_unchanged_by_a_nested_repo(self):
        api = self.path("api")
        calls = [("Bash", {"command": "cd sub && echo nestedword"}), ("Bash", {"command": "git push --force origin main"}),
                 ("Bash", {"command": "cd sub && git push --force origin main"}), ("Bash", {"command": "ls"}),
                 ("Write", {"file_path": f"{api}/sub/a.ts", "content": "nestedword"})]
        before = [self.pre(api, tool, **ti) for tool, ti in calls]
        guard_calls = [("Write", f"{api}/sub/.sdlc/.work/findings/r.md", "sdlc:code-reviewer"),
                       ("Write", f"{api}/.sdlc/.work/findings/r.md", "sdlc:code-reviewer"),
                       ("Read", f"{api}/sub/.sdlc/x.md", "sdlc:qa-tester"),
                       ("Read", f"{api}/docs/sdlc/x.md", "sdlc:qa-tester")]
        guard_before = [self.guard(api, *c) for c in guard_calls]

        self.write("api/sub/.sdlc/config.json", '{"docs_dir": "elsewhere"}')
        self.write("api/sub/.claude/hookify/nested.md", block_rule("nested", "nestedword"))
        self.write("api/sub/.claude/hookify/nested-file.md", block_rule("nested-file", "nestedword", "file", "new_text"))
        self.assertEqual([self.pre(api, tool, **ti) for tool, ti in calls], before)
        self.assertEqual([self.guard(api, *c) for c in guard_calls], guard_before)
        self.assertEqual(guard_before, ["deny", None, "deny", None])
        self.assertIsNone(self.denied_by(before[0]))
        self.assertIn("sdlc-force-push-main", self.denied_by(before[1]))

    def test_a_project_with_any_sdlc_folder_never_looks_below(self):
        # sdlc used without setup (.sdlc/ but no config.json): still the project's rules only
        self.write(".sdlc/todo.md", "")
        self.assertEqual(self.pre(self.root, "Bash", command="cd api && git push --force origin main"), {})
        self.assertEqual(self.guard(self.root, "Write", self.path("api/.sdlc/.work/findings/r.md"),
                                    "sdlc:code-reviewer"), "deny")

    # d. nothing to resolve, or nothing usable there: silent
    def test_unresolvable_calls_and_bad_repos_stay_silent(self):
        self.assertEqual(self.pre(self.root, "Bash", command="git push --force origin main"), {})  # acts in the workbench
        self.assertEqual(self.pre(self.root, "Bash", command="cd /nowhere/at/all && git push --force origin main"), {})
        self.assertEqual(self.pre(self.root, "Bash", command="cd 'unterminated && git push -f origin main"), {})
        outside = os.path.dirname(self.root)
        self.assertEqual(self.pre(self.root, "Bash", command=f"cd {outside} && git push --force origin main"), {})
        # a folder with guardrails but no .sdlc/config.json isn't an sdlc repo
        os.makedirs(self.path("web/.claude"))
        shutil.copytree(self.path("api/.claude/hookify"), self.path("web/.claude/hookify"))
        self.assertEqual(self.pre(self.root, "Bash", command="cd web && git push --force origin main"), {})
        # a broken rule in the repo below is reported, never blocks, and the hook still exits 0
        self.write("api/.claude/hookify/broken.md", "no frontmatter here")
        out = self.pre(self.root, "Bash", command="cd api && ls")
        self.assertNotIn("hookSpecificOutput", out)
        self.assertIn("broken.md", out.get("systemMessage", ""))
        code, out, raw, _ = run_hook(PRE, "not json", self.root)
        self.assertEqual((code, raw), (0, ""))
        code, out, raw, _ = run_hook(GUARD, {"agent_type": "sdlc:code-reviewer", "tool_name": "Write",
                                             "tool_input": ["not", "a", "dict"]}, self.root)
        self.assertEqual((code, raw), (0, ""))

    # e. other agents reach the same hookify through hosts/hook.py; Cursor names the workspace as the project
    def test_cursor_command_into_a_repo_below_is_denied(self):
        payload = {"hook_event_name": "preToolUse", "cwd": "", "workspace_roots": [self.root], "conversation_id": "c",
                   "tool_name": "Shell", "tool_input": {"command": "cd api && git push --force origin main"}}
        code, out, raw, err = run_hook(ADAPTER + ["cursor", "PreToolUse"], payload, PLUGIN_ROOT,
                                       {"CLAUDE_PROJECT_DIR": ""})
        self.assertEqual(code, 0, err)
        self.assertEqual((out or {}).get("permission"), "deny", raw)
        self.assertIn("sdlc-force-push-main", out["agent_message"])

if __name__ == "__main__":
    unittest.main()
