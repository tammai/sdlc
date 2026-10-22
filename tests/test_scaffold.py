"""scripts/scaffold.py: lock, file classes, keyed merges, migrations, upgrade and eject plans."""
import json
import os
import shutil
import sys
import tempfile
import unittest

from helpers import PLUGIN_ROOT, ProjectTestCase, run_hook

SCRIPT = os.path.join(PLUGIN_ROOT, "scripts", "scaffold.py")


class ScaffoldTest(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.plugin = os.path.realpath(tempfile.mkdtemp(prefix="sdlc-fake-plugin-"))
        self.addCleanup(shutil.rmtree, self.plugin, ignore_errors=True)
        self.set_plugin_version("1.3.0")
        self.template("templates/project/rules.md", "v{{plugin_version}} test: {{config.verify.full}}\n")
        self.template("templates/project/ci.yml", "run: just verify\n")
        self.template("templates/project/config.defaults.json",
                      json.dumps({"verify": {"full": ["just verify", "just test"]}, "areas": {"tests": ["**/*.test.*"]}}))

    # --- fixtures -------------------------------------------------------------------

    def set_plugin_version(self, v):
        self.plugin_file(".claude-plugin/plugin.json", json.dumps({"name": "sdlc", "version": v}))

    def plugin_file(self, rel, text):
        full = os.path.join(self.plugin, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(text)

    template = plugin_file

    def migration(self, name, version=None, summary="s"):
        fm = f"version: {version}\n" if version else ""
        self.plugin_file(f"migrations/{name}.md", f"---\n{fm}summary: {summary}\n---\n\nSteps.\n")

    def sc(self, *args, expect=0, plugin=None):
        code, out, raw, err = run_hook([sys.executable, SCRIPT, "--root", self.root, *args], "", self.root,
                                       env_extra={"CLAUDE_PLUGIN_ROOT": plugin or self.plugin})
        self.assertEqual(code, expect, f"{args}: {raw}{err}")
        self.assertIsNotNone(out, raw + err)
        return out

    def init(self, kind="brownfield"):
        return self.sc("init", "--kind", kind)

    def read(self, rel):
        with open(self.path(rel), encoding="utf-8") as f:
            return f.read()

    def lock(self):
        return json.loads(self.read(".sdlc/scaffold.lock.json"))

    def config(self):
        return json.loads(self.read(".sdlc/config.json"))

    # --- init / status / steps -----------------------------------------------------------

    def test_status_before_setup(self):
        out = self.sc("status")
        self.assertEqual(out["setup"], "none")
        self.assertFalse(out["configured"])

    def test_init_writes_config_and_lock(self):
        self.init("greenfield")
        self.assertEqual(self.lock()["scaffold_version"], "1.3.0")
        self.assertEqual(self.config()["min_plugin_version"], "1.3.0")
        self.assertEqual(self.config()["project"]["kind"], "greenfield")
        self.assertEqual(self.sc("status")["setup"], "in_progress")

    def test_init_twice_refuses_unless_forced(self):
        self.init()
        self.assertIn("already exists", self.sc("init", "--kind", "brownfield", expect=1)["error"])
        self.sc("init", "--kind", "brownfield", "--force")

    def test_init_keeps_existing_config(self):
        self.write(".sdlc/config.json", json.dumps({"min_plugin_version": "1.0.0", "custom": True}))
        self.init()
        self.assertTrue(self.config()["custom"])

    def test_steps_are_resumable(self):
        self.init()
        self.sc("step-done", "detect")
        self.sc("step-done", "detect")
        self.sc("step-done", "justfile")
        out = self.sc("status")
        self.assertEqual(out["completed_steps"], ["detect", "justfile"])
        self.assertEqual(out["setup"], "in_progress")
        self.sc("step-done", "commit", "--complete")
        self.assertEqual(self.sc("status")["setup"], "complete")

    def test_commands_need_a_lock(self):
        self.assertIn("init", self.sc("migrations", expect=1)["error"])

    def test_corrupt_lock_is_an_error_not_a_crash(self):
        self.write(".sdlc/scaffold.lock.json", "{nope")
        self.assertIn("not valid JSON", self.sc("status", expect=1)["error"])

    # --- drift ---------------------------------------------------------------------------

    def test_drift(self):
        self.init()
        self.assertEqual(self.sc("status")["drift"], "current")
        self.set_plugin_version("1.4.0")
        self.assertEqual(self.sc("status")["drift"], "behind")
        self.set_plugin_version("1.2.9")
        self.assertEqual(self.sc("status")["drift"], "plugin_too_old")  # below min_plugin_version 1.3.0
        self.sc("set-version", "1.5.0")
        self.set_plugin_version("1.4.0")
        self.write(".sdlc/config.json", json.dumps({"min_plugin_version": "1.0.0"}))
        self.assertEqual(self.sc("status")["drift"], "ahead")

    def test_versions_compare_numerically(self):
        self.init()
        self.set_plugin_version("1.10.0")
        self.sc("set-version", "1.9.0")
        self.assertEqual(self.sc("status")["drift"], "behind")

    def test_min_plugin_version_never_lowers(self):
        self.init()
        self.assertEqual(self.sc("set-version", "1.4.0", "--min-plugin", "1.4.0")["min_plugin_version"], "1.4.0")
        self.assertEqual(self.sc("set-version", "1.4.1", "--min-plugin", "1.2.0")["min_plugin_version"], "1.4.0")
        self.assertIn("not a version", self.sc("set-version", "latest", expect=1)["error"])

    # --- render / record / file states ---------------------------------------------------

    def test_render_generated_fills_placeholders_and_records(self):
        self.init()
        out = self.sc("render", "templates/project/rules.md", ".claude/rules/sdlc.md")
        self.assertTrue(out["changed"])
        self.assertEqual(self.read(".claude/rules/sdlc.md"), "v1.3.0 test: just verify, just test\n")
        entry = self.lock()["files"][".claude/rules/sdlc.md"]
        self.assertEqual((entry["class"], entry["template"]), ("generated", "templates/project/rules.md"))
        self.assertFalse(self.sc("render", "templates/project/rules.md", ".claude/rules/sdlc.md")["changed"])

    def test_render_missing_placeholder_writes_nothing(self):
        self.init()
        self.template("templates/project/bad.md", "{{config.nope.deep}} {{plugin_version}}")
        self.assertIn("config.nope.deep", self.sc("render", "templates/project/bad.md", "x.md", expect=1)["error"])
        self.assertFalse(os.path.exists(self.path("x.md")))

    def test_render_if_unchanged_refuses_edited_or_foreign_files(self):
        self.init()
        self.sc("render", "templates/project/ci.yml", ".github/workflows/sdlc-verify.yml", "--class", "seeded")
        self.write(".github/workflows/sdlc-verify.yml", "run: just verify && just e2e\n")
        args = ("render", "templates/project/ci.yml", ".github/workflows/sdlc-verify.yml",
                "--class", "seeded", "--if-unchanged")
        self.assertIn("edited", self.sc(*args, expect=2)["refused"])
        self.assertIn("e2e", self.read(".github/workflows/sdlc-verify.yml"))
        self.write("theirs.yml", "mine\n")
        self.sc("render", "templates/project/ci.yml", "theirs.yml", "--if-unchanged", expect=2)
        self.assertEqual(self.read("theirs.yml"), "mine\n")

    def test_render_if_unchanged_overwrites_untouched_file(self):
        self.init()
        self.sc("render", "templates/project/ci.yml", "ci.yml", "--class", "seeded")
        self.template("templates/project/ci.yml", "run: just verify --ci\n")
        self.assertTrue(self.sc("render", "templates/project/ci.yml", "ci.yml", "--class", "seeded",
                                "--if-unchanged")["changed"])
        self.assertEqual(self.read("ci.yml"), "run: just verify --ci\n")

    def test_record_and_file_states(self):
        self.init()
        for name in ("a.md", "b.md", "c.md"):
            self.write(name, name)
        self.sc("record", "seeded", "a.md", "b.md", "c.md")
        self.write("b.md", "edited")
        os.remove(self.path("c.md"))
        files = self.sc("status")["files"]
        self.assertEqual({k: v["state"] for k, v in files.items()},
                         {"a.md": "unchanged", "b.md": "modified", "c.md": "missing"})

    def test_record_rejects_missing_and_outside_paths(self):
        self.init()
        self.assertIn("does not exist", self.sc("record", "seeded", "nope.md", expect=1)["error"])
        self.assertIn("outside", self.sc("record", "seeded", "../escape.md", expect=1)["error"])
        self.assertIn("outside", self.sc("render", "templates/project/ci.yml", "../x.yml", expect=1)["error"])

    def test_forget_makes_a_file_user_owned(self):
        self.init()
        self.write("a.md", "a")
        self.sc("record", "seeded", "a.md")
        self.assertEqual(self.sc("forget", "a.md", "never.md")["forgotten"], ["a.md"])
        self.assertEqual(self.lock()["files"], {})

    # --- keyed merges ----------------------------------------------------------------------

    def test_allow_merges_and_only_removes_its_own_entries(self):
        self.init()
        self.write(".claude/settings.json", json.dumps(
            {"model": "opus", "permissions": {"allow": ["Bash(just test:*)"], "deny": ["Bash(curl:*)"]}}))
        out = self.sc("allow", "--add", "Bash(just test:*)", "Bash(just lint:*)")
        self.assertEqual(out["added"], ["Bash(just lint:*)"])  # the user already had just test
        self.sc("allow", "--remove", "Bash(just test:*)", "Bash(just lint:*)")
        settings = json.loads(self.read(".claude/settings.json"))
        self.assertEqual(settings["permissions"]["allow"], ["Bash(just test:*)"])
        self.assertEqual(settings["permissions"]["deny"], ["Bash(curl:*)"])
        self.assertEqual(settings["model"], "opus")

    def test_allow_creates_settings_file(self):
        self.init()
        self.sc("allow", "--add", "Bash(just verify:*)")
        self.assertEqual(json.loads(self.read(".claude/settings.json"))["permissions"]["allow"],
                         ["Bash(just verify:*)"])

    def test_gitignore_merges_and_only_removes_its_own_lines(self):
        self.init()
        self.write(".gitignore", "node_modules/\n.sdlc/.work/\n")
        self.assertEqual(self.sc("gitignore", "--add", ".sdlc/.work/", ".env")["added"], [".env"])
        self.sc("gitignore", "--remove", ".sdlc/.work/", ".env", "node_modules/")
        self.assertEqual(self.read(".gitignore"), "node_modules/\n.sdlc/.work/\n")

    # --- migrations --------------------------------------------------------------------------

    def test_pending_migrations_window_and_order(self):
        self.migration("1.2.0-old")                   # at or below scaffold_version: not pending
        self.migration("1.3.0-same")
        self.migration("1.10.0-later")
        self.migration("1.4.0-b-second")
        self.migration("1.4.0-a-first")
        self.migration("1.9.0-x", version="2.0.0")    # frontmatter version wins over the filename
        self.plugin_file("migrations/README.md", "not a migration")
        self.init()
        self.set_plugin_version("1.10.0")
        ids = [m["id"] for m in self.sc("migrations")["pending"]]
        self.assertEqual(ids, ["1.4.0-a-first", "1.4.0-b-second", "1.10.0-later"])

    def test_applied_and_skipped_migrations_are_not_pending(self):
        self.migration("1.4.0-a")
        self.migration("1.4.0-b")
        self.init()
        self.set_plugin_version("1.4.0")
        self.sc("migration", "1.4.0-a", "--applied")
        self.sc("migration", "1.4.0-b", "--skipped", "keeping flat layout")
        self.assertEqual(self.sc("migrations")["pending"], [])
        skipped = self.sc("migrations", "--revisit")["skipped"]
        self.assertEqual([(m["id"], m["reason"]) for m in skipped], [("1.4.0-b", "keeping flat layout")])
        self.sc("migration", "1.4.0-b", "--applied")  # revisited and applied after all
        self.assertEqual(self.lock()["migrations"]["skipped"], {})
        self.assertIn("already applied", self.sc("migration", "1.4.0-a", "--skipped", "x", expect=1)["error"])

    def test_unknown_migration_is_an_error(self):
        self.init()
        self.assertIn("unknown", self.sc("migration", "9.9.9-nope", "--applied", expect=1)["error"])

    def test_status_lists_pending_migrations(self):
        self.migration("1.4.0-a")
        self.init()
        self.set_plugin_version("1.4.0")
        self.assertEqual(self.sc("status")["pending_migrations"], ["1.4.0-a"])

    # --- upgrade plan ------------------------------------------------------------------------

    def test_upgrade_plan_classifies_every_file(self):
        self.init()
        self.sc("render", "templates/project/rules.md", "rules.md")
        for name in ("same", "changed", "edited", "deleted", "orphan"):
            self.template(f"templates/project/{name}.yml", f"{name} v1\n")
            self.sc("render", f"templates/project/{name}.yml", f"{name}.yml", "--class", "seeded")
        self.write("hand.md", "x")
        self.sc("record", "seeded", "hand.md")  # recorded without a template: upgrade leaves it alone
        self.template("templates/project/changed.yml", "changed v2\n")
        self.write("edited.yml", "edited by user\n")
        os.remove(self.path("deleted.yml"))
        os.remove(os.path.join(self.plugin, "templates/project/orphan.yml"))
        self.set_plugin_version("1.4.0")
        plan = self.sc("upgrade-plan")
        paths = {k: [i["path"] for i in plan[k]] if k != "template_gone" else plan[k]
                 for k in ("regenerate", "replace", "review", "restore", "template_gone")}
        self.assertEqual(paths, {"regenerate": ["rules.md"], "replace": ["changed.yml"], "review": ["edited.yml"],
                                 "restore": ["deleted.yml"], "template_gone": ["orphan.yml"]})
        self.assertEqual((plan["from"], plan["to"]), ("1.3.0", "1.4.0"))

    # --- eject -------------------------------------------------------------------------------

    def setup_for_eject(self):
        self.init()
        self.sc("render", "templates/project/rules.md", ".claude/rules/sdlc.md")
        self.sc("render", "templates/project/ci.yml", ".github/workflows/sdlc-verify.yml", "--class", "seeded")
        self.write(".claude/hookify/sdlc-rm.md", "rule")
        self.sc("record", "seeded", ".claude/hookify/sdlc-rm.md")
        self.write(".claude/hookify/sdlc-rm.md", "rule, tuned by user")
        self.write(".claude/settings.json", json.dumps({"permissions": {"allow": ["Bash(git status)"]}}))
        self.sc("allow", "--add", "Bash(just test:*)")
        self.sc("gitignore", "--add", ".sdlc/.work/")
        self.write(".sdlc/constitution.md", "mine")

    def test_eject_plan_is_dry_by_default(self):
        self.setup_for_eject()
        plan = self.sc("eject")
        self.assertEqual(plan["delete"], [".claude/rules/sdlc.md", ".github/workflows/sdlc-verify.yml"])
        self.assertEqual(plan["ask"], [".claude/hookify/sdlc-rm.md"])
        self.assertTrue(os.path.exists(self.path(".sdlc/scaffold.lock.json")))

    def test_eject_apply_keeps_user_work(self):
        self.setup_for_eject()
        out = self.sc("eject", "--apply")
        self.assertEqual(out["kept_edited"], [".claude/hookify/sdlc-rm.md"])
        for gone in (".claude/rules/sdlc.md", ".github", ".sdlc/scaffold.lock.json"):
            self.assertFalse(os.path.exists(self.path(gone)), gone)  # .github emptied, so removed
        for kept in (".claude/hookify/sdlc-rm.md", ".sdlc/constitution.md", ".sdlc/config.json"):
            self.assertTrue(os.path.exists(self.path(kept)), kept)
        self.assertEqual(json.loads(self.read(".claude/settings.json"))["permissions"]["allow"], ["Bash(git status)"])
        self.assertNotIn(".sdlc/.work/", self.read(".gitignore"))

    def test_eject_also_deletes_edited_files_on_request_only(self):
        self.setup_for_eject()
        self.assertIn("ask", self.sc("eject", "--apply", "--also", ".sdlc/constitution.md", expect=1)["error"])
        self.assertTrue(os.path.exists(self.path(".sdlc/scaffold.lock.json")))  # nothing applied
        self.sc("eject", "--apply", "--also", ".claude/hookify/sdlc-rm.md")
        self.assertFalse(os.path.exists(self.path(".claude/hookify")))

    # --- config defaults + filters ------------------------------------------------------------

    def test_config_merges_defaults_with_project_overrides(self):
        self.init()
        self.write(".sdlc/config.json", json.dumps(
            {"min_plugin_version": "1.3.0", "verify": {"full": ["pnpm test:all"]}, "extra": 1}))
        out = self.sc("config")
        self.assertEqual(out["config"]["verify"]["full"], ["pnpm test:all"])  # lists replace, not append
        self.assertEqual(out["config"]["areas"]["tests"], ["**/*.test.*"])    # default kept
        self.assertEqual(out["overrides"]["extra"], 1)

    def test_init_writes_overrides_only(self):
        self.init()
        self.assertEqual(set(self.config()), {"min_plugin_version", "project"})

    def test_yaml_list_and_json_filters(self):
        self.init()
        self.template("templates/project/f.md", "paths:\n{{config.areas.tests|yaml_list}}\nv={{ config.verify | json }}\n")
        self.assertEqual(self.sc("preview", "templates/project/f.md")["text"],
                         'paths:\n  - "**/*.test.*"\nv={"full": ["just verify", "just test"]}\n')

    def test_unknown_filter_is_an_error(self):
        self.init()
        self.template("templates/project/f.md", "{{config.verify|upper}}")
        self.assertIn("unknown template filter", self.sc("preview", "templates/project/f.md", expect=1)["error"])

    # --- the real plugin's templates ----------------------------------------------------------

    def test_real_rules_template_renders_with_default_config(self):
        self.sc("init", "--kind", "brownfield", plugin=PLUGIN_ROOT)
        self.sc("render", "templates/project/rules/sdlc.md", ".claude/rules/sdlc.md", plugin=PLUGIN_ROOT)
        text = self.read(".claude/rules/sdlc.md")
        self.assertNotIn("{{", text)
        self.assertIn("just verify, just test", text)


if __name__ == "__main__":
    unittest.main()
