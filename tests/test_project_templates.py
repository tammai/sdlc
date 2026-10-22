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
            used |= set(re.findall(r"config\.areas\.(\w+)", open(p).read()))
        self.assertEqual(used - set(areas), set(), "rule templates reference undefined areas")
        self.assertTrue(rules)

    def test_every_template_renders_without_leftover_placeholders(self):
        for path in shipped("**", "*.*"):
            if path.endswith("config.defaults.json"):
                continue
            with self.subTest(template=os.path.relpath(path, TEMPLATES)):
                self.assertIsNone(re.search(r"\{\{\s*(config|plugin_version)\b", self.render(path)))

    def test_ci_workflows_keep_github_expressions(self):
        for path in shipped("ci", "*.yml"):
            with self.subTest(workflow=os.path.basename(path)):
                text = self.render(path)
                self.assertIn("${{ github.ref }}", text)
                self.assertIn("runs-on: ${{ matrix.os }}", text)
                self.assertIn('os: ["ubuntu-latest"]', text)
                self.assertIn("shell: bash", text)
                self.assertIn("run: just verify", text)

    def justfile(self, stack, dest="justfile"):
        with open(os.path.join(PLUGIN_ROOT, "templates", "justfile", stack + ".just")) as f:
            self.write(dest, f.read())

    def test_every_stack_justfile_satisfies_the_contract(self):
        stacks = [os.path.basename(p)[:-5] for p in glob.glob(os.path.join(PLUGIN_ROOT, "templates", "justfile", "*.just"))]
        self.assertTrue({"node", "python", "go", "rust", "dart", "flutter", "shell", "gradle", "dotnet"} <= set(stacks))
        for stack in sorted(set(stacks) - {"polyglot-root"}):
            with self.subTest(stack=stack):
                self.justfile(stack)
                out = self.sc("contract")
                self.assertTrue(out["ok"], out)

    def test_polyglot_root_checks_every_package(self):
        self.justfile("polyglot-root")
        out = self.sc("contract")
        self.assertEqual(out["missing"], [])  # the root's own recipes are complete
        self.assertFalse(out["ok"])           # ...but its packages don't exist yet
        self.assertEqual(set(out["modules"]), {"api", "web", "scripts"})
        self.justfile("go", "services/api/justfile")
        self.justfile("node", "apps/web/justfile")
        self.justfile("shell", "scripts/justfile")
        out = self.sc("contract")
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["modules"]["api"]["justfile"], "services/api/justfile")
        self.write("scripts/justfile", "test:\n    bats test\n")
        out = self.sc("contract")
        self.assertFalse(out["ok"])
        self.assertIn("lint", out["modules"]["scripts"]["missing"])

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
