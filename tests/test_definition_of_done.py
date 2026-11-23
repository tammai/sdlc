"""A project's Definition of Done (.sdlc/2026-11-23-m-definition-of-done): config `done`, set by scaffold.py, printed
by brief.py, ticked in the change file and checked by ship.py."""
import json
import os
import subprocess
import sys
import unittest

from helpers import HOOKS, PLUGIN_ROOT, ProjectTestCase, run_hook

sys.path.insert(0, HOOKS)
SCAFFOLD = os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py")
SHIP = os.path.join(PLUGIN_ROOT, "scripts", "ship.py")
BRIEF = os.path.join(PLUGIN_ROOT, "scripts", "brief.py")
STATE = ("# Feature: login\nStatus: active\nProcess: 3\nCurrent: Stage 2 – Build\nBase: {base}\n\n## Stages\n"
         "- [ ] 1 Define\n- [ ] 2 Build\n- [ ] 4 Ship\n\n## Tasks\n\n1. **Store**\n   - Files: `src/store.py`\n\n"
         "## Public Surface\n\n- none\n\n## Gate log\n-\n\n## Deviations\n-\n")
CHANGE = "# Change\n\n## Acceptance criteria\n\n## Acceptance tests\n\n| AC | Test | Run |\n|---|---|---|\n"
DONE = ["CHANGELOG has a line for any user-visible change", "Docs updated where behaviour changed"]


