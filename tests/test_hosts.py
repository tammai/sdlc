"""scripts/hosts.py: Codex, Cursor and Antigravity files built from the Claude Code sources."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "hosts.py")


class HostsTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.write(".claude-plugin/plugin.json", json.dumps({"name": "sdlc", "version": "2.0.0", "description": "d"}))
        self.write(".claude-plugin/marketplace.json", json.dumps({"name": "sdlc", "plugins": []}))
        self.write("agents/reviewer.md", "---\nname: reviewer\ntools: Glob, Grep, Read, Bash\ndescription: Reviews.\n"
                                         "model: opus\n---\nReview it.\n")
        # Its Write is only for its findings report, which Cursor's flow doesn't read
        self.write("agents/code-reviewer.md", "---\nname: code-reviewer\ntools: Read, Write\ndescription: Checks.\n"
                                              "model: inherit\n---\nCheck it.\n")
        self.write("agents/qa-tester.md", "---\nname: qa-tester\ntools: Read, Bash, Write\ndescription: Tests.\n"
                                          "model: inherit\n---\nTest it.\n")

    def hosts(self, cmd):
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, cmd], capture_output=True, encoding="utf-8")
        return p.returncode, json.loads(p.stdout)

    def read(self, rel):
        with open(self.path(rel), encoding="utf-8") as f:
            return f.read()

    def test_build_writes_every_host_and_check_catches_drift(self):
        self.assertEqual(self.hosts("build")[0], 0)
        self.assertEqual(self.hosts("check"), (0, {"stale": []}))
        for manifest in (".codex-plugin/plugin.json", ".cursor-plugin/plugin.json", "plugin.json"):
            self.assertEqual(json.loads(self.read(manifest))["version"], "2.0.0", manifest)
        self.assertEqual(self.read("hosts/cursor/agents/reviewer.md"),
                         "---\nname: reviewer\ndescription: Reviews.\nmodel: inherit\nreadonly: true\n---\nReview it.\n")
        self.assertNotIn("readonly", self.read("hosts/cursor/agents/qa-tester.md"))  # it writes its report
        self.assertIn("readonly: true", self.read("hosts/cursor/agents/code-reviewer.md"))
        self.write(".claude-plugin/plugin.json", json.dumps({"name": "sdlc", "version": "2.1.0", "description": "d"}))
        code, out = self.hosts("check")
        self.assertEqual(code, 1)
        self.assertIn(".codex-plugin/plugin.json", out["stale"])

    def test_commands_become_skills_for_codex_and_antigravity(self):
        # Neither loads a command that takes $ARGUMENTS; the hook-driven ones can't work without hooks
        self.write("commands/start.md", "---\ndescription: Start a feature.\nargument-hint: \"[what]\"\n---\n"
                                        "Status: !`git status`\n\nRequest: $ARGUMENTS\n")
        self.write("commands/ralph-loop.md", "---\ndescription: Loop.\n---\nLoop.\n")
        self.assertEqual(self.hosts("build")[0], 0)
        self.assertEqual(self.read("hosts/skills/start/SKILL.md"),
                         "---\nname: start\ndescription: Start a feature.\n---\n"
                         "Status: run `git status`\n\nRequest: <the user's request>\n")
        self.assertFalse(os.path.exists(self.path("hosts/skills/ralph-loop")))
        codex = json.loads(self.read(".codex-plugin/plugin.json"))
        self.assertIn("./hosts/skills/", codex["skills"])
        self.assertNotEqual(codex["commands"], "./commands/")  # else Codex adds its own copies of some
        self.assertEqual(json.loads(self.read("plugin.json"))["skills"], "./hosts/skills/")

    def test_antigravity_dist_converts_the_agents_it_would_skip(self):
        out = os.path.join(self.root, "dist")
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, "dist", "antigravity", out],
                           capture_output=True, encoding="utf-8")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        with open(os.path.join(out, "agents", "reviewer.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "---\nname: reviewer\ndescription: Reviews.\nmodel: inherit\n"
                                       "tools: [\"Glob\", \"Grep\", \"Read\", \"Bash\"]\n---\nReview it.\n")
        self.assertTrue(os.path.exists(os.path.join(out, "plugin.json")))
        with open(self.path("agents/reviewer.md"), encoding="utf-8") as f:
            self.assertIn("model: opus", f.read())  # the Claude Code source is untouched


if __name__ == "__main__":
    unittest.main()
