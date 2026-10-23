"""templates/project/: every shipped template renders with the plugin defaults, and rules have valid frontmatter."""
import glob
import json
import os
import re
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase, run_hook

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py")
TEMPLATES = os.path.join(PLUGIN_ROOT, "templates", "project")
RULE_LINE_BUDGET = 30


def shipped(*parts):
    return sorted(glob.glob(os.path.join(TEMPLATES, *parts)))


class ProjectTemplatesTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.sc("init", "--kind", "brownfield")

    def sc(self, *args):
        code, out, raw, err = run_hook([sys.executable, SCRIPT, "--root", self.root, *args], "", self.root)
        self.assertEqual(code, 0, raw + err)
        return out

    def render(self, path):
        return self.sc("preview", os.path.relpath(path, PLUGIN_ROOT))["text"]

    def test_defaults_file_is_valid_json_with_every_area(self):
        with open(os.path.join(TEMPLATES, "config.defaults.json")) as f:
            areas = json.load(f)["areas"]
        rules = {os.path.basename(p)[:-3] for p in shipped("rules", "*.md")} - {"sdlc"}
        used = set()
        for p in shipped("rules", "*.md"):
            with open(p) as f:
                used |= set(re.findall(r"config\.areas\.(\w+)", f.read()))
        self.assertEqual(used - set(areas), set(), "rule templates reference undefined areas")
        self.assertTrue(rules)

    def test_every_template_renders_without_leftover_placeholders(self):
        for path in shipped("**", "*.*"):
            if path.endswith("config.defaults.json"):
                continue
            with self.subTest(template=os.path.relpath(path, TEMPLATES)):
                self.assertIsNone(re.search(r"\{\{\s*(config|plugin_version)\b", self.render(path)))

    def test_generated_ci_with_plugin_defaults(self):
        self.write(".sdlc/config.json", json.dumps({
            "min_plugin_version": "1.3.0", "project": {"kind": "greenfield", "stack": ["python"]},
            "commands": {"install": "uv sync --frozen", "test": "uv run pytest", "lint": "uv run ruff check .",
                         "typecheck": "uv run mypy .", "build": None}}))
        text = self.sc("preview", "builtin:ci")["text"]
        self.assertIn("astral-sh/setup-uv@v6", text)
        self.assertIn('os: ["ubuntu-latest"]', text)
        order = [l.strip() for l in text.splitlines() if l.strip().startswith("uv ")]
        self.assertEqual(order, ["uv sync --frozen", "uv run ruff check .", "uv run mypy .", "uv run pytest"])
        self.assertNotIn("{{", text.replace("${{", ""))

    def test_area_rules_have_paths_frontmatter_and_stay_short(self):
        for path in shipped("rules", "*.md"):
            name = os.path.basename(path)
            with self.subTest(rule=name):
                text = self.render(path)
                lines = text.strip().splitlines()
                self.assertLessEqual(len(lines), RULE_LINE_BUDGET)
                if name == "sdlc.md":  # always-on: no paths
                    self.assertFalse(text.startswith("---"))
                    continue
                m = re.match(r'^---\npaths:\n((?:  - "[^"\n]+"\n)+)---\n', text)
                self.assertIsNotNone(m, text[:200])
                self.assertIn("Managed by the sdlc plugin", text)


if __name__ == "__main__":
    unittest.main()
