"""scripts/scaffold.py: lock, file classes, keyed merges, migrations, upgrade and eject plans."""
import json
import os
import shutil
import subprocess
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
        self.template("templates/project/rules.md", "v{{plugin_version}} order: {{config.verify.order}}\n")
        self.template("templates/project/ci.yml", "run: make verify\n")
        self.template("templates/project/config.defaults.json",
                      json.dumps({"verify": {"order": ["lint", "test"]}, "areas": {"tests": ["**/*.test.*"]}}))

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

    def test_status_lists_the_repos_own_hookify_rules(self):
        # A cloned repo's rules reach the model; they're listed so the user can look before trusting them
        self.write(".claude/hookify/sdlc-dangerous-rm.md", "---\nname: sdlc-dangerous-rm\nevent: bash\naction: block\n---\nx\n")
        self.write(".claude/hookify/team-no-eval.md", "---\nname: team-no-eval\nenabled: true\nevent: file\naction: block\n---\nUse JSON.parse.\n")
        self.assertEqual(self.sc("status")["team_rules"],
                         [{"file": ".claude/hookify/team-no-eval.md", "event": "file", "action": "block", "enabled": True,
                           "message": "Use JSON.parse."}])

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
        self.sc("step-done", "commands")
        out = self.sc("status")
        self.assertEqual(out["completed_steps"], ["detect", "commands"])
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
        self.assertEqual(self.read(".claude/rules/sdlc.md"), "v1.3.0 order: lint, test\n")
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
        self.write(".github/workflows/sdlc-verify.yml", "run: make verify && make e2e\n")
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
        self.template("templates/project/ci.yml", "run: make verify --ci\n")
        self.assertTrue(self.sc("render", "templates/project/ci.yml", "ci.yml", "--class", "seeded",
                                "--if-unchanged")["changed"])
        self.assertEqual(self.read("ci.yml"), "run: make verify --ci\n")

    def test_crlf_checkout_of_an_untouched_file_counts_as_unchanged(self):
        # git with core.autocrlf=true checks out CRLF; the lock holds the hash of the LF render
        self.init()
        self.sc("render", "templates/project/ci.yml", "ci.yml", "--class", "seeded")
        with open(self.path("ci.yml"), "wb") as f:
            f.write(b"run: make verify\r\n")
        self.assertEqual(self.sc("status")["files"]["ci.yml"]["state"], "unchanged")
        self.template("templates/project/ci.yml", "run: make verify --ci\n")
        self.sc("render", "templates/project/ci.yml", "ci.yml", "--class", "seeded", "--if-unchanged")

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
        self.assertEqual(self.lock()["declined"], ["a.md", "never.md"])

    def test_upgrade_adds_rules_and_guardrails_new_in_this_version(self):
        self.template("templates/project/rules/sdlc.md", "always\n")
        self.template("templates/project/rules/tests.md", "tests\n")
        self.template("templates/project/hookify/sdlc-old.md", "old\n")
        self.template("templates/project/hookify/README.md", "not a rule\n")
        self.init()
        self.sc("render", "templates/project/rules/sdlc.md", ".claude/rules/sdlc.md")
        self.sc("render", "templates/project/hookify/sdlc-old.md", ".claude/hookify/sdlc-old.md", "--class", "seeded")
        self.template("templates/project/hookify/sdlc-new.md", "new\n")
        self.template("templates/project/hookify/sdlc-declined.md", "declined\n")
        self.template("templates/project/hookify/sdlc-clash.md", "clash\n")
        self.write(".claude/hookify/sdlc-clash.md", "the team's own file with that name\n")
        self.sc("forget", ".claude/hookify/sdlc-declined.md")
        add = {i["path"]: i for i in self.sc("upgrade-plan")["add"]}
        self.assertEqual(sorted(add), [".claude/hookify/sdlc-clash.md", ".claude/hookify/sdlc-new.md",
                                       ".claude/rules/sdlc-tests.md"])
        self.assertEqual((add[".claude/rules/sdlc-tests.md"]["class"], add[".claude/hookify/sdlc-new.md"]["class"]),
                         ("generated", "seeded"))
        self.assertTrue(add[".claude/hookify/sdlc-clash.md"]["exists"])
        self.assertNotIn("exists", add[".claude/hookify/sdlc-new.md"])

    # --- keyed merges ----------------------------------------------------------------------

    def test_allow_merges_and_only_removes_its_own_entries(self):
        self.init()
        self.write(".claude/settings.json", json.dumps(
            {"model": "opus", "permissions": {"allow": ["Bash(make test:*)"], "deny": ["Bash(curl:*)"]}}))
        out = self.sc("allow", "--add", "Bash(make test:*)", "Bash(make lint:*)")
        self.assertEqual(out["added"], ["Bash(make lint:*)"])  # the user already had make test
        self.sc("allow", "--remove", "Bash(make test:*)", "Bash(make lint:*)")
        settings = json.loads(self.read(".claude/settings.json"))
        self.assertEqual(settings["permissions"]["allow"], ["Bash(make test:*)"])
        self.assertEqual(settings["permissions"]["deny"], ["Bash(curl:*)"])
        self.assertEqual(settings["model"], "opus")

    def test_allow_creates_settings_file(self):
        self.init()
        self.sc("allow", "--add", "Bash(make verify:*)")
        self.assertEqual(json.loads(self.read(".claude/settings.json"))["permissions"]["allow"],
                         ["Bash(make verify:*)"])

    def test_enable_plugin_merges_and_only_removes_its_own_keys(self):
        self.init()
        self.write(".claude/settings.json", json.dumps(
            {"model": "opus", "enabledPlugins": {"other@mkt": True}, "extraKnownMarketplaces": {"sdlc": {"source": "mine"}}}))
        out = self.sc("enable-plugin")
        self.assertEqual(out["added"], ["enabledPlugins.sdlc@sdlc"])  # the user already had a marketplace named sdlc
        settings = json.loads(self.read(".claude/settings.json"))
        self.assertEqual(settings["enabledPlugins"], {"other@mkt": True, "sdlc@sdlc": True})
        self.assertEqual(self.sc("enable-plugin")["added"], [])  # idempotent
        self.sc("enable-plugin", "--remove")
        settings = json.loads(self.read(".claude/settings.json"))
        self.assertEqual(settings["enabledPlugins"], {"other@mkt": True})
        self.assertEqual(settings["extraKnownMarketplaces"], {"sdlc": {"source": "mine"}})
        self.assertEqual(settings["model"], "opus")

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

    def test_non_ascii_output_survives_a_non_utf8_pipe(self):
        self.migration("1.4.0-move", summary="rules → .claude/rules")
        self.init()
        self.set_plugin_version("1.4.0")
        code, out, raw, err = run_hook([sys.executable, SCRIPT, "--root", self.root, "migrations"], "", self.root,
                                       env_extra={"CLAUDE_PLUGIN_ROOT": self.plugin, "PYTHONIOENCODING": "cp1252"})
        self.assertEqual(code, 0, err)
        self.assertEqual(out["pending"][0]["summary"], "rules → .claude/rules")

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
        self.sc("allow", "--add", "Bash(make test:*)")
        self.sc("enable-plugin")
        self.sc("gitignore", "--add", ".sdlc/.work/")
        self.write(".sdlc/constitution.md", "mine")

    def test_eject_plan_is_dry_by_default(self):
        self.setup_for_eject()
        plan = self.sc("eject")
        self.assertEqual(plan["delete"], [".claude/rules/sdlc.md", ".github/workflows/sdlc-verify.yml"])
        self.assertEqual(plan["ask"], [".claude/hookify/sdlc-rm.md"])
        self.assertTrue(os.path.exists(self.path(".sdlc/scaffold.lock.json")))

    def test_eject_removes_the_scratch_folder(self):
        self.setup_for_eject()
        self.write(".sdlc/.work/verify-freshness.json", "{}")
        self.assertTrue(self.sc("eject", "--apply")["scratch_removed"])
        self.assertFalse(os.path.exists(self.path(".sdlc/.work")))
        self.assertTrue(os.path.exists(self.path(".sdlc/config.json")))

    def test_eject_apply_keeps_user_work(self):
        self.setup_for_eject()
        out = self.sc("eject", "--apply")
        self.assertEqual(out["kept_edited"], [".claude/hookify/sdlc-rm.md"])
        for gone in (".claude/rules/sdlc.md", ".github", ".sdlc/scaffold.lock.json"):
            self.assertFalse(os.path.exists(self.path(gone)), gone)  # .github emptied, so removed
        for kept in (".claude/hookify/sdlc-rm.md", ".sdlc/constitution.md", ".sdlc/config.json"):
            self.assertTrue(os.path.exists(self.path(kept)), kept)
        settings = json.loads(self.read(".claude/settings.json"))
        self.assertEqual(settings["permissions"]["allow"], ["Bash(git status)"])
        self.assertNotIn("enabledPlugins", settings)
        self.assertNotIn("extraKnownMarketplaces", settings)
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
            {"min_plugin_version": "1.3.0", "verify": {"order": ["test"]}, "extra": 1}))
        out = self.sc("config")
        self.assertEqual(out["config"]["verify"]["order"], ["test"])  # lists replace, not append
        self.assertEqual(out["config"]["areas"]["tests"], ["**/*.test.*"])    # default kept
        self.assertEqual(out["overrides"]["extra"], 1)

    def test_init_writes_overrides_only(self):
        self.init()
        self.assertEqual(set(self.config()), {"min_plugin_version", "project", "docs_dir"})

    def test_yaml_list_and_json_filters(self):
        self.init()
        self.template("templates/project/f.md", "paths:\n{{config.areas.tests|yaml_list}}\nv={{ config.verify | json }}\n")
        self.assertEqual(self.sc("preview", "templates/project/f.md")["text"],
                         'paths:\n  - "**/*.test.*"\nv={"order": ["lint", "test"]}\n')

    def test_foreign_placeholders_pass_through(self):
        self.init()
        self.template("templates/project/f.yml", "g: ${{ github.ref }}\nj: {{ other.tool }}\nv: {{plugin_version}}\n")
        self.assertEqual(self.sc("preview", "templates/project/f.yml")["text"],
                         "g: ${{ github.ref }}\nj: {{ other.tool }}\nv: 1.3.0\n")

    # --- commands contract, verify plan, allowlist, generated CI ---------------------------

    REQUIRED = {"contract": {"required": ["install", "test", "lint"]}, "verify": {"order": ["lint", "test"]}}

    def commands_config(self, **config):
        self.init()
        self.template("templates/project/config.defaults.json", json.dumps(self.REQUIRED))
        self.write(".sdlc/config.json", json.dumps({"min_plugin_version": "1.3.0", **config}))

    def test_contract_single_project(self):
        self.commands_config(commands={"install": "git --version", "test": "./run-tests.sh", "lint": None})
        out = self.sc("contract")
        root = out["scopes"]["(root)"]
        self.assertEqual((out["ok"], out["monorepo"], root["not_applicable"]), (True, False, ["lint"]))
        self.assertEqual(root["not_found"], {"test": "./run-tests.sh"})  # repo-relative path that doesn't exist
        self.assertFalse(out["tools_ok"])
        self.write("run-tests.sh", "")
        self.assertTrue(self.sc("contract")["tools_ok"])

    def test_contract_reports_missing_commands(self):
        self.commands_config(commands={"test": "git --version"})
        root = self.sc("contract")["scopes"]["(root)"]
        self.assertEqual(root["missing"], ["install", "lint"])
        self.assertFalse(root["ok"])

    def test_contract_skips_env_assignments_when_finding_the_tool(self):
        self.commands_config(commands={"install": "CI=1 FOO=bar git status", "test": "nosuchtool-xyz run",
                                       "lint": "git diff"})
        self.assertEqual(self.sc("contract")["scopes"]["(root)"]["not_found"], {"test": "nosuchtool-xyz"})

    def test_contract_monorepo_packages(self):
        cmds = {"install": "git --version", "test": "git --version", "lint": "git --version"}
        self.commands_config(packages=[{"name": "api", "path": "services/api", "stack": "go", "commands": cmds},
                                       {"name": "api", "path": "apps/web", "commands": {"test": "git log"}},
                                       {"path": "nowhere", "commands": cmds}])
        os.makedirs(self.path("services/api"))
        os.makedirs(self.path("apps/web"))
        out = self.sc("contract")
        self.assertTrue(out["monorepo"])
        self.assertFalse(out["ok"])
        self.assertTrue(out["scopes"]["api"]["ok"] is False)  # the duplicate name overwrote the first entry
        self.assertIn("duplicate package name 'api'", out["scopes"]["api"]["problems"])
        self.assertIn("package without a name", out["scopes"]["?"]["problems"])
        self.assertIn("path 'nowhere' does not exist", out["scopes"]["?"]["problems"])

    def test_run_commands_records_each_exit_and_flags_ones_that_cannot_run(self):
        self.commands_config(commands={"install": "git --version", "test": "git no-such-subcommand",
                                       "lint": "nosuchtool-xyz run"})
        out = self.sc("run-commands", expect=1)
        runs = out["scopes"]["(root)"]
        self.assertEqual(runs["install"]["exit"], 0)
        self.assertNotEqual(runs["test"]["exit"], 0)  # ran but failed: recorded, may be a baselined failure
        self.assertFalse(runs["lint"]["ran"])  # could not start: setup can't complete
        self.assertEqual(out["not_runnable"], ["(root) lint"])
        self.assertEqual(self.sc("contract")["runs"]["(root)"]["test"]["command"], "git no-such-subcommand")
        self.assertNotIn("tail", self.lock()["command_runs"]["(root)"]["test"])  # output stays out of the committed lock

    def test_commands_verify_plan(self):
        self.commands_config(packages=[
            {"name": "api", "path": "services/api/", "commands": {"install": "go mod download", "lint": "golangci-lint run",
                                                                 "test": "go test ./..."}},
            {"name": "sh", "path": "scripts", "commands": {"install": None, "lint": "shellcheck *.sh", "test": None}}])
        out = self.sc("commands")
        self.assertEqual([(x["scope"], x["cwd"], x["run"]) for x in out["install"]],
                         [("api", "services/api", "go mod download")])
        self.assertEqual([(x["scope"], x["step"]) for x in out["verify"]],
                         [("api", "lint"), ("api", "test"), ("sh", "lint")])

    def test_allow_from_commands(self):
        self.commands_config(commands={"install": "pnpm install", "test": "pnpm test", "lint": None})
        out = self.sc("allow", "--from-commands")
        self.assertEqual(out["added"], ["Bash(pnpm install:*)", "Bash(pnpm test:*)"])
        self.assertEqual(self.sc("allow", "--from-commands")["added"], [])  # idempotent

    def test_builtin_ci_single_project(self):
        self.commands_config(project={"stack": ["typescript"]},
                             commands={"install": "pnpm install --frozen-lockfile", "test": "pnpm test", "lint": "pnpm lint"},
                             ci={"os": ["ubuntu-latest", "windows-latest"]})
        out = self.sc("render", "builtin:ci", ".github/workflows/sdlc-verify.yml", "--class", "seeded")
        self.assertTrue(out["changed"])
        text = self.read(".github/workflows/sdlc-verify.yml")
        self.assertIn('os: ["ubuntu-latest", "windows-latest"]', text)
        self.assertIn("runs-on: ${{ matrix.os }}", text)
        self.assertIn("actions/setup-node@v7", text)
        self.assertIn("shell: bash", text)
        steps = [l.strip() for l in text.splitlines() if l.strip().startswith(("- name:", "pnpm"))]
        self.assertEqual(steps, ['- name: "install"', "pnpm install --frozen-lockfile", '- name: "lint"', "pnpm lint",
                                 '- name: "test"', "pnpm test"])
        self.assertNotIn("working-directory", text)
        self.assertEqual(self.lock()["files"][".github/workflows/sdlc-verify.yml"]["template"], "builtin:ci")

    def test_builtin_ci_polyglot(self):
        self.commands_config(packages=[
            {"name": "api", "path": "services/api", "stack": "go", "commands": {"test": "go test ./..."}},
            {"name": "core", "path": "libs/core", "stack": "rust", "commands": {"lint": "cargo clippy", "test": "cargo test"}},
            {"name": "app", "path": "apps/mobile", "stack": "elixir", "commands": {"test": "mix test"}}])
        self.write("services/api/go.mod", "module x\n")
        text = self.sc("preview", "builtin:ci")["text"]
        for want in ("actions/setup-go@v7", "go-version-file: services/api/go.mod", "dtolnay/rust-toolchain@stable",
                     "# TODO: add the toolchain setup for 'elixir'", '- name: "core · lint"',
                     "working-directory: libs/core"):
            self.assertIn(want, text)

    def test_builtin_ci_per_package(self):
        self.commands_config(packages=[
            {"name": "web", "path": "apps/web", "stack": "typescript", "commands": {"install": "pnpm i", "test": "pnpm test"}},
            {"name": "api", "path": "apps/api", "stack": "go", "commands": {"test": "go test ./..."}}])
        self.write("apps/api/go.mod", "module x\n")
        self.sc("render", "builtin:ci:web", ".github/workflows/sdlc-verify-web.yml", "--class", "seeded")
        text = self.read(".github/workflows/sdlc-verify-web.yml")
        for want in ('name: "sdlc verify web"', '"apps/web/**"', '"packages/**"', '- "*"\n',
                     '".github/workflows/sdlc-verify-web.yml"', "actions/setup-node@v7",
                     "working-directory: apps/web", "group: sdlc-verify-web-${{ github.ref }}"):
            self.assertIn(want, text)
        self.assertNotIn("go test", text)
        self.assertNotIn("setup-go", text)
        self.assertEqual(self.lock()["files"][".github/workflows/sdlc-verify-web.yml"]["template"], "builtin:ci:web")

    def test_builtin_ci_unknown_package_is_an_error(self):
        self.commands_config(packages=[{"name": "web", "path": "apps/web", "commands": {"test": "pnpm test"}}])
        self.assertIn("no package named 'mobile'", self.sc("preview", "builtin:ci:mobile", expect=1)["error"])

    def test_builtin_contract_check(self):
        self.commands_config(commands={"test": "make test"},
                             api_contract={"path": "packages/api-contract", "spec": "openapi.yaml"},
                             ci={"oasdiff_version": "1.11.7"})
        text = self.sc("preview", "builtin:contract-check")["text"]
        self.assertNotIn("paths:", text)  # always runs, so it can be a required check
        for want in ("fetch-depth: 0", "github.com/oasdiff/oasdiff@v1.11.7",
                     'bash .sdlc/ci/contract-check.sh "origin/${{ github.base_ref }}" packages/api-contract openapi.yaml'):
            self.assertIn(want, text)

    def test_builtin_codeowners(self):
        self.commands_config(commands={"test": "make test"}, project={"profile": "large", "owners": {
            "/apps/web/": ["@acme/web"], "/packages/api-contract/": ["@acme/backend", "@acme/leads"]}})
        lines = [l for l in self.sc("preview", "builtin:codeowners")["text"].splitlines() if not l.startswith("#")]
        self.assertEqual(lines, ["/apps/web/ @acme/web", "/packages/api-contract/ @acme/backend @acme/leads"])
        self.write(".sdlc/config.json", json.dumps({"min_plugin_version": "1.3.0", "commands": {"test": "make test"}}))
        self.assertIn("no project.owners", self.sc("preview", "builtin:codeowners", expect=1)["error"])

    def test_init_records_docs_dir_and_paths_resolve(self):
        self.sc("init", "--kind", "greenfield", "--docs-dir", "handbook/sdlc/")
        self.assertEqual(self.config()["docs_dir"], "handbook/sdlc")
        self.assertEqual(self.sc("paths", "2026-10-23-x")["intents"], "handbook/sdlc/intents/2026-10-23-x/")
        os.remove(self.path(".sdlc/config.json"))
        self.assertIn("not inside the repo", self.sc("init", "--kind", "greenfield", "--force", "--docs-dir", "../x",
                                                     expect=1)["error"])

    def test_status_names_a_docs_site(self):
        self.write("mkdocs.yml", "site_name: x\n")
        self.assertEqual(self.sc("status")["docs_site"], "mkdocs.yml")

    def test_templates_name_the_repos_layout_paths(self):
        self.init()
        self.template("templates/project/l.md", "{{layout.constitution}}")
        self.write(".sdlc/config.json", "{}")  # legacy: no docs_dir
        self.assertEqual(self.sc("preview", "templates/project/l.md")["text"], ".sdlc/constitution.md")
        self.write(".sdlc/config.json", json.dumps({"docs_dir": "docs/sdlc"}))
        self.assertEqual(self.sc("preview", "templates/project/l.md")["text"], "docs/sdlc/constitution.md")

    # --- relocate: old layout → state in .sdlc/state, documents in docs_dir --------------------------

    def git(self, *args):
        subprocess.run(["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t", *args], check=True,
                       capture_output=True)

    def legacy_repo(self, files):
        self.git("init", "-q", "-b", "main")
        for path in files:
            self.write(path, "x\n")
        self.init()
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "legacy")

    def test_relocate_moves_old_layout_and_is_idempotent(self):
        self.legacy_repo([".sdlc/f1/state.md", ".sdlc/f1/spec.md", ".sdlc/f1/checklists/r.md",
                          ".sdlc/constitution.md", ".sdlc/baseline.md", ".sdlc/lint/x.mjs"])
        self.assertNotIn("docs_dir", self.config())
        dry = self.sc("relocate")
        self.assertFalse(dry["applied"])
        self.assertIn([".sdlc/f1/state.md", ".sdlc/state/f1.md"], dry["moves"])
        self.assertFalse(os.path.exists(self.path(".sdlc/state/f1.md")))
        self.sc("relocate", "--apply")
        for path in (".sdlc/state/f1.md", "docs/sdlc/intents/f1/spec.md", "docs/sdlc/intents/f1/checklists/r.md",
                     "docs/sdlc/constitution.md", ".sdlc/baseline.md", ".sdlc/lint/x.mjs"):
            self.assertTrue(os.path.exists(self.path(path)), path)
        self.assertFalse(os.path.exists(self.path(".sdlc/f1")))
        self.assertEqual(self.config()["docs_dir"], "docs/sdlc")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "moved")
        self.assertEqual(self.sc("relocate", "--apply")["moves"], [])

    def test_relocate_stops_on_a_name_in_both_layouts(self):
        self.legacy_repo([".sdlc/f1/state.md", ".sdlc/state/f1.md", ".sdlc/f2/state.md"])
        out = self.sc("relocate", "--apply")
        self.assertEqual(out["conflicts"], ["f1"])
        self.assertFalse(out["applied"])
        for path in (".sdlc/f1/state.md", ".sdlc/f2/state.md"):  # nothing moves: never half-moved
            self.assertTrue(os.path.exists(self.path(path)), path)
        self.assertNotIn("docs_dir", self.config())

    def test_relocate_moves_only_tracked_files(self):
        self.legacy_repo([".gitignore", ".sdlc/f1/state.md", ".sdlc/f1/spec.md"])
        self.write(".gitignore", ".DS_Store\n")
        self.write(".sdlc/f1/.DS_Store", "x")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "ignore")
        self.sc("relocate", "--apply")
        self.assertTrue(os.path.exists(self.path("docs/sdlc/intents/f1/spec.md")))
        self.assertTrue(os.path.exists(self.path(".sdlc/state/f1.md")))
        self.assertEqual(self.config()["docs_dir"], "docs/sdlc")

    def test_init_force_keeps_a_recorded_docs_dir(self):
        self.sc("init", "--kind", "greenfield", "--docs-dir", "my/docs")
        self.sc("init", "--kind", "greenfield", "--force")
        self.assertEqual(self.config()["docs_dir"], "my/docs")

    def test_relocate_refuses_a_dirty_tree(self):
        self.legacy_repo([".sdlc/f1/state.md"])
        self.write(".sdlc/f1/spec.md", "draft\n")
        self.assertIn("uncommitted", self.sc("relocate", "--apply", expect=1)["error"])

    def test_builtin_ci_needs_commands(self):
        self.commands_config()
        self.assertIn("no commands", self.sc("preview", "builtin:ci", expect=1)["error"])

    def test_builtin_ci_is_upgradable(self):
        self.commands_config(commands={"install": "make deps", "test": "make test", "lint": "make lint"})
        self.sc("render", "builtin:ci", "ci.yml", "--class", "seeded")
        self.set_plugin_version("1.4.0")
        self.write(".sdlc/config.json", json.dumps({"min_plugin_version": "1.3.0",
                                                    "commands": {"install": "make deps", "test": "make check", "lint": "make lint"}}))
        self.assertEqual([i["path"] for i in self.sc("upgrade-plan")["replace"]], ["ci.yml"])

    def test_unknown_filter_is_an_error(self):
        self.init()
        self.template("templates/project/f.md", "{{config.verify|upper}}")
        self.assertIn("unknown template filter", self.sc("preview", "templates/project/f.md", expect=1)["error"])

    # --- AGENTS.md for Cursor and Codex (real workflow template) -----------------------------

    def agents_project(self, targets):
        self.sc("init", "--kind", "brownfield", plugin=PLUGIN_ROOT)
        self.write(".sdlc/config.json", json.dumps({"tools": {"targets": targets}}))
        self.write("CLAUDE.md", "# Repo\n\n@docs/extra.md\nRun `/sdlc:doctor` weekly.\n\n```python\n@pytest.fixture\n```\n")
        self.write(".claude/rules/api.md", '---\npaths:\n  - "src/api/**"\n---\n# API\n\nVersion every route.\n')

    def agents(self, *args, expect=0):
        return self.sc("agents", *args, expect=expect, plugin=PLUGIN_ROOT)

    def test_agents_writes_one_block_and_keeps_the_users_text(self):
        self.agents_project(["cursor", "codex"])
        with open(self.path("AGENTS.md"), "wb") as f:
            f.write(b"# Ours\r\n\r\nUse pnpm.\r\n")
        self.agents()
        with open(self.path("AGENTS.md"), "rb") as f:
            first = f.read()
        self.agents()
        with open(self.path("AGENTS.md"), "rb") as f:
            self.assertEqual(f.read(), first)  # deterministic: a rebuild changes nothing
        text = first.decode()
        self.assertTrue(text.startswith("# Ours\r\n\r\nUse pnpm.\r\n\r\n<!-- sdlc:begin"))
        self.assertEqual(text.count("<!-- sdlc:begin"), 1)
        self.assertNotIn("\n", text.replace("\r\n", ""))  # the block follows the file's CRLF
        self.assertIn("Never edit these files", text)
        self.assertIn("Also read `docs/extra.md`.", text)
        self.assertIn("`/sdlc:doctor` (Claude Code)", text)
        self.assertIn("\r\n@pytest.fixture\r\n", text)  # code samples aren't imports
        self.assertIn("### API\r\n\r\nApplies when working on files matching `src/api/**`.", text)
        self.assertEqual(self.lock()["merged"]["AGENTS.md#sdlc"], ["block"])

    def test_agents_stops_at_a_claude_only_line(self):
        self.agents_project(["codex"])
        self.write("CLAUDE.md", "# Repo\n\nRun ${CLAUDE_PLUGIN_ROOT}/x.\n")
        self.assertIn("CLAUDE.md:3:", self.agents(expect=1)["error"])
        self.assertFalse(os.path.exists(self.path("AGENTS.md")))

    def test_agents_check_and_upgrade_plan_report_drift(self):
        self.agents_project(["codex"])
        self.agents()
        self.assertEqual(self.agents("--check")["state"], "in_sync")
        self.write(".claude/rules/api.md", "# API\n\nVersion every route, always.\n")
        self.assertIn("out of date", self.agents("--check", expect=1)["error"])
        self.assertEqual(self.sc("upgrade-plan", plugin=PLUGIN_ROOT)["agents"], "stale")

    def test_agents_off_for_claude_only_and_unknown_target_is_an_error(self):
        self.agents_project(["claude-code"])
        self.assertEqual(self.agents()["result"], "off")
        self.assertFalse(os.path.exists(self.path("AGENTS.md")))
        self.write(".sdlc/config.json", json.dumps({"tools": {"targets": ["gemini"]}}))
        self.assertIn("unknown gemini", self.agents(expect=1)["error"])

    def test_eject_removes_the_block_and_a_file_it_created(self):
        self.agents_project(["codex"])
        self.agents()
        self.sc("eject", "--apply", plugin=PLUGIN_ROOT)
        self.assertFalse(os.path.exists(self.path("AGENTS.md")))

    # --- the real plugin's templates ----------------------------------------------------------

    def test_real_rules_template_renders_with_default_config(self):
        self.sc("init", "--kind", "brownfield", plugin=PLUGIN_ROOT)
        self.sc("render", "templates/project/rules/sdlc.md", ".claude/rules/sdlc.md", plugin=PLUGIN_ROOT)
        text = self.read(".claude/rules/sdlc.md")
        self.assertNotIn("{{", text)
        self.assertIn(".sdlc/config.json", text)


if __name__ == "__main__":
    unittest.main()
