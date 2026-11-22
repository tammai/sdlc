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

    def sc(self, *args, expect=0, plugin=None, env=None):
        code, out, raw, err = run_hook([sys.executable, SCRIPT, "--root", self.root, *args], "", self.root,
                                       env_extra={"CLAUDE_PLUGIN_ROOT": plugin or self.plugin,
                                                  "CLAUDE_CONFIG_DIR": self.path("claude-config"), **(env or {})})
        self.assertEqual(code, expect, f"{args}: {raw}{err}")
        self.assertIsNotNone(out, raw + err)
        return out

    def installed(self):
        """Claude Code's install record says the running plugin is the installed sdlc."""
        self.write("claude-config/plugins/installed_plugins.json", json.dumps(
            {"version": 2, "plugins": {"sdlc@sdlc": [{"scope": "user", "installPath": self.plugin}]}}))

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

    def test_upgrade_to_2_waits_for_1x_features_to_finish(self):
        self.init()
        self.sc("set-version", "1.8.1")
        self.set_plugin_version("2.0.0")
        self.write(".sdlc/state/old-active.md", "Status: active\nCurrent: Stage 5 – Prove\n")
        self.write(".sdlc/state/old-done.md", "Status: done\nCurrent: Stage 8 – Ship\n")
        self.assertEqual(self.sc("upgrade-plan")["old_features"], ["old-active"])
        self.assertIn("old-active", self.sc("set-version", "2.0.0", expect=2)["refused"])
        self.write(".sdlc/state/old-active.md", "Status: done\nCurrent: Stage 8 – Ship\n")
        self.assertEqual(self.sc("set-version", "2.0.0")["scaffold_version"], "2.0.0")

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

    def test_enable_plugin_writes_local_settings_and_only_removes_its_own_keys(self):
        self.template("templates/project/config.defaults.json", json.dumps({"companions": [
            {"id": "sdlc-extras@sdlc", "marketplace": "sdlc", "why": "extras", "default": False}]}))
        self.init()
        # Loaded from a directory (--plugin-dir) rather than installed: enabling the installed copy would load two
        out = self.sc("enable-plugin")
        self.assertNotIn("enabledPlugins.sdlc@sdlc", out["added"])
        self.assertIn("--plugin-dir", out["skipped"])
        self.installed()
        local = ".claude/settings.local.json"
        self.write(local, json.dumps({"enabledPlugins": {"other@mkt": False}, "extraKnownMarketplaces": {"sdlc": {"source": "mine"}}}))
        # sdlc itself, plus a companion picked by id; the team's committed settings.json is never touched
        out = self.sc("enable-plugin", "--with", "sdlc-extras@sdlc")
        self.assertEqual(out["added"], ["enabledPlugins.sdlc@sdlc", "enabledPlugins.sdlc-extras@sdlc"])
        self.assertIn("sdlc-extras@sdlc", [c["id"] for c in out["companions"]])  # what setup can mention
        settings = json.loads(self.read(local))
        self.assertEqual(settings["enabledPlugins"], {"other@mkt": False, "sdlc@sdlc": True, "sdlc-extras@sdlc": True})
        self.assertFalse(os.path.exists(self.path(".claude/settings.json")))
        self.assertEqual(self.sc("enable-plugin", "--with", "sdlc-extras@sdlc")["added"], [])  # idempotent
        self.sc("enable-plugin", "--remove")
        settings = json.loads(self.read(local))
        self.assertEqual(settings["enabledPlugins"], {"other@mkt": False})
        self.assertEqual(settings["extraKnownMarketplaces"], {"sdlc": {"source": "mine"}})  # the user's own
        # Only a listed companion can be enabled: no arbitrary plugin rides in on a typo
        self.assertIn("unknown@mkt", self.sc("enable-plugin", "--with", "unknown@mkt", expect=1)["error"])
        # The committed repo config can't add one: enable-plugin doesn't ask, so that would run a stranger's plugin
        self.write(".sdlc/config.json", json.dumps({"companions": [
            {"id": "evil@evil", "marketplace": "evil", "source": {"source": "github", "repo": "x/y"}, "default": True}]}))
        self.sc("enable-plugin")
        self.assertNotIn("evil@evil", json.loads(self.read(local))["enabledPlugins"])

    def test_enable_plugin_turns_on_the_shipped_companion_plugins(self):
        with open(os.path.join(PLUGIN_ROOT, "templates/project/config.defaults.json"), encoding="utf-8") as f:
            self.template("templates/project/config.defaults.json", f.read())
        self.init()
        self.installed()
        self.sc("enable-plugin")
        self.assertEqual(json.loads(self.read(".claude/settings.local.json"))["enabledPlugins"],
                         {"sdlc@sdlc": True, "sdlc-extras@sdlc": True, "sdlc-stepper@sdlc": True})

    def test_enable_plugin_team_commits_the_on_keys_and_keeps_turn_offs_local(self):
        self.template("templates/project/config.defaults.json", json.dumps({
            "companions": [{"id": "sdlc-extras@sdlc", "marketplace": "sdlc", "why": "extras", "default": True}],
            "conflicts": [{"name": "superpowers", "plugin": "superpowers", "why": "same skills twice"}]}))
        self.init()
        self.installed()
        self.write("claude-config/settings.json", json.dumps({"enabledPlugins": {"superpowers@mkt": True}}))
        self.write(".claude/settings.json", json.dumps({"permissions": {"allow": ["Bash(make:*)"]}}))
        # A teammate's clone gets only the committed file, so --team puts the on keys there
        out = self.sc("enable-plugin", "--team")
        self.assertEqual(out["commit"], ".claude/settings.json")
        team = json.loads(self.read(".claude/settings.json"))
        self.assertEqual(team["enabledPlugins"], {"sdlc@sdlc": True, "sdlc-extras@sdlc": True})
        self.assertIn("sdlc", team["extraKnownMarketplaces"])
        self.assertEqual(team["permissions"], {"allow": ["Bash(make:*)"]})
        # Turning a teammate's plugin off isn't the team's file's job: that stays this machine's
        self.assertEqual(json.loads(self.read(".claude/settings.local.json"))["enabledPlugins"], {"superpowers@mkt": False})
        self.assertTrue(all(c["on"] for c in out["companions"]))
        # Run again without --team (upgrade's keyed merge): the committed keys aren't shadowed locally
        self.assertEqual(self.sc("enable-plugin")["added"], [])
        # A companion added later joins the team's file too, so teammates get it as well
        self.template("templates/project/config.defaults.json", json.dumps({"companions": [
            {"id": "sdlc-extras@sdlc", "marketplace": "sdlc", "why": "extras"},
            {"id": "other@sdlc", "marketplace": "sdlc", "why": "other"}]}))
        self.assertEqual(self.sc("enable-plugin", "--with", "other@sdlc")["added"], ["enabledPlugins.other@sdlc"])
        self.assertTrue(json.loads(self.read(".claude/settings.json"))["enabledPlugins"]["other@sdlc"])
        self.assertEqual(sorted(self.sc("enable-plugin", "--remove-team")["removed"]), sorted([
            "extraKnownMarketplaces.sdlc", "enabledPlugins.sdlc@sdlc", "enabledPlugins.sdlc-extras@sdlc",
            "enabledPlugins.other@sdlc"]))
        self.assertEqual(json.loads(self.read(".claude/settings.json")), {"permissions": {"allow": ["Bash(make:*)"]}})

    def test_enable_plugin_lists_a_skill_companion_without_installing_it(self):
        self.template("templates/project/config.defaults.json", json.dumps({"companions": [
            {"skill": "security-audit", "install": "npx skills add x --skill security-audit", "why": "audits"}]}))
        self.init()
        self.installed()
        home = {"HOME": self.path("home"), "USERPROFILE": self.path("home")}  # skills also install to ~/.agents
        out = self.sc("enable-plugin", env=home)
        self.assertEqual(out["skills"], [{"skill": "security-audit", "why": "audits",
                                          "install": "npx skills add x --skill security-audit", "installed": False}])
        self.assertNotIn("security-audit", json.dumps(json.loads(self.read(".claude/settings.local.json"))))
        self.write(".claude/skills/security-audit/SKILL.md", "---\nname: security-audit\n---\n")  # a project install
        self.assertTrue(self.sc("enable-plugin", env=home)["skills"][0]["installed"])

    def test_enable_plugin_turns_a_conflicting_plugin_off_here_and_reports_spec_kit(self):
        self.template("templates/project/config.defaults.json", json.dumps({"conflicts": [
            {"name": "superpowers", "plugin": "superpowers", "why": "same skills twice"},
            {"name": "spec-kit", "files": [".specify/", ".claude/commands/speckit.*"], "why": "two spec flows"}]}))
        self.init()
        self.installed()
        self.write("claude-config/settings.json", json.dumps({"enabledPlugins": {"superpowers@mkt": True}}))
        self.write(".specify/memory/constitution.md", "x")
        out = self.sc("enable-plugin")
        # Off for this repo only, in this machine's file, with a warning naming what and why
        self.assertEqual(json.loads(self.read(".claude/settings.local.json"))["enabledPlugins"]["superpowers@mkt"], False)
        self.assertEqual([(c["id"], c["why"]) for c in out["turned_off"]], [("superpowers@mkt", "same skills twice")])
        self.assertEqual([(c["name"], c["found"]) for c in out["conflicts_in_repo"]], [("spec-kit", [".specify/"])])
        self.sc("enable-plugin", "--remove")  # taking it back restores the user's own setting
        self.assertNotIn("superpowers@mkt", json.loads(self.read(".claude/settings.local.json")).get("enabledPlugins", {}))

    def test_removing_plugin_keys_keeps_a_value_the_user_changed_since(self):
        # A key sdlc wrote and the user then flipped is the user's: --remove and eject must not delete it
        self.template("templates/project/config.defaults.json", json.dumps({"conflicts": [
            {"name": "superpowers", "plugin": "superpowers", "why": "same skills twice"}]}))
        self.init()
        self.installed()
        self.write("claude-config/settings.json", json.dumps({"enabledPlugins": {"superpowers@mkt": True}}))
        local = ".claude/settings.local.json"
        self.sc("enable-plugin")
        settings = json.loads(self.read(local))
        settings["enabledPlugins"].update({"sdlc@sdlc": False, "superpowers@mkt": True})
        self.write(local, json.dumps(settings))
        out = self.sc("enable-plugin", "--remove")
        self.assertEqual(out["removed"], ["extraKnownMarketplaces.sdlc"])
        self.assertEqual(sorted(out["kept"]), ["enabledPlugins.sdlc@sdlc", "enabledPlugins.superpowers@mkt"])
        self.assertEqual(json.loads(self.read(local))["enabledPlugins"], {"sdlc@sdlc": False, "superpowers@mkt": True})
        self.assertEqual(out["owned"], [])  # theirs now: a later --remove leaves them too
        # Eject takes the same path
        self.write(local, json.dumps({}))
        self.sc("enable-plugin")
        self.write(local, json.dumps({"enabledPlugins": {"sdlc@sdlc": False, "superpowers@mkt": False}}))
        out = self.sc("eject", "--apply")
        self.assertEqual(json.loads(self.read(local)), {"enabledPlugins": {"sdlc@sdlc": False}})
        self.assertEqual(out["kept"], {local: ["enabledPlugins.sdlc@sdlc"]})

    def test_gitignore_merges_and_only_removes_its_own_lines(self):
        self.init()
        self.write(".gitignore", "node_modules/\n.sdlc/.work/\n")
        self.assertEqual(self.sc("gitignore", "--add", ".sdlc/.work/", ".env")["added"], [".env"])
        self.sc("gitignore", "--remove", ".sdlc/.work/", ".env", "node_modules/")
        self.assertEqual(self.read(".gitignore"), "node_modules/\n.sdlc/.work/\n")

    def test_gitignore_untracks_what_was_committed_before_the_ignore(self):
        self.init()
        git = ["git", "-C", self.root, "-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run(git + ["init", "-q"], check=True)
        self.write(".sdlc/.work/trust-anchor.json", "{}")  # committed by mistake, before the ignore line
        subprocess.run(git + ["add", "-f", ".sdlc/.work/trust-anchor.json"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "oops"], check=True)
        out = self.sc("gitignore", "--add", ".sdlc/.work/")
        self.assertEqual(out["untracked"], [".sdlc/.work/trust-anchor.json"])
        tracked = subprocess.run(git + ["ls-files", ".sdlc/.work"], capture_output=True, encoding="utf-8").stdout
        self.assertEqual(tracked.strip(), "")
        self.assertTrue(os.path.exists(self.path(".sdlc/.work/trust-anchor.json")))  # kept on disk
        # A * in a line stays within one folder, as in .gitignore: a team rule under .claude/rules/ stays tracked
        self.write(".claude/rules/team.local.md", "rule")
        subprocess.run(git + ["add", "-f", ".claude/rules/team.local.md"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "rule"], check=True)
        self.assertEqual(self.sc("gitignore", "--add", ".claude/*.local.md")["untracked"], [])

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

    def merged(self):
        """A seeded file the user edited, then merged with the template as upgrade's "apply merge" records it."""
        self.init()
        self.template("templates/project/guard.md", "guard v1\n")
        self.sc("render", "templates/project/guard.md", "guard.md", "--class", "seeded")
        self.write("guard.md", "guard v1\nmine\n")
        self.sc("record", "seeded", "guard.md", "--template", "templates/project/guard.md")

    def test_a_merged_file_is_reviewed_not_replaced(self):
        self.merged()
        plan = self.sc("upgrade-plan")
        self.assertEqual([plan[k] for k in ("replace", "review")], [[], []])  # nothing new to merge
        self.template("templates/project/guard.md", "guard v2\n")
        plan = self.sc("upgrade-plan")
        self.assertEqual(([i["path"] for i in plan["replace"]], [i["path"] for i in plan["review"]]), ([], ["guard.md"]))
        self.assertIn("edited", self.sc("render", "templates/project/guard.md", "guard.md", "--class", "seeded",
                                        "--if-unchanged", expect=2)["refused"])
        self.assertEqual(self.read("guard.md"), "guard v1\nmine\n")

    def test_eject_asks_about_a_merged_file(self):
        self.merged()
        plan = self.sc("eject")
        self.assertIn("guard.md", plan["ask"])
        self.assertNotIn("guard.md", plan["delete"])

    def test_a_malformed_render_hash_is_refused(self):
        self.merged()
        lock = json.loads(self.read(".sdlc/scaffold.lock.json"))
        lock["files"]["guard.md"]["render_sha256"] = 7
        self.write(".sdlc/scaffold.lock.json", json.dumps(lock))
        out = self.sc("upgrade-plan", expect=1)  # a damaged lock: the script's own exit, with a message
        self.assertIn("'guard.md'", out["error"])

    def tamper(self, path, template, cls="generated"):
        lock = json.loads(self.read(".sdlc/scaffold.lock.json"))
        lock["files"][path] = {"class": cls, "sha256": None, "template": template}
        self.write(".sdlc/scaffold.lock.json", json.dumps(lock))

    def test_a_lock_template_outside_the_plugins_templates_is_refused(self):
        secret = os.path.join(os.path.realpath(tempfile.mkdtemp(prefix="sdlc-secret-")), "id_rsa")
        self.addCleanup(shutil.rmtree, os.path.dirname(secret), ignore_errors=True)
        with open(secret, "w", encoding="utf-8") as f:
            f.write("PRIVATE KEY\n")
        bads = [secret, os.path.relpath(secret, self.plugin), "templates/../" + os.path.relpath(secret, self.plugin),
                "builtin:evil", "builtin:ci:../x", "README.md", "templates\\project\\ci.yml", "C:/x", "C:x",
                "templates//project/ci.yml", "templates/./project/ci.yml", ""]
        try:  # a link out of templates/; Windows without the symlink privilege can't make one
            os.symlink(secret, os.path.join(self.plugin, "templates", "project", "link.md"))
            bads.append("templates/project/link.md")
        except (OSError, NotImplementedError):
            pass
        self.init()
        self.write("mine.md", "x")
        for bad in bads:
            self.tamper("leak.md", bad)
            out = self.sc("upgrade-plan", expect=1)
            self.assertIn("'leak.md'", out["error"], bad)
            self.assertFalse(os.path.exists(self.path("leak.md")), bad)
            self.tamper("leak.md", "templates/project/ci.yml")  # a fair entry: the lock reads again
            self.sc("upgrade-plan")
            # the CLI takes a Windows separator as the user's own: there it names a fair template
            if bad and not (os.sep == "\\" and bad == "templates\\project\\ci.yml"):
                self.assertIn("template", self.sc("render", bad, "leak2.md", expect=2)["refused"], bad)
                self.assertFalse(os.path.exists(self.path("leak2.md")), bad)
                self.assertIn("template", self.sc("preview", bad, expect=2)["refused"], bad)
                self.assertIn("template", self.sc("record", "seeded", "mine.md", "--template", bad, expect=2)["refused"], bad)
        self.assertNotIn("PRIVATE", json.dumps(self.sc("upgrade-plan")))
        # what the skills render still works; an entry recorded with no template stays fine
        out = self.sc("render", "builtin:ci:api", ".github/workflows/sdlc-verify-api.yml", expect=1)
        self.assertIn("no package named 'api'", out["error"])  # past the template check, to the package lookup
        self.sc("record", "seeded", "mine.md")
        self.sc("record", "seeded", "mine.md", "--template", "templates/project/ci.yml\r")  # a shell loop's \r
        self.assertEqual(json.loads(self.read(".sdlc/scaffold.lock.json"))["files"]["mine.md"]["template"],
                         "templates/project/ci.yml")
        self.assertEqual(self.sc("preview", "templates/project/ci.yml\r")["template"], "templates/project/ci.yml")
        for blank in (" ", "\r"):  # nothing left after the strip: refused, never read as no template
            self.assertIn("template", self.sc("record", "seeded", "mine.md", "--template", blank, expect=2)["refused"])

    def test_nothing_is_recorded_or_rendered_under_git(self):
        self.init()
        os.makedirs(self.path(".git/hooks"), exist_ok=True)
        os.makedirs(self.path("sub/.git/hooks"), exist_ok=True)
        dests = [".git/hooks/post-commit", ".GIT/config", "./.git/x", ".git./x", ".git /x", "GIT~1/x",
                 ".git::$INDEX_ALLOCATION/x", "sub/.git/hooks/pre-commit",
                 ".g\u200cit/hooks/x", "\ufeff.git/x", ".gi\u206at/x"]  # HFS+ ignores these code points (git's is_hfs_dotgit)
        try:  # a committed link into .git; Windows without the symlink privilege can't make one
            os.symlink(".git", self.path("x"), target_is_directory=True)
            dests.append("x/hooks/post-commit")
        except (OSError, NotImplementedError):
            pass
        self.write("mine.md", "x")
        for dest in dests:
            self.assertIn(".git", self.sc("render", "templates/project/ci.yml", dest, expect=2)["refused"], dest)
        self.assertEqual(os.listdir(self.path(".git/hooks")), [])
        self.assertEqual(os.listdir(self.path("sub/.git/hooks")), [])
        for ok in (".gitignore", ".github/workflows/sdlc-x.yml", ".gitattributes"):  # names that only start with .git
            self.sc("render", "templates/project/ci.yml", ok, "--class", "seeded")
        if os.path.islink(self.path("x")):
            self.write(".git/config", "[core]\n")
            self.assertIn(".git", self.sc("record", "seeded", "x/config", expect=2)["refused"])
            self.tamper("x/config", "templates/project/ci.yml")  # passes the shape check: caught where it's written
            plan = self.sc("upgrade-plan")
            self.assertIn("x/config", plan["outside"])
            self.assertNotIn("x/config", [i["path"] for i in plan["regenerate"]])
            os.remove(self.path("x"))
            os.symlink(".git", self.path(".claude"), target_is_directory=True)  # a shipped file's folder into .git
            self.template("templates/project/rules/sdlc.md", "rules\n")
            self.assertIn(".claude/rules/sdlc.md", self.sc("upgrade-plan")["outside"])
            os.remove(self.path(".claude"))
            os.symlink(".git", self.path("x"), target_is_directory=True)
            eject = self.sc("eject")
            self.assertIn("x/config", eject["outside"])
            self.assertNotIn("x/config", eject["delete"])
        self.tamper(".git/hooks/post-commit", "templates/project/ci.yml")
        self.assertIn(".git", self.sc("upgrade-plan", expect=1)["error"])

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
        self.installed()
        self.sc("enable-plugin")
        self.sc("gitignore", "--add", ".sdlc/.work/")
        self.write(".sdlc/constitution.md", "mine")

    def linked_out(self, rel, to):
        """`rel` replaced by a link to `to`; False where links can't be made (Windows without the privilege)."""
        if os.path.isdir(self.path(rel)) and not os.path.islink(self.path(rel)):
            shutil.rmtree(self.path(rel))
        elif os.path.lexists(self.path(rel)):
            os.remove(self.path(rel))
        os.makedirs(os.path.dirname(self.path(rel)) or self.root, exist_ok=True)
        try:
            os.symlink(to, self.path(rel))
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable here (Windows without the privilege)")
        return True

    def test_fixed_name_writers_refuse_a_link_out_of_the_repo_or_into_git(self):
        # .sdlc/2026-11-22-s-fixed-writers-refuse-links AC-001
        self.init()
        outside = tempfile.mkdtemp(prefix="sdlc-outside-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        secret = os.path.join(outside, "secret.txt")
        os.makedirs(self.path(".git"), exist_ok=True)
        self.write(".git/config", "[core]\n")
        calls = [(".gitignore", ("gitignore", "--add", "x/")), (".claude/settings.json", ("allow", "--add", "Bash(x)")),
                 (".claude/settings.local.json", ("enable-plugin",))]
        for rel, args in calls:
            for to in (secret, os.path.abspath(self.path(".git/config"))):
                with open(secret, "w", encoding="utf-8") as f:
                    f.write("token=1\n")
                self.linked_out(rel, to)
                self.installed()
                out = self.sc(*args, expect=2)
                self.assertIn(rel, out["refused"], (rel, to))
                self.assertEqual(self.read(".git/config"), "[core]\n", (rel, to))
                with open(secret, encoding="utf-8") as f:
                    self.assertEqual(f.read(), "token=1\n", (rel, to))
            os.remove(self.path(rel))
        # a folder of the path linked into .git: refused too
        os.makedirs(self.path(".git/info"), exist_ok=True)
        self.linked_out(".claude", os.path.abspath(self.path(".git/info")))
        self.assertIn(".claude/settings.json", self.sc("allow", "--add", "Bash(x)", expect=2)["refused"])
        self.assertFalse(os.path.exists(self.path(".git/info/settings.json")))
        os.remove(self.path(".claude"))
        # a link that stays inside the repo, outside .git, is still written through
        self.write("ignore.txt", "a/\n")
        self.linked_out(".gitignore", "ignore.txt")
        self.sc("gitignore", "--add", "b/")
        self.assertEqual(self.read("ignore.txt"), "a/\nb/\n")
        # the workbench's own .gitignore edits go through the same check (review r1 M-1)
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        import scaffold
        self.linked_out(".gitignore", secret)
        with self.assertRaises(scaffold.Refused):
            scaffold._ignore(scaffold.Project(self.root), "app")
        with self.assertRaises(scaffold.Refused):
            scaffold._gitignore_lines(scaffold.Project(self.root))
        with open(secret, encoding="utf-8") as f:
            self.assertEqual(f.read(), "token=1\n")

    def test_agents_md_link_out_of_the_repo_is_refused(self):
        # AC-001: AGENTS.md through a committed link is neither read nor written
        self.hosted_project("claude-code", "codex")
        os.makedirs(self.path(".git"), exist_ok=True)
        self.write(".git/config", "[core]\n")
        self.write("CLAUDE.md", "# Repo\n")
        outside = tempfile.mkdtemp(prefix="sdlc-outside-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        with open(os.path.join(outside, "AGENTS.md"), "w", encoding="utf-8") as f:
            f.write("token=1\n")
        for to in (os.path.abspath(self.path(".git/config")), os.path.join(outside, "AGENTS.md")):
            self.linked_out("AGENTS.md", to)
            self.assertIn("AGENTS.md", self.real("agents", expect=2)["refused"])
            self.assertEqual(self.read(".git/config"), "[core]\n")
            # read as absent: the mirror never carries the target's text
            self.assertNotIn("token=1", self.read_all(".claude/rules"))
            sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
            import scaffold
            self.assertIsNone(scaffold.agents_md_text(scaffold.Project(self.root)))
        with open(os.path.join(outside, "AGENTS.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "token=1\n")

    def test_agents_with_nothing_to_write_leaves_a_linked_agents_md_alone(self):
        # review r2 M1: Claude Code alone has no block to write, so a linked AGENTS.md is never opened or refused
        self.hosted_project("claude-code")
        os.makedirs(self.path(".git"), exist_ok=True)
        self.write(".git/config", "[core]\n")
        self.linked_out("AGENTS.md", os.path.abspath(self.path(".git/config")))
        self.assertEqual(self.real("agents")["result"], "off")
        self.assertEqual(self.read(".git/config"), "[core]\n")

    def test_eject_leaves_a_linked_fixed_file_untouched_and_lists_it(self):
        # AC-002: eject finishes, lists the linked file under outside, and never writes through it
        self.setup_for_eject()
        outside = tempfile.mkdtemp(prefix="sdlc-outside-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        target = os.path.join(outside, "gitignore")
        with open(target, "w", encoding="utf-8") as f:
            f.write(".sdlc/.work/\nmine/\n")
        self.linked_out(".gitignore", target)
        self.assertIn(".gitignore", self.sc("eject")["outside"])
        out = self.sc("eject", "--apply")
        self.assertIn(".gitignore", out["outside"])
        self.assertTrue(out["lock_removed"])
        with open(target, encoding="utf-8") as f:
            self.assertEqual(f.read(), ".sdlc/.work/\nmine/\n")

    def test_eject_lists_only_linked_files_with_something_recorded(self):
        # AC-001 (review R2-L2 of 2026-11-22-s-fixed-writers-refuse-links): nothing to unmerge, nothing to name
        self.setup_for_eject()  # claude-code only: no AGENTS.md block recorded
        outside = tempfile.mkdtemp(prefix="sdlc-outside-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        target = os.path.join(outside, "agents")
        with open(target, "w", encoding="utf-8") as f:
            f.write("theirs\n")
        self.linked_out("AGENTS.md", target)
        self.assertNotIn("AGENTS.md", self.sc("eject")["outside"])
        self.assertNotIn("AGENTS.md", self.sc("eject", "--apply")["outside"])
        with open(target, encoding="utf-8") as f:
            self.assertEqual(f.read(), "theirs\n")

    def read_all(self, rel):
        """Every file's text under the folder `rel`, joined (empty when it's missing)."""
        out = []
        for d, _, names in os.walk(self.path(rel)):
            for n in names:
                with open(os.path.join(d, n), encoding="utf-8", errors="replace") as f:
                    out.append(f.read())
        return "\n".join(out)

    def test_eject_finishes_with_claude_linked_into_git_or_outside(self):
        # AC-002 (review r1 H-1): a linked folder hides absent settings files; eject must still finish
        outside = tempfile.mkdtemp(prefix="sdlc-outside-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        for to in ("git", outside):
            self.setUp() if to == outside else None
            self.setup_for_eject()
            os.makedirs(self.path(".git/info"), exist_ok=True)
            target = os.path.abspath(self.path(".git/info")) if to == "git" else outside
            before = sorted(os.listdir(target))
            self.linked_out(".claude", target)
            plan = self.sc("eject")
            self.assertIn(".claude/settings.json", plan["outside"], to)
            self.assertIn(".claude/settings.local.json", plan["outside"], to)
            out = self.sc("eject", "--apply")
            self.assertTrue(out["lock_removed"], to)
            self.assertEqual(sorted(os.listdir(target)), before, to)

    def test_settings_read_through_a_link_read_as_absent(self):
        # AC-003 (review r1 H-2): the settings readers never open a linked file; enable-plugin refuses first
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        import scaffold
        self.init()
        outside = tempfile.mkdtemp(prefix="sdlc-outside-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        evil = os.path.join(outside, "settings.json")
        with open(evil, "w", encoding="utf-8") as f:
            json.dump({"enabledPlugins": {"x@y": True},
                       "hooks": {"PostToolUse": [{"hooks": [{"command": "impeccable/hook.mjs"}]}]}}, f)
        for rel in (".claude/settings.json", ".claude/settings.local.json"):
            self.linked_out(rel, evil)
            self.assertFalse(scaffold.plugin_enabled(self.root, "x@y"), rel)
            self.assertFalse(scaffold.impeccable_hook_wired(self.root), rel)
            self.assertEqual(scaffold.read_fixed_json(self.root, rel, {}), {}, rel)
            self.assertNotIn("x@y", scaffold.enabled_elsewhere(scaffold.Project(self.root)), rel)
            self.installed()
            self.assertIn(rel, self.sc("enable-plugin", expect=2)["refused"], rel)
            os.remove(self.path(rel))
        # --remove with keys to take back refuses a linked file; with none it has nothing to open
        self.installed()
        self.sc("enable-plugin")
        with open(self.path(".claude/settings.local.json"), encoding="utf-8") as f:
            local = f.read()
        with open(evil, "w", encoding="utf-8") as f:
            f.write(local)
        self.linked_out(".claude/settings.local.json", evil)
        self.assertIn(".claude/settings.local.json", self.sc("enable-plugin", "--remove", expect=2)["refused"])
        with open(evil, encoding="utf-8") as f:
            self.assertEqual(f.read(), local)
        self.assertEqual(self.sc("enable-plugin", "--remove-team")["removed"], [])

    def test_agents_block_skips_sources_linked_out_of_the_repo(self):
        # AC-004 (review r1 M-2): CLAUDE.md or a rule linked outside never reaches AGENTS.md
        self.hosted_project("claude-code", "codex")
        outside = tempfile.mkdtemp(prefix="sdlc-outside-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        secret = os.path.join(outside, "creds")
        with open(secret, "w", encoding="utf-8") as f:
            f.write("aws_secret=1\n")
        self.linked_out("CLAUDE.md", secret)
        self.linked_out(".claude/rules/leak.md", secret)
        self.real("agents")
        self.assertNotIn("aws_secret", self.read("AGENTS.md"))

    def test_agents_block_skips_unreadable_sources(self):
        # AC-003 (review r2 H1): a folder or a broken link at CLAUDE.md or a rule is left out, not a traceback
        self.hosted_project("claude-code", "codex")
        os.makedirs(self.path(".claude/rules/dir.md"))
        self.write(".claude/rules/plain.md", "# Plain rule\nkeep me\n")
        if os.path.exists(self.path("CLAUDE.md")):
            os.remove(self.path("CLAUDE.md"))
        os.makedirs(self.path("CLAUDE.md"))
        self.real("agents")
        self.assertIn("keep me", self.read("AGENTS.md"))

    def test_config_and_lock_linked_out_of_the_repo_are_refused(self):
        # AC-001 (review M2 of 2026-11-22-s-doctor-reads-no-links): never read from, or written to, outside
        outside = tempfile.mkdtemp(prefix="sdlc-outside-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        cfg = os.path.join(outside, "config.json")
        with open(cfg, "w", encoding="utf-8") as f:
            f.write('{"secret": 1}')
        self.linked_out(".sdlc/config.json", cfg)
        self.assertIn(".sdlc/config.json", self.sc("status", expect=1)["error"])
        os.remove(self.path(".sdlc/config.json"))
        os.makedirs(self.path(".git"), exist_ok=True)
        self.write(".git/config", "[core]\n")
        self.linked_out(".sdlc/scaffold.lock.json", os.path.join("..", ".git", "config"))
        self.assertIn(".sdlc/scaffold.lock.json", self.sc("status", expect=1)["error"])
        os.remove(self.path(".sdlc/scaffold.lock.json"))
        self.linked_out(".sdlc", outside)  # the whole folder: init writes nothing there
        self.sc("init", "--kind", "greenfield", expect=1)
        self.assertEqual(sorted(os.listdir(outside)), ["config.json"])
        with open(cfg, encoding="utf-8") as f:
            self.assertEqual(f.read(), '{"secret": 1}')

    def test_a_folder_at_a_recorded_path_counts_as_edited(self):
        # AC-002 (review r2 of 2026-11-22-s-doctor-reads-no-links): sha256 on a folder was a traceback
        self.init()
        self.sc("render", "templates/project/ci.yml", ".github/workflows/x.yml", "--class", "seeded")
        os.remove(self.path(".github/workflows/x.yml"))
        os.makedirs(self.path(".github/workflows/x.yml"))
        self.sc("status")
        plan = self.sc("upgrade-plan")
        self.assertNotIn(".github/workflows/x.yml", [i["path"] for i in plan.get("regenerate", [])])
        self.assertTrue(os.path.isdir(self.path(".github/workflows/x.yml")))
        # end-of-push review r1 H2: never "unchanged", even against a recorded "" hash; listed, never deleted
        lock = json.loads(self.read(".sdlc/scaffold.lock.json"))
        lock["files"][".github/workflows/x.yml"]["sha256"] = ""
        self.write(".sdlc/scaffold.lock.json", json.dumps(lock))
        self.assertIn(".github/workflows/x.yml", self.sc("upgrade-plan")["outside"])
        # round 2 R2-M2: render (with --if-unchanged too) refuses a folder at a recorded path, exit 2, folder kept
        self.assertIn("readable", self.sc("render", "templates/project/ci.yml", ".github/workflows/x.yml",
                                          "--if-unchanged", expect=2)["refused"])
        self.assertTrue(os.path.isdir(self.path(".github/workflows/x.yml")))
        eject = self.sc("eject")
        self.assertIn(".github/workflows/x.yml", eject["outside"])
        self.assertNotIn(".github/workflows/x.yml", eject["delete"])
        self.sc("eject", "--apply")
        self.assertTrue(os.path.isdir(self.path(".github/workflows/x.yml")))
        self.init()
        os.makedirs(self.path("adir.md"))
        self.assertIn("adir.md", self.sc("record", "seeded", "adir.md", expect=2)["refused"])  # nothing to hash

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

    def test_eject_removes_a_linked_scratch_folder_but_not_its_target(self):
        # a committed link at .sdlc/.work: eject removes the link itself, after the lock is gone, never what it
        # points to, and finishes rather than crashing in rmtree
        self.setup_for_eject()
        outside = os.path.realpath(tempfile.mkdtemp(prefix="sdlc-outside-"))
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        with open(os.path.join(outside, "keep.txt"), "w", encoding="utf-8") as f:
            f.write("mine")
        shutil.rmtree(self.path(".sdlc/.work"), ignore_errors=True)
        try:  # Windows without the symlink privilege can't make one
            os.symlink(outside, self.path(".sdlc/.work"), target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.assertTrue(self.sc("eject", "--apply")["scratch_removed"])
        self.assertFalse(os.path.lexists(self.path(".sdlc/.work")))
        self.assertFalse(os.path.exists(self.path(".sdlc/scaffold.lock.json")))
        self.assertEqual(os.listdir(outside), ["keep.txt"])

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

    def test_eject_keep_lists_only_what_exists(self):
        self.setup_for_eject()  # a config, but no baseline or design system
        keep = self.sc("eject")["keep"]
        self.assertIn(".sdlc/config.json", keep)
        self.assertNotIn(".sdlc/baseline.md", keep)
        self.assertFalse([k for k in keep if "design-system" in k], keep)

    def test_eject_keeps_the_prd_where_setup_recorded_it(self):
        self.setup_for_eject()
        self.write("product/PRD.md", "# Planner\n")  # one the user already had, used as is
        self.assertEqual(self.sc("prd", "product/PRD.md")["prd"], "product/PRD.md")
        self.assertIn("product/PRD.md", self.sc("eject")["keep"])
        self.sc("eject", "--apply")
        self.assertEqual(self.read("product/PRD.md"), "# Planner\n")

    def test_design_mode_records_and_refuses_unknown(self):
        self.init()
        self.assertEqual(self.sc("design")["design"], "builtin")  # no key: today's behaviour
        self.assertEqual(self.sc("design", "impeccable")["design"], "impeccable")
        self.assertEqual(json.loads(self.read(".sdlc/config.json"))["design"], "impeccable")
        self.assertIn("builtin", self.sc("design", "figma", expect=2)["refused"])
        self.assertEqual(self.sc("design")["design"], "impeccable")  # the refused value changed nothing

    def test_review_rounds_records_and_refuses_out_of_range(self):
        self.init()
        self.assertEqual(self.sc("review-rounds")["review_rounds"], 2)  # no key: today's cap
        self.assertEqual(self.sc("review-rounds", "3")["review_rounds"], 3)
        self.assertEqual(json.loads(self.read(".sdlc/config.json"))["review_rounds"], 3)
        for bad in ("1", "6", "x", "2.5"):
            self.assertIn("2 to 5", self.sc("review-rounds", bad, expect=2)["refused"])
        self.assertEqual(self.sc("review-rounds")["review_rounds"], 3)  # the refused values changed nothing

    def test_deploy_records_target_environments_and_runbook(self):
        self.init()
        self.assertIsNone(self.sc("deploy")["deploy"]["target"])  # nothing recorded yet
        out = self.sc("deploy", "--target", "gcp-cloud-run", "--env", "dev:routine", "--env", "prod")
        want = {"target": "gcp-cloud-run", "environments": [{"name": "dev", "routine": True},
                                                            {"name": "prod", "routine": False}],
                "runbook": "knowledge/runbooks/deploy.md"}
        self.assertEqual(out["deploy"], want)
        self.assertEqual(json.loads(self.read(".sdlc/config.json"))["deploy"], want)
        self.assertEqual(self.sc("deploy")["deploy"], want)
        self.assertEqual(self.sc("deploy", "--runbook", "knowledge/runbooks/gcp-deploy.md")["deploy"]["runbook"],
                         "knowledge/runbooks/gcp-deploy.md")
        self.assertIn("gcp-cloud-run", self.sc("deploy", "--target", "heroku", expect=2)["refused"])
        self.sc("deploy", "--target", "vercel", "--env", ":routine", expect=2)
        self.assertEqual(json.loads(self.read(".sdlc/config.json"))["deploy"]["target"], "gcp-cloud-run")

    def test_deploy_never_marks_production_routine(self):
        # a committed config is untrusted: it must never let /sdlc:deploy skip production's go-ahead (review r1 S-001)
        self.init()
        for name in ("prod", "Production", "live", "prd"):
            self.sc("deploy", "--target", "vercel", "--env", f"{name}:routine", expect=2)
        self.assertNotIn("deploy", json.loads(self.read(".sdlc/config.json")))
        config = json.loads(self.read(".sdlc/config.json"))
        config["deploy"] = {"target": "vercel", "environments": [{"name": "dev", "routine": True},
                                                                 {"name": "prod", "routine": True}]}
        self.write(".sdlc/config.json", json.dumps(config))
        out = self.sc("deploy")
        self.assertEqual(out["deploy"]["environments"], [{"name": "dev", "routine": True},
                                                         {"name": "prod", "routine": False}])
        self.assertIn("environments.prod.routine", out["invalid"])

    def test_deploy_checks_the_runbook_flag_and_every_stored_value(self):
        # review r1 M1, S-002/M2: a path outside the repo is refused (exit 2) or reported null, never printed as usable
        self.init()
        for bad in ("../x", "/etc/passwd", "", ".", "knowledge/../../x"):
            self.sc("deploy", "--runbook", bad, expect=2)
        config = json.loads(self.read(".sdlc/config.json"))
        config["deploy"] = {"target": "../../x", "environments": "prod", "runbook": "../../.bashrc"}
        self.write(".sdlc/config.json", json.dumps(config))
        out = self.sc("deploy")
        self.assertEqual(out["deploy"], {"target": None, "environments": [], "runbook": None})
        self.assertEqual(out["invalid"], ["environments", "runbook", "target"])
        out = self.sc("deploy", "--target", "vercel")  # recording drops what was invalid
        self.assertEqual(out["deploy"], {"target": "vercel", "environments": [], "runbook": "knowledge/runbooks/deploy.md"})
        self.assertNotIn("invalid", out)
        outside = tempfile.mkdtemp(prefix="sdlc-outside-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        try:
            os.symlink(outside, self.path("ops"))
        except (OSError, NotImplementedError):
            return  # no symlinks here (Windows without the privilege): the path checks above still ran
        self.sc("deploy", "--runbook", "ops/deploy.md", expect=2)
        # a stored or default runbook through the same symlink is reported invalid too (review r2 L-3)
        config = json.loads(self.read(".sdlc/config.json"))
        config["deploy"] = {"target": "vercel", "runbook": "ops/deploy.md"}
        self.write(".sdlc/config.json", json.dumps(config))
        self.assertIsNone(self.sc("deploy")["deploy"]["runbook"])
        del config["deploy"]["runbook"]
        self.write(".sdlc/config.json", json.dumps(config))
        os.symlink(outside, self.path("knowledge"))
        out = self.sc("deploy")
        self.assertIsNone(out["deploy"]["runbook"])
        self.assertIn("runbook", out["invalid"])

    def test_deploy_production_is_any_name_with_a_production_part(self):
        # review r2 M2/M-2: one check, on the flag and on stored config; names are plain ASCII so none can hide a part
        self.init()
        for name in ("prod-eu", "production_us", "eu.live", "PRD-2", "pro​d", "prod eu", "-x"):
            self.sc("deploy", "--target", "vercel", f"--env={name}:routine", expect=2)  # `=`: argparse reads -x as a flag
        out = self.sc("deploy", "--target", "vercel", "--env", "dev:routine", "--env", "product-preview:routine",
                      "--env", "prod-eu")
        self.assertEqual([(e["name"], e["routine"]) for e in out["deploy"]["environments"]],
                         [("dev", True), ("product-preview", True), ("prod-eu", False)])
        config = json.loads(self.read(".sdlc/config.json"))
        config["deploy"]["environments"] = [{"name": "prod-eu", "routine": True}, {"name": "pro​d", "routine": True}]
        self.write(".sdlc/config.json", json.dumps(config))
        out = self.sc("deploy")
        self.assertEqual(out["deploy"]["environments"], [{"name": "prod-eu", "routine": False}])
        self.assertEqual(out["invalid"], ["environments", "environments.prod-eu.routine"])

    def test_deploy_runbook_is_a_markdown_doc_outside_tool_folders(self):
        # review r2 L-2: /sdlc:deploy appends to the runbook, so it can't name a hook, settings or sdlc's own state
        self.init()
        for bad in (".git/hooks/pre-commit", ".git/x.md", ".claude/settings.json", ".claude/rules/x.md",
                    ".sdlc/config.md", "knowledge/runbooks/deploy.txt", "deploy"):
            self.sc("deploy", "--runbook", bad, expect=2)
        self.assertEqual(self.sc("deploy", "--runbook", "docs/ops/deploy.md")["deploy"]["runbook"], "docs/ops/deploy.md")
        config = json.loads(self.read(".sdlc/config.json"))
        config["deploy"]["runbook"] = ".claude/settings.json"
        self.write(".sdlc/config.json", json.dumps(config))
        self.assertIn("runbook", self.sc("deploy")["invalid"])

    def test_impeccable_enable_refuses_a_linked_local_settings_file(self):
        # R2-M2 of 2026-11-22-s-fixed-writers-refuse-links: the enable goes through fixed_target
        self.init()
        self.installed()
        outside = tempfile.mkdtemp(prefix="sdlc-outside-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        target = os.path.join(outside, "local.json")
        with open(target, "w", encoding="utf-8") as f:
            f.write("{}")
        self.linked_out(".claude/settings.local.json", target)
        self.write("claude-config/plugins/installed_plugins.json", json.dumps({"version": 2, "plugins": {
            "impeccable@x": [{"scope": "user", "installPath": self.path("claude-config/impeccable")}]}}))
        out = self.sc("design", "impeccable", "--enable", expect=2)
        self.assertIn("settings.local.json", out["refused"])
        with open(target, encoding="utf-8") as f:
            self.assertEqual(f.read(), "{}")

    def test_impeccable_mode_drops_ui_guardrail(self):
        # impeccable's detector hook does this job; both would report the same value on every edit
        self.template("templates/project/hookify/sdlc-ui-hardcoded-values.md", "ui\n")
        self.template("templates/project/hookify/sdlc-rm.md", "rm\n")
        self.init()
        self.sc("design", "impeccable")
        self.assertEqual([g["dest"] for g in self.sc("guardrails")["guardrails"]], [".claude/hookify/sdlc-rm.md"])
        self.assertEqual([i["path"] for i in self.sc("upgrade-plan")["add"]], [".claude/hookify/sdlc-rm.md"])
        self.sc("design", "builtin")
        self.assertEqual([g["dest"] for g in self.sc("guardrails")["guardrails"]],
                         [".claude/hookify/sdlc-rm.md", ".claude/hookify/sdlc-ui-hardcoded-values.md"])

    def test_switching_design_mode_swaps_the_ui_guardrail(self):
        # setup renders guardrails before it asks the mode, so the switch itself must swap the file, both ways
        tpl, dest = "templates/project/hookify/sdlc-ui-hardcoded-values.md", ".claude/hookify/sdlc-ui-hardcoded-values.md"
        self.template(tpl, "ui\n")
        self.init()
        self.sc("render", tpl, dest, "--class", "seeded")
        self.impeccable_plugin(enabled=True)  # its detector hook runs here, so the swap may happen
        self.assertEqual(self.sc("design", "impeccable")["guardrail"], {"removed": dest})
        self.assertFalse(os.path.exists(self.path(dest)))
        self.assertNotIn(dest, self.lock()["files"])
        self.assertNotIn(dest, self.lock().get("declined", []))  # untracked, not handed to the user for good
        self.assertEqual(self.sc("design", "builtin")["guardrail"], {"added": dest})
        self.assertEqual(self.read(dest), "ui\n")
        self.write(dest, "the team's edit\n")
        self.assertEqual(self.sc("design", "impeccable")["guardrail"]["ask"], dest)  # edited: never deleted
        self.assertEqual(self.read(dest), "the team's edit\n")

    def impeccable_plugin(self, enabled=None):
        """impeccable installed as a Claude Code plugin on this machine; enabled True/False sets it in the repo's
        local settings, None leaves it unlisted (off, as Claude Code reads it)."""
        self.write("claude-config/plugins/installed_plugins.json", json.dumps(
            {"version": 2, "plugins": {"impeccable@claude-community": [{"scope": "user", "installPath": "/x"}]}}))
        if enabled is not None:
            self.write(".claude/settings.local.json",
                       json.dumps({"enabledPlugins": {"impeccable@claude-community": enabled}}))

    def test_a_disabled_impeccable_plugin_is_installed_but_not_enabled(self):
        self.init()
        home = {"HOME": self.path("home"), "USERPROFILE": self.path("home")}  # keep this machine's skills out
        self.assertEqual(self.sc("design", env=home)["impeccable"], {"state": "missing", "hook": False})
        self.impeccable_plugin()
        out = self.sc("design", env=home)
        self.assertTrue(out["impeccable_installed"])
        self.assertEqual(out["impeccable"]["state"], "disabled")
        self.assertEqual(out["impeccable"]["plugin"], "impeccable@claude-community")
        self.write("claude-config/settings.json", json.dumps({"enabledPlugins": {"impeccable@claude-community": True}}))
        self.assertEqual(self.sc("design", env=home)["impeccable"]["state"], "enabled")  # on for every project
        self.write(".claude/settings.local.json", json.dumps({"enabledPlugins": {"impeccable@claude-community": False}}))
        self.assertEqual(self.sc("design", env=home)["impeccable"]["state"], "disabled")  # the repo's local file wins

    def test_design_enable_turns_impeccable_on_locally_and_enable_plugin_remove_takes_it_back(self):
        self.init()
        home = {"HOME": self.path("home"), "USERPROFILE": self.path("home")}
        self.assertIn("never installs", self.sc("design", "impeccable", "--enable", expect=2, env=home)["refused"])
        self.assertEqual(self.sc("design", env=home)["design"], "builtin")  # refused: the mode wasn't recorded
        self.impeccable_plugin()
        out = self.sc("design", "impeccable", "--enable", env=home)
        self.assertEqual(out["enabled"]["plugin"], "impeccable@claude-community")
        self.assertIn("next session", out["enabled"]["loads"])
        self.assertEqual(out["impeccable"]["state"], "enabled")
        settings = json.loads(self.read(".claude/settings.local.json"))
        self.assertIs(settings["enabledPlugins"]["impeccable@claude-community"], True)
        self.assertNotIn("enabledPlugins", json.loads(self.read(".claude/settings.json")) if os.path.exists(
            self.path(".claude/settings.json")) else {})  # never the team's file
        self.assertNotIn("enabled", self.sc("design", "impeccable", "--enable", env=home))  # already on: no-op
        self.sc("enable-plugin", "--remove")
        self.assertNotIn("impeccable@claude-community",
                         json.loads(self.read(".claude/settings.local.json")).get("enabledPlugins", {}))
        self.write(".claude/settings.json", json.dumps({"enabledPlugins": {"impeccable@claude-community": False}}))
        self.assertIn(".claude/settings.json", self.sc("design", "impeccable", "--enable", expect=2, env=home)["refused"])

    def test_impeccable_mode_keeps_the_ui_guardrail_until_its_hook_runs(self):
        tpl, dest = "templates/project/hookify/sdlc-ui-hardcoded-values.md", ".claude/hookify/sdlc-ui-hardcoded-values.md"
        self.template(tpl, "ui\n")
        self.init()
        self.sc("render", tpl, dest, "--class", "seeded")
        home = {"HOME": self.path("home"), "USERPROFILE": self.path("home")}
        self.impeccable_plugin()  # installed, off here: its hook won't run
        self.assertEqual(self.sc("design", "impeccable", "--enable", env=home)["guardrail"]["kept"], dest)
        self.assertTrue(os.path.exists(self.path(dest)))
        self.write(".impeccable/config.json", json.dumps({"hook": {"enabled": False}}))  # /impeccable hooks off
        self.assertEqual(self.sc("design", "impeccable", env=home)["guardrail"]["kept"], dest)
        self.write(".impeccable/config.local.json", json.dumps({"hook": {"enabled": True}}))  # this machine's on
        self.assertEqual(self.sc("design", "impeccable", env=home)["guardrail"], {"removed": dest})

    def test_impeccable_config_linked_out_of_the_repo_or_into_git_reads_as_absent(self):
        # a committed .impeccable/config.json is read through sdlc_scopes.read_repo_text (doctor and scaffold both
        # ask impeccable_hook_off), never through a link out of the repo or into .git
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        import scaffold
        off = json.dumps({"hook": {"enabled": False}})
        self.write(".impeccable/config.json", off)
        self.assertTrue(scaffold.impeccable_hook_off(self.root))  # a plain file still reads
        outside = os.path.realpath(tempfile.mkdtemp(prefix="sdlc-outside-"))
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        with open(os.path.join(outside, "config.json"), "w", encoding="utf-8") as f:
            f.write(off)
        self.write(".git/config.json", off)
        for target in (os.path.join(outside, "config.json"), os.path.join("..", ".git", "config.json")):
            os.remove(self.path(".impeccable/config.json"))
            try:  # Windows without the symlink privilege can't make one
                os.symlink(target, self.path(".impeccable/config.json"))
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            self.assertFalse(scaffold.impeccable_hook_off(self.root), target)

    def test_a_skill_folder_impeccable_needs_its_hook_manifest(self):
        self.init()
        home = {"HOME": self.path("home"), "USERPROFILE": self.path("home")}
        self.write(".claude/skills/impeccable/SKILL.md", "---\nname: impeccable\n---\n")
        self.assertEqual(self.sc("design", env=home)["impeccable"], {"state": "enabled", "via": "skill", "hook": False})
        self.write(".claude/settings.local.json", json.dumps({"hooks": {"PostToolUse": [{"hooks": [{
            "type": "command", "command": 'node "${CLAUDE_PROJECT_DIR}/.claude/skills/impeccable/scripts/hook.mjs"'}]}]}}))
        self.assertTrue(self.sc("design", env=home)["impeccable"]["hook"])

    def test_a_pending_step_runs_again_and_blocks_completing_setup(self):
        self.init()
        out = self.sc("step-done", "design-system", "--pending", "impeccable loads next session")
        self.assertNotIn("design-system", out["completed_steps"])
        self.assertEqual(self.sc("status")["pending_steps"], {"design-system": "impeccable loads next session"})
        self.assertIn("design-system", self.sc("step-done", "finalize", "--complete", expect=2)["refused"])
        self.assertEqual(self.sc("status")["setup"], "in_progress")
        self.sc("step-done", "design-system")
        self.assertEqual(self.sc("status")["pending_steps"], {})
        self.assertTrue(self.sc("step-done", "finalize", "--complete")["complete"])

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
        self.assertIn("package without a name", out["scopes"]["nowhere"]["problems"])  # named after its path
        self.assertIn("path 'nowhere' does not exist", out["scopes"]["nowhere"]["problems"])

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

    def test_builtin_ci_takes_a_stack_written_as_one_name(self):
        # Setup agents write "stack": "node" as often as ["node"]; read as letters it left the CI with # TODO lines
        self.commands_config(project={"stack": "node"}, commands={"test": "npm test"})
        self.sc("render", "builtin:ci", ".github/workflows/sdlc-verify.yml", "--class", "seeded")
        text = self.read(".github/workflows/sdlc-verify.yml")
        self.assertIn("actions/setup-node@v7", text)
        self.assertNotIn("TODO", text)

    def test_upgrade_offers_the_invariants_check_to_a_repo_with_ci(self):
        self.commands_config(project={"stack": ["typescript"]}, commands={"install": "pnpm install", "test": "pnpm test"})
        offered = lambda: {i["path"]: i["template"] for i in self.sc("upgrade-plan")["add"]}
        self.assertNotIn(".sdlc/ci/invariants.py", offered())  # no CI chosen: nothing to sit next to
        self.sc("render", "builtin:ci", ".github/workflows/sdlc-verify.yml", "--class", "seeded")
        self.template("templates/project/ci/invariants.py", "print('ok')\n")
        self.assertEqual({k: v for k, v in offered().items() if "invariants" in k},
                         {".sdlc/ci/invariants.py": "templates/project/ci/invariants.py",
                          ".github/workflows/sdlc-invariants.yml": "builtin:invariants"})
        for tpl, dest in (("templates/project/ci/invariants.py", ".sdlc/ci/invariants.py"),
                          ("builtin:invariants", ".github/workflows/sdlc-invariants.yml")):
            self.sc("render", tpl, dest, "--class", "seeded")
        self.assertFalse([k for k in offered() if "invariants" in k])

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

    def test_a_generated_entry_never_overwrites_or_deletes_an_untracked_local_file(self):
        # .sdlc/2026-11-22-s-generated-untracked AC-001 (security review S-2 of 2026-11-22-s-lock-template-trusted)
        self.git("init", "-q", "-b", "main")
        self.init()
        self.sc("render", "templates/project/ci.yml", ".env")  # a committed lock can name any path as generated
        self.sc("render", "templates/project/ci.yml", ".github/workflows/sdlc-x.yml")
        self.git("add", ".github", ".sdlc")
        self.git("commit", "-q", "-m", "x")
        self.write(".env", "API_KEY=local\n")  # the user's local file, never committed
        self.write(".github/workflows/sdlc-x.yml", "edited\n")  # tracked: regenerated as before
        plan = self.sc("upgrade-plan")
        regen = [i["path"] for i in plan["regenerate"]]
        self.assertNotIn(".env", regen)
        self.assertIn(".env", [i["path"] for i in plan["review"]])
        self.assertIn(".github/workflows/sdlc-x.yml", regen)
        eject = self.sc("eject")
        self.assertNotIn(".env", eject["delete"])
        self.assertIn(".env", eject["ask"])
        self.assertIn(".github/workflows/sdlc-x.yml", eject["delete"])
        self.sc("eject", "--apply")
        self.assertEqual(self.read(".env"), "API_KEY=local\n")

    def test_untracked_holds_when_git_refuses_the_repo_or_the_name_is_a_pathspec(self):
        # end-of-push review r1 M2, L1
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        import scaffold
        self.git("init", "-q", "-b", "main")
        self.write("[ab].txt", "x")
        self.write("a.txt", "x")
        self.git("add", "a.txt")
        self.git("commit", "-q", "-m", "x")
        p = scaffold.Project(self.root)
        self.assertTrue(p.untracked("[ab].txt"))  # as a pathspec it would match the tracked a.txt
        self.assertFalse(p.untracked("a.txt"))
        old = os.environ.get("GIT_DIR")
        os.environ["GIT_DIR"] = self.path("nowhere")
        try:
            self.assertTrue(p.untracked("a.txt"))  # git refuses: kept, never overwritten
        finally:
            os.environ.pop("GIT_DIR") if old is None else os.environ.__setitem__("GIT_DIR", old)

    def test_untracked_fails_closed_when_the_project_is_below_the_git_toplevel(self):
        # a monorepo package: its root holds no .git of its own, so a repo git refuses was read as "no repo", every
        # file as tracked, and a local file that differs from the lock was rendered over or deleted
        sys.path.insert(0, os.path.join(PLUGIN_ROOT, "scripts"))
        import scaffold
        self.git("init", "-q", "-b", "main")
        self.write("pkg/a.txt", "x")
        self.git("add", "pkg/a.txt")
        self.git("commit", "-q", "-m", "x")
        p = scaffold.Project(self.path("pkg"))
        self.assertFalse(p.untracked("a.txt"))
        self.assertTrue(p.untracked("b.txt"))
        old = os.environ.get("GIT_DIR")
        os.environ["GIT_DIR"] = self.path("nowhere")
        try:
            self.assertTrue(p.untracked("a.txt"))  # git refuses: kept, never overwritten
        finally:
            os.environ.pop("GIT_DIR") if old is None else os.environ.__setitem__("GIT_DIR", old)
        shutil.rmtree(self.path(".git"))
        self.write(".git", "gitdir: nowhere\n")  # a broken worktree link above the project
        self.assertTrue(p.untracked("a.txt"))
        # end review SP-H1: the project opened through a link from outside the repo still finds the real parents
        away = tempfile.mkdtemp(prefix="sdlc-away-")
        self.addCleanup(shutil.rmtree, away, ignore_errors=True)
        try:
            os.symlink(self.path("pkg"), os.path.join(away, "pkg"), target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.assertTrue(scaffold.Project(os.path.join(away, "pkg")).untracked("a.txt"))
        outside = os.path.realpath(tempfile.mkdtemp(prefix="sdlc-norepo-"))
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        self.assertFalse(scaffold.Project(outside).untracked("a.txt"))  # no repo at all: nothing to tell apart

    def legacy_repo(self, files):
        self.git("init", "-q", "-b", "main")
        for path in files:
            self.write(path, "x\n")
        self.init()
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "legacy")

    def test_relocate_moves_old_layout_and_is_idempotent(self):
        self.legacy_repo([".sdlc/f1/state.md", ".sdlc/f1/spec.md", ".sdlc/f1/checklists/r.md", ".sdlc/f2/state.md",
                          ".sdlc/f2/change.md", ".sdlc/constitution.md", ".sdlc/baseline.md", ".sdlc/lint/x.mjs"])
        self.assertNotIn("docs_dir", self.config())
        dry = self.sc("relocate")
        self.assertFalse(dry["applied"])
        self.assertIn([".sdlc/f1/state.md", ".sdlc/state/f1.md"], dry["moves"])
        self.assertFalse(os.path.exists(self.path(".sdlc/state/f1.md")))
        self.sc("relocate", "--apply")
        for path in (".sdlc/state/f1.md", "docs/sdlc/intents/f1/spec.md", "docs/sdlc/intents/f1/checklists/r.md",
                     "docs/sdlc/changes/f2.md",  # a 2.0 feature's change file goes to changes/
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

    # --- hosts and AGENTS.md (real workflow and policy templates) -----------------------------

    def real(self, *args, expect=0, env=None):
        code, out, raw, err = run_hook([sys.executable, SCRIPT, "--root", self.root, *args], "", self.root,
                                       env_extra={"CLAUDE_PLUGIN_ROOT": PLUGIN_ROOT, **(env or {})})
        self.assertEqual(code, expect, f"{args}: {raw}{err}")
        return out

    def hosted_project(self, *hosts):
        self.real("init", "--kind", "brownfield", "--host", hosts[0])
        for h in hosts[1:]:
            self.real("add-host", h)
        self.write("CLAUDE.md", "# Repo\n\n@docs/extra.md\nRun `/sdlc:doctor` weekly.\n\n```python\n@pytest.fixture\n```\n")
        self.write(".claude/rules/api.md", '---\npaths:\n  - "src/api/**"\n---\n# API\n\nVersion every route.\n')

    def test_host_comes_from_the_install_folder_then_the_environment(self):
        codex_install = os.path.join(self.root, ".codex", "plugins", "cache", "m", "sdlc", "1.0.0")
        shutil.copytree(os.path.join(PLUGIN_ROOT, "scripts"), os.path.join(codex_install, "scripts"))
        shutil.copytree(os.path.join(PLUGIN_ROOT, "hooks"), os.path.join(codex_install, "hooks"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        code, out, raw, err = run_hook([sys.executable, os.path.join(codex_install, "scripts", "scaffold.py"), "--root",
                                        self.root, "host"], "", self.root, env_extra={"CLAUDE_PLUGIN_ROOT": codex_install})
        self.assertEqual((out["host"], out["via"]), ("codex", "install path"), raw + err)  # CLAUDECODE=1 loses
        moved = {"CLAUDECODE": "", "CODEX_THREAD_ID": "t", "CLAUDE_CONFIG_DIR": os.path.dirname(PLUGIN_ROOT)}
        self.assertEqual(self.real("host", env=moved)["via"], "install path")  # config folder outside ~/.claude
        self.assertEqual(self.real("host", env={"CLAUDECODE": "", "CURSOR_AGENT": "1"})["host"], "cursor")
        nested = {"CODEX_THREAD_ID": "t"}  # Codex started from a Claude Code shell: can't tell, so setup asks
        self.assertIsNone(self.real("host", env=nested)["host"])
        self.assertIn("--host", self.real("init", "--kind", "greenfield", expect=1, env=nested)["error"])

    def test_a_second_agent_joins_and_gets_one_block_with_the_users_text_kept(self):
        self.hosted_project("claude-code")
        self.assertTrue(self.real("host", env={"CLAUDECODE": "", "CODEX_THREAD_ID": "t"})["joining"])
        with open(self.path("AGENTS.md"), "wb") as f:
            f.write(b"# Ours\r\n\r\nUse pnpm.\r\n")
        self.assertIsNone(self.real("agents")["mirror"])  # Claude Code alone: nothing to mirror yet
        self.real("add-host", "codex")
        self.real("agents")
        with open(self.path("AGENTS.md"), "rb") as f:
            first = f.read()
        self.real("agents")
        with open(self.path("AGENTS.md"), "rb") as f:
            self.assertEqual(f.read(), first)  # deterministic: a rebuild changes nothing
        text = first.decode()
        self.assertTrue(text.startswith("# Ours\r\n\r\nUse pnpm.\r\n\r\n<!-- sdlc:begin"))
        self.assertNotIn("\n", text.replace("\r\n", ""))  # the block follows the file's CRLF
        self.assertIn("Never edit these files", text)
        self.assertIn("Also read `docs/extra.md`.", text)
        self.assertIn("`/sdlc:doctor` (Claude Code)", text)
        self.assertIn("\r\n@pytest.fixture\r\n", text)  # code samples aren't imports
        self.assertIn("### API\r\n\r\nApplies when working on files matching `src/api/**`.", text)
        self.assertIn("### Code style (sdlc policy)", text)  # policy rules come from the templates
        # Claude Code doesn't read AGENTS.md: the team's own text reaches it through a generated rule
        self.assertIn("Use pnpm.", self.read(".claude/rules/sdlc-agents-md.md"))
        self.assertNotIn("sdlc:begin", self.read(".claude/rules/sdlc-agents-md.md"))
        self.assertEqual(self.lock()["hosts"], ["claude-code", "codex"])

    def test_agents_stops_at_a_claude_only_line(self):
        self.hosted_project("codex")
        self.write("CLAUDE.md", "# Repo\n\nRun ${CLAUDE_PLUGIN_ROOT}/x.\n")
        self.assertIn("CLAUDE.md:3:", self.real("agents", expect=1)["error"])
        self.assertFalse(os.path.exists(self.path("AGENTS.md")))

    def test_agents_check_and_upgrade_plan_report_drift(self):
        self.hosted_project("claude-code", "codex")
        self.real("agents")
        self.assertEqual(self.real("agents", "--check")["state"], "in_sync")
        self.write(".claude/rules/api.md", "# API\n\nVersion every route, always.\n")
        self.assertIn("out of date", self.real("agents", "--check", expect=1)["error"])
        self.assertEqual(self.real("upgrade-plan")["agents"], "stale")

    def test_a_repo_without_claude_code_gets_no_claude_files(self):
        self.hosted_project("codex")
        self.write("AGENTS.md", "Use pnpm.\n")
        self.assertIsNone(self.real("agents")["mirror"])
        self.assertEqual(self.real("upgrade-plan")["add"], [])
        self.assertIn("unknown host", self.real("add-host", "gemini", expect=1)["error"])

    def test_eject_removes_the_block_and_a_file_it_created(self):
        self.hosted_project("codex")
        self.real("agents")
        self.real("eject", "--apply")
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
