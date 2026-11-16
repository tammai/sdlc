"""scripts/capabilities.py: the living spec (#73), one file per capability, grown from each change's ACs at Ship."""
import json
import os
import subprocess
import sys
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "capabilities.py")
SHIP = os.path.join(PLUGIN_ROOT, "scripts", "ship.py")
CHANGE = ("# Sessions\n\n## Acceptance criteria\n\n- **AC-001** Given an idle session, when 30 minutes pass, then it "
          "expires.\n- **AC-002** Given a session, when the user signs out, then it ends.\n\n## Acceptance tests\n\n"
          "| AC | Test | Run |\n|---|---|---|\n| AC-001 | tests/t.py › test_idle | `pytest` |\n"
          "| AC-002 | tests/t.py › test_sign_out | `pytest` |\n\n## Capabilities\n\n{caps}\n")
STATE = "# s\nStatus: active\nProcess: 3\nTrack: {track}\nCurrent: Stage 2 – Build\n\n## Deviations\n-\n"


class CapabilitiesTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc", "living_spec": True}))
        self.write(".sdlc/state/s.md", STATE.format(track="M"))

    def caps(self, text, track="M"):
        self.write("docs/sdlc/changes/s.md", CHANGE.format(caps=text) if text is not None
                   else CHANGE.split("\n## Capabilities")[0] + "\n")
        self.write(".sdlc/state/s.md", STATE.format(track=track))

    def run_it(self, action="merge"):
        p = subprocess.run([sys.executable, SCRIPT, "--root", self.root, action, "s"], capture_output=True,
                           encoding="utf-8")
        return p.returncode, json.loads(p.stdout)

    def spec(self):
        with open(self.path("docs/sdlc/capabilities/sessions.md"), encoding="utf-8") as f:
            return f.read()

    def test_add_then_replace_and_remove_grow_one_file_per_capability(self):
        self.caps("- add sessions: AC-001 AC-002 — How long a sign-in lasts and how it ends")
        self.assertEqual(self.run_it(), (0, {"ok": True, "files": ["docs/sdlc/capabilities/sessions.md"],
                                             "problems": []}))
        text = self.spec()
        self.assertTrue(text.startswith("# sessions\n\nHow long a sign-in lasts and how it ends\n\n## Requirements\n"))
        self.assertIn("### R-001\nGiven an idle session, when 30 minutes pass, then it expires.\n"
                      "- Test: tests/t.py › test_idle\n- From: s AC-001\n", text)
        self.assertIn("### R-002\n", text)
        # a later change: R-001 changes, R-002 goes, a new AC is added after the highest id
        self.caps("- replace sessions R-001: AC-002\n- remove sessions R-002: sign-out moved to accounts\n"
                  "- add sessions: AC-001")
        self.assertEqual(self.run_it()[0], 0)
        text = self.spec()
        self.assertIn("### R-001\nGiven a session, when the user signs out, then it ends.\n", text)
        self.assertIn("### R-003\nGiven an idle session", text)
        self.assertNotIn("### R-002", text)

    def test_what_cant_be_applied_is_refused_and_nothing_is_written(self):
        self.caps("- add sessions: AC-001")  # a new capability without its purpose
        code, out = self.run_it()
        self.assertEqual((code, [p["code"] for p in out["problems"]]), (1, ["capability_needs_purpose"]))
        self.assertFalse(os.path.exists(self.path("docs/sdlc/capabilities/sessions.md")))
        self.caps(None)  # M without the section: the living spec is on, so it must say what it does to it
        self.assertEqual([p["code"] for p in self.run_it()[1]["problems"]], ["capabilities_missing"])
        self.caps(None, track="S")  # S may leave it out
        self.assertEqual(self.run_it(), (0, {"ok": True, "files": [], "problems": []}))
        self.caps("- none: an internal refactor")
        self.assertEqual(self.run_it()[0], 0)
        self.caps("- add sessions: AC-001 — Sessions")
        self.run_it()
        self.caps("- remove sessions R-001: gone")  # emptying a capability deletes a file: only with a retire line
        self.assertEqual([p["code"] for p in self.run_it()[1]["problems"]], ["capability_emptied"])
        self.caps("- retire sessions: replaced by accounts")
        self.assertEqual(self.run_it()[0], 0)
        self.assertFalse(os.path.exists(self.path("docs/sdlc/capabilities/sessions.md")))

    def test_define_sees_the_capabilities_and_its_off_by_default(self):
        self.caps("- add sessions: AC-001 — How long a sign-in lasts")
        self.run_it()
        brief = subprocess.run([sys.executable, os.path.join(PLUGIN_ROOT, "scripts", "brief.py"), "--root", self.root],
                               capture_output=True, encoding="utf-8").stdout
        self.assertIn("===== living spec: docs/sdlc/capabilities/", brief)
        self.assertIn("\nsessions: How long a sign-in lasts\n", brief)  # so Define reuses the name
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc"}))
        self.caps("- add accounts: AC-001 — Accounts")
        self.assertEqual(self.run_it(), (0, {"ok": True, "files": [], "problems": []}))


class ShipLivingSpecTest(ProjectTestCase):
    """ship.py checks the section before anything moves and writes the files into Ship's commit."""

    def setUp(self):
        super().setUp()
        git = ["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run(git + ["init", "-q", "-b", "main"], check=True)
        self.write(".gitignore", ".sdlc/.work/\n")
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"print('ok')\""},
                                                    "living_spec": True}))
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "base"], check=True)
        self.write(".sdlc/s/state.md", STATE.format(track="M"))

    def change(self, caps):
        self.write(".sdlc/s/change.md", CHANGE.replace("`pytest`", "manual").replace(
            "tests/t.py › test_idle", "manual").replace("tests/t.py › test_sign_out", "manual").format(caps=caps))

    def ship(self, caps):
        self.change(caps)
        p = subprocess.run([sys.executable, SHIP, "--root", self.root, "s", "--json", "--review", "none ran"],
                           capture_output=True, encoding="utf-8")
        return p.returncode, json.loads(p.stdout)

    def test_ship_writes_the_capability_file_or_refuses_before_anything_moves(self):
        code, out = self.ship("- replace sessions R-001: AC-001")
        self.assertEqual((code, out["problems"][0]["code"], out["problems"][1]["code"]),
                         (1, "capabilities_invalid", "capability_unknown"))
        with open(self.path(".sdlc/s/state.md"), encoding="utf-8") as f:
            self.assertIn("Current: Stage 2", f.read())
        # an earlier Ship wrote the file, then stopped before its commit: rerunning applies the section once, not twice
        self.change("- add sessions: AC-001 — Sessions")
        subprocess.run([sys.executable, SCRIPT, "--root", self.root, "merge", "s"], capture_output=True)
        code, out = self.ship("- add sessions: AC-001 — Sessions")
        self.assertEqual(code, 0, out)
        with open(self.path(".sdlc/capabilities/sessions.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("### R-001\n", text)
        self.assertNotIn("### R-002", text)
        self.assertEqual(out["capabilities"], [".sdlc/capabilities/sessions.md"])  # the legacy layout's docs
        self.assertIn(".sdlc/capabilities/sessions.md", out["staged"])


if __name__ == "__main__":
    unittest.main()
