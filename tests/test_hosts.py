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
        self.write("agents/verifier.md", "---\nname: verifier\ntools: Read, Bash, Write\ndescription: Verifies.\n"
                                         "model: inherit\n---\nVerify it.\n")

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
        self.assertNotIn("readonly", self.read("hosts/cursor/agents/verifier.md"))  # it writes its report
        self.write(".claude-plugin/plugin.json", json.dumps({"name": "sdlc", "version": "2.1.0", "description": "d"}))
        code, out = self.hosts("check")
        self.assertEqual(code, 1)
        self.assertIn(".codex-plugin/plugin.json", out["stale"])


if __name__ == "__main__":
    unittest.main()
