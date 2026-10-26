"""scripts/context_diet.py: per-source cost of what Claude Code lists every call, and the deterministic verdicts."""
import json
import math
import os
import subprocess
import sys

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "context_diet.py")


class ContextDietTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.write("project/app.py", "print('hi')\n")
        cache = ".claude/plugins/cache"
        self.write("home/.claude/settings.json", json.dumps({"enabledPlugins": {
            "sdlc@sdlc": True, "code-review@claude-plugins-official": True,
            "rust-analyzer-lsp@claude-plugins-official": True, "playwright@claude-plugins-official": True,
            "figma@claude-plugins-official": False}}))
        self.write("home/.claude/plugins/installed_plugins.json", json.dumps({"version": 2, "plugins": {
            k: [{"scope": "user", "installPath": self.path(f"home/{cache}/{k.split('@')[0]}")}]
            for k in ("sdlc@sdlc", "code-review@claude-plugins-official", "rust-analyzer-lsp@claude-plugins-official",
                      "playwright@claude-plugins-official", "figma@claude-plugins-official")}}))
        self.write(f"home/{cache}/sdlc/skills/start/SKILL.md", "---\nname: start\ndescription: >\n  Start a feature\n---\n")
        self.write(f"home/{cache}/code-review/commands/code-review.md", "---\ndescription: Review a PR\n---\n")
        self.write(f"home/{cache}/rust-analyzer-lsp/README.md", "lsp\n")
        self.write(f"home/{cache}/playwright/.mcp.json", json.dumps({"playwright": {"command": "npx"}}))  # no mcpServers key
        self.write(f"home/{cache}/figma/skills/figma-use/SKILL.md", "---\nname: figma-use\ndescription: Figma\n---\n")
        self.write(f"home/{cache}/figma/.mcp.json", json.dumps({"mcpServers": {"figma": {}}}))
        self.write("home/.claude/skills/wrangler/SKILL.md", "---\nname: wrangler\ndescription: Run Wrangler\n---\n")
        self.write("home/.claude/skills/synced/b1/docx/SKILL.md", "---\nname: docx\ndescription: Word files\n---\n")

    def diet(self):
        p = subprocess.run([sys.executable, SCRIPT, "--home", self.path("home"), "--root", self.path("project")],
                           capture_output=True, encoding="utf-8", errors="replace")
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout)
        return out, {s["name"]: s for s in out["sources"]}

    def test_fixture_home_gives_sources_costs_and_duplicate_verdicts(self):
        out, src = self.diet()
        cost = lambda line: math.ceil(len(line) / 4)  # noqa: E731
        self.assertEqual((src["sdlc"]["tokens"], src["sdlc"]["items"]), (cost("- sdlc:start: Start a feature\n"), 1))
        self.assertEqual(src["code-review"]["verdict"], "duplicate")
        self.assertEqual(src["rust-analyzer-lsp"]["verdict"], "off")  # python here, no rust
        self.assertIsNone(src["sdlc"]["verdict"])
        self.assertEqual((src["figma"]["enabled"], src["figma"]["tokens"]), (False, 0))
        self.assertEqual(src["playwright"]["mcp"], ["playwright"])
        self.assertEqual((src["wrangler"]["kind"], src["wrangler"]["tokens"]), ("personal", cost("- wrangler: Run Wrangler\n")))
        self.assertEqual((src["claude.ai skills"]["kind"], src["claude.ai skills"]["items"]), ("synced", 1))
        self.assertNotIn("docx", src)  # a synced skill is not a personal one
        self.assertEqual(out["problems"], [])

    def test_malformed_installed_plugins_is_reported_not_a_crash(self):
        self.write("home/.claude/plugins/installed_plugins.json", "{not json")
        out, src = self.diet()
        files = [p["file"] for p in out["problems"]]
        self.assertTrue(any(f.endswith("installed_plugins.json") for f in files), out["problems"])
        self.assertIn("sdlc@sdlc", files)  # enabled, but its folder can't be found
        self.assertEqual(src["code-review"]["verdict"], "duplicate")
