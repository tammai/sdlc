"""Team mode (.sdlc/2026-11-23-l-team-mode): config `team`, role agents for Define, Build and Ship held by the role
guard and the model router, and the orchestrator as their coordinator."""
import json
import os
import subprocess
import sys
import unittest

from helpers import HOOKS, PLUGIN_ROOT, ProjectTestCase, run_hook

SCAFFOLD = os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py")
ROLE_GUARD = ["python3", os.path.join(HOOKS, "role_guard.py")]
ROUTER = ["python3", os.path.join(HOOKS, "model_router.py")]


class TeamModeTest(ProjectTestCase):
    def sc(self, *args):
        p = subprocess.run([sys.executable, SCAFFOLD, "--root", self.root, *args], capture_output=True,
                           encoding="utf-8", errors="replace")
        return p.returncode, p.stdout + p.stderr

    def write_as(self, agent, rel):
        payload = {"hook_event_name": "PreToolUse", "cwd": self.root, "agent_type": f"sdlc:{agent}",
                   "tool_name": "Write", "tool_input": {"file_path": self.path(rel), "content": "x"}}
        _, out, raw, _ = run_hook(ROLE_GUARD, payload, self.root)
        return (out or {}).get("hookSpecificOutput", {}).get("permissionDecision")

    # AC-001
    def test_team_is_set_through_scaffold_in_full_mode_only(self):
        self.assertNotEqual(self.sc("team", "on")[0], 0)  # before setup
        self.assertEqual(self.sc("init", "--kind", "greenfield", "--host", "claude-code")[0], 0)
        self.assertEqual(self.sc("team", "on")[0], 0)
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            self.assertIs(json.load(f)["team"], True)
        self.assertTrue(json.loads(self.sc("team")[1])["team"])
        def status():
            start = {"hook_event_name": "SessionStart", "cwd": self.root, "source": "startup"}
            _, _, raw, _ = run_hook(["python3", os.path.join(HOOKS, "session_status.py")], start, self.root)
            return raw
        self.assertIn("team (role agents", status())
        self.assertEqual(self.sc("team", "maybe")[0], 2)
        self.assertEqual(self.sc("team", "off")[0], 0)
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            self.assertNotIn("team", json.load(f))
        self.assertNotIn("team (role agents", status())
        self.assertEqual(self.sc("team", "on")[0], 0)
        self.assertEqual(self.sc("mode", "advisory")[0], 0)
        with open(self.path(".sdlc/config.json"), encoding="utf-8") as f:
            self.assertNotIn("team", json.load(f))  # advisory drops it: back to full doesn't turn it on unasked
        self.assertNotIn("team (role agents", status())
        self.assertEqual(self.sc("team", "on")[0], 2)  # advisory runs no flow

    # AC-002
    def test_the_analyst_writes_only_the_change_file(self):
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc"}))
        self.assertEqual(self.write_as("analyst", "src/app.py"), "deny")
        self.assertEqual(self.write_as("analyst", "tests/test_app.py"), "deny")
        for rel in ("docs/sdlc/changes/login.md", ".sdlc/state/login.md", ".sdlc/state/login/backlog.md",
                    "docs/sdlc/objects.md"):
            self.assertIsNone(self.write_as("analyst", rel), rel)
        for rel in (".sdlc/config.json", ".sdlc/baseline.md", ".sdlc/.work/findings/login/code-reviewer-r1.md",
                    "docs/sdlc/constitution.md", "docs/sdlc/design-system.md", ".sdlc/state/login/../../config.json",
                    ".sdlc/todo.md", "docs/sdlc/recurring-defects.md", ".sdlc/.work/trust-anchor.json",
                    ".sdlc/.work/review-rounds.json", ".sdlc/config.json::$DATA", ".sdlc/CONFIG~1.JSO",
                    ".sdlc/state/login/notes.md:x", "docs/sdlc/changes/LOGIN~1.MD"):
            self.assertEqual(self.write_as("analyst", rel), "deny", rel)
        for rel in (".sdlc/newfeat/change.md", ".sdlc/ci/invariants.py", ".sdlc/lint/x.toml"):
            self.assertEqual(self.write_as("analyst", rel), "deny", rel)  # docs_dir set: no new old-layout folder
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc", "objects": "docs/domain/objects.md"}))
        self.assertIsNone(self.write_as("analyst", "docs/domain/objects.md"))
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc", "objects": ".claude/settings.json"}))
        self.assertEqual(self.write_as("analyst", ".claude/settings.json"), "deny")

    # AC-002, the old layout: a feature's folder under .sdlc/
    def test_the_analyst_writes_only_the_change_file_in_the_old_layout(self):
        for rel in (".sdlc/login/change.md", ".sdlc/login/state.md", ".sdlc/login/backlog.md", ".sdlc/objects.md"):
            self.assertIsNone(self.write_as("analyst", rel), rel)
        self.write(".sdlc/ci/invariants.py", "")  # the scaffold's own folders under .sdlc/ are no feature's
        self.write(".sdlc/old-feature/state.md", "# old\n")
        self.assertIsNone(self.write_as("analyst", ".sdlc/old-feature/change.md"))
        self.write(".sdlc/drafted/change.md", "# drafted\n")  # Define's first write made the folder, no state yet
        for rel in (".sdlc/drafted/change.md", ".sdlc/drafted/backlog.md"):
            self.assertIsNone(self.write_as("analyst", rel), rel)
        for rel in (".sdlc/lint/x.toml", ".sdlc/capabilities/x.json"):
            self.assertEqual(self.write_as("analyst", rel), "deny", rel)  # the scaffold's names, present or not
        for rel in (".sdlc/config.json", ".sdlc/constitution.md", ".sdlc/.work/findings/login/r1.md",
                    ".sdlc/Config.json", ".sdlc/ci/invariants.py", ".sdlc/ci/new.sh", ".sdlc/Bad_Name/change.md"):
            self.assertEqual(self.write_as("analyst", rel), "deny", rel)

    # AC-003
    def test_the_builder_never_writes_the_change_file(self):
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc"}))
        self.assertIsNone(self.write_as("builder", "src/app.py"))
        self.assertIsNone(self.write_as("builder", "tests/test_app.py"))
        self.assertEqual(self.write_as("builder", "docs/sdlc/changes/login.md"), "deny")
        self.assertEqual(self.write_as("builder", ".sdlc/login/change.md"), "deny")
        for rel in (".sdlc/login/change.md::$DATA", ".sdlc/login/CHANGE~1.MD", ".sdlc/login/change.md.",
                    "SDLC~1/login/change.md", "docs/SDLC~1/changes/login.md",
                    "docs/sdlc/changes/../changes/login.md"):
            self.assertEqual(self.write_as("builder", rel), "deny", rel)
        for rel in ("src/fixtures/a~1.json", "notes/12:30.md"):
            self.assertIsNone(self.write_as("builder", rel), rel)  # product names, nowhere near the record

    # AC-001 (2026-11-23-s-team-guard-followups)
    def test_the_builder_leaves_the_review_and_the_state_alone(self):
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc"}))
        folded = (".sdlc/.WORK/findings/login/r1.md",) if sys.platform in ("darwin", "win32") else ()
        for rel in (".sdlc/.work/findings/login/code-reviewer-r1.md", ".sdlc/state/login.md") + folded:
            self.assertEqual(self.write_as("builder", rel), "deny", rel)
        for rel in ("src/app.py", "tests/test_app.py", ".sdlc/state/login/backlog.md", ".sdlc/.work/scratch.txt"):
            self.assertIsNone(self.write_as("builder", rel), rel)
        self.write(".sdlc/config.json", json.dumps({}))
        self.write(".sdlc/login/state.md", "# login\n")
        self.assertEqual(self.write_as("builder", ".sdlc/login/state.md"), "deny")
        self.assertIsNone(self.write_as("builder", ".sdlc/login/backlog.md"))

    # AC-002 (2026-11-23-s-team-guard-followups)
    def test_an_objects_path_through_a_link_is_judged_where_it_leads(self):
        os.makedirs(self.path(".claude/agents"))
        os.makedirs(self.path("docs"))
        os.symlink(self.path(".claude/agents"), self.path("docs/agents"))
        self.write(".sdlc/config.json", json.dumps({"objects": "docs/agents/objects.md"}))
        self.assertEqual(self.write_as("analyst", "docs/agents/objects.md"), "deny")
        absolute = self.path("docs/domain/objects.md")
        self.write(".sdlc/config.json", json.dumps({"objects": absolute}))
        self.assertEqual(self.write_as("analyst", "docs/domain/objects.md"), "deny")
        self.write(".sdlc/config.json", json.dumps({"objects": "docs/domain/objects.md"}))
        self.assertIsNone(self.write_as("analyst", "docs/domain/objects.md"))

    @unittest.skipUnless(sys.platform in ("darwin", "win32"), "a case-insensitive file system")
    def test_the_builder_never_writes_the_change_file_by_another_case(self):
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc"}))
        for rel in (".SDLC/login/Change.md", "docs/sdlc/Changes/login.MD", "Docs/SDLC/changes/login.md"):
            self.assertEqual(self.write_as("builder", rel), "deny", rel)

    # AC-004
    def test_the_releaser_writes_no_product_code(self):
        self.assertEqual(self.write_as("releaser", "src/app.py"), "deny")
        self.assertEqual(self.write_as("releaser", "tests/test_app.py"), "deny")
        for rel in ("knowledge/gotchas/x.md", "CHANGELOG.md", ".sdlc/recurring-defects.md", ".sdlc/login/change.md",
                    "CLAUDE.md", ".claude/rules/api.md", ".claude/hookify.no-force.local.md",
                    "packages/web/CHANGELOG.md", "AGENTS.md"):
            self.assertIsNone(self.write_as("releaser", rel), rel)
        for rel in (".claude/hookifyx.py", ".claude/hookify", ".claude/settings.json"):
            self.assertEqual(self.write_as("releaser", rel), "deny", rel)

    # AC-005
    def test_the_analyst_runs_on_the_top_tier(self):
        self.write(".sdlc/login/state.md", "# login\nStatus: active\nProcess: 3\nTrack: M\nRisk: low\nTop model: opus\n")
        def dispatch(model):
            payload = {"hook_event_name": "PreToolUse", "cwd": self.root, "tool_name": "Agent",
                       "tool_input": {"subagent_type": "sdlc:analyst", "model": model, "description": "d",
                                      "prompt": "p"}}
            _, out, raw, _ = run_hook(ROUTER, payload, self.root)
            return (out or {}).get("hookSpecificOutput", {}).get("permissionDecision")
        self.assertEqual(dispatch("sonnet"), "deny")
        self.assertIsNone(dispatch("opus"))

    # AC-005, before Define's state file exists: team mode's config holds it
    def test_the_analyst_runs_on_the_top_tier_before_any_state(self):
        def dispatch(agent, model):
            payload = {"hook_event_name": "PreToolUse", "cwd": self.root, "tool_name": "Agent",
                       "tool_input": {"subagent_type": f"sdlc:{agent}", "model": model, "description": "d",
                                      "prompt": "p"}}
            _, out, raw, _ = run_hook(ROUTER, payload, self.root)
            return (out or {}).get("hookSpecificOutput", {}).get("permissionDecision")
        self.write(".sdlc/config.json", json.dumps({}))
        self.assertIsNone(dispatch("analyst", "sonnet"))  # no team, no feature: silent as before
        self.write(".sdlc/config.json", json.dumps({"team": True}))
        self.assertEqual(dispatch("analyst", "sonnet"), "deny")
        self.assertIsNone(dispatch("analyst", "opus"))
        self.assertEqual(dispatch("analyst", "fable"), "deny")  # fable is the user's call, set in a state file
        self.assertIsNone(dispatch("builder", "sonnet"))

    # AC-006
    def test_the_agents_and_the_flow_describe_team_mode(self):
        def text(rel):
            with open(os.path.join(PLUGIN_ROOT, rel), encoding="utf-8") as f:
                return f.read()
        for name in ("analyst", "builder", "releaser"):
            body = text(f"agents/{name}.md")
            self.assertTrue(body.startswith(f"---\nname: {name}\n"), name)
            self.assertIn("team mode", body.lower(), name)
        def section(body):
            start = body.index("**Team mode.**")
            return body[start:body.index("\n\n", start)]
        self.assertEqual(section(text("skills/orchestrator/SKILL.md")), section(text("commands/start.md")))
        for word in ("sdlc:analyst", "sdlc:builder", "sdlc:releaser", "coordinat"):
            self.assertIn(word, section(text("skills/orchestrator/SKILL.md")))
        self.assertIn("team mode", text("skills/orchestrator/references/flow.md").lower())
        # Define's gate call has one owner: the builder starts at the red step, never `advance 2` again
        self.assertNotIn("advance <f> 2", text("agents/builder.md"))
        # setup asks the question before init, so `team on` runs after it
        self.assertIn("after `init`", text("skills/setting-up-projects/references/advisory.md"))


if __name__ == "__main__":
    unittest.main()
