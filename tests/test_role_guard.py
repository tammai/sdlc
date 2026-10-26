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
        self.assertIsNone(self.call("Edit", "src/a.ts"))  # the main session
        self.assertIsNone(self.call("Edit", "src/a.ts", "general-purpose"))

    def test_verifier_writes_only_its_report_baseline_and_scratch(self):
        self.assertIsNone(self.call("Write", ".sdlc/login/test-report.md", "sdlc:verifier"))
        self.assertIsNone(self.call("Write", ".sdlc/.work/probes/kill-mid-write.sh", "sdlc:verifier"))  # a repro to hand back
        self.assertEqual(self.call("Edit", "src/a.ts", "sdlc:verifier"), "deny")
        self.assertEqual(self.call("Edit", ".sdlc/login/spec.md", "sdlc:verifier"), "deny")  # no moving the goalposts
        self.assertEqual(self.call("Write", ".sdlc/.work/trust-anchor.json", "sdlc:verifier"), "deny")

    def test_verifier_and_qa_tester_work_in_the_docs_folder(self):
        self.write(".sdlc/config.json", '{"docs_dir": "docs/sdlc"}')
        self.assertIsNone(self.call("Write", "docs/sdlc/intents/login/test-report.md", "sdlc:verifier"))
        self.assertEqual(self.call("Edit", "docs/sdlc/intents/login/spec.md", "sdlc:verifier"), "deny")
        self.assertIsNone(self.call("Read", "docs/sdlc/intents/login/spec.md", "sdlc:qa-tester"))
        self.assertIsNone(self.call("Write", "docs/sdlc/intents/login/qa-report.md", "sdlc:qa-tester"))
        self.assertEqual(self.call("Write", "docs/sdlc/test-report.md", "sdlc:verifier"), "deny")  # feature folders only
        self.assertEqual(self.call("Write", ".sdlc/state/test-report.md", "sdlc:verifier"), "deny")  # would read as state
        self.assertEqual(self.call("Write", ".sdlc/STATE/test-report.md", "sdlc:verifier"), "deny")
        self.assertEqual(self.call("Write", ".sdlc/WORK~1/test-report.md", "sdlc:verifier"), "deny")  # short name

    def test_qa_tester_reads_the_spec_but_not_the_code(self):
        self.assertIsNone(self.call("Read", ".sdlc/login/spec.md", "sdlc:qa-tester"))
        self.assertIsNone(self.call("Read", "README.md", "sdlc:qa-tester"))
        self.assertEqual(self.call("Read", "src/a.ts", "sdlc:qa-tester"), "deny")
        self.assertEqual(self.call("Grep", "src", "sdlc:qa-tester"), "deny")
        self.assertIsNone(self.call("Write", ".sdlc/login/qa-report.md", "sdlc:qa-tester"))


if __name__ == "__main__":
    unittest.main()