class DefinitionOfDoneTest(ProjectTestCase):
    def run_py(self, script, *args, **env):
        p = subprocess.run([sys.executable, script, "--root", self.root, *args], capture_output=True,
                           encoding="utf-8", errors="replace", env={**os.environ, **env})
        return p.returncode, p.stdout + p.stderr

    def git(self, *args):
        subprocess.run(["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t", *args], check=True)

    def stored(self):
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            return json.load(f)

    # AC-001
    def test_the_list_is_set_through_scaffold_within_its_limits(self):
        self.assertEqual(self.run_py(SCAFFOLD, "init", "--kind", "greenfield", "--host", "claude-code")[0], 0)
        code, out = self.run_py(SCAFFOLD, "done", *DONE)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.stored()["done"], DONE)
        self.assertEqual(json.loads(self.run_py(SCAFFOLD, "done")[1])["done"], DONE)
        for bad in ([""], ["x" * 201], [f"item {i}" for i in range(11)], ["two\nlines"], ["Docs — README"], ["Docs\u2028more"]):
            code, out = self.run_py(SCAFFOLD, "done", *bad)
            self.assertEqual(code, 2, (bad, out))
        self.assertEqual(self.stored()["done"], DONE)
        self.assertEqual(self.run_py(SCAFFOLD, "done", "--clear", "x")[0], 2)  # code review DOD11
        self.assertEqual(self.run_py(SCAFFOLD, "done", "--clear")[0], 0)
        self.assertNotIn("done", self.stored())

    # AC-002
    def test_the_brief_prints_the_list(self):
        self.write(".sdlc/config.json", json.dumps({"done": DONE}))
        code, out = self.run_py(BRIEF)
        self.assertIn("definition of done", out.lower())
        for item in DONE:
            self.assertIn(item, out)

    def ship_setup(self, done):
        self.git("init", "-q", "-b", "main")
        self.write(".gitignore", ".sdlc/.work/\n")
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"print('ok')\""}, "done": done}))
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        base = subprocess.run(["git", "-C", self.root, "rev-parse", "HEAD"], capture_output=True,
                              encoding="utf-8").stdout.strip()
        self.write(".sdlc/login/state.md", STATE.format(base=base))
        self.write("src/store.py", "x = 1\n")

    def ship(self):
        return self.run_py(SHIP, "login", "--review", "No review ran: low risk.")

    # AC-003
    def test_ship_refuses_until_every_item_is_ticked_with_evidence(self):
        self.ship_setup(DONE)
        for section, ok in (
                ("", False),  # no section
                (f"- [x] {DONE[0]} — added a line\n", False),  # one item missing
                (f"- [x] {DONE[0]} — added a line\n- [ ] {DONE[1]} — later\n", False),  # unticked
                (f"- [x] {DONE[0]} — added a line\n- [x] {DONE[1]}\n", False),  # no evidence
                (f"- [x] {DONE[0].upper()} — added a line\n- [x] {DONE[1]} — n/a: no docs touch this\n", True)):
            self.write(".sdlc/login/change.md", CHANGE + (f"\n## Definition of Done\n\n{section}" if section else ""))
            code, out = self.ship()
            self.assertEqual(code == 0, ok, (section, out))
            if not ok:
                self.assertIn("Definition of Done isn't met", out)
                with open(self.path(".sdlc/login/state.md"), encoding="utf-8") as f:
                    self.assertIn("Status: active", f.read())  # nothing moved

    def test_ship_holds_the_bar_the_feature_started_with(self):
        # code review DOD3, DOD4, DOD8, DOD9: an item at Base can't be dropped; an invalid list fails closed; a
        # refusal writes nothing; evidence is real; any ticked line counts
        self.ship_setup(DONE)
        ticked_first = f"- [x] {DONE[0]} — added a line\n"
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"print('ok')\""},
                                                   "done": DONE[:1]}))  # dropped after Base
        self.write(".sdlc/login/change.md", CHANGE + "\n## Definition of Done\n\n" + ticked_first)
        code, out = self.ship()
        self.assertNotEqual(code, 0, out)
        self.assertIn(DONE[1], out)
        with open(self.path(".sdlc/login/change.md"), encoding="utf-8") as f:
            self.assertNotIn("## Review", f.read())  # nothing written on a refusal
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"print('ok')\""},
                                                   "done": "not a list"}))
        code, out = self.ship()
        self.assertNotEqual(code, 0, out)
        self.assertIn("isn't valid", out)
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"print('ok')\""},
                                                   "done": DONE}))
        for weak in ("n/a", "n/a:", "<evidence>", "n/a: <reason>"):
            self.write(".sdlc/login/change.md", CHANGE + "\n## Definition of Done\n\n" + ticked_first
                       + f"- [x] {DONE[1]} — {weak}\n")
            code, out = self.ship()
            self.assertNotEqual(code, 0, (weak, out))
        self.write(".sdlc/login/change.md", CHANGE + "\n## Definition of Done\n\n" + ticked_first
                   + f"- [x] {DONE[1]} — README updated\n- [ ] {DONE[1]}\n")  # a stray unticked copy
        code, out = self.ship()
        self.assertEqual(code, 0, out)

    def test_the_last_accepted_list_is_the_bar(self):
        # code review r2 #1, #2: the user's accepted edit counts; an item they added can't be dropped unseen
        import trust_anchor
        self.ship_setup(DONE)
        cfg = {"commands": {"test": "python3 -c \"print('ok')\""}}
        self.write(".sdlc/config.json", json.dumps({**cfg, "done": DONE[:1]}))
        self.write(".sdlc/.work/trust-anchor.json", json.dumps(
            {"login": {"commands_ok": trust_anchor.commands(json.dumps({**cfg, "done": DONE[:1]}))}}))
        self.write(".sdlc/login/change.md", CHANGE + f"\n## Definition of Done\n\n- [x] {DONE[0]} — a line\n")
        code, out = self.ship()
        self.assertEqual(code, 0, out)  # the user removed DONE[1] and accepted it
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "next")
        base = subprocess.run(["git", "-C", self.root, "rev-parse", "HEAD"], capture_output=True,
                              encoding="utf-8").stdout.strip()
        self.write(".sdlc/login/state.md", STATE.format(base=base))
        self.write(".sdlc/.work/trust-anchor.json", json.dumps(
            {"login": {"commands_ok": trust_anchor.commands(json.dumps({**cfg, "done": DONE}))}}))
        self.write(".sdlc/config.json", json.dumps(cfg))  # the agent drops the accepted list
        code, out = self.ship()
        self.assertNotEqual(code, 0, out)
        self.assertIn(DONE[1], out)

    def test_odd_configs_fail_closed_or_mean_none(self):
        # code review r2 #7, #11: a malformed config is said; an empty list means none
        self.ship_setup(None)
        self.write(".sdlc/login/change.md", CHANGE)
        self.write(".sdlc/config.json", '{"commands": {"test": "true"}, "done": ["x"],}')
        code, out = self.run_py(BRIEF)
        self.assertIn("isn't valid", out)
        code, out = self.ship()
        self.assertNotEqual(code, 0, out)
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"print('ok')\""}, "done": []}))
        code, out = self.ship()
        self.assertEqual(code, 0, out)

    def test_the_heading_is_read_one_way(self):
        # code review r2 #4: the anchor and Ship share one heading rule
        import re
        import sdlc_scopes
        import trust_anchor  # noqa: F401
        for heading in ("## Definition of Done", "##  Definition of Done", "## Definition of Done  "):
            self.assertTrue(re.search(sdlc_scopes.DONE_HEADING, heading + "\n", re.M), heading)
        self.assertFalse(re.search(sdlc_scopes.DONE_HEADING, "## Definition of Done (team)\n", re.M))

    def test_done_needs_a_set_up_repo(self):
        # code review r2 #9
        code, out = self.run_py(SCAFFOLD, "done", "x")
        self.assertNotEqual(code, 0, out)
        self.assertFalse(os.path.exists(self.path(".sdlc/config.json")))

    def test_ticking_the_checklist_in_review_is_no_trust_anchor_notice(self):
        # code review DOD2: the section is filled in at Ship, after Review began
        self.ship_setup(DONE)
        with open(self.path(".sdlc/login/state.md"), encoding="utf-8") as f:
            state = f.read().replace("Current: Stage 2 – Build", "Current: Stage 3 – Review")
        self.write(".sdlc/login/state.md", state.replace("Status: active\n", "Status: active\nTrack: M\nRisk: low\n"))
        self.write(".sdlc/login/change.md", CHANGE + "\n## Definition of Done\n\n" + "".join(f"- [ ] {x}\n" for x in DONE))
        stop = {"hook_event_name": "Stop", "cwd": self.root, "stop_hook_active": False}
        hook = ["python3", os.path.join(HOOKS, "trust_anchor.py")]
        run_hook(hook, stop, self.root)
        self.write(".sdlc/login/change.md", CHANGE + "\n## Definition of Done\n\n"
                   + "".join(f"- [x] {x} — done\n" for x in DONE))
        _, out, raw, _ = run_hook(hook, stop, self.root)
        self.assertNotIn("criteria or tests changed", raw)

    def test_no_list_keeps_the_old_anchor_shape(self):
        # code review DOD7: a config without `done` serialises as before, so an old anchor doesn't read as changed
        import trust_anchor
        self.assertNotIn("done", trust_anchor.commands(json.dumps({"commands": {"test": "x"}})))

    def test_setup_routes_the_done_argument(self):
        # code review DOD5, DOD6
        with open(os.path.join(PLUGIN_ROOT, "commands", "setup.md"), encoding="utf-8") as f:
            self.assertIn("Arguments are `done`", f.read())
        with open(os.path.join(PLUGIN_ROOT, "skills", "setting-up-projects", "SKILL.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Never mark a step done without doing it.", text)
        self.assertIn("the user can delete any", text)

    def test_no_list_ships_as_before(self):
        self.ship_setup(None)
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"print('ok')\""}}))
        self.write(".sdlc/login/change.md", CHANGE)
        code, out = self.ship()
        self.assertEqual(code, 0, out)

    # AC-004
    def test_a_changed_list_is_a_trust_anchor_notice(self):
        self.ship_setup(DONE)
        state = STATE.replace("Status: active\n", "Status: active\nTrack: M\nRisk: low\nTop model: opus\n")
        with open(self.path(".sdlc/login/state.md"), encoding="utf-8") as f:
            base = [l for l in f.read().splitlines() if l.startswith("Base:")][0]
        self.write(".sdlc/login/state.md", state.replace("Base: {base}", base))
        stop = {"hook_event_name": "Stop", "cwd": self.root, "stop_hook_active": False}
        hook = ["python3", os.path.join(HOOKS, "trust_anchor.py")]
        run_hook(hook, stop, self.root)
        self.write(".sdlc/config.json", json.dumps({"commands": {"test": "python3 -c \"print('ok')\""},
                                                   "done": DONE[:1]}))
        _, out, raw, _ = run_hook(hook, stop, self.root)
        self.assertEqual((out or {}).get("decision"), "block", raw)
        self.assertIn("done (Definition of Done)", raw)  # code review DOD13

    # AC-005
    def test_the_flow_and_setup_text_name_it(self):
        def text(rel):
            with open(os.path.join(PLUGIN_ROOT, rel), encoding="utf-8") as f:
                return f.read()
        for rel in ("skills/orchestrator/references/flow.md", "skills/orchestrator/references/s-track.md",
                    "templates/change-template.md", "skills/setting-up-projects/SKILL.md"):
            self.assertIn("Definition of Done", text(rel), rel)
        self.assertIn("scaffold.py\" done", text("skills/setting-up-projects/references/definition-of-done.md")
                      .replace("$S done", "scaffold.py\" done"))


if __name__ == "__main__":
    unittest.main()
