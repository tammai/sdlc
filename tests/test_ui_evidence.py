"""UI evidence and the setup's solo or shared checks (.sdlc/2026-11-24-m-gh-92-ui-evidence-profile, issue #92 part 4): with config
`guards.ui_evidence` on, Ship needs screenshots (or a manual reason) for a change touching `areas.ui`; `scaffold.py
checks` writes the solo or shared defaults."""
import json
import os
import subprocess
import sys
import unittest

from helpers import HOOKS, PLUGIN_ROOT, ProjectTestCase, run_hook
import test_ship

sys.path.insert(0, HOOKS)
SCAFFOLD = os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py")


class UiEvidenceTest(test_ship.ShipTest):
    def setUp(self):
        super().setUp()
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"print('ok')\""},
                                                    "guards": {"ui_evidence": True}}))
        self.git("add", ".sdlc/config.json")
        self.git("commit", "-q", "-m", "guard on")
        base = self.out("rev-parse", "HEAD").strip()
        self.write(".sdlc/login/state.md", test_ship.STATE.format(base=base).replace(
            "## Tasks\n\n1. **Store**\n   - Files: `src/store.py`",
            "## Tasks\n\n1. **Store**\n   - Files: `src/store.py`, `src/App.tsx`").replace(
            "## Deviations\n-\n", "## Deviations\n- App What: a screen. Why: the test. Effect: none.\n"))
        import sdlc_layout
        self.work = sdlc_layout.paths(self.root, "login")["work"]

    def message(self):
        with open(self.path(".sdlc/.work/commit-msg.txt"), encoding="utf-8") as f:
            return f.read()

    # AC-001
    def test_a_ui_change_without_evidence_is_refused(self):
        self.write("src/App.tsx", "export const App = () => null\n")
        code, out = self.ship()
        self.assertNotEqual(code, 0, out)
        self.assertIn("UI evidence", out)
        cfg = {"commands": {"test": "python3 -c \"print('ok')\""}, "guards": {"ui_evidence": True}}
        self.write(".sdlc/config.json", json.dumps({**cfg, "areas": {"ui": []}}))  # config can't narrow it away
        code, out = self.ship()
        self.assertNotEqual(code, 0, out)
        self.write(".sdlc/config.json", json.dumps({**cfg, "areas": {"ui": None}}))  # nor break it
        code, out = self.ship()
        self.assertNotEqual(code, 0, out)
        self.assertNotIn("Traceback", out)
        self.write(".sdlc/config.json", json.dumps(cfg))
        os.remove(self.path("src/App.tsx"))
        code, out = self.ship()  # nothing in areas.ui: nothing asked
        self.assertEqual(code, 0, out)

    # AC-002
    def test_screenshots_ship_and_are_listed(self):
        self.write("src/App.tsx", "export const App = () => null\n")
        self.write(os.path.join(self.work, "ui", "home-after.png"), "png")
        code, out = self.ship()
        self.assertEqual(code, 0, out)
        self.assertIn("UI evidence", self.message())
        self.assertIn("home-after.png", self.message())

    # AC-002
    def test_a_manual_reason_ships_and_is_listed(self):
        self.write("src/App.tsx", "export const App = () => null\n")
        with open(self.path(".sdlc/login/change.md"), "a", encoding="utf-8") as f:
            f.write("\n## UI evidence\n\n- manual: no browser in CI\n")
        code, out = self.ship()
        self.assertEqual(code, 0, out)
        self.assertIn("- manual: no browser in CI", self.message())


import test_workbench  # noqa: E402


class WorkbenchUiEvidenceTest(test_workbench.WorkbenchShipCase):
    # AC-001 (code review r2 N1): in a workbench, a UI change in a branched app repo needs its evidence too
    def test_a_ui_change_in_an_app_repo_without_evidence_is_refused(self):
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        self.write(".sdlc/config.json", json.dumps({**cfg, "guards": {"ui_evidence": True}}))
        self.assertEqual(self.state("repo", "feat", "web")[0], 0)
        self.write("web/src/App.tsx", "export const App = () => null\n")
        self.state("deviation", "feat", "web/src/App.tsx .sdlc/config.json What: a screen. Why: test. Effect: none.")
        code, out = self.ship("--review", "No review ran: test.")
        self.assertNotEqual(code, 0, out)
        self.assertIn("UI evidence", out)


class ChecksTest(ProjectTestCase):
    def sc(self, *a):
        p = subprocess.run([sys.executable, SCAFFOLD, "--root", self.root, *a], capture_output=True,
                           encoding="utf-8", errors="replace")
        return p.returncode, p.stdout + p.stderr

    def config(self):
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            return json.load(f)

    # AC-003
    def test_checks_writes_the_solo_or_shared_defaults(self):
        self.assertEqual(self.sc("init", "--kind", "greenfield", "--host", "claude-code")[0], 0)
        self.assertNotEqual(self.sc("checks", "everyone")[0], 0)
        code, out = self.sc("checks", "shared")
        self.assertEqual(code, 0, out)
        cfg = self.config()
        self.assertEqual(cfg["approval"], "ml")
        self.assertEqual(cfg["guards"], {"s_tests": True, "dependencies": True, "lint_config": True,
                                         "ui_evidence": True})
        code, out = self.sc("checks", "solo")
        self.assertEqual(code, 0, out)
        cfg = self.config()
        self.assertNotIn("approval", cfg)
        self.assertNotIn("guards", cfg)
        self.assertEqual(self.sc("approval", "always")[0], 0)
        self.assertEqual(self.sc("checks", "shared")[0], 0)
        self.assertEqual(self.config()["approval"], "always")  # shared never lowers a stricter setting


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    for cls in (UiEvidenceTest, WorkbenchUiEvidenceTest, ChecksTest):
        for name in loader.getTestCaseNames(cls):
            if name in cls.__dict__:
                suite.addTest(cls(name))
    return suite


if __name__ == "__main__":
    unittest.main()
