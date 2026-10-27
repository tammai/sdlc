"""hooks/role_guard.py: the plugin's subagents stay in their role (agent_type names the caller)."""
import os
import unittest

from helpers import HOOKS, ProjectTestCase, run_hook

HOOK = ["python3", os.path.join(HOOKS, "role_guard.py")]


class RoleGuardTest(ProjectTestCase):
    def call(self, tool, rel, agent=None):
        key = "path" if tool in ("Grep", "Glob") else "file_path"
        payload = {"hook_event_name": "PreToolUse", "cwd": self.root, "tool_name": tool,
                   "tool_input": {key: self.path(rel)}}
        if agent:
            payload["agent_type"] = agent
        code, out, raw, err = run_hook(HOOK, payload, self.root)
        self.assertEqual(code, 0, err)
        return (out or {}).get("hookSpecificOutput", {}).get("permissionDecision")

    def test_reviewer_cannot_edit(self):
        self.assertEqual(self.call("Edit", "src/a.ts", "sdlc:code-reviewer"), "deny")
        self.assertEqual(self.call("Edit", "src/a.ts", "sdlc-extras:comment-analyzer"), "deny")  # the companion's
        self.assertIsNone(self.call("Edit", "src/a.ts"))  # the main session
        self.assertIsNone(self.call("Edit", "src/a.ts", "general-purpose"))

    def test_define_explorers_write_only_their_report(self):
        for agent in ("sdlc:code-explorer",):
            with self.subTest(agent=agent):
                self.assertIsNone(self.call("Write", ".sdlc/.work/findings/login/code-explorer-r1.md", agent))
                self.assertEqual(self.call("Write", "src/a.ts", agent), "deny")

    def test_reviewer_writes_its_findings_file_and_nothing_else(self):
        # Under the relay the main session passes paths, not findings: a reviewer writes its report here
        self.assertIsNone(self.call("Write", ".sdlc/.work/findings/code-reviewer-r1.md", "sdlc:code-reviewer"))
        self.assertEqual(self.call("Write", ".sdlc/.work/findings/../trust-anchor.json", "sdlc:code-reviewer"), "deny")
        self.assertEqual(self.call("Write", ".sdlc/login/review.md", "sdlc:code-reviewer"), "deny")

    def test_qa_tester_works_in_the_docs_folder(self):
        self.write(".sdlc/config.json", '{"docs_dir": "docs/sdlc"}')
        self.assertEqual(self.call("Edit", "docs/sdlc/intents/login/spec.md", "sdlc:qa-tester"), "deny")
        self.assertIsNone(self.call("Read", "docs/sdlc/intents/login/spec.md", "sdlc:qa-tester"))
        self.assertIsNone(self.call("Write", "docs/sdlc/intents/login/qa-report.md", "sdlc:qa-tester"))
        self.assertEqual(self.call("Write", "docs/sdlc/qa-report.md", "sdlc:qa-tester"), "deny")  # feature folders only
        self.assertEqual(self.call("Write", ".sdlc/state/qa-report.md", "sdlc:qa-tester"), "deny")  # would read as state
        self.assertEqual(self.call("Write", ".sdlc/STATE/qa-report.md", "sdlc:qa-tester"), "deny")
        self.assertEqual(self.call("Write", ".sdlc/WORK~1/qa-report.md", "sdlc:qa-tester"), "deny")  # short name

    def test_qa_tester_reads_the_spec_but_not_the_code(self):
        self.assertIsNone(self.call("Read", ".sdlc/login/spec.md", "sdlc:qa-tester"))
        self.assertIsNone(self.call("Read", "README.md", "sdlc:qa-tester"))
        self.assertEqual(self.call("Read", "src/a.ts", "sdlc:qa-tester"), "deny")
        self.assertEqual(self.call("Grep", "src", "sdlc:qa-tester"), "deny")
        self.assertIsNone(self.call("Write", ".sdlc/login/qa-report.md", "sdlc:qa-tester"))


if __name__ == "__main__":
    unittest.main()
