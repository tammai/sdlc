"""Opt-in guards (.sdlc/2026-11-24-s-gh-92-s-test-lock, issue #92 part 2): config `guards`, set through scaffold.py,
read through the trust anchor like `mode`, `skip` and `approval`."""
import json
import os
import subprocess
import sys
import unittest

from helpers import HOOKS, PLUGIN_ROOT, ProjectTestCase, run_hook

sys.path.insert(0, HOOKS)
SCAFFOLD = os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py")
HOOK = lambda name: [sys.executable, os.path.join(HOOKS, name)]  # noqa: E731  (as hooks.json runs them)
UTF8 = {"PYTHONUTF8": "1"}


class GuardsTest(ProjectTestCase):
    def config(self, **values):
        path = self.path(".sdlc/config.json")
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except OSError:
            data = {}
        data.update(values)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def stop(self):
        _, out, raw, _ = run_hook(HOOK("trust_anchor.py"), {"hook_event_name": "Stop", "cwd": self.root,
                                                            "stop_hook_active": False}, self.root, UTF8)
        return (out or {}).get("decision") == "block", raw

    # AC-002
    def test_turning_a_guard_off_waits_for_the_trust_anchor(self):
        import sdlc_scopes
        self.write(".sdlc/state/login.md", "# login\nStatus: active\nProcess: 3\nTrack: S\nRisk: low\n"
                                           "Top model: opus\nCurrent: Stage 2 – x\n")
        self.config(guards={"s_tests": True})  # on: honoured at once
        self.assertEqual(sdlc_scopes.guards(self.root), ["s_tests"])
        self.assertFalse(self.stop()[0])
        self.config(guards={"s_tests": False})  # off: waits
        self.assertEqual(sdlc_scopes.guards(self.root), ["s_tests"])
        hit, raw = self.stop()
        self.assertTrue(hit, raw)
        self.assertIn("s-tests", raw)
        run_hook(HOOK("trust_anchor.py"), {"hook_event_name": "UserPromptSubmit", "cwd": self.root, "prompt": "ok"},
                 self.root, UTF8)
        self.assertEqual(sdlc_scopes.guards(self.root), [])

    # AC-002 (code review r2 R2-1): a guard name this version doesn't know isn't damage
    def test_an_unknown_guard_in_the_record_keeps_what_was_accepted(self):
        import sdlc_scopes
        self.write(".sdlc/state/login.md", "# login\nStatus: active\nProcess: 3\nTrack: S\nRisk: low\n"
                                           "Top model: opus\nCurrent: Stage 2 – x\n")
        self.config(approval="high-risk")
        self.write(".sdlc/.work/trust-anchor.json", json.dumps({"_config": {
            "mode": "full", "skip": [], "notices": [], "approval": "ml", "guards": ["s_tests", "future_guard"]}}))
        self.assertEqual(sdlc_scopes.approval(self.root), "ml")
        self.assertEqual(sdlc_scopes.guards(self.root), ["s_tests"])
        _, raw = self.stop()
        self.assertNotIn("damaged", raw)
        with open(self.path(".sdlc/.work/trust-anchor.json"), encoding="utf-8") as f:
            self.assertIn("future_guard", json.load(f)["_config"]["guards"])  # kept for the version that knows it

    # AC-003
    def test_scaffold_sets_a_guard_and_the_status_line_shows_it(self):
        sc = lambda *a: subprocess.run([sys.executable, SCAFFOLD, "--root", self.root, *a], capture_output=True,  # noqa: E731
                                       encoding="utf-8", errors="replace")
        self.assertEqual(sc("init", "--kind", "greenfield", "--host", "claude-code").returncode, 0)
        self.assertNotEqual(sc("guard", "everything", "on").returncode, 0)
        p = sc("guard", "s-tests", "on")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["guards"], {"s_tests": True})
        _, _, raw, _ = run_hook(HOOK("session_status.py"), {"hook_event_name": "SessionStart", "cwd": self.root,
                                                            "source": "startup"}, self.root, UTF8)
        self.assertIn("guards s-tests", raw)


if __name__ == "__main__":
    unittest.main()
