"""Storybook as an opt-in living design system (.sdlc/2026-11-23-m-storybook-opt-in): config `storybook`, set by
scaffold.py, its stories required by the UI flow and review, its build run by verify when `commands.storybook` is set."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCAFFOLD = os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py")
DOCTOR = os.path.join(PLUGIN_ROOT, "scripts", "doctor.py")
sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))


class StorybookCase(ProjectTestCase):
    """Helpers only: a test class that subclassed one with tests ran those tests twice."""

    def sc(self, *args):
        p = subprocess.run([sys.executable, SCAFFOLD, "--root", self.root, *args], capture_output=True,
                           encoding="utf-8", errors="replace")
        return p.returncode, p.stdout + p.stderr

    def stored(self):
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            return json.load(f)

    def init(self):
        code, out = self.sc("init", "--kind", "greenfield", "--host", "claude-code")
        self.assertEqual(code, 0, out)


class StorybookTest(StorybookCase):
    # AC-001
    def test_storybook_is_turned_on_only_where_it_exists_and_in_builtin_mode(self):
        self.init()
        code, out = self.sc("storybook", "on")
        self.assertEqual(code, 2, out)  # no .storybook/ folder
        self.write(".storybook/main.js", "module.exports = {}\n")
        code, out = self.sc("storybook", "on")
        self.assertEqual(code, 0, out)
        self.assertIs(self.stored()["storybook"], True)
        self.assertTrue(json.loads(self.sc("storybook")[1])["storybook"])
        self.assertEqual(self.sc("storybook", "off")[0], 0)
        self.assertNotIn("storybook", self.stored())
        cfg = self.stored()
        cfg["design"] = "impeccable"
        self.write(".sdlc/config.json", json.dumps(cfg))
        code, out = self.sc("storybook", "on")
        self.assertEqual(code, 2, out)  # impeccable's DESIGN.md is the system there
        self.assertEqual(self.sc("storybook", "maybe")[0], 2)

    # AC-002
    def test_the_storybook_command_runs_after_build_when_set(self):
        import scaffold
        plan = scaffold.verify_plan({"commands": {"build": "b", "test": "t", "storybook": "s"}})
        steps = [x["step"] for x in plan["verify"]]
        self.assertEqual(steps, ["build", "storybook", "test"])
        plan = scaffold.verify_plan({"commands": {"build": "b", "test": "t"}})
        self.assertEqual([x["step"] for x in plan["verify"]], ["build", "test"])

    # AC-003
    def test_doctor_warns_when_storybook_is_on_but_missing(self):
        self.init()
        cfg = self.stored()
        cfg["storybook"] = True
        self.write(".sdlc/config.json", json.dumps(cfg))
        p = subprocess.run([sys.executable, DOCTOR, "--root", self.root], capture_output=True, encoding="utf-8",
                           errors="replace", env={**os.environ, "CLAUDE_PLUGIN_ROOT": PLUGIN_ROOT})
        checks = {c["check"]: c for c in json.loads(p.stdout)["checks"]}
        self.assertEqual(checks["storybook"]["status"], "warn", checks.get("storybook"))
        self.write(".storybook/main.js", "module.exports = {}\n")
        p = subprocess.run([sys.executable, DOCTOR, "--root", self.root], capture_output=True, encoding="utf-8",
                           errors="replace", env={**os.environ, "CLAUDE_PLUGIN_ROOT": PLUGIN_ROOT})
        checks = {c["check"]: c for c in json.loads(p.stdout)["checks"]}
        self.assertEqual(checks["storybook"]["status"], "ok", checks.get("storybook"))

    # AC-004
    def test_the_ui_flow_and_review_name_the_storybook_rules(self):
        def text(rel):
            with open(os.path.join(PLUGIN_ROOT, rel), encoding="utf-8") as f:
                return f.read()
        for rel, rule in (("skills/orchestrator/references/ui-work.md", "a story for every state"),
                          ("agents/ui-reviewer.md", "with no story in the catalog is off-system"),
                          ("skills/setting-up-projects/references/design-mode.md", "living design system"),
                          ("templates/design-system-template.md", "a story for each state it shows")):
            self.assertIn(rule, text(rel), rel)  # code review SB10: the rules, not just the word
        self.assertIn("scaffold.py\" storybook", text("skills/setting-up-projects/references/design-mode.md")
                      .replace("$S storybook", "scaffold.py\" storybook"))


class StorybookRound1Test(StorybookCase):
    """Code review r1 of 2026-11-23-m-storybook-opt-in."""

    def test_impeccable_mode_turns_storybook_off(self):
        # SB1
        self.init()
        self.write(".storybook/main.js", "module.exports = {}\n")
        self.assertEqual(self.sc("storybook", "on")[0], 0)
        cfg = self.stored()
        cfg["design"] = "impeccable"
        self.write(".sdlc/config.json", json.dumps(cfg))
        self.assertFalse(json.loads(self.sc("storybook")[1])["storybook"])  # reads as off outside builtin
        self.sc("design", "impeccable")
        self.assertNotIn("storybook", self.stored())

    def test_a_monorepo_finds_its_catalog_and_runs_its_root_command(self):
        # SB2, SB3
        import scaffold
        self.init()
        cfg = self.stored()
        cfg["packages"] = [{"name": "ui", "path": "packages/ui", "commands": {"test": "t"}}]
        cfg["commands"] = {"storybook": "s"}
        self.write(".sdlc/config.json", json.dumps(cfg))
        self.write("packages/ui/.storybook/main.js", "module.exports = {}\n")
        self.assertEqual(self.sc("storybook", "on")[0], 0)
        steps = [(x["scope"], x["step"]) for x in scaffold.verify_plan(self.stored())["verify"]]
        self.assertIn("storybook", [s for _, s in steps])

    def test_a_custom_order_without_storybook_is_said(self):
        # SB4
        self.init()
        self.write(".storybook/main.js", "module.exports = {}\n")
        cfg = self.stored()
        cfg["commands"] = {"storybook": "s", "test": "t"}
        cfg["verify"] = {"order": ["lint", "build", "test"]}
        self.write(".sdlc/config.json", json.dumps(cfg))
        code, out = self.sc("storybook", "on")
        self.assertEqual(code, 0, out)
        self.assertIn("verify.order", out)

    def test_the_build_output_is_never_drift_or_committed(self):
        # SB6 (and code review r2: the hooks' security reviews skip it too)
        import verify
        self.assertTrue(verify.GENERATED.search("storybook-static/index.html"))
        self.assertTrue(verify.GENERATED.search("packages/ui/storybook-static/iframe.html"))
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "hooks"))
        import gitutil
        self.assertIn("storybook-static/", gitutil.SKIP_PATH_PATTERNS)

    def test_doctor_names_the_right_fix_for_each_problem(self):
        # code review r2: impeccable mode and a custom order get their own warning and hint
        self.init()
        self.write(".storybook/main.js", "module.exports = {}\n")
        def check(cfg):
            self.write(".sdlc/config.json", json.dumps(cfg))
            p = subprocess.run([sys.executable, DOCTOR, "--root", self.root], capture_output=True, encoding="utf-8",
                               errors="replace", env={**os.environ, "CLAUDE_PLUGIN_ROOT": PLUGIN_ROOT})
            return {c["check"]: c for c in json.loads(p.stdout)["checks"]}["storybook"]
        base = self.stored()
        row = check({**base, "storybook": True, "design": "impeccable"})
        self.assertEqual(row["status"], "warn")
        self.assertIn("impeccable", row["detail"])
        self.assertNotIn("storybook init", row["fix"])
        row = check({**base, "storybook": True, "commands": {"storybook": "s"}, "verify": {"order": ["build"]}})
        self.assertEqual(row["status"], "warn")
        self.assertIn("verify.order", row["fix"])

    def test_the_report_names_package_commands_and_a_cleared_switch(self):
        # code review r2: the command field covers packages; switching to impeccable says it turned Storybook off
        self.init()
        self.write("packages/ui/.storybook/main.js", "module.exports = {}\n")
        cfg = self.stored()
        cfg["packages"] = [{"name": "ui", "path": "packages/ui", "commands": {"storybook": "pnpm build-storybook"}}]
        self.write(".sdlc/config.json", json.dumps(cfg))
        self.assertEqual(self.sc("storybook", "on")[0], 0)
        self.assertEqual(json.loads(self.sc("storybook")[1])["command"], {"ui": "pnpm build-storybook"})
        code, out = self.sc("design", "impeccable")
        self.assertIn("storybook", out.lower())


if __name__ == "__main__":
    unittest.main()
